"""Security middleware for production hardening (TP-1604).

Provides rate limiting, security headers, CSRF protection via
Referer/Origin validation, and trusted-host enforcement.

All middleware is conditionally enabled via ``AppConfig`` so that
development environments remain unrestricted.
"""

from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.types import ASGIApp

from app.config import AppConfig

# ---------------------------------------------------------------------------
# Security headers
# ---------------------------------------------------------------------------

_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "0",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add hardened HTTP security headers to every response.

    Headers set:
    * ``X-Content-Type-Options: nosniff``
    * ``X-Frame-Options: DENY``
    * ``Strict-Transport-Security`` (1 year, include subdomains)
    * ``Content-Security-Policy`` (self-only)
    * ``Referrer-Policy`` (strict-origin-when-cross-origin)
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        for key, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        return response


# ---------------------------------------------------------------------------
# CSRF protection (Referer / Origin check)
# ---------------------------------------------------------------------------

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """Validate Referer/Origin on state-changing requests.

    Only applies to methods outside ``_SAFE_METHODS`` (POST/PUT/PATCH/DELETE).
    Skips paths listed in ``config.csrf_exclude_paths`` (health, login).

    This provides defence-in-depth alongside ``SameSite=Lax`` cookies.
    """

    def __init__(self, app: ASGIApp, config: AppConfig) -> None:
        super().__init__(app)
        self._config = config
        self._exclude_prefixes = tuple(p for p in config.csrf_exclude_paths)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self._config.csrf_enabled:
            return await call_next(request)

        if request.method in _SAFE_METHODS:
            return await call_next(request)

        if request.url.path.startswith(self._exclude_prefixes):
            return await call_next(request)

        origin = request.headers.get("Origin")
        referer = request.headers.get("Referer")

        # One of Origin or Referer must be present
        if not origin and not referer:
            return PlainTextResponse(
                "CSRF check failed: missing Origin or Referer",
                status_code=403,
            )

        # Validate against allowed origins
        allowed = self._config.cors_origins
        # If permissive ("*"), allow any legitimate Origin/Referer
        if allowed == ["*"]:
            return await call_next(request)

        source = origin or referer or ""
        if not self._is_allowed_origin(source, allowed):
            return PlainTextResponse(
                "CSRF check failed: untrusted origin",
                status_code=403,
            )

        return await call_next(request)

    @staticmethod
    def _is_allowed_origin(source: str, allowed: list[str]) -> bool:
        for a in allowed:
            if source.startswith(a):
                return True
        return False


# ---------------------------------------------------------------------------
# Rate limiter (in-memory sliding window)
# ---------------------------------------------------------------------------


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding-window rate limiter.

    Tracks request counts per IP address.  When a limit is exceeded,
    returns ``429 Too Many Requests``.

    Login endpoint gets a stricter limit (``login_rate_limit_requests`` per
    ``login_rate_limit_window_seconds``).  All other routes share the
    general limit.

    Because state is in-process memory, limits reset on server restart.
    """

    def __init__(self, app: ASGIApp, config: AppConfig) -> None:
        super().__init__(app)
        self._config = config
        self._windows: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self._config.rate_limit_enabled:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        is_login = request.url.path == "/api/auth/login" and request.method == "POST"
        limit = (
            self._config.login_rate_limit_requests
            if is_login
            else self._config.rate_limit_requests
        )
        window = (
            self._config.login_rate_limit_window_seconds
            if is_login
            else self._config.rate_limit_window_seconds
        )

        window_key = f"{client_ip}:{'login' if is_login else 'general'}"
        timestamps = self._windows[window_key]

        # Prune expired entries
        cutoff = now - window
        self._windows[window_key] = [t for t in timestamps if t > cutoff]

        if len(self._windows[window_key]) >= limit:
            return PlainTextResponse(
                "Too Many Requests",
                status_code=429,
                headers={"Retry-After": str(int(window))},
            )

        self._windows[window_key].append(now)
        return await call_next(request)
