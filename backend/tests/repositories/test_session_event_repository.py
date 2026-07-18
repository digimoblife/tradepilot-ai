import uuid
from datetime import datetime, timezone

import pytest

from app.models.session_event import SessionEvent
from app.models.enums import SessionEventType
from app.repositories.session_event import SessionEventRepository


@pytest.mark.database
async def test_add_and_retrieve(session, data):
    repo = SessionEventRepository(session)
    event = SessionEvent(
        session_id=data.session_a,
        event_type=SessionEventType.SESSION_CREATED,
        occurred_at=datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc),
    )
    saved = await repo.add(event)
    assert saved.id is not None


@pytest.mark.database
async def test_get_by_id_for_user_owner(session, data):
    repo = SessionEventRepository(session)
    event = SessionEvent(
        session_id=data.session_a,
        event_type=SessionEventType.SESSION_CREATED,
        occurred_at=datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc),
    )
    saved = await repo.add(event)
    found = await repo.get_by_id_for_user(saved.id, data.user_a)
    assert found is not None
    assert found.id == saved.id


@pytest.mark.database
async def test_get_by_id_for_user_wrong_owner(session, data):
    repo = SessionEventRepository(session)
    event = SessionEvent(
        session_id=data.session_a,
        event_type=SessionEventType.SESSION_CREATED,
        occurred_at=datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc),
    )
    saved = await repo.add(event)
    found = await repo.get_by_id_for_user(saved.id, data.user_b)
    assert found is None


@pytest.mark.database
async def test_chronological_ordering(session, data):
    repo = SessionEventRepository(session)
    types = [
        SessionEventType.SESSION_CREATED,
        SessionEventType.EVIDENCE_UPLOADED,
        SessionEventType.ANALYSIS_REQUESTED,
    ]
    for i, et in enumerate(types):
        event = SessionEvent(
            session_id=data.session_a,
            event_type=et,
            occurred_at=datetime(2026, 7, 18, 9 + i, 0, 0, tzinfo=timezone.utc),
        )
        await repo.add(event)
    events = await repo.list_for_session_for_user(data.session_a, data.user_a)
    assert len(events) == 3
    assert events[0].event_type == SessionEventType.SESSION_CREATED


@pytest.mark.database
async def test_equal_timestamp_tie_breaker(session, data):
    repo = SessionEventRepository(session)
    ts = datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc)
    e2 = SessionEvent(
        id=uuid.uuid4(), session_id=data.session_a,
        event_type=SessionEventType.ANALYSIS_REQUESTED, occurred_at=ts,
    )
    e1 = SessionEvent(
        id=uuid.uuid4(), session_id=data.session_a,
        event_type=SessionEventType.EVIDENCE_UPLOADED, occurred_at=ts,
    )
    await repo.add(e2)
    await repo.add(e1)
    events = await repo.list_for_session_for_user(data.session_a, data.user_a)
    assert len(events) == 2
    ids = [e.id for e in events]
    assert ids == sorted(ids)


@pytest.mark.database
async def test_action_analysis_references(session, data):
    repo = SessionEventRepository(session)
    event = SessionEvent(
        session_id=data.session_a,
        event_type=SessionEventType.ANALYSIS_ACCEPTED,
        occurred_at=datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
        related_action_id=data.trade_action_a,
        related_analysis_id=data.analysis_a,
    )
    saved = await repo.add(event)
    found = await repo.get_by_id_for_user(saved.id, data.user_a)
    assert found is not None
    assert found.related_action_id == data.trade_action_a
    assert found.related_analysis_id == data.analysis_a


@pytest.mark.database
async def test_no_mutation(session, data):
    repo = SessionEventRepository(session)
    event = SessionEvent(
        session_id=data.session_a,
        event_type=SessionEventType.SESSION_CREATED,
        occurred_at=datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc),
    )
    saved = await repo.add(event)
    found = await repo.get_by_id_for_user(saved.id, data.user_a)
    assert found is not None
    assert found.event_type == SessionEventType.SESSION_CREATED
