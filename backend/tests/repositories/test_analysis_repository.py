from datetime import datetime, timezone

import pytest

from app.models.analysis import Analysis
from app.models.enums import AcceptanceStatus, AnalysisType
from app.repositories.analysis import AnalysisRepository


@pytest.mark.database
async def test_add_and_retrieve(session, data):
    repo = AnalysisRepository(session)
    analysis = Analysis(
        session_id=data.session_a,
        analysis_job_id=data.analysis_job_a,
        analysis_type=AnalysisType.INITIAL_ANALYSIS,
        acceptance_status=AcceptanceStatus.ACCEPTED,
        prompt_name="v1",
        prompt_version="1.0",
        schema_name="schema",
        schema_version="1.0",
    )
    saved = await repo.add(analysis)
    assert saved.id is not None


@pytest.mark.database
async def test_get_by_id_for_user_owner(session, data):
    repo = AnalysisRepository(session)
    found = await repo.get_by_id_for_user(data.analysis_a, data.user_a)
    assert found is not None
    assert found.id == data.analysis_a


@pytest.mark.database
async def test_get_by_id_for_user_wrong_owner(session, data):
    repo = AnalysisRepository(session)
    found = await repo.get_by_id_for_user(data.analysis_a, data.user_b)
    assert found is None


@pytest.mark.database
async def test_latest_accepted(session, data):
    repo = AnalysisRepository(session)
    a1 = Analysis(
        session_id=data.session_a,
        analysis_job_id=data.analysis_job_a,
        analysis_type=AnalysisType.INITIAL_ANALYSIS,
        acceptance_status=AcceptanceStatus.ACCEPTED,
        prompt_name="v1",
        prompt_version="1.0",
        schema_name="schema",
        schema_version="1.0",
        accepted_at=datetime(2026, 7, 18, 10, 0, 0, tzinfo=timezone.utc),
    )
    a2 = Analysis(
        session_id=data.session_a,
        analysis_job_id=data.analysis_job_a,
        analysis_type=AnalysisType.WATCHING_UPDATE,
        acceptance_status=AcceptanceStatus.ACCEPTED,
        prompt_name="v2",
        prompt_version="1.0",
        schema_name="schema",
        schema_version="1.0",
        accepted_at=datetime(2026, 7, 18, 11, 0, 0, tzinfo=timezone.utc),
    )
    await repo.add(a1)
    await repo.add(a2)
    latest = await repo.get_latest_accepted_for_user(data.session_a, data.user_a)
    assert latest is not None
    assert latest.prompt_name == "v2"


@pytest.mark.database
async def test_rejected_excluded_from_accepted(session, data):
    repo = AnalysisRepository(session)
    rejected = Analysis(
        session_id=data.session_a,
        analysis_job_id=data.analysis_job_a,
        analysis_type=AnalysisType.INITIAL_ANALYSIS,
        acceptance_status=AcceptanceStatus.REJECTED,
        prompt_name="v1",
        prompt_version="1.0",
        schema_name="schema",
        schema_version="1.0",
    )
    await repo.add(rejected)
    latest = await repo.get_latest_accepted_for_user(data.session_a, data.user_a)
    assert latest is not None  # seed analysis_a is ACCEPTED
    assert latest.acceptance_status == AcceptanceStatus.ACCEPTED


@pytest.mark.database
async def test_superseded_history(session, data):
    repo = AnalysisRepository(session)
    a2 = Analysis(
        session_id=data.session_a,
        analysis_job_id=data.analysis_job_a,
        analysis_type=AnalysisType.WATCHING_UPDATE,
        acceptance_status=AcceptanceStatus.SUPERSEDED,
        prompt_name="v2",
        prompt_version="1.0",
        schema_name="schema",
        schema_version="1.0",
    )
    await repo.add(a2)
    rows = await repo.list_for_session_for_user(data.session_a, data.user_a)
    assert len(rows) == 2
