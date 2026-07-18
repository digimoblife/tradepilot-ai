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

_DEFAULT_URL = (
    "postgresql+asyncpg://tradepilot:change_me@localhost:5432/tradepilot_test"
)


@pytest.fixture
def db_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", _DEFAULT_URL)


async def _make_job(
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
                text(
                    "INSERT INTO users (email, password_hash) "
                    "VALUES (:e, :p) RETURNING id"
                ),
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
        jr = (
            await conn.execute(
                text(
                    "INSERT INTO analysis_jobs (session_id, analysis_type) "
                    "VALUES (:sid, :at) RETURNING id"
                ),
                {"sid": sr[0], "at": "INITIAL_ANALYSIS"},
            )
        ).first()
        assert jr is not None
    return sr[0], jr[0]


@pytest.mark.database
async def test_valid_request_persists(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, jid = await _make_job(engine, "vrp")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO provider_requests (analysis_job_id, provider, "
                "prompt_name, prompt_version, schema_name, schema_version) "
                "VALUES (:jid, :pr, :pn, :pv, :sn, :sv) RETURNING id"
            ),
            {
                "jid": jid,
                "pr": "GEMINI",
                "pn": "initial_analysis_v1",
                "pv": "1.0.0",
                "sn": "initial_analysis",
                "sv": "1.0.0",
            },
        )
        row = result.first()
        assert row is not None
        assert isinstance(row[0], uuid.UUID)
    await engine.dispose()


@pytest.mark.database
async def test_job_fk_works(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, jid = await _make_job(engine, "jfw")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "SELECT id FROM provider_requests WHERE analysis_job_id = :jid"
            ),
            {"jid": jid},
        )
        assert result.first() is None
    await engine.dispose()


@pytest.mark.database
async def test_invalid_job_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO provider_requests (analysis_job_id, provider, "
                    "prompt_name, prompt_version, schema_name, schema_version) "
                    "VALUES (:jid, :pr, :pn, :pv, :sn, :sv)"
                ),
                {
                    "jid": uuid.uuid4(),
                    "pr": "GEMINI",
                    "pn": "v1",
                    "pv": "1.0",
                    "sn": "schema",
                    "sv": "1.0",
                },
            )
    await engine.dispose()


@pytest.mark.database
async def test_provider_controlled(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, jid = await _make_job(engine, "pco")
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO provider_requests (analysis_job_id, provider, "
                    "prompt_name, prompt_version, schema_name, schema_version) "
                    "VALUES (:jid, :pr, :pn, :pv, :sn, :sv)"
                ),
                {
                    "jid": jid,
                    "pr": "INVALID",
                    "pn": "v1",
                    "pv": "1.0",
                    "sn": "schema",
                    "sv": "1.0",
                },
            )
    await engine.dispose()


