"""Evidence Delta service for TradePilot AI.

Calculates mathematical and behavioral shifts between two point-in-time snapshots
to power contextual, razor-sharp Update Analyses for LLMs.
"""

from __future__ import annotations

from datetime import datetime
from app.api.schemas.evidence_snapshot import (
    BrokerFlowDelta,
    EvidenceDeltaSchema,
    EvidenceSnapshotSchema,
    ForeignFlowDelta,
    OrderbookDelta,
    PriceDelta,
)


class EvidenceDeltaCalculator:
    """Computes differences between base snapshot (N-1) and current snapshot (N)."""

    @classmethod
    def calculate_delta(
        cls, base: EvidenceSnapshotSchema, current: EvidenceSnapshotSchema
    ) -> EvidenceDeltaSchema:
        # Calculate time elapsed
        try:
            t_base = datetime.fromisoformat(base.captured_at)
            t_curr = datetime.fromisoformat(current.captured_at)
            elapsed_mins = max(1, int((t_curr - t_base).total_seconds() / 60))
        except Exception:
            elapsed_mins = 1

        # 1. Price Delta
        p_prev = base.quote.last_price
        p_curr = current.quote.last_price
        p_diff = p_curr - p_prev
        p_pct = round((p_diff / p_prev * 100), 2) if p_prev > 0 else 0.0

        price_delta = PriceDelta(
            previous_price=p_prev,
            current_price=p_curr,
            diff=p_diff,
            percent=p_pct,
        )

        # 2. Orderbook Delta
        prev_ratio = base.orderbook.bid_ask_ratio
        curr_ratio = current.orderbook.bid_ask_ratio
        if curr_ratio > prev_ratio + 0.15:
            ob_trend = "BID_PRESSURE_STRENGTHENING"
        elif curr_ratio < prev_ratio - 0.15:
            ob_trend = "OFFER_PRESSURE_INCREASING"
        else:
            ob_trend = "BALANCED_OR_STABLE"

        orderbook_delta = OrderbookDelta(
            previous_bid_ask_ratio=prev_ratio,
            current_bid_ask_ratio=curr_ratio,
            bid_pressure_trend=ob_trend,
        )

        # 3. Foreign Flow Delta
        prev_ff_shares = base.foreign_flow.today_1d.net_shares if base.foreign_flow.today_1d else 0
        curr_ff_shares = current.foreign_flow.today_1d.net_shares if current.foreign_flow.today_1d else 0
        ff_diff = curr_ff_shares - prev_ff_shares

        if ff_diff > 1_000_000:
            ff_status = "FOREIGN_ACCUMULATION_ACCELERATING"
        elif ff_diff < -1_000_000:
            ff_status = "FOREIGN_DISTRIBUTION_DETECTED"
        else:
            ff_status = "FOREIGN_FLOW_STEADY"

        foreign_flow_delta = ForeignFlowDelta(
            additional_net_shares=ff_diff,
            status=ff_status,
        )

        # 4. Broker Flow Delta
        lead_buyer = current.broker_flow.top_buyers[0].broker if current.broker_flow.top_buyers else None
        prev_lead_lots = base.broker_flow.top_buyers[0].lots if base.broker_flow.top_buyers else 0
        curr_lead_lots = current.broker_flow.top_buyers[0].lots if current.broker_flow.top_buyers else 0
        added_lots = curr_lead_lots - prev_lead_lots

        if base.broker_flow.bandar_status != current.broker_flow.bandar_status:
            bandar_shift = f"CHANGED_FROM_{base.broker_flow.bandar_status}_TO_{current.broker_flow.bandar_status}"
        else:
            bandar_shift = f"REMAINS_{current.broker_flow.bandar_status}"

        broker_flow_delta = BrokerFlowDelta(
            lead_buyer=lead_buyer,
            lead_buyer_added_lots=added_lots if added_lots > 0 else None,
            bandar_status_shift=bandar_shift,
        )

        # 5. Key Event Synthesis
        events: list[str] = []
        if p_diff > 0:
            events.append(f"Harga menguat +Rp {int(p_diff)} (+{p_pct}%) ke Rp {int(p_curr)}.")
        elif p_diff < 0:
            events.append(f"Harga terkoreksi -Rp {int(abs(p_diff))} ({p_pct}%) ke Rp {int(p_curr)}.")
        else:
            events.append(f"Harga stabil di level Rp {int(p_curr)}.")

        if ob_trend == "BID_PRESSURE_STRENGTHENING":
            events.append(f"Antrean bid menebal, rasio bid/ask naik ke {curr_ratio:.2f}x.")
        elif ob_trend == "OFFER_PRESSURE_INCREASING":
            events.append(f"Antrean offer menekan, rasio bid/ask turun ke {curr_ratio:.2f}x.")

        if ff_diff > 500_000:
            events.append(f"Asing menambah net buy +{ff_diff // 100:,} lot dalam {elapsed_mins} menit terakhir.")
        elif ff_diff < -500_000:
            events.append(f"Asing mencatatkan net sell {abs(ff_diff) // 100:,} lot dalam {elapsed_mins} menit terakhir.")

        return EvidenceDeltaSchema(
            base_snapshot_id=base.snapshot_id,
            current_snapshot_id=current.snapshot_id,
            time_elapsed_minutes=elapsed_mins,
            price_delta=price_delta,
            orderbook_delta=orderbook_delta,
            foreign_flow_delta=foreign_flow_delta,
            broker_flow_delta=broker_flow_delta,
            key_events=events,
        )
