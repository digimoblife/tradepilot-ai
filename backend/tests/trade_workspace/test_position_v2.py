from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User
from app.trade_workspace.models.position import PositionV2, PositionV2Status
from app.trade_workspace.models.trade_session import TradeSessionV2


def position_data(session_id: uuid.UUID, **overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "session_id": session_id,
        "entry_price": Decimal("100.25"),
        "entry_at": datetime.now(timezone.utc),
        "quantity": Decimal("10.5"),
        "stop_loss": Decimal("95.00"),
        "target_price": Decimal("110.00"),
    }
    data.update(overrides)
    return data


@pytest.mark.database
async def test_positions_v2_persistence(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    user_id = uuid.uuid4()
    older = datetime.now(timezone.utc) - timedelta(days=1)

    assert not {"provider", "model", "gemini"} & set(PositionV2.__table__.columns.keys())

    async with factory() as session:
        async with session.begin():
            session.add(
                User(
                    id=user_id,
                    email=f"p35-{user_id}@example.test",
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

            position = PositionV2(
                **position_data(first_session_id, created_at=older)
            )
            closed_position = PositionV2(
                **position_data(
                    second_session_id,
                    status=PositionV2Status.CLOSED,
                    closed_at=older + timedelta(hours=2),
                    created_at=older + timedelta(hours=1),
                )
            )
            session.add_all([position, closed_position])
            await session.flush()

            assert position.status is PositionV2Status.OPEN
            assert position.session_id == first_session_id
            assert position.closed_at is None
            assert closed_position.status is PositionV2Status.CLOSED
            assert closed_position.session_id == second_session_id

            read = await session.scalar(
                select(PositionV2).where(PositionV2.id == position.id)
            )
            assert read is position

            historical = list(
                (
                    await session.scalars(
                        select(PositionV2).order_by(PositionV2.created_at.asc())
                    )
                ).all()
            )
            assert [item.id for item in historical] == [position.id, closed_position.id]

        invalid_positions = [
            position_data(first_session_id, status="INVALID"),  # type: ignore[arg-type]
            position_data(first_session_id, entry_price=0),
            position_data(first_session_id, entry_price=-1),
            position_data(first_session_id, quantity=0),
            position_data(first_session_id, quantity=-1),
            position_data(first_session_id, stop_loss=0),
            position_data(first_session_id, stop_loss=-1),
            position_data(first_session_id, target_price=0),
            position_data(first_session_id, target_price=-1),
        ]
        for data in invalid_positions:
            with pytest.raises((IntegrityError, StatementError)):
                async with session.begin():
                    session.add(PositionV2(**data))
                    await session.flush()

        with pytest.raises(IntegrityError):
            async with session.begin():
                session.add(PositionV2(**position_data(first_session_id)))
                await session.flush()

        await session.close()

        async with factory() as cleanup_session:
            async with cleanup_session.begin():
                await cleanup_session.execute(
                    delete(PositionV2).where(
                        PositionV2.session_id.in_([first_session_id, second_session_id])
                    )
                )
                await cleanup_session.execute(
                    delete(TradeSessionV2).where(
                        TradeSessionV2.id.in_([first_session_id, second_session_id])
                    )
                )
                await cleanup_session.execute(delete(User).where(User.id == user_id))
