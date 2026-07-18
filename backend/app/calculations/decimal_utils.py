"""Shared Decimal helpers: conversion, quantization, safe division.

Precision rules (derived from database types and domain specs):
  - IDR prices ………………… quantize to whole rupiah (0 decimal places)
  - IDR money (PnL, proceeds) … whole rupiah
  - USD prices ………………… quantize to 2 decimal places (cents)
  - USD money …………………… 2 decimal places
  - Quantities ………………… 0 decimal places (whole units for MVP)
  - Percentages ……………… 2 decimal places (e.g. 3.93 means 3.93 %)
  - Rounding …………………… ROUND_HALF_UP
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from enum import StrEnum

from app.calculations.errors import InvalidDecimalError


class CurrencyCode(StrEnum):
    IDR = "IDR"
    USD = "USD"


# ---------------------------------------------------------------------------
# Module-level precision constants
# ---------------------------------------------------------------------------

IDR_PRICE_PRECISION = Decimal("1")
IDR_MONEY_PRECISION = Decimal("1")
USD_PRICE_PRECISION = Decimal("0.01")
USD_MONEY_PRECISION = Decimal("0.01")
QUANTITY_PRECISION = Decimal("1")
PERCENTAGE_PRECISION = Decimal("0.01")
RETURN_PRECISION = Decimal("0.01")

ROUNDING = ROUND_HALF_UP

# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------

_FINITE = frozenset({"NaN", "-NaN", "Infinity", "-Infinity", "sNaN", "-sNaN"})


def to_decimal(value: Decimal | int | str) -> Decimal:
    """Convert *value* to a valid finite ``Decimal``.

    Accepted types: ``Decimal``, ``int``, ``str``.

    Raises
    ------
    InvalidDecimalError
        If *value* is a ``float``, a non-finite ``Decimal``, an unparseable string,
        or any other unsupported type.
    """
    if isinstance(value, Decimal):
        if _is_non_finite(value):
            raise InvalidDecimalError(f"Non-finite Decimal: {value}")
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        raise InvalidDecimalError(
            "float is not accepted for financial calculations; use Decimal or str instead"
        )
    if isinstance(value, str):
        try:
            d = Decimal(value)
        except InvalidOperation as exc:
            raise InvalidDecimalError(f"Cannot parse Decimal from string: {value!r}") from exc
        if _is_non_finite(d):
            raise InvalidDecimalError(f"Non-finite Decimal: {d}")
        return d
    raise InvalidDecimalError(f"Unsupported type for Decimal conversion: {type(value).__name__}")


def _is_non_finite(d: Decimal) -> bool:
    return d.is_nan() or d.is_infinite()


# ---------------------------------------------------------------------------
# Quantization
# ---------------------------------------------------------------------------


def quantize_price(value: Decimal, currency: CurrencyCode = CurrencyCode.IDR) -> Decimal:
    """Quantize a price value according to currency rules."""
    prec = IDR_PRICE_PRECISION if currency == CurrencyCode.IDR else USD_PRICE_PRECISION
    return value.quantize(prec, rounding=ROUNDING)


def quantize_money(value: Decimal, currency: CurrencyCode = CurrencyCode.IDR) -> Decimal:
    """Quantize a monetary amount (PnL, proceeds, fees) according to currency rules."""
    prec = IDR_MONEY_PRECISION if currency == CurrencyCode.IDR else USD_MONEY_PRECISION
    return value.quantize(prec, rounding=ROUNDING)


def quantize_quantity(value: Decimal) -> Decimal:
    """Quantize a quantity (shares / units) to whole numbers."""
    return value.quantize(QUANTITY_PRECISION, rounding=ROUNDING)


def quantize_percentage(value: Decimal) -> Decimal:
    """Quantize a percentage to the standard precision."""
    return value.quantize(PERCENTAGE_PRECISION, rounding=ROUNDING)


def quantize_return(value: Decimal) -> Decimal:
    """Quantize a return percentage to standard precision."""
    return value.quantize(RETURN_PRECISION, rounding=ROUNDING)


# ---------------------------------------------------------------------------
# Safe division
# ---------------------------------------------------------------------------


def safe_divide(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    """Return ``numerator / denominator`` or ``None`` if denominator is zero."""
    if denominator == Decimal("0"):
        return None
    return numerator / denominator
