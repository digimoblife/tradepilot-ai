# ruff: noqa: E501
import json
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


async def _make_user_and_session(
    engine: AsyncEngine,
    label: str,
) -> tuple[uuid.UUID, uuid.UUID]:
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM trade_actions"))
        await conn.execute(text("DELETE FROM trade_states"))
        await conn.execute(text("DELETE FROM trade_sessions"))
        await conn.execute(text("DELETE FROM users"))
    async with engine.begin() as conn:
        ur = (
            await conn.execute(
                text(
                    "INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"
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
    return ur[0], sr[0]


@pytest.mark.database
async def test_action_can_be_inserted(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "ins")
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO trade_actions (session_id, action_type, confirmed_at, idempotency_key) "
                "VALUES (:sid, :at, :ca, :ik) RETURNING id"
            ),
            {
                "sid": sid,
                "at": "POSITION_OPENED",
                "ca": datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
                "ik": "ik-001",
            },
        )
        row = result.first()
        assert row is not None
        assert isinstance(row[0], uuid.UUID)
    await engine.dispose()


@pytest.mark.database
async def test_unknown_session_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO trade_actions (session_id, action_type, confirmed_at, idempotency_key) "
                    "VALUES (:sid, :at, :ca, :ik)"
                ),
                {
                    "sid": uuid.uuid4(),
                    "at": "POSITION_OPENED",
                    "ca": datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
                    "ik": "ik-unknown",
                },
            )
    await engine.dispose()


@pytest.mark.database
async def test_invalid_action_type_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "iat")
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO trade_actions (session_id, action_type, confirmed_at, idempotency_key) "
                    "VALUES (:sid, :at, :ca, :ik)"
                ),
                {
                    "sid": sid,
                    "at": "INVALID_ACTION",
                    "ca": datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
                    "ik": "ik-invalid",
                },
            )
    await engine.dispose()


@pytest.mark.database
async def test_idempotency_duplicate_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "idem")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO trade_actions (session_id, action_type, confirmed_at, idempotency_key) "
                "VALUES (:sid, :at, :ca, :ik)"
            ),
            {
                "sid": sid,
                "at": "STOP_LOSS_CONFIRMED",
                "ca": datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
                "ik": "dup-key",
            },
        )
        with pytest.raises(Exception):
            await conn.execute(
                text(
                    "INSERT INTO trade_actions (session_id, action_type, confirmed_at, idempotency_key) "
                    "VALUES (:sid, :at, :ca, :ik)"
                ),
                {
                    "sid": sid,
                    "at": "STOP_LOSS_CHANGED",
                    "ca": datetime(2026, 7, 18, 11, 0, 0, tzinfo=timezone.utc),
                    "ik": "dup-key",
                },
            )
    await engine.dispose()


