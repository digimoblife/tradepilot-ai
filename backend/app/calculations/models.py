"""Structured calculation result types."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.calculations.decimal_utils import CurrencyCode


@dataclass(frozen=True, slots=True)
class ClosingResult:
    """Full closing result for a completely closed position.

    All monetary values are quantized to the currency's precision.
    All percentages are percentage points (e.g. 3.93 means 3.93 %).
    """

    currency: CurrencyCode
    total_quantity: Decimal
    weighted_exit_price: Decimal
    gross_proceeds: Decimal
    cost_basis: Decimal
    gross_pnl: Decimal
    total_fees: Decimal
    total_taxes: Decimal
    net_pnl: Decimal
    gross_return_percentage: Decimal | None
    net_return_percentage: Decimal | None
