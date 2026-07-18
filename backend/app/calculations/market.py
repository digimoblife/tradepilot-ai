"""Pure market calculations: change, spread, percentage change.

All functions accept ``Decimal`` values and return ``Decimal``.
"""

from __future__ import annotations

from decimal import Decimal

from app.calculations.decimal_utils import quantize_percentage, safe_divide


def calculate_market_change(current: Decimal, previous: Decimal) -> Decimal:
    """Absolute price change: ``current - previous``.

    Returns a ``Decimal`` (may be negative or zero).  No quantization is applied;
    callers should quantize according to currency rules when storing results.
    """
    return current - previous


def calculate_spread(best_bid: Decimal, best_ask: Decimal) -> Decimal:
    """Spread: ``best_ask - best_bid``.

    Returns a ``Decimal`` (may be negative if the market appears crossed;
    domain validation will decide whether that is acceptable).
    """
    return best_ask - best_bid


def calculate_percentage_change(current: Decimal, previous: Decimal) -> Decimal | None:
    """Percentage change: ``((current - previous) / previous) × 100``.

    Returns ``None`` when *previous* is zero.
    Result is in percentage points (e.g. 5.25 means +5.25 %).
    """
    ratio = safe_divide(current - previous, previous)
    if ratio is None:
        return None
    return quantize_percentage(ratio * Decimal("100"))
