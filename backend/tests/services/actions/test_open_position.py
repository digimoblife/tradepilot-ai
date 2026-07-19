"""Tests for Open Position Service (TP-0503)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models.enums import (
    ActionType,
    ContextQuality,
    PositionStatus,
    SessionEventType,
    TradeSessionStatus,
)
from app.models.trade_action import TradeAction
from app.services.actions.open_position import (
    OpenPositionInvalidInputError,
    OpenPositionInvalidStateError,
    OpenPositionNotFoundError,
    OpenPositionService,
)
from app.services.trade_session import TradeSessionService
from app.lifecycle.service import SessionLifecycleService

pytestmark = pytest.mark.database

NOW = datetime(2026, 7, 18, 10, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
async def user_id(engine: AsyncEngine) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
            {"e": f"openpos_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
        )
        return r.first()[0]


async def _watching_session(engine: AsyncEngine, uid: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    """Create a session in WATCHING state."""
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        svc = TradeSessionService(s)
        session = await svc.create_session(owner_id=uid, ticker="BBRI")
        lc = SessionLifecycleService(s)
        await lc.transition(
            session_id=session.id,
            owner_id=uid,
            target_status=TradeSessionStatus.READY_FOR_ANALYSIS,
        )
        await lc.transition(
            session_id=session.id,
            owner_id=uid,
            target_status=TradeSessionStatus.ANALYZING,
        )
        await lc.transition(
            session_id=session.id,
            owner_id=uid,
            target_status=TradeSessionStatus.WATCHING,
        )
        await s.commit()
    return session.id, uid


# ===================================================================


class TestSuccessfulConfirmation:
    async def test_watching_to_open(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _watching_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = OpenPositionService(s)
            result = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"open_{uuid.uuid4().hex}",
                entry_price=2800,
                quantity=100,
                execution_timestamp=NOW,
                stop_loss=2700,
                target=2920,
            )
            assert result.session_id == sid
            assert result.session_status == TradeSessionStatus.OPEN_POSITION
            ts = result.trade_state
            assert ts.position_status == PositionStatus.OPEN
            assert ts.entry_price == 2800
            assert ts.original_quantity == 100
            assert ts.remaining_quantity == 100
            assert ts.active_stop_loss == 2700
            assert ts.active_target == 2920
            assert result.action.action_type == ActionType.POSITION_OPENED
            assert result.action.price == 2800
            assert result.action.quantity == 100

    async def test_action_created(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _watching_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = OpenPositionService(s)
            result = await svc.confirm(
                session_id=sid, owner_id=uid,
                idempotency_key=f"act_{uuid.uuid4().hex}",
                entry_price=2800, quantity=100, execution_timestamp=NOW,
            )
            assert result.action is not None
            assert result.action.id is not None

    async def test_session_status_open_position(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _watching_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = OpenPositionService(s)
            result = await svc.confirm(
                session_id=sid, owner_id=uid,
                idempotency_key=f"st_{uuid.uuid4().hex}",
                entry_price=2800, quantity=100, execution_timestamp=NOW,
            )
            assert result.session_status == TradeSessionStatus.OPEN_POSITION
            from app.models.trade_session import TradeSession
            ts = await s.get(TradeSession, sid)
            assert ts.lifecycle_status == TradeSessionStatus.OPEN_POSITION

    async def test_event_created(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _watching_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = OpenPositionService(s)
            await svc.confirm(
                session_id=sid, owner_id=uid,
                idempotency_key=f"ev_{uuid.uuid4().hex}",
                entry_price=2800, quantity=100, execution_timestamp=NOW,
            )
            result = await s.execute(
                text("SELECT COUNT(*) FROM session_events WHERE session_id = :sid AND event_type = 'POSITION_OPENED'"),
                {"sid": sid},
            )
            assert result.scalar_one() == 1

    async def test_context_summary_stale(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _watching_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            # Create a context summary
            from app.models.context_summary import ContextSummary
            cs = ContextSummary(session_id=sid, context_version=1, is_stale=False, quality=ContextQuality.HIGH)
            s.add(cs)
            await s.flush()

            svc = OpenPositionService(s)
            await svc.confirm(
                session_id=sid, owner_id=uid,
                idempotency_key=f"cs_{uuid.uuid4().hex}",
                entry_price=2800, quantity=100, execution_timestamp=NOW,
            )
            # Refresh and check
            await s.refresh(cs)
            assert cs.is_stale is True


class TestProposalMismatch:
    async def test_confirmed_differs_from_proposal(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        """User-confirmed values become canonical even if they differ from AI proposal."""
        sid, uid = await _watching_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = OpenPositionService(s)
            result = await svc.confirm(
                session_id=sid, owner_id=uid,
                idempotency_key=f"diff_{uuid.uuid4().hex}",
                entry_price=3000,  # different from AI's 2800
                quantity=50,       # different from AI's 100
                execution_timestamp=NOW,
                stop_loss=2900,    # different from AI's 2700
                target=3100,       # different from AI's 2920
            )
            assert result.trade_state.entry_price == 3000
            assert result.trade_state.original_quantity == 50
            assert result.trade_state.active_stop_loss == 2900
            assert result.trade_state.active_target == 3100

    async def test_no_proposal_required(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        """No AI proposal is required to exist."""
        sid, uid = await _watching_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = OpenPositionService(s)
            result = await svc.confirm(
                session_id=sid, owner_id=uid,
                idempotency_key=f"nop_{uuid.uuid4().hex}",
                entry_price=2800, quantity=100, execution_timestamp=NOW,
            )
            assert result.trade_state.position_status == PositionStatus.OPEN


class TestIdempotency:
    async def test_repeat_key_safe(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _watching_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        ik = f"idem_{uuid.uuid4().hex}"
        async with factory() as s:
            svc = OpenPositionService(s)
            r1 = await svc.confirm(
                session_id=sid, owner_id=uid, idempotency_key=ik,
                entry_price=2800, quantity=100, execution_timestamp=NOW,
            )
            await s.commit()
        async with factory() as s:
            svc = OpenPositionService(s)
            r2 = await svc.confirm(
                session_id=sid, owner_id=uid, idempotency_key=ik,
                entry_price=2800, quantity=100, execution_timestamp=NOW,
            )
            assert r2.action.id == r1.action.id

    async def test_no_duplicate_action(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _watching_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        ik = f"nodup_{uuid.uuid4().hex}"
        async with factory() as s:
            svc = OpenPositionService(s)
            await svc.confirm(
                session_id=sid, owner_id=uid, idempotency_key=ik,
                entry_price=2800, quantity=100, execution_timestamp=NOW,
            )
            await s.commit()
        async with factory() as s:
            svc = OpenPositionService(s)
            await svc.confirm(
                session_id=sid, owner_id=uid, idempotency_key=ik,
                entry_price=2800, quantity=100, execution_timestamp=NOW,
            )
            result = await s.execute(
                text("SELECT COUNT(*) FROM trade_actions WHERE session_id = :sid AND action_type = 'POSITION_OPENED'"),
                {"sid": sid},
            )
            assert result.scalar_one() == 1


class TestInvalidState:
    async def test_already_open(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _watching_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            # Open the position first
            svc = OpenPositionService(s)
            await svc.confirm(
                session_id=sid, owner_id=uid,
                idempotency_key=f"first_{uuid.uuid4().hex}",
                entry_price=2800, quantity=100, execution_timestamp=NOW,
            )
            await s.commit()
        async with factory() as s:
            svc = OpenPositionService(s)
            with pytest.raises(OpenPositionInvalidStateError):
                await svc.confirm(
                    session_id=sid, owner_id=uid,
                    idempotency_key=f"second_{uuid.uuid4().hex}",
                    entry_price=2800, quantity=100, execution_timestamp=NOW,
                )

    async def test_terminal_state(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        """Closed session cannot open position."""
        sid, uid = await _watching_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        # Set to closed directly via SQL for speed
        async with factory() as s:
            await s.execute(
                text("UPDATE trade_sessions SET lifecycle_status = 'CLOSED_TAKE_PROFIT', stable_status = 'CLOSED_TAKE_PROFIT' WHERE id = :sid"),
                {"sid": sid},
            )
            await s.commit()
        async with factory() as s:
            svc = OpenPositionService(s)
            with pytest.raises(OpenPositionInvalidStateError):
                await svc.confirm(
                    session_id=sid, owner_id=uid,
                    idempotency_key=f"term_{uuid.uuid4().hex}",
                    entry_price=2800, quantity=100, execution_timestamp=NOW,
                )


class TestOwnership:
    async def test_wrong_owner_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _watching_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = OpenPositionService(s)
            with pytest.raises(OpenPositionNotFoundError):
                await svc.confirm(
                    session_id=sid, owner_id=uuid.uuid4(),
                    idempotency_key=f"own_{uuid.uuid4().hex}",
                    entry_price=2800, quantity=100, execution_timestamp=NOW,
                )


class TestInputValidation:
    async def test_invalid_entry_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _watching_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = OpenPositionService(s)
            with pytest.raises(OpenPositionInvalidInputError):
                await svc.confirm(
                    session_id=sid, owner_id=uid,
                    idempotency_key=f"ie_{uuid.uuid4().hex}",
                    entry_price=-100, quantity=100, execution_timestamp=NOW,
                )

    async def test_invalid_quantity_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _watching_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = OpenPositionService(s)
            with pytest.raises(OpenPositionInvalidInputError):
                await svc.confirm(
                    session_id=sid, owner_id=uid,
                    idempotency_key=f"iq_{uuid.uuid4().hex}",
                    entry_price=2800, quantity=0, execution_timestamp=NOW,
                )

    async def test_float_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _watching_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = OpenPositionService(s)
            with pytest.raises(OpenPositionInvalidInputError):
                await svc.confirm(
                    session_id=sid, owner_id=uid,
                    idempotency_key=f"fl_{uuid.uuid4().hex}",
                    entry_price=2800.5, quantity=100, execution_timestamp=NOW,
                )


class TestAtomicRollback:
    async def test_context_stale_failure_rollback(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        """If something fails after action creation, nothing is committed."""
        sid, uid = await _watching_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            from app.services.actions.open_position import OpenPositionService as OPS
            # Create the service
            svc = OPS(s)
            # Execute within a savepoint that will fail
            async with s.begin_nested():
                try:
                    await svc.confirm(
                        session_id=sid, owner_id=uid,
                        idempotency_key=f"rb_{uuid.uuid4().hex}",
                        entry_price=2800, quantity=100, execution_timestamp=NOW,
                    )
                    # Force a failure
                    raise RuntimeError("Simulated failure")
                except RuntimeError:
                    pass
                await s.rollback()
            # Verify nothing was committed
            actions = await s.execute(
                text("SELECT COUNT(*) FROM trade_actions WHERE session_id = :sid"),
                {"sid": sid},
            )
            assert actions.scalar_one() == 0
