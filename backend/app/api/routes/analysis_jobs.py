"""Analysis Job API routes (TP-1004)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.schemas.analysis_jobs import AnalysisJobStatusResponse
from app.auth import AuthenticatedUser
from app.database.session import get_db_session
from app.models.enums import AnalysisJobStatus
from app.repositories.analysis_job import AnalysisJobRepository

router = APIRouter(prefix="/api/analysis-jobs", tags=["analysis-jobs"])

_RETRYABLE_STATUSES = frozenset({AnalysisJobStatus.FAILED.value})


# ---------------------------------------------------------------------------
# GET /api/analysis-jobs/{job_id}
# ---------------------------------------------------------------------------


@router.get("/{job_id}", response_model=AnalysisJobStatusResponse)
async def get_job_status(
    job_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> AnalysisJobStatusResponse:
    from app.repositories.analysis import AnalysisRepository

    repo = AnalysisJobRepository(db_session)
    job = await repo.get_by_id_for_user(job_id, current_user.id)
    if job is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Analysis job not found")

    analysis_id: str | None = None
    if job.status == AnalysisJobStatus.COMPLETED:
        analysis_repo = AnalysisRepository(db_session)
        analyses = await analysis_repo.list_for_session_for_user(
            job.session_id, current_user.id, limit=1,
        )
        matching = [a for a in analyses if a.analysis_job_id == job_id]
        if matching:
            analysis_id = str(matching[0].id)

    return AnalysisJobStatusResponse(
        job_id=str(job.id),
        session_id=str(job.session_id),
        analysis_type=job.analysis_type.value,
        status=job.status.value,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        available_at=job.available_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        last_error_code=job.last_error_code,
        last_error_message=job.last_error_message,
        analysis_id=analysis_id,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


# ---------------------------------------------------------------------------
# POST /api/analysis-jobs/{job_id}/retry
# ---------------------------------------------------------------------------


@router.post("/{job_id}/retry", status_code=202)
async def retry_job(
    job_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, object]:
    from app.models.enums import AnalysisJobStatus

    repo = AnalysisJobRepository(db_session)
    job = await repo.get_by_id_for_user_for_update(job_id, current_user.id)
    if job is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Analysis job not found")

    status_val = job.status.value

    if status_val not in _RETRYABLE_STATUSES:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail={
                "code": "ANALYSIS_JOB_NOT_RETRYABLE",
                "message": (
                    f"Job {job_id} is in status {status_val} "
                    f"and cannot be retried. Only FAILED jobs can be retried."
                ),
            },
        )

    if job.attempt_count >= job.max_attempts:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail={
                "code": "ANALYSIS_JOB_RETRY_EXHAUSTED",
                "message": (
                    f"Job {job_id} has exhausted its {job.max_attempts} "
                    f"retry attempts."
                ),
            },
        )

    # Reset job for retry
    now = datetime.now(timezone.utc)
    job.status = AnalysisJobStatus.QUEUED
    job.attempt_count += 1
    job.available_at = now
    job.lease_owner = None
    job.lease_acquired_at = None
    job.lease_expires_at = None
    job.last_error_code = None
    job.last_error_message = None
    job.started_at = None

    await db_session.flush()

    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "attempt_count": job.attempt_count,
        "max_attempts": job.max_attempts,
    }
