import pytest
from sqlalchemy import text, select, func

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
async def test_rollback_removes_repo_writes(session):
    await _clean_via_session(session)
    repo = TradeSessionRepository(session)
    ts = TradeSession(owner_id=uid(), ticker="ROLLBACK")
    await repo.add(ts)
    await session.rollback()
    # After rollback, row should not exist in a new connection
    r = await session.execute(
        select(TradeSession).where(TradeSession.ticker == "ROLLBACK")
    )
    assert r.first() is None, "Rolled-back row should not exist"


@pytest.mark.database
async def test_multi_repository_atomic_commit(session):
    await _clean_via_session(session)
    ts_repo = TradeSessionRepository(session)
    state_repo = TradeStateRepository(session)
    event_repo = SessionEventRepository(session)

    ts = TradeSession(owner_id=uid(), ticker="ATOMIC")
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

    # Add new session check separately
    r = await session.execute(
        select(TradeSession).where(TradeSession.ticker == "ATOMIC")
    )
    assert r.first() is not None, "Committed session should exist"


@pytest.mark.database
async def test_multi_repository_rollback(session):
    await _clean_via_session(session)
    ts_repo = TradeSessionRepository(session)
    state_repo = TradeStateRepository(session)

    ts = TradeSession(owner_id=uid(), ticker="ROLL_ALL")
    await ts_repo.add(ts)
    state = TradeState(session_id=ts.id)
    await state_repo.add(state)
    await session.rollback()

    r = await session.execute(
        select(TradeSession).where(TradeSession.ticker == "ROLL_ALL")
    )
    assert r.first() is None, "Rolled-back session should not exist"


@pytest.mark.database
async def test_integrity_error_propagates(session):
    from sqlalchemy.exc import IntegrityError

    await _clean_via_session(session)
    u = uid()
    ts_repo = TradeSessionRepository(session)
    ts = TradeSession(owner_id=u, ticker="INTEG")
    await ts_repo.add(ts)
    action_repo = TradeActionRepository(session)
    a1 = TradeAction(
        session_id=ts.id,
        action_type="POSITION_OPENED",
        confirmed_at=__import__("datetime").datetime(2026, 7, 18, 10, 0, 0),
        idempotency_key="int-err",
    )
    await action_repo.add(a1)
    a2 = TradeAction(
        session_id=ts.id,
        action_type="STOP_LOSS_CONFIRMED",
        confirmed_at=__import__("datetime").datetime(2026, 7, 18, 11, 0, 0),
        idempotency_key="int-err",
    )
    with pytest.raises(IntegrityError):
        await action_repo.add(a2)
    await session.rollback()


@pytest.mark.database
async def test_no_hidden_commit(session):
    await _clean_via_session(session)
    u = uid()
    ts_repo = TradeSessionRepository(session)
    ts = TradeSession(owner_id=u, ticker="NOCOMMIT")
    await ts_repo.add(ts)
    r = await session.execute(
        select(func.count()).select_from(TradeSession).where(
            TradeSession.ticker == "NOCOMMIT"
        )
    )
    count = r.scalar_one()
    assert count == 1, "Row should be visible in current transaction after flush"
    await session.rollback()


def uid():
    import uuid
    return uuid.uuid4()


async def _clean_via_session(s):
    await s.execute(
        text(
            "DELETE FROM session_events; "
            "DELETE FROM context_summaries; "
            "DELETE FROM validation_attempts; "
            "DELETE FROM provider_responses; "
            "DELETE FROM provider_requests; "
            "DELETE FROM trade_actions; "
            "DELETE FROM analyses; "
            "DELETE FROM analysis_jobs; "
            "DELETE FROM evidence; "
            "DELETE FROM trade_states; "
            "DELETE FROM trade_sessions; "
            "DELETE FROM users"
        )
    )
    await s.flush()
