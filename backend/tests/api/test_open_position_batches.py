"""Tests for Open Position Update evidence batches and API endpoints (P4).

PostgreSQL-backed tests — no mocking.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models.enums import AnalysisType, EvidenceBatchStatus, PositionStatus, TradeSessionStatus
from app.models.evidence_batch import EvidenceBatch
from app.services.actions.open_position import OpenPositionService
from app.services.evidence_batches import EvidenceBatchService
from app.services.evidence import EvidenceService

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
        await conn.execute(
            text(
                "INSERT INTO trade_sessions "
                "(id, owner_id, ticker, lifecycle_status, stable_status) "
                "VALUES (:sid, :uid, 'BBRI', :st, :st)"
            ),
            {"sid": session_id, "uid": user_id, "st": status},
        )
        await conn.execute(
            text(
                "INSERT INTO trade_states (session_id, position_status) "
                "VALUES (:sid, 'NOT_OPENED')"
            ),
            {"sid": session_id},
        )
    return user_id, session_id


# ===================================================================
# Tests
# ===================================================================


class TestOpenPositionBatchLifecycle:
    async def test_buy_creates_opu_draft_batch(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_user_and_session(engine, "INITIAL_ANALYZED")
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as db_session:
            svc = OpenPositionService(db_session)
            res = await svc.confirm(
                session_id=session_id,
                owner_id=user_id,
                idempotency_key=f"buy_{uuid.uuid4().hex}",
                entry_price="5000",
                quantity="100",
                execution_timestamp=datetime.now(timezone.utc),
            )
            assert res.session_status == TradeSessionStatus.OPEN_POSITION

            batch_svc = EvidenceBatchService(db_session)
            draft = await batch_svc.get_current_draft(
                session_id=session_id,
                owner_id=user_id,
                analysis_type=AnalysisType.OPEN_POSITION_UPDATE,
            )
            assert draft is not None
            assert draft.status == EvidenceBatchStatus.DRAFT
            assert draft.analysis_type == AnalysisType.OPEN_POSITION_UPDATE
            assert draft.monitoring_slot == "UNSPECIFIED"

    async def test_update_monitoring_slot(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_user_and_session(engine, "OPEN_POSITION")
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as db_session:
            batch_svc = EvidenceBatchService(db_session)
            batch = await batch_svc.get_or_create_current_draft(
                session_id=session_id,
                owner_id=user_id,
                analysis_type=AnalysisType.OPEN_POSITION_UPDATE,
            )
            assert batch.monitoring_slot == "UNSPECIFIED"

            updated = await batch_svc.update_monitoring_slot(batch, "MORNING")
            assert updated.monitoring_slot == "MORNING"

            updated_midday = await batch_svc.update_monitoring_slot(batch, "MIDDAY")
            assert updated_midday.monitoring_slot == "MIDDAY"

    async def test_opu_requires_orderbook(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_user_and_session(engine, "OPEN_POSITION")
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as db_session:
            batch_svc = EvidenceBatchService(db_session)
            batch = await batch_svc.get_or_create_current_draft(
                session_id=session_id,
                owner_id=user_id,
                analysis_type=AnalysisType.OPEN_POSITION_UPDATE,
            )

            evidence_svc = EvidenceService(db_session)
            required = await evidence_svc.get_required_evidence(
                session_id=session_id,
                owner_id=user_id,
                analysis_type=AnalysisType.OPEN_POSITION_UPDATE,
                evidence_batch_id=batch.id,
            )
            assert not required.complete
            assert len(required.missing_types) == 1

    async def test_opu_ready_with_orderbook(
        self,
        engine: AsyncEngine,
    ) -> None:
        user_id, session_id = await _make_user_and_session(engine, "OPEN_POSITION")
        factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

        async with factory() as db_session:
            batch_svc = EvidenceBatchService(db_session)
            batch = await batch_svc.get_or_create_current_draft(
                session_id=session_id,
                owner_id=user_id,
                analysis_type=AnalysisType.OPEN_POSITION_UPDATE,
            )

            evidence_svc = EvidenceService(db_session)
            await evidence_svc.create(
                session_id=session_id,
                owner_id=user_id,
                evidence_type="ORDERBOOK_SCREENSHOT",
                content=_make_image_bytes(),
                original_filename="ob.png",
                declared_mime_type="image/png",
                evidence_batch_id=batch.id,
            )

            required = await evidence_svc.get_required_evidence(
                session_id=session_id,
                owner_id=user_id,
                analysis_type=AnalysisType.OPEN_POSITION_UPDATE,
                evidence_batch_id=batch.id,
            )
            assert required.complete

            await batch_svc.mark_ready(batch)
            assert batch.status == EvidenceBatchStatus.READY
