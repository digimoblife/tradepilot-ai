"""Authentication service (TP-1001).

Provides credential authentication, session resolution, and revocation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.errors import (
    AuthenticationExpiredError,
    AuthenticationInactiveError,
    AuthenticationInvalidError,
    AuthenticationRequiredError,
)
from app.auth.passwords import verify_password
from app.auth.sessions import AuthSession, SessionStore
from app.config import AppConfig
from app.models.enums import AccountStatus
from app.repositories.auth_session import AuthSessionRepository
from app.repositories.user import UserRepository


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Safe identity fields exposed after successful authentication."""

    id: uuid.UUID
    email: str


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    """Result of a successful login."""

    user: AuthenticatedUser
    raw_token: str
    session: AuthSession


class AuthenticationService:
    """Handles login, session resolution, and logout."""

    def __init__(self, session: AsyncSession, config: AppConfig | None = None) -> None:
        self._session = session
        self._config = config or AppConfig()
        self._user_repo = UserRepository(session)
        self._session_repo = AuthSessionRepository(session)

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def authenticate(
        self,
        *,
        email: str,
        password: str,
    ) -> AuthenticatedSession:
        """Authenticate a user with email and password.

        Returns an ``AuthenticatedSession`` on success.

        Raises
        ------
        AuthenticationInvalidError
            For unknown email OR wrong password (same public error).
        AuthenticationInactiveError
            If the user account is not active.
        """
        from app.models.user import normalize_email

        normalized = normalize_email(email)

        user = await self._user_repo.get_by_email(normalized)
        if user is None:
            raise AuthenticationInvalidError(
                message="Invalid email or password",
            )

        if not verify_password(password, user.password_hash):
            raise AuthenticationInvalidError(
                message="Invalid email or password",
            )

        if user.account_status != AccountStatus.ACTIVE:
            raise AuthenticationInactiveError(
                message="Account is not active",
            )

        raw, session = SessionStore.create(
            user.id,
            self._config.auth_session_lifetime_seconds,
        )
        await self._session_repo.add(session)

        user.last_login_at = datetime.now(timezone.utc)

        return AuthenticatedSession(
            user=AuthenticatedUser(id=user.id, email=user.email),
            raw_token=raw,
            session=session,
        )

    # ------------------------------------------------------------------
    # Session resolution
    # ------------------------------------------------------------------

    async def resolve_session(
        self,
        *,
        raw_token: str,
    ) -> AuthenticatedUser:
        """Resolve a raw session token to an authenticated user.

        Raises
        ------
        AuthenticationRequiredError
            If no token is provided.
        AuthenticationInvalidError
            If the token is unknown or malformed.
        AuthenticationExpiredError
            If the session has expired.
        AuthenticationInactiveError
            If the associated user is no longer active.
        """
        if not raw_token:
            raise AuthenticationRequiredError(
                message="Authentication required",
            )

        session = await self._session_repo.get_by_token(raw_token)
        if session is None:
            raise AuthenticationInvalidError(
                message="Invalid session",
            )

        if session.revoked_at is not None:
            raise AuthenticationInvalidError(
                message="Session has been revoked",
            )

        now = datetime.now(timezone.utc)
        if session.expires_at <= now:
            raise AuthenticationExpiredError(
                message="Session has expired",
            )

        user = await self._user_repo.get_by_id(session.user_id)
        if user is None:
            raise AuthenticationInvalidError(
                message="Invalid session",
            )

        if user.account_status != AccountStatus.ACTIVE:
            raise AuthenticationInactiveError(
                message="Account is not active",
            )

        return AuthenticatedUser(id=user.id, email=user.email)

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    async def revoke_session(
        self,
        *,
        raw_token: str,
    ) -> None:
        """Revoke an authenticated session (logout)."""
        if not raw_token:
            return
        session = await self._session_repo.get_by_token(raw_token)
        if session is not None:
            await self._session_repo.revoke(session)
