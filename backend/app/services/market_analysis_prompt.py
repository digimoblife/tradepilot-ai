"""Prompt loading and evidence-table formatting for MarketAnalysisEngine.

Loads the versioned Gemini prompts from ``prompts/market_analysis/*.md`` and
formats the confirmed, system-computed evidence (Pluang, IDX, Stockbit,
Investing via the ZAPI gateway) into the compact tabular block those prompts
expect. This module never calls Gemini itself — see
``app.services.market_analysis_engine``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_PROMPTS_ROOT = Path(__file__).resolve().parents[3] / "prompts" / "market_analysis"


class PromptFileNotFoundError(Exception):
    pass


def load_prompt(name: str) -> str:
    """Load an approved market-analysis prompt file by name (without extension)."""
    path = _PROMPTS_ROOT / f"{name}.md"
    if not path.is_file():
        raise PromptFileNotFoundError(f"Market analysis prompt file is missing: {path.name}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise PromptFileNotFoundError(f"Market analysis prompt file is empty: {path.name}")
    return text


def _na(value: Any, suffix: str = "") -> str:
    """Render a value for the evidence table, or the explicit unavailable marker."""
    if value is None or value == "" or (isinstance(value, float) and value != value):
        return "Tidak tersedia"
    if isinstance(value, float):
        return f"{value:,.2f}{suffix}"
    if isinstance(value, int):
        return f"{value:,}{suffix}"
    return f"{value}{suffix}"


def _fmt_period(period: Any) -> str:
    if period is None:
        return "Tidak tersedia"
    net_shares = getattr(period, "net_shares", None)
    net_value = getattr(period, "net_value_idr", None)
    return f"{_na(net_shares, ' lembar')} (Rp {_na(net_value)})"


def _fmt_levels(levels: Any) -> str:
    if not levels:
        return "Tidak tersedia"
    return ", ".join(f"Rp {v:,.0f}" for v in levels)


def _fmt_top_brokers(items: Any) -> str:
    if not items:
        return "Tidak tersedia"
    parts = []
    for item in list(items)[:3]:
        broker = getattr(item, "broker", None) or "-"
        value_idr = getattr(item, "value_idr", None) or 0.0
        share = getattr(item, "market_share_percent", None)
        share_txt = f", porsi {share:.1f}%" if share else ""
        parts.append(f"{broker} (Rp {value_idr:,.0f}{share_txt})")
    return "; ".join(parts)


def _fmt_orderbook_levels(bids: Any, asks: Any) -> str:
    if not bids and not asks:
        return "Tidak tersedia"
    rows = []
    for bid, ask in zip(list(bids or [])[:3], list(asks or [])[:3]):
        rows.append(
            f"{bid.lots:,} lot @ Rp {bid.price:,.0f} | Rp {ask.price:,.0f} @ {ask.lots:,} lot"
        )
    return "; ".join(rows) if rows else "Tidak tersedia"


def _fmt_recent_bars(bars: Any) -> str:
    if not bars:
        return "Tidak tersedia"
    rows = []
    for bar in list(bars)[:3]:
        rows.append(
            f"{bar.date}: O{bar.open:,.0f} H{bar.high:,.0f} L{bar.low:,.0f} "
            f"C{bar.close:,.0f} Vol{bar.volume:,}"
        )
    return " | ".join(rows)


def build_pre_trade_evidence_table(
    *,
    snapshot: Any,
    trading_style: str,
    setup_note: str | None,
    tech: dict[str, Any] | None,
) -> str:
    """Build the tabular evidence block for the pre-trade (no position) prompt."""
    quote = snapshot.quote
    orderbook = snapshot.orderbook
    historical = snapshot.historical_ohlcv
    foreign_flow = snapshot.foreign_flow
    broker_flow = snapshot.broker_flow
    market_context = snapshot.market_context
    profile = getattr(snapshot, "company_profile", None)
    tech = tech or {}

    return f"""\
### 1. IDENTITAS & PROFIL EMITEN
- Ticker: {snapshot.symbol} | Sektor: {_na(getattr(profile, "sector", None))} | Sub-Sektor: {_na(getattr(profile, "sub_sector", None))}
- Gaya Trading User: {trading_style} | Catatan User: {_na(setup_note)}

