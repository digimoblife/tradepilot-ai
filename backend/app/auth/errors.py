"""Stable authentication error hierarchy (TP-1001)."""

AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
AUTHENTICATION_INVALID = "AUTHENTICATION_INVALID"
AUTHENTICATION_EXPIRED = "AUTHENTICATION_EXPIRED"
AUTHENTICATION_INACTIVE = "AUTHENTICATION_INACTIVE"


class AuthenticationError(Exception):
    """Base authentication error."""

    code: str = AUTHENTICATION_REQUIRED

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class AuthenticationRequiredError(AuthenticationError):
    code: str = AUTHENTICATION_REQUIRED


class AuthenticationInvalidError(AuthenticationError):
    code: str = AUTHENTICATION_INVALID


class AuthenticationExpiredError(AuthenticationError):
    code: str = AUTHENTICATION_EXPIRED


class AuthenticationInactiveError(AuthenticationError):
    code: str = AUTHENTICATION_INACTIVE
