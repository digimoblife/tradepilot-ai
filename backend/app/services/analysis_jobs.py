"""Analysis Job Creation Service (TP-0802).

Validates an analysis request and creates one queued Analysis Job.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.context import ContextFreshnessService
from app.models.analysis_job import AnalysisJob
from app.models.enums import AnalysisJobStatus, AnalysisType, TradeSessionStatus
from app.models.trade_session import TradeSession
from app.repositories.trade_session import TradeSessionRepository
from app.services.evidence import EvidenceService

# ---------------------------------------------------------------------------
# Lifecycle/analysis compatibility
# ---------------------------------------------------------------------------

_ANALYSIS_LIFECYCLE_MAP: dict[str, frozenset[str]] = {
    AnalysisType.INITIAL_ANALYSIS.value: frozenset(
        {TradeSessionStatus.READY_FOR_ANALYSIS.value, TradeSessionStatus.ANALYZING.value}
    ),
    AnalysisType.WATCHING_UPDATE.value: frozenset(
        {TradeSessionStatus.WATCHING.value, TradeSessionStatus.ANALYZING.value}
    ),
    AnalysisType.OPEN_POSITION_UPDATE.value: frozenset(
        {TradeSessionStatus.OPEN_POSITION.value, TradeSessionStatus.ANALYZING.value}
    ),
    AnalysisType.PARTIAL_EXIT_REVIEW.value: frozenset(
        {TradeSessionStatus.PARTIALLY_CLOSED.value, TradeSessionStatus.ANALYZING.value}
    ),
    AnalysisType.CLOSING_ANALYSIS.value: frozenset(
        {
            TradeSessionStatus.CLOSED_TAKE_PROFIT.value,
            TradeSessionStatus.CLOSED_STOP_LOSS.value,
            TradeSessionStatus.CLOSED_MANUAL.value,
            TradeSessionStatus.ANALYZING.value,
        }
    ),
}

# Active job statuses (non-terminal)
_ACTIVE_JOB_STATUSES = frozenset(
    {
        AnalysisJobStatus.CREATED.value,
        AnalysisJobStatus.QUEUED.value,
        AnalysisJobStatus.PROCESSING.value,
        AnalysisJobStatus.RETRYING.value,
    }
)

# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AnalysisJobCreationResult:
    job_id: uuid.UUID
    session_id: uuid.UUID
    analysis_type: str
    job_status: str
    previous_session_status: str
    current_session_status: str


# ---------------------------------------------------------------------------
# Stable errors
# ---------------------------------------------------------------------------


class AnalysisJobCreationError(Exception):
    code: str = "ANALYSIS_JOB_CREATION_ERROR"

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class AnalysisJobSessionNotFoundError(AnalysisJobCreationError):
    code: str = "ANALYSIS_JOB_SESSION_NOT_FOUND_OR_NOT_OWNED"


class AnalysisTypeInvalidForLifecycleError(AnalysisJobCreationError):
    code: str = "ANALYSIS_TYPE_INVALID_FOR_LIFECYCLE"


class AnalysisRequiredEvidenceMissingError(AnalysisJobCreationError):
    code: str = "ANALYSIS_REQUIRED_EVIDENCE_MISSING"


class AnalysisJobAlreadyActiveError(AnalysisJobCreationError):
    code: str = "ANALYSIS_JOB_ALREADY_ACTIVE"


class AnalysisJobContextRebuildFailedError(AnalysisJobCreationError):
    code: str = "ANALYSIS_JOB_CONTEXT_REBUILD_FAILED"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class AnalysisJobCreationService:
    """Validates an analysis request and creates one queued Analysis Job."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._session_repo = TradeSessionRepository(session)
        self._evidence_service = EvidenceService(session=session)

    async def create(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        analysis_type: AnalysisType | str,
        requested_at: datetime | None = None,
    ) -> AnalysisJobCreationResult:
        atype = _normalize_analysis_type(analysis_type)

        # 1. Load owned session
        ts = await self._session_repo.get_by_id_for_user_for_update(session_id, owner_id)
        if ts is None:
            raise AnalysisJobSessionNotFoundError(
                message="Trade Session not found or not owned",
            )

        current_status = (
            ts.stable_status.value if hasattr(ts.stable_status, "value") else str(ts.stable_status)
        )  # noqa: E501

        # 2. Validate analysis type for lifecycle
        allowed = _ANALYSIS_LIFECYCLE_MAP.get(atype)
        if allowed is None or current_status not in allowed:
            raise AnalysisTypeInvalidForLifecycleError(
                message=(
                    f"Analysis type {atype!r} is not allowed "
                    f"from session status {current_status!r}"
                ),
            )

        # 3. Verify required evidence
        required = await self._evidence_service.get_required_evidence(
            session_id=session_id,
            owner_id=owner_id,
            analysis_type=atype,
        )
        if not required.complete:
            missing_names = ", ".join(
                et.value if hasattr(et, "value") else str(et) for et in required.missing_types
            )  # noqa: E501
            raise AnalysisRequiredEvidenceMissingError(
                message=f"Missing required evidence: {missing_names}",
            )

        # 4. Prevent duplicate active job
        await self._check_no_duplicate_active(session_id, owner_id, atype)

        # 5. Ensure current context before queueing analysis
        try:
            freshness = ContextFreshnessService(self._session)
            await freshness.ensure_fresh(session_id=session_id, owner_id=owner_id)
        except Exception as exc:
            raise AnalysisJobContextRebuildFailedError(
                code=getattr(exc, "code", None),
                message=f"Context Summary rebuild failed before queueing analysis: {exc}",
            ) from exc

        # 6. Preserve previous status
        prev_status = (
            ts.stable_status.value if hasattr(ts.stable_status, "value") else str(ts.stable_status)
        )  # noqa: E501

        # 7. Create queued job
        job = AnalysisJob(
            id=uuid.uuid4(),
            session_id=session_id,
            analysis_type=atype,
            status=AnalysisJobStatus.QUEUED,
            attempt_count=0,
            max_attempts=3,
            previous_session_status=prev_status,
            requested_at=requested_at or datetime.now(timezone.utc),
            available_at=datetime.now(timezone.utc),
        )
        self._session.add(job)

        # 8. Transition session to ANALYZING
        _analyzing = TradeSessionStatus.ANALYZING
        ts.lifecycle_status = _analyzing
        ts.stable_status = _analyzing

        await self._session.flush()

        return AnalysisJobCreationResult(
            job_id=job.id,
            session_id=session_id,
            analysis_type=atype,
            job_status=AnalysisJobStatus.QUEUED.value,
            previous_session_status=prev_status,
            current_session_status=_analyzing.value,
        )

    async def _check_no_duplicate_active(
        self,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        analysis_type: str,
    ) -> None:
        result = await self._session.execute(
            select(AnalysisJob)
            .join(TradeSession, AnalysisJob.session_id == TradeSession.id)
            .where(
                AnalysisJob.session_id == session_id,
                TradeSession.owner_id == owner_id,
                AnalysisJob.analysis_type == analysis_type,
                AnalysisJob.status.in_(_ACTIVE_JOB_STATUSES),
            )
            .limit(1)
            .with_for_update()
        )
        existing = result.unique().scalar_one_or_none()
        if existing is not None:
            raise AnalysisJobAlreadyActiveError(
                message=(
                    f"Analysis job of type {analysis_type!r} "
                    f"is already active (status {existing.status.value})"
                ),
            )


def _normalize_analysis_type(atype: AnalysisType | str) -> str:
    if isinstance(atype, str):
        return atype
    return atype.value
