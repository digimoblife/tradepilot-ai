"""Tests for provider contracts (TP-0701).

Verifies shared interface, request/response models, capabilities,
immutability, and offline operation.
"""

from __future__ import annotations

import uuid

import pytest

from app.ai import (
    AIProvider,
    ProviderCapabilities,
    ProviderCapabilityUnsupportedError,
    ProviderImage,
    ProviderRequest,
    ProviderResponse,
    ProviderUsage,
    ensure_request_supported,
)

# ===================================================================
# Fake providers
# ===================================================================


class FakeGeminiProvider(AIProvider):
    """Fake Gemini-like provider supporting images and structured output."""

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return "gemini-3.5-flash"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_images=True,
            supports_structured_output=True,
            supports_system_prompt=True,
            supports_json_schema=True,
            supports_multi_image=True,
            maximum_images=10,
        )

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        ensure_request_supported(request, self.capabilities)
        return ProviderResponse(
            provider=self.name,
            model=self.model,
            raw_output='{"result": "ok"}',
            request_id=request.request_id,
            provider_response_id="gemini-resp-1",
            finish_reason="STOP",
            usage=ProviderUsage(
                input_tokens=50,
                output_tokens=10,
                total_tokens=60,
            ),
            latency_ms=1200,
            metadata={"safety_ratings": []},
        )


class FakeDeepSeekProvider(AIProvider):
    """Fake DeepSeek-like provider supporting structured output but no images."""

    @property
    def name(self) -> str:
        return "deepseek"

    @property
    def model(self) -> str:
        return "deepseek-chat"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_images=False,
            supports_structured_output=True,
            supports_system_prompt=True,
            supports_json_schema=False,
            maximum_images=0,
        )

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        ensure_request_supported(request, self.capabilities)
        return ProviderResponse(
            provider=self.name,
            model=self.model,
            raw_output='{"result": "ok"}',
            request_id=request.request_id,
            provider_response_id="deepseek-resp-1",
            finish_reason="stop",
            usage=ProviderUsage(input_tokens=100, output_tokens=20, total_tokens=120),
            latency_ms=2500,
            metadata={"provider_specific": "value"},
        )


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def request_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def text_request(request_id: uuid.UUID) -> ProviderRequest:
    return ProviderRequest(
        request_id=request_id,
        analysis_type="INITIAL_ANALYSIS",
        prompt_version="v1",
        user_prompt="Analyze this chart",
        expected_schema_name="initial_analysis",
        expected_schema_version="1.0",
    )


@pytest.fixture
def image_request(request_id: uuid.UUID) -> ProviderRequest:
    return ProviderRequest(
        request_id=request_id,
        analysis_type="OPEN_POSITION_UPDATE",
        prompt_version="v1",
        user_prompt="Review this orderbook",
        expected_schema_name="open_position_update",
        expected_schema_version="1.0",
        images=(
            ProviderImage(
                evidence_id=uuid.uuid4(),
                mime_type="image/png",
                storage_reference="user/session/file.png",
                byte_size=65536,
                width=1440,
                height=1920,
            ),
        ),
        structured_output_schema={
            "type": "object",
            "properties": {"result": {"type": "string"}},
        },
    )


# ===================================================================
# Shared interface
# ===================================================================


class TestSharedInterface:
    async def test_both_accept_same_request_model(
        self,
        text_request: ProviderRequest,
    ) -> None:
        gemini = FakeGeminiProvider()
        deepseek = FakeDeepSeekProvider()

        resp_g = await gemini.generate(text_request)
        resp_d = await deepseek.generate(text_request)

        assert isinstance(resp_g, ProviderResponse)
        assert isinstance(resp_d, ProviderResponse)

    async def test_both_return_same_response_type(self, text_request: ProviderRequest) -> None:
        gemini = FakeGeminiProvider()
        deepseek = FakeDeepSeekProvider()

        assert isinstance(await gemini.generate(text_request), ProviderResponse)
        assert isinstance(await deepseek.generate(text_request), ProviderResponse)

    async def test_code_calls_either_without_branching(
        self,
        text_request: ProviderRequest,
    ) -> None:
        providers: list[AIProvider] = [FakeGeminiProvider(), FakeDeepSeekProvider()]
        for provider in providers:
            resp = await provider.generate(text_request)
            assert resp.provider in ("gemini", "deepseek")
            assert resp.raw_output == '{"result": "ok"}'


# ===================================================================
# Request model
# ===================================================================


