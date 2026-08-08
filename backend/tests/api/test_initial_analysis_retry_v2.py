from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.api.exception_handlers import register_handlers
from app.auth import hash_password
from app.database.session import get_db_session
from app.models.user import User
from app.trade_workspace.api.routes.trade_sessions import router as rebuild_router
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
from app.trade_workspace.services.initial_analysis_retry import (
    InitialAnalysisRetryService,
    InitialAnalysisRetrySessionStateError,
)

pytestmark = pytest.mark.database

_NOW = datetime(2026, 7, 30, 10, 0, tzinfo=timezone.utc)
_ROLES = (
    EvidenceUploadV2Type.ORDERBOOK,
    EvidenceUploadV2Type.CHART_3_MONTH,
    EvidenceUploadV2Type.CHART_6_MONTH,
    EvidenceUploadV2Type.FOREIGN_FLOW_1W,
)


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
    status: AnalysisRequestV2Status = AnalysisRequestV2Status.FAILED,
    session_status: TradeSessionV2Status = TradeSessionV2Status.DRAFT,
    roles: tuple[EvidenceUploadV2Type, ...] = _ROLES,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, str]:
    user_id, session_id, request_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    email = f"p55b-{user_id}@example.test"
    async with engine.begin() as connection:
        await connection.execute(
            User.__table__.insert().values(
                id=user_id,
                email=email,
                password_hash=hash_password("testpass123"),
            )
        )
        await connection.execute(
            TradeSessionV2.__table__.insert().values(
                id=session_id,
                user_id=user_id,
                ticker="BBRI",
                company_name="Bank BRI",
                status=session_status,
            )
        )
        await connection.execute(
            AnalysisRequestV2.__table__.insert().values(
                id=request_id,
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                status=status,
                provider="gemini",
                model="configured-model",
                prompt_version="v1",
                input_snapshot={"snapshot": "preserve"},
                raw_response={"raw": "clear"},
                processed_response={"summary": "clear"},
                error_code="OLD_ERROR",
                error_message="old message",
                created_at=_NOW,
                started_at=_NOW,
                completed_at=_NOW,
            )
        )
        for role in roles:
            await connection.execute(
                EvidenceUploadV2.__table__.insert().values(
                    id=uuid.uuid4(),
                    session_id=session_id,
                    analysis_request_id=request_id,
                    evidence_type=role,
                    observation_period=None,
                    file_path=f"{session_id}/{role.value}.png",
                    original_filename=f"{role.value}.png",
                    mime_type="image/png",
                    size_bytes=10,
                )
            )
    return user_id, session_id, request_id, email


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


async def _retry(
    db_session: AsyncSession,
    session_id: uuid.UUID,
    email: str | None,
) -> tuple[int, dict[str, object]]:
    app = _app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        if email is not None:
            login = await client.post(
                "/api/auth/login",
                json={"email": email, "password": "testpass123"},
            )
            assert login.status_code == 200
        response = await client.post(f"/api/v2/trade-sessions/{session_id}/initial-analysis/retry")
    return response.status_code, response.json()


async def _read_request(session: AsyncSession, request_id: uuid.UUID) -> AnalysisRequestV2:
    request = await session.scalar(
        select(AnalysisRequestV2).where(AnalysisRequestV2.id == request_id)
    )
    assert request is not None
    return request


