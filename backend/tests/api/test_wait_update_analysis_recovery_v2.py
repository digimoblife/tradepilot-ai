from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.api.exception_handlers import register_handlers
from app.auth import hash_password
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
from app.trade_workspace.services.wait_update_analysis_retry import (
    WaitUpdateAnalysisRetryService,
)

pytestmark = pytest.mark.database

_NOW = datetime(2026, 7, 30, 10, 0, tzinfo=timezone.utc)


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
    request_status: AnalysisRequestV2Status = AnalysisRequestV2Status.FAILED,
    session_status: TradeSessionV2Status = TradeSessionV2Status.WAITING,
    request_type: AnalysisRequestV2Type = AnalysisRequestV2Type.WAIT_UPDATE,
    request_id: uuid.UUID | None = None,
    created_at: datetime = _NOW,
    raw_response: dict[str, object] | None = None,
    processed_response: dict[str, object] | None = None,
    error_code: str | None = "OLD_ERROR",
    error_message: str | None = "old error",
    with_evidence: bool = True,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, str]:
    user_id, session_id = uuid.uuid4(), uuid.uuid4()
    request_id = request_id or uuid.uuid4()
    email = f"p76-{user_id}@example.test"
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
                note="Catatan",
                status=session_status,
                closed_at=_NOW if session_status is TradeSessionV2Status.WAITING else None,
            )
        )
        await connection.execute(
            AnalysisRequestV2.__table__.insert().values(
                id=request_id,
                session_id=session_id,
                analysis_type=request_type,
                observation_period=(
                    AnalysisRequestV2ObservationPeriod.MORNING
                    if request_type is AnalysisRequestV2Type.WAIT_UPDATE
                    else None
                ),
                current_price=Decimal("123.45")
                if request_type is AnalysisRequestV2Type.WAIT_UPDATE
                else None,
                observation_at=_NOW if request_type is AnalysisRequestV2Type.WAIT_UPDATE else None,
                status=request_status,
                provider="gemini",
                model="gemini-3.1-flash-lite",
                prompt_version="v1",
                input_snapshot={"immutable": "preserved"},
                raw_response=raw_response,
                processed_response=processed_response,
                error_code=error_code,
                error_message=error_message,
                created_at=created_at,
                started_at=(
                    _NOW if request_status is not AnalysisRequestV2Status.PENDING else None
                ),
                completed_at=(
                    _NOW
                    if request_status
                    in {AnalysisRequestV2Status.FAILED, AnalysisRequestV2Status.COMPLETED}
                    else None
                ),
            )
        )
        if with_evidence and request_type is AnalysisRequestV2Type.WAIT_UPDATE:
            await connection.execute(
                EvidenceUploadV2.__table__.insert().values(
                    id=uuid.uuid4(),
                    session_id=session_id,
                    analysis_request_id=request_id,
                    evidence_type=EvidenceUploadV2Type.ORDERBOOK,
                    observation_period=AnalysisRequestV2ObservationPeriod.MORNING,
                    current_price=Decimal("123.45"),
                    observation_timestamp=_NOW,
                    file_path=f"{session_id}/orderbook.png",
                    original_filename="orderbook.png",
                    mime_type="image/png",
                    size_bytes=100,
                )
            )
    return user_id, session_id, request_id, email


def _app(db_session: AsyncSession, queue: RecordingQueue | None = None) -> FastAPI:
    app = FastAPI()
    register_handlers(app)
    app.include_router(auth_router)
    app.include_router(rebuild_router)
    if queue is not None:
        app.state.rebuild_analysis_queue = queue

    async def override_db():
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


async def _request(
    db_session: AsyncSession,
    path: str,
    *,
    method: str = "get",
    email: str | None,
    queue: RecordingQueue | None = None,
) -> tuple[int, dict[str, object]]:
    app = _app(db_session, queue)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        if email is not None:
            login = await client.post(
                "/api/auth/login",
                json={"email": email, "password": "testpass123"},
            )
            assert login.status_code == 200
        response = await getattr(client, method)(path)
    return response.status_code, response.json()


async def _read_request(session: AsyncSession, request_id: uuid.UUID) -> AnalysisRequestV2:
    request = await session.scalar(
        select(AnalysisRequestV2).where(AnalysisRequestV2.id == request_id)
    )
    assert request is not None
    return request