@pytest.mark.database
async def test_same_key_different_session_succeeds(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    # Create both sessions within a single cleanup scope
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM trade_actions"))
        await conn.execute(text("DELETE FROM trade_states"))
        await conn.execute(text("DELETE FROM trade_sessions"))
        await conn.execute(text("DELETE FROM users"))
        ur1 = (
            await conn.execute(
                text(
                    "INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"
                ),
                {"e": f"skd_a_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
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
                text(
                    "INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"
                ),
                {"e": f"skd_b_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
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
        s1 = sr1[0]
        s2 = sr2[0]
        await conn.execute(
            text(
                "INSERT INTO trade_actions (session_id, action_type, confirmed_at, idempotency_key) "
                "VALUES (:sid, :at, :ca, :ik)"
            ),
            {
                "sid": s1,
                "at": "POSITION_OPENED",
                "ca": datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
                "ik": "same-key",
            },
        )
        await conn.execute(
            text(
                "INSERT INTO trade_actions (session_id, action_type, confirmed_at, idempotency_key) "
                "VALUES (:sid, :at, :ca, :ik)"
            ),
            {
                "sid": s2,
                "at": "POSITION_OPENED",
                "ca": datetime(2026, 7, 18, 10, 30, 0, tzinfo=timezone.utc),
                "ik": "same-key",
            },
        )
    await engine.dispose()


@pytest.mark.database
async def test_negative_quantity_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "nq")
    async with engine.begin() as conn:
        with pytest.raises(Exception) as excinfo:
            await conn.execute(
                text(
                    "INSERT INTO trade_actions (session_id, action_type, confirmed_at, idempotency_key, quantity) "
                    "VALUES (:sid, :at, :ca, :ik, :q)"
                ),
                {
                    "sid": sid,
                    "at": "PARTIAL_EXIT",
                    "ca": datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
                    "ik": "ik-neg",
                    "q": Decimal("-100"),
                },
            )
        assert "violates check constraint" in str(excinfo.value)
    await engine.dispose()


@pytest.mark.database
async def test_decimal_price_round_trip(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "dpr")
    async with engine.begin() as conn:
        val = Decimal("3090.50")
        await conn.execute(
            text(
                "INSERT INTO trade_actions (session_id, action_type, confirmed_at, idempotency_key, price) "
                "VALUES (:sid, :at, :ca, :ik, :p)"
            ),
            {
                "sid": sid,
                "at": "POSITION_OPENED",
                "ca": datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
                "ik": "ik-dec",
                "p": val,
            },
        )
        row = (
            await conn.execute(
                text("SELECT price FROM trade_actions WHERE session_id = :sid"),
                {"sid": sid},
            )
        ).first()
        assert row is not None
        assert isinstance(row[0], Decimal)
        assert row[0] == val
    await engine.dispose()


@pytest.mark.database
async def test_jsonb_payload_round_trip(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "jrt")
    async with engine.begin() as conn:
        payload = {"key": "value", "numbers": [1, 2, 3]}
        await conn.execute(
            text(
                "INSERT INTO trade_actions (session_id, action_type, confirmed_at, idempotency_key, payload) "
                "VALUES (:sid, :at, :ca, :ik, CAST(:pl AS JSONB))"
            ),
            {
                "sid": sid,
                "at": "TARGET_CONFIRMED",
                "ca": datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
                "ik": "ik-json",
                "pl": json.dumps(payload),
            },
        )
        row = (
            await conn.execute(
                text("SELECT payload FROM trade_actions WHERE session_id = :sid"),
                {"sid": sid},
            )
        ).first()
        assert row is not None
        assert row[0] == payload
    await engine.dispose()


@pytest.mark.database
async def test_action_sequence_preserves_order(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "seq")
    actions = [
        (
            "POSITION_OPENED",
            datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
            "ik-seq-1",
            Decimal("3090"),
            Decimal("10000"),
        ),
        (
            "STOP_LOSS_CONFIRMED",
            datetime(2026, 7, 18, 10, 5, 0, tzinfo=timezone.utc),
            "ik-seq-2",
            Decimal("2840"),
            None,
        ),
        (
            "TARGET_CONFIRMED",
            datetime(2026, 7, 18, 10, 5, 0, tzinfo=timezone.utc),
            "ik-seq-3",
            Decimal("3250"),
            None,
        ),
        (
            "PARTIAL_EXIT",
            datetime(2026, 7, 18, 14, 0, 0, tzinfo=timezone.utc),
            "ik-seq-4",
            Decimal("3200"),
            Decimal("5000"),
        ),
    ]
    async with engine.begin() as conn:
        for at, ca, ik, p, q in actions:
            await conn.execute(
                text(
                    "INSERT INTO trade_actions (session_id, action_type, confirmed_at, idempotency_key, price, quantity) "
                    "VALUES (:sid, :at, :ca, :ik, :p, :q)"
                ),
                {"sid": sid, "at": at, "ca": ca, "ik": ik, "p": p, "q": q},
            )
        rows = (
            await conn.execute(
                text(
                    "SELECT action_type, confirmed_at, price, quantity, idempotency_key "
                    "FROM trade_actions WHERE session_id = :sid ORDER BY confirmed_at, id"
                ),
                {"sid": sid},
            )
        ).all()
        assert len(rows) == 4
        assert rows[0][0] == "POSITION_OPENED"
        assert rows[3][0] == "PARTIAL_EXIT"
    await engine.dispose()
