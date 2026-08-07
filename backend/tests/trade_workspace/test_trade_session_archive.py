from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.user import User
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.position import PositionV2, PositionV2Status
from app.trade_workspace.models.session_decision import (
    SessionDecisionV2,
    SessionDecisionV2Decision,
)
from app.trade_workspace.models.trade_closure import TradeClosureV2
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
from app.trade_workspace.services.trade_sessions import (
    ArchiveAlreadyArchivedError,
    ArchiveNotAllowedError,
    ArchiveSessionNotFoundError,
    RebuildTradeSessionService,
    RestoreNotArchivedError,
)


async def _seed_session(
    factory: async_sessionmaker[AsyncSession],
    *,
    status: TradeSessionV2Status,
    archived_at: datetime | None = None,
    with_related: bool = False,
) -> tuple[uuid.UUID, uuid.UUID, datetime]:
    user_id = uuid.uuid4()
    closed_at = datetime.now(timezone.utc) - timedelta(hours=1)
    async with factory() as session:
        async with session.begin():
            session.add(
                User(
                    id=user_id,
                    email=f"ux12-{user_id}@example.test",
                    password_hash="test-only",
                )
            )
            trade_session = TradeSessionV2(
                user_id=user_id,
                ticker="BBRI",
                company_name="Bank BRI",
                status=status,
                closed_at=closed_at if status in {
                    TradeSessionV2Status.CLOSED,
                    TradeSessionV2Status.CLOSED_SKIPPED,
                } else None,
                archived_at=archived_at,
            )
            session.add(trade_session)
            await session.flush()

            if with_related:
                request = AnalysisRequestV2(
                    session_id=trade_session.id,
                    analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                    status=AnalysisRequestV2Status.COMPLETED,
                    provider="gemini",
                    model="gemini-3.1-flash-lite",
                    prompt_version="v1",
                    input_snapshot={"fixture": True},
                    processed_response={"fixture": True},
                )
                session.add(request)
                await session.flush()
                session.add(
                    EvidenceUploadV2(
                        session_id=trade_session.id,
                        analysis_request_id=request.id,
                        evidence_type=EvidenceUploadV2Type.ORDERBOOK,
                        file_path="fixture/orderbook.png",
                        original_filename="orderbook.png",
                        mime_type="image/png",
                        size_bytes=10,
                    )
                )
                position = PositionV2(
                    session_id=trade_session.id,
                    entry_price=Decimal("100"),
                    entry_at=closed_at - timedelta(days=1),
                    quantity=Decimal("1"),
                    stop_loss=Decimal("95"),
                    target_price=Decimal("110"),
                    status=PositionV2Status.CLOSED,
                    closed_at=closed_at,
                )
                session.add(position)
                session.add(
                    SessionDecisionV2(
                        session_id=trade_session.id,
                        decision=SessionDecisionV2Decision.BUY,
                    )
                )
                await session.flush()
                session.add(
                    TradeClosureV2(
                        session_id=trade_session.id,
                        position_id=position.id,
                        close_price=Decimal("105"),
                        close_at=closed_at,
                        close_reason="USER_DECISION",
                        realized_profit_loss=Decimal("5"),
                    )
                )
                await session.flush()

            session_id = trade_session.id

    return user_id, session_id, closed_at


async def _cleanup(factory: async_sessionmaker[AsyncSession], user_id: uuid.UUID) -> None:
    async with factory() as session:
        async with session.begin():
            session_ids = select(TradeSessionV2.id).where(TradeSessionV2.user_id == user_id)
            await session.execute(
                delete(TradeClosureV2).where(TradeClosureV2.session_id.in_(session_ids))
            )
            await session.execute(
                delete(SessionDecisionV2).where(SessionDecisionV2.session_id.in_(session_ids))
            )
            await session.execute(
                delete(EvidenceUploadV2).where(EvidenceUploadV2.session_id.in_(session_ids))
            )
            await session.execute(
                delete(AnalysisRequestV2).where(AnalysisRequestV2.session_id.in_(session_ids))
            )
            await session.execute(
                delete(PositionV2).where(PositionV2.session_id.in_(session_ids))
            )
            await session.execute(delete(TradeSessionV2).where(TradeSessionV2.user_id == user_id))
            await session.execute(delete(User).where(User.id == user_id))


