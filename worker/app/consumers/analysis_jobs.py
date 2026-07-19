"""Analysis job consumer (TP-0805).

Coordinates queue claiming and processing for one job iteration.
Uses injected queue and processor — no direct backend imports.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

logger = logging.getLogger(__name__)


class AnalysisJobConsumer:
    """Claims and processes one eligible analysis job per call.

    Accepts a queue factory and processor factory via dependency
    injection, avoiding direct coupling to backend implementations.
    """

    def __init__(
        self,
        session_factory: Any,
        queue: Any,
        processor: Any,
        worker_id: str,
    ) -> None:
        self._session_factory = session_factory
        self._queue_cls = queue
        self._processor_cls = processor
        self._worker_id = worker_id

    async def run_once(self) -> bool:
        """Claim and process one job.

        Returns ``True`` if a job was claimed and processed.
        """
        lease_duration = timedelta(seconds=300)

        async with self._session_factory() as claim_session:
            claim_queue = self._queue_cls(claim_session)
            claimed = await claim_queue.claim_next(
                worker_id=self._worker_id,
                lease_duration=lease_duration,
            )
            if claimed is None:
                return False
            await claim_session.commit()

        async with self._session_factory() as process_session:
            process_processor = self._processor_cls(
                session=process_session,
            )

            try:
                result = await process_processor.process(
                    job_id=claimed.job_id,
                    worker_id=self._worker_id,
                )
                await process_session.commit()
                logger.info(
                    "Job %s processed by %s: status=%s restored=%s",
                    claimed.job_id,
                    self._worker_id,
                    result.job_status,
                    getattr(result, "restored_session_status", None),
                )
            except Exception:
                await process_session.rollback()
                logger.exception(
                    "Job %s processing failed for worker %s",
                    claimed.job_id,
                    self._worker_id,
                )
                raise

        return True
