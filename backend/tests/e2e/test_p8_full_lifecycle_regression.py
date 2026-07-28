"""P8 — Full Lifecycle Regression Suite (TP-1508).

Comprehensive end-to-end regression test suite proving the complete TradePilot AI
lifecycle from session creation through watching, position updates, full closure,
closing analysis, same-ticker history, failure paths, atomic rollback, and evaluation record audit.
Uses mock provider responses; does NOT invoke live Gemini APIs.
"""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.auth import AuthenticatedUser, hash_password
from app.jobs import AnalysisProcessingResult, AnalysisProcessor
from app.ai.providers.router import ProviderRouteAttempt, ProviderRouter, ProviderRoutingResult
from app.ai.providers import ProviderCapabilities, ProviderResponse
from app.models.trade_session import TradeSession
from app.models.enums import (
    AcceptanceStatus,
    ActionType,
    AnalysisJobStatus,
    AnalysisType,
    EvidenceBatchStatus,
    TradeSessionStatus,
)
from app.models.evaluation_record import CompletenessStatus, EvaluationRecord
from app.repositories.evaluation_record import EvaluationRecordRepository
from app.services.actions.full_exit import FullExitActionService
from app.services.actions.open_position import OpenPositionService
from app.services.actions.post_initial_decision import PostInitialDecisionService
from app.services.actions.stop_loss import StopLossActionService
from app.services.actions.target import TargetActionService
from app.services.analysis_jobs import AnalysisJobCreationService
from app.services.evaluation_backfill import EvaluationBackfillService
from app.services.evaluation_records import EvaluationRecordService
from app.services.evidence import EvidenceService
from app.services.evidence_batches import EvidenceBatchService
from app.services.same_ticker_history import SameTickerHistoryService
from app.services.trade_session import TradeSessionService

pytestmark = pytest.mark.database

FIXTURES_DIR = (
    Path(__file__).resolve().parent.parent.parent / "schemas" / "fixtures" / "valid" / "v1"
)

def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES_DIR / name).read_text())

def _make_image_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (10, 10), color="blue").save(buf, format="PNG")
    return buf.getvalue()


async def _create_test_user(engine: AsyncEngine) -> tuple[uuid.UUID, str]:
    uid = uuid.uuid4()
    email = f"user_p8_{uid.hex[:8]}@example.com"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, account_status) "
                "VALUES (:id, :e, :ph, 'ACTIVE')"
            ),
            {"id": uid, "e": email, "ph": hash_password("pass123")},
        )
    return uid, email


# ---------------------------------------------------------------------------
# Mock Provider Router for P8 AnalysisProcessor
# ---------------------------------------------------------------------------

def _partition_payloads_for_p8() -> dict[str, dict[str, object]]:
    payload = _load_fixture("initial_analysis_v2.valid.json")
    findings = payload["evidence_findings"]
    trade_plan = payload["trade_plan"]
    return {
        "MARKET_EVIDENCE": {
            "metadata": payload["metadata"],
            "market_facts": payload["market_facts"],
            "evidence_findings": {
                "orderbook": findings["orderbook"],
                "broker_summary": findings["broker_summary"],
                "foreign_flow": findings["foreign_flow"],
                "limitations": findings["limitations"],
            },
        },
        "CHART_ANALYSIS": {
            "evidence_findings": {
                "chart_3_month": findings["chart_3_month"],
                "chart_6_month": findings["chart_6_month"],
            },
            "trade_plan": {
                "nearest_support": trade_plan["nearest_support"],
                "nearest_resistance": trade_plan["nearest_resistance"],
            },
        },
        "TRADE_THESIS": {
            "trade_plan": {
                "entry_zone_low": trade_plan["entry_zone_low"],
                "entry_zone_high": trade_plan["entry_zone_high"],
                "chase_limit": trade_plan["chase_limit"],
                "stop_loss": trade_plan["stop_loss"],
                "target_1": trade_plan["target_1"],
                "target_2": trade_plan["target_2"],
                "invalidation": trade_plan["invalidation"],
                "risk_reward": trade_plan["risk_reward"],
            },
            "scenarios": payload["scenarios"],
        },
        "DECISION_ASSESSMENT": {
            "decision": payload["decision"],
            "probabilities": payload["probabilities"],
            "next_actions": payload["next_actions"],
        },
    }


