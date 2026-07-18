"""Pure exit calculations: partial and full closing.

All functions accept ``Decimal`` values and return ``Decimal``.
Uses frozen dataclass ``ExitFill`` for structured exit data.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.calculations.decimal_utils import (
    CurrencyCode,
    quantize_money,
    quantize_percentage,
    safe_divide,
)
from app.calculations.models import ClosingResult


@dataclass(frozen=True, slots=True)
class ExitFill:
    """A single exit fill with price and quantity."""

    price: Decimal
    quantity: Decimal


# ---------------------------------------------------------------------------
# Partial realised P&L
# ---------------------------------------------------------------------------


def calculate_partial_realized_pnl(
    exit_price: Decimal,
    average_entry_price: Decimal,
    exit_quantity: Decimal,
    currency: CurrencyCode = CurrencyCode.IDR,
) -> Decimal:
    """Realised P&L for one exit fill: ``(exit_price - entry_price) × exit_quantity``.

    Returns a ``Decimal`` quantized to the currency's money precision.
    """
    raw = (exit_price - average_entry_price) * exit_quantity
    return quantize_money(raw, currency)


# ---------------------------------------------------------------------------
# Sum of realised P&L across multiple fills
# ---------------------------------------------------------------------------


def calculate_sum_realized_pnl(
    entry_price: Decimal,
    fills: tuple[ExitFill, ...],
    currency: CurrencyCode = CurrencyCode.IDR,
) -> Decimal:
    """Sum realised P&L across several exit fills.

    Aggregation is performed at full precision; only the final sum is quantized.
    """
    total = Decimal("0")
    for fill in fills:
        total += (fill.price - entry_price) * fill.quantity
    return quantize_money(total, currency)


# ---------------------------------------------------------------------------
# Weighted average exit price
# ---------------------------------------------------------------------------


def calculate_weighted_average_exit(fills: tuple[ExitFill, ...]) -> Decimal | None:
    """Quantity-weighted average exit price.

    ``Σ(price_i × quantity_i) / Σ(quantity_i)``

    Returns ``None`` when total exited quantity is zero.
    The result is quantized to 6 decimal places (DB price precision).
    """
    total_value = Decimal("0")
    total_qty = Decimal("0")
    for fill in fills:
        total_value += fill.price * fill.quantity
        total_qty += fill.quantity
    avg = safe_divide(total_value, total_qty)
    if avg is None:
        return None
    return avg


# ---------------------------------------------------------------------------
# Gross closing P&L
# ---------------------------------------------------------------------------


def calculate_gross_closing_pnl(
    entry_price: Decimal,
    total_quantity: Decimal,
    weighted_exit_price: Decimal,
    currency: CurrencyCode = CurrencyCode.IDR,
) -> Decimal:
    """Gross closing P&L: ``(weighted_exit - entry) × total_quantity``.

    The formula reconciles with summed realised P&L for fully closed positions.
    """
    raw = (weighted_exit_price - entry_price) * total_quantity
    return quantize_money(raw, currency)


# ---------------------------------------------------------------------------
# Net closing P&L
# ---------------------------------------------------------------------------


def calculate_net_closing_pnl(
    gross_pnl: Decimal,
    total_fees: Decimal,
    total_taxes: Decimal = Decimal("0"),
    currency: CurrencyCode = CurrencyCode.IDR,
) -> Decimal:
    """Net closing P&L: ``gross_pnl - fees - taxes``."""
    return quantize_money(gross_pnl - total_fees - total_taxes, currency)


# ---------------------------------------------------------------------------
# Structured closing result
# ---------------------------------------------------------------------------


def calculate_gross_closing_result(
    entry_price: Decimal,
    total_quantity: Decimal,
    weighted_exit_price: Decimal,
    currency: CurrencyCode = CurrencyCode.IDR,
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal | None]:
    """Calculate multiple gross closing metrics at once.

    Returns ``(gross_proceeds, cost_basis, gross_pnl, weighted_exit_price,
    gross_return_percentage)``.

    *gross_return_percentage* is ``None`` when entry is zero.
    """

    gross_proceeds = quantize_money(weighted_exit_price * total_quantity, currency)
    cost_basis = quantize_money(entry_price * total_quantity, currency)
    gross_pnl = quantize_money(gross_proceeds - cost_basis, currency)

    gross_return_pct: Decimal | None = None
    if entry_price != Decimal("0"):
        gross_return_pct = quantize_percentage(
            ((weighted_exit_price - entry_price) / entry_price) * Decimal("100"),
        )

    return gross_proceeds, cost_basis, gross_pnl, weighted_exit_price, gross_return_pct


def calculate_net_closing_result(
    entry_price: Decimal,
    total_quantity: Decimal,
    weighted_exit_price: Decimal,
    total_fees: Decimal,
    total_taxes: Decimal = Decimal("0"),
    currency: CurrencyCode = CurrencyCode.IDR,
) -> ClosingResult:
    """Full closing result including net values."""
    gross_proceeds = quantize_money(weighted_exit_price * total_quantity, currency)
    cost_basis = quantize_money(entry_price * total_quantity, currency)
    gross_pnl = quantize_money(gross_proceeds - cost_basis, currency)
    net_pnl = quantize_money(gross_pnl - total_fees - total_taxes, currency)

    gross_return_pct: Decimal | None = None
    net_return_pct: Decimal | None = None
    if entry_price != Decimal("0"):
        gross_return_pct = quantize_percentage(
            ((weighted_exit_price - entry_price) / entry_price) * Decimal("100"),
        )
        net_return_pct = quantize_percentage(
            net_pnl / cost_basis * Decimal("100"),
        )

    return ClosingResult(
        currency=currency,
        total_quantity=total_quantity,
        weighted_exit_price=weighted_exit_price,
        gross_proceeds=gross_proceeds,
        cost_basis=cost_basis,
        gross_pnl=gross_pnl,
        total_fees=total_fees,
        total_taxes=total_taxes,
        net_pnl=net_pnl,
        gross_return_percentage=gross_return_pct,
        net_return_percentage=net_return_pct,
    )
