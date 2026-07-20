"""Pydantic schemas for Timeline API (TP-1006)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class TimelineActionReference(BaseModel):
    id: str
    action_type: str
    confirmed_at: datetime
    price: Decimal | None
    quantity: Decimal | None


class TimelineAnalysisReference(BaseModel):
    id: str
    analysis_type: str
    accepted_at: datetime | None
    schema_name: str
    schema_version: str


class TimelineEventResponse(BaseModel):
    id: str
    session_id: str
    event_type: str
    occurred_at: datetime
    created_at: datetime
    summary: str | None
    price: Decimal | None
    quantity: Decimal | None
    related_action: TimelineActionReference | None
    related_analysis: TimelineAnalysisReference | None


class TimelineListResponse(BaseModel):
    events: list[TimelineEventResponse]
    total: int