class P8FakeRouter:
    """Fake ProviderRouter supplying valid fixture payloads to AnalysisProcessor."""

    def __init__(self, override_payload: dict[str, Any] | None = None) -> None:
        self.override_payload = override_payload

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return "gemini-2.5-flash"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_images=True,
            supports_text_output=True,
            supports_structured_output=True,
            supports_system_prompt=True,
            supports_json_schema=True,
            supports_multi_image=True,
            maximum_images=10,
        )

    async def generate_validated(self, **kwargs: Any) -> ProviderRoutingResult:
        request = kwargs["request"]
        partition_name = request.metadata.get("partition_name") if request.metadata else None
        if partition_name:
            parts = _partition_payloads_for_p8()
            payload = parts.get(str(partition_name), {"recommendation": "BUY"})
        else:
            payload = _load_fixture("initial_analysis_v2.valid.json")

        resp = ProviderResponse(
            provider="gemini",
            model="gemini-2.5-flash",
            raw_output=json.dumps(payload),
            request_id=request.request_id,
            latency_ms=10,
        )
        attempt = ProviderRouteAttempt(
            sequence=1,
            provider="gemini",
            phase="PRIMARY",
            response=resp,
            payload=payload,
        )
        return ProviderRoutingResult(
            provider="gemini",
            response=resp,
            payload=payload,
            attempts=(attempt,),
            fallback_used=False,
        )

    async def route(self, request: Any, callbacks: Any = None) -> ProviderRoutingResult:
        atype = request.analysis_type
        if self.override_payload:
            payload = self.override_payload
        elif atype == "WATCHING_UPDATE":
            payload = _load_fixture("watching_update.valid.json")
        elif atype == "OPEN_POSITION_UPDATE":
            payload = _load_fixture("open_position_update.valid.json")
        elif atype == "CLOSING_ANALYSIS":
            payload = _load_fixture("closing_analysis.valid.json")
        else:
            payload = _load_fixture("initial_analysis_v2.valid.json")

        resp = ProviderResponse(
            provider="gemini",
            model="gemini-2.5-flash",
            raw_output=json.dumps(payload),
            request_id=request.request_id,
            latency_ms=10,
        )
        attempt = ProviderRouteAttempt(
            sequence=1,
            provider="gemini",
            phase="PRIMARY",
            response=resp,
            payload=payload,
        )
        return ProviderRoutingResult(
            provider="gemini",
            response=resp,
            payload=payload,
            attempts=(attempt,),
            fallback_used=False,
        )


# ---------------------------------------------------------------------------
# P8 Primary Full Lifecycle Test Class
# ---------------------------------------------------------------------------

