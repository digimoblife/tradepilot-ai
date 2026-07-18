# ruff: noqa: E501
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

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


async def _make_session(
    engine: AsyncEngine,
    label: str,
) -> uuid.UUID:
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
    return sr[0]


async def _make_action(
    engine: AsyncEngine,
    sid: uuid.UUID,
    label: str,
) -> uuid.UUID:
    async with engine.begin() as conn:
        ar = (
            await conn.execute(
                text(
                    "INSERT INTO trade_actions (session_id, action_type, confirmed_at, idempotency_key) "
                    "VALUES (:sid, :at, :ca, :ik) RETURNING id"
                ),
                {
                    "sid": sid,
                    "at": "POSITION_OPENED",
                    "ca": datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
                    "ik": f"se_{label}_{uuid.uuid4().hex[:8]}",
                },
            )
        ).first()
        assert ar is not None
    return ar[0]


async def _make_analysis(
    engine: AsyncEngine,
    sid: uuid.UUID,
) -> uuid.UUID:
    async with engine.begin() as conn:
        jr = (
            await conn.execute(
                text(
                    "INSERT INTO analysis_jobs (session_id, analysis_type) "
                    "VALUES (:sid, :at) RETURNING id"
                ),
                {"sid": sid, "at": "INITIAL_ANALYSIS"},
            )
        ).first()
        assert jr is not None
        ar = (
            await conn.execute(
                text(
                    "INSERT INTO analyses (session_id, analysis_job_id, analysis_type, "
                    "acceptance_status, prompt_name, prompt_version, schema_name, schema_version) "
                    "VALUES (:sid, :jid, :at, :ast, :pn, :pv, :sn, :sv) RETURNING id"
                ),
                {
                    "sid": sid,
                    "jid": jr[0],
                    "at": "INITIAL_ANALYSIS",
                    "ast": "ACCEPTED",
                    "pn": "v1",
                    "pv": "1.0",
                    "sn": "schema",
                    "sv": "1.0",
                },
            )
        ).first()
        assert ar is not None
    return ar[0]


@pytest.mark.database
async def test_valid_event_can_be_inserted(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "vei")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO session_events (session_id, event_type, occurred_at) "
                "VALUES (:sid, :et, :oa) RETURNING id"
            ),
            {
                "sid": sid,
                "et": "SESSION_CREATED",
                "oa": datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc),
            },
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
                    "INSERT INTO session_events (session_id, event_type, occurred_at) "
                    "VALUES (:sid, :et, :oa)"
                ),
                {
                    "sid": uuid.uuid4(),
                    "et": "SESSION_CREATED",
                    "oa": datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc),
                },
            )
    await engine.dispose()


@pytest.mark.database
async def test_invalid_event_type_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "iet")
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO session_events (session_id, event_type, occurred_at) "
                    "VALUES (:sid, :et, :oa)"
                ),
                {
                    "sid": sid,
                    "et": "INVALID_EVENT",
                    "oa": datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc),
                },
            )
    await engine.dispose()


@pytest.mark.database
async def test_timestamp_timezone_aware(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "tta")
    now = datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc)
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO session_events (session_id, event_type, occurred_at) "
                "VALUES (:sid, :et, :oa) RETURNING occurred_at, created_at"
            ),
            {
                "sid": sid,
                "et": "EVIDENCE_UPLOADED",
                "oa": now,
            },
        )
        row = result.first()
        assert row is not None
        assert row[0].tzinfo is not None
        assert row[1].tzinfo is not None
    await engine.dispose()


@pytest.mark.database
async def test_decimal_price_and_quantity(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "dpq")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO session_events (session_id, event_type, occurred_at, price, quantity) "
                "VALUES (:sid, :et, :oa, :pr, :qn) RETURNING price, quantity"
            ),
            {
                "sid": sid,
                "et": "POSITION_OPENED",
                "oa": datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
                "pr": Decimal("3090.50"),
                "qn": Decimal("10000"),
            },
        )
        row = result.first()
        assert row is not None
        assert isinstance(row[0], Decimal)
        assert row[0] == Decimal("3090.50")
        assert isinstance(row[1], Decimal)
        assert row[1] == Decimal("10000")
    await engine.dispose()


@pytest.mark.database
async def test_negative_quantity_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "nqr")
    async with engine.begin() as conn:
        with pytest.raises(Exception) as excinfo:
            await conn.execute(
                text(
                    "INSERT INTO session_events (session_id, event_type, occurred_at, quantity) "
                    "VALUES (:sid, :et, :oa, :qn)"
                ),
                {
                    "sid": sid,
                    "et": "PARTIAL_EXIT",
                    "oa": datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
                    "qn": Decimal("-100"),
                },
            )
        assert "violates check constraint" in str(excinfo.value)
    await engine.dispose()


@pytest.mark.database
async def test_compact_summary_round_trip(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "csr")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO session_events (session_id, event_type, occurred_at, compact_summary) "
                "VALUES (:sid, :et, :oa, :cs)"
            ),
            {
                "sid": sid,
                "et": "NOTE_ADDED",
                "oa": datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc),
                "cs": "User added a note about support level.",
            },
        )
        row = (
            await conn.execute(
                text(
                    "SELECT compact_summary FROM session_events WHERE session_id = :sid"
                ),
                {"sid": sid},
            )
        ).first()
        assert row is not None
        assert row[0] == "User added a note about support level."
    await engine.dispose()


