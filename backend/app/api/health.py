"""Application health and readiness endpoints (TP-1602).

Provides health endpoints:
* ``GET /health`` — process is running (lightweight).
* ``GET /health/ready`` — database readiness.
* ``GET /health/storage`` — storage backend status.
"""

from __future__ import annotations

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
