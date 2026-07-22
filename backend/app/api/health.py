"""Application health and readiness endpoints (TP-1602).

Provides four endpoints:
* ``GET /health`` — process is running (lightweight).
* ``GET /health/ready`` — database + schema registry readiness.
* ``GET /health/schema-registry`` — production schema registry status.
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
    schema_registry: ComponentStatus


class SchemaRegistryStatus(BaseModel):
    status: str
    registered_resources: int | None = None
    compiled_validators: int | None = None
    detail: str | None = None


class WorkerHeartbeatStatus(BaseModel):
    status: str
    worker_id: str | None = None
    started_at: str | None = None
    last_seen_at: str | None = None
    running_status: str | None = None
    detail: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    request: Request = None,  # type: ignore[assignment]
) -> ReadinessResponse:
    """Combined readiness: database + schema registry."""
    db_status = await _check_database(db)
    sr_status = _check_schema_registry(request)
    overall = (
        "ready" if db_status.status == "healthy" and sr_status.status == "healthy" else "unhealthy"
    )
    return ReadinessResponse(
        status=overall,
        database=db_status,
        schema_registry=sr_status,
    )


async def _check_database(db: AsyncSession) -> ComponentStatus:
    try:
        await db.execute(text("SELECT 1"))
        return _component_healthy("database reachable")
    except Exception as exc:
        return _component_unhealthy(str(exc))


def _check_schema_registry(request) -> ComponentStatus:
    app = getattr(request, "app", None)
    if app is None:
        return _component_unhealthy("no application context")
    registry = getattr(app.state, "schema_registry", None)
    if registry is None:
        return _component_unhealthy("schema registry not loaded")
    try:
        count = getattr(registry, "registered_resource_count", 0)
        if count > 0:
            return _component_healthy(f"{count} resource(s) registered")
        return _component_unhealthy("schema registry is empty")
    except Exception as exc:
        return _component_unhealthy(str(exc))


# ---------------------------------------------------------------------------
# GET /health/schema-registry
# ---------------------------------------------------------------------------


@router.get("/health/schema-registry", response_model=SchemaRegistryStatus)
async def health_schema_registry(request: Request = None) -> SchemaRegistryStatus:  # type: ignore[assignment]
    """Detailed schema registry status."""
    app = getattr(request, "app", None)
    if app is None:
        return SchemaRegistryStatus(status="unavailable", detail="no application context")

    manifest = getattr(app.state, "schema_manifest", None)
    registry = getattr(app.state, "schema_registry", None)

    if manifest is None or registry is None:
        return SchemaRegistryStatus(status="not_loaded", detail="schema registry not initialised")

    try:
        resources = getattr(registry, "registered_resource_count", 0)
        validators = getattr(registry, "compiled_validator_count", 0)
        return SchemaRegistryStatus(
            status="healthy",
            registered_resources=resources,
            compiled_validators=validators,
        )
    except Exception as exc:
        return SchemaRegistryStatus(status="error", detail=str(exc))


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
