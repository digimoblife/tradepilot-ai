"""Pydantic schemas for System-Acquired Evidence Snapshot and Delta."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class QuoteDomain(BaseModel):
    last_price: float
    change: float
    change_percent: float
    previous_close: float
    open: float
    high: float
    low: float
    volume_shares: int
    volume_lots: int
    value_idr: float
    frequency: int
    pe_ratio: float | None = None
    pbv_ratio: float | None = None
    market_cap: float | None = None
    timestamp: str | None = None


class OrderbookLevel(BaseModel):
    price: float
    lots: int


class OrderbookDomain(BaseModel):
    best_bid: float
    best_ask: float
    spread: float
    spread_percent: float
    total_bid_lots: int
    total_ask_lots: int
    bid_ask_ratio: float
    bid_percent: float
    ask_percent: float
    bids: list[OrderbookLevel] = Field(default_factory=list)
    asks: list[OrderbookLevel] = Field(default_factory=list)
    timestamp: str | None = None


class HistoricalBar(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    value: float | None = None
    net_foreign_shares: int | None = None


class HistoricalDomain(BaseModel):
    horizon_days: int
    start_date: str | None = None
    end_date: str | None = None
    computed_technical: dict[str, Any] = Field(default_factory=dict)
    recent_bars: list[HistoricalBar] = Field(default_factory=list)


class ForeignFlowPeriod(BaseModel):
    net_shares: int
    net_value_idr: float
    buy_shares: int | None = None
    sell_shares: int | None = None


class ForeignFlowDomain(BaseModel):
    today_1d: ForeignFlowPeriod | None = None
    weekly_1w: ForeignFlowPeriod | None = None
    monthly_1m: ForeignFlowPeriod | None = None
    three_month_3m: ForeignFlowPeriod | None = None
    foreign_status: str = "NEUTRAL"
    recent_daily_series: list[dict[str, Any]] = Field(default_factory=list)


class BrokerItem(BaseModel):
    broker: str
    lots: int
    value_idr: float
    avg_price: float
    market_share_percent: float | None = None


class BrokerFlowDomain(BaseModel):
    date: str | None = None
    is_net: bool = True
    top3_buyer_concentration_percent: float = 0.0
    top3_seller_concentration_percent: float = 0.0
    bandar_status: str = "NEUTRAL"
    top_buyers: list[BrokerItem] = Field(default_factory=list)
    top_sellers: list[BrokerItem] = Field(default_factory=list)


class MarketContextDomain(BaseModel):
    index_code: str = "COMPOSITE"
    index_name: str = "IHSG"
    index_price: float | None = None
    index_change_percent: float | None = None
    index_trend: str = "NEUTRAL"


class EvidenceSnapshotSchema(BaseModel):
    snapshot_id: str
    session_id: uuid.UUID | str
    symbol: str
    market: str = "IDX"
    captured_at: str
    snapshot_type: str = "INITIAL"
    sequence_number: int = 1
    providers_used: dict[str, str] = Field(default_factory=dict)
    completeness_status: str = "COMPLETE"
    quote: QuoteDomain
    orderbook: OrderbookDomain
    historical_ohlcv: HistoricalDomain
    foreign_flow: ForeignFlowDomain
    broker_flow: BrokerFlowDomain
    market_context: MarketContextDomain


class PriceDelta(BaseModel):
    previous_price: float
    current_price: float
    diff: float
    percent: float


class OrderbookDelta(BaseModel):
    previous_bid_ask_ratio: float
    current_bid_ask_ratio: float
    bid_pressure_trend: str


class ForeignFlowDelta(BaseModel):
    additional_net_shares: int
    status: str


class BrokerFlowDelta(BaseModel):
    lead_buyer: str | None = None
    lead_buyer_added_lots: int | None = None
    bandar_status_shift: str = "UNCHANGED"


class EvidenceDeltaSchema(BaseModel):
    base_snapshot_id: str
    current_snapshot_id: str
    time_elapsed_minutes: int
    price_delta: PriceDelta
    orderbook_delta: OrderbookDelta
    foreign_flow_delta: ForeignFlowDelta
    broker_flow_delta: BrokerFlowDelta
    key_events: list[str] = Field(default_factory=list)
