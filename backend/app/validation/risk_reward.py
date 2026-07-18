"""Risk and reward domain validation: risk max 5%, reward and risk-reward consistency."""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from app.calculations.decimal_utils import to_decimal
from app.calculations.errors import InvalidDecimalError
from app.calculations.position import (
    calculate_reward_percentage,
    calculate_risk_percentage,
    calculate_risk_reward_ratio,
)
from app.validation.issues import ValidationCategory, ValidationIssue, ValidationSeverity

DOMAIN = ValidationCategory("DOMAIN")

NUMERIC_INPUT_INVALID = "NUMERIC_INPUT_INVALID"
RISK_EXCEEDS_MAXIMUM = "RISK_EXCEEDS_MAXIMUM"
RISK_PERCENTAGE_MISMATCH = "RISK_PERCENTAGE_MISMATCH"
REWARD_PERCENTAGE_MISMATCH = "REWARD_PERCENTAGE_MISMATCH"
RISK_REWARD_MISMATCH = "RISK_REWARD_MISMATCH"


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


MAXIMUM_RISK_PERCENTAGE = Decimal("5")


def validate_risk_reward(payload: Mapping[str, object]) -> tuple[ValidationIssue, ...]:
    """Validate risk percentage, reward percentage, and risk-reward ratio.

    Requires ``entry_plan``, ``stop_loss_plan``, and ``target_plan`` dicts
    within the payload.
    """
    issues: list[ValidationIssue] = []

    _entry_plan = payload.get("entry_plan")
    _stop_plan = payload.get("stop_loss_plan")
    _target_plan = payload.get("target_plan")
    if not isinstance(_entry_plan, dict):
        return ()
    if not isinstance(_stop_plan, dict):
        return ()
    if not isinstance(_target_plan, dict):
        return ()
    entry_plan: dict[str, object] = _entry_plan
    stop_plan: dict[str, object] = _stop_plan
    target_plan: dict[str, object] = _target_plan

    # Numeric inputs
    numeric_fields = (
        ("entry_price", "/entry_plan/entry_price"),
        ("entry_zone_low", "/entry_plan/entry_zone_low"),
        ("stop_loss_price", "/stop_loss_plan/stop_loss_price"),
        ("target_price", "/target_plan/target_price"),
    )
    for field, path in numeric_fields:
        if field.startswith("entry"):
            parent = entry_plan
        elif field.startswith("stop"):
            parent = stop_plan
        else:
            parent = target_plan
        raw = parent.get(field)
        if raw is not None:
            try:
                _d(raw)
            except InvalidDecimalError:
                issues.append(
                    _make_issue(
                        NUMERIC_INPUT_INVALID,
                        path,
                        f"Invalid numeric input for {field}: "
                        f"type={type(raw).__name__}, value={raw!r}",
                        expected="Decimal, int, or str",
                        actual=f"{type(raw).__name__}: {raw!r}",
                    )
                )
    if issues:
        return tuple(sorted(issues, key=_sort_key))

    entry_type = entry_plan.get("entry_type")
    entry_price = _d(entry_plan.get("entry_price"))
    zone_low = _d(entry_plan.get("entry_zone_low"))
    zone_high = _d(entry_plan.get("entry_zone_high"))
    stop_price = _d(stop_plan.get("stop_loss_price"))
    target_price = _d(target_plan.get("target_price"))
    recommended_entry = entry_plan.get("entry_recommended")
    stop_recommended = stop_plan.get("stop_loss_recommended")
    target_recommended = target_plan.get("target_recommended")

    # Determine entry reference for risk/reward
    if entry_type == "EXACT_PRICE":
        risk_ref = entry_price
        reward_ref = entry_price
    elif entry_type == "PRICE_ZONE":
        risk_ref = zone_low  # risk uses worst case: lowest entry
        reward_ref = zone_high  # reward uses worst case: highest entry
    else:
        risk_ref = reward_ref = None

    # Risk percentage
    if (
        recommended_entry is True
        and stop_recommended is True
        and risk_ref is not None
        and stop_price is not None
    ):
        authoritative_risk = calculate_risk_percentage(risk_ref, stop_price)
        if authoritative_risk is not None:
            if authoritative_risk > MAXIMUM_RISK_PERCENTAGE:
                issues.append(
                    _make_issue(
                        RISK_EXCEEDS_MAXIMUM,
                        "/entry_plan",
                        (
                            "Risk ({authoritative_risk}%) exceeds maximum "
                            "({MAXIMUM_RISK_PERCENTAGE}%)"
                        ),
                        expected=f"<= {MAXIMUM_RISK_PERCENTAGE}%",
                        actual=f"{authoritative_risk}%",
                    )
                )

            # Check reported risk percentage if present
            ai_assessment = payload.get("ai_assessment")
            if isinstance(ai_assessment, dict):
                # The initial_risk_percentage may be stored in various places
                pass

            # Check initial_risk from stop_loss_plan
            reported_risk_pct = _d(stop_plan.get("initial_risk_percentage"))
            if reported_risk_pct is not None:
                diff = abs(authoritative_risk - reported_risk_pct)
                if diff > Decimal("0.01"):
                    issues.append(
                        _make_issue(
                            RISK_PERCENTAGE_MISMATCH,
                            "/stop_loss_plan/initial_risk_percentage",
                            (
                                "Reported risk ({reported_risk_pct}%) differs "
                                "from calculated ({authoritative_risk}%)"
                            ),
                            expected=str(authoritative_risk),
                            actual=str(reported_risk_pct),
                        )
                    )

        else:
            # Risk is undefined (zero entry)
            reported_risk_pct = _d(stop_plan.get("initial_risk_percentage"))
            if reported_risk_pct is not None:
                issues.append(
                    _make_issue(
                        RISK_PERCENTAGE_MISMATCH,
                        "/stop_loss_plan/initial_risk_percentage",
                        "Risk is undefined (zero entry)",
                        expected="null",
                        actual=str(reported_risk_pct),
                    )
                )

    # Reward percentage
    if (
        recommended_entry is True
        and target_recommended is True
        and reward_ref is not None
        and target_price is not None
    ):
        authoritative_reward = calculate_reward_percentage(target_price, reward_ref)
        if authoritative_reward is not None:
            # Check reported reward percentage if stored in target_plan
            # (Not all schemas store reported_reward; this is a consistency check when present)
            pass

            # Check if target_plan has a reward_percentage field
            reported_reward_pct = _d(target_plan.get("reward_percentage"))
            if reported_reward_pct is not None:
                diff = abs(authoritative_reward - reported_reward_pct)
                if diff > Decimal("0.01"):
                    issues.append(
                        _make_issue(
                            REWARD_PERCENTAGE_MISMATCH,
                            "/target_plan/reward_percentage",
                            (
                                "Reported reward ({reported_reward_pct}%) differs "
                                "from calculated ({authoritative_reward}%)"
                            ),
                            expected=str(authoritative_reward),
                            actual=str(reported_reward_pct),
                        )
                    )

    # Risk-reward ratio
    if (
        recommended_entry is True
        and stop_recommended is True
        and target_recommended is True
        and risk_ref is not None
        and stop_price is not None
        and reward_ref is not None
        and target_price is not None
    ):
        authoritative_rr = calculate_risk_reward_ratio(risk_ref, stop_price, target_price)
        if authoritative_rr is not None:
            reported_rr = _d(target_plan.get("risk_reward_ratio"))
            if reported_rr is not None:
                diff = abs(authoritative_rr - reported_rr)
                if diff > Decimal("0.01"):
                    issues.append(
                        _make_issue(
                            RISK_REWARD_MISMATCH,
                            "/target_plan/risk_reward_ratio",
                            (
                                "Reported risk-reward ({reported_rr}) differs "
                                "from calculated ({authoritative_rr})"
                            ),
                            expected=str(authoritative_rr),
                            actual=str(reported_rr),
                        )
                    )

    return tuple(sorted(issues, key=_sort_key))
