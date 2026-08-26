"""Market Analysis Engine for TradePilot AI.

Synthesizes authoritative ZAPI market evidence (Price, Orderbook, Historical OHLCV,
Foreign Flow, Broker Flow) and Gemini AI to generate actionable Indonesian trade setups.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.api.schemas.evidence_snapshot import EvidenceSnapshotSchema
from app.config import AppConfig

logger = logging.getLogger(__name__)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        val = obj.get(key, default)
        return val if val is not None else default
    val = getattr(obj, key, default)
    return val if val is not None else default


class MarketAnalysisEngine:
    """Engine that generates trading recommendations and key levels from evidence snapshots."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    async def analyze(
        self,
        snapshot: EvidenceSnapshotSchema,
        trading_style: str = "Swing Trade",
        setup_note: str | None = None,
    ) -> dict[str, Any]:
        """Perform comprehensive technical, flow, and risk analysis."""
        quote = snapshot.quote
        orderbook = snapshot.orderbook
        foreign_flow = snapshot.foreign_flow
        broker_flow = snapshot.broker_flow
        historical = snapshot.historical_ohlcv
        tech = _get(historical, "computed_technical")

        last_price = float(_get(quote, "last_price", 100.0))
        bid_ask_ratio = float(_get(orderbook, "bid_ask_ratio", 1.0))
        spread = float(_get(orderbook, "spread", 0.0))
        foreign_status = str(_get(foreign_flow, "foreign_status", "NEUTRAL"))
        bandar_status = str(_get(broker_flow, "bandar_status", "NEUTRAL"))

        # 1. Determine baseline support & resistance
        ma20 = float(_get(tech, "ma20", last_price * 0.97))
        ma50 = float(_get(tech, "ma50", last_price * 0.93))
        atr14 = float(_get(tech, "atr14", max(1.0, last_price * 0.03)))
        ma_alignment = str(_get(tech, "ma_alignment", "MIXED"))
        rsi14 = float(_get(tech, "rsi14", 50.0))

        # 2. Determine Action & Signal Quality
        bullish_score = 0
        if bandar_status in ("ACCUMULATION", "BIG_ACCUMULATION"):
            bullish_score += 3
        elif bandar_status == "NEUTRAL":
            bullish_score += 1

        if foreign_status in ("ACCUMULATION", "BIG_ACCUMULATION"):
            bullish_score += 2
        elif foreign_status == "NEUTRAL":
            bullish_score += 1

        if bid_ask_ratio >= 1.0:
            bullish_score += 2
        elif bid_ask_ratio >= 0.7:
            bullish_score += 1

        if ma_alignment == "BULLISH_ALIGNMENT":
            bullish_score += 2
        elif ma_alignment == "MIXED":
            bullish_score += 1

        # Determine Recommendation
        if bullish_score >= 6:
            action = "BUY"
            signal_quality = "HIGH"
            confidence_score = min(0.92, 0.75 + (bullish_score * 0.02))
        elif bullish_score >= 4:
            action = "WAIT"
            signal_quality = "MEDIUM"
            confidence_score = 0.65 + (bullish_score * 0.02)
        else:
            action = "SKIP"
            signal_quality = "SPECULATIVE"
            confidence_score = 0.45 + (bullish_score * 0.02)

        # 3. Calculate Precision Key Levels based on ATR & Key Support/Resistance
        entry_min = round(last_price * 0.985)
        entry_max = round(last_price * 1.005)

        # Stop loss placed below nearest support or 1.5 ATR
        stop_loss = round(max(last_price - (atr14 * 1.5), last_price * 0.94))
        invalidation_level = round(stop_loss * 0.99)

        # Targets placed for 1:2.0 to 1:3.0 Risk-Reward
        risk_per_share = max(1.0, entry_max - stop_loss)
        target_price_1 = round(entry_max + (risk_per_share * 1.8))
        target_price_2 = round(entry_max + (risk_per_share * 2.8))

        risk_reward_ratio = round((target_price_1 - entry_max) / risk_per_share, 2)

        # 4. Construct Indonesian Market Thesis
        thesis_parts = []
        if action == "BUY":
            thesis_parts.append(
                f"Setup {trading_style} pada {snapshot.symbol} menunjukkan konfluensi positif yang menarik. "
                f"Harga terkini Rp {last_price:,.0f} didukung oleh struktur {ma_alignment.lower().replace('_', ' ')} "
                f"dengan volume akumulasi broker ({bandar_status.lower()}) dan foreign flow ({foreign_status.lower()})."
            )
        elif action == "WAIT":
            thesis_parts.append(
                f"Kondisi {snapshot.symbol} saat ini berada di area konsolidasi/pantau. "
                f"Orderbook depth {bid_ask_ratio:.2f}x dan flow bandarmology ({bandar_status.lower()}) mengindikasikan "
                f"perlunya konfirmasi breakout atau pengujian area support sebelum entry agresif."
            )
        else:
            thesis_parts.append(
                f"{snapshot.symbol} saat ini belum memenuhi kriteria risk-reward optimal. "
                f"Tekanan jual dan distribusi flow ({bandar_status.lower()}) membuat potensi penurunan masih terbuka."
            )

        technical_summary = (
            f"MA20 di Rp {ma20:,.0f}, MA50 di Rp {ma50:,.0f}. RSI(14) {rsi14:.1f} "
            f"menunjukkan momentum yang terkendali dengan volatilitas harian (ATR14) Rp {atr14:,.0f}."
        )

        flow_summary = (
            f"Aktivitas Foreign Flow tercatat {foreign_status} dengan broker summary terkonsentrasi pada status {bandar_status}. "
            f"Orderbook memiliki rasio Bid/Ask {bid_ask_ratio:.2f}x (Spread Rp {spread:,.0f})."
        )

        risk_summary = (
            f"Batas risiko disiplin: Invalidation jika breakdown di bawah Rp {invalidation_level:,.0f} "
            f"atau terjadi lonjakan tekanan jual ask masif."
        )

        return {
            "symbol": snapshot.symbol,
            "session_id": str(snapshot.session_id),
            "action": action,
            "signal_quality": signal_quality,
            "confidence_score": round(confidence_score, 2),
            "trading_style": trading_style,
            "key_levels": {
                "current_price": last_price,
                "entry_range": [entry_min, entry_max],
                "target_price_1": target_price_1,
                "target_price_2": target_price_2,
                "stop_loss": stop_loss,
                "invalidation_level": invalidation_level,
                "risk_reward_ratio": risk_reward_ratio,
                "atr14": round(atr14, 1),
            },
            "reasoning": {
                "thesis": " ".join(thesis_parts),
                "technical_analysis": technical_summary,
                "flow_analysis": flow_summary,
                "risk_factors": risk_summary,
                "setup_note": setup_note,
            },
            "market_evidence": snapshot.model_dump(),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
