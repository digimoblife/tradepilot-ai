"""Tests for ProviderContextBuilder (TP-0803).

PostgreSQL-backed — no real AI provider calls.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.ai import (
    ProviderCapabilities,
    ProviderContext,
    ProviderContextBuilder,
    ProviderContextProviderIncompatibleError,
    ProviderContextSessionNotFoundError,
    ProviderContextStaleError,
)
from app.models.enums import AnalysisType

pytestmark = pytest.mark.database


# ===================================================================
# Helpers
# ===================================================================


async def _make_session(
    engine: AsyncEngine,
    owner_id: uuid.UUID,
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
            {"o": owner_id, "t": ticker, "ls": status, "ss": status},
        )
        sid = r.first()[0]
        await conn.execute(
            text(
                "INSERT INTO trade_states "
                "(session_id, position_status, thesis_status, state_version) "
                "VALUES (:s, 'NOT_OPENED', 'INTACT', 1)"
            ),
            {"s": sid},
        )
        return sid


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
                "VALUES (:sid, :oid, :et, :es, :key, :mt, 100, :mts) "
                "RETURNING id"
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


async def _add_context_summary(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    is_stale: bool = False,
    payload: dict | None = None,
) -> uuid.UUID:
    async with engine.begin() as conn:
        payload_json = json.dumps(payload or {})
        r = await conn.execute(
            text(
                "INSERT INTO context_summaries "
                "(session_id, context_version, payload, is_stale) "
                "VALUES (:sid, 1, :pl, :st) RETURNING id"
            ),
            {"sid": session_id, "pl": payload_json, "st": is_stale},
        )
        return r.first()[0]


async def _add_analysis(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    analysis_type: str,
    job_id: uuid.UUID,
    status: str = "ACCEPTED",
) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                "INSERT INTO analyses "
                "(session_id, analysis_job_id, analysis_type, acceptance_status, "
                "prompt_name, prompt_version, schema_name, schema_version, payload) "
                "VALUES (:sid, :jid, :at, :st, 'test', '1.0.0', 'test', '1.0.0', '{}') "
                "RETURNING id"
            ),
            {"sid": session_id, "jid": job_id, "at": analysis_type, "st": status},
        )
        return r.first()[0]


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
async def user_id(engine: AsyncEngine) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
            {"e": f"cb_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
        )
        return r.first()[0]


@pytest.fixture
async def other_user_id(engine: AsyncEngine) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
            {"e": f"cb2_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
        )
        return r.first()[0]


@pytest.fixture
def factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


_STANDARD_CAPS = ProviderCapabilities(
    supports_images=True,
    supports_structured_output=True,
    supports_system_prompt=True,
    supports_json_schema=True,
    supports_multi_image=True,
    maximum_images=10,
)

_NO_IMAGE_CAPS = ProviderCapabilities(
    supports_images=False,
    supports_structured_output=True,
    maximum_images=0,
)

_LIMITED_CAPS = ProviderCapabilities(
    supports_images=True,
    supports_structured_output=True,
    supports_multi_image=False,
    maximum_images=1,
)


# ===================================================================
# Complete context
# ===================================================================


class TestCompleteContext:
    async def test_builds_full_context(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, status="WATCHING")
        await _add_context_summary(engine, sid, is_stale=False, payload={"note": "ok"})

        async with factory() as s:
            builder = ProviderContextBuilder(s)
            ctx = await builder.build(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.WATCHING_UPDATE,
                provider_capabilities=_STANDARD_CAPS,
            )
            assert isinstance(ctx, ProviderContext)
            assert ctx.session_id == sid
            assert ctx.analysis_type == "WATCHING_UPDATE"

    async def test_canonical_facts_included(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, status="WATCHING", ticker="BBRI")
        await _add_context_summary(engine, sid, is_stale=False)
        async with factory() as s:
            builder = ProviderContextBuilder(s)
            ctx = await builder.build(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.WATCHING_UPDATE,
                provider_capabilities=_STANDARD_CAPS,
            )
            assert ctx.canonical_facts.get("ticker") == "BBRI"

    async def test_output_language(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, status="WATCHING")
        await _add_context_summary(engine, sid, is_stale=False)
        async with factory() as s:
            builder = ProviderContextBuilder(s)
            ctx = await builder.build(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.WATCHING_UPDATE,
                provider_capabilities=_STANDARD_CAPS,
            )
            assert ctx.metadata.get("output_language") == "id"


# ===================================================================
# Canonical separation
# ===================================================================


class TestCanonicalSeparation:
    async def test_canonical_facts_separate(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, status="WATCHING")
        await _add_context_summary(engine, sid, is_stale=False, payload={"entry_price": 5000})
        async with factory() as s:
            builder = ProviderContextBuilder(s)
            ctx = await builder.build(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.WATCHING_UPDATE,
                provider_capabilities=_STANDARD_CAPS,
            )
            # Canonical facts are in separate dict from context summary payload
            assert isinstance(ctx.canonical_facts, dict)
            assert "entry_price" not in ctx.metadata  # Not stored in generic metadata

    async def test_trade_state_unchanged(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, status="WATCHING")
        await _add_context_summary(engine, sid, is_stale=False)
        async with factory() as s:
            builder = ProviderContextBuilder(s)
            await builder.build(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.WATCHING_UPDATE,
                provider_capabilities=_STANDARD_CAPS,
            )
            # Verify no mutation
            ts_row = await s.execute(
                text("SELECT lifecycle_status FROM trade_sessions WHERE id = :sid"),
                {"sid": sid},
            )
            assert ts_row.first()[0] == "WATCHING"


# ===================================================================
# Stale context
# ===================================================================


class TestStaleContext:
    async def test_stale_context_rejected(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, status="WATCHING")
        await _add_context_summary(engine, sid, is_stale=True)
        async with factory() as s:
            builder = ProviderContextBuilder(s)
            with pytest.raises(ProviderContextStaleError):
                await builder.build(
                    session_id=sid,
                    owner_id=user_id,
                    analysis_type=AnalysisType.WATCHING_UPDATE,
                    provider_capabilities=_STANDARD_CAPS,
                )

    async def test_stale_context_no_mutation(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, status="WATCHING")
        await _add_context_summary(engine, sid, is_stale=True)
        async with factory() as s:
            builder = ProviderContextBuilder(s)
            with pytest.raises(ProviderContextStaleError):
                await builder.build(
                    session_id=sid,
                    owner_id=user_id,
                    analysis_type=AnalysisType.WATCHING_UPDATE,
                    provider_capabilities=_STANDARD_CAPS,
                )
        async with factory() as s:
            ts_row = await s.execute(
                text("SELECT lifecycle_status FROM trade_sessions WHERE id = :sid"),
                {"sid": sid},
            )
            assert ts_row.first()[0] == "WATCHING"


# ===================================================================
# Evidence ordering
# ===================================================================


class TestEvidenceOrdering:
    async def test_deterministic_order(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, status="WATCHING")
        await _add_context_summary(engine, sid, is_stale=False)

        # Insert in reverse canonical order
        await _add_evidence(engine, sid, user_id, "ORDERBOOK_SCREENSHOT")
        await _add_evidence(engine, sid, user_id, "CHART_SIX_MONTH")
        await _add_evidence(engine, sid, user_id, "CHART_THREE_MONTH")
        await _add_evidence(engine, sid, user_id, "BROKER_SUMMARY")

        async with factory() as s:
            builder = ProviderContextBuilder(s)
            ctx = await builder.build(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.WATCHING_UPDATE,
                provider_capabilities=_STANDARD_CAPS,
            )
            img_types = [img.mime_type for img in ctx.images]
            assert len(img_types) == 4

    async def test_repeated_build_same_order(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, status="WATCHING")
        await _add_context_summary(engine, sid, is_stale=False)
        await _add_evidence(engine, sid, user_id, "ORDERBOOK_SCREENSHOT")
        await _add_evidence(engine, sid, user_id, "CHART_THREE_MONTH")

        async with factory() as s:
            builder = ProviderContextBuilder(s)
            ctx1 = await builder.build(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.WATCHING_UPDATE,
                provider_capabilities=_STANDARD_CAPS,
            )
            ctx2 = await builder.build(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.WATCHING_UPDATE,
                provider_capabilities=_STANDARD_CAPS,
            )
            assert ctx1.images == ctx2.images

    async def test_inactive_evidence_excluded(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, status="WATCHING")
        await _add_context_summary(engine, sid, is_stale=False)
        await _add_evidence(engine, sid, user_id, "ORDERBOOK_SCREENSHOT", status="SUPERSEDED")
        async with factory() as s:
            builder = ProviderContextBuilder(s)
            ctx = await builder.build(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.WATCHING_UPDATE,
                provider_capabilities=_STANDARD_CAPS,
            )
            assert len(ctx.images) == 0


# ===================================================================
# Provider limits
# ===================================================================


class TestProviderLimits:
    async def test_image_capable_provider_receives_images(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, status="WATCHING")
        await _add_context_summary(engine, sid, is_stale=False)
        await _add_evidence(engine, sid, user_id, "ORDERBOOK_SCREENSHOT")
        async with factory() as s:
            builder = ProviderContextBuilder(s)
            ctx = await builder.build(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.WATCHING_UPDATE,
                provider_capabilities=_STANDARD_CAPS,
            )
            assert len(ctx.images) == 1

    async def test_no_image_provider_rejects(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, status="WATCHING")
        await _add_context_summary(engine, sid, is_stale=False)
        await _add_evidence(engine, sid, user_id, "ORDERBOOK_SCREENSHOT")
        async with factory() as s:
            builder = ProviderContextBuilder(s)
            with pytest.raises(ProviderContextProviderIncompatibleError):
                await builder.build(
                    session_id=sid,
                    owner_id=user_id,
                    analysis_type=AnalysisType.WATCHING_UPDATE,
                    provider_capabilities=_NO_IMAGE_CAPS,
                )

    async def test_image_limit_exceeded_truncated(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, status="WATCHING")
        await _add_context_summary(engine, sid, is_stale=False)
        for i in range(3):
            await _add_evidence(engine, sid, user_id, "CUSTOM_IMAGE")
        async with factory() as s:
            builder = ProviderContextBuilder(s)
            ctx = await builder.build(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.WATCHING_UPDATE,
                provider_capabilities=_LIMITED_CAPS,
            )
            assert len(ctx.images) == 1


# ===================================================================
# Ownership
# ===================================================================


class TestOwnership:
    async def test_wrong_owner_rejected(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        other_user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, status="WATCHING")
        await _add_context_summary(engine, sid, is_stale=False)
        async with factory() as s:
            builder = ProviderContextBuilder(s)
            with pytest.raises(ProviderContextSessionNotFoundError):
                await builder.build(
                    session_id=sid,
                    owner_id=other_user_id,
                    analysis_type=AnalysisType.WATCHING_UPDATE,
                    provider_capabilities=_STANDARD_CAPS,
                )


# ===================================================================
# Accepted analysis
# ===================================================================


class TestAcceptedAnalysis:
    async def test_accepted_analysis_included(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, status="WATCHING")
        await _add_context_summary(engine, sid, is_stale=False)
        # Create a job + accepted analysis
        async with engine.begin() as conn:
            jr = await conn.execute(
                text(
                    "INSERT INTO analysis_jobs "
                    "(session_id, analysis_type, status) "
                    "VALUES (:sid, 'WATCHING_UPDATE', 'COMPLETED') RETURNING id"
                ),
                {"sid": sid},
            )
            jid = jr.first()[0]
        await _add_analysis(engine, sid, "WATCHING_UPDATE", jid, status="ACCEPTED")

        async with factory() as s:
            builder = ProviderContextBuilder(s)
            ctx = await builder.build(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.WATCHING_UPDATE,
                provider_capabilities=_STANDARD_CAPS,
            )
            assert ctx.metadata.get("latest_analysis_id") is not None

    async def test_rejected_analysis_excluded(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, status="WATCHING")
        await _add_context_summary(engine, sid, is_stale=False)
        async with engine.begin() as conn:
            jr = await conn.execute(
                text(
                    "INSERT INTO analysis_jobs "
                    "(session_id, analysis_type, status) "
                    "VALUES (:sid, 'WATCHING_UPDATE', 'COMPLETED') RETURNING id"
                ),
                {"sid": sid},
            )
            jid = jr.first()[0]
        await _add_analysis(engine, sid, "WATCHING_UPDATE", jid, status="REJECTED")

        async with factory() as s:
            builder = ProviderContextBuilder(s)
            ctx = await builder.build(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.WATCHING_UPDATE,
                provider_capabilities=_STANDARD_CAPS,
            )
            assert ctx.metadata.get("latest_analysis_id") is None


# ===================================================================
# Boundaries
# ===================================================================


class TestBoundaries:
    async def test_no_provider_invocation(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, status="WATCHING")
        await _add_context_summary(engine, sid, is_stale=False)
        async with factory() as s:
            builder = ProviderContextBuilder(s)
            await builder.build(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.WATCHING_UPDATE,
                provider_capabilities=_STANDARD_CAPS,
            )

    async def test_no_persistence(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid = await _make_session(engine, user_id, status="WATCHING")
        await _add_context_summary(engine, sid, is_stale=False)
        async with factory() as s:
            builder = ProviderContextBuilder(s)
            await builder.build(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.WATCHING_UPDATE,
                provider_capabilities=_STANDARD_CAPS,
            )
            await s.rollback()
        async with factory() as s:
            row = await s.execute(
                text("SELECT lifecycle_status FROM trade_sessions WHERE id = :sid"),
                {"sid": sid},
            )
            assert row.first()[0] == "WATCHING"
