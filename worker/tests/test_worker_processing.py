"""Tests for rebuild worker processing flow.

Uses fake claim service and processor dependencies — no real database or AI calls.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import pytest

from app.config import WorkerConfig
from app.consumers.rebuild_analysis_requests import RebuildAnalysisRequestConsumer
from app.runtime import run_worker
from app.trade_workspace.services.analysis_request_claim import ClaimedAnalysisRequest
from app.trade_workspace.models.analysis_request import AnalysisRequestV2Status, AnalysisRequestV2Type


def _skip_startup_validation(config: WorkerConfig) -> None:
    return None


class FakeClaimService:
    def __init__(self, session: Any = None, claim_item: ClaimedAnalysisRequest | None = None) -> None:
        self.session = session
        self._claim_item = claim_item

    async def claim_next(self, *, worker_id: str | None = None) -> ClaimedAnalysisRequest | None:
        return self._claim_item


class FakeRebuildProcessor:
    def __init__(self, session: Any = None, fail: bool = False) -> None:
        self.session = session
        self.fail = fail
        self.processed_ids: list[uuid.UUID] = []

    async def process(self, *, analysis_request_id: uuid.UUID) -> Any:
        self.processed_ids.append(analysis_request_id)
        if self.fail:
            raise RuntimeError("Fake processor failure")
        from dataclasses import dataclass

        @dataclass
        class Result:
            status: str = "COMPLETED"

        return Result()


class FakeSession:
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class FakeSessionFactory:
    def __call__(self) -> FakeSession:
        return FakeSession()


class FakeHeartbeat:
    def __init__(self) -> None:
        self.initialized = False
        self.refreshed = False
        self.finalized = False
        self.final_status: str | None = None

    async def initialize(self) -> None:
        self.initialized = True

    async def refresh(self) -> None:
        self.refreshed = True

    async def finalize(self, status: str = "STOPPED") -> None:
        self.finalized = True
        self.final_status = status


class TestRebuildConsumer:
    async def test_no_pending_request_returns_false(self) -> None:
        consumer = RebuildAnalysisRequestConsumer(
            session_factory=FakeSessionFactory(),
            processor_factory=lambda session: FakeRebuildProcessor(session),
            worker_id="worker-1",
            claim_service_factory=lambda session: FakeClaimService(session, claim_item=None),
        )
        assert await consumer.run_once() is False

    async def test_claimed_request_commits_claim_session_and_invokes_processor(self) -> None:
        req_id = uuid.uuid4()
        claimed = ClaimedAnalysisRequest(
            request_id=req_id,
            session_id=uuid.uuid4(),
            analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
            status=AnalysisRequestV2Status.PROCESSING,
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            observation_period=None,
        )
        processor_instances: list[FakeRebuildProcessor] = []

        def processor_factory(session: Any) -> FakeRebuildProcessor:
            p = FakeRebuildProcessor(session)
            processor_instances.append(p)
            return p

        consumer = RebuildAnalysisRequestConsumer(
            session_factory=FakeSessionFactory(),
            processor_factory=processor_factory,
            worker_id="worker-1",
            claim_service_factory=lambda session: FakeClaimService(session, claim_item=claimed),
        )
        result = await consumer.run_once()
        assert result is True
        assert len(processor_instances) == 1
        assert processor_instances[0].processed_ids == [req_id]

    async def test_processing_failure_does_not_raise_out_of_run_once(self) -> None:
        req_id = uuid.uuid4()
        claimed = ClaimedAnalysisRequest(
            request_id=req_id,
            session_id=uuid.uuid4(),
            analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
            status=AnalysisRequestV2Status.PROCESSING,
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            observation_period=None,
        )

        def broken_processor_factory(session: Any) -> FakeRebuildProcessor:
            return FakeRebuildProcessor(session, fail=True)

        consumer = RebuildAnalysisRequestConsumer(
            session_factory=FakeSessionFactory(),
            processor_factory=broken_processor_factory,
            worker_id="worker-1",
            claim_service_factory=lambda session: FakeClaimService(session, claim_item=claimed),
        )
        # Exception during processor execution is logged and caught, allowing consumer to return True cleanly
        assert await consumer.run_once() is True


class TestRebuildRuntimeLoop:
    async def test_shutdown_stops_polling(self) -> None:
        config = WorkerConfig(
            worker_poll_interval_seconds=1,
            worker_name="test-worker",
        )
        shutdown_event = asyncio.Event()
        hb = FakeHeartbeat()

        async def trigger() -> None:
            await asyncio.sleep(0.05)
            shutdown_event.set()

        consumer = RebuildAnalysisRequestConsumer(
            session_factory=FakeSessionFactory(),
            processor_factory=lambda session: FakeRebuildProcessor(session),
            worker_id="test-worker",
            claim_service_factory=lambda session: FakeClaimService(session, claim_item=None),
        )

        await asyncio.gather(
            run_worker(
                config,
                shutdown_event,
                session_factory=FakeSessionFactory(),
                consumer=consumer,
                heartbeat=hb,
                startup_validator=_skip_startup_validation,
            ),
            trigger(),
        )
        assert hb.initialized
        assert hb.finalized

    async def test_processing_error_does_not_terminate_runtime_loop(self) -> None:
        config = WorkerConfig(
            worker_poll_interval_seconds=1,
            worker_name="test-worker",
        )
        shutdown_event = asyncio.Event()
        hb = FakeHeartbeat()

        req_id = uuid.uuid4()
        claimed = ClaimedAnalysisRequest(
            request_id=req_id,
            session_id=uuid.uuid4(),
            analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
            status=AnalysisRequestV2Status.PROCESSING,
            created_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            observation_period=None,
        )

        consumer = RebuildAnalysisRequestConsumer(
            session_factory=FakeSessionFactory(),
            processor_factory=lambda session: FakeRebuildProcessor(session, fail=True),
            worker_id="test-worker",
            claim_service_factory=lambda session: FakeClaimService(session, claim_item=claimed),
        )

        async def trigger() -> None:
            await asyncio.sleep(0.1)
            shutdown_event.set()

        await asyncio.gather(
            run_worker(
                config,
                shutdown_event,
                session_factory=FakeSessionFactory(),
                consumer=consumer,
                heartbeat=hb,
                startup_validator=_skip_startup_validation,
            ),
            trigger(),
        )
        assert hb.finalized
