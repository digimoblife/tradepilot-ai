"""Gemini provider adapter (TP-0703).

Implements the ``AIProvider`` contract for Google Gemini.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

from app.ai.providers.base import AIProvider
from app.ai.providers.capabilities import ProviderCapabilities, ensure_request_supported
from app.ai.providers.models import ProviderImage, ProviderRequest, ProviderResponse, ProviderUsage

# ---------------------------------------------------------------------------
# Stable error codes  (AI_PROVIDER_SPEC.md §23)
# ---------------------------------------------------------------------------


class GeminiError(Exception):
    """Base for all Gemini adapter errors."""

    code: str = "GEMINI_ERROR"

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class GeminiConfigurationError(GeminiError):
    code: str = "AI_PROVIDER_AUTHENTICATION_FAILED"


class GeminiAuthenticationError(GeminiError):
    code: str = "AI_PROVIDER_AUTHENTICATION_FAILED"


class GeminiRateLimitedError(GeminiError):
    code: str = "AI_PROVIDER_RATE_LIMITED"


class GeminiTimeoutError(GeminiError):
    code: str = "AI_PROVIDER_TIMEOUT"


class GeminiRefusedError(GeminiError):
    code: str = "AI_PROVIDER_CONTENT_FILTERED"


class GeminiInvalidResponseError(GeminiError):
    code: str = "AI_RESPONSE_EMPTY"


class GeminiRequestFailedError(GeminiError):
    code: str = "AI_PROVIDER_INVALID_REQUEST"


class GeminiSchemaConversionError(GeminiError):
    code: str = "AI_PROVIDER_INVALID_REQUEST"


# ---------------------------------------------------------------------------
# Client Protocol  (injectable for tests)
# ---------------------------------------------------------------------------


class GeminiModelClient(Protocol):
    """Minimal protocol for the Gemini model's async generate method."""

    async def generate_content_async(
        self,
        contents: list[Any],
        *,
        generation_config: Mapping[str, Any] | None = None,
    ) -> Any: ...

    @property
    def model_name(self) -> str: ...


# ---------------------------------------------------------------------------
# Default capabilities for Gemini 3.5 Flash (production model)
# ---------------------------------------------------------------------------

_DEFAULT_CAPABILITIES = ProviderCapabilities(
    supports_images=True,
    supports_text_output=True,
    supports_structured_output=True,
    supports_system_prompt=True,
    supports_json_schema=True,
    supports_multi_image=True,
    maximum_images=10,
)

# Gemini finish-reason mapping
_FINISH_REASON_MAP: dict[int, str] = {
    1: "STOP",
    2: "MAX_TOKENS",
    3: "SAFETY",
    4: "RECITATION",
    5: "OTHER",
}

_SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)\b(api[_ -]?key|authorization|bearer|token)\b\s*[:=]\s*([^\s,;]+)"
)


