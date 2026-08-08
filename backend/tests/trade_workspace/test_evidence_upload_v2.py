from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.trade_session import TradeSessionV2


def test_evidence_upload_v2_type_values_are_backward_compatible() -> None:
    assert [item.value for item in EvidenceUploadV2Type] == [
        "ORDERBOOK",
        "CHART_3_MONTH",
        "CHART_6_MONTH",
        "FOREIGN_FLOW_1W",
        "BROKER_FLOW_1D",
    ]


@pytest.mark.database
async def test_evidence_upload_v2_postgresql_enum_contains_all_values(engine) -> None:
    async with engine.connect() as connection:
        values = list(
            (
                await connection.scalars(
                    text("SELECT unnest(enum_range(NULL::evidence_upload_v2_type_enum))::text")
                )
            ).all()
        )
    assert values == [
        "ORDERBOOK",
        "CHART_3_MONTH",
        "CHART_6_MONTH",
        "FOREIGN_FLOW_1W",
        "BROKER_FLOW_1D",
    ]


def evidence_data(session_id: uuid.UUID, **overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "session_id": session_id,
        "evidence_type": EvidenceUploadV2Type.ORDERBOOK,
        "file_path": "local/evidence/orderbook.png",
        "original_filename": "orderbook.png",
        "mime_type": "image/png",
        "size_bytes": 1024,
    }
    data.update(overrides)
    return data


@pytest.mark.database
async def test_evidence_uploads_v2_persistence(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    user_id = uuid.uuid4()
    older = datetime.now(timezone.utc) - timedelta(days=1)

    async with factory() as session:
        async with session.begin():
            session.add(
                User(
                    id=user_id,
                    email=f"p33-{user_id}@example.test",
                    password_hash="test-only",
                )
            )
            trade_session = TradeSessionV2(
                user_id=user_id,
                ticker="BBRI",
                company_name="Bank BRI",
                created_at=older,
                updated_at=older,
            )
            session.add(trade_session)
            await session.flush()
            trade_session_id = trade_session.id

            analysis_request = AnalysisRequestV2(
                session_id=trade_session_id,
                analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                provider="gemini",
                model="gemini-3.1-flash-lite",
                prompt_version="v1",
                input_snapshot={"ticker": "BBRI"},
            )
            session.add(analysis_request)
            await session.flush()
            analysis_request_id = analysis_request.id

            initial = EvidenceUploadV2(
                **evidence_data(
                    trade_session_id,
                    evidence_type=EvidenceUploadV2Type.CHART_3_MONTH,
                    uploaded_at=older,
                )
            )
            linked = EvidenceUploadV2(
                **evidence_data(
                    trade_session_id,
                    analysis_request_id=analysis_request_id,
                    evidence_type=EvidenceUploadV2Type.CHART_6_MONTH,
                )
            )
            orderbook = EvidenceUploadV2(
                **evidence_data(
                    trade_session_id,
                    analysis_request_id=analysis_request_id,
                    observation_period="MORNING",
                )
            )
            midday = EvidenceUploadV2(
                **evidence_data(
                    trade_session_id,
                    analysis_request_id=analysis_request_id,
                    observation_period="MIDDAY",
                    file_path="local/evidence/orderbook-midday.png",
                    original_filename="orderbook-midday.png",
                )
            )
            afternoon = EvidenceUploadV2(
                **evidence_data(
                    trade_session_id,
                    analysis_request_id=analysis_request_id,
                    observation_period="AFTERNOON",
                    file_path="local/evidence/orderbook-afternoon.png",
                    original_filename="orderbook-afternoon.png",
                )
            )
            session.add_all([initial, linked, orderbook, midday, afternoon])
            await session.flush()

            assert initial.analysis_request_id is None
            assert linked.analysis_request_id == analysis_request_id
            assert linked.session_id == trade_session_id
            assert initial.observation_period is None

            read = await session.scalar(
                select(EvidenceUploadV2).where(EvidenceUploadV2.id == linked.id)
            )
            assert read is linked

            historical = list(
                (
                    await session.scalars(
                        select(EvidenceUploadV2)
                        .where(EvidenceUploadV2.session_id == trade_session_id)
                        .order_by(EvidenceUploadV2.uploaded_at.asc())
                    )
                ).all()
            )
            assert [item.id for item in historical] == [
                initial.id,
                linked.id,
                orderbook.id,
                midday.id,
                afternoon.id,
            ]

        invalid_uploads = [
            evidence_data(trade_session_id, evidence_type="INVALID"),  # type: ignore[arg-type]
            evidence_data(trade_session_id, observation_period="INVALID"),  # type: ignore[arg-type]
            evidence_data(trade_session_id, file_path="   "),
            evidence_data(trade_session_id, original_filename="   "),
            evidence_data(trade_session_id, mime_type="   "),
            evidence_data(trade_session_id, size_bytes=0),
            evidence_data(trade_session_id, size_bytes=-1),
        ]

        for data in invalid_uploads:
            with pytest.raises((IntegrityError, StatementError)):
                async with session.begin():
                    session.add(EvidenceUploadV2(**data))
                    await session.flush()

        await session.close()

        async with factory() as cleanup_session:
            async with cleanup_session.begin():
                await cleanup_session.execute(
                    delete(EvidenceUploadV2).where(EvidenceUploadV2.session_id == trade_session_id)
                )
                await cleanup_session.execute(
                    delete(AnalysisRequestV2).where(AnalysisRequestV2.id == analysis_request_id)
                )
                await cleanup_session.execute(
                    delete(TradeSessionV2).where(TradeSessionV2.id == trade_session_id)
                )
                await cleanup_session.execute(delete(User).where(User.id == user_id))
