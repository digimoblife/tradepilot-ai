"""Tests for analysis provider selection and production validation."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.ai.providers import ProviderCapabilities, ProviderImage, ProviderRequest
from app.ai.providers.capabilities import ensure_request_supported
from app.ai.providers.selection import (
    AnalysisProviderConfigurationError,
    build_analysis_provider_config,
    validate_analysis_provider_startup,
)


class _FakeGeminiProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        timeout_seconds: int,
        image_loader: object,
    ) -> None:
        self.api_key = api_key
        self._model = model_name
        self.timeout_seconds = timeout_seconds
        self.image_loader = image_loader
        self._capabilities = ProviderCapabilities(
            supports_images=True,
            supports_structured_output=True,
            supports_system_prompt=True,
            supports_json_schema=True,
            supports_multi_image=True,
            maximum_images=10,
        )

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return self._model

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities


def _config(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "app_env": "production",
        "provider_order": "gemini",
        "gemini_api_key": "secret-gemini-key",
        "gemini_model": "models/gemini-2.0-flash",
        "gemini_timeout_seconds": 120,
        "deepseek_api_key": "secret-deepseek-key",
        "deepseek_model": "deepseek-chat",
        "deepseek_base_url": "https://api.deepseek.com",
        "deepseek_timeout_seconds": 120,
        "storage_root": "storage/local",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_production_selection_is_gemini_only(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.ai.providers.selection as selection

    monkeypatch.setattr(selection, "GeminiProvider", _FakeGeminiProvider)

    provider_config = build_analysis_provider_config(_config())

    assert provider_config.provider_order == ("gemini",)
    assert set(provider_config.providers) == {"gemini"}
    assert provider_config.providers["gemini"].capabilities.supports_images is True


def test_production_rejects_deepseek_fallback_before_building_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.ai.providers.selection as selection

    def fail_deepseek(**kwargs: object) -> None:
        raise AssertionError("DeepSeek must not be enabled for production analysis")

    monkeypatch.setattr(selection, "GeminiProvider", _FakeGeminiProvider)
    monkeypatch.setattr(selection, "DeepSeekProvider", fail_deepseek)

    with pytest.raises(AnalysisProviderConfigurationError, match="PROVIDER_ORDER=gemini"):
        build_analysis_provider_config(_config(provider_order="gemini,deepseek"))


def test_deepseek_code_is_disabled_by_provider_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.ai.providers.selection as selection

    def fail_deepseek(**kwargs: object) -> None:
        raise AssertionError("DeepSeek constructor should not be called")

    monkeypatch.setattr(selection, "GeminiProvider", _FakeGeminiProvider)
    monkeypatch.setattr(selection, "DeepSeekProvider", fail_deepseek)

    provider_config = build_analysis_provider_config(
        _config(provider_order="gemini", deepseek_api_key="still-configured")
    )

    assert provider_config.provider_order == ("gemini",)
    assert "deepseek" not in provider_config.providers


def test_gemini_multimodal_capabilities_accept_required_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.ai.providers.selection as selection

    monkeypatch.setattr(selection, "GeminiProvider", _FakeGeminiProvider)
    provider_config = build_analysis_provider_config(_config())
    request = ProviderRequest(
        request_id=uuid.uuid4(),
        analysis_type="INITIAL",
        prompt_version="v1",
        user_prompt="Analisis awal",
        expected_schema_name="initial_analysis",
        expected_schema_version="1",
        system_prompt="Anda analis.",
        images=(
            ProviderImage(
                evidence_id=uuid.uuid4(),
                mime_type="image/png",
                storage_reference="u/s/chart.png",
                byte_size=123,
            ),
        ),
        structured_output_schema={},
    )

    ensure_request_supported(request, provider_config.providers["gemini"].capabilities)


def test_startup_validation_requires_gemini_credentials_without_leaking_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.ai.providers.selection as selection

    monkeypatch.setattr(selection, "GeminiProvider", _FakeGeminiProvider)

    with pytest.raises(AnalysisProviderConfigurationError) as excinfo:
        validate_analysis_provider_startup(_config(gemini_api_key=""))

    assert "Gemini API key is not configured" in str(excinfo.value)
    assert "secret" not in str(excinfo.value)


def test_startup_validation_requires_image_capable_gemini(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.ai.providers.selection as selection

    class TextOnlyGemini(_FakeGeminiProvider):
        @property
        def capabilities(self) -> ProviderCapabilities:
            return ProviderCapabilities(supports_images=False)

    monkeypatch.setattr(selection, "GeminiProvider", TextOnlyGemini)

    with pytest.raises(AnalysisProviderConfigurationError, match="image input"):
        validate_analysis_provider_startup(_config())
