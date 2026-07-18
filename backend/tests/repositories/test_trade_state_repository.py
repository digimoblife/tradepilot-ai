import uuid

import pytest

from app.models.trade_state import TradeState
from app.repositories.trade_state import TradeStateRepository


@pytest.mark.database
async def test_add_and_flush(session, session_a):
    repo = TradeStateRepository(session)
    state = TradeState(session_id=session_a)
    saved = await repo.add(state)
    assert saved.id is not None


@pytest.mark.database
async def test_get_for_user_owner(session, session_a, user_a, state_a):
    repo = TradeStateRepository(session)
    found = await repo.get_for_user(session_a, user_a)
    assert found is not None
    assert found.session_id == session_a


@pytest.mark.database
async def test_get_for_user_wrong_owner(session, session_a, user_b):
    repo = TradeStateRepository(session)
    found = await repo.get_for_user(session_a, user_b)
    assert found is None


@pytest.mark.database
async def test_get_for_user_for_update_owner(
    session, session_a, user_a, state_a
):
    repo = TradeStateRepository(session)
    found = await repo.get_for_user_for_update(session_a, user_a)
    assert found is not None
    assert found.session_id == session_a


@pytest.mark.database
async def test_get_for_user_for_update_wrong_owner(
    session, session_a, user_b
):
    repo = TradeStateRepository(session)
    found = await repo.get_for_user_for_update(session_a, user_b)
    assert found is None


@pytest.mark.database
async def test_unknown_session_returns_none(
    session, user_a
):
    repo = TradeStateRepository(session)
    found = await repo.get_for_user(uuid.uuid4(), user_a)
    assert found is None


@pytest.mark.database
async def test_no_mutation(session, session_a, user_a, state_a):
    repo = TradeStateRepository(session)
    found = await repo.get_for_user(session_a, user_a)
    assert found is not None
    # State version should remain unchanged by a read
    from sqlalchemy import text
    result = await session.execute(
        text("SELECT state_version FROM trade_states WHERE id = :id"),
        {"id": state_a},
    )
    row = result.first()
    assert row is not None
    assert row[0] == 1
