"""Opaque authenticated session management (TP-1001).

Uses the ``user_sessions`` table for persistence.
Session tokens are opaque random strings; only their SHA-256 hash
is stored server-side.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.types import pg_uuid, utc_datetime

# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

_TOKEN_BYTES = 32


def generate_raw_token() -> str:
    """Generate an unpredictable opaque session token."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def hash_token(raw: str) -> str:
    """Return the SHA-256 hash of a raw token for server-side storage."""
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# ORM model
# ---------------------------------------------------------------------------


class AuthSession(Base):
    __tablename__ = "user_sessions"

    __table_args__ = (
        Index("ix_user_sessions_token_hash", "token_hash", unique=True),
        Index("ix_user_sessions_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(pg_uuid(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        pg_uuid(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(utc_datetime(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        utc_datetime(), nullable=False, server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(utc_datetime(), nullable=True)

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("created_at", func.now())
        super().__init__(**kwargs)


_SESSION_CLEANUP_INTERVAL = 3600  # seconds between cleanup checks


class SessionStore:
    """Server-side session store backed by the ``user_sessions`` table.

    Thread-safe for a single-process server; for multi-process deployments
    the database provides the source of truth.
    """

    def __init__(self, session_factory: object = None) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @staticmethod
    def create(user_id: uuid.UUID, lifetime_seconds: int) -> tuple[str, AuthSession]:
        """Create a new session for *user_id*.

        Returns ``(raw_token, AuthSession)``.  The caller must persist
        the ``AuthSession`` and return the *raw_token* to the client.
        """
        raw = generate_raw_token()
        now = datetime.now(timezone.utc)
        session = AuthSession(
            user_id=user_id,
            token_hash=hash_token(raw),
            expires_at=datetime.fromtimestamp(now.timestamp() + lifetime_seconds, tz=timezone.utc),
            created_at=now,
            last_used_at=now,
        )
        return raw, session

    @staticmethod
    def is_valid(session: AuthSession) -> bool:
        """Check whether *session* is active and not expired or revoked."""
        if session.revoked_at is not None:
            return False
        now = datetime.now(timezone.utc)
        if session.expires_at <= now:
            return False
        return True

    @staticmethod
    def revoke(session: AuthSession) -> None:
        """Mark *session* as revoked."""
        session.revoked_at = datetime.now(timezone.utc)
