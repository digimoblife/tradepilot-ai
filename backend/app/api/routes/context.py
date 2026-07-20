"""Context Summary API routes (TP-1006)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.schemas.context import ContextSummaryResponse
from app.auth import AuthenticatedUser
from app.database.session import get_db_session
from app.repositories.context_summary import ContextSummaryRepository

router = APIRouter(prefix="/api/trade-sessions", tags=["context"])


@router.get("/{session_id}/context", response_model=ContextSummaryResponse)
async def get_context_summary(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> ContextSummaryResponse:
    repo = ContextSummaryRepository(db_session)
    cs = await repo.get_latest_for_user(session_id, current_user.id)
    if cs is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Context summary not found")

    return ContextSummaryResponse(
        id=str(cs.id),
        session_id=str(cs.session_id),
        context_version=cs.context_version,
        source_cutoff=cs.source_cutoff,
        is_stale=cs.is_stale,
        quality=cs.quality.value,
        payload=cs.payload,
        created_at=cs.created_at,
    )
