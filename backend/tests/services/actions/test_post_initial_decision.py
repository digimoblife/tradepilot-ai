from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models.enums import ActionType, PositionStatus, TradeSessionStatus
from app.models.trade_state import TradeState
from app.services.actions.post_initial_decision import (
    PostInitialDecisionInvalidStateError,
    PostInitialDecisionService,
)

pytestmark = pytest.mark.database

NOW = datetime(2026, 7, 27, 9, 0, tzinfo=timezone.utc)


@pytest.fixture
async def user_id(engine: AsyncEngine) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
            {"e": f"decision_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
        )
        return r.first()[0]


@pytest.fixture
def factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def _make_session(
    engine: AsyncEngine,
    owner_id: uuid.UUID,
    status: str,
) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                "INSERT INTO trade_sessions "
                "(owner_id, ticker, lifecycle_status, stable_status) "
                "VALUES (:oid, 'BBRI', :status, :status) RETURNING id"
            ),
            {"oid": owner_id, "status": status},
        )
        sid = r.first()[0]
        await conn.execute(
            text(
                "INSERT INTO trade_states (session_id, position_status, thesis_status) "
                "VALUES (:sid, 'NOT_OPENED', 'INTACT')"
            ),
            {"sid": sid},
        )
        return sid


class TestWaitDecision:
    async def test_initial_analyzed_to_watching(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, "INITIAL_ANALYZED")
        async with factory() as s:
            result = await PostInitialDecisionService(s).wait(
                session_id=sid,
                owner_id=user_id,
                idempotency_key=f"wait_{uuid.uuid4().hex}",
                confirmed_at=NOW,
            )
            assert result.session_status == TradeSessionStatus.WATCHING
            assert result.action.action_type == ActionType.USER_WAITED

    async def test_watching_to_watching_is_auditable(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, "WATCHING")
        async with factory() as s:
            await PostInitialDecisionService(s).wait(
                session_id=sid,
                owner_id=user_id,
                idempotency_key=f"wait1_{uuid.uuid4().hex}",
                confirmed_at=NOW,
            )
            await PostInitialDecisionService(s).wait(
                session_id=sid,
                owner_id=user_id,
                idempotency_key=f"wait2_{uuid.uuid4().hex}",
                confirmed_at=NOW,
            )
            count = (
                await s.execute(
                    text(
                        "SELECT COUNT(*) FROM trade_actions "
                        "WHERE session_id = :sid AND action_type = 'USER_WAITED'"
                    ),
                    {"sid": sid},
                )
            ).scalar_one()
            state = await s.get(TradeState, sid)
            assert count == 2
            assert state.position_status == PositionStatus.NOT_OPENED


class TestSkipDecision:
    async def test_initial_analyzed_to_closed_skipped(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, "INITIAL_ANALYZED")
        async with factory() as s:
            result = await PostInitialDecisionService(s).skip(
                session_id=sid,
                owner_id=user_id,
                idempotency_key=f"skip_{uuid.uuid4().hex}",
                confirmed_at=NOW,
                reason="USER_SKIPPED_SETUP",
            )
            assert result.session_status == TradeSessionStatus.CLOSED_SKIPPED
            assert result.action.action_type == ActionType.SESSION_SKIPPED
            assert result.action.payload["reason"] == "USER_SKIPPED_SETUP"

            row = (
                await s.execute(
                    text(
                        "SELECT lifecycle_status FROM trade_sessions WHERE id = :sid"
                    ),
                    {"sid": sid},
                )
            ).first()
            state = await s.get(TradeState, sid)
            assert row[0] == "CLOSED_SKIPPED"
            assert state.position_status == PositionStatus.NOT_OPENED
            assert state.entry_price is None

    async def test_watching_to_closed_skipped(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, "WATCHING")
        async with factory() as s:
            result = await PostInitialDecisionService(s).skip(
                session_id=sid,
                owner_id=user_id,
                idempotency_key=f"skip_{uuid.uuid4().hex}",
                confirmed_at=NOW,
            )
            assert result.session_status == TradeSessionStatus.CLOSED_SKIPPED

    async def test_invalid_source_rejected(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, "DRAFT")
        async with factory() as s:
            with pytest.raises(PostInitialDecisionInvalidStateError):
                await PostInitialDecisionService(s).skip(
                    session_id=sid,
                    owner_id=user_id,
                    idempotency_key=f"skip_{uuid.uuid4().hex}",
                    confirmed_at=NOW,
                )
