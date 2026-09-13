"""Unit tests for MarketAnalysisEngine's Gemini-backed pre-trade and in-trade analysis."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.api.schemas.evidence_snapshot import (
    BrokerFlowDomain,
    CompanyProfileDomain,
    EvidenceSnapshotSchema,
    ForeignFlowDomain,
    HistoricalDomain,
    MarketContextDomain,
    OrderbookDomain,
    QuoteDomain,
)
from app.config import AppConfig
from app.services.gemini_client import GeminiAdapterError, GeminiAdapterResult
from app.services.market_analysis_engine import MarketAnalysisEngine, MarketAnalysisEngineError


def _snapshot() -> EvidenceSnapshotSchema:
    return EvidenceSnapshotSchema(
        snapshot_id="SNP-TEST-001",
        session_id=uuid.uuid4(),
        symbol="BBCA",
        captured_at="2026-09-12T09:00:00+07:00",
        quote=QuoteDomain(
            last_price=6325.0,
            change=-100.0,
            change_percent=-1.56,
            previous_close=6425.0,
            open=6400.0,
            high=6400.0,
            low=6250.0,
            volume_shares=187_922_700,
            volume_lots=1_879_227,
            value_idr=1_200_000_000_000.0,
            frequency=12_840,
            pe_ratio=13.4,
            pbv_ratio=4.1,
            market_cap=776_970_000_000_000.0,
        ),
        orderbook=OrderbookDomain(
            best_bid=6300.0,
            best_ask=6325.0,
            spread=25.0,
            spread_percent=0.39,
            total_bid_lots=65604,
            total_ask_lots=17033,
            bid_ask_ratio=1.30,
            bid_percent=56.5,
            ask_percent=43.5,
        ),
        historical_ohlcv=HistoricalDomain(
            horizon_days=130,
            computed_technical={
                "ma20": 6480.0,
                "ma50": 6364.5,
                "ma200": 5890.0,
                "rsi14": 43.52,
                "atr14": 150.0,
                "ma_alignment": "MIXED",
                "high_52w": 8750.0,
                "low_52w": 4820.0,
                "key_supports": [6350.0, 6250.0],
                "key_resistances": [6425.0, 6500.0],
            },
        ),
        foreign_flow=ForeignFlowDomain(foreign_status="DISTRIBUTION"),
        broker_flow=BrokerFlowDomain(bandar_status="NEUTRAL"),
        market_context=MarketContextDomain(
            index_price=6541.38, index_change_percent=-0.73, index_trend="BEARISH"
        ),
        company_profile=CompanyProfileDomain(
            sector="Keuangan",
            sub_sector="Bank",
            pe_ratio=13.4,
            pbv_ratio=4.1,
            beta=-0.04,
            technical_summary="Strong Sell",
            next_earnings_date="2026-10-15",
        ),
    )


class _FakeAdapter:
    """Stand-in for GeminiAdapter that returns a canned structured response."""

    def __init__(
        self, payload: dict[str, Any] | None = None, error: Exception | None = None
    ) -> None:
        self._payload = payload
        self._error = error
        self.last_prompt_text: str | None = None
        self.last_output_schema: Any = None

    async def generate(
        self, *, prompt_text: str, output_schema: Any, **_: Any
    ) -> GeminiAdapterResult:
        self.last_prompt_text = prompt_text
        self.last_output_schema = output_schema
        if self._error is not None:
            raise self._error
        return GeminiAdapterResult(
            provider="gemini",
            model="gemini-3.5-flash-lite",
            raw_response=None,
            processed_response=self._payload or {},
        )


PRE_TRADE_PAYLOAD = {
    "action": "WAIT",
    "signal_quality": "SPECULATIVE",
    "confidence_score": 0.45,
    "key_levels": {
        "current_price": 9999.0,  # deliberately wrong — must be overridden by the engine
        "entry_range": [6175.0, 6325.0],
        "target_price_1": 6475.0,
        "target_price_2": 6625.0,
        "stop_loss": 6025.0,
        "invalidation_level": 6000.0,
        "risk_reward_ratio": 2.0,
        "atr14": 1.0,  # deliberately wrong — must be overridden by the engine
    },
    "reasoning": {
        "thesis": "thesis text",
        "technical_analysis": "technical text",
        "flow_analysis": "flow text",
        "action_guidance": "guidance text",
        "wait_guidance": "wait text",
        "risk_factors": "risk text",
    },
}

IN_TRADE_PAYLOAD = {
    "action": "HOLD",
    "signal_quality": "MEDIUM",
    "confidence_score": 0.65,
    "key_levels": {
        "current_price": 1.0,  # deliberately wrong — must be overridden by the engine
        "entry_price": 1.0,  # deliberately wrong — must be overridden by the engine
        "target_price_1": 6500,
        "target_price_2": 6650,
        "stop_loss": 6000,
        "invalidation_level": 6000,
        "trailing_stop": 6000,
        "trailing_stop_note": "hold trailing note",
        "distance_to_tp1_percent": 999.0,  # deliberately wrong
        "distance_to_sl_percent": 999.0,  # deliberately wrong
        "floating_pnl_percent": 999.0,  # deliberately wrong
        "atr14": 1.0,  # deliberately wrong
    },
    "reasoning": {
        "thesis": "in-trade thesis",
        "technical_analysis": "in-trade technical",
        "flow_analysis": "in-trade flow",
        "action_guidance": "in-trade guidance",
        "risk_factors": "in-trade risk",
    },
}


@pytest.mark.asyncio
async def test_pre_trade_analysis_overrides_confirmed_facts_and_maps_confidence() -> None:
    engine = MarketAnalysisEngine(AppConfig())
    fake = _FakeAdapter(payload=PRE_TRADE_PAYLOAD)
    result = await engine._analyze_pre_trade(
        adapter=fake,  # type: ignore[arg-type]
        snapshot=_snapshot(),
        last_price=6325.0,
        atr14=150.0,
        tech={"atr14": 150.0},
        trading_style="Swing Trade",
        setup_note="Catatan user",
    )

    assert result["action"] == "WAIT"
    assert result["is_in_trade"] is False
    # confidence_score is converted from the 0-1 fraction to a 0-100 int.
    assert result["confidence_score"] == 45
    # Confirmed system facts must win over whatever Gemini echoed back.
    assert result["key_levels"]["current_price"] == 6325.0
    assert result["key_levels"]["atr14"] == 150.0
    # Gemini's own recommended levels pass through untouched.
    assert result["key_levels"]["target_price_1"] == 6475.0
    assert result["reasoning"]["setup_note"] == "Catatan user"
    assert result["reasoning"]["thesis"] == "thesis text"
    assert fake.last_output_schema is not None


@pytest.mark.asyncio
async def test_in_trade_analysis_overrides_position_facts_and_arithmetic() -> None:
    engine = MarketAnalysisEngine(AppConfig())
    fake = _FakeAdapter(payload=IN_TRADE_PAYLOAD)
    position = {
        "entry_price": 6200.0,
        "quantity": 10,
        "stop_loss": 6000.0,
        "target_price": 6500.0,
        "status": "OPEN",
        "entry_timestamp": "2026-09-08T09:00:00Z",
    }
    result = await engine._analyze_in_trade(
        adapter=fake,  # type: ignore[arg-type]
        snapshot=_snapshot(),
        position=position,
        last_price=6325.0,
        atr14=150.0,
        tech={"atr14": 150.0},
        trading_style="Swing Trade",
        setup_note="Entry breakout MA20",
    )

    assert result["action"] == "HOLD"
    assert result["is_in_trade"] is True
    assert result["confidence_score"] == 65
    # Confirmed position facts and pure arithmetic always win over Gemini's echo.
    assert result["key_levels"]["current_price"] == 6325.0
    assert result["key_levels"]["entry_price"] == 6200.0
    assert result["key_levels"]["atr14"] == 150.0
    expected_floating_pnl_pct = round((6325.0 - 6200.0) / 6200.0 * 100, 2)
    assert result["key_levels"]["floating_pnl_percent"] == expected_floating_pnl_pct
    # Gemini's own trailing-stop recommendation passes through untouched.
    assert result["key_levels"]["trailing_stop_note"] == "hold trailing note"
    assert result["reasoning"]["setup_note"] == "Entry breakout MA20"


@pytest.mark.asyncio
async def test_analyze_dispatches_to_in_trade_branch_only_with_open_position() -> None:
    engine = MarketAnalysisEngine(AppConfig())
    engine._analyze_pre_trade = _record_call("pre_trade")  # type: ignore[method-assign]
    engine._analyze_in_trade = _record_call("in_trade")  # type: ignore[method-assign]

    await engine.analyze(_snapshot(), position=None)
    await engine.analyze(_snapshot(), position={"entry_price": 0})
    await engine.analyze(_snapshot(), position={"entry_price": 6200.0})

    assert engine._analyze_pre_trade.calls == 2  # type: ignore[attr-defined]
    assert engine._analyze_in_trade.calls == 1  # type: ignore[attr-defined]


def _record_call(_label: str) -> Any:
    async def _fn(**_: Any) -> dict[str, Any]:
        _fn.calls += 1  # type: ignore[attr-defined]
        return {}

    _fn.calls = 0  # type: ignore[attr-defined]
    return _fn


@pytest.mark.asyncio
async def test_gemini_failure_raises_engine_error_for_both_branches() -> None:
    engine = MarketAnalysisEngine(AppConfig())
    failing = _FakeAdapter(error=GeminiAdapterError("boom"))

    with pytest.raises(MarketAnalysisEngineError):
        await engine._analyze_pre_trade(
            adapter=failing,  # type: ignore[arg-type]
            snapshot=_snapshot(),
            last_price=6325.0,
            atr14=150.0,
            tech={},
            trading_style="Swing Trade",
            setup_note=None,
        )

    with pytest.raises(MarketAnalysisEngineError):
        await engine._analyze_in_trade(
            adapter=failing,  # type: ignore[arg-type]
            snapshot=_snapshot(),
            position={"entry_price": 6200.0, "stop_loss": 6000.0, "target_price": 6500.0},
            last_price=6325.0,
            atr14=150.0,
            tech={},
            trading_style="Swing Trade",
            setup_note=None,
        )
