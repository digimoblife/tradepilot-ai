"""Application health and readiness endpoints (TP-1602).

Provides health endpoints:
* ``GET /health`` — process is running (lightweight).
* ``GET /health/ready`` — database readiness.
* ``GET /health/storage`` — storage backend status.
* ``GET /health/worker`` — latest worker heartbeat status.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.database.session import get_db_session

router = APIRouter()

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ComponentStatus(BaseModel):
    status: str
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: str
    database: ComponentStatus


class WorkerHeartbeatStatus(BaseModel):
    status: str
    worker_id: str | None = None
    started_at: str | None = None
    last_seen_at: str | None = None
    running_status: str | None = None
    detail: str | None = None


# ---------------------------------------------------------------------------
# GET /health/storage
# ---------------------------------------------------------------------------


class StorageHealthResponse(BaseModel):
    status: str
    detail: str | None = None


@router.get("/health/storage", response_model=StorageHealthResponse)
async def health_storage() -> StorageHealthResponse:
    """Verify the configured storage root is writable and readable.

    All storage operations are synchronous and must not be awaited.
    The probe file is cleaned up in ``finally``.
    """
    from app.storage import create_file_storage

    import uuid

    storage = create_file_storage()
    data = b"healthcheck"
    file_created = False
    file_reference: str | None = None

    try:
        result = storage.store(
            user_id=uuid.UUID(int=0),
            session_id=uuid.UUID(int=0),
            original_filename=f".health_{uuid.uuid4().hex}.tmp",
            content=data,
        )
        file_created = True
        file_reference = result.file_reference

        stored = storage.read(file_reference=file_reference)

        if stored != data:
            return StorageHealthResponse(
                status="unhealthy",
                detail="readback mismatch",
            )

        return StorageHealthResponse(
            status="healthy",
            detail="store/read/delete succeeded",
        )
    except Exception as exc:
        return StorageHealthResponse(
            status="unhealthy",
            detail=str(exc),
        )
    finally:
        if file_created and file_reference is not None:
            try:
                storage.delete(file_reference=file_reference)
            except Exception:
                pass  # Best-effort cleanup; probe file will be removed on
                # next successful health check if it persists.


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# A heartbeat older than this threshold is considered stale/unhealthy
# regardless of its database status.  Default: 5 minutes ( ~ 2× the
# default worker poll interval of 5 s × 60 polling cycles).
_STALE_THRESHOLD_MINUTES = 5


def _component_healthy(detail: str = "") -> ComponentStatus:
    return ComponentStatus(status="healthy", detail=detail or None)


def _component_unhealthy(detail: str = "") -> ComponentStatus:
    return ComponentStatus(status="unhealthy", detail=detail or None)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Lightweight liveness check — the process is running."""
    return HealthResponse(status="ok", service="tradepilot-backend", version=__version__)


# ---------------------------------------------------------------------------
# GET /health/ready
# ---------------------------------------------------------------------------


@router.get("/health/ready", response_model=ReadinessResponse)
async def health_ready(
    db: AsyncSession = Depends(get_db_session),
) -> ReadinessResponse:
    """Readiness probe: database reachable."""
    db_status = await _check_database(db)
    overall = "ready" if db_status.status == "healthy" else "unhealthy"
    return ReadinessResponse(
        status=overall,
        database=db_status,
    )


async def _check_database(db: AsyncSession) -> ComponentStatus:
    try:
        await db.execute(text("SELECT 1"))
        return _component_healthy("database reachable")
    except Exception as exc:
        return _component_unhealthy(str(exc))


# ---------------------------------------------------------------------------
# GET /health/worker
# ---------------------------------------------------------------------------


@router.get("/health/worker", response_model=WorkerHeartbeatStatus)
async def health_worker(
    db: AsyncSession = Depends(get_db_session),
) -> WorkerHeartbeatStatus:
    """Latest worker heartbeat status from the database."""
    try:
        result = await db.execute(
            text(
                "SELECT worker_id, started_at, last_seen_at, status "
                "FROM worker_heartbeats "
                "ORDER BY last_seen_at DESC NULLS LAST "
                "LIMIT 1"
            )
        )
        row = result.first()
    except Exception:
        # Table may not exist yet
        return WorkerHeartbeatStatus(
            status="absent",
            detail="worker_heartbeats table unavailable (worker may not have run yet)",
        )

    if row is None:
        return WorkerHeartbeatStatus(
            status="absent",
            detail="no heartbeat records found",
        )

    worker_id, started_at, last_seen_at, running_status = row
    now = datetime.now(timezone.utc)

    # 1. A ST stopped heartbeat is never healthy
    if running_status is not None and running_status.upper() == "STOPPED":
        return WorkerHeartbeatStatus(
            status="stale",
            worker_id=worker_id,
            started_at=started_at.isoformat() if started_at else None,
            last_seen_at=last_seen_at.isoformat() if last_seen_at else None,
            running_status=running_status,
            detail="worker has stopped",
        )

    # 2. Check staleness by age
    if last_seen_at is None or (now - last_seen_at) > timedelta(minutes=_STALE_THRESHOLD_MINUTES):
        status_label = "stale"
        detail = (
            f"last seen {(now - last_seen_at).total_seconds():.0f}s ago"
            if last_seen_at
            else "never seen"
        )
    else:
        status_label = "healthy"
        detail = f"last seen {(now - last_seen_at).total_seconds():.0f}s ago"

    return WorkerHeartbeatStatus(
        status=status_label,
        worker_id=worker_id,
        started_at=started_at.isoformat() if started_at else None,
        last_seen_at=last_seen_at.isoformat() if last_seen_at else None,
        running_status=running_status,
        detail=detail,
    )
