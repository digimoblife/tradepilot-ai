import os
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import Column, Integer, MetaData, Table

from app.config import AppConfig
from app.database.session import create_async_engine_from_config
from app.database.types import (
    monetary_numeric,
    percentage_numeric,
    pg_uuid,
    price_numeric,
    utc_datetime,
)

_DEFAULT_TEST_URL = "postgresql+asyncpg://tradepilot:change_me@localhost:5432/tradepilot_test"


@pytest.fixture
def config() -> AppConfig:
    return AppConfig(
        database_url=os.environ.get("TEST_DATABASE_URL", _DEFAULT_TEST_URL),
    )


@pytest.mark.database
async def test_uuid_round_trip(config: AppConfig) -> None:
    engine = create_async_engine_from_config(config)
    meta = MetaData()
    t = Table(
        "test_uuid",
        meta,
        Column("id", pg_uuid(), primary_key=True),
        prefixes=["TEMPORARY"],
    )
    async with engine.begin() as conn:
        await conn.run_sync(meta.create_all)
        uid = uuid.uuid4()
        await conn.execute(t.insert().values(id=uid))
        row = (await conn.execute(t.select())).first()
        assert row is not None
        assert isinstance(row.id, uuid.UUID)
        assert row.id == uid
    await engine.dispose()


@pytest.mark.database
async def test_utc_datetime_round_trip(config: AppConfig) -> None:
    engine = create_async_engine_from_config(config)
    meta = MetaData()
    t = Table(
        "test_ts",
        meta,
        Column("id", Integer, primary_key=True),
        Column("ts", utc_datetime()),
        prefixes=["TEMPORARY"],
    )
    async with engine.begin() as conn:
        await conn.run_sync(meta.create_all)
        now = datetime.now(timezone.utc)
        await conn.execute(t.insert().values(id=1, ts=now))
        row = (await conn.execute(t.select())).first()
        assert row is not None
        assert isinstance(row.ts, datetime)
        assert row.ts == now
    await engine.dispose()


@pytest.mark.database
async def test_naive_datetime_converted_to_utc(config: AppConfig) -> None:
    engine = create_async_engine_from_config(config)
    meta = MetaData()
    t = Table(
        "test_naive",
        meta,
        Column("id", Integer, primary_key=True),
        Column("ts", utc_datetime()),
        prefixes=["TEMPORARY"],
    )
    async with engine.begin() as conn:
        await conn.run_sync(meta.create_all)
        naive = datetime(2026, 7, 17, 12, 0, 0)
        await conn.execute(t.insert().values(id=1, ts=naive))
        row = (await conn.execute(t.select())).first()
        assert row is not None
        assert row.ts.tzinfo is not None
    await engine.dispose()


@pytest.mark.database
async def test_price_numeric_round_trip(config: AppConfig) -> None:
    engine = create_async_engine_from_config(config)
    meta = MetaData()
    t = Table(
        "test_price",
        meta,
        Column("id", Integer, primary_key=True),
        Column("price", price_numeric()),
        prefixes=["TEMPORARY"],
    )
    from decimal import Decimal

    async with engine.begin() as conn:
        await conn.run_sync(meta.create_all)
        val = Decimal("2910.50")
        await conn.execute(t.insert().values(id=1, price=val))
        row = (await conn.execute(t.select())).first()
        assert row is not None
        assert isinstance(row.price, Decimal)
        assert row.price == val
    await engine.dispose()


@pytest.mark.database
async def test_monetary_numeric_round_trip(config: AppConfig) -> None:
    engine = create_async_engine_from_config(config)
    meta = MetaData()
    t = Table(
        "test_monetary",
        meta,
        Column("id", Integer, primary_key=True),
        Column("amount", monetary_numeric()),
        prefixes=["TEMPORARY"],
    )
    from decimal import Decimal

    async with engine.begin() as conn:
        await conn.run_sync(meta.create_all)
        val = Decimal("11000.00")
        await conn.execute(t.insert().values(id=1, amount=val))
        row = (await conn.execute(t.select())).first()
        assert row is not None
        assert isinstance(row.amount, Decimal)
        assert row.amount == val
    await engine.dispose()


@pytest.mark.database
async def test_percentage_numeric_precision(config: AppConfig) -> None:
    engine = create_async_engine_from_config(config)
    meta = MetaData()
    t = Table(
        "test_pct",
        meta,
        Column("id", Integer, primary_key=True),
        Column("pct", percentage_numeric()),
        prefixes=["TEMPORARY"],
    )
    from decimal import Decimal

    async with engine.begin() as conn:
        await conn.run_sync(meta.create_all)
        val = Decimal("12.3456")
        await conn.execute(t.insert().values(id=1, pct=val))
        row = (await conn.execute(t.select())).first()
        assert row is not None
        assert isinstance(row.pct, Decimal)
        assert row.pct == val
    await engine.dispose()