### 2. VALUASI & FUNDAMENTAL (Investing)
- P/E Ratio: {_na(getattr(profile, "pe_ratio", None), "x")} | P/BV Ratio: {_na(getattr(profile, "pbv_ratio", None), "x")} | Market Cap: {_na(getattr(quote, "market_cap", None))}
- EPS (TTM): Rp {_na(getattr(profile, "eps_ttm", None))} | Revenue: {_na(getattr(profile, "revenue", None))}
- Dividend: Rp {_na(getattr(profile, "dividend_per_share", None))}/lembar (Yield {_na(getattr(profile, "dividend_yield_percent", None), "%")})
- Beta vs IHSG: {_na(getattr(profile, "beta", None))} | Return 1 Tahun: {_na(getattr(profile, "one_year_return_percent", None), "%")}
- Rating Teknikal Analyst (Investing "Technical Summary"): {_na(getattr(profile, "technical_summary", None))}
- Tanggal Rilis Laporan Keuangan Berikutnya: {_na(getattr(profile, "next_earnings_date", None))}

### 3. HARGA REAL-TIME & ORDERBOOK (Pluang)
- Last: Rp {_na(quote.last_price)} ({quote.change:+,.0f} / {quote.change_percent:+.2f}%) | Prev Close: Rp {_na(quote.previous_close)}
- Open: {_na(quote.open)} | High: {_na(quote.high)} | Low: {_na(quote.low)}
- Volume: {_na(quote.volume_shares, " lembar")} ({_na(quote.volume_lots, " lot")}) | Value: Rp {_na(quote.value_idr)} | Freq: {_na(quote.frequency, "x")}
- Best Bid: Rp {_na(orderbook.best_bid)} ({_na(orderbook.total_bid_lots, " lot total")}) | Best Ask: Rp {_na(orderbook.best_ask)} ({_na(orderbook.total_ask_lots, " lot total")})
- Spread: Rp {_na(orderbook.spread)} ({_na(orderbook.spread_percent, "%")}) | Bid/Ask Ratio: {_na(orderbook.bid_ask_ratio, "x")} ({_na(orderbook.bid_percent, "%")} vs {_na(orderbook.ask_percent, "%")})
- Top 3 antrean bid/ask: {_fmt_orderbook_levels(orderbook.bids, orderbook.asks)}

### 4. TEKNIKAL & PRICE ACTION ({_na(historical.horizon_days)} Hari Bursa) (IDX)
- Moving Averages: MA20 {_na(tech.get("ma20"))} | MA50 {_na(tech.get("ma50"))} | MA200 {_na(tech.get("ma200"))} -> {_na(tech.get("ma_alignment"))}
- RSI(14): {_na(tech.get("rsi14"))} | ATR(14): Rp {_na(tech.get("atr14"))}
- 52-Week Range: Rp {_na(tech.get("low_52w"))} - Rp {_na(tech.get("high_52w"))}
- Key Support: {_fmt_levels(tech.get("key_supports"))} | Key Resistance: {_fmt_levels(tech.get("key_resistances"))}
- 3 bar OHLCV terakhir: {_fmt_recent_bars(historical.recent_bars)}

### 5. FOREIGN FLOW (IDX)
- Hari Ini (1D): {_fmt_period(foreign_flow.today_1d)} | 1 Minggu: {_fmt_period(foreign_flow.weekly_1w)} | 1 Bulan: {_fmt_period(foreign_flow.monthly_1m)} | 3 Bulan: {_fmt_period(foreign_flow.three_month_3m)}
- Status Asing Keseluruhan: {foreign_flow.foreign_status}

### 6. BANDARMOLOGY / BROKER SUMMARY (Pluang)
- Status Bandar: {broker_flow.bandar_status}
- Top 3 Buyer Concentration: {_na(broker_flow.top3_buyer_concentration_percent, "%")} | Top 3 Seller Concentration: {_na(broker_flow.top3_seller_concentration_percent, "%")}
- Top Buyers: {_fmt_top_brokers(broker_flow.top_buyers)} | Top Sellers: {_fmt_top_brokers(broker_flow.top_sellers)}

