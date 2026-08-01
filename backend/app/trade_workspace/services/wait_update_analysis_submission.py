from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AppConfig
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2ObservationPeriod,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
from app.trade_workspace.services.analysis_request_queue import (
    DEFAULT_GEMINI_MODEL,
    AnalysisRequestQueueService,
    DuplicateActiveRequestError,
    PersistenceError,
    QueueSubmissionError,
    SessionNotFoundError,
    SessionOwnershipMismatchError,
)

_ACTIVE_STATUSES = (
    AnalysisRequestV2Status.PENDING,
    AnalysisRequestV2Status.PROCESSING,
)


class WaitUpdateAnalysisSubmissionError(Exception):
    code = "WAIT_UPDATE_ANALYSIS_SUBMISSION_FAILED"
    status_code = 422


class WaitUpdateAnalysisSessionNotFoundError(WaitUpdateAnalysisSubmissionError):
    code = "SESSION_NOT_FOUND"
    status_code = 404


class WaitUpdateAnalysisSessionIneligibleError(WaitUpdateAnalysisSubmissionError):
    code = "SESSION_NOT_ELIGIBLE"
    status_code = 409


class WaitUpdateAnalysisInputNotReadyError(WaitUpdateAnalysisSubmissionError):
    code = "WAIT_UPDATE_INPUT_NOT_READY"
    status_code = 409


class WaitUpdateAnalysisActiveRequestError(WaitUpdateAnalysisSubmissionError):
    code = "WAIT_UPDATE_ANALYSIS_ACTIVE"
    status_code = 409


class WaitUpdateAnalysisPersistenceError(WaitUpdateAnalysisSubmissionError):
    code = "WAIT_UPDATE_ANALYSIS_PERSISTENCE_FAILED"
    status_code = 500


class WaitUpdateAnalysisQueueError(WaitUpdateAnalysisSubmissionError):
    code = "WAIT_UPDATE_ANALYSIS_QUEUE_FAILED"
    status_code = 503


class WaitUpdateAnalysisTransitionError(WaitUpdateAnalysisSubmissionError):
    code = "WAIT_UPDATE_ANALYSIS_TRANSITION_FAILED"
    status_code = 500


@dataclass(frozen=True, slots=True)
class WaitUpdateAnalysisSubmissionResult:
    analysis_request_id: uuid.UUID
    session_id: uuid.UUID
    analysis_type: AnalysisRequestV2Type
    request_status: AnalysisRequestV2Status
    evidence_id: uuid.UUID
    observation_period: AnalysisRequestV2ObservationPeriod
    session_status: TradeSessionV2Status
    created_at: datetime


