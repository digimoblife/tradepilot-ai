"""Tests for Stop Loss and Target Confirmation Services (TP-0504)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models.enums import (
    ActionType,
    ContextQuality,
    TradeSessionStatus,
)
from app.services.actions.open_position import OpenPositionService
from app.services.actions.stop_loss import (
    StopLossActionService,
    StopLossInvalidInputError,
    StopLossInvalidRelationshipError,
    StopLossInvalidStateError,
    StopLossNotFoundError,
)
from app.services.actions.target import (
    TargetActionService,
    TargetInvalidInputError,
    TargetInvalidRelationshipError,
    TargetInvalidStateError,
    TargetNotFoundError,
)
from app.services.trade_session import TradeSessionService

pytestmark = pytest.mark.database

NOW = datetime(2026, 7, 18, 10, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
async def user_id(engine: AsyncEngine) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
            {"e": f"st_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
        )
        return r.first()[0]


async def _open_session(engine: AsyncEngine, uid: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    """Create a session in OPEN_POSITION with entry=2800, qty=100."""
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        svc = TradeSessionService(s)
        session = await svc.create_session(owner_id=uid, ticker="BBRI")
        from app.lifecycle.service import SessionLifecycleService

        lc = SessionLifecycleService(s)
        await lc.transition(
            session_id=session.id,
            owner_id=uid,
            target_status=TradeSessionStatus.READY_FOR_ANALYSIS,
        )
        await lc.transition(
            session_id=session.id, owner_id=uid, target_status=TradeSessionStatus.ANALYZING
        )
        await lc.transition(
            session_id=session.id, owner_id=uid, target_status=TradeSessionStatus.WATCHING
        )
        await s.commit()

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        op = OpenPositionService(s)
        await op.confirm(
            session_id=session.id,
            owner_id=uid,
            idempotency_key=f"open_{uuid.uuid4().hex}",
            entry_price=2800,
            quantity=100,
            execution_timestamp=NOW,
        )
        await s.commit()
    return session.id, uid


# ===================================================================
# Stop Loss
# ===================================================================


class TestStopLossConfirm:
    async def test_initial_stop(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = StopLossActionService(s)
            result = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"sl_{uuid.uuid4().hex}",
                stop_loss=2700,
                confirmed_at=NOW,
            )
            assert result.action_type == ActionType.STOP_LOSS_CONFIRMED
            assert result.active_stop_loss == 2700

    async def test_stop_change(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = StopLossActionService(s)
            await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"sl1_{uuid.uuid4().hex}",
                stop_loss=2700,
                confirmed_at=NOW,
            )
            await s.commit()
        async with factory() as s:
            svc = StopLossActionService(s)
            result = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"sl2_{uuid.uuid4().hex}",
                stop_loss=2750,
                confirmed_at=NOW,
            )
            assert result.action_type == ActionType.STOP_LOSS_CHANGED
            assert result.active_stop_loss == 2750

    async def test_action_persisted(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        ik = f"ap_{uuid.uuid4().hex}"
        async with factory() as s:
            svc = StopLossActionService(s)
            await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=ik,
                stop_loss=2700,
                confirmed_at=NOW,
            )
            await s.commit()
        async with factory() as s:
            from sqlalchemy import select

            from app.models.trade_action import TradeAction

            act = (
                (await s.execute(select(TradeAction).where(TradeAction.idempotency_key == ik)))
                .unique()
                .scalar_one_or_none()
            )
            assert act is not None
            assert act.action_type == ActionType.STOP_LOSS_CONFIRMED
            assert act.price == 2700

    async def test_event_persisted(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = StopLossActionService(s)
            await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"ev_{uuid.uuid4().hex}",
                stop_loss=2700,
                confirmed_at=NOW,
            )
            await s.commit()
        async with factory() as s:
            cnt = (
                await s.execute(
                    text(
                        "SELECT COUNT(*) FROM session_events WHERE session_id = :sid AND event_type = 'STOP_LOSS_CHANGED'"
                    ),
                    {"sid": sid},
                )
            ).scalar_one()
            assert cnt >= 1

    async def test_context_summary_stale(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            from app.models.context_summary import ContextSummary

            cs = ContextSummary(
                session_id=sid, context_version=1, is_stale=False, quality=ContextQuality.HIGH
            )
            s.add(cs)
            await s.flush()
            svc = StopLossActionService(s)
            await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"cs_{uuid.uuid4().hex}",
                stop_loss=2700,
                confirmed_at=NOW,
            )
            await s.refresh(cs)
            assert cs.is_stale is True

    async def test_proposal_mismatch_allowed(
        self, engine: AsyncEngine, user_id: uuid.UUID
    ) -> None:
        """User-confirmed stop may differ from any AI proposal."""
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = StopLossActionService(s)
            result = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"pm_{uuid.uuid4().hex}",
                stop_loss=2650,  # different from any proposal
                confirmed_at=NOW,
            )
            assert result.active_stop_loss == 2650

    async def test_stop_equal_entry_rejected(
        self, engine: AsyncEngine, user_id: uuid.UUID
    ) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = StopLossActionService(s)
            with pytest.raises(StopLossInvalidRelationshipError):
                await svc.confirm(
                    session_id=sid,
                    owner_id=uid,
                    idempotency_key=f"eq_{uuid.uuid4().hex}",
                    stop_loss=2800,
                    confirmed_at=NOW,
                )

    async def test_stop_above_entry_rejected(
        self, engine: AsyncEngine, user_id: uuid.UUID
    ) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = StopLossActionService(s)
            with pytest.raises(StopLossInvalidRelationshipError):
                await svc.confirm(
                    session_id=sid,
                    owner_id=uid,
                    idempotency_key=f"ab_{uuid.uuid4().hex}",
                    stop_loss=2900,
                    confirmed_at=NOW,
                )

    async def test_float_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = StopLossActionService(s)
            with pytest.raises(StopLossInvalidInputError):
                await svc.confirm(
                    session_id=sid,
                    owner_id=uid,
                    idempotency_key=f"fl_{uuid.uuid4().hex}",
                    stop_loss=2700.5,
                    confirmed_at=NOW,
                )


# ===================================================================
# Target
# ===================================================================


class TestTargetConfirm:
    async def test_initial_target(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = TargetActionService(s)
            result = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"tg_{uuid.uuid4().hex}",
                target=2920,
                confirmed_at=NOW,
            )
            assert result.action_type == ActionType.TARGET_CONFIRMED
            assert result.active_target == 2920

    async def test_target_change(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = TargetActionService(s)
            await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"tg1_{uuid.uuid4().hex}",
                target=2920,
                confirmed_at=NOW,
            )
            await s.commit()
        async with factory() as s:
            svc = TargetActionService(s)
            result = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"tg2_{uuid.uuid4().hex}",
                target=3000,
                confirmed_at=NOW,
            )
            assert result.action_type == ActionType.TARGET_CHANGED
            assert result.active_target == 3000

    async def test_action_persisted(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        ik = f"tap_{uuid.uuid4().hex}"
        async with factory() as s:
            svc = TargetActionService(s)
            await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=ik,
                target=2920,
                confirmed_at=NOW,
            )
            await s.commit()
        async with factory() as s:
            from sqlalchemy import select

            from app.models.trade_action import TradeAction

            act = (
                (await s.execute(select(TradeAction).where(TradeAction.idempotency_key == ik)))
                .unique()
                .scalar_one_or_none()
            )
            assert act is not None
            assert act.action_type == ActionType.TARGET_CONFIRMED
            assert act.price == 2920

    async def test_event_persisted(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = TargetActionService(s)
            await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"tev_{uuid.uuid4().hex}",
                target=2920,
                confirmed_at=NOW,
            )
            await s.commit()
        async with factory() as s:
            cnt = (
                await s.execute(
                    text(
                        "SELECT COUNT(*) FROM session_events WHERE session_id = :sid AND event_type = 'TARGET_CHANGED'"
                    ),
                    {"sid": sid},
                )
            ).scalar_one()
            assert cnt >= 1

    async def test_proposal_mismatch_allowed(
        self, engine: AsyncEngine, user_id: uuid.UUID
    ) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = TargetActionService(s)
            result = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"tpm_{uuid.uuid4().hex}",
                target=3100,
                confirmed_at=NOW,
            )
            assert result.active_target == 3100

    async def test_target_equal_entry_rejected(
        self, engine: AsyncEngine, user_id: uuid.UUID
    ) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = TargetActionService(s)
            with pytest.raises(TargetInvalidRelationshipError):
                await svc.confirm(
                    session_id=sid,
                    owner_id=uid,
                    idempotency_key=f"teq_{uuid.uuid4().hex}",
                    target=2800,
                    confirmed_at=NOW,
                )

    async def test_target_below_entry_rejected(
        self, engine: AsyncEngine, user_id: uuid.UUID
    ) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = TargetActionService(s)
            with pytest.raises(TargetInvalidRelationshipError):
                await svc.confirm(
                    session_id=sid,
                    owner_id=uid,
                    idempotency_key=f"tbl_{uuid.uuid4().hex}",
                    target=2700,
                    confirmed_at=NOW,
                )

    async def test_float_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = TargetActionService(s)
            with pytest.raises(TargetInvalidInputError):
                await svc.confirm(
                    session_id=sid,
                    owner_id=uid,
                    idempotency_key=f"tfl_{uuid.uuid4().hex}",
                    target=2920.5,
                    confirmed_at=NOW,
                )


# ===================================================================
# Shared validation
# ===================================================================


class TestInvalidState:
    async def test_stop_not_opened(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        # Create a session that never reached OPEN_POSITION
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = TradeSessionService(s)
            session = await svc.create_session(owner_id=user_id, ticker="BBRI")
            await s.commit()
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = StopLossActionService(s)
            with pytest.raises(StopLossInvalidStateError):
                await svc.confirm(
                    session_id=session.id,
                    owner_id=user_id,
                    idempotency_key=f"ns_{uuid.uuid4().hex}",
                    stop_loss=2700,
                    confirmed_at=NOW,
                )

    async def test_target_not_opened(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = TradeSessionService(s)
            session = await svc.create_session(owner_id=user_id, ticker="BBRI")
            await s.commit()
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = TargetActionService(s)
            with pytest.raises(TargetInvalidStateError):
                await svc.confirm(
                    session_id=session.id,
                    owner_id=user_id,
                    idempotency_key=f"nt_{uuid.uuid4().hex}",
                    target=2920,
                    confirmed_at=NOW,
                )


class TestOwnership:
    async def test_stop_wrong_owner(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = StopLossActionService(s)
            with pytest.raises(StopLossNotFoundError):
                await svc.confirm(
                    session_id=sid,
                    owner_id=uuid.uuid4(),
                    idempotency_key=f"wo_{uuid.uuid4().hex}",
                    stop_loss=2700,
                    confirmed_at=NOW,
                )

    async def test_target_wrong_owner(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = TargetActionService(s)
            with pytest.raises(TargetNotFoundError):
                await svc.confirm(
                    session_id=sid,
                    owner_id=uuid.uuid4(),
                    idempotency_key=f"two_{uuid.uuid4().hex}",
                    target=2920,
                    confirmed_at=NOW,
                )


class TestIdempotency:
    async def test_stop_repeat_key_safe(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        ik = f"ir_{uuid.uuid4().hex}"
        async with factory() as s:
            svc = StopLossActionService(s)
            r1 = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=ik,
                stop_loss=2700,
                confirmed_at=NOW,
            )
            await s.commit()
        async with factory() as s:
            svc = StopLossActionService(s)
            r2 = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=ik,
                stop_loss=2700,
                confirmed_at=NOW,
            )
            assert r2.action.id == r1.action.id

    async def test_target_repeat_key_safe(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        ik = f"itr_{uuid.uuid4().hex}"
        async with factory() as s:
            svc = TargetActionService(s)
            r1 = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=ik,
                target=2920,
                confirmed_at=NOW,
            )
            await s.commit()
        async with factory() as s:
            svc = TargetActionService(s)
            r2 = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=ik,
                target=2920,
                confirmed_at=NOW,
            )
            assert r2.action.id == r1.action.id


class TestAtomicRollback:
    async def test_stop_rollback(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            from app.models.trade_state import TradeState

            ts = await s.get(TradeState, sid)
            orig_stop = ts.active_stop_loss

            svc = StopLossActionService(s)
            async with s.begin_nested():
                try:
                    r = await svc.confirm(
                        session_id=sid,
                        owner_id=uid,
                        idempotency_key=f"rb_{uuid.uuid4().hex}",
                        stop_loss=2700,
                        confirmed_at=NOW,
                    )
                    raise RuntimeError("Simulated failure")
                except RuntimeError:
                    pass
                await s.rollback()
            await s.refresh(ts)
            assert ts.active_stop_loss == orig_stop
