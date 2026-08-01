from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2ObservationPeriod,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.session_decision import SessionDecisionV2, SessionDecisionV2Decision
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
from app.trade_workspace.services.session_detail_aggregate import (
    SessionDetailAggregateNotFoundError,
    SessionDetailAggregateService,
)

pytestmark = pytest.mark.database


async def test_session_detail_aggregate_is_v2_owned_ordered_and_read_only(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    async with factory() as db:
        async with db.begin():
            db.add(User(id=user_id, email=f"aggregate-{user_id}@example.test", password_hash="test-only"))
            trade_session = TradeSessionV2(
                id=session_id, user_id=user_id, ticker="BBRI", company_name="Bank BRI", status=TradeSessionV2Status.WAITING
            )
            db.add(trade_session)
            await db.flush()
            initial_request = AnalysisRequestV2(
                session_id=session_id, analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                status=AnalysisRequestV2Status.COMPLETED, provider="gemini", model="test-model",
                prompt_version="v1", input_snapshot={}, processed_response={"summary": "advisory"},
            )
            wait_request = AnalysisRequestV2(
                session_id=session_id, analysis_type=AnalysisRequestV2Type.WAIT_UPDATE,
                observation_period=AnalysisRequestV2ObservationPeriod.MORNING, current_price=Decimal("1200"),
                observation_at=now, status=AnalysisRequestV2Status.COMPLETED, provider="gemini", model="test-model",
                prompt_version="v1", input_snapshot={"note": "keep separate"}, processed_response={"action": "WAIT"},
            )
            db.add_all([initial_request, wait_request])
            await db.flush()
            db.add_all([
                EvidenceUploadV2(
                    session_id=session_id, analysis_request_id=initial_request.id,
                    evidence_type=EvidenceUploadV2Type.ORDERBOOK, original_filename="book.png",
                    mime_type="image/png", size_bytes=10, file_path="stored/safe.png",
                ),
                EvidenceUploadV2(
                    session_id=session_id, analysis_request_id=wait_request.id,
                    evidence_type=EvidenceUploadV2Type.ORDERBOOK, original_filename="wait.png",
                    mime_type="image/png", size_bytes=10, file_path="stored/wait.png",
                ),
            ])
            db.add_all([
                SessionDecisionV2(session_id=session_id, decision=SessionDecisionV2Decision.WAIT, created_at=now),
                SessionDecisionV2(session_id=session_id, decision=SessionDecisionV2Decision.WAIT, created_at=now),
            ])
        before = await db.scalar(select(TradeSessionV2.updated_at).where(TradeSessionV2.id == session_id))
        aggregate = await SessionDetailAggregateService(db).get(user_id=user_id, session_id=session_id)
        again = await SessionDetailAggregateService(db).get(user_id=user_id, session_id=session_id)
        after = await db.scalar(select(TradeSessionV2.updated_at).where(TradeSessionV2.id == session_id))

        assert set(aggregate.payload) == {
            "session", "initial_evidence", "initial_analysis", "decisions", "wait_updates",
            "position", "position_updates", "closure",
        }
        assert [item["evidence_type"] for item in aggregate.payload["initial_evidence"]] == ["ORDERBOOK"]
        assert aggregate.payload["initial_analysis"]["analysis_type"] == "INITIAL_ANALYSIS"  # type: ignore[index]
        assert len(aggregate.payload["decisions"]) == 2
        assert len(aggregate.payload["wait_updates"]) == 1
        assert aggregate.payload == again.payload
        assert before == after

        with pytest.raises(SessionDetailAggregateNotFoundError):
            await SessionDetailAggregateService(db).get(user_id=uuid.uuid4(), session_id=session_id)

        await db.rollback()
        async with db.begin():
            await db.execute(delete(EvidenceUploadV2).where(EvidenceUploadV2.session_id == session_id))
            await db.execute(delete(AnalysisRequestV2).where(AnalysisRequestV2.session_id == session_id))
            await db.execute(delete(SessionDecisionV2).where(SessionDecisionV2.session_id == session_id))
            await db.execute(delete(TradeSessionV2).where(TradeSessionV2.id == session_id))
            await db.execute(delete(User).where(User.id == user_id))
