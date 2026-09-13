from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.errors import SESSION_NOT_FOUND, get_error_message
from app.auth import AuthenticatedUser
from app.database.session import get_db_session
from app.trade_workspace.api.schemas import (
    BuyDecisionRequest,
    BuyDecisionResponse,
    CloseRequest,
    CloseResponse,
    DecisionAvailabilityResponse,
    InitialAnalysisReadResponse,
    SessionDetailAggregateResponse,
    SkipDecisionRequest,
    SkipDecisionResponse,
    TradeSessionArchiveResponse,
    TradeSessionCreateRequest,
    TradeSessionListResponse,
    TradeSessionResponse,
    WaitDecisionResponse,
)
from app.trade_workspace.services.buy_decision import (
    BuyDecisionError,
    BuyDecisionService,
)
from app.trade_workspace.services.close import (
    CloseError,
    CloseService,
)
from app.trade_workspace.services.decision_availability import DecisionAvailabilityService
from app.trade_workspace.services.initial_analysis_read import (
    InitialAnalysisReadError,
    InitialAnalysisReadService,
)
from app.trade_workspace.services.session_detail_aggregate import (
    SessionDetailAggregateNotFoundError,
    SessionDetailAggregateService,
)
from app.trade_workspace.services.skip_decision import (
    SkipDecisionError,
    SkipDecisionService,
)
from app.trade_workspace.services.trade_sessions import (
    ArchiveError,
    RebuildTradeSessionService,
)
from app.trade_workspace.services.wait_decision import (
    WaitDecisionError,
    WaitDecisionService,
)

router = APIRouter(prefix="/api/v2/trade-sessions", tags=["rebuild-trade-sessions"])


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
        archived_at=trade_session.archived_at,
    )


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": SESSION_NOT_FOUND, "message": get_error_message(SESSION_NOT_FOUND)},
    )


def _archive_error(exc: ArchiveError) -> HTTPException:
    if exc.code == "SESSION_NOT_FOUND":
        return _not_found()
    messages = {
        "ARCHIVE_NOT_ALLOWED": "Trade session cannot be archived in its current state",
        "SESSION_ALREADY_ARCHIVED": "Trade session is already archived",
        "RESTORE_NOT_ALLOWED": "Trade session cannot be restored in its current state",
        "SESSION_NOT_ARCHIVED": "Trade session is not archived",
        "ARCHIVE_PERSISTENCE_FAILED": "Trade session archive operation failed",
    }
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": messages.get(exc.code, "Archive operation failed")},
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
        market_facts=result.market_facts,
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


@router.get("/archived", response_model=TradeSessionListResponse)
async def list_archived_trade_sessions(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> TradeSessionListResponse:
    sessions = await RebuildTradeSessionService(db_session).list_owned_archived(
        user_id=current_user.id
    )
    return TradeSessionListResponse(sessions=[_to_response(item) for item in sessions])


@router.post(
    "/{session_id}/archive",
    response_model=TradeSessionArchiveResponse,
)
async def archive_trade_session(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> TradeSessionArchiveResponse:
    try:
        result = await RebuildTradeSessionService(db_session).archive(
            user_id=current_user.id,
            session_id=session_id,
        )
    except ArchiveError as exc:
        raise _archive_error(exc) from exc
    return TradeSessionArchiveResponse(
        id=str(result.session_id),
        status=result.session_status.value,
        archived_at=result.archived_at,
    )


@router.post(
    "/{session_id}/restore",
    response_model=TradeSessionArchiveResponse,
)
async def restore_trade_session(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> TradeSessionArchiveResponse:
    try:
        result = await RebuildTradeSessionService(db_session).restore(
            user_id=current_user.id,
            session_id=session_id,
        )
    except ArchiveError as exc:
        raise _archive_error(exc) from exc
    return TradeSessionArchiveResponse(
        id=str(result.session_id),
        status=result.session_status.value,
        archived_at=result.archived_at,
    )


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


@router.get("/{session_id}/detail", response_model=SessionDetailAggregateResponse)
async def get_session_detail_aggregate(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> SessionDetailAggregateResponse:
    try:
        result = await SessionDetailAggregateService(db_session).get(
            user_id=current_user.id,
            session_id=session_id,
        )
    except SessionDetailAggregateNotFoundError:
        raise _not_found()
    return SessionDetailAggregateResponse(**result.payload)


@router.post(
    "/{session_id}/close",
    response_model=CloseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_close(
    session_id: uuid.UUID,
    body: CloseRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> CloseResponse:
    try:
        result = await CloseService(db_session).create(
            user_id=current_user.id,
            session_id=session_id,
            close_price=body.close_price,
            close_timestamp=body.close_timestamp,
            close_reason=body.close_reason,
            note=body.note,
        )
    except CloseError as exc:
        if exc.code == "SESSION_NOT_FOUND":
            raise _not_found() from exc
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    return CloseResponse(
        closure_id=str(result.closure_id),
        session_id=str(result.session_id),
        position_id=str(result.position_id),
        close_price=result.close_price,
        close_timestamp=result.close_timestamp,
        close_reason=result.close_reason,
        note=result.note,
        realized_profit_loss=result.realized_profit_loss,
        position_status=result.position_status.value,
        session_status=result.session_status.value,
        closed_at=result.closed_at,
        created_at=result.created_at,
    )
