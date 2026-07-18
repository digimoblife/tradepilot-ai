"""BBRI fixture integration test.

Uses the canonical BBRI trade parameters from spec documents:
  - Entry:  2800 x 100 shares
  - Partial exit:  50 @ 2920
  - Final exit:    50 @ 2900
  - Weighted avg exit:  2910
  - Gross P/L:         11000
"""

from __future__ import annotations

from decimal import Decimal

from app.calculations.exits import (
    ExitFill,
    calculate_gross_closing_pnl,
    calculate_sum_realized_pnl,
    calculate_weighted_average_exit,
)


def test_bbri_fixture_weighted_exit_and_gross_pnl() -> None:
    partial = ExitFill(Decimal("2920"), Decimal("50"))
    final = ExitFill(Decimal("2900"), Decimal("50"))
    fills = (partial, final)

    entry_price = Decimal("2800")
    total_quantity = Decimal("100")

    weighted_exit_price = calculate_weighted_average_exit(fills)
    assert weighted_exit_price is not None
    assert weighted_exit_price == Decimal("2910")

    gross_pnl = calculate_sum_realized_pnl(entry_price, fills)
    assert gross_pnl == Decimal("11000")

    gross_pnl_v2 = calculate_gross_closing_pnl(entry_price, total_quantity, weighted_exit_price)
    assert gross_pnl_v2 == Decimal("11000")


def test_bbri_fixture_weighted_exit_exact() -> None:
    fills = (
        ExitFill(Decimal("2920"), Decimal("50")),
        ExitFill(Decimal("2900"), Decimal("50")),
    )
    result = calculate_weighted_average_exit(fills)
    assert result == Decimal("2910")


def test_bbri_fixture_gross_pnl_exact() -> None:
    fills = (
        ExitFill(Decimal("2920"), Decimal("50")),
        ExitFill(Decimal("2900"), Decimal("50")),
    )
    result = calculate_sum_realized_pnl(Decimal("2800"), fills)
    assert result == Decimal("11000")


def test_bbri_gross_closing_pnl_reconciliation() -> None:
    """Gross closing P&L via the aggregate formula must match summed realised P&L."""
    entry = Decimal("2800")
    total_qty = Decimal("100")
    fills = (
        ExitFill(Decimal("2920"), Decimal("50")),
        ExitFill(Decimal("2900"), Decimal("50")),
    )

    weighted = calculate_weighted_average_exit(fills)
    assert weighted is not None
    assert weighted == Decimal("2910")

    sum_realized = calculate_sum_realized_pnl(entry, fills)
    gross_closing = calculate_gross_closing_pnl(entry, total_qty, weighted)

    assert sum_realized == gross_closing, (
        f"Sum realised P&L ({sum_realized}) must equal gross closing P&L ({gross_closing})"
    )
