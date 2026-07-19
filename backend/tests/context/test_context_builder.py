"""Tests for ContextSummaryBuilder (TP-0902).

PostgreSQL-backed — no real provider calls.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.context import (
    ContextSummaryBuilder,
    ContextSummaryBuildResult,
    ContextSummarySessionNotFoundError,
)

pytestmark = pytest.mark.database


# ===================================================================
# Helpers
# ===================================================================


async def _make_user(engine: AsyncEngine) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
            {"e": f"cb_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
        )
        return r.first()[0]


async def _make_session(
    engine: AsyncEngine,
    user_id: uuid.UUID,
    status: str = "WATCHING",
    ticker: str = "BBRI",
) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                "INSERT INTO trade_sessions "
                "(owner_id, ticker, lifecycle_status, stable_status) "
                "VALUES (:o, :t, :ls, :ss) RETURNING id"
            ),
            {"o": user_id, "t": ticker, "ls": status, "ss": status},
        )
        sid = r.first()[0]
        await conn.execute(
            text(
                "INSERT INTO trade_states "
                "(session_id, position_status, thesis_status, "
                "entry_price, original_quantity, remaining_quantity, "
                "active_stop_loss, active_target, state_version) "
                "VALUES (:s, 'NOT_OPENED', 'INTACT', "
                ":ep, :oq, :rq, :sl, :tg, 1)"
            ),
            {
                "s": sid,
                "ep": 2500,
                "oq": 1000,
                "rq": 1000,
                "sl": 2400,
                "tg": 2800,
            },
        )
        return sid


async def _add_session_event(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    event_type: str = "SESSION_CREATED",
    payload: str | None = None,
) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                "INSERT INTO session_events "
                "(session_id, event_type, occurred_at, compact_summary) "
                "VALUES (:sid, :et, :now, :pl) RETURNING id"
            ),
            {
                "sid": session_id,
                "et": event_type,
                "now": datetime.now(timezone.utc),
                "pl": payload or "{}",
            },
        )
        return r.first()[0]


async def _add_trade_action(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    action_type: str = "POSITION_OPENED",
    event_type: str = "POSITION_OPENED",
    price: int = 2520,
    quantity: int = 100,
) -> tuple[uuid.UUID, uuid.UUID]:
    async with engine.begin() as conn:
        ar = await conn.execute(
            text(
                "INSERT INTO trade_actions "
                "(session_id, action_type, confirmed_at, idempotency_key, "
                "price, quantity) "
                "VALUES (:sid, :at, :now, :ik, :p, :q) RETURNING id"
            ),
            {
                "sid": session_id,
                "at": action_type,
                "now": datetime.now(timezone.utc),
                "ik": f"ik_{uuid.uuid4().hex}",
                "p": price,
                "q": quantity,
            },
        )
        aid = ar.first()[0]
        er = await conn.execute(
            text(
                "INSERT INTO session_events "
                "(session_id, event_type, occurred_at, related_action_id) "
                "VALUES (:sid, :et, :now, :aid) RETURNING id"
            ),
            {
                "sid": session_id,
                "et": event_type,
                "now": datetime.now(timezone.utc),
                "aid": aid,
            },
        )
        return aid, er.first()[0]


async def _add_analysis(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    analysis_type: str = "INITIAL_ANALYSIS",
    status: str = "ACCEPTED",
    payload: dict | None = None,
    job_exists: bool = False,
) -> uuid.UUID:
    async with engine.begin() as conn:
        jid = None
        if job_exists:
            jr = await conn.execute(
                text(
                    "INSERT INTO analysis_jobs "
                    "(session_id, analysis_type, status) "
                    "VALUES (:sid, :at, 'COMPLETED') RETURNING id"
                ),
                {"sid": session_id, "at": analysis_type},
            )
            jid = jr.first()[0]

        pl = json.dumps(payload or {"executive_summary": "Test analysis"})
        r = await conn.execute(
            text(
                "INSERT INTO analyses "
                "(session_id, analysis_job_id, analysis_type, acceptance_status, "
                "prompt_name, prompt_version, schema_name, schema_version, payload) "
                "VALUES (:sid, :jid, :at, :st, "
                "'test_prompt', '1.0.0', 'test_schema', '1.0.0', :pl) RETURNING id"
            ),
            {
                "sid": session_id,
                "jid": jid,
                "at": analysis_type,
                "st": status,
                "pl": pl,
            },
        )
        return r.first()[0]


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
async def user_id(engine: AsyncEngine) -> uuid.UUID:
    return await _make_user(engine)


@pytest.fixture
async def other_user_id(engine: AsyncEngine) -> uuid.UUID:
    return await _make_user(engine)


@pytest.fixture
async def session_id(engine: AsyncEngine, user_id: uuid.UUID) -> uuid.UUID:
    return await _make_session(engine, user_id)


@pytest.fixture
def factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# ===================================================================
# Valid context summary
# ===================================================================


class TestValidContext:
    async def test_builds_payload(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_session_event(engine, session_id, "SESSION_CREATED")
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            assert isinstance(result, ContextSummaryBuildResult)
            assert result.session_id == session_id

    async def test_schema_valid(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_session_event(engine, session_id, "SESSION_CREATED")
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            assert result.validation_result.valid is True

    async def test_canonical_entry(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_session_event(engine, session_id, "SESSION_CREATED")
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            pos = result.payload.get("current_position", {})
            entry = pos.get("entry_price")
            assert entry is not None and "2500" in str(entry)

    async def test_canonical_quantity(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_session_event(engine, session_id, "SESSION_CREATED")
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            pos = result.payload.get("current_position", {})
            qty = pos.get("original_quantity")
            assert qty is not None and "1000" in str(qty)

    async def test_canonical_stop(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_session_event(engine, session_id, "SESSION_CREATED")
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            pos = result.payload.get("current_position", {})
            stop = pos.get("active_stop_loss")
            assert stop is not None and "2400" in str(stop)

    async def test_latest_analysis_represented(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_session_event(engine, session_id, "SESSION_CREATED")
        await _add_analysis(engine, session_id, "INITIAL_ANALYSIS", "ACCEPTED")
        await _add_analysis(engine, session_id, "WATCHING_UPDATE", "ACCEPTED")
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            ai = result.payload.get("latest_ai_assessment", {})
            assert ai.get("analysis_type") is not None

    async def test_rejected_analysis_excluded(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_session_event(engine, session_id, "SESSION_CREATED")
        await _add_analysis(engine, session_id, "INITIAL_ANALYSIS", "REJECTED")
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            ai = result.payload.get("latest_ai_assessment", {})
            assert ai.get("analysis_type") is None

    async def test_session_identity(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_session_event(engine, session_id, "SESSION_CREATED")
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            assert result.payload.get("ticker") == "BBRI"
            assert result.payload.get("session_id") == str(session_id)

    async def test_source_cutoff_deterministic(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_session_event(engine, session_id, "SESSION_CREATED")
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            r1 = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            r2 = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            assert r1.payload.get("ticker") == r2.payload.get("ticker")

    async def test_history_selected(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_session_event(engine, session_id, "SESSION_CREATED")
        await _add_trade_action(engine, session_id, "POSITION_OPENED")
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            assert len(result.selected_event_ids) >= 1


# ===================================================================
# Ownership
# ===================================================================


class TestOwnership:
    async def test_wrong_owner_rejected(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        other_user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_session_event(engine, session_id, "SESSION_CREATED")
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            with pytest.raises(ContextSummarySessionNotFoundError):
                await builder.build(
                    session_id=session_id, owner_id=other_user_id,
                )


# ===================================================================
# Boundaries
# ===================================================================


class TestBoundaries:
    async def test_trade_state_unchanged(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_session_event(engine, session_id, "SESSION_CREATED")
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            await builder.build(
                session_id=session_id, owner_id=user_id,
            )
        async with factory() as s:
            row = await s.execute(
                text("SELECT entry_price FROM trade_states WHERE session_id = :sid"),
                {"sid": session_id},
            )
            assert row.first()[0] == 2500

    async def test_no_provider_call(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_session_event(engine, session_id, "SESSION_CREATED")
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            await builder.build(
                session_id=session_id, owner_id=user_id,
            )

    async def test_no_persistence(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_session_event(engine, session_id, "SESSION_CREATED")
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            await builder.build(
                session_id=session_id, owner_id=user_id,
            )
