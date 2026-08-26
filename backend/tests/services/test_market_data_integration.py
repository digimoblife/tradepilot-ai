"""Unit and integration tests for System-Acquired Evidence via ZAPI."""

import pytest
from app.services.evidence_delta import EvidenceDeltaCalculator
from app.services.evidence_normalizer import EvidenceNormalizer
from app.services.evidence_validator import EvidenceValidator
from app.services.technical_indicators import (
    calculate_atr,
    calculate_rsi,
    calculate_sma,
    compute_technical_summary,
    find_swing_levels,
)


def test_technical_indicator_calculations():
    # 25 sample daily closing prices
    prices = [
        100.0, 102.0, 101.0, 103.0, 105.0, 104.0, 106.0, 108.0, 107.0, 109.0,
        110.0, 112.0, 111.0, 113.0, 115.0, 114.0, 116.0, 118.0, 117.0, 120.0,
        122.0, 121.0, 123.0, 125.0, 127.0
    ]

    sma20 = calculate_sma(prices, 20)
    assert sma20 is not None
    assert sma20 > 100.0

    rsi = calculate_rsi(prices, 14)
    assert rsi is not None
    assert 0 <= rsi <= 100

    bars = [
        {"high": p + 2, "low": p - 2, "close": p, "open": p - 1, "volume": 1000}
        for p in prices
    ]
    atr = calculate_atr(bars, 14)
    assert atr is not None
    assert atr > 0

    summary = compute_technical_summary(bars)
    assert "ma20" in summary
    assert "rsi14" in summary
    assert summary["high_52w"] == 129.0
    assert summary["low_52w"] == 98.0


def test_evidence_normalizer_and_validator():
    mock_quote = {
        "lastPrice": 6325,
        "previousClose": 6250,
        "openPrice": 6275,
        "highPrice": 6350,
        "lowPrice": 6250,
        "volume": 45820100,
        "frequency": 12840,
    }

    mock_orderbook = {
        "bestBid": 6325,
        "bestAsk": 6350,
        "bids": [{"price": 6325, "lots": 34200}, {"price": 6300, "lots": 51000}],
        "asks": [{"price": 6350, "lots": 28400}, {"price": 6375, "lots": 46500}],
    }

    mock_history = {
        "items": [
            {
                "date": "2026-08-26",
                "open": 6275,
                "high": 6350,
                "low": 6250,
                "close": 6325,
                "volume": 45820100,
                "netForeignShares": 14250000,
                "netForeignValue": 90131250000,
            }
            for _ in range(40)
        ]
    }

    mock_broker = {
        "buyers": [
            {"broker": "ZP", "lots": 131000, "value": 83200000000, "averagePrice": 6351},
            {"broker": "RX", "lots": 82000, "value": 51900000000, "averagePrice": 6330},
        ],
        "sellers": [
            {"broker": "YP", "lots": 58000, "value": 36600000000, "averagePrice": 6310},
        ],
    }

    mock_index = {
        "data": [{"IndexCode": "COMPOSITE", "Close": 7650.4, "Previous": 7620.0}]
    }

    snapshot = EvidenceNormalizer.assemble_snapshot(
        session_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
        symbol="BBCA",
        quote_raw=mock_quote,
        orderbook_raw=mock_orderbook,
        history_raw=mock_history,
        broker_raw=mock_broker,
        index_raw=mock_index,
    )

    assert snapshot.symbol == "BBCA"
    assert snapshot.quote.last_price == 6325
    assert snapshot.orderbook.best_bid == 6325
    assert snapshot.historical_ohlcv.horizon_days == 40
    assert snapshot.foreign_flow.today_1d.net_shares == 14250000
    assert len(snapshot.broker_flow.top_buyers) == 2

    # Validation
    val = EvidenceValidator.validate_snapshot(snapshot)
    assert val.is_valid is True
    assert val.completeness_status in ("COMPLETE", "PARTIAL")


