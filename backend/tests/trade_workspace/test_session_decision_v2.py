from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User
from app.trade_workspace.models.session_decision import (
    SessionDecisionV2,
    SessionDecisionV2Decision,
    SessionDecisionV2Reason,
)
from app.trade_workspace.models.trade_session import TradeSessionV2


def decision_data(session_id: uuid.UUID, **overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "session_id": session_id,
        "decision": SessionDecisionV2Decision.WAIT,
    }
    data.update(overrides)
    return data


@pytest.mark.database
async def test_session_decisions_v2_persistence(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    user_id = uuid.uuid4()
    older = datetime.now(timezone.utc) - timedelta(days=1)

    assert not {"provider", "model", "gemini"} & set(
        SessionDecisionV2.__table__.columns.keys()
    )

    async with factory() as session:
        async with session.begin():
            session.add(
                User(
                    id=user_id,
                    email=f"p34-{user_id}@example.test",
                    password_hash="test-only",
                )
            )
            first_session = TradeSessionV2(
                user_id=user_id,
                ticker="BBRI",
                company_name="Bank BRI",
            )
            second_session = TradeSessionV2(
                user_id=user_id,
                ticker="BBCA",
                company_name="Bank Central Asia",
            )
            session.add_all([first_session, second_session])
            await session.flush()
            first_session_id = first_session.id
            second_session_id = second_session.id

            first_wait = SessionDecisionV2(
                **decision_data(first_session_id, created_at=older)
            )
            second_wait = SessionDecisionV2(
                **decision_data(first_session_id, created_at=older + timedelta(hours=1))
            )
            skip = SessionDecisionV2(
                **decision_data(
                    first_session_id,
                    decision=SessionDecisionV2Decision.SKIP,
                    reason=SessionDecisionV2Reason.RISK_TOO_HIGH,
                    created_at=older + timedelta(hours=2),
                )
            )
            buy = SessionDecisionV2(
                **decision_data(
                    second_session_id,
                    decision=SessionDecisionV2Decision.BUY,
                    created_at=older + timedelta(hours=3),
                )
            )
            session.add_all([first_wait, second_wait, skip, buy])
            await session.flush()

            assert first_wait.decision is SessionDecisionV2Decision.WAIT
            assert second_wait.decision is SessionDecisionV2Decision.WAIT
            assert skip.reason is SessionDecisionV2Reason.RISK_TOO_HIGH
            assert buy.decision is SessionDecisionV2Decision.BUY
            assert buy.session_id == second_session_id

            read = await session.scalar(
                select(SessionDecisionV2).where(SessionDecisionV2.id == skip.id)
            )
            assert read is skip

            historical = list(
                (
                    await session.scalars(
                        select(SessionDecisionV2)
                        .where(SessionDecisionV2.session_id == first_session_id)
                        .order_by(SessionDecisionV2.created_at.asc())
                    )
                ).all()
            )
            assert [decision.id for decision in historical] == [
                first_wait.id,
                second_wait.id,
                skip.id,
            ]

        invalid_decisions = [
            decision_data(first_session_id, decision="INVALID"),  # type: ignore[arg-type]
            decision_data(
                first_session_id,
                reason="INVALID",  # type: ignore[arg-type]
            ),
        ]
        for data in invalid_decisions:
            with pytest.raises((IntegrityError, StatementError)):
                async with session.begin():
                    session.add(SessionDecisionV2(**data))
                    await session.flush()

        with pytest.raises(IntegrityError):
            async with session.begin():
                session.add(
                    SessionDecisionV2(
                        **decision_data(
                            second_session_id,
                            decision=SessionDecisionV2Decision.BUY,
                        )
                    )
                )
                await session.flush()

        await session.close()

        async with factory() as cleanup_session:
            async with cleanup_session.begin():
                await cleanup_session.execute(
                    delete(SessionDecisionV2).where(
                        SessionDecisionV2.session_id.in_([first_session_id, second_session_id])
                    )
                )
                await cleanup_session.execute(
                    delete(TradeSessionV2).where(
                        TradeSessionV2.id.in_([first_session_id, second_session_id])
                    )
                )
                await cleanup_session.execute(delete(User).where(User.id == user_id))
