from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
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
from app.trade_workspace.models.position import PositionV2, PositionV2Status
from app.trade_workspace.models.session_decision import SessionDecisionV2
from app.trade_workspace.models.trade_closure import TradeClosureV2
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
from app.trade_workspace.queue.analysis_request_queue import AnalysisRequestQueue
from app.trade_workspace.services.position_update_analysis_submission import (
    PositionUpdateAnalysisPersistenceError,
    PositionUpdateAnalysisSubmissionService,
)

pytestmark = pytest.mark.database

OBSERVATION = datetime(2026, 7, 30, 2, 15, tzinfo=timezone.utc)


class RecordingTransport:
    def __init__(self, *, fail: bool = False, delay: float = 0) -> None:
        self.fail = fail
        self.delay = delay
        self.payloads: list[dict[str, str]] = []

    async def publish(self, payload: bytes) -> None:
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError("isolated queue failure")
        self.payloads.append(json.loads(payload))


async def _seed_session(
    engine: AsyncEngine,
    *,
    status: TradeSessionV2Status = TradeSessionV2Status.OPEN_POSITION,
    position_status: PositionV2Status | None = PositionV2Status.OPEN,
    owner: tuple[uuid.UUID, str] | None = None,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID | None, str]:
    if owner is None:
        user_id, email = uuid.uuid4(), f"p82-{uuid.uuid4()}@example.test"
        create_user = True
    else:
        user_id, email = owner
        create_user = False
    session_id = uuid.uuid4()
    position_id = uuid.uuid4() if position_status is not None else None
    async with engine.begin() as connection:
        if create_user:
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
        if position_id is not None:
            await connection.execute(
                PositionV2.__table__.insert().values(
                    id=position_id,
                    session_id=session_id,
                    entry_price=Decimal("1200.000000"),
                    entry_at=datetime(2026, 7, 29, 2, tzinfo=timezone.utc),
                    quantity=Decimal("10.000000"),
                    stop_loss=Decimal("1100.000000"),
                    target_price=Decimal("1400.000000"),
                    note="immutable",
                    status=position_status,
                )
            )
    return user_id, session_id, position_id, email


async def _add_evidence(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    *,
    observation_timestamp: datetime,
    uploaded_at: datetime | None = None,
    analysis_request_id: uuid.UUID | None = None,
    current_price: Decimal | None = Decimal("1234.000000"),
    observation_period: AnalysisRequestV2ObservationPeriod
    | None = AnalysisRequestV2ObservationPeriod.MIDDAY,
    evidence_type: EvidenceUploadV2Type = EvidenceUploadV2Type.ORDERBOOK,
    file_path: str = "user/session/orderbook.png",
) -> uuid.UUID:
    evidence_id = uuid.uuid4()
    values: dict[str, object] = {
        "id": evidence_id,
        "session_id": session_id,
        "evidence_type": evidence_type,
        "analysis_request_id": analysis_request_id,
        "observation_period": observation_period,
        "current_price": current_price,
        "observation_timestamp": observation_timestamp,
        "file_path": file_path,
        "original_filename": "orderbook.png",
        "mime_type": "image/png",
        "size_bytes": 100,
    }
    if uploaded_at is not None:
        values["uploaded_at"] = uploaded_at
    async with engine.begin() as connection:
        await connection.execute(EvidenceUploadV2.__table__.insert().values(**values))
    return evidence_id


async def _add_prior_request(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    evidence_id: uuid.UUID,
    *,
    request_status: AnalysisRequestV2Status,
) -> uuid.UUID:
    request_id = uuid.uuid4()
    async with engine.begin() as connection:
        await connection.execute(
            AnalysisRequestV2.__table__.insert().values(
                id=request_id,
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.POSITION_UPDATE,
                observation_period=AnalysisRequestV2ObservationPeriod.MIDDAY,
                current_price=Decimal("1234.000000"),
                observation_at=OBSERVATION,
                status=request_status,
                provider="gemini",
                model="gemini-3.1-flash-lite",
                prompt_version="v1",
                input_snapshot={"prior": True},
            )
        )
        await connection.execute(
            EvidenceUploadV2.__table__.update()
            .where(EvidenceUploadV2.id == evidence_id)
            .values(analysis_request_id=request_id)
        )
    return request_id


def _app(db_session: AsyncSession, queue: AnalysisRequestQueue) -> FastAPI:
    app = FastAPI()
    register_handlers(app)
    app.include_router(auth_router)
    app.include_router(rebuild_router)
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


