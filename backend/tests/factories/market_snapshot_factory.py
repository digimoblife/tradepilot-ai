"""Market Snapshot test factory."""

from __future__ import annotations

import copy
from decimal import Decimal
from typing import Mapping

from app.calculations.market import (
    calculate_market_change,
    calculate_percentage_change,
    calculate_spread,
)
from tests.factories.deep_merge import deep_merge

_BASE = {
    "trading_date": "2026-07-18",
    "market_timestamp": "2026-07-18T09:30:00+07:00",
    "update_period": "MORNING",
    "currency": "IDR",
    "data_available": True,
    "open": 2800,
    "high": 2850,
    "low": 2780,
    "last": 2830,
    "close": None,
    "previous_close": 2780,
    "average": 2815,
    "change": None,
    "change_percentage": None,
    "volume": 15000000,
    "transaction_value": 42000000000,
    "best_bid": 2820,
    "best_offer": 2830,
    "spread": None,
    "spread_percentage": None,
    "summary": "Pasar bergerak positif pada sesi pagi.",
    "source": "MIXED",
    "limitations": [],
}


def make_market_snapshot(*, overrides: Mapping[str, object] | None = None) -> dict[str, object]:
    """Return a deterministic Market Snapshot dict.

    Derived fields (change, change_percentage, spread, spread_percentage)
    are automatically calculated from the raw OHLC / bid-offer values
    using accepted TP-0304 calculation helpers.

    Pass *overrides* to replace any field.  Explicitly overridden derived
    values are kept as-is (not recalculated).
    """
    raw = copy.deepcopy(_BASE)

    # Auto-calculate derived fields using TP-0304 helpers
    last = Decimal(str(raw["last"]))
    prev_close = Decimal(str(raw["previous_close"]))
    bid = Decimal(str(raw["best_bid"]))
    offer = Decimal(str(raw["best_offer"]))

    if raw["change"] is None:
        raw["change"] = int(calculate_market_change(last, prev_close))

    if raw["change_percentage"] is None:
        pct = calculate_percentage_change(last, prev_close)
        if pct is not None:
            raw["change_percentage"] = str(pct)

    if raw["spread"] is None:
        raw["spread"] = int(calculate_spread(bid, offer))

    if raw["spread_percentage"] is None:
        sp = calculate_spread(bid, offer)
        if sp is not None and offer > 0:
            sp_pct = (sp / offer) * 100
            raw["spread_percentage"] = str(Decimal(str(sp_pct)).quantize(Decimal("0.01")))

    if overrides:
        return deep_merge(raw, overrides)

    return raw
