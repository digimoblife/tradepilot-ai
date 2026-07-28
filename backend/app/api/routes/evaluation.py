"""API routes for evaluation records (P7).

Provides listing, filtering, detail view, on-demand backfill, and bounded JSON/CSV export
endpoints for authenticated users. Excludes raw provider content, prompts, and evidence images.
"""

from __future__ import annotations

import csv
import io
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.auth import AuthenticatedUser
from app.database.session import get_db_session
from app.repositories.evaluation_record import EvaluationRecordRepository
from app.services.evaluation_backfill import EvaluationBackfillService

router = APIRouter(prefix="/api/evaluation-records", tags=["evaluation"])

MAX_EXPORT_LIMIT = 500


class EvaluationRecordItemResponse(BaseModel):
    id: str
    owner_id: str
    session_id: str
    source_analysis_id: str | None = None
    ticker: str
    analysis_type: str
    prompt_name: str | None = None
    prompt_version: str | None = None
    schema_name: str | None = None
    schema_version: str | None = None
    provider: str | None = None
    model: str | None = None
    prediction_data: dict[str, Any]
    user_decision_data: dict[str, Any]
    outcome_data: dict[str, Any]
    completeness_status: str
    legacy_source: bool
    validation_warning_count: int
    quality_notes: list[str]
    created_at: str
    updated_at: str


class EvaluationRecordListResponse(BaseModel):
    items: list[EvaluationRecordItemResponse]
    total: int
    page: int
    limit: int


def _to_item_response(r: Any) -> EvaluationRecordItemResponse:
    return EvaluationRecordItemResponse(
        id=str(r.id),
        owner_id=str(r.owner_id),
        session_id=str(r.session_id),
        source_analysis_id=str(r.source_analysis_id) if r.source_analysis_id else None,
        ticker=r.ticker,
        analysis_type=r.analysis_type,
        prompt_name=r.prompt_name,
        prompt_version=r.prompt_version,
        schema_name=r.schema_name,
        schema_version=r.schema_version,
        provider=r.provider,
        model=r.model,
        prediction_data=r.prediction_data or {},
        user_decision_data=r.user_decision_data or {},
        outcome_data=r.outcome_data or {},
        completeness_status=r.completeness_status,
        legacy_source=r.legacy_source,
        validation_warning_count=r.validation_warning_count,
        quality_notes=r.quality_notes or [],
        created_at=r.created_at.isoformat() if hasattr(r.created_at, "isoformat") else str(r.created_at),
        updated_at=r.updated_at.isoformat() if hasattr(r.updated_at, "isoformat") else str(r.updated_at),
    )


@router.get("", response_model=EvaluationRecordListResponse)
async def list_evaluation_records(
    ticker: str | None = Query(None),
    analysis_type: str | None = Query(None),
    completeness_status: str | None = Query(None),
    session_status: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> EvaluationRecordListResponse:
    repo = EvaluationRecordRepository(db_session)
    offset = (page - 1) * limit
    records, total = await repo.list_by_owner(
        current_user.id,
        ticker=ticker,
        analysis_type=analysis_type,
        completeness_status=completeness_status,
        session_status=session_status,
        offset=offset,
        limit=limit,
    )
    items = [_to_item_response(r) for r in records]
    return EvaluationRecordListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/export/json")
async def export_evaluation_records_json(
    ticker: str | None = Query(None),
    analysis_type: str | None = Query(None),
    completeness_status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=MAX_EXPORT_LIMIT),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> Response:
    repo = EvaluationRecordRepository(db_session)
    records, _ = await repo.list_by_owner(
        current_user.id,
        ticker=ticker,
        analysis_type=analysis_type,
        completeness_status=completeness_status,
        offset=0,
        limit=limit,
    )
    data = [_to_item_response(r).model_dump() for r in records]
    content = json.dumps(data, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="evaluation_records.json"'},
    )


def _sanitize_csv(val: Any) -> str:
    s = str(val) if val is not None else ""
    if s.startswith(("=", "+", "-", "@")):
        return "'" + s
    return s


@router.get("/export/csv")
async def export_evaluation_records_csv(
    ticker: str | None = Query(None),
    analysis_type: str | None = Query(None),
    completeness_status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=MAX_EXPORT_LIMIT),
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    repo = EvaluationRecordRepository(db_session)
    records, _ = await repo.list_by_owner(
        current_user.id,
        ticker=ticker,
        analysis_type=analysis_type,
        completeness_status=completeness_status,
        offset=0,
        limit=limit,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "session_id",
        "ticker",
        "analysis_type",
        "recommendation",
        "user_action",
        "actual_entry_price",
        "actual_exit_price",
        "realized_return",
        "session_status",
        "completeness_status",
        "created_at",
    ])

    for r in records:
        pred = r.prediction_data or {}
        dec = r.user_decision_data or {}
        out = r.outcome_data or {}
        writer.writerow([
            _sanitize_csv(r.id),
            _sanitize_csv(r.session_id),
            _sanitize_csv(r.ticker),
            _sanitize_csv(r.analysis_type),
            _sanitize_csv(pred.get("recommendation") or ""),
            _sanitize_csv(dec.get("user_action") or ""),
            _sanitize_csv(dec.get("actual_entry_price") or ""),
            _sanitize_csv(dec.get("actual_exit_price") or ""),
            _sanitize_csv(out.get("realized_return") or ""),
            _sanitize_csv(out.get("session_status") or ""),
            _sanitize_csv(r.completeness_status),
            _sanitize_csv(r.created_at.isoformat() if hasattr(r.created_at, "isoformat") else str(r.created_at)),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="evaluation_records.csv"'},
    )


@router.post("/backfill/{session_id}")
async def backfill_session_evaluation(
    session_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    svc = EvaluationBackfillService(db_session)
    records = await svc.backfill_session(session_id, current_user.id)
    return {
        "session_id": str(session_id),
        "backfilled_count": len(records),
        "status": "COMPLETED",
    }


@router.get("/{record_id}", response_model=EvaluationRecordItemResponse)
async def get_evaluation_record_detail(
    record_id: uuid.UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db_session),
) -> EvaluationRecordItemResponse:
    repo = EvaluationRecordRepository(db_session)
    record = await repo.get_by_id(record_id, current_user.id)
    if record is None:
        raise HTTPException(status_code=404, detail="Evaluation record not found")
    return _to_item_response(record)