async def _post(
    db_session: AsyncSession,
    queue: AnalysisRequestQueue,
    session_id: uuid.UUID,
    email: str | None,
    *,
    body: object = None,
) -> tuple[int, dict[str, object]]:
    app = _app(db_session, queue)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        if email is not None:
            login = await client.post(
                "/api/auth/login", json={"email": email, "password": "testpass123"}
            )
            assert login.status_code == 200
        kwargs = {} if body is None else {"json": body}
        response = await client.post(
            f"/api/v2/trade-sessions/{session_id}/position-update-analysis",
            **kwargs,
        )
    return response.status_code, response.json()


async def _count(
    db_session: AsyncSession,
    model: type[object],
    session_id: uuid.UUID,
) -> int:
    return int(
        await db_session.scalar(
            select(func.count()).select_from(model).where(model.session_id == session_id)  # type: ignore[attr-defined]
        )
    )


async def test_owner_submits_latest_position_update_analysis_with_id_only_queue(
    engine: AsyncEngine,
    db_session: AsyncSession,
) -> None:
    user_id, session_id, position_id, email = await _seed_session(engine)
    older_id = await _add_evidence(
        engine,
        session_id,
        observation_timestamp=OBSERVATION - timedelta(hours=1),
        current_price=Decimal("1200.000000"),
    )
    latest_id = await _add_evidence(
        engine,
        session_id,
        observation_timestamp=OBSERVATION,
        current_price=Decimal("1234.567890"),
    )
    await _add_evidence(
        engine,
        session_id,
        observation_timestamp=OBSERVATION + timedelta(hours=1),
        current_price=None,
    )
    other_user, other_session, other_position, _ = await _seed_session(engine)
    other_evidence = await _add_evidence(
        engine,
        other_session,
        observation_timestamp=OBSERVATION + timedelta(days=1),
    )
    transport = RecordingTransport()
    queue = AnalysisRequestQueue(transport)
    code, payload = await _post(db_session, queue, session_id, email)

    assert code == 202
    request_id = uuid.UUID(payload["analysis_request_id"])
    assert payload == {
        "analysis_request_id": str(request_id),
        "session_id": str(session_id),
        "position_id": str(position_id),
        "analysis_type": "POSITION_UPDATE",
        "request_status": "PENDING",
        "evidence_id": str(latest_id),
        "observation_period": "MIDDAY",
        "session_status": "ANALYZING",
        "position_status": "OPEN",
        "created_at": payload["created_at"],
    }
    assert transport.payloads == [{"analysis_request_id": str(request_id)}]
    assert older_id != latest_id and other_user != user_id and other_position != position_id

    request = await db_session.scalar(
        select(AnalysisRequestV2).where(AnalysisRequestV2.id == request_id)
    )
    assert request is not None
    assert request.session_id == session_id
    assert request.analysis_type is AnalysisRequestV2Type.POSITION_UPDATE
    assert request.status is AnalysisRequestV2Status.PENDING
    assert request.provider == "gemini"
    assert request.model == "gemini-3.1-flash-lite"
    assert request.prompt_version == "v1"
    assert request.observation_period is AnalysisRequestV2ObservationPeriod.MIDDAY
    assert request.input_snapshot == {
        "session_id": str(session_id),
        "ticker": "BBRI",
        "analysis_type": "POSITION_UPDATE",
        "position_id": str(position_id),
        "evidence_id": str(latest_id),
        "current_price": "1234.567890",
        "observation_period": "MIDDAY",
        "observation_timestamp": OBSERVATION.isoformat(),
        "provider": "gemini",
        "model": "gemini-3.1-flash-lite",
        "prompt_version": "v1",
    }
    linked = await db_session.scalar(
        select(EvidenceUploadV2).where(EvidenceUploadV2.id == latest_id)
    )
    assert linked is not None and linked.analysis_request_id == request_id
    assert (
        await db_session.scalar(
            select(EvidenceUploadV2.analysis_request_id).where(
                EvidenceUploadV2.id == other_evidence
            )
        )
        is None
    )
    session = await db_session.scalar(
        select(TradeSessionV2).where(TradeSessionV2.id == session_id)
    )
    position = await db_session.scalar(select(PositionV2).where(PositionV2.id == position_id))
    assert session is not None and session.status is TradeSessionV2Status.ANALYZING
    assert session.closed_at is None
    assert position is not None and position.status is PositionV2Status.OPEN
    assert position.entry_price == Decimal("1200.000000")
    assert position.quantity == Decimal("10.000000")
    assert position.stop_loss == Decimal("1100.000000")
    assert position.target_price == Decimal("1400.000000")
    assert await _count(db_session, SessionDecisionV2, session_id) == 0
    assert await _count(db_session, TradeClosureV2, session_id) == 0


