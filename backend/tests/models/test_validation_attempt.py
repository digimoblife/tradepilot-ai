# ruff: noqa: E501
import json
import os
import uuid

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


async def _make_job_and_response(
    engine: AsyncEngine,
    label: str,
) -> tuple[uuid.UUID, uuid.UUID]:
    async with engine.begin() as conn:
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
                    "pr": "DEEPSEEK",
                    "pn": "v1",
                    "pv": "1.0",
                    "sn": "schema",
                    "sv": "1.0",
                },
            )
        ).first()
        resp_r = (
            await conn.execute(
                text(
                    "INSERT INTO provider_responses (provider_request_id, status, raw_text) "
                    "VALUES (:rid, :st, :rt) RETURNING id"
                ),
                {
                    "rid": req_r[0],
                    "st": "COMPLETED",
                    "rt": '{"key": "value"}',
                },
            )
        ).first()
    return jr[0], resp_r[0]


@pytest.mark.database
async def test_failed_parsing_attempt_persists(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    jid, resp_id = await _make_job_and_response(engine, "fpa")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO validation_attempts (analysis_job_id, provider_response_id, "
                "attempt_number, stage, valid) "
                "VALUES (:jid, :rid, :an, :st, :vl) RETURNING id"
            ),
            {
                "jid": jid,
                "rid": resp_id,
                "an": 1,
                "st": "PARSE",
                "vl": False,
            },
        )
        row = result.first()
        assert row is not None
    await engine.dispose()


@pytest.mark.database
async def test_schema_validation_failure_persists(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    jid, resp_id = await _make_job_and_response(engine, "svf")
    issues = [{"code": "MISSING_FIELD", "path": "/price", "severity": "ERROR"}]
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO validation_attempts (analysis_job_id, provider_response_id, "
                "attempt_number, stage, valid, issues) "
                "VALUES (:jid, :rid, :an, :st, :vl, CAST(:is AS JSONB))"
            ),
            {
                "jid": jid,
                "rid": resp_id,
                "an": 1,
                "st": "JSON_SCHEMA",
                "vl": False,
                "is": json.dumps(issues),
            },
        )
        row = (
            await conn.execute(
                text(
                    "SELECT issues FROM validation_attempts WHERE analysis_job_id = :jid"
                ),
                {"jid": jid},
            )
        ).first()
        assert row is not None
        assert row[0] == issues
    await engine.dispose()


@pytest.mark.database
async def test_domain_validation_failure_persists(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    jid, resp_id = await _make_job_and_response(engine, "dvf")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO validation_attempts (analysis_job_id, provider_response_id, "
                "attempt_number, stage, valid) "
                "VALUES (:jid, :rid, :an, :st, :vl) RETURNING id"
            ),
            {
                "jid": jid,
                "rid": resp_id,
                "an": 1,
                "st": "DOMAIN",
                "vl": False,
            },
        )
        row = result.first()
        assert row is not None
    await engine.dispose()


@pytest.mark.database
async def test_successful_validation_persists(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    jid, resp_id = await _make_job_and_response(engine, "svp")
    payload = {"price": 3090, "quantity": 100}
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO validation_attempts (analysis_job_id, provider_response_id, "
                "attempt_number, stage, valid, parsed_payload) "
                "VALUES (:jid, :rid, :an, :st, :vl, CAST(:pp AS JSONB))"
            ),
            {
                "jid": jid,
                "rid": resp_id,
                "an": 1,
                "st": "JSON_SCHEMA",
                "vl": True,
                "pp": json.dumps(payload),
            },
        )
        row = (
            await conn.execute(
                text(
                    "SELECT parsed_payload, validated_payload FROM validation_attempts WHERE analysis_job_id = :jid"
                ),
                {"jid": jid},
            )
        ).first()
        assert row is not None
        assert row[0] == payload
        assert row[1] is None
    await engine.dispose()


@pytest.mark.database
async def test_parsed_and_validated_payloads_distinct(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    jid, resp_id = await _make_job_and_response(engine, "pvd")
    parsed = {"raw": "data"}
    validated = {"validated": "data"}
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO validation_attempts (analysis_job_id, provider_response_id, "
                "attempt_number, stage, valid, parsed_payload, validated_payload) "
                "VALUES (:jid, :rid, :an, :st, :vl, CAST(:pp AS JSONB), CAST(:vp AS JSONB))"
            ),
            {
                "jid": jid,
                "rid": resp_id,
                "an": 1,
                "st": "STATE_CONSISTENCY",
                "vl": True,
                "pp": json.dumps(parsed),
                "vp": json.dumps(validated),
            },
        )
        row = (
            await conn.execute(
                text(
                    "SELECT parsed_payload, validated_payload FROM validation_attempts WHERE analysis_job_id = :jid"
                ),
                {"jid": jid},
            )
        ).first()
        assert row is not None
        assert row[0] == parsed
        assert row[1] == validated
        assert row[0] != row[1]
    await engine.dispose()


