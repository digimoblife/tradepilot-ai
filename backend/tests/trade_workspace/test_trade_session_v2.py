from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status


@pytest.mark.database
async def test_trade_sessions_v2_persistence(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    user_id = uuid.uuid4()
    older = datetime.now(timezone.utc) - timedelta(days=1)

    async with factory() as session:
        async with session.begin():
            user = User(
                id=user_id,
                email=f"p31-{user_id}@example.test",
                password_hash="test-only",
            )
            session.add(user)
            first = TradeSessionV2(
                user_id=user_id,
                ticker=" bbri ",
                company_name=" Bank BRI ",
                note="owned note",
                created_at=older,
                updated_at=older,
            )
            second = TradeSessionV2(
                user_id=user_id,
                ticker="TLKM",
                company_name="Telkom Indonesia",
            )
            session.add_all([first, second])
            await session.flush()

            assert first.id is not None
            assert first.status is TradeSessionV2Status.DRAFT
            assert first.user_id == user_id
            assert first.ticker == "BBRI"
            assert first.company_name == "Bank BRI"
            assert first.archived_at is None
            assert TradeSessionV2.__table__.c.archived_at.nullable is True
            assert "ARCHIVED" not in TradeSessionV2Status.__members__

            read = await session.scalar(
                select(TradeSessionV2).where(
                    TradeSessionV2.id == first.id,
                    TradeSessionV2.user_id == user_id,
                )
            )
            assert read is first
            assert read.note == "owned note"

            historical = list(
                (
                    await session.scalars(
                        select(TradeSessionV2)
                        .where(TradeSessionV2.user_id == user_id)
                        .order_by(TradeSessionV2.created_at.asc())
                    )
                ).all()
            )
            assert [item.id for item in historical] == [first.id, second.id]

        with pytest.raises((StatementError, IntegrityError)):
            async with session.begin():
                session.add(
                    TradeSessionV2(
                        user_id=user_id,
                        ticker="BBCA",
                        company_name="Bank Central Asia",
                        status="INVALID",  # type: ignore[arg-type]
                    )
                )
                await session.flush()

        with pytest.raises(IntegrityError):
            async with session.begin():
                session.add(
                    TradeSessionV2(
                        user_id=user_id,
                        ticker="   ",
                        company_name="Valid Company",
                    )
                )
                await session.flush()

        with pytest.raises(IntegrityError):
            async with session.begin():
                session.add(
                    TradeSessionV2(
                        user_id=user_id,
                        ticker="BBCA",
                        company_name="   ",
                    )
                )
                await session.flush()

        with pytest.raises(IntegrityError):
            async with session.begin():
                session.add(
                    TradeSessionV2(
                        user_id=user_id,
                        company_name="Missing Ticker",
                    )
                )
                await session.flush()

        with pytest.raises(IntegrityError):
            async with session.begin():
                session.add(
                    TradeSessionV2(
                        user_id=user_id,
                        ticker="BBCA",
                    )
                )
                await session.flush()

        await session.close()

        async with factory() as cleanup_session:
            async with cleanup_session.begin():
                await cleanup_session.execute(
                    delete(TradeSessionV2).where(TradeSessionV2.user_id == user_id)
                )
                await cleanup_session.execute(
                    delete(User).where(User.id == user_id)
                )