### 7. KONTEKS PASAR (IDX)
- IHSG: {_na(market_context.index_price)} ({_na(market_context.index_change_percent, "%")}) -> {market_context.index_trend}
"""


def build_in_trade_evidence_table(
    *,
    snapshot: Any,
    position: dict[str, Any],
    tech: dict[str, Any] | None,
    current_price: float,
    entry_price: float,
    stop_loss: float,
    target_price: float,
    floating_pnl_percent: float,
    floating_pnl_idr: float,
    distance_to_tp1_percent: float,
    distance_to_tp1_idr: float,
    distance_to_sl_percent: float,
    distance_to_sl_idr: float,
    setup_note: str | None = None,
) -> str:
    """Build the tabular evidence block for the in-trade (open position) prompt."""
    quote = snapshot.quote
    orderbook = snapshot.orderbook
    historical = snapshot.historical_ohlcv
    foreign_flow = snapshot.foreign_flow
    broker_flow = snapshot.broker_flow
    market_context = snapshot.market_context
    profile = getattr(snapshot, "company_profile", None)
    tech = tech or {}

    return f"""\
### 1. POSISI TERKONFIRMASI (User-owned, tidak boleh diubah)
- Ticker: {snapshot.symbol}
- Entry Price: Rp {entry_price:,.0f} | Waktu Entry: {_na(position.get("entry_timestamp"))} | Kuantitas: {_na(position.get("quantity"))} lot
- Stop Loss (User): Rp {stop_loss:,.0f} | Target Price (User): Rp {target_price:,.0f}
- Catatan Setup Awal: {_na(setup_note)}

### 2. STATUS POSISI SAAT INI (dihitung sistem)
- Harga Saat Ini: Rp {current_price:,.0f} | Floating P/L: Rp {floating_pnl_idr:+,.0f} ({floating_pnl_percent:+.2f}%)
- Jarak ke Target: Rp {distance_to_tp1_idr:+,.0f} ({distance_to_tp1_percent:+.2f}%)
- Jarak ke Stop Loss: Rp {distance_to_sl_idr:+,.0f} ({distance_to_sl_percent:+.2f}%)

### 3. VALUASI & FUNDAMENTAL (Investing)
- P/E Ratio: {_na(getattr(profile, "pe_ratio", None), "x")} | P/BV Ratio: {_na(getattr(profile, "pbv_ratio", None), "x")} | Market Cap: {_na(getattr(quote, "market_cap", None))}
- Rating Teknikal Analyst (Investing "Technical Summary"): {_na(getattr(profile, "technical_summary", None))}
- Tanggal Rilis Laporan Keuangan Berikutnya: {_na(getattr(profile, "next_earnings_date", None))}
- Beta vs IHSG: {_na(getattr(profile, "beta", None))}

### 4. HARGA REAL-TIME & ORDERBOOK (Pluang)
- Open: {_na(quote.open)} | High: {_na(quote.high)} | Low: {_na(quote.low)} | Prev Close: {_na(quote.previous_close)}
- Volume: {_na(quote.volume_shares, " lembar")} | Value: Rp {_na(quote.value_idr)}
- Best Bid: Rp {_na(orderbook.best_bid)} ({_na(orderbook.total_bid_lots, " lot")}) | Best Ask: Rp {_na(orderbook.best_ask)} ({_na(orderbook.total_ask_lots, " lot")})
- Spread: Rp {_na(orderbook.spread)} ({_na(orderbook.spread_percent, "%")}) | Bid/Ask Ratio: {_na(orderbook.bid_ask_ratio, "x")}

### 5. TEKNIKAL & PRICE ACTION ({_na(historical.horizon_days)} Hari Bursa) (IDX)
- Moving Averages: MA20 {_na(tech.get("ma20"))} | MA50 {_na(tech.get("ma50"))} | MA200 {_na(tech.get("ma200"))} -> {_na(tech.get("ma_alignment"))}
- RSI(14): {_na(tech.get("rsi14"))} | ATR(14): Rp {_na(tech.get("atr14"))}
- Key Support: {_fmt_levels(tech.get("key_supports"))} | Key Resistance: {_fmt_levels(tech.get("key_resistances"))}

