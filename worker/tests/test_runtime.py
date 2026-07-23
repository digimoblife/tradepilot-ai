import asyncio
from typing import Any

import pytest

from app.config import WorkerConfig
from app.consumers.analysis_jobs import AnalysisJobConsumer
from app.runtime import run_worker


def _skip_startup_validation(config: WorkerConfig) -> None:
    return None


class _FakeSession:
    async def __aenter__(self) -> Any:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        import uuid
        from dataclasses import dataclass

        @dataclass
        class _R:
            def scalar_one(self) -> Any:
                return uuid.uuid4()

            def scalar_one_or_none(self) -> Any:
                return None

            def unique(self) -> Any:
                return self

            def first(self) -> Any:
                return None

        return _R()


class _FakeFactory:
    def __call__(self) -> _FakeSession:
        return _FakeSession()


class _FakeQ:
    def __init__(self, session: Any = None) -> None:
        pass

    async def claim_next(self, **kwargs: Any) -> None:
        return None


class _FakeP:
    def __init__(self, session: Any = None) -> None:
        pass

    async def process(self, **kwargs: Any) -> Any:
        import uuid
        from dataclasses import dataclass

        @dataclass
        class _Result:
            job_id: Any = uuid.uuid4()
            job_status: str = "COMPLETED"

        return _Result()


@pytest.fixture
def fake_consumer() -> AnalysisJobConsumer:
    return AnalysisJobConsumer(
        session_factory=_FakeFactory(),
        queue=_FakeQ,
        processor=_FakeP,
        worker_id="test-worker",
    )


class _FakeHb:
    def __init__(self, session: Any = None, worker_id: str = "") -> None:
        pass

    async def initialize(self) -> None:
        pass

    async def refresh(self) -> None:
        pass

    async def finalize(self, status: str = "STOPPED") -> None:
        pass


@pytest.mark.asyncio
async def test_runtime_starts_and_stops_on_shutdown_event(fake_consumer: Any) -> None:
    config = WorkerConfig(worker_poll_interval_seconds=1, worker_name="test-worker")
    shutdown_event = asyncio.Event()

    async def trigger_shutdown() -> None:
        await asyncio.sleep(0.05)
        shutdown_event.set()

    await asyncio.gather(
        run_worker(
            config,
            shutdown_event,
            session_factory=_FakeFactory(),
            consumer=fake_consumer,
            heartbeat=_FakeHb(),
            startup_validator=_skip_startup_validation,
        ),
        trigger_shutdown(),
    )


@pytest.mark.asyncio
async def test_runtime_does_not_require_database(fake_consumer: Any) -> None:
    config = WorkerConfig(worker_poll_interval_seconds=1, worker_name="test-worker")
    shutdown_event = asyncio.Event()
    shutdown_event.set()
    await run_worker(
        config,
        shutdown_event,
        session_factory=_FakeFactory(),
        consumer=fake_consumer,
        heartbeat=_FakeHb(),
        startup_validator=_skip_startup_validation,
    )


@pytest.mark.asyncio
async def test_runtime_exits_immediately_when_shutdown_is_set(fake_consumer: Any) -> None:
    config = WorkerConfig(worker_poll_interval_seconds=3600, worker_name="test-worker")
    shutdown_event = asyncio.Event()
    shutdown_event.set()
    await asyncio.wait_for(
        run_worker(
            config,
            shutdown_event,
            session_factory=_FakeFactory(),
            consumer=fake_consumer,
            heartbeat=_FakeHb(),
            startup_validator=_skip_startup_validation,
        ),
        timeout=1.0,
    )


@pytest.mark.asyncio
async def test_runtime_idle_cycle_does_not_busy_spin(fake_consumer: Any) -> None:
    config = WorkerConfig(worker_poll_interval_seconds=1, worker_name="test-worker")
    shutdown_event = asyncio.Event()
    shutdown_event.set()
    start = asyncio.get_event_loop().time()
    await run_worker(
        config,
        shutdown_event,
        session_factory=_FakeFactory(),
        consumer=fake_consumer,
        heartbeat=_FakeHb(),
        startup_validator=_skip_startup_validation,
    )
    elapsed = asyncio.get_event_loop().time() - start
    assert elapsed < 0.5, f"Runtime took {elapsed:.3f}s — may have busy-spin"


@pytest.mark.asyncio
async def test_startup_validation_runs_before_heartbeat_and_claim(fake_consumer: Any) -> None:
    config = WorkerConfig(worker_poll_interval_seconds=1, worker_name="test-worker")
    shutdown_event = asyncio.Event()
    hb = _FakeHb()

    class _StartupError(RuntimeError):
        pass

    def fail_startup(config: WorkerConfig) -> None:
        raise _StartupError("missing prompts")

    with pytest.raises(_StartupError, match="missing prompts"):
        await run_worker(
            config,
            shutdown_event,
            session_factory=_FakeFactory(),
            consumer=fake_consumer,
            heartbeat=hb,
            startup_validator=fail_startup,
        )
