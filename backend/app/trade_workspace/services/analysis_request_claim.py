from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2ObservationPeriod,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)


@dataclass(frozen=True, slots=True)
class ClaimedAnalysisRequest:
    """Minimal metadata of a claimed request returned to the caller."""

    request_id: uuid.UUID
    session_id: uuid.UUID
    analysis_type: AnalysisRequestV2Type
    status: AnalysisRequestV2Status
    created_at: datetime
    started_at: datetime
    observation_period: AnalysisRequestV2ObservationPeriod | None


class AnalysisRequestClaimService:
    """Atomically claims at most one eligible PENDING row from analysis_requests_v2.

    Transaction Ownership Contract:
    - This service performs atomic selection using FOR UPDATE SKIP LOCKED.
    - It mutates status to PROCESSING and sets started_at to current UTC time.
    - It flushes (or relies on caller commit) to stage the change.
    - The caller owns the final commit/rollback boundary before executing analysis processing.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim_next(self, *, worker_id: str | None = None) -> ClaimedAnalysisRequest | None:
        """Find and claim the oldest eligible PENDING request.

        Uses PostgreSQL FOR UPDATE SKIP LOCKED to prevent concurrent worker collisions.
        Returns None if no eligible PENDING request is available.
        """
        now = datetime.now(timezone.utc)

        query = (
            select(AnalysisRequestV2)
            .where(AnalysisRequestV2.status == AnalysisRequestV2Status.PENDING)
            .order_by(AnalysisRequestV2.created_at.asc(), AnalysisRequestV2.id.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
            .execution_options(populate_existing=True)
        )

        request = await self._session.scalar(query)
        if request is None:
            return None

        request.status = AnalysisRequestV2Status.PROCESSING
        request.started_at = now

        await self._session.flush()

        return ClaimedAnalysisRequest(
            request_id=request.id,
            session_id=request.session_id,
            analysis_type=request.analysis_type,
            status=request.status,
            created_at=request.created_at,
            started_at=now,
            observation_period=request.observation_period,
        )
