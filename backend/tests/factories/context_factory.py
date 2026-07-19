"""Context Summary test factory."""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from app.calculations.position import calculate_unrealized_pnl, calculate_unrealized_return
from tests.factories.deep_merge import deep_merge

SESSION_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
TICKER = "BBRI"
ENTRY_PRICE = 2800
ORIGINAL_QTY = 100
REMAINING_QTY = 100

CONTEXT_VERSION = "1.0.0"


def make_context_summary(
    *,
    trade_state: Mapping[str, object] | None = None,
    overrides: Mapping[str, object] | None = None,
    current_price: int = 2890,
) -> dict[str, object]:
    """Return a deterministic Context Summary payload.

    If *trade_state* is supplied, relevant position facts are extracted
    from it (entry, quantity, remaining, active stop/target).

    Otherwise, a default OPEN position context is used.
    """
    pos = {}
    if trade_state:
        p = trade_state.get("position")
        if isinstance(p, dict):
            pos = p

    entry = pos.get("entry_price", ENTRY_PRICE)
    orig_qty = pos.get("original_quantity", ORIGINAL_QTY)
    rem_qty = pos.get("remaining_quantity", REMAINING_QTY)
    active_stop = pos.get("active_stop_loss", 2840)
    active_target = pos.get("active_target", 2920)
    entry_ts = pos.get("entry_timestamp", "2026-07-15T10:12:00+07:00")

    unrealized = calculate_unrealized_pnl(
        Decimal(str(current_price)),
        Decimal(str(entry)),
        Decimal(str(rem_qty)),
    )
    unrealized_return = calculate_unrealized_return(
        Decimal(str(current_price)),
        Decimal(str(entry)),
    )

    base = {
        "context_id": "66666666-6666-4666-8666-666666666666",
        "session_id": SESSION_ID,
        "ticker": TICKER,
        "company_name": "Bank Rakyat Indonesia",
        "currency": "IDR",
        "session_status": "OPEN_POSITION",
        "generated_at": "2026-07-18T09:40:00+07:00",
        "source_cutoff_timestamp": "2026-07-18T09:35:00+07:00",
        "context_version": CONTEXT_VERSION,
        "current_position": {
            "position_exists": True,
            "position_status": "OPEN",
            "entry_price": entry,
            "entry_timestamp": entry_ts,
            "original_quantity": orig_qty,
            "remaining_quantity": rem_qty,
            "average_exit_price": None,
            "current_price": current_price,
            "active_stop_loss": active_stop,
            "active_target": active_target,
            "realized_profit_loss": None,
            "realized_return_percentage": None,
            "unrealized_profit_loss": str(unrealized),
            "unrealized_return_percentage": str(unrealized_return)
            if unrealized_return is not None
            else None,
            "holding_duration_days": 2,
            "last_confirmed_at": "2026-07-15T10:12:00+07:00",
        },
        "active_levels": {
            "supports": [],
            "resistances": [],
            "entry_reference": {
                "price": entry,
                "label": "Entry referensi",
                "summary": "Harga entry posisi.",
            },
            "maximum_acceptable_entry": None,
            "active_stop_loss": {
                "price": active_stop,
                "label": "Active stop",
                "summary": "Batas risiko.",
            },
            "active_target": {
                "price": active_target,
                "label": "Active target",
                "summary": "Target profit.",
            },
            "proposed_stop_loss": None,
            "proposed_target": None,
            "invalidation_level": {
                "price": 2840,
                "label": "Invalidation",
                "summary": "Level invalidasi.",
            },
            "last_updated_at": "2026-07-18T09:35:00+07:00",
        },
        "context_quality": {
            "quality": "HIGH",
            "complete_enough_for_analysis": True,
            "canonical_state_included": True,
            "latest_analysis_included": True,
            "latest_evidence_included": True,
            "history_compressed": True,
            "stale": False,
            "limitations": [],
        },
        "summary": "BBRI dalam posisi Open Position dengan entry 2.800, stop 2.840, target 2.920.",
    }
    if overrides:
        return deep_merge(base, overrides)
    return base
