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
from app.trade_workspace.models.position import PositionV2, PositionV2Status
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
from app.trade_workspace.services.eligibility import (
    open_position_session_is_eligible,
    request_is_active,
    single_open_position,
    update_evidence_is_ready,
)

class PositionUpdateAnalysisSubmissionError(Exception):
    code = "POSITION_UPDATE_ANALYSIS_SUBMISSION_FAILED"
    status_code = 422


class PositionUpdateAnalysisSessionNotFoundError(PositionUpdateAnalysisSubmissionError):
    code = "SESSION_NOT_FOUND"
    status_code = 404


class PositionUpdateAnalysisNotAllowedError(PositionUpdateAnalysisSubmissionError):
    code = "POSITION_UPDATE_ANALYSIS_NOT_ALLOWED"
    status_code = 409


class PositionUpdateAnalysisInputNotReadyError(PositionUpdateAnalysisSubmissionError):
    code = "POSITION_UPDATE_INPUT_NOT_READY"
    status_code = 409


class PositionUpdateAnalysisActiveRequestError(PositionUpdateAnalysisSubmissionError):
    code = "POSITION_UPDATE_ANALYSIS_ACTIVE"
    status_code = 409


class PositionUpdateAnalysisPersistenceError(PositionUpdateAnalysisSubmissionError):
    code = "POSITION_UPDATE_ANALYSIS_PERSISTENCE_FAILED"
    status_code = 500


class PositionUpdateAnalysisQueueError(PositionUpdateAnalysisSubmissionError):
    code = "POSITION_UPDATE_ANALYSIS_QUEUE_FAILED"
    status_code = 503


class PositionUpdateAnalysisTransitionError(PositionUpdateAnalysisSubmissionError):
    code = "POSITION_UPDATE_ANALYSIS_TRANSITION_FAILED"
    status_code = 500


@dataclass(frozen=True, slots=True)
class PositionUpdateAnalysisSubmissionResult:
    analysis_request_id: uuid.UUID
    session_id: uuid.UUID
    position_id: uuid.UUID
    analysis_type: AnalysisRequestV2Type
    request_status: AnalysisRequestV2Status
    evidence_id: uuid.UUID
    observation_period: AnalysisRequestV2ObservationPeriod
    session_status: TradeSessionV2Status
    position_status: PositionV2Status
    created_at: datetime


