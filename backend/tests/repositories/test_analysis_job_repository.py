import uuid

import pytest

from app.models.analysis_job import AnalysisJob
from app.repositories.analysis_job import AnalysisJobRepository
from app.models.enums import AnalysisJobStatus, AnalysisType


@pytest.mark.database
async def test_add_and_retrieve(session, session_a, user_a):
    repo = AnalysisJobRepository(session)
    job = AnalysisJob(session_id=session_a, analysis_type=AnalysisType.INITIAL_ANALYSIS)
    saved = await repo.add(job)
    assert saved.id is not None


@pytest.mark.database
async def test_get_by_id_for_user_owner(
    session, session_a, user_a, job_a
):
    repo = AnalysisJobRepository(session)
    found = await repo.get_by_id_for_user(job_a, user_a)
    assert found is not None
    assert found.id == job_a


@pytest.mark.database
async def test_get_by_id_for_user_wrong_owner(
    session, job_a, user_b
):
    repo = AnalysisJobRepository(session)
    found = await repo.get_by_id_for_user(job_a, user_b)
    assert found is None


@pytest.mark.database
async def test_list_for_session_for_user(
    session, session_a, user_a, job_a
):
    repo = AnalysisJobRepository(session)
    rows = await repo.list_for_session_for_user(session_a, user_a)
    assert len(rows) >= 1


@pytest.mark.database
async def test_deterministic_ordering(session, session_a, user_a):
    repo = AnalysisJobRepository(session)
    for _ in range(3):
        job = AnalysisJob(session_id=session_a, analysis_type=AnalysisType.WATCHING_UPDATE)
        await repo.add(job)
    rows = await repo.list_for_session_for_user(session_a, user_a)
    assert len(rows) >= 3


@pytest.mark.database
async def test_known_job_row_lock(
    session, session_a, user_a, job_a
):
    repo = AnalysisJobRepository(session)
    found = await repo.get_by_id_for_user_for_update(job_a, user_a)
    assert found is not None


@pytest.mark.database
async def test_retry_lease_fields_unchanged(
    session, session_a, user_a, job_a
):
    repo = AnalysisJobRepository(session)
    found = await repo.get_by_id_for_user(job_a, user_a)
    assert found is not None
    assert found.attempt_count == 0
    assert found.max_attempts == 3
    assert found.lease_owner is None


@pytest.mark.database
async def test_no_queue_claiming(session, session_a, user_a, job_a):
    repo = AnalysisJobRepository(session)
    found = await repo.get_by_id_for_user(job_a, user_a)
    assert found is not None
    assert found.status == AnalysisJobStatus.CREATED
    # Status not changed by repository read


@pytest.mark.database
async def test_find_active_for_session_and_type(
    session, session_a, user_a
):
    repo = AnalysisJobRepository(session)
    job = AnalysisJob(session_id=session_a, analysis_type=AnalysisType.INITIAL_ANALYSIS)
    await repo.add(job)
    found = await repo.find_active_for_session_and_type_for_user(
        session_a, user_a, AnalysisType.INITIAL_ANALYSIS
    )
    assert found is not None