@pytest.mark.database
async def test_archive_and_restore_terminal_sessions_preserve_state(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    for status in (TradeSessionV2Status.CLOSED, TradeSessionV2Status.CLOSED_SKIPPED):
        user_id, session_id, closed_at = await _seed_session(
            factory, status=status, with_related=True
        )
        try:
            async with factory() as session:
                result = await RebuildTradeSessionService(session).archive(
                    user_id=user_id, session_id=session_id
                )
                assert result.session_status is status
                assert result.archived_at is not None
                assert result.archived_at.tzinfo is not None

            async with factory() as session:
                archived = await session.scalar(
                    select(TradeSessionV2).where(TradeSessionV2.id == session_id)
                )
                assert archived is not None
                assert archived.status is status
                assert archived.closed_at == closed_at
                assert archived.archived_at is not None
                counts_before = {
                    table: await session.scalar(select(func.count()).select_from(model))
                    for table, model in {
                        "requests": AnalysisRequestV2,
                        "evidence": EvidenceUploadV2,
                        "decisions": SessionDecisionV2,
                        "positions": PositionV2,
                        "closures": TradeClosureV2,
                    }.items()
                }

            async with factory() as session:
                result = await RebuildTradeSessionService(session).restore(
                    user_id=user_id, session_id=session_id
                )
                assert result.session_status is status
                assert result.archived_at is None

            async with factory() as session:
                restored = await session.scalar(
                    select(TradeSessionV2).where(TradeSessionV2.id == session_id)
                )
                assert restored is not None
                assert restored.status is status
                assert restored.closed_at == closed_at
                assert restored.archived_at is None
                counts_after = {
                    table: await session.scalar(select(func.count()).select_from(model))
                    for table, model in {
                        "requests": AnalysisRequestV2,
                        "evidence": EvidenceUploadV2,
                        "decisions": SessionDecisionV2,
                        "positions": PositionV2,
                        "closures": TradeClosureV2,
                    }.items()
                }
                assert counts_after == counts_before
        finally:
            await _cleanup(factory, user_id)


@pytest.mark.database
@pytest.mark.parametrize(
    "status",
    [
        TradeSessionV2Status.DRAFT,
        TradeSessionV2Status.ANALYZING,
        TradeSessionV2Status.ANALYZED,
        TradeSessionV2Status.WAITING,
        TradeSessionV2Status.OPEN_POSITION,
    ],
)
async def test_archive_rejects_non_terminal_sessions(engine, status: TradeSessionV2Status) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    user_id, session_id, _ = await _seed_session(factory, status=status)
    try:
        async with factory() as session:
            with pytest.raises(ArchiveNotAllowedError):
                await RebuildTradeSessionService(session).archive(
                    user_id=user_id, session_id=session_id
                )
    finally:
        await _cleanup(factory, user_id)


@pytest.mark.database
async def test_archive_restore_idempotency_and_owner_scope(engine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    owner_id, session_id, _ = await _seed_session(
        factory, status=TradeSessionV2Status.CLOSED
    )
    other_id, _, _ = await _seed_session(factory, status=TradeSessionV2Status.CLOSED)
    try:
        async with factory() as session:
            service = RebuildTradeSessionService(session)
            with pytest.raises(ArchiveSessionNotFoundError):
                await service.archive(user_id=other_id, session_id=session_id)
            await service.archive(user_id=owner_id, session_id=session_id)

        async with factory() as session:
            with pytest.raises(ArchiveAlreadyArchivedError):
                await RebuildTradeSessionService(session).archive(
                    user_id=owner_id, session_id=session_id
                )
            with pytest.raises(ArchiveSessionNotFoundError):
                await RebuildTradeSessionService(session).restore(
                    user_id=other_id, session_id=session_id
                )

        async with factory() as session:
            await RebuildTradeSessionService(session).restore(
                user_id=owner_id, session_id=session_id
            )

        async with factory() as session:
            with pytest.raises(RestoreNotArchivedError):
                await RebuildTradeSessionService(session).restore(
                    user_id=owner_id, session_id=session_id
                )
    finally:
        await _cleanup(factory, owner_id)
        await _cleanup(factory, other_id)
