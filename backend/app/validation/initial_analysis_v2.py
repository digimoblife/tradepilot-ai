from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Mapping

from app.validation.issues import ValidationCategory, ValidationIssue, ValidationSeverity


def validate_initial_analysis_v2(payload: Mapping[str, object]) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    plan = payload.get("trade_plan")
    if not isinstance(plan, Mapping):
        return ()

    entry_low = _decimal_or_none(plan.get("entry_zone_low"))
    entry_high = _decimal_or_none(plan.get("entry_zone_high"))
    stop_loss = _decimal_or_none(plan.get("stop_loss"))
    target_1 = _decimal_or_none(plan.get("target_1"))
    invalidation = _decimal_or_none(plan.get("invalidation"))

    if entry_low is not None and entry_high is not None and entry_low > entry_high:
        issues.append(
            ValidationIssue(
                code="DOMAIN_ENTRY_ZONE_INVALID",
                category=ValidationCategory.DOMAIN,
                severity=ValidationSeverity.ERROR,
                path="/trade_plan/entry_zone_low",
                message="entry_zone_low must be less than or equal to entry_zone_high",
                expected="entry_zone_low <= entry_zone_high",
                actual=str(entry_low),
            )
        )

    reference_entry = entry_low if entry_low is not None else entry_high
    if reference_entry is not None and stop_loss is not None and stop_loss >= reference_entry:
        issues.append(
            ValidationIssue(
                code="DOMAIN_STOP_LOSS_ABOVE_ENTRY",
                category=ValidationCategory.DOMAIN,
                severity=ValidationSeverity.ERROR,
                path="/trade_plan/stop_loss",
                message="stop_loss should be below reference entry for a long setup",
                expected="stop_loss < reference_entry",
                actual=str(stop_loss),
            )
        )

    if reference_entry is not None and target_1 is not None and target_1 <= reference_entry:
        issues.append(
            ValidationIssue(
                code="DOMAIN_TARGET_BELOW_ENTRY",
                category=ValidationCategory.DOMAIN,
                severity=ValidationSeverity.ERROR,
                path="/trade_plan/target_1",
                message="target_1 should be above reference entry for a long setup",
                expected="target_1 > reference_entry",
                actual=str(target_1),
            )
        )

    if invalidation is not None and reference_entry is not None and invalidation >= reference_entry:
        issues.append(
            ValidationIssue(
                code="DOMAIN_INVALIDATION_ABOVE_ENTRY",
                category=ValidationCategory.DOMAIN,
                severity=ValidationSeverity.ERROR,
                path="/trade_plan/invalidation",
                message="invalidation should be below reference entry for a long setup",
                expected="invalidation < reference_entry",
                actual=str(invalidation),
            )
        )

    return tuple(issues)


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
