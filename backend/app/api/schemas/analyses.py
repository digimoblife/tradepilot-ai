"""Pydantic schemas for Analysis API (TP-1004)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AnalysisRequest(BaseModel):
    analysis_type: str


class AnalysisSummaryResponse(BaseModel):
    id: str
    session_id: str
    analysis_type: str
    acceptance_status: str
    accepted_at: datetime | None
    created_at: datetime
    prompt_version: str
    schema_name: str
    schema_version: str
    supersedes_analysis_id: str | None

    model_config = {"from_attributes": True}


class AnalysisListResponse(BaseModel):
    analyses: list[AnalysisSummaryResponse]
    total: int


class AnalysisDetailResponse(BaseModel):
    id: str
    session_id: str
    analysis_type: str
    acceptance_status: str
    accepted_at: datetime | None
    created_at: datetime
    prompt_name: str
    prompt_version: str
    schema_name: str
    schema_version: str
    payload: dict[str, object] | None
    supersedes_analysis_id: str | None

    model_config = {"from_attributes": True}
