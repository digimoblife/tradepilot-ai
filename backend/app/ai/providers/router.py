"""Provider routing and fallback service (TP-0707).

Orchestrates provider calls in configured order with repair on
the current provider before falling back to the next provider.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from app.ai.parsing import extract_and_parse_json
from app.ai.providers.base import AIProvider
from app.ai.providers.gemini import normalize_initial_analysis_transport_payload
from app.ai.providers.watching_transport import normalize_watching_update_transport_payload
from app.ai.providers.open_position_transport import normalize_open_position_update_transport_payload
from app.ai.providers.capabilities import ensure_request_supported
from app.ai.providers.models import ProviderRequest, ProviderResponse
from app.ai.repair import (
    ProviderRepairService,
    RepairExhaustedError,
)
from app.ai.repair.service import RepairInvalidAttemptLimitError
from app.logging import get_logger
from app.validation import ValidationCategory, ValidationIssue, ValidationSeverity

# ---------------------------------------------------------------------------
# Attempt/result models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProviderRouteAttempt:
    """A single routing attempt (capability check, primary call, or repair)."""

    sequence: int
    provider: str
    phase: str
    response: ProviderResponse | None = None
    payload: Mapping[str, object] | None = None
    validation_errors: tuple[ValidationIssue, ...] = ()
    failure_code: str | None = None
    failure_message: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderRoutingResult:
    """Successful routing result with attempt history."""

    provider: str
    response: ProviderResponse
    payload: Mapping[str, object]
    attempts: tuple[ProviderRouteAttempt, ...]
    fallback_used: bool


# ---------------------------------------------------------------------------
# Stable errors
# ---------------------------------------------------------------------------


class ProviderRouterError(Exception):
    code: str = "PROVIDER_ROUTER_ERROR"

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class ProviderOrderEmptyError(ProviderRouterError):
    code: str = "PROVIDER_ORDER_EMPTY"


class ProviderUnknownError(ProviderRouterError):
    code: str = "PROVIDER_UNKNOWN"


class ProviderRoutingFailedError(ProviderRouterError):
    code: str = "PROVIDER_ROUTING_FAILED"

    def __init__(
        self,
        code: str | None = None,
        message: str = "",
        *,
        attempts: tuple[ProviderRouteAttempt, ...] = (),
        root_cause_code: str | None = None,
        root_cause_message: str | None = None,
        retryable: bool = True,
    ) -> None:
        self.attempts = attempts
        self.root_cause_code = root_cause_code
        self.root_cause_message = root_cause_message
        self.retryable = retryable
        super().__init__(code=code, message=message)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


class ProviderRouter:
    """Provider routing and fallback service."""

    def __init__(self) -> None:
        self._repair_service = ProviderRepairService()
        self._log = get_logger(__name__)

    async def generate_validated(
        self,
        *,
        request: ProviderRequest,
        providers: Mapping[str, AIProvider],
        provider_order: Sequence[str],
        max_provider_attempts: int | None = None,
        validate: Callable[
            [dict[str, object]],
            tuple[bool, tuple[ValidationIssue, ...]],
        ],
        canonical_facts: Mapping[str, object],
        max_repair_attempts: int,
    ) -> ProviderRoutingResult:
        if not provider_order:
            raise ProviderOrderEmptyError(message="Provider order is empty")

        _validate_provider_order(provider_order, set(providers.keys()))
        effective_order = tuple(provider_order[:max_provider_attempts]) if max_provider_attempts else tuple(provider_order)

        history: list[ProviderRouteAttempt] = []
        seq = 0
        primary_name = effective_order[0]

        for provider_name in effective_order:
            provider_obj = providers[provider_name]
            is_fallback = provider_name != primary_name

            # --- Capability check ---
            seq += 1
            try:
                ensure_request_supported(request, provider_obj.capabilities)
            except Exception as exc:
                code = getattr(exc, "code", "PROVIDER_CAPABILITY_UNSUPPORTED")
                history.append(
                    ProviderRouteAttempt(
                        sequence=seq,
                        provider=provider_name,
                        phase="CAPABILITY_CHECK",
                        failure_code=code,
                        failure_message=_safe_exception_message(exc),
                    )
                )
                continue

            # --- Primary call ---
            seq += 1
            try:
                provider_response = await provider_obj.generate(request)
            except Exception as exc:
                code = getattr(exc, "code", "PROVIDER_REQUEST_FAILED")
                history.append(
                    ProviderRouteAttempt(
                        sequence=seq,
                        provider=provider_name,
                        phase="PRIMARY",
                        failure_code=code,
                        failure_message=_safe_exception_message(exc),
                    )
                )
                continue

            # --- Parse ---
            try:
                parsed = extract_and_parse_json(provider_response.raw_output)
            except Exception as exc:
                code = getattr(exc, "code", "JSON_PARSE_ERROR")
                history.append(
                    ProviderRouteAttempt(
                        sequence=seq,
                        provider=provider_name,
                        phase="PRIMARY",
                        response=provider_response,
                        failure_code=code,
                        failure_message=_safe_exception_message(exc),
                    )
                )
                # Try repair
                if max_repair_attempts > 0:
                    result = await self._repair_and_record(
                        provider_obj=provider_obj,
                        provider_name=provider_name,
                        seq=seq,
                        request=request,
                        response=provider_response,
                        validation_errors=_parse_issues(code, str(exc)),
                        canonical_facts=canonical_facts,
                        validate=validate,
                        max_attempts=max_repair_attempts,
                        history=history,
                        is_fallback=is_fallback,
                    )
                    if result is not None:
                        return result
                    seq = len(history) if history else 0
                continue

            raw_payload = _to_mapping(parsed)
            canonical_payload = raw_payload
            provider_response = _with_payload_metadata(
                provider_response,
                raw_payload=raw_payload,
                normalized_payload=None,
            )

            try:
                canonical_payload = _normalize_payload(
                    request=request,
                    response=provider_response,
                    parsed=raw_payload,
                )
            except Exception as exc:
                code = getattr(exc, "code", "AI_RESPONSE_NORMALIZATION_FAILED")
                message = _safe_exception_message(exc)
                history.append(
                    ProviderRouteAttempt(
                        sequence=seq,
                        provider=provider_name,
                        phase="PRIMARY",
                        response=provider_response,
                        validation_errors=_parse_issues(code, message),
                        failure_code=code,
                        failure_message=message,
                    )
                )
                if max_repair_attempts > 0:
                    result = await self._repair_and_record(
                        provider_obj=provider_obj,
                        provider_name=provider_name,
                        seq=seq,
                        request=request,
                        response=provider_response,
                        validation_errors=_parse_issues(code, message),
                        canonical_facts=canonical_facts,
                        validate=validate,
                        max_attempts=max_repair_attempts,
                        history=history,
                        is_fallback=is_fallback,
                    )
                    if result is not None:
                        return result
                    seq = len(history) if history else 0
                continue

            provider_response = _with_payload_metadata(
                provider_response,
                raw_payload=raw_payload,
                normalized_payload=canonical_payload,
            )

            # --- Validate ---
            is_valid, issues = validate(dict(canonical_payload))
            validation_failure_code = None
            validation_failure_message = None
            if not is_valid:
                joined_messages = "; ".join(issue.message for issue in issues if issue.message)
                if issues and joined_messages:
                    validation_failure_code = issues[0].code
                    validation_failure_message = _sanitize_failure_message(joined_messages)
                else:
                    validation_failure_code = "REPAIR_VALIDATION_FAILED"
                    validation_failure_message = (
                        "Provider response validation failed with no issue details returned."
                    )

            history.append(
                ProviderRouteAttempt(
                    sequence=seq,
                    provider=provider_name,
                    phase="PRIMARY",
                    response=provider_response,
                    payload=canonical_payload,
                    validation_errors=issues,
                    failure_code=validation_failure_code,
                    failure_message=validation_failure_message,
                )
            )

            if is_valid:
                self._log.info(
                    "Provider routing succeeded",
                    extra={
                        "provider": provider_obj.name,
                        "model": provider_obj.model,
                        "schema": request.expected_schema_name,
                        "request_id": str(request.request_id),
                        "fallback_used": is_fallback,
                    },
                )
                return ProviderRoutingResult(
                    provider=provider_name,
                    response=provider_response,
                    payload=canonical_payload,
                    attempts=tuple(history),
                    fallback_used=is_fallback,
                )

            # Validation failed — repair
            if max_repair_attempts > 0:
                result = await self._repair_and_record(
                    provider_obj=provider_obj,
                    provider_name=provider_name,
                    seq=seq,
                    request=request,
                    response=provider_response,
                    validation_errors=list(issues),
                    canonical_facts=canonical_facts,
                    validate=validate,
                    max_attempts=max_repair_attempts,
                    history=history,
                    is_fallback=is_fallback,
                )
                if result is not None:
                    return result
                seq = len(history) if history else 0

        raise ProviderRoutingFailedError(
            message=(
                f"All {len(effective_order)} provider(s) failed ({len(history)} routing attempt(s))"
            ),
            attempts=tuple(history),
            root_cause_code=_root_cause_code(history),
            root_cause_message=_root_cause_message(history),
            retryable=_routing_failure_retryable(history),
        )

    async def _repair_and_record(
        self,
        *,
        provider_obj: AIProvider,
        provider_name: str,
        seq: int,
        request: ProviderRequest,
        response: ProviderResponse,
        validation_errors: list[ValidationIssue],
        canonical_facts: Mapping[str, object],
        validate: Callable[
            [dict[str, object]],
            tuple[bool, tuple[ValidationIssue, ...]],
        ],
        max_attempts: int,
        history: list[ProviderRouteAttempt],
        is_fallback: bool,
    ) -> ProviderRoutingResult | None:
        try:
            repair_result = await self._repair_service.repair(
                provider=provider_obj,
                original_request=request,
                original_response=response,
                validation_errors=validation_errors,
                canonical_facts=canonical_facts,
                validate=validate,
                max_attempts=max_attempts,
            )
        except RepairExhaustedError as exc:
            for ra in getattr(exc, "attempts", ()):
                seq += 1
                history.append(_repair_to_route(seq, provider_name, ra))
            return None
        except RepairInvalidAttemptLimitError:
            return None
        except Exception as exc:
            code = getattr(exc, "code", "REPAIR_PROVIDER_FAILED")
            seq += 1
            history.append(
                    ProviderRouteAttempt(
                        sequence=seq,
                        provider=provider_name,
                        phase="REPAIR",
                        failure_code=code,
                        failure_message=_safe_exception_message(exc),
                    )
                )
            return None

        # Repair succeeded
        for ra in repair_result.attempts:
            seq += 1
            history.append(_repair_to_route(seq, provider_name, ra))

        return ProviderRoutingResult(
            provider=provider_name,
            response=repair_result.response,
            payload=_to_mapping(dict(repair_result.payload)),
            attempts=tuple(history),
            fallback_used=is_fallback,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_provider_order(
    order: Sequence[str],
    available: set[str],
) -> None:
    for name in order:
        if name not in available:
            raise ProviderUnknownError(
                message=f"Unknown provider in order: {name!r}. Available: {sorted(available)}",
            )


def _repair_to_route(seq: int, provider_name: str, ra: Any) -> ProviderRouteAttempt:
    failure_message = None
    if getattr(ra, "validation_errors", ()):
        failure_message = _sanitize_failure_message(
            "; ".join(issue.message for issue in ra.validation_errors if issue.message) or ""
        )
    return ProviderRouteAttempt(
        sequence=seq,
        provider=provider_name,
        phase="REPAIR",
        response=ra.response,
        payload=(_to_mapping(dict(ra.parsed_payload)) if ra.parsed_payload is not None else None),
        validation_errors=ra.validation_errors,
        failure_code=ra.failure_code,
        failure_message=failure_message,
    )


def _parse_issues(code: str, message: str) -> list[ValidationIssue]:
    return [
        ValidationIssue(
            code=code,
            category=ValidationCategory.SCHEMA,
            severity=ValidationSeverity.ERROR,
            path="",
            message=message,
        ),
    ]


def _to_mapping(d: dict[str, object]) -> Mapping[str, object]:
    return dict(d)


def _normalize_payload(
    *,
    request: ProviderRequest,
    response: ProviderResponse,
    parsed: Mapping[str, object],
) -> Mapping[str, object]:
    if response.provider == "gemini" and request.expected_schema_name == "open_position_update":
        return normalize_open_position_update_transport_payload(
            parsed,
            application_metadata=request.metadata,
        )
    if response.provider == "gemini" and request.expected_schema_name == "watching_update":
        return normalize_watching_update_transport_payload(
            parsed,
            application_metadata=request.metadata,
        )
    if (
        response.provider == "gemini"
        and request.expected_schema_name == "initial_analysis"
        and any(name in parsed for name in ("chart_3_month_analysis", "chart_6_month_analysis"))
    ):
        canonical_chart_timestamps = None
        if isinstance(request.metadata, Mapping):
            raw = request.metadata.get("canonical_chart_timestamps")
            if isinstance(raw, Mapping):
                canonical_chart_timestamps = {
                    str(key): value
                    for key, value in raw.items()
                    if isinstance(value, str)
                }
        return normalize_initial_analysis_transport_payload(
            parsed,
            canonical_chart_timestamps=canonical_chart_timestamps,
        )
    return dict(parsed)


def _with_payload_metadata(
    response: ProviderResponse,
    *,
    raw_payload: Mapping[str, object],
    normalized_payload: Mapping[str, object] | None,
) -> ProviderResponse:
    metadata = dict(response.metadata) if isinstance(response.metadata, dict) else {}
    metadata["provider_payload_raw"] = dict(raw_payload)
    if normalized_payload is not None:
        metadata["normalized_payload"] = dict(normalized_payload)
    return ProviderResponse(
        provider=response.provider,
        model=response.model,
        raw_output=response.raw_output,
        request_id=response.request_id,
        provider_response_id=response.provider_response_id,
        finish_reason=response.finish_reason,
        usage=response.usage,
        latency_ms=response.latency_ms,
        metadata=metadata,
    )


_NON_RETRYABLE_ROUTING_CODES = frozenset(
    {
        "AI_PROVIDER_AUTHENTICATION_FAILED",
        "AI_PROVIDER_INVALID_REQUEST",
        "AI_PROVIDER_CONTENT_FILTERED",
        "AI_RESPONSE_EMPTY",
        "PROVIDER_CAPABILITY_UNSUPPORTED",
        "PROVIDER_UNKNOWN",
        "PROVIDER_ORDER_EMPTY",
        "JSON_PARSE_ERROR",
        "REPAIR_VALIDATION_FAILED",
    }
)
_SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)\b(api[_ -]?key|authorization|bearer|token)\b\s*[:=]\s*([^\s,;]+)"
)


def _routing_failure_retryable(attempts: Sequence[ProviderRouteAttempt]) -> bool:
    code = _root_cause_code(attempts)
    if code is None:
        return True
    if code in {"AI_PROVIDER_RATE_LIMITED", "AI_PROVIDER_TIMEOUT"}:
        return True
    if code in _NON_RETRYABLE_ROUTING_CODES:
        return False
    if code.startswith("SCHEMA_"):
        return False
    return True


def _root_cause_code(attempts: Sequence[ProviderRouteAttempt]) -> str | None:
    for attempt in reversed(attempts):
        if attempt.failure_code:
            return attempt.failure_code
    return None


def _root_cause_message(attempts: Sequence[ProviderRouteAttempt]) -> str | None:
    for attempt in reversed(attempts):
        if attempt.failure_message:
            return attempt.failure_message
    return None


def _sanitize_failure_message(message: str) -> str:
    cleaned = _SENSITIVE_VALUE_PATTERN.sub(r"\1=[REDACTED]", message)
    return cleaned[:500] if len(cleaned) > 500 else cleaned


def _safe_exception_message(exc: Exception) -> str:
    message = _sanitize_failure_message(str(exc))
    if message:
        return message

    fallback = getattr(exc, "message", "")
    if isinstance(fallback, str):
        fallback_message = _sanitize_failure_message(fallback.strip())
        if fallback_message:
            return fallback_message

    return _sanitize_failure_message(repr(exc))
