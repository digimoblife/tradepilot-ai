import asyncio
import logging

from app.config import WorkerConfig

logger = logging.getLogger(__name__)


async def run_worker(
    config: WorkerConfig,
    shutdown_event: asyncio.Event,
) -> None:
    logger.info(
        "Worker %s started (env=%s, poll=%ss)",
        config.worker_name,
        config.app_env,
        config.worker_poll_interval_seconds,
    )

    while not shutdown_event.is_set():
        try:
            await asyncio.wait_for(
                shutdown_event.wait(),
                timeout=config.worker_poll_interval_seconds,
            )
        except asyncio.TimeoutError:
            pass

    logger.info("Worker %s stopped", config.worker_name)
