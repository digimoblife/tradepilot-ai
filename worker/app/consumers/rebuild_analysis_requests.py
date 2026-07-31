"""Rebuild analysis request consumer for database-backed queue.

Coordinates claim transaction and processing transaction for analysis_requests_v2.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

try:
    from app.trade_workspace.services.analysis_request_claim import (
        AnalysisRequestClaimService,
        ClaimedAnalysisRequest,
    )
except ModuleNotFoundError:
    from backend.app.trade_workspace.services.analysis_request_claim import (  # type: ignore[no-redef]
        AnalysisRequestClaimService,
        ClaimedAnalysisRequest,
    )

log = logging.getLogger(__name__)


class RebuildAnalysisRequestConsumer:
    """Claims and processes one eligible PENDING rebuild analysis request per run_once call."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        processor_factory: Callable[[AsyncSession], Any],
        worker_id: str,
        claim_service_factory: Callable[[AsyncSession], Any] | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._processor_factory = processor_factory
        self._worker_id = worker_id
        self._claim_service_factory = claim_service_factory or AnalysisRequestClaimService

    async def run_once(self) -> bool:
        """Claim one PENDING request and process it.

        1. Open claim session.
        2. Claim request via AnalysisRequestClaimService (FOR UPDATE SKIP LOCKED).
        3. Commit claim transaction (setting status=PROCESSING) and close claim session.
        4. If claimed, open separate processing session, instantiate processor, and process.
        5. Return True if a request was claimed and processed, False otherwise.
        """
        claimed: ClaimedAnalysisRequest | None = None

        # 1 & 2 & 3: Claim transaction
        async with self._session_factory() as claim_session:
            claim_service = self._claim_service_factory(claim_session)
            claimed = await claim_service.claim_next(worker_id=self._worker_id)
            if claimed is not None:
                await claim_session.commit()

        if claimed is None:
            return False

        # 4 & 5: Processing transaction in separate session
        async with self._session_factory() as process_session:
            try:
                processor = self._processor_factory(process_session)
                result = await processor.process(analysis_request_id=claimed.request_id)
                log.info(
                    "Rebuild request processed",
                    extra={
                        "analysis_request_id": str(claimed.request_id),
                        "worker_id": self._worker_id,
                        "status": getattr(result, "status", "UNKNOWN"),
                    },
                )
            except Exception as exc:
                log.exception(
                    "Rebuild request processing failed",
                    extra={
                        "analysis_request_id": str(claimed.request_id),
                        "worker_id": self._worker_id,
                        "error": str(exc),
                    },
                )

        return True