class WaitUpdateAnalysisSubmissionService:
    """Submit one latest unlinked WAIT Update through the rebuild queue boundary."""

    def __init__(
        self,
        session: AsyncSession,
        queue: object = None,
        config: AppConfig | None = None,
    ) -> None:
        self._session = session
        self._queue = queue
        self._config = config or AppConfig()
        self._lock_key: int | None = None

    async def submit(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> WaitUpdateAnalysisSubmissionResult:
        await self._acquire_lock(session_id)
        try:
            trade_session = await self._load_owned_waiting_session(user_id, session_id)
            if await self._active_request(session_id) is not None:
                raise WaitUpdateAnalysisActiveRequestError(
                    "An active WAIT Update analysis request already exists"
                )
            evidence = await self._select_latest_evidence(session_id)

            snapshot = {
                "session_id": str(trade_session.id),
                "ticker": trade_session.ticker,
                "company_name": trade_session.company_name,
                "analysis_type": AnalysisRequestV2Type.WAIT_UPDATE.value,
                "evidence_id": str(evidence.id),
                "current_price": str(evidence.current_price),
                "observation_period": evidence.observation_period.value,
                "observation_timestamp": evidence.observation_timestamp.isoformat(),
                "provider": "gemini",
                "model": self._model,
                "prompt_version": "v1",
            }
            try:
                request_result = await AnalysisRequestQueueService(
                    self._session,
                    config=AppConfig(gemini_model=self._model),
                ).submit(
                    user_id=user_id,
                    session_id=session_id,
                    analysis_type=AnalysisRequestV2Type.WAIT_UPDATE,
                    prompt_version="v1",
                    input_snapshot=snapshot,
                    current_price=evidence.current_price,
                    observation_period=evidence.observation_period,
                    observation_at=evidence.observation_timestamp,
                    evidence_ids=[evidence.id],
                )
                await self._session.commit()
            except (SessionNotFoundError, SessionOwnershipMismatchError) as exc:
                await self._session.rollback()
                raise WaitUpdateAnalysisSessionNotFoundError(str(exc)) from exc
            except DuplicateActiveRequestError as exc:
                await self._session.rollback()
                raise WaitUpdateAnalysisActiveRequestError(str(exc)) from exc
            except QueueSubmissionError as exc:
                await self._session.rollback()
                raise WaitUpdateAnalysisQueueError(str(exc)) from exc
            except (PersistenceError, Exception) as exc:
                await self._session.rollback()
                raise WaitUpdateAnalysisPersistenceError(str(exc)) from exc

            request = await self._session.scalar(
                select(AnalysisRequestV2).where(AnalysisRequestV2.id == request_result.request_id)
            )
            if request is None:
                raise WaitUpdateAnalysisPersistenceError("Created request could not be read")

            return WaitUpdateAnalysisSubmissionResult(
                analysis_request_id=request.id,
                session_id=session_id,
                analysis_type=request.analysis_type,
                request_status=request.status,
                evidence_id=evidence.id,
                observation_period=evidence.observation_period,
                session_status=TradeSessionV2Status.WAITING,
                created_at=await self._request_created_at(request_result.request_id),
            )
        finally:
            await self._release_lock()

    @property
    def _model(self) -> str:
        return DEFAULT_GEMINI_MODEL

    async def _load_owned_waiting_session(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> TradeSessionV2:
        trade_session = await self._session.scalar(
            select(TradeSessionV2)
            .where(TradeSessionV2.id == session_id, TradeSessionV2.user_id == user_id)
            .with_for_update()
        )
        if trade_session is None:
            raise WaitUpdateAnalysisSessionNotFoundError("Rebuild session was not found")
        if trade_session.status is not TradeSessionV2Status.WAITING:
            raise WaitUpdateAnalysisSessionIneligibleError(
                "WAIT Update analysis requires a WAITING session"
            )
        return trade_session

    async def _active_request(self, session_id: uuid.UUID) -> AnalysisRequestV2 | None:
        return await self._session.scalar(
            select(AnalysisRequestV2)
            .where(
                AnalysisRequestV2.session_id == session_id,
                AnalysisRequestV2.analysis_type == AnalysisRequestV2Type.WAIT_UPDATE,
                AnalysisRequestV2.status.in_(_ACTIVE_STATUSES),
            )
            .limit(1)
        )

    async def _select_latest_evidence(self, session_id: uuid.UUID) -> EvidenceUploadV2:
        evidence = await self._session.scalar(
            select(EvidenceUploadV2)
            .where(
                EvidenceUploadV2.session_id == session_id,
                EvidenceUploadV2.evidence_type == EvidenceUploadV2Type.ORDERBOOK,
                EvidenceUploadV2.analysis_request_id.is_(None),
                EvidenceUploadV2.current_price.is_not(None),
                EvidenceUploadV2.observation_period.is_not(None),
                EvidenceUploadV2.observation_timestamp.is_not(None),
                func.length(func.btrim(EvidenceUploadV2.file_path)) > 0,
            )
            .order_by(
                EvidenceUploadV2.observation_timestamp.desc(),
                EvidenceUploadV2.uploaded_at.desc(),
                EvidenceUploadV2.id.desc(),
            )
            .with_for_update()
        )
        if evidence is None:
            raise WaitUpdateAnalysisInputNotReadyError(
                "No eligible unlinked WAIT Update input is available"
            )
        return evidence

    async def _request_created_at(self, request_id: uuid.UUID) -> datetime:
        created_at = await self._session.scalar(
            select(AnalysisRequestV2.created_at).where(AnalysisRequestV2.id == request_id)
        )
        if created_at is None:
            raise WaitUpdateAnalysisPersistenceError(
                "Created WAIT Update analysis request could not be read"
            )
        return created_at

    async def _acquire_lock(self, session_id: uuid.UUID) -> None:
        self._lock_key = int.from_bytes(session_id.bytes[:8], byteorder="big", signed=True)
        await self._session.execute(select(func.pg_advisory_xact_lock(self._lock_key)))

    async def _release_lock(self) -> None:
        self._lock_key = None
