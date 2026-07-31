"""Rebuild analysis request consumer for database-backed queue.

Coordinates claim transaction and processing transaction for analysis_requests_v2.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

try:
    from app.trade_workspace.models.analysis_request import (
        AnalysisRequestV2,
        AnalysisRequestV2Status,
        AnalysisRequestV2Type,
    )
    from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
    from app.trade_workspace.services.analysis_request_claim import (
        AnalysisRequestClaimService,
        ClaimedAnalysisRequest,
    )
    from app.trade_workspace.workers.analysis_processor import _sanitize_failure
except ModuleNotFoundError:
    from backend.app.trade_workspace.models.analysis_request import (  # type: ignore[no-redef]
        AnalysisRequestV2,
        AnalysisRequestV2Status,
        AnalysisRequestV2Type,
    )
    from backend.app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status  # type: ignore[no-redef]
    from backend.app.trade_workspace.services.analysis_request_claim import (  # type: ignore[no-redef]
        AnalysisRequestClaimService,
        ClaimedAnalysisRequest,
    )
    from backend.app.trade_workspace.workers.analysis_processor import _sanitize_failure  # type: ignore[no-redef]

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
                await self._mark_failed_request(process_session, claimed.request_id, exc)

        return True

    async def _mark_failed_request(
        self,
        session: AsyncSession,
        request_id: uuid.UUID,
        exc: Exception,
    ) -> None:
        """Safely mark a claimed request FAILED if processor factory construction or execution failed."""
        try:
            try:
                await session.rollback()
            except Exception:
                pass

            request = await session.scalar(
                select(AnalysisRequestV2)
                .where(AnalysisRequestV2.id == request_id)
                .with_for_update()
            )
            if request is None:
                return

            if (
                request.status is AnalysisRequestV2Status.COMPLETED
                or request.status is AnalysisRequestV2Status.FAILED
            ):
                return

            trade_session = await session.scalar(
                select(TradeSessionV2)
                .where(TradeSessionV2.id == request.session_id)
                .with_for_update()
            )

            error_code, error_message = _sanitize_failure(exc)

            request.status = AnalysisRequestV2Status.FAILED
            request.completed_at = datetime.now(timezone.utc)
            request.error_code = error_code
            request.error_message = error_message
            request.processed_response = None

            if (
                trade_session is not None
                and trade_session.status is TradeSessionV2Status.ANALYZING
            ):
                if request.analysis_type is AnalysisRequestV2Type.INITIAL_ANALYSIS:
                    trade_session.status = TradeSessionV2Status.DRAFT
                elif request.analysis_type is AnalysisRequestV2Type.WAIT_UPDATE:
                    trade_session.status = TradeSessionV2Status.WAITING
                elif request.analysis_type is AnalysisRequestV2Type.POSITION_UPDATE:
                    trade_session.status = TradeSessionV2Status.OPEN_POSITION

            await session.flush()
            await session.commit()
        except Exception as fail_exc:
            log.exception(
                "Failed to mark request as FAILED after processor failure",
                extra={
                    "analysis_request_id": str(request_id),
                    "worker_id": self._worker_id,
                    "error": str(fail_exc),
                },
            )
            try:
                await session.rollback()
            except Exception:
                pass
