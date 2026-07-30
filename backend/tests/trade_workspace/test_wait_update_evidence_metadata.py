from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User
from app.trade_workspace.models.analysis_request import AnalysisRequestV2ObservationPeriod
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status


@pytest.mark.database
async def test_wait_update_evidence_metadata_round_trip(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    user_id = uuid.uuid4()
    async with factory() as session:
        async with session.begin():
            session.add(
                User(
                    id=user_id,
                    email=f"p71a-{user_id}@example.test",
                    password_hash="test-only",
                )
            )
            trade_session = TradeSessionV2(
                user_id=user_id,
                ticker="BBRI",
                company_name="Bank BRI",
                status=TradeSessionV2Status.WAITING,
            )
            session.add(trade_session)
            await session.flush()

            initial = EvidenceUploadV2(
                session_id=trade_session.id,
                evidence_type=EvidenceUploadV2Type.ORDERBOOK,
                analysis_request_id=None,
                observation_period=None,
                file_path="user/session/initial.png",
                original_filename="initial.png",
                mime_type="image/png",
                size_bytes=128,
            )
            update = EvidenceUploadV2(
                session_id=trade_session.id,
                evidence_type=EvidenceUploadV2Type.ORDERBOOK,
                analysis_request_id=None,
                observation_period=AnalysisRequestV2ObservationPeriod.MIDDAY,
                current_price=Decimal("1234.567890"),
                observation_timestamp=datetime(
                    2026, 7, 30, 9, 15, 0, 123456, tzinfo=timezone.utc
                ),
                file_path="user/session/update.png",
                original_filename="update.png",
                mime_type="image/png",
                size_bytes=256,
            )
            session.add_all([initial, update])
            await session.flush()

            read_initial = await session.scalar(
                select(EvidenceUploadV2).where(EvidenceUploadV2.id == initial.id)
            )
            read_update = await session.scalar(
                select(EvidenceUploadV2).where(EvidenceUploadV2.id == update.id)
            )
            assert read_initial is not None
            assert read_initial.current_price is None
            assert read_initial.observation_timestamp is None
            assert read_update is not None
            assert read_update.session_id == trade_session.id
            assert read_update.evidence_type is EvidenceUploadV2Type.ORDERBOOK
            assert read_update.analysis_request_id is None
            assert read_update.observation_period is AnalysisRequestV2ObservationPeriod.MIDDAY
            assert read_update.current_price == Decimal("1234.567890")
            assert read_update.observation_timestamp == datetime(
                2026, 7, 30, 9, 15, 0, 123456, tzinfo=timezone.utc
            )
            assert read_update.original_filename == "update.png"
            assert read_update.mime_type == "image/png"
            assert read_update.size_bytes == 256
            assert trade_session.status is TradeSessionV2Status.WAITING

    columns = set(EvidenceUploadV2.__table__.columns.keys())
    assert {"current_price", "observation_timestamp", "observation_period"} <= columns
    assert EvidenceUploadV2.__table__.c.current_price.type.precision == 20
    assert EvidenceUploadV2.__table__.c.current_price.type.scale == 6
    assert EvidenceUploadV2.__table__.c.observation_timestamp.type.timezone is True