@pytest.mark.database
async def test_invalid_payload_not_in_validated(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    jid, resp_id = await _make_job_and_response(engine, "ipn")
    payload = {"invalid": "data"}
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO validation_attempts (analysis_job_id, provider_response_id, "
                "attempt_number, stage, valid, parsed_payload) "
                "VALUES (:jid, :rid, :an, :st, :vl, CAST(:pp AS JSONB))"
            ),
            {
                "jid": jid,
                "rid": resp_id,
                "an": 1,
                "st": "JSON_SCHEMA",
                "vl": False,
                "pp": json.dumps(payload),
            },
        )
        row = (
            await conn.execute(
                text(
                    "SELECT parsed_payload, validated_payload, valid FROM validation_attempts WHERE analysis_job_id = :jid"
                ),
                {"jid": jid},
            )
        ).first()
        assert row is not None
        assert row[0] == payload
        assert row[1] is None
        assert row[2] is False
    await engine.dispose()


@pytest.mark.database
async def test_issues_jsonb_round_trip(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    jid, resp_id = await _make_job_and_response(engine, "ijr")
    issues = [
        {"code": "INVALID_TYPE", "path": "/stop_loss", "severity": "ERROR"},
        {"code": "MISSING_FIELD", "path": "/target", "severity": "WARNING"},
    ]
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO validation_attempts (analysis_job_id, provider_response_id, "
                "attempt_number, stage, valid, issues) "
                "VALUES (:jid, :rid, :an, :st, :vl, CAST(:is AS JSONB))"
            ),
            {
                "jid": jid,
                "rid": resp_id,
                "an": 1,
                "st": "DOMAIN",
                "vl": False,
                "is": json.dumps(issues),
            },
        )
        row = (
            await conn.execute(
                text(
                    "SELECT issues FROM validation_attempts WHERE analysis_job_id = :jid"
                ),
                {"jid": jid},
            )
        ).first()
        assert row is not None
        assert row[0] == issues
    await engine.dispose()


@pytest.mark.database
async def test_job_and_response_fks(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    jid, resp_id = await _make_job_and_response(engine, "jrf")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO validation_attempts (analysis_job_id, provider_response_id, "
                "attempt_number, stage, valid) "
                "VALUES (:jid, :rid, :an, :st, :vl) RETURNING id"
            ),
            {
                "jid": jid,
                "rid": resp_id,
                "an": 1,
                "st": "PARSE",
                "vl": True,
            },
        )
        row = result.first()
        assert row is not None
        # Verify FK works
        rows = (
            await conn.execute(
                text(
                    "SELECT va.id FROM validation_attempts va "
                    "JOIN provider_responses pr ON pr.id = va.provider_response_id "
                    "WHERE va.id = :vid"
                ),
                {"vid": row[0]},
            )
        ).all()
        assert len(rows) == 1
    await engine.dispose()


@pytest.mark.database
async def test_invalid_references_fail(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO validation_attempts (analysis_job_id, provider_response_id, "
                    "attempt_number, stage, valid) "
                    "VALUES (:jid, :rid, :an, :st, :vl)"
                ),
                {
                    "jid": uuid.uuid4(),
                    "rid": uuid.uuid4(),
                    "an": 1,
                    "st": "NARRATIVE",
                    "vl": False,
                },
            )
    await engine.dispose()


@pytest.mark.database
async def test_attempt_ordering(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    jid, resp_id = await _make_job_and_response(engine, "aor")
    async with engine.begin() as conn:
        for i in range(1, 4):
            await conn.execute(
                text(
                    "INSERT INTO validation_attempts (analysis_job_id, provider_response_id, "
                    "attempt_number, stage, valid) "
                    "VALUES (:jid, :rid, :an, :st, :vl)"
                ),
                {
                    "jid": jid,
                    "rid": resp_id,
                    "an": i,
                    "st": "PARSE",
                    "vl": i == 3,
                },
            )
        rows = (
            await conn.execute(
                text(
                    "SELECT attempt_number, valid FROM validation_attempts "
                    "WHERE analysis_job_id = :jid ORDER BY attempt_number"
                ),
                {"jid": jid},
            )
        ).all()
        assert len(rows) == 3
        assert rows[2].valid is True
    await engine.dispose()
