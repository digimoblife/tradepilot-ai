from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.trade_workspace.models.session_decision import SessionDecisionV2Reason


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


class DecisionAvailabilityResponse(BaseModel):
    session_id: str
    session_status: str
    available_actions: list[str]


class WaitDecisionResponse(BaseModel):
    decision_id: str
    session_id: str
    decision_type: str
    decision_at: datetime
    session_status: str


class SkipDecisionResponse(BaseModel):
    decision_id: str
    session_id: str
    decision_type: str
    reason: str
    note: str | None
    decision_at: datetime
    session_status: str
    closed_at: datetime


class SkipDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: SessionDecisionV2Reason
    note: str | None = None


class BuyDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_price: Decimal = Field(gt=0)
    entry_timestamp: datetime
    quantity: Decimal = Field(gt=0)
    stop_loss: Decimal = Field(gt=0)
    target_price: Decimal = Field(gt=0)
    note: str | None = None


class BuyDecisionResponse(BaseModel):
    decision_id: str
    session_id: str
    decision_type: str
    decision_at: datetime
    position_id: str
    position_status: str
    entry_price: Decimal
    entry_timestamp: datetime
    quantity: Decimal
    stop_loss: Decimal
    target_price: Decimal
    note: str | None
    session_status: str


class WaitUpdateInputResponse(BaseModel):
    evidence_id: str
    session_id: str
    evidence_type: str
    original_filename: str
    mime_type: str
    size_bytes: int
    current_price: Decimal
    observation_period: str
    observation_timestamp: datetime
    uploaded_at: datetime
    session_status: str


class PositionUpdateInputResponse(BaseModel):
    evidence_id: str
    session_id: str
    position_id: str
    evidence_type: str
    original_filename: str
    mime_type: str
    size_bytes: int
    current_price: Decimal
    observation_period: str
    observation_timestamp: datetime
    uploaded_at: datetime
    session_status: str
    position_status: str


class InitialEvidenceResponse(BaseModel):
    id: str
    evidence_type: str
    original_filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime


class InitialEvidenceUploadResponse(BaseModel):
    evidence: list[InitialEvidenceResponse]


class InitialAnalysisSubmissionResponse(BaseModel):
    analysis_request_id: str
    session_id: str
    analysis_type: str
    request_status: str
    session_status: str
    created_at: datetime


class WaitUpdateAnalysisSubmissionResponse(BaseModel):
    analysis_request_id: str
    session_id: str
    analysis_type: str
    request_status: str
    evidence_id: str
    observation_period: str
    session_status: str
    created_at: datetime


class InitialAnalysisReadResponse(BaseModel):
    analysis_request_id: str
    session_id: str
    analysis_type: str
    request_status: str
    session_status: str
    processed_response: dict[str, object] | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class WaitUpdateAnalysisReadResponse(BaseModel):
    analysis_request_id: str
    session_id: str
    analysis_type: str
    request_status: str
    session_status: str
    processed_response: dict[str, object] | None
    error_code: str | None
    error_message: str | None
    observation_period: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class WaitUpdateAnalysisRecoveryResponse(BaseModel):
    analysis_request_id: str
    session_id: str
    analysis_type: str
    request_status: str
    session_status: str
    observation_period: str | None
    created_at: datetime
