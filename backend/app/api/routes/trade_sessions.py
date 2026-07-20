"""Trade Session API routes (TP-1002)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.schemas.trade_sessions import (
    TradeSessionArchiveResponse,
    TradeSessionCreateRequest,
    TradeSessionCreateResponse,
    TradeSessionDetailWithActionsResponse,
    TradeSessionListResponse,
    TradeSessionReadyResponse,
    TradeSessionSummaryResponse,
    TradeSessionUpdateRequest,
    TradeStateResponse,
)
from app.auth import AuthenticatedUser
from app.database.session import get_db_session
from app.lifecycle.service import InvalidSessionTransitionError, SessionLifecycleService
from app.lifecycle.transitions import get_allowed_transitions
from app.models.enums import TradeSessionStatus
from app.models.trade_session import TradeSession
from app.repositories.trade_session import TradeSessionRepository
from app.repositories.trade_state import TradeStateRepository
from app.services.actions.archive_session import ArchiveSessionActionService
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

    if TradeSessionStatus.READY_FOR_ANALYSIS in allowed_targets:
        actions.append("MARK_READY")
    if TradeSessionStatus.CANCELLED in allowed_targets:
        actions.append("CANCEL")
    if TradeSessionStatus.ARCHIVED in allowed_targets:
        actions.append("ARCHIVE")

    # Additional actions based on position status are derived by TP-1005
    return actions


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
        title=body.title,
    )
    return TradeSessionCreateResponse(
        id=str(ts.id),
        ticker=ts.ticker,
        company_name=body.company_name,
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

    return TradeSessionDetailWithActionsResponse(
        session=session_resp,
        trade_state=state_resp,
        allowed_actions=actions,
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

    # Only update mutable metadata fields
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
    # Check session exists and is owned first
    repo = TradeSessionRepository(db_session)
    ts_check = await repo.get_by_id_for_user(session_id, current_user.id)
    if ts_check is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Trade session not found")

    lc = SessionLifecycleService(db_session)
    try:
        ts = await lc.transition(
            session_id=session_id,
            owner_id=current_user.id,
            target_status=TradeSessionStatus.READY_FOR_ANALYSIS,
        )
    except InvalidSessionTransitionError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail={"code": exc.code, "message": str(exc)})

    return TradeSessionReadyResponse(
        id=str(ts.id),
        lifecycle_status=ts.lifecycle_status.value,
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
