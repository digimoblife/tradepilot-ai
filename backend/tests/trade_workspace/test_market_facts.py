"""Unit tests for the best-effort rebuild market-facts collector."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.config import AppConfig
from app.trade_workspace.services.market_facts import collect_market_facts


@pytest.mark.asyncio
async def test_returns_none_without_zapi_api_key() -> None:
    config = AppConfig(zapi_api_key="")
    result = await collect_market_facts(config=config, session_id=uuid.uuid4(), symbol="BBRI")
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_for_blank_symbol() -> None:
    config = AppConfig(zapi_api_key="test-key")
    result = await collect_market_facts(config=config, session_id=uuid.uuid4(), symbol="   ")
    assert result is None


@pytest.mark.asyncio
async def test_returns_none_when_collector_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _boom(self: object, **kwargs: object) -> object:
        raise RuntimeError("ZAPI unavailable")

    monkeypatch.setattr(
        "app.trade_workspace.services.market_facts.MarketDataCollector.acquire_snapshot",
        _boom,
    )
    config = AppConfig(zapi_api_key="test-key")
    result = await collect_market_facts(config=config, session_id=uuid.uuid4(), symbol="BBRI")
    assert result is None


@pytest.mark.asyncio
async def test_reduces_snapshot_into_compact_market_facts(monkeypatch: pytest.MonkeyPatch) -> None:
    snapshot = SimpleNamespace(
        captured_at="2026-01-01T09:00:00+07:00",
        quote=SimpleNamespace(
            pe_ratio=12.5, pbv_ratio=1.8, market_cap=5.0e13, volume_shares=1_000_000
        ),
        market_context=SimpleNamespace(
            index_name="IHSG", index_change_percent=0.42, index_trend="BULLISH"
        ),
        foreign_flow=SimpleNamespace(
            foreign_status="ACCUMULATION",
            monthly_1m=SimpleNamespace(net_shares=1_000_000, net_value_idr=5_000_000_000.0),
            three_month_3m=SimpleNamespace(net_shares=-200_000, net_value_idr=-900_000_000.0),
        ),
        orderbook=SimpleNamespace(
            spread_percent=0.25,
            bid_ask_ratio=1.45,
            total_bid_lots=125_000,
            total_ask_lots=86_000,
        ),
        historical_ohlcv=SimpleNamespace(
            recent_bars=[
                SimpleNamespace(volume=500_000, value=2_500_000_000.0) for _ in range(20)
            ]
        ),
    )

    async def _fake_acquire(self: object, **kwargs: object) -> tuple[object, object]:
        return snapshot, object()

    monkeypatch.setattr(
        "app.trade_workspace.services.market_facts.MarketDataCollector.acquire_snapshot",
        _fake_acquire,
    )
    config = AppConfig(zapi_api_key="test-key")
    result = await collect_market_facts(config=config, session_id=uuid.uuid4(), symbol="BBRI")

    assert result is not None
    assert result["pe_ratio"] == 12.5
    assert result["pbv_ratio"] == 1.8
    assert result["market_cap"] == 5.0e13
    assert result["volume_shares_today"] == 1_000_000
    assert result["avg_volume_20d_shares"] == 500_000.0
    assert result["volume_vs_average_ratio"] == 2.0
    assert result["avg_daily_value_idr_20d"] == 2_500_000_000.0
    assert result["index_name"] == "IHSG"
    assert result["index_change_percent"] == 0.42
    assert result["index_trend"] == "BULLISH"
    assert result["foreign_status"] == "ACCUMULATION"
    assert result["foreign_flow_1m"] == {"net_shares": 1_000_000, "net_value_idr": 5_000_000_000.0}
    assert result["foreign_flow_3m"] == {
        "net_shares": -200_000,
        "net_value_idr": -900_000_000.0,
    }
    assert result["system_spread_percent"] == 0.25
    assert result["system_bid_ask_ratio"] == 1.45
    assert result["system_total_bid_lots"] == 125_000
    assert result["system_total_ask_lots"] == 86_000
    assert result["ma20"] is None
    assert result["ma50"] is None
    assert result["ma200"] is None
    assert result["rsi14"] is None
    assert result["atr14"] is None
    assert result["high_52w"] is None
    assert result["low_52w"] is None
    assert result["ma_alignment"] is None
    assert result["key_supports"] is None
    assert result["key_resistances"] is None
    assert result["sector"] is None
    assert result["sub_sector"] is None
    assert result["dividend_yield_percent"] is None
    assert result["dividend_per_share"] is None
    assert result["eps_ttm"] is None
    assert result["beta"] is None
    assert result["one_year_return_percent"] is None
    assert result["next_earnings_date"] is None


@pytest.mark.asyncio
async def test_reduces_snapshot_with_company_profile_and_pe_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = SimpleNamespace(
        captured_at="2026-01-01T09:00:00+07:00",
        quote=SimpleNamespace(
            pe_ratio=None, pbv_ratio=None, market_cap=5.0e13, volume_shares=1_000_000
        ),
        market_context=None,
        foreign_flow=None,
        orderbook=None,
        historical_ohlcv=None,
        company_profile=SimpleNamespace(
            sector="Keuangan",
            sub_sector="Bank",
            pe_ratio=8.16,
            pbv_ratio=2.1,
            dividend_yield_percent=10.12,
            dividend_per_share=346.0,
            eps_ttm=406.65,
            beta=0.18,
            one_year_return_percent=-9.76,
            next_earnings_date="2026-10-28",
        ),
    )

    async def _fake_acquire(self: object, **kwargs: object) -> tuple[object, object]:
        return snapshot, object()

    monkeypatch.setattr(
        "app.trade_workspace.services.market_facts.MarketDataCollector.acquire_snapshot",
        _fake_acquire,
    )
    config = AppConfig(zapi_api_key="test-key")
    result = await collect_market_facts(config=config, session_id=uuid.uuid4(), symbol="BBRI")

    assert result is not None
    # P/E and PBV fell back to company_profile
    assert result["pe_ratio"] == 8.16
    assert result["pbv_ratio"] == 2.1
    assert result["sector"] == "Keuangan"
    assert result["sub_sector"] == "Bank"
    assert result["dividend_yield_percent"] == 10.12
    assert result["dividend_per_share"] == 346.0
    assert result["eps_ttm"] == 406.65
    assert result["beta"] == 0.18
    assert result["one_year_return_percent"] == -9.76
    assert result["next_earnings_date"] == "2026-10-28"



@pytest.mark.asyncio
async def test_returns_technical_indicators_when_computed_technical_is_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = SimpleNamespace(
        captured_at="2026-01-01T09:00:00+07:00",
        quote=None,
        market_context=None,
        foreign_flow=None,
        historical_ohlcv=SimpleNamespace(
            recent_bars=[],
            computed_technical={
                "ma20": 4200.0,
                "ma50": 4100.0,
                "ma200": 3900.0,
                "rsi14": 58.5,
                "atr14": 85.0,
                "high_52w": 4800.0,
                "low_52w": 3500.0,
                "ma_alignment": "BULLISH_ALIGNMENT",
                "key_supports": [4100.0, 4000.0],
                "key_resistances": [4300.0, 4400.0],
            },
        ),
    )

    async def _fake_acquire(self: object, **kwargs: object) -> tuple[object, object]:
        return snapshot, object()

    monkeypatch.setattr(
        "app.trade_workspace.services.market_facts.MarketDataCollector.acquire_snapshot",
        _fake_acquire,
    )
    config = AppConfig(zapi_api_key="test-key")
    result = await collect_market_facts(config=config, session_id=uuid.uuid4(), symbol="BBRI")

    assert result is not None
    assert result["ma20"] == 4200.0
    assert result["ma50"] == 4100.0
    assert result["ma200"] == 3900.0
    assert result["rsi14"] == 58.5
    assert result["atr14"] == 85.0
    assert result["high_52w"] == 4800.0
    assert result["low_52w"] == 3500.0
    assert result["ma_alignment"] == "BULLISH_ALIGNMENT"
    assert result["key_supports"] == [4100.0, 4000.0]
    assert result["key_resistances"] == [4300.0, 4400.0]


@pytest.mark.asyncio
async def test_technical_indicators_remain_none_when_computed_technical_empty_or_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 1. computed_technical is an empty dict
    snapshot_empty = SimpleNamespace(
        captured_at="2026-01-01T09:00:00+07:00",
        quote=SimpleNamespace(pe_ratio=10.0),
        market_context=None,
        foreign_flow=None,
        historical_ohlcv=SimpleNamespace(
            recent_bars=[],
            computed_technical={},
        ),
    )

    async def _fake_acquire_empty(self: object, **kwargs: object) -> tuple[object, object]:
        return snapshot_empty, object()

    monkeypatch.setattr(
        "app.trade_workspace.services.market_facts.MarketDataCollector.acquire_snapshot",
        _fake_acquire_empty,
    )
    config = AppConfig(zapi_api_key="test-key")
    result_empty = await collect_market_facts(
        config=config, session_id=uuid.uuid4(), symbol="BBRI"
    )
    assert result_empty is not None
    assert result_empty["avg_daily_value_idr_20d"] is None
    assert result_empty["system_spread_percent"] is None
    assert result_empty["system_bid_ask_ratio"] is None
    assert result_empty["system_total_bid_lots"] is None
    assert result_empty["system_total_ask_lots"] is None
    assert result_empty["ma20"] is None
    assert result_empty["ma50"] is None
    assert result_empty["ma200"] is None
    assert result_empty["rsi14"] is None
    assert result_empty["atr14"] is None
    assert result_empty["high_52w"] is None
    assert result_empty["low_52w"] is None
    assert result_empty["ma_alignment"] is None
    assert result_empty["key_supports"] is None
    assert result_empty["key_resistances"] is None

    # 2. historical_ohlcv is None (absent)
    snapshot_absent = SimpleNamespace(
        captured_at="2026-01-01T09:00:00+07:00",
        quote=SimpleNamespace(pe_ratio=10.0),
        market_context=None,
        foreign_flow=None,
        historical_ohlcv=None,
    )

    async def _fake_acquire_absent(self: object, **kwargs: object) -> tuple[object, object]:
        return snapshot_absent, object()

    monkeypatch.setattr(
        "app.trade_workspace.services.market_facts.MarketDataCollector.acquire_snapshot",
        _fake_acquire_absent,
    )
    result_absent = await collect_market_facts(
        config=config, session_id=uuid.uuid4(), symbol="BBRI"
    )
    assert result_absent is not None
    assert result_absent["avg_daily_value_idr_20d"] is None
    assert result_absent["system_spread_percent"] is None
    assert result_absent["system_bid_ask_ratio"] is None
    assert result_absent["system_total_bid_lots"] is None
    assert result_absent["system_total_ask_lots"] is None
    assert result_absent["ma20"] is None
    assert result_absent["ma_alignment"] is None
    assert result_absent["key_supports"] is None
    assert result_absent["key_resistances"] is None
