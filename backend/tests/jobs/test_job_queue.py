"""Tests for PostgreSQLJobQueue (TP-0801).

Uses actual PostgreSQL — no mocking.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.jobs import ClaimedJob, PostgreSQLJobQueue
from app.jobs.queue import (
    JobLeaseNotActiveError,
    JobLeaseNotOwnedError,
    JobQueueInvalidLeaseDurationError,
)

pytestmark = pytest.mark.database


_LEASE_1S = timedelta(seconds=1)


# ===================================================================
# Helpers
# ===================================================================


async def _make_session(
    engine: AsyncEngine,
    owner_id: uuid.UUID,
    ticker: str = "BBRI",
) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                "INSERT INTO trade_sessions "
                "(owner_id, ticker, lifecycle_status, stable_status) "
                "VALUES (:o, :t, 'DRAFT', 'DRAFT') RETURNING id"
            ),
            {"o": owner_id, "t": ticker},
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
        return sid


async def _insert_job(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    analysis_type: str = "INITIAL_ANALYSIS",
    status: str = "QUEUED",
    attempt_count: int = 0,
    max_attempts: int = 3,
    lease_expires_at: datetime | None = None,
    lease_owner: str | None = None,
    available_at: datetime | None = None,
) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                "INSERT INTO analysis_jobs "
                "(session_id, analysis_type, status, attempt_count, "
                "max_attempts, lease_expires_at, lease_owner, available_at) "
                "VALUES (:s, :at, :st, :ac, :ma, :lea, :lo, :ava) "
                "RETURNING id"
            ),
            {
                "s": session_id,
                "at": analysis_type,
                "st": status,
                "ac": attempt_count,
                "ma": max_attempts,
                "lea": lease_expires_at,
                "lo": lease_owner,
                "ava": available_at or datetime.now(timezone.utc),
            },
        )
        return r.first()[0]


async def _get_job_row(
    engine: AsyncEngine,
    job_id: uuid.UUID,
) -> tuple | None:
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                "SELECT status, lease_owner, lease_expires_at, attempt_count "
                "FROM analysis_jobs WHERE id = :jid"
            ),
            {"jid": job_id},
        )
        return r.first()


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture(autouse=True)
async def clean_jobs(engine: AsyncEngine) -> None:
    """Remove leftover jobs between tests."""
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM analysis_jobs"))


@pytest.fixture
async def user_id(engine: AsyncEngine) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
            {"e": f"q_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
        )
        return r.first()[0]


@pytest.fixture
async def session_id(engine: AsyncEngine, user_id: uuid.UUID) -> uuid.UUID:
    return await _make_session(engine, user_id)


@pytest.fixture
def factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# ===================================================================
# Basic claim
# ===================================================================


class TestBasicClaim:
    async def test_claim_one_queued_job(
        self,
        factory: async_sessionmaker[AsyncSession],
        engine: AsyncEngine,
        session_id: uuid.UUID,
    ) -> None:
        jid = await _insert_job(engine, session_id)
        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            result = await q.claim_next(worker_id="w1", lease_duration=_LEASE_1S)
            await s.commit()
            assert result is not None
            assert result.job_id == jid

    async def test_status_updates_to_processing(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _insert_job(engine, session_id)
        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            await q.claim_next(worker_id="w1", lease_duration=_LEASE_1S)
            await s.commit()
        row = await _get_job_row(engine, jid)
        assert row is not None
        assert row[0] == "PROCESSING"

    async def test_worker_ownership(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _insert_job(engine, session_id)
        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            await q.claim_next(worker_id="w1", lease_duration=_LEASE_1S)
            await s.commit()
        row = await _get_job_row(engine, jid)
        assert row is not None
        assert row[1] == "w1"

    async def test_lease_expiration(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _insert_job(engine, session_id)
        now = datetime.now(timezone.utc)
        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            result = await q.claim_next(
                worker_id="w1",
                lease_duration=timedelta(seconds=30),
                now=now,
            )
            assert result is not None
            expected = now + timedelta(seconds=30)
            assert abs((result.lease.expires_at - expected).total_seconds()) < 1

    async def test_first_attempt_count(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _insert_job(engine, session_id)
        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            result = await q.claim_next(worker_id="w1", lease_duration=_LEASE_1S)
            await s.commit()
            assert result is not None
            assert result.attempt_number == 1

    async def test_no_eligible_job_returns_none(
        self,
        factory: async_sessionmaker[AsyncSession],
        engine: AsyncEngine,
    ) -> None:
        # Ensure no queued jobs exist
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM analysis_jobs"))
        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            result = await q.claim_next(worker_id="w1", lease_duration=_LEASE_1S)
            assert result is None


# ===================================================================
# Concurrent claim
# ===================================================================


class TestConcurrentClaim:
    async def test_two_workers_race_one_job(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _insert_job(engine, session_id)

        async def attempt(worker: str) -> ClaimedJob | None:
            async with factory() as s:
                q = PostgreSQLJobQueue(s)
                result = await q.claim_next(
                    worker_id=worker,
                    lease_duration=_LEASE_1S,
                )
                await s.commit()
                return result

        r1, r2 = await asyncio.gather(attempt("w1"), attempt("w2"))
        winners = [r for r in (r1, r2) if r is not None]
        assert len(winners) == 1
        assert winners[0].job_id == jid

    async def test_two_workers_distinct_jobs(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _insert_job(engine, session_id, analysis_type="INITIAL_ANALYSIS")
        await _insert_job(engine, session_id, analysis_type="WATCHING_UPDATE")

        async def attempt(worker: str) -> ClaimedJob | None:
            async with factory() as s:
                q = PostgreSQLJobQueue(s)
                result = await q.claim_next(
                    worker_id=worker,
                    lease_duration=_LEASE_1S,
                )
                await s.commit()
                return result

        r1, r2 = await asyncio.gather(attempt("w1"), attempt("w2"))
        winners = [r for r in (r1, r2) if r is not None]
        assert len(winners) == 2

    async def test_active_lease_not_reclaimable(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _insert_job(engine, session_id)
        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            await q.claim_next(
                worker_id="w1",
                lease_duration=timedelta(seconds=30),
            )
            await s.commit()

        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            result = await q.claim_next(
                worker_id="w2",
                lease_duration=_LEASE_1S,
            )
            assert result is None

    async def test_expired_lease_can_be_reclaimed(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        jid = await _insert_job(engine, session_id, available_at=past)

        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            await q.claim_next(
                worker_id="w1",
                lease_duration=timedelta(seconds=1),
                now=past,
            )
            await s.commit()

        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            result = await q.claim_next(
                worker_id="w2",
                lease_duration=_LEASE_1S,
                now=datetime.now(timezone.utc),
            )
            await s.commit()
            assert result is not None
            assert result.job_id == jid

    async def test_reclaim_transfers_ownership(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        jid = await _insert_job(engine, session_id, available_at=past)

        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            await q.claim_next(
                worker_id="w1",
                lease_duration=timedelta(seconds=1),
                now=past,
            )
            await s.commit()

        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            await q.claim_next(
                worker_id="w2",
                lease_duration=_LEASE_1S,
                now=datetime.now(timezone.utc),
            )
            await s.commit()

        row = await _get_job_row(engine, jid)
        assert row is not None
        assert row[1] == "w2"

    async def test_reclaim_increments_attempt(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        await _insert_job(engine, session_id, available_at=past)

        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            await q.claim_next(
                worker_id="w1",
                lease_duration=timedelta(seconds=1),
                now=past,
            )
            await s.commit()

        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            result = await q.claim_next(
                worker_id="w2",
                lease_duration=_LEASE_1S,
                now=datetime.now(timezone.utc),
            )
            await s.commit()
            assert result is not None
            assert result.attempt_number == 2


# ===================================================================
# Lease duration
# ===================================================================


class TestLeaseDuration:
    async def test_positive_duration(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _insert_job(engine, session_id)
        now = datetime.now(timezone.utc)
        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            result = await q.claim_next(
                worker_id="w1",
                lease_duration=timedelta(seconds=60),
                now=now,
            )
            assert result is not None
            expected = now + timedelta(seconds=60)
            assert abs((result.lease.expires_at - expected).total_seconds()) < 2

    async def test_zero_duration_rejected(
        self,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            with pytest.raises(JobQueueInvalidLeaseDurationError):
                await q.claim_next(worker_id="w1", lease_duration=timedelta(0))

    async def test_negative_duration_rejected(
        self,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            with pytest.raises(JobQueueInvalidLeaseDurationError):
                await q.claim_next(worker_id="w1", lease_duration=timedelta(seconds=-1))

    async def test_timezone_aware_timestamps(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        await _insert_job(engine, session_id)
        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            now = datetime.now(timezone.utc)
            result = await q.claim_next(
                worker_id="w1",
                lease_duration=_LEASE_1S,
                now=now,
            )
            assert result is not None
            assert result.lease.claimed_at.tzinfo is not None
            assert result.lease.expires_at.tzinfo is not None


# ===================================================================
# Failed claim does not increment
# ===================================================================


class TestFailedClaim:
    async def test_failed_claim_does_not_increment(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _insert_job(engine, session_id)

        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            await q.claim_next(
                worker_id="w1",
                lease_duration=timedelta(seconds=30),
            )
            await s.commit()

        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            await q.claim_next(
                worker_id="w2",
                lease_duration=_LEASE_1S,
            )
            await s.commit()

        row = await _get_job_row(engine, jid)
        assert row is not None
        assert row[3] == 1  # attempt_count should be 1 (only w1 succeeded)


# ===================================================================
# Lease renewal
# ===================================================================


class TestLeaseRenewal:
    async def test_renew_lease(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _insert_job(engine, session_id)
        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            await q.claim_next(worker_id="w1", lease_duration=_LEASE_1S)
            lease = await q.renew_lease(
                job_id=jid,
                worker_id="w1",
                lease_duration=timedelta(seconds=30),
            )
            assert lease.worker_id == "w1"
            assert lease.attempt_number == 1

    async def test_renew_lease_wrong_worker(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _insert_job(engine, session_id)
        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            await q.claim_next(worker_id="w1", lease_duration=_LEASE_1S)
            with pytest.raises(JobLeaseNotOwnedError):
                await q.renew_lease(
                    job_id=jid,
                    worker_id="w2",
                    lease_duration=_LEASE_1S,
                )

    async def test_renew_lease_not_active(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _insert_job(engine, session_id)
        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            with pytest.raises(JobLeaseNotActiveError):
                await q.renew_lease(
                    job_id=jid,
                    worker_id="w1",
                    lease_duration=_LEASE_1S,
                )


# ===================================================================
# Lease release
# ===================================================================


class TestLeaseRelease:
    async def test_release_returns_to_queued(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _insert_job(engine, session_id)
        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            await q.claim_next(worker_id="w1", lease_duration=_LEASE_1S)
            await q.release(job_id=jid, worker_id="w1")
            await s.commit()

        row = await _get_job_row(engine, jid)
        assert row is not None
        assert row[0] == "QUEUED"
        assert row[1] is None

    async def test_release_wrong_worker(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _insert_job(engine, session_id)
        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            await q.claim_next(worker_id="w1", lease_duration=_LEASE_1S)
            with pytest.raises(JobLeaseNotOwnedError):
                await q.release(job_id=jid, worker_id="w2")

    async def test_release_not_processing(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _insert_job(engine, session_id)
        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            with pytest.raises(JobLeaseNotActiveError):
                await q.release(job_id=jid, worker_id="w1")

    async def test_release_after_reclaim_fails_for_old_worker(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        jid = await _insert_job(engine, session_id, available_at=past)

        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            await q.claim_next(
                worker_id="w1",
                lease_duration=timedelta(seconds=1),
                now=past,
            )
            await s.commit()

        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            await q.claim_next(
                worker_id="w2",
                lease_duration=_LEASE_1S,
                now=datetime.now(timezone.utc),
            )
            await s.commit()

        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            with pytest.raises(JobLeaseNotOwnedError):
                await q.release(job_id=jid, worker_id="w1")


# ===================================================================
# Atomic rollback
# ===================================================================


class TestAtomicRollback:
    async def test_rollback_preserves_original_state(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _insert_job(engine, session_id)
        async with factory() as s:
            q = PostgreSQLJobQueue(s)
            result = await q.claim_next(
                worker_id="w1",
                lease_duration=_LEASE_1S,
            )
            assert result is not None
            await s.rollback()

        row = await _get_job_row(engine, jid)
        assert row is not None
        assert row[0] == "QUEUED"
        assert row[1] is None
        assert row[2] is None
        assert row[3] == 0
