"""Tests for AnalysisProcessor (TP-0804).

PostgreSQL-backed — uses fake providers and routers.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.ai.providers import (
    AIProvider,
    ProviderRequest,
    ProviderResponse,
)
from app.ai.providers.router import (
    ProviderRouteAttempt,
    ProviderRouter,
    ProviderRoutingFailedError,
    ProviderRoutingResult,
)
from app.jobs import (
    AnalysisProcessingResult,
    AnalysisProcessor,
    AnalysisProcessorAlreadyTerminalError,
    AnalysisProcessorJobNotClaimedError,
    AnalysisProcessorLeaseExpiredError,
    AnalysisProcessorLeaseNotOwnedError,
)
from app.models.analysis import Analysis
from app.models.analysis_job import AnalysisJob
from app.models.enums import (
    AcceptanceStatus,
    AnalysisJobStatus,
)
from app.models.trade_session import TradeSession
from app.validation import ValidationIssue

pytestmark = pytest.mark.database

_LEASE_1S = timedelta(seconds=1)


# ===================================================================
# Fake router
# ===================================================================


class FakeRouter(ProviderRouter):
    def __init__(
        self,
        result: ProviderRoutingResult | type[Exception] | Exception | None = None,
    ) -> None:
        self.result = result
        self.last_request: ProviderRequest | None = None
        self.last_providers: dict[str, AIProvider] | None = None
        self.call_count = 0

    async def generate_validated(self, **kwargs: Any) -> Any:
        self.call_count += 1
        self.last_request = kwargs.get("request")
        self.last_providers = kwargs.get("providers")
        if isinstance(self.result, type) and issubclass(self.result, Exception):
            raise self.result("Fake router failure")
        if isinstance(self.result, Exception):
            raise self.result
        if self.result is not None:
            return self.result
        return ProviderRoutingResult(
            provider="gemini",
            response=ProviderResponse(
                provider="gemini",
                model="g-model",
                raw_output='{"ok": true}',
                request_id=uuid.uuid4(),
            ),
            payload={"ok": True},
            attempts=(
                ProviderRouteAttempt(
                    sequence=1,
                    provider="gemini",
                    phase="PRIMARY",
                ),
            ),
            fallback_used=False,
        )


class FailingContextBuilder:
    async def build(self, **kwargs: Any) -> Any:
        raise FileNotFoundError("/app/prompts/production/v1/initial_analysis.system.md")


# ===================================================================
# Helpers
# ===================================================================


async def _make_user(engine: AsyncEngine) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
            {"e": f"ap_{uuid.uuid4().hex[:8]}@t.com", "p": "pw"},
        )
        return r.first()[0]


async def _make_session(
    engine: AsyncEngine,
    user_id: uuid.UUID,
    status: str = "ANALYZING",
) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                "INSERT INTO trade_sessions "
                "(owner_id, ticker, lifecycle_status, stable_status) "
                "VALUES (:o, :t, :ls, :ss) RETURNING id"
            ),
            {"o": user_id, "t": "BBRI", "ls": status, "ss": status},
        )
        sid = r.first()[0]
        await conn.execute(
            text(
                "INSERT INTO trade_states "
                "(session_id, position_status, thesis_status, state_version) "
                "VALUES (:s, 'NOT_OPENED', 'INTACT', 1)"
            ),
            {"s": sid},
        )
        return sid


async def _make_claimed_job(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    worker_id: str = "w1",
    status: str = "PROCESSING",
    attempt_count: int = 1,
    max_attempts: int = 3,
    lease_expires: datetime | None = None,
    prev_status: str = "WATCHING",
) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                "INSERT INTO analysis_jobs "
                "(session_id, analysis_type, status, attempt_count, "
                "max_attempts, lease_owner, lease_expires_at, "
                "lease_acquired_at, previous_session_status, available_at) "
                "VALUES (:sid, 'WATCHING_UPDATE', :st, :ac, :ma, "
                ":lo, :lea, :now, :ps, :now) RETURNING id"
            ),
            {
                "sid": session_id,
                "st": status,
                "ac": attempt_count,
                "ma": max_attempts,
                "lo": worker_id,
                "lea": lease_expires or (datetime.now(timezone.utc) + timedelta(seconds=30)),
                "now": datetime.now(timezone.utc),
                "ps": prev_status,
            },
        )
        return r.first()[0]


async def _add_context_summary(
    engine: AsyncEngine,
    session_id: uuid.UUID,
    *,
    source_cutoff: datetime | None = None,
    is_stale: bool = False,
) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO context_summaries "
                "(session_id, context_version, source_cutoff, payload, is_stale) "
                "VALUES (:sid, 1, :cutoff, '{}', :stale)"
            ),
            {
                "sid": session_id,
                "cutoff": source_cutoff or datetime.now(timezone.utc),
                "stale": is_stale,
            },
        )


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
async def user_id(engine: AsyncEngine) -> uuid.UUID:
    return await _make_user(engine)


@pytest.fixture
async def session_id(engine: AsyncEngine, user_id: uuid.UUID) -> uuid.UUID:
    return await _make_session(engine, user_id, status="ANALYZING")


@pytest.fixture
def factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


# ===================================================================
# Successful processing
# ===================================================================


class TestSuccessfulProcessing:
    async def test_processes_claimed_job(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id)
        await _add_context_summary(engine, session_id)

        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                router=FakeRouter(),
                validate=_always_valid,
            )
            result = await proc.process(job_id=jid, worker_id="w1")
            assert isinstance(result, AnalysisProcessingResult)
            assert result.job_status == "COMPLETED"

    async def test_analysis_created(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id)
        await _add_context_summary(engine, session_id)
        async with factory() as s:
            proc = AnalysisProcessor(session=s, router=FakeRouter(), validate=_always_valid)
            result = await proc.process(job_id=jid, worker_id="w1")
            assert result.analysis_id is not None
            analysis = await s.get(Analysis, result.analysis_id)
            assert analysis is not None
            assert analysis.acceptance_status == AcceptanceStatus.ACCEPTED

    async def test_job_completed(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id)
        await _add_context_summary(engine, session_id)
        async with factory() as s:
            proc = AnalysisProcessor(session=s, router=FakeRouter(), validate=_always_valid)
            await proc.process(job_id=jid, worker_id="w1")
            job = await s.get(AnalysisJob, jid)
            assert job is not None
            assert job.status == AnalysisJobStatus.COMPLETED

    async def test_session_restored(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id, prev_status="WATCHING")
        await _add_context_summary(engine, session_id)
        async with factory() as s:
            proc = AnalysisProcessor(session=s, router=FakeRouter(), validate=_always_valid)
            result = await proc.process(job_id=jid, worker_id="w1")
            assert result.restored_session_status == "WATCHING"
            await s.commit()
        async with factory() as s:
            ts = await s.get(TradeSession, session_id)
            assert ts is not None
            assert ts.lifecycle_status.value == "WATCHING"

    async def test_trade_state_unchanged(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id)
        await _add_context_summary(engine, session_id)
        async with factory() as s:
            proc = AnalysisProcessor(session=s, router=FakeRouter(), validate=_always_valid)
            await proc.process(job_id=jid, worker_id="w1")
        async with factory() as s:
            row = await s.execute(
                text("SELECT position_status FROM trade_states WHERE session_id = :sid"),
                {"sid": session_id},
            )
            assert row.first()[0] == "NOT_OPENED"

    async def test_provider_history_persisted(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id)
        await _add_context_summary(engine, session_id)
        async with factory() as s:
            proc = AnalysisProcessor(session=s, router=FakeRouter(), validate=_always_valid)
            await proc.process(job_id=jid, worker_id="w1")
            # Check provider_request was created
            reqs = await s.execute(
                text("SELECT id FROM provider_requests WHERE analysis_job_id = :jid"),
                {"jid": jid},
            )
            assert reqs.first() is not None

    async def test_context_failure_does_not_call_provider(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id)
        router = FakeRouter()

        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                context_builder=FailingContextBuilder(),
                router=router,
                validate=_always_valid,
            )
            with pytest.raises(FileNotFoundError):
                await proc.process(job_id=jid, worker_id="w1")
            reqs = await s.execute(
                text("SELECT id FROM provider_requests WHERE analysis_job_id = :jid"),
                {"jid": jid},
            )

        assert router.call_count == 0
        assert reqs.first() is None

    async def test_stale_context_is_rebuilt_before_provider_call(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id)
        old_cutoff = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
        await _add_context_summary(
            engine,
            session_id,
            source_cutoff=old_cutoff,
            is_stale=True,
        )
        router = FakeRouter()

        async with factory() as s:
            proc = AnalysisProcessor(session=s, router=router, validate=_always_valid)
            result = await proc.process(job_id=jid, worker_id="w1")
            assert result.job_status == "COMPLETED"
            reqs = await s.execute(
                text("SELECT id FROM provider_requests WHERE analysis_job_id = :jid"),
                {"jid": jid},
            )
            await s.commit()

        assert router.call_count == 1
        assert reqs.first() is not None
        async with engine.begin() as conn:
            fresh_count = (
                await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM context_summaries "
                        "WHERE session_id = :sid AND is_stale = false "
                        "AND source_cutoff > :cutoff"
                    ),
                    {"sid": session_id, "cutoff": old_cutoff},
                )
            ).scalar_one()
        assert fresh_count >= 1

    async def test_lease_cleared(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id)
        await _add_context_summary(engine, session_id)
        async with factory() as s:
            proc = AnalysisProcessor(session=s, router=FakeRouter(), validate=_always_valid)
            await proc.process(job_id=jid, worker_id="w1")
            await s.commit()
        async with factory() as s:
            job = await s.get(AnalysisJob, jid)
            assert job is not None
            assert job.lease_owner is None


# ===================================================================
# Ownership and lease
# ===================================================================


class TestOwnership:
    async def test_wrong_worker_rejected(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id, worker_id="w1")
        await _add_context_summary(engine, session_id)
        async with factory() as s:
            proc = AnalysisProcessor(session=s, router=FakeRouter(), validate=_always_valid)
            with pytest.raises(AnalysisProcessorLeaseNotOwnedError):
                await proc.process(job_id=jid, worker_id="w2")

    async def test_unclaimed_job_rejected(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(
            engine,
            session_id,
            status="QUEUED",
            worker_id=None,
            lease_expires=None,
        )
        await _add_context_summary(engine, session_id)
        async with factory() as s:
            proc = AnalysisProcessor(session=s, router=FakeRouter(), validate=_always_valid)
            with pytest.raises(AnalysisProcessorJobNotClaimedError):
                await proc.process(job_id=jid, worker_id="w1")

    async def test_expired_lease_rejected(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        jid = await _make_claimed_job(
            engine,
            session_id,
            worker_id="w1",
            lease_expires=past,
        )
        await _add_context_summary(engine, session_id)
        async with factory() as s:
            proc = AnalysisProcessor(session=s, router=FakeRouter(), validate=_always_valid)
            with pytest.raises(AnalysisProcessorLeaseExpiredError):
                await proc.process(job_id=jid, worker_id="w1")

    async def test_completed_job_rejected(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id, status="COMPLETED")
        await _add_context_summary(engine, session_id)
        async with factory() as s:
            proc = AnalysisProcessor(session=s, router=FakeRouter(), validate=_always_valid)
            with pytest.raises(AnalysisProcessorAlreadyTerminalError):
                await proc.process(job_id=jid, worker_id="w1")


# ===================================================================
# Idempotency
# ===================================================================


class TestIdempotency:
    async def test_repeat_call_no_duplicate_analysis(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id)
        await _add_context_summary(engine, session_id)

        async with factory() as s:
            proc1 = AnalysisProcessor(session=s, router=FakeRouter(), validate=_always_valid)
            await proc1.process(job_id=jid, worker_id="w1")
            await s.commit()

        async with factory() as s:
            proc2 = AnalysisProcessor(session=s, router=FakeRouter(), validate=_always_valid)
            with pytest.raises(AnalysisProcessorAlreadyTerminalError):
                await proc2.process(job_id=jid, worker_id="w1")

        async with factory() as s:
            count = await s.execute(
                text("SELECT COUNT(*) FROM analyses WHERE analysis_job_id = :jid"),
                {"jid": jid},
            )
            assert count.scalar_one() == 1


# ===================================================================
# Provider routing failure
# ===================================================================


class TestRoutingFailure:
    async def test_transient_router_failure_sets_retry(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id, attempt_count=1, max_attempts=3)
        await _add_context_summary(engine, session_id)
        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                router=FakeRouter(
                    result=ProviderRoutingFailedError(
                        "All failed",
                        root_cause_code="AI_PROVIDER_TIMEOUT",
                        root_cause_message="Gemini timed out",
                        retryable=True,
                    )
                ),
                validate=_always_valid,
            )
            result = await proc.process(job_id=jid, worker_id="w1")
            assert result.job_status == AnalysisJobStatus.RETRYING.value
            await s.commit()
        async with factory() as s:
            job = await s.get(AnalysisJob, jid)
            assert job is not None
            assert job.status == AnalysisJobStatus.RETRYING
            assert job.last_error_code == "AI_PROVIDER_TIMEOUT"
            assert job.last_error_message == "Gemini timed out"

    async def test_deterministic_router_failure_sets_failed_without_repeated_retry(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id, attempt_count=1, max_attempts=3)
        await _add_context_summary(engine, session_id)
        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                router=FakeRouter(
                    result=ProviderRoutingFailedError(
                        "All failed",
                        root_cause_code="AI_PROVIDER_INVALID_REQUEST",
                        root_cause_message="Model not found: gemini-3.5-flash",
                        retryable=False,
                    )
                ),
                validate=_always_valid,
            )
            result = await proc.process(job_id=jid, worker_id="w1")
            assert result.job_status == AnalysisJobStatus.FAILED.value
            await s.commit()
        async with factory() as s:
            job = await s.get(AnalysisJob, jid)
            session = await s.get(TradeSession, session_id)
            assert job is not None
            assert session is not None
            assert job.status == AnalysisJobStatus.FAILED
            assert job.last_error_code == "AI_PROVIDER_INVALID_REQUEST"
            assert job.last_error_message == "Model not found: gemini-3.5-flash"
            assert session.lifecycle_status.value == "WATCHING"

    async def test_router_exhaustion_sets_failed_atomically(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id, attempt_count=3, max_attempts=3)
        await _add_context_summary(engine, session_id)
        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                router=FakeRouter(
                    result=ProviderRoutingFailedError(
                        "All failed",
                        root_cause_code="AI_PROVIDER_TIMEOUT",
                        root_cause_message="Gemini timed out after 120s",
                        retryable=True,
                    )
                ),
                validate=_always_valid,
            )
            result = await proc.process(job_id=jid, worker_id="w1")
            assert result.job_status == AnalysisJobStatus.FAILED.value
            await s.commit()
        async with factory() as s:
            job = await s.get(AnalysisJob, jid)
            session = await s.get(TradeSession, session_id)
            assert job is not None
            assert session is not None
            assert job.status == AnalysisJobStatus.FAILED
            assert job.last_error_code == "AI_PROVIDER_TIMEOUT"
            assert job.last_error_message == "Gemini timed out after 120s"
            assert session.lifecycle_status.value == "WATCHING"

    async def test_no_analysis_on_failure(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id, attempt_count=3, max_attempts=3)
        await _add_context_summary(engine, session_id)
        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                router=FakeRouter(
                    result=ProviderRoutingFailedError(
                        "All failed",
                        root_cause_code="AI_PROVIDER_INVALID_REQUEST",
                        root_cause_message="Model not found: gemini-3.5-flash",
                        retryable=False,
                    )
                ),
                validate=_always_valid,
            )
            await proc.process(job_id=jid, worker_id="w1")
        async with factory() as s:
            count = await s.execute(
                text("SELECT COUNT(*) FROM analyses WHERE analysis_job_id = :jid"),
                {"jid": jid},
            )
            assert count.scalar_one() == 0


# ===================================================================
# Boundaries
# ===================================================================


class TestBoundaries:
    async def test_no_claim_inside_processor(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        """Processor does not claim jobs."""
        jid = await _make_claimed_job(engine, session_id)
        await _add_context_summary(engine, session_id)
        async with factory() as s:
            proc = AnalysisProcessor(session=s, router=FakeRouter(), validate=_always_valid)
            await proc.process(job_id=jid, worker_id="w1")
            # processor should not have claimed any other job

    async def test_no_trade_state_mutation(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id)
        await _add_context_summary(engine, session_id)
        async with factory() as s:
            proc = AnalysisProcessor(session=s, router=FakeRouter(), validate=_always_valid)
            await proc.process(job_id=jid, worker_id="w1")
        async with factory() as s:
            row = await s.execute(
                text(
                    "SELECT position_status, entry_price FROM trade_states WHERE session_id = :sid"
                ),
                {"sid": session_id},
            )
            r = row.first()
            assert r[0] == "NOT_OPENED"
            assert r[1] is None


# ===================================================================
# Validate helpers
# ===================================================================


def _always_valid(
    payload: dict[str, object],
) -> tuple[bool, tuple[ValidationIssue, ...]]:
    return True, ()
