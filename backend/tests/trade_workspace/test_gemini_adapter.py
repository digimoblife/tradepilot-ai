from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

import pytest

from app.trade_workspace.ai.gemini_adapter import (
    DEFAULT_GEMINI_MODEL,
    GeminiAdapter,
    GeminiAdapterError,
    GeminiImagePart,
)

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {"recommendation": {"type": "string"}},
    "required": ["recommendation"],
}


@dataclass
class FakeResponse:
    text: str
    parsed: dict[str, Any] | None = None


class FakeGeminiClient:
    def __init__(self, response: Any) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def generate_content(
        self,
        *,
        model: str,
        contents: list[Any],
        config: dict[str, object],
    ) -> Any:
        self.calls.append({"model": model, "contents": contents, "config": config})
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _adapter(client: FakeGeminiClient, **kwargs: object) -> GeminiAdapter:
    return GeminiAdapter(api_key="test-secret-key", client=client, **kwargs)


@pytest.mark.asyncio
async def test_gemini_adapter_builds_one_ordered_structured_request() -> None:
    raw = FakeResponse('{"recommendation":"WAIT"}')
    client = FakeGeminiClient(raw)
    adapter = _adapter(client, model="gemini-configured")
    images = [
        GeminiImagePart(data=b"first", mime_type="image/png"),
        GeminiImagePart(data=b"second", mime_type="image/jpeg"),
    ]

    result = await adapter.generate(
        prompt_text="Analyze this evidence.",
        image_parts=images,
        output_schema=OUTPUT_SCHEMA,
    )

    assert result.provider == "gemini"
    assert result.model == "gemini-configured"
    assert result.raw_response is raw
    assert result.processed_response == {"recommendation": "WAIT"}
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["model"] == "gemini-configured"
    assert call["contents"][0] == "Analyze this evidence."
    assert [part.inline_data.data for part in call["contents"][1:]] == [
        b"first",
        b"second",
    ]
    assert [part.inline_data.mime_type for part in call["contents"][1:]] == [
        "image/png",
        "image/jpeg",
    ]
    assert call["config"]["response_mime_type"] == "application/json"
    assert call["config"]["response_json_schema"] == OUTPUT_SCHEMA


@pytest.mark.asyncio
async def test_absent_model_configuration_uses_production_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setattr(
        "app.trade_workspace.ai.gemini_adapter.AppConfig",
        lambda: SimpleNamespace(
            gemini_model="",
            gemini_api_key="",
            gemini_timeout_seconds=120,
        ),
    )
    client = FakeGeminiClient(FakeResponse('{"recommendation":"BUY"}'))

    result = await _adapter(client).generate(
        prompt_text="Prompt",
        output_schema=OUTPUT_SCHEMA,
    )

    assert result.provider == "gemini"
    assert result.model == DEFAULT_GEMINI_MODEL
    assert client.calls[0]["model"] == DEFAULT_GEMINI_MODEL


@pytest.mark.asyncio
async def test_parsed_sdk_json_is_returned_without_reparsing() -> None:
    parsed = {"recommendation": "SKIP"}
    client = FakeGeminiClient(FakeResponse("ignored", parsed=parsed))

    result = await _adapter(client).generate(
        prompt_text="Prompt",
        output_schema=OUTPUT_SCHEMA,
    )

    assert result.processed_response == parsed
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_malformed_structured_response_is_sanitized() -> None:
    client = FakeGeminiClient(FakeResponse("not-json"))

    with pytest.raises(GeminiAdapterError, match="malformed structured JSON") as exc_info:
        await _adapter(client).generate(prompt_text="Prompt", output_schema=OUTPUT_SCHEMA)

    assert "not-json" not in str(exc_info.value)
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_sdk_error_is_sanitized_without_fallback_call() -> None:
    client = FakeGeminiClient(RuntimeError("api_key=test-secret-key authorization=Bearer xyz"))

    with pytest.raises(GeminiAdapterError) as exc_info:
        await _adapter(client).generate(prompt_text="Prompt", output_schema=OUTPUT_SCHEMA)

    message = str(exc_info.value)
    assert "test-secret-key" not in message
    assert "xyz" not in message
    assert "gemini" in message.lower()
    assert "gemini-configured" not in message
    assert len(client.calls) == 1
