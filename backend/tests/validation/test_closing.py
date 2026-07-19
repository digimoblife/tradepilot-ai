"""Tests for Closing Validator (TP-0310)."""

from __future__ import annotations

import copy
from decimal import Decimal

from app.validation.closing import (
    CLOSING_FINAL_EXIT_QUANTITY_MISMATCH,
    CLOSING_GROSS_RESULT_MISMATCH,
    CLOSING_NET_RESULT_MISMATCH,
    CLOSING_NUMERIC_INPUT_INVALID,
    CLOSING_REASON_STATUS_MISMATCH,
    CLOSING_REMAINING_NOT_ZERO,
    CLOSING_TOTAL_EXIT_QUANTITY_MISMATCH,
    CLOSING_WEIGHTED_EXIT_MISMATCH,
    ClosingValidationResult,
    validate_closing,
)
from app.validation.timeline import CLOSING_TIMELINE_INVALID

# fmt: off

def _expect(result: ClosingValidationResult, code: str) -> None:
    assert not result.valid, f"Expected {code} but result is valid"
    codes = {i.code for i in result.issues}
    assert code in codes, f"Expected code {code!r} not in {codes}"


OPEN_PREV = {
    "entry_price": 2800,
    "original_quantity": 100,
    "remaining_quantity": 100,
    "position_status": "OPEN",
    "realized_pnl": None,
    "average_exit_price": None,
}

FULL_EXIT = {
    "final_exit_quantity": 100,
    "final_exit_price": 2910,
}

RESULT = {
    "entry_price": 2800,
    "original_quantity": 100,
    "average_exit_price": 2910,
    "gross_profit_loss": 11000,
    "fees": None,
    "taxes": None,
    "net_profit_loss": 11000,
}

CLOSED_RESULT = {
    **RESULT,
    "remaining_quantity": 0,
    "closed_at": "2026-07-17T15:30:00+07:00",
}

PARTIAL_PREV = {
    "entry_price": 2800,
    "original_quantity": 100,
    "remaining_quantity": 50,
    "position_status": "PARTIALLY_CLOSED",
    "realized_pnl": 6000,
    "average_exit_price": 2920,
}

FINAL_50 = {
    "final_exit_quantity": 50,
    "final_exit_price": 2900,
}

PARTIAL_EXIT_50 = {"exit_quantity": 50, "exit_price": 2920}

AVG_2910 = Decimal("2910")


# ===================================================================


class TestFinalExitQuantity:
    def test_valid(self) -> None:
        assert validate_closing(OPEN_PREV, FULL_EXIT, CLOSED_RESULT).valid

    def test_below_remaining(self) -> None:
        r = validate_closing(OPEN_PREV, {**FULL_EXIT, "final_exit_quantity": 50}, CLOSED_RESULT)
        _expect(r, CLOSING_FINAL_EXIT_QUANTITY_MISMATCH)

    def test_above_remaining(self) -> None:
        r = validate_closing(OPEN_PREV, {**FULL_EXIT, "final_exit_quantity": 150}, CLOSED_RESULT)
        _expect(r, CLOSING_FINAL_EXIT_QUANTITY_MISMATCH)

    def test_zero_exit(self) -> None:
        r = validate_closing(OPEN_PREV, {**FULL_EXIT, "final_exit_quantity": 0}, CLOSED_RESULT)
        _expect(r, CLOSING_FINAL_EXIT_QUANTITY_MISMATCH)


class TestResultingRemaining:
    def test_zero_valid(self) -> None:
        p = {**CLOSED_RESULT, "remaining_quantity": 0}
        assert validate_closing(OPEN_PREV, FULL_EXIT, p).valid

    def test_non_zero_invalid(self) -> None:
        r = validate_closing(OPEN_PREV, FULL_EXIT, {**CLOSED_RESULT, "remaining_quantity": 50})
        _expect(r, CLOSING_REMAINING_NOT_ZERO)


class TestTotalExitQuantity:
    def test_one_step(self) -> None:
        assert validate_closing(OPEN_PREV, FULL_EXIT, CLOSED_RESULT).valid

    def test_partial_plus_final(self) -> None:
        r = validate_closing(PARTIAL_PREV, FINAL_50, {
            **CLOSED_RESULT, "average_exit_price": AVG_2910,
        }, previous_exits=[PARTIAL_EXIT_50])
        assert r.valid

    def test_total_below_original(self) -> None:
        r = validate_closing(OPEN_PREV, {**FULL_EXIT, "final_exit_quantity": 50}, CLOSED_RESULT)
        _expect(r, CLOSING_TOTAL_EXIT_QUANTITY_MISMATCH)

    def test_total_above_original(self) -> None:
        r = validate_closing(OPEN_PREV, {**FULL_EXIT, "final_exit_quantity": 150}, CLOSED_RESULT)
        _expect(r, CLOSING_TOTAL_EXIT_QUANTITY_MISMATCH)


class TestWeightedExit:
    def test_one_step(self) -> None:
        assert validate_closing(OPEN_PREV, FULL_EXIT, CLOSED_RESULT).valid

    def test_partial_plus_final(self) -> None:
        r = validate_closing(PARTIAL_PREV, FINAL_50, {
            **CLOSED_RESULT, "average_exit_price": AVG_2910,
        }, previous_exits=[PARTIAL_EXIT_50])
        assert r.valid

    def test_mismatch(self) -> None:
        r = validate_closing(OPEN_PREV, FULL_EXIT, {
            **CLOSED_RESULT, "average_exit_price": Decimal("9999"),
        })
        _expect(r, CLOSING_WEIGHTED_EXIT_MISMATCH)


