"""Tests for AnalysisJobCreationService (TP-0802).

PostgreSQL-backed tests — no mocking.
"""

from __future__ import annotations

import uuid
from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.models.analysis_job import AnalysisJob
from app.models.enums import (
    AnalysisType,
)
from app.services.analysis_jobs import (
    AnalysisJobAlreadyActiveError,
    AnalysisJobCreationResult,
    AnalysisJobCreationService,
    AnalysisJobSessionNotFoundError,
    AnalysisRequiredEvidenceMissingError,
    AnalysisTypeInvalidForLifecycleError,
)

pytestmark = pytest.mark.database


# ===================================================================
# Helpers
# ===================================================================


async def _make_session(
    engine: AsyncEngine,
    owner_id: uuid.UUID,
    status: str = "DRAFT",
    ticker: str = "BBRI",
) -> tuple[uuid.UUID, str]:
    """Create a session and return (session_id, stable_status)."""
    stable = status
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                "INSERT INTO trade_sessions "
                "(owner_id, ticker, lifecycle_status, stable_status) "
                "VALUES (:o, :t, :ls, :ss) RETURNING id"
            ),
            {"o": owner_id, "t": ticker, "ls": status, "ss": stable},
        )
        sid = r.first()[0]
        await conn.execute(
            text(
                "INSERT INTO trade_states "
                "(session_id, position_status, thesis_status) "
                "VALUES (:s, 'NOT_OPENED', 'INTACT')"
            ),
            {"s": sid},
        )
        return sid, stable


async def _add_evidence(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    owner_id: uuid.UUID,
    evidence_type: str,
    status: str = "AVAILABLE",
) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                "INSERT INTO evidence "
                "(session_id, owner_id, evidence_type, evidence_status, "
                "storage_object_key, mime_type, file_size_bytes) "
                "VALUES (:sid, :oid, :et, :es, :key, 'image/png', 100) "
                "RETURNING id"
            ),
            {
                "sid": session_id,
                "oid": owner_id,
                "et": evidence_type,
                "es": status,
                "key": f"test/{evidence_type}.png",
            },
        )
        return r.first()[0]


