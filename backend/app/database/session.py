from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import AppConfig


def create_async_engine_from_config(config: AppConfig) -> AsyncEngine:
    return create_async_engine(
        config.database_url,
        pool_size=config.db_pool_size,
        max_overflow=config.db_max_overflow,
        pool_timeout=config.db_pool_timeout_seconds,
        pool_recycle=config.db_pool_recycle_seconds,
        echo=config.db_echo,
        # ssl=False is safe for local Docker PostgreSQL without TLS.
        # For production, derive ssl mode from configuration or remove to
        # use the asyncpg default (prefer).
        connect_args={"ssl": False},
    )


def create_async_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    assert _engine is not None, "Engine not initialised. Call init_database first."
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    assert _session_factory is not None, (
        "Session factory not initialised. Call init_database first."
    )
    return _session_factory


def init_database(config: AppConfig) -> None:
    global _engine, _session_factory
    _engine = create_async_engine_from_config(config)
    _session_factory = create_async_session_factory(_engine)


async def dispose_database_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None


async def get_database_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
