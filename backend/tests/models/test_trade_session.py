import os
import uuid

import pytest
from sqlalchemy import text

from app.config import AppConfig
from app.database.session import create_async_engine_from_config
from app.models.enums import TradeSessionStatus
from app.models.trade_session import normalize_currency, normalize_ticker

_DEFAULT_URL = (
    "postgresql+asyncpg://tradepilot:change_me@localhost:5432/tradepilot_test"
)


@pytest.fixture
def db_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", _DEFAULT_URL)


@pytest.mark.database
async def test_ticker_normalization() -> None:
    assert normalize_ticker("  bbri  ") == "BBRI"
    assert normalize_ticker("tlkm") == "TLKM"
    assert normalize_ticker("BBCA.JK") == "BBCA.JK"


@pytest.mark.database
async def test_currency_normalization() -> None:
    assert normalize_currency("  idr  ") == "IDR"
    assert normalize_currency("usd") == "USD"


@pytest.mark.database
async def test_default_status() -> None:
    assert TradeSessionStatus.DRAFT == "DRAFT"


@pytest.mark.database
async def test_session_can_be_inserted(db_url: str) -> None:
    engine = create_async_engine_from_config(AppConfig(database_url=db_url))
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
        user_row = (
            await conn.execute(
                text(
                    "INSERT INTO users (email, password_hash) "
                    "VALUES ('session_owner@t.com', 'pw') RETURNING id"
                )
            )
        ).first()
        assert user_row is not None
        uid = user_row[0]
        result = await conn.execute(
            text(
                "INSERT INTO trade_sessions (owner_id, ticker) "
                "VALUES (:uid, :t) RETURNING id"
            ),
            {"uid": uid, "t": "BBRI"},
        )
        row = result.first()
        assert row is not None
        assert isinstance(row[0], uuid.UUID)
    await engine.dispose()


@pytest.mark.database
async def test_unknown_user_rejected(db_url: str) -> None:
    engine = create_async_engine_from_config(AppConfig(database_url=db_url))
    fake_id = uuid.uuid4()
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text("INSERT INTO trade_sessions (owner_id, ticker) VALUES (:uid, :t)"),
                {"uid": fake_id, "t": "BBRI"},
            )
    await engine.dispose()


@pytest.mark.database
async def test_ticker_whitespace_removed(db_url: str) -> None:
    engine = create_async_engine_from_config(AppConfig(database_url=db_url))
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
        user_row = (
            await conn.execute(
                text(
                    "INSERT INTO users (email, password_hash) "
                    "VALUES ('ticker_norm@t.com', 'pw') RETURNING id"
                )
            )
        ).first()
        assert user_row is not None
        uid = user_row[0]
        normalized = normalize_ticker("  bbri  ")
        assert normalized == "BBRI"
        result = await conn.execute(
            text(
                "INSERT INTO trade_sessions (owner_id, ticker) "
                "VALUES (:uid, :t) RETURNING ticker"
            ),
            {"uid": uid, "t": normalized},
        )
        row = result.first()
        assert row is not None
        assert row[0] == "BBRI"
    await engine.dispose()


@pytest.mark.database
async def test_relationship_to_user(db_url: str) -> None:
    engine = create_async_engine_from_config(AppConfig(database_url=db_url))
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
        user_row = (
            await conn.execute(
                text(
                    "INSERT INTO users (email, password_hash) "
                    "VALUES ('rel@t.com', 'pw') RETURNING id"
                )
            )
        ).first()
        assert user_row is not None
        uid = user_row[0]
        await conn.execute(
            text("INSERT INTO trade_sessions (owner_id, ticker) VALUES (:uid, 'BBRI')"),
            {"uid": uid},
        )
        rows = (
            await conn.execute(
                text("SELECT id FROM trade_sessions WHERE owner_id = :uid"),
                {"uid": uid},
            )
        ).all()
        assert len(rows) >= 1
    await engine.dispose()
