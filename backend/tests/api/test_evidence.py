"""Tests for Evidence API (TP-1003)."""

from __future__ import annotations

import io
import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.api.routes.evidence import evidence_router
from app.api.routes.evidence import session_router as evidence_session_router
from app.auth import hash_password

pytestmark = pytest.mark.database


# ===================================================================
# Helpers
# ===================================================================


async def _ensure_user_sessions_table(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS user_sessions ("
                "id UUID PRIMARY KEY, "
                "user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, "
                "token_hash VARCHAR(64) NOT NULL UNIQUE, "
                "expires_at TIMESTAMPTZ NOT NULL, "
                "created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), "
                "last_used_at TIMESTAMPTZ, "
                "revoked_at TIMESTAMPTZ"
                ")"
            )
        )
        await conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_user_sessions_token_hash "
                "ON user_sessions(token_hash)"
            )
        )
        await conn.execute(
            text("CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions(user_id)")
        )


async def _make_user(
    engine: AsyncEngine,
    email: str | None = None,
    password: str = "testpass123",
    account_status: str = "ACTIVE",
) -> tuple[uuid.UUID, str]:
    uid = uuid.uuid4()
    pw_hash = hash_password(password)
    unique_email = email or f"ev_{uid.hex[:8]}@test.com"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, account_status) "
                "VALUES (:id, :e, :ph, :st)"
            ),
            {"id": uid, "e": unique_email, "ph": pw_hash, "st": account_status},
        )
    return uid, unique_email


async def _make_session(engine: AsyncEngine, uid: uuid.UUID) -> uuid.UUID:
    sid = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO trade_sessions "
                "(id, owner_id, ticker, lifecycle_status, stable_status) "
                "VALUES (:id, :oid, 'BBRI', 'WATCHING', 'WATCHING')"
            ),
            {"id": sid, "oid": uid},
        )
    return sid


async def _login_user(client: AsyncClient, email: str, password: str = "testpass123") -> str:
    resp = await client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert resp.status_code == 200
    cookie = resp.cookies.get("tradepilot_session")
    assert cookie is not None
    return cookie


def _make_png_bytes(size: int = 1024) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (10, 10), color="red")
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_jpeg_bytes() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (10, 10), color="blue")
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_webp_bytes() -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (10, 10), color="green")
    img.save(buf, format="WebP")
    return buf.getvalue()


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s


def _build_app(db_session: AsyncSession) -> FastAPI:
    app = FastAPI()

    from app.api.exception_handlers import register_handlers
    from app.database.session import get_db_session

    register_handlers(app)

    app.include_router(auth_router)
    app.include_router(evidence_session_router)
    app.include_router(evidence_router)

    async def _override() -> AsyncSession:
        return db_session

    app.dependency_overrides[get_db_session] = _override
    return app


