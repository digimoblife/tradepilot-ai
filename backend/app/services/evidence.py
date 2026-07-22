"""Evidence Service (TP-0603).

Create, replace, list, deactivate, and query required evidence
for owned Trade Sessions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.evidence import (
    EvidenceUploadValidator,
)
from app.models.enums import AnalysisType, EvidenceStatus, EvidenceType
from app.models.evidence import Evidence
from app.repositories.evidence import EvidenceRepository
from app.repositories.trade_session import TradeSessionRepository
from app.services.context_rebuild import ContextRebuildReason, ContextRebuildService
from app.storage import LocalFileStorage, StoredFile

# ---------------------------------------------------------------------------
# Required-evidence mapping
# ---------------------------------------------------------------------------

_REQUIRED_EVIDENCE: dict[AnalysisType, tuple[EvidenceType, ...]] = {
    AnalysisType.INITIAL_ANALYSIS: (
        EvidenceType.ORDERBOOK_SCREENSHOT,
        EvidenceType.CHART_THREE_MONTH,
        EvidenceType.CHART_SIX_MONTH,
    ),
    AnalysisType.WATCHING_UPDATE: (),
    AnalysisType.OPEN_POSITION_UPDATE: (),
    AnalysisType.PARTIAL_EXIT_REVIEW: (),
    AnalysisType.CLOSING_ANALYSIS: (),
}

# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EvidenceResult:
    """Result of a create or replace evidence operation."""

    evidence: Evidence
    stored_file: StoredFile


@dataclass(frozen=True, slots=True)
class RequiredEvidenceResult:
    """Result of querying required evidence for an analysis type."""

    analysis_type: AnalysisType
    required_types: tuple[EvidenceType, ...]
    present_types: tuple[EvidenceType, ...]
    missing_types: tuple[EvidenceType, ...]
    complete: bool


# ---------------------------------------------------------------------------
# Stable errors
# ---------------------------------------------------------------------------


class EvidenceServiceError(Exception):
    """Base for evidence service errors."""

    code: str = "EVIDENCE_SERVICE_ERROR"

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class EvidenceNotFoundError(EvidenceServiceError):
    code: str = "EVIDENCE_NOT_FOUND_OR_NOT_OWNED"


class EvidenceSessionNotFoundError(EvidenceServiceError):
    code: str = "EVIDENCE_SESSION_NOT_FOUND_OR_NOT_OWNED"


class EvidenceReplacementInvalidError(EvidenceServiceError):
    code: str = "EVIDENCE_REPLACEMENT_INVALID"


class EvidenceAlreadyInactiveError(EvidenceServiceError):
    code: str = "EVIDENCE_ALREADY_INACTIVE"


class EvidenceRequiredTypeUnsupportedError(EvidenceServiceError):
    code: str = "EVIDENCE_REQUIRED_TYPE_UNSUPPORTED"


class EvidenceStorageFailedError(EvidenceServiceError):
    code: str = "EVIDENCE_STORAGE_FAILED"


class EvidenceDuplicateActiveError(EvidenceServiceError):
    code: str = "EVIDENCE_DUPLICATE_ACTIVE"


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class EvidenceService:
    """Evidence lifecycle operations for owned Trade Sessions."""

    def __init__(
        self,
        session: AsyncSession,
        storage_root: Path | None = None,
        max_upload_size_bytes: int | None = None,
    ) -> None:
        from app.config import AppConfig

        config = AppConfig()
        self._session = session
        self._session_repo = TradeSessionRepository(session)
        self._evidence_repo = EvidenceRepository(session)
        effective_max_size = (
            max_upload_size_bytes
            if max_upload_size_bytes is not None
            else config.max_upload_size_bytes
        )
        self._validator = EvidenceUploadValidator(
            max_upload_size_bytes=effective_max_size,
        )
        root = storage_root if storage_root is not None else Path(config.storage_root)
        self._storage = LocalFileStorage(root=root)

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        evidence_type: EvidenceType | str,
        content: bytes,
        original_filename: str,
        declared_mime_type: str | None,
        market_timestamp: datetime | None = None,
        caption: str | None = None,
    ) -> EvidenceResult:
        ts = await self._session_repo.get_by_id_for_user(session_id, owner_id)
        if ts is None:
            raise EvidenceSessionNotFoundError(
                code="EVIDENCE_SESSION_NOT_FOUND_OR_NOT_OWNED",
                message="Trade Session not found or not owned",
            )

        validated_type = _normalize_type(evidence_type)

        existing = await self._evidence_repo.get_latest_active_by_type_for_user(
            session_id,
            owner_id,
            validated_type.value,
        )
        if existing is not None:
            raise EvidenceDuplicateActiveError(
                message=(
                    f"Active evidence of type {validated_type.value} already exists. "
                    "Use replace to update it."
                ),
            )

        return await self._store_evidence(
            session_id=session_id,
            owner_id=owner_id,
            evidence_type=validated_type,
            content=content,
            original_filename=original_filename,
            declared_mime_type=declared_mime_type,
            market_timestamp=market_timestamp,
            caption=caption,
            supersedes_id=None,
        )

    # ------------------------------------------------------------------
    # Replace
    # ------------------------------------------------------------------

    async def replace(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        evidence_type: EvidenceType | str,
        content: bytes,
        original_filename: str,
        declared_mime_type: str | None,
        market_timestamp: datetime | None = None,
        caption: str | None = None,
    ) -> EvidenceResult:
        ts = await self._session_repo.get_by_id_for_user(session_id, owner_id)
        if ts is None:
            raise EvidenceSessionNotFoundError(
                code="EVIDENCE_SESSION_NOT_FOUND_OR_NOT_OWNED",
                message="Trade Session not found or not owned",
            )

        validated_type = _normalize_type(evidence_type)

        old = await self._evidence_repo.get_latest_active_by_type_for_user(
            session_id,
            owner_id,
            validated_type.value,
        )

        if old is not None and old.evidence_status != EvidenceStatus.AVAILABLE:
            raise EvidenceReplacementInvalidError(
                message=f"Cannot replace evidence in status {old.evidence_status.value}",
            )

        result = await self._store_evidence(
            session_id=session_id,
            owner_id=owner_id,
            evidence_type=validated_type,
            content=content,
            original_filename=original_filename,
            declared_mime_type=declared_mime_type,
            market_timestamp=market_timestamp,
            caption=caption,
            supersedes_id=old.id if old is not None else None,
        )

        if old is not None:
            old.evidence_status = EvidenceStatus.SUPERSEDED
            self._session.add(old)

        await self._session.flush()

        rebuild = ContextRebuildService(self._session)
        await rebuild.rebuild_after_material_event(
            session_id=session_id,
            owner_id=owner_id,
            reason=ContextRebuildReason.EVIDENCE_REPLACED,
            source_id=result.evidence.id,
        )

        return result

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    async def list_for_session(
        self,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        *,
        limit: int | None = None,
    ) -> Sequence[Evidence]:
        ts = await self._session_repo.get_by_id_for_user(session_id, owner_id)
        if ts is None:
            raise EvidenceSessionNotFoundError(
                code="EVIDENCE_SESSION_NOT_FOUND_OR_NOT_OWNED",
                message="Trade Session not found or not owned",
            )
        return await self._evidence_repo.list_for_session_for_user(
            session_id,
            owner_id,
            limit=limit,
        )

    async def list_active_for_session(
        self,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        *,
        limit: int | None = None,
    ) -> Sequence[Evidence]:
        ts = await self._session_repo.get_by_id_for_user(session_id, owner_id)
        if ts is None:
            raise EvidenceSessionNotFoundError(
                code="EVIDENCE_SESSION_NOT_FOUND_OR_NOT_OWNED",
                message="Trade Session not found or not owned",
            )
        return await self._evidence_repo.list_active_for_session_for_user(
            session_id,
            owner_id,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Deactivate
    # ------------------------------------------------------------------

    async def deactivate(
        self,
        evidence_id: uuid.UUID,
        owner_id: uuid.UUID,
        *,
        reason: str = "Manually deactivated",
    ) -> None:
        ev = await self._evidence_repo.get_by_id_for_user(evidence_id, owner_id)
        if ev is None:
            raise EvidenceNotFoundError(
                code="EVIDENCE_NOT_FOUND_OR_NOT_OWNED",
                message="Evidence not found or not owned",
            )
        if ev.evidence_status != EvidenceStatus.AVAILABLE or ev.deleted_at is not None:
            raise EvidenceAlreadyInactiveError(
                message=f"Evidence is already in status {ev.evidence_status.value}",
            )
        ev.evidence_status = EvidenceStatus.EXCLUDED
        ev.exclusion_reason = reason
        ev.excluded_at = datetime.now(timezone.utc)
        self._session.add(ev)
        await self._session.flush()

    # ------------------------------------------------------------------
    # Required evidence
    # ------------------------------------------------------------------

    async def get_required_evidence(
        self,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        analysis_type: AnalysisType | str,
    ) -> RequiredEvidenceResult:
        if isinstance(analysis_type, str):
            try:
                analysis_type = AnalysisType(analysis_type)
            except ValueError:
                raise EvidenceRequiredTypeUnsupportedError(
                    message=f"Unsupported analysis type: {analysis_type}",
                )

        required = _REQUIRED_EVIDENCE.get(analysis_type)
        if required is None:
            raise EvidenceRequiredTypeUnsupportedError(
                message=f"Unsupported analysis type: {analysis_type.value}",
            )

        active = await self._evidence_repo.list_active_for_session_for_user(
            session_id,
            owner_id,
        )
        present_types = tuple(et for et in required if any(e.evidence_type == et for e in active))
        missing_types = tuple(et for et in required if et not in present_types)
        complete = len(missing_types) == 0

        return RequiredEvidenceResult(
            analysis_type=analysis_type,
            required_types=required,
            present_types=present_types,
            missing_types=missing_types,
            complete=complete,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _store_evidence(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        evidence_type: EvidenceType,
        content: bytes,
        original_filename: str,
        declared_mime_type: str | None,
        market_timestamp: datetime | None,
        caption: str | None,
        supersedes_id: uuid.UUID | None,
    ) -> EvidenceResult:
        validated = self._validator.validate(
            content=content,
            original_filename=original_filename,
            declared_mime_type=declared_mime_type,
            evidence_type=evidence_type.value,
        )

        stored = self._storage.store(
            user_id=owner_id,
            session_id=session_id,
            original_filename=original_filename,
            content=content,
        )

        try:
            ev = Evidence(
                id=uuid.uuid4(),
                session_id=session_id,
                owner_id=owner_id,
                evidence_type=evidence_type,
                evidence_status=EvidenceStatus.AVAILABLE,
                original_filename=original_filename,
                storage_object_key=stored.file_reference,
                mime_type=validated.detected_mime_type or None,
                file_size_bytes=validated.size_bytes,
                checksum_sha256=validated.checksum_sha256,
                market_timestamp=market_timestamp,
                caption=caption,
                supersedes_evidence_id=supersedes_id,
            )
            await self._evidence_repo.add(ev)
        except Exception:
            self._storage.delete(file_reference=stored.file_reference)
            raise

        return EvidenceResult(evidence=ev, stored_file=stored)


def _normalize_type(evidence_type: EvidenceType | str) -> EvidenceType:
    if isinstance(evidence_type, EvidenceType):
        return evidence_type
    try:
        return EvidenceType(evidence_type)
    except ValueError:
        raise EvidenceServiceError(
            code="EVIDENCE_TYPE_UNSUPPORTED",
            message=f"Unrecognised evidence type: {evidence_type}",
        )
