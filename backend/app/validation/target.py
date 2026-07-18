"""Target domain validation: target must be above entry for initial long setups."""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from app.calculations.decimal_utils import to_decimal
from app.calculations.errors import InvalidDecimalError
from app.validation.issues import ValidationCategory, ValidationIssue, ValidationSeverity

DOMAIN = ValidationCategory("DOMAIN")

NUMERIC_INPUT_INVALID = "NUMERIC_INPUT_INVALID"
TARGET_NOT_ABOVE_ENTRY = "TARGET_NOT_ABOVE_ENTRY"


def _make_issue(
    code: str, path: str, message: str, expected: str | None = None, actual: str | None = None
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        category=DOMAIN,
        severity=ValidationSeverity.ERROR,
        path=path,
        message=message,
        expected=expected,
        actual=actual,
    )


def _d(value: object) -> Decimal | None:
    if value is None:
        return None
    return to_decimal(value)  # type: ignore[arg-type]


def _sort_key(issue: ValidationIssue) -> tuple[str, str, str, str]:
    return (issue.path, issue.code, issue.category.value, issue.message)


def validate_target(payload: Mapping[str, object]) -> tuple[ValidationIssue, ...]:
    """Validate the target plan within an analysis payload.

    For an initial long setup, enforces ``target_price > entry_reference``.
    The entry reference is the ``entry_price`` for exact-entry plans, or
    the ``entry_zone_high`` for zone-entry plans (worst-case entry).
    """
    issues: list[ValidationIssue] = []

    entry_plan = payload.get("entry_plan")
    target_plan = payload.get("target_plan")
    if not isinstance(entry_plan, dict) or not isinstance(target_plan, dict):
        return ()

    # Numeric input check
    for field, path in (("target_price", "/target_plan/target_price"),):
        raw = target_plan.get(field)
        if raw is not None:
            try:
                _d(raw)
            except InvalidDecimalError:
                issues.append(
                    _make_issue(
                        NUMERIC_INPUT_INVALID,
                        path,
                        (
                            "Invalid numeric input for {field}: "
                            "type={type(raw).__name__}, value={raw!r}"
                        ),
                        expected="Decimal, int, or str",
                        actual=f"{type(raw).__name__}: {raw!r}",
                    )
                )

    if issues:
        return tuple(sorted(issues, key=_sort_key))

    recommended = target_plan.get("target_recommended")
    target_price = _d(target_plan.get("target_price"))

    entry_type = entry_plan.get("entry_type")
    entry_price = _d(entry_plan.get("entry_price"))
    zone_high = _d(entry_plan.get("entry_zone_high"))

    # Determine entry reference
    if entry_type == "EXACT_PRICE":
        ref_price = entry_price
    elif entry_type == "PRICE_ZONE":
        ref_price = zone_high
    else:
        ref_price = None

    if recommended is True and target_price is not None and ref_price is not None:
        if target_price <= ref_price:
            issues.append(
                _make_issue(
                    TARGET_NOT_ABOVE_ENTRY,
                    "/target_plan/target_price",
                    f"Target ({target_price}) must be above entry reference ({ref_price})",
                    expected=f"> {ref_price}",
                    actual=str(target_price),
                )
            )

    return tuple(sorted(issues, key=_sort_key))
