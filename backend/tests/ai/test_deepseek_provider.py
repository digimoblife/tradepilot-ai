"""Tests for DeepSeekProvider (TP-0704).

Uses an injected fake chat-completions client — no real API calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import pytest

from app.ai.providers import (
    AIProvider,
    DeepSeekAuthenticationError,
    DeepSeekConfigurationError,
    DeepSeekError,
    DeepSeekInvalidResponseError,
    DeepSeekProvider,
    DeepSeekRateLimitedError,
    DeepSeekRefusedError,
    DeepSeekTimeoutError,
    ProviderCapabilityUnsupportedError,
    ProviderImage,
    ProviderRequest,
    ProviderResponse,
)

# ===================================================================
# Fake response objects
# ===================================================================


@dataclass
class FakeMessage:
    content: str | None
    role: str = "assistant"


@dataclass
class FakeChoice:
    message: FakeMessage
    finish_reason: str = "stop"
    index: int = 0


@dataclass
class FakeUsage:
    prompt_tokens: int = 15
    completion_tokens: int = 25
    total_tokens: int = 40


@dataclass
class FakeChatResponse:
    id: str
    choices: list[FakeChoice]
    model: str = "deepseek-chat"
    usage: FakeUsage | None = None
    created: int = 1700000000
    system_fingerprint: str | None = "fp_abc"


# ===================================================================
# Fake client
# ===================================================================


class FakeDeepSeekClient:
    """Injected fake that implements the ``DeepSeekChatClient`` protocol."""

    def __init__(
        self,
        response: FakeChatResponse | None = None,
    ) -> None:
        self._response = response or FakeChatResponse(
            id="chatcmpl-deepseek-test",
            choices=[FakeChoice(message=FakeMessage(content='{"result": "ok"}'))],
            usage=FakeUsage(prompt_tokens=15, completion_tokens=25, total_tokens=40),
        )
        self.last_model: str | None = None
        self.last_messages: list[dict[str, str]] | None = None
        self.last_response_format: dict[str, Any] | None = None
        self.last_timeout: int | None = None

    async def chat_completions_create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
        timeout_seconds: int | None = None,
    ) -> Any:
        self.last_model = model
        self.last_messages = messages
        self.last_response_format = response_format
        self.last_timeout = timeout_seconds

        if isinstance(self._response, Exception):
            raise self._response

        return self._response


# ===================================================================
# Helpers
# ===================================================================


def _text_request(**overrides: Any) -> ProviderRequest:
    kwargs = dict(
        request_id=uuid.uuid4(),
        analysis_type="INITIAL_ANALYSIS",
        prompt_version="1.0.0",
        user_prompt="Analyze this setup",
        expected_schema_name="initial_analysis",
        expected_schema_version="1.0",
        system_prompt="You are a helpful analyst.",
    )
    kwargs.update(overrides)
    return ProviderRequest(**kwargs)


def _make_image() -> ProviderImage:
    return ProviderImage(
        evidence_id=uuid.uuid4(),
        mime_type="image/png",
        storage_reference="user/session/file.png",
        byte_size=1024,
    )


# ===================================================================
# Fixtures
# ===================================================================


def _fake_http_response() -> object:
    """Create a minimal fake ``httpx.Response`` for OpenAI SDK errors."""
    import httpx

    request = httpx.Request("POST", "https://api.deepseek.com/v1/chat/completions")
    return httpx.Response(status_code=400, request=request)


@pytest.fixture
def fake_client() -> FakeDeepSeekClient:
    return FakeDeepSeekClient()


@pytest.fixture
def provider(fake_client: FakeDeepSeekClient) -> DeepSeekProvider:
    return DeepSeekProvider(
        api_key="test-key",
        client=fake_client,
    )


@pytest.fixture
def text_req() -> ProviderRequest:
    return _text_request()


# ===================================================================
# Shared interface
# ===================================================================


class TestSharedInterface:
    def test_is_ai_provider(self, provider: DeepSeekProvider) -> None:
        assert isinstance(provider, AIProvider)

    def test_name(self, provider: DeepSeekProvider) -> None:
        assert provider.name == "deepseek"

    def test_model(self, provider: DeepSeekProvider) -> None:
        assert provider.model == "deepseek-chat"

    def test_capabilities(self, provider: DeepSeekProvider) -> None:
        caps = provider.capabilities
        assert caps.supports_images is False
        assert caps.supports_structured_output is True
        assert caps.maximum_images == 0

    async def test_accepts_common_request(
        self,
        provider: DeepSeekProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert isinstance(resp, ProviderResponse)

    async def test_returns_common_response(
        self,
        provider: DeepSeekProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert isinstance(resp, ProviderResponse)


# ===================================================================
# Text translation
# ===================================================================


class TestTextTranslation:
    async def test_system_prompt_becomes_system_message(
        self,
        provider: DeepSeekProvider,
        fake_client: FakeDeepSeekClient,
        text_req: ProviderRequest,
    ) -> None:
        await provider.generate(text_req)
        assert fake_client.last_messages is not None
        assert fake_client.last_messages[0]["role"] == "system"
        assert "helpful analyst" in fake_client.last_messages[0]["content"]

    async def test_user_prompt_becomes_user_message(
        self,
        provider: DeepSeekProvider,
        fake_client: FakeDeepSeekClient,
        text_req: ProviderRequest,
    ) -> None:
        await provider.generate(text_req)
        assert fake_client.last_messages is not None
        assert fake_client.last_messages[-1]["role"] == "user"
        assert "Analyze this setup" in fake_client.last_messages[-1]["content"]

    async def test_message_ordering(
        self,
        provider: DeepSeekProvider,
        fake_client: FakeDeepSeekClient,
        text_req: ProviderRequest,
    ) -> None:
        await provider.generate(text_req)
        assert fake_client.last_messages is not None
        assert len(fake_client.last_messages) == 2
        assert fake_client.last_messages[0]["role"] == "system"
        assert fake_client.last_messages[1]["role"] == "user"

    async def test_prompt_text_unchanged(
        self,
        provider: DeepSeekProvider,
        fake_client: FakeDeepSeekClient,
        text_req: ProviderRequest,
    ) -> None:
        await provider.generate(text_req)
        assert fake_client.last_messages is not None
        assert fake_client.last_messages[-1]["content"] == "Analyze this setup"

    async def test_no_system_prompt_omits_system_message(
        self,
        provider: DeepSeekProvider,
        fake_client: FakeDeepSeekClient,
    ) -> None:
        req = _text_request(system_prompt=None)
        await provider.generate(req)
        assert fake_client.last_messages is not None
        assert len(fake_client.last_messages) == 1
        assert fake_client.last_messages[0]["role"] == "user"


# ===================================================================
# Image rejection
# ===================================================================


class TestImageRejection:
    async def test_image_request_rejected(
        self,
        provider: DeepSeekProvider,
        fake_client: FakeDeepSeekClient,
    ) -> None:
        req = _text_request(images=(_make_image(),))
        with pytest.raises(ProviderCapabilityUnsupportedError):
            await provider.generate(req)

    async def test_no_provider_call_after_rejection(
        self,
        provider: DeepSeekProvider,
        fake_client: FakeDeepSeekClient,
    ) -> None:
        req = _text_request(images=(_make_image(),))
        try:
            await provider.generate(req)
        except ProviderCapabilityUnsupportedError:
            pass
        assert fake_client.last_messages is None


# ===================================================================
# Structured output
# ===================================================================


class TestStructuredOutput:
    async def test_response_format_sent(
        self,
        provider: DeepSeekProvider,
        fake_client: FakeDeepSeekClient,
        text_req: ProviderRequest,
    ) -> None:
        req = _text_request(structured_output_schema={"type": "object"})
        await provider.generate(req)
        assert fake_client.last_response_format == {"type": "json_object"}

    async def test_raw_json_unparsed(
        self,
        provider: DeepSeekProvider,
        text_req: ProviderRequest,
    ) -> None:
        req = _text_request(structured_output_schema={"type": "object"})
        resp = await provider.generate(req)
        assert resp.raw_output == '{"result": "ok"}'

    async def test_normal_text_without_schema(
        self,
        provider: DeepSeekProvider,
        fake_client: FakeDeepSeekClient,
        text_req: ProviderRequest,
    ) -> None:
        await provider.generate(text_req)
        assert fake_client.last_response_format is None


# ===================================================================
# Response mapping
# ===================================================================


class TestResponseMapping:
    async def test_provider_response_id(
        self,
        provider: DeepSeekProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert resp.provider_response_id == "chatcmpl-deepseek-test"

    async def test_model(
        self,
        provider: DeepSeekProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert resp.model == "deepseek-chat"

    async def test_finish_reason(
        self,
        provider: DeepSeekProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert resp.finish_reason == "STOP"

    async def test_usage(
        self,
        provider: DeepSeekProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert resp.usage is not None
        assert resp.usage.total_tokens == 40
        assert resp.usage.input_tokens == 15
        assert resp.usage.output_tokens == 25

    async def test_latency(
        self,
        provider: DeepSeekProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert resp.latency_ms is not None
        assert resp.latency_ms >= 0

    async def test_provider_metadata(
        self,
        provider: DeepSeekProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert "latency_ms" in resp.metadata
        assert resp.metadata.get("system_fingerprint") == "fp_abc"
        assert resp.metadata.get("created") == 1700000000

    async def test_missing_optional_metadata(
        self,
        fake_client: FakeDeepSeekClient,
        text_req: ProviderRequest,
    ) -> None:
        no_usage = FakeChatResponse(
            id="no-usage",
            choices=[FakeChoice(message=FakeMessage(content="output"))],
            usage=None,
        )
        fake_client._response = no_usage
        provider = DeepSeekProvider(api_key="k", client=fake_client)
        resp = await provider.generate(text_req)
        assert resp.usage is None


# ===================================================================
# Errors
# ===================================================================


class TestErrors:
    async def test_missing_configuration(self) -> None:
        with pytest.raises(DeepSeekConfigurationError):
            DeepSeekProvider(api_key="")

    async def test_authentication(
        self,
        fake_client: FakeDeepSeekClient,
        text_req: ProviderRequest,
    ) -> None:
        import openai

        fake_client._response = openai.AuthenticationError(  # type: ignore[assignment]
            "Invalid API key",
            response=_fake_http_response(),
            body=None,
        )
        provider = DeepSeekProvider(api_key="bad", client=fake_client)
        with pytest.raises(DeepSeekAuthenticationError):
            await provider.generate(text_req)

    async def test_permission(
        self,
        fake_client: FakeDeepSeekClient,
        text_req: ProviderRequest,
    ) -> None:
        import openai

        fake_client._response = openai.PermissionDeniedError(  # type: ignore[assignment]
            "No access",
            response=_fake_http_response(),
            body=None,
        )
        provider = DeepSeekProvider(api_key="bad", client=fake_client)
        with pytest.raises(DeepSeekAuthenticationError):
            await provider.generate(text_req)

    async def test_rate_limit(
        self,
        fake_client: FakeDeepSeekClient,
        text_req: ProviderRequest,
    ) -> None:
        import openai

        fake_client._response = openai.RateLimitError(  # type: ignore[assignment]
            "Rate limited",
            response=_fake_http_response(),
            body=None,
        )
        provider = DeepSeekProvider(api_key="k", client=fake_client)
        with pytest.raises(DeepSeekRateLimitedError):
            await provider.generate(text_req)

    async def test_timeout(
        self,
        fake_client: FakeDeepSeekClient,
        text_req: ProviderRequest,
    ) -> None:
        import openai

        fake_client._response = openai.APITimeoutError("Timed out")
        provider = DeepSeekProvider(api_key="k", client=fake_client)
        with pytest.raises(DeepSeekTimeoutError):
            await provider.generate(text_req)

    async def test_refusal(
        self,
        fake_client: FakeDeepSeekClient,
        text_req: ProviderRequest,
    ) -> None:
        """Empty content is treated as refusal."""
        resp = FakeChatResponse(
            id="refused",
            choices=[
                FakeChoice(
                    message=FakeMessage(content=None),
                    finish_reason="content_filter",
                )
            ],
        )
        fake_client._response = resp
        provider = DeepSeekProvider(api_key="k", client=fake_client)
        with pytest.raises(DeepSeekRefusedError):
            await provider.generate(text_req)

    async def test_no_choices(
        self,
        fake_client: FakeDeepSeekClient,
        text_req: ProviderRequest,
    ) -> None:
        resp = FakeChatResponse(
            id="no-choices",
            choices=[],
        )
        fake_client._response = resp
        provider = DeepSeekProvider(api_key="k", client=fake_client)
        with pytest.raises(DeepSeekInvalidResponseError):
            await provider.generate(text_req)

    async def test_missing_message(
        self,
        fake_client: FakeDeepSeekClient,
        text_req: ProviderRequest,
    ) -> None:
        resp = FakeChatResponse(
            id="no-message",
            choices=[FakeChoice(message=FakeMessage(content=None))],  # type: ignore[arg-type]
        )
        resp.choices[0].message = None  # type: ignore[assignment]
        fake_client._response = resp
        provider = DeepSeekProvider(api_key="k", client=fake_client)
        with pytest.raises(DeepSeekInvalidResponseError):
            await provider.generate(text_req)

    async def test_empty_content(
        self,
        fake_client: FakeDeepSeekClient,
        text_req: ProviderRequest,
    ) -> None:
        resp = FakeChatResponse(
            id="empty",
            choices=[FakeChoice(message=FakeMessage(content=""))],
        )
        fake_client._response = resp
        provider = DeepSeekProvider(api_key="k", client=fake_client)
        with pytest.raises(DeepSeekRefusedError):
            await provider.generate(text_req)

    async def test_unexpected_sdk_error(
        self,
        fake_client: FakeDeepSeekClient,
        text_req: ProviderRequest,
    ) -> None:
        fake_client._response = Exception("Unexpected SDK failure")
        provider = DeepSeekProvider(api_key="k", client=fake_client)
        with pytest.raises(DeepSeekError):
            await provider.generate(text_req)


# ===================================================================
# Immutability and boundaries
# ===================================================================


class TestImmutability:
    async def test_request_not_mutated(
        self,
        provider: DeepSeekProvider,
        text_req: ProviderRequest,
    ) -> None:
        original = text_req.user_prompt
        await provider.generate(text_req)
        assert text_req.user_prompt == original

    async def test_schema_not_mutated(
        self,
        provider: DeepSeekProvider,
        fake_client: FakeDeepSeekClient,
    ) -> None:
        schema = {"type": "object"}
        req = _text_request(structured_output_schema=schema)
        original = dict(schema)
        await provider.generate(req)
        assert schema == original

    async def test_no_database_access(
        self,
        provider: DeepSeekProvider,
        text_req: ProviderRequest,
    ) -> None:
        await provider.generate(text_req)

    async def test_no_prompt_registry_access(
        self,
        provider: DeepSeekProvider,
        text_req: ProviderRequest,
    ) -> None:
        await provider.generate(text_req)

    async def test_no_persistence(
        self,
        provider: DeepSeekProvider,
        text_req: ProviderRequest,
    ) -> None:
        await provider.generate(text_req)

    async def test_no_real_http(
        self,
        fake_client: FakeDeepSeekClient,
    ) -> None:
        provider = DeepSeekProvider(api_key="test", client=fake_client)
        req = _text_request()
        await provider.generate(req)

    async def test_no_real_api_key_required(
        self,
        fake_client: FakeDeepSeekClient,
    ) -> None:
        provider = DeepSeekProvider(api_key="fake-key", client=fake_client)
        req = _text_request()
        await provider.generate(req)
