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


async def _make_session_with_job(
    engine: AsyncEngine,
    label: str,
) -> tuple[uuid.UUID, uuid.UUID]:
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM trade_actions"))
        await conn.execute(text("DELETE FROM analyses"))
        await conn.execute(text("DELETE FROM session_events"))
        await conn.execute(text("DELETE FROM context_summaries"))
        await conn.execute(text("DELETE FROM validation_attempts"))
        await conn.execute(text("DELETE FROM provider_responses"))
        await conn.execute(text("DELETE FROM provider_requests"))
        await conn.execute(text("DELETE FROM analysis_jobs"))
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
    return sr[0], jr[0]


@pytest.mark.database
async def test_rejected_analysis_candidate(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid, jid = await _make_session_with_job(engine, "rac")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO analyses (session_id, analysis_job_id, analysis_type, "
                "acceptance_status, prompt_name, prompt_version, schema_name, schema_version) "
                "VALUES (:sid, :jid, :at, :ast, :pn, :pv, :sn, :sv) RETURNING id"
            ),
            {
                "sid": sid,
                "jid": jid,
                "at": "INITIAL_ANALYSIS",
                "ast": "REJECTED",
                "pn": "v1",
                "pv": "1.0",
                "sn": "initial_analysis",
                "sv": "1.0",
            },
        )
        row = result.first()
        assert row is not None
    await engine.dispose()


@pytest.mark.database
async def test_accepted_analysis_persists(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid, jid = await _make_session_with_job(engine, "aap")
    payload = {"summary": "Bullish setup", "target": 3250}
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO analyses (session_id, analysis_job_id, analysis_type, "
                "acceptance_status, prompt_name, prompt_version, schema_name, schema_version, "
                "payload, accepted_at) "
                "VALUES (:sid, :jid, :at, :ast, :pn, :pv, :sn, :sv, CAST(:pl AS JSONB), :aa) RETURNING id"
            ),
            {
                "sid": sid,
                "jid": jid,
                "at": "INITIAL_ANALYSIS",
                "ast": "ACCEPTED",
                "pn": "v1",
                "pv": "1.0",
                "sn": "initial_analysis",
                "sv": "1.0",
                "pl": json.dumps(payload),
                "aa": datetime(2026, 7, 18, 12, 0, 0, tzinfo=timezone.utc),
            },
        )
        row = result.first()
        assert row is not None
    await engine.dispose()


@pytest.mark.database
async def test_accepted_payload_distinct_from_raw(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid, jid = await _make_session_with_job(engine, "apd")
    accepted_payload = {"summary": "Validated analysis", "price": 3090}
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO analyses (session_id, analysis_job_id, analysis_type, "
                "acceptance_status, prompt_name, prompt_version, schema_name, schema_version, "
                "payload) "
                "VALUES (:sid, :jid, :at, :ast, :pn, :pv, :sn, :sv, CAST(:pl AS JSONB))"
            ),
            {
                "sid": sid,
                "jid": jid,
                "at": "WATCHING_UPDATE",
                "ast": "ACCEPTED",
                "pn": "v1",
                "pv": "1.0",
                "sn": "watching_update",
                "sv": "1.0",
                "pl": json.dumps(accepted_payload),
            },
        )
        row = (
            await conn.execute(
                text(
                    "SELECT payload FROM analyses WHERE analysis_job_id = :jid"
                ),
                {"jid": jid},
            )
        ).first()
        assert row is not None
        # Verify the accepted payload is the structured object, not raw text
        assert isinstance(row[0], dict)
        assert row[0]["summary"] == "Validated analysis"
    await engine.dispose()


