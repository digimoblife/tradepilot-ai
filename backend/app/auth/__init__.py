"""TradePilot AI authentication layer (TP-1001)."""

from app.auth.errors import (
    AuthenticationError,
    AuthenticationExpiredError,
    AuthenticationInactiveError,
    AuthenticationInvalidError,
    AuthenticationRequiredError,
)
from app.auth.passwords import hash_password, verify_password
from app.auth.service import (
    AuthenticatedSession,
    AuthenticatedUser,
    AuthenticationService,
)

__all__ = [
    "AuthenticatedSession",
    "AuthenticatedUser",
    "AuthenticationError",
    "AuthenticationExpiredError",
    "AuthenticationInactiveError",
    "AuthenticationInvalidError",
    "AuthenticationRequiredError",
    "AuthenticationService",
    "hash_password",
    "verify_password",
]
