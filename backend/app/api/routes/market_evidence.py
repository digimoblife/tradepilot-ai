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


from app.services.market_analysis_engine import MarketAnalysisEngine

_ANALYSIS_CACHE: dict[str, dict[str, Any]] = {}


@router.post(
    "/{session_id}/analyze",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
)
async def analyze_trade_session(
    session_id: uuid.UUID,
    symbol: str | None = Query(default=None, description="Optional override symbol"),
    config: AppConfig = Depends(get_config),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Execute AI Market Analysis on authoritative ZAPI data and update session state."""
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

        note = getattr(session, "note", None) or ""
        trading_style = "Swing Trade"
        if note.startswith("[") and "]" in note:
            trading_style = note[1 : note.index("]")]

        engine = MarketAnalysisEngine(config)
        analysis_result = await engine.analyze(
            snapshot=snapshot,
            trading_style=trading_style,
            setup_note=note,
        )

        # Update session status if in DRAFT
        try:
            from app.trade_workspace.models.trade_session import TradeSessionV2Status
            if getattr(session, "status", None) == TradeSessionV2Status.DRAFT:
                session.status = TradeSessionV2Status.ANALYZED
                await db.commit()
        except Exception:
            pass

        _ANALYSIS_CACHE[str(session_id)] = analysis_result
        return analysis_result
    except Exception as exc:
        logger.error("Failed to run AI market analysis: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to analyze market evidence: {str(exc)}",
        )


@router.get(
    "/{session_id}/workspace",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
)
async def get_session_workspace_data(
    session_id: uuid.UUID,
    config: AppConfig = Depends(get_config),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Retrieve full workspace data including session identity, market snapshot, and AI analysis."""
    session = await _find_session_by_id(session_id, db)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    cached_analysis = _ANALYSIS_CACHE.get(str(session_id))

    if not cached_analysis:
        collector = MarketDataCollector(config)
        try:
            snapshot, _ = await collector.acquire_snapshot(
                session_id=session_id,
                symbol=session.ticker,
                snapshot_type="INITIAL",
            )
            note = getattr(session, "note", None) or ""
            trading_style = "Swing Trade"
            if note.startswith("[") and "]" in note:
                trading_style = note[1 : note.index("]")]
            engine = MarketAnalysisEngine(config)
            cached_analysis = await engine.analyze(
                snapshot=snapshot,
                trading_style=trading_style,
                setup_note=note,
            )
            _ANALYSIS_CACHE[str(session_id)] = cached_analysis
        except Exception:
            cached_analysis = None

    status_val = getattr(session, "status", "DRAFT")
    if hasattr(status_val, "value"):
        status_val = status_val.value
    elif hasattr(status_val, "name"):
        status_val = status_val.name
    else:
        status_val = str(status_val)

    from app.trade_workspace.models.position import PositionV2
    from app.trade_workspace.models.trade_closure import TradeClosureV2
    from app.trade_workspace.models.session_decision import SessionDecisionV2

    pos = await db.scalar(
        select(PositionV2).where(PositionV2.session_id == session_id).limit(1)
    )
    pos_data = None
    if pos:
        pos_data = {
            "id": str(pos.id),
            "entry_price": float(pos.entry_price),
            "quantity": float(pos.quantity),
            "stop_loss": float(pos.stop_loss) if pos.stop_loss else None,
            "target_price": float(pos.target_price) if pos.target_price else None,
            "status": pos.status.value if hasattr(pos.status, "value") else str(pos.status),
            "entry_timestamp": (
                pos.entry_at.isoformat()
                if hasattr(pos, "entry_at") and pos.entry_at
                else None
            ),
        }

    closure = await db.scalar(
        select(TradeClosureV2).where(TradeClosureV2.session_id == session_id).limit(1)
    )
    closure_data = None
    if closure:
        closure_data = {
            "id": str(closure.id),
            "close_price": float(closure.close_price),
            "close_reason": closure.close_reason,
            "realized_profit_loss": float(closure.realized_profit_loss),
            "note": closure.note,
            "closed_at": closure.close_at.isoformat() if closure.close_at else None,
        }

    latest_decision = await db.scalar(
        select(SessionDecisionV2)
        .where(SessionDecisionV2.session_id == session_id)
        .order_by(SessionDecisionV2.created_at.desc())
        .limit(1)
    )
    decision_data = None
    if latest_decision:
        decision_data = {
            "decision": latest_decision.decision.value if hasattr(latest_decision.decision, "value") else str(latest_decision.decision),
            "reason": latest_decision.reason.value if hasattr(latest_decision.reason, "value") else (str(latest_decision.reason) if latest_decision.reason else None),
            "note": latest_decision.note,
            "decision_at": latest_decision.created_at.isoformat() if latest_decision.created_at else None,
        }

    return {
        "session": {
            "id": str(session.id),
            "ticker": session.ticker,
            "company_name": session.company_name,
            "status": status_val,
            "note": getattr(session, "note", None),
            "archived_at": session.archived_at.isoformat() if hasattr(session, "archived_at") and session.archived_at else None,
            "closed_at": session.closed_at.isoformat() if hasattr(session, "closed_at") and session.closed_at else None,
            "created_at": session.created_at.isoformat() if hasattr(session, "created_at") and session.created_at else None,
            "updated_at": session.updated_at.isoformat() if hasattr(session, "updated_at") and session.updated_at else None,
        },
        "analysis": cached_analysis,
        "position": pos_data,
        "closure": closure_data,
        "decision": decision_data,
    }
