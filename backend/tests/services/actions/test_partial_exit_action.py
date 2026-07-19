"""Tests for Partial Exit Action Service (TP-0505)."""

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
from app.services.actions.partial_exit import (
    PartialExitActionService,
    PartialExitInvalidInputError,
    PartialExitInvalidStateError,
    PartialExitNotFoundError,
    PartialExitQuantityInvalidError,
)
from app.services.trade_session import TradeSessionService
from app.services.actions.open_position import OpenPositionService

pytestmark = pytest.mark.database

NOW = datetime(2026, 7, 18, 10, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
async def user_id(engine: AsyncEngine) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
            {"e": f"pe_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
        )
        return r.first()[0]


async def _open_session(engine: AsyncEngine, uid: uuid.UUID, entry: int = 2800, qty: int = 100) -> tuple[uuid.UUID, uuid.UUID]:
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        svc = TradeSessionService(s)
        session = await svc.create_session(owner_id=uid, ticker="BBRI")
        from app.lifecycle.service import SessionLifecycleService

        lc = SessionLifecycleService(s)
        await lc.transition(session_id=session.id, owner_id=uid, target_status=TradeSessionStatus.READY_FOR_ANALYSIS)
        await lc.transition(session_id=session.id, owner_id=uid, target_status=TradeSessionStatus.ANALYZING)
        await lc.transition(session_id=session.id, owner_id=uid, target_status=TradeSessionStatus.WATCHING)
        await s.commit()

    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        op = OpenPositionService(s)
        await op.confirm(
            session_id=session.id, owner_id=uid,
            idempotency_key=f"open_{uuid.uuid4().hex}",
            entry_price=entry, quantity=qty, execution_timestamp=NOW,
        )
        await s.commit()
    return session.id, uid


# ===================================================================


class TestFirstPartialExit:
    async def test_successful(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = PartialExitActionService(s)
            result = await svc.confirm(
                session_id=sid, owner_id=uid,
                idempotency_key=f"pe1_{uuid.uuid4().hex}",
                exit_price=2920, exit_quantity=40, executed_at=NOW,
            )
            assert result.remaining_quantity == 60
            assert result.realized_pnl is not None
            # realized = (2920-2800)*40 = 4800
            assert result.realized_pnl == 4800

    async def test_action_persisted(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        ik = f"ap_{uuid.uuid4().hex}"
        async with factory() as s:
            svc = PartialExitActionService(s)
            await svc.confirm(
                session_id=sid, owner_id=uid, idempotency_key=ik,
                exit_price=2920, exit_quantity=40, executed_at=NOW,
            )
            await s.commit()
        async with factory() as s:
            from app.models.trade_action import TradeAction
            from sqlalchemy import select
            act = (await s.execute(
                select(TradeAction).where(TradeAction.idempotency_key == ik)
            )).unique().scalar_one_or_none()
            assert act is not None
            assert act.action_type == ActionType.PARTIAL_EXIT
            assert act.price == 2920
            assert act.quantity == 40

    async def test_event_persisted(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = PartialExitActionService(s)
            await svc.confirm(
                session_id=sid, owner_id=uid,
                idempotency_key=f"ev_{uuid.uuid4().hex}",
                exit_price=2920, exit_quantity=40, executed_at=NOW,
            )
            await s.commit()
        async with factory() as s:
            cnt = (await s.execute(
                text("SELECT COUNT(*) FROM session_events WHERE session_id = :sid AND event_type = 'PARTIAL_EXIT'"),
                {"sid": sid},
            )).scalar_one()
            assert cnt == 1

    async def test_remaining_quantity(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = PartialExitActionService(s)
            result = await svc.confirm(
                session_id=sid, owner_id=uid,
                idempotency_key=f"rq_{uuid.uuid4().hex}",
                exit_price=2920, exit_quantity=40, executed_at=NOW,
            )
            assert result.remaining_quantity == 60
            from app.models.trade_state import TradeState
            ts = await s.get(TradeState, sid)
            assert ts.remaining_quantity == 60
            assert ts.position_status == PositionStatus.PARTIALLY_CLOSED

    async def test_context_summary_stale(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            from app.models.context_summary import ContextSummary
            cs = ContextSummary(session_id=sid, context_version=1, is_stale=False, quality=ContextQuality.HIGH)
            s.add(cs)
            await s.flush()
            svc = PartialExitActionService(s)
            await svc.confirm(
                session_id=sid, owner_id=uid,
                idempotency_key=f"cs_{uuid.uuid4().hex}",
                exit_price=2920, exit_quantity=40, executed_at=NOW,
            )
            await s.refresh(cs)
            assert cs.is_stale is True


class TestRepeatedPartialExit:
    async def test_second_exit(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = PartialExitActionService(s)
            r1 = await svc.confirm(
                session_id=sid, owner_id=uid,
                idempotency_key=f"pe_{uuid.uuid4().hex}",
                exit_price=2920, exit_quantity=40, executed_at=NOW,
            )
            assert r1.remaining_quantity == 60
            await s.commit()
        async with factory() as s:
            svc = PartialExitActionService(s)
            r2 = await svc.confirm(
                session_id=sid, owner_id=uid,
                idempotency_key=f"pe_{uuid.uuid4().hex}",
                exit_price=2900, exit_quantity=30, executed_at=NOW,
            )
            assert r2.remaining_quantity == 30  # 60 - 30
            # Cumulative realized: first: (2920-2800)*40=4800, second: (2900-2800)*30=3000, total=7800
            assert r2.realized_pnl == 7800

    async def test_weighted_average(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        """40@2920 then 30@2900 → weighted = (40*2920+30*2900)/(70) = 203800/70."""
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            from app.calculations.exits import ExitFill, calculate_weighted_average_exit
            expected = calculate_weighted_average_exit((
                ExitFill(2920, 40), ExitFill(2900, 30),
            ))
            svc = PartialExitActionService(s)
            await svc.confirm(
                session_id=sid, owner_id=uid,
                idempotency_key=f"wa_{uuid.uuid4().hex}",
                exit_price=2920, exit_quantity=40, executed_at=NOW,
            )
            await s.commit()
        async with factory() as s:
            svc = PartialExitActionService(s)
            r2 = await svc.confirm(
                session_id=sid, owner_id=uid,
                idempotency_key=f"wa_{uuid.uuid4().hex}",
                exit_price=2900, exit_quantity=30, executed_at=NOW,
            )
            if expected is not None:
                from decimal import Decimal
                diff = abs(expected - r2.average_exit_price)
                assert diff < Decimal("0.00001"), f"Expected ~{expected}, got {r2.average_exit_price}"


class TestQuantityBoundaries:
    async def test_full_remaining_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = PartialExitActionService(s)
            with pytest.raises(PartialExitQuantityInvalidError):
                await svc.confirm(
                    session_id=sid, owner_id=uid,
                    idempotency_key=f"fr_{uuid.uuid4().hex}",
                    exit_price=2920, exit_quantity=100, executed_at=NOW,
                )

    async def test_excessive_quantity_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = PartialExitActionService(s)
            with pytest.raises(PartialExitQuantityInvalidError):
                await svc.confirm(
                    session_id=sid, owner_id=uid,
                    idempotency_key=f"eq_{uuid.uuid4().hex}",
                    exit_price=2920, exit_quantity=200, executed_at=NOW,
                )

    async def test_zero_quantity_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = PartialExitActionService(s)
            with pytest.raises(PartialExitInvalidInputError):
                await svc.confirm(
                    session_id=sid, owner_id=uid,
                    idempotency_key=f"zq_{uuid.uuid4().hex}",
                    exit_price=2920, exit_quantity=0, executed_at=NOW,
                )

    async def test_float_quantity_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = PartialExitActionService(s)
            with pytest.raises(PartialExitInvalidInputError):
                await svc.confirm(
                    session_id=sid, owner_id=uid,
                    idempotency_key=f"fq_{uuid.uuid4().hex}",
                    exit_price=2920, exit_quantity=40.5, executed_at=NOW,
                )


class TestExitPriceValidation:
    async def test_float_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = PartialExitActionService(s)
            with pytest.raises(PartialExitInvalidInputError):
                await svc.confirm(
                    session_id=sid, owner_id=uid,
                    idempotency_key=f"fp_{uuid.uuid4().hex}",
                    exit_price=2920.5, exit_quantity=40, executed_at=NOW,
                )


class TestOwnership:
    async def test_wrong_owner_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = PartialExitActionService(s)
            with pytest.raises(PartialExitNotFoundError):
                await svc.confirm(
                    session_id=sid, owner_id=uuid.uuid4(),
                    idempotency_key=f"wo_{uuid.uuid4().hex}",
                    exit_price=2920, exit_quantity=40, executed_at=NOW,
                )


class TestIdempotency:
    async def test_repeat_key_safe(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        ik = f"ir_{uuid.uuid4().hex}"
        async with factory() as s:
            svc = PartialExitActionService(s)
            r1 = await svc.confirm(
                session_id=sid, owner_id=uid, idempotency_key=ik,
                exit_price=2920, exit_quantity=40, executed_at=NOW,
            )
            await s.commit()
        async with factory() as s:
            svc = PartialExitActionService(s)
            r2 = await svc.confirm(
                session_id=sid, owner_id=uid, idempotency_key=ik,
                exit_price=2920, exit_quantity=40, executed_at=NOW,
            )
            assert r2.action.id == r1.action.id
            assert r2.remaining_quantity == 60


class TestAtomicRollback:
    async def test_rollback(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _open_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            from app.models.trade_state import TradeState
            ts = await s.get(TradeState, sid)
            orig_rem = ts.remaining_quantity
            svc = PartialExitActionService(s)
            async with s.begin_nested():
                try:
                    await svc.confirm(
                        session_id=sid, owner_id=uid,
                        idempotency_key=f"rb_{uuid.uuid4().hex}",
                        exit_price=2920, exit_quantity=40, executed_at=NOW,
                    )
                    raise RuntimeError("Simulated failure")
                except RuntimeError:
                    pass
                await s.rollback()
            await s.refresh(ts)
            assert ts.remaining_quantity == orig_rem
