from __future__ import annotations

import uuid

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
from app.trade_workspace.models.analysis_request import AnalysisRequestV2
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2
from app.trade_workspace.models.trade_session import TradeSessionV2

pytestmark = pytest.mark.database


async def _make_user(engine: AsyncEngine) -> tuple[uuid.UUID, str]:
    user_id = uuid.uuid4()
    email = f"p51-{user_id}@example.test"
    async with engine.begin() as connection:
        await connection.execute(
            User.__table__.insert().values(
                id=user_id,
                email=email,
                password_hash=hash_password("testpass123"),
            )
        )
    return user_id, email


def _build_app(db_session: AsyncSession) -> FastAPI:
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


@pytest.fixture
async def client(engine: AsyncEngine, db_session: AsyncSession) -> AsyncClient:
    app = _build_app(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def _login(client: AsyncClient, email: str) -> None:
    response = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "testpass123"},
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    "payload",
    [
        {"company_name": "Bank BRI"},
        {"ticker": "   ", "company_name": "Bank BRI"},
        {"ticker": "BBRI", "company_name": ""},
        {"ticker": "BBRI", "company_name": "   "},
    ],
)
async def test_create_rejects_missing_or_blank_required_fields(
    client: AsyncClient, engine: AsyncEngine, payload: dict[str, str]
) -> None:
    _, email = await _make_user(engine)
    await _login(client, email)

    response = await client.post("/api/v2/trade-sessions", json=payload)

    assert response.status_code == 422


async def test_create_persists_owned_draft_without_related_records(
    client: AsyncClient, engine: AsyncEngine, db_session: AsyncSession
) -> None:
    user_id, email = await _make_user(engine)
    await _login(client, email)

    response = await client.post(
        "/api/v2/trade-sessions",
        json={
            "ticker": "  bbri ",
            "company_name": "  Bank BRI  ",
            "note": "watch support",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ticker"] == "BBRI"
    assert body["company_name"] == "Bank BRI"
    assert body["note"] == "watch support"
    assert body["status"] == "DRAFT"
    assert body["closed_at"] is None
    assert set(body) == {
        "id",
        "ticker",
        "company_name",
        "status",
        "note",
        "created_at",
        "updated_at",
        "closed_at",
        "archived_at",
    }

    persisted = await db_session.scalar(
        select(TradeSessionV2).where(TradeSessionV2.id == uuid.UUID(body["id"]))
    )
    assert persisted is not None
    assert persisted.user_id == user_id
    assert persisted.status.value == "DRAFT"
    assert persisted.note == "watch support"
    assert await db_session.scalar(select(func.count(AnalysisRequestV2.id)).where(AnalysisRequestV2.session_id == persisted.id)) == 0
    assert await db_session.scalar(select(func.count(EvidenceUploadV2.id)).where(EvidenceUploadV2.session_id == persisted.id)) == 0

    override_response = await client.post(
        "/api/v2/trade-sessions",
        json={"ticker": "BBCA", "company_name": "Bank Central Asia", "status": "CLOSED"},
    )
    assert override_response.status_code == 422

    omitted_note = await client.post(
        "/api/v2/trade-sessions",
        json={"ticker": "TLKM", "company_name": "Telkom Indonesia"},
    )
    assert omitted_note.status_code == 201
    assert omitted_note.json()["note"] is None


async def test_list_and_detail_are_owned_ordered_and_minimal(
    client: AsyncClient, engine: AsyncEngine
) -> None:
    owner_id, owner_email = await _make_user(engine)
    _, other_email = await _make_user(engine)
    await _login(client, owner_email)

    first = await client.post(
        "/api/v2/trade-sessions",
        json={"ticker": "BBRI", "company_name": "Bank BRI"},
    )
    second = await client.post(
        "/api/v2/trade-sessions",
        json={"ticker": "BBCA", "company_name": "Bank Central Asia"},
    )
    assert first.status_code == 201
    assert second.status_code == 201

    listed = await client.get("/api/v2/trade-sessions")
    assert listed.status_code == 200
    sessions = listed.json()["sessions"]
    expected_order = sorted(
        [first.json(), second.json()],
        key=lambda item: (item["created_at"], item["id"]),
        reverse=True,
    )
    assert [item["id"] for item in sessions] == [item["id"] for item in expected_order]
    assert all(item["status"] == "DRAFT" for item in sessions)
    assert all(set(item) == set(sessions[0]) for item in sessions)
    assert owner_id == (await _owner_id(engine, uuid.UUID(first.json()["id"])))

    detail = await client.get(f"/api/v2/trade-sessions/{first.json()['id']}")
    assert detail.status_code == 200
    assert set(detail.json()) == {
        "id",
        "ticker",
        "company_name",
        "status",
        "note",
        "created_at",
        "updated_at",
        "closed_at",
        "archived_at",
    }
    assert not {
        "evidence",
        "analyses",
        "decisions",
        "position",
        "closure",
    } & set(detail.json())

    await client.post("/api/auth/logout")
    await _login(client, other_email)
    cross_user = await client.get(f"/api/v2/trade-sessions/{first.json()['id']}")
    missing = await client.get(f"/api/v2/trade-sessions/{uuid.uuid4()}")
    assert cross_user.status_code == 404
    assert missing.status_code == 404
    assert cross_user.json()["error"]["code"] == "SESSION_NOT_FOUND"


async def test_all_session_endpoints_require_authentication(
    client: AsyncClient,
) -> None:
    session_id = uuid.uuid4()
    assert (await client.post("/api/v2/trade-sessions", json={})).status_code == 401
    assert (await client.get("/api/v2/trade-sessions")).status_code == 401
    assert (await client.get(f"/api/v2/trade-sessions/{session_id}")).status_code == 401


async def _owner_id(engine: AsyncEngine, session_id: uuid.UUID) -> uuid.UUID:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        return await session.scalar(
            select(TradeSessionV2.user_id).where(TradeSessionV2.id == session_id)
        )
