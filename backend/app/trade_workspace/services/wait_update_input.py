from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AppConfig
from app.storage import FileStorage, StorageError, create_file_storage
from app.trade_workspace.models.analysis_request import AnalysisRequestV2ObservationPeriod
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
from app.trade_workspace.services.eligibility import wait_update_session_is_eligible

MAX_WAIT_UPDATE_INPUT_SIZE = 10 * 1024 * 1024
SUPPORTED_IMAGE_MIME_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})


class WaitUpdateInputError(Exception):
    code = "WAIT_UPDATE_INPUT_FAILED"
    status_code = 422


class WaitUpdateInputSessionNotFoundError(WaitUpdateInputError):
    code = "SESSION_NOT_FOUND"
    status_code = 404


class WaitUpdateInputNotAllowedError(WaitUpdateInputError):
    code = "WAIT_UPDATE_INPUT_NOT_ALLOWED"
    status_code = 409


class WaitUpdateInputValidationError(WaitUpdateInputError):
    code = "WAIT_UPDATE_INPUT_INVALID"
    status_code = 422


class WaitUpdateInputStorageError(WaitUpdateInputError):
    code = "WAIT_UPDATE_INPUT_STORAGE_FAILED"
    status_code = 500


class WaitUpdateInputPersistenceError(WaitUpdateInputError):
    code = "WAIT_UPDATE_INPUT_PERSISTENCE_FAILED"
    status_code = 500


@dataclass(frozen=True, slots=True)
class WaitUpdateInputResult:
    evidence_id: uuid.UUID
    session_id: uuid.UUID
    evidence_type: EvidenceUploadV2Type
    original_filename: str
    mime_type: str
    size_bytes: int
    current_price: Decimal
    observation_period: AnalysisRequestV2ObservationPeriod
    observation_timestamp: datetime
    uploaded_at: datetime
    session_status: TradeSessionV2Status


class WaitUpdateInputService:
    """Persist one explicit WAIT Update observation for one owned session."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        storage: FileStorage | None = None,
        max_size_bytes: int = MAX_WAIT_UPDATE_INPUT_SIZE,
    ) -> None:
        self._session = session
        self._storage = storage or create_file_storage(AppConfig())
        self._max_size_bytes = max_size_bytes

    async def submit(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        original_filename: str,
        mime_type: str,
        content: bytes,
        current_price: Decimal,
        observation_period: AnalysisRequestV2ObservationPeriod,
        observation_timestamp: datetime,
    ) -> WaitUpdateInputResult:
        trade_session = await self._load_owned_waiting_session(user_id, session_id)
        self._validate(
            original_filename=original_filename,
            mime_type=mime_type,
            content=content,
            current_price=current_price,
            observation_timestamp=observation_timestamp,
        )
        stored_reference: str | None = None
        try:
            stored = self._storage.store(
                user_id=user_id,
                session_id=session_id,
                original_filename=original_filename,
                content=content,
            )
            stored_reference = stored.file_reference
            evidence = EvidenceUploadV2(
                session_id=trade_session.id,
                evidence_type=EvidenceUploadV2Type.ORDERBOOK,
                analysis_request_id=None,
                observation_period=observation_period,
                current_price=current_price,
                observation_timestamp=observation_timestamp,
                file_path=stored.file_reference,
                original_filename=original_filename,
                mime_type=mime_type,
                size_bytes=stored.size_bytes,
            )
            self._session.add(evidence)
            await self._session.flush()
            await self._session.commit()
        except StorageError as exc:
            await self._rollback_and_cleanup(stored_reference)
            raise WaitUpdateInputStorageError("WAIT Update input storage failed") from exc
        except (OSError, SQLAlchemyError) as exc:
            await self._rollback_and_cleanup(stored_reference)
            raise WaitUpdateInputPersistenceError(
                "WAIT Update input could not be persisted"
            ) from exc
        except Exception:
            await self._rollback_and_cleanup(stored_reference)
            raise
        return WaitUpdateInputResult(
            evidence_id=evidence.id,
            session_id=evidence.session_id,
            evidence_type=evidence.evidence_type,
            original_filename=evidence.original_filename,
            mime_type=evidence.mime_type,
            size_bytes=evidence.size_bytes,
            current_price=evidence.current_price,
            observation_period=evidence.observation_period,
            observation_timestamp=evidence.observation_timestamp,
            uploaded_at=evidence.uploaded_at,
            session_status=trade_session.status,
        )

    async def _load_owned_waiting_session(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> TradeSessionV2:
        trade_session = await self._session.scalar(
            select(TradeSessionV2)
            .where(
                TradeSessionV2.id == session_id,
                TradeSessionV2.user_id == user_id,
            )
            .with_for_update()
        )
        if trade_session is None:
            raise WaitUpdateInputSessionNotFoundError("Trade session not found")
        if not wait_update_session_is_eligible(trade_session.status):
            raise WaitUpdateInputNotAllowedError(
                "WAIT Update input is only allowed for WAITING sessions"
            )
        return trade_session

    def _validate(
        self,
        *,
        original_filename: str,
        mime_type: str,
        content: bytes,
        current_price: Decimal,
        observation_timestamp: datetime,
    ) -> None:
        if not content:
            raise WaitUpdateInputValidationError("Orderbook file is empty")
        if mime_type not in SUPPORTED_IMAGE_MIME_TYPES:
            raise WaitUpdateInputValidationError("Orderbook MIME type is unsupported")
        if len(content) > self._max_size_bytes:
            raise WaitUpdateInputValidationError("Orderbook file is too large")
        if not original_filename:
            raise WaitUpdateInputValidationError("Orderbook filename is missing")
        if current_price <= 0:
            raise WaitUpdateInputValidationError("Current price must be positive")
        decimal_places = max(0, -current_price.as_tuple().exponent)
        if decimal_places > 6 or current_price.adjusted() > 13:
            raise WaitUpdateInputValidationError(
                "Current price exceeds the approved precision"
            )
        if observation_timestamp.tzinfo is None or observation_timestamp.utcoffset() is None:
            raise WaitUpdateInputValidationError(
                "Observation timestamp must include a timezone"
            )

    async def _rollback_and_cleanup(self, reference: str | None) -> None:
        await self._session.rollback()
        if reference is not None:
            try:
                self._storage.delete(file_reference=reference)
            except (OSError, StorageError):
                pass
