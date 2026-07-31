from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.api.exception_handlers import register_handlers
from app.auth import hash_password
from app.config import AppConfig
from app.database.session import get_db_session
from app.models.user import User
from app.trade_workspace.api.routes.trade_sessions import router as rebuild_router
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2ObservationPeriod,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status

pytestmark = pytest.mark.database

OBSERVATION = datetime(2026, 7, 30, 2, 15, tzinfo=timezone.utc)


class RecordingQueue:
    def __init__(self, *, fail: bool = False, delay: float = 0) -> None:
        self.calls: list[uuid.UUID] = []
        self.fail = fail
        self.delay = delay

    async def enqueue(self, *, analysis_request_id: uuid.UUID) -> None:
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError("queue unavailable")
        self.calls.append(analysis_request_id)


async def _seed(
    engine: AsyncEngine,
    *,
    status: TradeSessionV2Status = TradeSessionV2Status.WAITING,
    ticker: str = "BBRI",
    email_prefix: str = "p72",
    evidence: bool = True,
) -> tuple[uuid.UUID, uuid.UUID, str]:
    user_id, session_id = uuid.uuid4(), uuid.uuid4()
    email = f"{email_prefix}-{user_id}@example.test"
    async with engine.begin() as connection:
        await connection.execute(
            User.__table__.insert().values(
                id=user_id, email=email, password_hash=hash_password("testpass123")
            )
        )
        await connection.execute(
            TradeSessionV2.__table__.insert().values(
                id=session_id,
                user_id=user_id,
                ticker=ticker,
                company_name="Bank BRI",
                status=status,
            )
        )
        if evidence:
            await connection.execute(
                EvidenceUploadV2.__table__.insert().values(
                    id=uuid.uuid4(),
                    session_id=session_id,
                    evidence_type=EvidenceUploadV2Type.ORDERBOOK,
                    observation_period=AnalysisRequestV2ObservationPeriod.MIDDAY,
                    current_price=Decimal("1234.567890"),
                    observation_timestamp=OBSERVATION,
                    file_path=f"{session_id}/orderbook.png",
                    original_filename="orderbook.png",
                    mime_type="image/png",
                    size_bytes=10,
                )
            )
    return user_id, session_id, email


def _app(db_session: AsyncSession) -> FastAPI:
    app = FastAPI()
    register_handlers(app)
    app.include_router(auth_router)
    app.include_router(rebuild_router)

    async def override_db() -> AsyncSession:
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db_session] = override_db
    return app


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


async def _login(client: AsyncClient, email: str) -> None:
    response = await client.post(
        "/api/auth/login", json={"email": email, "password": "testpass123"}
    )
    assert response.status_code == 200


def _request(
    session_id: uuid.UUID,
    *,
    status: AnalysisRequestV2Status,
    analysis_type: AnalysisRequestV2Type = AnalysisRequestV2Type.WAIT_UPDATE,
) -> AnalysisRequestV2:
    return AnalysisRequestV2(
        session_id=session_id,
        analysis_type=analysis_type,
        observation_period=(
            AnalysisRequestV2ObservationPeriod.MIDDAY
            if analysis_type is not AnalysisRequestV2Type.INITIAL_ANALYSIS
            else None
        ),
        current_price=Decimal("1234.567890")
        if analysis_type is not AnalysisRequestV2Type.INITIAL_ANALYSIS
        else None,
        observation_at=(
            OBSERVATION
            if analysis_type is not AnalysisRequestV2Type.INITIAL_ANALYSIS
            else None
        ),
        status=status,
        provider="gemini",
        model=AppConfig().gemini_model,
        prompt_version="v1",
        input_snapshot={"preserved": True},
    )


