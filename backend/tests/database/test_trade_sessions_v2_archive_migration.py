from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

ALEMBIC_CFG = "alembic.ini"
PARENT_REVISION = "d0e1f2a3b4c5"
ARCHIVE_REVISION = "e1f2a3b4c5d6"
BACKEND_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_PATH = BACKEND_ROOT / ALEMBIC_CFG
MIGRATION_PATH = BACKEND_ROOT / "migrations/versions/e1f2a3b4c5d6_p72_archive_metadata.py"


def _sync_db_url() -> str:
    value = os.environ.get(
        "DATABASE_SYNC_URL",
        "postgresql+psycopg://tradepilot:change_me@localhost:5432/tradepilot_test",
    )
    assert "test" in value.lower(), f"Refusing migration test against non-test database: {value}"
    assert os.environ.get("APP_ENV", "") == "test", "APP_ENV must be 'test'"
    return value


def _alembic_config(db_url: str) -> Config:
    config = Config(str(ALEMBIC_PATH))
    config.set_main_option("sqlalchemy.url", db_url)
    return config


@pytest.mark.database
def test_archive_migration_revision_contract() -> None:
    source = MIGRATION_PATH.read_text()
    assert f'revision: str = "{ARCHIVE_REVISION}"' in source
    assert f'down_revision: str | None = "{PARENT_REVISION}"' in source
    assert "op.add_column(" in source
    assert '"trade_sessions_v2"' in source
    assert 'sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True)' in source
    assert 'op.drop_column("trade_sessions_v2", "archived_at")' in source
    assert "trade_sessions\"" not in source


@pytest.mark.database
def test_archive_migration_preserves_existing_v2_rows() -> None:
    db_url = _sync_db_url()
    config = _alembic_config(db_url)
    command.downgrade(config, "base")
    command.upgrade(config, PARENT_REVISION)

    engine = create_engine(db_url)
    try:
        with engine.begin() as connection:
            owner = "00000000-0000-0000-0000-000000000001"
            connection.execute(
                text(
                    "INSERT INTO users (id, email, password_hash) "
                    "VALUES (:id, :email, :password_hash)"
                ),
                {
                    "id": owner,
                    "email": "ux11-migration@example.test",
                    "password_hash": "test-only",
                },
            )
            connection.execute(
                text(
                    "INSERT INTO trade_sessions_v2 "
                    "(id, user_id, ticker, company_name, status, note) VALUES "
                    "(:draft_id, :owner, 'BBRI', 'Bank BRI', 'DRAFT', 'draft'), "
                    "(:closed_id, :owner, 'TLKM', 'Telkom Indonesia', 'CLOSED', 'closed'), "
                    "(:skipped_id, :owner, 'ASII', 'Astra International', "
                    "'CLOSED_SKIPPED', 'skipped')"
                ),
                {
                    "draft_id": "00000000-0000-0000-0000-000000000011",
                    "closed_id": "00000000-0000-0000-0000-000000000012",
                    "skipped_id": "00000000-0000-0000-0000-000000000013",
                    "owner": owner,
                },
            )

        command.upgrade(config, ARCHIVE_REVISION)
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT id::text, user_id::text, ticker, company_name, status, note, "
                    "archived_at "
                    "FROM trade_sessions_v2 ORDER BY id"
                )
            ).mappings().all()
            column = connection.execute(
                text(
                    "SELECT is_nullable, data_type, datetime_precision "
                    "FROM information_schema.columns "
                    "WHERE table_name = 'trade_sessions_v2' AND column_name = 'archived_at'"
                )
            ).mappings().one()

        assert [row["status"] for row in rows] == ["DRAFT", "CLOSED", "CLOSED_SKIPPED"]
        assert [row["archived_at"] for row in rows] == [None, None, None]
        assert rows[0]["ticker"] == "BBRI"
        assert rows[1]["company_name"] == "Telkom Indonesia"
        assert rows[2]["note"] == "skipped"
        assert column["is_nullable"] == "YES"
        assert column["data_type"] == "timestamp with time zone"

        command.downgrade(config, PARENT_REVISION)
        with engine.connect() as connection:
            remaining = connection.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.columns "
                    "WHERE table_name = 'trade_sessions_v2' AND column_name = 'archived_at'"
                )
            ).scalar_one()
        assert remaining == 0
        command.upgrade(config, ARCHIVE_REVISION)
    finally:
        engine.dispose()