@pytest.mark.database
async def test_schema_name_version_mandatory(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid, jid = await _make_session_with_job(engine, "snv_a")
    async with engine.begin() as conn:
        with pytest.raises(Exception) as excinfo:
            await conn.execute(
                text(
                    "INSERT INTO analyses (session_id, analysis_job_id, analysis_type, "
                    "acceptance_status, prompt_name, prompt_version, schema_name, schema_version) "
                    "VALUES (:sid, :jid, :at, :ast, :pn, :pv, :sn, :sv)"
                ),
                {
                    "sid": sid,
                    "jid": jid,
                    "at": "INITIAL_ANALYSIS",
                    "ast": "ACCEPTED",
                    "pn": "v1",
                    "pv": "1.0",
                    "sn": "",
                    "sv": "1.0",
                },
            )
        assert "violates check constraint" in str(excinfo.value)
    await engine.dispose()


@pytest.mark.database
async def test_prompt_version_mandatory(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid, jid = await _make_session_with_job(engine, "pvm")
    async with engine.begin() as conn:
        with pytest.raises(Exception) as excinfo:
            await conn.execute(
                text(
                    "INSERT INTO analyses (session_id, analysis_job_id, analysis_type, "
                    "acceptance_status, prompt_name, prompt_version, schema_name, schema_version) "
                    "VALUES (:sid, :jid, :at, :ast, :pn, :pv, :sn, :sv)"
                ),
                {
                    "sid": sid,
                    "jid": jid,
                    "at": "INITIAL_ANALYSIS",
                    "ast": "ACCEPTED",
                    "pn": "v1",
                    "pv": "",
                    "sn": "schema",
                    "sv": "1.0",
                },
            )
        assert "violates check constraint" in str(excinfo.value)
    await engine.dispose()


@pytest.mark.database
async def test_session_and_job_fks(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid, jid = await _make_session_with_job(engine, "sjf")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO analyses (session_id, analysis_job_id, analysis_type, "
                "acceptance_status, prompt_name, prompt_version, schema_name, schema_version) "
                "VALUES (:sid, :jid, :at, :ast, :pn, :pv, :sn, :sv) RETURNING id"
            ),
            {
                "sid": sid,
                "jid": jid,
                "at": "INITIAL_ANALYSIS",
                "ast": "PENDING",
                "pn": "v1",
                "pv": "1.0",
                "sn": "schema",
                "sv": "1.0",
            },
        )
        row = result.first()
        assert row is not None
    await engine.dispose()


@pytest.mark.database
async def test_invalid_references_fail(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO analyses (session_id, analysis_job_id, analysis_type, "
                    "acceptance_status, prompt_name, prompt_version, schema_name, schema_version) "
                    "VALUES (:sid, :jid, :at, :ast, :pn, :pv, :sn, :sv)"
                ),
                {
                    "sid": uuid.uuid4(),
                    "jid": uuid.uuid4(),
                    "at": "INITIAL_ANALYSIS",
                    "ast": "PENDING",
                    "pn": "v1",
                    "pv": "1.0",
                    "sn": "schema",
                    "sv": "1.0",
                },
            )
    await engine.dispose()


@pytest.mark.database
async def test_accepted_timestamp_timezone_aware(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid, jid = await _make_session_with_job(engine, "att")
    now = datetime(2026, 7, 18, 12, 0, 0, tzinfo=timezone.utc)
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO analyses (session_id, analysis_job_id, analysis_type, "
                "acceptance_status, prompt_name, prompt_version, schema_name, schema_version, "
                "accepted_at) "
                "VALUES (:sid, :jid, :at, :ast, :pn, :pv, :sn, :sv, :aa) RETURNING id"
            ),
            {
                "sid": sid,
                "jid": jid,
                "at": "OPEN_POSITION_UPDATE",
                "ast": "ACCEPTED",
                "pn": "v1",
                "pv": "1.0",
                "sn": "schema",
                "sv": "1.0",
                "aa": now,
            },
        )
        row = result.first()
        assert row is not None
    await engine.dispose()


@pytest.mark.database
async def test_superseding_analysis_relationship(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid, jid1 = await _make_session_with_job(engine, "sar")
    async with engine.begin() as conn:
        # Create a second job for superseding
        jr2 = (
            await conn.execute(
                text(
                    "INSERT INTO analysis_jobs (session_id, analysis_type) "
                    "VALUES (:sid, :at) RETURNING id"
                ),
                {"sid": sid, "at": "WATCHING_UPDATE"},
            )
        ).first()
        jid2 = jr2[0]
        # Create first analysis
        r1 = await conn.execute(
            text(
                "INSERT INTO analyses (session_id, analysis_job_id, analysis_type, "
                "acceptance_status, prompt_name, prompt_version, schema_name, schema_version) "
                "VALUES (:sid, :jid, :at, :ast, :pn, :pv, :sn, :sv) RETURNING id"
            ),
            {
                "sid": sid,
                "jid": jid1,
                "at": "INITIAL_ANALYSIS",
                "ast": "ACCEPTED",
                "pn": "v1",
                "pv": "1.0",
                "sn": "schema",
                "sv": "1.0",
            },
        )
        aid1 = r1.first()[0]
        # Create superseding analysis
        r2 = await conn.execute(
            text(
                "INSERT INTO analyses (session_id, analysis_job_id, analysis_type, "
                "acceptance_status, prompt_name, prompt_version, schema_name, schema_version, "
                "supersedes_analysis_id) "
                "VALUES (:sid, :jid, :at, :ast, :pn, :pv, :sn, :sv, :sid2) RETURNING id"
            ),
            {
                "sid": sid,
                "jid": jid2,
                "at": "WATCHING_UPDATE",
                "ast": "ACCEPTED",
                "pn": "v2",
                "pv": "1.0",
                "sn": "schema",
                "sv": "1.0",
                "sid2": aid1,
            },
        )
        aid2 = r2.first()[0]
        # Verify superseding relationship
        row = (
            await conn.execute(
                text(
                    "SELECT supersedes_analysis_id FROM analyses WHERE id = :aid"
                ),
                {"aid": aid2},
            )
        ).first()
        assert row is not None
        assert row[0] == aid1
        # Verify prior analysis still exists
        row = (
            await conn.execute(
                text("SELECT id FROM analyses WHERE id = :aid"),
                {"aid": aid1},
            )
        ).first()
        assert row is not None
    await engine.dispose()


@pytest.mark.database
async def test_invalid_superseding_id_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid, jid = await _make_session_with_job(engine, "isr")
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO analyses (session_id, analysis_job_id, analysis_type, "
                    "acceptance_status, prompt_name, prompt_version, schema_name, schema_version, "
                    "supersedes_analysis_id) "
                    "VALUES (:sid, :jid, :at, :ast, :pn, :pv, :sn, :sv, :sid2)"
                ),
                {
                    "sid": sid,
                    "jid": jid,
                    "at": "INITIAL_ANALYSIS",
                    "ast": "ACCEPTED",
                    "pn": "v1",
                    "pv": "1.0",
                    "sn": "schema",
                    "sv": "1.0",
                    "sid2": uuid.uuid4(),
                },
            )
    await engine.dispose()


@pytest.mark.database
async def test_self_superseding_fails(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid, jid = await _make_session_with_job(engine, "ssf")
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO analyses (session_id, analysis_job_id, analysis_type, "
                    "acceptance_status, prompt_name, prompt_version, schema_name, schema_version, "
                    "supersedes_analysis_id) "
                    "VALUES (:sid, :jid, :at, :ast, :pn, :pv, :sn, :sv, :sid2)"
                ),
                {
                    "sid": sid,
                    "jid": jid,
                    "at": "INITIAL_ANALYSIS",
                    "ast": "ACCEPTED",
                    "pn": "v1",
                    "pv": "1.0",
                    "sn": "schema",
                    "sv": "1.0",
                    "sid2": uuid.uuid4(),
                },
            )
    await engine.dispose()


@pytest.mark.database
async def test_accepted_history_query_deterministic(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid, jid = await _make_session_with_job(engine, "ahq")
    async with engine.begin() as conn:
        # Create multiple analyses at different times
        for i, (at, ast) in enumerate(
            [
                ("INITIAL_ANALYSIS", "REJECTED"),
                ("INITIAL_ANALYSIS", "ACCEPTED"),
                ("WATCHING_UPDATE", "ACCEPTED"),
                ("WATCHING_UPDATE", "SUPERSEDED"),
                ("WATCHING_UPDATE", "ACCEPTED"),
            ]
        ):
            jr = (
                await conn.execute(
                    text(
                        "INSERT INTO analysis_jobs (session_id, analysis_type) "
                        "VALUES (:sid, :at) RETURNING id"
                    ),
                    {"sid": sid, "at": at},
                )
            ).first()
            await conn.execute(
                text(
                    "INSERT INTO analyses (session_id, analysis_job_id, analysis_type, "
                    "acceptance_status, prompt_name, prompt_version, schema_name, schema_version) "
                    "VALUES (:sid, :jid, :at, :ast, :pn, :pv, :sn, :sv)"
                ),
                {
                    "sid": sid,
                    "jid": jr[0],
                    "at": at,
                    "ast": ast,
                    "pn": f"v{i}",
                    "pv": "1.0",
                    "sn": "schema",
                    "sv": "1.0",
                },
            )
        # Query accepted analyses ordered by created_at
        rows = (
            await conn.execute(
                text(
                    "SELECT acceptance_status, analysis_type FROM analyses "
                    "WHERE session_id = :sid "
                    "ORDER BY created_at, id"
                ),
                {"sid": sid},
            )
        ).all()
        assert len(rows) == 5
        accepted = [r for r in rows if r[0] == "ACCEPTED"]
        assert len(accepted) == 3
    await engine.dispose()


@pytest.mark.database
async def test_trade_action_analysis_fk(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid, jid = await _make_session_with_job(engine, "taf")
    async with engine.begin() as conn:
        # Create analysis
        ar = await conn.execute(
            text(
                "INSERT INTO analyses (session_id, analysis_job_id, analysis_type, "
                "acceptance_status, prompt_name, prompt_version, schema_name, schema_version) "
                "VALUES (:sid, :jid, :at, :ast, :pn, :pv, :sn, :sv) RETURNING id"
            ),
            {
                "sid": sid,
                "jid": jid,
                "at": "INITIAL_ANALYSIS",
                "ast": "ACCEPTED",
                "pn": "v1",
                "pv": "1.0",
                "sn": "schema",
                "sv": "1.0",
            },
        )
        aid = ar.first()[0]
        # Create trade action referencing analysis
        await conn.execute(
            text(
                "INSERT INTO trade_actions (session_id, action_type, confirmed_at, "
                "idempotency_key, related_analysis_id) "
                "VALUES (:sid, :at, :ca, :ik, :raid)"
            ),
            {
                "sid": sid,
                "at": "POSITION_OPENED",
                "ca": datetime(2026, 7, 18, 12, 0, 0, tzinfo=timezone.utc),
                "ik": "taf-001",
                "raid": aid,
            },
        )
    await engine.dispose()


@pytest.mark.database
async def test_nonexistent_analysis_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid, _ = await _make_session_with_job(engine, "nar")
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO trade_actions (session_id, action_type, confirmed_at, "
                    "idempotency_key, related_analysis_id) "
                    "VALUES (:sid, :at, :ca, :ik, :raid)"
                ),
                {
                    "sid": sid,
                    "at": "POSITION_OPENED",
                    "ca": datetime(2026, 7, 18, 12, 0, 0, tzinfo=timezone.utc),
                    "ik": "nar-001",
                    "raid": uuid.uuid4(),
                },
            )
    await engine.dispose()
