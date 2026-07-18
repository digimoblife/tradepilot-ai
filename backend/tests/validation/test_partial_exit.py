"""Tests for Partial Exit Validator (TP-0309)."""

from __future__ import annotations

import copy
from decimal import Decimal as Decimal

from app.validation.partial_exit import (
    PARTIAL_EXIT_AVERAGE_EXIT_MISMATCH,
    PARTIAL_EXIT_CLOSES_FULL_POSITION,
    PARTIAL_EXIT_NUMERIC_INPUT_INVALID,
    PARTIAL_EXIT_PREVIOUS_STATE_INVALID,
    PARTIAL_EXIT_QUANTITY_INVALID,
    PARTIAL_EXIT_QUANTITY_MISMATCH,
    PARTIAL_EXIT_REALIZED_PROFIT_LOSS_MISMATCH,
    PARTIAL_EXIT_RESULTING_STATUS_INVALID,
    PartialExitValidationResult,
    validate_partial_exit,
)


def _expect(result: PartialExitValidationResult, code: str) -> None:
    assert not result.valid, f"Expected {code} but result is valid"
    codes = {i.code for i in result.issues}
    assert code in codes, f"Expected code {code!r} not in {codes}"


OPEN_PREV = {
    "entry_price": 2800,
    "remaining_quantity": 100,
    "position_status": "OPEN",
    "realized_pnl": None,
    "average_exit_price": None,
}

EXIT_40 = {
    "exit_quantity": 40,
    "exit_price": 2920,
}

RESULT_60 = {
    "remaining_quantity": 60,
    "realized_pnl": 4800,
    "average_exit_price": 2920,
    "position_status": "PARTIALLY_CLOSED",
}

PARTIAL_PREV = {
    "entry_price": 2800,
    "remaining_quantity": 60,
    "position_status": "PARTIALLY_CLOSED",
    "realized_pnl": 4800,
    "average_exit_price": 2920,
}

EXIT_30 = {
    "exit_quantity": 30,
    "exit_price": 2900,
}

# Weighted avg: (40*2920 + 30*2900) / 70 = 203800/70
AVG_30 = Decimal("203800") / Decimal("70")

RESULT_30 = {
    "remaining_quantity": 30,
    "realized_pnl": 7800,
    "average_exit_price": AVG_30,
    "position_status": "PARTIALLY_CLOSED",
}

PREV_EXIT_40 = {"exit_quantity": 40, "exit_price": 2920}


# ===================================================================


class TestFirstPartialExit:
    def test_valid(self) -> None:
        r = validate_partial_exit(OPEN_PREV, EXIT_40, RESULT_60)
        assert r.valid

    def test_quantity_conservation_mismatch(self) -> None:
        r = validate_partial_exit(
            OPEN_PREV,
            EXIT_40,
            {
                "remaining_quantity": 50,
                "realized_pnl": 4800,
                "average_exit_price": 2920,
                "position_status": "PARTIALLY_CLOSED",
            },
        )
        _expect(r, PARTIAL_EXIT_QUANTITY_MISMATCH)

    def test_remaining_zero_rejected(self) -> None:
        r = validate_partial_exit(
            OPEN_PREV,
            {"exit_quantity": 100, "exit_price": 2920},
            {
                "remaining_quantity": 0,
                "realized_pnl": 12000,
                "average_exit_price": 2920,
                "position_status": "PARTIALLY_CLOSED",
            },
        )
        _expect(r, PARTIAL_EXIT_CLOSES_FULL_POSITION)

    def test_exit_equal_remaining_rejected(self) -> None:
        r = validate_partial_exit(
            OPEN_PREV,
            {"exit_quantity": 100, "exit_price": 2920},
            {
                "remaining_quantity": 0,
                "realized_pnl": 12000,
                "average_exit_price": 2920,
                "position_status": "PARTIALLY_CLOSED",
            },
        )
        _expect(r, PARTIAL_EXIT_CLOSES_FULL_POSITION)

    def test_exit_above_remaining_rejected(self) -> None:
        r = validate_partial_exit(
            OPEN_PREV,
            {"exit_quantity": 200, "exit_price": 2920},
            {
                "remaining_quantity": -100,
                "realized_pnl": 12000,
                "average_exit_price": 2920,
                "position_status": "PARTIALLY_CLOSED",
            },
        )
        _expect(r, PARTIAL_EXIT_CLOSES_FULL_POSITION)

    def test_zero_exit_rejected(self) -> None:
        r = validate_partial_exit(
            OPEN_PREV,
            {"exit_quantity": 0, "exit_price": 2920},
            {
                "remaining_quantity": 100,
                "realized_pnl": 0,
                "average_exit_price": 2920,
                "position_status": "PARTIALLY_CLOSED",
            },
        )
        _expect(r, PARTIAL_EXIT_QUANTITY_INVALID)


