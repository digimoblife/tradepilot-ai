"""Market Evidence API routes for TradePilot AI."""

from __future__ import annotations

import logging
import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import AppConfig
from app.database.session import get_db_session
from app.api.schemas.evidence_snapshot import EvidenceDeltaSchema, EvidenceSnapshotSchema
from app.models.enums import TradeSessionStatus
from app.repositories.trade_session import TradeSessionRepository
from app.services.evidence_delta import EvidenceDeltaCalculator
from app.services.market_data.collector import MarketDataCollector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["market-evidence"])

def get_config() -> AppConfig:
    return AppConfig()


@router.get(
    "/{session_id}/market-evidence/preview",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
)
async def preview_market_evidence(
    session_id: uuid.UUID,
    symbol: str | None = None,
    config: AppConfig = Depends(get_config),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Preview real-time market data from ZAPI before triggering full analysis."""
    session_repo = TradeSessionRepository(db)
    session = await session_repo.get_by_id(session_id)
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
    config: AppConfig = Depends(get_config),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Acquire and validate full market evidence for session."""
    session_repo = TradeSessionRepository(db)
    session = await session_repo.get_by_id(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    collector = MarketDataCollector(config)
    try:
        snapshot, val_result = await collector.acquire_snapshot(
            session_id=session_id,
            symbol=session.ticker,
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
        logger.error("Failed to acquire market evidence: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch market data from ZAPI: {str(exc)}",
        )
