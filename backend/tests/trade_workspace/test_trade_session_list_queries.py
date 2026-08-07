from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
from app.trade_workspace.services.trade_sessions import RebuildTradeSessionService


@pytest.mark.database
async def test_owned_lists_separate_archive_state_and_preserve_ordering(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    owner_id = uuid.uuid4()
    other_owner_id = uuid.uuid4()
    base_time = datetime(2026, 8, 1, tzinfo=timezone.utc)
    non_archived_statuses = [
        TradeSessionV2Status.DRAFT,
        TradeSessionV2Status.ANALYZING,
        TradeSessionV2Status.ANALYZED,
        TradeSessionV2Status.WAITING,
        TradeSessionV2Status.OPEN_POSITION,
        TradeSessionV2Status.CLOSED,
        TradeSessionV2Status.CLOSED_SKIPPED,
    ]

    async with factory() as session:
        async with session.begin():
            session.add_all(
                [
                    User(
                        id=owner_id,
                        email=f"ux13-owner-{owner_id}@example.test",
                        password_hash="test-only",
                    ),
                    User(
                        id=other_owner_id,
                        email=f"ux13-other-{other_owner_id}@example.test",
                        password_hash="test-only",
                    ),
                ]
            )
            non_archived = [
                TradeSessionV2(
                    user_id=owner_id,
                    ticker=f"N{index:02d}",
                    company_name=f"Non Archived {index}",
                    status=status,
                    created_at=base_time + timedelta(hours=index),
                    updated_at=base_time + timedelta(hours=index),
                )
                for index, status in enumerate(non_archived_statuses)
            ]
            archived = [
                TradeSessionV2(
                    user_id=owner_id,
                    ticker="AC01",
                    company_name="Archived Closed",
                    status=TradeSessionV2Status.CLOSED,
                    created_at=base_time + timedelta(hours=10),
                    updated_at=base_time + timedelta(hours=10),
                    archived_at=base_time + timedelta(hours=11),
                ),
                TradeSessionV2(
                    user_id=owner_id,
                    ticker="AC02",
                    company_name="Archived Skipped",
                    status=TradeSessionV2Status.CLOSED_SKIPPED,
                    created_at=base_time + timedelta(hours=11),
                    updated_at=base_time + timedelta(hours=11),
                    archived_at=base_time + timedelta(hours=12),
                ),
            ]
            other = TradeSessionV2(
                user_id=other_owner_id,
                ticker="OTHER",
                company_name="Other Owner",
                status=TradeSessionV2Status.CLOSED,
                created_at=base_time + timedelta(hours=20),
                updated_at=base_time + timedelta(hours=20),
                archived_at=base_time + timedelta(hours=21),
            )
            session.add_all([*non_archived, *archived, other])
            await session.flush()
            non_archived_ids = [item.id for item in reversed(non_archived)]
            archived_ids = [item.id for item in reversed(archived)]
            other_id = other.id

    try:
        async with factory() as session:
            service = RebuildTradeSessionService(session)
            assert [
                item.id for item in await service.list_owned(user_id=owner_id)
            ] == non_archived_ids
            assert [
                item.id for item in await service.list_owned_archived(user_id=owner_id)
            ] == archived_ids

            assert await service.list_owned(user_id=uuid.uuid4()) == []
            assert await service.list_owned_archived(user_id=uuid.uuid4()) == []

            assert (
                await service.get_owned(user_id=owner_id, session_id=archived_ids[0])
            ).id == archived_ids[0]
            assert (
                await service.get_owned(user_id=owner_id, session_id=non_archived_ids[0])
            ).id == non_archived_ids[0]
            assert await service.get_owned(user_id=owner_id, session_id=other_id) is None
            assert (
                await service.get_owned(user_id=uuid.uuid4(), session_id=archived_ids[0])
                is None
            )
            assert await service.get_owned(user_id=owner_id, session_id=uuid.uuid4()) is None

            before = {
                item.id: (item.status, item.archived_at)
                for item in [*non_archived, *archived]
            }
            after_rows = await session.scalars(
                select(TradeSessionV2).where(TradeSessionV2.user_id == owner_id)
            )
            assert {
                row.id: (row.status, row.archived_at)
                for row in after_rows
            } == before
    finally:
        async with factory() as session:
            async with session.begin():
                await session.execute(
                    delete(TradeSessionV2).where(
                        TradeSessionV2.user_id.in_([owner_id, other_owner_id])
                    )
                )
                await session.execute(
                    delete(User).where(User.id.in_([owner_id, other_owner_id]))
                )
