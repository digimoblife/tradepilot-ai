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


_TP0106_TABLES = {
    "analysis_jobs",
    "analyses",
    "provider_requests",
    "provider_responses",
    "validation_attempts",
}

_TP0106_ENUMS = {
    "analysis_type_enum",
    "analysis_job_status_enum",
    "acceptance_status_enum",
    "provider_enum",
    "provider_response_status_enum",
    "validation_stage_enum",
}


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
                    "WHERE table_schema = 'public' AND table_name IN ("
                    "'analysis_jobs', 'analyses', 'provider_requests', "
                    "'provider_responses', 'validation_attempts')"
                    " ORDER BY table_name"
                )
            )
        ).all()
        found = {r[0] for r in rows}
        assert found == _TP0106_TABLES
    await engine.dispose()


@pytest.mark.database
async def test_enum_types_exist(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text("SELECT t.typname FROM pg_type t WHERE t.typname = ANY(:enums)"),
                {"enums": list(_TP0106_ENUMS)},
            )
        ).all()
        assert len(rows) == 6
    await engine.dispose()


@pytest.mark.database
async def test_foreign_keys_exist(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT conname, contype FROM pg_constraint "
                    "WHERE conrelid::regclass::text IN ("
                    "'analysis_jobs', 'analyses', 'provider_requests', "
                    "'provider_responses', 'validation_attempts'"
                    ")"
                )
            )
        ).all()
        defs = {r[0]: r[1] for r in rows}
        assert "fk_analysis_jobs_session_id_trade_sessions" in defs
        assert "fk_analyses_session_id_trade_sessions" in defs
        assert "fk_analyses_analysis_job_id_analysis_jobs" in defs
        assert "fk_analyses_supersedes_analysis_id_analyses" in defs
        assert "fk_provider_requests_analysis_job_id_analysis_jobs" in defs
        assert "fk_provider_responses_provider_request_id_provider_requests" in defs
        assert "fk_validation_attempts_analysis_job_id_analysis_jobs" in defs
    await engine.dispose()


@pytest.mark.database
async def test_trade_action_deferred_fk_exists(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'trade_actions'::regclass "
                    "AND contype = 'f'"
                )
            )
        ).all()
        names = {r[0] for r in rows}
        assert "fk_trade_actions_related_analysis_id_analyses" in names
    await engine.dispose()


@pytest.mark.database
async def test_retry_constraints_exist(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'analysis_jobs'::regclass "
                    "AND contype = 'c'"
                )
            )
        ).all()
        names = {r[0] for r in rows}
        assert "ck_analysis_jobs_attempt_count" in names
        assert "ck_analysis_jobs_max_attempts" in names
        assert "ck_analysis_jobs_attempts_bound" in names
    await engine.dispose()


@pytest.mark.database
async def test_schema_version_requirements(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        # Check analyses constraints
        rows = (
            await conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'analyses'::regclass "
                    "AND contype = 'c'"
                )
            )
        ).all()
        names = {r[0] for r in rows}
        assert "ck_analyses_schema_name" in names
        assert "ck_analyses_schema_version" in names
        assert "ck_analyses_prompt_version" in names
    await engine.dispose()


@pytest.mark.database
async def test_superseding_fk_exists(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT conname, contype, pg_get_constraintdef(oid) "
                    "FROM pg_constraint WHERE conrelid = 'analyses'::regclass "
                    "AND conname = 'ck_analyses_no_self_supersede'"
                )
            )
        ).all()
        assert len(rows) == 1
        assert "supersedes_analysis_id IS NULL" in rows[0][2]
        assert "supersedes_analysis_id <> id" in rows[0][2]
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
                    "WHERE tablename IN ("
                    "'analysis_jobs', 'analyses', 'provider_requests', "
                    "'provider_responses', 'validation_attempts'"
                    ")"
                )
            )
        ).all()
        names = {r[0] for r in rows}
        assert "ix_analysis_jobs_queue" in names
        assert "ix_analysis_jobs_lease" in names
        assert "ix_analysis_jobs_session_created" in names
        assert "ix_analysis_jobs_session_type_status" in names
        assert "ix_analyses_session_type_created" in names
        assert "ix_analyses_accepted" in names
        assert "ix_analyses_supersedes" in names
        assert "ix_analyses_job" in names
    await engine.dispose()


@pytest.mark.database
def test_downgrade_removes_tp0106(sync_db_url: str) -> None:
    _assert_safe_test_db(sync_db_url)
    from alembic import command
    from alembic.config import Config

    config = Config(ALEMBIC_CFG)
    config.set_main_option("sqlalchemy.url", sync_db_url)
    command.downgrade(config, "9d219c5a02e1")


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
                {"tables": list(_TP0106_TABLES)},
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
                {"enums": list(_TP0106_ENUMS)},
            )
        ).all()
        assert len(rows) == 0
    await engine.dispose()


@pytest.mark.database
async def test_downgrade_removes_deferred_fk(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT conname FROM pg_constraint "
                    "WHERE conrelid = 'trade_actions'::regclass "
                    "AND contype = 'f' AND conname = 'fk_trade_actions_related_analysis_id_analyses'"
                )
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
    assert heads[0] == "fc58b8bbeab7"


@pytest.mark.database
async def test_no_tp0107_table_exists(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name IN "
                    "('context_summaries', 'session_events', 'worker_heartbeats')"
                )
            )
        ).all()
        assert len(rows) == 0
    await engine.dispose()


@pytest.mark.database
def test_alembic_drift_clean(sync_db_url: str) -> None:
    _assert_safe_test_db(sync_db_url)
    from alembic import command
    from alembic.config import Config

    config = Config(ALEMBIC_CFG)
    config.set_main_option("sqlalchemy.url", sync_db_url)
    command.check(config)
