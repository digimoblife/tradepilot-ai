# ruff: noqa: E501
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.config import AppConfig
from app.database.session import create_async_engine_from_config
from app.models.enums import PositionStatus, ThesisStatus
from app.models.trade_state import TradeState

_DEFAULT_URL = (
    "postgresql+asyncpg://tradepilot:change_me@localhost:5432/tradepilot_test"
)


@pytest.fixture
def db_url() -> str:
    return os.environ.get("TEST_DATABASE_URL", _DEFAULT_URL)


async def _make_user_and_session(
    engine: AsyncEngine,
    label: str,
) -> tuple[uuid.UUID, uuid.UUID]:
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM session_events"))
        await conn.execute(text("DELETE FROM context_summaries"))
        await conn.execute(text("DELETE FROM validation_attempts"))
        await conn.execute(text("DELETE FROM provider_responses"))
        await conn.execute(text("DELETE FROM provider_requests"))
        await conn.execute(text("DELETE FROM trade_actions"))
        await conn.execute(text("DELETE FROM analyses"))
        await conn.execute(text("DELETE FROM analysis_jobs"))
        await conn.execute(text("DELETE FROM evidence"))
        await conn.execute(text("DELETE FROM trade_states"))
        await conn.execute(text("DELETE FROM trade_sessions"))
        await conn.execute(text("DELETE FROM users"))
    async with engine.begin() as conn:
        user_r = (
            await conn.execute(
                text(
                    "INSERT INTO users (email, password_hash) "
                    "VALUES (:e, :p) RETURNING id"
                ),
                {"e": f"{label}_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
            )
        ).first()
        assert user_r is not None
        uid: uuid.UUID = user_r[0]
        sess_r = (
            await conn.execute(
                text(
                    "INSERT INTO trade_sessions (owner_id, ticker) "
                    "VALUES (:uid, :t) RETURNING id"
                ),
                {"uid": uid, "t": "BBRI"},
            )
        ).first()
        assert sess_r is not None
        sid: uuid.UUID = sess_r[0]
    return uid, sid


@pytest.mark.database
async def test_defaults() -> None:
    ts = TradeState()
    assert ts.position_status == PositionStatus.NOT_OPENED
    assert ts.thesis_status == ThesisStatus.INTACT
    assert ts.state_version == 1


@pytest.mark.database
async def test_not_opened_can_be_stored(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "no")
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO trade_states (session_id) VALUES (:sid)"),
            {"sid": sid},
        )
    await engine.dispose()


@pytest.mark.database
async def test_open_state_representation(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "open")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO trade_states ("
                "  session_id, position_status, entry_price, entry_at,"
                "  original_quantity, remaining_quantity,"
                "  active_stop_loss, active_target"
                ") VALUES (:sid, :ps, :ep, :ea, :oq, :rq, :sl, :tg)"
            ),
            {
                "sid": sid,
                "ps": "OPEN",
                "ep": Decimal("3090.50"),
                "ea": datetime(2026, 7, 17, 9, 0, 0, tzinfo=timezone.utc),
                "oq": Decimal("10000"),
                "rq": Decimal("10000"),
                "sl": Decimal("2840"),
                "tg": Decimal("3250"),
            },
        )
        row = (
            await conn.execute(
                text(
                    "SELECT position_status, entry_price, original_quantity "
                    "FROM trade_states WHERE session_id = :sid"
                ),
                {"sid": sid},
            )
        ).first()
        assert row is not None
        assert row[0] == "OPEN"
        assert row[1] == Decimal("3090.50")
        assert row[2] == Decimal("10000")
    await engine.dispose()


@pytest.mark.database
async def test_partially_closed_representation(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "pc")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO trade_states ("
                "  session_id, position_status, entry_price,"
                "  original_quantity, remaining_quantity,"
                "  average_exit_price, realized_pnl"
                ") VALUES (:sid, :ps, :ep, :oq, :rq, :aep, :pnl)"
            ),
            {
                "sid": sid,
                "ps": "PARTIALLY_CLOSED",
                "ep": Decimal("3090"),
                "oq": Decimal("10000"),
                "rq": Decimal("5000"),
                "aep": Decimal("3250"),
                "pnl": Decimal("800000"),
            },
        )
    await engine.dispose()


@pytest.mark.database
async def test_closed_state_representation(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "cl")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO trade_states ("
                "  session_id, position_status, entry_price,"
                "  original_quantity, remaining_quantity,"
                "  average_exit_price, realized_pnl, realized_return"
                ") VALUES (:sid, :ps, :ep, :oq, :rq, :aep, :pnl, :ret)"
            ),
            {
                "sid": sid,
                "ps": "CLOSED",
                "ep": Decimal("3090"),
                "oq": Decimal("10000"),
                "rq": Decimal("0"),
                "aep": Decimal("3130"),
                "pnl": Decimal("400000"),
                "ret": Decimal("12.94"),
            },
        )
    await engine.dispose()


