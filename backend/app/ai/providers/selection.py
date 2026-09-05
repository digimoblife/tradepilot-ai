"""Analysis provider construction and production validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from app.ai.providers.base import AIProvider
from app.ai.providers.capabilities import ProviderCapabilities
from app.ai.providers.deepseek import DeepSeekProvider
from app.ai.providers.gemini import GeminiProvider, _convert_gemini_schema_document
from app.schemas.manifest import REQUIRED_ANALYSIS_TYPES, load_production_manifest
from app.schemas.registry import LocalSchemaRegistry
from app.storage import create_file_storage


class AnalysisProviderConfigurationError(RuntimeError):
    """Raised when configured analysis providers are missing or unsafe."""

    code = "ANALYSIS_PROVIDER_CONFIGURATION_INVALID"


@dataclass(frozen=True, slots=True)
class AnalysisProviderConfig:
    providers: Mapping[str, AIProvider]
    provider_order: tuple[str, ...]


_DEPRECATED_GEMINI_MODELS = frozenset(
    {
        "gemini-2.0-flash",
        "models/gemini-2.0-flash",
    }
)
_SUPPORTED_GEMINI_MODELS: Mapping[str, ProviderCapabilities] = {
    "gemini-3.1-flash-lite": ProviderCapabilities(
        supports_images=True,
        supports_text_output=True,
        supports_structured_output=True,
        supports_system_prompt=True,
        supports_json_schema=True,
        supports_multi_image=True,
        maximum_images=10,
    ),
    "gemini-3.5-flash": ProviderCapabilities(
        supports_images=True,
        supports_text_output=True,
        supports_structured_output=True,
        supports_system_prompt=True,
        supports_json_schema=True,
        supports_multi_image=True,
        maximum_images=10,
    ),
    "gemini-3.5-flash-lite": ProviderCapabilities(
        supports_images=True,
        supports_text_output=True,
        supports_structured_output=True,
        supports_system_prompt=True,
        supports_json_schema=True,
        supports_multi_image=True,
        maximum_images=10,
    ),
}

_GEMINI_TRANSPORT_SCHEMA_FILES: Mapping[str, str] = {
    "watching_update": "watching_update_gemini_transport_v1.schema.json",
    "open_position_update": "open_position_update_gemini_transport_v1.schema.json",
}


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
    if gemini.model in _DEPRECATED_GEMINI_MODELS:
        raise AnalysisProviderConfigurationError(
            f"Gemini model {gemini.model} is deprecated or unavailable"
        )
    if gemini.model not in _SUPPORTED_GEMINI_MODELS:
        raise AnalysisProviderConfigurationError(
            f"Gemini model {gemini.model} is not approved for production analysis"
        )
    if not gemini.capabilities.supports_images:
        raise AnalysisProviderConfigurationError(
            "Configured Gemini model must support image input"
        )
    if not gemini.capabilities.supports_text_output:
        raise AnalysisProviderConfigurationError(
            "Configured Gemini model must support text output"
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
    if model_name in _DEPRECATED_GEMINI_MODELS:
        raise AnalysisProviderConfigurationError(
            f"Gemini model {model_name} is deprecated or unavailable"
        )
    capabilities = _SUPPORTED_GEMINI_MODELS.get(model_name)
    if capabilities is None:
        raise AnalysisProviderConfigurationError(
            f"Gemini model {model_name} is not approved for production analysis"
        )
    try:
        response_schemas = _load_gemini_response_schemas(
            getattr(config, "schema_package_root", "schemas/production/v1")
        )
    except Exception as exc:
        raise AnalysisProviderConfigurationError(
            f"Gemini response schema registration is invalid: {exc}"
        ) from exc

    storage = create_file_storage(config)

    return GeminiProvider(
        api_key=api_key,
        model_name=model_name,
        timeout_seconds=int(getattr(config, "gemini_timeout_seconds", 120)),
        image_loader=lambda image: storage.read(file_reference=image.storage_reference),
        capabilities=capabilities,
        response_schemas=response_schemas,
    )


def _load_gemini_response_schemas(
    schema_package_root: str | Path,
) -> dict[str, dict[str, object]]:
    """Load the active lifecycle response schemas from the canonical manifest."""
    package_root = Path(schema_package_root)
    manifest = load_production_manifest(package_root)
    registry = LocalSchemaRegistry(manifest, package_root)
    response_schemas: dict[str, dict[str, object]] = {}

    for analysis_type in REQUIRED_ANALYSIS_TYPES:
        registration = manifest.analysis_type_registry.get(analysis_type)
        if registration is None:
            raise ValueError(f"Manifest is missing analysis type: {analysis_type}")

        entry = manifest.get_schema(registration.schema_name, registration.schema_version)
        if entry is None or not entry.active:
            raise ValueError(
                f"Manifest schema for {analysis_type} is missing or inactive: "
                f"{registration.schema_name}/{registration.schema_version}"
            )
        if entry.category != "AI_ANALYSIS" or not entry.root_schema:
            raise ValueError(
                f"Manifest schema for {analysis_type} is not an active response schema: "
                f"{entry.name}"
            )

        registered = registry.get(entry.name, entry.version)
        schema_document = dict(registered.document)
        schema_path = registered.path
        transport_filename = _GEMINI_TRANSPORT_SCHEMA_FILES.get(entry.name)
        if transport_filename is not None:
            transport_path = package_root / transport_filename
            if not transport_path.is_file():
                raise ValueError(
                    f"Gemini transport schema for {entry.name} is missing: {transport_path}"
                )
            schema_document = json.loads(transport_path.read_text(encoding="utf-8"))
            schema_path = transport_path
        converted = _convert_gemini_schema_document(
            schema_document,
            schema_path=schema_path,
            package_root=package_root,
        )
        response_schemas[entry.name] = converted

    return response_schemas


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
