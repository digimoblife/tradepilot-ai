"""Trade State test factories for the four canonical position states."""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from app.calculations.exits import (
    ExitFill,
    calculate_gross_closing_pnl,
    calculate_partial_realized_pnl,
    calculate_weighted_average_exit,
)
from app.calculations.position import calculate_unrealized_pnl, calculate_unrealized_return
from tests.factories.deep_merge import deep_merge

SESSION_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
TICKER = "BBRI"
CURRENCY = "IDR"
ENTRY_PRICE = 2800
ORIGINAL_QTY = 100

OPEN_TS = "2026-07-15T10:12:00+07:00"
CONFIRMED_TS = "2026-07-15T10:12:00+07:00"
PARTIAL_TS = "2026-07-17T14:05:00+07:00"
CLOSE_TS = "2026-07-17T15:12:00+07:00"
NOW_TS = "2026-07-18T12:00:00+07:00"


def make_not_opened_trade_state(
    *,
    overrides: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Canonical NOT_OPENED position."""
    base = {
        "session_id": SESSION_ID,
        "ticker": TICKER,
        "currency": CURRENCY,
        "session_status": "WATCHING",
        "created_at": "2026-07-15T09:05:00+07:00",
        "updated_at": "2026-07-15T09:05:00+07:00",
        "position": {
            "position_exists": False,
            "position_status": "NOT_OPENED",
            "entry_price": None,
            "entry_timestamp": None,
            "original_quantity": None,
            "remaining_quantity": None,
            "average_exit_price": None,
            "active_stop_loss": None,
            "active_target": None,
            "realized_profit_loss": None,
            "realized_return_percentage": None,
            "unrealized_profit_loss": None,
            "unrealized_return_percentage": None,
            "distance_to_stop_percentage": None,
            "distance_to_target_percentage": None,
            "holding_duration_days": None,
            "last_confirmed_at": None,
        },
        "latest_market_price": None,
    }
    if overrides:
        return deep_merge(base, overrides)
    return base


def make_open_trade_state(
    *,
    overrides: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Canonical OPEN position.

    Entry 2800, qty 100, stop 2840, target 2920.
    Current market price 2890 → unrealized P/L 9000.
    """
    current_price = 2890
    unrealized = calculate_unrealized_pnl(
        Decimal(str(current_price)),
        Decimal(str(ENTRY_PRICE)),
        Decimal(str(ORIGINAL_QTY)),
    )
    unrealized_return = calculate_unrealized_return(
        Decimal(str(current_price)),
        Decimal(str(ENTRY_PRICE)),
    )

    base = {
        "session_id": SESSION_ID,
        "ticker": TICKER,
        "currency": CURRENCY,
        "session_status": "OPEN_POSITION",
        "created_at": "2026-07-15T09:05:00+07:00",
        "updated_at": NOW_TS,
        "position": {
            "position_exists": True,
            "position_status": "OPEN",
            "entry_price": ENTRY_PRICE,
            "entry_timestamp": OPEN_TS,
            "original_quantity": ORIGINAL_QTY,
            "remaining_quantity": ORIGINAL_QTY,
            "average_exit_price": None,
            "active_stop_loss": 2840,
            "active_target": 2920,
            "realized_profit_loss": None,
            "realized_return_percentage": None,
            "unrealized_profit_loss": str(unrealized),
            "unrealized_return_percentage": str(unrealized_return)
            if unrealized_return is not None
            else None,
            "distance_to_stop_percentage": "1.73",
            "distance_to_target_percentage": "1.04",
            "holding_duration_days": 2,
            "last_confirmed_at": CONFIRMED_TS,
        },
        "latest_market_price": current_price,
    }
    if overrides:
        return deep_merge(base, overrides)
    return base


def make_partial_trade_state(
    *,
    overrides: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Canonical PARTIALLY_CLOSED position.

    50 shares exited at 2920 → realized 6000.  50 remaining.
    """
    exit_price = 2920
    exited_qty = 50
    realized = calculate_partial_realized_pnl(
        Decimal(str(exit_price)),
        Decimal(str(ENTRY_PRICE)),
        Decimal(str(exited_qty)),
    )
    remaining = ORIGINAL_QTY - exited_qty
    unrealized = calculate_unrealized_pnl(
        Decimal("2910"),
        Decimal(str(ENTRY_PRICE)),
        Decimal(str(remaining)),
    )
    unrealized_return = calculate_unrealized_return(
        Decimal("2910"),
        Decimal(str(ENTRY_PRICE)),
    )

    base = {
        "session_id": SESSION_ID,
        "ticker": TICKER,
        "currency": CURRENCY,
        "session_status": "PARTIALLY_CLOSED",
        "created_at": "2026-07-15T09:05:00+07:00",
        "updated_at": PARTIAL_TS,
        "position": {
            "position_exists": True,
            "position_status": "PARTIALLY_CLOSED",
            "entry_price": ENTRY_PRICE,
            "entry_timestamp": OPEN_TS,
            "original_quantity": ORIGINAL_QTY,
            "remaining_quantity": remaining,
            "average_exit_price": exit_price,
            "active_stop_loss": 2840,
            "active_target": 3000,
            "realized_profit_loss": str(realized),
            "realized_return_percentage": "4.29",
            "unrealized_profit_loss": str(unrealized),
            "unrealized_return_percentage": str(unrealized_return)
            if unrealized_return is not None
            else None,
            "distance_to_stop_percentage": "2.41",
            "distance_to_target_percentage": "3.09",
            "holding_duration_days": 2,
            "last_confirmed_at": PARTIAL_TS,
        },
        "latest_market_price": 2910,
    }
    if overrides:
        return deep_merge(base, overrides)
    return base


def make_closed_trade_state(
    *,
    overrides: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Canonical CLOSED position.

    Partial: 50@2920.  Final: 50@2900.  Weighted avg exit: 2910.
    Gross P/L: 11000.
    """
    fills = (ExitFill(Decimal("2920"), Decimal("50")), ExitFill(Decimal("2900"), Decimal("50")))
    weighted_exit = calculate_weighted_average_exit(fills)
    gross = (
        calculate_gross_closing_pnl(
            Decimal(str(ENTRY_PRICE)), Decimal(str(ORIGINAL_QTY)), weighted_exit
        )
        if weighted_exit is not None
        else 0
    )

    base = {
        "session_id": SESSION_ID,
        "ticker": TICKER,
        "currency": CURRENCY,
        "session_status": "CLOSED_TAKE_PROFIT",
        "created_at": "2026-07-15T09:05:00+07:00",
        "updated_at": CLOSE_TS,
        "position": {
            "position_exists": True,
            "position_status": "CLOSED",
            "entry_price": ENTRY_PRICE,
            "entry_timestamp": OPEN_TS,
            "original_quantity": ORIGINAL_QTY,
            "remaining_quantity": 0,
            "average_exit_price": int(weighted_exit) if weighted_exit is not None else None,
            "active_stop_loss": None,
            "active_target": None,
            "realized_profit_loss": str(gross),
            "realized_return_percentage": "3.93",
            "unrealized_profit_loss": None,
            "unrealized_return_percentage": None,
            "distance_to_stop_percentage": None,
            "distance_to_target_percentage": None,
            "holding_duration_days": 2,
            "last_confirmed_at": CLOSE_TS,
        },
        "latest_market_price": None,
    }
    if overrides:
        return deep_merge(base, overrides)
    return base