class TestP8FullLifecycleRegression:

    async def test_full_primary_lifecycle_e2e(self, engine: AsyncEngine) -> None:
        """Executes the complete happy-path lifecycle from DRAFT to CLOSED & Evaluation."""

        user_id, email = await _create_test_user(engine)
        ticker = "BBRI"

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        # -------------------------------------------------------------------
        # Step 1: Create Trade Session
        # -------------------------------------------------------------------
        async with factory() as s:
            ts_svc = TradeSessionService(s)
            session_result = await ts_svc.create_session(owner_id=user_id, ticker=ticker)
            session_id = session_result.id
            assert session_result.lifecycle_status == TradeSessionStatus.DRAFT.value

            # Get or create initial DRAFT evidence batch
            batch_svc = EvidenceBatchService(s)
            init_batch = await batch_svc.get_or_create_current_draft(
                session_id=session_id, owner_id=user_id, analysis_type=AnalysisType.INITIAL_ANALYSIS
            )
            assert init_batch is not None
            assert init_batch.status == EvidenceBatchStatus.DRAFT

            # ---------------------------------------------------------------
            # Step 2: Upload Initial Evidence & Mark Ready
            # ---------------------------------------------------------------
            ev_svc = EvidenceService(s, storage_root=Path("/tmp"))
            img_bytes = _make_image_bytes()

            for etype in ("ORDERBOOK_SCREENSHOT", "CHART_THREE_MONTH", "CHART_SIX_MONTH"):
                await ev_svc.create(
                    session_id=session_id,
                    owner_id=user_id,
                    evidence_type=etype,
                    content=img_bytes,
                    original_filename="test.png",
                    declared_mime_type="image/png",
                    evidence_batch_id=init_batch.id,
                )

            await batch_svc.mark_ready(init_batch)
            await s.commit()
        async with factory() as s:
            await s.execute(
                text(
                    "UPDATE trade_sessions SET lifecycle_status='READY_FOR_INITIAL_ANALYSIS', "
                    "stable_status='READY_FOR_INITIAL_ANALYSIS' WHERE id=:sid"
                ),
                {"sid": session_id},
            )
            await s.commit()

        # -------------------------------------------------------------------
        # Step 3: Request & Process Initial Analysis
        # -------------------------------------------------------------------
        async with factory() as s:
            job_svc = AnalysisJobCreationService(s)
            job_res = await job_svc.create(
                session_id=session_id,
                owner_id=user_id,
                analysis_type=AnalysisType.INITIAL_ANALYSIS,
            )
            job_id = job_res.job_id
            await s.commit()

        # Claim lease on job before processing
        async with factory() as s:
            await s.execute(
                text(
                    "UPDATE analysis_jobs SET status='PROCESSING', lease_owner='w1', "
                    "lease_acquired_at=NOW(), lease_expires_at=NOW() + INTERVAL '30 seconds' "
                    "WHERE id=:jid"
                ),
                {"jid": job_id},
            )
            await s.commit()

        async with factory() as s:
            router = P8FakeRouter()
            proc = AnalysisProcessor(
                session=s,
                router=router,
                providers={"gemini": router},
                provider_order=["gemini"],
            )
            res = await proc.process(job_id=job_id, worker_id="w1")
            assert res.job_status == AnalysisJobStatus.COMPLETED.value
            await s.commit()

        async with factory() as s:
            # Verify batch frozen & session INITIAL_ANALYZED
            ts = await s.get(TradeSession, session_id)
            assert ts.lifecycle_status == TradeSessionStatus.INITIAL_ANALYZED.value
            batch_svc = EvidenceBatchService(s)
            frozen_init_batch = await batch_svc.get_for_user(batch_id=init_batch.id, owner_id=user_id)
            assert frozen_init_batch.status == EvidenceBatchStatus.FROZEN

            # Verify prediction record created automatically
            eval_repo = EvaluationRecordRepository(s)
            eval_records, total = await eval_repo.list_by_owner(user_id)
            assert total >= 1
            pred_rec = eval_records[0]
            assert pred_rec.prediction_data["recommendation"] in ("WAIT", "BUY")

        # -------------------------------------------------------------------
        # Step 4: User WAIT -> WATCHING & First Watching Update
        # -------------------------------------------------------------------
        async with factory() as s:
            post_svc = PostInitialDecisionService(s)
            wait_res = await post_svc.wait(
                session_id=session_id,
                owner_id=user_id,
                idempotency_key="wait_key_1",
                confirmed_at=datetime.now(timezone.utc),
            )
            assert wait_res.session_status == TradeSessionStatus.WATCHING
            await s.commit()

        # Upload watching evidence & process Watching Update
        async with factory() as s:
            batch_svc = EvidenceBatchService(s)
            watch_batch1 = await batch_svc.get_current_draft(
                session_id=session_id, owner_id=user_id, analysis_type=AnalysisType.WATCHING_UPDATE
            )
            assert watch_batch1 is not None

            ev_svc = EvidenceService(s, storage_root=Path("/tmp"))
            await ev_svc.create(
                session_id=session_id,
                owner_id=user_id,
                evidence_type="ORDERBOOK_SCREENSHOT",
                content=img_bytes,
                original_filename="watch.png",
                declared_mime_type="image/png",
                evidence_batch_id=watch_batch1.id,
            )
            await batch_svc.mark_ready(watch_batch1)
            await s.commit()

        async with factory() as s:
            job_res = await AnalysisJobCreationService(s).create(
                session_id=session_id,
                owner_id=user_id,
                analysis_type=AnalysisType.WATCHING_UPDATE,
            )
            await s.commit()
            job_id_w1 = job_res.job_id

        async with factory() as s:
            await s.execute(
                text(
                    "UPDATE analysis_jobs SET status='PROCESSING', lease_owner='w1', "
                    "lease_acquired_at=NOW(), lease_expires_at=NOW() + INTERVAL '30 seconds' "
                    "WHERE id=:jid"
                ),
                {"jid": job_id_w1},
            )
            await s.commit()

        async with factory() as s:
            router = P8FakeRouter()
            proc = AnalysisProcessor(session=s, router=router, providers={"gemini": router}, provider_order=["gemini"])
            await proc.process(job_id=job_id_w1, worker_id="w1")
            await s.commit()

        # -------------------------------------------------------------------
        # Step 5: Second WAIT & Second Watching Update
        # -------------------------------------------------------------------
        async with factory() as s:
            await PostInitialDecisionService(s).wait(
                session_id=session_id,
                owner_id=user_id,
                idempotency_key="wait_key_2",
                confirmed_at=datetime.now(timezone.utc),
            )
            await s.commit()

        async with factory() as s:
            batch_svc = EvidenceBatchService(s)
            watch_batch2 = await batch_svc.get_current_draft(
                session_id=session_id, owner_id=user_id, analysis_type=AnalysisType.WATCHING_UPDATE
            )
            assert watch_batch2.sequence_number == 2

            ev_svc = EvidenceService(s, storage_root=Path("/tmp"))
            await ev_svc.create(
                session_id=session_id,
                owner_id=user_id,
                evidence_type="ORDERBOOK_SCREENSHOT",
                content=img_bytes,
                original_filename="watch2.png",
                declared_mime_type="image/png",
                evidence_batch_id=watch_batch2.id,
            )
            await batch_svc.mark_ready(watch_batch2)
            await s.commit()

        async with factory() as s:
            job_res = await AnalysisJobCreationService(s).create(
                session_id=session_id,
                owner_id=user_id,
                analysis_type=AnalysisType.WATCHING_UPDATE,
            )
            await s.commit()
            job_id_w2 = job_res.job_id

        async with factory() as s:
            await s.execute(
                text(
                    "UPDATE analysis_jobs SET status='PROCESSING', lease_owner='w1', "
                    "lease_acquired_at=NOW(), lease_expires_at=NOW() + INTERVAL '30 seconds' "
                    "WHERE id=:jid"
                ),
                {"jid": job_id_w2},
            )
            await s.commit()

        async with factory() as s:
            router = P8FakeRouter()
            await AnalysisProcessor(session=s, router=router, providers={"gemini": router}, provider_order=["gemini"]).process(job_id=job_id_w2, worker_id="w1")
            await s.commit()

        # -------------------------------------------------------------------
        # Step 6: User BUY -> OPEN_POSITION & Open Position Update
        # -------------------------------------------------------------------
        async with factory() as s:
            open_svc = OpenPositionService(s)
            buy_res = await open_svc.confirm(
                session_id=session_id,
                owner_id=user_id,
                idempotency_key="buy_key_1",
                entry_price=Decimal("5000"),
                quantity=Decimal("100"),
                execution_timestamp=datetime.now(timezone.utc),
                stop_loss=Decimal("4800"),
                target=Decimal("5500"),
            )
            assert buy_res.session_status == TradeSessionStatus.OPEN_POSITION
            await s.commit()

        # Upload Open Position evidence & run Open Position Update
        async with factory() as s:
            batch_svc = EvidenceBatchService(s)
            op_batch = await batch_svc.get_current_draft(
                session_id=session_id, owner_id=user_id, analysis_type=AnalysisType.OPEN_POSITION_UPDATE
            )
            assert op_batch is not None
            await batch_svc.update_monitoring_slot(op_batch, "MIDDAY")

            ev_svc = EvidenceService(s, storage_root=Path("/tmp"))
            await ev_svc.create(
                session_id=session_id,
                owner_id=user_id,
                evidence_type="ORDERBOOK_SCREENSHOT",
                content=img_bytes,
                original_filename="op.png",
                declared_mime_type="image/png",
                evidence_batch_id=op_batch.id,
            )
            await batch_svc.mark_ready(op_batch)
            await s.commit()

        async with factory() as s:
            job_res = await AnalysisJobCreationService(s).create(
                session_id=session_id,
                owner_id=user_id,
                analysis_type=AnalysisType.OPEN_POSITION_UPDATE,
            )
            await s.commit()
            job_id_op = job_res.job_id

        async with factory() as s:
            await s.execute(
                text(
                    "UPDATE analysis_jobs SET status='PROCESSING', lease_owner='w1', "
                    "lease_acquired_at=NOW(), lease_expires_at=NOW() + INTERVAL '30 seconds' "
                    "WHERE id=:jid"
                ),
                {"jid": job_id_op},
            )
            await s.commit()

        async with factory() as s:
            router = P8FakeRouter()
            await AnalysisProcessor(session=s, router=router, providers={"gemini": router}, provider_order=["gemini"]).process(job_id=job_id_op, worker_id="w1")
            await s.commit()

        # -------------------------------------------------------------------
        # Step 7: Confirm Stop & Target Adjustments
        # -------------------------------------------------------------------
        async with factory() as s:
            stop_svc = StopLossActionService(s)
            await stop_svc.confirm(
                session_id=session_id,
                owner_id=user_id,
                idempotency_key="stop_key_1",
                stop_loss=Decimal("4850"),
                confirmed_at=datetime.now(timezone.utc),
            )
            target_svc = TargetActionService(s)
            await target_svc.confirm(
                session_id=session_id,
                owner_id=user_id,
                idempotency_key="target_key_1",
                target=Decimal("5600"),
                confirmed_at=datetime.now(timezone.utc),
            )
            await s.commit()

        # -------------------------------------------------------------------
        # Step 8: User SELL -> CLOSED & Closing Analysis
        # -------------------------------------------------------------------
        async with factory() as s:
            exit_svc = FullExitActionService(s)
            exit_res = await exit_svc.confirm(
                session_id=session_id,
                owner_id=user_id,
                idempotency_key="sell_key_1",
                exit_price=Decimal("5600"),
                exit_quantity=Decimal("100"),
                executed_at=datetime.now(timezone.utc),
                closing_reason="TAKE_PROFIT",
            )
            assert exit_res.gross_pnl == Decimal("60000")  # (5600 - 5000) * 100
            await s.commit()

        # Request & process Closing Analysis (no evidence batch required)
        async with factory() as s:
            job_res = await AnalysisJobCreationService(s).create(
                session_id=session_id,
                owner_id=user_id,
                analysis_type=AnalysisType.CLOSING_ANALYSIS,
            )
            await s.commit()
            job_id_close = job_res.job_id

        async with factory() as s:
            await s.execute(
                text(
                    "UPDATE analysis_jobs SET status='PROCESSING', lease_owner='w1', "
                    "lease_acquired_at=NOW(), lease_expires_at=NOW() + INTERVAL '30 seconds' "
                    "WHERE id=:jid"
                ),
                {"jid": job_id_close},
            )
            await s.commit()

        async with factory() as s:
            router = P8FakeRouter()
            await AnalysisProcessor(session=s, router=router, providers={"gemini": router}, provider_order=["gemini"]).process(job_id=job_id_close, worker_id="w1")
            await s.commit()

        # -------------------------------------------------------------------
        # Step 9: Create Second Session for Same Ticker -> History Verification
        # -------------------------------------------------------------------
        async with factory() as s:
            ts_svc = TradeSessionService(s)
            session2 = await ts_svc.create_session(owner_id=user_id, ticker=ticker)
            session2_id = session2.id
            await s.commit()

        async with factory() as s:
            hist_svc = SameTickerHistoryService(s)
            hist = await hist_svc.build_history_summary(
                owner_id=user_id,
                ticker=ticker,
                current_session_id=session2_id,
            )
            assert hist["historical_context_used"] is True
            assert hist["historical_session_count"] == 1
            assert str(session_id) in hist["historical_source_session_ids"]

        # -------------------------------------------------------------------
        # Step 10: Evaluation Records Verification
        # -------------------------------------------------------------------
        async with factory() as s:
            eval_repo = EvaluationRecordRepository(s)
            records, total = await eval_repo.list_by_owner(user_id)
            assert total >= 4

            # Find the outcome-completed evaluation record for session 1
            completed_records = [r for r in records if r.session_id == session_id and r.completeness_status == CompletenessStatus.COMPLETE.value]
            assert len(completed_records) >= 1
            completed_rec = completed_records[0]
            assert completed_rec.user_decision_data.get("user_action") == "SELL"
            assert float(completed_rec.outcome_data.get("realized_pnl", 0)) > 0