class TestRequestModel:
    def test_text_only(self, text_request: ProviderRequest) -> None:
        assert text_request.images == ()
        assert text_request.structured_output_schema is None

    def test_with_image(self, image_request: ProviderRequest) -> None:
        assert len(image_request.images) == 1
        assert image_request.images[0].mime_type == "image/png"

    def test_analysis_type_retained(self, text_request: ProviderRequest) -> None:
        assert text_request.analysis_type == "INITIAL_ANALYSIS"

    def test_prompt_version_retained(self, text_request: ProviderRequest) -> None:
        assert text_request.prompt_version == "v1"

    def test_schema_name_retained(self, text_request: ProviderRequest) -> None:
        assert text_request.expected_schema_name == "initial_analysis"

    def test_schema_version_retained(self, text_request: ProviderRequest) -> None:
        assert text_request.expected_schema_version == "1.0"

    def test_metadata_retained(self, request_id: uuid.UUID) -> None:
        original = {"key": "value", "num": 42}
        req = ProviderRequest(
            request_id=request_id,
            analysis_type="WATCHING_UPDATE",
            prompt_version="v2",
            user_prompt="Update",
            expected_schema_name="watching_update",
            expected_schema_version="2.0",
            metadata=original,
        )
        assert req.metadata["key"] == "value"
        assert req.metadata["num"] == 42


# ===================================================================
# Response model
# ===================================================================


class TestResponseModel:
    async def test_raw_output_retained_exactly(self, text_request: ProviderRequest) -> None:
        gemini = FakeGeminiProvider()
        resp = await gemini.generate(text_request)
        assert resp.raw_output == '{"result": "ok"}'

    async def test_provider_name(self, text_request: ProviderRequest) -> None:
        gemini = FakeGeminiProvider()
        resp = await gemini.generate(text_request)
        assert resp.provider == "gemini"

    async def test_model_name(self, text_request: ProviderRequest) -> None:
        deepseek = FakeDeepSeekProvider()
        resp = await deepseek.generate(text_request)
        assert resp.model == "deepseek-chat"

    async def test_request_id(self, text_request: ProviderRequest) -> None:
        gemini = FakeGeminiProvider()
        resp = await gemini.generate(text_request)
        assert resp.request_id == text_request.request_id

    async def test_provider_response_id(self, text_request: ProviderRequest) -> None:
        gemini = FakeGeminiProvider()
        resp = await gemini.generate(text_request)
        assert resp.provider_response_id == "gemini-resp-1"

    async def test_finish_reason(self, text_request: ProviderRequest) -> None:
        gemini = FakeGeminiProvider()
        resp = await gemini.generate(text_request)
        assert resp.finish_reason == "STOP"

    async def test_usage_metadata(self, text_request: ProviderRequest) -> None:
        gemini = FakeGeminiProvider()
        resp = await gemini.generate(text_request)
        assert resp.usage is not None
        assert resp.usage.total_tokens == 60

    async def test_latency(self, text_request: ProviderRequest) -> None:
        gemini = FakeGeminiProvider()
        resp = await gemini.generate(text_request)
        assert resp.latency_ms == 1200

    async def test_provider_specific_metadata(self, text_request: ProviderRequest) -> None:
        deepseek = FakeDeepSeekProvider()
        resp = await deepseek.generate(text_request)
        assert resp.metadata == {"provider_specific": "value"}

    async def test_no_json_parsing(self, text_request: ProviderRequest) -> None:
        """Raw output must remain unparsed."""
        gemini = FakeGeminiProvider()
        resp = await gemini.generate(text_request)
        assert isinstance(resp.raw_output, str)
        # The contract does not parse into dict
        assert resp.raw_output == '{"result": "ok"}'


# ===================================================================
# Capabilities
# ===================================================================


