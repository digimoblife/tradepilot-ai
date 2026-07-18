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
async def test_evidence_table_columns(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = 'evidence' ORDER BY ordinal_position"
                )
            )
        ).all()
        cols = {r[0] for r in rows}
        for c in (
            "id",
            "session_id",
            "owner_id",
            "evidence_type",
            "evidence_status",
            "uploaded_at",
            "created_at",
            "updated_at",
        ):
            assert c in cols
    await engine.dispose()


@pytest.mark.database
async def test_constraints_exist(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT conname, contype, pg_get_constraintdef(oid) "
                    "FROM pg_constraint WHERE conrelid = 'evidence'::regclass ORDER BY conname"
                )
            )
        ).all()
        defs = {r[0]: (r[1], r[2]) for r in rows}
        assert "ck_evidence_file_size_non_negative" in defs
        assert "ck_evidence_extraction_confidence_range" in defs
        assert "ck_evidence_excluded_state" in defs
        assert "ck_evidence_checksum_format" in defs
        assert "ck_evidence_no_self_replacement" in defs
        assert "ck_evidence_safe_storage_key" in defs
        assert "fk_evidence_session_id_trade_sessions" in defs
        assert "fk_evidence_owner_id_users" in defs
        assert "fk_evidence_supersedes_evidence_id_evidence" in defs
    await engine.dispose()


@pytest.mark.database
async def test_enum_types_exist(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT t.typname FROM pg_type t WHERE t.typname IN ('evidence_type_enum', 'evidence_status_enum', 'extraction_status_enum')"
                )
            )
        ).all()
        assert len(rows) == 3


@pytest.mark.database
async def test_only_expected_tables(async_db_url: str) -> None:
    config = AppConfig(database_url=async_db_url)
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name NOT IN ('alembic_version') ORDER BY table_name"
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
            "analysis_jobs",
            "analyses",
            "provider_requests",
            "provider_responses",
            "validation_attempts",
        }
    await engine.dispose()
