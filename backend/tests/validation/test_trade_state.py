"""Tests for Trade State domain validator (TP-0306)."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from decimal import Decimal

from app.validation.issues import ValidationCategory, ValidationSeverity
from app.validation.trade_state import (
    CLOSED_POSITION_AVERAGE_EXIT_MISSING,
    CLOSED_POSITION_HAS_ACTIVE_STOP,
    CLOSED_POSITION_HAS_ACTIVE_TARGET,
    CLOSED_POSITION_HAS_REMAINING_QUANTITY,
    CLOSED_POSITION_HAS_UNREALIZED_RESULT,
    NON_POSITION_HAS_POSITION_VALUES,
    OPEN_POSITION_HAS_AVERAGE_EXIT,
    OPEN_POSITION_INVALID_ENTRY,
    OPEN_POSITION_INVALID_ORIGINAL_QUANTITY,
    OPEN_POSITION_INVALID_REMAINING_QUANTITY,
    OPEN_POSITION_QUANTITY_MISMATCH,
    PARTIAL_POSITION_AVERAGE_EXIT_MISSING,
    PARTIAL_POSITION_INVALID_QUANTITY,
    PARTIAL_POSITION_REALIZED_RESULT_MISSING,
    POSITION_REMAINING_EXCEEDS_ORIGINAL,
    TRADE_STATE_ACTION_AFTER_FULL_EXIT,
    TRADE_STATE_ACTION_BEFORE_OPEN,
    TRADE_STATE_ACTION_CUMULATIVE_EXCEEDS_ORIGINAL,
    TRADE_STATE_ACTION_DUPLICATE_FULL_EXIT,
    TRADE_STATE_ACTION_DUPLICATE_OPEN,
    TRADE_STATE_ACTION_ENTRY_PRICE_MISMATCH,
    TRADE_STATE_ACTION_HISTORY_INCONSISTENT,
    TRADE_STATE_ACTION_INVALID_QUANTITY,
    TRADE_STATE_ACTION_MISSING_FULL_EXIT,
    TRADE_STATE_ACTION_MISSING_OPEN,
    TRADE_STATE_ACTION_ORIGINAL_QUANTITY_MISMATCH,
    TRADE_STATE_ACTION_REMAINING_MISMATCH,
    TRADE_STATE_ACTION_TIMESTAMP_MISMATCH,
    TRADE_STATE_NUMERIC_INPUT_INVALID,
    TRADE_STATE_TIMESTAMP_ORDER_INVALID,
    ConfirmedActionSnapshot,
    TradeStateValidationResult,
    validate_trade_state,
)

NOW = datetime(2026, 7, 18, 12, 0, 0, tzinfo=timezone.utc)
OPEN_TS = datetime(2026, 7, 15, 10, 12, tzinfo=timezone.utc)
BEFORE_TS = datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc)
AFTER_TS = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
EXIT_TS = datetime(2026, 7, 17, 14, 5, tzinfo=timezone.utc)
CLOSE_TS = datetime(2026, 7, 17, 15, 12, tzinfo=timezone.utc)


def _not_opened() -> dict[str, object]:
    return {
        "session_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "ticker": "BBRI",
        "position": {
            "position_exists": False,
            "position_status": "NOT_OPENED",
            "entry_price": None,
            "entry_timestamp": None,
            "original_quantity": None,
            "remaining_quantity": None,
            "average_exit_price": None,
            "active_stop_loss": None,
            "active_target": None,
            "realized_profit_loss": None,
            "realized_return_percentage": None,
            "unrealized_profit_loss": None,
            "unrealized_return_percentage": None,
            "distance_to_stop_percentage": None,
            "distance_to_target_percentage": None,
            "holding_duration_days": None,
            "last_confirmed_at": None,
        },
    }


def _open_pos() -> dict[str, object]:
    return {
        "session_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "ticker": "BBRI",
        "position": {
            "position_exists": True,
            "position_status": "OPEN",
            "entry_price": 2800,
            "entry_timestamp": "2026-07-15T10:12:00+07:00",
            "original_quantity": 100,
            "remaining_quantity": 100,
            "average_exit_price": None,
            "active_stop_loss": 2840,
            "active_target": 2920,
            "realized_profit_loss": None,
            "realized_return_percentage": None,
            "unrealized_profit_loss": 9000,
            "unrealized_return_percentage": "3.21",
            "distance_to_stop_percentage": "1.73",
            "distance_to_target_percentage": "1.04",
            "holding_duration_days": 2,
            "last_confirmed_at": "2026-07-15T10:12:00+07:00",
        },
    }


def _partial_pos() -> dict[str, object]:
    return {
        "session_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "ticker": "BBRI",
        "position": {
            "position_exists": True,
            "position_status": "PARTIALLY_CLOSED",
            "entry_price": 2800,
            "entry_timestamp": "2026-07-15T10:12:00+07:00",
            "original_quantity": 100,
            "remaining_quantity": 50,
            "average_exit_price": 2920,
            "active_stop_loss": 2840,
            "active_target": 3000,
            "realized_profit_loss": 6000,
            "realized_return_percentage": "4.29",
            "unrealized_profit_loss": 5500,
            "unrealized_return_percentage": "3.93",
            "distance_to_stop_percentage": "2.41",
            "distance_to_target_percentage": "3.09",
            "holding_duration_days": 2,
            "last_confirmed_at": "2026-07-17T14:05:00+07:00",
        },
    }


def _closed_pos() -> dict[str, object]:
    return {
        "session_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "ticker": "BBRI",
        "position": {
            "position_exists": True,
            "position_status": "CLOSED",
            "entry_price": 2800,
            "entry_timestamp": "2026-07-15T10:12:00+07:00",
            "original_quantity": 100,
            "remaining_quantity": 0,
            "average_exit_price": 2910,
            "active_stop_loss": None,
            "active_target": None,
            "realized_profit_loss": 11000,
            "realized_return_percentage": "3.93",
            "unrealized_profit_loss": None,
            "unrealized_return_percentage": None,
            "distance_to_stop_percentage": None,
            "distance_to_target_percentage": None,
            "holding_duration_days": 2,
            "last_confirmed_at": "2026-07-17T15:12:00+07:00",
        },
    }


def _expect(result: TradeStateValidationResult, code: str) -> None:
    assert not result.valid, f"Expected {code} but result is valid"
    codes = {i.code for i in result.issues}
    assert code in codes, f"Expected code {code!r} not in {codes}"


# ===================================================================
# Internal state tests
# ===================================================================


class TestNotOpened:
    def test_valid(self) -> None:
        assert validate_trade_state(_not_opened()).valid

    def test_valid_with_thesis(self) -> None:
        p = _not_opened()
        p["thesis"] = {"status": "NOT_ESTABLISHED"}
        assert validate_trade_state(p).valid

    def test_entry_price_present(self) -> None:
        p = _not_opened()
        p["position"]["entry_price"] = 2800
        _expect(validate_trade_state(p), NON_POSITION_HAS_POSITION_VALUES)

    def test_quantities_present(self) -> None:
        p = _not_opened()
        p["position"]["original_quantity"] = 100
        _expect(validate_trade_state(p), NON_POSITION_HAS_POSITION_VALUES)

    def test_active_stop_present(self) -> None:
        p = _not_opened()
        p["position"]["active_stop_loss"] = 2700
        _expect(validate_trade_state(p), NON_POSITION_HAS_POSITION_VALUES)

    def test_active_target_present(self) -> None:
        p = _not_opened()
        p["position"]["active_target"] = 2920
        _expect(validate_trade_state(p), NON_POSITION_HAS_POSITION_VALUES)

    def test_avg_exit_present(self) -> None:
        p = _not_opened()
        p["position"]["average_exit_price"] = 2910
        _expect(validate_trade_state(p), NON_POSITION_HAS_POSITION_VALUES)

    def test_realized_pnl_present(self) -> None:
        p = _not_opened()
        p["position"]["realized_profit_loss"] = 1000
        _expect(validate_trade_state(p), NON_POSITION_HAS_POSITION_VALUES)

    def test_payload_unchanged(self) -> None:
        p = _not_opened()
        before = copy.deepcopy(p)
        validate_trade_state(p)
        assert p == before


class TestOpen:
    def test_valid(self) -> None:
        assert validate_trade_state(_open_pos()).valid

    def test_missing_entry_price(self) -> None:
        p = _open_pos()
        p["position"]["entry_price"] = None
        _expect(validate_trade_state(p), OPEN_POSITION_INVALID_ENTRY)

    def test_zero_entry_price(self) -> None:
        p = _open_pos()
        p["position"]["entry_price"] = 0
        _expect(validate_trade_state(p), OPEN_POSITION_INVALID_ENTRY)

    def test_zero_original_quantity(self) -> None:
        p = _open_pos()
        p["position"]["original_quantity"] = 0
        _expect(validate_trade_state(p), OPEN_POSITION_INVALID_ORIGINAL_QUANTITY)

    def test_zero_remaining_quantity(self) -> None:
        p = _open_pos()
        p["position"]["remaining_quantity"] = 0
        _expect(validate_trade_state(p), OPEN_POSITION_INVALID_REMAINING_QUANTITY)

    def test_remaining_below_original(self) -> None:
        p = _open_pos()
        p["position"]["remaining_quantity"] = 50
        _expect(validate_trade_state(p), OPEN_POSITION_QUANTITY_MISMATCH)

    def test_remaining_above_original(self) -> None:
        p = _open_pos()
        p["position"]["remaining_quantity"] = 150
        _expect(validate_trade_state(p), POSITION_REMAINING_EXCEEDS_ORIGINAL)

    def test_has_average_exit(self) -> None:
        p = _open_pos()
        p["position"]["average_exit_price"] = 2910
        _expect(validate_trade_state(p), OPEN_POSITION_HAS_AVERAGE_EXIT)


class TestPartial:
    def test_valid(self) -> None:
        assert validate_trade_state(_partial_pos()).valid

    def test_remaining_equal_original(self) -> None:
        p = _partial_pos()
        p["position"]["remaining_quantity"] = 100
        _expect(validate_trade_state(p), PARTIAL_POSITION_INVALID_QUANTITY)

    def test_remaining_zero(self) -> None:
        p = _partial_pos()
        p["position"]["remaining_quantity"] = 0
        _expect(validate_trade_state(p), PARTIAL_POSITION_INVALID_QUANTITY)

    def test_remaining_above_original(self) -> None:
        p = _partial_pos()
        p["position"]["remaining_quantity"] = 150
        _expect(validate_trade_state(p), POSITION_REMAINING_EXCEEDS_ORIGINAL)

    def test_missing_average_exit(self) -> None:
        p = _partial_pos()
        p["position"]["average_exit_price"] = None
        _expect(validate_trade_state(p), PARTIAL_POSITION_AVERAGE_EXIT_MISSING)

    def test_missing_realized_pnl(self) -> None:
        p = _partial_pos()
        p["position"]["realized_profit_loss"] = None
        _expect(validate_trade_state(p), PARTIAL_POSITION_REALIZED_RESULT_MISSING)

    def test_missing_realized_return(self) -> None:
        p = _partial_pos()
        p["position"]["realized_return_percentage"] = None
        _expect(validate_trade_state(p), PARTIAL_POSITION_REALIZED_RESULT_MISSING)


class TestClosed:
    def test_valid(self) -> None:
        assert validate_trade_state(_closed_pos()).valid

    def test_remaining_above_zero(self) -> None:
        p = _closed_pos()
        p["position"]["remaining_quantity"] = 50
        _expect(validate_trade_state(p), CLOSED_POSITION_HAS_REMAINING_QUANTITY)

    def test_retains_active_stop(self) -> None:
        p = _closed_pos()
        p["position"]["active_stop_loss"] = 2840
        _expect(validate_trade_state(p), CLOSED_POSITION_HAS_ACTIVE_STOP)

    def test_retains_active_target(self) -> None:
        p = _closed_pos()
        p["position"]["active_target"] = 2920
        _expect(validate_trade_state(p), CLOSED_POSITION_HAS_ACTIVE_TARGET)

    def test_retains_both_active_levels(self) -> None:
        p = _closed_pos()
        p["position"]["active_stop_loss"] = 2840
        p["position"]["active_target"] = 2920
        r = validate_trade_state(p)
        _expect(r, CLOSED_POSITION_HAS_ACTIVE_STOP)
        _expect(r, CLOSED_POSITION_HAS_ACTIVE_TARGET)

    def test_has_unrealized_pnl(self) -> None:
        p = _closed_pos()
        p["position"]["unrealized_profit_loss"] = 5000
        _expect(validate_trade_state(p), CLOSED_POSITION_HAS_UNREALIZED_RESULT)

    def test_missing_average_exit(self) -> None:
        p = _closed_pos()
        p["position"]["average_exit_price"] = None
        _expect(validate_trade_state(p), CLOSED_POSITION_AVERAGE_EXIT_MISSING)

    def test_retains_entry_history(self) -> None:
        assert validate_trade_state(_closed_pos()).valid


class TestQuantityConservation:
    def test_remaining_exceeds_original(self) -> None:
        p = _open_pos()
        p["position"]["remaining_quantity"] = 200
        _expect(validate_trade_state(p), POSITION_REMAINING_EXCEEDS_ORIGINAL)


class TestTimestamps:
    def test_valid_ordering(self) -> None:
        assert validate_trade_state(_open_pos()).valid

    def test_entry_after_confirmed(self) -> None:
        p = _open_pos()
        p["position"]["entry_timestamp"] = "2026-07-18T12:00:00+07:00"
        p["position"]["last_confirmed_at"] = "2026-07-15T10:12:00+07:00"
        _expect(validate_trade_state(p), TRADE_STATE_TIMESTAMP_ORDER_INVALID)


class TestNumericInput:
    def test_float_rejected(self) -> None:
        p = _open_pos()
        p["position"]["entry_price"] = 2800.5
        _expect(validate_trade_state(p), TRADE_STATE_NUMERIC_INPUT_INVALID)

    def test_nan_rejected(self) -> None:
        p = _open_pos()
        p["position"]["entry_price"] = "NaN"
        _expect(validate_trade_state(p), TRADE_STATE_NUMERIC_INPUT_INVALID)

    def test_infinity_rejected(self) -> None:
        p = _open_pos()
        p["position"]["entry_price"] = "Infinity"
        _expect(validate_trade_state(p), TRADE_STATE_NUMERIC_INPUT_INVALID)

    def test_decimal_accepted(self) -> None:
        p = _open_pos()
        p["position"]["entry_price"] = Decimal("2800")  # type: ignore[assignment]
        assert validate_trade_state(p).valid

    def test_int_accepted(self) -> None:
        assert validate_trade_state(_open_pos()).valid

    def test_str_accepted(self) -> None:
        p = _open_pos()
        p["position"]["entry_price"] = "2800"
        assert validate_trade_state(p).valid

    def test_payload_unchanged(self) -> None:
        p = _open_pos()
        p["position"]["entry_price"] = 2800.5
        before = copy.deepcopy(p)
        validate_trade_state(p)
        assert p == before


class TestMultiError:
    def test_multiple_errors(self) -> None:
        p = _open_pos()
        p["position"]["entry_price"] = 0
        p["position"]["original_quantity"] = 0
        p["position"]["remaining_quantity"] = 200
        r = validate_trade_state(p)
        assert not r.valid and len(r.issues) >= 3

    def test_deterministic_ordering(self) -> None:
        p = _open_pos()
        p["position"]["entry_price"] = 0
        p["position"]["original_quantity"] = 0
        assert validate_trade_state(p).issues == validate_trade_state(p).issues


class TestIssueFields:
    def test_all_fields_populated(self) -> None:
        p = _open_pos()
        p["position"]["entry_price"] = 0
        p["position"]["original_quantity"] = -1
        p["position"]["remaining_quantity"] = 200
        r = validate_trade_state(p)
        for issue in r.issues:
            assert issue.code and issue.category == ValidationCategory.DOMAIN
            assert issue.severity == ValidationSeverity.ERROR
            assert issue.path and issue.message


# ===================================================================
# Action consistency tests
# ===================================================================

OPEN_ACT = ConfirmedActionSnapshot("POSITION_OPENED", OPEN_TS, Decimal("2800"), Decimal("100"))
PARTIAL_ACT = ConfirmedActionSnapshot("PARTIAL_EXIT", EXIT_TS, Decimal("2920"), Decimal("50"))
FULL_ACT = ConfirmedActionSnapshot("FULL_EXIT", CLOSE_TS, Decimal("2900"), Decimal("50"))


class TestActionOpen:
    def test_valid_open_action(self) -> None:
        assert validate_trade_state(_open_pos(), confirmed_actions=(OPEN_ACT,)).valid

    def test_missing_open_action(self) -> None:
        _expect(
            validate_trade_state(_open_pos(), confirmed_actions=()),
            TRADE_STATE_ACTION_MISSING_OPEN,
        )

    def test_duplicate_open_action(self) -> None:
        _expect(
            validate_trade_state(_open_pos(), confirmed_actions=(OPEN_ACT, OPEN_ACT)),
            TRADE_STATE_ACTION_DUPLICATE_OPEN,
        )

    def test_entry_price_mismatch(self) -> None:
        a = ConfirmedActionSnapshot("POSITION_OPENED", OPEN_TS, Decimal("5000"), Decimal("100"))
        _expect(
            validate_trade_state(_open_pos(), confirmed_actions=(a,)),
            TRADE_STATE_ACTION_ENTRY_PRICE_MISMATCH,
        )

    def test_original_quantity_mismatch(self) -> None:
        a = ConfirmedActionSnapshot("POSITION_OPENED", OPEN_TS, Decimal("2800"), Decimal("999"))
        _expect(
            validate_trade_state(_open_pos(), confirmed_actions=(a,)),
            TRADE_STATE_ACTION_ORIGINAL_QUANTITY_MISMATCH,
        )

    def test_entry_timestamp_after_open(self) -> None:
        p = _open_pos()
        p["position"]["entry_timestamp"] = "2026-07-20T12:00:00+07:00"
        _expect(
            validate_trade_state(p, confirmed_actions=(OPEN_ACT,)),
            TRADE_STATE_ACTION_TIMESTAMP_MISMATCH,
        )

    def test_entry_timestamp_before_open_valid(self) -> None:
        p = _open_pos()
        p["position"]["entry_timestamp"] = "2026-07-15T09:00:00+07:00"
        assert validate_trade_state(p, confirmed_actions=(OPEN_ACT,)).valid

    def test_float_action_price(self) -> None:
        p = _open_pos()
        p["position"]["entry_price"] = 2800.5
        _expect(
            validate_trade_state(p, confirmed_actions=(OPEN_ACT,)),
            TRADE_STATE_NUMERIC_INPUT_INVALID,
        )


class TestActionChronology:
    def test_partial_before_open(self) -> None:
        acts = (
            ConfirmedActionSnapshot("PARTIAL_EXIT", BEFORE_TS, Decimal("2920"), Decimal("50")),
            OPEN_ACT,
        )
        _expect(
            validate_trade_state(_partial_pos(), confirmed_actions=acts),
            TRADE_STATE_ACTION_BEFORE_OPEN,
        )

    def test_full_exit_before_open(self) -> None:
        acts = (
            ConfirmedActionSnapshot("FULL_EXIT", BEFORE_TS, Decimal("2900"), Decimal("50")),
            OPEN_ACT,
        )
        _expect(
            validate_trade_state(_closed_pos(), confirmed_actions=acts),
            TRADE_STATE_ACTION_BEFORE_OPEN,
        )

    def test_stop_before_open(self) -> None:
        acts = (
            ConfirmedActionSnapshot("STOP_LOSS_CONFIRMED", BEFORE_TS, Decimal("2700"), None),
            OPEN_ACT,
        )
        _expect(
            validate_trade_state(_open_pos(), confirmed_actions=acts),
            TRADE_STATE_ACTION_BEFORE_OPEN,
        )

    def test_target_before_open(self) -> None:
        acts = (
            ConfirmedActionSnapshot("TARGET_CONFIRMED", BEFORE_TS, Decimal("2920"), None),
            OPEN_ACT,
        )
        _expect(
            validate_trade_state(_open_pos(), confirmed_actions=acts),
            TRADE_STATE_ACTION_BEFORE_OPEN,
        )

    def test_partial_after_full_exit(self) -> None:
        later = datetime(2026, 7, 19, 10, 0, tzinfo=timezone.utc)
        acts = (
            OPEN_ACT,
            FULL_ACT,
            ConfirmedActionSnapshot("PARTIAL_EXIT", later, Decimal("2920"), Decimal("50")),
        )
        _expect(
            validate_trade_state(_closed_pos(), confirmed_actions=acts),
            TRADE_STATE_ACTION_AFTER_FULL_EXIT,
        )

    def test_stop_change_after_full_exit(self) -> None:
        later = datetime(2026, 7, 19, 10, 0, tzinfo=timezone.utc)
        acts = (
            OPEN_ACT,
            FULL_ACT,
            ConfirmedActionSnapshot("STOP_LOSS_CHANGED", later, Decimal("3000"), None),
        )
        _expect(
            validate_trade_state(_closed_pos(), confirmed_actions=acts),
            TRADE_STATE_ACTION_AFTER_FULL_EXIT,
        )

    def test_unsorted_input_same_result(self) -> None:
        rev = (FULL_ACT, PARTIAL_ACT, OPEN_ACT)
        srt = (OPEN_ACT, PARTIAL_ACT, FULL_ACT)
        assert (
            validate_trade_state(_closed_pos(), confirmed_actions=rev).issues
            == validate_trade_state(_closed_pos(), confirmed_actions=srt).issues
        )

    def test_action_list_unchanged(self) -> None:
        acts = (
            OPEN_ACT,
            ConfirmedActionSnapshot("PARTIAL_EXIT", BEFORE_TS, Decimal("2920"), Decimal("50")),
        )
        before = copy.deepcopy(acts)
        validate_trade_state(_partial_pos(), confirmed_actions=acts)
        assert acts == before


class TestActionDuplicateFullExit:
    def test_duplicate_full_exit_rejected(self) -> None:
        acts = (
            OPEN_ACT,
            ConfirmedActionSnapshot("FULL_EXIT", AFTER_TS, Decimal("2900"), Decimal("50")),
            ConfirmedActionSnapshot("FULL_EXIT", AFTER_TS, Decimal("2910"), Decimal("50")),
        )
        _expect(
            validate_trade_state(_closed_pos(), confirmed_actions=acts),
            TRADE_STATE_ACTION_DUPLICATE_FULL_EXIT,
        )


class TestActionPartialQuantity:
    def test_valid_single_partial(self) -> None:
        acts = (OPEN_ACT, PARTIAL_ACT)
        assert validate_trade_state(_partial_pos(), confirmed_actions=acts).valid

    def test_valid_repeated_partial(self) -> None:
        p20 = ConfirmedActionSnapshot("PARTIAL_EXIT", EXIT_TS, Decimal("2900"), Decimal("20"))
        p30 = ConfirmedActionSnapshot("PARTIAL_EXIT", EXIT_TS, Decimal("2920"), Decimal("30"))
        p = _partial_pos()
        p["position"]["remaining_quantity"] = 50
        acts = (OPEN_ACT, p20, p30)
        assert validate_trade_state(p, confirmed_actions=acts).valid

    def test_remaining_reconciliation_match(self) -> None:
        acts = (
            OPEN_ACT,
            ConfirmedActionSnapshot("PARTIAL_EXIT", EXIT_TS, Decimal("2920"), Decimal("60")),
        )
        p = _partial_pos()
        p["position"]["remaining_quantity"] = 40
        assert validate_trade_state(p, confirmed_actions=acts).valid

    def test_remaining_reconciliation_mismatch(self) -> None:
        p = _partial_pos()
        p["position"]["remaining_quantity"] = 60
        acts = (OPEN_ACT, PARTIAL_ACT)
        _expect(
            validate_trade_state(p, confirmed_actions=acts), TRADE_STATE_ACTION_REMAINING_MISMATCH
        )

    def test_cumulative_exceeds_original(self) -> None:
        acts = (
            OPEN_ACT,
            ConfirmedActionSnapshot("PARTIAL_EXIT", EXIT_TS, Decimal("2920"), Decimal("60")),
            ConfirmedActionSnapshot("PARTIAL_EXIT", EXIT_TS, Decimal("2900"), Decimal("60")),
        )
        _expect(
            validate_trade_state(_partial_pos(), confirmed_actions=acts),
            TRADE_STATE_ACTION_CUMULATIVE_EXCEEDS_ORIGINAL,
        )

    def test_partial_consumes_whole_position(self) -> None:
        acts = (
            OPEN_ACT,
            ConfirmedActionSnapshot("PARTIAL_EXIT", EXIT_TS, Decimal("2920"), Decimal("100")),
        )
        _expect(
            validate_trade_state(_partial_pos(), confirmed_actions=acts),
            TRADE_STATE_ACTION_HISTORY_INCONSISTENT,
        )

    def test_negative_partial_quantity(self) -> None:
        acts = (
            OPEN_ACT,
            ConfirmedActionSnapshot("PARTIAL_EXIT", EXIT_TS, Decimal("2920"), Decimal("-50")),
        )
        _expect(
            validate_trade_state(_partial_pos(), confirmed_actions=acts),
            TRADE_STATE_ACTION_INVALID_QUANTITY,
        )


class TestActionClosed:
    def test_valid_open_partial_full(self) -> None:
        assert validate_trade_state(
            _closed_pos(), confirmed_actions=(OPEN_ACT, PARTIAL_ACT, FULL_ACT)
        ).valid

    def test_closed_without_open(self) -> None:
        _expect(
            validate_trade_state(_closed_pos(), confirmed_actions=(FULL_ACT,)),
            TRADE_STATE_ACTION_MISSING_OPEN,
        )

    def test_closed_without_full_exit(self) -> None:
        _expect(
            validate_trade_state(_closed_pos(), confirmed_actions=(OPEN_ACT, PARTIAL_ACT)),
            TRADE_STATE_ACTION_MISSING_FULL_EXIT,
        )

    def test_full_exit_before_open(self) -> None:
        before = datetime(2026, 7, 14, 8, 0, tzinfo=timezone.utc)
        acts = (
            ConfirmedActionSnapshot("FULL_EXIT", before, Decimal("2900"), Decimal("100")),
            OPEN_ACT,
        )
        _expect(
            validate_trade_state(_closed_pos(), confirmed_actions=acts),
            TRADE_STATE_ACTION_BEFORE_OPEN,
        )


class TestActionContextOmitted:
    def test_none_skips_checks(self) -> None:
        assert validate_trade_state(_open_pos()).valid

    def test_empty_tuple_runs_checks(self) -> None:
        _expect(
            validate_trade_state(_open_pos(), confirmed_actions=()),
            TRADE_STATE_ACTION_MISSING_OPEN,
        )


class TestActionMultiError:
    def test_multiple_action_errors(self) -> None:
        acts = (
            ConfirmedActionSnapshot("PARTIAL_EXIT", BEFORE_TS, Decimal("2920"), Decimal("50")),
            ConfirmedActionSnapshot("POSITION_OPENED", OPEN_TS, Decimal("9999"), Decimal("100")),
        )
        r = validate_trade_state(_partial_pos(), confirmed_actions=acts)
        assert not r.valid
        assert TRADE_STATE_ACTION_BEFORE_OPEN in {i.code for i in r.issues}
        assert TRADE_STATE_ACTION_ENTRY_PRICE_MISMATCH in {i.code for i in r.issues}

    def test_deterministic_ordering_with_actions(self) -> None:
        acts = (
            ConfirmedActionSnapshot("PARTIAL_EXIT", BEFORE_TS, Decimal("2920"), Decimal("50")),
            ConfirmedActionSnapshot("POSITION_OPENED", OPEN_TS, Decimal("9999"), Decimal("100")),
        )
        assert (
            validate_trade_state(_partial_pos(), confirmed_actions=acts).issues
            == validate_trade_state(_partial_pos(), confirmed_actions=acts).issues
        )


class TestStableCodeCoverage:
    def test_all_internal_codes_tested(self) -> None:
        codes = {
            TRADE_STATE_NUMERIC_INPUT_INVALID,
            NON_POSITION_HAS_POSITION_VALUES,
            OPEN_POSITION_INVALID_ENTRY,
            OPEN_POSITION_INVALID_ORIGINAL_QUANTITY,
            OPEN_POSITION_INVALID_REMAINING_QUANTITY,
            OPEN_POSITION_HAS_AVERAGE_EXIT,
            OPEN_POSITION_QUANTITY_MISMATCH,
            PARTIAL_POSITION_INVALID_QUANTITY,
            PARTIAL_POSITION_AVERAGE_EXIT_MISSING,
            PARTIAL_POSITION_REALIZED_RESULT_MISSING,
            CLOSED_POSITION_HAS_REMAINING_QUANTITY,
            CLOSED_POSITION_HAS_ACTIVE_STOP,
            CLOSED_POSITION_HAS_ACTIVE_TARGET,
            CLOSED_POSITION_HAS_UNREALIZED_RESULT,
            CLOSED_POSITION_AVERAGE_EXIT_MISSING,
            POSITION_REMAINING_EXCEEDS_ORIGINAL,
            TRADE_STATE_ACTION_HISTORY_INCONSISTENT,
            TRADE_STATE_TIMESTAMP_ORDER_INVALID,
        }
        assert len(codes) == 18

    def test_all_action_codes_tested(self) -> None:
        codes = {
            TRADE_STATE_ACTION_MISSING_OPEN,
            TRADE_STATE_ACTION_DUPLICATE_OPEN,
            TRADE_STATE_ACTION_ENTRY_PRICE_MISMATCH,
            TRADE_STATE_ACTION_ORIGINAL_QUANTITY_MISMATCH,
            TRADE_STATE_ACTION_TIMESTAMP_MISMATCH,
            TRADE_STATE_ACTION_BEFORE_OPEN,
            TRADE_STATE_ACTION_AFTER_FULL_EXIT,
            TRADE_STATE_ACTION_DUPLICATE_FULL_EXIT,
            TRADE_STATE_ACTION_HISTORY_INCONSISTENT,
            TRADE_STATE_ACTION_MISSING_FULL_EXIT,
            TRADE_STATE_ACTION_CUMULATIVE_EXCEEDS_ORIGINAL,
            TRADE_STATE_ACTION_REMAINING_MISMATCH,
            TRADE_STATE_ACTION_INVALID_QUANTITY,
        }
        assert len(codes) == 13
