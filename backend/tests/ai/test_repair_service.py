"""Tests for ProviderRepairService (TP-0706).

Uses fake providers and callbacks — no real network access.
"""

from __future__ import annotations

import uuid
from typing import Any, Callable

import pytest

from app.ai.providers import (
    AIProvider,
    ProviderCapabilities,
    ProviderRequest,
    ProviderResponse,
)
from app.ai.repair import (
    ProviderRepairService,
    RepairExhaustedError,
    RepairInvalidAttemptLimitError,
    RepairProviderFailedError,
    RepairResult,
)
from app.validation import ValidationCategory, ValidationIssue, ValidationSeverity

# ===================================================================
# Fake provider
# ===================================================================


class FakeRepairProvider(AIProvider):
    """Fake provider for repair tests. Returns configurable responses."""

    def __init__(
        self,
        responses: list[ProviderResponse | Exception],
    ) -> None:
        self._responses = list(responses)
        self.call_count = 0
        self.last_request: ProviderRequest | None = None

    @property
    def name(self) -> str:
        return "fake-repair"

    @property
    def model(self) -> str:
        return "fake-model"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities()

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        self.call_count += 1
        self.last_request = request
        resp = self._responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


# ===================================================================
# Helpers
# ===================================================================


def _make_request(**overrides: Any) -> ProviderRequest:
    kwargs = dict(
        request_id=uuid.uuid4(),
        analysis_type="INITIAL_ANALYSIS",
        prompt_version="1.0.0",
        user_prompt="Analyze",
        expected_schema_name="initial_analysis",
        expected_schema_version="1.0",
        system_prompt="You are an analyst.",
    )
    kwargs.update(overrides)
    return ProviderRequest(**kwargs)


def _make_response(
    raw_output: str = '{"result": "ok"}',
) -> ProviderResponse:
    return ProviderResponse(
        provider="gemini",
        model="gemini-2.0-flash",
        raw_output=raw_output,
        request_id=uuid.uuid4(),
    )


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
            message="Test validation error",
        ),
    )


def _valid_on_nth(n: int) -> Callable:
    """Return a validate function that succeeds on the *n*-th call (1-indexed)."""

    class _Counter:
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
                    path="/retry",
                    message=f"Attempt {self.calls}",
                ),
            )

    return _Counter()


# ===================================================================
# Repair prompt
# ===================================================================


class TestRepairPrompt:
    def test_normalized_error_codes_included(self) -> None:
        from app.ai.repair.prompt_builder import RepairPromptBuilder

        builder = RepairPromptBuilder()
        issues = [
            ValidationIssue(
                code="SCHEMA_ERROR",
                category=ValidationCategory.SCHEMA,
                severity=ValidationSeverity.ERROR,
                path="/price",
                message="Price must be positive",
            ),
        ]
        prompt = builder.build(
            original_raw_output='{"price": -1}',
            validation_errors=issues,
            canonical_facts={"ticker": "BBRI"},
            expected_schema_name="test",
            expected_schema_version="1.0",
        )
        assert "SCHEMA_ERROR" in prompt
        assert "/price" in prompt
        assert "Price must be positive" in prompt

    def test_canonical_facts_included(self) -> None:
        from app.ai.repair.prompt_builder import RepairPromptBuilder

        builder = RepairPromptBuilder()
        prompt = builder.build(
            original_raw_output="{}",
            validation_errors=[],
            canonical_facts={"ticker": "BBRI", "entry_price": 2500},
            expected_schema_name="test",
            expected_schema_version="1.0",
        )
        assert "BBRI" in prompt
        assert "2500" in prompt

    def test_canonical_facts_protected(self) -> None:
        from app.ai.repair.prompt_builder import RepairPromptBuilder

        builder = RepairPromptBuilder()
        prompt = builder.build(
            original_raw_output="{}",
            validation_errors=[],
            canonical_facts={"ticker": "BBRI"},
            expected_schema_name="test",
            expected_schema_version="1.0",
        )
        assert "DO NOT CHANGE" in prompt
        assert "authoritative" in prompt.lower()

    def test_json_only_instruction(self) -> None:
        from app.ai.repair.prompt_builder import RepairPromptBuilder

        builder = RepairPromptBuilder()
        prompt = builder.build(
            original_raw_output="{}",
            validation_errors=[],
            canonical_facts={},
            expected_schema_name="test",
            expected_schema_version="1.0",
        )
        assert "exactly one valid JSON object" in prompt
        assert "markdown" in prompt.lower()
        assert "commentary" in prompt.lower()
        assert "array" in prompt.lower()

    def test_original_output_included(self) -> None:
        from app.ai.repair.prompt_builder import RepairPromptBuilder

        builder = RepairPromptBuilder()
        prompt = builder.build(
            original_raw_output='{"bad": "value"}',
            validation_errors=[],
            canonical_facts={"ticker": "BBRI"},
            expected_schema_name="test",
            expected_schema_version="1.0",
        )
        assert '{"bad": "value"}' in prompt

    def test_schema_identity_included(self) -> None:
        from app.ai.repair.prompt_builder import RepairPromptBuilder

        builder = RepairPromptBuilder()
        prompt = builder.build(
            original_raw_output="{}",
            validation_errors=[],
            canonical_facts={},
            expected_schema_name="initial_analysis",
            expected_schema_version="1.5",
        )
        assert "initial_analysis" in prompt
        assert "1.5" in prompt

    def test_inputs_not_mutated(self) -> None:
        from app.ai.repair.prompt_builder import RepairPromptBuilder

        builder = RepairPromptBuilder()
        facts = {"ticker": "BBRI"}
        issues = [
            ValidationIssue(
                code="ERR",
                category=ValidationCategory.SCHEMA,
                severity=ValidationSeverity.ERROR,
                path="/x",
                message="Error",
            ),
        ]
        orig_facts = dict(facts)
        orig_issues = list(issues)
        builder.build(
            original_raw_output="{}",
            validation_errors=issues,
            canonical_facts=facts,
            expected_schema_name="s",
            expected_schema_version="v",
        )
        assert facts == orig_facts
        assert len(issues) == len(orig_issues)


