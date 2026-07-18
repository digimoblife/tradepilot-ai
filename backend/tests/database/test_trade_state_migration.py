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
async def test_trade_states_table_columns(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT column_name, data_type, is_nullable "
                    "FROM information_schema.columns "
                    "WHERE table_name = 'trade_states' ORDER BY ordinal_position"
                )
            )
        ).all()
        col_names = {r[0] for r in rows}
        for col in (
            "session_id",
            "position_status",
            "thesis_status",
            "state_version",
            "created_at",
            "updated_at",
        ):
            assert col in col_names, f"Missing column: {col}"
        assert "entry_price" in col_names
        assert "original_quantity" in col_names
        assert "remaining_quantity" in col_names
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
                    "WHERE conrelid = 'trade_states'::regclass "
                    "AND contype = 'f'"
                )
            )
        ).all()
        assert len(rows) >= 1
    await engine.dispose()


@pytest.mark.database
async def test_primary_key_is_session_id(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT column_name FROM information_schema.key_column_usage "
                    "WHERE table_name = 'trade_states' AND constraint_name = 'pk_trade_states'"
                )
            )
        ).all()
        assert any("session_id" in str(r) for r in rows)
    await engine.dispose()


@pytest.mark.database
async def test_enum_types_exist(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT t.typname FROM pg_type t "
                    "WHERE t.typname IN ('position_status_enum', 'thesis_status_enum')"
                )
            )
        ).all()
        found = {r[0] for r in rows}
        assert "position_status_enum" in found
        assert "thesis_status_enum" in found
    await engine.dispose()


@pytest.mark.database
async def test_check_constraints_exist(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT conname, pg_get_constraintdef(oid) "
                    "FROM pg_constraint "
                    "WHERE conrelid = 'trade_states'::regclass "
                    "AND contype = 'c' "
                    "ORDER BY conname"
                )
            )
        ).all()
        defs = {r[0]: r[1] for r in rows}
        assert "ck_trade_states_original_quantity_non_negative" in defs
        assert "ck_trade_states_remaining_quantity_non_negative" in defs
        assert "ck_trade_states_remaining_not_above_original" in defs
        assert "ck_trade_states_state_version_min" in defs
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
                    "WHERE table_schema = 'public' "
                    "AND table_name NOT IN ('alembic_version') "
                    "ORDER BY table_name"
                )
            )
        ).all()
        tables = {r[0] for r in rows}
        assert tables == {
            "users",
            "trade_sessions",
            "trade_states",
            "trade_actions",
            "evidence",
        }, f"Unexpected tables: {tables}"
    await engine.dispose()
