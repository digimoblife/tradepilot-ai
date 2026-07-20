"""User repository (TP-1001)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.unique().scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        from app.models.user import normalize_email

        normalized = normalize_email(email)
        result = await self._session.execute(select(User).where(User.email == normalized))
        return result.unique().scalar_one_or_none()