@pytest.mark.database
async def test_related_action_fk(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "raf")
    aid = await _make_action(engine, sid, "raf")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO session_events (session_id, event_type, occurred_at, related_action_id) "
                "VALUES (:sid, :et, :oa, :raid) RETURNING id"
            ),
            {
                "sid": sid,
                "et": "POSITION_OPENED",
                "oa": datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
                "raid": aid,
            },
        )
        row = result.first()
        assert row is not None
    await engine.dispose()


@pytest.mark.database
async def test_invalid_action_id_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "iar")
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO session_events (session_id, event_type, occurred_at, related_action_id) "
                    "VALUES (:sid, :et, :oa, :raid)"
                ),
                {
                    "sid": sid,
                    "et": "POSITION_OPENED",
                    "oa": datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
                    "raid": uuid.uuid4(),
                },
            )
    await engine.dispose()


@pytest.mark.database
async def test_related_analysis_fk(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "rlf")
    anid = await _make_analysis(engine, sid)
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO session_events (session_id, event_type, occurred_at, related_analysis_id) "
                "VALUES (:sid, :et, :oa, :raid) RETURNING id"
            ),
            {
                "sid": sid,
                "et": "ANALYSIS_ACCEPTED",
                "oa": datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
                "raid": anid,
            },
        )
        row = result.first()
        assert row is not None
    await engine.dispose()


@pytest.mark.database
async def test_invalid_analysis_id_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "iir")
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO session_events (session_id, event_type, occurred_at, related_analysis_id) "
                    "VALUES (:sid, :et, :oa, :raid)"
                ),
                {
                    "sid": sid,
                    "et": "ANALYSIS_ACCEPTED",
                    "oa": datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
                    "raid": uuid.uuid4(),
                },
            )
    await engine.dispose()


@pytest.mark.database
async def test_event_without_action_or_analysis(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "ewo")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO session_events (session_id, event_type, occurred_at) "
                "VALUES (:sid, :et, :oa) RETURNING id"
            ),
            {
                "sid": sid,
                "et": "SESSION_CREATED",
                "oa": datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc),
            },
        )
        row = result.first()
        assert row is not None
    await engine.dispose()


@pytest.mark.database
async def test_chronological_query(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "chq")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO session_events (session_id, event_type, occurred_at) "
                "VALUES (:sid, :et, :oa)"
            ),
            {
                "sid": sid,
                "et": "SESSION_CREATED",
                "oa": datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc),
            },
        )
        await conn.execute(
            text(
                "INSERT INTO session_events (session_id, event_type, occurred_at) "
                "VALUES (:sid, :et, :oa)"
            ),
            {
                "sid": sid,
                "et": "EVIDENCE_UPLOADED",
                "oa": datetime(2026, 7, 18, 9, 30, 0, tzinfo=timezone.utc),
            },
        )
        await conn.execute(
            text(
                "INSERT INTO session_events (session_id, event_type, occurred_at) "
                "VALUES (:sid, :et, :oa)"
            ),
            {
                "sid": sid,
                "et": "ANALYSIS_REQUESTED",
                "oa": datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
            },
        )
        rows = (
            await conn.execute(
                text(
                    "SELECT event_type FROM session_events "
                    "WHERE session_id = :sid "
                    "ORDER BY occurred_at, id"
                ),
                {"sid": sid},
            )
        ).all()
        assert len(rows) == 3
        assert [r[0] for r in rows] == [
            "SESSION_CREATED",
            "EVIDENCE_UPLOADED",
            "ANALYSIS_REQUESTED",
        ]
    await engine.dispose()


@pytest.mark.database
async def test_deterministic_tie_breaker(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    sid = await _make_session(engine, "dtb")
    id1 = uuid.uuid4()
    id2 = uuid.uuid4()
    ts = datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO session_events (id, session_id, event_type, occurred_at) "
                "VALUES (:id, :sid, :et, :oa)"
            ),
            {"id": id1, "sid": sid, "et": "EVIDENCE_UPLOADED", "oa": ts},
        )
        await conn.execute(
            text(
                "INSERT INTO session_events (id, session_id, event_type, occurred_at) "
                "VALUES (:id, :sid, :et, :oa)"
            ),
            {"id": id2, "sid": sid, "et": "ANALYSIS_REQUESTED", "oa": ts},
        )
        rows = (
            await conn.execute(
                text(
                    "SELECT id FROM session_events "
                    "WHERE session_id = :sid "
                    "ORDER BY occurred_at, id"
                ),
                {"sid": sid},
            )
        ).all()
        # id1 < id2 in UUID comparison, so id1 comes first
        if id1 < id2:
            assert rows[0][0] == id1
            assert rows[1][0] == id2
        else:
            assert rows[0][0] == id2
            assert rows[1][0] == id1
    await engine.dispose()