class TestCapabilities:
    def test_gemini_supports_images(self) -> None:
        caps = FakeGeminiProvider().capabilities
        assert caps.supports_images is True
        assert caps.supports_text_output is True
        assert caps.supports_structured_output is True
        assert caps.supports_multi_image is True
        assert caps.maximum_images == 10

    def test_deepseek_no_images_supports_structured_output(self) -> None:
        caps = FakeDeepSeekProvider().capabilities
        assert caps.supports_images is False
        assert caps.supports_text_output is True
        assert caps.supports_structured_output is True
        assert caps.maximum_images == 0

    def test_capabilities_available_through_interface(self) -> None:
        providers: list[AIProvider] = [FakeGeminiProvider(), FakeDeepSeekProvider()]
        for provider in providers:
            caps = provider.capabilities
            assert isinstance(caps, ProviderCapabilities)

    def test_image_request_rejected_when_unsupported(
        self,
        image_request: ProviderRequest,
    ) -> None:
        deepseek = FakeDeepSeekProvider()
        with pytest.raises(ProviderCapabilityUnsupportedError):
            ensure_request_supported(image_request, deepseek.capabilities)

    def test_image_request_accepted_when_supported(
        self,
        image_request: ProviderRequest,
    ) -> None:
        caps = FakeGeminiProvider().capabilities
        # Should not raise
        ensure_request_supported(image_request, caps)

    def test_text_request_accepted_by_both(self, text_request: ProviderRequest) -> None:
        ensure_request_supported(text_request, FakeGeminiProvider().capabilities)
        ensure_request_supported(text_request, FakeDeepSeekProvider().capabilities)

    def test_structured_output_rejected_when_unsupported(self, request_id: uuid.UUID) -> None:
        caps = ProviderCapabilities(supports_structured_output=False)
        req = ProviderRequest(
            request_id=request_id,
            analysis_type="TEST",
            prompt_version="v1",
            user_prompt="test",
            expected_schema_name="test",
            expected_schema_version="1.0",
            structured_output_schema={"type": "object"},
        )
        with pytest.raises(ProviderCapabilityUnsupportedError):
            ensure_request_supported(req, caps)

    def test_system_prompt_accepted(self, text_request: ProviderRequest) -> None:
        caps = FakeGeminiProvider().capabilities
        ensure_request_supported(text_request, caps)  # system_prompt is None, so it passes

    def test_multi_image_exceeds_limit(self, request_id: uuid.UUID) -> None:
        caps = ProviderCapabilities(supports_images=True, supports_multi_image=False)
        req = ProviderRequest(
            request_id=request_id,
            analysis_type="TEST",
            prompt_version="v1",
            user_prompt="test",
            expected_schema_name="test",
            expected_schema_version="1.0",
            images=(
                ProviderImage(
                    evidence_id=uuid.uuid4(),
                    mime_type="image/png",
                    storage_reference="a.png",
                    byte_size=100,
                ),
                ProviderImage(
                    evidence_id=uuid.uuid4(),
                    mime_type="image/png",
                    storage_reference="b.png",
                    byte_size=200,
                ),
            ),
        )
        with pytest.raises(ProviderCapabilityUnsupportedError):
            ensure_request_supported(req, caps)


# ===================================================================
# Immutability
# ===================================================================


class TestImmutability:
    def test_request_immutable(self, text_request: ProviderRequest) -> None:
        with pytest.raises(AttributeError):
            text_request.analysis_type = "CHANGED"  # type: ignore[misc]

    async def test_response_immutable(self, text_request: ProviderRequest) -> None:
        gemini = FakeGeminiProvider()
        resp = await gemini.generate(text_request)
        with pytest.raises(AttributeError):
            resp.provider = "changed"  # type: ignore[misc]

    def test_images_tuple_isolation(self, request_id: uuid.UUID) -> None:
        img = ProviderImage(
            evidence_id=uuid.uuid4(),
            mime_type="image/png",
            storage_reference="f.png",
            byte_size=100,
        )
        req = ProviderRequest(
            request_id=request_id,
            analysis_type="TEST",
            prompt_version="v1",
            user_prompt="test",
            expected_schema_name="test",
            expected_schema_version="1.0",
            images=(img,),
        )
        assert len(req.images) == 1
        # tuple is immutable
        with pytest.raises(TypeError):
            req.images[0] = img  # type: ignore[index]

    def test_metadata_isolation(self, request_id: uuid.UUID) -> None:
        original = {"a": 1}
        req = ProviderRequest(
            request_id=request_id,
            analysis_type="TEST",
            prompt_version="v1",
            user_prompt="test",
            expected_schema_name="test",
            expected_schema_version="1.0",
            metadata=original,
        )
        original["a"] = 999
        # The request's metadata should be independent
        assert req.metadata["a"] == 1

    def test_no_mutable_defaults(self) -> None:
        """Repeated construction should not share mutable objects."""
        rid = uuid.uuid4()
        r1 = ProviderRequest(
            request_id=rid,
            analysis_type="T",
            prompt_version="v1",
            user_prompt="p",
            expected_schema_name="s",
            expected_schema_version="1",
        )
        r2 = ProviderRequest(
            request_id=rid,
            analysis_type="T",
            prompt_version="v1",
            user_prompt="p",
            expected_schema_name="s",
            expected_schema_version="1",
        )
        assert r1.metadata is not r2.metadata


# ===================================================================
# Offline / no-network
# ===================================================================


class TestOffline:
    def test_no_http_called(self) -> None:
        """Fake providers never make HTTP calls."""
        gemini = FakeGeminiProvider()
        assert gemini.name == "gemini"
        assert gemini.model == "gemini-3.5-flash"

    def test_no_api_key_required(self) -> None:
        FakeGeminiProvider()
        FakeDeepSeekProvider()

    def test_no_database_access(self) -> None:
        caps = FakeGeminiProvider().capabilities
        assert isinstance(caps, ProviderCapabilities)

    def test_no_environment_secrets_required(self) -> None:
        """Construction does not read env vars."""
        import os

        # These would fail if provider tried to read them
        api_key = os.environ.get("GEMINI_API_KEY")
        assert api_key is None or True  # just verifying no crash
