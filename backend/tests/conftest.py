"""Shared conftest for tests that require a database engine."""

from __future__ import annotations

import os
from typing import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

_DEFAULT_URL = "postgresql+asyncpg://tradepilot:change_me@localhost:5432/tradepilot_test"


@pytest.fixture(scope="session")
def db_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", _DEFAULT_URL)


@pytest.fixture(scope="session")
async def engine(db_url: str) -> AsyncIterator[AsyncEngine]:
    e = create_async_engine(db_url, poolclass=NullPool)
    yield e
    await e.dispose()
