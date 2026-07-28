"""Tests for P7 Evaluation Record Service & Backfill.

Verifies structured prediction extraction, user decision recording, outcome completion,
idempotency, null-safety, and on-demand backfill.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models.analysis import Analysis
from app.models.enums import AcceptanceStatus, TradeSessionStatus
from app.models.evaluation_record import CompletenessStatus
from app.models.trade_session import TradeSession
from app.models.trade_state import TradeState
from app.services.evaluation_backfill import EvaluationBackfillService
from app.services.evaluation_records import EvaluationRecordService

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


async def _make_session_and_state(
    engine: AsyncEngine,
    owner_id: uuid.UUID,
    ticker: str = "BBRI",
    status: str = "INITIAL_ANALYZED",
) -> tuple[TradeSession, TradeState]:
    session_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
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

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        ts = await s.get(TradeSession, session_id)
        tstate = await s.get(TradeState, session_id)
        assert ts is not None
        assert tstate is not None
        return ts, tstate


async def _make_job(engine: AsyncEngine, session_id: uuid.UUID) -> uuid.UUID:
    job_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO analysis_jobs (id, session_id, analysis_type, status, previous_session_status, attempt_count, max_attempts, requested_at, available_at) "
                "VALUES (:jid, :sid, 'INITIAL_ANALYSIS', 'COMPLETED', 'DRAFT', 1, 1, :now, :now)"
            ),
            {"jid": job_id, "sid": session_id, "now": now},
        )
    return job_id


class TestEvaluationRecordService:
    async def test_actual_execution_model_is_persisted(self, engine: AsyncEngine) -> None:
        user_id = await _make_user(engine)
        ts, _ = await _make_session_and_state(engine, user_id)
        job_id = await _make_job(engine, ts.id)

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as s:
            analysis = Analysis(
                id=uuid.uuid4(),
                session_id=ts.id,
                analysis_job_id=job_id,
                analysis_type="INITIAL_ANALYSIS",
                acceptance_status=AcceptanceStatus.ACCEPTED,
                prompt_name="initial_analysis",
                prompt_version="2.0.0",
                schema_name="initial_analysis_v2",
                schema_version="2.0.0",
                payload={
                    "metadata": {
                        "provider": "gemini",
                        "model": "gemini-3.1-flash-lite",
                        "ticker": "BBRI",
                        "company_name": "Bank Rakyat Indonesia",
                    },
                    "recommendation": "BUY",
                },
            )
            s.add(analysis)
            await s.flush()

            record = await EvaluationRecordService(s).record_prediction_from_analysis(analysis, ts)

            assert record is not None
            assert record.provider == "gemini"
            assert record.model == "gemini-3.1-flash-lite"

    async def test_metadata_model_overrides_legacy_default_only_with_actual_value(
        self, engine: AsyncEngine
    ) -> None:
        user_id = await _make_user(engine)
        ts, _ = await _make_session_and_state(engine, user_id)
        job_id = await _make_job(engine, ts.id)

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as s:
            analysis = Analysis(
                id=uuid.uuid4(),
                session_id=ts.id,
                analysis_job_id=job_id,
                analysis_type="INITIAL_ANALYSIS",
                acceptance_status=AcceptanceStatus.ACCEPTED,
                prompt_name="initial_analysis",
                prompt_version="2.0.0",
                schema_name="initial_analysis_v2",
                schema_version="2.0.0",
                payload={"metadata": {"provider": "gemini", "model": "gemini-3.1-flash-lite"}},
            )
            s.add(analysis)
            await s.flush()

            record = await EvaluationRecordService(s).record_prediction_from_analysis(analysis, ts)

            assert record is not None
            assert record.model != "gemini-2.5-flash"
            assert record.model == "gemini-3.1-flash-lite"

    async def test_record_prediction_from_accepted_analysis(self, engine: AsyncEngine) -> None:
        user_id = await _make_user(engine)
        ts, _ = await _make_session_and_state(engine, user_id)
        job_id = await _make_job(engine, ts.id)

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as s:
            analysis = Analysis(
                id=uuid.uuid4(),
                session_id=ts.id,
                analysis_job_id=job_id,
                analysis_type="INITIAL_ANALYSIS",
                acceptance_status=AcceptanceStatus.ACCEPTED,
                prompt_name="initial_analysis",
                prompt_version="1.0.0",
                schema_name="initial_analysis",
                schema_version="1.0.0",
                payload={
                    "recommendation": "BUY",
                    "confidence": 0.85,
                    "bullish_probability": 0.70,
                    "bearish_probability": 0.15,
                    "neutral_probability": 0.15,
                    "proposed_entry": "5000",
                    "proposed_stop": "4800",
                    "proposed_targets": ["5500", "6000"],
                },
            )
            s.add(analysis)
            await s.flush()

            svc = EvaluationRecordService(s)
            record = await svc.record_prediction_from_analysis(analysis, ts)
            assert record is not None
            assert record.session_id == ts.id
            assert record.source_analysis_id == analysis.id
            assert record.prediction_data["recommendation"] == "BUY"
            assert record.prediction_data["confidence"] == 0.85
            assert record.completeness_status == CompletenessStatus.PARTIAL.value

    async def test_unaccepted_analysis_excluded(self, engine: AsyncEngine) -> None:
        user_id = await _make_user(engine)
        ts, _ = await _make_session_and_state(engine, user_id)
        job_id = await _make_job(engine, ts.id)

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as s:
            analysis = Analysis(
                id=uuid.uuid4(),
                session_id=ts.id,
                analysis_job_id=job_id,
                analysis_type="INITIAL_ANALYSIS",
                acceptance_status=AcceptanceStatus.REJECTED,
                prompt_name="initial_analysis",
                prompt_version="1.0.0",
                schema_name="initial_analysis",
                schema_version="1.0.0",
                payload={"recommendation": "BUY"},
            )
            s.add(analysis)
            await s.flush()

            svc = EvaluationRecordService(s)
            record = await svc.record_prediction_from_analysis(analysis, ts)
            assert record is None

    async def test_idempotency_prevents_duplicate_records(self, engine: AsyncEngine) -> None:
        user_id = await _make_user(engine)
        ts, _ = await _make_session_and_state(engine, user_id)
        job_id = await _make_job(engine, ts.id)

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as s:
            analysis = Analysis(
                id=uuid.uuid4(),
                session_id=ts.id,
                analysis_job_id=job_id,
                analysis_type="INITIAL_ANALYSIS",
                acceptance_status=AcceptanceStatus.ACCEPTED,
                prompt_name="initial_analysis",
                prompt_version="1.0.0",
                schema_name="initial_analysis",
                schema_version="1.0.0",
                payload={"recommendation": "BUY"},
            )
            s.add(analysis)
            await s.flush()

            svc = EvaluationRecordService(s)
            rec1 = await svc.record_prediction_from_analysis(analysis, ts)
            rec2 = await svc.record_prediction_from_analysis(analysis, ts)
            assert rec1 is not None
            assert rec2 is not None
            assert rec1.id == rec2.id

    async def test_record_user_decision_and_outcome_completion(self, engine: AsyncEngine) -> None:
        user_id = await _make_user(engine)
        ts, tstate = await _make_session_and_state(engine, user_id, status="CLOSED")

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as s:
            svc = EvaluationRecordService(s)
            # Record user BUY action
            rec = await svc.record_user_decision(
                ts,
                "BUY",
                {"entry_price": 5000, "entry_timestamp": "2026-07-27T10:00:00Z"},
            )
            assert rec is not None
            assert rec.user_decision_data["user_action"] == "BUY"
            assert rec.user_decision_data["actual_entry_price"] == "5000"

            # Record outcome completion
            rec_outcome = await svc.record_outcome_on_closure(ts, tstate)
            assert rec_outcome is not None
            assert rec_outcome.outcome_data["session_completed"] is True
            assert float(rec_outcome.outcome_data["realized_return"]) == 10.0
            assert rec_outcome.completeness_status == CompletenessStatus.COMPLETE.value

    async def test_backfill_session(self, engine: AsyncEngine) -> None:
        user_id = await _make_user(engine)
        ts, _ = await _make_session_and_state(engine, user_id, status="CLOSED")

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as s:
            backfill_svc = EvaluationBackfillService(s)
            records = await backfill_svc.backfill_session(ts.id, user_id)
            for r in records:
                assert r.legacy_source is True

    async def test_ai_recommendation_user_decision_mismatch(self, engine: AsyncEngine) -> None:
        user_id = await _make_user(engine)
        ts, tstate = await _make_session_and_state(engine, user_id, status="CLOSED")
        job_id = await _make_job(engine, ts.id)

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as s:
            analysis = Analysis(
                id=uuid.uuid4(),
                session_id=ts.id,
                analysis_job_id=job_id,
                analysis_type="INITIAL_ANALYSIS",
                acceptance_status=AcceptanceStatus.ACCEPTED,
                prompt_name="initial_analysis",
                prompt_version="1.0.0",
                schema_name="initial_analysis",
                schema_version="1.0.0",
                payload={"recommendation": "BUY"},
            )
            s.add(analysis)
            await s.flush()

            svc = EvaluationRecordService(s)
            # Record AI recommendation BUY
            await svc.record_prediction_from_analysis(analysis, ts)
            # Record User action SKIP (mismatch)
            await svc.record_user_decision(ts, "SKIP", {"reason": "risk too high"})
            rec_outcome = await svc.record_outcome_on_closure(ts, tstate)
            assert rec_outcome is not None
            assert rec_outcome.prediction_data["recommendation"] == "BUY"
            assert rec_outcome.user_decision_data["user_action"] == "SKIP"
            assert rec_outcome.outcome_data["recommendation_user_agreement"] is False

    async def test_repeated_decisions_auditable(self, engine: AsyncEngine) -> None:
        user_id = await _make_user(engine)
        ts, _ = await _make_session_and_state(engine, user_id)

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        async with factory() as s:
            svc = EvaluationRecordService(s)
            await svc.record_user_decision(ts, "WAIT", {"confirmed_at": "2026-07-28T08:00:00Z"})
            rec = await svc.record_user_decision(ts, "WAIT", {"confirmed_at": "2026-07-28T09:00:00Z"})
            assert rec is not None
            confirmed = rec.user_decision_data.get("confirmed_actions", [])
            assert len(confirmed) == 2
            assert confirmed[0]["action"] == "WAIT"
            assert confirmed[1]["action"] == "WAIT"
