"""Pydantic schemas for Trade Action API (TP-1005)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BaseActionRequest(BaseModel):
    session_id: str
    idempotency_key: str = Field(..., min_length=1)


class OpenPositionRequest(BaseActionRequest):
    entry_price: object
    quantity: object
    executed_at: datetime
    stop_loss: object | None = None
    target: object | None = None
    note: str | None = None


class StopActionRequest(BaseActionRequest):
    stop_loss: object
    confirmed_at: datetime
    note: str | None = None


class TargetActionRequest(BaseActionRequest):
    target: object
    confirmed_at: datetime
    note: str | None = None


class PartialExitRequest(BaseActionRequest):
    exit_price: object
    exit_quantity: object
    executed_at: datetime
    reason: str | None = None
    note: str | None = None


class FullExitRequest(BaseActionRequest):
    exit_price: object
    exit_quantity: object
    executed_at: datetime
    closing_reason: str
    fees: object | None = None
    note: str | None = None


class CancelSessionRequest(BaseActionRequest):
    cancelled_at: datetime
    reason: str | None = None
    note: str | None = None


class TradeActionResponse(BaseModel):
    id: str
    session_id: str
    action_type: str
    confirmed_at: datetime
    price: str | None
    quantity: str | None


class TradeStateSnapshot(BaseModel):
    position_status: str
    entry_price: str | None
    original_quantity: str | None
    remaining_quantity: str | None
    active_stop_loss: str | None
    active_target: str | None
    average_exit_price: str | None
    realized_pnl: str | None
    state_version: int


class ActionResultResponse(BaseModel):
    action: TradeActionResponse
    session_status: str
    trade_state: TradeStateSnapshot
