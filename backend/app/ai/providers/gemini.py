"""Gemini provider adapter (TP-0703).

Implements the ``AIProvider`` contract for Google Gemini.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Protocol

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


# ---------------------------------------------------------------------------
# Client Protocol  (injectable for tests)
# ---------------------------------------------------------------------------


class GeminiModelClient(Protocol):
    """Minimal protocol for the Gemini model's async generate method."""

    async def generate_content_async(self, contents: list[Any]) -> Any: ...

    @property
    def model_name(self) -> str: ...


# ---------------------------------------------------------------------------
# Default capabilities for Gemini 2.0 Flash (MVP model)
# ---------------------------------------------------------------------------

_DEFAULT_CAPABILITIES = ProviderCapabilities(
    supports_images=True,
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
    ) -> None:
        self._api_key = api_key
        self._model_name = model_name or "models/gemini-2.0-flash"
        self._timeout_seconds = timeout_seconds
        self._capabilities = capabilities or _DEFAULT_CAPABILITIES
        self._image_loader = image_loader or _default_image_loader

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

        started_at = time.monotonic()

        try:
            raw = await self._model.generate_content_async(contents)
        except Exception as exc:
            raise _map_exception(exc) from exc

        elapsed_ms = int((time.monotonic() - started_at) * 1000)

        return self._build_response(raw, request, elapsed_ms, generation_config)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_model(self) -> GeminiModelClient:
        import google.generativeai as genai

        if not self._api_key:
            raise GeminiConfigurationError(
                message="Gemini API key is not configured",
            )

        genai.configure(api_key=self._api_key)  # type: ignore[attr-defined]

        system_instruction = None  # Set per-request in contents

        model = genai.GenerativeModel(  # type: ignore[attr-defined]
            model_name=self._model_name,
            system_instruction=system_instruction,
        )
        return model

    def _build_contents(self, request: ProviderRequest) -> list[Any]:
        parts: list[Any] = []

        from google.generativeai import protos

        if request.system_prompt:
            parts.append(
                protos.Part(text=f"[SYSTEM]\n{request.system_prompt}\n[/SYSTEM]"),
            )

        parts.append(protos.Part(text=request.user_prompt))

        for pi in request.images:
            image_bytes = self._image_loader(pi)
            parts.append(
                protos.Part(
                    inline_data=protos.Blob(
                        mime_type=pi.mime_type,
                        data=image_bytes,
                    ),
                ),
            )

        return parts

    def _build_generation_config(self, request: ProviderRequest) -> dict[str, Any]:
        config: dict[str, Any] = {}

        if request.structured_output_schema is not None:
            config["response_mime_type"] = "application/json"
            config["response_schema"] = request.structured_output_schema

        return config

    @staticmethod
    def _build_response(
        raw: Any,
        request: ProviderRequest,
        elapsed_ms: int,
        generation_config: dict[str, Any],
    ) -> ProviderResponse:
        raw_output = raw.text if hasattr(raw, "text") and raw.text is not None else ""

        finish_reason = None
        if hasattr(raw, "candidates") and raw.candidates:
            try:
                fr = raw.candidates[0].finish_reason
                if isinstance(fr, int):
                    finish_reason = _FINISH_REASON_MAP.get(fr, f"UNKNOWN_{fr}")
                else:
                    finish_reason = str(fr)
            except (AttributeError, IndexError):
                pass

        usage = None
        if hasattr(raw, "usage_metadata") and raw.usage_metadata is not None:
            um = raw.usage_metadata
            usage = ProviderUsage(
                input_tokens=getattr(um, "prompt_token_count", None),
                output_tokens=getattr(um, "candidates_token_count", None),
                total_tokens=getattr(um, "total_token_count", None),
            )

        provider_response_id = None
        if hasattr(raw, "candidates") and raw.candidates:
            try:
                provider_response_id = raw.candidates[0].index
            except (AttributeError, IndexError):
                pass

        metadata: dict[str, Any] = {}
        if hasattr(raw, "prompt_feedback") and raw.prompt_feedback is not None:
            metadata["prompt_feedback"] = _safe_metadata(raw.prompt_feedback)

        metadata["latency_ms"] = elapsed_ms
        if generation_config:
            metadata["generation_config"] = _safe_metadata(generation_config)

        return ProviderResponse(
            provider="gemini",
            model=request.metadata.get("model_name", "gemini-2.0-flash")
            if isinstance(request.metadata, dict)
            else "gemini-2.0-flash",  # noqa: E501
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
    import google.api_core.exceptions as api_exc

    if isinstance(exc, api_exc.DeadlineExceeded):
        return GeminiTimeoutError(message=str(exc))
    if isinstance(exc, api_exc.Unauthenticated):
        return GeminiAuthenticationError(message=str(exc))
    if isinstance(exc, api_exc.PermissionDenied):
        return GeminiAuthenticationError(message=str(exc))
    if isinstance(exc, api_exc.ResourceExhausted):
        return GeminiRateLimitedError(message=str(exc))
    if isinstance(exc, api_exc.InvalidArgument):
        return GeminiRequestFailedError(message=str(exc))
    if isinstance(exc, api_exc.NotFound):
        return GeminiConfigurationError(message=f"Model not found: {exc}")

    # Check for blocked/safety responses
    exc_str = str(exc).lower()
    if "safety" in exc_str or "blocked" in exc_str or "finish_reason" in exc_str:
        return GeminiRefusedError(message=str(exc))
    if "timed out" in exc_str or "timeout" in exc_str or "deadline" in exc_str:
        return GeminiTimeoutError(message=str(exc))

    return GeminiRequestFailedError(message=str(exc))


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
