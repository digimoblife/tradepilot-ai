"""PostgreSQL-backed job queue (TP-0801).

Provides atomic claim, lease management, and reclaim for analysis jobs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.models import ClaimedJob, JobLease
from app.models.analysis_job import AnalysisJob
from app.models.enums import AnalysisJobStatus

_QUEUED = AnalysisJobStatus.QUEUED
_PROCESSING = AnalysisJobStatus.PROCESSING
_COMPLETED = AnalysisJobStatus.COMPLETED
_FAILED = AnalysisJobStatus.FAILED
_CANCELLED = AnalysisJobStatus.CANCELLED

_TERMINAL = frozenset({_COMPLETED, _FAILED, _CANCELLED})


# ---------------------------------------------------------------------------
# Stable errors
# ---------------------------------------------------------------------------


class JobQueueError(Exception):
    """Base for all job queue errors."""

    code: str = "JOB_QUEUE_ERROR"

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class JobQueueInvalidLeaseDurationError(JobQueueError):
    code: str = "JOB_QUEUE_INVALID_LEASE_DURATION"


class JobLeaseNotOwnedError(JobQueueError):
    code: str = "JOB_LEASE_NOT_OWNED"


class JobLeaseNotActiveError(JobQueueError):
    code: str = "JOB_LEASE_NOT_ACTIVE"


class JobNotClaimableError(JobQueueError):
    code: str = "JOB_NOT_CLAIMABLE"


# ---------------------------------------------------------------------------
# Queue
# ---------------------------------------------------------------------------


class PostgreSQLJobQueue:
    """Durable PostgreSQL-backed job queue with FOR UPDATE SKIP LOCKED."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim_next(
        self,
        *,
        worker_id: str,
        lease_duration: timedelta,
        now: datetime | None = None,
    ) -> ClaimedJob | None:
        if lease_duration <= timedelta(0):
            raise JobQueueInvalidLeaseDurationError(
                message=f"Lease duration must be positive, got {lease_duration}",
            )

        now = now or datetime.now(timezone.utc)

        # Eligible jobs:
        # 1. QUEUED status with available_at <= now
        # 2. PROCESSING status with expired lease and attempt_count < max_attempts
        now_ts = now
        eligible = or_(
            and_(
                AnalysisJob.status == _QUEUED,
                AnalysisJob.available_at <= now_ts,
            ),
            and_(
                AnalysisJob.status == _PROCESSING,
                AnalysisJob.lease_expires_at <= now_ts,
                AnalysisJob.available_at <= now_ts,
            ),
        )

        query = (
            select(AnalysisJob)
            .where(
                and_(
                    eligible,
                    AnalysisJob.attempt_count < AnalysisJob.max_attempts,
                    AnalysisJob.status.not_in(_TERMINAL),
                )
            )
            .order_by(AnalysisJob.available_at, AnalysisJob.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )

        result = await self._session.execute(query)
        job = result.unique().scalar_one_or_none()

        if job is None:
            return None

        return await self._claim(job, worker_id, lease_duration, now)

    async def renew_lease(
        self,
        *,
        job_id: uuid.UUID,
        worker_id: str,
        lease_duration: timedelta,
        now: datetime | None = None,
    ) -> JobLease:
        if lease_duration <= timedelta(0):
            raise JobQueueInvalidLeaseDurationError(
                message=f"Lease duration must be positive, got {lease_duration}",
            )

        now = now or datetime.now(timezone.utc)

        result = await self._session.execute(
            select(AnalysisJob)
            .where(
                AnalysisJob.id == job_id,
                AnalysisJob.status == _PROCESSING,
            )
            .with_for_update()
        )
        job = result.unique().scalar_one_or_none()

        if job is None:
            raise JobLeaseNotActiveError(
                message=f"Job {job_id} is not in PROCESSING state",
            )

        if job.lease_owner != worker_id:
            raise JobLeaseNotOwnedError(
                message=f"Worker {worker_id!r} does not own lease for job {job_id}",
            )

        new_expires = now + lease_duration
        job.lease_expires_at = new_expires
        await self._session.flush()

        return JobLease(
            job_id=job.id,
            worker_id=worker_id,
            claimed_at=job.lease_acquired_at or now,
            expires_at=new_expires,
            attempt_number=job.attempt_count,
        )

    async def release(
        self,
        *,
        job_id: uuid.UUID,
        worker_id: str,
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now(timezone.utc)

        result = await self._session.execute(
            select(AnalysisJob)
            .where(
                AnalysisJob.id == job_id,
                AnalysisJob.status == _PROCESSING,
            )
            .with_for_update()
        )
        job = result.unique().scalar_one_or_none()

        if job is None:
            raise JobLeaseNotActiveError(
                message=f"Job {job_id} is not in PROCESSING state",
            )

        if job.lease_owner != worker_id:
            raise JobLeaseNotOwnedError(
                message=f"Worker {worker_id!r} does not own lease for job {job_id}",
            )

        job.status = _QUEUED
        job.lease_owner = None
        job.lease_acquired_at = None
        job.lease_expires_at = None
        job.available_at = now
        await self._session.flush()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _claim(
        self,
        job: AnalysisJob,
        worker_id: str,
        lease_duration: timedelta,
        now: datetime,
    ) -> ClaimedJob:
        expires_at = now + lease_duration

        was_reclaim = job.status == _PROCESSING

        job.status = _PROCESSING
        job.lease_owner = worker_id
        job.lease_acquired_at = now
        job.lease_expires_at = expires_at
        job.attempt_count += 1

        if not was_reclaim:
            job.started_at = now

        await self._session.flush()

        lease = JobLease(
            job_id=job.id,
            worker_id=worker_id,
            claimed_at=now,
            expires_at=expires_at,
            attempt_number=job.attempt_count,
        )

        return ClaimedJob(
            job_id=job.id,
            session_id=job.session_id,
            analysis_type=job.analysis_type.value
            if hasattr(job.analysis_type, "value")
            else str(job.analysis_type),
            attempt_number=job.attempt_count,
            lease=lease,
        )
