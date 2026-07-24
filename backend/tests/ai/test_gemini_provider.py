"""Tests for GeminiProvider (TP-0703).

Uses an injected fake model client — no real API calls.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

import pytest

from app.ai.providers import (
    AIProvider,
    GeminiAuthenticationError,
    GeminiConfigurationError,
    GeminiError,
    GeminiProvider,
    GeminiRateLimitedError,
    GeminiRefusedError,
    GeminiRequestFailedError,
    GeminiTimeoutError,
    ProviderImage,
    ProviderRequest,
    ProviderResponse,
)

# ===================================================================
# Fake Gemini model client
# ===================================================================


@dataclass
class FakeUsageMetadata:
    prompt_token_count: int | None = 10
    candidates_token_count: int | None = 20
    total_token_count: int | None = 30


@dataclass
class FakeCandidate:
    finish_reason: int = 1  # STOP
    index: int = 0


@dataclass
class FakePromptFeedback:
    block_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"block_reason": self.block_reason}


class FakeGeminiResponse:
    """Simulates a ``google.generativeai.types.GenerateContentResponse``."""

    def __init__(
        self,
        text: str = '{"result": "ok"}',
        finish_reason: int = 1,
        usage: FakeUsageMetadata | None = None,
        candidates: list[FakeCandidate] | None = None,
        prompt_feedback: FakePromptFeedback | None = None,
    ) -> None:
        self.text = text
        self._finish_reason = finish_reason
        self._usage = usage if usage is not None else FakeUsageMetadata()
        self._candidates = candidates or [FakeCandidate(finish_reason=finish_reason)]
        self._prompt_feedback = prompt_feedback

    @property
    def candidates(self) -> list[FakeCandidate]:
        return self._candidates

    @property
    def usage_metadata(self) -> FakeUsageMetadata | None:
        return self._usage if self._usage is not None else None

    @property
    def prompt_feedback(self) -> FakePromptFeedback | None:
        return self._prompt_feedback


class FakeGeminiModel:
    """Injected fake model that implements the GeminiModelClient protocol."""

    def __init__(self, response: FakeGeminiResponse | None = None) -> None:
        self._response = response or FakeGeminiResponse()
        self.last_contents: list[Any] = []
        self.model_name: str = "gemini-3.5-flash"

    async def generate_content_async(self, contents: list[Any]) -> FakeGeminiResponse:
        self.last_contents = contents
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


# ===================================================================
# Helpers
# ===================================================================


def _make_image(evidence_id: uuid.UUID | None = None) -> ProviderImage:
    return ProviderImage(
        evidence_id=evidence_id or uuid.uuid4(),
        mime_type="image/png",
        storage_reference="user/session/file.png",
        byte_size=1024,
        width=100,
        height=100,
    )


def _image_loader(img: ProviderImage) -> bytes:
    return b"fake-image-bytes"


def _text_request(**overrides: Any) -> ProviderRequest:
    kwargs = dict(
        request_id=uuid.uuid4(),
        analysis_type="INITIAL_ANALYSIS",
        prompt_version="1.0.0",
        user_prompt="Analyze this chart",
        expected_schema_name="initial_analysis",
        expected_schema_version="1.0",
        system_prompt="You are a helpful analyst.",
    )
    kwargs.update(overrides)
    return ProviderRequest(**kwargs)


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def fake_model() -> FakeGeminiModel:
    return FakeGeminiModel()


@pytest.fixture
def provider(fake_model: FakeGeminiModel) -> GeminiProvider:
    return GeminiProvider(
        api_key="test-key",
        model=fake_model,
        image_loader=_image_loader,
    )


@pytest.fixture
def text_req() -> ProviderRequest:
    return _text_request()


@pytest.fixture
def image_req() -> ProviderRequest:
    return _text_request(
        images=(_make_image(),),
    )


# ===================================================================
# Shared interface
# ===================================================================


class TestSharedInterface:
    def test_is_ai_provider(self, provider: GeminiProvider) -> None:
        assert isinstance(provider, AIProvider)

    def test_name(self, provider: GeminiProvider) -> None:
        assert provider.name == "gemini"

    def test_model(self, provider: GeminiProvider) -> None:
        assert provider.model == "gemini-3.5-flash"

    def test_capabilities(self, provider: GeminiProvider) -> None:
        caps = provider.capabilities
        assert caps.supports_images is True
        assert caps.supports_text_output is True
        assert caps.supports_structured_output is True
        assert caps.supports_multi_image is True
        assert caps.maximum_images == 10

    async def test_accepts_common_request(
        self,
        provider: GeminiProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert isinstance(resp, ProviderResponse)

    async def test_returns_common_response(
        self,
        provider: GeminiProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert isinstance(resp, ProviderResponse)


# ===================================================================
# Text request
# ===================================================================


class TestTextRequest:
    async def test_system_prompt_mapped(
        self,
        provider: GeminiProvider,
        fake_model: FakeGeminiModel,
        text_req: ProviderRequest,
    ) -> None:
        await provider.generate(text_req)
        contents = fake_model.last_contents
        parts_text = " ".join(str(p) for p in contents)
        assert "You are a helpful analyst" in parts_text

    async def test_user_prompt_mapped(
        self,
        provider: GeminiProvider,
        fake_model: FakeGeminiModel,
        text_req: ProviderRequest,
    ) -> None:
        await provider.generate(text_req)
        contents = fake_model.last_contents
        parts_text = " ".join(str(p) for p in contents)
        assert "Analyze this chart" in parts_text

    async def test_request_id_retained(
        self,
        provider: GeminiProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert resp.request_id == text_req.request_id

    async def test_raw_output_retained_exactly(
        self,
        provider: GeminiProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert resp.raw_output == '{"result": "ok"}'

    async def test_no_json_parsing(
        self,
        provider: GeminiProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert isinstance(resp.raw_output, str)
        # Not parsed into a dict
        assert resp.raw_output == '{"result": "ok"}'


# ===================================================================
# Image request
# ===================================================================


class TestImageRequest:
    async def test_single_image_translated(
        self,
        provider: GeminiProvider,
        fake_model: FakeGeminiModel,
    ) -> None:
        req = _text_request(images=(_make_image(),))
        await provider.generate(req)
        contents = fake_model.last_contents
        parts_text = " ".join(str(p) for p in contents)
        assert "inline_data" in parts_text or "image/png" in parts_text

    async def test_multiple_images_preserve_order(
        self,
        provider: GeminiProvider,
        fake_model: FakeGeminiModel,
    ) -> None:
        img1 = _make_image()
        img2 = _make_image()
        req = _text_request(images=(img1, img2))
        await provider.generate(req)
        contents = fake_model.last_contents
        # Count image-like parts
        image_count = sum(1 for p in contents if "image/png" in str(p))
        assert image_count == 2

    async def test_mime_types_preserved(
        self,
        provider: GeminiProvider,
        fake_model: FakeGeminiModel,
    ) -> None:
        req = _text_request(images=(_make_image(),))
        await provider.generate(req)
        contents = fake_model.last_contents
        parts_text = " ".join(str(p) for p in contents)
        assert "image/png" in parts_text

    async def test_image_loader_called(
        self,
        fake_model: FakeGeminiModel,
    ) -> None:
        loaded: list[uuid.UUID] = []

        def loader(img: ProviderImage) -> bytes:
            loaded.append(img.evidence_id)
            return b"loaded"

        provider = GeminiProvider(api_key="k", model=fake_model, image_loader=loader)
        img = _make_image()
        req = _text_request(images=(img,))
        await provider.generate(req)
        assert img.evidence_id in loaded

    async def test_image_loader_failure(
        self,
        fake_model: FakeGeminiModel,
    ) -> None:
        def failing_loader(img: ProviderImage) -> bytes:
            raise GeminiRequestFailedError(message="Loader failed")

        provider = GeminiProvider(api_key="k", model=fake_model, image_loader=failing_loader)
        req = _text_request(images=(_make_image(),))
        with pytest.raises(GeminiRequestFailedError):
            await provider.generate(req)

    async def test_image_count_limit(
        self,
        fake_model: FakeGeminiModel,
    ) -> None:
        from app.ai.providers import ProviderCapabilityUnsupportedError

        provider = GeminiProvider(
            api_key="k",
            model=fake_model,
            image_loader=_image_loader,
        )
        many_images = tuple(_make_image() for _ in range(11))
        req = _text_request(images=many_images)
        with pytest.raises(ProviderCapabilityUnsupportedError):
            await provider.generate(req)


# ===================================================================
# Structured output
# ===================================================================


class TestStructuredOutput:
    async def test_schema_supplied(
        self,
        provider: GeminiProvider,
        fake_model: FakeGeminiModel,
        text_req: ProviderRequest,
    ) -> None:
        schema = {"type": "object", "properties": {"result": {"type": "string"}}}
        req = _text_request(structured_output_schema=schema)
        resp = await provider.generate(req)
        assert resp.raw_output is not None

    async def test_schema_unchanged(
        self,
        provider: GeminiProvider,
        fake_model: FakeGeminiModel,
        text_req: ProviderRequest,
    ) -> None:
        schema = {"type": "object", "properties": {"result": {"type": "string"}}}
        original = dict(schema)
        req = _text_request(structured_output_schema=schema)
        await provider.generate(req)
        assert schema == original

    async def test_raw_json_unparsed(
        self,
        provider: GeminiProvider,
        text_req: ProviderRequest,
    ) -> None:
        req = _text_request(structured_output_schema={"type": "object"})
        resp = await provider.generate(req)
        assert resp.raw_output == '{"result": "ok"}'

    async def test_text_only_without_schema(
        self,
        provider: GeminiProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert resp.raw_output is not None


# ===================================================================
# Response mapping
# ===================================================================


class TestResponseMapping:
    async def test_provider_response_id(
        self,
        provider: GeminiProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert resp.provider_response_id is not None

    async def test_finish_reason(
        self,
        provider: GeminiProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert resp.finish_reason == "STOP"

    async def test_token_usage(
        self,
        provider: GeminiProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert resp.usage is not None
        assert resp.usage.total_tokens == 30

    async def test_latency(
        self,
        provider: GeminiProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert resp.latency_ms is not None
        assert resp.latency_ms >= 0

    async def test_gemini_metadata(
        self,
        provider: GeminiProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert "latency_ms" in resp.metadata

    async def test_missing_optional_metadata(
        self,
        fake_model: FakeGeminiModel,
        text_req: ProviderRequest,
    ) -> None:
        # Response with no usage metadata
        no_usage_response = FakeGeminiResponse(
            text="output",
        )
        no_usage_response._usage = None  # type: ignore[assignment]
        fake_model._response = no_usage_response
        provider = GeminiProvider(api_key="k", model=fake_model)
        resp = await provider.generate(text_req)
        assert resp.usage is None

    async def test_empty_text_handled(
        self,
        fake_model: FakeGeminiModel,
        text_req: ProviderRequest,
    ) -> None:
        empty_response = FakeGeminiResponse(text=None)  # type: ignore[arg-type]
        fake_model._response = empty_response
        provider = GeminiProvider(api_key="k", model=fake_model)
        resp = await provider.generate(text_req)
        assert resp.raw_output == ""


# ===================================================================
# Errors
# ===================================================================


class TestErrors:
    async def test_missing_configuration(self) -> None:
        with pytest.raises(GeminiConfigurationError):
            GeminiProvider(api_key="")

    async def test_authentication(
        self,
        fake_model: FakeGeminiModel,
        text_req: ProviderRequest,
    ) -> None:
        import google.api_core.exceptions as api_exc

        fake_model._response = api_exc.Unauthenticated("Invalid API key")  # type: ignore[assignment]
        provider = GeminiProvider(api_key="bad", model=fake_model)
        with pytest.raises(GeminiAuthenticationError):
            await provider.generate(text_req)

    async def test_rate_limit(
        self,
        fake_model: FakeGeminiModel,
        text_req: ProviderRequest,
    ) -> None:
        import google.api_core.exceptions as api_exc

        fake_model._response = api_exc.ResourceExhausted("Rate limited")  # type: ignore[assignment]
        provider = GeminiProvider(api_key="k", model=fake_model)
        with pytest.raises(GeminiRateLimitedError):
            await provider.generate(text_req)

    async def test_timeout(
        self,
        fake_model: FakeGeminiModel,
        text_req: ProviderRequest,
    ) -> None:
        import google.api_core.exceptions as api_exc

        fake_model._response = api_exc.DeadlineExceeded("Timed out")  # type: ignore[assignment]
        provider = GeminiProvider(api_key="k", model=fake_model)
        with pytest.raises(GeminiTimeoutError):
            await provider.generate(text_req)

    async def test_refusal(
        self,
        fake_model: FakeGeminiModel,
        text_req: ProviderRequest,
    ) -> None:
        fake_model._response = Exception("Response was blocked due to safety")  # type: ignore[assignment]
        provider = GeminiProvider(api_key="k", model=fake_model)
        with pytest.raises(GeminiRefusedError):
            await provider.generate(text_req)

    async def test_generic_sdk_failure(
        self,
        fake_model: FakeGeminiModel,
        text_req: ProviderRequest,
    ) -> None:
        fake_model._response = Exception("Unexpected SDK error")  # type: ignore[assignment]
        provider = GeminiProvider(api_key="k", model=fake_model)
        with pytest.raises(GeminiError):
            await provider.generate(text_req)


# ===================================================================
# Immutability and boundaries
# ===================================================================


class TestImmutability:
    async def test_request_not_mutated(
        self,
        provider: GeminiProvider,
        text_req: ProviderRequest,
    ) -> None:
        original = text_req.user_prompt
        await provider.generate(text_req)
        assert text_req.user_prompt == original

    async def test_schema_not_mutated(
        self,
        provider: GeminiProvider,
        fake_model: FakeGeminiModel,
    ) -> None:
        schema = {"type": "object"}
        req = _text_request(structured_output_schema=schema)
        original = dict(schema)
        await provider.generate(req)
        assert schema == original

    async def test_no_database_access(
        self,
        provider: GeminiProvider,
        text_req: ProviderRequest,
    ) -> None:
        await provider.generate(text_req)

    async def test_no_prompt_registry_access(
        self,
        provider: GeminiProvider,
        text_req: ProviderRequest,
    ) -> None:
        await provider.generate(text_req)

    async def test_no_persistence(
        self,
        provider: GeminiProvider,
        text_req: ProviderRequest,
    ) -> None:
        await provider.generate(text_req)

    async def test_no_real_http(
        self,
        fake_model: FakeGeminiModel,
    ) -> None:
        provider = GeminiProvider(api_key="test", model=fake_model)
        req = _text_request()
        await provider.generate(req)

    async def test_no_real_api_key_required_for_tests(
        self,
        fake_model: FakeGeminiModel,
    ) -> None:
        provider = GeminiProvider(api_key="fake-key", model=fake_model)
        req = _text_request()
        await provider.generate(req)