class TestPreviousState:
    def test_not_opened_rejected(self) -> None:
        r = validate_partial_exit(
            {
                "entry_price": None,
                "remaining_quantity": None,
                "position_status": "NOT_OPENED",
                "realized_pnl": None,
                "average_exit_price": None,
            },
            EXIT_40,
            RESULT_60,
        )
        _expect(r, PARTIAL_EXIT_PREVIOUS_STATE_INVALID)

    def test_closed_rejected(self) -> None:
        r = validate_partial_exit(
            {
                "entry_price": 2800,
                "remaining_quantity": 0,
                "position_status": "CLOSED",
                "realized_pnl": 11000,
                "average_exit_price": 2910,
            },
            EXIT_40,
            RESULT_60,
        )
        _expect(r, PARTIAL_EXIT_PREVIOUS_STATE_INVALID)

    def test_open_valid(self) -> None:
        assert validate_partial_exit(OPEN_PREV, EXIT_40, RESULT_60).valid

    def test_partially_closed_valid(self) -> None:
        assert validate_partial_exit(
            PARTIAL_PREV, EXIT_30, RESULT_30, previous_exits=[PREV_EXIT_40]
        ).valid


class TestRealizedPnl:
    def test_profitable(self) -> None:
        assert validate_partial_exit(OPEN_PREV, EXIT_40, RESULT_60).valid

    def test_losing(self) -> None:
        r = validate_partial_exit(
            OPEN_PREV,
            {"exit_quantity": 40, "exit_price": 2700},
            {
                "remaining_quantity": 60,
                "realized_pnl": -4000,
                "average_exit_price": 2700,
                "position_status": "PARTIALLY_CLOSED",
            },
        )
        assert r.valid

    def test_zero_result(self) -> None:
        r = validate_partial_exit(
            OPEN_PREV,
            {"exit_quantity": 40, "exit_price": 2800},
            {
                "remaining_quantity": 60,
                "realized_pnl": 0,
                "average_exit_price": 2800,
                "position_status": "PARTIALLY_CLOSED",
            },
        )
        assert r.valid

    def test_mismatch(self) -> None:
        r = validate_partial_exit(
            OPEN_PREV,
            EXIT_40,
            {
                "remaining_quantity": 60,
                "realized_pnl": 9999,
                "average_exit_price": 2920,
                "position_status": "PARTIALLY_CLOSED",
            },
        )
        _expect(r, PARTIAL_EXIT_REALIZED_PROFIT_LOSS_MISMATCH)


class TestResultingStatus:
    def test_wrong_status_rejected(self) -> None:
        r = validate_partial_exit(
            OPEN_PREV,
            EXIT_40,
            {
                "remaining_quantity": 60,
                "realized_pnl": 4800,
                "average_exit_price": 2920,
                "position_status": "OPEN",
            },
        )
        _expect(r, PARTIAL_EXIT_RESULTING_STATUS_INVALID)


class TestRepeatedPartialExit:
    def test_valid_second_exit(self) -> None:
        r = validate_partial_exit(PARTIAL_PREV, EXIT_30, RESULT_30, previous_exits=[PREV_EXIT_40])
        assert r.valid

    def test_weighted_average_mismatch(self) -> None:
        r = validate_partial_exit(
            PARTIAL_PREV,
            EXIT_30,
            {
                "remaining_quantity": 30,
                "realized_pnl": 7800,
                "average_exit_price": 9999,
                "position_status": "PARTIALLY_CLOSED",
            },
            previous_exits=[PREV_EXIT_40],
        )
        _expect(r, PARTIAL_EXIT_AVERAGE_EXIT_MISMATCH)

    def test_cumulative_realized_mismatch(self) -> None:
        r = validate_partial_exit(
            PARTIAL_PREV,
            EXIT_30,
            {
                "remaining_quantity": 30,
                "realized_pnl": 9999,
                "average_exit_price": 2912,
                "position_status": "PARTIALLY_CLOSED",
            },
            previous_exits=[PREV_EXIT_40],
        )
        _expect(r, PARTIAL_EXIT_REALIZED_PROFIT_LOSS_MISMATCH)


class TestDecimalInput:
    def test_float_rejected(self) -> None:
        p = dict(OPEN_PREV)
        p["entry_price"] = 2800.5
        r = validate_partial_exit(p, EXIT_40, RESULT_60)
        _expect(r, PARTIAL_EXIT_NUMERIC_INPUT_INVALID)


class TestImmutability:
    def test_all_inputs_unchanged(self) -> None:
        prev = copy.deepcopy(OPEN_PREV)
        exit_ = dict(EXIT_40)
        result = dict(RESULT_60)
        before_prev = copy.deepcopy(prev)
        before_exit = copy.deepcopy(exit_)
        before_result = copy.deepcopy(result)
        validate_partial_exit(prev, exit_, result)
        assert prev == before_prev
        assert exit_ == before_exit
        assert result == before_result


class TestMultiError:
    def test_multiple_errors(self) -> None:
        r = validate_partial_exit(
            OPEN_PREV,
            {"exit_quantity": -5, "exit_price": 2920},
            {
                "remaining_quantity": -5,
                "realized_pnl": 9999,
                "average_exit_price": 2920,
                "position_status": "OPEN",
            },
        )
        assert not r.valid
        assert len(r.issues) >= 2

    def test_deterministic_ordering(self) -> None:
        p = dict(OPEN_PREV)
        p["remaining_quantity"] = None
        r1 = validate_partial_exit(p, EXIT_40, RESULT_60)
        r2 = validate_partial_exit(p, EXIT_40, RESULT_60)
        assert r1.issues == r2.issues
