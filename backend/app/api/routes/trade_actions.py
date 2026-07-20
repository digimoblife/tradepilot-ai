"""Trade Action API routes (TP-1005)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.schemas.trade_actions import (
    ActionResultResponse,
    CancelSessionRequest,
    FullExitRequest,
    OpenPositionRequest,
    PartialExitRequest,
    StopActionRequest,
    TargetActionRequest,
    TradeActionResponse,
    TradeStateSnapshot,
)
from app.auth import AuthenticatedUser
from app.database.session import get_db_session
from typing import Any
from app.repositories.trade_session import TradeSessionRepository
from app.repositories.trade_state import TradeStateRepository

router = APIRouter(prefix="/api/actions", tags=["trade-actions"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _map_service_error(exc: Exception) -> None:
    from fastapi import HTTPException

    code = getattr(exc, "code", "")
    if "NOT_FOUND" in code or "NOT_OWNED" in code:
        raise HTTPException(status_code=404, detail={"code": code, "message": str(exc)})
    if (
        "INVALID_STATE" in code
        or "INVALID_LIFECYCLE" in code
        or "INVALID_INPUT" in code
        or "INVALID_RELATIONSHIP" in code
        or "QUANTITY_INVALID" in code
        or "QUANTITY_MISMATCH" in code
        or "INVALID_REASON" in code
        or "INVALID_TIMELINE" in code
    ):
        raise HTTPException(status_code=422, detail={"code": code, "message": str(exc)})
    raise


def _build_response(
    action: Any,
    trade_state: Any,
    session_status: Any,
) -> ActionResultResponse:
    return ActionResultResponse(
        action=TradeActionResponse(
            id=str(action.id),
            session_id=str(action.session_id),
            action_type=action.action_type.value,
            confirmed_at=action.confirmed_at,
            price=str(action.price) if action.price is not None else None,
            quantity=str(action.quantity) if action.quantity is not None else None,
        ),
        session_status=session_status.value,
        trade_state=TradeStateSnapshot(
            position_status=trade_state.position_status.value,
            entry_price=str(trade_state.entry_price) if trade_state.entry_price else None,
            original_quantity=str(trade_state.original_quantity)
            if trade_state.original_quantity
            else None,
            remaining_quantity=str(trade_state.remaining_quantity)
            if trade_state.remaining_quantity
            else None,
            active_stop_loss=str(trade_state.active_stop_loss)
            if trade_state.active_stop_loss
            else None,
            active_target=str(trade_state.active_target) if trade_state.active_target else None,
            average_exit_price=str(trade_state.average_exit_price)
            if trade_state.average_exit_price
            else None,
            realized_pnl=str(trade_state.realized_pnl) if trade_state.realized_pnl else None,
            state_version=trade_state.state_version,
        ),
    )


async def _load_state_and_build(
    db_session: AsyncSession,
    session_id: uuid.UUID,
    owner_id: uuid.UUID,
    action: Any,
) -> ActionResultResponse:
    tstate = await TradeStateRepository(db_session).get_for_user(session_id, owner_id)
    ts = await TradeSessionRepository(db_session).get_by_id_for_user(session_id, owner_id)
    assert ts is not None
    return _build_response(action, tstate, ts.lifecycle_status)


# ---------------------------------------------------------------------------
# POST /api/actions/open-position
# ---------------------------------------------------------------------------


@router.post("/open-position", response_model=ActionResultResponse)
async def open_position(
    body: OpenPositionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> ActionResultResponse:
    from app.services.actions.open_position import OpenPositionError, OpenPositionService

    svc = OpenPositionService(db_session)
    try:
        result = await svc.confirm(
            session_id=uuid.UUID(body.session_id),
            owner_id=current_user.id,
            idempotency_key=body.idempotency_key,
            entry_price=body.entry_price,
            quantity=body.quantity,
            execution_timestamp=body.executed_at,
            stop_loss=body.stop_loss,
            target=body.target,
            note=body.note,
        )
    except OpenPositionError as exc:
        _map_service_error(exc)

    return _build_response(result.action, result.trade_state, result.session_status)


# ---------------------------------------------------------------------------
# POST /api/actions/confirm-stop
# POST /api/actions/change-stop
# ---------------------------------------------------------------------------


async def _stop_action(
    body: StopActionRequest,
    current_user: AuthenticatedUser,
    db_session: AsyncSession,
) -> ActionResultResponse:
    from app.services.actions.stop_loss import StopLossActionService, StopLossError

    svc = StopLossActionService(db_session)
    try:
        result = await svc.confirm(
            session_id=uuid.UUID(body.session_id),
            owner_id=current_user.id,
            idempotency_key=body.idempotency_key,
            stop_loss=body.stop_loss,
            confirmed_at=body.confirmed_at,
            note=body.note,
        )
    except StopLossError as exc:
        _map_service_error(exc)

    return await _load_state_and_build(
        db_session,
        uuid.UUID(body.session_id),
        current_user.id,
        result.action,
    )


@router.post("/confirm-stop", response_model=ActionResultResponse)
async def confirm_stop(
    body: StopActionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> ActionResultResponse:
    return await _stop_action(body, current_user, db_session)


@router.post("/change-stop", response_model=ActionResultResponse)
async def change_stop(
    body: StopActionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> ActionResultResponse:
    return await _stop_action(body, current_user, db_session)


# ---------------------------------------------------------------------------
# POST /api/actions/confirm-target
# POST /api/actions/change-target
# ---------------------------------------------------------------------------


async def _target_action(
    body: TargetActionRequest,
    current_user: AuthenticatedUser,
    db_session: AsyncSession,
) -> ActionResultResponse:
    from app.services.actions.target import TargetActionService, TargetError

    svc = TargetActionService(db_session)
    try:
        result = await svc.confirm(
            session_id=uuid.UUID(body.session_id),
            owner_id=current_user.id,
            idempotency_key=body.idempotency_key,
            target=body.target,
            confirmed_at=body.confirmed_at,
            note=body.note,
        )
    except TargetError as exc:
        _map_service_error(exc)

    return await _load_state_and_build(
        db_session,
        uuid.UUID(body.session_id),
        current_user.id,
        result.action,
    )


@router.post("/confirm-target", response_model=ActionResultResponse)
async def confirm_target(
    body: TargetActionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> ActionResultResponse:
    return await _target_action(body, current_user, db_session)


@router.post("/change-target", response_model=ActionResultResponse)
async def change_target(
    body: TargetActionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> ActionResultResponse:
    return await _target_action(body, current_user, db_session)


# ---------------------------------------------------------------------------
# POST /api/actions/partial-exit
# ---------------------------------------------------------------------------


@router.post("/partial-exit", response_model=ActionResultResponse)
async def partial_exit(
    body: PartialExitRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> ActionResultResponse:
    from app.services.actions.partial_exit import (
        PartialExitActionService,
        PartialExitError,
    )

    svc = PartialExitActionService(db_session)
    try:
        result = await svc.confirm(
            session_id=uuid.UUID(body.session_id),
            owner_id=current_user.id,
            idempotency_key=body.idempotency_key,
            exit_price=body.exit_price,
            exit_quantity=body.exit_quantity,
            executed_at=body.executed_at,
            reason=body.reason,
            note=body.note,
        )
    except PartialExitError as exc:
        _map_service_error(exc)

    return await _load_state_and_build(
        db_session,
        uuid.UUID(body.session_id),
        current_user.id,
        result.action,
    )


# ---------------------------------------------------------------------------
# POST /api/actions/full-exit
# ---------------------------------------------------------------------------


@router.post("/full-exit", response_model=ActionResultResponse)
async def full_exit(
    body: FullExitRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> ActionResultResponse:
    from app.services.actions.full_exit import FullExitActionService, FullExitError

    svc = FullExitActionService(db_session)
    try:
        result = await svc.confirm(
            session_id=uuid.UUID(body.session_id),
            owner_id=current_user.id,
            idempotency_key=body.idempotency_key,
            exit_price=body.exit_price,
            exit_quantity=body.exit_quantity,
            executed_at=body.executed_at,
            closing_reason=body.closing_reason,
            fees=body.fees,
            note=body.note,
        )
    except FullExitError as exc:
        _map_service_error(exc)

    return await _load_state_and_build(
        db_session,
        uuid.UUID(body.session_id),
        current_user.id,
        result.action,
    )


# ---------------------------------------------------------------------------
# POST /api/actions/cancel
# ---------------------------------------------------------------------------


@router.post("/cancel", response_model=ActionResultResponse)
async def cancel_session(
    body: CancelSessionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> ActionResultResponse:
    from app.services.actions.cancel_session import (
        CancelSessionActionService,
        CancelSessionError,
    )

    svc = CancelSessionActionService(db_session)
    try:
        result = await svc.confirm(
            session_id=uuid.UUID(body.session_id),
            owner_id=current_user.id,
            idempotency_key=body.idempotency_key,
            cancelled_at=body.cancelled_at,
            reason=body.reason,
            note=body.note,
        )
    except CancelSessionError as exc:
        _map_service_error(exc)

    from app.repositories.trade_state import TradeStateRepository

    tstate = await TradeStateRepository(db_session).get_for_user(
        uuid.UUID(body.session_id),
        current_user.id,
    )
    return _build_response(result.action, tstate, result.session_status)
