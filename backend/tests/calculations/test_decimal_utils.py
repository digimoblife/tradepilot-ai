"""Tests for Decimal utilities."""

from __future__ import annotations

from decimal import Decimal, getcontext, localcontext

import pytest

from app.calculations.decimal_utils import (
    CurrencyCode,
    InvalidDecimalError,
    quantize_money,
    quantize_percentage,
    quantize_price,
    quantize_quantity,
    safe_divide,
    to_decimal,
)


class TestToDecimal:
    def test_decimal_passthrough(self) -> None:
        d = Decimal("3.14")
        assert to_decimal(d) is d

    def test_integer_conversion(self) -> None:
        assert to_decimal(42) == Decimal("42")

    def test_string_conversion(self) -> None:
        assert to_decimal("3.14") == Decimal("3.14")

    def test_string_zero(self) -> None:
        assert to_decimal("0") == Decimal("0")

    def test_string_negative(self) -> None:
        assert to_decimal("-123.45") == Decimal("-123.45")

    def test_float_rejected(self) -> None:
        with pytest.raises(InvalidDecimalError, match="float"):
            to_decimal(0.1)  # type: ignore[arg-type]

    def test_invalid_string(self) -> None:
        with pytest.raises(InvalidDecimalError, match="Cannot parse"):
            to_decimal("not-a-number")

    def test_nan_rejected(self) -> None:
        with pytest.raises(InvalidDecimalError, match="Non-finite"):
            to_decimal(Decimal("NaN"))

    def test_positive_infinity_rejected(self) -> None:
        with pytest.raises(InvalidDecimalError, match="Non-finite"):
            to_decimal(Decimal("Infinity"))

    def test_negative_infinity_rejected(self) -> None:
        with pytest.raises(InvalidDecimalError, match="Non-finite"):
            to_decimal(Decimal("-Infinity"))

    def test_snan_rejected(self) -> None:
        with pytest.raises(InvalidDecimalError, match="Non-finite"):
            to_decimal(Decimal("sNaN"))

    def test_nan_string_rejected(self) -> None:
        with pytest.raises(InvalidDecimalError, match="Non-finite"):
            to_decimal("NaN")

    def test_inf_string_rejected(self) -> None:
        with pytest.raises(InvalidDecimalError, match="Non-finite"):
            to_decimal("Infinity")

    def test_unsupported_type_rejected(self) -> None:
        with pytest.raises(InvalidDecimalError, match="Unsupported type"):
            to_decimal([1, 2, 3])  # type: ignore[arg-type]


class TestQuantizePrice:
    def test_idr_whole_number(self) -> None:
        assert quantize_price(Decimal("2800"), CurrencyCode.IDR) == Decimal("2800")

    def test_idr_fractional_rounded(self) -> None:
        assert quantize_price(Decimal("1234.5678"), CurrencyCode.IDR) == Decimal("1235")

    def test_idr_half_up_boundary(self) -> None:
        assert quantize_price(Decimal("1234.50"), CurrencyCode.IDR) == Decimal("1235")

    def test_idr_half_down(self) -> None:
        assert quantize_price(Decimal("1234.49"), CurrencyCode.IDR) == Decimal("1234")

    def test_idr_negative(self) -> None:
        assert quantize_price(Decimal("-100.50"), CurrencyCode.IDR) == Decimal("-101")

    def test_usd_cents(self) -> None:
        assert quantize_price(Decimal("14.50"), CurrencyCode.USD) == Decimal("14.50")

    def test_usd_fractional(self) -> None:
        assert quantize_price(Decimal("14.501"), CurrencyCode.USD) == Decimal("14.50")

    def test_usd_round_up(self) -> None:
        assert quantize_price(Decimal("14.509"), CurrencyCode.USD) == Decimal("14.51")


class TestQuantizeMoney:
    def test_idr_whole(self) -> None:
        assert quantize_money(Decimal("11000"), CurrencyCode.IDR) == Decimal("11000")

    def test_idr_fractional_pnl(self) -> None:
        assert quantize_money(Decimal("11000.500"), CurrencyCode.IDR) == Decimal("11001")

    def test_idr_negative_pnl(self) -> None:
        assert quantize_money(Decimal("-5000.50"), CurrencyCode.IDR) == Decimal("-5001")

    def test_rounding_boundary_half_up(self) -> None:
        assert quantize_money(Decimal("1000.50"), CurrencyCode.IDR) == Decimal("1001")
        assert quantize_money(Decimal("1000.49"), CurrencyCode.IDR) == Decimal("1000")

    def test_usd_cents(self) -> None:
        assert quantize_money(Decimal("100.50"), CurrencyCode.USD) == Decimal("100.50")

    def test_usd_fractional(self) -> None:
        assert quantize_money(Decimal("100.501"), CurrencyCode.USD) == Decimal("100.50")


class TestQuantizeQuantity:
    def test_whole_number(self) -> None:
        assert quantize_quantity(Decimal("100")) == Decimal("100")

    def test_fractional_rounds(self) -> None:
        assert quantize_quantity(Decimal("50.6")) == Decimal("51")

    def test_fractional_rounds_down(self) -> None:
        assert quantize_quantity(Decimal("50.4")) == Decimal("50")


class TestQuantizePercentage:
    def test_two_decimals(self) -> None:
        assert quantize_percentage(Decimal("3.9300")) == Decimal("3.93")

    def test_rounding(self) -> None:
        assert quantize_percentage(Decimal("3.937")) == Decimal("3.94")

    def test_negative(self) -> None:
        assert quantize_percentage(Decimal("-1.070")) == Decimal("-1.07")


class TestSafeDivide:
    def test_normal_division(self) -> None:
        assert safe_divide(Decimal("10"), Decimal("2")) == Decimal("5")

    def test_zero_denominator(self) -> None:
        assert safe_divide(Decimal("10"), Decimal("0")) is None

    def test_negative_result(self) -> None:
        assert safe_divide(Decimal("-10"), Decimal("2")) == Decimal("-5")

    def test_zero_numerator(self) -> None:
        assert safe_divide(Decimal("0"), Decimal("5")) == Decimal("0")


class TestLocalContext:
    def test_global_context_not_mutated(self) -> None:
        prec_before = getcontext().prec
        with localcontext() as ctx:
            ctx.prec = 2
            Decimal("1") / Decimal("3")  # 0.33 in this context (exercises local)
        prec_after = getcontext().prec
        assert prec_before == prec_after
        # Our functions should still work with normal precision
        assert to_decimal(42) == Decimal("42")
        assert quantize_price(Decimal("2800"), CurrencyCode.IDR) == Decimal("2800")
