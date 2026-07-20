"""Pydantic schemas for Trade Session API (TP-1002)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Create request
# ---------------------------------------------------------------------------


class TradeSessionCreateRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=32, description="Stock ticker")
    company_name: str | None = Field(None, max_length=255)
    exchange: str | None = None
    currency: str = Field(default="IDR", min_length=2, max_length=10)
    title: str | None = Field(None, max_length=255)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class TradeSessionSummaryResponse(BaseModel):
    id: str
    ticker: str
    company_name: str | None
    exchange: str
    currency: str
    title: str | None
    lifecycle_status: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None

    model_config = {"from_attributes": True}


class TradeStateResponse(BaseModel):
    position_status: str
    thesis_status: str
    entry_price: Decimal | None = None
    entry_at: datetime | None = None
    original_quantity: Decimal | None = None
    remaining_quantity: Decimal | None = None
    active_stop_loss: Decimal | None = None
    active_target: Decimal | None = None
    average_exit_price: Decimal | None = None
    realized_pnl: Decimal | None = None
    realized_return: Decimal | None = None
    state_version: int

    model_config = {"from_attributes": True}


class TradeSessionDetailResponse(BaseModel):
    session: TradeSessionSummaryResponse
    trade_state: TradeStateResponse


class TradeSessionListResponse(BaseModel):
    sessions: list[TradeSessionSummaryResponse]
    total: int


class TradeSessionCreateResponse(BaseModel):
    id: str
    ticker: str
    company_name: str | None
    exchange: str
    currency: str
    title: str | None
    lifecycle_status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TradeSessionArchiveResponse(BaseModel):
    id: str
    lifecycle_status: str
    archived_at: datetime | None

    model_config = {"from_attributes": True}


class TradeSessionUpdateRequest(BaseModel):
    title: str | None = None
    company_name: str | None = None
    exchange: str | None = None
    currency: str | None = None
    ticker: str | None = None


class TradeSessionReadyResponse(BaseModel):
    id: str
    lifecycle_status: str

    model_config = {"from_attributes": True}


class TradeSessionAllowedActions(BaseModel):
    allowed_actions: list[str]


class TradeSessionDetailWithActionsResponse(BaseModel):
    session: TradeSessionSummaryResponse
    trade_state: TradeStateResponse
    allowed_actions: list[str]
