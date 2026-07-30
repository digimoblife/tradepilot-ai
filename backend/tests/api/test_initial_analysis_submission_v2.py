from __future__ import annotations

import uuid

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
from app.trade_workspace.models.analysis_request import AnalysisRequestV2, AnalysisRequestV2Status
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status

pytestmark = pytest.mark.database


class RecordingQueue:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[uuid.UUID] = []
        self.fail = fail

    async def enqueue(self, *, analysis_request_id: uuid.UUID) -> None:
        if self.fail:
            raise RuntimeError("queue unavailable")
        self.calls.append(analysis_request_id)


async def _seed(
    engine: AsyncEngine,
    *,
    status: TradeSessionV2Status = TradeSessionV2Status.DRAFT,
    evidence_types: tuple[EvidenceUploadV2Type, ...] = tuple(EvidenceUploadV2Type),
) -> tuple[uuid.UUID, uuid.UUID, str]:
    user_id, session_id = uuid.uuid4(), uuid.uuid4()
    email = f"p53-{user_id}@example.test"
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
                ticker="BBRI",
                company_name="Bank BRI",
                status=status,
            )
        )
        for evidence_type in evidence_types:
            await connection.execute(
                EvidenceUploadV2.__table__.insert().values(
                    id=uuid.uuid4(),
                    session_id=session_id,
                    evidence_type=evidence_type,
                    file_path=f"{session_id}/{evidence_type.value}.png",
                    original_filename=f"{evidence_type.value}.png",
                    mime_type="image/png",
                    size_bytes=10,
                )
            )
    return user_id, session_id, email


def _app(db_session: AsyncSession, queue: RecordingQueue) -> FastAPI:
    app = FastAPI()
    register_handlers(app)
    app.include_router(auth_router)
    app.include_router(rebuild_router)
    app.state.rebuild_analysis_queue = queue

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


async def test_initial_analysis_submission_persists_request_links_evidence_and_starts_analysis(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    user_id, session_id, email = await _seed(engine)
    queue = RecordingQueue()
    app = _app(db_session, queue)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(client, email)
        response = await client.post(f"/api/v2/trade-sessions/{session_id}/initial-analysis")

    assert response.status_code == 202
    payload = response.json()
    assert payload["session_id"] == str(session_id)
    assert payload["analysis_type"] == "INITIAL_ANALYSIS"
    assert payload["request_status"] == "PENDING"
    assert payload["session_status"] == "ANALYZING"
    request_id = uuid.UUID(payload["analysis_request_id"])
    assert queue.calls == [request_id]

    request = await db_session.scalar(
        select(AnalysisRequestV2).where(AnalysisRequestV2.id == request_id)
    )
    assert request is not None
    assert request.session_id == session_id
    assert request.status is AnalysisRequestV2Status.PENDING
    assert request.provider == "gemini"
    assert request.model == AppConfig().gemini_model
    assert request.prompt_version == "v1"
    assert request.current_price is None
    assert request.observation_period is None
    assert request.observation_at is None
    assert request.input_snapshot["session_id"] == str(session_id)
    assert set(request.input_snapshot["evidence_ids"]) == {
        item.value for item in EvidenceUploadV2Type
    }

    evidence = list(
        (
            await db_session.scalars(
                select(EvidenceUploadV2).where(EvidenceUploadV2.session_id == session_id)
            )
        ).all()
    )
    assert len(evidence) == 3
    assert {item.analysis_request_id for item in evidence} == {request_id}
    assert {item.observation_period for item in evidence} == {None}
    owner = await db_session.scalar(
        select(TradeSessionV2.user_id).where(TradeSessionV2.id == session_id)
    )
    assert owner == user_id


@pytest.mark.parametrize("missing", list(EvidenceUploadV2Type))
async def test_missing_required_role_is_rejected_without_queue_or_request(
    engine: AsyncEngine, db_session: AsyncSession, missing: EvidenceUploadV2Type
) -> None:
    _, session_id, email = await _seed(
        engine,
        evidence_types=tuple(x for x in EvidenceUploadV2Type if x != missing),
    )
    queue = RecordingQueue()
    app = _app(db_session, queue)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(client, email)
        response = await client.post(f"/api/v2/trade-sessions/{session_id}/initial-analysis")
    assert response.status_code == 422
    assert queue.calls == []
    assert (
        await db_session.scalar(
            select(AnalysisRequestV2).where(AnalysisRequestV2.session_id == session_id)
        )
        is None
    )


async def test_non_draft_session_is_rejected(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, email = await _seed(engine, status=TradeSessionV2Status.ANALYZING)
    queue = RecordingQueue()
    app = _app(db_session, queue)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(client, email)
        response = await client.post(f"/api/v2/trade-sessions/{session_id}/initial-analysis")
    assert response.status_code == 409
    assert queue.calls == []


async def test_queue_failure_preserves_pending_request_and_draft_session(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, email = await _seed(engine)
    queue = RecordingQueue(fail=True)
    app = _app(db_session, queue)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(client, email)
        response = await client.post(f"/api/v2/trade-sessions/{session_id}/initial-analysis")

    assert response.status_code == 503
    assert queue.calls == []
    request = await db_session.scalar(
        select(AnalysisRequestV2).where(AnalysisRequestV2.session_id == session_id)
    )
    assert request is not None
    assert request.status is AnalysisRequestV2Status.PENDING
    session = await db_session.scalar(
        select(TradeSessionV2).where(TradeSessionV2.id == session_id)
    )
    assert session is not None
    assert session.status is TradeSessionV2Status.DRAFT
