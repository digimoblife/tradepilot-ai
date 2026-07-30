from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.errors import SESSION_NOT_FOUND, get_error_message
from app.auth import AuthenticatedUser
from app.database.session import get_db_session
from app.trade_workspace.api.schemas import (
    TradeSessionCreateRequest,
    TradeSessionListResponse,
    TradeSessionResponse,
)
from app.trade_workspace.services.trade_sessions import RebuildTradeSessionService

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
    )


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": SESSION_NOT_FOUND, "message": get_error_message(SESSION_NOT_FOUND)},
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


@router.get("", response_model=TradeSessionListResponse)
async def list_trade_sessions(
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> TradeSessionListResponse:
    sessions = await RebuildTradeSessionService(db_session).list_owned(
        user_id=current_user.id
    )
    return TradeSessionListResponse(sessions=[_to_response(item) for item in sessions])


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
