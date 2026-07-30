from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.errors import SESSION_NOT_FOUND, get_error_message
from app.auth import AuthenticatedUser
from app.database.session import get_db_session
from app.trade_workspace.api.schemas import (
    BuyDecisionRequest,
    BuyDecisionResponse,
    DecisionAvailabilityResponse,
    InitialAnalysisReadResponse,
    InitialAnalysisSubmissionResponse,
    InitialEvidenceResponse,
    InitialEvidenceUploadResponse,
    SkipDecisionRequest,
    SkipDecisionResponse,
    TradeSessionCreateRequest,
    TradeSessionListResponse,
    TradeSessionResponse,
    WaitDecisionResponse,
    WaitUpdateInputResponse,
)
from app.trade_workspace.models.analysis_request import AnalysisRequestV2ObservationPeriod
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2Type
from app.trade_workspace.services.buy_decision import (
    BuyDecisionError,
    BuyDecisionService,
)
from app.trade_workspace.services.decision_availability import DecisionAvailabilityService
from app.trade_workspace.services.evidence_uploads import (
    InitialEvidenceInput,
    InitialEvidenceUploadError,
    InitialEvidenceUploadService,
)
from app.trade_workspace.services.initial_analysis_read import (
    InitialAnalysisReadError,
    InitialAnalysisReadService,
)
from app.trade_workspace.services.initial_analysis_retry import (
    InitialAnalysisRetryError,
    InitialAnalysisRetryService,
)
from app.trade_workspace.services.initial_analysis_submission import (
    InitialAnalysisSubmissionError,
    InitialAnalysisSubmissionService,
)
from app.trade_workspace.services.skip_decision import (
    SkipDecisionError,
    SkipDecisionService,
)
from app.trade_workspace.services.trade_sessions import RebuildTradeSessionService
from app.trade_workspace.services.wait_decision import (
    WaitDecisionError,
    WaitDecisionService,
)
from app.trade_workspace.services.wait_update_input import (
    WaitUpdateInputError,
    WaitUpdateInputService,
)

router = APIRouter(prefix="/api/v2/trade-sessions", tags=["rebuild-trade-sessions"])


def get_rebuild_analysis_queue(request: Request) -> object:
    queue = getattr(request.app.state, "rebuild_analysis_queue", None)
    if queue is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "QUEUE_UNAVAILABLE", "message": "Analysis queue is unavailable"},
        )
    return queue


def _to_response(trade_session: object) -> TradeSessionResponse:
    status_value = (
        trade_session.status.value
        if hasattr(trade_session.status, "value")
        else str(trade_session.status)
    )
    return TradeSessionResponse(
        id=str(trade_session.id),
        ticker=trade_session.ticker,
        company_name=trade_session.company_name,
        status=status_value,
        note=trade_session.note,
        created_at=trade_session.created_at,
        updated_at=trade_session.updated_at,
        closed_at=trade_session.closed_at,
    )


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": SESSION_NOT_FOUND, "message": get_error_message(SESSION_NOT_FOUND)},
    )


def _upload_error(exc: Exception) -> HTTPException:
    code = getattr(exc, "code", "INITIAL_EVIDENCE_UPLOAD_FAILED")
    message = {
        "SESSION_NOT_FOUND": "Trade session not found",
        "SESSION_NOT_ELIGIBLE": "Trade session is not eligible for initial evidence",
        "INITIAL_EVIDENCE_EXISTS": "Initial evidence already exists",
        "INITIAL_EVIDENCE_INVALID_FILE": "Initial evidence files are invalid",
        "INITIAL_EVIDENCE_STORAGE_FAILED": "Initial evidence storage failed",
        "INITIAL_EVIDENCE_PERSISTENCE_FAILED": "Initial evidence could not be persisted",
    }.get(code, "Initial evidence upload failed")
    return HTTPException(
        status_code=getattr(exc, "status_code", 422),
        detail={"code": code, "message": message},
    )


def _safe_original_filename(filename: str | None) -> str:
    value = (filename or "upload").replace("\\", "/").split("/")[-1].strip()
    return (value or "upload")[:255]


def _evidence_response(item: object) -> InitialEvidenceResponse:
    return InitialEvidenceResponse(
        id=str(item.id),
        evidence_type=item.evidence_type.value,
        original_filename=item.original_filename,
        mime_type=item.mime_type,
        size_bytes=item.size_bytes,
        uploaded_at=item.uploaded_at,
    )


