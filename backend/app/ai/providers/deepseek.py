"""DeepSeek provider adapter (TP-0704).

Implements the ``AIProvider`` contract for DeepSeek (OpenAI-compatible API).
"""

from __future__ import annotations

import time
from typing import Any, Protocol

from app.ai.providers.base import AIProvider
from app.ai.providers.capabilities import ProviderCapabilities, ensure_request_supported
from app.ai.providers.models import ProviderRequest, ProviderResponse, ProviderUsage

# ---------------------------------------------------------------------------
# Stable errors
# ---------------------------------------------------------------------------


class DeepSeekError(Exception):
    """Base for all DeepSeek adapter errors."""

    code: str = "DEEPSEEK_ERROR"

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class DeepSeekConfigurationError(DeepSeekError):
    code: str = "AI_PROVIDER_AUTHENTICATION_FAILED"


class DeepSeekAuthenticationError(DeepSeekError):
    code: str = "AI_PROVIDER_AUTHENTICATION_FAILED"


class DeepSeekRateLimitedError(DeepSeekError):
    code: str = "AI_PROVIDER_RATE_LIMITED"


class DeepSeekTimeoutError(DeepSeekError):
    code: str = "AI_PROVIDER_TIMEOUT"


class DeepSeekRefusedError(DeepSeekError):
    code: str = "AI_PROVIDER_CONTENT_FILTERED"


class DeepSeekInvalidResponseError(DeepSeekError):
    code: str = "AI_RESPONSE_EMPTY"


class DeepSeekRequestFailedError(DeepSeekError):
    code: str = "AI_PROVIDER_INVALID_REQUEST"


# ---------------------------------------------------------------------------
# Client protocol
# ---------------------------------------------------------------------------


class DeepSeekChatClient(Protocol):
    """Minimal protocol for the OpenAI-compatible chat completions client."""

    async def chat_completions_create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
        timeout_seconds: int | None = None,
    ) -> Any: ...


# ---------------------------------------------------------------------------
# Default capabilities
# ---------------------------------------------------------------------------

_DEFAULT_CAPABILITIES = ProviderCapabilities(
    supports_images=False,
    supports_structured_output=True,
    supports_system_prompt=True,
    supports_json_schema=False,
    supports_multi_image=False,
    maximum_images=0,
)


# ---------------------------------------------------------------------------
# Finish-reason mapping (OpenAI-compatible)
# ---------------------------------------------------------------------------

