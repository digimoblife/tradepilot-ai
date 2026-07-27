from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AnalysisType, EvidenceBatchStatus
from app.models.evidence_batch import EvidenceBatch
from app.repositories.evidence_batch import EvidenceBatchRepository
from app.repositories.trade_session import TradeSessionRepository

IMMUTABLE_BATCH_STATUSES = frozenset(
    {
        EvidenceBatchStatus.READY,
        EvidenceBatchStatus.PROCESSING,
        EvidenceBatchStatus.FROZEN,
        EvidenceBatchStatus.FAILED,
    }
)


@dataclass(frozen=True, slots=True)
class EvidenceBatchSummary:
    id: uuid.UUID
    session_id: uuid.UUID
    analysis_type: str
    status: str
    sequence_number: int
    label: str | None
    created_at: datetime
    ready_at: datetime | None
    processing_at: datetime | None
    frozen_at: datetime | None
    failed_at: datetime | None


class EvidenceBatchServiceError(Exception):
    code = "EVIDENCE_BATCH_SERVICE_ERROR"

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class EvidenceBatchSessionNotFoundError(EvidenceBatchServiceError):
    code = "EVIDENCE_BATCH_SESSION_NOT_FOUND"


class EvidenceBatchImmutableError(EvidenceBatchServiceError):
    code = "EVIDENCE_BATCH_IMMUTABLE"


class EvidenceBatchInvalidStateError(EvidenceBatchServiceError):
    code = "EVIDENCE_BATCH_INVALID_STATE"


class EvidenceBatchNotFoundError(EvidenceBatchServiceError):
    code = "EVIDENCE_BATCH_NOT_FOUND"


class EvidenceBatchService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = EvidenceBatchRepository(session)
        self._session_repo = TradeSessionRepository(session)

    async def get_or_create_current_draft(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        analysis_type: AnalysisType = AnalysisType.INITIAL_ANALYSIS,
    ) -> EvidenceBatch:
        ts = await self._session_repo.get_by_id_for_user_for_update(session_id, owner_id)
        if ts is None:
            raise EvidenceBatchSessionNotFoundError(
                message="Trade Session not found or not owned"
            )

        latest_draft = await self._repo.get_latest_by_status(
            session_id,
            owner_id,
            analysis_type,
            EvidenceBatchStatus.DRAFT,
            for_update=True,
        )
        if latest_draft is not None:
            return latest_draft

        sequence = await self._repo.next_sequence(session_id, analysis_type)
        batch = EvidenceBatch(
            id=uuid.uuid4(),
            session_id=session_id,
            owner_id=owner_id,
            analysis_type=analysis_type,
            status=EvidenceBatchStatus.DRAFT,
            sequence_number=sequence,
            label=f"{analysis_type.value.replace('_', ' ').title()} Batch {sequence}",
        )
        return await self._repo.add(batch)

    async def get_current_draft(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        analysis_type: AnalysisType = AnalysisType.INITIAL_ANALYSIS,
    ) -> EvidenceBatch | None:
        return await self._repo.get_latest_by_status(
            session_id,
            owner_id,
            analysis_type,
            EvidenceBatchStatus.DRAFT,
        )

    async def get_ready_for_processing(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        analysis_type: AnalysisType = AnalysisType.INITIAL_ANALYSIS,
    ) -> EvidenceBatch | None:
        return await self._repo.get_latest_by_status(
            session_id,
            owner_id,
            analysis_type,
            EvidenceBatchStatus.READY,
            for_update=True,
        )

    async def get_latest_for_session(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        analysis_type: AnalysisType = AnalysisType.INITIAL_ANALYSIS,
    ) -> EvidenceBatch | None:
        return await self._repo.get_latest_for_session(
            session_id,
            owner_id,
            analysis_type,
        )

    async def mark_ready(self, batch: EvidenceBatch, *, now: datetime | None = None) -> None:
        if batch.status != EvidenceBatchStatus.DRAFT:
            raise EvidenceBatchInvalidStateError(
                message=f"Cannot mark batch {batch.id} ready from {batch.status.value}"
            )
        batch.status = EvidenceBatchStatus.READY
        batch.ready_at = now or datetime.now(timezone.utc)
        await self._session.flush()

    async def mark_processing(self, batch: EvidenceBatch, *, now: datetime | None = None) -> None:
        if batch.status != EvidenceBatchStatus.READY:
            raise EvidenceBatchInvalidStateError(
                message=f"Cannot process batch {batch.id} from {batch.status.value}"
            )
        batch.status = EvidenceBatchStatus.PROCESSING
        batch.processing_at = now or datetime.now(timezone.utc)
        await self._session.flush()

    async def freeze(self, batch_id: uuid.UUID | None, *, now: datetime | None = None) -> None:
        if batch_id is None:
            return
        batch = await self._session.get(EvidenceBatch, batch_id)
        if batch is None:
            return
        if batch.status != EvidenceBatchStatus.PROCESSING:
            raise EvidenceBatchInvalidStateError(
                message=f"Cannot freeze batch {batch.id} from {batch.status.value}"
            )
        batch.status = EvidenceBatchStatus.FROZEN
        batch.frozen_at = now or datetime.now(timezone.utc)
        await self._session.flush()

    async def fail(self, batch_id: uuid.UUID | None, *, now: datetime | None = None) -> None:
        if batch_id is None:
            return
        batch = await self._session.get(EvidenceBatch, batch_id)
        if batch is None:
            return
        if batch.status not in {EvidenceBatchStatus.PROCESSING, EvidenceBatchStatus.READY}:
            return
        batch.status = EvidenceBatchStatus.FAILED
        batch.failed_at = now or datetime.now(timezone.utc)
        await self._session.flush()

    async def assert_mutable(self, batch_id: uuid.UUID | None) -> None:
        if batch_id is None:
            return
        batch = await self._session.get(EvidenceBatch, batch_id)
        if batch is None:
            raise EvidenceBatchNotFoundError(message="Evidence Batch not found")
        if batch.status in IMMUTABLE_BATCH_STATUSES:
            raise EvidenceBatchImmutableError(
                message=f"Evidence Batch {batch.id} is {batch.status.value}"
            )

    async def list_for_session(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> Sequence[EvidenceBatch]:
        return await self._repo.list_for_session(session_id, owner_id)
