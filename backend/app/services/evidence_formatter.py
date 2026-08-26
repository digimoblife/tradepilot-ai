"""Evidence Formatter service for TradePilot AI.

Formats canonical EvidenceSnapshotSchema and EvidenceDeltaSchema into clean,
compact, and authoritative Markdown tables for LLM prompt injection.
"""

from __future__ import annotations

from app.api.schemas.evidence_snapshot import EvidenceDeltaSchema, EvidenceSnapshotSchema


class EvidenceFormatter:
    """Serializes snapshots into compact tabular Markdown representations."""

    @classmethod
    def format_snapshot_to_markdown(cls, s: EvidenceSnapshotSchema) -> str:
        q = s.quote
        ob = s.orderbook
        tech = s.historical_ohlcv.computed_technical
        ff = s.foreign_flow
        bf = s.broker_flow
        mc = s.market_context

        # 1. Market Quote Block
        quote_text = (
            f"### 1. REAL-TIME MARKET QUOTE\n"
            f"- Ticker: {s.symbol} ({s.market}) | Waktu Snapshot: {s.captured_at}\n"
            f"- Last Price: Rp {q.last_price:,.0f} ({q.change:+,.0f} / {q.change_percent:+.2f}%) | Prev Close: Rp {q.previous_close:,.0f}\n"
            f"- Open: {q.open:,.0f} | High: {q.high:,.0f} | Low: {q.low:,.0f} | Vol: {q.volume_lots:,.0f} lot | Val: Rp {q.value_idr:,.0f} | Freq: {q.frequency:,}x\n"
        )
        if q.pe_ratio or q.pbv_ratio:
            quote_text += f"- P/E: {q.pe_ratio or 'N/A'}x | PBV: {q.pbv_ratio or 'N/A'}x\n"

        # 2. Orderbook Block
        ob_text = (
            f"\n### 2. ORDERBOOK MICROSTRUCTURE (Provider: {s.providers_used.get('orderbook', 'PLUANG')})\n"
            f"- Best Bid: Rp {ob.best_bid:,.0f} | Best Offer: Rp {ob.best_ask:,.0f} | Spread: Rp {ob.spread:,.0f} ({ob.spread_percent:.2f}%)\n"
            f"- Total Bid Depth: {ob.total_bid_lots:,} lot ({ob.bid_percent}%) vs Total Offer Depth: {ob.total_ask_lots:,} lot ({ob.ask_percent}%)\n"
            f"- Bid/Ask Ratio: {ob.bid_ask_ratio:.2f}x (Tekanan Beli > Jual jika > 1.0)\n"
            f"Top 3 Antrean Orderbook:\n"
            f"| Bid Lots | Bid Price | Offer Price | Offer Lots |\n"
            f"| :--- | :--- | :--- | :--- |\n"
        )
        for i in range(min(3, max(len(ob.bids), len(ob.asks)))):
            b_lot = f"{ob.bids[i].lots:,}" if i < len(ob.bids) else "-"
            b_px = f"{ob.bids[i].price:,.0f}" if i < len(ob.bids) else "-"
            a_px = f"{ob.asks[i].price:,.0f}" if i < len(ob.asks) else "-"
            a_lot = f"{ob.asks[i].lots:,}" if i < len(ob.asks) else "-"
            ob_text += f"| {b_lot} | {b_px} | {a_px} | {a_lot} |\n"

        # 3. Technicals Block
        tech_text = (
            f"\n### 3. TECHNICAL & PRICE ACTION (IDX - {s.historical_ohlcv.horizon_days} Hari Bursa)\n"
            f"- Moving Averages: MA20: {tech.get('ma20') or 'N/A'} | MA50: {tech.get('ma50') or 'N/A'} | MA200: {tech.get('ma200') or 'N/A'} -> Alignment: {tech.get('ma_alignment', 'UNKNOWN')}\n"
            f"- Momentum: RSI(14): {tech.get('rsi14') or 'N/A'} | ATR(14): {tech.get('atr14') or 'N/A'}\n"
            f"- 52-Week Range: Low {tech.get('low_52w') or 'N/A'} - High {tech.get('high_52w') or 'N/A'}\n"
            f"- Key Support Levels: {', '.join(str(int(x)) for x in tech.get('key_supports', [])) or 'None'}\n"
            f"- Key Resistance Levels: {', '.join(str(int(x)) for x in tech.get('key_resistances', [])) or 'None'}\n"
        )

        # 4. Foreign Flow Block
        today_ff_lots = (ff.today_1d.net_shares // 100) if ff.today_1d else 0
        today_ff_val = ff.today_1d.net_value_idr if ff.today_1d else 0
        w1_ff_lots = (ff.weekly_1w.net_shares // 100) if ff.weekly_1w else 0
        m1_ff_lots = (ff.monthly_1m.net_shares // 100) if ff.monthly_1m else 0
        ff_text = (
            f"\n### 4. FOREIGN FLOW (Smart Money / Asing)\n"
            f"- Today (1D): Net {'Buy' if today_ff_lots >= 0 else 'Sell'} {today_ff_lots:+,} lot (Rp {today_ff_val:+,.0f})\n"
            f"- 1-Week (1W): Net {'Buy' if w1_ff_lots >= 0 else 'Sell'} {w1_ff_lots:+,} lot\n"
            f"- 1-Month (1M): Net {'Buy' if m1_ff_lots >= 0 else 'Sell'} {m1_ff_lots:+,} lot\n"
            f"- Status Akumulasi Asing: {ff.foreign_status}\n"
        )

        # 5. Broker Flow / Bandarmology Block
        buyers_summary = ", ".join(
            f"{b.broker} ({b.lots:,} lot @ {b.avg_price:,.0f})" for b in bf.top_buyers[:3]
        ) or "None"
        sellers_summary = ", ".join(
            f"{s.broker} ({s.lots:,} lot @ {s.avg_price:,.0f})" for s in bf.top_sellers[:3]
        ) or "None"
        bf_text = (
            f"\n### 5. BROKER FLOW 1D (Bandarmology)\n"
            f"- Top 3 Buyer Concentration: {bf.top3_buyer_concentration_percent:.1f}% vs Top 3 Seller Concentration: {bf.top3_seller_concentration_percent:.1f}%\n"
            f"- Status Bandar: {bf.bandar_status}\n"
            f"- Top 3 Buyers: {buyers_summary}\n"
            f"- Top 3 Sellers: {sellers_summary}\n"
        )

        # 6. Market Context
        mc_text = (
            f"\n### 6. MARKET CONTEXT (IHSG)\n"
            f"- {mc.index_name} ({mc.index_code}): {mc.index_price or 'N/A'} ({mc.index_change_percent:+.2f}%) -> {mc.index_trend}\n"
        )

        return quote_text + ob_text + tech_text + ff_text + bf_text + mc_text

    @classmethod
    def format_delta_to_markdown(cls, d: EvidenceDeltaSchema) -> str:
        events_str = "\n".join(f"- {e}" for e in d.key_events)
        return (
            f"### EVIDENCE DELTA (Perubahan Antara Snapshot #{d.base_snapshot_id} -> #{d.current_snapshot_id})\n"
            f"- Waktu Berlalu: {d.time_elapsed_minutes} menit\n"
            f"- Pergerakan Harga: Rp {d.price_delta.previous_price:,.0f} -> Rp {d.price_delta.current_price:,.0f} ({d.price_delta.diff:+,.0f} / {d.price_delta.percent:+.2f}%)\n"
            f"- Pergeseran Orderbook: Rasio Bid/Ask {d.orderbook_delta.previous_bid_ask_ratio:.2f}x -> {d.orderbook_delta.current_bid_ask_ratio:.2f}x ({d.orderbook_delta.bid_pressure_trend})\n"
            f"- Aliran Dana Asing: Tambahan net foreign {int(d.foreign_flow_delta.additional_net_shares // 100):+,} lot ({d.foreign_flow_delta.status})\n"
            f"- Bandarmology Shift: {d.broker_flow_delta.bandar_status_shift}\n"
            f"\nPeristiwa Utama:\n{events_str}\n"
        )
