from datetime import datetime, timezone

import pytest

from app.models.evidence import Evidence
from app.models.enums import EvidenceStatus, EvidenceType
from app.repositories.evidence import EvidenceRepository


@pytest.mark.database
async def test_add_and_retrieve(session, data):
    repo = EvidenceRepository(session)
    ev = Evidence(
        session_id=data.session_a,
        owner_id=data.user_a,
        evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
        evidence_status=EvidenceStatus.AVAILABLE,
    )
    saved = await repo.add(ev)
    assert saved.id is not None


@pytest.mark.database
async def test_get_by_id_for_user_owner(session, data):
    repo = EvidenceRepository(session)
    ev = Evidence(
        session_id=data.session_a,
        owner_id=data.user_a,
        evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
        evidence_status=EvidenceStatus.AVAILABLE,
    )
    saved = await repo.add(ev)
    found = await repo.get_by_id_for_user(saved.id, data.user_a)
    assert found is not None
    assert found.id == saved.id


@pytest.mark.database
async def test_get_by_id_for_user_wrong_owner(session, data):
    repo = EvidenceRepository(session)
    ev = Evidence(
        session_id=data.session_a,
        owner_id=data.user_a,
        evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
        evidence_status=EvidenceStatus.AVAILABLE,
    )
    saved = await repo.add(ev)
    found = await repo.get_by_id_for_user(saved.id, data.user_b)
    assert found is None


@pytest.mark.database
async def test_list_for_session_for_user(session, data):
    repo = EvidenceRepository(session)
    for _ in range(3):
        ev = Evidence(
            session_id=data.session_a,
            owner_id=data.user_a,
            evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
            evidence_status=EvidenceStatus.AVAILABLE,
        )
        await repo.add(ev)
    rows = await repo.list_for_session_for_user(data.session_a, data.user_a)
    assert len(rows) == 3


@pytest.mark.database
async def test_list_active_for_session(session, data):
    repo = EvidenceRepository(session)
    ev1 = Evidence(
        session_id=data.session_a,
        owner_id=data.user_a,
        evidence_type=EvidenceType.CHART_THREE_MONTH,
        evidence_status=EvidenceStatus.AVAILABLE,
    )
    ev2 = Evidence(
        session_id=data.session_a,
        owner_id=data.user_a,
        evidence_type=EvidenceType.CHART_SIX_MONTH,
        evidence_status=EvidenceStatus.EXCLUDED,
        exclusion_reason="not relevant",
        excluded_at=datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
    )
    await repo.add(ev1)
    await repo.add(ev2)
    rows = await repo.list_active_for_session_for_user(data.session_a, data.user_a)
    assert len(rows) == 1


@pytest.mark.database
async def test_inactive_remains_queryable(session, data):
    repo = EvidenceRepository(session)
    ev = Evidence(
        session_id=data.session_a,
        owner_id=data.user_a,
        evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
        evidence_status=EvidenceStatus.EXCLUDED,
        exclusion_reason="not relevant",
        excluded_at=datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
    )
    saved = await repo.add(ev)
    found = await repo.get_by_id_for_user(saved.id, data.user_a)
    assert found is not None
    assert found.evidence_status == EvidenceStatus.EXCLUDED


@pytest.mark.database
async def test_no_commit(session, data):
    repo = EvidenceRepository(session)
    ev = Evidence(
        session_id=data.session_a,
        owner_id=data.user_a,
        evidence_type=EvidenceType.ORDERBOOK_SCREENSHOT,
        evidence_status=EvidenceStatus.AVAILABLE,
    )
    saved = await repo.add(ev)
    assert saved.id is not None
