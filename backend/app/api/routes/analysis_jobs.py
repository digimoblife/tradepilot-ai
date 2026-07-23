"""Analysis Job API routes (TP-1004)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.schemas.analysis_jobs import AnalysisJobStatusResponse
from app.auth import AuthenticatedUser
from app.database.session import get_db_session
from app.jobs import PostgreSQLJobQueue
from app.models.analysis_job import AnalysisJob
from app.models.enums import AnalysisJobStatus, TradeSessionStatus
from app.models.trade_session import TradeSession
from app.repositories.analysis_job import AnalysisJobRepository

router = APIRouter(prefix="/api/analysis-jobs", tags=["analysis-jobs"])

_RETRYABLE_STATUSES = frozenset({AnalysisJobStatus.FAILED.value})
_ACTIVE_JOB_STATUSES = frozenset(
    {
        AnalysisJobStatus.CREATED,
        AnalysisJobStatus.QUEUED,
        AnalysisJobStatus.PROCESSING,
        AnalysisJobStatus.RETRYING,
    }
)


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

    queue = PostgreSQLJobQueue(db_session)
    terminalized = await queue.terminalize_expired_exhausted_processing(job_id=job_id)
    if terminalized:
        refreshed = await repo.get_by_id_for_user(job_id, current_user.id)
        if refreshed is not None:
            job = refreshed

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

    queue = PostgreSQLJobQueue(db_session)
    terminalized = await queue.terminalize_expired_exhausted_processing(job_id=job_id)
    if terminalized:
        refreshed = await repo.get_by_id_for_user_for_update(job_id, current_user.id)
        if refreshed is not None:
            job = refreshed

    status_val = job.status.value

    if job.status in _ACTIVE_JOB_STATUSES:
        return _retry_response(job)

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

    active_duplicate = await _find_active_duplicate(db_session, job)
    if active_duplicate is not None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=409,
            detail={
                "code": "ANALYSIS_JOB_ALREADY_ACTIVE",
                "message": "Masih ada analisis aktif untuk sesi ini.",
            },
        )

    # Requeue the same job for a fresh manual attempt.
    now = datetime.now(timezone.utc)
    job.status = AnalysisJobStatus.QUEUED
    job.attempt_count = 0
    job.available_at = now
    job.lease_owner = None
    job.lease_acquired_at = None
    job.lease_expires_at = None
    job.last_error_code = None
    job.last_error_message = None
    job.started_at = None
    job.completed_at = None

    trade_session = await _get_owned_session_for_update(db_session, job, current_user.id)
    if trade_session is not None:
        trade_session.lifecycle_status = TradeSessionStatus.ANALYZING
        trade_session.stable_status = TradeSessionStatus.ANALYZING

    await db_session.flush()

    return _retry_response(job)


def _retry_response(job: AnalysisJob) -> dict[str, object]:
    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "attempt_count": job.attempt_count,
        "max_attempts": job.max_attempts,
    }


async def _find_active_duplicate(
    db_session: AsyncSession,
    job: AnalysisJob,
) -> AnalysisJob | None:
    result = await db_session.execute(
        select(AnalysisJob)
        .where(
            and_(
                AnalysisJob.id != job.id,
                AnalysisJob.session_id == job.session_id,
                AnalysisJob.analysis_type == job.analysis_type,
                AnalysisJob.status.in_(_ACTIVE_JOB_STATUSES),
            )
        )
        .limit(1)
        .with_for_update()
    )
    return result.unique().scalar_one_or_none()


async def _get_owned_session_for_update(
    db_session: AsyncSession,
    job: AnalysisJob,
    owner_id: uuid.UUID,
) -> TradeSession | None:
    result = await db_session.execute(
        select(TradeSession)
        .where(
            TradeSession.id == job.session_id,
            TradeSession.owner_id == owner_id,
        )
        .with_for_update()
    )
    return result.unique().scalar_one_or_none()
