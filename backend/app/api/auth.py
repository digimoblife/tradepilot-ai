"""Authentication routes (TP-1001)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    clear_session_cookie,
    get_current_user,
    set_session_cookie,
)
from app.auth import (
    AuthenticatedUser,
    AuthenticationService,
)
from app.config import AppConfig
from app.database.session import get_db_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    id: str
    email: str


class MeResponse(BaseModel):
    id: str
    email: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db_session: AsyncSession = Depends(get_db_session),
) -> LoginResponse:
    """Authenticate with email and password.

    Sets an HTTP-only session cookie on success.
    """
    svc = AuthenticationService(db_session)
    result = await svc.authenticate(email=body.email, password=body.password)

    set_session_cookie(response, result.raw_token)

    return LoginResponse(id=str(result.user.id), email=result.user.email)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db_session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Revoke the current session and clear the cookie."""
    _cfg = AppConfig()
    raw_token: str | None = request.cookies.get(_cfg.auth_cookie_name)
    if raw_token:
        svc = AuthenticationService(db_session)
        await svc.revoke_session(raw_token=raw_token)

    clear_session_cookie(response)
    return {"status": "ok"}


@router.get("/me", response_model=MeResponse)
async def me(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> MeResponse:
    """Return the currently authenticated user's identity."""
    return MeResponse(id=str(current_user.id), email=current_user.email)
