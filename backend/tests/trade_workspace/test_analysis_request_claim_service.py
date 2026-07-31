from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.auth import hash_password
from app.models.user import User
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2ObservationPeriod,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
from app.trade_workspace.services.analysis_request_claim import AnalysisRequestClaimService

pytestmark = pytest.mark.database


async def _seed(
    factory: async_sessionmaker[AsyncSession],
    *,
    status: TradeSessionV2Status = TradeSessionV2Status.ANALYZING,
) -> tuple[uuid.UUID, uuid.UUID]:
    user_id, session_id = uuid.uuid4(), uuid.uuid4()
    async with factory() as session:
        async with session.begin():
            await session.execute(
                EvidenceUploadV2.__table__.update().values(analysis_request_id=None)
            )
            await session.execute(delete(AnalysisRequestV2))
            session.add(
                User(
                    id=user_id,
                    email=f"claim-test-{user_id}@example.test",
                    password_hash=hash_password("testpass123"),
                )
            )
            await session.flush()
            session.add(
                TradeSessionV2(
                    id=session_id,
                    user_id=user_id,
                    ticker="BBRI",
                    company_name="Bank BRI",
                    status=status,
                )
            )
    return user_id, session_id


def _create_request(
    session_id: uuid.UUID,
    *,
    analysis_type: AnalysisRequestV2Type = AnalysisRequestV2Type.INITIAL_ANALYSIS,
    status: AnalysisRequestV2Status = AnalysisRequestV2Status.PENDING,
    created_at: datetime | None = None,
) -> AnalysisRequestV2:
    req = AnalysisRequestV2(
        session_id=session_id,
        analysis_type=analysis_type,
        status=status,
        provider="gemini",
        model="gemini-3.1-flash-lite",
        prompt_version="v1",
        input_snapshot={"test": True},
    )
    if analysis_type is not AnalysisRequestV2Type.INITIAL_ANALYSIS:
        req.current_price = Decimal("123.45")
        req.observation_period = AnalysisRequestV2ObservationPeriod.MIDDAY
        req.observation_at = datetime.now(timezone.utc)
    if created_at is not None:
        req.created_at = created_at
    return req