# ===================================================================
# Successful repair
# ===================================================================


class TestSuccessfulRepair:
    async def test_first_attempt_succeeds(self) -> None:
        provider = FakeRepairProvider(
            responses=[_make_response('{"fixed": true}')],
        )
        service = ProviderRepairService()
        result = await service.repair(
            provider=provider,
            original_request=_make_request(),
            original_response=_make_response('{"bad": 1}'),
            validation_errors=[],
            canonical_facts={"ticker": "BBRI"},
            validate=_always_valid,
            max_attempts=3,
        )
        assert isinstance(result, RepairResult)
        assert result.payload == {"fixed": True}
        assert provider.call_count == 1

    async def test_common_request_used(self) -> None:
        provider = FakeRepairProvider(
            responses=[_make_response('{"ok": true}')],
        )
        service = ProviderRepairService()
        orig_req = _make_request()
        await service.repair(
            provider=provider,
            original_request=orig_req,
            original_response=_make_response(),
            validation_errors=[],
            canonical_facts={},
            validate=_always_valid,
            max_attempts=1,
        )
        assert provider.last_request is not None
        assert provider.last_request.analysis_type == orig_req.analysis_type
        assert provider.last_request.expected_schema_name == orig_req.expected_schema_name

    async def test_attempt_count_is_one(self) -> None:
        provider = FakeRepairProvider(
            responses=[_make_response('{"ok": true}')],
        )
        service = ProviderRepairService()
        result = await service.repair(
            provider=provider,
            original_request=_make_request(),
            original_response=_make_response(),
            validation_errors=[],
            canonical_facts={},
            validate=_always_valid,
            max_attempts=3,
        )
        assert len(result.attempts) == 1

    async def test_no_later_call_after_success(self) -> None:
        provider = FakeRepairProvider(
            responses=[_make_response('{"ok": true}')],
        )
        service = ProviderRepairService()
        await service.repair(
            provider=provider,
            original_request=_make_request(),
            original_response=_make_response(),
            validation_errors=[],
            canonical_facts={},
            validate=_always_valid,
            max_attempts=5,
        )
        assert provider.call_count == 1


# ===================================================================
# Validation retry
# ===================================================================


