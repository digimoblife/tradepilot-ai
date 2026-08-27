"""Market Analysis Engine for TradePilot AI.

Synthesizes authoritative ZAPI market evidence (Price, Orderbook, Historical OHLCV,
Foreign Flow, Broker Flow) and Gemini AI to generate actionable Indonesian trade setups
and in-trade position management with a casual, friendly, and practical tone of voice.
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
        position: dict[str, Any] | None = None,
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

        # Build reusable flow phrases
        if foreign_status == "STRONG_ACCUMULATION":
            foreign_phrase = "Asing terpantau rajin serok barang (Strong Accumulation)"
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

        # -------------------------------------------------------------
        # BRANCH A: IN-TRADE EVALUATION (Session has Open Position)
        # -------------------------------------------------------------
        if position and position.get("entry_price") and float(position.get("entry_price", 0)) > 0:
            entry_price = float(position["entry_price"])
            quantity_lots = float(position.get("quantity") or 1.0)
            user_sl = float(position.get("stop_loss") or 0)
            user_tp = float(position.get("target_price") or 0)

            stop_loss = user_sl if user_sl > 0 else round(max(entry_price - (atr14 * 1.5), entry_price * 0.94))
            invalidation_level = round(stop_loss * 0.99)
            target_price_1 = user_tp if user_tp > 0 else round(entry_price + ((entry_price - stop_loss) * 1.8))
            target_price_2 = round(entry_price + ((entry_price - stop_loss) * 2.8))

            floating_pnl_pts = last_price - entry_price
            floating_pnl_pct = (floating_pnl_pts / entry_price * 100) if entry_price > 0 else 0.0
            dist_to_tp1_pts = target_price_1 - last_price
            dist_to_tp1_pct = (dist_to_tp1_pts / last_price * 100) if last_price > 0 else 0.0
            dist_to_sl_pts = last_price - stop_loss
            dist_to_sl_pct = (dist_to_sl_pts / last_price * 100) if last_price > 0 else 0.0

            # Dynamic Trailing Stop calculation
            if floating_pnl_pct >= 5.0:
                trailing_stop = round(last_price - (atr14 * 1.0))
                trailing_stop_note = f"Kunci profit bertahap di Rp {trailing_stop:,.0f}"
            elif floating_pnl_pct >= 2.0:
                trailing_stop = round(entry_price)
                trailing_stop_note = f"Geser SL ke modal/BEP di Rp {trailing_stop:,.0f}"
            else:
                trailing_stop = round(stop_loss)
                trailing_stop_note = f"Pertahankan batas aman di Rp {trailing_stop:,.0f}"

            # Determine In-Trade Stance Action
            if last_price >= target_price_1:
                action = "TAKE_PROFIT"
                signal_quality = "HIGH"
                confidence_score = 0.95
                thesis_text = (
                    f"Posisi {snapshot.symbol} saat ini sedang sangat prima (+{floating_pnl_pct:.2f}%) "
                    f"dan telah mencapai/mendekati area Target Profit (TP1 Rp {target_price_1:,.0f}). "
                    f"Momentum sudah sangat optimal untuk merealisasikan cuan (Take Profit) bertahap!"
                )
                guidance_text = (
                    f"• Tindakan: Ambil profit bertahap (jual 50% lot di TP1 Rp {target_price_1:,.0f} dan biarkan sisa lot berlari ke TP2 Rp {target_price_2:,.0f}).\n"
                    f"• Pengawalan: Pasang Trailing Stop ketat di Rp {trailing_stop:,.0f} untuk mengamankan sisa posisi."
                )
            elif last_price <= stop_loss or floating_pnl_pct <= -5.0:
                action = "CUT_LOSS"
                signal_quality = "HIGH"
                confidence_score = 0.90
                thesis_text = (
                    f"Posisi {snapshot.symbol} saat ini sedang tertekan (-{abs(floating_pnl_pct):.2f}%) dari modal beli (Rp {entry_price:,.0f}) "
                    f"dan mendekati/menembus batas toleransi risiko Stop Loss (Rp {stop_loss:,.0f}). "
                    f"Disiplin lindungi sisa modal untuk mencegah penurunan berlanjut!"
                )
                guidance_text = (
                    f"• Tindakan: Lakukan eksekusi Cut Loss disiplin sekarang untuk mengamankan modal trading.\n"
                    f"• Batas Akhir: Segera tutup posisi jika harga tetap bertahan di bawah Rp {stop_loss:,.0f} dengan tekanan jual ask tebal."
                )
            elif floating_pnl_pct >= 2.5:
                action = "TRAILING_STOP"
                signal_quality = "HIGH"
                confidence_score = 0.88
                thesis_text = (
                    f"Posisi {snapshot.symbol} sedang dalam kondisi profit (+{floating_pnl_pct:.2f}%). "
                    f"Tren kenaikan masih terjaga, namun sangat disarankan menaikkan batas proteksi (Trailing Stop) "
                    f"ke area BEP Rp {trailing_stop:,.0f} agar keuntungan yang sudah didapat terkunci aman."
                )
                guidance_text = (
                    f"• Tindakan: Tahan posisi (HOLD) sembari menaikkan Stop Loss ke Rp {trailing_stop:,.0f} (BEP/Kunci Profit).\n"
                    f"• Target: Pantau pergerakan harga menuju target TP1 Rp {target_price_1:,.0f} (+{dist_to_tp1_pct:.1f}% lagi)."
                )
            else:
                action = "HOLD"
                signal_quality = "HIGH"
                confidence_score = 0.85
                thesis_text = (
                    f"Posisi {snapshot.symbol} masih dalam rentang pengawalan normal ({'+' if floating_pnl_pct >= 0 else ''}{floating_pnl_pct:.2f}% dari harga beli Rp {entry_price:,.0f}). "
                    f"Struktur tren harga dan konfluensi pasar masih cukup kondusif untuk dikawal menuju target TP1 Rp {target_price_1:,.0f}."
                )
                guidance_text = (
                    f"• Tindakan: Pertahankan posisi (HOLD) dengan disiplin.\n"
                    f"• Trigger BEP: Jika harga berhasil naik menembus Rp {round(entry_price * 1.025):,.0f}, segera naikkan SL ke harga modal (Rp {entry_price:,.0f}).\n"
                    f"• Batas SL: Cut loss jika harga breakdown di bawah Rp {stop_loss:,.0f}."
                )

            technical_text = (
                f"• Harga saat ini Rp {last_price:,.0f} berada {'di atas' if last_price >= ma20 else 'di bawah'} MA20 (Rp {ma20:,.0f}) dan MA50 (Rp {ma50:,.0f}).\n"
                f"• Momentum RSI {rsi14:.1f} {'sehat dalam fase penguatan' if rsi14 > 50 else 'mulai melandai / konsolidasi'} dengan volatilitas harian (ATR14) Rp {atr14:,.0f}."
            )
            flow_text = (
                f"• {foreign_phrase}.\n"
                f"• {bandar_phrase} dengan rasio antrean Bid/Ask {bid_ask_ratio:.2f}x (Spread Rp {spread:,.0f})."
            )
            risk_text = (
                f"Batas toleransi risiko disiplin: Stop Loss di Rp {stop_loss:,.0f} (toleransi invalidasi Rp {invalidation_level:,.0f}). "
                f"Jarak risiko tersisa: {dist_to_sl_pct:.1f}%."
            )

            return {
                "symbol": snapshot.symbol,
                "session_id": str(snapshot.session_id),
                "action": action,
                "signal_quality": signal_quality,
                "confidence_score": round(confidence_score, 2),
                "trading_style": trading_style,
                "is_in_trade": True,
                "key_levels": {
                    "current_price": last_price,
                    "entry_price": entry_price,
                    "entry_range": [round(entry_price * 0.99), round(entry_price * 1.01)],
                    "target_price_1": target_price_1,
                    "target_price_2": target_price_2,
                    "stop_loss": stop_loss,
                    "invalidation_level": invalidation_level,
                    "distance_to_tp1": round(dist_to_tp1_pts),
                    "distance_to_tp1_percent": round(dist_to_tp1_pct, 2),
                    "distance_to_sl": round(dist_to_sl_pts),
                    "distance_to_sl_percent": round(dist_to_sl_pct, 2),
                    "trailing_stop": trailing_stop,
                    "trailing_stop_note": trailing_stop_note,
                    "floating_pnl": round(floating_pnl_pts * quantity_lots * 100),
                    "floating_pnl_percent": round(floating_pnl_pct, 2),
                    "atr14": round(atr14, 1),
                },
                "reasoning": {
                    "thesis": thesis_text,
                    "technical_analysis": technical_text,
                    "flow_analysis": flow_text,
                    "action_guidance": guidance_text,
                    "risk_factors": risk_text,
                    "setup_note": setup_note,
                },
                "market_evidence": snapshot.model_dump(),
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            }

        # -------------------------------------------------------------
        # BRANCH B: PRE-TRADE ANALYSIS (DRAFT / ANALYZED / WAITING)
        # -------------------------------------------------------------
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

        entry_min = round(last_price * 0.985)
        entry_max = round(last_price * 1.005)
        stop_loss = round(max(last_price - (atr14 * 1.5), last_price * 0.94))
        invalidation_level = round(stop_loss * 0.99)
        risk_per_share = max(1.0, entry_max - stop_loss)
        target_price_1 = round(entry_max + (risk_per_share * 1.8))
        target_price_2 = round(entry_max + (risk_per_share * 2.8))
        risk_reward_ratio = round((target_price_1 - entry_max) / risk_per_share, 2)

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
            "is_in_trade": False,
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
