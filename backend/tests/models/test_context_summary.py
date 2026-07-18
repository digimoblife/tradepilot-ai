# ruff: noqa: E501
import json
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


async def _make_session(
    engine: AsyncEngine,
    label: str,
    do_cleanup: bool = True,
) -> uuid.UUID:
    if do_cleanup:
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
    return sr[0]


@pytest.mark.database
async def test_valid_summary_can_be_inserted(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "vsc")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO context_summaries (session_id, context_version) "
                "VALUES (:sid, :cv) RETURNING id"
            ),
            {"sid": sid, "cv": 1},
        )
        row = result.first()
        assert row is not None
        assert isinstance(row[0], uuid.UUID)
    await engine.dispose()


@pytest.mark.database
async def test_session_fk(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO context_summaries (session_id, context_version) "
                    "VALUES (:sid, :cv)"
                ),
                {"sid": uuid.uuid4(), "cv": 1},
            )
    await engine.dispose()


@pytest.mark.database
async def test_version_minimum(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "vmn")
    async with engine.begin() as conn:
        with pytest.raises(Exception) as excinfo:
            await conn.execute(
                text(
                    "INSERT INTO context_summaries (session_id, context_version) "
                    "VALUES (:sid, :cv)"
                ),
                {"sid": sid, "cv": 0},
            )
        assert "violates check constraint" in str(excinfo.value)
    await engine.dispose()


@pytest.mark.database
async def test_duplicate_version_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "dvr")
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO context_summaries (session_id, context_version) VALUES (:sid, :cv)"),
            {"sid": sid, "cv": 1},
        )
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO context_summaries (session_id, context_version) "
                    "VALUES (:sid, :cv)"
                ),
                {"sid": sid, "cv": 1},
            )
    await engine.dispose()


@pytest.mark.database
async def test_same_version_different_session_succeeds(db_url: str) -> None:
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
                {"e": f"sv1_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
            )
        ).first()
        sr1 = (
            await conn.execute(
                text(
                    "INSERT INTO trade_sessions (owner_id, ticker) VALUES (:uid, :t) RETURNING id"
                ),
                {"uid": ur1[0], "t": "BBRI"},
            )
        ).first()
        ur2 = (
            await conn.execute(
                text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
                {"e": f"sv2_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
            )
        ).first()
        sr2 = (
            await conn.execute(
                text(
                    "INSERT INTO trade_sessions (owner_id, ticker) VALUES (:uid, :t) RETURNING id"
                ),
                {"uid": ur2[0], "t": "BBRI"},
            )
        ).first()
        await conn.execute(
            text("INSERT INTO context_summaries (session_id, context_version) VALUES (:sid, :cv)"),
            {"sid": sr1[0], "cv": 1},
        )
        await conn.execute(
            text("INSERT INTO context_summaries (session_id, context_version) VALUES (:sid, :cv)"),
            {"sid": sr2[0], "cv": 1},
        )
    await engine.dispose()


@pytest.mark.database
async def test_multiple_versions_retained(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "mvr")
    async with engine.begin() as conn:
        for v in range(1, 5):
            await conn.execute(
                text(
                    "INSERT INTO context_summaries (session_id, context_version) "
                    "VALUES (:sid, :cv)"
                ),
                {"sid": sid, "cv": v},
            )
        rows = (
            await conn.execute(
                text(
                    "SELECT context_version FROM context_summaries "
                    "WHERE session_id = :sid ORDER BY context_version"
                ),
                {"sid": sid},
            )
        ).all()
        assert len(rows) == 4
        assert [r[0] for r in rows] == [1, 2, 3, 4]
    await engine.dispose()


@pytest.mark.database
async def test_payload_jsonb_round_trip(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "pjr")
    payload = {"summary": "test", "values": [1, 2, 3]}
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO context_summaries (session_id, context_version, payload) "
                "VALUES (:sid, :cv, CAST(:pl AS JSONB))"
            ),
            {"sid": sid, "cv": 1, "pl": json.dumps(payload)},
        )
        row = (
            await conn.execute(
                text("SELECT payload FROM context_summaries WHERE session_id = :sid"),
                {"sid": sid},
            )
        ).first()
        assert row is not None
        assert row[0] == payload
    await engine.dispose()


@pytest.mark.database
async def test_default_quality(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "dfl")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO context_summaries (session_id, context_version) "
                "VALUES (:sid, :cv) RETURNING quality, is_stale"
            ),
            {"sid": sid, "cv": 1},
        )
        row = result.first()
        assert row is not None
        assert row[0] == "HIGH"
        assert row[1] is False
    await engine.dispose()


@pytest.mark.database
async def test_invalid_quality_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "iqr")
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO context_summaries (session_id, context_version, quality) "
                    "VALUES (:sid, :cv, :ql)"
                ),
                {"sid": sid, "cv": 1, "ql": "INVALID"},
            )
    await engine.dispose()


@pytest.mark.database
async def test_source_cutoff_round_trip(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "scr")
    cutoff = datetime(2026, 7, 18, 12, 0, 0, tzinfo=timezone.utc)
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO context_summaries (session_id, context_version, source_cutoff) "
                "VALUES (:sid, :cv, :sc) RETURNING source_cutoff"
            ),
            {"sid": sid, "cv": 1, "sc": cutoff},
        )
        row = result.first()
        assert row is not None
        assert row[0] == cutoff
    await engine.dispose()


@pytest.mark.database
async def test_created_timestamp_timezone_aware(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "ctt")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO context_summaries (session_id, context_version) "
                "VALUES (:sid, :cv) RETURNING created_at"
            ),
            {"sid": sid, "cv": 1},
        )
        row = result.first()
        assert row is not None
        assert row[0].tzinfo is not None
    await engine.dispose()


@pytest.mark.database
async def test_latest_summary_selection(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "lss")
    async with engine.begin() as conn:
        for v in range(1, 6):
            await conn.execute(
                text(
                    "INSERT INTO context_summaries (session_id, context_version) "
                    "VALUES (:sid, :cv)"
                ),
                {"sid": sid, "cv": v},
            )
        rows = (
            await conn.execute(
                text(
                    "SELECT context_version FROM context_summaries "
                    "WHERE session_id = :sid "
                    "ORDER BY context_version DESC LIMIT 1"
                ),
                {"sid": sid},
            )
        ).all()
        assert len(rows) == 1
        assert rows[0][0] == 5
    await engine.dispose()
