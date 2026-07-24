"""Analysis provider construction and production validation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.ai.providers.base import AIProvider
from app.ai.providers.deepseek import DeepSeekProvider
from app.ai.providers.gemini import GeminiProvider
from app.storage import create_file_storage


class AnalysisProviderConfigurationError(RuntimeError):
    """Raised when configured analysis providers are missing or unsafe."""

    code = "ANALYSIS_PROVIDER_CONFIGURATION_INVALID"


@dataclass(frozen=True, slots=True)
class AnalysisProviderConfig:
    providers: Mapping[str, AIProvider]
    provider_order: tuple[str, ...]


def build_analysis_provider_config(config: Any) -> AnalysisProviderConfig:
    """Build configured providers for analysis jobs.

    Production analysis is intentionally Gemini-only because required evidence
    can include screenshots and other images.
    """
    provider_order = parse_provider_order(getattr(config, "provider_order", "gemini"))
    app_env = str(getattr(config, "app_env", "")).lower()
    if app_env == "production" and provider_order != ("gemini",):
        raise AnalysisProviderConfigurationError(
            "Production analysis must use PROVIDER_ORDER=gemini only"
        )

    providers: dict[str, AIProvider] = {}
    for name in provider_order:
        if name == "gemini":
            providers[name] = _build_gemini(config)
        elif name == "deepseek":
            providers[name] = _build_deepseek(config)
        else:
            raise AnalysisProviderConfigurationError(
                f"Unknown analysis provider configured: {name}"
            )

    if not providers:
        raise AnalysisProviderConfigurationError("At least one analysis provider is required")

    primary = providers[provider_order[0]]
    if app_env == "production" and not primary.capabilities.supports_images:
        raise AnalysisProviderConfigurationError(
            "Production analysis provider must support image input"
        )

    return AnalysisProviderConfig(providers=providers, provider_order=provider_order)


def validate_analysis_provider_startup(config: Any) -> None:
    """Fail fast when production analysis provider config is unusable."""
    provider_config = build_analysis_provider_config(config)
    if provider_config.provider_order != ("gemini",):
        return

    gemini = provider_config.providers["gemini"]
    if not gemini.model:
        raise AnalysisProviderConfigurationError("Gemini model is not configured")
    if not gemini.capabilities.supports_images:
        raise AnalysisProviderConfigurationError(
            "Configured Gemini model must support image input"
        )


def parse_provider_order(value: str) -> tuple[str, ...]:
    order = tuple(part.strip().lower() for part in value.split(",") if part.strip())
    if not order:
        raise AnalysisProviderConfigurationError("PROVIDER_ORDER must not be empty")
    return order


def _build_gemini(config: Any) -> GeminiProvider:
    api_key = str(getattr(config, "gemini_api_key", "") or "")
    model_name = str(getattr(config, "gemini_model", "") or "")
    if not api_key:
        raise AnalysisProviderConfigurationError("Gemini API key is not configured")
    if not model_name:
        raise AnalysisProviderConfigurationError("Gemini model is not configured")

    storage = create_file_storage(config)

    return GeminiProvider(
        api_key=api_key,
        model_name=model_name,
        timeout_seconds=int(getattr(config, "gemini_timeout_seconds", 120)),
        image_loader=lambda image: storage.read(file_reference=image.storage_reference),
    )


def _build_deepseek(config: Any) -> DeepSeekProvider:
    api_key = str(getattr(config, "deepseek_api_key", "") or "")
    if not api_key:
        raise AnalysisProviderConfigurationError("DeepSeek API key is not configured")

    return DeepSeekProvider(
        api_key=api_key,
        model_name=str(getattr(config, "deepseek_model", "") or "deepseek-chat"),
        base_url=str(getattr(config, "deepseek_base_url", "") or "https://api.deepseek.com"),
        timeout_seconds=int(getattr(config, "deepseek_timeout_seconds", 120)),
    )
