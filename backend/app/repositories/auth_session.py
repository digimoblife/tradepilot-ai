"""Auth session repository (TP-1001)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.sessions import AuthSession, hash_token


class AuthSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, entity: AuthSession) -> AuthSession:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def get_by_token(self, raw_token: str) -> AuthSession | None:
        token_hash = hash_token(raw_token)
        result = await self._session.execute(
            select(AuthSession).where(AuthSession.token_hash == token_hash)
        )
        return result.unique().scalar_one_or_none()

    async def get_by_user_id(self, user_id: uuid.UUID, *, limit: int = 10) -> list[AuthSession]:
        result = await self._session.execute(
            select(AuthSession)
            .where(AuthSession.user_id == user_id)
            .order_by(AuthSession.created_at.desc())
            .limit(limit)
        )
        return list(result.unique().scalars().all())

    async def revoke(self, session: AuthSession) -> None:
        from app.auth.sessions import SessionStore

        SessionStore.revoke(session)
        await self._session.flush()
