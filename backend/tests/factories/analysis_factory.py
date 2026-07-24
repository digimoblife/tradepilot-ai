"""Analysis payload factory supporting multiple analysis types."""

from __future__ import annotations

from decimal import Decimal
from typing import Mapping

from app.calculations.position import (
    calculate_reward_percentage,
    calculate_risk_percentage,
    calculate_risk_reward_ratio,
)
from tests.factories.deep_merge import deep_merge
from tests.factories.market_snapshot_factory import make_market_snapshot

SESSION_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
ANALYSIS_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
TICKER = "BBRI"

_NARRATIVE = {
    "evidence_summary_summary": "Analisa menggunakan orderbook dan chart.",
    "market_snapshot_summary": "Harga bergerak positif sejak pembukaan.",
    "executive_headline": "Setup rebound membutuhkan konfirmasi buyer.",
    "executive_summary": "Kondisi awal menunjukkan potensi rebound.",
    "orderbook_conclusion": "Orderbook belum mendukung entry.",
    "ai_summary": "Setup masih lemah, diperlukan konfirmasi tambahan.",
}


def _metadata(analysis_type: str) -> dict[str, object]:
    return {
        "analysis_id": ANALYSIS_ID,
        "session_id": SESSION_ID,
        "analysis_type": analysis_type,
        "ticker": TICKER,
        "company_name": "Bank Rakyat Indonesia",
        "analysis_timestamp": "2026-07-18T10:00:00+07:00",
        "language": "id",
        "schema": {
            "schema_name": "initial_analysis",
            "schema_version": "1.0.0",
        },
        "prompt_version": "1.0.0",
        "provider": "GEMINI",
        "model": "gemini-3.5-flash",
    }


def _entry_plan() -> dict[str, object]:
    entry = 2800
    stop = 2700
    target = 2920
    calculate_risk_percentage(Decimal(str(entry)), Decimal(str(stop)))
    calculate_reward_percentage(Decimal(str(target)), Decimal(str(entry)))
    calculate_risk_reward_ratio(Decimal(str(entry)), Decimal(str(stop)), Decimal(str(target)))
    return {
        "entry_recommended": False,
        "entry_type": "WAIT",
        "entry_price": None,
        "entry_zone_low": None,
        "entry_zone_high": None,
        "confirmation_required": False,
        "confirmation_condition": None,
        "chase_risk": "UNKNOWN",
        "maximum_acceptable_entry": None,
        "cancel_entry_condition": "Batalkan jika harga turun di bawah 2.700.",
        "summary": "Entry tidak direkomendasikan saat ini.",
    }


def _stop_loss_plan() -> dict[str, object]:
    return {
        "stop_loss_recommended": True,
        "stop_loss_price": 2700,
        "risk_from_reference_entry_percentage": "3.57",
        "invalidation_condition": "Keluar jika harga menembus 2.700.",
        "reason": "Stop loss awal.",
        "maximum_risk_respected": True,
        "summary": "Stop loss awal di 2.700.",
    }


def _target_plan() -> dict[str, object]:
    return {
        "target_recommended": True,
        "target_price": 2920,
        "reward_from_reference_entry_percentage": "4.29",
        "risk_reward_ratio": "1.20",
        "target_basis": "Resistance teknikal.",
        "primary_obstacle": "Resistance 2.900.",
        "required_condition": "Buyer menguat.",
        "summary": "Target awal di 2.920.",
    }


def make_analysis(
    analysis_type: str = "INITIAL_ANALYSIS", *, overrides: Mapping[str, object] | None = None
) -> dict[str, object]:
    """Return a deterministic analysis payload for the given *analysis_type*.

    Supported types: INITIAL_ANALYSIS, OPEN_POSITION_UPDATE.
    """
    ms = make_market_snapshot()
    meta = _metadata(analysis_type)

    if analysis_type == "INITIAL_ANALYSIS":
        payload: dict[str, object] = {
            "metadata": meta,
            "evidence_summary": {
                "evidence_ids": [ANALYSIS_ID],
                "orderbook_available": True,
                "chart_3_month_available": True,
                "chart_6_month_available": True,
                "latest_orderbook_timestamp": "2026-07-18T09:30:00+07:00",
                "latest_chart_timestamp": "2026-07-18T09:30:00+07:00",
                "has_unreadable_evidence": False,
                "has_stale_evidence": False,
                "summary": _NARRATIVE["evidence_summary_summary"],
                "limitations": [],
            },
            "market_snapshot": ms,
            "executive_summary": {
                "setup_status": "UNKNOWN",
                "recommended_action": "NO_ACTION",
                "headline": _NARRATIVE["executive_headline"],
                "summary": _NARRATIVE["executive_summary"],
                "main_opportunity": "Potensi rebound ke 2.900.",
                "main_risk": "Rebound gagal dan harga turun.",
            },
            "orderbook_analysis": {},
            "chart_3_month_analysis": {},
            "chart_6_month_analysis": {},
            "combined_chart_analysis": {},
            "price_levels": {},
            "entry_plan": _entry_plan(),
            "stop_loss_plan": _stop_loss_plan(),
            "target_plan": _target_plan(),
            "initial_thesis": {},
            "trading_plan": {},
            "ai_assessment": {},
            "warnings_and_missing_information": {},
        }
    elif analysis_type == "OPEN_POSITION_UPDATE":
        payload = {
            "metadata": meta,
            "update_period": "MIDDAY",
            "comparison": {},
            "evidence_summary": {},
            "market_snapshot": ms,
            "today_summary": {},
            "orderbook_analysis": {},
            "chart_update": {},
            "position_assessment": {
                "entry_price": 2800,
                "current_price": 2890,
                "remaining_quantity": 100,
                "active_stop_loss": 2840,
                "active_target": 2920,
                "unrealized_profit_loss": 9000,
                "unrealized_return_percentage": "3.21",
                "distance_to_stop_percentage": "1.73",
                "distance_to_target_percentage": "1.04",
                "holding_duration_days": 2,
                "health": "HEALTHY_WITH_CAUTION",
                "summary": "Posisi profit.",
            },
            "thesis_assessment": {},
            "target_assessment": {},
            "stop_loss_assessment": {},
            "trading_plan": {},
            "ai_assessment": {},
            "changes_from_previous": [],
            "warnings_and_missing_information": {},
        }
    else:
        raise ValueError(f"Unsupported analysis type: {analysis_type}")

    if overrides:
        return deep_merge(payload, overrides)
    return payload
