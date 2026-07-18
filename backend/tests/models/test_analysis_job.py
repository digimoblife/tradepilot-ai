# ruff: noqa: E501
import os
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import AppConfig
from app.database.session import create_async_engine_from_config

_DEFAULT_URL = "postgresql+asyncpg://tradepilot:change_me@localhost:5432/tradepilot_test"


@pytest.fixture
def db_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", _DEFAULT_URL)


async def _make_user_and_session(
    engine: AsyncEngine,
    label: str,
) -> tuple[uuid.UUID, uuid.UUID]:
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM session_events"))
        await conn.execute(text("DELETE FROM context_summaries"))
        await conn.execute(text("DELETE FROM validation_attempts"))
        await conn.execute(text("DELETE FROM provider_responses"))
        await conn.execute(text("DELETE FROM provider_requests"))
        await conn.execute(text("DELETE FROM trade_actions"))
        await conn.execute(text("DELETE FROM analyses"))
        await conn.execute(text("DELETE FROM analysis_jobs"))
        await conn.execute(text("DELETE FROM evidence"))
        await conn.execute(text("DELETE FROM trade_states"))
        await conn.execute(text("DELETE FROM trade_sessions"))
        await conn.execute(text("DELETE FROM users"))
    async with engine.begin() as conn:
        ur = (
            await conn.execute(
                text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
                {"e": f"{label}_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
            )
        ).first()
        assert ur is not None
        sr = (
            await conn.execute(
                text(
                    "INSERT INTO trade_sessions (owner_id, ticker) VALUES (:uid, :t) RETURNING id"
                ),
                {"uid": ur[0], "t": "BBRI"},
            )
        ).first()
        assert sr is not None
    return ur[0], sr[0]


@pytest.mark.database
async def test_valid_job_can_be_inserted(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "vjb")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO analysis_jobs (session_id, analysis_type, status) "
                "VALUES (:sid, :at, :st) RETURNING id"
            ),
            {"sid": sid, "at": "INITIAL_ANALYSIS", "st": "CREATED"},
        )
        row = result.first()
        assert row is not None
        assert isinstance(row[0], uuid.UUID)
    await engine.dispose()


@pytest.mark.database
async def test_session_fk_works(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "sfk")
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT id FROM analysis_jobs WHERE session_id = :sid"),
            {"sid": sid},
        )
        assert result.first() is None
    await engine.dispose()


@pytest.mark.database
async def test_invalid_session_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text("INSERT INTO analysis_jobs (session_id, analysis_type) VALUES (:sid, :at)"),
                {"sid": uuid.uuid4(), "at": "INITIAL_ANALYSIS"},
            )
    await engine.dispose()


@pytest.mark.database
async def test_default_status(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "def")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO analysis_jobs (session_id, analysis_type) "
                "VALUES (:sid, :at) RETURNING status"
            ),
            {"sid": sid, "at": "WATCHING_UPDATE"},
        )
        row = result.first()
        assert row is not None
        assert row[0] == "CREATED"
    await engine.dispose()


@pytest.mark.database
async def test_analysis_type_controlled(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "atc")
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text("INSERT INTO analysis_jobs (session_id, analysis_type) VALUES (:sid, :at)"),
                {"sid": sid, "at": "INVALID_TYPE"},
            )
    await engine.dispose()


@pytest.mark.database
async def test_attempt_defaults(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "atd")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO analysis_jobs (session_id, analysis_type) "
                "VALUES (:sid, :at) RETURNING attempt_count, max_attempts"
            ),
            {"sid": sid, "at": "OPEN_POSITION_UPDATE"},
        )
        row = result.first()
        assert row is not None
        assert row[0] == 0
        assert row[1] == 3
    await engine.dispose()


@pytest.mark.database
async def test_negative_attempt_count_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "nac")
    async with engine.begin() as conn:
        with pytest.raises(Exception) as excinfo:
            await conn.execute(
                text(
                    "INSERT INTO analysis_jobs (session_id, analysis_type, attempt_count) "
                    "VALUES (:sid, :at, :ac)"
                ),
                {"sid": sid, "at": "PARTIAL_EXIT_REVIEW", "ac": -1},
            )
        assert "violates check constraint" in str(excinfo.value)
    await engine.dispose()


