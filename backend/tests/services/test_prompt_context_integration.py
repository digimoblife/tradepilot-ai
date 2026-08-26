"""Tests for Fase 4: Tabular Prompt Formatting & Context Building for Gemini LLM.

Validates that EvidenceSnapshot and EvidenceDelta are serialized into clean, authoritative
Markdown tables and structured context without requiring multimodal vision images.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
import uuid

from app.api.schemas.evidence_snapshot import (
    BrokerFlowDomain,
    BrokerItem,
    EvidenceDeltaSchema,
    EvidenceSnapshotSchema,
    ForeignFlowDomain,
    ForeignFlowPeriod,
    HistoricalBar,
    HistoricalDomain,
    MarketContextDomain,
    OrderbookDomain,
    OrderbookLevel,
    PriceDelta,
    QuoteDomain,
)
from app.services.evidence_formatter import EvidenceFormatter


def _create_sample_snapshot() -> EvidenceSnapshotSchema:
    return EvidenceSnapshotSchema(
        snapshot_id="SNP-20260826-BBCA-001",
        session_id=uuid.uuid4(),
        symbol="BBCA",
        market="IDX",
        captured_at="2026-08-26T09:37:12+07:00",
        snapshot_type="INITIAL",
        sequence_number=1,
        providers_used={
            "quote": "PLUANG",
            "orderbook": "PLUANG",
            "historical_ohlcv": "IDX",
            "foreign_flow": "IDX",
            "broker_flow": "PLUANG",
            "market_context": "IDX",
        },
        completeness_status="COMPLETE",
        quote=QuoteDomain(
            last_price=6325.0,
            change=75.0,
            change_percent=1.20,
            previous_close=6250.0,
            open=6275.0,
            high=6350.0,
            low=6250.0,
            volume_shares=45820100,
            volume_lots=458201,
            value_idr=289812000000.0,
            frequency=12840,
            pe_ratio=18.4,
            pbv_ratio=4.1,
            market_cap=1205000000000000.0,
        ),
        orderbook=OrderbookDomain(
            best_bid=6325.0,
            best_ask=6350.0,
            spread=25.0,
            spread_percent=0.39,
            total_bid_lots=184500,
            total_ask_lots=142100,
            bid_ask_ratio=1.30,
            bid_percent=56.5,
            ask_percent=43.5,
            bids=[
                OrderbookLevel(price=6325.0, lots=34200),
                OrderbookLevel(price=6300.0, lots=51000),
                OrderbookLevel(price=6275.0, lots=42100),
            ],
            asks=[
                OrderbookLevel(price=6350.0, lots=28400),
                OrderbookLevel(price=6375.0, lots=46500),
                OrderbookLevel(price=6400.0, lots=67200),
            ],
        ),
        historical_ohlcv=HistoricalDomain(
            horizon_days=130,
            start_date="2026-02-15",
            end_date="2026-08-26",
            computed_technical={
                "ma20": 6210.0,
                "ma50": 6125.0,
                "ma200": 5890.0,
                "rsi14": 58.4,
                "atr14": 85.0,
                "high_52w": 6500.0,
                "low_52w": 5200.0,
                "key_supports": [6250.0, 6100.0, 5950.0],
                "key_resistances": [6350.0, 6425.0, 6500.0],
            },
            recent_bars=[
                HistoricalBar(
                    date="2026-08-26",
                    open=6275.0,
                    high=6350.0,
                    low=6250.0,
                    close=6325.0,
                    volume=45820100,
                    value=289812000000.0,
                )
            ],
        ),
        foreign_flow=ForeignFlowDomain(
            today_1d=ForeignFlowPeriod(
                net_shares=14250000,
                net_value_idr=90131250000.0,
                buy_shares=22100000,
                sell_shares=7850000,
            ),
            weekly_1w=ForeignFlowPeriod(net_shares=48200000, net_value_idr=304500000000.0),
            monthly_1m=ForeignFlowPeriod(net_shares=112500000, net_value_idr=709800000000.0),
            three_month_3m=ForeignFlowPeriod(net_shares=285000000, net_value_idr=1780000000000.0),
            foreign_status="STRONG_ACCUMULATION",
        ),
        broker_flow=BrokerFlowDomain(
            date="2026-08-26",
            is_net=True,
            top3_buyer_concentration_percent=64.2,
            top3_seller_concentration_percent=38.5,
            bandar_status="ACCUMULATION",
            top_buyers=[
                BrokerItem(broker="ZP", lots=131000, value_idr=83200000000.0, avg_price=6351.0),
                BrokerItem(broker="RX", lots=82000, value_idr=51900000000.0, avg_price=6330.0),
                BrokerItem(broker="AK", lots=64000, value_idr=40400000000.0, avg_price=6315.0),
            ],
            top_sellers=[
                BrokerItem(broker="YP", lots=58000, value_idr=36600000000.0, avg_price=6310.0),
                BrokerItem(broker="PD", lots=49000, value_idr=30900000000.0, avg_price=6305.0),
                BrokerItem(broker="CC", lots=35000, value_idr=22100000000.0, avg_price=6315.0),
            ],
        ),
        market_context=MarketContextDomain(
            index_code="COMPOSITE",
            index_name="IHSG",
            index_price=7650.4,
            index_change_percent=0.45,
            index_trend="BULLISH",
        ),
    )


def test_format_snapshot_to_markdown_contains_all_six_domains() -> None:
    snapshot = _create_sample_snapshot()
    md = EvidenceFormatter.format_snapshot_to_markdown(snapshot)

    # 1. Quote assertions
    assert "REAL-TIME MARKET QUOTE" in md
    assert "BBCA" in md
    assert "Rp 6,325" in md
    assert "+1.20%" in md

    # 2. Orderbook assertions
    assert "ORDERBOOK MICROSTRUCTURE" in md
    assert "Best Bid: Rp 6,325" in md
    assert "Best Offer: Rp 6,350" in md
    assert "1.30x" in md

    # 3. Technicals assertions
    assert "TECHNICAL & PRICE ACTION" in md
    assert "MA20: 6210" in md
    assert "RSI(14): 58.4" in md
    assert "6250" in md  # Key support

    # 4. Foreign Flow assertions
    assert "FOREIGN FLOW" in md
    assert "STRONG_ACCUMULATION" in md
    assert "+142,500 lot" in md

    # 5. Broker Summary assertions
    assert "BROKER FLOW 1D" in md
    assert "ZP" in md
    assert "ACCUMULATION" in md
    assert "64.2%" in md

    # 6. Market Context assertions
    assert "MARKET CONTEXT" in md
    assert "IHSG" in md
    assert "7650.4" in md


def test_format_delta_to_markdown_contains_shifts_and_events() -> None:
    delta = EvidenceDeltaSchema(
        base_snapshot_id="SNP-20260826-BBCA-001",
        current_snapshot_id="SNP-20260826-BBCA-002",
        time_elapsed_minutes=35,
        price_delta=PriceDelta(previous_price=6250.0, current_price=6325.0, diff=75.0, percent=1.20),
        orderbook_delta={
            "previous_bid_ask_ratio": 1.05,
            "current_bid_ask_ratio": 1.30,
            "bid_pressure_trend": "STRENGTHENING",
        },
        foreign_flow_delta={
            "additional_net_shares": 5200000,
            "status": "ACCUMULATION_CONTINUES",
        },
        broker_flow_delta={
            "lead_buyer": "ZP",
            "lead_buyer_added_lots": 45000,
            "bandar_status_shift": "REMAINS_ACCUMULATION",
        },
        key_events=[
            "Harga menembus resistance minor 6.300",
            "Bid depth bertambah 32.000 lot di area 6.300 - 6.325",
            "Asing melanjutkan net buy tambahan +5.2M shares",
        ],
    )

    md = EvidenceFormatter.format_delta_to_markdown(delta)

    assert "EVIDENCE DELTA" in md
    assert "Waktu Berlalu: 35 menit" in md
    assert "Pergerakan Harga: Rp 6,250 -> Rp 6,325 (+75 / +1.20%)" in md
    assert "Rasio Bid/Ask 1.05x -> 1.30x (STRENGTHENING)" in md
    assert "Harga menembus resistance minor 6.300" in md
