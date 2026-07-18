import pytest

from app.models.context_summary import ContextSummary
from app.repositories.context_summary import ContextSummaryRepository


@pytest.mark.database
async def test_add_and_retrieve(session, data):
    repo = ContextSummaryRepository(session)
    cs = ContextSummary(session_id=data.session_a, context_version=1)
    saved = await repo.add(cs)
    assert saved.id is not None


@pytest.mark.database
async def test_get_by_id_for_user_owner(session, data):
    repo = ContextSummaryRepository(session)
    cs = ContextSummary(session_id=data.session_a, context_version=1)
    saved = await repo.add(cs)
    found = await repo.get_by_id_for_user(saved.id, data.user_a)
    assert found is not None
    assert found.id == saved.id


@pytest.mark.database
async def test_get_by_id_for_user_wrong_owner(session, data):
    repo = ContextSummaryRepository(session)
    cs = ContextSummary(session_id=data.session_a, context_version=1)
    saved = await repo.add(cs)
    found = await repo.get_by_id_for_user(saved.id, data.user_b)
    assert found is None


@pytest.mark.database
async def test_multiple_versions_retained(session, data):
    repo = ContextSummaryRepository(session)
    for v in range(1, 4):
        cs = ContextSummary(session_id=data.session_a, context_version=v)
        await repo.add(cs)
    rows = await repo.list_versions_for_user(data.session_a, data.user_a)
    assert len(rows) == 3


@pytest.mark.database
async def test_latest_selected_by_query(session, data):
    repo = ContextSummaryRepository(session)
    for v in range(1, 6):
        cs = ContextSummary(session_id=data.session_a, context_version=v)
        await repo.add(cs)
    latest = await repo.get_latest_for_user(data.session_a, data.user_a)
    assert latest is not None
    assert latest.context_version == 5


@pytest.mark.database
async def test_stale_filtering(session, data):
    repo = ContextSummaryRepository(session)
    cs1 = ContextSummary(session_id=data.session_a, context_version=1, is_stale=True)
    cs2 = ContextSummary(session_id=data.session_a, context_version=2, is_stale=False)
    await repo.add(cs1)
    await repo.add(cs2)
    latest_non_stale = await repo.get_latest_non_stale_for_user(data.session_a, data.user_a)
    assert latest_non_stale is not None
    assert latest_non_stale.context_version == 2


@pytest.mark.database
async def test_prior_versions_available(session, data):
    repo = ContextSummaryRepository(session)
    cs1 = ContextSummary(session_id=data.session_a, context_version=1)
    cs2 = ContextSummary(session_id=data.session_a, context_version=2)
    await repo.add(cs1)
    await repo.add(cs2)
    rows = await repo.list_versions_for_user(data.session_a, data.user_a)
    assert len(rows) == 2
    assert rows[0].context_version == 1
    assert rows[1].context_version == 2


@pytest.mark.database
async def test_deterministic_history(session, data):
    repo = ContextSummaryRepository(session)
    await repo.add(ContextSummary(session_id=data.session_a, context_version=5))
    await repo.add(ContextSummary(session_id=data.session_a, context_version=3))
    rows = await repo.list_versions_for_user(data.session_a, data.user_a)
    assert rows[0].context_version == 3
    assert rows[1].context_version == 5
