"""Provider repair service (TP-0706).

Bounded repair attempts using the same provider with normalised
validation errors as repair guidance.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from app.ai.parsing import (
    ExtractionError,
    ParseError,
    extract_and_parse_json,
)
from app.ai.providers import AIProvider, ProviderRequest, ProviderResponse
from app.ai.repair.prompt_builder import RepairPromptBuilder
from app.validation import ValidationCategory, ValidationIssue, ValidationSeverity

# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RepairAttempt:
    """A single repair attempt."""

    attempt_number: int
    request: ProviderRequest
    response: ProviderResponse | None = None
    parsed_payload: Mapping[str, object] | None = None
    validation_errors: tuple[ValidationIssue, ...] = ()
    failure_code: str | None = None


@dataclass(frozen=True, slots=True)
class RepairResult:
    """Final result of a repair sequence."""

    payload: Mapping[str, object]
    response: ProviderResponse
    attempts: tuple[RepairAttempt, ...]


# ---------------------------------------------------------------------------
# Stable errors
# ---------------------------------------------------------------------------


class RepairError(Exception):
    """Base for all repair errors."""

    code: str = "REPAIR_ERROR"

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class RepairInvalidAttemptLimitError(RepairError):
    code: str = "REPAIR_INVALID_ATTEMPT_LIMIT"


class RepairProviderFailedError(RepairError):
    code: str = "REPAIR_PROVIDER_FAILED"


class RepairOutputInvalidError(RepairError):
    code: str = "REPAIR_OUTPUT_INVALID"


class RepairValidationFailedError(RepairError):
    code: str = "REPAIR_VALIDATION_FAILED"


class RepairExhaustedError(RepairError):
    code: str = "REPAIR_ATTEMPTS_EXHAUSTED"

    def __init__(
        self,
        code: str | None = None,
        message: str = "",
        *,
        attempts: tuple[RepairAttempt, ...] = (),
    ) -> None:
        self.attempts = attempts
        super().__init__(code=code, message=message)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ProviderRepairService:
    """Repair invalid provider output with bounded retries.

    Uses the same provider for all repair attempts.  Each attempt feeds
    the latest validation errors back into a new repair prompt.
    """

    def __init__(self) -> None:
        self._prompt_builder = RepairPromptBuilder()

    async def repair(
        self,
        *,
        provider: AIProvider,
        original_request: ProviderRequest,
        original_response: ProviderResponse,
        validation_errors: Sequence[ValidationIssue],
        canonical_facts: Mapping[str, object],
        validate: Callable[
            [dict[str, object]],
            tuple[bool, tuple[ValidationIssue, ...]],
        ],
        max_attempts: int,
    ) -> RepairResult:
        if max_attempts < 1:
            raise RepairInvalidAttemptLimitError(
                message=f"max_attempts must be >= 1, got {max_attempts}",
            )

        current_errors = list(validation_errors)
        history: list[RepairAttempt] = []

        for attempt_num in range(1, max_attempts + 1):
            repair_prompt = self._prompt_builder.build(
                original_raw_output=original_response.raw_output,
                validation_errors=current_errors,
                canonical_facts=canonical_facts,
                expected_schema_name=original_request.expected_schema_name,
                expected_schema_version=original_request.expected_schema_version,
            )

            repair_req = ProviderRequest(
                request_id=uuid.uuid4(),
                analysis_type=original_request.analysis_type,
                prompt_version=original_request.prompt_version,
                user_prompt=repair_prompt,
                expected_schema_name=original_request.expected_schema_name,
                expected_schema_version=original_request.expected_schema_version,
                system_prompt=original_request.system_prompt,
                structured_output_schema=original_request.structured_output_schema,
                timeout_seconds=original_request.timeout_seconds,
            )

            try:
                provider_response = await provider.generate(repair_req)
            except Exception as exc:
                code = getattr(exc, "code", "REPAIR_PROVIDER_FAILED")
                attempt_updated = RepairAttempt(
                    attempt_number=attempt_num,
                    request=repair_req,
                    failure_code=code,
                )
                history.append(attempt_updated)
                raise RepairProviderFailedError(
                    message=f"Provider failed on repair attempt {attempt_num}: {exc}",
                ) from exc

            # Parse with TP-0705
            try:
                parsed = extract_and_parse_json(provider_response.raw_output)
            except (ExtractionError, ParseError) as exc:
                code = getattr(exc, "code", "REPAIR_OUTPUT_INVALID")
                attempt_updated = RepairAttempt(
                    attempt_number=attempt_num,
                    request=repair_req,
                    response=provider_response,
                    failure_code=code,
                )
                history.append(attempt_updated)
                if attempt_num < max_attempts:
                    current_errors = _normalize_parsing_failure(
                        exc,
                        provider_response.raw_output,
                    )
                    continue
                raise RepairOutputInvalidError(
                    message=f"Repair output invalid on attempt {attempt_num}: {exc}",
                ) from exc

            # Validate
            is_valid, issues = validate(parsed)

            if is_valid:
                history.append(
                    RepairAttempt(
                        attempt_number=attempt_num,
                        request=repair_req,
                        response=provider_response,
                        parsed_payload=dict(parsed),
                    )
                )
                return RepairResult(
                    payload=dict(parsed),
                    response=provider_response,
                    attempts=tuple(history),
                )

            # Validation failed
            attempt_updated = RepairAttempt(
                attempt_number=attempt_num,
                request=repair_req,
                response=provider_response,
                parsed_payload=dict(parsed),
                validation_errors=tuple(issues),
            )
            history.append(attempt_updated)

            if attempt_num >= max_attempts:
                raise RepairExhaustedError(
                    message=(
                        f"All {max_attempts} repair attempts exhausted. "
                        f"Last attempt had {len(issues)} validation error(s)."
                    ),
                    attempts=tuple(history),
                )

            current_errors = list(issues)

        # Should not be reached, but guard against logic errors
        raise RepairExhaustedError(
            message=f"Repair exhausted after {max_attempts} attempts",
            attempts=tuple(history),
        )


def _normalize_parsing_failure(
    exc: Exception,
    raw_output: str,
) -> list[ValidationIssue]:
    """Wrap a parsing/extraction failure into a single ValidationIssue."""
    code = getattr(exc, "code", "JSON_PARSE_ERROR")
    return [
        ValidationIssue(
            code=code,
            category=ValidationCategory.SCHEMA,
            severity=ValidationSeverity.ERROR,
            path="",
            message=f"JSON parsing failed: {exc}",
        ),
    ]
