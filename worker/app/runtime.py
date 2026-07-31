"""Worker runtime loop (TP-0805 / TP-1703 fix).

Coordinates polling, consumer, and heartbeat lifecycle.
Uses dependency injection — no direct backend imports.

One ``WorkerHeartbeat`` instance is created at startup and reused for
all heartbeat operations throughout the worker's lifetime.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import WorkerConfig
from app.heartbeat import WorkerHeartbeat
from app.logging import get_logger

log = get_logger(__name__)


async def run_worker(
    config: WorkerConfig,
    shutdown_event: asyncio.Event,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    consumer: Any | None = None,
    heartbeat: WorkerHeartbeat | None = None,
    startup_validator: Callable[[WorkerConfig], None] | None = None,
) -> None:
    """Start the worker polling loop.

    Accepts optional injected dependencies for testing.
    When *heartbeat* is provided it is used directly; otherwise a new
    ``WorkerHeartbeat`` is created from the session factory.
    """
    from sqlalchemy.ext.asyncio import create_async_engine

    worker_id = config.worker_name
    if startup_validator is None:
        from app.startup_validation import validate_worker_startup

        startup_validator = validate_worker_startup
    startup_validator(config)

    if session_factory is not None:
        factory = session_factory
        engine = None
    else:
        engine = create_async_engine(config.database_url, pool_pre_ping=True)
        factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    log.info(
        "Worker started",
        extra={
            "worker_id": worker_id,
            "env": config.app_env,
            "poll_interval": config.worker_poll_interval_seconds,
        },
    )

    # Create one heartbeat instance for the entire worker lifecycle
    hb = heartbeat or WorkerHeartbeat(factory, worker_id)
    try:
        await hb.initialize()
    except Exception:
        log.exception("Failed to initialize heartbeat", extra={"worker_id": worker_id})
        raise

    # Consumer
    default_consumer = consumer or _create_consumer(factory, worker_id, config)

    shutdown_requested = False

    while not shutdown_requested and not shutdown_event.is_set():
        try:
            await hb.refresh()

            await default_consumer.run_once()

        except asyncio.CancelledError:
            log.info("Worker cancelled", extra={"worker_id": worker_id})
            shutdown_requested = True
            break
        except Exception:
            log.exception("Worker iteration failed", extra={"worker_id": worker_id})

        if not shutdown_requested and not shutdown_event.is_set():
            try:
                await asyncio.wait_for(
                    shutdown_event.wait(),
                    timeout=config.worker_poll_interval_seconds,
                )
            except asyncio.TimeoutError:
                pass

    # Finalize
    log.info("Worker shutting down", extra={"worker_id": worker_id})
    try:
        await hb.finalize("STOPPED")
    except Exception:
        log.exception("Failed to finalize heartbeat", extra={"worker_id": worker_id})

    if engine is not None:
        await engine.dispose()
    log.info("Worker shut down complete", extra={"worker_id": worker_id})


def _create_consumer(
    factory: async_sessionmaker[AsyncSession],
    worker_id: str,
    config: WorkerConfig,
) -> Any:
    """Lazy import to avoid backend dependency at module level."""
    from pathlib import Path
    from app.consumers.rebuild_analysis_requests import RebuildAnalysisRequestConsumer
    from app.trade_workspace.workers.analysis_processor import (
        LocalEvidenceImageResolver,
        RebuildAnalysisProcessor,
    )

    storage_root = Path(config.storage_root)

    def processor_factory(session: AsyncSession) -> RebuildAnalysisProcessor:
        return RebuildAnalysisProcessor(
            session=session,
            image_resolver=LocalEvidenceImageResolver(storage_root=storage_root),
        )

    return RebuildAnalysisRequestConsumer(
        session_factory=factory,
        processor_factory=processor_factory,
        worker_id=worker_id,
    )


def _build_validation_service(service_cls: type[Any]) -> Any:
    try:
        return service_cls(schema_package_root="schemas/production/v1")
    except Exception as exc:
        raise RuntimeError(
            f"Failed to initialize UnifiedValidationService: {exc}",
        ) from exc


def _build_validation_callback_factory(validation_service: Any) -> Callable[..., Any]:
    def factory(
        *,
        analysis_type: str,
        session_status_before_job: str | None,
        canonical_facts: dict[str, object],
    ) -> Callable[[dict[str, object]], tuple[bool, tuple[Any, ...]]]:
        trade_state = _canonical_trade_state_from_facts(canonical_facts)

        def validate(payload: dict[str, object]) -> tuple[bool, tuple[Any, ...]]:
            result = validation_service.validate(
                payload,
                expected_analysis_type=analysis_type,
                trade_state=trade_state,
                session_status_before_job=session_status_before_job,
                continue_on_schema_errors=analysis_type == "INITIAL_ANALYSIS",
            )
            return result.valid, result.issues

        return validate

    return factory


def _assert_real_validation_factory(
    validate_factory: Callable[..., Any],
    placeholder_validate: Callable[[dict[str, object]], tuple[bool, tuple[Any, ...]]],
) -> None:
    probe = validate_factory(
        analysis_type="INITIAL_ANALYSIS",
        session_status_before_job=None,
        canonical_facts={},
    )
    if probe is placeholder_validate:
        raise RuntimeError(
            "Worker validation callback resolved to placeholder _always_invalid.",
        )


def _canonical_trade_state_from_facts(
    canonical_facts: dict[str, object],
) -> dict[str, object] | None:
    trade_state: dict[str, object] = {}

    session_id = canonical_facts.get("session_id")
    if session_id is not None:
        trade_state["session_id"] = session_id

    ticker = canonical_facts.get("ticker")
    if ticker is not None:
        trade_state["ticker"] = ticker

    position: dict[str, object] = {}
    for key in (
        "entry_price",
        "original_quantity",
        "remaining_quantity",
        "active_stop_loss",
        "active_target",
        "position_status",
    ):
        value = canonical_facts.get(key)
        if value is not None:
            position[key] = value

    if position:
        trade_state["position"] = position

    return trade_state or None