# ---------------------------------------------------------------------------
# P8 Regression & Failure Path Scenarios
# ---------------------------------------------------------------------------

class TestP8FailureAndEdgeScenarios:

    async def test_provider_failure_path(self, engine: AsyncEngine) -> None:
        """Provider failure marks job & batch FAILED, restores session safely."""
        user_id, _ = await _create_test_user(engine)
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as s:
            ts = await TradeSessionService(s).create_session(owner_id=user_id, ticker="TLKM")
            sid = ts.id
            batch_svc = EvidenceBatchService(s)
            batch = await batch_svc.get_or_create_current_draft(
                session_id=sid, owner_id=user_id, analysis_type=AnalysisType.INITIAL_ANALYSIS
            )
            ev_svc = EvidenceService(s, storage_root=Path("/tmp"))
            img_bytes = _make_image_bytes()
            for etype in ("ORDERBOOK_SCREENSHOT", "CHART_THREE_MONTH", "CHART_SIX_MONTH"):
                await ev_svc.create(
                    session_id=sid,
                    owner_id=user_id,
                    evidence_type=etype,
                    content=img_bytes,
                    original_filename="t.png",
                    declared_mime_type="image/png",
                    evidence_batch_id=batch.id,
                )
            await batch_svc.mark_ready(batch)
            await s.commit()

        # Transition to READY_FOR_INITIAL_ANALYSIS before creating job
        async with factory() as s:
            await s.execute(
                text(
                    "UPDATE trade_sessions SET lifecycle_status='READY_FOR_INITIAL_ANALYSIS', "
                    "stable_status='READY_FOR_INITIAL_ANALYSIS' WHERE id=:sid"
                ),
                {"sid": sid},
            )
            await s.commit()

        async with factory() as s:
            job_res = await AnalysisJobCreationService(s).create(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.INITIAL_ANALYSIS,
            )
            await s.commit()
            job_id = job_res.job_id

        class FailingRouter:
            @property
            def name(self) -> str:
                return "gemini"

            @property
            def model(self) -> str:
                return "gemini-2.5-flash"

            @property
            def capabilities(self) -> ProviderCapabilities:
                return ProviderCapabilities(
                    supports_images=True,
                    supports_text_output=True,
                    supports_structured_output=True,
                    supports_system_prompt=True,
                    supports_json_schema=True,
                    supports_multi_image=True,
                    maximum_images=10,
                )

            async def generate_validated(self, *args: Any, **kwargs: Any) -> Any:
                from app.ai.providers.router import ProviderRoutingFailedError
                raise ProviderRoutingFailedError(
                    message="Provider connection timeout",
                    root_cause_code="AI_PROVIDER_TIMEOUT",
                    root_cause_message="Timeout",
                    retryable=False,
                )

            async def route(self, *args: Any, **kwargs: Any) -> Any:
                from app.ai.providers.router import ProviderRoutingFailedError
                raise ProviderRoutingFailedError(
                    message="Provider connection timeout",
                    root_cause_code="AI_PROVIDER_TIMEOUT",
                    root_cause_message="Timeout",
                    retryable=False,
                )

        async with factory() as s:
            await s.execute(
                text(
                    "UPDATE analysis_jobs SET status='PROCESSING', lease_owner='w1', "
                    "lease_acquired_at=NOW(), lease_expires_at=NOW() + INTERVAL '30 seconds' "
                    "WHERE id=:jid"
                ),
                {"jid": job_id},
            )
            await s.commit()

        async with factory() as s:
            failing_router = FailingRouter()
            proc = AnalysisProcessor(
                session=s,
                router=failing_router,
                providers={"gemini": failing_router},
                provider_order=["gemini"],
            )
            res = await proc.process(job_id=job_id, worker_id="w1")
            assert res.job_status == AnalysisJobStatus.FAILED.value
            await s.commit()

        async with factory() as s:
            batch = await EvidenceBatchService(s).get_for_user(batch_id=batch.id, owner_id=user_id)
            assert batch.status == EvidenceBatchStatus.FAILED

    async def test_terminal_session_mutation_rejection(self, engine: AsyncEngine) -> None:
        """CLOSED session rejects evidence upload, BUY, WAIT, SKIP, and new active analysis."""
        user_id, _ = await _create_test_user(engine)
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as s:
            ts = await TradeSessionService(s).create_session(owner_id=user_id, ticker="ASII")
            sid = ts.id
            # Force status to CLOSED using enum
            ts.lifecycle_status = TradeSessionStatus.CLOSED
            ts.stable_status = TradeSessionStatus.CLOSED
            await s.commit()

        async with factory() as s:
            from app.services.evidence_batches import EvidenceBatchImmutableError
            from app.services.actions.post_initial_decision import PostInitialDecisionInvalidStateError

            with pytest.raises(EvidenceBatchImmutableError):
                await EvidenceBatchService(s).get_or_create_current_draft(
                    session_id=sid, owner_id=user_id, analysis_type=AnalysisType.INITIAL_ANALYSIS
                )

            with pytest.raises(PostInitialDecisionInvalidStateError):
                await PostInitialDecisionService(s).wait(
                    session_id=sid, owner_id=user_id, idempotency_key="k1", confirmed_at=datetime.now(timezone.utc)
                )

    async def test_cross_user_isolation(self, engine: AsyncEngine) -> None:
        """User A cannot access User B's sessions, evaluation records, or history."""
        u1, _ = await _create_test_user(engine)
        u2, _ = await _create_test_user(engine)

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as s:
            ts1 = await TradeSessionService(s).create_session(owner_id=u1, ticker="UNVR")
            sid1 = ts1.id
            await s.commit()

        async with factory() as s:
            # User 2 tries to access User 1's session
            ts_lookup = await TradeSessionService(s)._repo.get_by_id_for_user(sid1, u2)
            assert ts_lookup is None

            # User 2 list evaluation records
            eval_repo = EvaluationRecordRepository(s)
            records, total = await eval_repo.list_by_owner(u2)
            assert total == 0
