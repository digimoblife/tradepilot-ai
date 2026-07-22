"""Shared provider contract test suite (TP-1503).

Tests that both Gemini and DeepSeek adapters follow the same application-level
behavior and response contract using mocked provider responses.

Each test is parametrized over both adapters so the same contract expectation
is verified for each.

No real provider APIs are called.  No network access occurs.
"""

from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ai.parsing.json_extractor import (
    ExtractionError,
    extract_json_object,
)
from app.ai.parsing.json_parser import ParseError, extract_and_parse_json
from app.ai.providers.base import AIProvider
from app.ai.providers.deepseek import DeepSeekProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.models import ProviderImage, ProviderRequest, ProviderResponse
from app.schemas.manifest import load_production_manifest
from app.schemas.registry import LocalSchemaRegistry
from app.validation.json_schema import JsonSchemaValidationService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _schema_service() -> JsonSchemaValidationService:
    """Build a JsonSchemaValidationService from production schemas."""
    pkg = Path(tempfile.mkdtemp()) / "production" / "v1"
    pkg.mkdir(parents=True, exist_ok=True)
    prod = Path(__file__).resolve().parent.parent.parent / "schemas" / "production" / "v1"
    for f in prod.iterdir():
        if f.is_file():
            shutil.copy2(f, pkg / f.name)
    manifest = load_production_manifest(pkg)
    registry = LocalSchemaRegistry(manifest, pkg)
    return JsonSchemaValidationService(registry)


def make_request(
    request_id: uuid.UUID | None = None,
    **overrides: Any,
) -> ProviderRequest:
    rid = request_id or uuid.uuid4()
    base = {
        "request_id": rid,
        "analysis_type": "INITIAL_ANALYSIS",
        "prompt_version": "1.0.0",
        "user_prompt": "Analyze this chart.",
        "expected_schema_name": "initial_analysis",
        "expected_schema_version": "1.0.0",
    }
    base.update(overrides)
    return ProviderRequest(**base)  # type: ignore[arg-type]


def make_response(
    provider: AIProvider,
    request: ProviderRequest,
    raw_output: str = '{"result": "ok"}',
    **overrides: Any,
) -> ProviderResponse:
    base = {
        "provider": provider.name,
        "model": provider.model,
        "raw_output": raw_output,
        "request_id": request.request_id,
    }
    base.update(overrides)
    return ProviderResponse(**base)  # type: ignore[arg-type]


def _mock_gemini_client(raw_output: str) -> MagicMock:
    """Build a mock GeminiModelClient that returns *raw_output*."""
    mock_client = MagicMock()
    response = MagicMock()
    response.text = raw_output
    response.prompt_feedback = None
    candidate = MagicMock()
    candidate.finish_reason = 1  # STOP
    candidate.content.parts = [MagicMock(text=raw_output)]
    response.candidates = [candidate]
    usage = MagicMock()
    usage.prompt_token_count = 50
    usage.candidates_token_count = 10
    usage.total_token_count = 60
    mock_client.count_tokens = AsyncMock(return_value=MagicMock(total_tokens=60))
    mock_client.generate_content_async = AsyncMock(return_value=response)
    return mock_client


def _mock_deepseek_client(raw_output: str) -> MagicMock:
    """Build a mock DeepSeekChatClient that returns *raw_output*."""
    mock_client = MagicMock()
    choice = MagicMock(spec=["message", "finish_reason"])
    choice.message = MagicMock(spec=["content"])
    choice.message.content = raw_output
    choice.finish_reason = "stop"
    response = MagicMock(spec=["choices", "id", "usage", "model", "created"])
    response.choices = [choice]
    response.id = "chatcmpl-mock"
    response.model = "deepseek-chat"
    response.created = 1234567890
    usage = MagicMock(spec=["prompt_tokens", "completion_tokens", "total_tokens"])
    usage.prompt_tokens = 100
    usage.completion_tokens = 20
    usage.total_tokens = 120
    response.usage = usage
    mock_client.chat_completions_create = AsyncMock(return_value=response)
    return mock_client


# ---------------------------------------------------------------------------
# Provider fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def request_id() -> uuid.UUID:
    return uuid.UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def text_request(request_id: uuid.UUID) -> ProviderRequest:
    return make_request(request_id=request_id)


