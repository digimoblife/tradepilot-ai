"""Best-effort system-fetched market facts for the rebuild AI pipeline.

This module fetches a small set of numeric, system-verified facts from the
existing ZAPI-backed market data collector (fundamental ratios, IHSG index
context, and medium-term foreign flow) and reduces them to a compact,
JSON-safe dict that submission services attach to ``AnalysisRequestV2.input_snapshot``.

These facts are supplementary context only. Acquisition is strictly best
effort: any failure (ZAPI unavailable, missing API key, unknown ticker, network
timeout) must never block or fail an Initial Analysis / WAIT Update /
Position Update submission. On any failure this module returns ``None`` and
the submission proceeds without market facts, exactly like the historical
behavior before this module existed.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.config import AppConfig
from app.services.market_data.collector import MarketDataCollector

logger = logging.getLogger(__name__)

_RECENT_VOLUME_WINDOW = 20


async def collect_market_facts(
    *,
    config: AppConfig,
    session_id: uuid.UUID,
    symbol: str,
) -> dict[str, Any] | None:
    """Fetch a compact snapshot of fundamental, index, and foreign-flow facts.

    Returns ``None`` when ZAPI is not configured or the fetch fails for any
    reason. Never raises.
    """
    if not symbol or not symbol.strip():
        return None
    if not config.zapi_api_key:
        return None

    try:
        collector = MarketDataCollector(config)
        snapshot, _validation = await collector.acquire_snapshot(
            session_id=session_id,
            symbol=symbol,
            snapshot_type="MARKET_FACTS",
        )
    except Exception as exc:  # noqa: BLE001 - best-effort, never block submission
        logger.warning(
            "Market facts collection failed for %s (session %s): %s",
            symbol,
            session_id,
            exc,
        )
        return None

    try:
        return _reduce_snapshot(snapshot)
    except Exception as exc:  # noqa: BLE001 - defensive, snapshot shape may vary
        logger.warning(
            "Market facts reduction failed for %s (session %s): %s",
            symbol,
            session_id,
            exc,
        )
        return None


def _reduce_snapshot(snapshot: Any) -> dict[str, Any] | None:
    quote = getattr(snapshot, "quote", None)
    market_context = getattr(snapshot, "market_context", None)
    foreign_flow = getattr(snapshot, "foreign_flow", None)
    history = getattr(snapshot, "historical_ohlcv", None)
    orderbook = getattr(snapshot, "orderbook", None)
    company_profile = getattr(snapshot, "company_profile", None)
    if company_profile is None and isinstance(snapshot, dict):
        company_profile = snapshot.get("company_profile")

    volume_today = getattr(quote, "volume_shares", None) if quote else None
    avg_volume = _average_recent_volume(history)
    avg_value = _average_recent_value(history)
    volume_ratio = (
        round(volume_today / avg_volume, 3)
        if volume_today and avg_volume and avg_volume > 0
        else None
    )

    computed_tech = getattr(history, "computed_technical", None) if history else None
    if computed_tech is None and isinstance(history, dict):
        computed_tech = history.get("computed_technical")

    pe_ratio = getattr(quote, "pe_ratio", None) if quote else None
    if pe_ratio is None:
        pe_ratio = _optional_float_val(_profile_field(company_profile, "pe_ratio"))

    pbv_ratio = getattr(quote, "pbv_ratio", None) if quote else None
    if pbv_ratio is None:
        pbv_ratio = _optional_float_val(_profile_field(company_profile, "pbv_ratio"))

    facts: dict[str, Any] = {
        "captured_at": getattr(snapshot, "captured_at", None),
        "sector": _optional_str_val(_profile_field(company_profile, "sector")),
        "sub_sector": _optional_str_val(_profile_field(company_profile, "sub_sector")),
        "pe_ratio": pe_ratio,
        "pbv_ratio": pbv_ratio,
        "market_cap": getattr(quote, "market_cap", None) if quote else None,
        "dividend_yield_percent": (
            _optional_float_val(_profile_field(company_profile, "dividend_yield_percent"))
        ),
        "dividend_per_share": (
            _optional_float_val(_profile_field(company_profile, "dividend_per_share"))
        ),
        "eps_ttm": _optional_float_val(_profile_field(company_profile, "eps_ttm")),
        "beta": _optional_float_val(_profile_field(company_profile, "beta")),
        "one_year_return_percent": (
            _optional_float_val(_profile_field(company_profile, "one_year_return_percent"))
        ),
        "next_earnings_date": (
            _optional_str_val(_profile_field(company_profile, "next_earnings_date"))
        ),
        "volume_shares_today": volume_today,
        "avg_volume_20d_shares": avg_volume,
        "volume_vs_average_ratio": volume_ratio,
        "avg_daily_value_idr_20d": avg_value,
        "index_name": getattr(market_context, "index_name", None) if market_context else None,
        "index_change_percent": (
            getattr(market_context, "index_change_percent", None) if market_context else None
        ),
        "index_trend": getattr(market_context, "index_trend", None) if market_context else None,
        "foreign_status": getattr(foreign_flow, "foreign_status", None) if foreign_flow else None,
        "foreign_flow_1m": _period(foreign_flow, "monthly_1m"),
        "foreign_flow_3m": _period(foreign_flow, "three_month_3m"),
        "system_spread_percent": (
            _optional_float_val(_orderbook_field(orderbook, "spread_percent"))
        ),
        "system_bid_ask_ratio": (
            _optional_float_val(_orderbook_field(orderbook, "bid_ask_ratio"))
        ),
        "system_total_bid_lots": (
            _optional_int_val(_orderbook_field(orderbook, "total_bid_lots"))
        ),
        "system_total_ask_lots": (
            _optional_int_val(_orderbook_field(orderbook, "total_ask_lots"))
        ),
        "ma20": _optional_float_val(_tech_field(computed_tech, "ma20")),
        "ma50": _optional_float_val(_tech_field(computed_tech, "ma50")),
        "ma200": _optional_float_val(_tech_field(computed_tech, "ma200")),
        "rsi14": _optional_float_val(_tech_field(computed_tech, "rsi14")),
        "atr14": _optional_float_val(_tech_field(computed_tech, "atr14")),
        "high_52w": _optional_float_val(_tech_field(computed_tech, "high_52w")),
        "low_52w": _optional_float_val(_tech_field(computed_tech, "low_52w")),
        "ma_alignment": (
            str(_tech_field(computed_tech, "ma_alignment"))
            if _tech_field(computed_tech, "ma_alignment") is not None
            else None
        ),
        "key_supports": _clean_float_list(_tech_field(computed_tech, "key_supports")),
        "key_resistances": _clean_float_list(_tech_field(computed_tech, "key_resistances")),
    }

    if not any(value is not None for value in facts.values() if value != facts["captured_at"]):
        return None
    return facts


def _profile_field(profile: Any, key: str) -> Any:
    if profile is None:
        return None
    if isinstance(profile, dict):
        return profile.get(key)
    return getattr(profile, key, None)


def _optional_str_val(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned if cleaned else None
    return str(value).strip() or None


def _orderbook_field(orderbook: Any, key: str) -> Any:
    if orderbook is None:
        return None
    if isinstance(orderbook, dict):
        return orderbook.get(key)
    return getattr(orderbook, key, None)


def _tech_field(computed_tech: Any, key: str) -> Any:
    if computed_tech is None:
        return None
    if isinstance(computed_tech, dict):
        return computed_tech.get(key)
    return getattr(computed_tech, key, None)


def _optional_float_val(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int_val(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clean_float_list(value: Any) -> list[float] | None:
    if value is None or not isinstance(value, (list, tuple)):
        return None
    try:
        return [float(x) for x in value]
    except (TypeError, ValueError):
        return None


def _period(foreign_flow: Any, attribute: str) -> dict[str, Any] | None:
    if foreign_flow is None:
        return None
    period = getattr(foreign_flow, attribute, None)
    if period is None:
        return None
    return {
        "net_shares": getattr(period, "net_shares", None),
        "net_value_idr": getattr(period, "net_value_idr", None),
    }


def _average_recent(history: Any, attribute: str) -> float | None:
    if history is None:
        return None
    bars = getattr(history, "recent_bars", None) or []
    values: list[float] = []
    for bar in bars:
        raw_val = bar.get(attribute) if isinstance(bar, dict) else getattr(bar, attribute, None)
        if raw_val is not None and raw_val > 0:
            try:
                values.append(float(raw_val))
            except (TypeError, ValueError):
                continue
    window = values[-_RECENT_VOLUME_WINDOW:]
    if not window:
        return None
    return round(sum(window) / len(window), 2)


def _average_recent_volume(history: Any) -> float | None:
    return _average_recent(history, "volume")


def _average_recent_value(history: Any) -> float | None:
    return _average_recent(history, "value")