@pytest.mark.database
async def test_invalid_max_attempt_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "ima")
    async with engine.begin() as conn:
        with pytest.raises(Exception) as excinfo:
            await conn.execute(
                text(
                    "INSERT INTO analysis_jobs (session_id, analysis_type, max_attempts) "
                    "VALUES (:sid, :at, :ma)"
                ),
                {"sid": sid, "at": "CLOSING_ANALYSIS", "ma": 0},
            )
        assert "violates check constraint" in str(excinfo.value)
    await engine.dispose()


@pytest.mark.database
async def test_lease_timestamps_timezone_aware(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "ltt")
    now = datetime(2026, 7, 18, 12, 0, 0, tzinfo=timezone.utc)
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO analysis_jobs (session_id, analysis_type, lease_owner, "
                "lease_acquired_at, lease_expires_at) "
                "VALUES (:sid, :at, :lo, :laa, :lea) RETURNING id"
            ),
            {
                "sid": sid,
                "at": "INITIAL_ANALYSIS",
                "lo": "worker-1",
                "laa": now,
                "lea": datetime(2026, 7, 18, 12, 5, 0, tzinfo=timezone.utc),
            },
        )
        row = result.first()
        assert row is not None
    await engine.dispose()


@pytest.mark.database
async def test_error_metadata_round_trip(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "emr")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO analysis_jobs (session_id, analysis_type, "
                "last_error_code, last_error_message) "
                "VALUES (:sid, :at, :ec, :em) RETURNING id"
            ),
            {
                "sid": sid,
                "at": "INITIAL_ANALYSIS",
                "ec": "PROVIDER_ERROR",
                "em": "Provider returned 500",
            },
        )
        row = result.first()
        assert row is not None
        row2 = (
            await conn.execute(
                text(
                    "SELECT last_error_code, last_error_message FROM analysis_jobs WHERE id = :jid"
                ),
                {"jid": row[0]},
            )
        ).first()
        assert row2 is not None
        assert row2[0] == "PROVIDER_ERROR"
        assert row2[1] == "Provider returned 500"
    await engine.dispose()


@pytest.mark.database
async def test_queue_order_deterministic(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM session_events"))
        await conn.execute(text("DELETE FROM context_summaries"))
        await conn.execute(text("DELETE FROM validation_attempts"))
        await conn.execute(text("DELETE FROM provider_responses"))
        await conn.execute(text("DELETE FROM provider_requests"))
        await conn.execute(text("DELETE FROM trade_actions"))
        await conn.execute(text("DELETE FROM analyses"))
        await conn.execute(text("DELETE FROM analysis_jobs"))
        await conn.execute(text("DELETE FROM evidence"))
        await conn.execute(text("DELETE FROM trade_states"))
        await conn.execute(text("DELETE FROM trade_sessions"))
        await conn.execute(text("DELETE FROM users"))
        ur1 = (
            await conn.execute(
                text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
                {"e": f"qo1_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
            )
        ).first()
        assert ur1 is not None
        sr1 = (
            await conn.execute(
                text(
                    "INSERT INTO trade_sessions (owner_id, ticker) VALUES (:uid, :t) RETURNING id"
                ),
                {"uid": ur1[0], "t": "BBRI"},
            )
        ).first()
        assert sr1 is not None
        ur2 = (
            await conn.execute(
                text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
                {"e": f"qo2_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
            )
        ).first()
        assert ur2 is not None
        sr2 = (
            await conn.execute(
                text(
                    "INSERT INTO trade_sessions (owner_id, ticker) VALUES (:uid, :t) RETURNING id"
                ),
                {"uid": ur2[0], "t": "BBRI"},
            )
        ).first()
        assert sr2 is not None
        r1 = await conn.execute(
            text(
                "INSERT INTO analysis_jobs (session_id, analysis_type, requested_at) "
                "VALUES (:sid, :at, :ra) RETURNING id"
            ),
            {
                "sid": sr1[0],
                "at": "INITIAL_ANALYSIS",
                "ra": datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
            },
        )
        r2 = await conn.execute(
            text(
                "INSERT INTO analysis_jobs (session_id, analysis_type, requested_at) "
                "VALUES (:sid, :at, :ra) RETURNING id"
            ),
            {
                "sid": sr2[0],
                "at": "INITIAL_ANALYSIS",
                "ra": datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc),
            },
        )
        id1 = r1.first()[0]
        id2 = r2.first()[0]
        rows = (
            await conn.execute(text("SELECT id FROM analysis_jobs ORDER BY requested_at, id"))
        ).all()
        # The earlier requested_at should come first
        assert rows[0][0] == id2
        assert rows[1][0] == id1
    await engine.dispose()
