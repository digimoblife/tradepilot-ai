import pytest

from app.models.analysis_job import AnalysisJob
from app.models.enums import AnalysisJobStatus, AnalysisType
from app.repositories.analysis_job import AnalysisJobRepository


@pytest.mark.database
async def test_add_and_retrieve(session, data):
    repo = AnalysisJobRepository(session)
    job = AnalysisJob(session_id=data.session_a, analysis_type=AnalysisType.INITIAL_ANALYSIS)
    saved = await repo.add(job)
    assert saved.id is not None


@pytest.mark.database
async def test_get_by_id_for_user_owner(session, data):
    repo = AnalysisJobRepository(session)
    found = await repo.get_by_id_for_user(data.analysis_job_a, data.user_a)
    assert found is not None
    assert found.id == data.analysis_job_a


@pytest.mark.database
async def test_get_by_id_for_user_wrong_owner(session, data):
    repo = AnalysisJobRepository(session)
    found = await repo.get_by_id_for_user(data.analysis_job_a, data.user_b)
    assert found is None


@pytest.mark.database
async def test_list_for_session_for_user(session, data):
    repo = AnalysisJobRepository(session)
    rows = await repo.list_for_session_for_user(data.session_a, data.user_a)
    assert len(rows) >= 1


@pytest.mark.database
async def test_known_job_row_lock(session, data):
    repo = AnalysisJobRepository(session)
    found = await repo.get_by_id_for_user_for_update(data.analysis_job_a, data.user_a)
    assert found is not None


@pytest.mark.database
async def test_retry_lease_fields_unchanged(session, data):
    repo = AnalysisJobRepository(session)
    found = await repo.get_by_id_for_user(data.analysis_job_a, data.user_a)
    assert found is not None
    assert found.attempt_count == 0
    assert found.max_attempts == 3
    assert found.lease_owner is None


@pytest.mark.database
async def test_no_queue_claiming(session, data):
    repo = AnalysisJobRepository(session)
    found = await repo.get_by_id_for_user(data.analysis_job_a, data.user_a)
    assert found is not None
    assert found.status == AnalysisJobStatus.CREATED


@pytest.mark.database
async def test_find_active_for_session_and_type(session, data):
    repo = AnalysisJobRepository(session)
    job = AnalysisJob(session_id=data.session_a, analysis_type=AnalysisType.INITIAL_ANALYSIS)
    await repo.add(job)
    found = await repo.find_active_for_session_and_type_for_user(
        data.session_a, data.user_a, AnalysisType.INITIAL_ANALYSIS
    )
    assert found is not None
