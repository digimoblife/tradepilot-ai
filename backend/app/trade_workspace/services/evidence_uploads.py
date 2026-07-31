from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AppConfig
from app.storage import FileStorage, StorageError, create_file_storage
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status

MAX_INITIAL_EVIDENCE_SIZE = 10 * 1024 * 1024
SUPPORTED_IMAGE_MIME_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})
INITIAL_EVIDENCE_TYPES = (
    EvidenceUploadV2Type.ORDERBOOK,
    EvidenceUploadV2Type.CHART_3_MONTH,
    EvidenceUploadV2Type.CHART_6_MONTH,
)


class InitialEvidenceUploadError(Exception):
    code = "INITIAL_EVIDENCE_UPLOAD_FAILED"
    status_code = 422


class InitialEvidenceSessionNotFoundError(InitialEvidenceUploadError):
    code = "SESSION_NOT_FOUND"
    status_code = 404


class InitialEvidenceSessionIneligibleError(InitialEvidenceUploadError):
    code = "SESSION_NOT_ELIGIBLE"
    status_code = 409


class InitialEvidenceDuplicateError(InitialEvidenceUploadError):
    code = "INITIAL_EVIDENCE_EXISTS"
    status_code = 409


class InitialEvidenceFileError(InitialEvidenceUploadError):
    code = "INITIAL_EVIDENCE_INVALID_FILE"
    status_code = 422


class InitialEvidenceStorageError(InitialEvidenceUploadError):
    code = "INITIAL_EVIDENCE_STORAGE_FAILED"
    status_code = 500


class InitialEvidencePersistenceError(InitialEvidenceUploadError):
    code = "INITIAL_EVIDENCE_PERSISTENCE_FAILED"
    status_code = 500


@dataclass(frozen=True, slots=True)
class InitialEvidenceInput:
    evidence_type: EvidenceUploadV2Type
    original_filename: str
    mime_type: str
    content: bytes


class InitialEvidenceUploadService:
    """Atomically store and persist one rebuild initial-evidence set."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        storage: FileStorage | None = None,
        max_size_bytes: int = MAX_INITIAL_EVIDENCE_SIZE,
    ) -> None:
        self._session = session
        self._storage = storage or create_file_storage(AppConfig())
        self._max_size_bytes = max_size_bytes

    async def upload(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        files: Sequence[InitialEvidenceInput],
    ) -> list[EvidenceUploadV2]:
        trade_session = await self._load_owned_session(user_id, session_id)
        await self._reject_duplicate(session_id)
        self._validate_inputs(files)

        stored_references: list[str] = []
        records: list[EvidenceUploadV2] = []
        try:
            for item in files:
                stored = self._storage.store(
                    user_id=user_id,
                    session_id=session_id,
                    original_filename=item.original_filename,
                    content=item.content,
                )
                stored_references.append(stored.file_reference)
                records.append(
                    EvidenceUploadV2(
                        session_id=trade_session.id,
                        evidence_type=item.evidence_type,
                        analysis_request_id=None,
                        observation_period=None,
                        file_path=stored.file_reference,
                        original_filename=item.original_filename,
                        mime_type=item.mime_type,
                        size_bytes=stored.size_bytes,
                    )
                )
            self._session.add_all(records)
            await self._session.flush()
            await self._session.commit()
        except StorageError as exc:
            await self._rollback_and_cleanup(stored_references)
            raise InitialEvidenceStorageError("Initial evidence storage failed") from exc
        except (OSError, SQLAlchemyError) as exc:
            await self._rollback_and_cleanup(stored_references)
            raise InitialEvidencePersistenceError(
                "Initial evidence could not be persisted"
            ) from exc
        except Exception:
            await self._rollback_and_cleanup(stored_references)
            raise
        return records

    async def get_initial_evidence(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> list[EvidenceUploadV2]:
        trade_session = await self._session.scalar(
            select(TradeSessionV2).where(
                TradeSessionV2.id == session_id,
                TradeSessionV2.user_id == user_id,
            )
        )
        if trade_session is None:
            raise InitialEvidenceSessionNotFoundError("Trade session not found")

        records = await self._session.scalars(
            select(EvidenceUploadV2)
            .where(
                EvidenceUploadV2.session_id == session_id,
                EvidenceUploadV2.evidence_type.in_(INITIAL_EVIDENCE_TYPES),
                EvidenceUploadV2.observation_period.is_(None),
            )
            .order_by(EvidenceUploadV2.uploaded_at.asc())
        )
        return list(records.all())

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
            raise InitialEvidenceSessionNotFoundError("Trade session not found")
        if trade_session.status is not TradeSessionV2Status.DRAFT:
            raise InitialEvidenceSessionIneligibleError("Trade session is not eligible")
        return trade_session

    async def _reject_duplicate(self, session_id: uuid.UUID) -> None:
        existing = await self._session.scalar(
            select(EvidenceUploadV2)
            .where(
                EvidenceUploadV2.session_id == session_id,
                EvidenceUploadV2.evidence_type.in_(INITIAL_EVIDENCE_TYPES),
                EvidenceUploadV2.analysis_request_id.is_(None),
                EvidenceUploadV2.observation_period.is_(None),
            )
            .limit(1)
        )
        if existing is not None:
            raise InitialEvidenceDuplicateError("Initial evidence already exists")

    def _validate_inputs(self, files: Sequence[InitialEvidenceInput]) -> None:
        if len(files) != len(INITIAL_EVIDENCE_TYPES):
            raise InitialEvidenceFileError("Exactly three initial evidence files are required")
        if tuple(item.evidence_type for item in files) != INITIAL_EVIDENCE_TYPES:
            raise InitialEvidenceFileError("Initial evidence roles are invalid")
        for item in files:
            if not item.content:
                raise InitialEvidenceFileError("Initial evidence file is empty")
            if item.mime_type not in SUPPORTED_IMAGE_MIME_TYPES:
                raise InitialEvidenceFileError("Initial evidence MIME type is unsupported")
            if len(item.content) > self._max_size_bytes:
                raise InitialEvidenceFileError("Initial evidence file is too large")
            if not item.original_filename:
                raise InitialEvidenceFileError("Initial evidence filename is missing")

    async def _rollback_and_cleanup(self, references: Sequence[str]) -> None:
        await self._session.rollback()
        for reference in references:
            try:
                self._storage.delete(file_reference=reference)
            except (OSError, StorageError):
                continue
