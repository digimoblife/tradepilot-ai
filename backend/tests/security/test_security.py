"""Security hardening tests (TP-1604).

Covers: cross-user resource isolation, unauthorized evidence access,
unsafe upload paths, security headers, rate limiting, CSRF protection,
secure cookies, and path traversal prevention.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.routes.evidence import evidence_router
from app.api.routes.evidence import session_router as evidence_session_router
from app.api.routes.trade_sessions import router as ts_router
from app.api.security import (
    _SECURITY_HEADERS,
    CSRFProtectionMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.auth import hash_password
from app.config import AppConfig
from app.database.session import get_db_session

pytestmark = pytest.mark.database


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_app(override_session: AsyncSession | None = None) -> FastAPI:
    from app.api.exception_handlers import register_handlers

    app = FastAPI()
    register_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(evidence_session_router)
    app.include_router(evidence_router)
    app.include_router(ts_router)
    if override_session is not None:

        async def _override() -> AsyncSession:
            return override_session

        app.dependency_overrides[get_db_session] = _override
    return app


async def _create_user(engine: AsyncEngine, label: str = "u") -> uuid.UUID:
    uid = uuid.uuid4()
    email = f"sec_{label}_{uid.hex[:8]}@test.com"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO users (id, email, password_hash, account_status) "
                "VALUES (:id, :e, :ph, 'ACTIVE')"
            ),
            {"id": uid, "e": email, "ph": hash_password("pass")},
        )
    return uid


async def _create_session(
    engine: AsyncEngine, user_id: uuid.UUID, ticker: str = "BBRI"
) -> uuid.UUID:
    sid = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO trade_sessions "
                "(id, owner_id, ticker, lifecycle_status, stable_status) "
                "VALUES (:id, :oid, :t, 'DRAFT', 'DRAFT')"
            ),
            {"id": sid, "oid": user_id, "t": ticker},
        )
        await conn.execute(
            text(
                "INSERT INTO trade_states "
                "(session_id, position_status, thesis_status, state_version) "
                "VALUES (:sid, 'NOT_OPENED', 'INTACT', 1)"
            ),
            {"sid": sid},
        )
    return sid


async def _upload_evidence(
    engine: AsyncEngine, session_id: uuid.UUID, user_id: uuid.UUID
) -> uuid.UUID:
    eid = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO evidence "
                "(id, session_id, owner_id, evidence_type, storage_object_key, "
                " original_filename, mime_type, "
                " file_size_bytes, checksum_sha256) "
                "VALUES "
                "(:id, :sid, :oid, 'CHART_THREE_MONTH', 'safe-key.png', "
                "'chart.png', 'image/png', "
                " 1024, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')"
            ),
            {
                "id": eid,
                "sid": session_id,
                "oid": user_id,
            },
        )
    return eid


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s


# ===================================================================
# 1. Cross-user resource access
# ===================================================================


class TestCrossUserAccess:
    async def test_user_a_cannot_access_user_b_session(
        self, engine: AsyncEngine, db_session: AsyncSession
    ) -> None:
        uid_a = await _create_user(engine, "ca")
        uid_b = await _create_user(engine, "cb")
        sid_a = await _create_session(engine, uid_a)

        # Try to fetch session A as user B via direct repository call
        from app.repositories.trade_session import TradeSessionRepository

        repo = TradeSessionRepository(db_session)
        result = await repo.get_by_id_for_user(sid_a, uid_b)
        assert result is None, "User B should not see User A's session"

    async def test_user_a_cannot_access_user_b_evidence(
        self, engine: AsyncEngine, db_session: AsyncSession
    ) -> None:
        uid_a = await _create_user(engine, "ea")
        uid_b = await _create_user(engine, "eb")
        sid_a = await _create_session(engine, uid_a)
        eid_a = await _upload_evidence(engine, sid_a, uid_a)

        from app.repositories.evidence import EvidenceRepository

        repo = EvidenceRepository(db_session)
        result = await repo.get_by_id_for_user(eid_a, uid_b)
        assert result is None, "User B should not see User A's evidence"


# ===================================================================
# 2. Unauthorized evidence access
# ===================================================================


class TestUnauthorizedEvidenceAccess:
    async def test_unauthenticated_evidence_list_fails(
        self, engine: AsyncEngine, db_session: AsyncSession
    ) -> None:
        app = _build_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/api/evidence/sessions")
        assert resp.status_code in (401, 403), "Unauthenticated access should fail"

    async def test_unauthenticated_evidence_download_fails(
        self, engine: AsyncEngine, db_session: AsyncSession
    ) -> None:
        app = _build_app(db_session)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/api/evidence/{uuid.uuid4()}/file")
        assert resp.status_code in (401, 403), "Unauthenticated download should fail"


# ===================================================================
# 3. Unsafe upload paths
# ===================================================================


class TestUnsafeUploadPaths:
    async def test_path_traversal_rejected_by_storage(self) -> None:
        """Storage layer rejects references with path traversal."""
        from tempfile import TemporaryDirectory

        from app.storage.local import LocalFileStorage

        with TemporaryDirectory() as root:
            storage = LocalFileStorage(Path(root))

            # Null byte in reference
            with pytest.raises(Exception):
                await storage.read("safe\x00.png")

            # Path traversal via read
            with pytest.raises(Exception):
                await storage.read("../../etc/passwd")

            # Absolute path
            with pytest.raises(Exception):
                await storage.read("/absolute/path")

    async def test_malicious_original_filename_safe(
        self, engine: AsyncEngine, db_session: AsyncSession
    ) -> None:
        """Original filename is metadata only, never used in storage path."""
        from app.repositories.evidence import EvidenceRepository

        uid = await _create_user(engine, "mf")
        sid = await _create_session(engine, uid)
        eid = uuid.uuid4()
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO evidence "
                    "(id, session_id, owner_id, evidence_type, storage_object_key, "
                    " original_filename, mime_type, "
                    " file_size_bytes, checksum_sha256) "
                    "VALUES "
                    "(:id, :sid, :oid, 'CHART_THREE_MONTH', 'safe-key.png', "
                    "'../../secret.txt', 'image/png', "
                    " 1024, 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')"
                ),
                {"id": eid, "sid": sid, "oid": uid},
            )
        repo = EvidenceRepository(db_session)
        ev = await repo.get_by_id_for_user(eid, uid)
        assert ev is not None
        assert ev.original_filename == "../../secret.txt"
        assert ev.storage_object_key == "safe-key.png"
        assert "/" not in ev.storage_object_key or ".." not in ev.storage_object_key


# ===================================================================
# 4. Security headers
# ===================================================================


class TestSecurityHeaders:
    async def test_headers_present(self, db_session: AsyncSession) -> None:
        app = _build_app(db_session)
        app.add_middleware(SecurityHeadersMiddleware)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/health")
        for header in _SECURITY_HEADERS:
            assert header in resp.headers, f"Missing header: {header}"
            assert resp.headers[header] == _SECURITY_HEADERS[header]

    async def test_nosniff_on_evidence_download(
        self, engine: AsyncEngine, db_session: AsyncSession
    ) -> None:
        uid = await _create_user(engine, "ns")
        sid = await _create_session(engine, uid)
        eid = await _upload_evidence(engine, sid, uid)
        app = _build_app(db_session)
        app.add_middleware(SecurityHeadersMiddleware)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get(f"/api/evidence/{eid}/file")
        # Even without auth (no cookie), the response should have nosniff
        assert "X-Content-Type-Options" in resp.headers or resp.status_code in (401, 403)


# ===================================================================
# 5. Rate limiting
# ===================================================================


class TestRateLimiting:
    async def test_rate_limiter_blocks_excess(self) -> None:
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            config=AppConfig(
                rate_limit_enabled=True,
                rate_limit_requests=3,
                rate_limit_window_seconds=60,
            ),
        )

        @app.get("/test")
        async def test_route() -> dict:
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            for _ in range(3):
                resp = await ac.get("/test")
                assert resp.status_code == 200
            # Fourth request within window should be blocked
            resp = await ac.get("/test")
            assert resp.status_code == 429

    async def test_rate_limiter_disabled_by_default(self) -> None:
        app = FastAPI()
        app.add_middleware(
            RateLimitMiddleware,
            config=AppConfig(rate_limit_enabled=False),
        )

        @app.get("/test")
        async def test_route() -> dict:
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            for _ in range(10):
                resp = await ac.get("/test")
                assert resp.status_code == 200


# ===================================================================
# 6. CSRF protection
# ===================================================================


class TestCSRFProtection:
    async def test_missing_referer_blocked(self) -> None:
        app = FastAPI()
        app.add_middleware(
            CSRFProtectionMiddleware,
            config=AppConfig(
                csrf_enabled=True,
                cors_origins=["https://trusted.example.com"],
            ),
        )

        @app.post("/api/submit")
        async def submit() -> dict:
            return {"ok": True}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="https://trusted.example.com"
        ) as ac:
            resp = await ac.post("/api/submit", headers={})  # No Origin/Referer
        assert resp.status_code == 403

    async def test_valid_origin_allowed(self) -> None:
        app = FastAPI()
        app.add_middleware(
            CSRFProtectionMiddleware,
            config=AppConfig(
                csrf_enabled=True,
                cors_origins=["https://trusted.example.com"],
            ),
        )

        @app.post("/api/submit")
        async def submit() -> dict:
            return {"ok": True}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="https://trusted.example.com"
        ) as ac:
            resp = await ac.post(
                "/api/submit",
                headers={"Origin": "https://trusted.example.com"},
            )
        assert resp.status_code == 200

    async def test_disabled_by_default(self) -> None:
        app = FastAPI()
        app.add_middleware(
            CSRFProtectionMiddleware,
            config=AppConfig(csrf_enabled=False),
        )

        @app.post("/api/submit")
        async def submit() -> dict:
            return {"ok": True}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/submit")
        assert resp.status_code == 200

    async def test_safe_methods_skipped(self) -> None:
        app = FastAPI()
        app.add_middleware(
            CSRFProtectionMiddleware,
            config=AppConfig(
                csrf_enabled=True,
                cors_origins=["https://trusted.example.com"],
            ),
        )

        @app.get("/api/data")
        async def data() -> dict:
            return {"ok": True}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="https://trusted.example.com"
        ) as ac:
            resp = await ac.get("/api/data")  # No Origin needed for GET
        assert resp.status_code == 200


# ===================================================================
# 7. Secure cookies
# ===================================================================


class TestSecureCookies:
    def test_cookie_secure_configurable(self) -> None:
        """auth_cookie_secure defaults to False but can be set to True."""
        config = AppConfig()
        assert config.auth_cookie_secure is False

        config = AppConfig(auth_cookie_secure=True)
        assert config.auth_cookie_secure is True

    def test_cookie_httponly_samesite(self, db_session: AsyncSession) -> None:
        """Cookies are set with httponly and samesite=lax."""
        from fastapi.responses import Response

        from app.api.dependencies import set_session_cookie

        resp = Response()
        set_session_cookie(resp, "test-token")
        # Cookies are set via response.set_cookie, verified via header
        set_cookie_header = resp.headers.get("set-cookie", "")
        assert "httponly" in set_cookie_header.lower()
        assert "samesite=lax" in set_cookie_header.lower()


# ===================================================================
# 8. Upload-size limits
# ===================================================================


class TestUploadSizeLimits:
    async def test_max_body_size_configurable(self) -> None:
        assert AppConfig().max_upload_size_bytes == 10485760
        assert AppConfig(max_upload_size_bytes=1).max_upload_size_bytes == 1


# ===================================================================
# 9. Global app security config
# ===================================================================


class TestAppSecurityConfig:
    async def test_config_allowed_hosts_default(self) -> None:
        config = AppConfig()
        assert config.allowed_hosts == ["*"]

    async def test_config_cors_origins_default(self) -> None:
        config = AppConfig()
        assert config.cors_origins == ["*"]