@pytest.mark.parametrize(
    "status",
    [
        TradeSessionV2Status.DRAFT,
        TradeSessionV2Status.ANALYZING,
        TradeSessionV2Status.ANALYZED,
        TradeSessionV2Status.WAITING,
        TradeSessionV2Status.CLOSED,
        TradeSessionV2Status.CLOSED_SKIPPED,
    ],
)
async def test_position_update_analysis_rejects_inactive_sessions(
    engine: AsyncEngine,
    db_session: AsyncSession,
    status: TradeSessionV2Status,
) -> None:
    _, session_id, _, email = await _seed_session(engine, status=status)
    await _add_evidence(engine, session_id, observation_timestamp=OBSERVATION)
    transport = RecordingTransport()
    code, payload = await _post(db_session, AnalysisRequestQueue(transport), session_id, email)
    assert code == 409
    assert payload["error"]["code"] == "POSITION_UPDATE_ANALYSIS_NOT_ALLOWED"
    assert not transport.payloads
    assert await _count(db_session, AnalysisRequestV2, session_id) == 0


@pytest.mark.parametrize("position_status", [None, PositionV2Status.CLOSED])
async def test_position_update_analysis_rejects_missing_or_non_open_position(
    engine: AsyncEngine,
    db_session: AsyncSession,
    position_status: PositionV2Status | None,
) -> None:
    _, session_id, _, email = await _seed_session(engine, position_status=position_status)
    await _add_evidence(engine, session_id, observation_timestamp=OBSERVATION)
    transport = RecordingTransport()
    code, payload = await _post(db_session, AnalysisRequestQueue(transport), session_id, email)
    assert code == 409
    assert payload["error"]["code"] == "POSITION_UPDATE_ANALYSIS_NOT_ALLOWED"
    assert await _count(db_session, AnalysisRequestV2, session_id) == 0


async def test_no_eligible_evidence_and_ownership_are_safe(
    engine: AsyncEngine,
    db_session: AsyncSession,
) -> None:
    _, session_id, _, owner_email = await _seed_session(engine)
    await _add_evidence(
        engine,
        session_id,
        observation_timestamp=OBSERVATION,
        current_price=None,
    )
    _, other_session, _, other_email = await _seed_session(engine)
    transport = RecordingTransport()
    cross_code, cross_payload = await _post(
        db_session, AnalysisRequestQueue(transport), session_id, other_email
    )
    missing_code, missing_payload = await _post(
        db_session, AnalysisRequestQueue(transport), uuid.uuid4(), owner_email
    )
    no_input_code, no_input_payload = await _post(
        db_session, AnalysisRequestQueue(transport), other_session, other_email
    )
    unauth_code, unauth_payload = await _post(
        db_session, AnalysisRequestQueue(transport), session_id, None
    )
    assert cross_code == missing_code == 404
    assert (
        cross_payload["error"]["code"] == missing_payload["error"]["code"] == "SESSION_NOT_FOUND"
    )
    assert no_input_code == 409
    assert no_input_payload["error"]["code"] == "POSITION_UPDATE_INPUT_NOT_READY"
    assert unauth_code == 401
    assert unauth_payload["error"]["code"] == "AUTHENTICATION_REQUIRED"
    assert not transport.payloads


@pytest.mark.parametrize(
    "request_status", [AnalysisRequestV2Status.PENDING, AnalysisRequestV2Status.PROCESSING]
)
async def test_active_position_update_request_blocks_duplicate(
    engine: AsyncEngine,
    db_session: AsyncSession,
    request_status: AnalysisRequestV2Status,
) -> None:
    _, session_id, _, email = await _seed_session(engine)
    evidence_id = await _add_evidence(engine, session_id, observation_timestamp=OBSERVATION)
    await _add_prior_request(engine, session_id, evidence_id, request_status=request_status)
    await _add_evidence(engine, session_id, observation_timestamp=OBSERVATION + timedelta(hours=1))
    transport = RecordingTransport()
    code, payload = await _post(db_session, AnalysisRequestQueue(transport), session_id, email)
    assert code == 409
    assert payload["error"]["code"] == "POSITION_UPDATE_ANALYSIS_ACTIVE"
    assert not transport.payloads
    assert await _count(db_session, AnalysisRequestV2, session_id) == 1


