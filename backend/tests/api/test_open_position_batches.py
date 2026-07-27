"""Tests for Open Position Update evidence batches, atomicity, stop/target audit, and API endpoints (P4).

PostgreSQL-backed tests — no mocking.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from types import SimpleNamespace
from typing import Any

import pytest
from PIL import Image
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.ai.providers.router import (
    ProviderRouteAttempt,
    ProviderRouter,
    ProviderRoutingFailedError,
    ProviderRoutingResult,
)
from app.jobs import AnalysisProcessor
from app.models.analysis import Analysis
from app.models.analysis_job import AnalysisJob
from app.models.enums import AnalysisJobStatus, AnalysisType, EvidenceBatchStatus, PositionStatus, TradeSessionStatus
from app.models.evidence_batch import EvidenceBatch
from app.models.trade_action import TradeAction
from app.services.actions.open_position import OpenPositionService
from app.services.actions.stop_loss import StopLossActionService
from app.services.actions.target import TargetActionService
from app.services.evidence_batches import EvidenceBatchService
from app.services.evidence import EvidenceService

pytestmark = pytest.mark.database


# ===================================================================
# Helpers
# ===================================================================


def _make_image_bytes() -> bytes:
    img = Image.new("RGB", (50, 50), color="blue")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def _make_user_and_session(
    engine: AsyncEngine,
    status: str = "INITIAL_ANALYZED",
) -> tuple[uuid.UUID, uuid.UUID]:
    async with engine.begin() as conn:
        user = await conn.execute(
            text(
                "INSERT INTO users (email, password_hash) "
                "VALUES (:e, 'hash') RETURNING id"
            ),
            {"e": f"user_{uuid.uuid4().hex[:8]}@example.com"},
        )
        user_id = user.scalar_one()

        session_id = uuid.uuid4()
        stable_st = "OPEN_POSITION" if status in ("ANALYZING", "OPEN_POSITION") else status
        await conn.execute(
            text(
                "INSERT INTO trade_sessions "
                "(id, owner_id, ticker, lifecycle_status, stable_status) "
                "VALUES (:sid, :uid, 'BBRI', :st, :sst)"
            ),
            {"sid": session_id, "uid": user_id, "st": status, "sst": stable_st},
        )
        pos_st = "OPEN" if status == "OPEN_POSITION" or status == "ANALYZING" else "NOT_OPENED"
        await conn.execute(
            text(
                "INSERT INTO trade_states "
                "(session_id, position_status, entry_price, entry_at, original_quantity, remaining_quantity) "
                "VALUES (:sid, :pst, 5000, :eat, 100, 100)"
            ),
            {
                "sid": session_id,
                "pst": pos_st,
                "eat": datetime.now(timezone.utc) if pos_st == "OPEN" else None,
            },
        )
    return user_id, session_id


async def _make_open_position_session(engine: AsyncEngine) -> tuple[uuid.UUID, uuid.UUID]:
    user_id, session_id = await _make_user_and_session(engine, "INITIAL_ANALYZED")
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        svc = OpenPositionService(s)
        await svc.confirm(
            session_id=session_id,
            owner_id=user_id,
            idempotency_key=f"buy_{uuid.uuid4().hex}",
            entry_price="5000",
            quantity="100",
            execution_timestamp=datetime.now(timezone.utc),
        )
        await s.commit()
    return user_id, session_id


class FakeRouter(ProviderRouter):
    def __init__(self, result: ProviderRoutingResult | Exception | None = None) -> None:
        self.result = result

    async def generate_validated(self, **kwargs: Any) -> Any:
        if isinstance(self.result, Exception):
            raise self.result
        if self.result is not None:
            return self.result
        return ProviderRoutingResult(
            provider="gemini",
            response=SimpleNamespace(provider="gemini", model="g-model", raw_output="{}"),
            payload={"ok": True},
            attempts=(ProviderRouteAttempt(sequence=1, provider="gemini", phase="PRIMARY"),),
            fallback_used=False,
        )


class FakeOPUContextBuilder:
    async def build(self, **kwargs: Any) -> Any:
        return SimpleNamespace(
            session_id=kwargs["session_id"],
            analysis_type="OPEN_POSITION_UPDATE",
            prompt_version="1.0.0",
            system_prompt="OPU system prompt",
            user_prompt="OPU user prompt",
            expected_schema_name="open_position_update",
            expected_schema_version="1.0.0",
            structured_output_schema={},
            canonical_facts={},
            images=(),
            metadata={"session_id": str(kwargs["session_id"])},
        )


def _always_valid(payload: dict[str, object]) -> tuple[bool, tuple[Any, ...]]:
    return True, ()


# ===================================================================
# Tests
# ===================================================================


class TestOpenPositionBatchLifecycle:
    async def test_buy_creates_opu_draft_batch(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_user_and_session(engine, "INITIAL_ANALYZED")
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as db_session:
            svc = OpenPositionService(db_session)
            res = await svc.confirm(
                session_id=session_id,
                owner_id=user_id,
                idempotency_key=f"buy_{uuid.uuid4().hex}",
                entry_price="5000",
                quantity="100",
                execution_timestamp=datetime.now(timezone.utc),
            )
            assert res.session_status == TradeSessionStatus.OPEN_POSITION

            batch_svc = EvidenceBatchService(db_session)
            draft = await batch_svc.get_current_draft(
                session_id=session_id,
                owner_id=user_id,
                analysis_type=AnalysisType.OPEN_POSITION_UPDATE,
            )
            assert draft is not None
            assert draft.status == EvidenceBatchStatus.DRAFT
            assert draft.analysis_type == AnalysisType.OPEN_POSITION_UPDATE
            assert draft.monitoring_slot == "UNSPECIFIED"

    async def test_update_monitoring_slot(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_user_and_session(engine, "OPEN_POSITION")
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as db_session:
            batch_svc = EvidenceBatchService(db_session)
            batch = await batch_svc.get_or_create_current_draft(
                session_id=session_id,
                owner_id=user_id,
                analysis_type=AnalysisType.OPEN_POSITION_UPDATE,
            )
            assert batch.monitoring_slot == "UNSPECIFIED"

            updated = await batch_svc.update_monitoring_slot(batch, "MORNING")
            assert updated.monitoring_slot == "MORNING"

            updated_midday = await batch_svc.update_monitoring_slot(batch, "MIDDAY")
            assert updated_midday.monitoring_slot == "MIDDAY"

    async def test_opu_requires_orderbook(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_user_and_session(engine, "OPEN_POSITION")
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as db_session:
            batch_svc = EvidenceBatchService(db_session)
            batch = await batch_svc.get_or_create_current_draft(
                session_id=session_id,
                owner_id=user_id,
                analysis_type=AnalysisType.OPEN_POSITION_UPDATE,
            )

            evidence_svc = EvidenceService(db_session)
            required = await evidence_svc.get_required_evidence(
                session_id=session_id,
                owner_id=user_id,
                analysis_type=AnalysisType.OPEN_POSITION_UPDATE,
                evidence_batch_id=batch.id,
            )
            assert not required.complete
            assert len(required.missing_types) == 1

    async def test_opu_ready_with_orderbook(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_user_and_session(engine, "OPEN_POSITION")
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as db_session:
            batch_svc = EvidenceBatchService(db_session)
            batch = await batch_svc.get_or_create_current_draft(
                session_id=session_id,
                owner_id=user_id,
                analysis_type=AnalysisType.OPEN_POSITION_UPDATE,
            )

            evidence_svc = EvidenceService(db_session)
            await evidence_svc.create(
                session_id=session_id,
                owner_id=user_id,
                evidence_type="ORDERBOOK_SCREENSHOT",
                content=_make_image_bytes(),
                original_filename="ob.png",
                declared_mime_type="image/png",
                evidence_batch_id=batch.id,
            )

            required = await evidence_svc.get_required_evidence(
                session_id=session_id,
                owner_id=user_id,
                analysis_type=AnalysisType.OPEN_POSITION_UPDATE,
                evidence_batch_id=batch.id,
            )
            assert required.complete

            await batch_svc.mark_ready(batch)
            assert batch.status == EvidenceBatchStatus.READY


class TestOpenPositionUpdateAtomicity:
    async def test_analysis_persistence_rollback_on_batch_freeze_failure(
        self,
        engine: AsyncEngine,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        user_id, session_id = await _make_open_position_session(engine)
        job_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        async with engine.begin() as conn:
            batch_res = await conn.execute(
                text("SELECT id FROM evidence_batches WHERE session_id = :sid AND analysis_type = 'OPEN_POSITION_UPDATE'"),
                {"sid": session_id},
            )
            batch_id = batch_res.scalar_one()
            await conn.execute(
                text("UPDATE evidence_batches SET status = 'PROCESSING' WHERE id = :bid"),
                {"bid": batch_id},
            )
            await conn.execute(
                text("UPDATE trade_sessions SET lifecycle_status = 'ANALYZING' WHERE id = :sid"),
                {"sid": session_id},
            )
            await conn.execute(
                text(
                    "INSERT INTO analysis_jobs (id, session_id, evidence_batch_id, analysis_type, status, previous_session_status, attempt_count, max_attempts, requested_at, available_at, lease_owner, lease_expires_at) "
                    "VALUES (:jid, :sid, :bid, 'OPEN_POSITION_UPDATE', 'PROCESSING', 'OPEN_POSITION', 0, 1, :now, :now, 'w1', :exp)"
                ),
                {"jid": job_id, "sid": session_id, "bid": batch_id, "now": now, "exp": now + timedelta(seconds=60)},
            )

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async def _failing_freeze(self: Any, batch_id: Any, *, now: Any = None) -> None:
            raise RuntimeError("Simulated batch freeze storage failure")

        monkeypatch.setattr(EvidenceBatchService, "freeze", _failing_freeze)

        async with factory() as db_session:
            proc = AnalysisProcessor(
                session=db_session,
                context_builder=FakeOPUContextBuilder(),
                router=FakeRouter(),
                validate=_always_valid,
            )
            with pytest.raises(RuntimeError, match="Simulated batch freeze storage failure"):
                await proc.process(job_id=job_id, worker_id="w1")
            await db_session.rollback()

        # Verify atomic rollback
        async with factory() as db_session:
            analysis_count = (
                await db_session.execute(
                    text("SELECT COUNT(*) FROM analyses WHERE session_id = :sid"),
                    {"sid": session_id},
                )
            ).scalar_one()
            assert analysis_count == 0

            batch = await db_session.get(EvidenceBatch, batch_id)
            assert batch is not None
            assert batch.status == EvidenceBatchStatus.PROCESSING  # Not frozen

    async def test_successful_opu_restores_open_position_status(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_open_position_session(engine)
        job_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        async with engine.begin() as conn:
            batch_res = await conn.execute(
                text("SELECT id FROM evidence_batches WHERE session_id = :sid AND analysis_type = 'OPEN_POSITION_UPDATE'"),
                {"sid": session_id},
            )
            batch_id = batch_res.scalar_one()
            await conn.execute(
                text("UPDATE evidence_batches SET status = 'PROCESSING' WHERE id = :bid"),
                {"bid": batch_id},
            )
            await conn.execute(
                text("UPDATE trade_sessions SET lifecycle_status = 'ANALYZING' WHERE id = :sid"),
                {"sid": session_id},
            )
            await conn.execute(
                text(
                    "INSERT INTO analysis_jobs (id, session_id, evidence_batch_id, analysis_type, status, previous_session_status, attempt_count, max_attempts, requested_at, available_at, lease_owner, lease_expires_at) "
                    "VALUES (:jid, :sid, :bid, 'OPEN_POSITION_UPDATE', 'PROCESSING', 'OPEN_POSITION', 0, 1, :now, :now, 'w1', :exp)"
                ),
                {"jid": job_id, "sid": session_id, "bid": batch_id, "now": now, "exp": now + timedelta(seconds=60)},
            )

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as db_session:
            proc = AnalysisProcessor(
                session=db_session,
                context_builder=FakeOPUContextBuilder(),
                router=FakeRouter(),
                validate=_always_valid,
            )
            res = await proc.process(job_id=job_id, worker_id="w1")
            assert res.job_status == "COMPLETED"
            assert res.restored_session_status == "OPEN_POSITION"

            batch = await db_session.get(EvidenceBatch, batch_id)
            assert batch is not None
            assert batch.status == EvidenceBatchStatus.FROZEN

    async def test_terminal_failure_marks_batch_failed(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_open_position_session(engine)
        job_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        async with engine.begin() as conn:
            batch_res = await conn.execute(
                text("SELECT id FROM evidence_batches WHERE session_id = :sid AND analysis_type = 'OPEN_POSITION_UPDATE'"),
                {"sid": session_id},
            )
            batch_id = batch_res.scalar_one()
            await conn.execute(
                text("UPDATE evidence_batches SET status = 'PROCESSING' WHERE id = :bid"),
                {"bid": batch_id},
            )
            await conn.execute(
                text("UPDATE trade_sessions SET lifecycle_status = 'ANALYZING' WHERE id = :sid"),
                {"sid": session_id},
            )
            await conn.execute(
                text(
                    "INSERT INTO analysis_jobs (id, session_id, evidence_batch_id, analysis_type, status, previous_session_status, attempt_count, max_attempts, requested_at, available_at, lease_owner, lease_expires_at) "
                    "VALUES (:jid, :sid, :bid, 'OPEN_POSITION_UPDATE', 'PROCESSING', 'OPEN_POSITION', 0, 1, :now, :now, 'w1', :exp)"
                ),
                {"jid": job_id, "sid": session_id, "bid": batch_id, "now": now, "exp": now + timedelta(seconds=60)},
            )

        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as db_session:
            failing_router = FakeRouter(
                result=ProviderRoutingFailedError("Routing failed", root_cause_code="AI_TIMEOUT")
            )
            proc = AnalysisProcessor(
                session=db_session,
                context_builder=FakeOPUContextBuilder(),
                router=failing_router,
                validate=_always_valid,
            )
            res = await proc.process(job_id=job_id, worker_id="w1")
            assert res.job_status == "FAILED"
            assert res.restored_session_status == "OPEN_POSITION"

            batch = await db_session.get(EvidenceBatch, batch_id)
            assert batch is not None
            assert batch.status == EvidenceBatchStatus.FAILED


class TestStopTargetAudit:
    async def test_stop_loss_audit_record(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_open_position_session(engine)
        source_analysis_id = uuid.uuid4()
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as db_session:
            svc = StopLossActionService(db_session)
            res = await svc.confirm(
                session_id=session_id,
                owner_id=user_id,
                idempotency_key=f"stop_{uuid.uuid4().hex}",
                stop_loss="4800",
                confirmed_at=datetime.now(timezone.utc),
                note="Trailing stop raise",
                source_analysis_id=source_analysis_id,
            )
            assert res.active_stop_loss == 4800

            action = await db_session.get(TradeAction, res.action.id)
            assert action is not None
            assert action.session_id == session_id
            assert action.note == "Trailing stop raise"
            assert action.payload.get("source_analysis_id") == str(source_analysis_id)
            assert action.payload.get("previous_stop") is None

    async def test_target_audit_record(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_open_position_session(engine)
        source_analysis_id = uuid.uuid4()
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as db_session:
            svc = TargetActionService(db_session)
            res = await svc.confirm(
                session_id=session_id,
                owner_id=user_id,
                idempotency_key=f"target_{uuid.uuid4().hex}",
                target="5500",
                confirmed_at=datetime.now(timezone.utc),
                note="Target extension",
                source_analysis_id=source_analysis_id,
            )
            assert res.active_target == 5500

            action = await db_session.get(TradeAction, res.action.id)
            assert action is not None
            assert action.session_id == session_id
            assert action.note == "Target extension"
            assert action.payload.get("source_analysis_id") == str(source_analysis_id)
            assert action.payload.get("previous_target") is None
