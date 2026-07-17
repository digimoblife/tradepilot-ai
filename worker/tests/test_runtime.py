import asyncio

import pytest

from app.config import WorkerConfig
from app.runtime import run_worker


@pytest.mark.asyncio
async def test_runtime_starts_and_stops_on_shutdown_event() -> None:
    config = WorkerConfig(worker_poll_interval_seconds=1)
    shutdown_event = asyncio.Event()

    async def trigger_shutdown() -> None:
        await asyncio.sleep(0.05)
        shutdown_event.set()

    await asyncio.gather(
        run_worker(config, shutdown_event),
        trigger_shutdown(),
    )


@pytest.mark.asyncio
async def test_runtime_does_not_require_database() -> None:
    config = WorkerConfig(worker_poll_interval_seconds=1)
    shutdown_event = asyncio.Event()
    shutdown_event.set()
    await run_worker(config, shutdown_event)


@pytest.mark.asyncio
async def test_runtime_exits_immediately_when_shutdown_is_set() -> None:
    config = WorkerConfig(worker_poll_interval_seconds=3600)
    shutdown_event = asyncio.Event()
    shutdown_event.set()
    await asyncio.wait_for(
        run_worker(config, shutdown_event),
        timeout=1.0,
    )


@pytest.mark.asyncio
async def test_runtime_idle_cycle_does_not_busy_spin() -> None:
    config = WorkerConfig(worker_poll_interval_seconds=1)
    shutdown_event = asyncio.Event()
    shutdown_event.set()
    start = asyncio.get_event_loop().time()
    await run_worker(config, shutdown_event)
    elapsed = asyncio.get_event_loop().time() - start
    assert elapsed < 0.5, f"Runtime took {elapsed:.3f}s — may have busy-spun"