### 6. FOREIGN FLOW (IDX)
- Hari Ini (1D): {_fmt_period(foreign_flow.today_1d)} | 1 Minggu: {_fmt_period(foreign_flow.weekly_1w)} | 1 Bulan: {_fmt_period(foreign_flow.monthly_1m)}
- Status Asing Keseluruhan: {foreign_flow.foreign_status}

### 7. BANDARMOLOGY / BROKER SUMMARY (Pluang)
- Status Bandar: {broker_flow.bandar_status}
- Top 3 Buyer Concentration: {_na(broker_flow.top3_buyer_concentration_percent, "%")} | Top 3 Seller Concentration: {_na(broker_flow.top3_seller_concentration_percent, "%")}

### 8. KONTEKS PASAR (IDX)
- IHSG: {_na(market_context.index_price)} ({_na(market_context.index_change_percent, "%")}) -> {market_context.index_trend}
"""


PRE_TRADE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["BUY", "WAIT", "SKIP"]},
        "signal_quality": {"type": "string", "enum": ["HIGH", "MEDIUM", "SPECULATIVE"]},
        "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
        "key_levels": {
            "type": "object",
            "properties": {
                "current_price": {"type": "number"},
                "entry_range": {
                    "type": "array",
                    "items": {"type": "number"},
                    "minItems": 2,
                    "maxItems": 2,
                },
                "target_price_1": {"type": "number"},
                "target_price_2": {"type": "number"},
                "stop_loss": {"type": "number"},
                "invalidation_level": {"type": "number"},
                "risk_reward_ratio": {"type": "number"},
                "atr14": {"type": "number"},
            },
            "required": [
                "current_price",
                "entry_range",
                "target_price_1",
                "target_price_2",
                "stop_loss",
                "invalidation_level",
                "risk_reward_ratio",
                "atr14",
            ],
        },
        "reasoning": {
            "type": "object",
            "properties": {
                "thesis": {"type": "string"},
                "technical_analysis": {"type": "string"},
                "flow_analysis": {"type": "string"},
                "action_guidance": {"type": "string"},
                "wait_guidance": {"type": ["string", "null"]},
                "risk_factors": {"type": "string"},
            },
            "required": [
                "thesis",
                "technical_analysis",
                "flow_analysis",
                "action_guidance",
                "wait_guidance",
                "risk_factors",
            ],
        },
    },
    "required": ["action", "signal_quality", "confidence_score", "key_levels", "reasoning"],
}

IN_TRADE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["HOLD", "TRAILING_STOP", "TAKE_PROFIT", "CUT_LOSS"],
        },
        "signal_quality": {"type": "string", "enum": ["HIGH", "MEDIUM", "SPECULATIVE"]},
        "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
        "key_levels": {
            "type": "object",
            "properties": {
                "current_price": {"type": "number"},
                "entry_price": {"type": "number"},
                "target_price_1": {"type": "number"},
                "target_price_2": {"type": "number"},
                "stop_loss": {"type": "number"},
                "invalidation_level": {"type": "number"},
                "trailing_stop": {"type": "number"},
                "trailing_stop_note": {"type": "string"},
                "distance_to_tp1_percent": {"type": "number"},
                "distance_to_sl_percent": {"type": "number"},
                "floating_pnl_percent": {"type": "number"},
                "atr14": {"type": "number"},
            },
            "required": [
                "current_price",
                "entry_price",
                "target_price_1",
                "target_price_2",
                "stop_loss",
                "invalidation_level",
                "trailing_stop",
                "trailing_stop_note",
                "distance_to_tp1_percent",
                "distance_to_sl_percent",
                "floating_pnl_percent",
                "atr14",
            ],
        },
        "reasoning": {
            "type": "object",
            "properties": {
                "thesis": {"type": "string"},
                "technical_analysis": {"type": "string"},
                "flow_analysis": {"type": "string"},
                "action_guidance": {"type": "string"},
                "risk_factors": {"type": "string"},
            },
            "required": [
                "thesis",
                "technical_analysis",
                "flow_analysis",
                "action_guidance",
                "risk_factors",
            ],
        },
    },
    "required": ["action", "signal_quality", "confidence_score", "key_levels", "reasoning"],
}