class _GoogleGenAIModelClient:
    """Thin wrapper around the current Google GenAI async client."""

    def __init__(self, *, api_key: str, model_name: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate_content_async(
        self,
        contents: list[Any],
        *,
        generation_config: Mapping[str, Any] | None = None,
    ) -> Any:
        return await self._client.aio.models.generate_content(
            model=self._model_name,
            contents=contents,
            config=generation_config,
        )


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class GeminiProvider(AIProvider):
    """Gemini implementation of the ``AIProvider`` interface."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_name: str | None = None,
        timeout_seconds: int = 120,
        model: GeminiModelClient | None = None,
        image_loader: Callable[[ProviderImage], bytes] | None = None,
        capabilities: ProviderCapabilities | None = None,
        response_schemas: dict[str, dict[str, object]] | None = None,
    ) -> None:
        self._api_key = api_key
        self._model_name = model_name or "gemini-3.5-flash"
        self._timeout_seconds = timeout_seconds
        self._capabilities = capabilities or _DEFAULT_CAPABILITIES
        self._image_loader = image_loader or _default_image_loader
        self._response_schemas = dict(response_schemas or {})

        if model is not None:
            self._model = model
        else:
            self._model = self._build_model()

    # ------------------------------------------------------------------
    # AIProvider properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return self._model_name

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    # ------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        ensure_request_supported(request, self._capabilities)

        contents = self._build_contents(request)
        generation_config = self._build_generation_config(request)
        timeout_seconds = request.timeout_seconds or self._timeout_seconds

        started_at = time.monotonic()

        try:
            raw = await asyncio.wait_for(
                self._model.generate_content_async(
                    contents,
                    generation_config=generation_config or None,
                ),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            raise GeminiTimeoutError(
                message=f"Gemini request timed out after {timeout_seconds} seconds",
            ) from exc
        except Exception as exc:
            raise _map_exception(exc) from exc

        elapsed_ms = int((time.monotonic() - started_at) * 1000)

        return self._build_response(
            raw,
            request,
            elapsed_ms,
            generation_config,
            configured_model_name=self._model_name,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_model(self) -> GeminiModelClient:
        if not self._api_key:
            raise GeminiConfigurationError(
                message="Gemini API key is not configured",
            )
        return _GoogleGenAIModelClient(
            api_key=self._api_key,
            model_name=self._model_name,
        )

    def _build_contents(self, request: ProviderRequest) -> list[Any]:
        parts: list[Any] = []
        from google.genai import types

        parts.append(request.user_prompt)

        for pi in request.images:
            image_bytes = self._image_loader(pi)
            parts.append(types.Part.from_bytes(data=image_bytes, mime_type=pi.mime_type))

        return parts

    def _build_generation_config(self, request: ProviderRequest) -> dict[str, Any]:
        config: dict[str, Any] = {}

        if request.system_prompt:
            config["system_instruction"] = request.system_prompt

        response_schema = self._resolve_response_schema(request)
        if response_schema is not None:
            config["response_mime_type"] = "application/json"
            config["response_json_schema"] = response_schema

        return config

    def _resolve_response_schema(self, request: ProviderRequest) -> dict[str, object] | None:
        if request.expected_schema_name == "initial_analysis":
            schema = self._response_schemas.get("initial_analysis")
            if schema is None:
                raise GeminiConfigurationError(
                    message="Initial Analysis Gemini response schema is not configured",
                )
            return schema
        if request.structured_output_schema is not None:
            return dict(request.structured_output_schema)
        return None

    @staticmethod
    def _build_response(
        raw: Any,
        request: ProviderRequest,
        elapsed_ms: int,
        generation_config: dict[str, Any],
        *,
        configured_model_name: str,
    ) -> ProviderResponse:
        raw_output = _extract_response_text(raw)

        finish_reason = _extract_finish_reason(raw)

        usage = None
        if hasattr(raw, "usage_metadata") and raw.usage_metadata is not None:
            um = raw.usage_metadata
            usage = ProviderUsage(
                input_tokens=getattr(um, "prompt_token_count", None),
                output_tokens=(
                    getattr(um, "response_token_count", None)
                    or getattr(um, "candidates_token_count", None)
                ),
                total_tokens=getattr(um, "total_token_count", None),
            )

        provider_response_id = _normalize_provider_response_id(raw)

        metadata: dict[str, Any] = {}
        if hasattr(raw, "prompt_feedback") and raw.prompt_feedback is not None:
            metadata["prompt_feedback"] = _safe_metadata(raw.prompt_feedback)
        if getattr(raw, "parsed", None) is not None:
            metadata["parsed"] = _safe_metadata(raw.parsed)
        if getattr(raw, "model_version", None) is not None:
            metadata["model_version"] = _safe_metadata(raw.model_version)

        metadata["latency_ms"] = elapsed_ms
        if generation_config:
            metadata["generation_config"] = _safe_metadata(generation_config)

        return ProviderResponse(
            provider="gemini",
            model=request.metadata.get("model_name", configured_model_name)
            if isinstance(request.metadata, dict)
            else configured_model_name,
            raw_output=raw_output,
            request_id=request.request_id,
            provider_response_id=provider_response_id,
            finish_reason=finish_reason,
            usage=usage,
            latency_ms=elapsed_ms,
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _default_image_loader(image: ProviderImage) -> bytes:
    raise GeminiRequestFailedError(
        message=f"No image loader configured for evidence {image.evidence_id}",
    )


def _map_exception(exc: Exception) -> GeminiError:
    message = _extract_safe_exception_text(exc)
    status_code = _extract_status_code(exc)

    if status_code in {401, 403}:
        return GeminiAuthenticationError(message=message)
    if status_code == 404:
        return GeminiConfigurationError(message=f"Model not found: {message}")
    if status_code == 408:
        return GeminiTimeoutError(message=message)
    if status_code == 429:
        return GeminiRateLimitedError(message=message)
    if status_code == 400:
        return GeminiRequestFailedError(message=message)
    if status_code in {500, 502, 503, 504}:
        return GeminiTimeoutError(message=message)

    # Check for blocked/safety responses
    exc_str = message.lower()
    if "safety" in exc_str or "blocked" in exc_str or "finish_reason" in exc_str:
        return GeminiRefusedError(message=message)
    if "quota" in exc_str or "rate limit" in exc_str or "resource exhausted" in exc_str:
        return GeminiRateLimitedError(message=message)
    if "permission" in exc_str or "unauthorized" in exc_str or "forbidden" in exc_str:
        return GeminiAuthenticationError(message=message)
    if "timed out" in exc_str or "timeout" in exc_str or "deadline" in exc_str:
        return GeminiTimeoutError(message=message)

    return GeminiRequestFailedError(message=message)


def _extract_status_code(exc: Exception) -> int | None:
    for attr in ("code", "status_code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    if response is not None:
        for attr in ("status_code", "status_code", "status"):
            value = getattr(response, attr, None)
            if isinstance(value, int):
                return value
    return None


def _extract_response_text(raw: Any) -> str:
    try:
        text = getattr(raw, "text", None)
    except Exception:  # noqa: BLE001
        text = None
    return text if isinstance(text, str) else ""


def _extract_finish_reason(raw: Any) -> str | None:
    candidates = getattr(raw, "candidates", None)
    if not candidates:
        return None
    try:
        finish_reason = candidates[0].finish_reason
    except (AttributeError, IndexError):
        return None

    if isinstance(finish_reason, int):
        return _FINISH_REASON_MAP.get(finish_reason, f"UNKNOWN_{finish_reason}")
    if hasattr(finish_reason, "name"):
        name = getattr(finish_reason, "name", None)
        if isinstance(name, str) and name:
            return name
    rendered = str(finish_reason)
    return rendered or None


def _extract_safe_exception_text(exc: Exception) -> str:
    message = _sanitize_exception_text(getattr(exc, "message", ""))
    if message:
        return _append_retry_after(message, exc)

    details = _stringify_exception_value(getattr(exc, "details", None))
    details = _sanitize_exception_text(details)
    if details:
        return _append_retry_after(details, exc)

    errors = _stringify_exception_value(getattr(exc, "errors", None))
    errors = _sanitize_exception_text(errors)
    if errors:
        return _append_retry_after(errors, exc)

    text = _sanitize_exception_text(str(exc))
    if text:
        return _append_retry_after(text, exc)

    return _append_retry_after(_sanitize_exception_text(repr(exc)), exc)


def _stringify_exception_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        parts = [_stringify_exception_value(item) for item in value]
        return "; ".join(part for part in parts if part)
    if isinstance(value, dict):
        rendered = _safe_metadata(value)
        return str(rendered)
    return str(_safe_metadata(value))


def _sanitize_exception_text(text: str) -> str:
    if not text:
        return ""
    cleaned = _SENSITIVE_VALUE_PATTERN.sub(r"\1=[REDACTED]", text.strip())
    return cleaned[:500] if len(cleaned) > 500 else cleaned


def _append_retry_after(message: str, exc: Exception) -> str:
    retry_after = _extract_retry_after(exc)
    if not retry_after:
        return message

    lowered = message.lower()
    if "retry-after" in lowered or "retry after" in lowered:
        return message

    combined = f"{message} Retry-After: {retry_after}"
    return combined[:500] if len(combined) > 500 else combined


def _extract_retry_after(exc: Exception) -> str | None:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers is None:
        headers = getattr(exc, "headers", None)
    if headers is None:
        return None

    value: Any = None
    if isinstance(headers, dict):
        value = headers.get("Retry-After") or headers.get("retry-after")
    else:
        getter = getattr(headers, "get", None)
        if callable(getter):
            value = getter("Retry-After") or getter("retry-after")

    if value is None:
        return None

    rendered = _sanitize_exception_text(str(value))
    return rendered or None


def _safe_metadata(obj: Any) -> Any:
    """Convert an SDK object to a JSON-safe representation."""
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if isinstance(obj, dict):
        return {k: _safe_metadata(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe_metadata(v) for v in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)


def _normalize_provider_response_id(raw: Any) -> str | None:
    candidate = None
    if hasattr(raw, "candidates") and raw.candidates:
        try:
            candidate = raw.candidates[0]
        except IndexError:
            candidate = None

    for value in (
        getattr(raw, "response_id", None),
        getattr(raw, "id", None),
        getattr(candidate, "response_id", None) if candidate is not None else None,
        getattr(candidate, "id", None) if candidate is not None else None,
    ):
        normalized = _stringify_provider_response_id(value)
        if normalized is not None:
            return normalized

    return None


def load_initial_analysis_response_schema(
    schema_package_root: str | Path = "schemas/production/v1",
) -> dict[str, object]:
    package_root = Path(schema_package_root)
    schema_path = package_root / "initial_analysis.schema.json"
    if not schema_path.is_file():
        raise GeminiSchemaConversionError(
            message=f"Initial Analysis schema file not found: {schema_path}",
        )

    raw_schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return _convert_gemini_schema_document(raw_schema, schema_path=schema_path, package_root=package_root)


_IGNORED_SCHEMA_KEYS = frozenset(
    {
        "examples",
        "default",
        "minLength",
        "maxLength",
        "pattern",
        "const",
        "allOf",
        "if",
        "then",
        "else",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "uniqueItems",
        "minProperties",
        "maxProperties",
        "readOnly",
        "writeOnly",
        "deprecated",
    }
)
_SUPPORTED_SCHEMA_KEYS = frozenset(
    {
        "$schema",
        "$id",
        "$defs",
        "$ref",
        "$anchor",
        "type",
        "format",
        "title",
        "description",
        "enum",
        "items",
        "prefixItems",
        "minItems",
        "maxItems",
        "minimum",
        "maximum",
        "anyOf",
        "oneOf",
        "properties",
        "additionalProperties",
        "required",
        "propertyOrdering",
    }
)


def _convert_gemini_schema_document(
    raw_schema: dict[str, object],
    *,
    schema_path: Path,
    package_root: Path,
) -> dict[str, object]:
    converted = _convert_schema_node(
        raw_schema,
        schema_path=schema_path,
        package_root=package_root,
        document=raw_schema,
    )
    if not isinstance(converted, dict):
        raise GeminiSchemaConversionError(message="Converted Gemini schema must be an object")
    return converted


def _convert_schema_node(
    node: object,
    *,
    schema_path: Path,
    package_root: Path,
    document: dict[str, object],
) -> object:
    if isinstance(node, list):
        return [
            _convert_schema_node(
                item,
                schema_path=schema_path,
                package_root=package_root,
                document=document,
            )
            for item in node
        ]
    if not isinstance(node, dict):
        return node

    if "$ref" in node:
        resolved, resolved_path, resolved_document = _resolve_schema_ref(
            str(node["$ref"]),
            schema_path=schema_path,
            package_root=package_root,
            document=document,
        )
        merged = dict(resolved)
        for key, value in node.items():
            if key != "$ref":
                merged[key] = value
        return _convert_schema_node(
            merged,
            schema_path=resolved_path,
            package_root=package_root,
            document=resolved_document,
        )

    unsupported = set(node) - _SUPPORTED_SCHEMA_KEYS - _IGNORED_SCHEMA_KEYS
    if unsupported:
        raise GeminiSchemaConversionError(
            message=(
                f"Unsupported schema keywords for Gemini conversion in {schema_path.name}: "
                f"{sorted(unsupported)}"
            ),
        )

    converted: dict[str, object] = {}

    for key, value in node.items():
        if key in _IGNORED_SCHEMA_KEYS:
            continue
        if key in {"$schema", "$id", "$anchor", "title", "description", "format", "propertyOrdering"}:
            converted[key] = value
            continue
        if key == "type":
            if isinstance(value, list):
                converted[key] = [
                    _convert_schema_node(item, schema_path=schema_path, package_root=package_root, document=document)
                    for item in value
                ]
            else:
                converted[key] = value
            continue
        if key == "enum":
            converted[key] = list(value) if isinstance(value, list) else value
            continue
        if key == "required":
            if not isinstance(value, list):
                raise GeminiSchemaConversionError(
                    message=f"Schema required must be an array in {schema_path.name}",
                )
            converted[key] = list(value)
            continue
        if key == "additionalProperties":
            if isinstance(value, dict):
                converted[key] = _convert_schema_node(
                    value,
                    schema_path=schema_path,
                    package_root=package_root,
                    document=document,
                )
            else:
                converted[key] = value
            continue
        if key == "$defs":
            if not isinstance(value, dict):
                raise GeminiSchemaConversionError(
                    message=f"Schema $defs must be an object in {schema_path.name}",
                )
            converted[key] = {
                def_name: _convert_schema_node(
                    def_value,
                    schema_path=schema_path,
                    package_root=package_root,
                    document=document,
                )
                for def_name, def_value in value.items()
            }
            continue
        if key == "properties":
            if not isinstance(value, dict):
                raise GeminiSchemaConversionError(
                    message=f"Schema properties must be an object in {schema_path.name}",
                )
            converted[key] = {
                prop_name: _convert_schema_node(
                    prop_value,
                    schema_path=schema_path,
                    package_root=package_root,
                    document=document,
                )
                for prop_name, prop_value in value.items()
            }
            continue
        if key in {"items"}:
            converted[key] = _convert_schema_node(
                value,
                schema_path=schema_path,
                package_root=package_root,
                document=document,
            )
            continue
        if key in {"prefixItems", "anyOf", "oneOf"}:
            if not isinstance(value, list):
                raise GeminiSchemaConversionError(
                    message=f"Schema {key} must be an array in {schema_path.name}",
                )
            converted[key] = [
                _convert_schema_node(
                    item,
                    schema_path=schema_path,
                    package_root=package_root,
                    document=document,
                )
                for item in value
            ]
            continue
        converted[key] = value

    return converted


def _resolve_schema_ref(
    ref: str,
    *,
    schema_path: Path,
    package_root: Path,
    document: dict[str, object],
) -> tuple[dict[str, object], Path, dict[str, object]]:
    if ref.startswith("#/"):
        return _resolve_json_pointer(document, ref[1:]), schema_path, document

    path_part, _, pointer = ref.partition("#")
    if ref.startswith("https://schemas.tradepilot.local/production/v1/"):
        filename = path_part.rsplit("/", 1)[-1]
        target_path = package_root / filename
    else:
        target_path = (schema_path.parent / path_part).resolve()

    if not target_path.is_file():
        raise GeminiSchemaConversionError(message=f"Referenced schema file not found: {target_path}")

    target_document = json.loads(target_path.read_text(encoding="utf-8"))
    if not pointer:
        return target_document, target_path, target_document
    return _resolve_json_pointer(target_document, pointer), target_path, target_document


def _resolve_json_pointer(document: dict[str, object], pointer: str) -> dict[str, object]:
    current: object = document
    for token in pointer.lstrip("/").split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            raise GeminiSchemaConversionError(
                message=f"Schema JSON pointer not found: #{pointer}",
            )
        current = current[token]
    if not isinstance(current, dict):
        raise GeminiSchemaConversionError(
            message=f"Schema JSON pointer must resolve to an object: #{pointer}",
        )
    return current


def _stringify_provider_response_id(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, int):
        return str(value) if value > 0 else None
    return None
