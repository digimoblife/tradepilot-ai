"""Stop-loss domain validation: stop must be below entry for initial long setups."""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from app.calculations.decimal_utils import to_decimal
from app.calculations.errors import InvalidDecimalError
from app.validation.issues import ValidationCategory, ValidationIssue, ValidationSeverity

DOMAIN = ValidationCategory("DOMAIN")

NUMERIC_INPUT_INVALID = "NUMERIC_INPUT_INVALID"
STOP_NOT_BELOW_ENTRY = "STOP_NOT_BELOW_ENTRY"


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


def validate_stop_loss(payload: Mapping[str, object]) -> tuple[ValidationIssue, ...]:
    """Validate the stop-loss plan within an analysis payload.

    For an initial long setup, enforces ``stop_loss_price < entry_reference``.
    The entry reference is the ``entry_price`` from the ``entry_plan`` for
    exact-entry plans, or the ``entry_zone_low`` for zone-entry plans.
    """
    issues: list[ValidationIssue] = []

    entry_plan = payload.get("entry_plan")
    stop_plan = payload.get("stop_loss_plan")
    if not isinstance(entry_plan, dict) or not isinstance(stop_plan, dict):
        return ()

    # Numeric input check
    for field, path in (("stop_loss_price", "/stop_loss_plan/stop_loss_price"),):
        raw = stop_plan.get(field)
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

    recommended = stop_plan.get("stop_loss_recommended")
    stop_price = _d(stop_plan.get("stop_loss_price"))

    entry_type = entry_plan.get("entry_type")
    entry_price = _d(entry_plan.get("entry_price"))
    zone_low = _d(entry_plan.get("entry_zone_low"))

    # Determine entry reference: exact price for EXACT_PRICE, zone low for PRICE_ZONE
    if entry_type == "EXACT_PRICE":
        ref_price = entry_price
    elif entry_type == "PRICE_ZONE":
        ref_price = zone_low
    else:
        ref_price = None

    if recommended is True and stop_price is not None and ref_price is not None:
        if stop_price >= ref_price:
            issues.append(
                _make_issue(
                    STOP_NOT_BELOW_ENTRY,
                    "/stop_loss_plan/stop_loss_price",
                    f"Stop loss ({stop_price}) must be below entry reference ({ref_price})",
                    expected=f"< {ref_price}",
                    actual=str(stop_price),
                )
            )

    return tuple(sorted(issues, key=_sort_key))
