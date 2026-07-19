"""Tests for Cancel and Archive Action Services (TP-0507)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models.enums import ActionType, ContextQuality, TradeSessionStatus
from app.services.actions.archive_session import (
    ArchiveSessionActionService,
    ArchiveSessionInvalidStateError,
    ArchiveSessionNotFoundError,
)
from app.services.actions.cancel_session import (
    CancelSessionActionService,
    CancelSessionInvalidStateError,
    CancelSessionNotFoundError,
)
from app.services.trade_session import TradeSessionService

pytestmark = pytest.mark.database

NOW = datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
async def user_id(engine: AsyncEngine) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
            {"e": f"ca_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
        )
        return r.first()[0]


async def _draft_session(engine: AsyncEngine, uid: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        svc = TradeSessionService(s)
        session = await svc.create_session(owner_id=uid, ticker="BBRI")
        await s.commit()
    return session.id, uid


async def _session_with_status(
    engine: AsyncEngine,
    uid: uuid.UUID,
    status: TradeSessionStatus,
) -> tuple[uuid.UUID, uuid.UUID]:
    sid, uid2 = await _draft_session(engine, uid)
    if status == TradeSessionStatus.DRAFT:
        return sid, uid2
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        await s.execute(
            text(
                "UPDATE trade_sessions SET lifecycle_status = :st, "
                "stable_status = :st WHERE id = :sid"
            ),
            {"st": status.value, "sid": sid},
        )
        await s.commit()
    return sid, uid2


# ===================================================================
# Cancellation
# ===================================================================


class TestCancelSuccess:
    async def test_draft_cancelled(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _draft_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = CancelSessionActionService(s)
            result = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"cd_{uuid.uuid4().hex}",
                cancelled_at=NOW,
                reason="Changed mind",
            )
            assert result.session_status == TradeSessionStatus.CANCELLED
            from app.models.trade_session import TradeSession

            ts = await s.get(TradeSession, sid)
            assert ts is not None
            assert ts.lifecycle_status == TradeSessionStatus.CANCELLED
            assert ts.stable_status == TradeSessionStatus.CANCELLED

    async def test_action_persisted(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _draft_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        ik = f"cap_{uuid.uuid4().hex}"
        async with factory() as s:
            svc = CancelSessionActionService(s)
            await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=ik,
                cancelled_at=NOW,
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
            assert act.action_type == ActionType.SESSION_CANCELLED

    async def test_context_summary_stale(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _draft_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            from app.models.context_summary import ContextSummary

            cs = ContextSummary(
                session_id=sid, context_version=1, is_stale=False, quality=ContextQuality.HIGH
            )
            s.add(cs)
            await s.flush()
            svc = CancelSessionActionService(s)
            await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"ccs_{uuid.uuid4().hex}",
                cancelled_at=NOW,
            )
            await s.refresh(cs)
            assert cs.is_stale is True


class TestCancelRejection:
    async def test_open_position_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _session_with_status(engine, user_id, TradeSessionStatus.OPEN_POSITION)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = CancelSessionActionService(s)
            with pytest.raises(CancelSessionInvalidStateError):
                await svc.confirm(
                    session_id=sid,
                    owner_id=uid,
                    idempotency_key=f"cop_{uuid.uuid4().hex}",
                    cancelled_at=NOW,
                )

    async def test_closed_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _session_with_status(
            engine, user_id, TradeSessionStatus.CLOSED_TAKE_PROFIT
        )
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = CancelSessionActionService(s)
            with pytest.raises(CancelSessionInvalidStateError):
                await svc.confirm(
                    session_id=sid,
                    owner_id=uid,
                    idempotency_key=f"ccl_{uuid.uuid4().hex}",
                    cancelled_at=NOW,
                )

    async def test_wrong_owner_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _draft_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = CancelSessionActionService(s)
            with pytest.raises(CancelSessionNotFoundError):
                await svc.confirm(
                    session_id=sid,
                    owner_id=uuid.uuid4(),
                    idempotency_key=f"cwo_{uuid.uuid4().hex}",
                    cancelled_at=NOW,
                )


class TestCancelIdempotency:
    async def test_repeat_key_safe(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _draft_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        ik = f"cir_{uuid.uuid4().hex}"
        async with factory() as s:
            svc = CancelSessionActionService(s)
            r1 = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=ik,
                cancelled_at=NOW,
            )
            await s.commit()
        async with factory() as s:
            svc = CancelSessionActionService(s)
            r2 = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=ik,
                cancelled_at=NOW,
            )
            assert r2.action.id == r1.action.id


class TestCancelRollback:
    async def test_rollback(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _draft_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            from app.models.trade_session import TradeSession

            ts = await s.get(TradeSession, sid)
            assert ts is not None
            orig_status = ts.lifecycle_status
            svc = CancelSessionActionService(s)
            async with s.begin_nested():
                try:
                    await svc.confirm(
                        session_id=sid,
                        owner_id=uid,
                        idempotency_key=f"crb_{uuid.uuid4().hex}",
                        cancelled_at=NOW,
                    )
                    raise RuntimeError("Simulated failure")
                except RuntimeError:
                    pass
                await s.rollback()
            await s.refresh(ts)
            assert ts.lifecycle_status == orig_status


# ===================================================================
# Archive
# ===================================================================


class TestArchiveSuccess:
    @pytest.mark.parametrize(
        "status",
        [
            TradeSessionStatus.CANCELLED,
            TradeSessionStatus.CLOSED_TAKE_PROFIT,
            TradeSessionStatus.CLOSED_STOP_LOSS,
            TradeSessionStatus.CLOSED_MANUAL,
        ],
    )
    async def test_archive_eligible(
        self, engine: AsyncEngine, user_id: uuid.UUID, status: TradeSessionStatus
    ) -> None:
        sid, uid = await _session_with_status(engine, user_id, status)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = ArchiveSessionActionService(s)
            result = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=f"ae_{status.value}_{uuid.uuid4().hex}",
                archived_at=NOW,
            )
            assert result.session_status == TradeSessionStatus.ARCHIVED
            from app.models.trade_session import TradeSession

            ts = await s.get(TradeSession, sid)
            assert ts is not None
            assert ts.lifecycle_status == TradeSessionStatus.ARCHIVED
            assert ts.stable_status == TradeSessionStatus.ARCHIVED

    async def test_action_persisted(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _session_with_status(engine, user_id, TradeSessionStatus.CANCELLED)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        ik = f"aap_{uuid.uuid4().hex}"
        async with factory() as s:
            svc = ArchiveSessionActionService(s)
            await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=ik,
                archived_at=NOW,
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
            assert act.action_type == ActionType.SESSION_ARCHIVED


class TestArchiveRejection:
    @pytest.mark.parametrize(
        "status",
        [
            TradeSessionStatus.DRAFT,
            TradeSessionStatus.WATCHING,
            TradeSessionStatus.OPEN_POSITION,
            TradeSessionStatus.PARTIALLY_CLOSED,
        ],
    )
    async def test_active_rejected(
        self, engine: AsyncEngine, user_id: uuid.UUID, status: TradeSessionStatus
    ) -> None:
        sid, uid = await _session_with_status(engine, user_id, status)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = ArchiveSessionActionService(s)
            with pytest.raises(ArchiveSessionInvalidStateError):
                await svc.confirm(
                    session_id=sid,
                    owner_id=uid,
                    idempotency_key=f"ar_{status.value}_{uuid.uuid4().hex}",
                    archived_at=NOW,
                )

    async def test_wrong_owner_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _session_with_status(
            engine, user_id, TradeSessionStatus.CLOSED_TAKE_PROFIT
        )
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = ArchiveSessionActionService(s)
            with pytest.raises(ArchiveSessionNotFoundError):
                await svc.confirm(
                    session_id=sid,
                    owner_id=uuid.uuid4(),
                    idempotency_key=f"awo_{uuid.uuid4().hex}",
                    archived_at=NOW,
                )


class TestArchiveIdempotency:
    async def test_repeat_key_safe(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _session_with_status(
            engine, user_id, TradeSessionStatus.CLOSED_TAKE_PROFIT
        )
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        ik = f"air_{uuid.uuid4().hex}"
        async with factory() as s:
            svc = ArchiveSessionActionService(s)
            r1 = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=ik,
                archived_at=NOW,
            )
            await s.commit()
        async with factory() as s:
            svc = ArchiveSessionActionService(s)
            r2 = await svc.confirm(
                session_id=sid,
                owner_id=uid,
                idempotency_key=ik,
                archived_at=NOW,
            )
            assert r2.action.id == r1.action.id


class TestArchiveRollback:
    async def test_rollback(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _session_with_status(
            engine, user_id, TradeSessionStatus.CLOSED_TAKE_PROFIT
        )
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            from app.models.trade_session import TradeSession

            ts = await s.get(TradeSession, sid)
            assert ts is not None
            orig_status = ts.lifecycle_status
            svc = ArchiveSessionActionService(s)
            async with s.begin_nested():
                try:
                    await svc.confirm(
                        session_id=sid,
                        owner_id=uid,
                        idempotency_key=f"arb_{uuid.uuid4().hex}",
                        archived_at=NOW,
                    )
                    raise RuntimeError("Simulated failure")
                except RuntimeError:
                    pass
                await s.rollback()
            await s.refresh(ts)
            assert ts.lifecycle_status == orig_status