@pytest.mark.database
async def test_schema_name_version_mandatory(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, jid = await _make_job(engine, "snv")
    async with engine.begin() as conn:
        with pytest.raises(Exception) as excinfo:
            await conn.execute(
                text(
                    "INSERT INTO provider_requests (analysis_job_id, provider, "
                    "prompt_name, prompt_version, schema_name, schema_version) "
                    "VALUES (:jid, :pr, :pn, :pv, :sn, :sv)"
                ),
                {
                    "jid": jid,
                    "pr": "GEMINI",
                    "pn": "v1",
                    "pv": "1.0",
                    "sn": "",
                    "sv": "1.0",
                },
            )
        assert "violates check constraint" in str(excinfo.value)
    await engine.dispose()


@pytest.mark.database
async def test_attempt_number_constraint(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, jid = await _make_job(engine, "anc")
    async with engine.begin() as conn:
        with pytest.raises(Exception) as excinfo:
            await conn.execute(
                text(
                    "INSERT INTO provider_requests (analysis_job_id, provider, "
                    "prompt_name, prompt_version, schema_name, schema_version, attempt_number) "
                    "VALUES (:jid, :pr, :pn, :pv, :sn, :sv, :an)"
                ),
                {
                    "jid": jid,
                    "pr": "GEMINI",
                    "pn": "v1",
                    "pv": "1.0",
                    "sn": "schema",
                    "sv": "1.0",
                    "an": 0,
                },
            )
        assert "violates check constraint" in str(excinfo.value)
    await engine.dispose()


@pytest.mark.database
async def test_jsonb_request_payload_round_trip(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, jid = await _make_job(engine, "jrp")
    payload = {"prompt": "Analyze this chart", "images": ["img1.png"]}
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO provider_requests (analysis_job_id, provider, "
                "prompt_name, prompt_version, schema_name, schema_version, request_payload) "
                "VALUES (:jid, :pr, :pn, :pv, :sn, :sv, CAST(:rp AS JSONB))"
            ),
            {
                "jid": jid,
                "pr": "GEMINI",
                "pn": "v1",
                "pv": "1.0",
                "sn": "schema",
                "sv": "1.0",
                "rp": json.dumps(payload),
            },
        )
        row = (
            await conn.execute(
                text(
                    "SELECT request_payload FROM provider_requests WHERE analysis_job_id = :jid"
                ),
                {"jid": jid},
            )
        ).first()
        assert row is not None
        assert row[0] == payload
    await engine.dispose()


@pytest.mark.database
async def test_multiple_attempts_per_job(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, jid = await _make_job(engine, "map")
    async with engine.begin() as conn:
        for i in range(1, 4):
            await conn.execute(
                text(
                    "INSERT INTO provider_requests (analysis_job_id, provider, "
                    "prompt_name, prompt_version, schema_name, schema_version, attempt_number) "
                    "VALUES (:jid, :pr, :pn, :pv, :sn, :sv, :an)"
                ),
                {
                    "jid": jid,
                    "pr": "GEMINI",
                    "pn": f"v{i}",
                    "pv": "1.0",
                    "sn": "schema",
                    "sv": "1.0",
                    "an": i,
                },
            )
        rows = (
            await conn.execute(
                text(
                    "SELECT attempt_number FROM provider_requests WHERE analysis_job_id = :jid ORDER BY attempt_number"
                ),
                {"jid": jid},
            )
        ).all()
        assert len(rows) == 3
        assert [r[0] for r in rows] == [1, 2, 3]
    await engine.dispose()


@pytest.mark.database
async def test_chronological_ordering(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, jid = await _make_job(engine, "chr")
    async with engine.begin() as conn:
        r1 = await conn.execute(
            text(
                "INSERT INTO provider_requests (analysis_job_id, provider, "
                "prompt_name, prompt_version, schema_name, schema_version, requested_at) "
                "VALUES (:jid, :pr, :pn, :pv, :sn, :sv, :ra) RETURNING id"
            ),
            {
                "jid": jid,
                "pr": "GEMINI",
                "pn": "v1",
                "pv": "1.0",
                "sn": "schema",
                "sv": "1.0",
                "ra": datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc),
            },
        )
        r2 = await conn.execute(
            text(
                "INSERT INTO provider_requests (analysis_job_id, provider, "
                "prompt_name, prompt_version, schema_name, schema_version, requested_at) "
                "VALUES (:jid, :pr, :pn, :pv, :sn, :sv, :ra) RETURNING id"
            ),
            {
                "jid": jid,
                "pr": "GEMINI",
                "pn": "v2",
                "pv": "1.0",
                "sn": "schema",
                "sv": "1.0",
                "ra": datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
            },
        )
        id1 = r1.first()[0]
        id2 = r2.first()[0]
        rows = (
            await conn.execute(
                text(
                    "SELECT id FROM provider_requests WHERE analysis_job_id = :jid ORDER BY requested_at, id"
                ),
                {"jid": jid},
            )
        ).all()
        assert rows[0][0] == id1
        assert rows[1][0] == id2
    await engine.dispose()
