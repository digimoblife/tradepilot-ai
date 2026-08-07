from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AppConfig
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
from app.trade_workspace.services.analysis_request_queue import (
    AnalysisRequestQueueService,
    DuplicateActiveRequestError,
    QueueSubmissionError,
    SessionNotFoundError,
    SessionOwnershipMismatchError,
)
from app.trade_workspace.services.eligibility import (
    initial_evidence_session_is_eligible,
    initial_evidence_set_is_complete,
    request_is_active,
)

_REQUIRED_EVIDENCE = (
    EvidenceUploadV2Type.ORDERBOOK,
    EvidenceUploadV2Type.CHART_3_MONTH,
    EvidenceUploadV2Type.CHART_6_MONTH,
)


class InitialAnalysisSubmissionError(Exception):
    code = "INITIAL_ANALYSIS_SUBMISSION_FAILED"
    status_code = 422


class InitialAnalysisSessionNotFoundError(InitialAnalysisSubmissionError):
    code = "SESSION_NOT_FOUND"
    status_code = 404


class InitialAnalysisSessionIneligibleError(InitialAnalysisSubmissionError):
    code = "SESSION_NOT_ELIGIBLE"
    status_code = 409


class InitialAnalysisEvidenceInvalidError(InitialAnalysisSubmissionError):
    code = "INITIAL_EVIDENCE_INVALID"


class InitialAnalysisActiveRequestError(InitialAnalysisSubmissionError):
    code = "INITIAL_ANALYSIS_ACTIVE"
    status_code = 409


class InitialAnalysisPersistenceError(InitialAnalysisSubmissionError):
    code = "INITIAL_ANALYSIS_PERSISTENCE_FAILED"
    status_code = 500


class InitialAnalysisQueueError(InitialAnalysisSubmissionError):
    code = "INITIAL_ANALYSIS_QUEUE_FAILED"
    status_code = 503


@dataclass(frozen=True, slots=True)
class InitialAnalysisSubmissionResult:
    analysis_request_id: uuid.UUID
    session_id: uuid.UUID
    analysis_type: AnalysisRequestV2Type
    request_status: AnalysisRequestV2Status
    session_status: TradeSessionV2Status
    created_at: datetime


class InitialAnalysisSubmissionService:
    def __init__(
        self,
        session: AsyncSession,
        queue: object = None,
        config: AppConfig | None = None,
    ) -> None:
        self._session = session
        self._queue = queue
        self._config = config
        self._lock_key: int | None = None

    async def submit(
        self, *, user_id: uuid.UUID, session_id: uuid.UUID
    ) -> InitialAnalysisSubmissionResult:
        await self._acquire_lock(session_id)
        try:
            trade_session = await self._load_session(user_id, session_id)
            if not initial_evidence_session_is_eligible(trade_session.status):
                raise InitialAnalysisSessionIneligibleError(
                    "Trade session is no longer eligible for initial analysis"
                )
            evidence = await self._load_required_evidence(session_id)
            active = await self._active_request(session_id)
            if active is not None:
                raise InitialAnalysisActiveRequestError(
                    "An active initial analysis request already exists"
                )

            snapshot = {
                "session_id": str(trade_session.id),
                "ticker": trade_session.ticker,
                "company_name": trade_session.company_name,
                "analysis_type": AnalysisRequestV2Type.INITIAL_ANALYSIS.value,
                "evidence_ids": {item.evidence_type.value: str(item.id) for item in evidence},
            }
            try:
                result = await AnalysisRequestQueueService(
                    self._session, config=self._config
                ).submit(
                    user_id=user_id,
                    session_id=session_id,
                    analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                    prompt_version="v1",
                    input_snapshot=snapshot,
                    evidence_ids=[item.id for item in evidence],
                )
                trade_session.status = TradeSessionV2Status.ANALYZING
                await self._session.commit()
            except (DuplicateActiveRequestError,) as exc:
                await self._session.rollback()
                raise InitialAnalysisActiveRequestError(str(exc)) from exc
            except (SessionNotFoundError, SessionOwnershipMismatchError) as exc:
                await self._session.rollback()
                raise InitialAnalysisSessionNotFoundError(str(exc)) from exc
            except QueueSubmissionError as exc:
                await self._session.rollback()
                raise InitialAnalysisQueueError(str(exc)) from exc
            except Exception as exc:
                await self._session.rollback()
                raise InitialAnalysisPersistenceError(str(exc)) from exc

            request = await self._session.scalar(
                select(AnalysisRequestV2).where(AnalysisRequestV2.id == result.request_id)
            )
            if request is None:
                raise InitialAnalysisPersistenceError("Created request could not be read")
            return InitialAnalysisSubmissionResult(
                analysis_request_id=request.id,
                session_id=session_id,
                analysis_type=request.analysis_type,
                request_status=request.status,
                session_status=TradeSessionV2Status.ANALYZING,
                created_at=request.created_at,
            )
        finally:
            await self._release_lock()

    async def _load_session(self, user_id: uuid.UUID, session_id: uuid.UUID) -> TradeSessionV2:
        item = await self._session.scalar(
            select(TradeSessionV2)
            .where(TradeSessionV2.id == session_id, TradeSessionV2.user_id == user_id)
            .with_for_update()
        )
        if item is None:
            raise InitialAnalysisSessionNotFoundError("Rebuild session was not found")
        if not initial_evidence_session_is_eligible(item.status):
            raise InitialAnalysisSessionIneligibleError("Trade session is not a draft")
        return item

    async def _load_required_evidence(self, session_id: uuid.UUID) -> list[EvidenceUploadV2]:
        items = list(
            (
                await self._session.scalars(
                    select(EvidenceUploadV2)
                    .where(EvidenceUploadV2.session_id == session_id)
                    .with_for_update()
                )
            ).all()
        )
        by_type: dict[EvidenceUploadV2Type, list[EvidenceUploadV2]] = {}
        for item in items:
            by_type.setdefault(item.evidence_type, []).append(item)
        selected: list[EvidenceUploadV2] = []
        for evidence_type in _REQUIRED_EVIDENCE:
            matches = by_type.get(evidence_type, [])
            if len(matches) != 1:
                raise InitialAnalysisEvidenceInvalidError(
                    "Exactly one unassigned evidence record is required for each initial role"
                )
            item = matches[0]
            if item.analysis_request_id is not None or item.observation_period is not None:
                raise InitialAnalysisEvidenceInvalidError(
                    "Initial evidence is already assigned or has an observation period"
                )
            selected.append(item)
        if not initial_evidence_set_is_complete(items):
            raise InitialAnalysisEvidenceInvalidError(
                "Initial evidence is already assigned or has an observation period"
            )
        return selected

    async def _active_request(self, session_id: uuid.UUID) -> AnalysisRequestV2 | None:
        return await self._session.scalar(
            select(AnalysisRequestV2)
            .where(
                AnalysisRequestV2.session_id == session_id,
                AnalysisRequestV2.analysis_type == AnalysisRequestV2Type.INITIAL_ANALYSIS,
                AnalysisRequestV2.status.in_(
                    tuple(status for status in AnalysisRequestV2Status if request_is_active(status))
                ),
            )
            .limit(1)
        )

    async def _acquire_lock(self, session_id: uuid.UUID) -> None:
        self._lock_key = int.from_bytes(session_id.bytes[:8], byteorder="big", signed=True)
        await self._session.execute(select(func.pg_advisory_xact_lock(self._lock_key)))

    async def _release_lock(self) -> None:
        self._lock_key = None
