"""Timeline API routes (TP-1006)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.schemas.timeline import (
    TimelineActionReference,
    TimelineAnalysisReference,
    TimelineEventResponse,
    TimelineListResponse,
)
from app.auth import AuthenticatedUser
from app.database.session import get_db_session
from app.models.enums import AcceptanceStatus
from app.repositories.session_event import SessionEventRepository

router = APIRouter(prefix="/api/trade-sessions", tags=["timeline"])


async def _load_action(db_session: AsyncSession, action_id: uuid.UUID, owner_id: uuid.UUID, session_id: uuid.UUID) -> Any:
    """Load a Trade Action by ID, verifying ownership."""
    from app.repositories.trade_session import TradeSessionRepository

    ts = await TradeSessionRepository(db_session).get_by_id_for_user(session_id, owner_id)
    if ts is None:
        return None
    from app.models.trade_action import TradeAction

    result = await db_session.get(TradeAction, action_id)
    if result is None or result.session_id != session_id:
        return None
    return result


async def _load_analysis(db_session: AsyncSession, analysis_id: uuid.UUID, owner_id: uuid.UUID, session_id: uuid.UUID) -> Any:
    """Load an Analysis by ID, verifying ownership and acceptance."""
    from app.repositories.trade_session import TradeSessionRepository

    ts = await TradeSessionRepository(db_session).get_by_id_for_user(session_id, owner_id)
    if ts is None:
        return None
    from app.models.analysis import Analysis

    result = await db_session.get(Analysis, analysis_id)
    if result is None or result.session_id != session_id:
        return None
    if result.acceptance_status != AcceptanceStatus.ACCEPTED:
        return None
    return result


@router.get("/{session_id}/timeline", response_model=TimelineListResponse)
async def get_timeline(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
    event_type: str | None = Query(None),
    from_timestamp: datetime | None = Query(None),
    to_timestamp: datetime | None = Query(None),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> TimelineListResponse:
    # Verify session ownership
    from app.repositories.trade_session import TradeSessionRepository

    ts = await TradeSessionRepository(db_session).get_by_id_for_user(session_id, current_user.id)
    if ts is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Trade session not found")

    repo = SessionEventRepository(db_session)
    events = await repo.list_for_session_for_user(
        session_id,
        current_user.id,
        event_type=event_type,
        occurred_after=from_timestamp,
        occurred_before=to_timestamp,
        limit=limit + offset if limit else None,
    )

    items = events[offset : offset + limit] if limit else events

    result: list[TimelineEventResponse] = []
    for ev in items:
        action_ref = None
        if ev.related_action_id is not None:
            action = await _load_action(
                db_session,
                ev.related_action_id,
                current_user.id,
                session_id,
            )
            if action is not None:
                action_ref = TimelineActionReference(
                    id=str(action.id),
                    action_type=action.action_type.value,
                    confirmed_at=action.confirmed_at,
                    price=action.price,
                    quantity=action.quantity,
                )

        analysis_ref = None
        if ev.related_analysis_id is not None:
            analysis = await _load_analysis(
                db_session,
                ev.related_analysis_id,
                current_user.id,
                session_id,
            )
            if analysis is not None:
                analysis_ref = TimelineAnalysisReference(
                    id=str(analysis.id),
                    analysis_type=analysis.analysis_type.value,
                    accepted_at=analysis.accepted_at,
                    schema_name=analysis.schema_name,
                    schema_version=analysis.schema_version,
                )

        result.append(
            TimelineEventResponse(
                id=str(ev.id),
                session_id=str(ev.session_id),
                event_type=ev.event_type.value,
                occurred_at=ev.occurred_at,
                created_at=ev.created_at,
                summary=ev.compact_summary,
                price=ev.price,
                quantity=ev.quantity,
                related_action=action_ref,
                related_analysis=analysis_ref,
            )
        )

    return TimelineListResponse(events=result, total=len(result))
