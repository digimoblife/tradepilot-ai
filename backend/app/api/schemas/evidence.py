"""Pydantic schemas for Evidence API (TP-1003)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EvidenceResponse(BaseModel):
    id: str
    session_id: str
    evidence_type: str
    status: str
    original_filename: str | None
    mime_type: str | None
    file_size_bytes: int | None
    checksum_sha256: str | None
    market_timestamp: datetime | None
    uploaded_at: datetime
    caption: str | None
    supersedes_evidence_id: str | None

    model_config = {"from_attributes": True}


class EvidenceListResponse(BaseModel):
    evidence: list[EvidenceResponse]
    total: int


class EvidenceErrorResponse(BaseModel):
    code: str
    message: str
