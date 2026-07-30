from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User
from app.trade_workspace.models.position import PositionV2
from app.trade_workspace.models.trade_closure import TradeClosureV2
from app.trade_workspace.models.trade_session import TradeSessionV2


def closure_data(
    session_id: uuid.UUID,
    position_id: uuid.UUID,
    **overrides: object,
) -> dict[str, object]:
    data: dict[str, object] = {
        "session_id": session_id,
        "position_id": position_id,
        "close_price": Decimal("105.50"),
        "close_at": datetime.now(timezone.utc),
        "close_reason": "USER_DECISION",
        "realized_profit_loss": Decimal("55.125000"),
    }
    data.update(overrides)
    return data


def position_data(session_id: uuid.UUID) -> dict[str, object]:
    return {
        "session_id": session_id,
        "entry_price": Decimal("100.25"),
        "entry_at": datetime.now(timezone.utc) - timedelta(days=2),
        "quantity": Decimal("10.5"),
        "stop_loss": Decimal("95.00"),
        "target_price": Decimal("110.00"),
    }


@pytest.mark.database
async def test_trade_closures_v2_persistence(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    user_id = uuid.uuid4()
    older = datetime.now(timezone.utc) - timedelta(days=1)

    assert not {"provider", "model", "gemini"} & set(
        TradeClosureV2.__table__.columns.keys()
    )

    async with factory() as session:
        async with session.begin():
            session.add(
                User(
                    id=user_id,
                    email=f"p36-{user_id}@example.test",
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
            third_session = TradeSessionV2(
                user_id=user_id,
                ticker="BMRI",
                company_name="Bank Mandiri",
            )
            session.add_all([first_session, second_session, third_session])
            await session.flush()
            first_session_id = first_session.id
            second_session_id = second_session.id
            third_session_id = third_session.id

            first_position = PositionV2(**position_data(first_session_id))
            second_position = PositionV2(**position_data(second_session_id))
            third_position = PositionV2(**position_data(third_session_id))
            session.add_all([first_position, second_position, third_position])
            await session.flush()
            first_position_id = first_position.id
            second_position_id = second_position.id
            third_position_id = third_position.id

            first_closure = TradeClosureV2(
                **closure_data(
                    first_session_id,
                    first_position_id,
                    created_at=older,
                )
            )
            second_closure = TradeClosureV2(
                **closure_data(
                    second_session_id,
                    second_position_id,
                    realized_profit_loss=Decimal("0"),
                    note=None,
                    created_at=older + timedelta(hours=1),
                )
            )
            negative_closure = TradeClosureV2(
                **closure_data(
                    third_session_id,
                    third_position_id,
                    realized_profit_loss=Decimal("-12.50"),
                    created_at=older + timedelta(hours=2),
                )
            )
            session.add_all([first_closure, second_closure])
            await session.flush()

            assert first_closure.session_id == first_session_id
            assert first_closure.position_id == first_position_id
            assert first_closure.note is None
            assert first_closure.realized_profit_loss == Decimal("55.125000")
            assert second_closure.realized_profit_loss == Decimal("0.000000")

            read = await session.scalar(
                select(TradeClosureV2).where(TradeClosureV2.id == first_closure.id)
            )
            assert read is first_closure

            historical = list(
                (
                    await session.scalars(
                        select(TradeClosureV2).order_by(TradeClosureV2.created_at.asc())
                    )
                ).all()
            )
            assert [closure.id for closure in historical] == [
                first_closure.id,
                second_closure.id,
            ]

            session.add(negative_closure)
            await session.flush()
            assert negative_closure.realized_profit_loss == Decimal("-12.500000")

        invalid_closures = [
            closure_data(first_session_id, first_position_id, close_price=0),
            closure_data(first_session_id, first_position_id, close_price=-1),
            closure_data(first_session_id, first_position_id, close_reason=""),
            closure_data(first_session_id, first_position_id, close_reason="   "),
        ]
        for data in invalid_closures:
            with pytest.raises((IntegrityError, StatementError)):
                async with session.begin():
                    session.add(TradeClosureV2(**data))
                    await session.flush()

        with pytest.raises(IntegrityError):
            async with session.begin():
                session.add(TradeClosureV2(**closure_data(first_session_id, first_position_id)))
                await session.flush()

        await session.close()

        async with factory() as cleanup_session:
            async with cleanup_session.begin():
                await cleanup_session.execute(
                    delete(TradeClosureV2).where(
                        TradeClosureV2.session_id.in_(
                            [first_session_id, second_session_id, third_session_id]
                        )
                    )
                )
                await cleanup_session.execute(
                    delete(PositionV2).where(
                        PositionV2.session_id.in_(
                            [first_session_id, second_session_id, third_session_id]
                        )
                    )
                )
                await cleanup_session.execute(
                    delete(TradeSessionV2).where(
                        TradeSessionV2.id.in_(
                            [first_session_id, second_session_id, third_session_id]
                        )
                    )
                )
                await cleanup_session.execute(delete(User).where(User.id == user_id))
