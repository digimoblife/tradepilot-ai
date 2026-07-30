from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2ObservationPeriod,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.trade_session import TradeSessionV2


def request_data(session_id: uuid.UUID, **overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "session_id": session_id,
        "analysis_type": AnalysisRequestV2Type.WAIT_UPDATE,
        "observation_period": AnalysisRequestV2ObservationPeriod.MORNING,
        "current_price": 123.45,
        "observation_at": datetime.now(timezone.utc),
        "provider": "gemini",
        "model": "gemini-3.1-flash-lite",
        "prompt_version": "v1",
        "input_snapshot": {"ticker": "BBRI"},
    }
    data.update(overrides)
    return data


@pytest.mark.database
async def test_analysis_requests_v2_persistence(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    user_id = uuid.uuid4()
    older = datetime.now(timezone.utc) - timedelta(days=1)

    async with factory() as session:
        async with session.begin():
            session.add(
                User(
                    id=user_id,
                    email=f"p32-{user_id}@example.test",
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

            initial = AnalysisRequestV2(
                **request_data(
                    trade_session.id,
                    analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                    observation_period=None,
                    current_price=None,
                    observation_at=None,
                )
            )
            waiting = AnalysisRequestV2(**request_data(trade_session.id))
            position = AnalysisRequestV2(
                **request_data(
                    trade_session.id,
                    analysis_type=AnalysisRequestV2Type.POSITION_UPDATE,
                    observation_period=AnalysisRequestV2ObservationPeriod.AFTERNOON,
                    current_price=125.0,
                )
            )
            session.add_all([initial, waiting, position])
            await session.flush()

            assert initial.status is AnalysisRequestV2Status.PENDING
            assert initial.current_price is None
            assert initial.observation_period is None
            assert initial.observation_at is None
            assert waiting.session_id == trade_session.id
            assert position.session_id == trade_session.id

            read = await session.scalar(
                select(AnalysisRequestV2).where(
                        AnalysisRequestV2.id == waiting.id,
                        AnalysisRequestV2.session_id == trade_session_id,
                )
            )
            assert read is waiting

            historical = list(
                (
                    await session.scalars(
                        select(AnalysisRequestV2)
                        .where(AnalysisRequestV2.session_id == trade_session_id)
                        .order_by(AnalysisRequestV2.created_at.asc())
                    )
                ).all()
            )
            assert [request.id for request in historical] == [initial.id, waiting.id, position.id]

        invalid_requests = [
            request_data(trade_session.id, current_price=None),
            request_data(trade_session.id, observation_period=None),
            request_data(trade_session.id, observation_at=None),
            request_data(
                trade_session.id,
                analysis_type=AnalysisRequestV2Type.POSITION_UPDATE,
                current_price=None,
            ),
            request_data(
                trade_session.id,
                analysis_type=AnalysisRequestV2Type.POSITION_UPDATE,
                observation_period=None,
            ),
            request_data(
                trade_session.id,
                analysis_type=AnalysisRequestV2Type.POSITION_UPDATE,
                observation_at=None,
            ),
            request_data(trade_session.id, current_price=0),
            request_data(trade_session.id, current_price=-1),
            request_data(trade_session.id, analysis_type="INVALID"),  # type: ignore[arg-type]
            request_data(trade_session.id, status="INVALID"),  # type: ignore[arg-type]
            request_data(trade_session.id, observation_period="INVALID"),  # type: ignore[arg-type]
            request_data(trade_session.id, provider="openai"),
        ]

        for data in invalid_requests:
            with pytest.raises((IntegrityError, StatementError)):
                async with session.begin():
                    session.add(AnalysisRequestV2(**data))
                    await session.flush()

        await session.close()

        async with factory() as cleanup_session:
            async with cleanup_session.begin():
                await cleanup_session.execute(
                    delete(AnalysisRequestV2).where(
                        AnalysisRequestV2.session_id == trade_session_id
                    )
                )
                await cleanup_session.execute(
                    delete(TradeSessionV2).where(TradeSessionV2.id == trade_session_id)
                )
                await cleanup_session.execute(delete(User).where(User.id == user_id))
