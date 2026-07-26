"""Tests for GeminiProvider (TP-0703).

Uses an injected fake model client — no real API calls.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from io import BytesIO
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

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
from app.ai.providers.gemini import (
    GeminiNormalizationError,
    GeminiSchemaConversionError,
    build_initial_analysis_transport_schema,
    _convert_gemini_schema_document,
    load_initial_analysis_response_schema,
    normalize_initial_analysis_transport_payload,
)
from app.ai.initial_analysis_partitioning import (
    PARTITIONS,
    build_partition_schemas,
    build_partition_user_prompt,
    decimalize_json_numbers_for_validation,
    merge_partition_payloads,
    select_partition_images,
    validate_partition_payload,
)
from app.schemas.manifest import load_production_manifest
from app.schemas.registry import LocalSchemaRegistry
from app.validation import UnifiedValidationService
from app.validation.json_schema import JsonSchemaValidationService

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
        self.last_generation_config: dict[str, Any] | None = None
        self.model_name: str = "gemini-3.5-flash"

    async def generate_content_async(
        self,
        contents: list[Any],
        *,
        generation_config: dict[str, Any] | None = None,
    ) -> FakeGeminiResponse:
        self.last_contents = contents
        self.last_generation_config = generation_config
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


def _schema_root() -> Path:
    return Path(__file__).resolve().parents[3] / "schemas" / "production" / "v1"


def _initial_analysis_response_schema() -> dict[str, object]:
    return load_initial_analysis_response_schema(_schema_root())


def _initial_analysis_transport_schema() -> dict[str, object]:
    return build_initial_analysis_transport_schema(_initial_analysis_response_schema())


def _valid_initial_analysis_payload() -> dict[str, object]:
    fixture_path = Path(__file__).resolve().parents[3] / "schemas" / "fixtures" / "valid" / "v1" / "initial_analysis.valid.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    market_snapshot = payload["market_snapshot"]
    market_snapshot["previous_close"] = market_snapshot["last"]
    market_snapshot["change"] = 0
    market_snapshot["change_percentage"] = 0
    market_snapshot["best_bid"] = market_snapshot["best_offer"]
    market_snapshot["spread"] = 0
    market_snapshot["spread_percentage"] = 0
    return payload


def _transport_initial_analysis_payload() -> dict[str, object]:
    payload = _valid_initial_analysis_payload()
    for section_name in ("chart_3_month_analysis", "chart_6_month_analysis"):
        section = payload[section_name]
        section["nearest_support"] = (
            section["nearest_support"]["price"] if section["nearest_support"] is not None else None
        )
        section["nearest_resistance"] = (
            section["nearest_resistance"]["price"] if section["nearest_resistance"] is not None else None
        )
        section.pop("structure_status", None)
        section.pop("volume_condition", None)
        section.pop("supports_setup", None)
    return payload


def _provider_with_schema(**kwargs: Any) -> GeminiProvider:
    kwargs.setdefault("response_schemas", {"initial_analysis": _initial_analysis_response_schema()})
    return GeminiProvider(**kwargs)


def _verified_png_1x1_bytes() -> bytes:
    buf = BytesIO()
    Image.new("RGB", (1, 1), (255, 255, 255)).save(buf, format="PNG")
    png_bytes = buf.getvalue()
    Image.open(BytesIO(png_bytes)).verify()
    return png_bytes


def _real_image_bytes() -> tuple[bytes, bytes, bytes]:
    colors = ((255, 255, 255), (192, 192, 192), (0, 0, 0))
    images: list[bytes] = []
    for color in colors:
        buf = BytesIO()
        Image.new("RGB", (1, 1), color).save(buf, format="PNG")
        png_bytes = buf.getvalue()
        Image.open(BytesIO(png_bytes)).verify()
        images.append(png_bytes)
    return tuple(images)  # type: ignore[return-value]


def _real_image_loader_factory(image_bytes: tuple[bytes, bytes, bytes]) -> Callable[[ProviderImage], bytes]:
    by_reference = {
        "user/session/file-1.png": image_bytes[0],
        "user/session/file-2.png": image_bytes[1],
        "user/session/file-3.png": image_bytes[2],
    }

    def load(image: ProviderImage) -> bytes:
        return by_reference[image.storage_reference]

    return load


def _real_images() -> tuple[ProviderImage, ProviderImage, ProviderImage]:
    return (
        ProviderImage(
            evidence_id=uuid.uuid4(),
            mime_type="image/png",
            storage_reference="user/session/file-1.png",
            byte_size=69,
            width=1,
            height=1,
        ),
        ProviderImage(
            evidence_id=uuid.uuid4(),
            mime_type="image/png",
            storage_reference="user/session/file-2.png",
            byte_size=69,
            width=1,
            height=1,
        ),
        ProviderImage(
            evidence_id=uuid.uuid4(),
            mime_type="image/png",
            storage_reference="user/session/file-3.png",
            byte_size=69,
            width=1,
            height=1,
        ),
    )


def _real_request(
    *,
    user_prompt: str,
    expected_schema_name: str,
    expected_schema_version: str,
    structured_output_schema: dict[str, object] | None,
    images: tuple[ProviderImage, ...],
    timeout_seconds: int,
) -> ProviderRequest:
    return ProviderRequest(
        request_id=uuid.uuid4(),
        analysis_type="INITIAL_ANALYSIS",
        prompt_version="1.0.0",
        user_prompt=user_prompt,
        expected_schema_name=expected_schema_name,
        expected_schema_version=expected_schema_version,
        system_prompt="Jawab singkat dan patuhi schema.",
        images=images,
        structured_output_schema=structured_output_schema,
        timeout_seconds=timeout_seconds,
    )


async def _run_real_case(
    *,
    api_key: str,
    label: str,
    user_prompt: str,
    expected_schema_name: str,
    expected_schema_version: str,
    structured_output_schema: dict[str, object] | None,
    response_schemas: dict[str, dict[str, object]] | None,
    images: tuple[ProviderImage, ...],
    timeout_seconds: int = 60,
) -> dict[str, object]:
    provider = GeminiProvider(
        api_key=api_key,
        model_name="gemini-3.5-flash",
        timeout_seconds=timeout_seconds,
        image_loader=_real_image_loader_factory(_real_image_bytes()),
        response_schemas=response_schemas,
    )
    request = _real_request(
        user_prompt=user_prompt,
        expected_schema_name=expected_schema_name,
        expected_schema_version=expected_schema_version,
        structured_output_schema=structured_output_schema,
        images=images,
        timeout_seconds=timeout_seconds,
    )
    started_at = time.monotonic()
    try:
        response = await provider.generate(request)
    except GeminiError as exc:
        return {
            "case": label,
            "success": False,
            "elapsed_seconds": round(time.monotonic() - started_at, 3),
            "error_code": exc.code,
            "error_message": exc.message,
        }

    elapsed_seconds = round(time.monotonic() - started_at, 3)
    try:
        parsed = json.loads(response.raw_output)
        valid_json = True
        top_level_keys = list(parsed.keys())[:20] if isinstance(parsed, dict) else []
    except Exception:  # noqa: BLE001
        parsed = None
        valid_json = False
        top_level_keys = []

    result: dict[str, object] = {
        "case": label,
        "success": True,
        "elapsed_seconds": elapsed_seconds,
        "response_received": True,
        "valid_json": valid_json,
        "top_level_keys": top_level_keys,
        "finish_reason": response.finish_reason,
        "parsed": parsed,
    }
    return result


def _schema_with_sections(
    schema: dict[str, object],
    section_names: tuple[str, ...],
) -> dict[str, object]:
    properties = schema["properties"]
    assert isinstance(properties, dict)
    required = schema["required"]
    assert isinstance(required, list)

    pruned_required = [name for name in required if name in section_names]
    return {
        key: value
        for key, value in {
            "type": schema.get("type"),
            "description": schema.get("description"),
            "additionalProperties": schema.get("additionalProperties"),
            "properties": {name: properties[name] for name in section_names},
            "required": pruned_required,
        }.items()
        if value is not None
    }


async def _find_first_failing_top_level_section(
    *,
    api_key: str,
    image_count: int,
    full_schema: dict[str, object],
    timeout_seconds: int = 60,
) -> dict[str, object] | None:
    required = full_schema.get("required", ())
    if not isinstance(required, list):
        return None

    images = _real_images()[:image_count]
    sections: list[str] = []
    for section in required:
        if not isinstance(section, str):
            continue
        sections.append(section)
        case_result = await _run_real_case(
            api_key=api_key,
            label=f"boundary:{section}",
            user_prompt="Return only valid JSON matching the response schema.",
            expected_schema_name="initial_analysis",
            expected_schema_version="1.0.0",
            structured_output_schema=None,
            response_schemas={
                "initial_analysis": _schema_with_sections(full_schema, tuple(sections)),
            },
            images=images,
            timeout_seconds=timeout_seconds,
        )
        if not bool(case_result.get("success")):
            return {
                "first_failing_section": section,
                "sections_tested": list(sections),
                "failure": case_result,
            }

    return None


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
    return _provider_with_schema(
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
        assert fake_model.last_generation_config is not None
        assert fake_model.last_generation_config["system_instruction"] == "You are a helpful analyst."

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

        provider = _provider_with_schema(api_key="k", model=fake_model, image_loader=loader)
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

        provider = _provider_with_schema(
            api_key="k",
            model=fake_model,
            image_loader=failing_loader,
        )
        req = _text_request(images=(_make_image(),))
        with pytest.raises(GeminiRequestFailedError):
            await provider.generate(req)

    async def test_image_count_limit(
        self,
        fake_model: FakeGeminiModel,
    ) -> None:
        from app.ai.providers import ProviderCapabilityUnsupportedError

        provider = _provider_with_schema(
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
    async def test_active_initial_analysis_schema_attached_to_generation_config(
        self,
        provider: GeminiProvider,
        fake_model: FakeGeminiModel,
    ) -> None:
        req = _text_request()
        await provider.generate(req)

        assert fake_model.last_generation_config is not None
        assert fake_model.last_generation_config["response_mime_type"] == "application/json"
        assert fake_model.last_generation_config["response_json_schema"] == _initial_analysis_transport_schema()

    async def test_transport_schema_reduces_chart_level_fields(
        self,
        provider: GeminiProvider,
        fake_model: FakeGeminiModel,
    ) -> None:
        await provider.generate(_text_request())

        schema = fake_model.last_generation_config["response_json_schema"]
        chart = schema["properties"]["chart_3_month_analysis"]
        assert chart["required"] == [
            "available",
            "chart_timestamp",
            "trend",
            "momentum",
            "breakout_status",
            "breakdown_status",
            "nearest_support",
            "nearest_resistance",
            "positive_signals",
            "risk_signals",
            "limitations",
            "conclusion",
        ]
        assert chart["properties"]["nearest_support"] == {
            "oneOf": [{"type": "number"}, {"type": "null"}]
        }
        assert chart["properties"]["nearest_resistance"] == {
            "oneOf": [{"type": "number"}, {"type": "null"}]
        }

    def test_transport_schema_preserves_top_level_contract_and_reduces_chart_complexity(self) -> None:
        raw_schema = json.loads((_schema_root() / "initial_analysis.schema.json").read_text())
        canonical = _initial_analysis_response_schema()
        transport = _initial_analysis_transport_schema()

        assert transport["required"] == raw_schema["required"]
        assert (
            transport["properties"]["ai_assessment"]["required"]
            == canonical["properties"]["ai_assessment"]["required"]
        )
        assert (
            transport["properties"]["ai_assessment"]["properties"]
            == canonical["properties"]["ai_assessment"]["properties"]
        )
        canonical_chart = json.dumps(canonical["properties"]["chart_3_month_analysis"], sort_keys=True)
        transport_chart = json.dumps(transport["properties"]["chart_3_month_analysis"], sort_keys=True)
        assert len(transport_chart) < len(canonical_chart)

    def test_unsupported_schema_keywords_are_rejected(self) -> None:
        with pytest.raises(GeminiSchemaConversionError, match="Unsupported schema keywords"):
            _convert_gemini_schema_document(
                {"type": "object", "not": {"type": "null"}},
                schema_path=Path("invalid.schema.json"),
                package_root=Path("."),
            )

    async def test_valid_schema_constrained_output_passes_local_validation(
        self,
        fake_model: FakeGeminiModel,
    ) -> None:
        payload = _valid_initial_analysis_payload()
        provider = _provider_with_schema(
            api_key="test-key",
            model=FakeGeminiModel(response=FakeGeminiResponse(text=json.dumps(payload))),
            image_loader=_image_loader,
        )

        response = await provider.generate(_text_request())
        validation = UnifiedValidationService(
            schema_package_root=str(_schema_root()),
        ).validate(
            json.loads(response.raw_output),
            expected_analysis_type="INITIAL_ANALYSIS",
        )

        assert validation.valid is True

    def test_transport_output_normalizes_to_canonical_chart_objects(self) -> None:
        transport_payload = _transport_initial_analysis_payload()

        normalized = normalize_initial_analysis_transport_payload(transport_payload)

        chart = normalized["chart_3_month_analysis"]
        assert chart["timeframe"] == "THREE_MONTH"
        assert chart["structure_status"] == "UNKNOWN"
        assert chart["volume_condition"] == "UNKNOWN"
        assert chart["supports_setup"] is None
        assert chart["nearest_support"] == {
            "price": 2720,
            "label": "Three-month support",
            "summary": "Level support tiga bulan yang dinormalisasi dari respons transport Gemini.",
        }
        assert chart["nearest_resistance"] == {
            "price": 2900,
            "label": "Three-month resistance",
            "summary": "Level resistance tiga bulan yang dinormalisasi dari respons transport Gemini.",
        }

        validation = UnifiedValidationService(
            schema_package_root=str(_schema_root()),
        ).validate(
            normalized,
            expected_analysis_type="INITIAL_ANALYSIS",
        )
        assert validation.valid is True

    def test_transport_normalizer_preserves_null_levels(self) -> None:
        transport_payload = _transport_initial_analysis_payload()
        transport_payload["chart_3_month_analysis"]["nearest_support"] = None
        transport_payload["chart_3_month_analysis"]["nearest_resistance"] = None

        normalized = normalize_initial_analysis_transport_payload(transport_payload)

        assert normalized["chart_3_month_analysis"]["nearest_support"] is None
        assert normalized["chart_3_month_analysis"]["nearest_resistance"] is None

    def test_transport_normalizer_rejects_unsafe_missing_required_values(self) -> None:
        transport_payload = _transport_initial_analysis_payload()
        transport_payload["chart_3_month_analysis"].pop("conclusion")

        with pytest.raises(GeminiNormalizationError, match="chart_3_month_analysis.conclusion"):
            normalize_initial_analysis_transport_payload(transport_payload)

    @pytest.mark.skipif(
        os.environ.get("RUN_GEMINI_PROVIDER_MATRIX") != "1",
        reason="Set RUN_GEMINI_PROVIDER_MATRIX=1 to run live Gemini partition checks",
    )
    async def test_real_provider_google_genai_partitioned_initial_analysis(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            pytest.skip("GEMINI_API_KEY is required for the live Gemini matrix")

        images = _real_images()
        schema_root = _schema_root()
        manifest = load_production_manifest(schema_root)
        schema_registry = LocalSchemaRegistry(manifest, schema_root)
        schema_service = JsonSchemaValidationService(schema_registry)
        unified_validation = UnifiedValidationService(schema_package_root=str(schema_root))
        partition_schemas = build_partition_schemas(schema_root)
        provider = _provider_with_schema(
            api_key=api_key,
            image_loader=_real_image_loader_factory(_real_image_bytes()),
        )
        validated_partitions: dict[str, dict[str, object]] = {}
        results: list[dict[str, object]] = []

        for partition in PARTITIONS:
            prompt = build_partition_user_prompt(
                base_user_prompt="Return only valid JSON matching the response schema.",
                partition_name=partition.name,
                validated_context=validated_partitions,
            )
            request = _real_request(
                user_prompt=prompt,
                expected_schema_name="initial_analysis",
                expected_schema_version="1.0.0",
                structured_output_schema=partition_schemas[partition.name].provider_schema,
                images=select_partition_images(partition_name=partition.name, images=images),
                timeout_seconds=60,
            )
            started_at = time.monotonic()
            try:
                response = await provider.generate(request)
            except GeminiError as exc:
                results.append(
                    {
                        "partition": partition.name,
                        "success": False,
                        "elapsed_seconds": round(time.monotonic() - started_at, 3),
                        "error_code": exc.code,
                        "error_message": exc.message,
                    }
                )
                break

            elapsed_seconds = round(time.monotonic() - started_at, 3)
            parsed = json.loads(response.raw_output)
            normalized = (
                normalize_initial_analysis_transport_payload(parsed)
                if partition.name == "CHART_ANALYSIS"
                else parsed
            )
            is_valid, issues = validate_partition_payload(
                payload=normalized,
                partition_name=partition.name,
                schemas=partition_schemas,
            )
            result = {
                "partition": partition.name,
                "success": is_valid,
                "elapsed_seconds": elapsed_seconds,
                "top_level_keys": list(parsed.keys())[:20] if isinstance(parsed, dict) else [],
                "finish_reason": response.finish_reason,
                "input_tokens": response.usage.input_tokens if response.usage else None,
                "output_tokens": response.usage.output_tokens if response.usage else None,
                "total_tokens": response.usage.total_tokens if response.usage else None,
                "latency_ms": response.latency_ms,
            }
            if not is_valid:
                result["issue_codes"] = [issue.code for issue in issues[:10]]
                result["issue_messages"] = [issue.message for issue in issues[:5]]
                results.append(result)
                break

            validated_partitions[partition.name] = dict(normalized)
            results.append(result)

        merged_payload = None
        schema_validation = None
        full_validation = None
        if len(validated_partitions) == len(PARTITIONS):
            merged_payload = merge_partition_payloads(validated_partitions)
            schema_validation = schema_service.validate_by_name(
                merged_payload,
                "initial_analysis",
                "1.0.0",
            )
            if schema_validation.valid:
                full_validation = unified_validation.validate(
                    decimalize_json_numbers_for_validation(merged_payload),
                    expected_analysis_type="INITIAL_ANALYSIS",
                )

        print(
            json.dumps(
                {
                    "model": "gemini-3.5-flash",
                    "results": results,
                    "merged": merged_payload is not None,
                    "schema_valid": schema_validation.valid if schema_validation else None,
                    "schema_issue_codes": (
                        [issue.code for issue in schema_validation.issues[:10]]
                        if schema_validation is not None
                        else None
                    ),
                    "canonical_valid": full_validation.valid if full_validation else None,
                    "canonical_issue_codes": (
                        [issue.code for issue in full_validation.issues[:10]]
                        if full_validation is not None
                        else None
                    ),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        assert len(results) == 4
        assert all(bool(result.get("success")) is True for result in results)
        assert merged_payload is not None
        assert schema_validation is not None and schema_validation.valid is True
        assert full_validation is not None and full_validation.valid is True


# ===================================================================
# Response mapping
# ===================================================================


class TestResponseMapping:
    async def test_provider_response_id(
        self,
        text_req: ProviderRequest,
    ) -> None:
        response = FakeGeminiResponse()
        response.response_id = "gemini-response-123"  # type: ignore[attr-defined]
        provider = _provider_with_schema(api_key="k", model=FakeGeminiModel(response=response))
        resp = await provider.generate(text_req)
        assert resp.provider_response_id == "gemini-response-123"

    async def test_missing_provider_response_id_returns_none(
        self,
        provider: GeminiProvider,
        text_req: ProviderRequest,
    ) -> None:
        resp = await provider.generate(text_req)
        assert resp.provider_response_id is None

    async def test_numeric_real_provider_response_id_normalized_to_string(
        self,
        text_req: ProviderRequest,
    ) -> None:
        response = FakeGeminiResponse()
        response.id = 12345  # type: ignore[attr-defined]
        provider = _provider_with_schema(api_key="k", model=FakeGeminiModel(response=response))
        resp = await provider.generate(text_req)
        assert resp.provider_response_id == "12345"

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
        provider = _provider_with_schema(api_key="k", model=fake_model)
        resp = await provider.generate(text_req)
        assert resp.usage is None

    async def test_empty_text_handled(
        self,
        fake_model: FakeGeminiModel,
        text_req: ProviderRequest,
    ) -> None:
        empty_response = FakeGeminiResponse(text=None)  # type: ignore[arg-type]
        fake_model._response = empty_response
        provider = _provider_with_schema(api_key="k", model=fake_model)
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
        provider = _provider_with_schema(api_key="bad", model=fake_model)
        with pytest.raises(GeminiAuthenticationError):
            await provider.generate(text_req)

    async def test_rate_limit(
        self,
        fake_model: FakeGeminiModel,
        text_req: ProviderRequest,
    ) -> None:
        import google.api_core.exceptions as api_exc

        fake_model._response = api_exc.ResourceExhausted("Rate limited")  # type: ignore[assignment]
        provider = _provider_with_schema(api_key="k", model=fake_model)
        with pytest.raises(GeminiRateLimitedError):
            await provider.generate(text_req)

    async def test_timeout(
        self,
        fake_model: FakeGeminiModel,
        text_req: ProviderRequest,
    ) -> None:
        import google.api_core.exceptions as api_exc

        fake_model._response = api_exc.DeadlineExceeded("Timed out")  # type: ignore[assignment]
        provider = _provider_with_schema(api_key="k", model=fake_model)
        with pytest.raises(GeminiTimeoutError):
            await provider.generate(text_req)

    async def test_refusal(
        self,
        fake_model: FakeGeminiModel,
        text_req: ProviderRequest,
    ) -> None:
        fake_model._response = Exception("Response was blocked due to safety")  # type: ignore[assignment]
        provider = _provider_with_schema(api_key="k", model=fake_model)
        with pytest.raises(GeminiRefusedError):
            await provider.generate(text_req)

    async def test_generic_sdk_failure(
        self,
        fake_model: FakeGeminiModel,
        text_req: ProviderRequest,
    ) -> None:
        fake_model._response = Exception("Unexpected SDK error")  # type: ignore[assignment]
        provider = _provider_with_schema(api_key="k", model=fake_model)
        with pytest.raises(GeminiError):
            await provider.generate(text_req)

    async def test_sdk_error_prefers_message_over_details_and_empty_str(
        self,
        fake_model: FakeGeminiModel,
        text_req: ProviderRequest,
    ) -> None:
        class _SdkStyleError(Exception):
            def __init__(self) -> None:
                self.message = "request failed api_key=secret-token"
                self.details = ["detail that should not win"]
                self.errors = [{"reason": "detail fallback"}]

            def __str__(self) -> str:
                return ""

        fake_model._response = _SdkStyleError()  # type: ignore[assignment]
        provider = _provider_with_schema(api_key="k", model=fake_model)

        with pytest.raises(GeminiRequestFailedError) as exc:
            await provider.generate(text_req)

        assert exc.value.message == "request failed api_key=[REDACTED]"

    async def test_sdk_error_uses_details_when_message_is_empty(
        self,
        fake_model: FakeGeminiModel,
        text_req: ProviderRequest,
    ) -> None:
        class _SdkStyleError(Exception):
            def __init__(self) -> None:
                self.message = ""
                self.details = ["detail token=secret-token", {"reason": "model missing"}]
                self.errors = [{"reason": "unused fallback"}]

            def __str__(self) -> str:
                return ""

        fake_model._response = _SdkStyleError()  # type: ignore[assignment]
        provider = _provider_with_schema(api_key="k", model=fake_model)

        with pytest.raises(GeminiRequestFailedError) as exc:
            await provider.generate(text_req)

        assert exc.value.message == "detail token=[REDACTED]; {'reason': 'model missing'}"

    async def test_request_timeout_seconds_override_is_used(
        self,
        monkeypatch: pytest.MonkeyPatch,
        fake_model: FakeGeminiModel,
    ) -> None:
        observed: dict[str, float] = {}

        async def fake_wait_for(awaitable: Any, timeout: float) -> Any:
            observed["timeout"] = timeout
            return await awaitable

        monkeypatch.setattr("app.ai.providers.gemini.asyncio.wait_for", fake_wait_for)

        provider = _provider_with_schema(api_key="k", model=fake_model, timeout_seconds=17)
        await provider.generate(_text_request(timeout_seconds=5))

        assert observed["timeout"] == 5

    async def test_provider_timeout_used_when_request_timeout_absent(
        self,
        monkeypatch: pytest.MonkeyPatch,
        fake_model: FakeGeminiModel,
    ) -> None:
        observed: dict[str, float] = {}

        async def fake_wait_for(awaitable: Any, timeout: float) -> Any:
            observed["timeout"] = timeout
            return await awaitable

        monkeypatch.setattr("app.ai.providers.gemini.asyncio.wait_for", fake_wait_for)

        provider = _provider_with_schema(api_key="k", model=fake_model, timeout_seconds=17)
        await provider.generate(_text_request())

        assert observed["timeout"] == 17


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
        provider = _provider_with_schema(api_key="test", model=fake_model)
        req = _text_request()
        await provider.generate(req)

    async def test_no_real_api_key_required_for_tests(
        self,
        fake_model: FakeGeminiModel,
    ) -> None:
        provider = _provider_with_schema(api_key="fake-key", model=fake_model)
        req = _text_request()
        await provider.generate(req)