async def test_read_returns_latest_wait_result_without_exposing_input_or_raw_response(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    user_id, session_id, older_id, email = await _seed(
        engine,
        request_status=AnalysisRequestV2Status.COMPLETED,
        processed_response={"update_summary": "Terbaru"},
        raw_response={"secret": "raw"},
        created_at=_NOW,
    )
    newer_id = uuid.uuid4()
    await _seed(
        engine,
        request_status=AnalysisRequestV2Status.COMPLETED,
        request_id=newer_id,
        processed_response={"update_summary": "Paling baru"},
        raw_response={"secret": "new raw"},
        created_at=_NOW + timedelta(seconds=1),
    )
    # Keep the test explicitly scoped to one session; the second seed is independent.
    async with db_session.begin():
        await db_session.execute(
            AnalysisRequestV2.__table__.update()
            .where(AnalysisRequestV2.id == newer_id)
            .values(session_id=session_id)
        )
        await db_session.execute(
            EvidenceUploadV2.__table__.update()
            .where(EvidenceUploadV2.analysis_request_id == newer_id)
            .values(session_id=session_id)
        )
    status_code, payload = await _request(
        db_session,
        f"/api/v2/trade-sessions/{session_id}/wait-update-analysis",
        email=email,
    )
    assert status_code == 200
    assert payload["analysis_request_id"] == str(newer_id)
    assert payload["processed_response"] == {"update_summary": "Paling baru"}
    assert "raw_response" not in payload
    assert "input_snapshot" not in payload
    assert payload["request_status"] == "COMPLETED"
    assert payload["session_status"] == "WAITING"
    assert older_id != newer_id
    assert user_id


@pytest.mark.parametrize(
    ("request_status", "session_status", "processed", "error_code", "error_message"),
    [
        (AnalysisRequestV2Status.PENDING, TradeSessionV2Status.WAITING, None, None, None),
        (AnalysisRequestV2Status.PROCESSING, TradeSessionV2Status.ANALYZING, None, None, None),
        (
            AnalysisRequestV2Status.COMPLETED,
            TradeSessionV2Status.WAITING,
            {"update_summary": "Selesai"},
            None,
            None,
        ),
        (
            AnalysisRequestV2Status.FAILED,
            TradeSessionV2Status.WAITING,
            None,
            "SAFE_ERROR",
            "Kesalahan tersanitasi",
        ),
    ],
)
async def test_read_returns_status_specific_safe_payload(
    engine: AsyncEngine,
    db_session: AsyncSession,
    request_status: AnalysisRequestV2Status,
    session_status: TradeSessionV2Status,
    processed: dict[str, object] | None,
    error_code: str | None,
    error_message: str | None,
) -> None:
    _, session_id, request_id, email = await _seed(
        engine,
        request_status=request_status,
        session_status=session_status,
        processed_response=processed,
        error_code=error_code,
        error_message=error_message,
    )
    before = await _read_request(db_session, request_id)
    status_code, payload = await _request(
        db_session,
        f"/api/v2/trade-sessions/{session_id}/wait-update-analysis",
        email=email,
    )
    after = await _read_request(db_session, request_id)
    assert status_code == 200
    assert payload["request_status"] == request_status.value
    expected_processed = (
        processed if request_status is AnalysisRequestV2Status.COMPLETED else None
    )
    expected_error_code = (
        error_code if request_status is AnalysisRequestV2Status.FAILED else None
    )
    expected_error_message = (
        error_message if request_status is AnalysisRequestV2Status.FAILED else None
    )
    assert payload["processed_response"] == expected_processed
    assert payload["error_code"] == expected_error_code
    assert payload["error_message"] == expected_error_message
    assert before.status is after.status
    assert before.started_at == after.started_at
    assert before.completed_at == after.completed_at


async def test_failed_retry_reuses_request_and_evidence_and_clears_result(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, request_id, email = await _seed(
        engine,
        raw_response={"raw": "clear"},
        processed_response={"update_summary": "clear"},
    )
    queue = RecordingQueue()
    status_code, payload = await _request(
        db_session,
        f"/api/v2/trade-sessions/{session_id}/wait-update-analysis/retry",
        method="post",
        email=email,
        queue=queue,
    )
    assert status_code == 202
    assert payload["analysis_request_id"] == str(request_id)
    assert payload["session_status"] == "ANALYZING"
    assert queue.calls == [request_id]
    request = await _read_request(db_session, request_id)
    assert request.status is AnalysisRequestV2Status.PENDING
    assert request.started_at is None
    assert request.completed_at is None
    assert request.raw_response is None
    assert request.processed_response is None
    assert request.error_code is None
    assert request.error_message is None
    assert request.input_snapshot == {"immutable": "preserved"}
    evidence_count = await db_session.scalar(
        select(func.count()).select_from(EvidenceUploadV2).where(
            EvidenceUploadV2.analysis_request_id == request_id
        )
    )
    assert evidence_count == 1


async def test_pending_waiting_retry_preserves_fields_and_queue_failure_is_recoverable(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, request_id, email = await _seed(
        engine,
        request_status=AnalysisRequestV2Status.PENDING,
        raw_response={"must": "remain"},
        processed_response={"must": "remain"},
    )
    queue = RecordingQueue(fail=True)
    status_code, _ = await _request(
        db_session,
        f"/api/v2/trade-sessions/{session_id}/wait-update-analysis/retry",
        method="post",
        email=email,
        queue=queue,
    )
    assert status_code == 503
    request = await _read_request(db_session, request_id)
    assert request.status is AnalysisRequestV2Status.PENDING
    assert request.raw_response == {"must": "remain"}
    assert request.processed_response == {"must": "remain"}
    session = await db_session.scalar(
        select(TradeSessionV2).where(TradeSessionV2.id == session_id)
    )
    assert session is not None
    assert session.status is TradeSessionV2Status.WAITING
    assert queue.calls == []


@pytest.mark.parametrize(
    "request_status",
    [AnalysisRequestV2Status.PROCESSING, AnalysisRequestV2Status.COMPLETED],
)
async def test_retry_rejects_ineligible_states(
    engine: AsyncEngine, db_session: AsyncSession, request_status: AnalysisRequestV2Status
) -> None:
    _, session_id, _, email = await _seed(engine, request_status=request_status)
    queue = RecordingQueue()
    status_code, payload = await _request(
        db_session,
        f"/api/v2/trade-sessions/{session_id}/wait-update-analysis/retry",
        method="post",
        email=email,
        queue=queue,
    )
    assert status_code == 409
    assert payload["error"]["code"] == "WAIT_UPDATE_RETRY_NOT_ALLOWED"
    assert queue.calls == []


async def test_retry_rejects_missing_evidence_cross_user_and_unauthenticated(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, _, email = await _seed(engine, with_evidence=False)
    _, _, _, other_email = await _seed(engine)
    queue = RecordingQueue()
    invalid_status, invalid_payload = await _request(
        db_session,
        f"/api/v2/trade-sessions/{session_id}/wait-update-analysis/retry",
        method="post",
        email=email,
        queue=queue,
    )
    cross_status, cross_payload = await _request(
        db_session,
        f"/api/v2/trade-sessions/{session_id}/wait-update-analysis/retry",
        method="post",
        email=other_email,
        queue=queue,
    )
    anonymous_status, _ = await _request(
        db_session,
        f"/api/v2/trade-sessions/{session_id}/wait-update-analysis/retry",
        method="post",
        email=None,
        queue=queue,
    )
    assert invalid_status == 409
    assert invalid_payload["error"]["code"] == "WAIT_UPDATE_EVIDENCE_INVALID"
    assert cross_status == 404
    assert cross_payload["error"]["code"] == "SESSION_NOT_FOUND"
    assert anonymous_status in {401, 403}
    assert queue.calls == []


async def test_concurrent_retry_calls_have_one_success_and_do_not_affect_other_session(
    engine: AsyncEngine,
) -> None:
    first_user, first_session_id, first_request_id, _ = await _seed(engine)
    second_user, second_session_id, second_request_id, _ = await _seed(engine)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    first_queue = RecordingQueue(delay=0.05)
    second_queue = RecordingQueue()
    async with factory() as first_session, factory() as second_session:
        first = WaitUpdateAnalysisRetryService(first_session, first_queue)
        second = WaitUpdateAnalysisRetryService(second_session, second_queue)
        first_result, second_result = await asyncio.gather(
            first.retry(user_id=first_user, session_id=first_session_id),
            second.retry(user_id=second_user, session_id=second_session_id),
        )
    assert first_result.analysis_request_id == first_request_id
    assert second_result.analysis_request_id == second_request_id
    assert first_queue.calls == [first_request_id]
    assert second_queue.calls == [second_request_id]
