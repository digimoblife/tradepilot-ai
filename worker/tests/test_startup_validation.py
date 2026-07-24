from __future__ import annotations

import sys
from types import ModuleType

import pytest

from app.config import WorkerConfig
from app.startup_validation import WorkerStartupValidationError, validate_worker_startup


class _FakePromptRegistry:
    def __init__(self, *, prompts_root: object) -> None:
        self.prompts_root = prompts_root


def _install_fake_backend_modules(
    monkeypatch: pytest.MonkeyPatch,
    provider_validator: object,
) -> None:
    ai_module = ModuleType("app.ai")
    prompts_module = ModuleType("app.ai.prompts")
    providers_module = ModuleType("app.ai.providers")
    prompts_module.PromptRegistry = _FakePromptRegistry
    providers_module.validate_analysis_provider_startup = provider_validator
    monkeypatch.setitem(sys.modules, "app.ai", ai_module)
    monkeypatch.setitem(sys.modules, "app.ai.prompts", prompts_module)
    monkeypatch.setitem(sys.modules, "app.ai.providers", providers_module)


def test_startup_validation_validates_prompts_and_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def validate_provider(config: WorkerConfig) -> None:
        nonlocal called
        called = True
        assert config.provider_order == "gemini"

    _install_fake_backend_modules(monkeypatch, validate_provider)

    validate_worker_startup(WorkerConfig(gemini_api_key="secret"))

    assert called is True


def test_startup_validation_wraps_provider_errors_without_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def validate_provider(config: WorkerConfig) -> None:
        raise RuntimeError("Gemini API key is not configured")

    _install_fake_backend_modules(monkeypatch, validate_provider)

    with pytest.raises(WorkerStartupValidationError) as excinfo:
        validate_worker_startup(WorkerConfig(gemini_api_key="super-secret"))

    assert "Konfigurasi provider analisis produksi tidak valid" in str(excinfo.value)
    assert "super-secret" not in str(excinfo.value)
