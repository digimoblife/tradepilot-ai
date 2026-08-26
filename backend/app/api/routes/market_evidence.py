"""Market Evidence API routes for TradePilot AI.

Provides REST endpoints to preview, acquire, and compute evidence deltas
from authoritative ZAPI data feeds (Pluang, IDX, Stockbit).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import AppConfig
from app.database.session import get_db_session
from app.api.schemas.evidence_snapshot import (
    EvidenceDeltaSchema,
    EvidenceSnapshotSchema,
)
from app.models.enums import TradeSessionStatus
from app.models.trade_session import TradeSession
from app.trade_workspace.models.trade_session import TradeSessionV2
from app.services.evidence_delta import EvidenceDeltaCalculator
from app.services.market_data.collector import MarketDataCollector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["market-evidence"])


def get_config() -> AppConfig:
    return AppConfig()


async def _find_session_by_id(session_id: uuid.UUID, db: AsyncSession):
    """Query session from either TradeSessionV2 (preferred) or TradeSession (v1)."""
    res_v2 = await db.execute(select(TradeSessionV2).where(TradeSessionV2.id == session_id))
    session = res_v2.scalar_one_or_none()
    if session is not None:
        return session
    res_v1 = await db.execute(select(TradeSession).where(TradeSession.id == session_id))
    return res_v1.scalar_one_or_none()


@router.get(
    "/{session_id}/market-evidence/preview",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
)
async def preview_market_evidence(
    session_id: uuid.UUID,
    symbol: str | None = Query(default=None, description="Optional override symbol"),
    config: AppConfig = Depends(get_config),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Preview real-time market data from ZAPI before triggering full analysis."""
    session = await _find_session_by_id(session_id, db)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    target_symbol = symbol or session.ticker
    collector = MarketDataCollector(config)

    try:
        snapshot, val_result = await collector.acquire_snapshot(
            session_id=session_id,
            symbol=target_symbol,
            snapshot_type="INITIAL",
        )
        return {
            "snapshot": snapshot.model_dump(),
            "validation": {
                "is_valid": val_result.is_valid,
                "completeness_status": val_result.completeness_status,
                "critical_errors": val_result.critical_errors,
                "warnings": val_result.warnings,
            },
        }
    except Exception as exc:
        logger.error("Failed to acquire market evidence preview: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch market data from ZAPI: {str(exc)}",
        )


@router.post(
    "/{session_id}/market-evidence/acquire",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
)
async def acquire_market_evidence(
    session_id: uuid.UUID,
    snapshot_type: str = Query(default="INITIAL", description="INITIAL, UPDATE, or MANUAL_REFRESH"),
    symbol: str | None = Query(default=None, description="Optional override symbol"),
    config: AppConfig = Depends(get_config),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Acquire and validate authoritative market evidence for a trade session."""
    session = await _find_session_by_id(session_id, db)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    target_symbol = symbol or session.ticker
    collector = MarketDataCollector(config)

    try:
        snapshot, val_result = await collector.acquire_snapshot(
            session_id=session_id,
            symbol=target_symbol,
            snapshot_type=snapshot_type,
        )
        return {
            "snapshot": snapshot.model_dump(),
            "validation": {
                "is_valid": val_result.is_valid,
                "completeness_status": val_result.completeness_status,
                "critical_errors": val_result.critical_errors,
                "warnings": val_result.warnings,
            },
        }
    except Exception as exc:
        logger.error("Failed to acquire market evidence: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch market data from ZAPI: {str(exc)}",
        )


from pydantic import BaseModel


class DeltaComputationRequest(BaseModel):
    base_snapshot: EvidenceSnapshotSchema
    current_snapshot: EvidenceSnapshotSchema | None = None


@router.post(
    "/{session_id}/market-evidence/delta",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
)
async def compute_market_evidence_delta(
    session_id: uuid.UUID,
    body: DeltaComputationRequest,
    symbol: str | None = Query(default=None, description="Optional override symbol"),
    config: AppConfig = Depends(get_config),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Compute delta changes between base_snapshot and current_snapshot (or acquire fresh)."""
    calculator = EvidenceDeltaCalculator()

    if body.current_snapshot is not None:
        delta = calculator.calculate_delta(body.base_snapshot, body.current_snapshot)
        return {
            "current_snapshot": body.current_snapshot.model_dump(),
            "delta": delta.model_dump(),
            "validation": {
                "is_valid": True,
                "completeness_status": "COMPLETE",
                "critical_errors": [],
                "warnings": [],
            },
        }

    session = await _find_session_by_id(session_id, db)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    target_symbol = symbol or session.ticker
    collector = MarketDataCollector(config)

    try:
        current_snapshot, val_result = await collector.acquire_snapshot(
            session_id=session_id,
            symbol=target_symbol,
            snapshot_type="UPDATE",
        )
        delta = calculator.calculate_delta(body.base_snapshot, current_snapshot)
        return {
            "current_snapshot": current_snapshot.model_dump(),
            "delta": delta.model_dump(),
            "validation": {
                "is_valid": val_result.is_valid,
                "completeness_status": val_result.completeness_status,
                "critical_errors": val_result.critical_errors,
                "warnings": val_result.warnings,
            },
        }
    except Exception as exc:
        logger.error("Failed to compute market evidence delta: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to compute delta: {str(exc)}",
        )
