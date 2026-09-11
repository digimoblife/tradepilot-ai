from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

import app
from app.config import WorkerConfig
from app.runtime import run_worker
from app.startup_validation import (
    WorkerStartupValidationError,
    validate_worker_startup,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_APP = _REPO_ROOT / "backend" / "app"


def _extend_app_namespace() -> None:
    backend_app = str(_BACKEND_APP)
    if backend_app not in app.__path__:
        app.__path__.append(backend_app)


_extend_app_namespace()


class _FakeConsumer:
    async def run_once(self) -> None:
        pass


class _FakeHb:
    async def initialize(self) -> None:
        pass

    async def refresh(self) -> None:
        pass

    async def finalize(self, status: str = "STOPPED") -> None:
        pass


class _FakeFactory:
    def __call__(self) -> object:
        return self

    async def __aenter__(self) -> object:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


def test_valid_v2_startup_configuration_passes() -> None:
    """1. Valid V2 startup configuration passes."""
    config = WorkerConfig(
        gemini_model="gemini-3.5-flash-lite",
        gemini_api_key="valid-key",
        app_env="development",
    )
    validate_worker_startup(config)


def test_missing_v2_prompt_fails(tmp_path: Path) -> None:
    """2. Missing V2 prompt fails."""
    config = WorkerConfig(gemini_model="gemini-3.5-flash-lite")
    with pytest.raises(WorkerStartupValidationError, match="Prompt rebuild produksi wajib"):
        validate_worker_startup(config, prompts_root=tmp_path)


def test_corrupt_v2_prompt_fails(tmp_path: Path) -> None:
    """3. Corrupt/unreadable V2 prompt fails (e.g. empty prompt file)."""
    (tmp_path / "initial_analysis.md").write_text("", encoding="utf-8")
    (tmp_path / "wait_update.md").write_text("valid", encoding="utf-8")
    (tmp_path / "position_update.md").write_text("valid", encoding="utf-8")
    config = WorkerConfig(gemini_model="gemini-3.5-flash-lite")
    with pytest.raises(WorkerStartupValidationError, match="Prompt rebuild produksi wajib"):
        validate_worker_startup(config, prompts_root=tmp_path)


def test_missing_v2_schema_fails(tmp_path: Path) -> None:
    """4. Missing V2 schema fails."""
    config = WorkerConfig(gemini_model="gemini-3.5-flash-lite")
    with pytest.raises(WorkerStartupValidationError, match="Schema rebuild produksi wajib"):
        validate_worker_startup(config, schemas_root=tmp_path)


def test_malformed_v2_schema_fails(tmp_path: Path) -> None:
    """5. Malformed V2 schema fails (invalid json or not a mapping)."""
    (tmp_path / "initial_analysis.schema.json").write_text("{not valid json", encoding="utf-8")
    (tmp_path / "wait_update.schema.json").write_text("{}", encoding="utf-8")
    (tmp_path / "position_update.schema.json").write_text("{}", encoding="utf-8")
    config = WorkerConfig(gemini_model="gemini-3.5-flash-lite")
    with pytest.raises(WorkerStartupValidationError, match="Schema rebuild produksi wajib"):
        validate_worker_startup(config, schemas_root=tmp_path)


def test_missing_gemini_model_fails() -> None:
    """6. Missing Gemini model fails."""
    config = WorkerConfig(gemini_model="")
    with pytest.raises(WorkerStartupValidationError, match="Gemini model is not configured"):
        validate_worker_startup(config)


def test_missing_gemini_api_key_fails_in_production() -> None:
    """7. Missing Gemini API key fails in production."""
    config = WorkerConfig(app_env="production", gemini_api_key="")
    with pytest.raises(WorkerStartupValidationError, match="Gemini API key is not configured"):
        validate_worker_startup(config)


def test_secret_values_never_appear_in_error_messages() -> None:
    """8. Secret values never appear in startup error messages."""
    secret = "SUPER_SECRET_GEMINI_KEY_9999"
    with pytest.raises(WorkerStartupValidationError) as exc_info:
        test_config = WorkerConfig(app_env="production", gemini_api_key=secret, gemini_model="")
        validate_worker_startup(test_config)

    err_str = str(exc_info.value)
    assert secret not in err_str
    assert "Gemini model is not configured" in err_str


def test_legacy_v1_infrastructure_not_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """9. Legacy V1 PromptRegistry/provider validation is no longer required."""
    import sys

    # Unload any legacy V1 modules if imported by preceding tests in the session
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("app.ai.prompts") or mod_name.startswith("app.ai.providers"):
            monkeypatch.delitem(sys.modules, mod_name, raising=False)

    config = WorkerConfig(gemini_model="gemini-3.5-flash-lite", app_env="development")
    validate_worker_startup(config)
    assert "app.ai.prompts" not in sys.modules
    assert "app.ai.providers" not in sys.modules


@pytest.mark.asyncio
async def test_worker_lifecycle_behavior_remains_unchanged() -> None:
    """10. Existing worker lifecycle behavior remains unchanged."""
    config = WorkerConfig(worker_poll_interval_seconds=1, worker_name="test-worker")
    shutdown_event = asyncio.Event()
    shutdown_event.set()

    await run_worker(
        config,
        shutdown_event,
        session_factory=_FakeFactory(),  # type: ignore[arg-type]
        consumer=_FakeConsumer(),
        heartbeat=_FakeHb(),  # type: ignore[arg-type]
    )
