"""Tests for Full Exit Action Service (TP-0506)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models.enums import (
    ActionType,
    PositionStatus,
    TradeSessionStatus,
)
from app.services.actions.full_exit import (
    FullExitActionService,
    FullExitInvalidInputError,
    FullExitInvalidReasonError,
    FullExitNotFoundError,
    FullExitQuantityMismatchError,
)
from app.services.actions.open_position import OpenPositionService
from app.services.actions.partial_exit import PartialExitActionService
from app.services.trade_session import TradeSessionService

pytestmark = pytest.mark.database

NOW = datetime(2026, 7, 18, 10, 12, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 7, 18, 15, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
async def user_id(engine: AsyncEngine) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
            {"e": f"fe_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
        )
        return r.first()[0]


async def _open_session(
    engine: AsyncEngine,
    uid: uuid.UUID,
    entry: int = 2800,
    qty: int = 100,
) -> tuple[uuid.UUID, uuid.UUID]:
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
            entry_price=entry,
            quantity=qty,
            execution_timestamp=NOW,
        )
        await s.commit()
    return session.id, uid


async def _partial_session(
    engine: AsyncEngine,
    uid: uuid.UUID,
) -> tuple[uuid.UUID, uuid.UUID]:
    sid, uid2 = await _open_session(engine, uid)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        px = PartialExitActionService(s)
        await px.confirm(
            session_id=sid,
            owner_id=uid2,
            idempotency_key=f"part_{uuid.uuid4().hex}",
            exit_price=2920,
            exit_quantity=40,
            executed_at=NOW,
        )
        await s.commit()
    return sid, uid2


# ===================================================================


class TestFullExitFromOpen:
    async def test_closes_position(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = FullExitActionService(s)
            result = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"fe_{uuid.uuid4().hex}",
                exit_price=2910,
                exit_quantity=100,
                executed_at=LATER,
                closing_reason="TAKE_PROFIT",
            )
            assert result.weighted_exit_price == 2910
            assert result.gross_pnl == 11000  # (2910-2800)*100
            assert result.net_pnl == 11000

    async def test_remaining_zero(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = FullExitActionService(s)
            await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"rz_{uuid.uuid4().hex}",
                exit_price=2910,
                exit_quantity=100,
                executed_at=LATER,
                closing_reason="TAKE_PROFIT",
            )
            from app.models.trade_state import TradeState

            ts = await s.get(TradeState, sid)
            assert ts is not None
            assert ts.remaining_quantity == 0
            assert ts.position_status == PositionStatus.CLOSED
            assert ts.active_stop_loss is None
            assert ts.active_target is None

    async def test_terminal_status(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = FullExitActionService(s)
            await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"ts_{uuid.uuid4().hex}",
                exit_price=2910,
                exit_quantity=100,
                executed_at=LATER,
                closing_reason="STOP_LOSS",
            )
            from app.models.trade_session import TradeSession

            sess = await s.get(TradeSession, sid)
            assert sess is not None
            assert sess.lifecycle_status == TradeSessionStatus.CLOSED_STOP_LOSS

    async def test_action_persisted(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        ik = f"ap_{uuid.uuid4().hex}"
        async with factory() as s:
            svc = FullExitActionService(s)
            await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=ik,
                exit_price=2910,
                exit_quantity=100,
                executed_at=LATER,
                closing_reason="MANUAL_EXIT",
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
            assert act.action_type == ActionType.FULL_EXIT
            assert act.price == 2910


class TestFullExitAfterPartial:
    async def test_cumulative_result(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _partial_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = FullExitActionService(s)
            result = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"cr_{uuid.uuid4().hex}",
                exit_price=2900,
                exit_quantity=60,
                executed_at=LATER,
                closing_reason="TAKE_PROFIT",
            )
            # Partial: 40@2920 → P&L=4800. Final: 60@2900 → P&L=6000. Total=10800
            assert result.gross_pnl == 10800

    async def test_weighted_average(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        """40@2920 + 60@2900 = (116800+174000)/100 = 290800/100 = 2908."""
        sid, uid = await _partial_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = FullExitActionService(s)
            result = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"wa_{uuid.uuid4().hex}",
                exit_price=2900,
                exit_quantity=60,
                executed_at=LATER,
                closing_reason="TAKE_PROFIT",
            )
            from decimal import Decimal

            expected = Decimal("290800") / Decimal("100")
            assert result.weighted_exit_price is not None
            assert abs(expected - result.weighted_exit_price) < Decimal("0.001")


class TestClosingReasons:
    @pytest.mark.parametrize(
        "reason,expected_status",
        [
            ("TAKE_PROFIT", TradeSessionStatus.CLOSED_TAKE_PROFIT),
            ("STOP_LOSS", TradeSessionStatus.CLOSED_STOP_LOSS),
            ("MANUAL_EXIT", TradeSessionStatus.CLOSED_MANUAL),
        ],
    )
    async def test_mapping(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        reason: str,
        expected_status: TradeSessionStatus,
    ) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = FullExitActionService(s)
            await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"cr_{reason}_{uuid.uuid4().hex}",
                exit_price=2910,
                exit_quantity=100,
                executed_at=LATER,
                closing_reason=reason,
            )
            from app.models.trade_session import TradeSession

            sess = await s.get(TradeSession, sid)
            assert sess is not None
            assert sess.lifecycle_status == expected_status


class TestQuantityValidation:
    async def test_below_remaining_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = FullExitActionService(s)
            with pytest.raises(FullExitQuantityMismatchError):
                await svc.confirm(
                    session_id=sid,
                    owner_id=uid,
                    idempotency_key=f"bq_{uuid.uuid4().hex}",
                    exit_price=2910,
                    exit_quantity=50,
                    executed_at=LATER,
                    closing_reason="TAKE_PROFIT",
                )

    async def test_above_remaining_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = FullExitActionService(s)
            with pytest.raises(FullExitQuantityMismatchError):
                await svc.confirm(
                    session_id=sid,
                    owner_id=uid,
                    idempotency_key=f"aq_{uuid.uuid4().hex}",
                    exit_price=2910,
                    exit_quantity=150,
                    executed_at=LATER,
                    closing_reason="TAKE_PROFIT",
                )

    async def test_float_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = FullExitActionService(s)
            with pytest.raises(FullExitInvalidInputError):
                await svc.confirm(
                    session_id=sid,
                    owner_id=uid,
                    idempotency_key=f"fq_{uuid.uuid4().hex}",
                    exit_price=2910,
                    exit_quantity=100.5,
                    executed_at=LATER,
                    closing_reason="TAKE_PROFIT",
                )


class TestReasonValidation:
    async def test_invalid_reason_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = FullExitActionService(s)
            with pytest.raises(FullExitInvalidReasonError):
                await svc.confirm(
                    session_id=sid,
                    owner_id=uid,
                    idempotency_key=f"ir_{uuid.uuid4().hex}",
                    exit_price=2910,
                    exit_quantity=100,
                    executed_at=LATER,
                    closing_reason="UNKNOWN_REASON",
                )


class TestTimeline:
    async def test_exit_before_entry_rejected(
        self, engine: AsyncEngine, user_id: uuid.UUID
    ) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        ts_before_entry = datetime(2026, 7, 15, 8, 0, 0, tzinfo=timezone.utc)
        async with factory() as s:
            svc = FullExitActionService(s)
            with pytest.raises(Exception):
                await svc.confirm(
                    session_id=sid,
                    owner_id=uid,
                    idempotency_key=f"tb_{uuid.uuid4().hex}",
                    exit_price=2910,
                    exit_quantity=100,
                    executed_at=ts_before_entry,
                    closing_reason="TAKE_PROFIT",
                )


class TestOwnership:
    async def test_wrong_owner_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = FullExitActionService(s)
            with pytest.raises(FullExitNotFoundError):
                await svc.confirm(
                    session_id=sid,
                    owner_id=uuid.uuid4(),
                    idempotency_key=f"wo_{uuid.uuid4().hex}",
                    exit_price=2910,
                    exit_quantity=100,
                    executed_at=LATER,
                    closing_reason="TAKE_PROFIT",
                )


class TestIdempotency:
    async def test_repeat_key_safe(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        ik = f"ir_{uuid.uuid4().hex}"
        async with factory() as s:
            svc = FullExitActionService(s)
            r1 = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=ik,
                exit_price=2910,
                exit_quantity=100,
                executed_at=LATER,
                closing_reason="TAKE_PROFIT",
            )
            await s.commit()
        async with factory() as s:
            svc = FullExitActionService(s)
            r2 = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=ik,
                exit_price=2910,
                exit_quantity=100,
                executed_at=LATER,
                closing_reason="TAKE_PROFIT",
            )
            assert r2.action.id == r1.action.id


class TestAtomicRollback:
    async def test_rollback(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            from app.models.trade_state import TradeState

            ts = await s.get(TradeState, sid)
            assert ts is not None
            orig_rem = ts.remaining_quantity
            orig_status = ts.position_status
            svc = FullExitActionService(s)
            async with s.begin_nested():
                try:
                    await svc.confirm(
                        session_id=sid,
                        owner_id=uid,
                        idempotency_key=f"rb_{uuid.uuid4().hex}",
                        exit_price=2910,
                        exit_quantity=100,
                        executed_at=LATER,
                        closing_reason="TAKE_PROFIT",
                    )
                    raise RuntimeError("Simulated failure")
                except RuntimeError:
                    pass
                await s.rollback()
            await s.refresh(ts)
            assert ts.remaining_quantity == orig_rem
            assert ts.position_status == orig_status
