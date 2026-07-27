"""On-demand deterministic backfill service for evaluation records (P7).

Processes pre-existing completed sessions and accepted analyses into structured
evaluation records without raw provider content or speculative inferences.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.models.enums import AcceptanceStatus, TradeSessionStatus
from app.models.evaluation_record import CompletenessStatus, EvaluationRecord
from app.models.trade_action import TradeAction
from app.models.trade_session import TradeSession
from app.models.trade_state import TradeState
from app.services.evaluation_records import EvaluationRecordService


class EvaluationBackfillService:
    """Service to backfill evaluation records for pre-existing sessions."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._session = db_session
        self._svc = EvaluationRecordService(db_session)

    async def backfill_session(self, session_id: uuid.UUID, owner_id: uuid.UUID) -> list[EvaluationRecord]:
        """Backfill evaluation records for a single session."""
        ts_query = select(TradeSession).where(
            TradeSession.id == session_id,
            TradeSession.owner_id == owner_id,
        )
        ts_res = await self._session.execute(ts_query)
        ts = ts_res.scalar_one_or_none()
        if ts is None:
            return []

        created_records: list[EvaluationRecord] = []

        # 1. Backfill from accepted analyses
        analyses_query = (
            select(Analysis)
            .where(
                Analysis.session_id == session_id,
                Analysis.acceptance_status == AcceptanceStatus.ACCEPTED,
            )
            .order_by(Analysis.accepted_at.asc())
        )
        a_res = await self._session.execute(analyses_query)
        accepted_analyses = list(a_res.scalars().all())

        for analysis in accepted_analyses:
            rec = await self._svc.record_prediction_from_analysis(analysis, ts)
            if rec is not None:
                rec.legacy_source = True
                created_records.append(rec)

        # 2. Backfill trade actions
        actions_query = (
            select(TradeAction)
            .where(TradeAction.session_id == session_id)
            .order_by(TradeAction.created_at.asc())
        )
        act_res = await self._session.execute(actions_query)
        actions = list(act_res.scalars().all())

        for act in actions:
            action_type_str = act.action_type.value if hasattr(act.action_type, "value") else str(act.action_type)
            rec = await self._svc.record_user_decision(
                ts,
                action_type_str,
                act.payload or {},
            )
            if rec is not None:
                rec.legacy_source = True

        # 3. Backfill outcome if session is closed or skipped
        status_val = ts.lifecycle_status.value if hasattr(ts.lifecycle_status, "value") else str(ts.lifecycle_status)
        if status_val in (
            TradeSessionStatus.CLOSED.value,
            TradeSessionStatus.CLOSED_SKIPPED.value,
            TradeSessionStatus.CLOSED_TAKE_PROFIT.value,
            TradeSessionStatus.CLOSED_STOP_LOSS.value,
            TradeSessionStatus.CLOSED_MANUAL.value,
        ):
            state_query = select(TradeState).where(TradeState.session_id == session_id)
            st_res = await self._session.execute(state_query)
            tstate = st_res.scalar_one_or_none()

            rec = await self._svc.record_outcome_on_closure(ts, tstate)
            if rec is not None:
                rec.legacy_source = True
                if rec.completeness_status == CompletenessStatus.PARTIAL.value:
                    rec.completeness_status = CompletenessStatus.LEGACY_PARTIAL.value

        return created_records
