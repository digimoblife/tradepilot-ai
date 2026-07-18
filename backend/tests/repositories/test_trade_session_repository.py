import pytest
from sqlalchemy import text

from app.models.trade_session import TradeSession
from app.repositories.trade_session import TradeSessionRepository


@pytest.mark.database
async def test_add_and_flush(session, data):
    repo = TradeSessionRepository(session)
    ts = TradeSession(owner_id=data.user_a, ticker="BBCA")
    saved = await repo.add(ts)
    assert saved.id is not None
    assert saved.ticker == "BBCA"


@pytest.mark.database
async def test_get_by_id_for_user_owner(session, data):
    repo = TradeSessionRepository(session)
    found = await repo.get_by_id_for_user(data.session_a, data.user_a)
    assert found is not None
    assert found.id == data.session_a


@pytest.mark.database
async def test_get_by_id_for_user_wrong_owner(session, data):
    repo = TradeSessionRepository(session)
    found = await repo.get_by_id_for_user(data.session_a, data.user_b)
    assert found is None


@pytest.mark.database
async def test_list_for_user_contains_only_owner(session, data):
    repo = TradeSessionRepository(session)
    rows = await repo.list_for_user(data.user_a)
    ids = {r.id for r in rows}
    assert data.session_a in ids
    assert data.session_b not in ids


@pytest.mark.database
async def test_list_for_user_deterministic_order(session, data):
    repo = TradeSessionRepository(session)
    ts1 = TradeSession(owner_id=data.user_a, ticker="A")
    ts2 = TradeSession(owner_id=data.user_a, ticker="B")
    await repo.add(ts1)
    await repo.add(ts2)
    rows = await repo.list_for_user(data.user_a)
    assert len(rows) >= 2


@pytest.mark.database
async def test_get_by_id_for_user_for_update_owner(session, data):
    repo = TradeSessionRepository(session)
    found = await repo.get_by_id_for_user_for_update(data.session_a, data.user_a)
    assert found is not None
    assert found.id == data.session_a


@pytest.mark.database
async def test_get_by_id_for_user_for_update_wrong_owner(session, data):
    repo = TradeSessionRepository(session)
    found = await repo.get_by_id_for_user_for_update(data.session_a, data.user_b)
    assert found is None


@pytest.mark.database
async def test_no_commit(session, data):
    repo = TradeSessionRepository(session)
    found = await repo.get_by_id_for_user(data.session_a, data.user_a)
    assert found is not None


@pytest.mark.database
async def test_exists_for_user(session, data):
    repo = TradeSessionRepository(session)
    assert await repo.exists_for_user(data.session_a, data.user_a) is True
    assert await repo.exists_for_user(data.session_a, data.user_b) is False
