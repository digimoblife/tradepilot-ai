import asyncio
import signal

from app.config import WorkerConfig
from app.logging import configure_logging, get_logger
from app.runtime import run_worker

log = get_logger(__name__)


def register_shutdown_handlers(
    loop: asyncio.AbstractEventLoop,
    shutdown_event: asyncio.Event,
) -> None:
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown_event.set)
        except (NotImplementedError, ValueError):
            pass


async def main() -> None:
    config = WorkerConfig()
    configure_logging(config.log_level)

    shutdown_event = asyncio.Event()

    loop = asyncio.get_running_loop()
    register_shutdown_handlers(loop, shutdown_event)

    log.info("Initialising worker", extra={"worker_name": config.worker_name})

    await run_worker(config, shutdown_event)

    log.info("Worker shut down complete", extra={"worker_name": config.worker_name})


if __name__ == "__main__":
    asyncio.run(main())