@pytest.mark.database
async def test_one_state_per_session(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "one")
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO trade_states (session_id) VALUES (:sid)"),
            {"sid": sid},
        )
        with pytest.raises(Exception):
            await conn.execute(
                text("INSERT INTO trade_states (session_id) VALUES (:sid)"),
                {"sid": sid},
            )
    await engine.dispose()


@pytest.mark.database
async def test_unknown_session_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    fake = uuid.uuid4()
    async with engine.begin() as conn:
        with pytest.raises(Exception):
            await conn.execute(
                text("INSERT INTO trade_states (session_id) VALUES (:sid)"),
                {"sid": fake},
            )
    await engine.dispose()


@pytest.mark.database
async def test_decimal_round_trip(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "dec")
    async with engine.begin() as conn:
        val = Decimal("0.1")
        await conn.execute(
            text(
                "INSERT INTO trade_states (session_id, entry_price) VALUES (:sid, :ep)"
            ),
            {"sid": sid, "ep": val},
        )
        row = (
            await conn.execute(
                text("SELECT entry_price FROM trade_states WHERE session_id = :sid"),
                {"sid": sid},
            )
        ).first()
        assert row is not None
        assert isinstance(row[0], Decimal)
        assert row[0] == val
    await engine.dispose()


@pytest.mark.database
async def test_negative_original_quantity_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "neg")
    async with engine.begin() as conn:
        with pytest.raises(Exception) as excinfo:
            await conn.execute(
                text(
                    "INSERT INTO trade_states (session_id, original_quantity) "
                    "VALUES (:sid, :oq)"
                ),
                {"sid": sid, "oq": Decimal("-1")},
            )
        assert "violates check constraint" in str(excinfo.value)
    await engine.dispose()


@pytest.mark.database
async def test_negative_remaining_quantity_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "negr")
    async with engine.begin() as conn:
        with pytest.raises(Exception) as excinfo:
            await conn.execute(
                text(
                    "INSERT INTO trade_states (session_id, original_quantity, remaining_quantity) "
                    "VALUES (:sid, :oq, :rq)"
                ),
                {"sid": sid, "oq": Decimal("100"), "rq": Decimal("-1")},
            )
        assert "violates check constraint" in str(excinfo.value)
    await engine.dispose()


@pytest.mark.database
async def test_remaining_above_original_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "rao")
    async with engine.begin() as conn:
        with pytest.raises(Exception) as excinfo:
            await conn.execute(
                text(
                    "INSERT INTO trade_states (session_id, original_quantity, remaining_quantity) "
                    "VALUES (:sid, :oq, :rq)"
                ),
                {"sid": sid, "oq": Decimal("100"), "rq": Decimal("200")},
            )
        assert "violates check constraint" in str(excinfo.value)
    await engine.dispose()


@pytest.mark.database
async def test_negative_state_version_rejected(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    _, sid = await _make_user_and_session(engine, "nsv")
    async with engine.begin() as conn:
        with pytest.raises(Exception) as excinfo:
            await conn.execute(
                text(
                    "INSERT INTO trade_states (session_id, state_version) "
                    "VALUES (:sid, :sv)"
                ),
                {"sid": sid, "sv": 0},
            )
        assert "violates check constraint" in str(excinfo.value)
    await engine.dispose()


@pytest.mark.database
async def test_model_annotations_are_decimal() -> None:
    hints = TradeState.__annotations__
    decimal_fields = [
        "entry_price",
        "original_quantity",
        "remaining_quantity",
        "active_stop_loss",
        "active_target",
        "average_exit_price",
        "realized_pnl",
        "realized_return",
    ]
    for field in decimal_fields:
        ann = hints.get(field)
        assert ann is not None, f"Missing annotation for {field}"
        assert "Decimal" in str(ann), f"{field} annotation is {ann}, expected Decimal"
    assert "float" not in str(hints.get("entry_price"))


@pytest.mark.database
async def test_exact_decimal_round_trip(db_url: str) -> None:
    config = AppConfig(database_url=db_url)
    engine = create_async_engine_from_config(config)
    vals = [
        Decimal("0.1"),
        Decimal("0.2"),
        Decimal("1234.567891"),
        Decimal("999999999999.123456"),
    ]
    for v in vals:
        _, sid = await _make_user_and_session(engine, f"edr_{v}")
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO trade_states (session_id, entry_price) "
                    "VALUES (:sid, :ep)"
                ),
                {"sid": sid, "ep": v},
            )
            row = (
                await conn.execute(
                    text(
                        "SELECT entry_price FROM trade_states WHERE session_id = :sid"
                    ),
                    {"sid": sid},
                )
            ).first()
            assert row is not None
            assert isinstance(row[0], Decimal), f"Expected Decimal, got {type(row[0])}"
            assert row[0] == v, f"Expected {v}, got {row[0]}"
    await engine.dispose()
