from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.api.exception_handlers import register_handlers
from app.auth import hash_password
from app.database.session import get_db_session
from app.models.user import User
from app.trade_workspace.api.routes.trade_sessions import router as rebuild_router
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status

pytestmark = pytest.mark.database


async def _seed_user_and_session(
    engine: AsyncEngine,
    *,
    owner: tuple[uuid.UUID, str] | None = None,
    with_evidence: bool = True,
) -> tuple[uuid.UUID, uuid.UUID, str]:
    if owner is None:
        user_id, email = uuid.uuid4(), f"evidence-{uuid.uuid4()}@example.test"
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
                ticker="TLKM",
                company_name="Telkom Indonesia",
                status=TradeSessionV2Status.DRAFT,
            )
        )
        if with_evidence:
            evidence_types = [
                (EvidenceUploadV2Type.ORDERBOOK, "orderbook.png", "/secret/storage/path/ob.png"),
                (EvidenceUploadV2Type.CHART_3_MONTH, "chart3m.png", "/secret/storage/path/c3.png"),
                (EvidenceUploadV2Type.CHART_6_MONTH, "chart6m.png", "/secret/storage/path/c6.png"),
            ]
            for etype, fname, fpath in evidence_types:
                await connection.execute(
                    EvidenceUploadV2.__table__.insert().values(
                        id=uuid.uuid4(),
                        session_id=session_id,
                        evidence_type=etype,
                        analysis_request_id=None,
                        observation_period=None,
                        file_path=fpath,
                        original_filename=fname,
                        mime_type="image/png",
                        size_bytes=12345,
                        uploaded_at=datetime.now(timezone.utc),
                    )
                )
    return user_id, session_id, email


def _build_app(engine: AsyncEngine) -> FastAPI:
    app = FastAPI()
    register_handlers(app)
    app.include_router(auth_router)
    app.include_router(rebuild_router)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def _override_db() -> AsyncSession:
        async with session_maker() as session:
            yield session
            await session.commit()

    app.dependency_overrides[get_db_session] = _override_db
    return app


async def _login(client: AsyncClient, email: str) -> None:
    res = await client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_read_initial_evidence_success(engine: AsyncEngine) -> None:
    user_id, session_id, email = await _seed_user_and_session(engine, with_evidence=True)
    app = _build_app(engine)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(client, email)

        res = await client.get(f"/api/v2/trade-sessions/{session_id}/initial-evidence")
        assert res.status_code == 200
        data = res.json()

        assert "evidence" in data
        evidence_items = data["evidence"]
        assert len(evidence_items) == 3

        types = [e["evidence_type"] for e in evidence_items]
        assert types == ["ORDERBOOK", "CHART_3_MONTH", "CHART_6_MONTH"]

        filenames = [e["original_filename"] for e in evidence_items]
        assert filenames == ["orderbook.png", "chart3m.png", "chart6m.png"]

        # Ensure no physical file paths or storage internals exposed
        for item in evidence_items:
            assert "file_path" not in item
            assert "/secret/storage" not in str(item)


@pytest.mark.asyncio
async def test_read_initial_evidence_empty_session(engine: AsyncEngine) -> None:
    user_id, session_id, email = await _seed_user_and_session(engine, with_evidence=False)
    app = _build_app(engine)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(client, email)

        res = await client.get(f"/api/v2/trade-sessions/{session_id}/initial-evidence")
        assert res.status_code == 200
        data = res.json()
        assert data["evidence"] == []


@pytest.mark.asyncio
async def test_read_initial_evidence_ownership_enforcement(engine: AsyncEngine) -> None:
    user_id_1, session_id_1, email_1 = await _seed_user_and_session(engine, with_evidence=True)
    user_id_2, session_id_2, email_2 = await _seed_user_and_session(engine, with_evidence=True)
    app = _build_app(engine)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # User 1 tries to access User 2's session -> 404
        await _login(client, email_1)
        res = await client.get(f"/api/v2/trade-sessions/{session_id_2}/initial-evidence")
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_read_initial_evidence_unauthenticated(engine: AsyncEngine) -> None:
    user_id, session_id, email = await _seed_user_and_session(engine, with_evidence=True)
    app = _build_app(engine)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(f"/api/v2/trade-sessions/{session_id}/initial-evidence")
        assert res.status_code == 401
