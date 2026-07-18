import pytest
from sqlalchemy import text, select, func
from sqlalchemy.exc import IntegrityError

from app.models.trade_session import TradeSession
from app.models.trade_state import TradeState
from app.models.trade_action import TradeAction
from app.models.session_event import SessionEvent
from app.models.enums import SessionEventType
from app.repositories.trade_session import TradeSessionRepository
from app.repositories.trade_state import TradeStateRepository
from app.repositories.session_event import SessionEventRepository
from app.repositories.trade_action import TradeActionRepository


@pytest.mark.database
async def test_rollback_removes_repo_writes(session, engine):
    await _clean(engine)
    uid = await _make_user(engine)
    repo = TradeSessionRepository(session)
    ts = TradeSession(owner_id=uid, ticker="RBTEST")
    await repo.add(ts)
    await session.rollback()
    async with engine.begin() as c:
        r = await c.execute(text("SELECT id FROM trade_sessions WHERE ticker = 'RBTEST'"))
        assert r.first() is None


@pytest.mark.database
async def test_multi_repository_atomic_commit(session, engine):
    await _clean(engine)
    uid = await _make_user(engine)
    ts_repo = TradeSessionRepository(session)
    state_repo = TradeStateRepository(session)
    event_repo = SessionEventRepository(session)

    ts = TradeSession(owner_id=uid, ticker="ATOMIC")
    await ts_repo.add(ts)
    state = TradeState(session_id=ts.id)
    await state_repo.add(state)
    event = SessionEvent(
        session_id=ts.id,
        event_type=SessionEventType.SESSION_CREATED,
        occurred_at=__import__("datetime").datetime(2026, 7, 18, 9, 0, 0),
    )
    await event_repo.add(event)
    await session.commit()

    async with engine.begin() as c:
        r = await c.execute(text("SELECT id FROM trade_sessions WHERE ticker = 'ATOMIC'"))
        assert r.first() is not None
        r = await c.execute(
            text("SELECT session_id FROM trade_states WHERE session_id = :sid"), {"sid": ts.id}
        )
        assert r.first() is not None
        r = await c.execute(
            text("SELECT id FROM session_events WHERE session_id = :sid"), {"sid": ts.id}
        )
        assert r.first() is not None


@pytest.mark.database
async def test_multi_repository_database_failure_rollback(session, engine):
    await _clean(engine)
    uid = await _make_user(engine)
    ts_repo = TradeSessionRepository(session)
    state_repo = TradeStateRepository(session)
    action_repo = TradeActionRepository(session)

    ts = TradeSession(owner_id=uid, ticker="FAILROLL")
    await ts_repo.add(ts)
    state = TradeState(session_id=ts.id)
    await state_repo.add(state)

    a1 = TradeAction(
        session_id=ts.id,
        action_type="POSITION_OPENED",
        confirmed_at=__import__("datetime").datetime(2026, 7, 18, 10, 0, 0),
        idempotency_key="fail-dup",
    )
    await action_repo.add(a1)
    a2 = TradeAction(
        session_id=ts.id,
        action_type="STOP_LOSS_CONFIRMED",
        confirmed_at=__import__("datetime").datetime(2026, 7, 18, 11, 0, 0),
        idempotency_key="fail-dup",
    )
    with pytest.raises(IntegrityError):
        await action_repo.add(a2)
    await session.rollback()

    async with engine.begin() as c:
        r = await c.execute(text("SELECT id FROM trade_sessions WHERE ticker = 'FAILROLL'"))
        assert r.first() is None
        r = await c.execute(
            text("SELECT id FROM trade_actions WHERE idempotency_key = 'fail-dup'")
        )
        assert r.first() is None


@pytest.mark.database
async def test_integrity_error_propagates(session, engine):
    await _clean(engine)
    uid = await _make_user(engine)
    ts_repo = TradeSessionRepository(session)
    action_repo = TradeActionRepository(session)

    ts = TradeSession(owner_id=uid, ticker="IERR")
    await ts_repo.add(ts)
    a1 = TradeAction(
        session_id=ts.id, action_type="POSITION_OPENED",
        confirmed_at=__import__("datetime").datetime(2026, 7, 18, 10, 0, 0),
        idempotency_key="ierr",
    )
    await action_repo.add(a1)
    a2 = TradeAction(
        session_id=ts.id, action_type="STOP_LOSS_CONFIRMED",
        confirmed_at=__import__("datetime").datetime(2026, 7, 18, 11, 0, 0),
        idempotency_key="ierr",
    )
    with pytest.raises(IntegrityError):
        await action_repo.add(a2)
    await session.rollback()


@pytest.mark.database
async def test_no_hidden_commit(session, engine):
    import uuid

    await _clean(engine)
    uid = await _make_user(engine)
    repo = TradeSessionRepository(session)
    ts = TradeSession(owner_id=uid, ticker="NOCMT")
    await repo.add(ts)
    r = await session.execute(
        select(func.count()).select_from(TradeSession).where(TradeSession.ticker == "NOCMT")
    )
    assert r.scalar_one() == 1
    await session.rollback()
    r = await session.execute(
        select(func.count()).select_from(TradeSession).where(TradeSession.ticker == "NOCMT")
    )
    assert r.scalar_one() == 0


async def _clean(engine):
    async with engine.begin() as c:
        await c.execute(text("DELETE FROM session_events"))
        await c.execute(text("DELETE FROM context_summaries"))
        await c.execute(text("DELETE FROM validation_attempts"))
        await c.execute(text("DELETE FROM provider_responses"))
        await c.execute(text("DELETE FROM provider_requests"))
        await c.execute(text("DELETE FROM trade_actions"))
        await c.execute(text("DELETE FROM analyses"))
        await c.execute(text("DELETE FROM analysis_jobs"))
        await c.execute(text("DELETE FROM evidence"))
        await c.execute(text("DELETE FROM trade_states"))
        await c.execute(text("DELETE FROM trade_sessions"))
        await c.execute(text("DELETE FROM users"))


async def _make_user(engine):
    import uuid
    async with engine.begin() as c:
        r = (
            await c.execute(
                text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
                {"e": f"tx_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
            )
        ).first()
        return r[0]
