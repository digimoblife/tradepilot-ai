import os

import pytest
from sqlalchemy import text

from app.config import AppConfig
from app.database.session import (
    create_async_engine_from_config,
    create_async_session_factory,
)

_DEFAULT_TEST_URL = "postgresql+asyncpg://tradepilot:change_me@localhost:5432/tradepilot_test"


@pytest.fixture
def config() -> AppConfig:
    return AppConfig(
        database_url=os.environ.get("TEST_DATABASE_URL", _DEFAULT_TEST_URL),
    )


@pytest.mark.database
async def test_async_engine_can_connect(config: AppConfig) -> None:
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar_one() == 1
    await engine.dispose()


@pytest.mark.database
async def test_session_factory_returns_async_session(config: AppConfig) -> None:
    engine = create_async_engine_from_config(config)
    factory = create_async_session_factory(engine)
    async with factory() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1
    await engine.dispose()


@pytest.mark.database
async def test_session_closes_reliably(config: AppConfig) -> None:
    engine = create_async_engine_from_config(config)
    factory = create_async_session_factory(engine)
    async with factory() as session:
        await session.execute(text("SELECT 1"))
    await engine.dispose()


@pytest.mark.database
async def test_rollback_removes_data(config: AppConfig) -> None:
    import asyncpg

    conn1 = await asyncpg.connect(
        host="postgres",
        port=5432,
        user="tradepilot",
        password="change_me",
        database="tradepilot_test",
    )
    await conn1.execute("CREATE TEMPORARY TABLE test_rollback (id INT PRIMARY KEY)")
    await conn1.execute("INSERT INTO test_rollback (id) VALUES (42)")
    row = await conn1.fetchrow("SELECT id FROM test_rollback")
    assert row[0] == 42
    await conn1.close()

    conn2 = await asyncpg.connect(
        host="postgres",
        port=5432,
        user="tradepilot",
        password="change_me",
        database="tradepilot_test",
    )
    result = await conn2.fetchval(
        "SELECT EXISTS ("
        "  SELECT FROM information_schema.tables "
        "  WHERE table_name = 'test_rollback'"
        ")"
    )
    assert result is False
    await conn2.close()


@pytest.mark.database
async def test_exception_triggers_rollback(config: AppConfig) -> None:
    engine = create_async_engine_from_config(config)
    factory = create_async_session_factory(engine)

    async with factory() as session:
        await session.execute(text("CREATE TEMPORARY TABLE test_exc (id INT PRIMARY KEY)"))
        await session.execute(text("INSERT INTO test_exc (id) VALUES (1)"))
        await session.rollback()

        result = await session.execute(
            text(
                "SELECT EXISTS ("
                "  SELECT FROM information_schema.tables "
                "  WHERE table_name = 'test_exc'"
                ")"
            )
        )
        assert result.scalar_one() is False

    await engine.dispose()


@pytest.mark.database
async def test_engine_disposal_works(config: AppConfig) -> None:
    engine = create_async_engine_from_config(config)
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    await engine.dispose()

    assert True
