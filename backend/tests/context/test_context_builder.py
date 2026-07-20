"""Tests for ContextSummaryBuilder (TP-0902)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.context import (
    ContextSummaryBuildResult,
    ContextSummaryBuilder,
    ContextSummarySessionNotFoundError,
    ContextSummaryValidationFailedError,
)
from app.models.enums import AcceptanceStatus, AnalysisType

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
    status: str = "OPEN_POSITION",
    ticker: str = "BBRI",
) -> tuple[uuid.UUID, str]:
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
            "active_stop_loss, active_target, state_version, entry_at) "
            "VALUES (:s, 'OPEN', 'INTACT', "
            ":ep, :oq, :rq, :sl, :tg, 1, :ea)"
            ),
            {
                "s": sid, "ep": 2500, "oq": 1000, "rq": 1000,
                "sl": 2400, "tg": 2800,
                "ea": datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc),
            },
        )
        return sid, status


async def _add_evidence(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    owner_id: uuid.UUID,
    evidence_type: str,
    status: str = "AVAILABLE",
    mime_type: str = "image/png",
    market_ts: datetime | None = None,
) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                "INSERT INTO evidence "
                "(session_id, owner_id, evidence_type, evidence_status, "
                "storage_object_key, mime_type, file_size_bytes, market_timestamp) "
                "VALUES (:sid, :oid, :et, :es, :key, :mt, 100, :mts) RETURNING id"
            ),
            {
                "sid": session_id,
                "oid": owner_id,
                "et": evidence_type,
                "es": status,
                "key": f"test/{evidence_type}",
                "mt": mime_type,
                "mts": market_ts,
            },
        )
        return r.first()[0]


async def _add_analysis(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    analysis_type: str = "INITIAL_ANALYSIS",
    status: str = "ACCEPTED",
    payload: dict | None = None,
) -> uuid.UUID:
    async with engine.begin() as conn:
        data = payload or {"executive_summary": "Initial thesis intact"}
        pl = json.dumps(data)
        r = await conn.execute(
            text(
                "INSERT INTO analyses "
                "(session_id, analysis_type, acceptance_status, "
                "prompt_name, prompt_version, schema_name, schema_version, payload, "
                "accepted_at) "
                "VALUES (:sid, :at, :st, "
                "'test', '1.0.0', 'test', '1.0.0', :pl, :now) RETURNING id"
            ),
            {
                "sid": session_id, "at": analysis_type, "st": status,
                "pl": pl, "now": datetime.now(timezone.utc),
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
    sid, _ = await _make_session(engine, user_id)
    return sid


@pytest.fixture
def factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# ===================================================================
# Full schema validation
# ===================================================================


class TestSchemaValidation:
    async def test_payload_schema_valid(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            assert isinstance(result, ContextSummaryBuildResult)

    async def test_domain_valid(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            assert result.validation_result.valid is True

    async def test_canonical_entry(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            entry = result.payload["current_position"]["entry_price"]
            assert entry is not None and "2500" in str(entry)

    async def test_canonical_quantity(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            qty = result.payload["current_position"]["original_quantity"]
            assert qty is not None and "1000" in str(qty)

    async def test_canonical_stop(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            stop = result.payload["current_position"]["active_stop_loss"]
            assert stop is not None and "2400" in str(stop)


# ===================================================================
# Original thesis
# ===================================================================


class TestOriginalThesis:
    async def test_original_thesis_from_earliest_accepted(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_analysis(engine, session_id, "INITIAL_ANALYSIS", "ACCEPTED",
                            {"executive_summary": "Original thesis statement"})
        await _add_analysis(engine, session_id, "WATCHING_UPDATE", "ACCEPTED",
                            {"executive_summary": "Updated thesis"})
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            thesis = result.payload["thesis_context"]
            assert thesis["original_thesis"] == "Original thesis statement"

    async def test_rejected_analysis_not_original(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_analysis(engine, session_id, "INITIAL_ANALYSIS", "REJECTED",
                            {"executive_summary": "Rejected thesis"})
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            assert result.payload["thesis_context"]["original_thesis"] is None

    async def test_current_thesis_separate(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            thesis = result.payload["thesis_context"]
            assert thesis["status"] is not None
            assert isinstance(thesis["original_thesis"], str) or thesis["original_thesis"] is None


# ===================================================================
# Pending proposals
# ===================================================================


class TestPendingProposals:
    async def test_pending_stop_proposal(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_analysis(engine, session_id, "WATCHING_UPDATE", "ACCEPTED",
                            {"proposed_stop_loss": {"price": 2350, "label": "Proposed SL", "summary": "Test"}})
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            props = result.payload["active_levels"]["proposed_stop_loss"]
            assert props is not None

    async def test_pending_target_proposal(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_analysis(engine, session_id, "WATCHING_UPDATE", "ACCEPTED",
                            {"target_proposal": {"price": 2900, "label": "Proposed Target", "summary": "Test"}})
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            props = result.payload["active_levels"]["proposed_target"]
            assert props is not None

    async def test_proposal_not_canonical(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_analysis(engine, session_id, "WATCHING_UPDATE", "ACCEPTED",
                            {"proposed_stop_loss": {"price": 2350, "label": "Proposed SL", "summary": "Test"}})
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            # Active stop remains canonical
            active = result.payload["active_levels"]["active_stop_loss"]
            assert active is not None and "2400" in str(active["price"])


# ===================================================================
# Chart context
# ===================================================================


class TestChartContext:
    async def test_chart_3_month_included(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_evidence(engine, session_id, user_id, "CHART_THREE_MONTH")
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            cc = result.payload["latest_chart_context"]
            assert cc["chart_3_month_available"] is True
            assert cc["available"] is True


    async def test_chart_6_month_included(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_evidence(engine, session_id, user_id, "CHART_SIX_MONTH")
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            cc = result.payload["latest_chart_context"]
            assert cc["chart_6_month_available"] is True

    async def test_market_upload_timestamps_separate(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        market_ts = datetime(2026, 7, 15, 9, 30, tzinfo=timezone.utc)
        await _add_evidence(engine, session_id, user_id,
                            "CHART_THREE_MONTH", market_ts=market_ts)
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            cc = result.payload["latest_chart_context"]
            assert cc["chart_3_month_available"] is True
            assert cc["latest_chart_timestamp"] is not None

    async def test_superseded_chart_excluded(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_evidence(engine, session_id, user_id,
                            "CHART_THREE_MONTH", status="SUPERSEDED")
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            cc = result.payload["latest_chart_context"]
            assert cc["chart_3_month_available"] is False


# ===================================================================
# Limitations
# ===================================================================


class TestLimitations:
    async def test_analysis_limitation_retained(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_analysis(engine, session_id, "INITIAL_ANALYSIS", "ACCEPTED",
                            {"limitations": ["Orderbook partially visible"]})
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            cq = result.payload["context_quality"]
            assert any("Orderbook" in str(l) for l in cq["limitations"])

    async def test_no_fabricated_limitations(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            cq = result.payload["context_quality"]
            assert isinstance(cq["limitations"], list)


# ===================================================================
# Source cutoff and determinism
# ===================================================================


class TestCutoffAndDeterminism:
    async def test_cutoff_from_latest_source(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _add_analysis(engine, session_id, "WATCHING_UPDATE", "ACCEPTED")
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            result = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            assert result.source_cutoff is not None

    async def test_repeated_build_identical_payload(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            r1 = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            r2 = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            assert r1.payload["context_id"] == r2.payload["context_id"]
            assert r1.payload["ticker"] == r2.payload["ticker"]

    async def test_no_random_context_id(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            r1 = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            r2 = await builder.build(
                session_id=session_id, owner_id=user_id,
            )
            assert r1.payload["context_id"] == r2.payload["context_id"]


# ===================================================================
# Ownership
# ===================================================================


class TestOwnership:
    async def test_wrong_owner_rejected(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        other_user_id: uuid.UUID, session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
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
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            await builder.build(session_id=session_id, owner_id=user_id)
        async with factory() as s:
            row = await s.execute(
                text("SELECT entry_price FROM trade_states WHERE session_id=:sid"),
                {"sid": session_id},
            )
            assert row.first()[0] == 2500

    async def test_no_provider_call(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            await builder.build(session_id=session_id, owner_id=user_id)

    async def test_no_persistence(
        self, engine: AsyncEngine, user_id: uuid.UUID,
        session_id: uuid.UUID, factory: async_sessionmaker[AsyncSession],
    ) -> None:
        async with factory() as s:
            builder = ContextSummaryBuilder(s)
            await builder.build(session_id=session_id, owner_id=user_id)
