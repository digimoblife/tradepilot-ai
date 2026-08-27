"""Technical indicator calculations for TradePilot AI.

Calculates deterministic moving averages, RSI, ATR, and support/resistance levels
from canonical OHLCV bar series so LLMs do not need to calculate math.
"""

from __future__ import annotations

from typing import Any


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert any value to float, handling '-', None, and formatted strings."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = val.strip().replace(",", "")
        if not cleaned or cleaned in ("-", "--", "N/A", "null", "None", "nan", "Infinity", "-Infinity"):
            return default
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def calculate_sma(prices: list[float], period: int) -> float | None:
    """Calculate Simple Moving Average."""
    valid_prices = [p for p in prices if p > 0]
    if len(valid_prices) < period:
        return None
    return round(sum(valid_prices[-period:]) / period, 2)


def calculate_rsi(closes: list[float], period: int = 14) -> float | None:
    """Calculate Relative Strength Index (RSI)."""
    valid_closes = [c for c in closes if c > 0]
    if len(valid_closes) <= period:
        return None

    gains: list[float] = []
    losses: list[float] = []

    for i in range(1, len(valid_closes)):
        diff = valid_closes[i] - valid_closes[i - 1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(abs(diff))

    if len(gains) < period:
        return None

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return round(rsi, 2)


def calculate_atr(bars: list[dict[str, Any]], period: int = 14) -> float | None:
    """Calculate Average True Range (ATR)."""
    if len(bars) < period + 1:
        return None

    tr_list: list[float] = []
    for i in range(1, len(bars)):
        high = _safe_float(bars[i].get("high") or bars[i].get("High"))
        low = _safe_float(bars[i].get("low") or bars[i].get("Low"))
        prev_close = _safe_float(bars[i - 1].get("close") or bars[i - 1].get("Close"))

        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_list.append(tr)

    if len(tr_list) < period:
        return None

    atr = sum(tr_list[-period:]) / period
    return round(atr, 2)


def find_swing_levels(bars: list[dict[str, Any]], window: int = 5) -> tuple[list[float], list[float]]:
    """Identify key swing support and resistance levels from historical bars."""
    if len(bars) < window * 2 + 1:
        return [], []

    supports: list[float] = []
    resistances: list[float] = []

    highs = [_safe_float(b.get("high") or b.get("High")) for b in bars]
    lows = [_safe_float(b.get("low") or b.get("Low")) for b in bars]

    for i in range(window, len(bars) - window):
        current_high = highs[i]
        current_low = lows[i]

        if current_high > 0 and current_high == max(highs[i - window : i + window + 1]):
            resistances.append(current_high)
        if current_low > 0 and current_low == min(lows[i - window : i + window + 1]):
            supports.append(current_low)

    # Return top 3 most recent unique levels
    unique_supports = sorted(list(set(supports)), reverse=True)[:3]
    unique_resistances = sorted(list(set(resistances)))[:3]

    return unique_supports, unique_resistances


def compute_technical_summary(bars: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute complete technical summary from daily bars (ordered chronologically oldest to newest)."""
    if not bars:
        return {}

    closes = [_safe_float(b.get("close") or b.get("Close")) for b in bars]
    highs = [_safe_float(b.get("high") or b.get("High")) for b in bars]
    lows = [_safe_float(b.get("low") or b.get("Low")) for b in bars]

    valid_closes = [c for c in closes if c > 0]
    valid_highs = [h for h in highs if h > 0]
    valid_lows = [l for l in lows if l > 0]

    ma20 = calculate_sma(closes, 20)
    ma50 = calculate_sma(closes, 50)
    ma200 = calculate_sma(closes, 200)
    rsi14 = calculate_rsi(closes, 14)
    atr14 = calculate_atr(bars, 14)

    high_52w = max(valid_highs) if valid_highs else None
    low_52w = min(valid_lows) if valid_lows else None

    supports, resistances = find_swing_levels(bars)

    last_price = valid_closes[-1] if valid_closes else None
    ma_alignment = "UNKNOWN"
    if last_price and ma20 and ma50:
        if last_price > ma20 > ma50:
            ma_alignment = "BULLISH_ALIGNMENT"
        elif last_price < ma20 < ma50:
            ma_alignment = "BEARISH_ALIGNMENT"
        else:
            ma_alignment = "MIXED"

    return {
        "ma20": ma20,
        "ma50": ma50,
        "ma200": ma200,
        "rsi14": rsi14,
        "atr14": atr14,
        "high_52w": high_52w,
        "low_52w": low_52w,
        "ma_alignment": ma_alignment,
        "key_supports": supports,
        "key_resistances": resistances,
    }
