import os
import uuid

import pytest
from sqlalchemy import text

from app.config import AppConfig
from app.database.session import create_async_engine_from_config
from app.models.enums import AccountStatus
from app.models.user import User, normalize_email

_DEFAULT_URL = (
    "postgresql+asyncpg://tradepilot:change_me@localhost:5432/tradepilot_test"
)


@pytest.fixture
def db_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", _DEFAULT_URL)


@pytest.mark.database
async def test_user_can_be_inserted(db_url: str) -> None:
    engine = create_async_engine_from_config(AppConfig(database_url=db_url))
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
        result = await conn.execute(
            text(
                "INSERT INTO users (email, password_hash) "
                "VALUES (:email, :ph) RETURNING id"
            ),
            {"email": "test@example.com", "ph": "hashed_pw"},
        )
        row = result.first()
        assert row is not None
        assert isinstance(row[0], uuid.UUID)
    await engine.dispose()


@pytest.mark.database
async def test_email_normalization(db_url: str) -> None:
    assert normalize_email("  Test@Example.COM  ") == "test@example.com"
    assert normalize_email("USER@DOMAIN.ID") == "user@domain.id"


@pytest.mark.database
async def test_user_defaults(db_url: str) -> None:
    assert User().account_status == AccountStatus.ACTIVE
    assert User().preferred_ui_language == "id-ID"
    assert User().timezone == "Asia/Jakarta"


@pytest.mark.database
async def test_timestamps_are_timezone_aware(db_url: str) -> None:
    u = User(email="ts@test.com", password_hash="x")
    assert u.created_at is not None
    assert u.updated_at is not None


@pytest.mark.database
async def test_uuid_primary_key(db_url: str) -> None:
    engine = create_async_engine_from_config(AppConfig(database_url=db_url))
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
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    "INSERT INTO users (email, password_hash) "
                    "VALUES ('pk@test.com', 'pw') RETURNING id"
                )
            )
        ).first()
        assert row is not None
        assert isinstance(row[0], uuid.UUID)
    await engine.dispose()


@pytest.mark.database
async def test_duplicate_email_rejected(db_url: str) -> None:
    engine = create_async_engine_from_config(AppConfig(database_url=db_url))
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
        await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES ('dup@t.com', 'pw')")
        )
        with pytest.raises(Exception):
            await conn.execute(
                text("INSERT INTO users (email, password_hash) VALUES (:e, :p)"),
                {"e": "dup@t.com", "p": "pw"},
            )
    await engine.dispose()
