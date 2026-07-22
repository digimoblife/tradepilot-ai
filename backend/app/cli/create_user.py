#!/usr/bin/env python3
"""Production CLI to create or update the first TradePilot user.

Usage from the backend container::

    python -m app.cli.create_user --email user@example.com

Optional explicit reset::

    python -m app.cli.create_user \\
        --email user@example.com \\
        --reset-password

The password is prompted interactively (hidden) by default.  In non-interactive
environments set ``CREATE_USER_PASSWORD`` env var (use with caution —
never in shared/CI contexts).
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
import uuid

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.auth.passwords import hash_password


def _get_db_url() -> str:
    url = os.environ.get("DATABASE_SYNC_URL") or os.environ.get("DATABASE_URL", "")
    if not url:
        print("ERROR: DATABASE_SYNC_URL or DATABASE_URL must be set", file=sys.stderr)
        sys.exit(1)
    # Convert async URL to sync if needed
    url = url.replace("+asyncpg", "+psycopg")
    return url


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def user_exists(engine, email: str) -> bool:
    with Session(engine) as session:
        result = session.execute(
            text("SELECT 1 FROM users WHERE email = :e"),
            {"e": email},
        )
        return result.first() is not None


def create_user(
    engine,
    email: str,
    password: str,
    *,
    reset: bool = False,
) -> str:
    normalized = _normalize_email(email)
    exists = user_exists(engine, normalized)

    if exists and not reset:
        print(
            f"ERROR: User {normalized} already exists. Use --reset-password to update.",
            file=sys.stderr,
        )
        sys.exit(1)

    hashed = hash_password(password)
    uid = uuid.uuid4()

    with Session(engine) as session:
        if exists and reset:
            session.execute(
                text(
                    "UPDATE users SET password_hash = :ph, "
                    "account_status = 'ACTIVE', updated_at = NOW() "
                    "WHERE email = :e"
                ),
                {"ph": hashed, "e": normalized},
            )
            print(f"Password reset for {normalized}")
        else:
            session.execute(
                text(
                    "INSERT INTO users "
                    "(id, email, password_hash, account_status, "
                    "created_at, updated_at) "
                    "VALUES (:id, :e, :ph, 'ACTIVE', NOW(), NOW())"
                ),
                {"id": uid, "e": normalized, "ph": hashed},
            )
            print(f"User {normalized} created (id={uid})")
        session.commit()

    return str(uid)


def _prompt_password(reset: bool) -> str:
    env_pw = os.environ.get("CREATE_USER_PASSWORD")
    if env_pw:
        return env_pw
    label = "New password" if reset else "Password"
    pw = getpass.getpass(f"{label}: ")
    confirm = getpass.getpass("Confirm: ")
    if pw != confirm:
        print("ERROR: Passwords do not match", file=sys.stderr)
        sys.exit(1)
    if not pw:
        print("ERROR: Password must not be empty", file=sys.stderr)
        sys.exit(1)
    return pw


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update a TradePilot user")
    parser.add_argument("--email", required=True, help="User email address")
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Reset password for existing user",
    )
    args = parser.parse_args()

    password = _prompt_password(reset=args.reset_password)

    engine = create_engine(_get_db_url())
    try:
        create_user(engine, args.email, password, reset=args.reset_password)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
