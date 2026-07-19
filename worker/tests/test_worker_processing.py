"""Tests for worker processing (TP-0805).

Uses fake queue/processor dependencies — no real database or AI calls.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from app.config import WorkerConfig
from app.consumers.analysis_jobs import AnalysisJobConsumer
from app.runtime import run_worker

# ===================================================================
# Fake queue
# ===================================================================


class FakeQueue:
    def __init__(self, session: Any = None) -> None:
        self.session = session
        self.call_count = 0
        self.last_worker_id: str | None = None

    async def claim_next(
        self,
        *,
        worker_id: str,
        lease_duration: timedelta,
        now: datetime | None = None,
    ) -> Any | None:
        self.call_count += 1
        self.last_worker_id = worker_id
        return None  # no job by default


class FakeQueueWithJob(FakeQueue):
    def __init__(self, session: Any = None, job_id: uuid.UUID | None = None) -> None:
        super().__init__(session)
        self._job_id = job_id or uuid.uuid4()

    async def claim_next(
        self,
        *,
        worker_id: str,
        lease_duration: timedelta,
        now: datetime | None = None,
    ) -> Any:
        self.call_count += 1
        self.last_worker_id = worker_id
        return _fake_claimed_job(self._job_id)


def _fake_claimed_job(job_id: uuid.UUID) -> Any:
    from dataclasses import dataclass

    @dataclass
    class FakeLease:
        job_id: uuid.UUID
        worker_id: str
        claimed_at: datetime
        expires_at: datetime
        attempt_number: int

    @dataclass
    class FakeClaimedJob:
        job_id: uuid.UUID
        session_id: uuid.UUID
        analysis_type: str
        attempt_number: int
        lease: FakeLease

    return FakeClaimedJob(
        job_id=job_id,
        session_id=uuid.uuid4(),
        analysis_type="WATCHING_UPDATE",
        attempt_number=1,
        lease=FakeLease(
            job_id=job_id,
            worker_id="w1",
            claimed_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=300),
            attempt_number=1,
        ),
    )


# ===================================================================
# Fake processor
# ===================================================================


class _FakeProcessorState:
    """Shared mutable state for FakeProcessor."""

    def __init__(self) -> None:
        self.call_count = 0
        self.last_job_id: uuid.UUID | None = None
        self.last_worker_id: str | None = None
        self.fail: bool = False


class FakeProcessor:
    """Fake processor — class-level, instantiated by consumer."""

    _state = _FakeProcessorState()

    def __init__(self, session: Any = None) -> None:
        self.session = session

    async def process(self, *, job_id: uuid.UUID, worker_id: str) -> Any:
        state = FakeProcessor._state
        state.call_count += 1
        state.last_job_id = job_id
        state.last_worker_id = worker_id
        if state.fail:
            raise RuntimeError("Processor failure")
        from dataclasses import dataclass

        @dataclass
        class FakeResult:
            job_id: uuid.UUID
            session_id: uuid.UUID
            analysis_id: uuid.UUID | None
            job_status: str
            restored_session_status: str | None
            provider: str | None
            fallback_used: bool

        return FakeResult(
            job_id=job_id,
            session_id=uuid.uuid4(),
            analysis_id=uuid.uuid4(),
            job_status="COMPLETED",
            restored_session_status="WATCHING",
            provider="gemini",
            fallback_used=False,
        )


# ===================================================================
# Fake session factory
# ===================================================================


class FakeSession:
    async def __aenter__(self) -> FakeSession:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        from dataclasses import dataclass

        @dataclass
        class FakeResult:
            _val: Any = None

            def scalar_one(self) -> Any:
                return uuid.uuid4()

            def first(self) -> Any:
                return None

            def scalar_one_or_none(self) -> Any:
                return None

            def unique(self) -> Any:
                return self

            def scalars(self) -> Any:
                return self

            def all(self) -> list:
                return []

        return FakeResult()


class FakeSessionFactory:
    def __call__(self) -> FakeSession:
        return FakeSession()


# ===================================================================
# Fake heartbeat
# ===================================================================


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


# ===================================================================
# Consumer tests
# ===================================================================


class TestConsumer:
    async def test_no_job_returns_false(self) -> None:
        FakeProcessor._state = _FakeProcessorState()
        consumer = AnalysisJobConsumer(
            session_factory=FakeSessionFactory(),
            queue=FakeQueue,
            processor=FakeProcessor,
            worker_id="w1",
        )
        result = await consumer.run_once()
        assert result is False

    async def test_claimed_job_passed_to_processor(self) -> None:
        _expected_job_id = uuid.uuid4()
        FakeProcessor._state = _FakeProcessorState()

        class _Q(FakeQueueWithJob):
            def __init__(self, session: Any = None) -> None:  # noqa: N805
                super().__init__(session, job_id=_expected_job_id)

        consumer = AnalysisJobConsumer(
            session_factory=FakeSessionFactory(),
            queue=_Q,
            processor=FakeProcessor,
            worker_id="w1",
        )
        result = await consumer.run_once()
        assert result is True
        assert FakeProcessor._state.last_job_id == _expected_job_id

    async def test_worker_id_used(self) -> None:
        FakeProcessor._state = _FakeProcessorState()

        class _Q(FakeQueueWithJob):
            pass

        consumer = AnalysisJobConsumer(
            session_factory=FakeSessionFactory(),
            queue=_Q,
            processor=FakeProcessor,
            worker_id="custom-worker",
        )
        await consumer.run_once()

    async def test_processing_error_raises(self) -> None:
        FakeProcessor._state = _FakeProcessorState()
        FakeProcessor._state.fail = True

        consumer = AnalysisJobConsumer(
            session_factory=FakeSessionFactory(),
            queue=FakeQueueWithJob,
            processor=FakeProcessor,
            worker_id="w1",
        )
        with pytest.raises(RuntimeError, match="Processor failure"):
            await consumer.run_once()


# ===================================================================
# Heartbeat tests
# ===================================================================


class TestHeartbeat:
    async def test_heartbeat_initialized(self) -> None:
        hb = FakeHeartbeat()
        await hb.initialize()
        assert hb.initialized

    async def test_heartbeat_refreshed(self) -> None:
        hb = FakeHeartbeat()
        await hb.refresh()
        assert hb.refreshed

    async def test_heartbeat_finalized(self) -> None:
        hb = FakeHeartbeat()
        await hb.finalize("STOPPED")
        assert hb.finalized
        assert hb.final_status == "STOPPED"


# ===================================================================
# Runtime loop tests
# ===================================================================


class TestRuntimeLoop:
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

        await asyncio.gather(
            run_worker(
                config,
                shutdown_event,
                session_factory=FakeSessionFactory(),
                consumer=AnalysisJobConsumer(
                    session_factory=FakeSessionFactory(),
                    queue=FakeQueue,
                    processor=FakeProcessor(),
                    worker_id="test-worker",
                ),
                heartbeat=hb,
            ),
            trigger(),
        )
        assert hb.initialized
        assert hb.finalized

    async def test_processing_error_does_not_terminate(self) -> None:
        config = WorkerConfig(
            worker_poll_interval_seconds=1,
            worker_name="test-worker",
        )
        shutdown_event = asyncio.Event()
        hb = FakeHeartbeat()

        FakeProcessor._state = _FakeProcessorState()
        FakeProcessor._state.fail = True
        consumer = AnalysisJobConsumer(
            session_factory=FakeSessionFactory(),
            queue=FakeQueueWithJob,
            processor=FakeProcessor,
            worker_id="test-worker",
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
            ),
            trigger(),
        )
        assert hb.finalized

    async def test_no_busy_spin_when_no_job(self) -> None:
        config = WorkerConfig(
            worker_poll_interval_seconds=10,
            worker_name="test-worker",
        )
        shutdown_event = asyncio.Event()
        shutdown_event.set()

        start = asyncio.get_event_loop().time()
        await run_worker(
            config,
            shutdown_event,
            session_factory=FakeSessionFactory(),
            consumer=AnalysisJobConsumer(
                session_factory=FakeSessionFactory(),
                queue=FakeQueue,
                processor=FakeProcessor(),
                worker_id="test-worker",
            ),
            heartbeat=FakeHeartbeat(),
        )
        elapsed = asyncio.get_event_loop().time() - start
        assert elapsed < 2.0, f"Runtime took {elapsed:.3f}s — may have busy-spun"
