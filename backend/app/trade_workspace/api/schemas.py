from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.session_decision import (
    SessionDecisionV2Decision,
    SessionDecisionV2Reason,
)
from app.trade_workspace.services.current_step import (
    CurrentStepCode,
    CurrentStepMode,
    WorkflowAction,
)
from app.trade_workspace.services.session_summary import SessionActivityType


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
    archived_at: datetime | None


class TradeSessionArchiveResponse(BaseModel):
    id: str
    status: str
    archived_at: datetime | None


class TradeSessionListResponse(BaseModel):
    sessions: list[TradeSessionResponse]


class CurrentStepActiveRequestResponse(BaseModel):
    id: str
    analysis_type: AnalysisRequestV2Type
    status: AnalysisRequestV2Status


class CurrentStepFailedRequestResponse(CurrentStepActiveRequestResponse):
    retry_allowed: bool


class CurrentStepResponse(BaseModel):
    code: CurrentStepCode
    mode: CurrentStepMode
    workflow_actions: list[WorkflowAction]
    active_request: CurrentStepActiveRequestResponse | None
    failed_request: CurrentStepFailedRequestResponse | None
    read_only: bool


class LatestAnalysisSummaryResponse(BaseModel):
    analysis_type: AnalysisRequestV2Type
    completed_at: datetime
    has_result: bool


class SessionRecentActivityItemResponse(BaseModel):
    type: SessionActivityType
    occurred_at: datetime
    analysis_type: AnalysisRequestV2Type | None
    decision: SessionDecisionV2Decision | None


class SessionDetailAggregateResponse(BaseModel):
    session: dict[str, object]
    initial_evidence: list[dict[str, object]]
    initial_analysis: dict[str, object] | None
    decisions: list[dict[str, object]]
    wait_updates: list[dict[str, object]]
    position: dict[str, object] | None
    position_updates: list[dict[str, object]]
    closure: dict[str, object] | None
    current_step: CurrentStepResponse
    latest_analysis: LatestAnalysisSummaryResponse | None
    recent_activity: list[SessionRecentActivityItemResponse]


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


class PositionUpdateAnalysisSubmissionResponse(BaseModel):
    analysis_request_id: str
    session_id: str
    position_id: str
    analysis_type: str
    request_status: str
    evidence_id: str
    observation_period: str
    session_status: str
    position_status: str
    created_at: datetime


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


class PositionDetailResponse(BaseModel):
    id: str
    session_id: str
    status: str
    entry_price: Decimal
    entry_timestamp: datetime
    quantity: Decimal
    stop_loss: Decimal
    target_price: Decimal
    note: str | None
    created_at: datetime


class PositionUpdateItemResponse(BaseModel):
    analysis_request_id: str
    session_id: str
    analysis_type: str
    request_status: str
    current_price: Decimal | None
    observation_period: str | None
    observation_timestamp: datetime | None
    processed_response: dict[str, object] | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    evidence_id: str | None = None
    original_filename: str | None = None


class PositionUpdatesReadResponse(BaseModel):
    position: PositionDetailResponse | None
    updates: list[PositionUpdateItemResponse]


class CloseRequest(BaseModel):
    close_price: Decimal = Field(..., gt=0, max_digits=20, decimal_places=6)
    close_timestamp: datetime
    close_reason: str = Field(..., min_length=1, max_length=64)
    note: str | None = None


class CloseResponse(BaseModel):
    closure_id: str
    session_id: str
    position_id: str
    close_price: Decimal
    close_timestamp: datetime
    close_reason: str
    note: str | None
    realized_profit_loss: Decimal
    position_status: str
    session_status: str
    closed_at: datetime
    created_at: datetime
