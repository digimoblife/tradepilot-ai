# ruff: noqa: E501
import os

import pytest
from sqlalchemy import text

from app.config import AppConfig
from app.database.session import create_async_engine_from_config

ALEMBIC_CFG = "alembic.ini"


def _assert_safe_test_db(db_url: str) -> None:
    assert "test" in db_url.lower(), (
        f"Refusing to run destructive tests against non-test database: {db_url}"
    )
    assert os.environ.get("APP_ENV", "") == "test", (
        "APP_ENV must be 'test' for destructive migration tests"
    )


_DEFAULT_SYNC_URL = (
    "postgresql+psycopg://tradepilot:change_me@localhost:5432/tradepilot_test"
)
_DEFAULT_ASYNC_URL = (
    "postgresql+asyncpg://tradepilot:change_me@localhost:5432/tradepilot_test"
)


@pytest.fixture(scope="session")
def sync_db_url() -> str:
    return os.environ.get("DATABASE_SYNC_URL", _DEFAULT_SYNC_URL)


@pytest.fixture(scope="session")
def async_db_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", _DEFAULT_ASYNC_URL)


@pytest.mark.database
def test_alembic_configuration_loads(sync_db_url: str) -> None:
    _assert_safe_test_db(sync_db_url)
    from alembic.config import Config

    config = Config(ALEMBIC_CFG)
    assert config.config_file_name == ALEMBIC_CFG


@pytest.mark.database
def test_alembic_upgrade_and_downgrade(sync_db_url: str) -> None:
    _assert_safe_test_db(sync_db_url)
    from alembic import command
    from alembic.config import Config

    config = Config(ALEMBIC_CFG)
    config.set_main_option("sqlalchemy.url", sync_db_url)

    command.upgrade(config, "head")
    command.downgrade(config, "base")
    command.upgrade(config, "head")


@pytest.mark.database
async def test_no_business_tables_after_migration(
    async_db_url: str,
) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)

    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' "
                "AND table_name NOT IN ('alembic_version')"
            )
        )
        tables = {row[0] for row in result}
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


@pytest.mark.database
async def test_alembic_current_revision_returns_head(
    sync_db_url: str,
) -> None:
    from alembic import command
    from alembic.config import Config

    config = Config(ALEMBIC_CFG)
    config.set_main_option("sqlalchemy.url", sync_db_url)

    command.upgrade(config, "head")

    from alembic.script import ScriptDirectory

    script = ScriptDirectory.from_config(config)
    head = script.get_current_head()
    assert head is not None, "No head revision found"
