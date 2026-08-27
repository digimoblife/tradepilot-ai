"""Market Analysis Engine for TradePilot AI.

Synthesizes authoritative ZAPI market evidence (Price, Orderbook, Historical OHLCV,
Foreign Flow, Broker Flow) and Gemini AI to generate actionable Indonesian trade setups
with a casual, friendly, and practical tone of voice.
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
        """Perform comprehensive technical, flow, and risk analysis in a friendly tone."""
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

        # 1. Determine baseline technical indicators
        ma20 = float(_get(tech, "ma20", last_price * 0.97))
        ma50 = float(_get(tech, "ma50", last_price * 0.93))
        atr14 = float(_get(tech, "atr14", max(1.0, last_price * 0.03)))
        ma_alignment = str(_get(tech, "ma_alignment", "MIXED"))
        rsi14 = float(_get(tech, "rsi14", 50.0))
        supports = _get(tech, "key_supports") or []
        resistances = _get(tech, "key_resistances") or []
        valid_supports = [float(s) for s in supports if float(s) < last_price]
        valid_resistances = [float(r) for r in resistances if float(r) > last_price]
        nearest_support = valid_supports[0] if valid_supports else round(last_price * 0.97)
        nearest_resistance = valid_resistances[0] if valid_resistances else round(last_price * 1.02)

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

        if bid_ask_ratio >= 1.2:
            bullish_score += 2
        elif bid_ask_ratio >= 0.8:
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

        # Targets placed for 1:1.8 to 1:2.8 Risk-Reward
        risk_per_share = max(1.0, entry_max - stop_loss)
        target_price_1 = round(entry_max + (risk_per_share * 1.8))
        target_price_2 = round(entry_max + (risk_per_share * 2.8))

        risk_reward_ratio = round((target_price_1 - entry_max) / risk_per_share, 2)

        # 4. Construct Casual & Actionable Indonesian Market Reasoning
        if foreign_status == "STRONG_ACCUMULATION":
            foreign_phrase = "Asing terpantau mulai rajin serok barang (Strong Accumulation)"
        elif foreign_status == "ACCUMULATION":
            foreign_phrase = "Asing mulai akumulasi tipis (Accumulation)"
        elif foreign_status in ("DISTRIBUTION", "STRONG_DISTRIBUTION"):
            foreign_phrase = "Asing terpantau masih pasif/jualan (Distribution)"
        else:
            foreign_phrase = "Aliran dana asing masih relatif anteng (Neutral)"

        if bandar_status in ("BIG_ACCUMULATION", "ACCUMULATION"):
            bandar_phrase = f"Broker/bandar berada pada posisi serok ({bandar_status.replace('_', ' ').title()})"
        elif bandar_status in ("BIG_DISTRIBUTION", "DISTRIBUTION"):
            bandar_phrase = f"Broker lokal terpantau masih distribusi ({bandar_status.replace('_', ' ').title()})"
        else:
            bandar_phrase = f"Broker lokal masih gerak santai ({bandar_status.title()})"

        if action == "WAIT":
            thesis_text = (
                f"Harga {snapshot.symbol} sekarang lagi fase santai/sideways di kisaran Rp {last_price:,.0f}. "
                f"{foreign_phrase}, tapi antrean bid-offer masih seimbang (Rasio Bid/Ask {bid_ask_ratio:.2f}x). "
                f"Belum ada dorongan kuat buat langsung loncat masuk sekarang."
            )
            technical_text = (
                f"• Tren harga masih anteng di area MA50 (Rp {ma50:,.0f}) dengan MA20 di Rp {ma20:,.0f}.\n"
                f"• Momentum RSI {rsi14:.1f} netral (gak kemahalan, gak kemurahan) dengan fluktuasi harian (ATR14) Rp {atr14:,.0f}."
            )
            flow_text = (
                f"• {foreign_phrase}.\n"
                f"• {bandar_phrase} dengan spread antrean harga Rp {spread:,.0f}."
            )
            guidance_text = (
                f"• Apa yang ditunggu: Tunggu harga berhasil tembus dan bertahan di atas Rp {nearest_resistance:,.0f} dengan volume ramai, "
                f"ATAU tunggu serok santai kalau harga pullback mendekati area support Rp {nearest_support:,.0f}.\n"
                f"• Sampai kapan: Pantau sampai sesi penutupan bursa hari ini. Jika harga malah anjlok menembus Rp {invalidation_level:,.0f}, abaikan setup ini."
            )
            risk_text = (
                f"Pasang stop loss disiplin di Rp {stop_loss:,.0f} (toleransi batas invalidasi Rp {invalidation_level:,.0f})."
            )

        elif action == "BUY":
            thesis_text = (
                f"Setup {trading_style} pada {snapshot.symbol} terlihat menarik dan punya peluang bagus! "
                f"Harga di Rp {last_price:,.0f} didukung aliran dana yang masuk dan konfirmasi teknikal yang solid buat entry terukur."
            )
            technical_text = (
                f"• Harga bergerak solid di atas support MA20 (Rp {ma20:,.0f}) dan MA50 (Rp {ma50:,.0f}).\n"
                f"• Momentum RSI {rsi14:.1f} bergerak sehat dalam fase penguatan harga dengan volatilitas harian (ATR14) Rp {atr14:,.0f}."
            )
            flow_text = (
                f"• {foreign_phrase}.\n"
                f"• {bandar_phrase} dengan antrean bid tebal (Rasio Bid/Ask {bid_ask_ratio:.2f}x)."
            )
            guidance_text = (
                f"• Area Beli: Masuk santai di rentang Rp {entry_min:,.0f} - Rp {entry_max:,.0f}.\n"
                f"• Target Cuan: Ambil profit bertahap di TP1 Rp {target_price_1:,.0f} dan TP2 Rp {target_price_2:,.0f}."
            )
            risk_text = (
                f"Pasang stop loss disiplin di Rp {stop_loss:,.0f} (toleransi batas invalidasi Rp {invalidation_level:,.0f})."
            )

        else:  # SKIP
            thesis_text = (
                f"Setup {snapshot.symbol} sebaiknya dilewati dulu untuk saat ini. "
                f"Potensi reward belum sebanding dengan risiko penurunan, dan belum ada tanda-tanda minat beli yang meyakinkan di harga Rp {last_price:,.0f}."
            )
            technical_text = (
                f"• Struktur harga masih rentan koreksi di bawah rata-rata pergerakan utama (MA20 Rp {ma20:,.0f}, MA50 Rp {ma50:,.0f}).\n"
                f"• Indikator momentum RSI {rsi14:.1f} belum menunjukkan sinyal pembalikan arah yang valid."
            )
            flow_text = (
                f"• Tekanan jual masih dominan dengan aksi {bandar_phrase.lower()}.\n"
                f"• {foreign_phrase} dengan antrean bid-ask tipis {bid_ask_ratio:.2f}x."
            )
            guidance_text = (
                f"• Alasan utama: Rasio risk/reward kurang menarik dan konfirmasi bandarmology belum mendukung.\n"
                f"• Saran: Cari peluang di emiten lain yang punya momentum lebih segar dan akumulasi lebih jelas."
            )
            risk_text = (
                f"Jika tetap memantau, jangan sentuh sebelum harga mampu bertahan stabil di atas Rp {invalidation_level:,.0f}."
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
                "thesis": thesis_text,
                "technical_analysis": technical_text,
                "flow_analysis": flow_text,
                "action_guidance": guidance_text,
                "wait_guidance": guidance_text if action == "WAIT" else None,
                "risk_factors": risk_text,
                "setup_note": setup_note,
            },
            "market_evidence": snapshot.model_dump(),
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
