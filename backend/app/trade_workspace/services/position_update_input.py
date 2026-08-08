from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AppConfig
from app.storage import FileStorage, StorageError, create_file_storage
from app.trade_workspace.models.analysis_request import AnalysisRequestV2ObservationPeriod
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.position import PositionV2, PositionV2Status
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
from app.trade_workspace.services.eligibility import (
    open_position_session_is_eligible,
    single_open_position,
)

MAX_POSITION_UPDATE_INPUT_SIZE = 10 * 1024 * 1024
SUPPORTED_IMAGE_MIME_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})


class PositionUpdateInputError(Exception):
    code = "POSITION_UPDATE_INPUT_FAILED"
    status_code = 422


class PositionUpdateInputSessionNotFoundError(PositionUpdateInputError):
    code = "SESSION_NOT_FOUND"
    status_code = 404


class PositionUpdateInputNotAllowedError(PositionUpdateInputError):
    code = "POSITION_UPDATE_INPUT_NOT_ALLOWED"
    status_code = 409


class PositionUpdateInputValidationError(PositionUpdateInputError):
    code = "POSITION_UPDATE_INPUT_INVALID"
    status_code = 422


class PositionUpdateInputStorageError(PositionUpdateInputError):
    code = "POSITION_UPDATE_INPUT_STORAGE_FAILED"
    status_code = 500


class PositionUpdateInputPersistenceError(PositionUpdateInputError):
    code = "POSITION_UPDATE_INPUT_PERSISTENCE_FAILED"
    status_code = 500


@dataclass(frozen=True, slots=True)
class PositionUpdateInputResult:
    evidence_id: uuid.UUID
    session_id: uuid.UUID
    position_id: uuid.UUID
    evidence_type: EvidenceUploadV2Type
    original_filename: str
    mime_type: str
    size_bytes: int
    current_price: Decimal
    observation_period: AnalysisRequestV2ObservationPeriod
    observation_timestamp: datetime
    uploaded_at: datetime
    session_status: TradeSessionV2Status
    position_status: PositionV2Status