@pytest.fixture
def image_request(request_id: uuid.UUID) -> ProviderRequest:
    return make_request(
        request_id=request_id,
        images=(
            ProviderImage(
                evidence_id=uuid.uuid4(),
                mime_type="image/png",
                storage_reference="session/file.png",
                byte_size=65536,
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Adapter helpers – parametrized over both providers
# ---------------------------------------------------------------------------


def _gemini(raw_output: str = '{"result": "ok"}') -> GeminiProvider:
    return GeminiProvider(
        api_key="test-key",
        model_name="gemini-2.0-flash",
        model=_mock_gemini_client(raw_output),
    )


def _deepseek(raw_output: str = '{"result": "ok"}') -> DeepSeekProvider:
    return DeepSeekProvider(
        api_key="test-key",
        model_name="deepseek-chat",
        client=_mock_deepseek_client(raw_output),
    )


PROVIDER_BUILDERS = [
    pytest.param(_gemini, id="gemini"),
    pytest.param(_deepseek, id="deepseek"),
]


# ===================================================================
# 1. Valid JSON response
# ===================================================================


class TestValidJsonResponse:
    """Provider returns valid JSON payload — contract validation succeeds."""

    @pytest.mark.parametrize("builder", PROVIDER_BUILDERS)
    async def test_generate_returns_response(self, builder, text_request):
        provider = builder()
        resp = await provider.generate(text_request)
        assert isinstance(resp, ProviderResponse)
        assert resp.provider == provider.name
        assert resp.model == provider.model

    @pytest.mark.parametrize("builder", PROVIDER_BUILDERS)
    async def test_raw_output_is_string(self, builder, text_request):
        provider = builder()
        resp = await provider.generate(text_request)
        assert isinstance(resp.raw_output, str)

    @pytest.mark.parametrize("builder", PROVIDER_BUILDERS)
    async def test_raw_output_can_be_parsed(self, builder, text_request):
        provider = builder('{"test": "value", "number": 42}')
        resp = await provider.generate(text_request)
        parsed = extract_and_parse_json(resp.raw_output)
        assert parsed["test"] == "value"
        assert parsed["number"] == 42


# ===================================================================
# 2. Fenced JSON response
# ===================================================================


class TestFencedJsonResponse:
    """Provider returns JSON wrapped in Markdown fences."""

    @pytest.mark.parametrize("builder", PROVIDER_BUILDERS)
    async def test_fenced_json_is_extracted(self, builder, text_request):
        fenced = '```json\n{"key": "value"}\n```'
        provider = builder(fenced)
        resp = await provider.generate(text_request)
        extracted = extract_json_object(resp.raw_output)
        assert extracted.strip() == '{"key": "value"}'

    @pytest.mark.parametrize("builder", PROVIDER_BUILDERS)
    async def test_fenced_json_parses_correctly(self, builder, text_request):
        fenced = '```json\n{"a": 1, "b": 2}\n```'
        provider = builder(fenced)
        resp = await provider.generate(text_request)
        parsed = extract_and_parse_json(resp.raw_output)
        assert parsed["a"] == 1
        assert parsed["b"] == 2


# ===================================================================
# 3. Commentary response
# ===================================================================


class TestCommentaryResponse:
    """Provider returns JSON with surrounding explanatory text."""

    @pytest.mark.parametrize("builder", PROVIDER_BUILDERS)
    async def test_commentary_before_json(self, builder, text_request):
        with_comment = 'Here is the analysis:\n{"result": "positive"}'
        provider = builder(with_comment)
        resp = await provider.generate(text_request)
        parsed = extract_and_parse_json(resp.raw_output)
        assert parsed["result"] == "positive"

    @pytest.mark.parametrize("builder", PROVIDER_BUILDERS)
    async def test_commentary_after_json(self, builder, text_request):
        with_comment = '{"result": "positive"}\n\nThis means the outlook is good.'
        provider = builder(with_comment)
        resp = await provider.generate(text_request)
        parsed = extract_and_parse_json(resp.raw_output)
        assert parsed["result"] == "positive"


# ===================================================================
# 4. Missing property
# ===================================================================


class TestMissingProperty:
    """Provider response missing required schema fields — schema validation fails."""

    @pytest.mark.parametrize("builder", PROVIDER_BUILDERS)
    async def test_missing_required_field_rejected(self, builder, text_request):
        missing = '{"metadata": {"analysis_id": "abc"}}'
        provider = builder(missing)
        resp = await provider.generate(text_request)
        parsed = extract_and_parse_json(resp.raw_output)
        assert "metadata" in parsed
        # Schema validation should reject this as incomplete
        svc = _schema_service()
        result = svc.validate_by_name(parsed, "initial_analysis", "1.0.0")
        assert not result.valid
        codes = {i.code for i in result.issues}
        assert "SCHEMA_REQUIRED_FIELD_MISSING" in codes


# ===================================================================
# 5. Invalid enum
# ===================================================================


class TestInvalidEnum:
    """Provider returns unsupported enum values — schema validation fails."""

    @pytest.mark.parametrize("builder", PROVIDER_BUILDERS)
    async def test_invalid_enum_rejected(self, builder, text_request):
        invalid = (
            '{"metadata": {"analysis_id": "12345678-1234-5678-1234-567812345678",'
            '"session_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",'
            '"analysis_type": "INVALID_TYPE",'
            '"ticker": "BBRI", "company_name": "Test",'
            '"analysis_timestamp": "2026-07-18T08:30:00Z",'
            '"language": "id",'
            '"schema": {"schema_name": "initial_analysis", "schema_version": "1.0.0"},'
            '"prompt_version": "1.0.0", "provider": "GEMINI", "model": "test"}}'
        )
        provider = builder(invalid)
        resp = await provider.generate(text_request)
        parsed = extract_and_parse_json(resp.raw_output)
        # Schema validation should reject the invalid enum
        svc = _schema_service()
        result = svc.validate_by_name(parsed, "initial_analysis", "1.0.0")
        assert not result.valid
        codes = {i.code for i in result.issues}
        assert "SCHEMA_ENUM_INVALID" in codes


# ===================================================================
# 6. Extra property
# ===================================================================


class TestExtraProperty:
    """Provider returns unexpected properties — schema strictness verified."""

    @pytest.mark.parametrize("builder", PROVIDER_BUILDERS)
    async def test_extra_property_returned_and_parsed(self, builder, text_request):
        with_extra = (
            '{"metadata": {"analysis_id": "12345678-1234-5678-1234-567812345678",'
            '"session_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",'
            '"analysis_type": "INITIAL_ANALYSIS",'
            '"ticker": "BBRI", "company_name": "Test",'
            '"analysis_timestamp": "2026-07-18T08:30:00Z",'
            '"language": "id",'
            '"schema": {"schema_name": "initial_analysis", "schema_version": "1.0.0"},'
            '"prompt_version": "1.0.0", "provider": "GEMINI", "model": "test"},'
            '"unexpected_field": "should not exist"}'
        )
        provider = builder(with_extra)
        resp = await provider.generate(text_request)
        parsed = extract_and_parse_json(resp.raw_output)
        assert parsed["unexpected_field"] == "should not exist"
        # Schema validation should reject extra property
        svc = _schema_service()
        result = svc.validate_by_name(parsed, "initial_analysis", "1.0.0")
        assert not result.valid
        codes = {i.code for i in result.issues}
        assert "SCHEMA_UNKNOWN_PROPERTY" in codes


# ===================================================================
# 7. Malformed JSON
# ===================================================================


class TestMalformedJson:
    """Provider returns invalid JSON — parsing failure detected."""

    @pytest.mark.parametrize("builder", PROVIDER_BUILDERS)
    async def test_malformed_json_raises(self, builder, text_request):
        provider = builder('{"broken": "json"')
        resp = await provider.generate(text_request)
        with pytest.raises((ExtractionError, ParseError)):
            extract_and_parse_json(resp.raw_output)

    @pytest.mark.parametrize("builder", PROVIDER_BUILDERS)
    async def test_empty_string_raises(self, builder, text_request):
        provider = builder("")
        try:
            resp = await provider.generate(text_request)
            with pytest.raises((ExtractionError, ParseError)):
                extract_and_parse_json(resp.raw_output)
        except Exception as e:
            # Provider may reject empty content during generate()
            code = getattr(e, "code", None)
            assert code is not None, f"Expected error with code, got {type(e).__name__}"


# ===================================================================
# 8. Refusal
# ===================================================================


class TestRefusal:
    """Provider refuses or cannot answer — response classification."""

    @pytest.mark.parametrize("builder", PROVIDER_BUILDERS)
    async def test_empty_content_is_refusal(self, builder, text_request):
        provider = builder("")
        try:
            resp = await provider.generate(text_request)
            with pytest.raises((ExtractionError, ParseError)):
                extract_and_parse_json(resp.raw_output)
        except Exception as e:
            code = getattr(e, "code", None)
            assert code is not None, f"Expected error with code, got {type(e).__name__}"

    @pytest.mark.parametrize("builder", PROVIDER_BUILDERS)
    async def test_non_json_refusal_is_detected(self, builder, text_request):
        provider = builder("I cannot provide that analysis.")
        resp = await provider.generate(text_request)
        # Non-JSON text should not parse as JSON
        with pytest.raises((ExtractionError, ParseError)):
            extract_and_parse_json(resp.raw_output)


# ===================================================================
# 9. State conflict
# ===================================================================


class TestStateConflict:
    """Provider returns payload conflicting with canonical Trade State."""

    @pytest.mark.parametrize("builder", PROVIDER_BUILDERS)
    async def test_entry_mismatch_detected(self, builder, text_request):
        provider = builder(
            '{"position_assessment": {"entry_price": 9999,'
            '"current_price": 100, "remaining_quantity": 100,'
            '"active_stop_loss": null, "active_target": null,'
            '"health": "HEALTHY", "summary": "Test"}}'
        )
        resp = await provider.generate(text_request)
        from app.validation.state_consistency import validate_state_consistency

        parsed = extract_and_parse_json(resp.raw_output)
        canonical = {
            "session_id": str(text_request.request_id),
            "ticker": "BBRI",
            "position": {
                "position_status": "OPEN",
                "entry_price": "2800",
                "original_quantity": "100",
                "remaining_quantity": "100",
                "active_stop_loss": None,
                "active_target": None,
            },
        }
        result = validate_state_consistency(parsed, canonical)
        assert not result.valid
        codes = {i.code for i in result.issues}
        assert "STATE_ENTRY_PRICE_MISMATCH" in codes


# ===================================================================
# 10. Repair
# ===================================================================


class TestRepair:
    """Actual repair flow via ProviderRepairService."""

    @pytest.mark.parametrize("builder", PROVIDER_BUILDERS)
    async def test_repair_service_invoked_and_succeeds(self, builder, text_request):
        """ProviderRepairService is called, provider fixes output, schema passes."""
        import json

        from app.ai.repair import ProviderRepairService

        svc = _schema_service()

        # Load a valid fixture to use as the repair provider response
        fdir = Path(__file__).resolve().parent.parent.parent
        fixt_path = fdir / "schemas" / "fixtures" / "valid" / "v1" / "initial_analysis.valid.json"
        valid_raw = fixt_path.read_text()
        valid_payload = json.loads(valid_raw)
        assert svc.validate_by_name(valid_payload, "initial_analysis", "1.0.0").valid

        # --- Step 1: provider returns invalid output ---
        # Use a provider configured with the INVALID output for the first call.
        # The repair service will call provider.generate() again with a repair prompt.
        # Our mock always returns the same raw_output, so we configure it with valid data
        # but the ORIGINAL response that we PASS IN to repair() will be the invalid one.

        provider = builder(valid_raw)
        original_resp = ProviderResponse(
            provider=provider.name,
            model=provider.model,
            raw_output='{"metadata": {"analysis_id": "bad"}}',
            request_id=text_request.request_id,
        )

        # Parse the original invalid output — it's structurally valid JSON
        original_parsed = extract_and_parse_json(original_resp.raw_output)

        # Schema validation rejects the original
        schema_result = svc.validate_by_name(original_parsed, "initial_analysis", "1.0.0")
        assert not schema_result.valid
        codes = {i.code for i in schema_result.issues}
        assert "SCHEMA_REQUIRED_FIELD_MISSING" in codes

        validation_errors = schema_result.issues
        canonical_facts = {"ticker": "BBRI", "session_id": "test"}

        def validate_fn(p: dict[str, object]) -> tuple[bool, tuple]:
            result = svc.validate_by_name(p, "initial_analysis", "1.0.0")
            return result.valid, tuple(result.issues)

        # --- Step 2: invoke ProviderRepairService ---
        repair_svc = ProviderRepairService()
        repair_result = await repair_svc.repair(
            provider=provider,
            original_request=text_request,
            original_response=original_resp,
            validation_errors=validation_errors,
            canonical_facts=canonical_facts,
            validate=validate_fn,
            max_attempts=3,
        )

        # --- Step 3: verify repair result ---
        assert repair_result is not None
        assert len(repair_result.attempts) == 1
        assert repair_result.attempts[0].attempt_number == 1

        # The repaired payload passes schema
        assert svc.validate_by_name(dict(repair_result.payload), "initial_analysis", "1.0.0").valid

        # The repaired output is what the mock provider returned (the valid fixture)
        assert repair_result.payload.get("metadata", {}).get("ticker") == "BBRI"

        # Canonical facts remain unchanged
        assert canonical_facts == {"ticker": "BBRI", "session_id": "test"}


# ===================================================================
# 11. Fallback
# ===================================================================


class TestFallback:
    """Primary provider failure → fallback invoked → valid payload."""

    async def test_gemini_fails_deepseek_fallback_succeeds(self, text_request):
        """Gemini fails, DeepSeek fallback returns valid payload."""
        from app.ai.providers.router import ProviderRouter

        gemini = _gemini('{"invalid: broken')
        deepseek = _deepseek('{"result": "ok", "value": 42}')
        router = ProviderRouter()
        providers = {"gemini": gemini, "deepseek": deepseek}

        result = await router.generate_validated(
            request=text_request,
            providers=providers,
            provider_order=["gemini", "deepseek"],
            validate=lambda p: (True, ()),
            canonical_facts={},
            max_repair_attempts=1,
        )

        assert result.provider == "deepseek"
        assert result.fallback_used
        assert result.payload["result"] == "ok"
        assert result.payload["value"] == 42
        assert len(result.attempts) >= 2

    async def test_gemini_succeeds_no_fallback(self, text_request):
        """Gemini response is valid — no fallback needed."""
        from app.ai.providers.router import ProviderRouter

        gemini = _gemini('{"status": "ok"}')
        deepseek = _deepseek('{"status": "should-not-be-used"}')
        router = ProviderRouter()
        providers = {"gemini": gemini, "deepseek": deepseek}

        result = await router.generate_validated(
            request=text_request,
            providers=providers,
            provider_order=["gemini", "deepseek"],
            validate=lambda p: (True, ()),
            canonical_facts={},
            max_repair_attempts=1,
        )

        assert result.provider == "gemini"
        assert not result.fallback_used
        assert result.payload["status"] == "ok"

    async def test_invalid_primary_not_accepted(self, text_request):
        """Gemini returns parse-invalid output — not accepted as final."""
        from app.ai.providers.router import ProviderRouter

        gemini = _gemini("")
        deepseek = _deepseek('{"fallback": "accepted"}')
        router = ProviderRouter()
        providers = {"gemini": gemini, "deepseek": deepseek}

        result = await router.generate_validated(
            request=text_request,
            providers=providers,
            provider_order=["gemini", "deepseek"],
            validate=lambda p: (True, ()),
            canonical_facts={},
            max_repair_attempts=1,
        )

        assert result.provider == "deepseek"
        assert result.fallback_used
        assert result.payload["fallback"] == "accepted"
        assert result.attempts[0].provider == "gemini"
        assert result.attempts[0].failure_code is not None

    async def test_attempt_history_retained(self, text_request):
        """All routing attempts are recorded in result."""
        from app.ai.providers.router import ProviderRouter

        gemini = _gemini('{"first": "try"}')
        router = ProviderRouter()
        providers = {"gemini": gemini, "deepseek": _deepseek('{"second": "try"}')}

        result = await router.generate_validated(
            request=text_request,
            providers=providers,
            provider_order=["gemini", "deepseek"],
            validate=lambda p: (True, ()),
            canonical_facts={},
            max_repair_attempts=1,
        )

        assert len(result.attempts) >= 1

    def test_both_are_valid_ai_provider_subclasses(self):
        """Both GeminiProvider and DeepSeekProvider implement AIProvider."""
        from app.ai.providers.base import AIProvider

        gemini = _gemini()
        deepseek = _deepseek()
        assert isinstance(gemini, AIProvider)
        assert isinstance(deepseek, AIProvider)


# ===================================================================
# Provider-specific error mapping
# ===================================================================


class TestProviderErrorMapping:
    """Error codes follow the same taxonomy across providers."""

    @pytest.mark.parametrize("builder", PROVIDER_BUILDERS)
    async def test_provider_error_format(self, builder):
        provider = builder()
        assert provider.name in ("gemini", "deepseek")

    def test_gemini_error_codes_match_deepseek(self):
        from app.ai.providers.deepseek import (
            DeepSeekAuthenticationError,
            DeepSeekRateLimitedError,
            DeepSeekRefusedError,
            DeepSeekTimeoutError,
        )
        from app.ai.providers.gemini import (
            GeminiAuthenticationError,
            GeminiRateLimitedError,
            GeminiRefusedError,
            GeminiTimeoutError,
        )

        mapping = [
            (
                GeminiAuthenticationError,
                DeepSeekAuthenticationError,
                "AI_PROVIDER_AUTHENTICATION_FAILED",
            ),
            (GeminiRateLimitedError, DeepSeekRateLimitedError, "AI_PROVIDER_RATE_LIMITED"),
            (GeminiTimeoutError, DeepSeekTimeoutError, "AI_PROVIDER_TIMEOUT"),
            (GeminiRefusedError, DeepSeekRefusedError, "AI_PROVIDER_CONTENT_FILTERED"),
        ]

        for gem_cls, ds_cls, expected_code in mapping:
            g_err = gem_cls(message="test")
            d_err = ds_cls(message="test")
            assert g_err.code == expected_code, f"Gemini code mismatch: {g_err.code}"
            assert d_err.code == expected_code, f"DeepSeek code mismatch: {d_err.code}"
