"""Analysis API routes (TP-1004)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.schemas.analyses import (
    AnalysisDetailResponse,
    AnalysisListResponse,
    AnalysisRequest,
    AnalysisSummaryResponse,
)
from app.auth import AuthenticatedUser
from app.database.session import get_db_session
from app.models.enums import AcceptanceStatus
from app.repositories.analysis import AnalysisRepository
from app.services.analysis_jobs import AnalysisJobCreationService

session_router = APIRouter(prefix="/api/trade-sessions", tags=["analyses"])
analysis_router = APIRouter(prefix="/api/analyses", tags=["analyses"])


# ---------------------------------------------------------------------------
# POST /api/trade-sessions/{session_id}/analyses
# ---------------------------------------------------------------------------


@session_router.post("/{session_id}/analyses", status_code=202)
async def request_analysis(
    session_id: uuid.UUID,
    body: AnalysisRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    from app.api.schemas.analysis_jobs import AnalysisJobCreateResponse
    from app.services.analysis_jobs import (
        AnalysisJobAlreadyActiveError,
        AnalysisJobCreationError,
        AnalysisJobSessionNotFoundError,
        AnalysisRequiredEvidenceMissingError,
        AnalysisTypeInvalidForLifecycleError,
    )

    svc = AnalysisJobCreationService(db_session)
    try:
        result = await svc.create(
            session_id=session_id,
            owner_id=current_user.id,
            analysis_type=body.analysis_type,
        )
    except AnalysisJobSessionNotFoundError:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Trade session not found")
    except AnalysisJobAlreadyActiveError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=409, detail={"code": exc.code, "message": str(exc)})
    except AnalysisTypeInvalidForLifecycleError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail={"code": exc.code, "message": str(exc)})
    except AnalysisRequiredEvidenceMissingError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail={"code": exc.code, "message": str(exc)})
    except AnalysisJobCreationError as exc:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail={"code": exc.code, "message": str(exc)})

    resp = AnalysisJobCreateResponse(
        job_id=str(result.job_id),
        session_id=str(result.session_id),
        analysis_type=result.analysis_type,
        status=result.job_status,
        attempt_count=0,
        max_attempts=3,
        available_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        previous_session_status=result.previous_session_status,
    )
    return resp.model_dump()


# ---------------------------------------------------------------------------
# GET /api/trade-sessions/{session_id}/analyses
# ---------------------------------------------------------------------------


@session_router.get("/{session_id}/analyses", response_model=AnalysisListResponse)
async def list_analyses(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
    analysis_type: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> AnalysisListResponse:
    repo = AnalysisRepository(db_session)
    all_items = await repo.list_for_session_for_user(
        session_id,
        current_user.id,
        limit=limit + offset,
    )

    # Return only accepted analyses
    accepted = [a for a in all_items if a.acceptance_status == AcceptanceStatus.ACCEPTED]

    if analysis_type:
        accepted = [a for a in accepted if str(a.analysis_type) == analysis_type]

    items = accepted[offset : offset + limit]
    result = [
        AnalysisSummaryResponse(
            id=str(a.id),
            session_id=str(a.session_id),
            analysis_type=a.analysis_type.value,
            acceptance_status=a.acceptance_status.value,
            accepted_at=a.accepted_at,
            created_at=a.created_at,
            prompt_version=a.prompt_version,
            schema_name=a.schema_name,
            schema_version=a.schema_version,
            supersedes_analysis_id=(
                str(a.supersedes_analysis_id) if a.supersedes_analysis_id else None
            ),
        )
        for a in items
    ]
    return AnalysisListResponse(analyses=result, total=len(result))


# ---------------------------------------------------------------------------
# GET /api/analyses/{analysis_id}
# ---------------------------------------------------------------------------


@analysis_router.get("/{analysis_id}", response_model=AnalysisDetailResponse)
async def get_analysis(
    analysis_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> AnalysisDetailResponse:
    repo = AnalysisRepository(db_session)
    analysis = await repo.get_by_id_for_user(analysis_id, current_user.id)
    if analysis is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Analysis not found")

    if analysis.acceptance_status != AcceptanceStatus.ACCEPTED:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return AnalysisDetailResponse(
        id=str(analysis.id),
        session_id=str(analysis.session_id),
        analysis_type=analysis.analysis_type.value,
        acceptance_status=analysis.acceptance_status.value,
        accepted_at=analysis.accepted_at,
        created_at=analysis.created_at,
        prompt_name=analysis.prompt_name,
        prompt_version=analysis.prompt_version,
        schema_name=analysis.schema_name,
        schema_version=analysis.schema_version,
        payload=analysis.payload,
        supersedes_analysis_id=(
            str(analysis.supersedes_analysis_id) if analysis.supersedes_analysis_id else None
        ),
    )