class PositionUpdateAnalysisSubmissionService:
    """Submit one latest unlinked Position Update through the rebuild queue."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._lock_key: int | None = None

    async def submit(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> PositionUpdateAnalysisSubmissionResult:
        await self._acquire_lock(session_id)
        try:
            trade_session, position = await self._load_owned_open_position(user_id, session_id)
            if await self._active_request(session_id) is not None:
                raise PositionUpdateAnalysisActiveRequestError(
                    "An active Position Update analysis request already exists"
                )
            evidence = await self._select_latest_evidence(session_id)
            broker_flow = await self._select_matching_broker_flow(session_id, evidence)
            evidence_records = [evidence] + ([broker_flow] if broker_flow is not None else [])
            snapshot = {
                "session_id": str(trade_session.id),
                "ticker": trade_session.ticker,
                "analysis_type": AnalysisRequestV2Type.POSITION_UPDATE.value,
                "position_id": str(position.id),
                "evidence_id": str(evidence.id),
                "current_price": str(evidence.current_price),
                "observation_period": evidence.observation_period.value,
                "observation_timestamp": evidence.observation_timestamp.isoformat(),
                "provider": "gemini",
                "model": DEFAULT_GEMINI_MODEL,
                "prompt_version": "v1",
            }
            try:
                request_result = await AnalysisRequestQueueService(
                    self._session,
                    config=AppConfig(gemini_model=DEFAULT_GEMINI_MODEL),
                ).submit(
                    user_id=user_id,
                    session_id=session_id,
                    analysis_type=AnalysisRequestV2Type.POSITION_UPDATE,
                    prompt_version="v1",
                    input_snapshot=snapshot,
                    current_price=evidence.current_price,
                    observation_period=evidence.observation_period,
                    observation_at=evidence.observation_timestamp,
                    evidence_ids=[item.id for item in evidence_records],
                )
                await self._session.commit()
            except (SessionNotFoundError, SessionOwnershipMismatchError) as exc:
                await self._session.rollback()
                raise PositionUpdateAnalysisSessionNotFoundError(str(exc)) from exc
            except DuplicateActiveRequestError as exc:
                await self._session.rollback()
                raise PositionUpdateAnalysisActiveRequestError(str(exc)) from exc
            except QueueSubmissionError as exc:
                await self._session.rollback()
                raise PositionUpdateAnalysisQueueError(str(exc)) from exc
            except (PersistenceError, Exception) as exc:
                await self._session.rollback()
                raise PositionUpdateAnalysisPersistenceError(str(exc)) from exc

            created_at = await self._request_created_at(request_result.request_id)
            return PositionUpdateAnalysisSubmissionResult(
                analysis_request_id=request_result.request_id,
                session_id=session_id,
                position_id=position.id,
                analysis_type=request_result.analysis_type,
                request_status=request_result.status,
                evidence_id=evidence.id,
                observation_period=evidence.observation_period,
                session_status=TradeSessionV2Status.OPEN_POSITION,
                position_status=position.status,
                created_at=created_at,
            )
        finally:
            await self._release_lock()

    async def _load_owned_open_position(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> tuple[TradeSessionV2, PositionV2]:
        trade_session = await self._session.scalar(
            select(TradeSessionV2)
            .where(TradeSessionV2.id == session_id, TradeSessionV2.user_id == user_id)
            .with_for_update()
        )
        if trade_session is None:
            raise PositionUpdateAnalysisSessionNotFoundError("Trade session not found")
        if not open_position_session_is_eligible(trade_session.status):
            raise PositionUpdateAnalysisNotAllowedError(
                "Position Update analysis requires an OPEN_POSITION session"
            )
        positions = list(
            (
                await self._session.scalars(
                    select(PositionV2).where(PositionV2.session_id == session_id).with_for_update()
                )
            ).all()
        )
        if len(positions) != 1:
            raise PositionUpdateAnalysisNotAllowedError(
                "Exactly one position is required for Position Update analysis"
            )
        position = single_open_position(positions)
        if position is None:
            raise PositionUpdateAnalysisNotAllowedError(
                "Position Update analysis requires an OPEN position"
            )
        return trade_session, position

    async def _active_request(self, session_id: uuid.UUID) -> AnalysisRequestV2 | None:
        return await self._session.scalar(
            select(AnalysisRequestV2)
            .where(
                AnalysisRequestV2.session_id == session_id,
                AnalysisRequestV2.analysis_type == AnalysisRequestV2Type.POSITION_UPDATE,
                AnalysisRequestV2.status.in_(
                    tuple(status for status in AnalysisRequestV2Status if request_is_active(status))
                ),
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
        if evidence is None or not update_evidence_is_ready(
            evidence,
            require_relative_path=True,
        ):
            raise PositionUpdateAnalysisInputNotReadyError(
                "No eligible unlinked Position Update input is available"
            )
        return evidence

    async def _request_created_at(self, request_id: uuid.UUID) -> datetime:
        created_at = await self._session.scalar(
            select(AnalysisRequestV2.created_at).where(AnalysisRequestV2.id == request_id)
        )
        if created_at is None:
            raise PositionUpdateAnalysisPersistenceError(
                "Created Position Update analysis request could not be read"
            )
        return created_at

    async def _select_matching_broker_flow(
        self,
        session_id: uuid.UUID,
        orderbook: EvidenceUploadV2,
    ) -> EvidenceUploadV2 | None:
        return await self._session.scalar(
            select(EvidenceUploadV2)
            .where(
                EvidenceUploadV2.session_id == session_id,
                EvidenceUploadV2.evidence_type == EvidenceUploadV2Type.BROKER_FLOW_1D,
                EvidenceUploadV2.analysis_request_id.is_(None),
                EvidenceUploadV2.current_price == orderbook.current_price,
                EvidenceUploadV2.observation_period == orderbook.observation_period,
                EvidenceUploadV2.observation_timestamp == orderbook.observation_timestamp,
                EvidenceUploadV2.uploaded_at == orderbook.uploaded_at,
                func.length(func.btrim(EvidenceUploadV2.file_path)) > 0,
            )
            .limit(1)
            .with_for_update()
        )

    async def _acquire_lock(self, session_id: uuid.UUID) -> None:
        self._lock_key = int.from_bytes(session_id.bytes[:8], byteorder="big", signed=True)
        await self._session.execute(select(func.pg_advisory_xact_lock(self._lock_key)))

    async def _release_lock(self) -> None:
        self._lock_key = None
