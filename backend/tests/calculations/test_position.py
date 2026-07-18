"""Tests for position calculations."""

from __future__ import annotations

from decimal import Decimal

from app.calculations.position import (
    calculate_current_distance_to_stop,
    calculate_current_distance_to_target,
    calculate_remaining_quantity,
    calculate_reward_percentage,
    calculate_risk_percentage,
    calculate_risk_reward_ratio,
    calculate_setup_distance_to_stop,
    calculate_setup_distance_to_target,
    calculate_unrealized_pnl,
    calculate_unrealized_return,
)


class TestUnrealizedPnl:
    def test_profit(self) -> None:
        result = calculate_unrealized_pnl(Decimal("2900"), Decimal("2800"), Decimal("100"))
        assert result == Decimal("10000")

    def test_loss(self) -> None:
        result = calculate_unrealized_pnl(Decimal("2700"), Decimal("2800"), Decimal("100"))
        assert result == Decimal("-10000")

    def test_zero(self) -> None:
        result = calculate_unrealized_pnl(Decimal("2800"), Decimal("2800"), Decimal("100"))
        assert result == Decimal("0")

    def test_remaining_quantity_used(self) -> None:
        """After partial exit, only remaining quantity is used."""
        result = calculate_unrealized_pnl(Decimal("2900"), Decimal("2800"), Decimal("50"))
        assert result == Decimal("5000")

    def test_usd_precision(self) -> None:
        from app.calculations.decimal_utils import CurrencyCode

        result = calculate_unrealized_pnl(
            Decimal("15.50"),
            Decimal("14.50"),
            Decimal("20"),
            currency=CurrencyCode.USD,
        )
        assert result == Decimal("20.00")


class TestUnrealizedReturn:
    def test_positive(self) -> None:
        result = calculate_unrealized_return(Decimal("2900"), Decimal("2800"))
        assert result == Decimal("3.57")

    def test_negative(self) -> None:
        result = calculate_unrealized_return(Decimal("2700"), Decimal("2800"))
        assert result == Decimal("-3.57")

    def test_zero_entry(self) -> None:
        assert calculate_unrealized_return(Decimal("100"), Decimal("0")) is None


class TestRemainingQuantity:
    def test_basic(self) -> None:
        assert calculate_remaining_quantity(Decimal("100"), Decimal("50")) == Decimal("50")

    def test_zero_exit(self) -> None:
        assert calculate_remaining_quantity(Decimal("100"), Decimal("0")) == Decimal("100")


class TestCurrentDistanceToStop:
    def test_positive_distance(self) -> None:
        result = calculate_current_distance_to_stop(Decimal("2900"), Decimal("2840"))
        assert result == Decimal("2.07")

    def test_price_at_stop(self) -> None:
        result = calculate_current_distance_to_stop(Decimal("2840"), Decimal("2840"))
        assert result == Decimal("0.00")

    def test_stop_above_price(self) -> None:
        """Stop above current produces negative distance."""
        result = calculate_current_distance_to_stop(Decimal("2800"), Decimal("2900"))
        assert result == Decimal("-3.57")

    def test_zero_current(self) -> None:
        assert calculate_current_distance_to_stop(Decimal("0"), Decimal("100")) is None


class TestCurrentDistanceToTarget:
    def test_positive_distance(self) -> None:
        result = calculate_current_distance_to_target(Decimal("2920"), Decimal("2800"))
        assert result == Decimal("4.29")

    def test_price_at_target(self) -> None:
        result = calculate_current_distance_to_target(Decimal("2800"), Decimal("2800"))
        assert result == Decimal("0.00")

    def test_target_below_price(self) -> None:
        """Target below current produces negative distance."""
        result = calculate_current_distance_to_target(Decimal("2700"), Decimal("2800"))
        assert result == Decimal("-3.57")

    def test_zero_current(self) -> None:
        assert calculate_current_distance_to_target(Decimal("100"), Decimal("0")) is None


class TestSetupDistanceToStop:
    def test_normal_long(self) -> None:
        result = calculate_setup_distance_to_stop(Decimal("2800"), Decimal("2700"))
        assert result == Decimal("3.57")

    def test_zero_entry(self) -> None:
        assert calculate_setup_distance_to_stop(Decimal("0"), Decimal("100")) is None

    def test_stop_above_entry(self) -> None:
        """Negative risk when stop is above entry."""
        result = calculate_setup_distance_to_stop(Decimal("2700"), Decimal("2800"))
        # (2700 - 2800) / 2700 * 100 = -3.7037... → -3.70
        assert result == Decimal("-3.70")


class TestSetupDistanceToTarget:
    def test_normal_long(self) -> None:
        result = calculate_setup_distance_to_target(Decimal("2920"), Decimal("2800"))
        assert result == Decimal("4.29")

    def test_target_below_entry(self) -> None:
        result = calculate_setup_distance_to_target(Decimal("2700"), Decimal("2800"))
        assert result == Decimal("-3.57")


class TestRiskPercentage:
    def test_bbri_fixture(self) -> None:
        """BBRI initial stop 2700, entry 2800 = 3.57%."""
        result = calculate_risk_percentage(Decimal("2800"), Decimal("2700"))
        assert result == Decimal("3.57")


class TestRewardPercentage:
    def test_bbri_fixture(self) -> None:
        """BBRI initial target 2920, entry 2800 = 4.29%."""
        result = calculate_reward_percentage(Decimal("2920"), Decimal("2800"))
        assert result == Decimal("4.29")


class TestRiskRewardRatio:
    def test_valid_long(self) -> None:
        """Entry 2800, stop 2700, target 2920 → 1.20."""
        result = calculate_risk_reward_ratio(
            Decimal("2800"),
            Decimal("2700"),
            Decimal("2920"),
        )
        assert result == Decimal("1.20")

    def test_zero_risk(self) -> None:
        assert (
            calculate_risk_reward_ratio(
                Decimal("100"),
                Decimal("100"),
                Decimal("200"),
            )
            is None
        )

    def test_inverted(self) -> None:
        """Stop above entry gives negative reward fraction → negative ratio."""
        result = calculate_risk_reward_ratio(
            Decimal("2700"),
            Decimal("2800"),
            Decimal("2900"),
        )
        assert result is not None
        assert result < Decimal("0")
