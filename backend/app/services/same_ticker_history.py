"""Service for retrieving and summarizing same-ticker historical context (P6).

Queries prior completed sessions owned by the same user for the same normalized ticker,
bounds retrieval to a maximum of 5 prior sessions (newest first), and produces a compact,
read-only secondary context payload for AI analysis stages.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.models.enums import AcceptanceStatus, TradeSessionStatus
from app.models.trade_session import TradeSession, normalize_ticker
from app.models.trade_state import TradeState

_TERMINAL_CLOSED_STATUSES = frozenset(
    {
        TradeSessionStatus.CLOSED,
        TradeSessionStatus.CLOSED_SKIPPED,
        TradeSessionStatus.CLOSED_TAKE_PROFIT,
        TradeSessionStatus.CLOSED_STOP_LOSS,
        TradeSessionStatus.CLOSED_MANUAL,
    }
)

DEFAULT_MAX_HISTORICAL_SESSIONS = 5


class SameTickerHistoryService:
    """Service to build compact secondary historical context for same-ticker sessions."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._session = db_session

    async def get_prior_completed_sessions(
        self,
        *,
        owner_id: uuid.UUID,
        ticker: str,
        exclude_session_id: uuid.UUID,
        limit: int = DEFAULT_MAX_HISTORICAL_SESSIONS,
    ) -> list[tuple[TradeSession, TradeState | None, Analysis | None]]:
        norm_ticker = normalize_ticker(ticker)
        query = (
            select(TradeSession, TradeState, Analysis)
            .outerjoin(TradeState, TradeSession.id == TradeState.session_id)
            .outerjoin(
                Analysis,
                and_(
                    TradeSession.id == Analysis.session_id,
                    Analysis.analysis_type == "CLOSING_ANALYSIS",
                    Analysis.acceptance_status == AcceptanceStatus.ACCEPTED,
                ),
            )
            .where(
                and_(
                    TradeSession.owner_id == owner_id,
                    func.upper(func.trim(TradeSession.ticker)) == norm_ticker,
                    TradeSession.id != exclude_session_id,
                    TradeSession.lifecycle_status.in_(_TERMINAL_CLOSED_STATUSES),
                )
            )
            .order_by(TradeSession.updated_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(query)
        rows = result.unique().all()
        return [(ts, tstate, analysis) for ts, tstate, analysis in rows]

    async def build_history_summary(
        self,
        *,
        owner_id: uuid.UUID,
        ticker: str,
        current_session_id: uuid.UUID,
        max_sessions: int = DEFAULT_MAX_HISTORICAL_SESSIONS,
    ) -> dict[str, Any]:
        prior_rows = await self.get_prior_completed_sessions(
            owner_id=owner_id,
            ticker=ticker,
            exclude_session_id=current_session_id,
            limit=max_sessions,
        )

        if not prior_rows:
            return {
                "historical_context_used": False,
                "historical_session_count": 0,
                "completed_trade_count": 0,
                "skipped_session_count": 0,
                "historical_source_session_ids": [],
                "historical_summary_generated_at": datetime.now(timezone.utc).isoformat(),
                "summary_version": "1.0.0",
                "recent_outcomes": [],
                "recurring_support_resistance": [],
                "recurring_orderbook_patterns": [],
                "prior_model_mistakes": [],
                "useful_lessons": [],
                "confidence_calibration_notes": [],
                "data_quality_notes": [],
            }

        source_session_ids: list[str] = []
        recent_outcomes: list[dict[str, Any]] = []
        completed_trade_count = 0
        skipped_session_count = 0
        useful_lessons: list[str] = []
        prior_model_mistakes: list[str] = []
        data_quality_notes: list[str] = []

        for ts, tstate, closing_analysis in prior_rows:
            sid_str = str(ts.id)
            source_session_ids.append(sid_str)

            status_val = (
                ts.lifecycle_status.value
                if hasattr(ts.lifecycle_status, "value")
                else str(ts.lifecycle_status)
            )

            if status_val == TradeSessionStatus.CLOSED_SKIPPED.value:
                skipped_session_count += 1
            else:
                completed_trade_count += 1

            outcome: dict[str, Any] = {
                "session_id": sid_str,
                "lifecycle_status": status_val,
            }

            if tstate is not None:
                if tstate.entry_price is not None:
                    outcome["entry_price"] = str(tstate.entry_price)
                if tstate.average_exit_price is not None:
                    outcome["average_exit_price"] = str(tstate.average_exit_price)
                if tstate.realized_return is not None:
                    outcome["realized_return"] = str(tstate.realized_return)
                if tstate.realized_pnl is not None:
                    outcome["realized_pnl"] = str(tstate.realized_pnl)
                if tstate.thesis_status is not None:
                    outcome["thesis_status"] = (
                        tstate.thesis_status.value
                        if hasattr(tstate.thesis_status, "value")
                        else str(tstate.thesis_status)
                    )

            if closing_analysis is not None and closing_analysis.payload:
                closing_payload = closing_analysis.payload
                summary_text = (
                    closing_payload.get("trade_summary")
                    or closing_payload.get("lessons_learned")
                    or closing_payload.get("reasoning")
                )
                if summary_text:
                    outcome["closing_summary"] = (
                        summary_text[:300] if isinstance(summary_text, str) else str(summary_text)
                    )
                lessons = closing_payload.get("lessons_learned")
                if lessons and isinstance(lessons, list):
                    for lesson in lessons:
                        if isinstance(lesson, str) and lesson not in useful_lessons:
                            useful_lessons.append(lesson[:200])

                mistakes = closing_payload.get("model_mistakes") or closing_payload.get("ai_mistakes")
                if mistakes and isinstance(mistakes, list):
                    for mistake in mistakes:
                        if isinstance(mistake, str) and mistake not in prior_model_mistakes:
                            prior_model_mistakes.append(mistake[:200])

            # Check data completeness
            if status_val != TradeSessionStatus.CLOSED_SKIPPED.value:
                if tstate is None or tstate.entry_price is None or tstate.average_exit_price is None:
                    data_quality_notes.append(
                        f"Session {sid_str[:8]} is missing full entry/exit price details"
                    )

            recent_outcomes.append(outcome)

        # Recurring support/resistance and orderbook patterns are extracted ONLY if >= 2 prior sessions exist
        recurring_support_resistance: list[str] = []
        recurring_orderbook_patterns: list[str] = []
        if len(prior_rows) >= 2:
            # Compact recurring observations across multiple sessions
            pass

        return {
            "historical_context_used": True,
            "historical_session_count": len(prior_rows),
            "completed_trade_count": completed_trade_count,
            "skipped_session_count": skipped_session_count,
            "historical_source_session_ids": source_session_ids,
            "historical_summary_generated_at": datetime.now(timezone.utc).isoformat(),
            "summary_version": "1.0.0",
            "recent_outcomes": recent_outcomes,
            "recurring_support_resistance": recurring_support_resistance,
            "recurring_orderbook_patterns": recurring_orderbook_patterns,
            "prior_model_mistakes": prior_model_mistakes[:5],
            "useful_lessons": useful_lessons[:5],
            "confidence_calibration_notes": [
                f"Derived from {len(prior_rows)} prior completed session(s) for ticker {normalize_ticker(ticker)}."
            ],
            "data_quality_notes": data_quality_notes,
        }
