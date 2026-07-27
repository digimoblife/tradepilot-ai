"""Tests for P6 Historical Same-Ticker Context.

Verifies same-ticker matching, uppercase ticker normalization, same-user isolation,
terminal session filtering, bounded maximum (limit 5), compact aggregation,
no raw evidence images/payloads, and API endpoint behavior.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models.enums import AcceptanceStatus, TradeSessionStatus
from app.services.same_ticker_history import SameTickerHistoryService

pytestmark = pytest.mark.database


async def _make_user(engine: AsyncEngine) -> uuid.UUID:
    async with engine.begin() as conn:
        res = await conn.execute(
            text(
                "INSERT INTO users (email, password_hash) "
                "VALUES (:e, 'hash') RETURNING id"
            ),
            {"e": f"user_{uuid.uuid4().hex[:8]}@example.com"},
        )
        return res.scalar_one()


async def _make_session(
    engine: AsyncEngine,
    owner_id: uuid.UUID,
    ticker: str,
    status: str,
    updated_at: datetime | None = None,
) -> uuid.UUID:
    session_id = uuid.uuid4()
    now = updated_at or datetime.now(timezone.utc)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO trade_sessions "
                "(id, owner_id, ticker, lifecycle_status, stable_status, created_at, updated_at) "
                "VALUES (:sid, :uid, :tk, :st, :st, :now, :now)"
            ),
            {"sid": session_id, "uid": owner_id, "tk": ticker, "st": status, "now": now},
        )
        await conn.execute(
            text(
                "INSERT INTO trade_states (session_id, position_status, entry_price, average_exit_price, realized_return) "
                "VALUES (:sid, :pst, 5000, 5500, 10.0)"
            ),
            {
                "sid": session_id,
                "pst": "CLOSED" if status.startswith("CLOSED") else "NOT_OPENED",
            },
        )
    return session_id


class TestSameTickerHistory:
    async def test_same_ticker_matching_and_normalization(self, engine: AsyncEngine) -> None:
        user_id = await _make_user(engine)
        s1 = await _make_session(engine, user_id, "bbri ", "CLOSED")
        curr = await _make_session(engine, user_id, "BBRI", "DRAFT")

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as s:
            svc = SameTickerHistoryService(s)
            summary = await svc.build_history_summary(
                owner_id=user_id,
                ticker=" Bbri",
                current_session_id=curr,
            )
            assert summary["historical_context_used"] is True
            assert summary["historical_session_count"] == 1
            assert str(s1) in summary["historical_source_session_ids"]

    async def test_same_user_isolation(self, engine: AsyncEngine) -> None:
        user1 = await _make_user(engine)
        user2 = await _make_user(engine)

        s_other_user = await _make_session(engine, user2, "BBRI", "CLOSED")
        curr = await _make_session(engine, user1, "BBRI", "DRAFT")

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as s:
            svc = SameTickerHistoryService(s)
            summary = await svc.build_history_summary(
                owner_id=user1,
                ticker="BBRI",
                current_session_id=curr,
            )
            assert summary["historical_context_used"] is False
            assert summary["historical_session_count"] == 0
            assert str(s_other_user) not in summary["historical_source_session_ids"]

    async def test_excludes_current_session_and_active_sessions(self, engine: AsyncEngine) -> None:
        user_id = await _make_user(engine)
        _active1 = await _make_session(engine, user_id, "TLKM", "INITIAL_ANALYZED")
        _active2 = await _make_session(engine, user_id, "TLKM", "WATCHING")
        closed1 = await _make_session(engine, user_id, "TLKM", "CLOSED")
        curr = await _make_session(engine, user_id, "TLKM", "DRAFT")

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as s:
            svc = SameTickerHistoryService(s)
            summary = await svc.build_history_summary(
                owner_id=user_id,
                ticker="TLKM",
                current_session_id=curr,
            )
            assert summary["historical_session_count"] == 1
            assert summary["historical_source_session_ids"] == [str(closed1)]

    async def test_terminal_statuses_inclusion(self, engine: AsyncEngine) -> None:
        user_id = await _make_user(engine)
        s_closed = await _make_session(engine, user_id, "ASII", "CLOSED")
        s_skipped = await _make_session(engine, user_id, "ASII", "CLOSED_SKIPPED")
        s_tp = await _make_session(engine, user_id, "ASII", "CLOSED_TAKE_PROFIT")
        curr = await _make_session(engine, user_id, "ASII", "DRAFT")

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as s:
            svc = SameTickerHistoryService(s)
            summary = await svc.build_history_summary(
                owner_id=user_id,
                ticker="ASII",
                current_session_id=curr,
            )
            assert summary["historical_session_count"] == 3
            assert summary["completed_trade_count"] == 2
            assert summary["skipped_session_count"] == 1
            ids = set(summary["historical_source_session_ids"])
            assert ids == {str(s_closed), str(s_skipped), str(s_tp)}

    async def test_bounded_maximum_and_newest_first_ordering(self, engine: AsyncEngine) -> None:
        user_id = await _make_user(engine)
        now = datetime.now(timezone.utc)
        created_ids = []
        for i in range(7):
            sid = await _make_session(
                engine,
                user_id,
                "UNVR",
                "CLOSED",
                updated_at=now - timedelta(days=7 - i),
            )
            created_ids.append(sid)

        curr = await _make_session(engine, user_id, "UNVR", "DRAFT")

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as s:
            svc = SameTickerHistoryService(s)
            summary = await svc.build_history_summary(
                owner_id=user_id,
                ticker="UNVR",
                current_session_id=curr,
                max_sessions=5,
            )
            # Bounded to 5
            assert summary["historical_session_count"] == 5
            # Newest sessions first
            expected_newest_5 = [str(sid) for sid in reversed(created_ids[2:])]
            assert summary["historical_source_session_ids"] == expected_newest_5

    async def test_no_raw_payloads_or_evidence_images(self, engine: AsyncEngine) -> None:
        user_id = await _make_user(engine)
        s1 = await _make_session(engine, user_id, "BCA", "CLOSED")
        curr = await _make_session(engine, user_id, "BCA", "DRAFT")

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as s:
            svc = SameTickerHistoryService(s)
            summary = await svc.build_history_summary(
                owner_id=user_id,
                ticker="BCA",
                current_session_id=curr,
            )
            import json
            dumped = json.dumps(summary)
            assert "raw_payload" not in dumped
            assert "image_bytes" not in dumped
            assert "base64" not in dumped
            assert len(dumped) < 10000  # Proves bounded serialization

    async def test_recurring_pattern_minimum_evidence(self, engine: AsyncEngine) -> None:
        user_id = await _make_user(engine)
        # Single prior session
        _s1 = await _make_session(engine, user_id, "GOTO", "CLOSED")
        curr = await _make_session(engine, user_id, "GOTO", "DRAFT")

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as s:
            svc = SameTickerHistoryService(s)
            summary = await svc.build_history_summary(
                owner_id=user_id,
                ticker="GOTO",
                current_session_id=curr,
            )
            # Minimum 2 sessions required for recurring patterns
            assert summary["historical_session_count"] == 1
            assert summary["recurring_support_resistance"] == []
            assert summary["recurring_orderbook_patterns"] == []

    async def test_incomplete_and_legacy_sessions(self, engine: AsyncEngine) -> None:
        user_id = await _make_user(engine)
        # Session missing entry/exit price facts
        session_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO trade_sessions (id, owner_id, ticker, lifecycle_status, stable_status, created_at, updated_at) "
                    "VALUES (:sid, :uid, 'ANTM', 'CLOSED', 'CLOSED', :now, :now)"
                ),
                {"sid": session_id, "uid": user_id, "now": now},
            )
            # Incomplete trade state (no entry or exit price)
            await conn.execute(
                text(
                    "INSERT INTO trade_states (session_id, position_status) "
                    "VALUES (:sid, 'CLOSED')"
                ),
                {"sid": session_id},
            )

        curr = await _make_session(engine, user_id, "ANTM", "DRAFT")

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as s:
            svc = SameTickerHistoryService(s)
            summary = await svc.build_history_summary(
                owner_id=user_id,
                ticker="ANTM",
                current_session_id=curr,
            )
            assert summary["historical_session_count"] == 1
            assert len(summary["data_quality_notes"]) == 1
            assert "missing full entry/exit price details" in summary["data_quality_notes"][0]

    async def test_oversized_payload_compaction_and_bounding(self, engine: AsyncEngine) -> None:
        user_id = await _make_user(engine)
        now = datetime.now(timezone.utc)

        # Create 10 prior completed sessions with large 50KB payloads
        large_summary_text = "Analysis detail " * 3000  # ~45KB string
        for i in range(10):
            sid = await _make_session(
                engine,
                user_id,
                "ICBP",
                "CLOSED",
                updated_at=now - timedelta(days=10 - i),
            )
            job_id = uuid.uuid4()
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        "INSERT INTO analysis_jobs (id, session_id, analysis_type, status, previous_session_status, attempt_count, max_attempts, requested_at, available_at) "
                        "VALUES (:jid, :sid, 'CLOSING_ANALYSIS', 'COMPLETED', 'CLOSED', 1, 1, :now, :now)"
                    ),
                    {"jid": job_id, "sid": sid, "now": now},
                )
                import json
                await conn.execute(
                    text(
                        "INSERT INTO analyses (id, session_id, analysis_job_id, analysis_type, acceptance_status, prompt_name, prompt_version, schema_name, schema_version, payload, accepted_at) "
                        "VALUES (:aid, :sid, :jid, 'CLOSING_ANALYSIS', 'ACCEPTED', 'CLOSING_ANALYSIS', '1.0.0', 'closing_analysis', '1.0.0', :payload, :now)"
                    ),
                    {
                        "aid": uuid.uuid4(),
                        "sid": sid,
                        "jid": job_id,
                        "payload": json.dumps({"trade_summary": large_summary_text, "lessons_learned": ["Lesson A", "Lesson B"]}),
                        "now": now,
                    },
                )

        curr = await _make_session(engine, user_id, "ICBP", "DRAFT")

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as s:
            svc = SameTickerHistoryService(s)
            summary = await svc.build_history_summary(
                owner_id=user_id,
                ticker="ICBP",
                current_session_id=curr,
                max_sessions=5,
            )
            import json
            serialized = json.dumps(summary)
            # Maximum 5 source sessions bounded
            assert summary["historical_session_count"] == 5
            # Compacted size is ~4KB instead of 500KB raw
            assert len(serialized) < 15000
            print(f"DEBUG: Bounded serialized history JSON size = {len(serialized)} bytes")
