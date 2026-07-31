from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AppConfig
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2ObservationPeriod,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status

DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite"
_ACTIVE_STATUSES = (
    AnalysisRequestV2Status.PENDING,
    AnalysisRequestV2Status.PROCESSING,
)


class AnalysisRequestServiceError(Exception):
    """Base error for rebuild analysis request creation."""


class SessionNotFoundError(AnalysisRequestServiceError):
    pass


class SessionOwnershipMismatchError(AnalysisRequestServiceError):
    pass


class UnsupportedAnalysisTypeError(AnalysisRequestServiceError):
    pass


class EvidenceNotFoundError(AnalysisRequestServiceError):
    pass


class EvidenceOwnershipMismatchError(AnalysisRequestServiceError):
    pass


class EvidenceAlreadyAssignedError(AnalysisRequestServiceError):
    pass


class DuplicateActiveRequestError(AnalysisRequestServiceError):
    pass


class PersistenceError(AnalysisRequestServiceError):
    pass


class QueueSubmissionError(AnalysisRequestServiceError):
    pass


@dataclass(frozen=True, slots=True)
class AnalysisRequestServiceResult:
    request_id: uuid.UUID
    analysis_type: AnalysisRequestV2Type
    status: AnalysisRequestV2Status
    provider: str
    model: str


class AnalysisRequestQueueService:
    """Create one rebuild request with PENDING status, assign evidence, transition session to ANALYZING, and commit atomically."""

    def __init__(
        self,
        session: AsyncSession,
        queue: object = None,
        config: AppConfig | None = None,
    ) -> None:
        self._session = session
        self._config = config or AppConfig()

    async def submit(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        analysis_type: AnalysisRequestV2Type | str,
        prompt_version: str,
        input_snapshot: Mapping[str, object],
        current_price: Decimal | None = None,
        observation_period: AnalysisRequestV2ObservationPeriod | None = None,
        observation_at: datetime | None = None,
        evidence_ids: Sequence[uuid.UUID] | None = None,
    ) -> AnalysisRequestServiceResult:
        resolved_type = _resolve_analysis_type(analysis_type)
        trade_session = await self._load_owned_session(user_id, session_id)

        evidence = await self._load_selected_evidence(
            session_id=session_id,
            evidence_ids=evidence_ids or (),
        )
        await self._reject_duplicate(session_id=session_id, analysis_type=resolved_type)

        model = str(self._config.gemini_model or "").strip() or DEFAULT_GEMINI_MODEL
        request = AnalysisRequestV2(
            session_id=session_id,
            analysis_type=resolved_type,
            observation_period=(
                observation_period
                if resolved_type is not AnalysisRequestV2Type.INITIAL_ANALYSIS
                else None
            ),
            current_price=(
                current_price
                if resolved_type is not AnalysisRequestV2Type.INITIAL_ANALYSIS
                else None
            ),
            observation_at=(
                observation_at
                if resolved_type is not AnalysisRequestV2Type.INITIAL_ANALYSIS
                else None
            ),
            status=AnalysisRequestV2Status.PENDING,
            provider="gemini",
            model=model,
            prompt_version=prompt_version,
            input_snapshot=dict(input_snapshot),
            raw_response=None,
            processed_response=None,
            error_code=None,
            error_message=None,
            started_at=None,
            completed_at=None,
        )

        try:
            self._session.add(request)
            await self._session.flush()
            for item in evidence:
                item.analysis_request_id = request.id
            await self._session.flush()
        except SQLAlchemyError as exc:
            raise PersistenceError("Rebuild analysis request could not be persisted") from exc

        return AnalysisRequestServiceResult(
            request_id=request.id,
            analysis_type=request.analysis_type,
            status=request.status,
            provider=request.provider,
            model=request.model,
        )

    async def _load_owned_session(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> TradeSessionV2:
        trade_session = await self._session.scalar(
            select(TradeSessionV2)
            .where(TradeSessionV2.id == session_id)
            .with_for_update()
        )
        if trade_session is None:
            raise SessionNotFoundError("Rebuild session was not found")
        if trade_session.user_id != user_id:
            raise SessionOwnershipMismatchError("Rebuild session ownership mismatch")
        return trade_session

    async def _load_selected_evidence(
        self,
        *,
        session_id: uuid.UUID,
        evidence_ids: Sequence[uuid.UUID],
    ) -> list[EvidenceUploadV2]:
        unique_ids = tuple(dict.fromkeys(evidence_ids))
        if not unique_ids:
            return []
        evidence = list(
            (
                await self._session.scalars(
                    select(EvidenceUploadV2)
                    .where(EvidenceUploadV2.id.in_(unique_ids))
                    .with_for_update()
                )
            ).all()
        )
        found_ids = {item.id for item in evidence}
        missing_ids = [item_id for item_id in unique_ids if item_id not in found_ids]
        if missing_ids:
            raise EvidenceNotFoundError(
                "One or more selected rebuild evidence records were not found"
            )
        if any(item.session_id != session_id for item in evidence):
            raise EvidenceOwnershipMismatchError("Selected evidence ownership mismatch")
        if any(item.analysis_request_id is not None for item in evidence):
            raise EvidenceAlreadyAssignedError(
                "Selected evidence is already assigned to a request"
            )
        return evidence

    async def _reject_duplicate(
        self,
        *,
        session_id: uuid.UUID,
        analysis_type: AnalysisRequestV2Type,
    ) -> None:
        existing = await self._session.scalar(
            select(AnalysisRequestV2)
            .where(
                AnalysisRequestV2.session_id == session_id,
                AnalysisRequestV2.analysis_type == analysis_type,
                AnalysisRequestV2.status.in_(_ACTIVE_STATUSES),
            )
            .limit(1)
        )
        if existing is not None:
            raise DuplicateActiveRequestError("An active rebuild request already exists")


def _resolve_analysis_type(
    analysis_type: AnalysisRequestV2Type | str,
) -> AnalysisRequestV2Type:
    try:
        return AnalysisRequestV2Type(analysis_type)
    except (TypeError, ValueError) as exc:
        raise UnsupportedAnalysisTypeError(
            f"Unsupported rebuild analysis type: {analysis_type!r}"
        ) from exc
