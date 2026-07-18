"""Entry plan domain validation: exact entry, zone entry, maximum acceptable entry."""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from app.calculations.decimal_utils import to_decimal
from app.calculations.errors import InvalidDecimalError
from app.validation.issues import ValidationCategory, ValidationIssue, ValidationSeverity

DOMAIN = ValidationCategory("DOMAIN")

NUMERIC_INPUT_INVALID = "NUMERIC_INPUT_INVALID"
EXACT_ENTRY_STRUCTURE_INVALID = "EXACT_ENTRY_STRUCTURE_INVALID"
ENTRY_ZONE_STRUCTURE_INVALID = "ENTRY_ZONE_STRUCTURE_INVALID"
ENTRY_ZONE_LOW_ABOVE_HIGH = "ENTRY_ZONE_LOW_ABOVE_HIGH"
MAXIMUM_ACCEPTABLE_ENTRY_INVALID = "MAXIMUM_ACCEPTABLE_ENTRY_INVALID"
ENTRY_ABOVE_MAXIMUM_ACCEPTABLE = "ENTRY_ABOVE_MAXIMUM_ACCEPTABLE"
NON_ENTRY_PLAN_HAS_ENTRY_PRICE = "NON_ENTRY_PLAN_HAS_ENTRY_PRICE"


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


def validate_entry_plan(payload: Mapping[str, object]) -> tuple[ValidationIssue, ...]:
    """Validate the entry plan within an analysis payload.

    Expects ``payload`` to contain an ``entry_plan`` dict with the canonical
    entry-plan fields.
    """
    issues: list[ValidationIssue] = []

    entry_plan = payload.get("entry_plan")
    if not isinstance(entry_plan, dict):
        return ()

    # Numeric input check
    for field, path in (
        ("entry_price", "/entry_plan/entry_price"),
        ("entry_zone_low", "/entry_plan/entry_zone_low"),
        ("entry_zone_high", "/entry_plan/entry_zone_high"),
        ("maximum_acceptable_entry", "/entry_plan/maximum_acceptable_entry"),
    ):
        raw = entry_plan.get(field)
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

    recommended = entry_plan.get("entry_recommended")
    entry_type = entry_plan.get("entry_type")
    entry_price = _d(entry_plan.get("entry_price"))
    zone_low = _d(entry_plan.get("entry_zone_low"))
    zone_high = _d(entry_plan.get("entry_zone_high"))
    max_acceptable = _d(entry_plan.get("maximum_acceptable_entry"))

    # Non-entry plans must not have entry prices
    if recommended is False or entry_type in ("WAIT", "NO_ENTRY"):
        if entry_price is not None or zone_low is not None or zone_high is not None:
            issues.append(
                _make_issue(
                    NON_ENTRY_PLAN_HAS_ENTRY_PRICE,
                    "/entry_plan",
                    f"Non-entry plan ({entry_type}) must not have entry price or zone fields",
                    expected="null entry fields",
                    actual="non-null entry fields present",
                )
            )

    # Exact entry
    if recommended is True and entry_type == "EXACT_PRICE":
        if entry_price is None or entry_price <= Decimal("0"):
            issues.append(
                _make_issue(
                    EXACT_ENTRY_STRUCTURE_INVALID,
                    "/entry_plan/entry_price",
                    "Exact entry must have a positive entry price",
                    expected="> 0",
                    actual=str(entry_price) if entry_price is not None else "null",
                )
            )

        # Max acceptable entry
        if max_acceptable is not None and entry_price is not None:
            if max_acceptable <= Decimal("0"):
                issues.append(
                    _make_issue(
                        MAXIMUM_ACCEPTABLE_ENTRY_INVALID,
                        "/entry_plan/maximum_acceptable_entry",
                        f"Maximum acceptable entry must be positive, got {max_acceptable}",
                        expected="> 0",
                        actual=str(max_acceptable),
                    )
                )
            elif entry_price > max_acceptable:
                issues.append(
                    _make_issue(
                        ENTRY_ABOVE_MAXIMUM_ACCEPTABLE,
                        "/entry_plan/entry_price",
                        (
                            "Entry price ({entry_price}) exceeds "
                            "maximum acceptable entry ({max_acceptable})"
                        ),
                        expected=f"<= {max_acceptable}",
                        actual=str(entry_price),
                    )
                )

    # Entry zone
    if recommended is True and entry_type == "PRICE_ZONE":
        if (
            zone_low is None
            or zone_high is None
            or zone_low <= Decimal("0")
            or zone_high <= Decimal("0")
        ):
            issues.append(
                _make_issue(
                    ENTRY_ZONE_STRUCTURE_INVALID,
                    "/entry_plan",
                    "Entry zone must have positive low and high bounds",
                    expected="low > 0, high > 0",
                    actual=f"low={zone_low}, high={zone_high}",
                )
            )
        elif zone_low > zone_high:
            issues.append(
                _make_issue(
                    ENTRY_ZONE_LOW_ABOVE_HIGH,
                    "/entry_plan/entry_zone_low",
                    f"Entry zone low ({zone_low}) exceeds high ({zone_high})",
                    expected=f"<= {zone_high}",
                    actual=str(zone_low),
                )
            )

        # If exact entry price is present alongside a zone, it should be inside
        if entry_price is not None and zone_low is not None and zone_high is not None:
            if entry_price < zone_low or entry_price > zone_high:
                issues.append(
                    _make_issue(
                        EXACT_ENTRY_STRUCTURE_INVALID,
                        "/entry_plan/entry_price",
                        f"Entry price ({entry_price}) is outside zone [{zone_low}, {zone_high}]",
                        expected=f"between {zone_low} and {zone_high}",
                        actual=str(entry_price),
                    )
                )

        # Max acceptable entry vs zone
        if max_acceptable is not None and zone_high is not None:
            if max_acceptable <= Decimal("0"):
                issues.append(
                    _make_issue(
                        MAXIMUM_ACCEPTABLE_ENTRY_INVALID,
                        "/entry_plan/maximum_acceptable_entry",
                        f"Maximum acceptable entry must be positive, got {max_acceptable}",
                        expected="> 0",
                        actual=str(max_acceptable),
                    )
                )
            elif zone_high > max_acceptable:
                issues.append(
                    _make_issue(
                        ENTRY_ABOVE_MAXIMUM_ACCEPTABLE,
                        "/entry_plan/entry_zone_high",
                        (
                            "Zone high ({zone_high}) exceeds "
                            "maximum acceptable entry ({max_acceptable})"
                        ),
                        expected=f"<= {max_acceptable}",
                        actual=str(zone_high),
                    )
                )

    return tuple(sorted(issues, key=_sort_key))
