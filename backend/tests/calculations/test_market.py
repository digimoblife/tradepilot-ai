"""Tests for market calculations."""

from __future__ import annotations

from decimal import Decimal

from app.calculations.market import (
    calculate_market_change,
    calculate_percentage_change,
    calculate_spread,
)


class TestMarketChange:
    def test_positive_change(self) -> None:
        assert calculate_market_change(Decimal("1100"), Decimal("1000")) == Decimal("100")

    def test_negative_change(self) -> None:
        assert calculate_market_change(Decimal("900"), Decimal("1000")) == Decimal("-100")

    def test_zero_change(self) -> None:
        assert calculate_market_change(Decimal("1000"), Decimal("1000")) == Decimal("0")

    def test_decimal_precision_preserved(self) -> None:
        result = calculate_market_change(Decimal("0.000001"), Decimal("0.000002"))
        assert result == Decimal("-0.000001")


class TestSpread:
    def test_positive_spread(self) -> None:
        assert calculate_spread(Decimal("10"), Decimal("12")) == Decimal("2")

    def test_zero_spread(self) -> None:
        assert calculate_spread(Decimal("10"), Decimal("10")) == Decimal("0")

    def test_negative_crossed_market(self) -> None:
        """Crossed market where ask < bid produces negative spread."""
        assert calculate_spread(Decimal("12"), Decimal("10")) == Decimal("-2")


class TestPercentageChange:
    def test_positive(self) -> None:
        result = calculate_percentage_change(Decimal("1100"), Decimal("1000"))
        assert result == Decimal("10.00")

    def test_negative(self) -> None:
        result = calculate_percentage_change(Decimal("900"), Decimal("1000"))
        assert result == Decimal("-10.00")

    def test_zero_change(self) -> None:
        result = calculate_percentage_change(Decimal("1000"), Decimal("1000"))
        assert result == Decimal("0.00")

    def test_zero_denominator(self) -> None:
        assert calculate_percentage_change(Decimal("100"), Decimal("0")) is None

    def test_fractional_change(self) -> None:
        result = calculate_percentage_change(Decimal("105"), Decimal("100"))
        assert result == Decimal("5.00")

    def test_small_change(self) -> None:
        result = calculate_percentage_change(Decimal("1001"), Decimal("1000"))
        assert result == Decimal("0.10")

    def test_no_float_artifact(self) -> None:
        result = calculate_percentage_change(Decimal("10"), Decimal("3"))
        assert result == Decimal("233.33")
