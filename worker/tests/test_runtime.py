import asyncio
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import app
from app.config import WorkerConfig
from app.consumers.analysis_jobs import AnalysisJobConsumer
from app.runtime import (
    _assert_real_validation_factory,
    _build_validation_callback_factory,
    _create_consumer,
    run_worker,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_APP = _REPO_ROOT / "backend" / "app"


def _extend_app_namespace() -> None:
    backend_app = str(_BACKEND_APP)
    if backend_app not in app.__path__:
        app.__path__.append(backend_app)


_extend_app_namespace()


def _make_initial_analysis_payload() -> dict[str, object]:
    import json
    fixture_path = _REPO_ROOT / "schemas" / "fixtures" / "valid" / "v1" / "initial_analysis_v2.valid.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    return payload


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


def test_worker_creates_rebuild_consumer() -> None:
    from app.consumers.rebuild_analysis_requests import RebuildAnalysisRequestConsumer

    consumer = _create_consumer(_FakeFactory(), "worker-1", WorkerConfig())
    assert isinstance(consumer, RebuildAnalysisRequestConsumer)
    assert callable(consumer._processor_factory)


def test_initial_analysis_validator_accepts_valid_payload() -> None:
    _extend_app_namespace()

    from app.validation import UnifiedValidationService

    service = UnifiedValidationService(schema_package_root=str(_REPO_ROOT / "schemas" / "production" / "v1"))
    validate_factory = _build_validation_callback_factory(service)
    validate = validate_factory(
        analysis_type="INITIAL_ANALYSIS",
        session_status_before_job="READY_FOR_ANALYSIS",
        canonical_facts={
            "session_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "ticker": "BBRI",
        },
    )

    is_valid, issues = validate(_make_initial_analysis_payload())
    assert is_valid is True
    assert issues == ()


def test_initial_analysis_validator_returns_concrete_issues_for_invalid_payload() -> None:
    _extend_app_namespace()

    from app.validation import UnifiedValidationService

    service = UnifiedValidationService(schema_package_root=str(_REPO_ROOT / "schemas" / "production" / "v1"))
    validate_factory = _build_validation_callback_factory(service)
    validate = validate_factory(
        analysis_type="INITIAL_ANALYSIS",
        session_status_before_job="READY_FOR_ANALYSIS",
        canonical_facts={
            "session_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "ticker": "BBRI",
        },
    )

    payload = _make_initial_analysis_payload()
    market_facts = payload["market_facts"]
    assert isinstance(market_facts, dict)
    market_facts["high"] = "invalid_string_type"

    is_valid, issues = validate(payload)
    assert is_valid is False
    assert issues
    assert any(issue.message for issue in issues)


def test_initial_analysis_validator_continues_after_schema_errors_only_for_initial_analysis() -> None:
    calls: list[dict[str, object]] = []

    class FakeResult:
        valid = True
        issues: tuple[object, ...] = ()

    class FakeValidationService:
        def validate(self, payload: dict[str, object], **kwargs: object) -> FakeResult:
            calls.append(dict(kwargs))
            return FakeResult()

    validate_factory = _build_validation_callback_factory(FakeValidationService())
    initial_validate = validate_factory(
        analysis_type="INITIAL_ANALYSIS",
        session_status_before_job="READY_FOR_ANALYSIS",
        canonical_facts={},
    )
    watching_validate = validate_factory(
        analysis_type="WATCHING_UPDATE",
        session_status_before_job="WATCHING",
        canonical_facts={},
    )

    initial_validate({"ok": True})
    watching_validate({"ok": True})

    assert calls[0]["continue_on_schema_errors"] is True
    assert calls[1]["continue_on_schema_errors"] is False


def test_placeholder_validator_factory_is_rejected() -> None:
    _extend_app_namespace()

    import app.jobs.processor as processor_module

    with pytest.raises(
        RuntimeError,
        match="placeholder _always_invalid",
    ):
        _assert_real_validation_factory(
            lambda **kwargs: processor_module._always_invalid,
            processor_module._always_invalid,
        )
