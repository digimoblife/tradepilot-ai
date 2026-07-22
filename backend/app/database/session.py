"""Database session factory and FastAPI dependency (TP-1001)."""

from __future__ import annotations

from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import AppConfig

_engine = None
_session_factory = None


def _get_engine(config: AppConfig) -> Any:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            config.database_url,
            pool_size=config.db_pool_size,
            max_overflow=config.db_max_overflow,
            pool_recycle=config.db_pool_recycle_seconds,
            echo=config.db_echo,
        )
    return _engine


def get_engine() -> Any:
    """Return the shared async engine, creating it on first call."""
    return _get_engine(AppConfig())


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    global _session_factory
    if _session_factory is None:
        config = AppConfig()
        engine = _get_engine(config)
        _session_factory = async_sessionmaker(
            bind=engine, class_=AsyncSession, expire_on_commit=False
        )
    async with _session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