@router.post("", response_model=TradeSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_trade_session(
    body: TradeSessionCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> TradeSessionResponse:
    trade_session = await RebuildTradeSessionService(db_session).create(
        user_id=current_user.id,
        ticker=body.ticker,
        company_name=body.company_name,
        note=body.note,
    )
    return _to_response(trade_session)


@router.post(
    "/{session_id}/initial-evidence",
    response_model=InitialEvidenceUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_initial_evidence(
    session_id: uuid.UUID,
    orderbook: UploadFile = File(...),
    chart_3_month: UploadFile = File(...),
    chart_6_month: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> InitialEvidenceUploadResponse:
    uploads = (
        (orderbook, EvidenceUploadV2Type.ORDERBOOK),
        (chart_3_month, EvidenceUploadV2Type.CHART_3_MONTH),
        (chart_6_month, EvidenceUploadV2Type.CHART_6_MONTH),
    )
    inputs = [
        InitialEvidenceInput(
            evidence_type=evidence_type,
            original_filename=_safe_original_filename(upload.filename),
            mime_type=upload.content_type or "",
            content=await upload.read(),
        )
        for upload, evidence_type in uploads
    ]
    try:
        records = await InitialEvidenceUploadService(db_session).upload(
            user_id=current_user.id,
            session_id=session_id,
            files=inputs,
        )
    except InitialEvidenceUploadError as exc:
        raise _upload_error(exc) from exc
    return InitialEvidenceUploadResponse(evidence=[_evidence_response(item) for item in records])


@router.post(
    "/{session_id}/wait-update-input",
    response_model=WaitUpdateInputResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_wait_update_input(
    session_id: uuid.UUID,
    orderbook: UploadFile = File(...),
    current_price: Decimal = Form(...),
    observation_period: AnalysisRequestV2ObservationPeriod = Form(...),
    observation_timestamp: datetime = Form(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> WaitUpdateInputResponse:
    try:
        result = await WaitUpdateInputService(db_session).submit(
            user_id=current_user.id,
            session_id=session_id,
            original_filename=_safe_original_filename(orderbook.filename),
            mime_type=orderbook.content_type or "",
            content=await orderbook.read(),
            current_price=current_price,
            observation_period=observation_period,
            observation_timestamp=observation_timestamp,
        )
    except WaitUpdateInputError as exc:
        if exc.code == "SESSION_NOT_FOUND":
            raise _not_found() from exc
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    return WaitUpdateInputResponse(
        evidence_id=str(result.evidence_id),
        session_id=str(result.session_id),
        evidence_type=result.evidence_type.value,
        original_filename=result.original_filename,
        mime_type=result.mime_type,
        size_bytes=result.size_bytes,
        current_price=result.current_price,
        observation_period=result.observation_period.value,
        observation_timestamp=result.observation_timestamp,
        uploaded_at=result.uploaded_at,
        session_status=result.session_status.value,
    )


@router.post(
    "/{session_id}/initial-analysis",
    response_model=InitialAnalysisSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_initial_analysis(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
    queue: object = Depends(get_rebuild_analysis_queue),
) -> InitialAnalysisSubmissionResponse:
    try:
        result = await InitialAnalysisSubmissionService(db_session, queue).submit(
            user_id=current_user.id,
            session_id=session_id,
        )
    except InitialAnalysisSubmissionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    return InitialAnalysisSubmissionResponse(
        analysis_request_id=str(result.analysis_request_id),
        session_id=str(result.session_id),
        analysis_type=result.analysis_type.value,
        request_status=result.request_status.value,
        session_status=result.session_status.value,
        created_at=result.created_at,
    )


@router.get(
    "/{session_id}/initial-analysis",
    response_model=InitialAnalysisReadResponse,
)
async def read_initial_analysis(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> InitialAnalysisReadResponse:
    try:
        result = await InitialAnalysisReadService(db_session).get_latest(
            user_id=current_user.id,
            session_id=session_id,
        )
    except InitialAnalysisReadError as exc:
        raise _not_found() from exc
    return InitialAnalysisReadResponse(
        analysis_request_id=str(result.analysis_request_id),
        session_id=str(result.session_id),
        analysis_type=result.analysis_type.value,
        request_status=result.request_status.value,
        session_status=result.session_status.value,
        processed_response=result.processed_response,
        error_code=result.error_code,
        error_message=result.error_message,
        created_at=result.created_at,
        started_at=result.started_at,
        completed_at=result.completed_at,
    )


@router.post(
    "/{session_id}/initial-analysis/retry",
    response_model=InitialAnalysisSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_initial_analysis(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
    queue: object = Depends(get_rebuild_analysis_queue),
) -> InitialAnalysisSubmissionResponse:
    try:
        result = await InitialAnalysisRetryService(db_session, queue).retry(
            user_id=current_user.id,
            session_id=session_id,
        )
    except InitialAnalysisRetryError as exc:
        if exc.code == "SESSION_NOT_FOUND":
            raise _not_found() from exc
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    return InitialAnalysisSubmissionResponse(
        analysis_request_id=str(result.analysis_request_id),
        session_id=str(result.session_id),
        analysis_type=result.analysis_type.value,
        request_status=result.request_status.value,
        session_status=result.session_status.value,
        created_at=result.created_at,
    )


@router.get("", response_model=TradeSessionListResponse)
async def list_trade_sessions(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> TradeSessionListResponse:
    sessions = await RebuildTradeSessionService(db_session).list_owned(
        user_id=current_user.id
    )
    return TradeSessionListResponse(sessions=[_to_response(item) for item in sessions])


@router.get(
    "/{session_id}/available-actions",
    response_model=DecisionAvailabilityResponse,
)
async def get_available_actions(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> DecisionAvailabilityResponse:
    result = await DecisionAvailabilityService(db_session).get_owned(
        user_id=current_user.id,
        session_id=session_id,
    )
    if result is None:
        raise _not_found()
    return DecisionAvailabilityResponse(
        session_id=str(result.session_id),
        session_status=result.session_status.value,
        available_actions=list(result.available_actions),
    )


@router.post(
    "/{session_id}/decisions/wait",
    response_model=WaitDecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_wait_decision(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> WaitDecisionResponse:
    try:
        result = await WaitDecisionService(db_session).create(
            user_id=current_user.id,
            session_id=session_id,
        )
    except WaitDecisionError as exc:
        if exc.code == "SESSION_NOT_FOUND":
            raise _not_found() from exc
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    return WaitDecisionResponse(
        decision_id=str(result.decision_id),
        session_id=str(result.session_id),
        decision_type=result.decision_type.value,
        decision_at=result.decision_at,
        session_status=result.session_status.value,
    )


@router.post(
    "/{session_id}/decisions/buy",
    response_model=BuyDecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_buy_decision(
    session_id: uuid.UUID,
    body: BuyDecisionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> BuyDecisionResponse:
    try:
        result = await BuyDecisionService(db_session).create(
            user_id=current_user.id,
            session_id=session_id,
            entry_price=body.entry_price,
            entry_timestamp=body.entry_timestamp,
            quantity=body.quantity,
            stop_loss=body.stop_loss,
            target_price=body.target_price,
            note=body.note,
        )
    except BuyDecisionError as exc:
        if exc.code == "SESSION_NOT_FOUND":
            raise _not_found() from exc
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    return BuyDecisionResponse(
        decision_id=str(result.decision_id),
        session_id=str(result.session_id),
        decision_type=result.decision_type.value,
        decision_at=result.decision_at,
        position_id=str(result.position_id),
        position_status=result.position_status.value,
        entry_price=result.entry_price,
        entry_timestamp=result.entry_timestamp,
        quantity=result.quantity,
        stop_loss=result.stop_loss,
        target_price=result.target_price,
        note=result.note,
        session_status=result.session_status.value,
    )


@router.post(
    "/{session_id}/decisions/skip",
    response_model=SkipDecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_skip_decision(
    session_id: uuid.UUID,
    body: SkipDecisionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> SkipDecisionResponse:
    try:
        result = await SkipDecisionService(db_session).create(
            user_id=current_user.id,
            session_id=session_id,
            reason=body.reason,
            note=body.note,
        )
    except SkipDecisionError as exc:
        if exc.code == "SESSION_NOT_FOUND":
            raise _not_found() from exc
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    return SkipDecisionResponse(
        decision_id=str(result.decision_id),
        session_id=str(result.session_id),
        decision_type=result.decision_type.value,
        reason=result.reason.value,
        note=result.note,
        decision_at=result.decision_at,
        session_status=result.session_status.value,
        closed_at=result.closed_at,
    )


@router.get("/{session_id}", response_model=TradeSessionResponse)
async def get_trade_session(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> TradeSessionResponse:
    trade_session = await RebuildTradeSessionService(db_session).get_owned(
        user_id=current_user.id,
        session_id=session_id,
    )
    if trade_session is None:
        raise _not_found()
    return _to_response(trade_session)
