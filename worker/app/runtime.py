"""Worker runtime loop (TP-0805).

Coordinates polling, consumer, and heartbeat lifecycle.
Uses dependency injection — no direct backend imports.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import WorkerConfig
from app.consumers.analysis_jobs import AnalysisJobConsumer
from app.heartbeat import WorkerHeartbeat

logger = logging.getLogger(__name__)


async def run_worker(
    config: WorkerConfig,
    shutdown_event: asyncio.Event,
    *,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
    consumer: AnalysisJobConsumer | None = None,
    heartbeat: WorkerHeartbeat | None = None,
) -> None:
    """Start the worker polling loop.

    Accepts optional injected dependencies for testing.
    """
    from sqlalchemy.ext.asyncio import create_async_engine

    worker_id = config.worker_name

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

    logger.info(
        "Worker %s started (env=%s, poll=%ss)",
        worker_id,
        config.app_env,
        config.worker_poll_interval_seconds,
    )

    # Heartbeat
    async with factory() as hb_session:
        hb = heartbeat or WorkerHeartbeat(hb_session, worker_id)
        try:
            await hb.initialize()
        except Exception:
            logger.exception("Failed to initialize heartbeat for %s", worker_id)
            raise

    # Consumer
    default_consumer = consumer or _create_consumer(factory, worker_id)

    shutdown_requested = False

    while not shutdown_requested and not shutdown_event.is_set():
        try:
            async with factory() as hb_session:
                hb_refresh = heartbeat or WorkerHeartbeat(hb_session, worker_id)
                try:
                    await hb_refresh.refresh()
                except Exception:
                    logger.warning("Heartbeat refresh failed for %s", worker_id)

            await default_consumer.run_once()

        except asyncio.CancelledError:
            logger.info("Worker %s cancelled", worker_id)
            shutdown_requested = True
            break
        except Exception:
            logger.exception("Worker %s iteration failed", worker_id)

        if not shutdown_requested and not shutdown_event.is_set():
            try:
                await asyncio.wait_for(
                    shutdown_event.wait(),
                    timeout=config.worker_poll_interval_seconds,
                )
            except asyncio.TimeoutError:
                pass

    # Finalize
    logger.info("Worker %s shutting down", worker_id)
    try:
        async with factory() as hb_session:
            hb_final = heartbeat or WorkerHeartbeat(hb_session, worker_id)
            await hb_final.finalize("STOPPED")
    except Exception:
        logger.exception("Failed to finalize heartbeat for %s", worker_id)

    if engine is not None:
        await engine.dispose()
    logger.info("Worker %s shut down complete", worker_id)


def _create_consumer(
    factory: async_sessionmaker[AsyncSession],
    worker_id: str,
) -> Any:
    """Lazy import to avoid backend dependency at module level."""
    from app.jobs import AnalysisProcessor, PostgreSQLJobQueue

    return AnalysisJobConsumer(
        session_factory=factory,
        queue=PostgreSQLJobQueue,
        processor=AnalysisProcessor,
        worker_id=worker_id,
    )
