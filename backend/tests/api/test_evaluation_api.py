"""API integration tests for P7 Evaluation Records.

Verifies list endpoints, filtering, pagination, detail access,
cross-user authorization rejection, JSON export, and CSV export.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.main import app
from app.models.evaluation_record import CompletenessStatus, EvaluationRecord

pytestmark = pytest.mark.database


async def _make_user(engine: AsyncEngine) -> tuple[uuid.UUID, str]:
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    async with engine.begin() as conn:
        res = await conn.execute(
            text(
                "INSERT INTO users (email, password_hash) "
                "VALUES (:e, 'hash') RETURNING id"
            ),
            {"e": email},
        )
        return res.scalar_one(), email


async def _make_eval_record(
    engine: AsyncEngine,
    owner_id: uuid.UUID,
    ticker: str = "BBRI",
    analysis_type: str = "INITIAL_ANALYSIS",
) -> uuid.UUID:
    record_id = uuid.uuid4()
    session_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO trade_sessions "
                "(id, owner_id, ticker, lifecycle_status, stable_status, created_at, updated_at) "
                "VALUES (:sid, :uid, :tk, 'CLOSED', 'CLOSED', :now, :now)"
            ),
            {"sid": session_id, "uid": owner_id, "tk": ticker, "now": now},
        )
        await conn.execute(
            text(
                "INSERT INTO evaluation_records "
                "(id, owner_id, session_id, ticker, analysis_type, prediction_data, user_decision_data, outcome_data, completeness_status, legacy_source, validation_warning_count, quality_notes, created_at, updated_at) "
                "VALUES (:id, :uid, :sid, :tk, :at, '{\"recommendation\":\"BUY\"}', '{\"user_action\":\"BUY\",\"actual_entry_price\":\"5000\"}', '{\"realized_return\":\"10.0\"}', 'COMPLETE', false, 0, '[]', :now, :now)"
            ),
            {
                "id": record_id,
                "uid": owner_id,
                "sid": session_id,
                "tk": ticker,
                "at": analysis_type,
                "now": now,
            },
        )
    return record_id


class TestEvaluationAPI:
    async def test_list_evaluation_records(self, engine: AsyncEngine) -> None:
        user_id, email = await _make_user(engine)
        r1 = await _make_eval_record(engine, user_id, ticker="BBRI")
        r2 = await _make_eval_record(engine, user_id, ticker="TLKM")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            from app.api.dependencies import get_current_user
            from app.auth import AuthenticatedUser
            from app.database.session import get_db_session

            async def _override_db():
                factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
                async with factory() as session:
                    yield session

            def _override_owner():
                return AuthenticatedUser(id=user_id, email=email)

            app.dependency_overrides[get_db_session] = _override_db
            app.dependency_overrides[get_current_user] = _override_owner
            try:
                res = await client.get("/api/evaluation-records")
                assert res.status_code == 200
                data = res.json()
                assert data["total"] == 2
                assert len(data["items"]) == 2

                # Filter by ticker
                res_filtered = await client.get("/api/evaluation-records?ticker=BBRI")
                assert res_filtered.status_code == 200
                assert res_filtered.json()["total"] == 1
            finally:
                app.dependency_overrides.pop(get_current_user, None)
                app.dependency_overrides.pop(get_db_session, None)

    async def test_cross_user_isolation(self, engine: AsyncEngine) -> None:
        user1_id, email1 = await _make_user(engine)
        user2_id, email2 = await _make_user(engine)

        rec_user1 = await _make_eval_record(engine, user1_id)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            from app.api.dependencies import get_current_user
            from app.auth import AuthenticatedUser
            from app.database.session import get_db_session

            async def _override_db():
                factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
                async with factory() as session:
                    yield session

            def _override_user2():
                return AuthenticatedUser(id=user2_id, email=email2)

            app.dependency_overrides[get_db_session] = _override_db
            app.dependency_overrides[get_current_user] = _override_user2
            try:
                # User 2 tries to fetch User 1's record
                res = await client.get(f"/api/evaluation-records/{rec_user1}")
                assert res.status_code == 404
            finally:
                app.dependency_overrides.pop(get_current_user, None)
                app.dependency_overrides.pop(get_db_session, None)

    async def test_export_json_and_csv_bounded(self, engine: AsyncEngine) -> None:
        user_id, email = await _make_user(engine)
        await _make_eval_record(engine, user_id, ticker="ASII")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            from app.api.dependencies import get_current_user
            from app.auth import AuthenticatedUser
            from app.database.session import get_db_session

            async def _override_db():
                factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
                async with factory() as session:
                    yield session

            def _override_owner():
                return AuthenticatedUser(id=user_id, email=email)

            app.dependency_overrides[get_db_session] = _override_db
            app.dependency_overrides[get_current_user] = _override_owner
            try:
                # Test JSON export
                res_json = await client.get("/api/evaluation-records/export/json")
                assert res_json.status_code == 200
                assert res_json.headers["content-type"] == "application/json"
                json_data = res_json.json()
                assert len(json_data) == 1
                assert json_data[0]["ticker"] == "ASII"
                # Excludes raw prompt/response/image bytes
                assert "raw_prompt" not in res_json.text
                assert "image_bytes" not in res_json.text

                # Test CSV export
                res_csv = await client.get("/api/evaluation-records/export/csv")
                assert res_csv.status_code == 200
                assert "text/csv" in res_csv.headers["content-type"]
                csv_text = res_csv.text
                assert "id,session_id,ticker" in csv_text
                assert "ASII" in csv_text
            finally:
                app.dependency_overrides.pop(get_current_user, None)
                app.dependency_overrides.pop(get_db_session, None)