class PositionUpdateInputService:
    """Persist one explicit Position Update observation for one open position."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        storage: FileStorage | None = None,
        max_size_bytes: int = MAX_POSITION_UPDATE_INPUT_SIZE,
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
        broker_flow_original_filename: str | None = None,
        broker_flow_mime_type: str | None = None,
        broker_flow_content: bytes | None = None,
    ) -> PositionUpdateInputResult:
        await self._session.execute(
            select(func.pg_advisory_xact_lock(_session_lock_key(session_id)))
        )
        trade_session, position = await self._load_eligible_owner(user_id, session_id)
        self._validate(
            original_filename=original_filename,
            mime_type=mime_type,
            content=content,
            current_price=current_price,
            observation_timestamp=observation_timestamp,
            broker_flow_original_filename=broker_flow_original_filename,
            broker_flow_mime_type=broker_flow_mime_type,
            broker_flow_content=broker_flow_content,
        )

        stored_references: list[str] = []
        try:
            uploaded_at = datetime.now(timezone.utc)
            stored = self._storage.store(
                user_id=user_id,
                session_id=session_id,
                original_filename=original_filename,
                content=content,
            )
            stored_references.append(stored.file_reference)
            evidence = EvidenceUploadV2(
                session_id=session_id,
                evidence_type=EvidenceUploadV2Type.ORDERBOOK,
                analysis_request_id=None,
                observation_period=observation_period,
                current_price=current_price,
                observation_timestamp=observation_timestamp,
                file_path=stored.file_reference,
                original_filename=original_filename,
                mime_type=mime_type,
                size_bytes=stored.size_bytes,
                uploaded_at=uploaded_at,
            )
            records = [evidence]
            if broker_flow_content is not None:
                broker_stored = self._storage.store(
                    user_id=user_id,
                    session_id=session_id,
                    original_filename=broker_flow_original_filename or "",
                    content=broker_flow_content,
                )
                stored_references.append(broker_stored.file_reference)
                records.append(
                    EvidenceUploadV2(
                        session_id=session_id,
                        evidence_type=EvidenceUploadV2Type.BROKER_FLOW_1D,
                        analysis_request_id=None,
                        observation_period=observation_period,
                        current_price=current_price,
                        observation_timestamp=observation_timestamp,
                        file_path=broker_stored.file_reference,
                        original_filename=broker_flow_original_filename or "",
                        mime_type=broker_flow_mime_type or "",
                        size_bytes=broker_stored.size_bytes,
                        uploaded_at=uploaded_at,
                    )
                )
            self._session.add_all(records)
            await self._session.flush()
            await self._session.commit()
        except StorageError as exc:
            await self._rollback_and_cleanup(stored_references)
            raise PositionUpdateInputStorageError("Position Update input storage failed") from exc
        except (OSError, SQLAlchemyError) as exc:
            await self._rollback_and_cleanup(stored_references)
            raise PositionUpdateInputPersistenceError(
                "Position Update input could not be persisted"
            ) from exc
        except Exception:
            await self._rollback_and_cleanup(stored_references)
            raise

        return PositionUpdateInputResult(
            evidence_id=evidence.id,
            session_id=evidence.session_id,
            position_id=position.id,
            evidence_type=evidence.evidence_type,
            original_filename=evidence.original_filename,
            mime_type=evidence.mime_type,
            size_bytes=evidence.size_bytes,
            current_price=evidence.current_price,
            observation_period=evidence.observation_period,
            observation_timestamp=evidence.observation_timestamp,
            uploaded_at=evidence.uploaded_at,
            session_status=trade_session.status,
            position_status=position.status,
        )

    async def _load_eligible_owner(
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
            raise PositionUpdateInputSessionNotFoundError("Trade session not found")
        if not open_position_session_is_eligible(trade_session.status):
            raise PositionUpdateInputNotAllowedError(
                "Position Update input is only allowed for OPEN_POSITION sessions"
            )

        positions = list(
            (
                await self._session.scalars(
                    select(PositionV2).where(PositionV2.session_id == session_id).with_for_update()
                )
            ).all()
        )
        if len(positions) != 1:
            raise PositionUpdateInputNotAllowedError(
                "Exactly one position is required for Position Update input"
            )
        position = single_open_position(positions)
        if position is None:
            raise PositionUpdateInputNotAllowedError(
                "Position Update input requires an OPEN position"
            )
        return trade_session, position

    def _validate(
        self,
        *,
        original_filename: str,
        mime_type: str,
        content: bytes,
        current_price: Decimal,
        observation_timestamp: datetime,
        broker_flow_original_filename: str | None,
        broker_flow_mime_type: str | None,
        broker_flow_content: bytes | None,
    ) -> None:
        if not content:
            raise PositionUpdateInputValidationError("Orderbook file is empty")
        if mime_type not in SUPPORTED_IMAGE_MIME_TYPES:
            raise PositionUpdateInputValidationError("Orderbook MIME type is unsupported")
        if len(content) > self._max_size_bytes:
            raise PositionUpdateInputValidationError("Orderbook file is too large")
        if not original_filename:
            raise PositionUpdateInputValidationError("Orderbook filename is missing")
        if not current_price.is_finite() or current_price <= 0:
            raise PositionUpdateInputValidationError("Current price must be positive")
        decimal_places = max(0, -current_price.as_tuple().exponent)
        if decimal_places > 6 or current_price.adjusted() > 13:
            raise PositionUpdateInputValidationError(
                "Current price exceeds the approved precision"
            )
        if observation_timestamp.tzinfo is None or observation_timestamp.utcoffset() is None:
            raise PositionUpdateInputValidationError(
                "Observation timestamp must include a timezone"
            )
        broker_values = (
            broker_flow_original_filename,
            broker_flow_mime_type,
            broker_flow_content,
        )
        if any(value is not None for value in broker_values):
            if any(value is None for value in broker_values):
                raise PositionUpdateInputValidationError("Broker Flow file is incomplete")
            if not broker_flow_content:
                raise PositionUpdateInputValidationError("Broker Flow file is empty")
            if broker_flow_mime_type not in SUPPORTED_IMAGE_MIME_TYPES:
                raise PositionUpdateInputValidationError("Broker Flow MIME type is unsupported")
            if len(broker_flow_content) > self._max_size_bytes:
                raise PositionUpdateInputValidationError("Broker Flow file is too large")
            if not broker_flow_original_filename:
                raise PositionUpdateInputValidationError("Broker Flow filename is missing")

    async def _rollback_and_cleanup(self, references: Sequence[str]) -> None:
        await self._session.rollback()
        for reference in references:
            try:
                self._storage.delete(file_reference=reference)
            except (OSError, StorageError):
                continue


def _session_lock_key(session_id: uuid.UUID) -> int:
    return int.from_bytes(session_id.bytes[:8], byteorder="big", signed=True)
