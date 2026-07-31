from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status

_REQUIRED_EVIDENCE = (
    EvidenceUploadV2Type.ORDERBOOK,
    EvidenceUploadV2Type.CHART_3_MONTH,
    EvidenceUploadV2Type.CHART_6_MONTH,
)
_SESSION_LOCKS: dict[uuid.UUID, asyncio.Lock] = {}
_SESSION_LOCKS_GUARD = asyncio.Lock()


class InitialAnalysisRetryError(Exception):
    code = "INITIAL_ANALYSIS_RETRY_FAILED"
    status_code = 422


class InitialAnalysisRetrySessionNotFoundError(InitialAnalysisRetryError):
    code = "SESSION_NOT_FOUND"
    status_code = 404


class InitialAnalysisRetrySessionStateError(InitialAnalysisRetryError):
    code = "SESSION_NOT_ELIGIBLE"
    status_code = 409


class InitialAnalysisRetryRequestNotFoundError(InitialAnalysisRetryError):
    code = "INITIAL_ANALYSIS_NOT_FOUND"
    status_code = 404


class InitialAnalysisRetryNotAllowedError(InitialAnalysisRetryError):
    code = "INITIAL_ANALYSIS_RETRY_NOT_ALLOWED"
    status_code = 409


class InitialAnalysisRetryEvidenceError(InitialAnalysisRetryError):
    code = "INITIAL_EVIDENCE_INVALID"


class InitialAnalysisRetryPersistenceError(InitialAnalysisRetryError):
    code = "INITIAL_ANALYSIS_RETRY_PERSISTENCE_FAILED"
    status_code = 500


class InitialAnalysisRetryQueueError(InitialAnalysisRetryError):
    code = "INITIAL_ANALYSIS_RETRY_QUEUE_FAILED"
    status_code = 503


@dataclass(frozen=True, slots=True)
class InitialAnalysisRetryResult:
    analysis_request_id: uuid.UUID
    session_id: uuid.UUID
    analysis_type: AnalysisRequestV2Type
    request_status: AnalysisRequestV2Status
    session_status: TradeSessionV2Status
    created_at: datetime


class InitialAnalysisRetryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._lock_key: int | None = None
        self._session_lock: asyncio.Lock | None = None

    async def retry(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> InitialAnalysisRetryResult:
        await self._acquire_session_lock(session_id)
        try:
            trade_session = await self._load_owned_draft(user_id, session_id)
            request = await self._load_latest_request(session_id)
            await self._validate_evidence(session_id, request.id)

            if request.status not in {
                AnalysisRequestV2Status.FAILED,
                AnalysisRequestV2Status.PENDING,
            }:
                raise InitialAnalysisRetryNotAllowedError(
                    "Initial Analysis request is not retryable"
                )

            if request.status is AnalysisRequestV2Status.FAILED:
                request.status = AnalysisRequestV2Status.PENDING
                request.started_at = None
                request.completed_at = None
                request.error_code = None
                request.error_message = None
                request.raw_response = None
                request.processed_response = None

            trade_session.status = TradeSessionV2Status.ANALYZING
            try:
                await self._session.commit()
            except SQLAlchemyError as exc:
                await self._session.rollback()
                raise InitialAnalysisRetryPersistenceError(
                    "Initial Analysis retry status could not be persisted"
                ) from exc

            return InitialAnalysisRetryResult(
                analysis_request_id=request.id,
                session_id=trade_session.id,
                analysis_type=request.analysis_type,
                request_status=request.status,
                session_status=trade_session.status,
                created_at=request.created_at,
            )
        finally:
            await self._release_session_lock()

    async def _load_owned_draft(
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
            raise InitialAnalysisRetrySessionNotFoundError("Rebuild session was not found")
        if trade_session.status is not TradeSessionV2Status.DRAFT:
            raise InitialAnalysisRetrySessionStateError("Trade session is not a draft")
        return trade_session

    async def _load_latest_request(self, session_id: uuid.UUID) -> AnalysisRequestV2:
        request = await self._session.scalar(
            select(AnalysisRequestV2)
            .where(
                AnalysisRequestV2.session_id == session_id,
                AnalysisRequestV2.analysis_type == AnalysisRequestV2Type.INITIAL_ANALYSIS,
            )
            .order_by(desc(AnalysisRequestV2.created_at), desc(AnalysisRequestV2.id))
            .limit(1)
            .with_for_update()
        )
        if request is None:
            raise InitialAnalysisRetryRequestNotFoundError(
                "Initial Analysis request was not found"
            )
        return request

    async def _validate_evidence(self, session_id: uuid.UUID, request_id: uuid.UUID) -> None:
        evidence = list(
            (
                await self._session.scalars(
                    select(EvidenceUploadV2)
                    .where(EvidenceUploadV2.analysis_request_id == request_id)
                    .with_for_update()
                )
            ).all()
        )
        linked = [item for item in evidence if item.analysis_request_id == request_id]
        if any(item.session_id != session_id for item in linked):
            raise InitialAnalysisRetryEvidenceError("Initial evidence ownership mismatch")
        by_type: dict[EvidenceUploadV2Type, list[EvidenceUploadV2]] = {}
        for item in linked:
            by_type.setdefault(item.evidence_type, []).append(item)
        for evidence_type in _REQUIRED_EVIDENCE:
            items = by_type.get(evidence_type, [])
            if len(items) != 1 or items[0].observation_period is not None:
                raise InitialAnalysisRetryEvidenceError(
                    "Exactly one linked initial evidence record is required for each role"
                )
        if any(item.session_id != session_id for item in evidence):
            raise InitialAnalysisRetryEvidenceError("Initial evidence ownership mismatch")

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