@pytest.fixture
async def client(engine: AsyncEngine, db_session: AsyncSession) -> AsyncClient:
    app = _build_app(db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ===================================================================
# Authentication and ownership
# ===================================================================


class TestAuth:
    async def test_anonymous_upload_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        png = _make_png_bytes()
        resp = await client.post(
            f"/api/trade-sessions/{uuid.uuid4()}/evidence",
            files={"file": ("test.png", png, "image/png")},
            data={"evidence_type": "ORDERBOOK_SCREENSHOT"},
        )
        assert resp.status_code == 401

    async def test_anonymous_list_rejected(self, engine: AsyncEngine, client: AsyncClient) -> None:
        resp = await client.get(f"/api/trade-sessions/{uuid.uuid4()}/evidence")
        assert resp.status_code == 401

    async def test_anonymous_file_rejected(self, engine: AsyncEngine, client: AsyncClient) -> None:
        resp = await client.get(f"/api/evidence/{uuid.uuid4()}/file")
        assert resp.status_code == 401

    async def test_cross_user_upload_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid1, email1 = await _make_user(engine)
        uid2, email2 = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid1)
        cookie = await _login_user(client, email2)
        png = _make_png_bytes()
        resp = await client.post(
            f"/api/trade-sessions/{sid}/evidence",
            files={"file": ("test.png", png, "image/png")},
            data={"evidence_type": "ORDERBOOK_SCREENSHOT"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 404


# ===================================================================
# Upload
# ===================================================================


class TestUpload:
    async def test_upload_png(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid)
        cookie = await _login_user(client, email)
        png = _make_png_bytes()
        resp = await client.post(
            f"/api/trade-sessions/{sid}/evidence",
            files={"file": ("chart.png", png, "image/png")},
            data={"evidence_type": "CHART_THREE_MONTH"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["evidence_type"] == "CHART_THREE_MONTH"
        assert data["status"] == "AVAILABLE"
        assert data["original_filename"] == "chart.png"
        assert data["mime_type"] == "image/png"

    async def test_upload_jpeg(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid)
        cookie = await _login_user(client, email)
        jpeg = _make_jpeg_bytes()
        resp = await client.post(
            f"/api/trade-sessions/{sid}/evidence",
            files={"file": ("photo.jpg", jpeg, "image/jpeg")},
            data={"evidence_type": "BROKER_SUMMARY"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 201

    async def test_upload_webp(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid)
        cookie = await _login_user(client, email)
        webp = _make_webp_bytes()
        resp = await client.post(
            f"/api/trade-sessions/{sid}/evidence",
            files={"file": ("image.webp", webp, "image/webp")},
            data={"evidence_type": "CHART_SIX_MONTH"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 201

    async def test_market_timestamp_retained(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid)
        cookie = await _login_user(client, email)
        png = _make_png_bytes()
        ts = "2026-07-15T09:30:00+00:00"
        resp = await client.post(
            f"/api/trade-sessions/{sid}/evidence",
            files={"file": ("chart.png", png, "image/png")},
            data={"evidence_type": "CHART_THREE_MONTH", "market_timestamp": ts},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 201
        assert resp.json()["market_timestamp"] is not None

    async def test_unsupported_type_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid)
        cookie = await _login_user(client, email)
        png = _make_png_bytes()
        resp = await client.post(
            f"/api/trade-sessions/{sid}/evidence",
            files={"file": ("chart.png", png, "image/png")},
            data={"evidence_type": "INVALID_TYPE"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 422

    async def test_empty_file_rejected(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.post(
            f"/api/trade-sessions/{sid}/evidence",
            files={"file": ("empty.png", b"", "image/png")},
            data={"evidence_type": "ORDERBOOK_SCREENSHOT"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 422


# ===================================================================
# Listing
# ===================================================================


class TestList:
    async def test_list_evidence(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid)
        cookie = await _login_user(client, email)
        png = _make_png_bytes()
        await client.post(
            f"/api/trade-sessions/{sid}/evidence",
            files={"file": ("c1.png", png, "image/png")},
            data={"evidence_type": "CHART_THREE_MONTH"},
            cookies={"tradepilot_session": cookie},
        )
        await client.post(
            f"/api/trade-sessions/{sid}/evidence",
            files={"file": ("c2.png", png, "image/png")},
            data={"evidence_type": "CHART_SIX_MONTH"},
            cookies={"tradepilot_session": cookie},
        )
        resp = await client.get(
            f"/api/trade-sessions/{sid}/evidence",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    async def test_empty_list(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/trade-sessions/{sid}/evidence",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_cross_user_list_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid1, email1 = await _make_user(engine)
        uid2, email2 = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid1)
        cookie = await _login_user(client, email2)
        resp = await client.get(
            f"/api/trade-sessions/{sid}/evidence",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 404


# ===================================================================
# File serving
# ===================================================================


class TestFileServing:
    async def test_download_exact_bytes(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid)
        cookie = await _login_user(client, email)
        png = _make_png_bytes()
        upload_resp = await client.post(
            f"/api/trade-sessions/{sid}/evidence",
            files={"file": ("chart.png", png, "image/png")},
            data={"evidence_type": "CHART_THREE_MONTH"},
            cookies={"tradepilot_session": cookie},
        )
        evid = upload_resp.json()["id"]
        file_resp = await client.get(
            f"/api/evidence/{evid}/file",
            cookies={"tradepilot_session": cookie},
        )
        assert file_resp.status_code == 200
        assert file_resp.content == png
        assert file_resp.headers["content-type"] == "image/png"

    async def test_cross_user_file_rejected(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid1, email1 = await _make_user(engine)
        uid2, email2 = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid1)
        cookie1 = await _login_user(client, email1)
        png = _make_png_bytes()
        upload_resp = await client.post(
            f"/api/trade-sessions/{sid}/evidence",
            files={"file": ("chart.png", png, "image/png")},
            data={"evidence_type": "CHART_THREE_MONTH"},
            cookies={"tradepilot_session": cookie1},
        )
        evid = upload_resp.json()["id"]
        cookie2 = await _login_user(client, email2)
        file_resp = await client.get(
            f"/api/evidence/{evid}/file",
            cookies={"tradepilot_session": cookie2},
        )
        assert file_resp.status_code == 404

    async def test_unknown_evidence_404(self, engine: AsyncEngine, client: AsyncClient) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        cookie = await _login_user(client, email)
        resp = await client.get(
            f"/api/evidence/{uuid.uuid4()}/file",
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 404


# ===================================================================
# Indonesian error messages
# ===================================================================


class TestIndonesianMessages:
    async def test_unsupported_mime_message(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        uid, email = await _make_user(engine)
        await _ensure_user_sessions_table(engine)
        sid = await _make_session(engine, uid)
        cookie = await _login_user(client, email)
        resp = await client.post(
            f"/api/trade-sessions/{sid}/evidence",
            files={"file": ("test.txt", b"not an image", "text/plain")},
            data={"evidence_type": "ORDERBOOK_SCREENSHOT"},
            cookies={"tradepilot_session": cookie},
        )
        assert resp.status_code == 422
        body = resp.json()
        error_obj = body.get("error", {})
        msg = error_obj.get("message", "")
        assert len(msg) > 5  # non-trivial Indonesian message


# ===================================================================
# Boundaries
# ===================================================================


class TestBoundaries:
    async def test_no_analysis_endpoint(self, engine: AsyncEngine, client: AsyncClient) -> None:
        resp = await client.get("/api/analysis")
        assert resp.status_code == 404

    async def test_no_analysis_job_endpoint(
        self, engine: AsyncEngine, client: AsyncClient
    ) -> None:
        resp = await client.post("/api/analysis-jobs", json={})
        assert resp.status_code == 404
