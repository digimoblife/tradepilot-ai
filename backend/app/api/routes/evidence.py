"""Evidence API routes (TP-1003)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import NoReturn

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.api.schemas.evidence import (
    EvidenceListResponse,
    EvidenceResponse,
)
from app.auth import AuthenticatedUser
from app.database.session import get_db_session
from app.evidence.validation import (
    EvidenceValidationError,
)
from app.models.evidence import Evidence as EvidenceModel
from app.services.evidence import (
    EvidenceNotFoundError,
    EvidenceService,
    EvidenceServiceError,
    EvidenceSessionNotFoundError,
)

session_router = APIRouter(prefix="/api/trade-sessions", tags=["evidence"])
evidence_router = APIRouter(prefix="/api/evidence", tags=["evidence"])


# ---------------------------------------------------------------------------
# Indonesian invalid-file messages
# ---------------------------------------------------------------------------

_INVALID_FILE_MESSAGES: dict[str, str] = {
    "EVIDENCE_EMPTY_FILE": "Berkas kosong. Silakan unggah berkas yang valid.",
    "EVIDENCE_FILE_TOO_LARGE": ("Ukuran berkas terlalu besar. Maksimum 10 MB."),
    "EVIDENCE_TYPE_UNSUPPORTED": ("Tipe bukti tidak dikenal. Silakan pilih tipe yang tersedia."),
    "EVIDENCE_MIME_UNSUPPORTED": ("Format file tidak didukung. Gunakan PNG, JPEG, atau WebP."),
    "EVIDENCE_MIME_MISMATCH": ("Format berkas tidak sesuai dengan tipe yang dideklarasikan."),
    "EVIDENCE_IMAGE_INVALID": ("Berkas gambar tidak dapat dibaca atau rusak."),
    "EVIDENCE_DIMENSIONS_INVALID": ("Dimensi gambar tidak valid."),
}


def _evidence_error(code: str, status: int = 422) -> NoReturn:
    from fastapi import HTTPException

    msg = _INVALID_FILE_MESSAGES.get(code, "Terjadi kesalahan saat memproses berkas.")
    raise HTTPException(status_code=status, detail={"code": code, "message": msg})


def _evidence_to_response(ev: EvidenceModel) -> EvidenceResponse:
    return EvidenceResponse(
        id=str(ev.id),
        session_id=str(ev.session_id),
        evidence_type=ev.evidence_type.value,
        status=ev.evidence_status.value,
        original_filename=ev.original_filename,
        mime_type=ev.mime_type,
        file_size_bytes=ev.file_size_bytes,
        checksum_sha256=ev.checksum_sha256,
        market_timestamp=ev.market_timestamp,
        uploaded_at=ev.uploaded_at,
        caption=ev.caption,
        supersedes_evidence_id=(
            str(ev.supersedes_evidence_id) if ev.supersedes_evidence_id else None
        ),
    )


# ---------------------------------------------------------------------------
# POST /api/trade-sessions/{session_id}/evidence
# ---------------------------------------------------------------------------


@session_router.post("/{session_id}/evidence", response_model=EvidenceResponse, status_code=201)
async def upload_evidence(
    session_id: uuid.UUID,
    file: UploadFile = File(...),
    evidence_type: str = Form(...),
    market_timestamp: str | None = Form(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> EvidenceResponse:
    content = await file.read()
    filename = file.filename or "upload"

    parsed_market_ts: datetime | None = None
    if market_timestamp:
        try:
            parsed_market_ts = datetime.fromisoformat(market_timestamp)
        except (ValueError, TypeError):
            return _evidence_error("EVIDENCE_MIME_UNSUPPORTED", 422)

    svc = EvidenceService(db_session)
    try:
        result = await svc.create(
            session_id=session_id,
            owner_id=current_user.id,
            evidence_type=evidence_type,
            content=content,
            original_filename=filename,
            declared_mime_type=file.content_type,
            market_timestamp=parsed_market_ts,
        )
    except EvidenceSessionNotFoundError:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Trade session not found")
    except EvidenceValidationError as exc:
        return _evidence_error(exc.code, 422)
    except EvidenceServiceError as exc:
        if hasattr(exc, "code") and exc.code in _INVALID_FILE_MESSAGES:
            return _evidence_error(str(exc.code), 422)
        raise

    ev = result.evidence
    return _evidence_to_response(ev)


# ---------------------------------------------------------------------------
# GET /api/trade-sessions/{session_id}/evidence
# ---------------------------------------------------------------------------


@session_router.get("/{session_id}/evidence", response_model=EvidenceListResponse)
async def list_evidence(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
    active_only: bool = Query(False, description="Filter to active evidence only"),
    limit: int = Query(50, ge=1, le=200),
) -> EvidenceListResponse:
    svc = EvidenceService(db_session)
    try:
        if active_only:
            items = await svc.list_active_for_session(
                session_id,
                current_user.id,
                limit=limit,
            )
        else:
            items = await svc.list_for_session(
                session_id,
                current_user.id,
                limit=limit,
            )
    except EvidenceSessionNotFoundError:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Trade session not found")

    result = [_evidence_to_response(e) for e in items]
    return EvidenceListResponse(evidence=result, total=len(result))


# ---------------------------------------------------------------------------
# GET /api/evidence/{evidence_id}
# ---------------------------------------------------------------------------


@evidence_router.get("/{evidence_id}", response_model=EvidenceResponse)
async def get_evidence(
    evidence_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> EvidenceResponse:
    from app.repositories.evidence import EvidenceRepository

    repo = EvidenceRepository(db_session)
    ev = await repo.get_by_id_for_user(evidence_id, current_user.id)
    if ev is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Evidence not found")
    return _evidence_to_response(ev)


# ---------------------------------------------------------------------------
# GET /api/evidence/{evidence_id}/file
# ---------------------------------------------------------------------------


@evidence_router.get("/{evidence_id}/file")
async def get_evidence_file(
    evidence_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> Response:
    from app.repositories.evidence import EvidenceRepository

    repo = EvidenceRepository(db_session)
    ev = await repo.get_by_id_for_user(evidence_id, current_user.id)
    if ev is None or ev.storage_object_key is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Evidence not found")

    from pathlib import Path

    from app.config import AppConfig
    from app.storage import LocalFileStorage

    config = AppConfig()
    storage = LocalFileStorage(root=Path(config.storage_root))

    try:
        file_bytes = storage.read(file_reference=ev.storage_object_key)
    except Exception:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="File not found")

    from fastapi.responses import Response as FastAPIResponse

    return FastAPIResponse(
        content=file_bytes,
        media_type=ev.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'inline; filename="{ev.original_filename or "evidence"}"',
        },
    )


# ---------------------------------------------------------------------------
# POST /api/evidence/{evidence_id}/replace
# ---------------------------------------------------------------------------


@evidence_router.post("/{evidence_id}/replace", response_model=EvidenceResponse)
async def replace_evidence(
    evidence_id: uuid.UUID,
    file: UploadFile = File(...),
    evidence_type: str = Form(...),
    market_timestamp: str | None = Form(None),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> EvidenceResponse:
    from app.repositories.evidence import EvidenceRepository

    repo = EvidenceRepository(db_session)
    existing = await repo.get_by_id_for_user(evidence_id, current_user.id)
    if existing is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Evidence not found")

    content = await file.read()
    filename = file.filename or "upload"

    parsed_market_ts: datetime | None = None
    if market_timestamp:
        try:
            parsed_market_ts = datetime.fromisoformat(market_timestamp)
        except (ValueError, TypeError):
            return _evidence_error("EVIDENCE_MIME_UNSUPPORTED", 422)

    svc = EvidenceService(db_session)
    try:
        result = await svc.replace(
            session_id=existing.session_id,
            owner_id=current_user.id,
            evidence_type=evidence_type,
            content=content,
            original_filename=filename,
            declared_mime_type=file.content_type,
            market_timestamp=parsed_market_ts,
        )
    except EvidenceValidationError as exc:
        return _evidence_error(exc.code, 422)

    ev = result.evidence
    return _evidence_to_response(ev)


# ---------------------------------------------------------------------------
# POST /api/evidence/{evidence_id}/deactivate
# ---------------------------------------------------------------------------


@evidence_router.post("/{evidence_id}/deactivate", response_model=EvidenceResponse)
async def deactivate_evidence(
    evidence_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> EvidenceResponse:
    from app.repositories.evidence import EvidenceRepository

    repo = EvidenceRepository(db_session)
    ev = await repo.get_by_id_for_user(evidence_id, current_user.id)
    if ev is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Evidence not found")

    svc = EvidenceService(db_session)
    try:
        await svc.deactivate(evidence_id, current_user.id)
    except EvidenceNotFoundError:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Evidence not found")

    # Re-read after deactivation
    ev = await repo.get_by_id_for_user(evidence_id, current_user.id)
    assert ev is not None
    return _evidence_to_response(ev)
