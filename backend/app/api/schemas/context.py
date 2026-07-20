"""Pydantic schemas for Context Summary API (TP-1006)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ContextSummaryResponse(BaseModel):
    id: str
    session_id: str
    context_version: int
    source_cutoff: datetime | None
    is_stale: bool
    quality: str
    payload: dict[str, object] | None
    created_at: datetime
