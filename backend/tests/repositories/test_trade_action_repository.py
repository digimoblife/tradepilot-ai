import uuid
from datetime import datetime, timezone

import pytest

from app.models.trade_action import TradeAction
from app.repositories.trade_action import TradeActionRepository


@pytest.mark.database
async def test_add_and_retrieve(session, session_a, user_a):
    repo = TradeActionRepository(session)
    action = TradeAction(
        session_id=session_a,
        action_type="POSITION_OPENED",
        confirmed_at=datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
        idempotency_key="ik-001",
    )
    saved = await repo.add(action)
    assert saved.id is not None


@pytest.mark.database
async def test_get_by_id_for_user_owner(
    session, session_a, user_a, action_a
):
    repo = TradeActionRepository(session)
    found = await repo.get_by_id_for_user(action_a, user_a)
    assert found is not None
    assert found.id == action_a


@pytest.mark.database
async def test_get_by_id_for_user_wrong_owner(
    session, action_a, user_b
):
    repo = TradeActionRepository(session)
    found = await repo.get_by_id_for_user(action_a, user_b)
    assert found is None


@pytest.mark.database
async def test_idempotency_lookup(session, session_a, user_a):
    repo = TradeActionRepository(session)
    action = TradeAction(
        session_id=session_a,
        action_type="STOP_LOSS_CONFIRMED",
        confirmed_at=datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
        idempotency_key="dup-key",
    )
    await repo.add(action)
    found = await repo.get_by_idempotency_key_for_user(
        session_a, user_a, "dup-key"
    )
    assert found is not None
    assert found.idempotency_key == "dup-key"


@pytest.mark.database
async def test_idempotency_lookup_wrong_user(
    session, session_a, user_a, user_b
):
    repo = TradeActionRepository(session)
    action = TradeAction(
        session_id=session_a,
        action_type="STOP_LOSS_CONFIRMED",
        confirmed_at=datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
        idempotency_key="dup-key-2",
    )
    await repo.add(action)
    found = await repo.get_by_idempotency_key_for_user(
        session_a, user_b, "dup-key-2"
    )
    assert found is None


@pytest.mark.database
async def test_deterministic_history(session, session_a, user_a):
    repo = TradeActionRepository(session)
    for i in range(3):
        action = TradeAction(
            session_id=session_a,
            action_type="POSITION_OPENED",
            confirmed_at=datetime(2026, 7, 18, 9 + i, 0, 0, tzinfo=timezone.utc),
            idempotency_key=f"hist-{i}",
        )
        await repo.add(action)
    actions = await repo.list_for_session_for_user(session_a, user_a)
    assert len(actions) == 3
    times = [a.confirmed_at for a in actions]
    assert times == sorted(times)


@pytest.mark.database
async def test_duplicate_key_error_propagates(
    session, session_a, user_a
):
    repo = TradeActionRepository(session)
    from sqlalchemy.exc import IntegrityError
    action1 = TradeAction(
        session_id=session_a,
        action_type="POSITION_OPENED",
        confirmed_at=datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
        idempotency_key="dup-err",
    )
    await repo.add(action1)
    action2 = TradeAction(
        session_id=session_a,
        action_type="STOP_LOSS_CONFIRMED",
        confirmed_at=datetime(2026, 7, 18, 11, 0, 0, tzinfo=timezone.utc),
        idempotency_key="dup-err",
    )
    with pytest.raises(IntegrityError):
        await repo.add(action2)


@pytest.mark.database
async def test_no_commit(session, session_a, user_a, action_a):
    repo = TradeActionRepository(session)
    found = await repo.get_by_id_for_user(action_a, user_a)
    assert found is not None
