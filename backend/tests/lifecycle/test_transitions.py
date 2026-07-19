"""Tests for Session Lifecycle Service (TP-0502)."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.lifecycle.service import (
    InvalidSessionTransitionError,
    SessionLifecycleService,
)
from app.lifecycle.transitions import is_transition_allowed
from app.models.enums import TradeSessionStatus
from app.repositories.trade_session import TradeSessionRepository
from app.services.trade_session import TradeSessionService

pytestmark = pytest.mark.database


@pytest.fixture
async def user_id(engine: AsyncEngine) -> uuid.UUID:
    async with engine.begin() as conn:
        result = await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
            {"e": f"lifecycle_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
        )
        return result.first()[0]


@pytest.fixture
async def ctx(engine: AsyncEngine, user_id: uuid.UUID) -> tuple[AsyncSession, uuid.UUID]:
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s, user_id


async def _make_session(
    engine: AsyncEngine, owner_id: uuid.UUID, status: TradeSessionStatus = TradeSessionStatus.DRAFT,
) -> tuple[TradeSessionService, AsyncSession, uuid.UUID, uuid.UUID]:
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        svc = TradeSessionService(s)
        session = await svc.create_session(owner_id=owner_id, ticker="BBRI")
        # Update to desired status via direct SQL for speed
        if status != TradeSessionStatus.DRAFT:
            await s.execute(
                text("UPDATE trade_sessions SET lifecycle_status = :st, stable_status = :st WHERE id = :sid"),
                {"st": status.value, "sid": session.id},
            )
            await s.flush()
        await s.commit()
    return session.id, owner_id


# ===================================================================


class TestTransitionRegistry:
    def test_draft_to_ready(self) -> None:
        assert is_transition_allowed(TradeSessionStatus.DRAFT, TradeSessionStatus.READY_FOR_ANALYSIS)

    def test_draft_to_archived(self) -> None:
        assert is_transition_allowed(TradeSessionStatus.DRAFT, TradeSessionStatus.ARCHIVED)

    def test_draft_to_open_invalid(self) -> None:
        assert not is_transition_allowed(TradeSessionStatus.DRAFT, TradeSessionStatus.OPEN_POSITION)

    def test_closed_to_draft_invalid(self) -> None:
        assert not is_transition_allowed(TradeSessionStatus.CLOSED_TAKE_PROFIT, TradeSessionStatus.DRAFT)

    def test_closed_to_watching_invalid(self) -> None:
        assert not is_transition_allowed(TradeSessionStatus.CLOSED_STOP_LOSS, TradeSessionStatus.WATCHING)

    def test_archived_to_draft_invalid(self) -> None:
        assert not is_transition_allowed(TradeSessionStatus.ARCHIVED, TradeSessionStatus.DRAFT)

    def test_analyzing_to_stable_allowed(self) -> None:
        assert is_transition_allowed(TradeSessionStatus.ANALYZING, TradeSessionStatus.WATCHING)
        assert is_transition_allowed(TradeSessionStatus.ANALYZING, TradeSessionStatus.OPEN_POSITION)

    def test_analyzing_to_analyzing_allowed(self) -> None:
        assert is_transition_allowed(TradeSessionStatus.ANALYZING, TradeSessionStatus.ANALYZING)

    def test_partial_to_partial_allowed(self) -> None:
        assert is_transition_allowed(TradeSessionStatus.PARTIALLY_CLOSED, TradeSessionStatus.PARTIALLY_CLOSED)

    def test_open_to_analyzing_allowed(self) -> None:
        assert is_transition_allowed(TradeSessionStatus.OPEN_POSITION, TradeSessionStatus.ANALYZING)


class TestLifecycleService:
    async def test_draft_to_ready(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _make_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = SessionLifecycleService(s)
            result = await svc.transition(
                session_id=sid, owner_id=uid, target_status=TradeSessionStatus.READY_FOR_ANALYSIS,
            )
            assert result.lifecycle_status == TradeSessionStatus.READY_FOR_ANALYSIS
            assert result.stable_status == TradeSessionStatus.READY_FOR_ANALYSIS

    async def test_invalid_transition_error(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _make_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = SessionLifecycleService(s)
            with pytest.raises(InvalidSessionTransitionError) as exc:
                await svc.transition(
                    session_id=sid, owner_id=uid, target_status=TradeSessionStatus.OPEN_POSITION,
                )
            assert exc.value.code == "SESSION_TRANSITION_INVALID"
            assert exc.value.current_status == TradeSessionStatus.DRAFT
            assert exc.value.target_status == TradeSessionStatus.OPEN_POSITION

    async def test_state_unchanged_after_invalid(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _make_session(engine, user_id)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = SessionLifecycleService(s)
            try:
                await svc.transition(
                    session_id=sid, owner_id=uid, target_status=TradeSessionStatus.OPEN_POSITION,
                )
            except InvalidSessionTransitionError:
                pass
            ts = await TradeSessionRepository(s).get_by_id_for_user(sid, uid)
            assert ts is not None
            assert ts.lifecycle_status == TradeSessionStatus.DRAFT


class TestClosedCannotReopen:
    async def test_closed_take_profit(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _make_session(engine, user_id, TradeSessionStatus.CLOSED_TAKE_PROFIT)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = SessionLifecycleService(s)
            for target in [TradeSessionStatus.DRAFT, TradeSessionStatus.WATCHING, TradeSessionStatus.OPEN_POSITION]:
                with pytest.raises(InvalidSessionTransitionError):
                    await svc.transition(session_id=sid, owner_id=uid, target_status=target)

    async def test_closed_stop_loss(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _make_session(engine, user_id, TradeSessionStatus.CLOSED_STOP_LOSS)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = SessionLifecycleService(s)
            with pytest.raises(InvalidSessionTransitionError):
                await svc.transition(
                    session_id=sid, owner_id=uid, target_status=TradeSessionStatus.DRAFT,
                )


class TestArchivedCannotReopen:
    async def test_archived(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _make_session(engine, user_id, TradeSessionStatus.ARCHIVED)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = SessionLifecycleService(s)
            with pytest.raises(InvalidSessionTransitionError):
                await svc.transition(
                    session_id=sid, owner_id=uid, target_status=TradeSessionStatus.DRAFT,
                )


class TestAnalyzing:
    async def test_enter_analyzing_preserves_stable(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _make_session(engine, user_id, TradeSessionStatus.WATCHING)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = SessionLifecycleService(s)
            result = await svc.transition(
                session_id=sid, owner_id=uid, target_status=TradeSessionStatus.ANALYZING,
            )
            assert result.lifecycle_status == TradeSessionStatus.ANALYZING
            assert result.stable_status == TradeSessionStatus.WATCHING  # preserved

    async def test_analyzing_from_open_position(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _make_session(engine, user_id, TradeSessionStatus.OPEN_POSITION)
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = SessionLifecycleService(s)
            result = await svc.transition(
                session_id=sid, owner_id=uid, target_status=TradeSessionStatus.ANALYZING,
            )
            assert result.lifecycle_status == TradeSessionStatus.ANALYZING
            assert result.stable_status == TradeSessionStatus.OPEN_POSITION


class TestOwnership:
    async def test_wrong_owner_rejected(self, engine: AsyncEngine, user_id: uuid.UUID) -> None:
        sid, uid = await _make_session(engine, user_id)
        wrong_uid = uuid.uuid4()
        factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as s:
            svc = SessionLifecycleService(s)
            with pytest.raises(InvalidSessionTransitionError):
                await svc.transition(
                    session_id=sid, owner_id=wrong_uid, target_status=TradeSessionStatus.READY_FOR_ANALYSIS,
                )
