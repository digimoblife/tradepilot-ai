# ruff: noqa: E501
import os

import pytest
from sqlalchemy import text

from app.config import AppConfig
from app.database.session import create_async_engine_from_config

ALEMBIC_CFG = "alembic.ini"
_DEFAULT_SYNC = (
    "postgresql+psycopg://tradepilot:change_me@localhost:5432/tradepilot_test"
)
_DEFAULT_ASYNC = (
    "postgresql+asyncpg://tradepilot:change_me@localhost:5432/tradepilot_test"
)


def _assert_safe_test_db(db_url: str) -> None:
    assert "test" in db_url.lower()
    assert os.environ.get("APP_ENV", "") == "test"


@pytest.fixture(scope="session")
def sync_db_url() -> str:
    return os.environ.get("DATABASE_SYNC_URL", _DEFAULT_SYNC)


@pytest.fixture(scope="session")
def async_db_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", _DEFAULT_ASYNC)


@pytest.mark.database
def test_migration_creates_tables(sync_db_url: str) -> None:
    _assert_safe_test_db(sync_db_url)
    from alembic import command
    from alembic.config import Config

    config = Config(ALEMBIC_CFG)
    config.set_main_option("sqlalchemy.url", sync_db_url)
    command.upgrade(config, "head")


@pytest.mark.database
async def test_users_table_columns(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT column_name, data_type, is_nullable "
                    "FROM information_schema.columns "
                    "WHERE table_name = 'users' ORDER BY ordinal_position"
                )
            )
        ).all()
        col_names = {r[0] for r in rows}
        for col in (
            "id",
            "email",
            "password_hash",
            "account_status",
            "created_at",
            "updated_at",
        ):
            assert col in col_names, f"Missing column: {col}"
    await engine.dispose()


@pytest.mark.database
async def test_trade_sessions_table_columns(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT column_name, data_type, is_nullable "
                    "FROM information_schema.columns "
                    "WHERE table_name = 'trade_sessions' ORDER BY ordinal_position"
                )
            )
        ).all()
        col_names = {r[0] for r in rows}
        for col in (
            "id",
            "owner_id",
            "ticker",
            "lifecycle_status",
            "created_at",
            "updated_at",
            "version",
        ):
            assert col in col_names, f"Missing column: {col}"
    await engine.dispose()


@pytest.mark.database
async def test_foreign_key_exists(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'trade_sessions'::regclass "
                    "AND contype = 'f'"
                )
            )
        ).all()
        assert len(rows) >= 1
    await engine.dispose()


@pytest.mark.database
async def test_unique_email_constraint(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'users'::regclass "
                    "AND contype = 'u'"
                )
            )
        ).all()
        assert any("email" in str(r[0]) for r in rows)
    await engine.dispose()


@pytest.mark.database
async def test_only_expected_tables_exist(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' "
                    "AND table_name NOT IN ('alembic_version') "
                    "ORDER BY table_name"
                )
            )
        ).all()
        tables = {r[0] for r in rows}
        assert tables == {
            "analyses",
            "analysis_jobs",
            "context_summaries",
            "evidence",
            "provider_requests",
            "provider_responses",
            "session_events",
            "trade_actions",
            "trade_sessions",
            "trade_states",
            "users",
            "validation_attempts",
        }, f"Unexpected tables: {tables}"
    await engine.dispose()