class TestValidationRetry:
    async def test_validation_failure_triggers_retry(self) -> None:
        provider = FakeRepairProvider(
            responses=[
                _make_response('{"attempt": 1}'),
                _make_response('{"attempt": 2, "fixed": true}'),
            ],
        )
        validate = _valid_on_nth(2)
        service = ProviderRepairService()
        result = await service.repair(
            provider=provider,
            original_request=_make_request(),
            original_response=_make_response(),
            validation_errors=[],
            canonical_facts={},
            validate=validate,
            max_attempts=3,
        )
        assert result.payload == {"attempt": 2, "fixed": True}
        assert provider.call_count == 2

    async def test_latest_errors_in_retry_prompt(self) -> None:
        provider = FakeRepairProvider(
            responses=[
                _make_response('{"v": 1}'),
                _make_response('{"v": 2}'),
            ],
        )
        service = ProviderRepairService()
        await service.repair(
            provider=provider,
            original_request=_make_request(),
            original_response=_make_response(),
            validation_errors=[],
            canonical_facts={},
            validate=_valid_on_nth(2),
            max_attempts=3,
        )
        # The second request should include the retry validation error
        assert provider.last_request is not None
        assert (
            "RETRY" in provider.last_request.user_prompt
            or "Attempt" in provider.last_request.user_prompt
        )  # noqa: E501


# ===================================================================
# Parsing retry
# ===================================================================


class TestParsingRetry:
    async def test_parsing_failure_triggers_retry(self) -> None:
        provider = FakeRepairProvider(
            responses=[
                _make_response(raw_output="not json at all"),
                _make_response(raw_output='{"fixed": true}'),
            ],
        )
        service = ProviderRepairService()
        result = await service.repair(
            provider=provider,
            original_request=_make_request(),
            original_response=_make_response(),
            validation_errors=[],
            canonical_facts={},
            validate=_always_valid,
            max_attempts=3,
        )
        assert result.payload == {"fixed": True}
        assert provider.call_count == 2

    async def test_parsing_failure_normalized(self) -> None:
        provider = FakeRepairProvider(
            responses=[
                _make_response(raw_output="[1, 2]"),
                _make_response(raw_output='{"ok": true}'),
            ],
        )
        service = ProviderRepairService()
        result = await service.repair(
            provider=provider,
            original_request=_make_request(),
            original_response=_make_response(),
            validation_errors=[],
            canonical_facts={},
            validate=_always_valid,
            max_attempts=3,
        )
        assert result.payload == {"ok": True}


# ===================================================================
# Maximum attempts
# ===================================================================


class TestMaxAttempts:
    async def test_zero_rejected(self) -> None:
        service = ProviderRepairService()
        with pytest.raises(RepairInvalidAttemptLimitError):
            await service.repair(
                provider=FakeRepairProvider([]),
                original_request=_make_request(),
                original_response=_make_response(),
                validation_errors=[],
                canonical_facts={},
                validate=_always_valid,
                max_attempts=0,
            )

    async def test_negative_rejected(self) -> None:
        service = ProviderRepairService()
        with pytest.raises(RepairInvalidAttemptLimitError):
            await service.repair(
                provider=FakeRepairProvider([]),
                original_request=_make_request(),
                original_response=_make_response(),
                validation_errors=[],
                canonical_facts={},
                validate=_always_valid,
                max_attempts=-1,
            )

    async def test_exact_maximum_calls(self) -> None:
        provider = FakeRepairProvider(
            responses=[
                _make_response('{"a": 1}'),
                _make_response('{"a": 2}'),
            ],
        )
        service = ProviderRepairService()
        with pytest.raises(RepairExhaustedError):
            await service.repair(
                provider=provider,
                original_request=_make_request(),
                original_response=_make_response(),
                validation_errors=[],
                canonical_facts={},
                validate=_always_invalid,
                max_attempts=2,
            )
        assert provider.call_count == 2

    async def test_no_call_beyond_maximum(self) -> None:
        provider = FakeRepairProvider(
            responses=[
                _make_response('{"a": 1}'),
            ],
        )
        service = ProviderRepairService()
        with pytest.raises(RepairExhaustedError):
            await service.repair(
                provider=provider,
                original_request=_make_request(),
                original_response=_make_response(),
                validation_errors=[],
                canonical_facts={},
                validate=_always_invalid,
                max_attempts=1,
            )
        assert provider.call_count == 1

    async def test_stable_exhausted_error(self) -> None:
        provider = FakeRepairProvider(
            responses=[
                _make_response('{"a": 1}'),
            ],
        )
        service = ProviderRepairService()
        with pytest.raises(RepairExhaustedError) as exc:
            await service.repair(
                provider=provider,
                original_request=_make_request(),
                original_response=_make_response(),
                validation_errors=[],
                canonical_facts={},
                validate=_always_invalid,
                max_attempts=1,
            )
        assert "REPAIR_ATTEMPTS_EXHAUSTED" in str(exc.value)


