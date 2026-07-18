import uuid
import pytest
from sqlalchemy import text

from app.models.trade_state import TradeState
from app.repositories.trade_state import TradeStateRepository


@pytest.mark.database
async def test_add_and_flush(session, data):
    repo = TradeStateRepository(session)
    state = TradeState(session_id=data.session_b)
    saved = await repo.add(state)
    assert saved.session_id == data.session_b


@pytest.mark.database
async def test_get_for_user_owner(session, data):
    repo = TradeStateRepository(session)
    found = await repo.get_for_user(data.session_a, data.user_a)
    assert found is not None
    assert found.session_id == data.session_a


@pytest.mark.database
async def test_get_for_user_wrong_owner(session, data):
    repo = TradeStateRepository(session)
    found = await repo.get_for_user(data.session_a, data.user_b)
    assert found is None


@pytest.mark.database
async def test_get_for_user_for_update_owner(session, data):
    repo = TradeStateRepository(session)
    found = await repo.get_for_user_for_update(data.session_a, data.user_a)
    assert found is not None
    assert found.session_id == data.session_a


@pytest.mark.database
async def test_get_for_user_for_update_wrong_owner(session, data):
    repo = TradeStateRepository(session)
    found = await repo.get_for_user_for_update(data.session_a, data.user_b)
    assert found is None


@pytest.mark.database
async def test_unknown_session_returns_none(session, data):
    repo = TradeStateRepository(session)
    found = await repo.get_for_user(uuid.uuid4(), data.user_a)
    assert found is None


@pytest.mark.database
async def test_no_mutation(session, data):
    repo = TradeStateRepository(session)
    found = await repo.get_for_user(data.session_a, data.user_a)
    assert found is not None
    r = await session.execute(
        text("SELECT state_version FROM trade_states WHERE session_id = :sid"),
        {"sid": data.trade_state_a},
    )
    row = r.first()
    assert row is not None
    assert row[0] == 1