async def test_failed_retry_reuses_request_and_evidence_and_transitions_session(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, request_id, email = await _seed(engine)

    status_code, payload = await _retry(db_session, session_id, email)

    assert status_code == 202
    assert payload == {
        "analysis_request_id": str(request_id),
        "session_id": str(session_id),
        "analysis_type": "INITIAL_ANALYSIS",
        "request_status": "PENDING",
        "session_status": "ANALYZING",
        "created_at": _NOW.isoformat().replace("+00:00", "Z"),
    }
    request = await _read_request(db_session, request_id)
    assert request.status is AnalysisRequestV2Status.PENDING
    assert request.started_at is None
    assert request.completed_at is None
    assert request.error_code is None
    assert request.error_message is None
    assert request.raw_response is None
    assert request.processed_response is None
    assert request.provider == "gemini"
    assert request.model == "configured-model"
    assert request.prompt_version == "v1"
    assert request.input_snapshot == {"snapshot": "preserve"}
    assert request.created_at == _NOW
    evidence = list(
        (
            await db_session.scalars(
                select(EvidenceUploadV2).where(
                    EvidenceUploadV2.session_id == session_id,
                    EvidenceUploadV2.analysis_request_id == request_id,
                )
            )
        ).all()
    )
    assert {item.evidence_type for item in evidence} == set(_ROLES)
    assert all(item.observation_period is None for item in evidence)
    session = await db_session.scalar(
        select(TradeSessionV2).where(TradeSessionV2.id == session_id)
    )
    assert session is not None
    assert session.status is TradeSessionV2Status.ANALYZING


async def test_pending_retry_reuses_request_without_resetting_fields(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, request_id, email = await _seed(engine, status=AnalysisRequestV2Status.PENDING)

    status_code, payload = await _retry(db_session, session_id, email)

    assert status_code == 202
    assert uuid.UUID(payload["analysis_request_id"]) == request_id
    request = await _read_request(db_session, request_id)
    assert request.status is AnalysisRequestV2Status.PENDING
    assert request.error_code == "OLD_ERROR"
    assert request.raw_response == {"raw": "clear"}


@pytest.mark.parametrize(
    "request_status",
    [AnalysisRequestV2Status.PROCESSING, AnalysisRequestV2Status.COMPLETED],
)
async def test_non_retryable_request_is_rejected(
    engine: AsyncEngine,
    db_session: AsyncSession,
    request_status: AnalysisRequestV2Status,
) -> None:
    _, session_id, _, email = await _seed(engine, status=request_status)

    status_code, payload = await _retry(db_session, session_id, email)

    assert status_code == 409
    assert payload["error"]["code"] == "INITIAL_ANALYSIS_RETRY_NOT_ALLOWED"


async def test_invalid_evidence_rejects_without_queue(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, _, email = await _seed(engine, roles=_ROLES[:2])

    status_code, payload = await _retry(db_session, session_id, email)

    assert status_code == 422
    assert payload["error"]["code"] == "INITIAL_EVIDENCE_INVALID"


async def test_cross_user_and_missing_session_are_not_found(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, _, _ = await _seed(engine)
    _, _, _, other_email = await _seed(engine)

    cross_status, cross_payload = await _retry(db_session, session_id, other_email)
    missing_status, missing_payload = await _retry(db_session, uuid.uuid4(), other_email)

    assert cross_status == 404
    assert cross_payload["error"]["code"] == "SESSION_NOT_FOUND"
    assert missing_status == 404
    assert missing_payload["error"]["code"] == "SESSION_NOT_FOUND"


async def test_unauthenticated_and_non_draft_are_rejected(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, _, email = await _seed(engine, session_status=TradeSessionV2Status.ANALYZED)

    unauthenticated_status, unauthenticated_payload = await _retry(db_session, session_id, None)
    status_code, payload = await _retry(db_session, session_id, email)

    assert unauthenticated_status in {401, 403}
    assert "analysis_request_id" not in unauthenticated_payload
    assert status_code == 409
    assert payload["error"]["code"] == "SESSION_NOT_ELIGIBLE"


async def test_concurrent_retries_for_one_session_have_one_success(
    engine: AsyncEngine,
) -> None:
    user_id, session_id, request_id, _ = await _seed(engine)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as first_session, factory() as second_session:
        first = InitialAnalysisRetryService(first_session)
        second = InitialAnalysisRetryService(second_session)
        first_result, second_result = await asyncio.gather(
            first.retry(user_id=user_id, session_id=session_id),
            second.retry(user_id=user_id, session_id=session_id),
            return_exceptions=True,
        )

    outcomes = (first_result, second_result)
    assert sum(isinstance(item, InitialAnalysisRetrySessionStateError) for item in outcomes) == 1
    assert sum(hasattr(item, "analysis_request_id") for item in outcomes) == 1


async def test_retries_for_independent_sessions_do_not_block_each_other(
    engine: AsyncEngine,
) -> None:
    first_user, first_session_id, first_request_id, _ = await _seed(engine)
    second_user, second_session_id, second_request_id, _ = await _seed(engine)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as first_session, factory() as second_session:
        first, second = (
            InitialAnalysisRetryService(first_session),
            InitialAnalysisRetryService(second_session),
        )
        first_result, second_result = await asyncio.gather(
            first.retry(user_id=first_user, session_id=first_session_id),
            second.retry(user_id=second_user, session_id=second_session_id),
        )

    assert first_result.analysis_request_id == first_request_id
    assert second_result.analysis_request_id == second_request_id