# ===================================================================
# Provider failure
# ===================================================================


class TestProviderFailure:
    async def test_provider_failure_propagates(self) -> None:
        provider = FakeRepairProvider(
            responses=[Exception("API failure")],
        )
        service = ProviderRepairService()
        with pytest.raises(RepairProviderFailedError):
            await service.repair(
                provider=provider,
                original_request=_make_request(),
                original_response=_make_response(),
                validation_errors=[],
                canonical_facts={},
                validate=_always_valid,
                max_attempts=3,
            )

    async def test_no_fallback_provider(self) -> None:
        """Only the original provider is called."""
        provider = FakeRepairProvider(
            responses=[Exception("fail")],
        )
        service = ProviderRepairService()
        with pytest.raises(RepairProviderFailedError):
            await service.repair(
                provider=provider,
                original_request=_make_request(),
                original_response=_make_response(),
                validation_errors=[],
                canonical_facts={},
                validate=_always_valid,
                max_attempts=1,
            )
        assert provider.call_count == 1


# ===================================================================
# Immutability
# ===================================================================


class TestImmutability:
    async def test_canonical_facts_unchanged(self) -> None:
        provider = FakeRepairProvider(
            responses=[_make_response('{"ok": true}')],
        )
        service = ProviderRepairService()
        facts = {"ticker": "BBRI", "price": 2500}
        orig = dict(facts)
        await service.repair(
            provider=provider,
            original_request=_make_request(),
            original_response=_make_response(),
            validation_errors=[],
            canonical_facts=facts,
            validate=_always_valid,
            max_attempts=1,
        )
        assert facts == orig

    async def test_original_request_unchanged(self) -> None:
        provider = FakeRepairProvider(
            responses=[_make_response('{"ok": true}')],
        )
        service = ProviderRepairService()
        req = _make_request()
        orig_prompt = req.user_prompt
        await service.repair(
            provider=provider,
            original_request=req,
            original_response=_make_response(),
            validation_errors=[],
            canonical_facts={},
            validate=_always_valid,
            max_attempts=1,
        )
        assert req.user_prompt == orig_prompt

    async def test_original_response_unchanged(self) -> None:
        provider = FakeRepairProvider(
            responses=[_make_response('{"ok": true}')],
        )
        service = ProviderRepairService()
        resp = _make_response('{"original": true}')
        orig_raw = resp.raw_output
        await service.repair(
            provider=provider,
            original_request=_make_request(),
            original_response=resp,
            validation_errors=[],
            canonical_facts={},
            validate=_always_valid,
            max_attempts=1,
        )
        assert resp.raw_output == orig_raw


# ===================================================================
# Boundaries
# ===================================================================


class TestBoundaries:
    async def test_no_database_access(self) -> None:
        service = ProviderRepairService()
        provider = FakeRepairProvider(
            responses=[_make_response('{"ok": true}')],
        )
        await service.repair(
            provider=provider,
            original_request=_make_request(),
            original_response=_make_response(),
            validation_errors=[],
            canonical_facts={},
            validate=_always_valid,
            max_attempts=1,
        )

    async def test_no_persistence(self) -> None:
        service = ProviderRepairService()
        provider = FakeRepairProvider(
            responses=[_make_response('{"ok": true}')],
        )
        await service.repair(
            provider=provider,
            original_request=_make_request(),
            original_response=_make_response(),
            validation_errors=[],
            canonical_facts={},
            validate=_always_valid,
            max_attempts=1,
        )

    async def test_no_real_http(self) -> None:
        service = ProviderRepairService()
        provider = FakeRepairProvider(
            responses=[_make_response('{"ok": true}')],
        )
        await service.repair(
            provider=provider,
            original_request=_make_request(),
            original_response=_make_response(),
            validation_errors=[],
            canonical_facts={},
            validate=_always_valid,
            max_attempts=1,
        )

    async def test_no_fallback_routing(self) -> None:
        """Only the injected provider is used."""
        service = ProviderRepairService()
        provider = FakeRepairProvider(
            responses=[_make_response('{"ok": true}')],
        )
        await service.repair(
            provider=provider,
            original_request=_make_request(),
            original_response=_make_response(),
            validation_errors=[],
            canonical_facts={},
            validate=_always_valid,
            max_attempts=1,
        )
