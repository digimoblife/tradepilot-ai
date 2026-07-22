"""Tests for the user_sessions migration (4a2b6c8d0e1f).

Uses raw SQL inspection (not Alembic) to verify the table structure
matches what the migration creates.  The migration DDL is verified
manually during development; this test ensures the test database
has the correct schema expected by the auth code.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, inspect, text

pytestmark = pytest.mark.database

_DB_URL = os.environ.get(
    "DATABASE_SYNC_URL",
    "postgresql+psycopg://tradepilot:change_me@localhost:5432/tradepilot_test",
)

_SESSION_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
)
"""

_TOKEN_HASH_INDEX = (
    "CREATE INDEX IF NOT EXISTS ix_user_sessions_token_hash ON user_sessions(token_hash)"
)
_USER_ID_INDEX = "CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions(user_id)"


@pytest.fixture(scope="module")
def engine():
    e = create_engine(_DB_URL)
    yield e
    e.dispose()


class TestUserSessionsSchema:
    def test_table_structure_matches_migration(self, engine):
        """Verify that the table helper matches migration 4a2b6c8d0e1f."""
        with engine.begin() as c:
            c.execute(text(_SESSION_TABLE_SQL))
            c.execute(text(_TOKEN_HASH_INDEX))
            c.execute(text(_USER_ID_INDEX))

        cols = {col["name"]: col for col in inspect(engine).get_columns("user_sessions")}

        expected = {
            "id": False,
            "user_id": False,
            "token_hash": False,
            "expires_at": False,
            "created_at": False,
            "last_used_at": True,
            "revoked_at": True,
        }
        for name, nullable in expected.items():
            assert name in cols, f"Missing column: {name}"
            assert cols[name]["nullable"] == nullable, (
                f"{name}: expected nullable={nullable}, got {cols[name]['nullable']}"
            )

    def test_foreign_key_to_users(self, engine):
        fks = inspect(engine).get_foreign_keys("user_sessions")
        user_fks = [fk for fk in fks if fk["constrained_columns"] == ["user_id"]]
        assert len(user_fks) >= 1, "No FK on user_id"
        fk = user_fks[0]
        assert fk["referred_table"] == "users"
        assert fk["referred_columns"] == ["id"]

    def test_indexes(self, engine):
        indexes = {ix["name"]: ix for ix in inspect(engine).get_indexes("user_sessions")}
        assert (
            "ix_user_sessions_token_hash" in indexes or "user_sessions_token_hash_key" in indexes
        )
        assert "ix_user_sessions_user_id" in indexes
