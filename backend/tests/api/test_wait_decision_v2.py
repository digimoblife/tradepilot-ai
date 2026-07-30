from __future__ import annotations

import uuid
from datetime import datetime, timezone
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

pytestmark = pytest.mark.database


async def _seed(
    engine: AsyncEngine,
    status: TradeSessionV2Status,
    *,
    owner: tuple[uuid.UUID, str] | None = None,
    with_position: bool = False,
) -> tuple[uuid.UUID, uuid.UUID, str]:
    if owner is None:
        user_id, email = uuid.uuid4(), f"p62-{uuid.uuid4()}@example.test"
        create_user = True
    else:
        user_id, email = owner
        create_user = False
    session_id = uuid.uuid4()
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
        if with_position:
            await connection.execute(
                PositionV2.__table__.insert().values(
                    id=uuid.uuid4(),
                    session_id=session_id,
                    entry_price=Decimal("100"),
                    entry_at=datetime.now(timezone.utc),
                    quantity=Decimal("1"),
                    stop_loss=Decimal("95"),
                    target_price=Decimal("110"),
                    status=PositionV2Status.OPEN,
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


async def _post_wait(
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
        response = await client.post(
            f"/api/v2/trade-sessions/{session_id}/decisions/wait"
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


async def test_owner_can_wait_from_analyzed_and_p61_availability_remains_available(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    user_id, session_id, email = await _seed(engine, TradeSessionV2Status.ANALYZED)
    code, payload = await _post_wait(db_session, session_id, email)
    assert code == 201
    assert payload["session_id"] == str(session_id)
    assert payload["decision_type"] == "WAIT"
    assert payload["session_status"] == "WAITING"
    decision = await db_session.scalar(
        select(SessionDecisionV2).where(SessionDecisionV2.id == uuid.UUID(payload["decision_id"]))
    )
    assert decision is not None
    assert decision.session_id == session_id
    assert decision.decision is SessionDecisionV2Decision.WAIT
    session = await db_session.scalar(
        select(TradeSessionV2).where(TradeSessionV2.id == session_id)
    )
    assert session is not None
    assert session.user_id == user_id
    assert session.status is TradeSessionV2Status.WAITING
    assert session.closed_at is None

    app = _app(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
        availability = await client.get(
            f"/api/v2/trade-sessions/{session_id}/available-actions"
        )
    assert availability.status_code == 200
    assert availability.json()["available_actions"] == ["BUY", "WAIT", "SKIP"]


async def test_repeated_wait_is_auditable_and_preserves_prior_decision(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, email = await _seed(engine, TradeSessionV2Status.WAITING)
    first_code, first = await _post_wait(db_session, session_id, email)
    second_code, second = await _post_wait(db_session, session_id, email)
    assert first_code == second_code == 201
    assert first["decision_id"] != second["decision_id"]
    assert first["decision_type"] == second["decision_type"] == "WAIT"
    assert first["session_status"] == second["session_status"] == "WAITING"
    assert await _count(db_session, SessionDecisionV2, session_id) == 2
    decisions = list(
        (
            await db_session.scalars(
                select(SessionDecisionV2)
                .where(SessionDecisionV2.session_id == session_id)
                .order_by(SessionDecisionV2.created_at, SessionDecisionV2.id)
            )
        ).all()
    )
    assert [item.decision for item in decisions] == [
        SessionDecisionV2Decision.WAIT,
        SessionDecisionV2Decision.WAIT,
    ]


@pytest.mark.parametrize(
    "status",
    [
        TradeSessionV2Status.DRAFT,
        TradeSessionV2Status.ANALYZING,
        TradeSessionV2Status.OPEN_POSITION,
        TradeSessionV2Status.CLOSED,
        TradeSessionV2Status.CLOSED_SKIPPED,
    ],
)
async def test_wait_rejects_ineligible_status_without_partial_persistence(
    engine: AsyncEngine, db_session: AsyncSession, status: TradeSessionV2Status
) -> None:
    _, session_id, email = await _seed(engine, status)
    code, payload = await _post_wait(db_session, session_id, email)
    assert code == 409
    assert payload["error"]["code"] == "WAIT_NOT_ALLOWED"
    assert await _count(db_session, SessionDecisionV2, session_id) == 0
    session = await db_session.scalar(
        select(TradeSessionV2).where(TradeSessionV2.id == session_id)
    )
    assert session is not None
    assert session.status is status


async def test_wait_rejects_existing_position_and_creates_no_related_records(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, email = await _seed(
        engine, TradeSessionV2Status.ANALYZED, with_position=True
    )
    code, payload = await _post_wait(db_session, session_id, email)
    assert code == 409
    assert payload["error"]["code"] == "WAIT_POSITION_EXISTS"
    assert await _count(db_session, SessionDecisionV2, session_id) == 0
    assert await _count(db_session, TradeClosureV2, session_id) == 0
    assert await _count(db_session, AnalysisRequestV2, session_id) == 0


async def test_wait_preserves_evidence_analysis_and_closed_at(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, email = await _seed(engine, TradeSessionV2Status.ANALYZED)
    request_id = uuid.uuid4()
    evidence_ids = [uuid.uuid4() for _ in range(3)]
    async with engine.begin() as connection:
        await connection.execute(
            AnalysisRequestV2.__table__.insert().values(
                id=request_id,
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                status=AnalysisRequestV2Status.COMPLETED,
                provider="gemini",
                model="configured-model",
                prompt_version="v1",
                input_snapshot={"preserved": True},
                processed_response={"summary": "preserved"},
            )
        )
        for evidence_id, evidence_type in zip(evidence_ids, EvidenceUploadV2Type, strict=True):
            await connection.execute(
                EvidenceUploadV2.__table__.insert().values(
                    id=evidence_id,
                    session_id=session_id,
                    analysis_request_id=request_id,
                    evidence_type=evidence_type,
                    file_path=f"local/{evidence_id}.png",
                    original_filename=f"{evidence_type.value}.png",
                    mime_type="image/png",
                    size_bytes=10,
                )
            )
    code, _ = await _post_wait(db_session, session_id, email)
    assert code == 201
    assert await _count(db_session, EvidenceUploadV2, session_id) == 3
    request = await db_session.scalar(
        select(AnalysisRequestV2).where(AnalysisRequestV2.id == request_id)
    )
    assert request is not None
    assert request.processed_response == {"summary": "preserved"}
    assert await _count(db_session, PositionV2, session_id) == 0
    session = await db_session.scalar(
        select(TradeSessionV2).where(TradeSessionV2.id == session_id)
    )
    assert session is not None
    assert session.status is TradeSessionV2Status.WAITING
    assert session.closed_at is None


async def test_wait_enforces_ownership_and_authentication(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    _, session_id, owner_email = await _seed(engine, TradeSessionV2Status.ANALYZED)
    _, missing_owner_session, other_email = await _seed(engine, TradeSessionV2Status.ANALYZED)
    cross_code, _ = await _post_wait(db_session, session_id, other_email)
    missing_code, _ = await _post_wait(db_session, uuid.uuid4(), owner_email)
    unauthenticated_code, _ = await _post_wait(db_session, missing_owner_session, None)
    assert cross_code == 404
    assert missing_code == 404
    assert unauthenticated_code == 401


async def test_wait_is_scoped_to_one_session(
    engine: AsyncEngine, db_session: AsyncSession
) -> None:
    owner = (uuid.uuid4(), f"p62-shared-{uuid.uuid4()}@example.test")
    async with engine.begin() as connection:
        await connection.execute(
            User.__table__.insert().values(
                id=owner[0], email=owner[1], password_hash=hash_password("testpass123")
            )
        )
    _, session_a, email = await _seed(
        engine, TradeSessionV2Status.ANALYZED, owner=owner
    )
    _, session_b, _ = await _seed(engine, TradeSessionV2Status.ANALYZED, owner=owner)
    code, _ = await _post_wait(db_session, session_a, email)
    assert code == 201
    first = await db_session.scalar(select(TradeSessionV2).where(TradeSessionV2.id == session_a))
    second = await db_session.scalar(select(TradeSessionV2).where(TradeSessionV2.id == session_b))
    assert first is not None and second is not None
    assert first.status is TradeSessionV2Status.WAITING
    assert second.status is TradeSessionV2Status.ANALYZED
    assert await _count(db_session, SessionDecisionV2, session_a) == 1
    assert await _count(db_session, SessionDecisionV2, session_b) == 0
