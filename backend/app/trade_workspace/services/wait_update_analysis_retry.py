from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2ObservationPeriod,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
from app.trade_workspace.services.eligibility import (
    request_is_retryable,
    wait_retry_evidence_is_valid,
    wait_update_session_is_eligible,
)

_SESSION_LOCKS: dict[uuid.UUID, asyncio.Lock] = {}
_SESSION_LOCKS_GUARD = asyncio.Lock()


class WaitUpdateAnalysisRetryError(Exception):
    code = "WAIT_UPDATE_RETRY_FAILED"
    status_code = 422


class WaitUpdateAnalysisRetrySessionNotFoundError(WaitUpdateAnalysisRetryError):
    code = "SESSION_NOT_FOUND"
    status_code = 404


class WaitUpdateAnalysisRetryRequestNotFoundError(WaitUpdateAnalysisRetryError):
    code = "WAIT_UPDATE_ANALYSIS_NOT_FOUND"
    status_code = 404


class WaitUpdateAnalysisRetrySessionStateError(WaitUpdateAnalysisRetryError):
    code = "WAIT_UPDATE_RETRY_SESSION_NOT_ELIGIBLE"
    status_code = 409


class WaitUpdateAnalysisRetryNotAllowedError(WaitUpdateAnalysisRetryError):
    code = "WAIT_UPDATE_RETRY_NOT_ALLOWED"
    status_code = 409


class WaitUpdateAnalysisRetryEvidenceError(WaitUpdateAnalysisRetryError):
    code = "WAIT_UPDATE_EVIDENCE_INVALID"
    status_code = 409


class WaitUpdateAnalysisRetryPersistenceError(WaitUpdateAnalysisRetryError):
    code = "WAIT_UPDATE_RETRY_PERSISTENCE_FAILED"
    status_code = 500


class WaitUpdateAnalysisRetryQueueError(WaitUpdateAnalysisRetryError):
    code = "WAIT_UPDATE_RETRY_QUEUE_FAILED"
    status_code = 503


class WaitUpdateAnalysisRetryTransitionError(WaitUpdateAnalysisRetryError):
    code = "WAIT_UPDATE_RETRY_TRANSITION_FAILED"
    status_code = 500


@dataclass(frozen=True, slots=True)
class WaitUpdateAnalysisRetryResult:
    analysis_request_id: uuid.UUID
    session_id: uuid.UUID
    analysis_type: AnalysisRequestV2Type
    request_status: AnalysisRequestV2Status
    session_status: TradeSessionV2Status
    observation_period: AnalysisRequestV2ObservationPeriod | None
    created_at: datetime