class TestGrossResult:
    def test_profitable(self) -> None:
        assert validate_closing(OPEN_PREV, FULL_EXIT, CLOSED_RESULT).valid

    def test_losing(self) -> None:
        r = validate_closing(OPEN_PREV, {"final_exit_quantity": 100, "final_exit_price": 2700}, {
            **CLOSED_RESULT, "average_exit_price": 2700,
            "gross_profit_loss": -10000, "net_profit_loss": -10000,
        })
        assert r.valid

    def test_break_even(self) -> None:
        r = validate_closing(OPEN_PREV, {"final_exit_quantity": 100, "final_exit_price": 2800}, {
            **CLOSED_RESULT, "average_exit_price": 2800,
            "gross_profit_loss": 0, "net_profit_loss": 0,
        })
        assert r.valid

    def test_mismatch(self) -> None:
        r = validate_closing(OPEN_PREV, FULL_EXIT, {**CLOSED_RESULT, "gross_profit_loss": 999})
        _expect(r, CLOSING_GROSS_RESULT_MISMATCH)


class TestNetResult:
    def test_zero_fees(self) -> None:
        assert validate_closing(OPEN_PREV, FULL_EXIT, CLOSED_RESULT).valid

    def test_with_fees(self) -> None:
        r = validate_closing(OPEN_PREV, FULL_EXIT, {
            **CLOSED_RESULT, "fees": 250, "net_profit_loss": 10750,
        })
        assert r.valid

    def test_mismatch(self) -> None:
        r = validate_closing(OPEN_PREV, FULL_EXIT, {**CLOSED_RESULT, "net_profit_loss": 999})
        _expect(r, CLOSING_NET_RESULT_MISMATCH)


class TestTimeline:
    def test_valid(self) -> None:
        r = validate_closing(
            {**OPEN_PREV, "entry_timestamp": "2026-07-15T10:12:00+07:00"},
            {**FULL_EXIT, "exit_timestamp": "2026-07-17T15:12:00+07:00"},
            {**CLOSED_RESULT, "closed_at": "2026-07-17T15:30:00+07:00"},
        )
        assert r.valid

    def test_final_exit_before_entry(self) -> None:
        r = validate_closing(
            {**OPEN_PREV, "entry_timestamp": "2026-07-17T15:12:00+07:00"},
            {**FULL_EXIT, "exit_timestamp": "2026-07-15T10:12:00+07:00"},
            CLOSED_RESULT,
        )
        _expect(r, CLOSING_TIMELINE_INVALID)


class TestClosingReason:
    def test_valid_mapping(self) -> None:
        r = validate_closing(OPEN_PREV, FULL_EXIT, CLOSED_RESULT,
                             closing_reason="TAKE_PROFIT",
                             resulting_session_status="CLOSED_TAKE_PROFIT")
        assert r.valid

    def test_stop_loss_mapping(self) -> None:
        r = validate_closing(OPEN_PREV, FULL_EXIT, CLOSED_RESULT,
                             closing_reason="STOP_LOSS",
                             resulting_session_status="CLOSED_STOP_LOSS")
        assert r.valid

    def test_manual_exit_mapping(self) -> None:
        r = validate_closing(OPEN_PREV, FULL_EXIT, CLOSED_RESULT,
                             closing_reason="MANUAL_EXIT",
                             resulting_session_status="CLOSED_MANUAL")
        assert r.valid

    def test_thesis_invalidated_mapping(self) -> None:
        r = validate_closing(OPEN_PREV, FULL_EXIT, CLOSED_RESULT,
                             closing_reason="THESIS_INVALIDATED",
                             resulting_session_status="CLOSED_MANUAL")
        assert r.valid

    def test_invalid_mapping(self) -> None:
        r = validate_closing(OPEN_PREV, FULL_EXIT, CLOSED_RESULT,
                             closing_reason="TAKE_PROFIT",
                             resulting_session_status="CLOSED_STOP_LOSS")
        _expect(r, CLOSING_REASON_STATUS_MISMATCH)


class TestNumericInput:
    def test_float_rejected(self) -> None:
        r = validate_closing(
            {**OPEN_PREV, "entry_price": 2800.5}, FULL_EXIT, CLOSED_RESULT,
        )
        _expect(r, CLOSING_NUMERIC_INPUT_INVALID)


class TestImmutability:
    def test_all_inputs_unchanged(self) -> None:
        prev, exit_, result = copy.deepcopy(OPEN_PREV), dict(FULL_EXIT), dict(CLOSED_RESULT)
        b_p, b_e, b_r = copy.deepcopy(prev), copy.deepcopy(exit_), copy.deepcopy(result)
        validate_closing(prev, exit_, result)
        assert prev == b_p and exit_ == b_e and result == b_r


class TestMultiError:
    def test_multiple_errors(self) -> None:
        r = validate_closing(
            {**OPEN_PREV, "entry_price": 0, "original_quantity": 0},
            {**FULL_EXIT, "final_exit_quantity": -5},
            {**CLOSED_RESULT, "gross_profit_loss": 999, "net_profit_loss": 999},
        )
        assert not r.valid and len(r.issues) >= 2

    def test_deterministic_ordering(self) -> None:
        p = {**OPEN_PREV, "remaining_quantity": None}
        r1 = validate_closing(p, FULL_EXIT, CLOSED_RESULT)
        r2 = validate_closing(p, FULL_EXIT, CLOSED_RESULT)
        assert r1.issues == r2.issues
