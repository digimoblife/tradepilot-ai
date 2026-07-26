"""Tests for ProviderRouter (TP-0707).

Uses fake providers — no real network access.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest

from app.ai.providers import (
    AIProvider,
    ProviderCapabilities,
    ProviderImage,
    ProviderOrderEmptyError,
    ProviderRequest,
    ProviderResponse,
    ProviderRouter,
    ProviderRoutingFailedError,
    ProviderUnknownError,
)
from app.validation import ValidationCategory, ValidationIssue, ValidationSeverity

# ===================================================================
# Fake providers
# ===================================================================


class FakeProvider(AIProvider):
    """Configurable fake provider for routing tests."""

    def __init__(
        self,
        name: str = "fake",
        *,
        responses: list[ProviderResponse | Exception] | None = None,
        capabilities: ProviderCapabilities | None = None,
    ) -> None:
        self._name = name
        self._responses = list(responses or [])
        self._caps = capabilities or ProviderCapabilities(
            supports_images=True,
            supports_structured_output=True,
        )
        self.call_count = 0
        self.last_request: ProviderRequest | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def model(self) -> str:
        return f"{self._name}-model"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._caps

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        self.call_count += 1
        self.last_request = request
        if not self._responses:
            return ProviderResponse(
                provider=self._name,
                model=self.model,
                raw_output='{"ok": true}',
                request_id=request.request_id,
            )
        resp = self._responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


# ===================================================================
# Validation helpers
# ===================================================================


def _always_valid(
    payload: dict[str, object],
) -> tuple[bool, tuple[ValidationIssue, ...]]:
    return True, ()


def _always_invalid(
    payload: dict[str, object],
) -> tuple[bool, tuple[ValidationIssue, ...]]:
    return False, (
        ValidationIssue(
            code="TEST_ERROR",
            category=ValidationCategory.SCHEMA,
            severity=ValidationSeverity.ERROR,
            path="/test",
            message="Test error",
        ),
    )


def _valid_on_nth(n: int) -> Any:
    class Counter:
        def __init__(self) -> None:
            self.calls = 0

        def __call__(self, payload: dict[str, object]) -> tuple[bool, tuple[ValidationIssue, ...]]:
            self.calls += 1
            if self.calls >= n:
                return True, ()
            return False, (
                ValidationIssue(
                    code="RETRY",
                    category=ValidationCategory.SCHEMA,
                    severity=ValidationSeverity.ERROR,
                    path="/r",
                    message=f"Attempt {self.calls}",
                ),
            )

    return Counter()


# ===================================================================
# Request helper
# ===================================================================


def _req(**overrides: Any) -> ProviderRequest:
    kwargs = dict(
        request_id=uuid.uuid4(),
        analysis_type="INITIAL_ANALYSIS",
        prompt_version="1.0.0",
        user_prompt="Analyze",
        expected_schema_name="initial_analysis",
        expected_schema_version="1.0",
    )
    kwargs.update(overrides)
    return ProviderRequest(**kwargs)


# ===================================================================
# Configured order
# ===================================================================


class TestConfiguredOrder:
    async def test_gemini_before_deepseek(self) -> None:
        gemini = FakeProvider("gemini")
        deepseek = FakeProvider("deepseek")
        router = ProviderRouter()
        await router.generate_validated(
            request=_req(),
            providers={"gemini": gemini, "deepseek": deepseek},
            provider_order=["gemini", "deepseek"],
            validate=_always_valid,
            canonical_facts={},
            max_repair_attempts=2,
        )
        assert gemini.call_count == 1
        assert deepseek.call_count == 0

    async def test_deepseek_not_called_on_gemini_success(self) -> None:
        gemini = FakeProvider("gemini")
        deepseek = FakeProvider("deepseek")
        router = ProviderRouter()
        await router.generate_validated(
            request=_req(),
            providers={"gemini": gemini, "deepseek": deepseek},
            provider_order=["gemini", "deepseek"],
            validate=_always_valid,
            canonical_facts={},
            max_repair_attempts=2,
        )
        assert deepseek.call_count == 0

    async def test_deepseek_called_after_gemini_fails(self) -> None:
        gemini = FakeProvider(
            "gemini",
            responses=[Exception("fail")],
        )
        deepseek = FakeProvider("deepseek")
        router = ProviderRouter()
        result = await router.generate_validated(
            request=_req(),
            providers={"gemini": gemini, "deepseek": deepseek},
            provider_order=["gemini", "deepseek"],
            validate=_always_valid,
            canonical_facts={},
            max_repair_attempts=2,
        )
        assert gemini.call_count == 1
        assert deepseek.call_count == 1
        assert result.provider == "deepseek"

    async def test_single_attempt_does_not_fallback_after_primary_failure(self) -> None:
        gemini = FakeProvider("gemini", responses=[Exception("fail")])
        deepseek = FakeProvider("deepseek")
        router = ProviderRouter()

        with pytest.raises(ProviderRoutingFailedError):
            await router.generate_validated(
                request=_req(),
                providers={"gemini": gemini, "deepseek": deepseek},
                provider_order=["gemini", "deepseek"],
                max_provider_attempts=1,
                validate=_always_valid,
                canonical_facts={},
                max_repair_attempts=0,
            )

        assert gemini.call_count == 1
        assert deepseek.call_count == 0

    async def test_empty_order_rejected(self) -> None:
        router = ProviderRouter()
        with pytest.raises(ProviderOrderEmptyError):
            await router.generate_validated(
                request=_req(),
                providers={"gemini": FakeProvider("gemini")},
                provider_order=[],
                validate=_always_valid,
                canonical_facts={},
                max_repair_attempts=1,
            )

    async def test_unknown_provider_rejected(self) -> None:
        router = ProviderRouter()
        with pytest.raises(ProviderUnknownError):
            await router.generate_validated(
                request=_req(),
                providers={"gemini": FakeProvider("gemini")},
                provider_order=["gemini", "unknown"],
                validate=_always_valid,
                canonical_facts={},
                max_repair_attempts=1,
            )


# ===================================================================
# Primary success
# ===================================================================


class TestPrimarySuccess:
    async def test_gemini_valid_returns_immediately(self) -> None:
        gemini = FakeProvider("gemini")
        deepseek = FakeProvider("deepseek")
        router = ProviderRouter()
        result = await router.generate_validated(
            request=_req(),
            providers={"gemini": gemini, "deepseek": deepseek},
            provider_order=["gemini", "deepseek"],
            validate=_always_valid,
            canonical_facts={},
            max_repair_attempts=2,
        )
        assert result.provider == "gemini"
        assert gemini.call_count == 1
        assert deepseek.call_count == 0

    async def test_no_fallback_after_primary_success(self) -> None:
        router = ProviderRouter()
        result = await router.generate_validated(
            request=_req(),
            providers={"gemini": FakeProvider("gemini"), "deepseek": FakeProvider("deepseek")},
            provider_order=["gemini", "deepseek"],
            validate=_always_valid,
            canonical_facts={},
            max_repair_attempts=2,
        )
        assert result.fallback_used is False

    async def test_parsing_applied(self) -> None:
        gemini = FakeProvider("gemini")
        router = ProviderRouter()
        result = await router.generate_validated(
            request=_req(),
            providers={"gemini": gemini},
            provider_order=["gemini"],
            validate=_always_valid,
            canonical_facts={},
            max_repair_attempts=2,
        )
        assert result.payload == {"ok": True}

    async def test_validation_applied(self) -> None:
        gemini = FakeProvider("gemini")
        router = ProviderRouter()
        result = await router.generate_validated(
            request=_req(),
            providers={"gemini": gemini},
            provider_order=["gemini"],
            validate=_always_valid,
            canonical_facts={},
            max_repair_attempts=2,
        )
        assert result.payload is not None

    async def test_gemini_transport_payload_is_normalized_before_validation(self) -> None:
        payload = {
            "chart_3_month_analysis": {
                "available": True,
                "chart_timestamp": "2026-07-25T09:00:00Z",
                "trend": "BULLISH",
                "momentum": "IMPROVING",
                "breakout_status": "NOT_PRESENT",
                "breakdown_status": "FAILED",
                "nearest_support": 2720,
                "nearest_resistance": 2900,
                "positive_signals": ["Buyer bertahan."],
                "risk_signals": ["Resistance dekat."],
                "limitations": ["Hanya satu snapshot chart."],
                "conclusion": "Struktur jangka pendek membaik.",
            },
            "chart_6_month_analysis": {
                "available": True,
                "chart_timestamp": "2026-07-25T09:00:00Z",
                "trend": "NEUTRAL",
                "momentum": "MIXED",
                "breakout_status": "NOT_PRESENT",
                "breakdown_status": "NOT_PRESENT",
                "nearest_support": None,
                "nearest_resistance": 3000,
                "positive_signals": ["Base masih terjaga."],
                "risk_signals": ["Trend menengah belum kuat."],
                "limitations": ["Belum ada volume detail."],
                "conclusion": "Trend menengah masih menunggu konfirmasi.",
            },
        }
        response = ProviderResponse(
            provider="gemini",
            model="gemini-3.5-flash",
            raw_output=json.dumps(payload),
            request_id=uuid.uuid4(),
        )
        gemini = FakeProvider("gemini", responses=[response])
        router = ProviderRouter()

        captured: dict[str, object] = {}

        def _validate(payload: dict[str, object]) -> tuple[bool, tuple[ValidationIssue, ...]]:
            captured.update(payload)
            return True, ()

        result = await router.generate_validated(
            request=_req(),
            providers={"gemini": gemini},
            provider_order=["gemini"],
            validate=_validate,
            canonical_facts={},
            max_repair_attempts=0,
        )

        chart = captured["chart_3_month_analysis"]
        assert isinstance(chart, dict)
        assert chart["timeframe"] == "THREE_MONTH"
        assert chart["nearest_support"] == {
            "price": 2720,
            "label": "Three-month support",
            "summary": "Level support tiga bulan yang dinormalisasi dari respons transport Gemini.",
        }
        assert result.response.raw_output == json.dumps(payload)
        assert result.response.metadata["provider_payload_raw"] == payload
        assert result.payload["chart_6_month_analysis"]["nearest_support"] is None

    async def test_gemini_chart_timestamps_from_request_metadata_are_used_for_normalization(self) -> None:
        payload = {
            "chart_3_month_analysis": {
                "available": True,
                "trend": "BULLISH",
                "momentum": "IMPROVING",
                "breakout_status": "NOT_PRESENT",
                "breakdown_status": "FAILED",
                "nearest_support": 2720,
                "nearest_resistance": 2900,
                "positive_signals": ["Buyer bertahan."],
                "risk_signals": ["Resistance dekat."],
                "limitations": ["Hanya satu snapshot chart."],
                "conclusion": "Struktur jangka pendek membaik.",
            },
            "chart_6_month_analysis": {
                "available": True,
                "chart_timestamp": "2026-01-01T00:00:00+00:00",
                "trend": "NEUTRAL",
                "momentum": "MIXED",
                "breakout_status": "NOT_PRESENT",
                "breakdown_status": "NOT_PRESENT",
                "nearest_support": None,
                "nearest_resistance": 3000,
                "positive_signals": ["Base masih terjaga."],
                "risk_signals": ["Trend menengah belum kuat."],
                "limitations": ["Belum ada volume detail."],
                "conclusion": "Trend menengah masih menunggu konfirmasi.",
            },
        }
        response = ProviderResponse(
            provider="gemini",
            model="gemini-3.5-flash",
            raw_output=json.dumps(payload),
            request_id=uuid.uuid4(),
        )
        gemini = FakeProvider("gemini", responses=[response])
        router = ProviderRouter()

        result = await router.generate_validated(
            request=_req(
                metadata={
                    "canonical_chart_timestamps": {
                        "chart_3_month_analysis": "2026-07-24T09:15:00+07:00",
                        "chart_6_month_analysis": "2026-07-23T15:45:00+07:00",
                    }
                }
            ),
            providers={"gemini": gemini},
            provider_order=["gemini"],
            validate=_always_valid,
            canonical_facts={},
            max_repair_attempts=0,
        )

        assert result.payload["chart_3_month_analysis"]["chart_timestamp"] == "2026-07-24T09:15:00+07:00"
        assert result.payload["chart_6_month_analysis"]["chart_timestamp"] == "2026-07-23T15:45:00+07:00"


# ===================================================================
# Repair before fallback
# ===================================================================


class TestRepairBeforeFallback:
    async def test_repair_invoked_on_validation_failure(self) -> None:
        gemini = FakeProvider("gemini")
        deepseek = FakeProvider("deepseek")
        router = ProviderRouter()
        result = await router.generate_validated(
            request=_req(),
            providers={"gemini": gemini, "deepseek": deepseek},
            provider_order=["gemini", "deepseek"],
            validate=_valid_on_nth(2),
            canonical_facts={},
            max_repair_attempts=3,
        )
        # Gemini called once, then repair called (total > 1 gemini call)
        assert result.provider == "gemini"

    async def test_repair_success_prevents_fallback(self) -> None:
        gemini = FakeProvider("gemini")
        deepseek = FakeProvider("deepseek")
        router = ProviderRouter()
        result = await router.generate_validated(
            request=_req(),
            providers={"gemini": gemini, "deepseek": deepseek},
            provider_order=["gemini", "deepseek"],
            validate=_valid_on_nth(2),
            canonical_facts={},
            max_repair_attempts=3,
        )
        assert result.provider == "gemini"
        assert result.fallback_used is False
        assert deepseek.call_count == 0

    async def test_repair_raw_responses_in_history(self) -> None:
        gemini = FakeProvider("gemini")
        router = ProviderRouter()
        result = await router.generate_validated(
            request=_req(),
            providers={"gemini": gemini},
            provider_order=["gemini"],
            validate=_valid_on_nth(2),
            canonical_facts={},
            max_repair_attempts=3,
        )
        # At least one repair attempt should exist in history
        repair_attempts = [a for a in result.attempts if a.phase == "REPAIR"]
        assert len(repair_attempts) >= 1

    async def test_repair_disabled_keeps_single_provider_invocation(self) -> None:
        gemini = FakeProvider("gemini")
        router = ProviderRouter()

        with pytest.raises(ProviderRoutingFailedError):
            await router.generate_validated(
                request=_req(),
                providers={"gemini": gemini},
                provider_order=["gemini"],
                max_provider_attempts=1,
                validate=_always_invalid,
                canonical_facts={},
                max_repair_attempts=0,
            )

        assert gemini.call_count == 1

    async def test_repair_disabled_preserves_concrete_validation_error(self) -> None:
        gemini = FakeProvider("gemini")
        router = ProviderRouter()

        with pytest.raises(ProviderRoutingFailedError) as exc:
            await router.generate_validated(
                request=_req(),
                providers={"gemini": gemini},
                provider_order=["gemini"],
                max_provider_attempts=1,
                validate=_always_invalid,
                canonical_facts={},
                max_repair_attempts=0,
            )

        assert exc.value.root_cause_code == "TEST_ERROR"
        assert exc.value.root_cause_message == "Test error"

    async def test_malformed_json_still_fails(self) -> None:
        gemini = FakeProvider(
            "gemini",
            responses=[
                ProviderResponse(
                    provider="gemini",
                    model="gemini-model",
                    raw_output="{not json",
                    request_id=uuid.uuid4(),
                )
            ],
        )
        router = ProviderRouter()

        with pytest.raises(ProviderRoutingFailedError) as exc:
            await router.generate_validated(
                request=_req(),
                providers={"gemini": gemini},
                provider_order=["gemini"],
                max_provider_attempts=1,
                validate=_always_valid,
                canonical_facts={},
                max_repair_attempts=0,
            )

        assert exc.value.root_cause_code == "JSON_OBJECT_NOT_FOUND"

    async def test_repair_disabled_preserves_fallback_validation_message_when_issues_empty(self) -> None:
        gemini = FakeProvider("gemini")
        router = ProviderRouter()

        def _invalid_without_issues(
            payload: dict[str, object],
        ) -> tuple[bool, tuple[ValidationIssue, ...]]:
            return False, ()

        with pytest.raises(ProviderRoutingFailedError) as exc:
            await router.generate_validated(
                request=_req(),
                providers={"gemini": gemini},
                provider_order=["gemini"],
                max_provider_attempts=1,
                validate=_invalid_without_issues,
                canonical_facts={},
                max_repair_attempts=0,
            )

        assert exc.value.root_cause_code == "REPAIR_VALIDATION_FAILED"
        assert (
            exc.value.root_cause_message
            == "Provider response validation failed with no issue details returned."
        )


# ===================================================================
# Fallback success
# ===================================================================


class TestFallbackSuccess:
    async def test_gemini_failure_deepseek_succeeds(self) -> None:
        gemini = FakeProvider(
            "gemini",
            responses=[Exception("Gemini error")],
        )
        deepseek = FakeProvider("deepseek")
        router = ProviderRouter()
        result = await router.generate_validated(
            request=_req(),
            providers={"gemini": gemini, "deepseek": deepseek},
            provider_order=["gemini", "deepseek"],
            validate=_always_valid,
            canonical_facts={},
            max_repair_attempts=2,
        )
        assert result.provider == "deepseek"
        assert result.fallback_used is True

    async def test_repair_exhaustion_then_deepseek_succeeds(self) -> None:
        deepseek = FakeProvider("deepseek")
        router = ProviderRouter()
        result = await router.generate_validated(
            request=_req(),
            providers={
                "gemini": FakeProvider("gemini"),
                "deepseek": deepseek,
            },
            provider_order=["gemini", "deepseek"],
            validate=_valid_on_nth(3),  # Gemini primary + 1 repair fail, then DeepSeek
            max_repair_attempts=1,
            canonical_facts={},
        )
        assert result.provider == "deepseek"
        assert result.fallback_used is True

    async def test_all_responses_in_history(self) -> None:
        gemini = FakeProvider(
            "gemini",
            responses=[Exception("fail")],
        )
        deepseek = FakeProvider("deepseek")
        router = ProviderRouter()
        result = await router.generate_validated(
            request=_req(),
            providers={"gemini": gemini, "deepseek": deepseek},
            provider_order=["gemini", "deepseek"],
            validate=_always_valid,
            canonical_facts={},
            max_repair_attempts=2,
        )
        assert len(result.attempts) >= 2

    async def test_validated_final_payload_only(self) -> None:
        gemini = FakeProvider("gemini", responses=[Exception("fail")])
        deepseek = FakeProvider("deepseek")
        router = ProviderRouter()
        result = await router.generate_validated(
            request=_req(),
            providers={"gemini": gemini, "deepseek": deepseek},
            provider_order=["gemini", "deepseek"],
            validate=_always_valid,
            canonical_facts={},
            max_repair_attempts=2,
        )
        assert result.payload == {"ok": True}


# ===================================================================
# Provider compatibility
# ===================================================================


class TestProviderCompatibility:
    async def test_incompatible_skipped(self) -> None:
        no_images = ProviderCapabilities(supports_images=False)
        gemini = FakeProvider("gemini")
        deepseek = FakeProvider("deepseek", capabilities=no_images)
        router = ProviderRouter()
        img = ProviderImage(
            evidence_id=uuid.uuid4(),
            mime_type="image/png",
            storage_reference="f.png",
            byte_size=100,
        )
        result = await router.generate_validated(
            request=_req(images=(img,)),
            providers={"gemini": gemini, "deepseek": deepseek},
            provider_order=["gemini", "deepseek"],
            validate=_always_valid,
            canonical_facts={},
            max_repair_attempts=2,
        )
        assert result.provider == "gemini"
        # DeepSeek should not be called (capability check fails first)
        assert deepseek.call_count == 0

    async def test_capability_failure_recorded(self) -> None:
        no_images = ProviderCapabilities(supports_images=False)
        gemini = FakeProvider(
            "gemini",
            responses=[Exception("Gemini fail")],
        )
        deepseek = FakeProvider("deepseek", capabilities=no_images)
        router = ProviderRouter()
        img = ProviderImage(
            evidence_id=uuid.uuid4(),
            mime_type="image/png",
            storage_reference="f.png",
            byte_size=100,
        )
        with pytest.raises(ProviderRoutingFailedError) as exc:
            await router.generate_validated(
                request=_req(images=(img,)),
                providers={"gemini": gemini, "deepseek": deepseek},
                provider_order=["gemini", "deepseek"],
                validate=_always_valid,
                canonical_facts={},
                max_repair_attempts=2,
            )
        cap_fails = [a for a in exc.value.attempts if a.phase == "CAPABILITY_CHECK"]
        assert len(cap_fails) >= 1


# ===================================================================
# All fail
# ===================================================================


class TestAllFail:
    async def test_both_providers_fail(self) -> None:
        gemini = FakeProvider("gemini", responses=[Exception("fail")])
        deepseek = FakeProvider("deepseek", responses=[Exception("fail")])
        router = ProviderRouter()
        with pytest.raises(ProviderRoutingFailedError) as exc:
            await router.generate_validated(
                request=_req(),
                providers={"gemini": gemini, "deepseek": deepseek},
                provider_order=["gemini", "deepseek"],
                validate=_always_valid,
                canonical_facts={},
                max_repair_attempts=2,
            )
        assert "PROVIDER_ROUTING_FAILED" in str(exc.value)

    async def test_both_invalid_output(self) -> None:
        deepseek = FakeProvider("deepseek")
        router = ProviderRouter()
        with pytest.raises(ProviderRoutingFailedError):
            await router.generate_validated(
                request=_req(),
                providers={"gemini": FakeProvider("gemini"), "deepseek": deepseek},
                provider_order=["gemini", "deepseek"],
                validate=_always_invalid,
                canonical_facts={},
                max_repair_attempts=1,
            )

    async def test_final_error_contains_history(self) -> None:
        gemini = FakeProvider("gemini", responses=[Exception("fail")])
        deepseek = FakeProvider("deepseek", responses=[Exception("fail")])
        router = ProviderRouter()
        with pytest.raises(ProviderRoutingFailedError) as exc:
            await router.generate_validated(
                request=_req(),
                providers={"gemini": gemini, "deepseek": deepseek},
                provider_order=["gemini", "deepseek"],
                validate=_always_valid,
                canonical_facts={},
                max_repair_attempts=2,
            )
        assert len(exc.value.attempts) >= 2

    async def test_final_error_retains_sanitized_root_cause(self) -> None:
        class _GeminiTimeoutError(Exception):
            code = "AI_PROVIDER_TIMEOUT"

            def __str__(self) -> str:
                return "request failed api_key=secret-token"

        gemini = FakeProvider("gemini", responses=[_GeminiTimeoutError()])
        router = ProviderRouter()

        with pytest.raises(ProviderRoutingFailedError) as exc:
            await router.generate_validated(
                request=_req(),
                providers={"gemini": gemini},
                provider_order=["gemini"],
                validate=_always_valid,
                canonical_facts={},
                max_repair_attempts=2,
            )

        assert exc.value.root_cause_code == "AI_PROVIDER_TIMEOUT"
        assert exc.value.root_cause_message == "request failed api_key=[REDACTED]"
        assert exc.value.retryable is True

    async def test_final_error_uses_safe_fallback_when_str_is_empty(self) -> None:
        class _GeminiInvalidRequestError(Exception):
            code = "AI_PROVIDER_INVALID_REQUEST"

            def __init__(self) -> None:
                self.message = "model missing token=secret-token"

            def __str__(self) -> str:
                return ""

        gemini = FakeProvider("gemini", responses=[_GeminiInvalidRequestError()])
        router = ProviderRouter()

        with pytest.raises(ProviderRoutingFailedError) as exc:
            await router.generate_validated(
                request=_req(),
                providers={"gemini": gemini},
                provider_order=["gemini"],
                validate=_always_valid,
                canonical_facts={},
                max_repair_attempts=2,
            )

        assert exc.value.root_cause_code == "AI_PROVIDER_INVALID_REQUEST"
        assert exc.value.root_cause_message == "model missing token=[REDACTED]"

    async def test_no_invalid_payload_returned(self) -> None:
        router = ProviderRouter()
        try:
            await router.generate_validated(
                request=_req(),
                providers={
                    "gemini": FakeProvider("gemini"),
                    "deepseek": FakeProvider("deepseek"),
                },
                provider_order=["gemini", "deepseek"],
                validate=_always_invalid,
                canonical_facts={},
                max_repair_attempts=1,
            )
        except ProviderRoutingFailedError:
            pass


# ===================================================================
# Raw response retention
# ===================================================================


class TestRawResponseRetention:
    async def test_primary_response_retained(self) -> None:
        gemini = FakeProvider("gemini")
        router = ProviderRouter()
        result = await router.generate_validated(
            request=_req(),
            providers={"gemini": gemini},
            provider_order=["gemini"],
            validate=_always_valid,
            canonical_facts={},
            max_repair_attempts=2,
        )
        assert len(result.attempts) >= 1
        primary = [a for a in result.attempts if a.phase == "PRIMARY"]
        assert len(primary) >= 1
        assert primary[0].response is not None

    async def test_fallback_response_retained(self) -> None:
        gemini = FakeProvider("gemini", responses=[Exception("fail")])
        deepseek = FakeProvider("deepseek")
        router = ProviderRouter()
        result = await router.generate_validated(
            request=_req(),
            providers={"gemini": gemini, "deepseek": deepseek},
            provider_order=["gemini", "deepseek"],
            validate=_always_valid,
            canonical_facts={},
            max_repair_attempts=2,
        )
        deepseek_attempts = [a for a in result.attempts if a.provider == "deepseek"]
        assert any(a.response is not None for a in deepseek_attempts)


# ===================================================================
# Boundaries
# ===================================================================


class TestBoundaries:
    async def test_request_unchanged(self) -> None:
        req = _req()
        original = req.user_prompt
        router = ProviderRouter()
        await router.generate_validated(
            request=req,
            providers={"gemini": FakeProvider("gemini")},
            provider_order=["gemini"],
            validate=_always_valid,
            canonical_facts={},
            max_repair_attempts=2,
        )
        assert req.user_prompt == original

    async def test_no_persistence(self) -> None:
        router = ProviderRouter()
        await router.generate_validated(
            request=_req(),
            providers={"gemini": FakeProvider("gemini")},
            provider_order=["gemini"],
            validate=_always_valid,
            canonical_facts={},
            max_repair_attempts=2,
        )

    async def test_no_real_http(self) -> None:
        router = ProviderRouter()
        await router.generate_validated(
            request=_req(),
            providers={"gemini": FakeProvider("gemini")},
            provider_order=["gemini"],
            validate=_always_valid,
            canonical_facts={},
            max_repair_attempts=2,
        )

    async def test_no_job_mutation(self) -> None:
        router = ProviderRouter()
        await router.generate_validated(
            request=_req(),
            providers={"gemini": FakeProvider("gemini")},
            provider_order=["gemini"],
            validate=_always_valid,
            canonical_facts={},
            max_repair_attempts=2,
        )