def test_evidence_delta_calculation():
    # Base Snapshot (N-1)
    base = EvidenceNormalizer.assemble_snapshot(
        session_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
        symbol="BBCA",
        quote_raw={"lastPrice": 6250, "openPrice": 6250, "highPrice": 6275, "lowPrice": 6200, "volume": 20000000},
        orderbook_raw={"bestBid": 6250, "bestAsk": 6275, "bids": [{"price": 6250, "lots": 10000}], "asks": [{"price": 6275, "lots": 10000}]},
        history_raw={"items": [{"date": "2026-08-26", "open": 6250, "high": 6275, "low": 6200, "close": 6250, "volume": 20000000, "netForeignShares": 5000000} for _ in range(35)]},
        broker_raw={"buyers": [{"broker": "ZP", "lots": 50000, "averagePrice": 6250}], "sellers": [{"broker": "YP", "lots": 30000, "averagePrice": 6250}]},
        index_raw={"data": [{"IndexCode": "COMPOSITE", "Close": 7600.0}]},
        sequence_number=1,
    )

    # Current Snapshot (N) - Price up, foreign net buy up
    current = EvidenceNormalizer.assemble_snapshot(
        session_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
        symbol="BBCA",
        quote_raw={"lastPrice": 6325, "openPrice": 6250, "highPrice": 6350, "lowPrice": 6200, "volume": 35000000},
        orderbook_raw={"bestBid": 6325, "bestAsk": 6350, "bids": [{"price": 6325, "lots": 25000}], "asks": [{"price": 6350, "lots": 15000}]},
        history_raw={"items": [{"date": "2026-08-26", "open": 6250, "high": 6350, "low": 6200, "close": 6325, "volume": 35000000, "netForeignShares": 12000000} for _ in range(35)]},
        broker_raw={"buyers": [{"broker": "ZP", "lots": 90000, "averagePrice": 6300}], "sellers": [{"broker": "YP", "lots": 40000, "averagePrice": 6280}]},
        index_raw={"data": [{"IndexCode": "COMPOSITE", "Close": 7630.0}]},
        sequence_number=2,
    )

    delta = EvidenceDeltaCalculator.calculate_delta(base, current)

    assert delta.price_delta.previous_price == 6250
    assert delta.price_delta.current_price == 6325
    assert delta.price_delta.diff == 75
    assert delta.price_delta.percent > 0
    assert delta.foreign_flow_delta.additional_net_shares == 7000000
    assert len(delta.key_events) > 0


def test_evidence_formatter():
    from app.services.evidence_formatter import EvidenceFormatter

    snapshot = EvidenceNormalizer.assemble_snapshot(
        session_id="3fa85f64-5717-4562-b3fc-2c963f66afa6",
        symbol="BBCA",
        quote_raw={"lastPrice": 6325, "previousClose": 6250, "openPrice": 6275, "highPrice": 6350, "lowPrice": 6250, "volume": 45820100, "frequency": 12840},
        orderbook_raw={"bestBid": 6325, "bestAsk": 6350, "bids": [{"price": 6325, "lots": 34200}], "asks": [{"price": 6350, "lots": 28400}]},
        history_raw={"items": [{"date": "2026-08-26", "open": 6275, "high": 6350, "low": 6250, "close": 6325, "volume": 45820100, "netForeignShares": 14250000} for _ in range(40)]},
        broker_raw={"buyers": [{"broker": "ZP", "lots": 131000, "averagePrice": 6351}], "sellers": [{"broker": "YP", "lots": 58000, "averagePrice": 6310}]},
        index_raw={"data": [{"IndexCode": "COMPOSITE", "Close": 7650.4}]},
    )

    md = EvidenceFormatter.format_snapshot_to_markdown(snapshot)
    assert "REAL-TIME MARKET QUOTE" in md
    assert "BBCA" in md
    assert "Rp 6,325" in md
    assert "ORDERBOOK MICROSTRUCTURE" in md
    assert "FOREIGN FLOW" in md
    assert "BROKER FLOW 1D" in md