async def test_owner_can_submit_wait_update_analysis_from_waiting_session(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, email = await _seed(engine)
    app = _app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(client, email)
        response = await client.post(f"/api/v2/trade-sessions/{session_id}/wait-updates")

    assert response.status_code == 202
    payload = response.json()
    request_id = uuid.UUID(payload["analysis_request_id"])
    evidence_id = uuid.UUID(payload["evidence_id"])
    assert payload == {
        "analysis_request_id": str(request_id),
        "session_id": str(session_id),
        "analysis_type": "WAIT_UPDATE",
        "request_status": "PENDING",
        "evidence_id": str(evidence_id),
        "observation_period": "MIDDAY",
        "session_status": "ANALYZING",
        "created_at": payload["created_at"],
    }

    request = await db_session.scalar(
        select(AnalysisRequestV2).where(AnalysisRequestV2.id == request_id)
    )
    assert request is not None
    assert request.session_id == session_id
    assert request.analysis_type is AnalysisRequestV2Type.WAIT_UPDATE
    assert request.status is AnalysisRequestV2Status.PENDING
    assert request.provider == "gemini"
    assert request.model == "gemini-3.1-flash-lite"
    assert request.prompt_version == "v1"
    assert request.observation_period is AnalysisRequestV2ObservationPeriod.MIDDAY
    assert request.current_price == Decimal("1234.567890")
    assert request.observation_at == OBSERVATION
    assert request.input_snapshot == {
        "session_id": str(session_id),
        "ticker": "BBRI",
        "company_name": "Bank BRI",
        "analysis_type": "WAIT_UPDATE",
        "evidence_id": str(evidence_id),
        "current_price": "1234.567890",
        "observation_period": "MIDDAY",
        "observation_timestamp": OBSERVATION.isoformat(),
        "provider": "gemini",
        "model": "gemini-3.1-flash-lite",
        "prompt_version": "v1",
    }

    evidence = await db_session.scalar(
        select(EvidenceUploadV2).where(EvidenceUploadV2.id == evidence_id)
    )
    assert evidence is not None
    assert evidence.analysis_request_id == request_id
    session = await db_session.scalar(
        select(TradeSessionV2).where(TradeSessionV2.id == session_id)
    )
    assert session is not None
    assert session.status is TradeSessionV2Status.ANALYZING
    assert session.closed_at is None


async def test_latest_eligible_evidence_is_selected_deterministically(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, email = await _seed(engine, evidence=False, email_prefix="p72-order")
    older_id, newer_id, tied_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    older = OBSERVATION - timedelta(hours=2)
    newer = OBSERVATION + timedelta(hours=1)
    async with engine.begin() as connection:
        await connection.execute(
            EvidenceUploadV2.__table__.insert(),
            [
                {
                    "id": older_id,
                    "session_id": session_id,
                    "evidence_type": EvidenceUploadV2Type.ORDERBOOK,
                    "observation_period": AnalysisRequestV2ObservationPeriod.MORNING,
                    "current_price": Decimal("100"),
                    "observation_timestamp": older,
                    "file_path": f"{session_id}/older.png",
                    "original_filename": "older.png",
                    "mime_type": "image/png",
                    "size_bytes": 10,
                },
                {
                    "id": newer_id,
                    "session_id": session_id,
                    "evidence_type": EvidenceUploadV2Type.ORDERBOOK,
                    "observation_period": AnalysisRequestV2ObservationPeriod.AFTERNOON,
                    "current_price": Decimal("102"),
                    "observation_timestamp": newer,
                    "file_path": f"{session_id}/newer.png",
                    "original_filename": "newer.png",
                    "mime_type": "image/png",
                    "size_bytes": 10,
                },
                {
                    "id": tied_id,
                    "session_id": session_id,
                    "evidence_type": EvidenceUploadV2Type.ORDERBOOK,
                    "observation_period": AnalysisRequestV2ObservationPeriod.AFTERNOON,
                    "current_price": Decimal("103"),
                    "observation_timestamp": newer,
                    "file_path": f"{session_id}/tied.png",
                    "original_filename": "tied.png",
                    "mime_type": "image/png",
                    "size_bytes": 10,
                },
            ],
        )
    app = _app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(client, email)
        response = await client.post(f"/api/v2/trade-sessions/{session_id}/wait-updates")
    assert response.status_code == 202
    assert uuid.UUID(response.json()["evidence_id"]) == max(newer_id, tied_id)
    assert uuid.UUID(response.json()["evidence_id"]) != older_id


@pytest.mark.parametrize(
    "status",
    [status for status in TradeSessionV2Status if status is not TradeSessionV2Status.WAITING],
)
async def test_non_waiting_sessions_are_rejected(
    engine: AsyncEngine, db_session: AsyncSession, status: TradeSessionV2Status
) -> None:
    _, session_id, email = await _seed(engine, status=status, evidence=True)
    app = _app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(client, email)
        response = await client.post(f"/api/v2/trade-sessions/{session_id}/wait-updates")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SESSION_NOT_ELIGIBLE"


@pytest.mark.parametrize(
    "request_status",
    [AnalysisRequestV2Status.PENDING, AnalysisRequestV2Status.PROCESSING],
)
async def test_active_wait_update_request_blocks_duplicate_submission(
    engine: AsyncEngine, db_session: AsyncSession, request_status: AnalysisRequestV2Status
) -> None:
    _, session_id, email = await _seed(engine)
    async with db_session.begin():
        db_session.add(_request(session_id, status=request_status))
    app = _app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(client, email)
        response = await client.post(f"/api/v2/trade-sessions/{session_id}/wait-updates")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "WAIT_UPDATE_ANALYSIS_ACTIVE"


async def test_completed_prior_cycle_does_not_block_new_submission(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, email = await _seed(engine)
    async with db_session.begin():
        db_session.add(_request(session_id, status=AnalysisRequestV2Status.COMPLETED))
    app = _app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(client, email)
        response = await client.post(f"/api/v2/trade-sessions/{session_id}/wait-updates")
    assert response.status_code == 202
    assert (
        await db_session.scalar(
            select(AnalysisRequestV2.id).where(
                AnalysisRequestV2.session_id == session_id,
                AnalysisRequestV2.analysis_type == AnalysisRequestV2Type.WAIT_UPDATE,
            )
        )
        is not None
    )


async def test_missing_metadata_and_no_eligible_input_are_rejected_safely(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, email = await _seed(engine, evidence=False)
    async with engine.begin() as connection:
        await connection.execute(
            EvidenceUploadV2.__table__.insert().values(
                id=uuid.uuid4(),
                session_id=session_id,
                evidence_type=EvidenceUploadV2Type.ORDERBOOK,
                file_path=f"{session_id}/missing-price.png",
                original_filename="missing-price.png",
                mime_type="image/png",
                size_bytes=10,
            )
        )
    app = _app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(client, email)
        response = await client.post(f"/api/v2/trade-sessions/{session_id}/wait-updates")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "WAIT_UPDATE_INPUT_NOT_READY"


async def test_successful_submission_commits_request_pending_evidence_linked_and_session_analyzing(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    """P4.4 database-backed queue: verify atomic commit persists PENDING request,
    linked evidence, and ANALYZING session status without transport calls."""
    _, session_id, email = await _seed(engine)
    app = _app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(client, email)
        response = await client.post(f"/api/v2/trade-sessions/{session_id}/wait-updates")
    assert response.status_code == 202
    request = await db_session.scalar(
        select(AnalysisRequestV2).where(
            AnalysisRequestV2.session_id == session_id,
            AnalysisRequestV2.analysis_type == AnalysisRequestV2Type.WAIT_UPDATE,
        )
    )
    assert request is not None
    assert request.status is AnalysisRequestV2Status.PENDING
    evidence = await db_session.scalar(
        select(EvidenceUploadV2).where(EvidenceUploadV2.session_id == session_id)
    )
    assert evidence is not None
    assert evidence.analysis_request_id == request.id
    session = await db_session.scalar(
        select(TradeSessionV2).where(TradeSessionV2.id == session_id)
    )
    assert session is not None
    assert session.status is TradeSessionV2Status.ANALYZING


async def test_ownership_and_authentication_are_safe(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, owner_email = await _seed(engine)
    _, _, other_email = await _seed(engine, email_prefix="p72-other", ticker="BBCA")
    app = _app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"/api/v2/trade-sessions/{session_id}/wait-updates")
        assert response.status_code == 401
        await _login(client, other_email)
        response = await client.post(f"/api/v2/trade-sessions/{session_id}/wait-updates")
        assert response.status_code == 404
        await client.post("/api/auth/logout")
        await _login(client, owner_email)
        response = await client.post(f"/api/v2/trade-sessions/{uuid.uuid4()}/wait-updates")
    assert response.status_code == 404


async def test_concurrent_sessions_are_independent_and_duplicate_submission_is_serialized(
    engine: AsyncEngine,
) -> None:
    _, session_a, email_a = await _seed(engine, email_prefix="p72-a", ticker="BBRI")
    _, session_b, email_b = await _seed(engine, email_prefix="p72-b", ticker="BBCA")
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async def submit(session_id: uuid.UUID, email: str) -> int:
        async with factory() as db_session:
            app = _app(db_session)
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await _login(client, email)
                response = await client.post(
                    f"/api/v2/trade-sessions/{session_id}/wait-updates"
                )
                return response.status_code

    statuses = await asyncio.gather(
        submit(session_a, email_a),
        submit(session_a, email_a),
        submit(session_b, email_b),
    )
    assert sorted(statuses) == [202, 202, 409]
    async with factory() as session:
        rows = list(
            (
                await session.scalars(
                    select(AnalysisRequestV2).where(
                        AnalysisRequestV2.session_id.in_((session_a, session_b)),
                        AnalysisRequestV2.analysis_type == AnalysisRequestV2Type.WAIT_UPDATE,
                    )
                )
            ).all()
        )
        assert {row.session_id for row in rows} == {session_a, session_b}
        assert all(row.status is AnalysisRequestV2Status.PENDING for row in rows)
