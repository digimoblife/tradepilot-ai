"""Closing Validator (TP-0310).

Validates a final-exit transition and resulting closed trade result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Mapping, Sequence

from app.calculations.decimal_utils import to_decimal
from app.calculations.errors import InvalidDecimalError
from app.calculations.exits import (
    ExitFill,
    calculate_weighted_average_exit,
)
from app.validation.issues import ValidationCategory, ValidationIssue, ValidationSeverity
from app.validation.timeline import validate_timeline

DOMAIN = ValidationCategory("DOMAIN")

CLOSING_FINAL_EXIT_QUANTITY_MISMATCH = "CLOSING_FINAL_EXIT_QUANTITY_MISMATCH"
CLOSING_REMAINING_NOT_ZERO = "CLOSING_REMAINING_NOT_ZERO"
CLOSING_TOTAL_EXIT_QUANTITY_MISMATCH = "CLOSING_TOTAL_EXIT_QUANTITY_MISMATCH"
CLOSING_WEIGHTED_EXIT_MISMATCH = "CLOSING_WEIGHTED_EXIT_MISMATCH"
CLOSING_GROSS_RESULT_MISMATCH = "CLOSING_GROSS_RESULT_MISMATCH"
CLOSING_NET_RESULT_MISMATCH = "CLOSING_NET_RESULT_MISMATCH"
CLOSING_REASON_STATUS_MISMATCH = "CLOSING_REASON_STATUS_MISMATCH"
CLOSING_NUMERIC_INPUT_INVALID = "CLOSING_NUMERIC_INPUT_INVALID"


@dataclass(frozen=True, slots=True)
class ClosingValidationResult:
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


# Canonical closing-reason → session-status mapping
CLOSING_REASON_MAP: dict[str, str] = {
    "TAKE_PROFIT": "CLOSED_TAKE_PROFIT",
    "STOP_LOSS": "CLOSED_STOP_LOSS",
    "MANUAL_EXIT": "CLOSED_MANUAL",
    "THESIS_INVALIDATED": "CLOSED_MANUAL",
    "RISK_REDUCTION": "CLOSED_MANUAL",
}


def validate_closing(
    previous_state: Mapping[str, object],
    final_exit: Mapping[str, object],
    resulting_state: Mapping[str, object],
    *,
    previous_exits: Sequence[Mapping[str, object]] | None = None,
    timeline_events: Sequence[Mapping[str, object]] | None = None,
    closing_reason: str | None = None,
    resulting_session_status: str | None = None,
) -> ClosingValidationResult:
    """Validate a final-exit transition and closed trade result.

    Parameters
    ----------
    previous_state:
        Position before final exit.  Contains ``entry_price``,
        ``original_quantity``, ``remaining_quantity``, ``position_status``,
        optional ``realized_pnl`` and ``average_exit_price``.
    final_exit:
        The final exit action.  Contains ``final_exit_price`` and
        ``final_exit_quantity``.
    resulting_state:
        The closed position result (``trade_result`` section).  Contains
        ``entry_price``, ``original_quantity``, ``average_exit_price``,
        ``gross_profit_loss``, ``fees``, ``taxes``, ``net_profit_loss``.
    previous_exits:
        Optional earlier partial-exit dicts, each with ``exit_quantity``
        and ``exit_price``.
    timeline_events:
        Optional timeline event dicts, each with ``timestamp`` and
        ``event_type``.
    closing_reason:
        The closing reason string (e.g. ``"TAKE_PROFIT"``).
    resulting_session_status:
        The terminal session status (e.g. ``"CLOSED_TAKE_PROFIT"``).
    """
    issues: list[ValidationIssue] = []

    # Extract values
    fields_to_check: list[tuple[str, str, Mapping[str, object]]] = [
        ("entry_price", "entry_price", previous_state),
        ("orig_qty", "original_quantity", previous_state),
        ("prev_rem_qty", "remaining_quantity", previous_state),
        ("exit_qty", "final_exit_quantity", final_exit),
        ("exit_price", "final_exit_price", final_exit),
        ("result_entry", "entry_price", resulting_state),
        ("result_orig_qty", "original_quantity", resulting_state),
        ("result_avg_exit", "average_exit_price", resulting_state),
        ("result_gross", "gross_profit_loss", resulting_state),
        ("result_fees", "fees", resulting_state),
        ("result_taxes", "taxes", resulting_state),
        ("result_net", "net_profit_loss", resulting_state),
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
                        CLOSING_NUMERIC_INPUT_INVALID,
                        f"/{field_name}",
                        f"Invalid numeric input for {field_name}: "
                        f"type={type(raw).__name__}, value={raw!r}",
                        expected="Decimal, int, or str",
                        actual=f"{type(raw).__name__}: {raw!r}",
                    )
                )
        else:
            vals[key] = None

    if issues:
        return ClosingValidationResult(valid=False, issues=tuple(issues))

    entry_price = vals.get("entry_price")
    orig_qty = vals.get("orig_qty")
    prev_rem_qty = vals.get("prev_rem_qty")
    exit_qty = vals.get("exit_qty")
    exit_price = vals.get("exit_price")

    # 1. Final exit quantity must match previous remaining
    if exit_qty is not None and prev_rem_qty is not None and exit_qty != prev_rem_qty:
        issues.append(
            _make_issue(
                CLOSING_FINAL_EXIT_QUANTITY_MISMATCH,
                "/final_exit_quantity",
                f"Final exit quantity ({exit_qty}) != previous remaining ({prev_rem_qty})",
                expected=str(prev_rem_qty),
                actual=str(exit_qty),
            )
        )

    # 2. Zero exit quantity rejected
    if exit_qty is not None and exit_qty <= Decimal("0"):
        issues.append(
            _make_issue(
                CLOSING_FINAL_EXIT_QUANTITY_MISMATCH,
                "/final_exit_quantity",
                f"Final exit quantity ({exit_qty}) must be positive",
                expected="> 0",
                actual=str(exit_qty),
            )
        )

    # 3. Resulting remaining must be zero
    result_rem = resulting_state.get("remaining_quantity")
    if result_rem is not None:
        try:
            result_rem_d = _d(result_rem)
            if result_rem_d is not None and result_rem_d != Decimal("0"):
                issues.append(
                    _make_issue(
                        CLOSING_REMAINING_NOT_ZERO,
                        "/remaining_quantity",
                        f"Resulting remaining ({result_rem_d}) must be 0 for a closed position",
                        expected="0",
                        actual=str(result_rem_d),
                    )
                )
        except InvalidDecimalError:
            pass

    # 4. Total exit quantity must equal original
    total_exit_qty = Decimal("0")
    if previous_exits:
        for pe in previous_exits:
            pe_qty_raw = pe.get("exit_quantity")
            if pe_qty_raw is not None:
                try:
                    pe_qty = _d(pe_qty_raw)
                    if pe_qty is not None:
                        total_exit_qty += pe_qty
                except InvalidDecimalError:
                    pass
    if exit_qty is not None:
        total_exit_qty += exit_qty

    result_orig_qty = vals.get("result_orig_qty")
    if result_orig_qty is not None and result_orig_qty > Decimal("0"):
        if total_exit_qty != result_orig_qty:
            issues.append(
                _make_issue(
                    CLOSING_TOTAL_EXIT_QUANTITY_MISMATCH,
                    "/original_quantity",
                    (
                        "Total exit quantity ({total_exit_qty}) "
                        "!= original quantity ({result_orig_qty})"
                    ),
                    expected=str(result_orig_qty),
                    actual=str(total_exit_qty),
                )
            )

    # 5. Weighted average exit
    if entry_price is not None and exit_qty is not None and exit_price is not None:
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
            diff = abs(authoritative_avg - result_avg_exit)
            if diff > Decimal("0.000001"):
                issues.append(
                    _make_issue(
                        CLOSING_WEIGHTED_EXIT_MISMATCH,
                        "/average_exit_price",
                        f"Resulting average exit ({result_avg_exit}) "
                        f"!= authoritative ({authoritative_avg})",
                        expected=str(authoritative_avg),
                        actual=str(result_avg_exit),
                    )
                )

        # 6. Gross result
        result_gross = vals.get("result_gross")
        if result_gross is not None and orig_qty is not None and authoritative_avg is not None:
            authoritative_gross = (authoritative_avg - entry_price) * orig_qty
            if abs(authoritative_gross - result_gross) > Decimal("0.000001"):
                issues.append(
                    _make_issue(
                        CLOSING_GROSS_RESULT_MISMATCH,
                        "/gross_profit_loss",
                        f"Resulting gross P/L ({result_gross}) "
                        f"!= authoritative ({authoritative_gross})",
                        expected=str(authoritative_gross),
                        actual=str(result_gross),
                    )
                )

        # 7. Net result
        result_net = vals.get("result_net")
        result_fees = vals.get("result_fees")
        if result_net is not None and result_gross is not None:
            net_fees = result_fees if result_fees is not None else Decimal("0")
            result_taxes_d = vals.get("result_taxes")
            net_taxes = result_taxes_d if result_taxes_d is not None else Decimal("0")
            authoritative_net = result_gross - net_fees - net_taxes
            if abs(authoritative_net - result_net) > Decimal("0.000001"):
                issues.append(
                    _make_issue(
                        CLOSING_NET_RESULT_MISMATCH,
                        "/net_profit_loss",
                        f"Resulting net P/L ({result_net}) != authoritative ({authoritative_net})",
                        expected=str(authoritative_net),
                        actual=str(result_net),
                    )
                )

    # 8. Timeline
    entry_ts = previous_state.get("entry_timestamp")
    exit_ts = final_exit.get("exit_timestamp")
    closed_ts = resulting_state.get("closed_at")
    if isinstance(entry_ts, str) or isinstance(exit_ts, str):
        partial_exit_timestamps: list[str] = []
        if previous_exits:
            for pe in previous_exits:
                pe_ts = pe.get("exit_timestamp")
                if isinstance(pe_ts, str):
                    partial_exit_timestamps.append(pe_ts)
        tl_issues = validate_timeline(
            entry_timestamp=str(entry_ts) if isinstance(entry_ts, str) else None,
            final_exit_timestamp=str(exit_ts) if isinstance(exit_ts, str) else None,
            timeline_events=timeline_events,
            partial_exit_timestamps=partial_exit_timestamps or None,
            closed_at_timestamp=str(closed_ts) if isinstance(closed_ts, str) else None,
        )
        issues.extend(tl_issues)

    # 9. Closing reason → session status
    if closing_reason is not None and resulting_session_status is not None:
        expected_status = CLOSING_REASON_MAP.get(closing_reason)
        if expected_status is not None and resulting_session_status != expected_status:
            issues.append(
                _make_issue(
                    CLOSING_REASON_STATUS_MISMATCH,
                    "/closing_reason",
                    f"Closing reason ({closing_reason}) maps to "
                    f"{expected_status}, not {resulting_session_status}",
                    expected=expected_status,
                    actual=resulting_session_status,
                )
            )

    issues.sort(key=_sort_key)
    return ClosingValidationResult(
        valid=len(issues) == 0,
        issues=tuple(issues),
    )
