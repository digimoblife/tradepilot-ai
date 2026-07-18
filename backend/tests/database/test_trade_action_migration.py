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
def test_migration_upgrade(sync_db_url: str) -> None:
    _assert_safe_test_db(sync_db_url)
    from alembic import command
    from alembic.config import Config

    config = Config(ALEMBIC_CFG)
    config.set_main_option("sqlalchemy.url", sync_db_url)
    command.upgrade(config, "head")


@pytest.mark.database
async def test_trade_actions_table_columns(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'trade_actions' ORDER BY ordinal_position"
                )
            )
        ).all()
        cols = {r[0] for r in rows}
        for c in (
            "id",
            "session_id",
            "action_type",
            "confirmed_at",
            "price",
            "quantity",
            "note",
            "related_analysis_id",
            "idempotency_key",
            "payload",
            "created_at",
        ):
            assert c in cols, f"Missing column: {c}"
    await engine.dispose()


@pytest.mark.database
async def test_session_foreign_key(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'trade_actions'::regclass AND contype = 'f'"
                )
            )
        ).all()
        assert len(rows) >= 1
    await engine.dispose()


@pytest.mark.database
async def test_enum_type_exists(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT t.typname FROM pg_type t "
                    "WHERE t.typname = 'trade_action_type_enum'"
                )
            )
        ).all()
        assert len(rows) >= 1
    await engine.dispose()


@pytest.mark.database
async def test_unique_idempotency_constraint(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT indexname, indexdef FROM pg_indexes "
                    "WHERE tablename = 'trade_actions' AND indexdef LIKE '%UNIQUE%'"
                )
            )
        ).all()
        assert any("idempotency" in str(r[0]) for r in rows)
    await engine.dispose()


@pytest.mark.database
async def test_quantity_check_constraint(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'trade_actions'::regclass AND contype = 'c'"
                )
            )
        ).all()
        names = {r[0] for r in rows}
        assert "ck_trade_actions_quantity_non_negative" in names
    await engine.dispose()


@pytest.mark.database
async def test_only_expected_tables(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name NOT IN ('alembic_version') "
                    "ORDER BY table_name"
                )
            )
        ).all()
        tables = {r[0] for r in rows}
        assert tables == {"users", "trade_sessions", "trade_states", "trade_actions"}
    await engine.dispose()
