# ruff: noqa: E501
import json
import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import AppConfig
from app.database.session import create_async_engine_from_config

_DEFAULT_URL = "postgresql+asyncpg://tradepilot:change_me@localhost:5432/tradepilot_test"


@pytest.fixture
def db_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", _DEFAULT_URL)


async def _make_request(
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
        sr = (
            await conn.execute(
                text(
                    "INSERT INTO trade_sessions (owner_id, ticker) VALUES (:uid, :t) RETURNING id"
                ),
                {"uid": ur[0], "t": "BBRI"},
            )
        ).first()
        jr = (
            await conn.execute(
                text(
                    "INSERT INTO analysis_jobs (session_id, analysis_type) "
                    "VALUES (:sid, :at) RETURNING id"
                ),
                {"sid": sr[0], "at": "INITIAL_ANALYSIS"},
            )
        ).first()
        req_r = (
            await conn.execute(
                text(
                    "INSERT INTO provider_requests (analysis_job_id, provider, "
                    "prompt_name, prompt_version, schema_name, schema_version) "
                    "VALUES (:jid, :pr, :pn, :pv, :sn, :sv) RETURNING id"
                ),
                {
                    "jid": jr[0],
                    "pr": "GEMINI",
                    "pn": "v1",
                    "pv": "1.0",
                    "sn": "schema",
                    "sv": "1.0",
                },
            )
        ).first()
    return jr[0], req_r[0]


@pytest.mark.database
async def test_successful_response_persists(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, req_id = await _make_request(engine, "srp")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO provider_responses (provider_request_id, status, raw_text) "
                "VALUES (:rid, :st, :rt) RETURNING id"
            ),
            {
                "rid": req_id,
                "st": "COMPLETED",
                "rt": '{"result": "ok"}',
            },
        )
        row = result.first()
        assert row is not None
    await engine.dispose()


@pytest.mark.database
async def test_failed_response_persists(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, req_id = await _make_request(engine, "frp")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO provider_responses (provider_request_id, status, error_code, error_message) "
                "VALUES (:rid, :st, :ec, :em) RETURNING id"
            ),
            {
                "rid": req_id,
                "st": "FAILED",
                "ec": "RATE_LIMIT",
                "em": "Rate limit exceeded",
            },
        )
        row = result.first()
        assert row is not None
    await engine.dispose()


@pytest.mark.database
async def test_raw_text_remains_auditable(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, req_id = await _make_request(engine, "rtr")
    raw = '{"analysis": "{\\"key\\": \\"value\\"}"}'
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO provider_responses (provider_request_id, status, raw_text) "
                "VALUES (:rid, :st, :rt)"
            ),
            {"rid": req_id, "st": "COMPLETED", "rt": raw},
        )
        row = (
            await conn.execute(
                text("SELECT raw_text FROM provider_responses WHERE provider_request_id = :rid"),
                {"rid": req_id},
            )
        ).first()
        assert row is not None
        assert row[0] == raw
    await engine.dispose()


@pytest.mark.database
async def test_transport_failure_representable(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, req_id = await _make_request(engine, "tfr")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO provider_responses (provider_request_id, status, "
                "error_code, error_message) "
                "VALUES (:rid, :st, :ec, :em) RETURNING id"
            ),
            {
                "rid": req_id,
                "st": "FAILED",
                "ec": "NETWORK_ERROR",
                "em": "Connection timeout",
            },
        )
        row = result.first()
        assert row is not None
    await engine.dispose()


@pytest.mark.database
async def test_request_fk_works(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, req_id = await _make_request(engine, "rfw")
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT id FROM provider_responses WHERE provider_request_id = :rid"),
            {"rid": req_id},
        )
        assert result.first() is None
    await engine.dispose()


@pytest.mark.database
async def test_invalid_request_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO provider_responses (provider_request_id, status) "
                    "VALUES (:rid, :st)"
                ),
                {"rid": uuid.uuid4(), "st": "COMPLETED"},
            )
    await engine.dispose()


@pytest.mark.database
async def test_latency_constraint(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, req_id = await _make_request(engine, "lat")
    async with engine.begin() as conn:
        with pytest.raises(Exception) as excinfo:
            await conn.execute(
                text(
                    "INSERT INTO provider_responses (provider_request_id, status, latency_ms) "
                    "VALUES (:rid, :st, :lm)"
                ),
                {"rid": req_id, "st": "COMPLETED", "lm": -1},
            )
        assert "violates check constraint" in str(excinfo.value)
    await engine.dispose()


@pytest.mark.database
async def test_token_count_constraints(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, req_id = await _make_request(engine, "tcc")
    async with engine.begin() as conn:
        with pytest.raises(Exception) as excinfo:
            await conn.execute(
                text(
                    "INSERT INTO provider_responses (provider_request_id, status, input_tokens) "
                    "VALUES (:rid, :st, :it)"
                ),
                {"rid": req_id, "st": "COMPLETED", "it": -5},
            )
        assert "violates check constraint" in str(excinfo.value)
    await engine.dispose()


@pytest.mark.database
async def test_jsonb_metadata_round_trip(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, req_id = await _make_request(engine, "jmr")
    meta = {"prompt_tokens": 100, "completion_tokens": 50}
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO provider_responses (provider_request_id, status, usage_metadata) "
                "VALUES (:rid, :st, CAST(:um AS JSONB))"
            ),
            {
                "rid": req_id,
                "st": "COMPLETED",
                "um": json.dumps(meta),
            },
        )
        row = (
            await conn.execute(
                text(
                    "SELECT usage_metadata FROM provider_responses WHERE provider_request_id = :rid"
                ),
                {"rid": req_id},
            )
        ).first()
        assert row is not None
        assert row[0] == meta
    await engine.dispose()


@pytest.mark.database
async def test_raw_response_is_not_analysis(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, req_id = await _make_request(engine, "rrn")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO provider_responses (provider_request_id, status, raw_text) "
                "VALUES (:rid, :st, :rt)"
            ),
            {"rid": req_id, "st": "COMPLETED", "rt": '{"result": "raw"}'},
        )
        row = (
            await conn.execute(
                text("SELECT raw_text FROM provider_responses WHERE provider_request_id = :rid"),
                {"rid": req_id},
            )
        ).first()
        assert row is not None
        # raw response is not an Analysis - verify it stays as raw text
        assert "result" in row[0]
    await engine.dispose()
