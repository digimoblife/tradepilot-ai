"""Canonical State Consistency Validator (TP-0308).

Compares an AI analysis payload with the authoritative canonical Trade State.
Active values must match exactly.  Proposed/recommended values may differ.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Mapping

from app.calculations.decimal_utils import to_decimal
from app.calculations.errors import InvalidDecimalError
from app.validation.issues import ValidationCategory, ValidationIssue, ValidationSeverity

DOMAIN = ValidationCategory("DOMAIN")

# ---------------------------------------------------------------------------
# Stable error codes
# ---------------------------------------------------------------------------

STATE_SESSION_ID_MISMATCH = "STATE_SESSION_ID_MISMATCH"
STATE_TICKER_MISMATCH = "STATE_TICKER_MISMATCH"
STATE_ENTRY_PRICE_MISMATCH = "STATE_ENTRY_PRICE_MISMATCH"
STATE_ORIGINAL_QUANTITY_MISMATCH = "STATE_ORIGINAL_QUANTITY_MISMATCH"
STATE_REMAINING_QUANTITY_MISMATCH = "STATE_REMAINING_QUANTITY_MISMATCH"
STATE_ACTIVE_STOP_MISMATCH = "STATE_ACTIVE_STOP_MISMATCH"
STATE_ACTIVE_TARGET_MISMATCH = "STATE_ACTIVE_TARGET_MISMATCH"
STATE_POSITION_STATUS_MISMATCH = "STATE_POSITION_STATUS_MISMATCH"
STATE_NUMERIC_INPUT_INVALID = "STATE_NUMERIC_INPUT_INVALID"

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StateConsistencyValidationResult:
    valid: bool
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _cmp_str(
    ai_val: object, canonical_val: object, path: str, code: str, label: str
) -> ValidationIssue | None:
    """Compare two optional string values."""
    if ai_val is None or canonical_val is None:
        return None
    s_ai = str(ai_val)
    s_canon = str(canonical_val)
    if s_ai != s_canon:
        return _make_issue(
            code,
            path,
            f"AI {label} ({s_ai}) != canonical {label} ({s_canon})",
            expected=s_canon,
            actual=s_ai,
        )
    return None


def _cmp_decimal(
    ai_val: object, canonical_val: object, path: str, code: str, label: str
) -> ValidationIssue | None:
    """Compare two optional Decimal values using authoritative conversion."""
    if ai_val is None and canonical_val is None:
        return None
    if ai_val is not None:
        try:
            d_ai = _d(ai_val)
        except InvalidDecimalError:
            return _make_issue(
                STATE_NUMERIC_INPUT_INVALID,
                path,
                f"Invalid numeric AI {label}: type={type(ai_val).__name__}, value={ai_val!r}",
                expected="Decimal, int, or str",
                actual=f"{type(ai_val).__name__}: {ai_val!r}",
            )
    else:
        d_ai = None

    if canonical_val is not None:
        try:
            d_canon = _d(canonical_val)
        except InvalidDecimalError:
            return _make_issue(
                STATE_NUMERIC_INPUT_INVALID,
                path,
                f"Invalid numeric canonical {label}: {canonical_val!r}",
                expected="valid Decimal",
                actual=str(canonical_val),
            )
    else:
        d_canon = None

    # Both non-null: must match
    if d_ai is not None and d_canon is not None and d_ai != d_canon:
        return _make_issue(
            code,
            path,
            f"AI {label} ({d_ai}) != canonical {label} ({d_canon})",
            expected=str(d_canon),
            actual=str(d_ai),
        )

    # AI says non-null but canonical says null: AI invented an active value
    if d_ai is not None and d_canon is None:
        return _make_issue(
            code,
            path,
            f"AI {label} ({d_ai}) is non-null but canonical {label} is null",
            expected="null",
            actual=str(d_ai),
        )

    return None


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------


def validate_state_consistency(
    payload: Mapping[str, object],
    canonical_state: Mapping[str, object],
) -> StateConsistencyValidationResult:
    """Compare an AI analysis payload against canonical Trade State.

    Parameters
    ----------
    payload:
        The AI analysis payload (already schema-validated).  Contains
        ``metadata.session_id``, ``metadata.ticker``,
        ``position_assessment.entry_price``,
        ``position_assessment.remaining_quantity``,
        ``position_assessment.active_stop_loss``,
        ``position_assessment.active_target``, etc.
    canonical_state:
        The authoritative canonical Trade State payload (already
        schema-validated, e.g. from ``backend/app/validation/trade_state.py``).
        Contains ``session_id``, ``ticker``, ``position.entry_price``,
        ``position.original_quantity``, ``position.remaining_quantity``,
        ``position.active_stop_loss``, ``position.active_target``,
        ``position.position_status``.

    Returns
    -------
    StateConsistencyValidationResult
    """
    issues: list[ValidationIssue] = []

    # Extract AI metadata
    metadata = payload.get("metadata")
    ai_session_id = None
    ai_ticker = None
    if isinstance(metadata, dict):
        ai_session_id = metadata.get("session_id")
        ai_ticker = metadata.get("ticker")

    # Extract canonical state fields
    position = canonical_state.get("position")
    canon_position = position if isinstance(position, dict) else {}

    # 1. Session ID
    canon_session_id = canonical_state.get("session_id")
    issue = _cmp_str(
        ai_session_id,
        canon_session_id,
        "/metadata/session_id",
        STATE_SESSION_ID_MISMATCH,
        "session ID",
    )
    if issue:
        issues.append(issue)

    # 2. Ticker
    canon_ticker = canonical_state.get("ticker")
    issue = _cmp_str(ai_ticker, canon_ticker, "/metadata/ticker", STATE_TICKER_MISMATCH, "ticker")
    if issue:
        issues.append(issue)

    # 3. Position status
    ai_pos_status = payload.get("position_status")
    canon_pos_status = canon_position.get("position_status")
    if ai_pos_status is not None and canon_pos_status is not None:
        issue = _cmp_str(
            ai_pos_status,
            canon_pos_status,
            "/position_status",
            STATE_POSITION_STATUS_MISMATCH,
            "position status",
        )
        if issue:
            issues.append(issue)

    # Extract AI position assessment
    ai_pos = payload.get("position_assessment")
    ai_position = ai_pos if isinstance(ai_pos, dict) else {}

    # 4. Entry price
    issue = _cmp_decimal(
        ai_position.get("entry_price"),
        canon_position.get("entry_price"),
        "/position_assessment/entry_price",
        STATE_ENTRY_PRICE_MISMATCH,
        "entry price",
    )
    if issue:
        issues.append(issue)

    # 5. Original quantity (may be in different locations)
    canon_orig_qty = canon_position.get("original_quantity")
    # Check in AI payload metadata or other sections
    ai_orig_qty = payload.get("original_quantity")
    if ai_orig_qty is None:
        ai_orig_qty = metadata.get("original_quantity") if isinstance(metadata, dict) else None
    issue = _cmp_decimal(
        ai_orig_qty,
        canon_orig_qty,
        "/original_quantity",
        STATE_ORIGINAL_QUANTITY_MISMATCH,
        "original quantity",
    )
    if issue:
        issues.append(issue)

    # 6. Remaining quantity
    issue = _cmp_decimal(
        ai_position.get("remaining_quantity"),
        canon_position.get("remaining_quantity"),
        "/position_assessment/remaining_quantity",
        STATE_REMAINING_QUANTITY_MISMATCH,
        "remaining quantity",
    )
    if issue:
        issues.append(issue)

    # 7. Active stop loss
    issue = _cmp_decimal(
        ai_position.get("active_stop_loss"),
        canon_position.get("active_stop_loss"),
        "/position_assessment/active_stop_loss",
        STATE_ACTIVE_STOP_MISMATCH,
        "active stop",
    )
    if issue:
        issues.append(issue)

    # 8. Active target
    issue = _cmp_decimal(
        ai_position.get("active_target"),
        canon_position.get("active_target"),
        "/position_assessment/active_target",
        STATE_ACTIVE_TARGET_MISMATCH,
        "active target",
    )
    if issue:
        issues.append(issue)

    issues.sort(key=_sort_key)

    return StateConsistencyValidationResult(
        valid=len(issues) == 0,
        issues=tuple(issues),
    )
