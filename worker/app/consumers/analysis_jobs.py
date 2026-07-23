"""Analysis job consumer (TP-0805).

Coordinates queue claiming and processing for one job iteration.
Uses injected queue and processor — no direct backend imports.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.logging import get_logger

log = get_logger(__name__)


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
            try:
                process_processor = self._processor_cls(
                    session=process_session,
                )
                result = await process_processor.process(
                    job_id=claimed.job_id,
                    worker_id=self._worker_id,
                )
                await process_session.commit()
                log.info(
                    "Job processed",
                    extra={
                        "analysis_job_id": str(claimed.job_id),
                        "worker_id": self._worker_id,
                        "job_status": result.job_status,
                        "restored_status": getattr(result, "restored_session_status", None),
                    },
                )
            except Exception as exc:
                await process_session.rollback()
                await self._record_processing_error(process_session, claimed.job_id, exc)
                log.exception(
                    "Job processing failed",
                    extra={
                        "analysis_job_id": str(claimed.job_id),
                        "worker_id": self._worker_id,
                    },
                )
                raise

        return True

    async def _record_processing_error(
        self,
        session: Any,
        job_id: Any,
        exc: Exception,
    ) -> None:
        queue = self._queue_cls(session)
        record_error = getattr(queue, "record_processing_error", None)
        if record_error is None:
            return

        error_code = str(getattr(exc, "code", "") or "ANALYSIS_JOB_PROCESSING_FAILED")
        error_message = str(exc) or exc.__class__.__name__
        try:
            await record_error(
                job_id=job_id,
                worker_id=self._worker_id,
                error_code=error_code,
                error_message=error_message,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            log.exception(
                "Failed to record job processing error",
                extra={
                    "analysis_job_id": str(job_id),
                    "worker_id": self._worker_id,
                    "error_code": error_code,
                },
            )