class WaitUpdateAnalysisRetryService:
    """Explicitly re-enqueue one eligible WAIT_UPDATE request."""

    def __init__(self, session: AsyncSession, queue: object = None) -> None:
        self._session = session
        self._queue = queue
        self._session_lock: asyncio.Lock | None = None
        self._lock_key: int | None = None

    async def retry(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> WaitUpdateAnalysisRetryResult:
        await self._acquire_session_lock(session_id)
        try:
            trade_session = await self._load_owned_session(user_id, session_id)
            if not wait_update_session_is_eligible(trade_session.status):
                raise WaitUpdateAnalysisRetrySessionStateError(
                    "Trade session is not waiting"
                )
            request = await self._load_latest_request(session_id)
            await self._validate_evidence(session_id, request)
            if not request_is_retryable(request.status):
                raise WaitUpdateAnalysisRetryNotAllowedError(
                    "WAIT Update request is not retryable"
                )

            if request.status is AnalysisRequestV2Status.FAILED:
                request.status = AnalysisRequestV2Status.PENDING
                request.started_at = None
                request.completed_at = None
                request.raw_response = None
                request.processed_response = None
                request.error_code = None
                request.error_message = None

            try:
                await self._session.commit()
            except SQLAlchemyError as exc:
                await self._session.rollback()
                raise WaitUpdateAnalysisRetryPersistenceError(
                    "WAIT Update retry status could not be persisted"
                ) from exc

            return WaitUpdateAnalysisRetryResult(
                analysis_request_id=request.id,
                session_id=session_id,
                analysis_type=request.analysis_type,
                request_status=request.status,
                session_status=TradeSessionV2Status.WAITING,
                observation_period=request.observation_period,
                created_at=request.created_at,
            )
        finally:
            await self._release_session_lock()

    async def _load_owned_session(
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
            raise WaitUpdateAnalysisRetrySessionNotFoundError(
                "Rebuild session was not found"
            )
        return trade_session

    async def _load_latest_request(self, session_id: uuid.UUID) -> AnalysisRequestV2:
        request = await self._session.scalar(
            select(AnalysisRequestV2)
            .where(
                AnalysisRequestV2.session_id == session_id,
                AnalysisRequestV2.analysis_type == AnalysisRequestV2Type.WAIT_UPDATE,
            )
            .order_by(AnalysisRequestV2.created_at.desc(), AnalysisRequestV2.id.desc())
            .limit(1)
            .with_for_update()
        )
        if request is None:
            raise WaitUpdateAnalysisRetryRequestNotFoundError(
                "WAIT Update request was not found"
            )
        return request

    async def _validate_evidence(
        self,
        session_id: uuid.UUID,
        request: AnalysisRequestV2,
    ) -> None:
        evidence = list(
            (
                await self._session.scalars(
                    select(EvidenceUploadV2)
                    .where(EvidenceUploadV2.analysis_request_id == request.id)
                    .with_for_update()
                )
            ).all()
        )
        if len(evidence) not in (1, 2):
            raise WaitUpdateAnalysisRetryEvidenceError(
                "WAIT Update requires ORDERBOOK and at most one BROKER_FLOW_1D"
            )
        orderbooks = [
            item for item in evidence if item.evidence_type is EvidenceUploadV2Type.ORDERBOOK
        ]
        broker_flows = [
            item for item in evidence if item.evidence_type is EvidenceUploadV2Type.BROKER_FLOW_1D
        ]
        if len(orderbooks) != 1 or len(broker_flows) != len(evidence) - 1:
            raise WaitUpdateAnalysisRetryEvidenceError(
                "WAIT Update requires ORDERBOOK and optionally BROKER_FLOW_1D"
            )
        item = orderbooks[0]
        if (
            item.session_id != session_id
            or item.evidence_type is not EvidenceUploadV2Type.ORDERBOOK
            or item.current_price is None
            or item.observation_period is None
            or item.observation_timestamp is None
            or item.current_price != request.current_price
            or item.observation_period is not request.observation_period
            or item.observation_timestamp != request.observation_at
            or not item.file_path.strip()
            or Path(item.file_path).is_absolute()
        ):
            raise WaitUpdateAnalysisRetryEvidenceError(
                "Linked WAIT Update evidence is invalid"
            )
        if any(
            broker.session_id != session_id
            or not broker.file_path.strip()
            or Path(broker.file_path).is_absolute()
            for broker in broker_flows
        ):
            raise WaitUpdateAnalysisRetryEvidenceError(
                "Linked WAIT Update Broker Flow evidence is invalid"
            )
        if not wait_retry_evidence_is_valid(
            session_id=session_id,
            request=request,
            evidence=evidence,
        ):
            raise WaitUpdateAnalysisRetryEvidenceError(
                "Linked WAIT Update evidence is invalid"
            )

    async def _acquire_session_lock(self, session_id: uuid.UUID) -> None:
        async with _SESSION_LOCKS_GUARD:
            self._session_lock = _SESSION_LOCKS.setdefault(session_id, asyncio.Lock())
        await self._session_lock.acquire()
        self._lock_key = int.from_bytes(session_id.bytes[:8], byteorder="big", signed=True)
        try:
            await self._session.execute(select(func.pg_advisory_xact_lock(self._lock_key)))
        except Exception:
            self._session_lock.release()
            self._session_lock = None
            raise

    async def _release_session_lock(self) -> None:
        try:
            self._lock_key = None
        finally:
            if self._session_lock is not None:
                self._session_lock.release()
                self._session_lock = None
