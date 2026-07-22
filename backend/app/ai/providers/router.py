"""Provider routing and fallback service (TP-0707).

Orchestrates provider calls in configured order with repair on
the current provider before falling back to the next provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from app.ai.parsing import extract_and_parse_json
from app.ai.providers.base import AIProvider
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
    ) -> None:
        self.attempts = attempts
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

        history: list[ProviderRouteAttempt] = []
        seq = 0
        primary_name = provider_order[0]

        for provider_name in provider_order:
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
                    )
                )
                # Try repair
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

            # --- Validate ---
            is_valid, issues = validate(parsed)

            history.append(
                ProviderRouteAttempt(
                    sequence=seq,
                    provider=provider_name,
                    phase="PRIMARY",
                    response=provider_response,
                    payload=_to_mapping(parsed),
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
                    payload=_to_mapping(parsed),
                    attempts=tuple(history),
                    fallback_used=is_fallback,
                )

            # Validation failed — repair
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
                f"All {len(provider_order)} provider(s) failed ({len(history)} routing attempt(s))"
            ),
            attempts=tuple(history),
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
    return ProviderRouteAttempt(
        sequence=seq,
        provider=provider_name,
        phase="REPAIR",
        response=ra.response,
        payload=(_to_mapping(dict(ra.parsed_payload)) if ra.parsed_payload is not None else None),
        validation_errors=ra.validation_errors,
        failure_code=ra.failure_code,
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
