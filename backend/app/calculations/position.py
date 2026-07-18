"""Pure position calculations: unrealised P&L, distances, risk/reward.

All functions accept ``Decimal`` values and return ``Decimal``.
Long-position formulas only (MVP is long-only).

Unit conventions:
  - P&L values are in money (IDR whole rupiah / USD cents).
  - Percentages are percentage points (e.g. 5.25 means 5.25 %).
  - Ratios are dimensionless.
"""

from __future__ import annotations

from decimal import Decimal

from app.calculations.decimal_utils import (
    CurrencyCode,
    quantize_money,
    quantize_percentage,
    safe_divide,
)


def calculate_unrealized_pnl(
    current_price: Decimal,
    average_entry_price: Decimal,
    remaining_quantity: Decimal,
    currency: CurrencyCode = CurrencyCode.IDR,
) -> Decimal:
    """Unrealised P&L: ``(current_price - entry_price) × remaining_quantity``.

    Returns a ``Decimal`` quantized to the currency's money precision.
    """
    raw = (current_price - average_entry_price) * remaining_quantity
    return quantize_money(raw, currency)


def calculate_unrealized_return(
    current_price: Decimal,
    average_entry_price: Decimal,
) -> Decimal | None:
    """Unrealised return: ``((current_price - entry_price) / entry_price) × 100``.

    Returns ``None`` when *average_entry_price* is zero.
    """
    ratio = safe_divide(current_price - average_entry_price, average_entry_price)
    if ratio is None:
        return None
    return quantize_percentage(ratio * Decimal("100"))


def calculate_remaining_quantity(
    original_quantity: Decimal,
    exited_quantity: Decimal,
) -> Decimal:
    """Remaining quantity after a partial exit.

    Returns ``original_quantity - exited_quantity``.
    """
    return original_quantity - exited_quantity


# ---------------------------------------------------------------------------
# Distance to stop (current price vs active stop)
# ---------------------------------------------------------------------------


def calculate_current_distance_to_stop(
    current_price: Decimal,
    stop_price: Decimal,
) -> Decimal | None:
    """Downside distance from current price to active stop: ``((current - stop) / current) × 100``.

    For a long position, this is positive when *stop* is below *current*.
    Returns ``None`` when *current_price* is zero.
    """
    ratio = safe_divide(current_price - stop_price, current_price)
    if ratio is None:
        return None
    return quantize_percentage(ratio * Decimal("100"))


# ---------------------------------------------------------------------------
# Distance to target (current price vs active target)
# ---------------------------------------------------------------------------


def calculate_current_distance_to_target(
    target_price: Decimal,
    current_price: Decimal,
) -> Decimal | None:
    """Upside distance from current price to target: ``((target - current) / current) × 100``.

    For a long position, this is positive when *target* is above *current*.
    Returns ``None`` when *current_price* is zero.
    """
    ratio = safe_divide(target_price - current_price, current_price)
    if ratio is None:
        return None
    return quantize_percentage(ratio * Decimal("100"))


# ---------------------------------------------------------------------------
# Setup risk distance (entry price to stop loss)
# ---------------------------------------------------------------------------


def calculate_setup_distance_to_stop(
    entry_price: Decimal,
    stop_price: Decimal,
) -> Decimal | None:
    """Initial risk from entry to stop: ``((entry - stop) / entry) × 100``.

    Positive when *stop* is below *entry* (normal long position).
    Returns ``None`` when *entry_price* is zero.
    """
    ratio = safe_divide(entry_price - stop_price, entry_price)
    if ratio is None:
        return None
    return quantize_percentage(ratio * Decimal("100"))


# ---------------------------------------------------------------------------
# Setup distance to target (entry price to target)
# ---------------------------------------------------------------------------


def calculate_setup_distance_to_target(
    target_price: Decimal,
    entry_price: Decimal,
) -> Decimal | None:
    """Setup reward from entry to target: ``((target - entry) / entry) × 100``.

    Positive when *target* is above *entry*.
    Returns ``None`` when *entry_price* is zero.
    """
    ratio = safe_divide(target_price - entry_price, entry_price)
    if ratio is None:
        return None
    return quantize_percentage(ratio * Decimal("100"))


# ---------------------------------------------------------------------------
# Risk percentage (initial setup)
# ---------------------------------------------------------------------------


def calculate_risk_percentage(
    entry_price: Decimal,
    stop_price: Decimal,
) -> Decimal | None:
    """Initial risk percentage: ``((entry - stop) / entry) × 100``.

    Alias for ``calculate_setup_distance_to_stop``.
    """
    return calculate_setup_distance_to_stop(entry_price, stop_price)


# ---------------------------------------------------------------------------
# Reward percentage (initial setup)
# ---------------------------------------------------------------------------


def calculate_reward_percentage(
    target_price: Decimal,
    entry_price: Decimal,
) -> Decimal | None:
    """Setup reward percentage: ``((target - entry) / entry) × 100``.

    Alias for ``calculate_setup_distance_to_target``.
    """
    return calculate_setup_distance_to_target(target_price, entry_price)


# ---------------------------------------------------------------------------
# Risk-reward ratio
# ---------------------------------------------------------------------------


def calculate_risk_reward_ratio(
    entry_price: Decimal,
    stop_price: Decimal,
    target_price: Decimal,
) -> Decimal | None:
    """Risk-reward ratio: ``(target - entry) / (entry - stop)``.

    For a valid long setup: positive when stop < entry < target.
    Returns ``None`` when risk distance (entry - stop) is zero.
    """
    risk = entry_price - stop_price
    reward = target_price - entry_price
    ratio = safe_divide(reward, risk)
    if ratio is None:
        return None
    return ratio
