"""Partial Exit Validator (TP-0309).

Validates a partial-exit transition: previous position state + exit action
-> resulting position state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Mapping, Sequence

from app.calculations.decimal_utils import to_decimal
from app.calculations.errors import InvalidDecimalError
from app.calculations.exits import (
    ExitFill,
    calculate_partial_realized_pnl,
    calculate_weighted_average_exit,
)
from app.validation.issues import ValidationCategory, ValidationIssue, ValidationSeverity

DOMAIN = ValidationCategory("DOMAIN")

PARTIAL_EXIT_QUANTITY_INVALID = "PARTIAL_EXIT_QUANTITY_INVALID"
PARTIAL_EXIT_CLOSES_FULL_POSITION = "PARTIAL_EXIT_CLOSES_FULL_POSITION"
PARTIAL_EXIT_QUANTITY_MISMATCH = "PARTIAL_EXIT_QUANTITY_MISMATCH"
PARTIAL_EXIT_PREVIOUS_STATE_INVALID = "PARTIAL_EXIT_PREVIOUS_STATE_INVALID"
PARTIAL_EXIT_RESULTING_STATUS_INVALID = "PARTIAL_EXIT_RESULTING_STATUS_INVALID"
PARTIAL_EXIT_REALIZED_PROFIT_LOSS_MISMATCH = "PARTIAL_EXIT_REALIZED_PROFIT_LOSS_MISMATCH"
PARTIAL_EXIT_AVERAGE_EXIT_MISMATCH = "PARTIAL_EXIT_AVERAGE_EXIT_MISMATCH"
PARTIAL_EXIT_NUMERIC_INPUT_INVALID = "PARTIAL_EXIT_NUMERIC_INPUT_INVALID"


@dataclass(frozen=True, slots=True)
class PartialExitValidationResult:
    valid: bool
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)


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


def _sort_key(issue: ValidationIssue) -> tuple[str, str, str, str]:
    return (issue.path, issue.code, issue.category.value, issue.message)


def _d(value: object) -> Decimal | None:
    if value is None:
        return None
    return to_decimal(value)  # type: ignore[arg-type]


def validate_partial_exit(
    previous_state: Mapping[str, object],
    partial_exit: Mapping[str, object],
    resulting_state: Mapping[str, object],
    *,
    previous_exits: Sequence[Mapping[str, object]] | None = None,
) -> PartialExitValidationResult:
    """Validate a partial-exit transition.

    Parameters
    ----------
    previous_state:
        The position state before the exit.  Contains ``remaining_quantity``,
        ``entry_price``, ``position_status``, and optional ``realized_pnl``
        and ``average_exit_price``.
    partial_exit:
        The current exit action.  Contains ``exit_quantity`` and ``exit_price``.
    resulting_state:
        The position state after the exit.  Contains ``remaining_quantity``,
        ``realized_pnl``, ``average_exit_price``, and ``position_status``.
    previous_exits:
        Optional list of earlier partial-exit dicts, each containing
        ``exit_quantity`` and ``exit_price``.  Used for weighted-average
        and cumulative realized P/L validation on repeated exits.
    """
    issues: list[ValidationIssue] = []

    # Extract values through authoritative Decimal conversion
    fields_to_check: list[tuple[str, str, Mapping[str, object]]] = [
        ("entry_price", "entry_price", previous_state),
        ("prev_rem_qty", "remaining_quantity", previous_state),
        ("exit_qty", "exit_quantity", partial_exit),
        ("exit_price", "exit_price", partial_exit),
        ("result_rem_qty", "remaining_quantity", resulting_state),
        ("result_realized", "realized_pnl", resulting_state),
        ("result_avg_exit", "average_exit_price", resulting_state),
    ]

    vals: dict[str, Decimal | None] = {}
    for key, field_name, source in fields_to_check:
        raw = source.get(field_name)
        if raw is not None:
            try:
                vals[key] = _d(raw)
            except InvalidDecimalError:
                issues.append(
                    _make_issue(
                        PARTIAL_EXIT_NUMERIC_INPUT_INVALID,
                        f"/{field_name}",
                        f"Invalid numeric input for {field_name}: "
                        f"type={type(raw).__name__}, value={raw!r}",
                        expected="Decimal, int, or str",
                        actual=f"{type(raw).__name__}: {raw!r}",
                    )
                )
                vals[key] = None
        else:
            vals[key] = None

    if issues:
        return PartialExitValidationResult(valid=False, issues=tuple(issues))

    entry_price = vals.get("entry_price")
    prev_rem_qty = vals.get("prev_rem_qty")
    exit_qty = vals.get("exit_qty")
    exit_price = vals.get("exit_price")
    result_rem_qty = vals.get("result_rem_qty")

    # 1. Previous state validation
    prev_status = previous_state.get("position_status")
    if prev_status is not None:
        if prev_status not in ("OPEN", "PARTIALLY_CLOSED"):
            issues.append(
                _make_issue(
                    PARTIAL_EXIT_PREVIOUS_STATE_INVALID,
                    "/previous_state/position_status",
                    f"Partial exit from {prev_status} state is not allowed",
                    expected="OPEN or PARTIALLY_CLOSED",
                    actual=str(prev_status),
                )
            )
            # Cannot continue if previous state is invalid
            return PartialExitValidationResult(
                valid=False, issues=tuple(sorted(issues, key=_sort_key))
            )

    # 2. Exit quantity > 0
    if exit_qty is not None and exit_qty <= Decimal("0"):
        issues.append(
            _make_issue(
                PARTIAL_EXIT_QUANTITY_INVALID,
                "/exit_quantity",
                f"Exit quantity ({exit_qty}) must be positive",
                expected="> 0",
                actual=str(exit_qty),
            )
        )

    # 3. Remaining > 0
    if result_rem_qty is not None and result_rem_qty <= Decimal("0"):
        issues.append(
            _make_issue(
                PARTIAL_EXIT_CLOSES_FULL_POSITION,
                "/resulting_state/remaining_quantity",
                (
                    "Resulting remaining quantity ({result_rem_qty}) "
                    "must be positive for a partial exit"
                ),
                expected="> 0",
                actual=str(result_rem_qty),
            )
        )

    # 4. Exit < previous remaining
    if exit_qty is not None and prev_rem_qty is not None and exit_qty >= prev_rem_qty:
        issues.append(
            _make_issue(
                PARTIAL_EXIT_CLOSES_FULL_POSITION,
                "/exit_quantity",
                (
                    "Exit quantity ({exit_qty}) must be less than "
                    "previous remaining ({prev_rem_qty})"
                ),
                expected=f"< {prev_rem_qty}",
                actual=str(exit_qty),
            )
        )

    # 5. Quantity conservation
    if exit_qty is not None and result_rem_qty is not None and prev_rem_qty is not None:
        expected_rem = prev_rem_qty - exit_qty
        if result_rem_qty != expected_rem:
            issues.append(
                _make_issue(
                    PARTIAL_EXIT_QUANTITY_MISMATCH,
                    "/resulting_state/remaining_quantity",
                    (
                        "Resulting remaining ({result_rem_qty}) != previous "
                        "remaining ({prev_rem_qty}) - exit ({exit_qty}) = {expected_rem}"
                    ),
                    expected=str(expected_rem),
                    actual=str(result_rem_qty),
                )
            )

    # 6. Resulting status
    result_status = resulting_state.get("position_status")
    if result_status is not None and result_status != "PARTIALLY_CLOSED":
        issues.append(
            _make_issue(
                PARTIAL_EXIT_RESULTING_STATUS_INVALID,
                "/resulting_state/position_status",
                f"Resulting status ({result_status}) must be PARTIALLY_CLOSED",
                expected="PARTIALLY_CLOSED",
                actual=str(result_status),
            )
        )

    # 7. Realized P/L
    if entry_price is not None and exit_qty is not None and exit_price is not None:
        authoritative_partial_pnl = calculate_partial_realized_pnl(
            exit_price, entry_price, exit_qty
        )

        # Previous realized P/L (null treated as 0 for cumulative)
        prev_realized = _d(previous_state.get("realized_pnl"))
        if prev_realized is None:
            prev_realized = Decimal("0")

        expected_cumulative = prev_realized + authoritative_partial_pnl
        result_realized = vals.get("result_realized")

        if result_realized is not None and expected_cumulative != result_realized:
            issues.append(
                _make_issue(
                    PARTIAL_EXIT_REALIZED_PROFIT_LOSS_MISMATCH,
                    "/resulting_state/realized_pnl",
                    f"Resulting realized P/L ({result_realized}) != "
                    f"expected ({expected_cumulative}) = previous ({prev_realized}) "
                    f"+ partial ({authoritative_partial_pnl})",
                    expected=str(expected_cumulative),
                    actual=str(result_realized),
                )
            )

    # 8. Weighted average exit
    if exit_qty is not None and exit_price is not None and entry_price is not None:
        # Build the fill list: previous exits + current exit
        fills: list[ExitFill] = []
        if previous_exits:
            for pe in previous_exits:
                pe_qty = _d(pe.get("exit_quantity"))
                pe_price = _d(pe.get("exit_price"))
                if pe_qty is not None and pe_price is not None:
                    fills.append(ExitFill(price=pe_price, quantity=pe_qty))
        fills.append(ExitFill(price=exit_price, quantity=exit_qty))

        authoritative_avg = calculate_weighted_average_exit(tuple(fills))
        result_avg_exit = vals.get("result_avg_exit")

        if authoritative_avg is not None and result_avg_exit is not None:
            # Compare at DB price precision
            diff = abs(authoritative_avg - result_avg_exit)
            if diff > Decimal("0.000001"):
                issues.append(
                    _make_issue(
                        PARTIAL_EXIT_AVERAGE_EXIT_MISMATCH,
                        "/resulting_state/average_exit_price",
                        (
                            "Resulting average exit ({result_avg_exit}) != "
                            "authoritative ({authoritative_avg})"
                        ),
                        expected=str(authoritative_avg),
                        actual=str(result_avg_exit),
                    )
                )

    issues.sort(key=_sort_key)
    return PartialExitValidationResult(
        valid=len(issues) == 0,
        issues=tuple(issues),
    )
