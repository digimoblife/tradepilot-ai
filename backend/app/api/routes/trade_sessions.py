"""Trade Session API routes (TP-1002)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.schemas.trade_sessions import (
    ConfirmStopRequest,
    ConfirmTargetRequest,
    EvidenceBatchSummaryResponse,
    StopLossConfirmResponse,
    TargetConfirmResponse,
    TradeSessionArchiveResponse,
    TradeSessionCreateRequest,
    TradeSessionCreateResponse,
    TradeSessionDetailWithActionsResponse,
    TradeSessionListResponse,
    TradeSessionReadyResponse,
    TradeSessionSummaryResponse,
    TradeSessionUpdateRequest,
    TradeStateResponse,
    UpdateMonitoringSlotRequest,
)
from app.auth import AuthenticatedUser
from app.database.session import get_db_session
from app.lifecycle.service import InvalidSessionTransitionError, SessionLifecycleService
from app.lifecycle.transitions import get_allowed_transitions
from app.models.analysis_job import AnalysisJob
from app.models.enums import AnalysisJobStatus, AnalysisType, EvidenceBatchStatus, TradeSessionStatus
from app.models.evidence_batch import EvidenceBatch
from app.models.trade_session import TradeSession
from app.repositories.trade_session import TradeSessionRepository
from app.repositories.trade_state import TradeStateRepository
from app.services.actions.archive_session import ArchiveSessionActionService
from app.services.actions.stop_loss import (
    StopLossActionService,
    StopLossInvalidInputError,
    StopLossInvalidRelationshipError,
    StopLossInvalidStateError,
    StopLossNotFoundError,
)
from app.services.actions.target import (
    TargetActionService,
    TargetInvalidInputError,
    TargetInvalidRelationshipError,
    TargetInvalidStateError,
    TargetNotFoundError,
)
from app.services.evidence_batches import (
    EvidenceBatchInvalidSlotError,
    EvidenceBatchInvalidStateError,
    EvidenceBatchService,
)
from app.services.evidence import EvidenceService
from app.services.trade_session import TradeSessionService

router = APIRouter(prefix="/api/trade-sessions", tags=["trade-sessions"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _load_session(
    db_session: AsyncSession,
    session_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> tuple[TradeSessionSummaryResponse, TradeStateResponse, TradeSession] | None:
    """Load session and trade_state for an owner. Returns None if not found."""
    repo = TradeSessionRepository(db_session)
    ts = await repo.get_by_id_for_user(session_id, owner_id)
    if ts is None:
        return None

    state_repo = TradeStateRepository(db_session)
    trade_state = await state_repo.get_for_user(session_id, owner_id)

    session_resp = TradeSessionSummaryResponse(
        id=str(ts.id),
        ticker=ts.ticker,
        company_name=ts.company_name,
        exchange=ts.market.value if hasattr(ts.market, "value") else str(ts.market),
        currency=ts.currency.value if hasattr(ts.currency, "value") else str(ts.currency),
        title=ts.title,
        lifecycle_status=ts.lifecycle_status.value,
        created_at=ts.created_at,
        updated_at=ts.updated_at,
        archived_at=ts.archived_at,
    )

    if trade_state is not None:
        state_resp = TradeStateResponse(
            position_status=trade_state.position_status.value,
            thesis_status=trade_state.thesis_status.value,
            entry_price=trade_state.entry_price,
            entry_at=trade_state.entry_at,
            original_quantity=trade_state.original_quantity,
            remaining_quantity=trade_state.remaining_quantity,
            active_stop_loss=trade_state.active_stop_loss,
            active_target=trade_state.active_target,
            average_exit_price=trade_state.average_exit_price,
            realized_pnl=trade_state.realized_pnl,
            realized_return=trade_state.realized_return,
            state_version=trade_state.state_version,
        )
    else:
        from app.models.enums import PositionStatus, ThesisStatus

        state_resp = TradeStateResponse(
            position_status=PositionStatus.NOT_OPENED.value,
            thesis_status=ThesisStatus.INTACT.value,
            state_version=1,
        )

    return session_resp, state_resp, ts


def _derive_allowed_actions(lifecycle_status: str) -> list[str]:
    """Return the list of user-facing actions allowed by the current lifecycle status."""
    actions: list[str] = []

    try:
        current = TradeSessionStatus(lifecycle_status)
    except ValueError:
        return actions

    if current == TradeSessionStatus.ARCHIVED:
        return actions

    allowed_targets = get_allowed_transitions(current)

    if TradeSessionStatus.READY_FOR_INITIAL_ANALYSIS in allowed_targets:
        actions.append("MARK_READY")
    if current in {
        TradeSessionStatus.READY_FOR_INITIAL_ANALYSIS,
        TradeSessionStatus.READY_FOR_ANALYSIS,
    }:
        actions.append("REQUEST_INITIAL_ANALYSIS")
    if current == TradeSessionStatus.INITIAL_ANALYZED:
        actions.extend(["OPEN_POSITION", "WAIT", "SKIP"])
    if current == TradeSessionStatus.WATCHING:
        actions.extend(["REQUEST_WATCHING_UPDATE", "OPEN_POSITION", "WAIT", "SKIP"])
    if current == TradeSessionStatus.OPEN_POSITION:
        actions.extend(
            [
                "REQUEST_OPEN_POSITION_UPDATE",
                "CONFIRM_STOP",
                "CHANGE_STOP",
                "CONFIRM_TARGET",
                "CHANGE_TARGET",
                "FULL_EXIT",
            ]
        )
    if current in {
        TradeSessionStatus.CLOSED,
        TradeSessionStatus.CLOSED_TAKE_PROFIT,
        TradeSessionStatus.CLOSED_STOP_LOSS,
        TradeSessionStatus.CLOSED_MANUAL,
    }:
        actions.append("REQUEST_CLOSING_ANALYSIS")
    if TradeSessionStatus.CANCELLED in allowed_targets:
        actions.append("CANCEL")
    if TradeSessionStatus.ARCHIVED in allowed_targets:
        actions.append("ARCHIVE")

    return actions


def _batch_to_response(batch: object) -> EvidenceBatchSummaryResponse:
    return EvidenceBatchSummaryResponse(
        id=str(batch.id),
        session_id=str(batch.session_id),
        analysis_type=batch.analysis_type.value
        if hasattr(batch.analysis_type, "value")
        else str(batch.analysis_type),
        status=batch.status.value if hasattr(batch.status, "value") else str(batch.status),
        sequence_number=batch.sequence_number,
        label=batch.label,
        monitoring_slot=getattr(batch, "monitoring_slot", None),
        created_at=batch.created_at,
        ready_at=batch.ready_at,
        processing_at=batch.processing_at,
        frozen_at=batch.frozen_at,
        failed_at=batch.failed_at,
    )


def _current_batch_analysis_type(status: TradeSessionStatus) -> AnalysisType | None:
    if status == TradeSessionStatus.WATCHING:
        return AnalysisType.WATCHING_UPDATE
    if status == TradeSessionStatus.OPEN_POSITION:
        return AnalysisType.OPEN_POSITION_UPDATE
    if status in {
        TradeSessionStatus.DRAFT,
        TradeSessionStatus.READY_FOR_INITIAL_ANALYSIS,
        TradeSessionStatus.READY_FOR_ANALYSIS,
        TradeSessionStatus.ANALYZING,
        TradeSessionStatus.INITIAL_ANALYZED,
    }:
        return AnalysisType.INITIAL_ANALYSIS
    return None


async def _active_job_batch(
    db_session: AsyncSession,
    *,
    session_id: uuid.UUID,
) -> EvidenceBatch | None:
    active_statuses = (
        AnalysisJobStatus.CREATED,
        AnalysisJobStatus.QUEUED,
        AnalysisJobStatus.PROCESSING,
        AnalysisJobStatus.RETRYING,
    )
    result = await db_session.execute(
        select(AnalysisJob)
        .where(
            AnalysisJob.session_id == session_id,
            AnalysisJob.status.in_(active_statuses),
            AnalysisJob.evidence_batch_id.is_not(None),
        )
        .order_by(AnalysisJob.created_at.desc())
        .limit(1)
    )
    job = result.unique().scalar_one_or_none()
    if job is None or job.evidence_batch_id is None:
        return None
    return await db_session.get(EvidenceBatch, job.evidence_batch_id)


# ---------------------------------------------------------------------------
# POST /
# ---------------------------------------------------------------------------


@router.post("", response_model=TradeSessionCreateResponse, status_code=201)
async def create_trade_session(
    body: TradeSessionCreateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> TradeSessionCreateResponse:
    svc = TradeSessionService(db_session)
    ts = await svc.create_session(
        owner_id=current_user.id,
        ticker=body.ticker,
        currency=body.currency,
        company_name=body.company_name,
        title=body.title,
    )
    return TradeSessionCreateResponse(
        id=str(ts.id),
        ticker=ts.ticker,
        company_name=ts.company_name,
        exchange=ts.market.value if hasattr(ts.market, "value") else str(ts.market),
        currency=ts.currency.value if hasattr(ts.currency, "value") else str(ts.currency),
        title=ts.title,
        lifecycle_status=ts.lifecycle_status.value,
        created_at=ts.created_at,
        updated_at=ts.updated_at,
    )


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------


@router.get("", response_model=TradeSessionListResponse)
async def list_trade_sessions(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
    status: str | None = Query(None, description="Filter by lifecycle status"),
    ticker: str | None = Query(None, max_length=32),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> TradeSessionListResponse:
    repo = TradeSessionRepository(db_session)
    sessions = await repo.list_for_user(
        current_user.id,
        limit=limit,
        offset=offset,
    )

    if status:
        sessions = [s for s in sessions if s.lifecycle_status.value == status]
    if ticker:
        sessions = [s for s in sessions if s.ticker == ticker.strip().upper()]

    result = [
        TradeSessionSummaryResponse(
            id=str(s.id),
            ticker=s.ticker,
            company_name=s.company_name,
            exchange=s.market.value if hasattr(s.market, "value") else str(s.market),
            currency=s.currency.value if hasattr(s.currency, "value") else str(s.currency),
            title=s.title,
            lifecycle_status=s.lifecycle_status.value,
            created_at=s.created_at,
            updated_at=s.updated_at,
            archived_at=s.archived_at,
        )
        for s in sessions
    ]
    return TradeSessionListResponse(sessions=result, total=len(result))


# ---------------------------------------------------------------------------
# GET /{session_id}
# ---------------------------------------------------------------------------


@router.get("/{session_id}", response_model=TradeSessionDetailWithActionsResponse)
async def get_trade_session(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> TradeSessionDetailWithActionsResponse:
    loaded = await _load_session(db_session, session_id, current_user.id)
    if loaded is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Trade session not found")

    session_resp, state_resp, ts = loaded
    actions = _derive_allowed_actions(ts.lifecycle_status.value)
    batch_svc = EvidenceBatchService(db_session)
    current_batch = None
    if ts.lifecycle_status == TradeSessionStatus.ANALYZING:
        current_batch = await _active_job_batch(db_session, session_id=session_id)
    batch_analysis_type = _current_batch_analysis_type(ts.lifecycle_status)
    if current_batch is None and batch_analysis_type is not None:
        current_batch = await batch_svc.get_latest_for_session(
            session_id=session_id,
            owner_id=current_user.id,
            analysis_type=batch_analysis_type,
        )
    batches = await batch_svc.list_for_session(session_id=session_id, owner_id=current_user.id)

    return TradeSessionDetailWithActionsResponse(
        session=session_resp,
        trade_state=state_resp,
        allowed_actions=actions,
        evidence_batches=[_batch_to_response(b) for b in batches],
        current_evidence_batch=_batch_to_response(current_batch) if current_batch else None,
    )


# ---------------------------------------------------------------------------
# PATCH /{session_id}
# ---------------------------------------------------------------------------


@router.patch("/{session_id}", response_model=TradeSessionSummaryResponse)
async def update_trade_session(
    session_id: uuid.UUID,
    body: TradeSessionUpdateRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> TradeSessionSummaryResponse:
    repo = TradeSessionRepository(db_session)
    ts = await repo.get_by_id_for_user(session_id, current_user.id)
    if ts is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Trade session not found")

    if body.title is not None:
        ts.title = body.title
    if body.company_name is not None:
        ts.company_name = body.company_name
    if body.exchange is not None:
        from app.models.enums import Market

        try:
            ts.market = Market(body.exchange.upper())
        except ValueError:
            from fastapi import HTTPException

            raise HTTPException(status_code=422, detail=f"Invalid exchange: {body.exchange}")
    if body.currency is not None:
        from app.models.enums import Currency

        ts.currency = Currency(body.currency.upper())
    if body.ticker is not None:
        ts.ticker = body.ticker.strip().upper()

    await db_session.flush()
    await db_session.refresh(ts)

    return TradeSessionSummaryResponse(
        id=str(ts.id),
        ticker=ts.ticker,
        company_name=ts.company_name,
        exchange=ts.market.value if hasattr(ts.market, "value") else str(ts.market),
        currency=ts.currency.value if hasattr(ts.currency, "value") else str(ts.currency),
        title=ts.title,
        lifecycle_status=ts.lifecycle_status.value,
        created_at=ts.created_at,
        updated_at=ts.updated_at,
        archived_at=ts.archived_at,
    )


# ---------------------------------------------------------------------------
# POST /{session_id}/ready
# ---------------------------------------------------------------------------


@router.post("/{session_id}/ready", response_model=TradeSessionReadyResponse)
async def ready_trade_session(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> TradeSessionReadyResponse:
    repo = TradeSessionRepository(db_session)
    ts_check = await repo.get_by_id_for_user(session_id, current_user.id)
    if ts_check is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Trade session not found")
    if ts_check.lifecycle_status != TradeSessionStatus.DRAFT:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_SESSION_TRANSITION",
                "message": "Only DRAFT sessions can be marked ready.",
            },
        )

    batch_svc = EvidenceBatchService(db_session)
    batch = await batch_svc.get_current_draft(
        session_id=session_id,
        owner_id=current_user.id,
    )
    if batch is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail={
                "code": "ANALYSIS_REQUIRED_EVIDENCE_MISSING",
                "message": "Missing Initial Analysis evidence batch",
            },
        )
    evidence_svc = EvidenceService(db_session)
    required = await evidence_svc.get_required_evidence(
        session_id=session_id,
        owner_id=current_user.id,
        analysis_type="INITIAL_ANALYSIS",
        evidence_batch_id=batch.id,
    )
    if not required.complete:
        from fastapi import HTTPException

        missing = ", ".join(t.value for t in required.missing_types)
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ANALYSIS_REQUIRED_EVIDENCE_MISSING",
                "message": f"Missing required evidence: {missing}",
            },
        )
    await batch_svc.mark_ready(batch)

    lc = SessionLifecycleService(db_session)
    try:
        ts = await lc.transition(
            session_id=session_id,
            owner_id=current_user.id,
            target_status=TradeSessionStatus.READY_FOR_INITIAL_ANALYSIS,
        )
    except InvalidSessionTransitionError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail={"code": exc.code, "message": str(exc)})

    return TradeSessionReadyResponse(
        id=str(ts.id),
        lifecycle_status=ts.lifecycle_status.value,
    )


# ---------------------------------------------------------------------------
# POST /{session_id}/initial-batches/{batch_id}/ready
# ---------------------------------------------------------------------------


@router.post(
    "/{session_id}/initial-batches/{batch_id}/ready",
    response_model=EvidenceBatchSummaryResponse,
)
async def ready_initial_analysis_batch(
    session_id: uuid.UUID,
    batch_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> EvidenceBatchSummaryResponse:
    from fastapi import HTTPException

    repo = TradeSessionRepository(db_session)
    ts = await repo.get_by_id_for_user(session_id, current_user.id)
    if ts is None:
        raise HTTPException(status_code=404, detail="Trade session not found")
    if ts.lifecycle_status != TradeSessionStatus.READY_FOR_INITIAL_ANALYSIS:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INITIAL_BATCH_INVALID_SESSION_STATE",
                "message": (
                    "Initial Analysis batch readiness is only allowed while "
                    "READY_FOR_INITIAL_ANALYSIS."
                ),
            },
        )

    batch_svc = EvidenceBatchService(db_session)
    batch = await batch_svc.get_for_user(batch_id=batch_id, owner_id=current_user.id)
    if (
        batch is None
        or batch.session_id != session_id
        or batch.analysis_type != AnalysisType.INITIAL_ANALYSIS
    ):
        raise HTTPException(
            status_code=404,
            detail={
                "code": "INITIAL_BATCH_NOT_FOUND",
                "message": "Initial Analysis evidence batch not found.",
            },
        )

    evidence_svc = EvidenceService(db_session)
    required = await evidence_svc.get_required_evidence(
        session_id=session_id,
        owner_id=current_user.id,
        analysis_type=AnalysisType.INITIAL_ANALYSIS,
        evidence_batch_id=batch.id,
    )
    if not required.complete:
        missing = ", ".join(t.value for t in required.missing_types)
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ANALYSIS_REQUIRED_EVIDENCE_MISSING",
                "message": f"Missing required evidence: {missing}",
            },
        )

    if batch.status == EvidenceBatchStatus.READY:
        return _batch_to_response(batch)
    if batch.status != EvidenceBatchStatus.DRAFT:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INITIAL_BATCH_INVALID_STATE",
                "message": f"Cannot mark Initial Analysis batch ready from {batch.status.value}.",
            },
        )

    await batch_svc.mark_ready(batch)
    return _batch_to_response(batch)


# ---------------------------------------------------------------------------
# POST /{session_id}/watching-batches
# ---------------------------------------------------------------------------


@router.post("/{session_id}/watching-batches", response_model=EvidenceBatchSummaryResponse)
async def create_or_resolve_watching_batch(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> EvidenceBatchSummaryResponse:
    from fastapi import HTTPException

    repo = TradeSessionRepository(db_session)
    ts = await repo.get_by_id_for_user(session_id, current_user.id)
    if ts is None:
        raise HTTPException(status_code=404, detail="Trade session not found")
    if ts.lifecycle_status != TradeSessionStatus.WATCHING:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "WATCHING_BATCH_INVALID_SESSION_STATE",
                "message": "Watching Update batches can only be created while WATCHING.",
            },
        )

    batch_svc = EvidenceBatchService(db_session)
    batch = await batch_svc.get_or_create_current_draft(
        session_id=session_id,
        owner_id=current_user.id,
        analysis_type=AnalysisType.WATCHING_UPDATE,
    )
    return _batch_to_response(batch)


# ---------------------------------------------------------------------------
# POST /{session_id}/watching-batches/{batch_id}/ready
# ---------------------------------------------------------------------------


@router.post(
    "/{session_id}/watching-batches/{batch_id}/ready",
    response_model=EvidenceBatchSummaryResponse,
)
async def ready_watching_batch(
    session_id: uuid.UUID,
    batch_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> EvidenceBatchSummaryResponse:
    from fastapi import HTTPException

    repo = TradeSessionRepository(db_session)
    ts = await repo.get_by_id_for_user(session_id, current_user.id)
    if ts is None:
        raise HTTPException(status_code=404, detail="Trade session not found")
    if ts.lifecycle_status != TradeSessionStatus.WATCHING:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "WATCHING_BATCH_INVALID_SESSION_STATE",
                "message": "Watching Update readiness is only allowed while WATCHING.",
            },
        )

    batch_svc = EvidenceBatchService(db_session)
    batch = await batch_svc.get_for_user(batch_id=batch_id, owner_id=current_user.id)
    if (
        batch is None
        or batch.session_id != session_id
        or batch.analysis_type != AnalysisType.WATCHING_UPDATE
    ):
        raise HTTPException(
            status_code=404,
            detail={
                "code": "WATCHING_BATCH_NOT_FOUND",
                "message": "Watching Update evidence batch not found.",
            },
        )

    evidence_svc = EvidenceService(db_session)
    required = await evidence_svc.get_required_evidence(
        session_id=session_id,
        owner_id=current_user.id,
        analysis_type=AnalysisType.WATCHING_UPDATE,
        evidence_batch_id=batch.id,
    )
    if not required.complete:
        missing = ", ".join(t.value for t in required.missing_types)
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ANALYSIS_REQUIRED_EVIDENCE_MISSING",
                "message": f"Missing required evidence: {missing}",
            },
        )

    if batch.status == EvidenceBatchStatus.READY:
        return _batch_to_response(batch)
    if batch.status != EvidenceBatchStatus.DRAFT:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "WATCHING_BATCH_INVALID_STATE",
                "message": f"Cannot mark Watching Update batch ready from {batch.status.value}.",
            },
        )

    await batch_svc.mark_ready(batch)
    return _batch_to_response(batch)


# ---------------------------------------------------------------------------
# POST /{session_id}/open-position-batches
# ---------------------------------------------------------------------------


@router.post("/{session_id}/open-position-batches", response_model=EvidenceBatchSummaryResponse)
async def create_or_resolve_open_position_batch(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> EvidenceBatchSummaryResponse:
    from fastapi import HTTPException

    repo = TradeSessionRepository(db_session)
    ts = await repo.get_by_id_for_user(session_id, current_user.id)
    if ts is None:
        raise HTTPException(status_code=404, detail="Trade session not found")
    if ts.lifecycle_status != TradeSessionStatus.OPEN_POSITION:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "OPEN_POSITION_BATCH_INVALID_SESSION_STATE",
                "message": "Open Position Update batches can only be created while OPEN_POSITION.",
            },
        )

    batch_svc = EvidenceBatchService(db_session)
    batch = await batch_svc.get_or_create_current_draft(
        session_id=session_id,
        owner_id=current_user.id,
        analysis_type=AnalysisType.OPEN_POSITION_UPDATE,
    )
    return _batch_to_response(batch)


# ---------------------------------------------------------------------------
# PATCH /{session_id}/open-position-batches/{batch_id}/slot
# ---------------------------------------------------------------------------


@router.patch(
    "/{session_id}/open-position-batches/{batch_id}/slot",
    response_model=EvidenceBatchSummaryResponse,
)
async def update_open_position_batch_slot(
    session_id: uuid.UUID,
    batch_id: uuid.UUID,
    body: UpdateMonitoringSlotRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> EvidenceBatchSummaryResponse:
    from fastapi import HTTPException

    repo = TradeSessionRepository(db_session)
    ts = await repo.get_by_id_for_user(session_id, current_user.id)
    if ts is None:
        raise HTTPException(status_code=404, detail="Trade session not found")

    batch_svc = EvidenceBatchService(db_session)
    batch = await batch_svc.get_for_user(batch_id=batch_id, owner_id=current_user.id)
    if (
        batch is None
        or batch.session_id != session_id
        or batch.analysis_type != AnalysisType.OPEN_POSITION_UPDATE
    ):
        raise HTTPException(
            status_code=404,
            detail={
                "code": "OPEN_POSITION_BATCH_NOT_FOUND",
                "message": "Open Position Update evidence batch not found.",
            },
        )

    try:
        updated = await batch_svc.update_monitoring_slot(batch, body.slot)
    except EvidenceBatchInvalidSlotError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": exc.code, "message": str(exc)},
        )
    except EvidenceBatchInvalidStateError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": exc.code, "message": str(exc)},
        )

    return _batch_to_response(updated)


# ---------------------------------------------------------------------------
# POST /{session_id}/open-position-batches/{batch_id}/ready
# ---------------------------------------------------------------------------


@router.post(
    "/{session_id}/open-position-batches/{batch_id}/ready",
    response_model=EvidenceBatchSummaryResponse,
)
async def ready_open_position_batch(
    session_id: uuid.UUID,
    batch_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> EvidenceBatchSummaryResponse:
    from fastapi import HTTPException

    repo = TradeSessionRepository(db_session)
    ts = await repo.get_by_id_for_user(session_id, current_user.id)
    if ts is None:
        raise HTTPException(status_code=404, detail="Trade session not found")
    if ts.lifecycle_status != TradeSessionStatus.OPEN_POSITION:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "OPEN_POSITION_BATCH_INVALID_SESSION_STATE",
                "message": "Open Position Update readiness is only allowed while OPEN_POSITION.",
            },
        )

    batch_svc = EvidenceBatchService(db_session)
    batch = await batch_svc.get_for_user(batch_id=batch_id, owner_id=current_user.id)
    if (
        batch is None
        or batch.session_id != session_id
        or batch.analysis_type != AnalysisType.OPEN_POSITION_UPDATE
    ):
        raise HTTPException(
            status_code=404,
            detail={
                "code": "OPEN_POSITION_BATCH_NOT_FOUND",
                "message": "Open Position Update evidence batch not found.",
            },
        )

    evidence_svc = EvidenceService(db_session)
    required = await evidence_svc.get_required_evidence(
        session_id=session_id,
        owner_id=current_user.id,
        analysis_type=AnalysisType.OPEN_POSITION_UPDATE,
        evidence_batch_id=batch.id,
    )
    if not required.complete:
        missing = ", ".join(t.value for t in required.missing_types)
        raise HTTPException(
            status_code=422,
            detail={
                "code": "ANALYSIS_REQUIRED_EVIDENCE_MISSING",
                "message": f"Missing required evidence: {missing}",
            },
        )

    if batch.status == EvidenceBatchStatus.READY:
        return _batch_to_response(batch)
    if batch.status != EvidenceBatchStatus.DRAFT:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "OPEN_POSITION_BATCH_INVALID_STATE",
                "message": f"Cannot mark Open Position Update batch ready from {batch.status.value}.",
            },
        )

    await batch_svc.mark_ready(batch)
    return _batch_to_response(batch)


# ---------------------------------------------------------------------------
# POST /{session_id}/confirm-stop
# ---------------------------------------------------------------------------


@router.post("/{session_id}/confirm-stop", response_model=StopLossConfirmResponse)
async def confirm_stop_loss(
    session_id: uuid.UUID,
    body: ConfirmStopRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> StopLossConfirmResponse:
    from fastapi import HTTPException

    svc = StopLossActionService(db_session)
    try:
        result = await svc.confirm(
            session_id=session_id,
            owner_id=current_user.id,
            idempotency_key=body.idempotency_key,
            stop_loss=body.price,
            confirmed_at=body.confirmed_at or datetime.now(timezone.utc),
            note=body.note,
        )
    except StopLossNotFoundError:
        raise HTTPException(status_code=404, detail="Trade session not found")
    except (StopLossInvalidStateError, StopLossInvalidInputError, StopLossInvalidRelationshipError) as exc:
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": str(exc)})

    return StopLossConfirmResponse(
        session_id=str(result.session_id),
        action_type=result.action_type.value,
        active_stop_loss=result.active_stop_loss,
    )


# ---------------------------------------------------------------------------
# POST /{session_id}/confirm-target
# ---------------------------------------------------------------------------


@router.post("/{session_id}/confirm-target", response_model=TargetConfirmResponse)
async def confirm_target(
    session_id: uuid.UUID,
    body: ConfirmTargetRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> TargetConfirmResponse:
    from fastapi import HTTPException

    svc = TargetActionService(db_session)
    try:
        result = await svc.confirm(
            session_id=session_id,
            owner_id=current_user.id,
            idempotency_key=body.idempotency_key,
            target=body.price,
            confirmed_at=body.confirmed_at or datetime.now(timezone.utc),
            note=body.note,
        )
    except TargetNotFoundError:
        raise HTTPException(status_code=404, detail="Trade session not found")
    except (TargetInvalidStateError, TargetInvalidInputError, TargetInvalidRelationshipError) as exc:
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": str(exc)})

    return TargetConfirmResponse(
        session_id=str(result.session_id),
        action_type=result.action_type.value,
        active_target=result.active_target,
    )


# ---------------------------------------------------------------------------
# POST /{session_id}/archive
# ---------------------------------------------------------------------------


@router.post("/{session_id}/archive", response_model=TradeSessionArchiveResponse)
async def archive_trade_session(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> TradeSessionArchiveResponse:
    from app.services.actions.archive_session import (
        ArchiveSessionInvalidStateError,
        ArchiveSessionNotFoundError,
    )

    svc = ArchiveSessionActionService(db_session)
    try:
        result = await svc.confirm(
            session_id=session_id,
            owner_id=current_user.id,
            idempotency_key=(
                f"api_archive_{session_id}_{current_user.id}_"
                f"{datetime.now(timezone.utc).timestamp()}"
            ),
            archived_at=datetime.now(timezone.utc),
        )
    except ArchiveSessionNotFoundError:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Trade session not found")
    except ArchiveSessionInvalidStateError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail={"code": exc.code, "message": str(exc)})
    return TradeSessionArchiveResponse(
        id=str(result.session_id),
        lifecycle_status=result.session_status.value,
        archived_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# POST /{session_id}/closing-analysis
# ---------------------------------------------------------------------------


@router.post("/{session_id}/closing-analysis", response_model=dict[str, object], status_code=202)
async def request_closing_analysis(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    from fastapi import HTTPException
    from app.services.analysis_jobs import (
        AnalysisJobCreationService,
        AnalysisJobSessionNotFoundError,
        AnalysisTypeInvalidForLifecycleError,
        AnalysisJobAlreadyActiveError,
        AnalysisJobAcceptedAlreadyExistsError,
        AnalysisRequiredEvidenceMissingError,
    )

    svc = AnalysisJobCreationService(db_session)
    try:
        result = await svc.create(
            session_id=session_id,
            owner_id=current_user.id,
            analysis_type=AnalysisType.CLOSING_ANALYSIS,
        )
    except AnalysisJobSessionNotFoundError:
        raise HTTPException(status_code=404, detail="Trade session not found")
    except AnalysisTypeInvalidForLifecycleError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "CLOSING_ANALYSIS_INVALID_SESSION_STATE",
                "message": str(exc),
            },
        )
    except (AnalysisJobAlreadyActiveError, AnalysisJobAcceptedAlreadyExistsError) as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": exc.code,
                "message": exc.message if hasattr(exc, "message") else str(exc),
            },
        )
    except AnalysisRequiredEvidenceMissingError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": exc.code, "message": str(exc)},
        )

    return {
        "job_id": str(result.job_id),
        "session_id": str(result.session_id),
        "analysis_type": result.analysis_type,
        "status": result.job_status,
        "previous_session_status": result.previous_session_status,
        "current_session_status": result.current_session_status,
    }


# ---------------------------------------------------------------------------
# GET /{session_id}/same-ticker-history
# ---------------------------------------------------------------------------


@router.get("/{session_id}/same-ticker-history", response_model=dict[str, object])
async def get_same_ticker_history(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    from app.repositories.trade_session import TradeSessionRepository
    from app.services.same_ticker_history import SameTickerHistoryService

    repo = TradeSessionRepository(db_session)
    ts = await repo.get_by_id_for_user(session_id, current_user.id)
    if ts is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Trade session not found")

    svc = SameTickerHistoryService(db_session)
    summary = await svc.build_history_summary(
        owner_id=current_user.id,
        ticker=ts.ticker,
        current_session_id=session_id,
    )

    return {
        "session_id": str(session_id),
        "ticker": ts.ticker,
        "historical_context_used": summary["historical_context_used"],
        "historical_session_count": summary["historical_session_count"],
        "completed_trade_count": summary["completed_trade_count"],
        "skipped_session_count": summary["skipped_session_count"],
        "historical_source_session_ids": summary["historical_source_session_ids"],
        "historical_summary_generated_at": summary["historical_summary_generated_at"],
        "recent_outcomes": summary["recent_outcomes"],
        "useful_lessons": summary["useful_lessons"],
        "confidence_calibration_notes": summary["confidence_calibration_notes"],
        "data_quality_notes": summary["data_quality_notes"],
    }
