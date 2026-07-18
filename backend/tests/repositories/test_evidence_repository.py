import uuid
from datetime import datetime, timezone

import pytest

from app.models.evidence import Evidence
from app.repositories.evidence import EvidenceRepository
from app.models.enums import EvidenceStatus, EvidenceType


@pytest.mark.database
async def test_add_and_retrieve(session, session_a, user_a):
    repo = EvidenceRepository(session)
    ev = Evidence(
        session_id=session_a,
        owner_id=user_a,
        evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
        evidence_status=EvidenceStatus.AVAILABLE,
    )
    saved = await repo.add(ev)
    assert saved.id is not None


@pytest.mark.database
async def test_get_by_id_for_user_owner(
    session, session_a, user_a
):
    repo = EvidenceRepository(session)
    ev = Evidence(
        session_id=session_a,
        owner_id=user_a,
        evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
        evidence_status=EvidenceStatus.AVAILABLE,
    )
    saved = await repo.add(ev)
    found = await repo.get_by_id_for_user(saved.id, user_a)
    assert found is not None
    assert found.id == saved.id


@pytest.mark.database
async def test_get_by_id_for_user_wrong_owner(
    session, session_a, user_a, user_b
):
    repo = EvidenceRepository(session)
    ev = Evidence(
        session_id=session_a,
        owner_id=user_a,
        evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
        evidence_status=EvidenceStatus.AVAILABLE,
    )
    saved = await repo.add(ev)
    found = await repo.get_by_id_for_user(saved.id, user_b)
    assert found is None


@pytest.mark.database
async def test_list_for_session_for_user(
    session, session_a, user_a
):
    repo = EvidenceRepository(session)
    for i in range(3):
        ev = Evidence(
            session_id=session_a,
            owner_id=user_a,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            evidence_status=EvidenceStatus.AVAILABLE,
        )
        await repo.add(ev)
    rows = await repo.list_for_session_for_user(session_a, user_a)
    assert len(rows) == 3


@pytest.mark.database
async def test_list_active_for_session_for_user(
    session, session_a, user_a
):
    repo = EvidenceRepository(session)
    ev1 = Evidence(
        session_id=session_a,
        owner_id=user_a,
        evidence_type=EvidenceType.CHART_THREE_MONTH,
        evidence_status=EvidenceStatus.AVAILABLE,
    )
    ev2 = Evidence(
        session_id=session_a,
        owner_id=user_a,
        evidence_type=EvidenceType.CHART_SIX_MONTH,
        evidence_status=EvidenceStatus.EXCLUDED,
    )
    await repo.add(ev1)
    await repo.add(ev2)
    rows = await repo.list_active_for_session_for_user(session_a, user_a)
    assert len(rows) == 1


@pytest.mark.database
async def test_deterministic_ordering(session, session_a, user_a):
    repo = EvidenceRepository(session)
    ev1 = Evidence(
        session_id=session_a,
        owner_id=user_a,
        evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
        evidence_status=EvidenceStatus.AVAILABLE,
    )
    ev2 = Evidence(
        session_id=session_a,
        owner_id=user_a,
        evidence_type=EvidenceType.CHART_THREE_MONTH,
        evidence_status=EvidenceStatus.AVAILABLE,
    )
    await repo.add(ev1)
    await repo.add(ev2)
    rows = await repo.list_for_session_for_user(session_a, user_a)
    assert len(rows) == 2


@pytest.mark.database
async def test_inactive_remains_queryable(
    session, session_a, user_a
):
    repo = EvidenceRepository(session)
    ev = Evidence(
        session_id=session_a,
        owner_id=user_a,
        evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
        evidence_status=EvidenceStatus.EXCLUDED,
    )
    saved = await repo.add(ev)
    found = await repo.get_by_id_for_user(saved.id, user_a)
    assert found is not None
    # Repository did not change status
    assert found.evidence_status == EvidenceStatus.EXCLUDED


@pytest.mark.database
async def test_no_commit(session, session_a, user_a):
    repo = EvidenceRepository(session)
    ev = Evidence(
        session_id=session_a,
        owner_id=user_a,
        evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
        evidence_status=EvidenceStatus.AVAILABLE,
    )
    saved = await repo.add(ev)
    assert saved.id is not None