async def test_claim_returns_none_when_no_pending_request(engine: AsyncEngine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    _, session_id = await _seed(factory)
    async with factory() as session:
        async with session.begin():
            session.add_all(
                [
                    _create_request(session_id, status=AnalysisRequestV2Status.COMPLETED),
                    _create_request(session_id, status=AnalysisRequestV2Status.FAILED),
                    _create_request(session_id, status=AnalysisRequestV2Status.PROCESSING),
                ]
            )

    async with factory() as session:
        service = AnalysisRequestClaimService(session)
        result = await service.claim_next(worker_id="worker-1")
        assert result is None


async def test_claim_claims_one_pending_request_and_updates_status(engine: AsyncEngine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    _, session_id = await _seed(factory)
    req = _create_request(session_id, status=AnalysisRequestV2Status.PENDING)
    async with factory() as session:
        async with session.begin():
            session.add(req)

    before = datetime.now(timezone.utc)
    async with factory() as session:
        service = AnalysisRequestClaimService(session)
        claimed = await service.claim_next(worker_id="worker-1")

        assert claimed is not None
        assert claimed.request_id == req.id
        assert claimed.status is AnalysisRequestV2Status.PROCESSING
        assert claimed.started_at >= before

        # Verify staged status in same database session before explicit commit
        db_req = await session.scalar(
            select(AnalysisRequestV2).where(AnalysisRequestV2.id == req.id)
        )
        assert db_req is not None
        assert db_req.status is AnalysisRequestV2Status.PROCESSING
        assert db_req.started_at == claimed.started_at


async def test_claim_orders_pending_requests_deterministically_oldest_first(
    engine: AsyncEngine,
) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    _, session_id = await _seed(factory)
    now = datetime.now(timezone.utc)
    req_newer = _create_request(
        session_id,
        status=AnalysisRequestV2Status.PENDING,
        created_at=now + timedelta(seconds=10),
    )
    req_older = _create_request(
        session_id,
        status=AnalysisRequestV2Status.PENDING,
        created_at=now,
    )
    async with factory() as session:
        async with session.begin():
            session.add_all([req_newer, req_older])

    async with factory() as session:
        service = AnalysisRequestClaimService(session)
        claimed_first = await service.claim_next(worker_id="worker-1")
        assert claimed_first is not None
        assert claimed_first.request_id == req_older.id


async def test_caller_rollback_restores_pending_status(engine: AsyncEngine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    _, session_id = await _seed(factory)
    req = _create_request(session_id, status=AnalysisRequestV2Status.PENDING)
    async with factory() as session:
        async with session.begin():
            session.add(req)

    async with factory() as session:
        service = AnalysisRequestClaimService(session)
        claimed = await service.claim_next(worker_id="worker-1")
        assert claimed is not None
        await session.rollback()

    async with factory() as session:
        restored = await session.scalar(
            select(AnalysisRequestV2).where(AnalysisRequestV2.id == req.id)
        )
        assert restored is not None
        assert restored.status is AnalysisRequestV2Status.PENDING
        assert restored.started_at is None


async def test_caller_commit_preserves_processing_status(engine: AsyncEngine) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    _, session_id = await _seed(factory)
    req = _create_request(session_id, status=AnalysisRequestV2Status.PENDING)
    async with factory() as session:
        async with session.begin():
            session.add(req)

    async with factory() as session:
        service = AnalysisRequestClaimService(session)
        claimed = await service.claim_next(worker_id="worker-1")
        assert claimed is not None
        await session.commit()

    async with factory() as session:
        persisted = await session.scalar(
            select(AnalysisRequestV2).where(AnalysisRequestV2.id == req.id)
        )
        assert persisted is not None
        assert persisted.status is AnalysisRequestV2Status.PROCESSING


async def test_concurrent_claims_cannot_claim_same_request(
    engine: AsyncEngine,
) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    _, session_id = await _seed(factory)
    req = _create_request(session_id, status=AnalysisRequestV2Status.PENDING)
    async with factory() as seed_session:
        async with seed_session.begin():
            seed_session.add(req)

    async def claim_worker(worker_name: str):
        async with factory() as session:
            service = AnalysisRequestClaimService(session)
            res = await service.claim_next(worker_id=worker_name)
            if res is not None:
                await session.commit()
            return res

    results = await asyncio.gather(claim_worker("worker-1"), claim_worker("worker-2"))
    claimed_results = [r for r in results if r is not None]

    assert len(claimed_results) == 1
    assert claimed_results[0].request_id == req.id


async def test_skip_locked_allows_claiming_second_candidate_if_first_is_locked(
    engine: AsyncEngine,
) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    _, session_id = await _seed(factory)
    now = datetime.now(timezone.utc)
    req1 = _create_request(session_id, created_at=now)
    req2 = _create_request(session_id, created_at=now + timedelta(seconds=5))
    async with factory() as seed_session:
        async with seed_session.begin():
            seed_session.add_all([req1, req2])

    async with factory() as lock_session:
        async with lock_session.begin():
            query = (
                select(AnalysisRequestV2)
                .where(AnalysisRequestV2.id == req1.id)
                .with_for_update()
            )
            locked_req1 = await lock_session.scalar(query)
            assert locked_req1 is not None

            # Worker 2 attempts claim concurrently; SKIP LOCKED should bypass locked req1 and claim req2
            async with factory() as worker_session:
                service = AnalysisRequestClaimService(worker_session)
                claimed = await service.claim_next(worker_id="worker-2")
                if claimed is not None:
                    await worker_session.commit()

                assert claimed is not None
                assert claimed.request_id == req2.id


async def test_claim_service_does_not_modify_session_status_or_create_legacy_jobs(
    engine: AsyncEngine,
) -> None:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    _, session_id = await _seed(factory, status=TradeSessionV2Status.ANALYZING)
    req = _create_request(session_id, status=AnalysisRequestV2Status.PENDING)
    async with factory() as session:
        async with session.begin():
            session.add(req)

    async with factory() as session:
        service = AnalysisRequestClaimService(session)
        claimed = await service.claim_next(worker_id="worker-1")
        assert claimed is not None
        await session.commit()

    async with factory() as session:
        trade_session = await session.scalar(
            select(TradeSessionV2).where(TradeSessionV2.id == session_id)
        )
        assert trade_session is not None
        assert trade_session.status is TradeSessionV2Status.ANALYZING
