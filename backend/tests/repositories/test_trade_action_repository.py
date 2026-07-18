from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.trade_action import TradeAction
from app.repositories.trade_action import TradeActionRepository


@pytest.mark.database
async def test_add_and_retrieve(session, data):
    repo = TradeActionRepository(session)
    action = TradeAction(
        session_id=data.session_a,
        action_type="POSITION_OPENED",
        confirmed_at=datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
        idempotency_key="ta-001",
    )
    saved = await repo.add(action)
    assert saved.id is not None


@pytest.mark.database
async def test_get_by_id_for_user_owner(session, data):
    repo = TradeActionRepository(session)
    found = await repo.get_by_id_for_user(data.trade_action_a, data.user_a)
    assert found is not None
    assert found.id == data.trade_action_a


@pytest.mark.database
async def test_get_by_id_for_user_wrong_owner(session, data):
    repo = TradeActionRepository(session)
    found = await repo.get_by_id_for_user(data.trade_action_a, data.user_b)
    assert found is None


@pytest.mark.database
async def test_idempotency_lookup(session, data):
    repo = TradeActionRepository(session)
    action = TradeAction(
        session_id=data.session_a,
        action_type="STOP_LOSS_CONFIRMED",
        confirmed_at=datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
        idempotency_key="idem-test",
    )
    await repo.add(action)
    found = await repo.get_by_idempotency_key_for_user(data.session_a, data.user_a, "idem-test")
    assert found is not None


@pytest.mark.database
async def test_idempotency_lookup_wrong_user(session, data):
    repo = TradeActionRepository(session)
    action = TradeAction(
        session_id=data.session_a,
        action_type="STOP_LOSS_CONFIRMED",
        confirmed_at=datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
        idempotency_key="idem-user-x",
    )
    await repo.add(action)
    found = await repo.get_by_idempotency_key_for_user(data.session_a, data.user_b, "idem-user-x")
    assert found is None


@pytest.mark.database
async def test_deterministic_history(session, data):
    repo = TradeActionRepository(session)
    for i in range(3):
        action = TradeAction(
            session_id=data.session_a,
            action_type="POSITION_OPENED",
            confirmed_at=datetime(2026, 7, 18, 9 + i, 0, 0, tzinfo=timezone.utc),
            idempotency_key=f"hist-{i}",
        )
        await repo.add(action)
    actions = await repo.list_for_session_for_user(data.session_a, data.user_a)
    assert len(actions) == 4  # includes seed action_a
    times = [a.confirmed_at for a in actions]
    assert times == sorted(times)


@pytest.mark.database
async def test_duplicate_key_error_propagates(session, data):
    repo = TradeActionRepository(session)
    action1 = TradeAction(
        session_id=data.session_a,
        action_type="POSITION_OPENED",
        confirmed_at=datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
        idempotency_key="dup-err",
    )
    await repo.add(action1)
    action2 = TradeAction(
        session_id=data.session_a,
        action_type="STOP_LOSS_CONFIRMED",
        confirmed_at=datetime(2026, 7, 18, 11, 0, 0, tzinfo=timezone.utc),
        idempotency_key="dup-err",
    )
    with pytest.raises(IntegrityError):
        await repo.add(action2)


@pytest.mark.database
async def test_no_commit(session, data):
    repo = TradeActionRepository(session)
    found = await repo.get_by_id_for_user(data.trade_action_a, data.user_a)
    assert found is not None