@pytest.mark.parametrize(
    "prior_status", [AnalysisRequestV2Status.COMPLETED, AnalysisRequestV2Status.FAILED]
)
async def test_completed_or_failed_prior_cycle_allows_new_cycle(
    engine: AsyncEngine,
    db_session: AsyncSession,
    prior_status: AnalysisRequestV2Status,
) -> None:
    _, session_id, _, email = await _seed_session(engine)
    prior_evidence = await _add_evidence(engine, session_id, observation_timestamp=OBSERVATION)
    await _add_prior_request(engine, session_id, prior_evidence, request_status=prior_status)
    latest_evidence = await _add_evidence(
        engine, session_id, observation_timestamp=OBSERVATION + timedelta(hours=1)
    )
    transport = RecordingTransport()
    code, payload = await _post(db_session, AnalysisRequestQueue(transport), session_id, email)
    assert code == 202
    assert payload["evidence_id"] == str(latest_evidence)
    assert await _count(db_session, AnalysisRequestV2, session_id) == 2
    assert len(transport.payloads) == 1


async def test_queue_failure_keeps_pending_request_and_linked_evidence(
    engine: AsyncEngine,
    db_session: AsyncSession,
) -> None:
    _, session_id, position_id, email = await _seed_session(engine)
    evidence_id = await _add_evidence(engine, session_id, observation_timestamp=OBSERVATION)
    transport = RecordingTransport(fail=True)
    code, payload = await _post(db_session, AnalysisRequestQueue(transport), session_id, email)
    assert code == 503
    assert payload["error"]["code"] == "POSITION_UPDATE_ANALYSIS_QUEUE_FAILED"
    request = await db_session.scalar(
        select(AnalysisRequestV2).where(AnalysisRequestV2.session_id == session_id)
    )
    assert request is not None and request.status is AnalysisRequestV2Status.PENDING
    linked = await db_session.scalar(
        select(EvidenceUploadV2).where(EvidenceUploadV2.id == evidence_id)
    )
    assert linked is not None and linked.analysis_request_id == request.id
    session = await db_session.scalar(
        select(TradeSessionV2).where(TradeSessionV2.id == session_id)
    )
    position = await db_session.scalar(select(PositionV2).where(PositionV2.id == position_id))
    assert session is not None and session.status is TradeSessionV2Status.OPEN_POSITION
    assert position is not None and position.status is PositionV2Status.OPEN
    assert not transport.payloads
    assert await _count(db_session, AnalysisRequestV2, session_id) == 1


async def test_persistence_failure_leaves_evidence_unlinked(
    engine: AsyncEngine,
    db_session: AsyncSession,
) -> None:
    _, session_id, _, email = await _seed_session(engine)
    evidence_id = await _add_evidence(engine, session_id, observation_timestamp=OBSERVATION)
    transport = RecordingTransport()

    async def fail_flush(*args: object, **kwargs: object) -> None:
        raise SQLAlchemyError("submission persistence failure")

    db_session.flush = fail_flush  # type: ignore[method-assign]
    user_id = await db_session.scalar(
        select(TradeSessionV2.user_id).where(TradeSessionV2.id == session_id)
    )
    with pytest.raises(PositionUpdateAnalysisPersistenceError):
        await PositionUpdateAnalysisSubmissionService(
            db_session, AnalysisRequestQueue(transport)
        ).submit(user_id=user_id, session_id=session_id)
    assert await _count(db_session, AnalysisRequestV2, session_id) == 0
    linked = await db_session.scalar(
        select(EvidenceUploadV2).where(EvidenceUploadV2.id == evidence_id)
    )
    assert linked is not None and linked.analysis_request_id is None
    assert not transport.payloads


async def test_concurrent_same_session_submission_creates_at_most_one_request(
    engine: AsyncEngine,
) -> None:
    _, session_id, _, email = await _seed_session(engine)
    await _add_evidence(engine, session_id, observation_timestamp=OBSERVATION)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    transport = RecordingTransport(delay=0.05)

    async def submit() -> int:
        async with factory() as session:
            return (
                await _post(
                    session,
                    AnalysisRequestQueue(transport),
                    session_id,
                    email,
                )
            )[0]

    results = await asyncio.gather(submit(), submit())
    assert sorted(results) == [202, 409]
    assert len(transport.payloads) == 1
    async with factory() as session:
        assert await _count(session, AnalysisRequestV2, session_id) == 1


async def test_session_a_does_not_block_session_b(
    engine: AsyncEngine,
) -> None:
    owner = await _seed_session(engine)
    _, session_b, _, _ = await _seed_session(engine, owner=(owner[0], owner[3]))
    await _add_evidence(engine, owner[1], observation_timestamp=OBSERVATION)
    await _add_evidence(engine, session_b, observation_timestamp=OBSERVATION)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    transport = RecordingTransport()

    async def submit(session_id: uuid.UUID) -> int:
        async with factory() as session:
            return (
                await _post(
                    session,
                    AnalysisRequestQueue(transport),
                    session_id,
                    owner[3],
                )
            )[0]

    assert sorted(await asyncio.gather(submit(owner[1]), submit(session_b))) == [202, 202]
    assert len(transport.payloads) == 2
