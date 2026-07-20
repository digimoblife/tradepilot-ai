"""FastAPI route dependencies (TP-1001).

Provides ``get_current_user`` for authenticated route protection.
"""

from __future__ import annotations

from fastapi import Depends, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    AuthenticatedUser,
    AuthenticationService,
)
from app.auth.errors import (
    AuthenticationError,
    AuthenticationRequiredError,
)
from app.config import AppConfig
from app.database.session import get_db_session

_CONFIG = AppConfig()


async def get_current_user(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
) -> AuthenticatedUser:
    """Resolve the authenticated user from the session cookie.

    Raises standard ``AuthenticationError`` subclasses on failure.
    """
    raw_token: str | None = request.cookies.get(_CONFIG.auth_cookie_name)
    if not raw_token:
        raise AuthenticationRequiredError(message="Authentication required")

    svc = AuthenticationService(db_session)
    return await svc.resolve_session(raw_token=raw_token)


async def get_optional_user(
    request: Request,
    db_session: AsyncSession = Depends(get_db_session),
) -> AuthenticatedUser | None:
    """Resolve the authenticated user if a valid session cookie exists.

    Returns ``None`` when no authentication is present (no error raised).
    """
    raw_token: str | None = request.cookies.get(_CONFIG.auth_cookie_name)
    if not raw_token:
        return None
    try:
        svc = AuthenticationService(db_session)
        return await svc.resolve_session(raw_token=raw_token)
    except AuthenticationError:
        return None


def set_session_cookie(response: Response, raw_token: str) -> None:
    """Set the authentication cookie on the response."""
    cfg = _CONFIG
    response.set_cookie(
        key=cfg.auth_cookie_name,
        value=raw_token,
        httponly=True,
        samesite="lax",
        max_age=cfg.auth_session_lifetime_seconds,
        secure=cfg.auth_cookie_secure,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    """Clear the authentication cookie on the response."""
    response.delete_cookie(
        key=_CONFIG.auth_cookie_name,
        path="/",
    )