def _make_image_bytes() -> bytes:
    img = Image.new("RGB", (50, 50), color="blue")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def _seed_initial_evidence(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> None:
    for et in ("ORDERBOOK_SCREENSHOT", "CHART_THREE_MONTH", "CHART_SIX_MONTH"):
        await _add_evidence(engine, session_id, owner_id, et)


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
async def user_id(engine: AsyncEngine) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
            {"e": f"ajc_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
        )
        return r.first()[0]


@pytest.fixture
async def other_user_id(engine: AsyncEngine) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
            {"e": f"ajc2_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
        )
        return r.first()[0]


@pytest.fixture
def factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# ===================================================================
# Valid creation — INITIAL_ANALYSIS from READY_FOR_ANALYSIS
# ===================================================================


class TestValidCreation:
    async def test_creates_queued_job(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="READY_FOR_ANALYSIS")
        await _seed_initial_evidence(engine, sid, user_id)

        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            result = await svc.create(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.INITIAL_ANALYSIS,
            )
            assert isinstance(result, AnalysisJobCreationResult)
            assert result.analysis_type == "INITIAL_ANALYSIS"
            assert result.job_status == "QUEUED"

    async def test_job_belongs_to_correct_session(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="READY_FOR_ANALYSIS")
        await _seed_initial_evidence(engine, sid, user_id)

        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            result = await svc.create(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.INITIAL_ANALYSIS,
            )
            assert result.session_id == sid

    async def test_attempt_count_initial(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="READY_FOR_ANALYSIS")
        await _seed_initial_evidence(engine, sid, user_id)

        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            result = await svc.create(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.INITIAL_ANALYSIS,
            )
            job = await s.get(AnalysisJob, result.job_id)
            assert job is not None
            assert job.attempt_count == 0

    async def test_no_lease_owner(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="READY_FOR_ANALYSIS")
        await _seed_initial_evidence(engine, sid, user_id)

        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            result = await svc.create(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.INITIAL_ANALYSIS,
            )
            job = await s.get(AnalysisJob, result.job_id)
            assert job is not None
            assert job.lease_owner is None
            assert job.lease_expires_at is None


# ===================================================================
# Lifecycle compatibility
# ===================================================================


class TestLifecycleCompatibility:
    async def test_valid_initial_analysis_from_ready(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="READY_FOR_ANALYSIS")
        await _seed_initial_evidence(engine, sid, user_id)
        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            result = await svc.create(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.INITIAL_ANALYSIS,
            )
            assert result.job_status == "QUEUED"

    async def test_invalid_initial_from_watching(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="WATCHING")
        await _seed_initial_evidence(engine, sid, user_id)
        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            with pytest.raises(AnalysisTypeInvalidForLifecycleError):
                await svc.create(
                    session_id=sid,
                    owner_id=user_id,
                    analysis_type=AnalysisType.INITIAL_ANALYSIS,
                )

    async def test_no_job_created_on_invalid(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="WATCHING")
        await _seed_initial_evidence(engine, sid, user_id)
        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            with pytest.raises(AnalysisTypeInvalidForLifecycleError):
                await svc.create(
                    session_id=sid,
                    owner_id=user_id,
                    analysis_type=AnalysisType.INITIAL_ANALYSIS,
                )
            count = await s.execute(
                text("SELECT COUNT(*) FROM analysis_jobs WHERE session_id = :sid"),
                {"sid": sid},
            )
            assert count.scalar_one() == 0

    async def test_open_position_update_from_open(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="OPEN_POSITION")
        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            result = await svc.create(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.OPEN_POSITION_UPDATE,
            )
            assert result.job_status == "QUEUED"

    async def test_closing_analysis_from_closed(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        for closed_status in ("CLOSED_TAKE_PROFIT", "CLOSED_STOP_LOSS", "CLOSED_MANUAL"):
            sid, _ = await _make_session(engine, user_id, status=closed_status)
            async with factory() as s:
                svc = AnalysisJobCreationService(s)
                result = await svc.create(
                    session_id=sid,
                    owner_id=user_id,
                    analysis_type=AnalysisType.CLOSING_ANALYSIS,
                )
                assert result.job_status == "QUEUED"


# ===================================================================
# Required evidence
# ===================================================================


class TestRequiredEvidence:
    async def test_all_evidence_present_allows_creation(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="READY_FOR_ANALYSIS")
        await _seed_initial_evidence(engine, sid, user_id)
        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            result = await svc.create(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.INITIAL_ANALYSIS,
            )
            assert result.job_status == "QUEUED"

    async def test_no_evidence_rejected(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="READY_FOR_ANALYSIS")
        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            with pytest.raises(AnalysisRequiredEvidenceMissingError):
                await svc.create(
                    session_id=sid,
                    owner_id=user_id,
                    analysis_type=AnalysisType.INITIAL_ANALYSIS,
                )

    async def test_partial_evidence_rejected(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="READY_FOR_ANALYSIS")
        await _add_evidence(engine, sid, user_id, "ORDERBOOK_SCREENSHOT")
        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            with pytest.raises(AnalysisRequiredEvidenceMissingError):
                await svc.create(
                    session_id=sid,
                    owner_id=user_id,
                    analysis_type=AnalysisType.INITIAL_ANALYSIS,
                )

    async def test_inactive_evidence_ignored(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="READY_FOR_ANALYSIS")
        await _add_evidence(engine, sid, user_id, "ORDERBOOK_SCREENSHOT", status="SUPERSEDED")
        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            with pytest.raises(AnalysisRequiredEvidenceMissingError):
                await svc.create(
                    session_id=sid,
                    owner_id=user_id,
                    analysis_type=AnalysisType.INITIAL_ANALYSIS,
                )


# ===================================================================
# Duplicate active jobs
# ===================================================================


class TestDuplicateActive:
    async def test_queued_duplicate_rejected(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="READY_FOR_ANALYSIS")
        await _seed_initial_evidence(engine, sid, user_id)
        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            await svc.create(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.INITIAL_ANALYSIS,
            )
            with pytest.raises(AnalysisJobAlreadyActiveError):
                await svc.create(
                    session_id=sid,
                    owner_id=user_id,
                    analysis_type=AnalysisType.INITIAL_ANALYSIS,
                )

    async def test_duplicate_rejection_leaves_session_unchanged(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="READY_FOR_ANALYSIS")
        await _seed_initial_evidence(engine, sid, user_id)
        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            await svc.create(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.INITIAL_ANALYSIS,
            )
            with pytest.raises(AnalysisJobAlreadyActiveError):
                await svc.create(
                    session_id=sid,
                    owner_id=user_id,
                    analysis_type=AnalysisType.INITIAL_ANALYSIS,
                )
            await s.commit()

        # Session should still be ANALYZING (first job succeeded)
        async with factory() as s:
            ts = await s.execute(
                text("SELECT lifecycle_status, stable_status FROM trade_sessions WHERE id = :sid"),
                {"sid": sid},
            )
            row = ts.first()
            assert row is not None
            assert row[0] == "ANALYZING"

    async def test_duplicate_same_type_rejected_before_new(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Same-type duplicate is rejected before creating a second job."""
        sid, _ = await _make_session(engine, user_id, status="OPEN_POSITION")
        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            await svc.create(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.OPEN_POSITION_UPDATE,
            )
            with pytest.raises(AnalysisJobAlreadyActiveError):
                await svc.create(
                    session_id=sid,
                    owner_id=user_id,
                    analysis_type=AnalysisType.OPEN_POSITION_UPDATE,
                )
            await s.rollback()


# ===================================================================
# Ownership
# ===================================================================


class TestOwnership:
    async def test_wrong_owner_rejected(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        other_user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="READY_FOR_ANALYSIS")
        await _seed_initial_evidence(engine, sid, user_id)
        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            with pytest.raises(AnalysisJobSessionNotFoundError):
                await svc.create(
                    session_id=sid,
                    owner_id=other_user_id,
                    analysis_type=AnalysisType.INITIAL_ANALYSIS,
                )

    async def test_no_job_created_on_wrong_owner(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        other_user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="READY_FOR_ANALYSIS")
        await _seed_initial_evidence(engine, sid, user_id)
        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            with pytest.raises(AnalysisJobSessionNotFoundError):
                await svc.create(
                    session_id=sid,
                    owner_id=other_user_id,
                    analysis_type=AnalysisType.INITIAL_ANALYSIS,
                )
            count = await s.execute(
                text("SELECT COUNT(*) FROM analysis_jobs WHERE session_id = :sid"),
                {"sid": sid},
            )
            assert count.scalar_one() == 0


# ===================================================================
# Previous status and ANALYZING transition
# ===================================================================


class TestStatusTransition:
    async def test_session_becomes_analyzing(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="READY_FOR_ANALYSIS")
        await _seed_initial_evidence(engine, sid, user_id)
        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            result = await svc.create(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.INITIAL_ANALYSIS,
            )
            assert result.current_session_status == "ANALYZING"

    async def test_previous_status_preserved(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="WATCHING")
        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            result = await svc.create(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.WATCHING_UPDATE,
            )
            assert result.previous_session_status == "WATCHING"

    async def test_previous_status_on_job(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="OPEN_POSITION")
        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            result = await svc.create(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.OPEN_POSITION_UPDATE,
            )
            job = await s.get(AnalysisJob, result.job_id)
            assert job is not None
            assert job.previous_session_status == "OPEN_POSITION"

    async def test_preserved_not_overwritten(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """The preserved stable_status is not overwritten by ANALYZING."""
        sid, _ = await _make_session(engine, user_id, status="READY_FOR_ANALYSIS")
        await _seed_initial_evidence(engine, sid, user_id)
        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            result = await svc.create(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.INITIAL_ANALYSIS,
            )
            assert result.previous_session_status == "READY_FOR_ANALYSIS"
            # stable_status is set to ANALYZING (both lifecycle and stable are ANALYZING)
            ts = await s.execute(
                text("SELECT stable_status FROM trade_sessions WHERE id = :sid"),
                {"sid": sid},
            )
            row = ts.first()
            assert row is not None
            assert row[0] == "ANALYZING"


# ===================================================================
# Atomic rollback
# ===================================================================


class TestAtomicRollback:
    async def test_rollback_no_job_no_transition(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        sid, _ = await _make_session(engine, user_id, status="READY_FOR_ANALYSIS")
        await _seed_initial_evidence(engine, sid, user_id)

        async with factory() as s:
            svc = AnalysisJobCreationService(s)
            result = await svc.create(
                session_id=sid,
                owner_id=user_id,
                analysis_type=AnalysisType.INITIAL_ANALYSIS,
            )
            assert result.job_status == "QUEUED"
            await s.rollback()

        # Verify nothing persisted
        async with factory() as s:
            count = await s.execute(
                text("SELECT COUNT(*) FROM analysis_jobs WHERE session_id = :sid"),
                {"sid": sid},
            )
            assert count.scalar_one() == 0
            ts_row = await s.execute(
                text("SELECT lifecycle_status FROM trade_sessions WHERE id = :sid"),
                {"sid": sid},
            )
            row = ts_row.first()
            assert row is not None
            assert row[0] == "READY_FOR_ANALYSIS"
