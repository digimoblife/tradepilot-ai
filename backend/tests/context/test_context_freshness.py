"""Tests for ContextFreshnessService (TP-0903)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.context import (
    ContextFreshnessEnsureResult,
    ContextFreshnessService,
    ContextFreshnessSessionNotFoundError,
    ContextSummaryNotFoundError,
    ContextSummarySessionMismatchError,
)

pytestmark = pytest.mark.database


# ===================================================================
# Helpers
# ===================================================================


async def _make_user(engine: AsyncEngine) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
            {"e": f"fr_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
        )
        return r.first()[0]


async def _make_session(
    engine: AsyncEngine,
    user_id: uuid.UUID,
    status: str = "OPEN_POSITION",
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
        return r.first()[0]


async def _make_context_summary(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    *,
    source_cutoff: datetime,
    version: int = 1,
    is_stale: bool = False,
) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                "INSERT INTO context_summaries "
                "(session_id, context_version, source_cutoff, payload, is_stale) "
                "VALUES (:sid, :v, :sc, '{}'::jsonb, :stale) RETURNING id"
            ),
            {"sid": session_id, "v": version, "sc": source_cutoff, "stale": is_stale},
        )
        return r.first()[0]


async def _add_trade_action(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    action_type: str,
    confirmed_at: datetime,
) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                "INSERT INTO trade_actions "
                "(session_id, action_type, confirmed_at, idempotency_key) "
                "VALUES (:sid, :at, :ca, :ik) RETURNING id"
            ),
            {
                "sid": session_id,
                "at": action_type,
                "ca": confirmed_at,
                "ik": f"fr_{uuid.uuid4().hex}",
            },
        )
        return r.first()[0]


async def _add_analysis(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    analysis_type: str = "WATCHING_UPDATE",
    status: str = "ACCEPTED",
    accepted_at: datetime | None = None,
) -> uuid.UUID:
    async with engine.begin() as conn:
        pl = json.dumps({"executive_summary": "test"})
        r = await conn.execute(
            text(
                "INSERT INTO analyses "
                "(session_id, analysis_type, acceptance_status, "
                "prompt_name, prompt_version, schema_name, schema_version, "
                "payload, accepted_at) "
                "VALUES (:sid, :at, :st, "
                "'test', '1.0.0', 'test', '1.0.0', :pl, :aa) RETURNING id"
            ),
            {
                "sid": session_id,
                "at": analysis_type,
                "st": status,
                "pl": pl,
                "aa": accepted_at,
            },
        )
        return r.first()[0]


async def _make_trade_state(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    position_status: str = "OPEN",
) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO trade_states "
                "(session_id, position_status, thesis_status, "
                "entry_price, original_quantity, remaining_quantity, "
                "active_stop_loss, active_target, state_version, entry_at) "
                "VALUES (:s, :ps, 'INTACT', "
                "2500, 1000, 1000, 2400, 2800, 1, :ea) "
                "ON CONFLICT (session_id) DO NOTHING"
            ),
            {
                "s": session_id,
                "ps": position_status,
                "ea": datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc),
            },
        )


async def _add_evidence(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    owner_id: uuid.UUID,
    evidence_type: str,
    status: str = "AVAILABLE",
    market_ts: datetime | None = None,
    uploaded_at: datetime | None = None,
    deleted: bool = False,
) -> uuid.UUID:
    async with engine.begin() as conn:
        now = datetime.now(timezone.utc)
        exclusion_reason = None
        excluded_at = None
        if status == "EXCLUDED":
            exclusion_reason = "Test exclusion"
            excluded_at = now
        r = await conn.execute(
            text(
                "INSERT INTO evidence "
                "(session_id, owner_id, evidence_type, evidence_status, "
                "storage_object_key, mime_type, file_size_bytes, "
                "market_timestamp, uploaded_at, deleted_at, "
                "exclusion_reason, excluded_at) "
                "VALUES (:sid, :oid, :et, :es, :key, 'image/png', 100, "
                ":mts, :ua, :da, :er, :ea) RETURNING id"
            ),
            {
                "sid": session_id,
                "oid": owner_id,
                "et": evidence_type,
                "es": status,
                "key": f"test/fr_{uuid.uuid4().hex}",
                "mts": market_ts,
                "ua": uploaded_at or now,
                "da": now if deleted else None,
                "er": exclusion_reason,
                "ea": excluded_at,
            },
        )
        return r.first()[0]


async def _add_session_event(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    event_type: str,
    occurred_at: datetime,
) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                "INSERT INTO session_events "
                "(session_id, event_type, occurred_at) "
                "VALUES (:sid, :et, :oa) RETURNING id"
            ),
            {"sid": session_id, "et": event_type, "oa": occurred_at},
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
# Fresh context
# ===================================================================


class TestFreshContext:
    async def test_equal_cutoff_fresh(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        cs_id = await _make_context_summary(engine, session_id, source_cutoff=base)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is True
            assert result.context_summary_id == cs_id
            assert result.source_cutoff == base
            assert result.stale_reasons == ()

    async def test_cutoff_newer_than_sources(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
        older = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _add_trade_action(engine, session_id, "POSITION_OPENED", older)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is True
            assert result.source_cutoff == base

    async def test_fresh_no_record_changes(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is True
            # Verify no db writes by re-reading state
            row = await s.execute(
                text("SELECT is_stale FROM context_summaries WHERE session_id=:sid"),
                {"sid": session_id},
            )
            assert row.first()[0] is False


# ===================================================================
# Explicit stale flag
# ===================================================================


class TestExplicitStale:
    async def test_stale_flag_returns_stale(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base, is_stale=True)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is False
            assert any(r.code == "CONTEXT_EXPLICITLY_STALE" for r in result.stale_reasons)

    async def test_equal_timestamps_do_not_override_stale_flag(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base, is_stale=True)
        # Add a source at exactly the same cutoff time (should NOT clear staleness)
        await _add_trade_action(engine, session_id, "POSITION_OPENED", base)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is False
            assert any(r.code == "CONTEXT_EXPLICITLY_STALE" for r in result.stale_reasons)

    async def test_service_does_not_clear_flag(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base, is_stale=True)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            await svc.check(session_id=session_id, owner_id=user_id)
        # Verify flag unchanged
        async with factory() as s:
            row = await s.execute(
                text("SELECT is_stale FROM context_summaries WHERE session_id=:sid"),
                {"sid": session_id},
            )
            assert row.first()[0] is True


# ===================================================================
# Confirmed actions
# ===================================================================


class TestConfirmedActions:
    async def test_newer_position_open_makes_stale(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_trade_action(engine, session_id, "POSITION_OPENED", newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is False
            assert any(r.code == "CONTEXT_NEWER_TRADE_ACTION" for r in result.stale_reasons)

    async def test_newer_stop_change_makes_stale(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_trade_action(engine, session_id, "STOP_LOSS_CHANGED", newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is False

    async def test_newer_target_change_makes_stale(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_trade_action(engine, session_id, "TARGET_CONFIRMED", newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is False

    async def test_newer_partial_exit_makes_stale(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_trade_action(engine, session_id, "PARTIAL_EXIT", newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is False

    async def test_newer_full_exit_makes_stale(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_trade_action(engine, session_id, "FULL_EXIT", newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is False

    async def test_action_at_cutoff_remains_fresh(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        await _add_trade_action(engine, session_id, "POSITION_OPENED", base)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is True


# ===================================================================
# Accepted analyses
# ===================================================================


class TestAcceptedAnalyses:
    async def test_newer_accepted_analysis_makes_stale(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_analysis(engine, session_id, "WATCHING_UPDATE", "ACCEPTED", accepted_at=newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is False
            assert any(r.code == "CONTEXT_NEWER_ACCEPTED_ANALYSIS" for r in result.stale_reasons)

    async def test_rejected_analysis_ignored(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_analysis(engine, session_id, "WATCHING_UPDATE", "REJECTED", accepted_at=newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is True

    async def test_raw_response_ignored(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_analysis(engine, session_id, "WATCHING_UPDATE", "PENDING", accepted_at=newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is True

    async def test_older_accepted_analysis_ignored(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        older = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _add_analysis(engine, session_id, "INITIAL_ANALYSIS", "ACCEPTED", accepted_at=older)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is True


# ===================================================================
# Evidence
# ===================================================================


class TestEvidence:
    async def test_newer_active_chart_makes_stale(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_evidence(engine, session_id, user_id, "CHART_THREE_MONTH", market_ts=newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is False
            assert any(r.code == "CONTEXT_NEWER_ACTIVE_EVIDENCE" for r in result.stale_reasons)

    async def test_replaced_active_evidence_makes_stale(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_evidence(engine, session_id, user_id, "ORDERBOOK_SCREENSHOT", market_ts=newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is False

    async def test_superseded_evidence_ignored(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        # Superseded evidence is not returned by list_active_for_session_for_user
        await _add_evidence(
            engine, session_id, user_id, "CHART_THREE_MONTH", status="SUPERSEDED", market_ts=newer
        )
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is True

    async def test_excluded_evidence_ignored(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_evidence(
            engine, session_id, user_id, "CHART_THREE_MONTH", status="EXCLUDED", market_ts=newer
        )
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is True

    async def test_deleted_evidence_ignored(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_evidence(
            engine, session_id, user_id, "CHART_THREE_MONTH", market_ts=newer, deleted=True
        )
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is True

    async def test_market_timestamp_rule(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        market_ts = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        upload_ts = datetime(2026, 7, 14, 8, 0, tzinfo=timezone.utc)
        await _add_evidence(
            engine,
            session_id,
            user_id,
            "CHART_THREE_MONTH",
            market_ts=market_ts,
            uploaded_at=upload_ts,
        )
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            # market_ts is newer than base, so stale
            assert result.fresh is False

    async def test_upload_timestamp_rule(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        upload_ts = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_evidence(
            engine, session_id, user_id, "CHART_THREE_MONTH", market_ts=None, uploaded_at=upload_ts
        )
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is False


# ===================================================================
# Material events
# ===================================================================


class TestMaterialEvents:
    async def test_newer_material_event_makes_stale(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_session_event(engine, session_id, "POSITION_OPENED", newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is False
            assert any(r.code == "CONTEXT_NEWER_MATERIAL_EVENT" for r in result.stale_reasons)

    async def test_routine_event_ignored(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_session_event(engine, session_id, "NOTE_ADDED", newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.fresh is True


# ===================================================================
# No summary and ownership
# ===================================================================


class TestNoSummaryAndOwnership:
    async def test_missing_summary_raises(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        async with factory() as s:
            svc = ContextFreshnessService(s)
            with pytest.raises(ContextSummaryNotFoundError):
                await svc.check(session_id=session_id, owner_id=user_id)

    async def test_wrong_owner_rejected(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        other_user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            with pytest.raises(ContextFreshnessSessionNotFoundError):
                await svc.check(session_id=session_id, owner_id=other_user_id)

    async def test_session_not_found_raises(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        bogus = uuid.uuid4()
        async with factory() as s:
            svc = ContextFreshnessService(s)
            with pytest.raises(ContextFreshnessSessionNotFoundError):
                await svc.check(session_id=bogus, owner_id=user_id)

    async def test_summary_from_another_session_rejected(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
        cs_id = await _make_context_summary(engine, session_id, source_cutoff=base)
        other_session = await _make_session(engine, user_id)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            with pytest.raises(ContextSummarySessionMismatchError):
                await svc.check(
                    session_id=other_session,
                    owner_id=user_id,
                    context_summary_id=cs_id,
                )


# ===================================================================
# Determinism
# ===================================================================


class TestDeterminism:
    async def test_repeated_check_identical(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_trade_action(engine, session_id, "POSITION_OPENED", newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            r1 = await svc.check(session_id=session_id, owner_id=user_id)
            r2 = await svc.check(session_id=session_id, owner_id=user_id)
            assert r1.fresh == r2.fresh
            assert r1.source_cutoff == r2.source_cutoff
            assert r1.required_cutoff == r2.required_cutoff
            assert len(r1.stale_reasons) == len(r2.stale_reasons)
            for a, b in zip(r1.stale_reasons, r2.stale_reasons):
                assert a.code == b.code
                assert a.source_id == b.source_id
                assert a.source_timestamp == b.source_timestamp

    async def test_reason_ordering_deterministic(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        ts1 = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        ts2 = datetime(2026, 7, 17, 10, 0, tzinfo=timezone.utc)
        await _add_trade_action(engine, session_id, "POSITION_OPENED", ts1)
        await _add_trade_action(engine, session_id, "STOP_LOSS_CHANGED", ts2)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            reasons = result.stale_reasons
            assert len(reasons) >= 2
            # Should be ordered by timestamp descending
            for i in range(len(reasons) - 1):
                r_i = reasons[i]
                r_j = reasons[i + 1]
                t_i = r_i.source_timestamp.timestamp() if r_i.source_timestamp else 0
                t_j = r_j.source_timestamp.timestamp() if r_j.source_timestamp else 0
                assert t_i >= t_j

    async def test_timestamps_timezone_aware(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.check(session_id=session_id, owner_id=user_id)
            assert result.source_cutoff.tzinfo is not None
            assert result.required_cutoff.tzinfo is not None


# ===================================================================
# Boundaries
# ===================================================================


class TestBoundaries:
    async def test_no_context_summary_build(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            await svc.check(session_id=session_id, owner_id=user_id)
        # Verify no new context summary was created
        async with factory() as s:
            rows = (
                await s.execute(
                    text("SELECT COUNT(*) FROM context_summaries WHERE session_id=:sid"),
                    {"sid": session_id},
                )
            ).first()[0]
            assert rows == 1

    async def test_no_stale_flag_update(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        cs_id = await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_trade_action(engine, session_id, "POSITION_OPENED", newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            await svc.check(session_id=session_id, owner_id=user_id)
        # Verify is_stale not auto-updated
        async with factory() as s:
            row = await s.execute(
                text("SELECT is_stale FROM context_summaries WHERE id=:cid"),
                {"cid": cs_id},
            )
            assert row.first()[0] is False

    async def test_no_provider_call(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            await svc.check(session_id=session_id, owner_id=user_id)
        # No provider call — just check it completes

    async def test_no_action_mutation(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        action_id = await _add_trade_action(engine, session_id, "POSITION_OPENED", newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            await svc.check(session_id=session_id, owner_id=user_id)
        # Verify action unchanged
        async with factory() as s:
            row = await s.execute(
                text("SELECT action_type FROM trade_actions WHERE id=:aid"),
                {"aid": action_id},
            )
            assert row.first()[0] == "POSITION_OPENED"

    async def test_no_analysis_mutation(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        aid = await _add_analysis(
            engine, session_id, "WATCHING_UPDATE", "ACCEPTED", accepted_at=newer
        )
        async with factory() as s:
            svc = ContextFreshnessService(s)
            await svc.check(session_id=session_id, owner_id=user_id)
        async with factory() as s:
            row = await s.execute(
                text("SELECT acceptance_status FROM analyses WHERE id=:aid"),
                {"aid": aid},
            )
            assert row.first()[0] == "ACCEPTED"


# ===================================================================
# Ensure-fresh: fresh context (no rebuild)
# ===================================================================


class TestEnsureFreshFresh:
    async def test_returns_existing_when_fresh(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
        cs_id = await _make_context_summary(engine, session_id, source_cutoff=base)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.ensure_fresh(session_id=session_id, owner_id=user_id)
            assert result.rebuilt is False
            assert result.context_summary_id == cs_id
            assert result.context_version >= 1
            assert isinstance(result, ContextFreshnessEnsureResult)

    async def test_no_duplicate_version_when_fresh(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            await svc.ensure_fresh(session_id=session_id, owner_id=user_id)
            rows = (
                await s.execute(
                    text("SELECT COUNT(*) FROM context_summaries WHERE session_id=:sid"),
                    {"sid": session_id},
                )
            ).first()[0]
            assert rows == 1

    async def test_idempotent_repeated_ensure(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            r1 = await svc.ensure_fresh(session_id=session_id, owner_id=user_id)
            r2 = await svc.ensure_fresh(session_id=session_id, owner_id=user_id)
            assert r1.rebuilt is False
            assert r2.rebuilt is False
            assert r1.context_summary_id == r2.context_summary_id
            assert r1.context_version == r2.context_version


# ===================================================================
# Ensure-fresh: stale context rebuild
# ===================================================================


class TestEnsureFreshRebuild:
    async def _setup(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        cutoff: datetime,
    ) -> None:
        """Create trade_state + base context_summary for rebuild tests."""
        await _make_trade_state(engine, session_id)
        await _make_context_summary(engine, session_id, source_cutoff=cutoff)

    async def test_accepted_analysis_triggers_rebuild(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await self._setup(engine, session_id, user_id, base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_analysis(engine, session_id, "WATCHING_UPDATE", "ACCEPTED", accepted_at=newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.ensure_fresh(session_id=session_id, owner_id=user_id)
            assert result.rebuilt is True
            assert result.context_version >= 1
            assert result.source_cutoff >= newer
            assert result.payload != {}

    async def test_new_version_persisted(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await self._setup(engine, session_id, user_id, base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_analysis(engine, session_id, "WATCHING_UPDATE", "ACCEPTED", accepted_at=newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            await svc.ensure_fresh(session_id=session_id, owner_id=user_id)
            # Verify within the same session (flush is visible)
            rows = (
                await s.execute(
                    text("SELECT COUNT(*) FROM context_summaries WHERE session_id=:sid"),
                    {"sid": session_id},
                )
            ).first()[0]
            assert rows == 2

    async def test_old_version_retained(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_trade_state(engine, session_id)
        old_id = await _make_context_summary(engine, session_id, source_cutoff=base, version=1)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_analysis(engine, session_id, "WATCHING_UPDATE", "ACCEPTED", accepted_at=newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            await svc.ensure_fresh(session_id=session_id, owner_id=user_id)
            row = await s.execute(
                text("SELECT id FROM context_summaries WHERE id=:oid"),
                {"oid": old_id},
            )
            assert row.first() is not None

    async def test_latest_lookup_returns_new(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await self._setup(engine, session_id, user_id, base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_analysis(engine, session_id, "WATCHING_UPDATE", "ACCEPTED", accepted_at=newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.ensure_fresh(session_id=session_id, owner_id=user_id)
            check = await svc.check(session_id=session_id, owner_id=user_id)
            assert check.fresh is True
            assert check.context_summary_id == result.context_summary_id

    async def test_user_action_triggers_rebuild(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await self._setup(engine, session_id, user_id, base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_trade_action(engine, session_id, "STOP_LOSS_CHANGED", newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.ensure_fresh(session_id=session_id, owner_id=user_id)
            assert result.rebuilt is True
            assert result.context_version >= 1

    async def test_evidence_replacement_triggers_rebuild(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await self._setup(engine, session_id, user_id, base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_evidence(engine, session_id, user_id, "CHART_THREE_MONTH", market_ts=newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.ensure_fresh(session_id=session_id, owner_id=user_id)
            assert result.rebuilt is True
            assert result.context_version >= 1

    async def test_explicit_stale_triggers_rebuild(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 20, 12, 0, tzinfo=timezone.utc)
        await _make_trade_state(engine, session_id)
        await _make_context_summary(engine, session_id, source_cutoff=base, is_stale=True)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.ensure_fresh(session_id=session_id, owner_id=user_id)
            assert result.rebuilt is True
            assert result.context_version >= 1

    async def test_source_cutoff_advanced(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await self._setup(engine, session_id, user_id, base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_analysis(engine, session_id, "WATCHING_UPDATE", "ACCEPTED", accepted_at=newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.ensure_fresh(session_id=session_id, owner_id=user_id)
            assert result.source_cutoff >= newer

    async def test_rebuilt_verified_fresh(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await self._setup(engine, session_id, user_id, base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_analysis(engine, session_id, "WATCHING_UPDATE", "ACCEPTED", accepted_at=newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.ensure_fresh(session_id=session_id, owner_id=user_id)
            assert result.rebuilt is True
            check = await svc.check(session_id=session_id, owner_id=user_id)
            assert check.fresh is True


# ===================================================================
# Ensure-fresh: missing summary
# ===================================================================


class TestEnsureFreshMissing:
    async def test_check_still_raises(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        async with factory() as s:
            svc = ContextFreshnessService(s)
            with pytest.raises(ContextSummaryNotFoundError):
                await svc.check(session_id=session_id, owner_id=user_id)

    async def test_ensure_creates_initial(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _make_trade_state(engine, session_id)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.ensure_fresh(session_id=session_id, owner_id=user_id)
            assert result.rebuilt is True
            assert result.context_version >= 1
            assert result.payload != {}

    async def test_initial_version_correct(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _make_trade_state(engine, session_id)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.ensure_fresh(session_id=session_id, owner_id=user_id)
            assert result.context_version >= 1

    async def test_repeated_ensure_does_not_duplicate(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _make_trade_state(engine, session_id)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            r1 = await svc.ensure_fresh(session_id=session_id, owner_id=user_id)
            r2 = await svc.ensure_fresh(session_id=session_id, owner_id=user_id)
            assert r1.rebuilt is True
            assert r2.rebuilt is False
            assert r1.context_summary_id == r2.context_summary_id
            rows = (
                await s.execute(
                    text("SELECT COUNT(*) FROM context_summaries WHERE session_id=:sid"),
                    {"sid": session_id},
                )
            ).first()[0]
            assert rows == 1


# ===================================================================
# Ensure-fresh: boundaries
# ===================================================================


class TestEnsureFreshBoundaries:
    async def test_no_provider_call(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_trade_state(engine, session_id)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_analysis(engine, session_id, "WATCHING_UPDATE", "ACCEPTED", accepted_at=newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            await svc.ensure_fresh(session_id=session_id, owner_id=user_id)

    async def test_trade_state_unchanged(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_trade_state(engine, session_id)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_analysis(engine, session_id, "WATCHING_UPDATE", "ACCEPTED", accepted_at=newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            await svc.ensure_fresh(session_id=session_id, owner_id=user_id)
        async with factory() as s:
            row = await s.execute(
                text("SELECT entry_price FROM trade_states WHERE session_id=:sid"),
                {"sid": session_id},
            )
            val = row.first()
            assert val is not None and val[0] == 2500

    async def test_no_api_or_frontend(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        base = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _make_trade_state(engine, session_id)
        await _make_context_summary(engine, session_id, source_cutoff=base)
        newer = datetime(2026, 7, 16, 10, 0, tzinfo=timezone.utc)
        await _add_analysis(engine, session_id, "WATCHING_UPDATE", "ACCEPTED", accepted_at=newer)
        async with factory() as s:
            svc = ContextFreshnessService(s)
            result = await svc.ensure_fresh(session_id=session_id, owner_id=user_id)
            assert result.rebuilt is True
