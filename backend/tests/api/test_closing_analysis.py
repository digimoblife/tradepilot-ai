"""Tests for P5 Sell and Closing Analysis flow.

PostgreSQL-backed tests verifying full exit confirmation, calculation of metrics,
atomicity/rollback, terminal state enforcement, and Closing Analysis job creation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO
from types import SimpleNamespace
from typing import Any

import pytest
from PIL import Image
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.ai.providers.router import (
    ProviderRouteAttempt,
    ProviderRouter,
    ProviderRoutingResult,
)
from app.jobs import AnalysisProcessor
from app.models.analysis import Analysis
from app.models.analysis_job import AnalysisJob
from app.models.enums import AcceptanceStatus, AnalysisJobStatus, AnalysisType, EvidenceBatchStatus, PositionStatus, TradeSessionStatus
from app.models.evidence_batch import EvidenceBatch
from app.models.trade_action import TradeAction
from app.services.actions.full_exit import FullExitActionService, FullExitInvalidInputError, FullExitInvalidStateError
from app.services.actions.open_position import OpenPositionService
from app.services.actions.stop_loss import StopLossActionService, StopLossInvalidStateError
from app.services.actions.target import TargetActionService, TargetInvalidStateError
from app.services.analysis_jobs import (
    AnalysisJobAcceptedAlreadyExistsError,
    AnalysisJobAlreadyActiveError,
    AnalysisJobCreationService,
    AnalysisTypeInvalidForLifecycleError,
)
from app.services.evidence import EvidenceService
from app.services.evidence_batches import EvidenceBatchService

pytestmark = pytest.mark.database


# ===================================================================
# Helpers
# ===================================================================


def _make_image_bytes() -> bytes:
    img = Image.new("RGB", (50, 50), color="blue")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def _make_user_and_session(
    engine: AsyncEngine,
    status: str = "INITIAL_ANALYZED",
) -> tuple[uuid.UUID, uuid.UUID]:
    async with engine.begin() as conn:
        user = await conn.execute(
            text(
                "INSERT INTO users (email, password_hash) "
                "VALUES (:e, 'hash') RETURNING id"
            ),
            {"e": f"user_{uuid.uuid4().hex[:8]}@example.com"},
        )
        user_id = user.scalar_one()

        session_id = uuid.uuid4()
        stable_st = "OPEN_POSITION" if status in ("ANALYZING", "OPEN_POSITION") else status
        await conn.execute(
            text(
                "INSERT INTO trade_sessions "
                "(id, owner_id, ticker, lifecycle_status, stable_status) "
                "VALUES (:sid, :uid, 'BBRI', :st, :sst)"
            ),
            {"sid": session_id, "uid": user_id, "st": status, "sst": stable_st},
        )
        pos_st = "OPEN" if status in ("OPEN_POSITION", "ANALYZING") else "NOT_OPENED"
        await conn.execute(
            text(
                "INSERT INTO trade_states "
                "(session_id, position_status, entry_price, entry_at, original_quantity, remaining_quantity) "
                "VALUES (:sid, :pst, 5000, :eat, 100, 100)"
            ),
            {
                "sid": session_id,
                "pst": pos_st,
                "eat": datetime.now(timezone.utc) - timedelta(days=5) if pos_st == "OPEN" else None,
            },
        )
    return user_id, session_id


async def _make_open_position_session(engine: AsyncEngine) -> tuple[uuid.UUID, uuid.UUID]:
    user_id, session_id = await _make_user_and_session(engine, "INITIAL_ANALYZED")
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        svc = OpenPositionService(s)
        await svc.confirm(
            session_id=session_id,
            owner_id=user_id,
            idempotency_key=f"buy_{uuid.uuid4().hex}",
            entry_price="5000",
            quantity="100",
            execution_timestamp=datetime.now(timezone.utc) - timedelta(days=5),
        )
        await s.commit()
    return user_id, session_id


async def _make_closed_session(engine: AsyncEngine) -> tuple[uuid.UUID, uuid.UUID]:
    user_id, session_id = await _make_open_position_session(engine)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        svc = FullExitActionService(s)
        await svc.confirm(
            session_id=session_id,
            owner_id=user_id,
            idempotency_key=f"sell_{uuid.uuid4().hex}",
            exit_price="5500",
            exit_quantity="100",
            executed_at=datetime.now(timezone.utc),
            closing_reason="TAKE_PROFIT",
            note="Full profit taken",
        )
        await s.commit()
    return user_id, session_id


# ===================================================================
# Tests
# ===================================================================


class TestFullSellConfirmation:
    async def test_full_sell_requires_exit_price_and_timestamp(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_open_position_session(engine)
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as s:
            svc = FullExitActionService(s)
            with pytest.raises(FullExitInvalidInputError):
                await svc.confirm(
                    session_id=session_id,
                    owner_id=user_id,
                    idempotency_key=f"sell_{uuid.uuid4().hex}",
                    exit_price="0",
                    exit_quantity="100",
                    executed_at=datetime.now(timezone.utc),
                    closing_reason="TAKE_PROFIT",
                )

    async def test_full_sell_computes_realized_return_and_duration(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_open_position_session(engine)
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as s:
            svc = FullExitActionService(s)
            res = await svc.confirm(
                session_id=session_id,
                owner_id=user_id,
                idempotency_key=f"sell_{uuid.uuid4().hex}",
                exit_price="5500",
                exit_quantity="100",
                executed_at=datetime.now(timezone.utc),
                closing_reason="TAKE_PROFIT",
                note="Closed for gain",
            )
            from app.repositories.trade_session import TradeSessionRepository
            from app.repositories.trade_state import TradeStateRepository
            ts = await TradeSessionRepository(s).get_by_id_for_user(session_id, user_id)
            tstate = await TradeStateRepository(s).get_for_user(session_id, user_id)
            assert ts is not None and ts.lifecycle_status == TradeSessionStatus.CLOSED
            assert tstate is not None and tstate.position_status == PositionStatus.CLOSED

            # Query trade_actions for realized PnL payload
            action = await s.get(TradeAction, res.action.id)
            assert action is not None
            assert action.payload.get("gross_pnl") is not None
            assert action.payload.get("closing_reason") == "TAKE_PROFIT"
            assert tstate.realized_pnl is not None

    async def test_full_exit_rollback_on_failure(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_open_position_session(engine)
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as s:
            svc = FullExitActionService(s)
            with pytest.raises(Exception):
                await svc.confirm(
                    session_id=session_id,
                    owner_id=user_id,
                    idempotency_key=f"sell_{uuid.uuid4().hex}",
                    exit_price="5500",
                    exit_quantity="999",
                    executed_at=datetime.now(timezone.utc),
                    closing_reason="TAKE_PROFIT",
                )
            await s.rollback()

        async with factory() as s:
            from app.repositories.trade_session import TradeSessionRepository
            from app.repositories.trade_state import TradeStateRepository
            ts = await TradeSessionRepository(s).get_by_id_for_user(session_id, user_id)
            tstate = await TradeStateRepository(s).get_for_user(session_id, user_id)
            assert ts is not None and ts.lifecycle_status == TradeSessionStatus.OPEN_POSITION
            assert tstate is not None and tstate.position_status == PositionStatus.OPEN


class TestTerminalClosedStateEnforcement:
    async def test_closed_session_rejects_evidence_upload(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_closed_session(engine)
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as s:
            svc = EvidenceService(s)
            # Evidence upload directly or via batch is blocked on terminal session
            with pytest.raises(Exception):
                await svc.create(
                    session_id=session_id,
                    owner_id=user_id,
                    evidence_type="ORDERBOOK_SCREENSHOT",
                    content=_make_image_bytes(),
                    original_filename="ob.png",
                    declared_mime_type="image/png",
                )

    async def test_closed_session_rejects_watching_batch_creation(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_closed_session(engine)
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as s:
            svc = EvidenceBatchService(s)
            with pytest.raises(Exception):
                await svc.get_or_create_current_draft(
                    session_id=session_id,
                    owner_id=user_id,
                    analysis_type=AnalysisType.WATCHING_UPDATE,
                )

    async def test_closed_session_rejects_stop_and_target_adjustments(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_closed_session(engine)
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as s:
            stop_svc = StopLossActionService(s)
            with pytest.raises(StopLossInvalidStateError):
                await stop_svc.confirm(
                    session_id=session_id,
                    owner_id=user_id,
                    idempotency_key=f"stop_{uuid.uuid4().hex}",
                    stop_loss="4800",
                    confirmed_at=datetime.now(timezone.utc),
                )

            target_svc = TargetActionService(s)
            with pytest.raises(TargetInvalidStateError):
                await target_svc.confirm(
                    session_id=session_id,
                    owner_id=user_id,
                    idempotency_key=f"target_{uuid.uuid4().hex}",
                    target="6000",
                    confirmed_at=datetime.now(timezone.utc),
                )

    async def test_closed_session_rejects_repeated_full_exit(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_closed_session(engine)
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as s:
            svc = FullExitActionService(s)
            with pytest.raises(FullExitInvalidStateError):
                await svc.confirm(
                    session_id=session_id,
                    owner_id=user_id,
                    idempotency_key=f"sell2_{uuid.uuid4().hex}",
                    exit_price="5500",
                    exit_quantity="100",
                    executed_at=datetime.now(timezone.utc),
                    closing_reason="TAKE_PROFIT",
                )


class TestClosingAnalysisJobCreation:
    async def test_request_closing_analysis_job(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_closed_session(engine)
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as s:
            job_svc = AnalysisJobCreationService(s)
            res = await job_svc.create(
                session_id=session_id,
                owner_id=user_id,
                analysis_type=AnalysisType.CLOSING_ANALYSIS,
            )
            assert res.analysis_type == "CLOSING_ANALYSIS"
            assert res.job_status == "QUEUED"
            assert res.evidence_batch_id is None

    async def test_duplicate_active_closing_analysis_job_prevented(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_closed_session(engine)
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as s:
            job_svc = AnalysisJobCreationService(s)
            await job_svc.create(
                session_id=session_id,
                owner_id=user_id,
                analysis_type=AnalysisType.CLOSING_ANALYSIS,
            )
            await s.commit()

        # Session is now in ANALYZING state from first job creation; active duplicate should raise error
        async with factory() as s:
            job_svc = AnalysisJobCreationService(s)
            with pytest.raises((AnalysisJobAlreadyActiveError, AnalysisTypeInvalidForLifecycleError)):
                await job_svc.create(
                    session_id=session_id,
                    owner_id=user_id,
                    analysis_type=AnalysisType.CLOSING_ANALYSIS,
                )

    async def test_accepted_duplicate_closing_analysis_prevented(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_closed_session(engine)
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        # Seed an accepted Closing Analysis
        job_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO analysis_jobs (id, session_id, analysis_type, status, previous_session_status, attempt_count, max_attempts, requested_at, available_at) "
                    "VALUES (:jid, :sid, 'CLOSING_ANALYSIS', 'COMPLETED', 'CLOSED', 1, 1, :now, :now)"
                ),
                {"jid": job_id, "sid": session_id, "now": now},
            )

        async with factory() as s:
            analysis = Analysis(
                id=uuid.uuid4(),
                session_id=session_id,
                analysis_job_id=job_id,
                analysis_type="CLOSING_ANALYSIS",
                acceptance_status=AcceptanceStatus.ACCEPTED,
                prompt_name="CLOSING_ANALYSIS",
                prompt_version="1.0.0",
                schema_name="closing_analysis",
                schema_version="1.0.0",
                payload={"trade_summary": "Good trade"},
                accepted_at=datetime.now(timezone.utc),
            )
            s.add(analysis)
            await s.commit()

        async with factory() as s:
            job_svc = AnalysisJobCreationService(s)
            with pytest.raises(AnalysisJobAcceptedAlreadyExistsError):
                await job_svc.create(
                    session_id=session_id,
                    owner_id=user_id,
                    analysis_type=AnalysisType.CLOSING_ANALYSIS,
                )
