import uuid
from datetime import datetime, timezone

import pytest

from app.models.session_event import SessionEvent
from app.repositories.session_event import SessionEventRepository
from app.models.enums import SessionEventType


@pytest.mark.database
async def test_add_and_retrieve(session, session_a, user_a):
    repo = SessionEventRepository(session)
    event = SessionEvent(
        session_id=session_a,
        event_type=SessionEventType.SESSION_CREATED,
        occurred_at=datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc),
    )
    saved = await repo.add(event)
    assert saved.id is not None


@pytest.mark.database
async def test_get_by_id_for_user_owner(
    session, session_a, user_a
):
    repo = SessionEventRepository(session)
    event = SessionEvent(
        session_id=session_a,
        event_type=SessionEventType.SESSION_CREATED,
        occurred_at=datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc),
    )
    saved = await repo.add(event)
    found = await repo.get_by_id_for_user(saved.id, user_a)
    assert found is not None
    assert found.id == saved.id


@pytest.mark.database
async def test_get_by_id_for_user_wrong_owner(
    session, session_a, user_a, user_b
):
    repo = SessionEventRepository(session)
    event = SessionEvent(
        session_id=session_a,
        event_type=SessionEventType.SESSION_CREATED,
        occurred_at=datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc),
    )
    saved = await repo.add(event)
    found = await repo.get_by_id_for_user(saved.id, user_b)
    assert found is None


@pytest.mark.database
async def test_chronological_ordering(
    session, session_a, user_a
):
    repo = SessionEventRepository(session)
    for i, et in enumerate(
        [SessionEventType.SESSION_CREATED, SessionEventType.EVIDENCE_UPLOADED, SessionEventType.ANALYSIS_REQUESTED]
    ):
        event = SessionEvent(
            session_id=session_a,
            event_type=et,
            occurred_at=datetime(2026, 7, 18, 9 + i, 0, 0, tzinfo=timezone.utc),
        )
        await repo.add(event)
    events = await repo.list_for_session_for_user(session_a, user_a)
    assert len(events) == 3
    assert events[0].event_type == SessionEventType.SESSION_CREATED
    assert events[2].event_type == SessionEventType.ANALYSIS_REQUESTED


@pytest.mark.database
async def test_equal_timestamp_tie_breaker(
    session, session_a, user_a
):
    repo = SessionEventRepository(session)
    ts = datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc)
    e1 = SessionEvent(
        id=uuid.uuid4(),
        session_id=session_a,
        event_type=SessionEventType.EVIDENCE_UPLOADED,
        occurred_at=ts,
    )
    e2 = SessionEvent(
        id=uuid.uuid4(),
        session_id=session_a,
        event_type=SessionEventType.ANALYSIS_REQUESTED,
        occurred_at=ts,
    )
    # Insert e2 first, e1 second to test that ordering by id works
    await repo.add(e2)
    await repo.add(e1)
    events = await repo.list_for_session_for_user(session_a, user_a)
    assert len(events) == 2
    # With same timestamp, ordering is by id
    ids = [e.id for e in events]
    assert ids == sorted(ids)


@pytest.mark.database
async def test_action_analysis_references(
    session, session_a, user_a, action_a, analysis_a
):
    repo = SessionEventRepository(session)
    event = SessionEvent(
        session_id=session_a,
        event_type=SessionEventType.ANALYSIS_ACCEPTED,
        occurred_at=datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
        related_action_id=action_a,
        related_analysis_id=analysis_a,
    )
    saved = await repo.add(event)
    found = await repo.get_by_id_for_user(saved.id, user_a)
    assert found is not None
    assert found.related_action_id == action_a
    assert found.related_analysis_id == analysis_a


@pytest.mark.database
async def test_no_mutation(session, session_a, user_a):
    repo = SessionEventRepository(session)
    event = SessionEvent(
        session_id=session_a,
        event_type=SessionEventType.SESSION_CREATED,
        occurred_at=datetime(2026, 7, 18, 9, 0, 0, tzinfo=timezone.utc),
    )
    saved = await repo.add(event)
    found = await repo.get_by_id_for_user(saved.id, user_a)
    assert found is not None
    # Repository did not change event type
    assert found.event_type == SessionEventType.SESSION_CREATED
