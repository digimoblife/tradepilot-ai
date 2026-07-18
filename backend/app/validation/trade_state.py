"""Domain validation for TradePilot AI Trade State payloads.

Validates canonical position structure, quantity conservation, active-level
rules, timestamp ordering, and optional confirmed-action consistency.

The validator is read-only: it never mutates the payload or actions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Mapping, Sequence

from app.calculations.decimal_utils import to_decimal
from app.calculations.errors import InvalidDecimalError
from app.validation.issues import ValidationCategory, ValidationIssue, ValidationSeverity

# ---------------------------------------------------------------------------
# Domain issue category
# ---------------------------------------------------------------------------

DOMAIN_CATEGORY = ValidationCategory("DOMAIN")

# ---------------------------------------------------------------------------
# Stable error codes
# ---------------------------------------------------------------------------

# Numeric input
TRADE_STATE_NUMERIC_INPUT_INVALID = "TRADE_STATE_NUMERIC_INPUT_INVALID"

# Not-opened state
NON_POSITION_HAS_POSITION_VALUES = "NON_POSITION_HAS_POSITION_VALUES"

# Open state
OPEN_POSITION_INVALID_ENTRY = "OPEN_POSITION_INVALID_ENTRY"
OPEN_POSITION_INVALID_ORIGINAL_QUANTITY = "OPEN_POSITION_INVALID_ORIGINAL_QUANTITY"
OPEN_POSITION_INVALID_REMAINING_QUANTITY = "OPEN_POSITION_INVALID_REMAINING_QUANTITY"
OPEN_POSITION_HAS_AVERAGE_EXIT = "OPEN_POSITION_HAS_AVERAGE_EXIT"
OPEN_POSITION_QUANTITY_MISMATCH = "OPEN_POSITION_QUANTITY_MISMATCH"

# Partial state
PARTIAL_POSITION_INVALID_QUANTITY = "PARTIAL_POSITION_INVALID_QUANTITY"
PARTIAL_POSITION_AVERAGE_EXIT_MISSING = "PARTIAL_POSITION_AVERAGE_EXIT_MISSING"
PARTIAL_POSITION_REALIZED_RESULT_MISSING = "PARTIAL_POSITION_REALIZED_RESULT_MISSING"

# Closed state
CLOSED_POSITION_HAS_REMAINING_QUANTITY = "CLOSED_POSITION_HAS_REMAINING_QUANTITY"
CLOSED_POSITION_HAS_ACTIVE_STOP = "CLOSED_POSITION_HAS_ACTIVE_STOP"
CLOSED_POSITION_HAS_ACTIVE_TARGET = "CLOSED_POSITION_HAS_ACTIVE_TARGET"
CLOSED_POSITION_HAS_UNREALIZED_RESULT = "CLOSED_POSITION_HAS_UNREALIZED_RESULT"
CLOSED_POSITION_AVERAGE_EXIT_MISSING = "CLOSED_POSITION_AVERAGE_EXIT_MISSING"

# Quantity conservation
POSITION_REMAINING_EXCEEDS_ORIGINAL = "POSITION_REMAINING_EXCEEDS_ORIGINAL"

# Action consistency
TRADE_STATE_ACTION_HISTORY_INCONSISTENT = "TRADE_STATE_ACTION_HISTORY_INCONSISTENT"
TRADE_STATE_ACTION_MISSING_OPEN = "TRADE_STATE_ACTION_MISSING_OPEN"
TRADE_STATE_ACTION_DUPLICATE_OPEN = "TRADE_STATE_ACTION_DUPLICATE_OPEN"
TRADE_STATE_ACTION_ENTRY_PRICE_MISMATCH = "TRADE_STATE_ACTION_ENTRY_PRICE_MISMATCH"
TRADE_STATE_ACTION_ORIGINAL_QUANTITY_MISMATCH = "TRADE_STATE_ACTION_ORIGINAL_QUANTITY_MISMATCH"
TRADE_STATE_ACTION_TIMESTAMP_MISMATCH = "TRADE_STATE_ACTION_TIMESTAMP_MISMATCH"
TRADE_STATE_ACTION_BEFORE_OPEN = "TRADE_STATE_ACTION_BEFORE_OPEN"
TRADE_STATE_ACTION_AFTER_FULL_EXIT = "TRADE_STATE_ACTION_AFTER_FULL_EXIT"
TRADE_STATE_ACTION_DUPLICATE_FULL_EXIT = "TRADE_STATE_ACTION_DUPLICATE_FULL_EXIT"
TRADE_STATE_ACTION_CUMULATIVE_EXCEEDS_ORIGINAL = "TRADE_STATE_ACTION_CUMULATIVE_EXCEEDS_ORIGINAL"
TRADE_STATE_ACTION_REMAINING_MISMATCH = "TRADE_STATE_ACTION_REMAINING_MISMATCH"
TRADE_STATE_ACTION_MISSING_FULL_EXIT = "TRADE_STATE_ACTION_MISSING_FULL_EXIT"
TRADE_STATE_ACTION_INVALID_QUANTITY = "TRADE_STATE_ACTION_INVALID_QUANTITY"

# Timestamp
TRADE_STATE_TIMESTAMP_ORDER_INVALID = "TRADE_STATE_TIMESTAMP_ORDER_INVALID"

# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TradeStateValidationResult:
    valid: bool
    issues: tuple[ValidationIssue, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Confirmed action snapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ConfirmedActionSnapshot:
    """Immutable snapshot of one confirmed user action for cross-validation."""

    action_type: str
    confirmed_at: datetime
    price: Decimal | None
    quantity: Decimal | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_issue(
    code: str,
    path: str,
    message: str,
    expected: str | None = None,
    actual: str | None = None,
) -> ValidationIssue:
    return ValidationIssue(
        code=code,
        category=DOMAIN_CATEGORY,
        severity=ValidationSeverity.ERROR,
        path=path,
        message=message,
        expected=expected,
        actual=actual,
    )


def _sort_key(issue: ValidationIssue) -> tuple[str, str, str, str]:
    return (issue.path, issue.code, issue.category.value, issue.message)


def _d(value: object) -> Decimal | None:
    """Convert a raw value to Decimal via authoritative ``to_decimal()``.

    Returns ``None`` when the value is ``None``.
    Raises ``InvalidDecimalError`` for float / non-finite input.
    """
    if value is None:
        return None
    return to_decimal(value)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Numeric input validation
# ---------------------------------------------------------------------------


_POSITION_NUMERIC_FIELDS: tuple[tuple[str, str], ...] = (
    ("entry_price", "/position/entry_price"),
    ("original_quantity", "/position/original_quantity"),
    ("remaining_quantity", "/position/remaining_quantity"),
    ("average_exit_price", "/position/average_exit_price"),
    ("active_stop_loss", "/position/active_stop_loss"),
    ("active_target", "/position/active_target"),
    ("realized_profit_loss", "/position/realized_profit_loss"),
    ("realized_return_percentage", "/position/realized_return_percentage"),
    ("unrealized_profit_loss", "/position/unrealized_profit_loss"),
    ("unrealized_return_percentage", "/position/unrealized_return_percentage"),
)


def _validate_numeric_inputs(payload: Mapping[str, object]) -> list[ValidationIssue]:
    """Validate all numeric fields through authoritative ``to_decimal()``."""
    issues: list[ValidationIssue] = []
    position = payload.get("position")
    if not isinstance(position, dict):
        return issues

    for field_key, field_path in _POSITION_NUMERIC_FIELDS:
        raw = position.get(field_key)
        if raw is None:
            continue
        try:
            _d(raw)
        except InvalidDecimalError:
            issues.append(
                _make_issue(
                    TRADE_STATE_NUMERIC_INPUT_INVALID,
                    field_path,
                    f"Invalid numeric input for {field_key}: "
                    f"type={type(raw).__name__}, value={raw!r}",
                    expected="Decimal, int, or str",
                    actual=f"{type(raw).__name__}: {raw!r}",
                )
            )
    return issues


# ---------------------------------------------------------------------------
# Position status helpers
# ---------------------------------------------------------------------------


def _get_position(
    payload: Mapping[str, object],
) -> dict[str, object] | None:
    p = payload.get("position")
    return p if isinstance(p, dict) else None


def _get_status(position: dict[str, object]) -> str | None:
    s = position.get("position_status")
    return str(s) if isinstance(s, str) else None


# ---------------------------------------------------------------------------
# Not-opened validation
# ---------------------------------------------------------------------------


def _validate_not_opened(position: dict[str, object]) -> list[ValidationIssue]:
    """All position fields must be null/zero when not opened."""
    issues: list[ValidationIssue] = []

    null_fields = [
        ("entry_price", "/position/entry_price"),
        ("entry_timestamp", "/position/entry_timestamp"),
        ("original_quantity", "/position/original_quantity"),
        ("remaining_quantity", "/position/remaining_quantity"),
        ("average_exit_price", "/position/average_exit_price"),
        ("active_stop_loss", "/position/active_stop_loss"),
        ("active_target", "/position/active_target"),
        ("realized_profit_loss", "/position/realized_profit_loss"),
        ("realized_return_percentage", "/position/realized_return_percentage"),
        ("unrealized_profit_loss", "/position/unrealized_profit_loss"),
        ("unrealized_return_percentage", "/position/unrealized_return_percentage"),
        ("last_confirmed_at", "/position/last_confirmed_at"),
    ]

    has_value = False
    for field_key, field_path in null_fields:
        val = position.get(field_key)
        if val is not None:
            has_value = True
            break

    if has_value:
        issues.append(
            _make_issue(
                NON_POSITION_HAS_POSITION_VALUES,
                "/position",
                "Position is not opened but contains non-null position fields",
                expected="all position fields null",
                actual="non-null values present",
            )
        )

    return issues


# ---------------------------------------------------------------------------
# Open state validation
# ---------------------------------------------------------------------------


def _validate_open(position: dict[str, object]) -> list[ValidationIssue]:
    """Validate a position with status OPEN."""
    issues: list[ValidationIssue] = []

    entry = _d(position.get("entry_price"))
    orig_qty = _d(position.get("original_quantity"))
    rem_qty = _d(position.get("remaining_quantity"))
    avg_exit = _d(position.get("average_exit_price"))
    exists_raw = position.get("position_exists")

    if exists_raw is not True:
        issues.append(
            _make_issue(
                OPEN_POSITION_INVALID_ENTRY,
                "/position/position_exists",
                "Open position must have position_exists=true",
                expected="true",
                actual=str(exists_raw),
            )
        )

    if entry is None or entry <= Decimal("0"):
        issues.append(
            _make_issue(
                OPEN_POSITION_INVALID_ENTRY,
                "/position/entry_price",
                "Open position must have a positive entry price",
                expected="> 0",
                actual=str(entry) if entry is not None else "null",
            )
        )

    if orig_qty is None or orig_qty <= Decimal("0"):
        issues.append(
            _make_issue(
                OPEN_POSITION_INVALID_ORIGINAL_QUANTITY,
                "/position/original_quantity",
                "Open position must have a positive original quantity",
                expected="> 0",
                actual=str(orig_qty) if orig_qty is not None else "null",
            )
        )

    if rem_qty is None or rem_qty <= Decimal("0"):
        issues.append(
            _make_issue(
                OPEN_POSITION_INVALID_REMAINING_QUANTITY,
                "/position/remaining_quantity",
                "Open position must have a positive remaining quantity",
                expected="> 0",
                actual=str(rem_qty) if rem_qty is not None else "null",
            )
        )

    if avg_exit is not None:
        issues.append(
            _make_issue(
                OPEN_POSITION_HAS_AVERAGE_EXIT,
                "/position/average_exit_price",
                "Open position must not have an average exit price",
                expected="null",
                actual=str(avg_exit),
            )
        )

    if orig_qty is not None and rem_qty is not None and orig_qty > Decimal("0"):
        if rem_qty != orig_qty:
            issues.append(
                _make_issue(
                    OPEN_POSITION_QUANTITY_MISMATCH,
                    "/position/remaining_quantity",
                    f"Open position remaining quantity ({rem_qty}) "
                    f"must equal original ({orig_qty})",
                    expected=str(orig_qty),
                    actual=str(rem_qty),
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Partial state validation
# ---------------------------------------------------------------------------


def _validate_partial(position: dict[str, object]) -> list[ValidationIssue]:
    """Validate a position with status PARTIALLY_CLOSED."""
    issues: list[ValidationIssue] = []

    orig_qty = _d(position.get("original_quantity"))
    rem_qty = _d(position.get("remaining_quantity"))
    avg_exit = _d(position.get("average_exit_price"))
    realized = _d(position.get("realized_profit_loss"))
    realized_return = _d(position.get("realized_return_percentage"))

    if orig_qty is None or orig_qty <= Decimal("0"):
        issues.append(
            _make_issue(
                PARTIAL_POSITION_INVALID_QUANTITY,
                "/position/original_quantity",
                "Partially closed position must have a positive original quantity",
                expected="> 0",
                actual=str(orig_qty) if orig_qty is not None else "null",
            )
        )

    if rem_qty is None or rem_qty <= Decimal("0"):
        issues.append(
            _make_issue(
                PARTIAL_POSITION_INVALID_QUANTITY,
                "/position/remaining_quantity",
                "Partially closed position must have a positive remaining quantity",
                expected="> 0",
                actual=str(rem_qty) if rem_qty is not None else "null",
            )
        )

    if (
        orig_qty is not None
        and rem_qty is not None
        and orig_qty > Decimal("0")
        and rem_qty > Decimal("0")
    ):
        if rem_qty >= orig_qty:
            issues.append(
                _make_issue(
                    PARTIAL_POSITION_INVALID_QUANTITY,
                    "/position/remaining_quantity",
                    f"Partially closed position remaining ({rem_qty}) "
                    f"must be less than original ({orig_qty})",
                    expected=f"< {orig_qty}",
                    actual=str(rem_qty),
                )
            )

    if avg_exit is None or avg_exit <= Decimal("0"):
        issues.append(
            _make_issue(
                PARTIAL_POSITION_AVERAGE_EXIT_MISSING,
                "/position/average_exit_price",
                "Partially closed position must have a positive average exit price",
                expected="> 0",
                actual=str(avg_exit) if avg_exit is not None else "null",
            )
        )

    if realized is None:
        issues.append(
            _make_issue(
                PARTIAL_POSITION_REALIZED_RESULT_MISSING,
                "/position/realized_profit_loss",
                "Partially closed position must have a realized P&L",
                expected="non-null",
                actual="null",
            )
        )

    if realized_return is None:
        issues.append(
            _make_issue(
                PARTIAL_POSITION_REALIZED_RESULT_MISSING,
                "/position/realized_return_percentage",
                "Partially closed position must have a realized return percentage",
                expected="non-null",
                actual="null",
            )
        )

    return issues


# ---------------------------------------------------------------------------
# Closed state validation
# ---------------------------------------------------------------------------


def _validate_closed(position: dict[str, object]) -> list[ValidationIssue]:
    """Validate a position with status CLOSED."""
    issues: list[ValidationIssue] = []

    rem_qty = _d(position.get("remaining_quantity"))
    avg_exit = _d(position.get("average_exit_price"))
    active_stop = _d(position.get("active_stop_loss"))
    active_target = _d(position.get("active_target"))
    unrealized = _d(position.get("unrealized_profit_loss"))
    unrealized_return = _d(position.get("unrealized_return_percentage"))

    if rem_qty is not None and rem_qty != Decimal("0"):
        issues.append(
            _make_issue(
                CLOSED_POSITION_HAS_REMAINING_QUANTITY,
                "/position/remaining_quantity",
                f"Closed position must have remaining quantity 0, got {rem_qty}",
                expected="0",
                actual=str(rem_qty),
            )
        )

    if avg_exit is None or avg_exit <= Decimal("0"):
        issues.append(
            _make_issue(
                CLOSED_POSITION_AVERAGE_EXIT_MISSING,
                "/position/average_exit_price",
                "Closed position must have a positive average exit price",
                expected="> 0",
                actual=str(avg_exit) if avg_exit is not None else "null",
            )
        )

    if active_stop is not None:
        issues.append(
            _make_issue(
                CLOSED_POSITION_HAS_ACTIVE_STOP,
                "/position/active_stop_loss",
                f"Closed position must not have an active stop loss, got {active_stop}",
                expected="null",
                actual=str(active_stop),
            )
        )

    if active_target is not None:
        issues.append(
            _make_issue(
                CLOSED_POSITION_HAS_ACTIVE_TARGET,
                "/position/active_target",
                f"Closed position must not have an active target, got {active_target}",
                expected="null",
                actual=str(active_target),
            )
        )

    if unrealized is not None or unrealized_return is not None:
        issues.append(
            _make_issue(
                CLOSED_POSITION_HAS_UNREALIZED_RESULT,
                "/position",
                "Closed position must not have unrealized P&L fields",
                expected="null",
                actual="non-null unrealized fields present",
            )
        )

    return issues


# ---------------------------------------------------------------------------
# Quantity conservation
# ---------------------------------------------------------------------------


def _validate_quantity_conservation(position: dict[str, object]) -> list[ValidationIssue]:
    """Validate remaining <= original across all states."""
    issues: list[ValidationIssue] = []

    orig_qty = _d(position.get("original_quantity"))
    rem_qty = _d(position.get("remaining_quantity"))

    if orig_qty is not None and rem_qty is not None and orig_qty >= Decimal("0"):
        if rem_qty > orig_qty:
            issues.append(
                _make_issue(
                    POSITION_REMAINING_EXCEEDS_ORIGINAL,
                    "/position/remaining_quantity",
                    f"Remaining quantity ({rem_qty}) exceeds original ({orig_qty})",
                    expected=f"<= {orig_qty}",
                    actual=str(rem_qty),
                )
            )

    return issues


# ---------------------------------------------------------------------------
# Timestamp validation
# ---------------------------------------------------------------------------


def _validate_timestamps(position: dict[str, object]) -> list[ValidationIssue]:
    """Validate timestamp ordering within position."""
    issues: list[ValidationIssue] = []

    entry_ts_str = position.get("entry_timestamp")
    last_confirmed_str = position.get("last_confirmed_at")

    if isinstance(entry_ts_str, str) and isinstance(last_confirmed_str, str):
        try:
            entry_dt = datetime.fromisoformat(entry_ts_str)
            confirmed_dt = datetime.fromisoformat(last_confirmed_str)
            if entry_dt > confirmed_dt:
                issues.append(
                    _make_issue(
                        TRADE_STATE_TIMESTAMP_ORDER_INVALID,
                        "/position/entry_timestamp",
                        f"Entry timestamp ({entry_ts_str}) is after "
                        f"last confirmed action ({last_confirmed_str})",
                        expected=f"<= {last_confirmed_str}",
                        actual=entry_ts_str,
                    )
                )
        except (ValueError, TypeError):
            pass

    return issues


# ---------------------------------------------------------------------------
# Action consistency
# ---------------------------------------------------------------------------


def _validate_actions(
    position: dict[str, object],
    actions: Sequence[ConfirmedActionSnapshot] | None,
) -> list[ValidationIssue]:
    """Validate confirmed-action consistency when action snapshots supplied.

    When ``actions`` is ``None``, all cross-action checks are skipped
    (only internal state rules apply).  An explicit empty tuple means
    action context was supplied with no actions.

    Chronology rules (where relevant):
      - POSITION_OPENED must precede all exit actions.
      - FULL_EXIT must be the last position-related action.
      - PARTIAL_EXIT must precede FULL_EXIT.
      - Duplicate POSITION_OPENED or FULL_EXIT actions are rejected.
    """
    if actions is None:
        return []

    issues: list[ValidationIssue] = []
    status = _get_status(position)

    # Sort chronologically without mutating caller input
    sorted_actions = tuple(sorted(actions, key=lambda a: a.confirmed_at))

    # ------------------------------------------------------------------
    # 1. Find the open action(s)
    # ------------------------------------------------------------------
    open_actions = [a for a in sorted_actions if a.action_type == "POSITION_OPENED"]
    partial_actions = [a for a in sorted_actions if a.action_type == "PARTIAL_EXIT"]
    full_exit_actions = [a for a in sorted_actions if a.action_type == "FULL_EXIT"]

    # Non-NOT_OPENED states require an open action
    if status in ("OPEN", "PARTIALLY_CLOSED", "CLOSED"):
        if not open_actions:
            issues.append(
                _make_issue(
                    TRADE_STATE_ACTION_MISSING_OPEN,
                    "/position",
                    f"Position status is {status} but no POSITION_OPENED action found",
                    expected="at least one POSITION_OPENED action",
                    actual="none",
                )
            )
            # Cannot continue with action matching if no open action
            return issues

        # Duplicate open actions
        if len(open_actions) > 1:
            issues.append(
                _make_issue(
                    TRADE_STATE_ACTION_DUPLICATE_OPEN,
                    "/position",
                    f"Found {len(open_actions)} POSITION_OPENED actions, expected 1",
                    expected="1",
                    actual=str(len(open_actions)),
                )
            )

        effective_open = open_actions[0]

        # 2. Entry price match
        state_entry = _d(position.get("entry_price"))
        if state_entry is not None and effective_open.price is not None:
            open_price = _d(effective_open.price)
            if open_price is not None and state_entry != open_price:
                issues.append(
                    _make_issue(
                        TRADE_STATE_ACTION_ENTRY_PRICE_MISMATCH,
                        "/position/entry_price",
                        f"State entry price ({state_entry}) does not match "
                        f"confirmed open action price ({open_price})",
                        expected=str(open_price),
                        actual=str(state_entry),
                    )
                )

        # 3. Original quantity match
        state_orig_qty = _d(position.get("original_quantity"))
        if state_orig_qty is not None and effective_open.quantity is not None:
            open_qty = _d(effective_open.quantity)
            if open_qty is not None and state_orig_qty != open_qty:
                issues.append(
                    _make_issue(
                        TRADE_STATE_ACTION_ORIGINAL_QUANTITY_MISMATCH,
                        "/position/original_quantity",
                        f"State original quantity ({state_orig_qty}) does not match "
                        f"confirmed open action quantity ({open_qty})",
                        expected=str(open_qty),
                        actual=str(state_orig_qty),
                    )
                )

        # 4. Entry timestamp match (entry <= confirmed_at)
        entry_ts_str = position.get("entry_timestamp")
        if isinstance(entry_ts_str, str):
            try:
                entry_dt = datetime.fromisoformat(entry_ts_str)
                if entry_dt > effective_open.confirmed_at:
                    issues.append(
                        _make_issue(
                            TRADE_STATE_ACTION_TIMESTAMP_MISMATCH,
                            "/position/entry_timestamp",
                            f"Entry timestamp ({entry_ts_str}) is after "
                            f"confirmed open action ({effective_open.confirmed_at})",
                            expected=f"<= {effective_open.confirmed_at.isoformat()}",
                            actual=entry_ts_str,
                        )
                    )
            except (ValueError, TypeError):
                pass

    # ------------------------------------------------------------------
    # 5. Chronology: actions before open
    # ------------------------------------------------------------------
    if open_actions:
        open_ts = open_actions[0].confirmed_at
        position_action_types = {
            "PARTIAL_EXIT",
            "FULL_EXIT",
            "STOP_LOSS_CONFIRMED",
            "STOP_LOSS_CHANGED",
            "TARGET_CONFIRMED",
            "TARGET_CHANGED",
        }
        for a in sorted_actions:
            if a.action_type in position_action_types and a.confirmed_at < open_ts:
                issues.append(
                    _make_issue(
                        TRADE_STATE_ACTION_BEFORE_OPEN,
                        "/confirmed_actions",
                        f"{a.action_type} action at {a.confirmed_at.isoformat()} "
                        f"is before POSITION_OPENED at {open_ts.isoformat()}",
                        expected=f">= {open_ts.isoformat()}",
                        actual=a.confirmed_at.isoformat(),
                    )
                )

    # ------------------------------------------------------------------
    # 6. Actions after full exit
    # ------------------------------------------------------------------
    if full_exit_actions:
        last_full_exit = full_exit_actions[-1]
        full_exit_ts = last_full_exit.confirmed_at
        position_action_types = {
            "PARTIAL_EXIT",
            "FULL_EXIT",
            "STOP_LOSS_CONFIRMED",
            "STOP_LOSS_CHANGED",
            "TARGET_CONFIRMED",
            "TARGET_CHANGED",
        }
        for a in sorted_actions:
            if a.action_type in position_action_types and a.confirmed_at > full_exit_ts:
                if a is not last_full_exit:  # allow the full exit itself
                    issues.append(
                        _make_issue(
                            TRADE_STATE_ACTION_AFTER_FULL_EXIT,
                            "/confirmed_actions",
                            f"{a.action_type} action at {a.confirmed_at.isoformat()} "
                            f"is after FULL_EXIT at {full_exit_ts.isoformat()}",
                            expected=f"<= {full_exit_ts.isoformat()}",
                            actual=a.confirmed_at.isoformat(),
                        )
                    )

    # ------------------------------------------------------------------
    # 7. Duplicate full exit
    # ------------------------------------------------------------------
    if len(full_exit_actions) > 1:
        issues.append(
            _make_issue(
                TRADE_STATE_ACTION_DUPLICATE_FULL_EXIT,
                "/confirmed_actions",
                f"Found {len(full_exit_actions)} FULL_EXIT actions, expected 1",
                expected="1",
                actual=str(len(full_exit_actions)),
            )
        )

    # ------------------------------------------------------------------
    # 8. Required action types per state
    # ------------------------------------------------------------------
    if status in ("PARTIALLY_CLOSED", "CLOSED"):
        if not partial_actions:
            status_name = "PARTIALLY_CLOSED" if status == "PARTIALLY_CLOSED" else "CLOSED"
            issues.append(
                _make_issue(
                    TRADE_STATE_ACTION_HISTORY_INCONSISTENT,
                    "/position",
                    f"Position status is {status_name} but no PARTIAL_EXIT action found",
                    expected="at least one PARTIAL_EXIT action",
                    actual="none",
                )
            )

    if status == "CLOSED":
        if not full_exit_actions:
            issues.append(
                _make_issue(
                    TRADE_STATE_ACTION_MISSING_FULL_EXIT,
                    "/position",
                    "Position status is CLOSED but no FULL_EXIT action found",
                    expected="at least one FULL_EXIT action",
                    actual="none",
                )
            )

    # ------------------------------------------------------------------
    # 9. Cumulative partial quantity
    # ------------------------------------------------------------------
    if partial_actions and open_actions:
        state_orig_qty = _d(position.get("original_quantity"))
        cum_exit_qty = Decimal("0")
        for p in partial_actions:
            if p.quantity is not None:
                try:
                    pq = to_decimal(p.quantity)
                except InvalidDecimalError:
                    issues.append(
                        _make_issue(
                            TRADE_STATE_ACTION_INVALID_QUANTITY,
                            "/confirmed_actions",
                            f"Invalid quantity in PARTIAL_EXIT action: {p.quantity!r}",
                            expected="valid Decimal",
                            actual=str(p.quantity),
                        )
                    )
                    continue
                if pq <= Decimal("0"):
                    issues.append(
                        _make_issue(
                            TRADE_STATE_ACTION_INVALID_QUANTITY,
                            "/confirmed_actions",
                            f"Non-positive quantity ({pq}) in PARTIAL_EXIT action",
                            expected="> 0",
                            actual=str(pq),
                        )
                    )
                else:
                    cum_exit_qty += pq

        if state_orig_qty is not None and state_orig_qty > Decimal("0"):
            if cum_exit_qty > state_orig_qty:
                issues.append(
                    _make_issue(
                        TRADE_STATE_ACTION_CUMULATIVE_EXCEEDS_ORIGINAL,
                        "/position/remaining_quantity",
                        f"Cumulative partial exit quantity ({cum_exit_qty}) "
                        f"exceeds original ({state_orig_qty})",
                        expected=f"<= {state_orig_qty}",
                        actual=str(cum_exit_qty),
                    )
                )

            # Remaining quantity reconciliation
            state_rem_qty = _d(position.get("remaining_quantity"))
            if state_rem_qty is not None and status == "PARTIALLY_CLOSED":
                expected_rem = state_orig_qty - cum_exit_qty
                if expected_rem >= Decimal("0") and state_rem_qty != expected_rem:
                    issues.append(
                        _make_issue(
                            TRADE_STATE_ACTION_REMAINING_MISMATCH,
                            "/position/remaining_quantity",
                            f"State remaining ({state_rem_qty}) differs from "
                            f"expected ({expected_rem}) based on cumulative exits "
                            f"({cum_exit_qty})",
                            expected=str(expected_rem),
                            actual=str(state_rem_qty),
                        )
                    )

            # Partial exiting full position
            if status == "PARTIALLY_CLOSED" and cum_exit_qty >= state_orig_qty:
                issues.append(
                    _make_issue(
                        TRADE_STATE_ACTION_HISTORY_INCONSISTENT,
                        "/position/remaining_quantity",
                        f"Cumulative partial exits ({cum_exit_qty}) equal or "
                        f"exceed original ({state_orig_qty}) but status is "
                        f"PARTIALLY_CLOSED",
                        expected="< original quantity",
                        actual=str(cum_exit_qty),
                    )
                )

    return issues


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------


def validate_trade_state(
    payload: Mapping[str, object],
    *,
    confirmed_actions: Sequence[ConfirmedActionSnapshot] | None = None,
) -> TradeStateValidationResult:
    """Validate a Trade State payload against all domain rules.

    Parameters
    ----------
    payload:
        The Trade State dictionary (already schema-validated).
    confirmed_actions:
        Optional sequence of immutable confirmed-action snapshots for
        cross-validation.  If ``None``, action-consistency checks are skipped.

    Returns
    -------
    TradeStateValidationResult
    """
    issues: list[ValidationIssue] = []

    # Numeric input validation before any downstream arithmetic
    issues.extend(_validate_numeric_inputs(payload))
    if issues:
        return TradeStateValidationResult(valid=False, issues=tuple(issues))

    position = _get_position(payload)
    if position is None:
        issues.append(
            _make_issue(
                TRADE_STATE_NUMERIC_INPUT_INVALID,
                "/position",
                "Trade state payload must contain a position object",
            )
        )
        return TradeStateValidationResult(valid=False, issues=tuple(issues))

    status = _get_status(position)

    if status == "NOT_OPENED":
        issues.extend(_validate_not_opened(position))
    elif status == "OPEN":
        issues.extend(_validate_open(position))
    elif status == "PARTIALLY_CLOSED":
        issues.extend(_validate_partial(position))
    elif status == "CLOSED":
        issues.extend(_validate_closed(position))

    # Quantity conservation always runs
    issues.extend(_validate_quantity_conservation(position))

    # Timestamps always run
    issues.extend(_validate_timestamps(position))

    # Action consistency (optional)
    issues.extend(_validate_actions(position, confirmed_actions))

    issues.sort(key=_sort_key)

    return TradeStateValidationResult(
        valid=len(issues) == 0,
        issues=tuple(issues),
    )