_FINISH_REASON_MAP: dict[str, str] = {
    "stop": "STOP",
    "length": "MAX_TOKENS",
    "content_filter": "SAFETY",
    "tool_calls": "TOOL_CALLS",
    "insufficient_system_resource": "ERROR",
}


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class DeepSeekProvider(AIProvider):
    """DeepSeek implementation of the ``AIProvider`` interface."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int = 120,
        client: DeepSeekChatClient | None = None,
        capabilities: ProviderCapabilities | None = None,
    ) -> None:
        self._api_key = api_key
        self._model_name = model_name or "deepseek-chat"
        self._base_url = base_url or "https://api.deepseek.com"
        self._timeout_seconds = timeout_seconds
        self._capabilities = capabilities or _DEFAULT_CAPABILITIES

        if client is not None:
            self._client = client
        else:
            self._client = self._build_client()

    # ------------------------------------------------------------------
    # AIProvider properties
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return "deepseek"

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

        timeout = request.timeout_seconds or self._timeout_seconds
        messages = self._build_messages(request)
        response_format = self._build_response_format(request)

        started_at = time.monotonic()

        try:
            raw = await self._client.chat_completions_create(
                model=self._model_name,
                messages=messages,
                response_format=response_format,
                timeout_seconds=timeout,
            )
        except Exception as exc:
            raise _map_exception(exc) from exc

        elapsed_ms = int((time.monotonic() - started_at) * 1000)

        return self._build_response(raw, request, elapsed_ms)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_client(self) -> DeepSeekChatClient:
        if not self._api_key:
            raise DeepSeekConfigurationError(
                message="DeepSeek API key is not configured",
            )

        from openai import AsyncOpenAI

        oai = AsyncOpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
        )
        return _OpenAIWrapper(oai)

    @staticmethod
    def _build_messages(request: ProviderRequest) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.user_prompt})
        return messages

    @staticmethod
    def _build_response_format(
        request: ProviderRequest,
    ) -> dict[str, Any] | None:
        if request.structured_output_schema is not None:
            return {"type": "json_object"}
        return None

    @staticmethod
    def _build_response(
        raw: Any,
        request: ProviderRequest,
        elapsed_ms: int,
    ) -> ProviderResponse:
        # Extract choice
        choices = getattr(raw, "choices", None) or (
            raw.get("choices") if isinstance(raw, dict) else None
        )
        if not choices:
            raise DeepSeekInvalidResponseError(message="No choices in response")

        choice = choices[0]
        message = getattr(choice, "message", None) or (
            choice.get("message") if isinstance(choice, dict) else None
        )
        if message is None:
            raise DeepSeekInvalidResponseError(message="Missing message in response choice")

        content = getattr(message, "content", None) or (
            message.get("content") if isinstance(message, dict) else None
        )
        if content is None or content == "":
            raise DeepSeekRefusedError(message="Empty or refused response content")

        finish_reason_raw = getattr(choice, "finish_reason", None) or (
            choice.get("finish_reason") if isinstance(choice, dict) else None
        )
        fr_str = str(finish_reason_raw or "")
        finish_reason = _FINISH_REASON_MAP.get(fr_str, fr_str)

        provider_response_id = getattr(raw, "id", None) or (
            raw.get("id") if isinstance(raw, dict) else None
        )

        # Usage
        usage_obj = getattr(raw, "usage", None) or (
            raw.get("usage") if isinstance(raw, dict) else None
        )
        usage = None
        if usage_obj is not None:
            usage = ProviderUsage(
                input_tokens=_safe_int(usage_obj, "prompt_tokens"),
                output_tokens=_safe_int(usage_obj, "completion_tokens"),
                total_tokens=_safe_int(usage_obj, "total_tokens"),
            )

        # Metadata
        metadata: dict[str, Any] = {}
        metadata["latency_ms"] = elapsed_ms
        system_fp = getattr(raw, "system_fingerprint", None) or (
            raw.get("system_fingerprint") if isinstance(raw, dict) else None
        )
        if system_fp is not None:
            metadata["system_fingerprint"] = system_fp
        created_ts = getattr(raw, "created", None) or (
            raw.get("created") if isinstance(raw, dict) else None
        )
        if created_ts is not None:
            metadata["created"] = created_ts
        metadata["model"] = getattr(raw, "model", None) or (
            raw.get("model") if isinstance(raw, dict) else None
        )

        return ProviderResponse(
            provider="deepseek",
            model=metadata.get("model", "deepseek-chat"),
            raw_output=content,
            request_id=request.request_id,
            provider_response_id=(
                str(provider_response_id) if provider_response_id is not None else None
            ),
            finish_reason=finish_reason,
            usage=usage,
            latency_ms=elapsed_ms,
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _OpenAIWrapper:
    """Wraps ``openai.AsyncOpenAI`` into the ``DeepSeekChatClient`` protocol."""

    def __init__(self, client: Any) -> None:
        self._client = client

    async def chat_completions_create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
        timeout_seconds: int | None = None,
    ) -> Any:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format
        if timeout_seconds is not None:
            kwargs["timeout"] = timeout_seconds

        return await self._client.chat.completions.create(**kwargs)


def _map_exception(exc: Exception) -> DeepSeekError:
    import openai as oai

    if isinstance(exc, oai.AuthenticationError):
        return DeepSeekAuthenticationError(message=str(exc))
    if isinstance(exc, oai.PermissionDeniedError):
        return DeepSeekAuthenticationError(message=str(exc))
    if isinstance(exc, oai.RateLimitError):
        return DeepSeekRateLimitedError(message=str(exc))
    if isinstance(exc, oai.APITimeoutError):
        return DeepSeekTimeoutError(message=str(exc))
    if isinstance(exc, oai.APIConnectionError):
        return DeepSeekTimeoutError(message=str(exc))
    if isinstance(exc, oai.BadRequestError):
        return DeepSeekRequestFailedError(message=str(exc))
    if isinstance(exc, oai.NotFoundError):
        return DeepSeekConfigurationError(message=f"Model or endpoint not found: {exc}")
    if isinstance(exc, oai.InternalServerError):
        return DeepSeekRequestFailedError(message=str(exc))

    exc_str = str(exc).lower()
    if "timeout" in exc_str or "timed out" in exc_str:
        return DeepSeekTimeoutError(message=str(exc))
    if "rate" in exc_str and "limit" in exc_str:
        return DeepSeekRateLimitedError(message=str(exc))

    return DeepSeekRequestFailedError(message=str(exc))


def _safe_int(obj: Any, attr: str) -> int | None:
    val = getattr(obj, attr, None) if not isinstance(obj, dict) else obj.get(attr)
    if val is not None:
        try:
            return int(val)
        except (ValueError, TypeError):
            return None
    return None
