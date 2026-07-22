"""Tests for the create_user CLI (TP-1704)."""

from __future__ import annotations

import os
import uuid
from typing import Any, Iterator

import pytest
from sqlalchemy import create_engine, text

from app.auth.passwords import verify_password
from app.cli.create_user import create_user, user_exists

pytestmark = pytest.mark.database

_DB_URL = os.environ.get(
    "DATABASE_SYNC_URL",
    "postgresql+psycopg://tradepilot:change_me@localhost:5432/tradepilot_test",
)


@pytest.fixture(scope="module")
def engine() -> Any:
    e = create_engine(_DB_URL)
    yield e
    e.dispose()


@pytest.fixture(autouse=True)
def _cleanup(engine: Any) -> Iterator[None]:
    yield
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM users WHERE email LIKE 'cli_test_%@test.com'"))


# ===================================================================
# CLI tests
# ===================================================================


class TestCreateUserCLI:
    def test_creates_active_user(self, engine: Any) -> None:
        email = "cli_test_create@test.com"
        uid = create_user(engine, email, "secret123")
        assert uid is not None
        assert uuid.UUID(uid)

        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT account_status, password_hash FROM users WHERE email = :e"),
                {"e": email},
            ).first()
        assert row is not None
        assert row[0] == "ACTIVE"
        assert verify_password("secret123", row[1])

    def test_login_succeeds_with_created_user(self, engine: Any) -> None:
        email = "cli_test_login@test.com"
        create_user(engine, email, "pass123")
        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT password_hash FROM users WHERE email = :e"),
                {"e": email},
            ).first()
        assert row is not None
        assert verify_password("pass123", row[0])

    def test_duplicate_user_rejected(self, engine: Any) -> None:
        email = "cli_test_dup@test.com"
        create_user(engine, email, "secret")
        with pytest.raises(SystemExit):
            create_user(engine, email, "other")

    def test_password_reset_works(self, engine: Any) -> None:
        email = "cli_test_reset@test.com"
        create_user(engine, email, "first_pass")
        # Reset password
        create_user(engine, email, "new_pass", reset=True)
        with engine.begin() as conn:
            row = conn.execute(
                text("SELECT password_hash FROM users WHERE email = :e"),
                {"e": email},
            ).first()
        assert row is not None
        assert verify_password("new_pass", row[0])
        assert not verify_password("first_pass", row[0])

    def test_password_not_in_output(self, engine: Any) -> None:
        email = "cli_test_secret@test.com"
        import io
        import sys

        captured = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        try:
            create_user(engine, email, "super_secret_123")
        finally:
            sys.stdout = old_stdout

        output = captured.getvalue()
        assert "super_secret_123" not in output

    def test_user_exists_check(self, engine: Any) -> None:
        email = "cli_test_exists@test.com"
        assert not user_exists(engine, email)
        create_user(engine, email, "pw")
        assert user_exists(engine, email)
