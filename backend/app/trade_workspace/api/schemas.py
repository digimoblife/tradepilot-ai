from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TradeSessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(min_length=1, max_length=32)
    company_name: str = Field(min_length=1, max_length=255)
    note: str | None = None

    @field_validator("ticker", "company_name", mode="before")
    @classmethod
    def reject_blank_text(cls, value: object) -> object:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


class TradeSessionResponse(BaseModel):
    id: str
    ticker: str
    company_name: str
    status: str
    note: str | None
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None


class TradeSessionListResponse(BaseModel):
    sessions: list[TradeSessionResponse]


class InitialEvidenceResponse(BaseModel):
    id: str
    evidence_type: str
    original_filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime


class InitialEvidenceUploadResponse(BaseModel):
    evidence: list[InitialEvidenceResponse]
