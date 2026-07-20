"""Centralized FastAPI exception handlers (TP-1007)."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.errors import (
    INTERNAL_ERROR,
    VALIDATION_ERROR,
    get_error_message,
    status_code_for,
)
from app.api.schemas.errors import ErrorDetail, ErrorResponse


def _safe_message(exc: Exception, code: str) -> str:
    """Return a safe user-facing message, preferring Indonesian."""
    msg = getattr(exc, "message", None)
    if msg and isinstance(msg, str):
        # Strip any [CODE] prefix from the service error
        if msg.startswith("[") and "]" in msg:
            msg = msg.split("]", 1)[1].strip()
        if msg:
            return msg
    return get_error_message(code)


def _make_response(
    status: int, code: str, message: str, details: list[dict[str, object]] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=ErrorResponse(
            error=ErrorDetail(code=code, message=message, details=details),
        ).model_dump(),
    )


def register_handlers(app: FastAPI) -> None:
    """Register all unified exception handlers."""

    # ------------------------------------------------------------------
    # AuthenticationError
    # ------------------------------------------------------------------
    from app.auth.errors import AuthenticationError

    @app.exception_handler(AuthenticationError)
    async def auth_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
        code = exc.code or "AUTHENTICATION_REQUIRED"
        msg = _safe_message(exc, code)
        return _make_response(status_code_for(code), code, msg)

    # ------------------------------------------------------------------
    # RequestValidationError
    # ------------------------------------------------------------------
    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        details: list[dict[str, object]] = []
        for err in exc.errors():
            loc = err.get("loc", [])
            field = ".".join(str(p) for p in loc) if loc else ""
            inp = err.get("input")
            details.append({
                "field": field,
                "code": err.get("type", "value_error"),
                "message": (
                    err.get("msg", "Nilai tidak valid.")
                    if not _looks_secret(inp) else "Nilai tidak valid."
                ),
            })
        return _make_response(422, VALIDATION_ERROR, get_error_message(VALIDATION_ERROR), details)

    # ------------------------------------------------------------------
    # HTTPException (raised by route code for 404, 409, etc.)
    # ------------------------------------------------------------------
    @app.exception_handler(HTTPException)
    async def http_handler(request: Request, exc: HTTPException) -> JSONResponse:
        code = INTERNAL_ERROR
        detail = exc.detail
        if isinstance(detail, dict):
            code = detail.get("code", INTERNAL_ERROR)
            msg = detail.get("message", get_error_message(code))
        elif isinstance(detail, str):
            msg = detail
        else:
            msg = get_error_message(INTERNAL_ERROR)
        return _make_response(exc.status_code, code, msg)

    # ------------------------------------------------------------------
    # Generic Exception (domain service errors fall through here)
    # ------------------------------------------------------------------
    @app.exception_handler(Exception)
    async def general_handler(request: Request, exc: Exception) -> JSONResponse:
        code = getattr(exc, "code", INTERNAL_ERROR)
        if not isinstance(code, str) or not code:
            code = INTERNAL_ERROR
        msg = _safe_message(exc, code)
        status = status_code_for(code)
        if code == INTERNAL_ERROR or status == 500:
            status = 500
            msg = get_error_message(INTERNAL_ERROR)
        return _make_response(status, code, msg)


def _looks_secret(value: object) -> bool:
    """Check if a value looks like a secret that should not be echoed."""
    if isinstance(value, str) and len(value) > 20 and not value.isprintable():
        return True
    return False
