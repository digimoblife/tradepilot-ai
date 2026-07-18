"""Tests for exit calculations."""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

from app.calculations.decimal_utils import CurrencyCode
from app.calculations.exits import (
    ExitFill,
    calculate_gross_closing_pnl,
    calculate_gross_closing_result,
    calculate_net_closing_pnl,
    calculate_net_closing_result,
    calculate_partial_realized_pnl,
    calculate_sum_realized_pnl,
    calculate_weighted_average_exit,
)
from app.calculations.models import ClosingResult


class TestPartialRealizedPnl:
    def test_profitable_exit(self) -> None:
        result = calculate_partial_realized_pnl(
            Decimal("2920"),
            Decimal("2800"),
            Decimal("50"),
        )
        assert result == Decimal("6000")

    def test_losing_exit(self) -> None:
        result = calculate_partial_realized_pnl(
            Decimal("2700"),
            Decimal("2800"),
            Decimal("50"),
        )
        assert result == Decimal("-5000")

    def test_zero_quantity(self) -> None:
        result = calculate_partial_realized_pnl(
            Decimal("2920"),
            Decimal("2800"),
            Decimal("0"),
        )
        assert result == Decimal("0")

    def test_usd_precision(self) -> None:
        result = calculate_partial_realized_pnl(
            Decimal("15.80"),
            Decimal("14.50"),
            Decimal("20"),
            currency=CurrencyCode.USD,
        )
        assert result == Decimal("26.00")


class TestSumRealizedPnl:
    def test_two_fills(self) -> None:
        fills = (
            ExitFill(Decimal("2920"), Decimal("50")),
            ExitFill(Decimal("2900"), Decimal("50")),
        )
        result = calculate_sum_realized_pnl(Decimal("2800"), fills)
        assert result == Decimal("11000")

    def test_profit_and_loss(self) -> None:
        fills = (
            ExitFill(Decimal("3000"), Decimal("50")),
            ExitFill(Decimal("2600"), Decimal("50")),
        )
        result = calculate_sum_realized_pnl(Decimal("2800"), fills)
        # (200*50) + (-200*50) = 10000 - 10000 = 0
        assert result == Decimal("0")

    def test_single_fill(self) -> None:
        fills = (ExitFill(Decimal("2920"), Decimal("100")),)
        result = calculate_sum_realized_pnl(Decimal("2800"), fills)
        assert result == Decimal("12000")

    def test_no_fills(self) -> None:
        result = calculate_sum_realized_pnl(Decimal("2800"), ())
        assert result == Decimal("0")


class TestWeightedAverageExit:
    def test_two_equal_fills(self) -> None:
        fills = (
            ExitFill(Decimal("2920"), Decimal("50")),
            ExitFill(Decimal("2900"), Decimal("50")),
        )
        result = calculate_weighted_average_exit(fills)
        assert result == Decimal("2910")

    def test_single_fill(self) -> None:
        fills = (ExitFill(Decimal("3000"), Decimal("100")),)
        result = calculate_weighted_average_exit(fills)
        assert result == Decimal("3000")

    def test_uneven_quantities(self) -> None:
        fills = (
            ExitFill(Decimal("1000"), Decimal("10")),
            ExitFill(Decimal("2000"), Decimal("20")),
        )
        result = calculate_weighted_average_exit(fills)
        # (1000*10 + 2000*20) / 30 = 50000/30 = 1666.666666... (repeating)
        # No quantization applied to weighted exit; raw Decimal precision
        assert result is not None
        assert result == Decimal("50000") / Decimal("30")

    def test_zero_total_quantity(self) -> None:
        fills = (
            ExitFill(Decimal("1000"), Decimal("0")),
            ExitFill(Decimal("2000"), Decimal("0")),
        )
        assert calculate_weighted_average_exit(fills) is None

    def test_input_order_independence(self) -> None:
        fills_a = (
            ExitFill(Decimal("2920"), Decimal("50")),
            ExitFill(Decimal("2900"), Decimal("50")),
        )
        fills_b = (
            ExitFill(Decimal("2900"), Decimal("50")),
            ExitFill(Decimal("2920"), Decimal("50")),
        )
        assert calculate_weighted_average_exit(fills_a) == calculate_weighted_average_exit(fills_b)


class TestInputImmutability:
    def test_fills_not_mutated(self) -> None:
        fills = (
            ExitFill(Decimal("2920"), Decimal("50")),
            ExitFill(Decimal("2900"), Decimal("50")),
        )
        before = deepcopy(fills)
        calculate_weighted_average_exit(fills)
        calculate_sum_realized_pnl(Decimal("2800"), fills)
        assert fills == before


class TestGrossClosingPnl:
    def test_bbri_fixture(self) -> None:
        result = calculate_gross_closing_pnl(
            Decimal("2800"),
            Decimal("100"),
            Decimal("2910"),
        )
        assert result == Decimal("11000")


class TestNetClosingPnl:
    def test_no_fees(self) -> None:
        result = calculate_net_closing_pnl(
            Decimal("11000"),
            Decimal("0"),
            Decimal("0"),
        )
        assert result == Decimal("11000")

    def test_with_fees(self) -> None:
        result = calculate_net_closing_pnl(
            Decimal("11000"),
            Decimal("500"),
            Decimal("100"),
        )
        assert result == Decimal("10400")

    def test_idr_rounding(self) -> None:
        result = calculate_net_closing_pnl(
            Decimal("11000.50"),
            Decimal("100.50"),
        )
        assert result == Decimal("10900")


class TestGrossClosingResult:
    def test_bbri_fixture(self) -> None:
        proceeds, cost_basis, gross_pnl, weighted_exit, gross_return = (
            calculate_gross_closing_result(Decimal("2800"), Decimal("100"), Decimal("2910"))
        )
        assert proceeds == Decimal("291000")
        assert cost_basis == Decimal("280000")
        assert gross_pnl == Decimal("11000")
        assert weighted_exit == Decimal("2910")
        assert gross_return == Decimal("3.93")


class TestNetClosingResult:
    def test_bbri_fixture_no_fees(self) -> None:
        result = calculate_net_closing_result(
            Decimal("2800"),
            Decimal("100"),
            Decimal("2910"),
            total_fees=Decimal("0"),
        )
        assert isinstance(result, ClosingResult)
        assert result.currency == CurrencyCode.IDR
        assert result.total_quantity == Decimal("100")
        assert result.weighted_exit_price == Decimal("2910")
        assert result.gross_proceeds == Decimal("291000")
        assert result.cost_basis == Decimal("280000")
        assert result.gross_pnl == Decimal("11000")
        assert result.total_fees == Decimal("0")
        assert result.total_taxes == Decimal("0")
        assert result.net_pnl == Decimal("11000")
        assert result.gross_return_percentage == Decimal("3.93")
        assert result.net_return_percentage == Decimal("3.93")

    def test_with_fees_and_taxes(self) -> None:
        result = calculate_net_closing_result(
            Decimal("2800"),
            Decimal("100"),
            Decimal("2910"),
            total_fees=Decimal("250"),
            total_taxes=Decimal("100"),
        )
        assert result.net_pnl == Decimal("10650")
        assert result.gross_pnl == Decimal("11000")
        assert result.gross_return_percentage == Decimal("3.93")
