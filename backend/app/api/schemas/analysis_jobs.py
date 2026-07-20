"""Pydantic schemas for Analysis Job API (TP-1004)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AnalysisJobCreateResponse(BaseModel):
    job_id: str
    session_id: str
    analysis_type: str
    status: str
    attempt_count: int
    max_attempts: int
    available_at: datetime
    created_at: datetime
    previous_session_status: str | None


class AnalysisJobStatusResponse(BaseModel):
    job_id: str
    session_id: str
    analysis_type: str
    status: str
    attempt_count: int
    max_attempts: int
    available_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    last_error_code: str | None
    last_error_message: str | None
    analysis_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
