# ruff: noqa: E501
import os

import pytest
from sqlalchemy import text

from app.config import AppConfig
from app.database.session import create_async_engine_from_config

ALEMBIC_CFG = "alembic.ini"
_DEFAULT_SYNC = "postgresql+psycopg://tradepilot:change_me@localhost:5432/tradepilot_test"
_DEFAULT_ASYNC = "postgresql+asyncpg://tradepilot:change_me@localhost:5432/tradepilot_test"


def _assert_safe_test_db(db_url: str) -> None:
    assert "test" in db_url.lower()
    assert os.environ.get("APP_ENV", "") == "test"


@pytest.fixture(scope="session")
def sync_db_url() -> str:
    return os.environ.get("DATABASE_SYNC_URL", _DEFAULT_SYNC)


@pytest.fixture(scope="session")
def async_db_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", _DEFAULT_ASYNC)


_TP0107_TABLES = {"context_summaries", "session_events"}

_TP0107_ENUMS = {"context_quality_enum", "session_event_type_enum"}


@pytest.mark.database
def test_migration_upgrade(sync_db_url: str) -> None:
    _assert_safe_test_db(sync_db_url)
    from alembic import command
    from alembic.config import Config

    config = Config(ALEMBIC_CFG)
    config.set_main_option("sqlalchemy.url", sync_db_url)
    command.upgrade(config, "head")


@pytest.mark.database
async def test_tables_exist(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name IN "
                    "('context_summaries', 'session_events') ORDER BY table_name"
                )
            )
        ).all()
        found = {r[0] for r in rows}
        assert found == _TP0107_TABLES
    await engine.dispose()


@pytest.mark.database
async def test_enum_types_exist(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text("SELECT t.typname FROM pg_type t WHERE t.typname = ANY(:enums)"),
                {"enums": list(_TP0107_ENUMS)},
            )
        ).all()
        assert len(rows) == 2
    await engine.dispose()


@pytest.mark.database
async def test_context_summary_session_fk(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'context_summaries'::regclass AND contype = 'f'"
                )
            )
        ).all()
        names = {r[0] for r in rows}
        assert "fk_context_summaries_session_id_trade_sessions" in names
    await engine.dispose()


@pytest.mark.database
async def test_session_event_session_fk(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'session_events'::regclass AND contype = 'f'"
                )
            )
        ).all()
        names = {r[0] for r in rows}
        assert "fk_session_events_session_id_trade_sessions" in names
    await engine.dispose()


@pytest.mark.database
async def test_related_action_fk(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'session_events'::regclass AND contype = 'f'"
                )
            )
        ).all()
        names = {r[0] for r in rows}
        assert "fk_session_events_related_action_id_trade_actions" in names
    await engine.dispose()


@pytest.mark.database
async def test_related_analysis_fk(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'session_events'::regclass AND contype = 'f'"
                )
            )
        ).all()
        names = {r[0] for r in rows}
        assert "fk_session_events_related_analysis_id_analyses" in names
    await engine.dispose()


@pytest.mark.database
async def test_version_uniqueness(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'context_summaries'::regclass "
                    "AND contype = 'u'"
                )
            )
        ).all()
        names = {r[0] for r in rows}
        assert "uq_context_summaries_session_version" in names
    await engine.dispose()


@pytest.mark.database
async def test_version_check(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'context_summaries'::regclass "
                    "AND contype = 'c' AND conname = 'ck_context_summaries_version'"
                )
            )
        ).all()
        assert len(rows) == 1
    await engine.dispose()


@pytest.mark.database
async def test_quantity_check(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'session_events'::regclass "
                    "AND contype = 'c' AND conname = 'ck_session_events_quantity'"
                )
            )
        ).all()
        assert len(rows) == 1
    await engine.dispose()


@pytest.mark.database
async def test_indexes_exist(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes "
                    "WHERE tablename IN ('context_summaries', 'session_events')"
                )
            )
        ).all()
        names = {r[0] for r in rows}
        assert "ix_context_summaries_session_version" in names
        assert "ix_context_summaries_session_created" in names
        assert "ix_session_events_chronological" in names
        assert "ix_session_events_type" in names
    await engine.dispose()


@pytest.mark.database
def test_downgrade_removes_tp0107(sync_db_url: str) -> None:
    _assert_safe_test_db(sync_db_url)
    from alembic import command
    from alembic.config import Config

    config = Config(ALEMBIC_CFG)
    config.set_main_option("sqlalchemy.url", sync_db_url)
    command.downgrade(config, "fc58b8bbeab7")


@pytest.mark.database
async def test_downgrade_removes_tables(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = ANY(:tables)"
                ),
                {"tables": list(_TP0107_TABLES)},
            )
        ).all()
        assert len(rows) == 0
    await engine.dispose()


@pytest.mark.database
async def test_downgrade_removes_enums(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text("SELECT t.typname FROM pg_type t WHERE t.typname = ANY(:enums)"),
                {"enums": list(_TP0107_ENUMS)},
            )
        ).all()
        assert len(rows) == 0
    await engine.dispose()


@pytest.mark.database
def test_re_upgrade_succeeds(sync_db_url: str) -> None:
    _assert_safe_test_db(sync_db_url)
    from alembic import command
    from alembic.config import Config

    config = Config(ALEMBIC_CFG)
    config.set_main_option("sqlalchemy.url", sync_db_url)
    command.upgrade(config, "head")


@pytest.mark.database
async def test_one_head(sync_db_url: str) -> None:
    _assert_safe_test_db(sync_db_url)
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(ALEMBIC_CFG)
    config.set_main_option("sqlalchemy.url", sync_db_url)
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    assert len(heads) == 1
    assert heads[0] == "8e4d747e19db"


@pytest.mark.database
def test_alembic_drift_clean(sync_db_url: str) -> None:
    _assert_safe_test_db(sync_db_url)
    from alembic import command
    from alembic.config import Config

    config = Config(ALEMBIC_CFG)
    config.set_main_option("sqlalchemy.url", sync_db_url)
    command.check(config)
