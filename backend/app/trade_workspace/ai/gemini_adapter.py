from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.config import AppConfig

DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite"


@dataclass(frozen=True, slots=True)
class GeminiImagePart:
    """Ordered image data supplied to the rebuild Gemini boundary."""

    data: bytes
    mime_type: str


@dataclass(frozen=True, slots=True)
class GeminiAdapterResult:
    """The explicit result returned by the rebuild Gemini adapter."""

    provider: str
    model: str
    raw_response: Any
    processed_response: dict[str, Any]


class GeminiAdapterError(Exception):
    """Sanitized errors raised by the rebuild Gemini boundary."""


class _GeminiClient(Protocol):
    async def generate_content(
        self,
        *,
        model: str,
        contents: list[Any],
        config: Mapping[str, object],
    ) -> Any: ...


class _GoogleGeminiClient:
    def __init__(self, api_key: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)

    async def generate_content(
        self,
        *,
        model: str,
        contents: list[Any],
        config: Mapping[str, object],
    ) -> Any:
        return await self._client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=dict(config),
        )


class GeminiAdapter:
    """Single Gemini-only request boundary for rebuild runtime use."""

    provider = "gemini"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int | None = None,
        client: _GeminiClient | None = None,
    ) -> None:
        config = AppConfig()
        configured_model = model if model is not None else config.gemini_model
        self._model = configured_model or DEFAULT_GEMINI_MODEL
        self._api_key = api_key if api_key is not None else config.gemini_api_key
        self._timeout_seconds = (
            timeout_seconds if timeout_seconds is not None else config.gemini_timeout_seconds
        )
        self._client = client

    @property
    def model(self) -> str:
        return self._model

    async def generate(
        self,
        *,
        prompt_text: str,
        image_parts: Sequence[GeminiImagePart] = (),
        output_schema: Mapping[str, object],
    ) -> GeminiAdapterResult:
        contents = self._build_contents(prompt_text, image_parts)
        request_config: dict[str, object] = {
            "response_mime_type": "application/json",
            "response_json_schema": dict(output_schema),
        }
        client = self._client or self._build_client()

        try:
            raw_response = await self._call_once(client, contents, request_config)
        except GeminiAdapterError:
            raise
        except Exception as exc:
            raise GeminiAdapterError(
                self._sanitize_error(
                    f"Gemini request failed for model {self._model}: {exc}"
                )
            ) from exc

        try:
            processed_response = _parse_structured_response(raw_response)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise GeminiAdapterError(
                f"Gemini returned malformed structured JSON for model {self._model}."
            ) from exc

        return GeminiAdapterResult(
            provider=self.provider,
            model=self._model,
            raw_response=raw_response,
            processed_response=processed_response,
        )

    async def _call_once(
        self,
        client: _GeminiClient,
        contents: list[Any],
        request_config: Mapping[str, object],
    ) -> Any:
        return await client.generate_content(
            model=self._model,
            contents=contents,
            config=request_config,
        )

    def _build_client(self) -> _GeminiClient:
        if not self._api_key:
            raise GeminiAdapterError("Gemini API key is not configured.")
        return _GoogleGeminiClient(self._api_key)

    @staticmethod
    def _build_contents(
        prompt_text: str,
        image_parts: Sequence[GeminiImagePart],
    ) -> list[Any]:
        from google.genai import types

        contents: list[Any] = [prompt_text]
        contents.extend(
            types.Part.from_bytes(data=image.data, mime_type=image.mime_type)
            for image in image_parts
        )
        return contents

    def _sanitize_error(self, message: str) -> str:
        sanitized = message
        if self._api_key:
            sanitized = sanitized.replace(self._api_key, "[REDACTED]")
        sanitized = re.sub(
            r"(?i)authorization\s*[:=]\s*bearer\s+[^\s,;]+",
            "authorization=[REDACTED]",
            sanitized,
        )
        sanitized = re.sub(
            r"(?i)(api[_ -]?key|token)\s*[:=]\s*[^\s,;]+",
            r"\1=[REDACTED]",
            sanitized,
        )
        sanitized = re.sub(r"(?i)\bbearer\s+[^\s,;]+", "bearer [REDACTED]", sanitized)
        return sanitized[:500]


def _parse_structured_response(raw_response: Any) -> dict[str, Any]:
    parsed = getattr(raw_response, "parsed", None)
    if isinstance(parsed, Mapping):
        return dict(parsed)

    text = getattr(raw_response, "text", raw_response)
    if not isinstance(text, str):
        raise TypeError("structured response is not text or an object")
    decoded = json.loads(text)
    if not isinstance(decoded, dict):
        raise ValueError("structured response must be a JSON object")
    return decoded
