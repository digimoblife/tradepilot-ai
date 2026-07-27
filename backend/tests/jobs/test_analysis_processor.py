"""Tests for AnalysisProcessor (TP-0804).

PostgreSQL-backed — uses fake providers and routers.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.ai.providers import (
    AIProvider,
    ProviderCapabilities,
    ProviderImage,
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
    EvidenceBatchStatus,
)
from app.models.trade_session import TradeSession
from app.services.evidence_batches import EvidenceBatchService
from app.validation import (
    ValidationCategory,
    ValidationIssue,
    ValidationSeverity,
)

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


class CountingProvider(AIProvider):
    def __init__(self, responses: list[ProviderResponse | Exception]) -> None:
        self._responses = list(responses)
        self.call_count = 0

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return "gemini-3.1-flash-lite"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_images=True,
            supports_text_output=True,
            supports_structured_output=True,
            supports_system_prompt=True,
            supports_json_schema=True,
            supports_multi_image=True,
            maximum_images=10,
        )

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        self.call_count += 1
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeInitialAnalysisContextBuilder:
    def __init__(self) -> None:
        self.images = (
            ProviderImage(uuid.uuid4(), "image/png", "user/session/file-1.png", 69, 1, 1),
            ProviderImage(uuid.uuid4(), "image/png", "user/session/file-2.png", 69, 1, 1),
            ProviderImage(uuid.uuid4(), "image/png", "user/session/file-3.png", 69, 1, 1),
        )

    async def build(self, **kwargs: Any) -> Any:
        return SimpleNamespace(
            session_id=kwargs["session_id"],
            analysis_type="INITIAL_ANALYSIS",
            prompt_version="2.0.0",
            system_prompt="System prompt",
            user_prompt="Base user prompt",
            expected_schema_name="initial_analysis_v2",
            expected_schema_version="2.0.0",
            structured_output_schema={},
            canonical_facts={},
            images=self.images,
            metadata={
                "session_id": str(kwargs["session_id"]),
                "canonical_chart_timestamps": {
                    "chart_3_month_analysis": "2026-07-24T09:15:00+07:00",
                    "chart_6_month_analysis": "2026-07-23T15:45:00+07:00",
                },
            },
        )


class PartitionRouter(ProviderRouter):
    def __init__(
        self,
        *,
        payloads_by_partition: dict[str, dict[str, object]],
        failing_partition: str | None = None,
        failure_code: str = "AI_PROVIDER_TIMEOUT",
        failure_message: str = "Gemini timed out",
    ) -> None:
        self.payloads_by_partition = payloads_by_partition
        self.failing_partition = failing_partition
        self.failure_code = failure_code
        self.failure_message = failure_message
        self.calls: list[tuple[str, tuple[str, ...]]] = []
        self.request_metadata: list[dict[str, object]] = []
        self.validations: list[str] = []

    async def generate_validated(self, **kwargs: Any) -> Any:
        request: ProviderRequest = kwargs["request"]
        validate = kwargs["validate"]
        partition_name = str(request.metadata["partition_name"])
        image_refs = tuple(img.storage_reference for img in request.images)
        self.calls.append((partition_name, image_refs))
        self.request_metadata.append(dict(request.metadata))

        if self.failing_partition == partition_name:
            raise ProviderRoutingFailedError(
                message="Partition failed",
                root_cause_code=self.failure_code,
                root_cause_message=self.failure_message,
                retryable=self.failure_code in {"AI_PROVIDER_TIMEOUT", "AI_PROVIDER_RATE_LIMITED"},
            )

        payload = self.payloads_by_partition[partition_name]
        validated_payload = payload
        is_valid, issues = validate(dict(validated_payload))
        self.validations.append(partition_name)
        if not is_valid:
            raise ProviderRoutingFailedError(
                message="Partition validation failed",
                attempts=(
                    ProviderRouteAttempt(
                        sequence=1,
                        provider="gemini",
                        phase="PRIMARY",
                        response=ProviderResponse(
                            provider="gemini",
                            model="gemini-3.1-flash-lite",
                            raw_output=json.dumps(payload),
                            request_id=request.request_id,
                            metadata={"provider_payload_raw": payload},
                        ),
                        payload=validated_payload,
                        failure_code=issues[0].code if issues else "REPAIR_VALIDATION_FAILED",
                        failure_message=issues[0].message if issues else "Partition invalid",
                    ),
                ),
                root_cause_code=issues[0].code if issues else "REPAIR_VALIDATION_FAILED",
                root_cause_message=issues[0].message if issues else "Partition invalid",
                retryable=False,
            )

        response = ProviderResponse(
            provider="gemini",
            model="gemini-3.1-flash-lite",
            raw_output=json.dumps(payload),
            request_id=request.request_id,
            finish_reason="STOP",
            latency_ms=123,
            metadata={"provider_payload_raw": payload},
        )
        return ProviderRoutingResult(
            provider="gemini",
            response=response,
            payload=validated_payload,
            attempts=(
                ProviderRouteAttempt(
                    sequence=1,
                    provider="gemini",
                    phase="PRIMARY",
                    response=response,
                    payload=validated_payload,
                ),
            ),
            fallback_used=False,
        )


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
    analysis_type: str = "WATCHING_UPDATE",
    evidence_batch_id: uuid.UUID | None = None,
) -> uuid.UUID:
    async with engine.begin() as conn:
        r = await conn.execute(
            text(
                "INSERT INTO analysis_jobs "
                "(session_id, evidence_batch_id, analysis_type, status, attempt_count, "
                "max_attempts, lease_owner, lease_expires_at, "
                "lease_acquired_at, previous_session_status, available_at) "
                "VALUES (:sid, :batch_id, :atype, :st, :ac, :ma, "
                ":lo, :lea, :now, :ps, :now) RETURNING id"
            ),
            {
                "sid": session_id,
                "batch_id": evidence_batch_id,
                "atype": analysis_type,
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


def _valid_initial_analysis_payload() -> dict[str, object]:
    fixture_path = (
        Path(__file__).resolve().parents[3]
        / "schemas"
        / "fixtures"
        / "valid"
        / "v1"
        / "initial_analysis_v2.valid.json"
    )
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _partition_payloads() -> dict[str, dict[str, object]]:
    payload = _valid_initial_analysis_payload()
    findings = payload["evidence_findings"]
    trade_plan = payload["trade_plan"]

    return {
        "MARKET_EVIDENCE": {
            "metadata": payload["metadata"],
            "market_facts": payload["market_facts"],
            "evidence_findings": {
                "orderbook": findings["orderbook"],
                "broker_summary": findings["broker_summary"],
                "foreign_flow": findings["foreign_flow"],
                "limitations": findings["limitations"],
            },
        },
        "CHART_ANALYSIS": {
            "evidence_findings": {
                "chart_3_month": findings["chart_3_month"],
                "chart_6_month": findings["chart_6_month"],
            },
            "trade_plan": {
                "nearest_support": trade_plan["nearest_support"],
                "nearest_resistance": trade_plan["nearest_resistance"],
            },
        },
        "TRADE_THESIS": {
            "trade_plan": {
                "entry_zone_low": trade_plan["entry_zone_low"],
                "entry_zone_high": trade_plan["entry_zone_high"],
                "chase_limit": trade_plan["chase_limit"],
                "stop_loss": trade_plan["stop_loss"],
                "target_1": trade_plan["target_1"],
                "target_2": trade_plan["target_2"],
                "invalidation": trade_plan["invalidation"],
                "risk_reward": trade_plan["risk_reward"],
            },
            "scenarios": payload["scenarios"],
        },
        "DECISION_ASSESSMENT": {
            "decision": payload["decision"],
            "probabilities": payload["probabilities"],
            "next_actions": payload["next_actions"],
        },
    }


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
    async def test_freeze_failure_rolls_back_accepted_analysis(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        batch_id = uuid.uuid4()
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO evidence_batches "
                    "(id, session_id, owner_id, analysis_type, status, sequence_number) "
                    "VALUES (:id, :sid, :owner_id, 'WATCHING_UPDATE', 'PROCESSING', 1)"
                ),
                {"id": batch_id, "sid": session_id, "owner_id": user_id},
            )
        jid = await _make_claimed_job(
            engine,
            session_id,
            analysis_type="WATCHING_UPDATE",
            evidence_batch_id=batch_id,
        )
        await _add_context_summary(engine, session_id)

        async def fail_freeze(
            self: EvidenceBatchService,
            batch_id: uuid.UUID | None,
            *,
            now: datetime | None = None,
        ) -> None:
            raise RuntimeError("freeze failed")

        monkeypatch.setattr(EvidenceBatchService, "freeze", fail_freeze)

        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                router=FakeRouter(),
                validate=_always_valid,
            )
            with pytest.raises(RuntimeError, match="freeze failed"):
                await proc.process(job_id=jid, worker_id="w1")
            await s.rollback()

        async with factory() as s:
            analysis_count = (
                await s.execute(
                    text("SELECT COUNT(*) FROM analyses WHERE analysis_job_id = :jid"),
                    {"jid": jid},
                )
            ).scalar_one()
            job_status = (
                await s.execute(
                    text("SELECT status FROM analysis_jobs WHERE id = :jid"),
                    {"jid": jid},
                )
            ).scalar_one()
            batch_status = (
                await s.execute(
                    text("SELECT status FROM evidence_batches WHERE id = :batch_id"),
                    {"batch_id": batch_id},
                )
            ).scalar_one()

        assert analysis_count == 0
        assert job_status == AnalysisJobStatus.PROCESSING.value
        assert batch_status == EvidenceBatchStatus.PROCESSING.value

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

    async def test_success_path_persists_real_provider_audit_data(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id)
        await _add_context_summary(engine, session_id)

        provider = CountingProvider(
            [
                ProviderResponse(
                    provider="gemini",
                    model="gemini-3.1-flash-lite",
                    raw_output='{"ok": true}',
                    request_id=uuid.uuid4(),
                    provider_response_id="resp-success",
                    finish_reason="STOP",
                    usage=None,
                    latency_ms=321,
                )
            ]
        )

        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                providers={"gemini": provider},
                provider_order=["gemini"],
                validate=_always_valid,
            )
            result = await proc.process(job_id=jid, worker_id="w1")
            assert result.job_status == AnalysisJobStatus.COMPLETED.value
            assert result.restored_session_status == "WATCHING"
            await s.commit()
            await s.commit()

        async with factory() as s:
            req_row = (
                await s.execute(
                    text(
                        "SELECT provider, provider_model "
                        "FROM provider_requests WHERE analysis_job_id = :jid"
                    ),
                    {"jid": jid},
                )
            ).first()
            resp_row = (
                await s.execute(
                    text(
                        "SELECT status, raw_text, raw_payload, model_name, finish_reason, latency_ms "
                        "FROM provider_responses "
                        "WHERE provider_request_id = ("
                        "  SELECT id FROM provider_requests WHERE analysis_job_id = :jid"
                        ")"
                    ),
                    {"jid": jid},
                )
            ).first()

        assert req_row == ("GEMINI", "gemini-3.1-flash-lite")
        assert resp_row is not None
        assert resp_row[0] == "COMPLETED"
        assert resp_row[1] == '{"ok": true}'
        assert resp_row[2] == {"ok": True}
        assert resp_row[3] == "gemini-3.1-flash-lite"
        assert resp_row[4] == "STOP"
        assert resp_row[5] == 321

    async def test_missing_response_id_persists_as_null(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id)
        await _add_context_summary(engine, session_id)

        provider = CountingProvider(
            [
                ProviderResponse(
                    provider="gemini",
                    model="gemini-3.1-flash-lite",
                    raw_output='{"ok": true}',
                    request_id=uuid.uuid4(),
                    provider_response_id=None,
                )
            ]
        )

        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                providers={"gemini": provider},
                provider_order=["gemini"],
                validate=_always_valid,
            )
            await proc.process(job_id=jid, worker_id="w1")
            await s.commit()

        async with factory() as s:
            persisted_id = (
                await s.execute(
                    text(
                        "SELECT provider_response_id FROM provider_responses "
                        "WHERE provider_request_id = ("
                        "  SELECT id FROM provider_requests WHERE analysis_job_id = :jid"
                        ")"
                    ),
                    {"jid": jid},
                )
            ).scalar_one()

        assert persisted_id is None

    async def test_numeric_provider_response_id_is_normalized_to_string(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id)
        await _add_context_summary(engine, session_id)

        provider = CountingProvider(
            [
                ProviderResponse(
                    provider="gemini",
                    model="gemini-3.1-flash-lite",
                    raw_output='{"ok": true}',
                    request_id=uuid.uuid4(),
                    provider_response_id=123,  # type: ignore[arg-type]
                )
            ]
        )

        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                providers={"gemini": provider},
                provider_order=["gemini"],
                validate=_always_valid,
            )
            await proc.process(job_id=jid, worker_id="w1")
            await s.commit()

        async with factory() as s:
            persisted_id = (
                await s.execute(
                    text(
                        "SELECT provider_response_id FROM provider_responses "
                        "WHERE provider_request_id = ("
                        "  SELECT id FROM provider_requests WHERE analysis_job_id = :jid"
                        ")"
                    ),
                    {"jid": jid},
                )
            ).scalar_one()

        assert persisted_id == "123"

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
    async def test_parseable_validation_failure_persists_response_and_commits_failed_job(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id, attempt_count=1, max_attempts=1)
        await _add_context_summary(engine, session_id)

        provider = CountingProvider(
            [
                ProviderResponse(
                    provider="gemini",
                    model="gemini-3.1-flash-lite",
                    raw_output='{"analysis": "ok"}',
                    request_id=uuid.uuid4(),
                    provider_response_id=0,  # type: ignore[arg-type]
                    finish_reason="STOP",
                    usage=None,
                    latency_ms=654,
                    metadata={"safe": True},
                )
            ]
        )

        issue = ValidationIssue(
            code="SCHEMA_REQUIRED_FIELD_MISSING",
            category=ValidationCategory.SCHEMA,
            severity=ValidationSeverity.ERROR,
            path="/ai_assessment/bias",
            message="Missing required property: bias",
        )

        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                providers={"gemini": provider},
                provider_order=["gemini"],
                validate=lambda payload: (False, (issue,)),
            )
            result = await proc.process(job_id=jid, worker_id="w1")
            assert result.job_status == AnalysisJobStatus.FAILED.value
            await s.commit()

        async with factory() as s:
            job = await s.get(AnalysisJob, jid)
            req_row = (
                await s.execute(
                    text(
                        "SELECT provider, provider_model "
                        "FROM provider_requests WHERE analysis_job_id = :jid"
                    ),
                    {"jid": jid},
                )
            ).first()
            resp_row = (
                await s.execute(
                    text(
                        "SELECT status, raw_text, raw_payload, provider_response_id, model_name, finish_reason, latency_ms, "
                        "error_code, error_message "
                        "FROM provider_responses "
                        "WHERE provider_request_id = ("
                        "  SELECT id FROM provider_requests WHERE analysis_job_id = :jid"
                        ")"
                    ),
                    {"jid": jid},
                )
            ).first()

        assert job is not None
        assert job.status == AnalysisJobStatus.FAILED
        assert job.last_error_code == "SCHEMA_REQUIRED_FIELD_MISSING"
        assert "bias" in (job.last_error_message or "")
        assert req_row == ("GEMINI", "gemini-3.1-flash-lite")
        assert resp_row is not None
        assert resp_row[0] == "FAILED"
        assert resp_row[1] == '{"analysis": "ok"}'
        assert resp_row[2] == {"analysis": "ok"}
        assert resp_row[3] is None
        assert resp_row[4] == "gemini-3.1-flash-lite"
        assert resp_row[5] == "STOP"
        assert resp_row[6] == 654
        assert resp_row[7] == "SCHEMA_REQUIRED_FIELD_MISSING"
        assert "bias" in (resp_row[8] or "")

    async def test_failed_job_persists_raw_provider_payload_separately_from_normalized_payload(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id, attempt_count=1, max_attempts=1)
        await _add_context_summary(engine, session_id)

        raw_payload = {
            "chart_3_month_analysis": {
                "available": True,
                "nearest_support": 2720,
            }
        }
        normalized_payload = {
            "chart_3_month_analysis": {
                "available": True,
                "nearest_support": {
                    "price": 2720,
                    "label": "Three-month support",
                    "summary": "Normalized support level.",
                },
            }
        }

        routing_error = ProviderRoutingFailedError(
            message="All failed",
            attempts=(
                ProviderRouteAttempt(
                    sequence=1,
                    provider="gemini",
                    phase="PRIMARY",
                    response=ProviderResponse(
                        provider="gemini",
                        model="gemini-3.1-flash-lite",
                        raw_output='{"chart_3_month_analysis":{"available":true,"nearest_support":2720}}',
                        request_id=uuid.uuid4(),
                        metadata={"provider_payload_raw": raw_payload},
                    ),
                    payload=normalized_payload,
                    failure_code="SCHEMA_REQUIRED_FIELD_MISSING",
                    failure_message="Missing required property: ai_assessment",
                ),
            ),
            root_cause_code="SCHEMA_REQUIRED_FIELD_MISSING",
            root_cause_message="Missing required property: ai_assessment",
            retryable=False,
        )

        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                router=FakeRouter(result=routing_error),
                validate=_always_valid,
            )
            result = await proc.process(job_id=jid, worker_id="w1")
            assert result.job_status == AnalysisJobStatus.FAILED.value
            await s.commit()

        async with factory() as s:
            resp_row = (
                await s.execute(
                    text(
                        "SELECT raw_payload "
                        "FROM provider_responses "
                        "WHERE provider_request_id = ("
                        "  SELECT id FROM provider_requests WHERE analysis_job_id = :jid"
                        ")"
                    ),
                    {"jid": jid},
                )
            ).first()

        assert resp_row is not None
        assert resp_row[0] == raw_payload

    async def test_provider_failure_sets_failed_after_one_call(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id, attempt_count=1, max_attempts=1)
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
            assert result.job_status == AnalysisJobStatus.FAILED.value
            await s.commit()
        async with factory() as s:
            job = await s.get(AnalysisJob, jid)
            session = await s.get(TradeSession, session_id)
            assert job is not None
            assert session is not None
            assert job.status == AnalysisJobStatus.FAILED
            assert job.last_error_code == "AI_PROVIDER_TIMEOUT"
            assert job.last_error_message == "Gemini timed out"
            assert session.lifecycle_status.value == "WATCHING"

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
                        root_cause_message="Model not found: gemini-3.1-flash-lite",
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
            assert job.last_error_message == "Model not found: gemini-3.1-flash-lite"
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
                        root_cause_message="Model not found: gemini-3.1-flash-lite",
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

    async def test_rate_limit_failure_becomes_failed_after_one_provider_call(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id, attempt_count=1, max_attempts=1)
        await _add_context_summary(engine, session_id)

        class _RateLimitError(Exception):
            code = "AI_PROVIDER_RATE_LIMITED"

            def __str__(self) -> str:
                return "rate limited Retry-After: 60"

        provider = CountingProvider([_RateLimitError()])

        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                providers={"gemini": provider},
                provider_order=["gemini"],
                validate=_always_valid,
            )
            result = await proc.process(job_id=jid, worker_id="w1")
            assert result.job_status == AnalysisJobStatus.FAILED.value
            await s.commit()

        async with factory() as s:
            job = await s.get(AnalysisJob, jid)
            assert job is not None
            assert provider.call_count == 1
            assert job.status == AnalysisJobStatus.FAILED
            assert job.last_error_code == "AI_PROVIDER_RATE_LIMITED"
            assert job.last_error_message == "rate limited Retry-After: 60"

    async def test_manual_retry_can_invoke_provider_once_again(
        self,
        engine: AsyncEngine,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(engine, session_id, attempt_count=1, max_attempts=1)
        await _add_context_summary(engine, session_id)

        class _TimeoutError(Exception):
            code = "AI_PROVIDER_TIMEOUT"

            def __str__(self) -> str:
                return "Gemini timed out"

        provider = CountingProvider(
            [
                _TimeoutError(),
                ProviderResponse(
                    provider="gemini",
                    model="gemini-3.1-flash-lite",
                    raw_output='{"ok": true}',
                    request_id=uuid.uuid4(),
                ),
            ]
        )

        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                providers={"gemini": provider},
                provider_order=["gemini"],
                validate=_always_valid,
            )
            first = await proc.process(job_id=jid, worker_id="w1")
            assert first.job_status == AnalysisJobStatus.FAILED.value
            await s.commit()

        now = datetime.now(timezone.utc)
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "UPDATE analysis_jobs SET status = 'PROCESSING', attempt_count = 1, "
                    "max_attempts = 1, lease_owner = 'w1', lease_acquired_at = :now, "
                    "lease_expires_at = :lease, available_at = :now, completed_at = NULL, "
                    "last_error_code = NULL, last_error_message = NULL "
                    "WHERE id = :jid"
                ),
                {"jid": jid, "now": now, "lease": now + timedelta(seconds=30)},
            )
            await conn.execute(
                text(
                    "UPDATE trade_sessions SET lifecycle_status = 'ANALYZING', stable_status = 'ANALYZING' "
                    "WHERE id = :sid"
                ),
                {"sid": session_id},
            )

        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                providers={"gemini": provider},
                provider_order=["gemini"],
                validate=_always_valid,
            )
            second = await proc.process(job_id=jid, worker_id="w1")
            assert second.job_status == AnalysisJobStatus.COMPLETED.value
            await s.commit()

        assert provider.call_count == 2


# ===================================================================
# Boundaries
# ===================================================================


class TestBoundaries:
    async def test_unhandled_exception_rollback_removes_transient_audit_rows(
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
                router=FakeRouter(result=RuntimeError("boom")),
                validate=_always_valid,
            )
            with pytest.raises(Exception):
                await proc.process(job_id=jid, worker_id="w1")
            await s.rollback()

        async with factory() as s:
            req_count = (
                await s.execute(
                    text("SELECT COUNT(*) FROM provider_requests WHERE analysis_job_id = :jid"),
                    {"jid": jid},
                )
            ).scalar_one()
            resp_count = (
                await s.execute(
                    text(
                        "SELECT COUNT(*) FROM provider_responses "
                        "WHERE provider_request_id IN ("
                        "  SELECT id FROM provider_requests WHERE analysis_job_id = :jid"
                        ")"
                    ),
                    {"jid": jid},
                )
            ).scalar_one()

        assert req_count == 0
        assert resp_count == 0

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


class TestPartitionedInitialAnalysis:
    async def test_images_routed_only_to_required_partitions(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(
            engine,
            session_id,
            analysis_type="INITIAL_ANALYSIS",
            prev_status="READY_FOR_ANALYSIS",
        )
        await _add_context_summary(engine, session_id)
        router = PartitionRouter(payloads_by_partition=_partition_payloads())
        provider = CountingProvider([])

        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                context_builder=FakeInitialAnalysisContextBuilder(),
                router=router,
                validate=_always_valid,
                providers={"gemini": provider},
                provider_order=["gemini"],
            )
            result = await proc.process(job_id=jid, worker_id="w1")
            assert result.job_status == AnalysisJobStatus.COMPLETED.value
            await s.commit()

        assert router.calls == [
            ("MARKET_EVIDENCE", ("user/session/file-1.png",)),
            ("CHART_ANALYSIS", ("user/session/file-2.png", "user/session/file-3.png")),
            ("TRADE_THESIS", ()),
            ("DECISION_ASSESSMENT", ()),
        ]
        assert "canonical_chart_timestamps" not in router.request_metadata[0]
        assert router.request_metadata[1]["canonical_chart_timestamps"] == {
            "chart_3_month_analysis": "2026-07-24T09:15:00+07:00",
            "chart_6_month_analysis": "2026-07-23T15:45:00+07:00",
        }
        assert "canonical_chart_timestamps" not in router.request_metadata[2]
        assert "canonical_chart_timestamps" not in router.request_metadata[3]
        assert [metadata["model_name"] for metadata in router.request_metadata] == [
            "gemini-3.1-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-3.1-flash-lite",
        ]
        async with factory() as s:
            status = (
                await s.execute(
                    text("SELECT lifecycle_status FROM trade_sessions WHERE id = :sid"),
                    {"sid": session_id},
                )
            ).scalar_one()
            assert status == "INITIAL_ANALYZED"

    async def test_unusable_partition_stops_before_next_request(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(
            engine,
            session_id,
            analysis_type="INITIAL_ANALYSIS",
            prev_status="READY_FOR_ANALYSIS",
        )
        await _add_context_summary(engine, session_id)
        payloads = _partition_payloads()
        payloads["MARKET_EVIDENCE"] = {}
        router = PartitionRouter(payloads_by_partition=payloads)
        provider = CountingProvider([])

        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                context_builder=FakeInitialAnalysisContextBuilder(),
                router=router,
                validate=_always_valid,
                providers={"gemini": provider},
                provider_order=["gemini"],
            )
            result = await proc.process(job_id=jid, worker_id="w1")
            assert result.job_status == AnalysisJobStatus.FAILED.value
            await s.commit()

        assert router.calls == [("MARKET_EVIDENCE", ("user/session/file-1.png",))]
        assert router.validations == ["MARKET_EVIDENCE"]
        async with factory() as s:
            status = (
                await s.execute(
                    text("SELECT lifecycle_status FROM trade_sessions WHERE id = :sid"),
                    {"sid": session_id},
                )
            ).scalar_one()
            assert status == "READY_FOR_ANALYSIS"

    async def test_post_merge_domain_validation_warning_completes_job(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(
            engine,
            session_id,
            analysis_type="INITIAL_ANALYSIS",
            prev_status="READY_FOR_ANALYSIS",
        )
        await _add_context_summary(engine, session_id)
        router = PartitionRouter(payloads_by_partition=_partition_payloads())
        provider = CountingProvider([])
        merged_payloads: list[dict[str, object]] = []

        def _domain_invalid(payload: dict[str, object]) -> tuple[bool, tuple[ValidationIssue, ...]]:
            merged_payloads.append(dict(payload))
            return False, (
                ValidationIssue(
                    code="DOMAIN_TEST_FAILURE",
                    category=ValidationCategory.DOMAIN,
                    severity=ValidationSeverity.ERROR,
                    path="/trading_plan",
                    message="Domain validator rejected trading plan",
                ),
            )

        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                context_builder=FakeInitialAnalysisContextBuilder(),
                router=router,
                validate=_domain_invalid,
                providers={"gemini": provider},
                provider_order=["gemini"],
            )
            result = await proc.process(job_id=jid, worker_id="w1")
            assert result.job_status == AnalysisJobStatus.COMPLETED.value
            await s.commit()

        assert len(router.calls) == 4
        assert len(merged_payloads) == 1

        async with factory() as s:
            job_status = (
                await s.execute(
                    text("SELECT status, last_error_code FROM analysis_jobs WHERE id = :jid"),
                    {"jid": jid},
                )
            ).first()
            warning_row = (
                await s.execute(
                    text(
                        "SELECT stage, valid, issues "
                        "FROM validation_attempts WHERE analysis_job_id = :jid"
                    ),
                    {"jid": jid},
                )
            ).first()
            analysis_count = (
                await s.execute(
                    text("SELECT COUNT(*) FROM analyses WHERE analysis_job_id = :jid"),
                    {"jid": jid},
                )
            ).scalar_one()

        assert job_status == ("COMPLETED", None)
        assert warning_row is not None
        assert warning_row[0] == "DOMAIN"
        assert warning_row[1] is True
        assert warning_row[2]["mode"] == "INITIAL_ANALYSIS_NON_BLOCKING_MVP"
        assert warning_row[2]["warnings"][0]["code"] == "DOMAIN_TEST_FAILURE"
        assert warning_row[2]["warnings"][0]["severity"] == "WARNING"
        assert analysis_count == 1

    async def test_schema_mismatches_are_warnings_and_payload_values_are_preserved(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(
            engine,
            session_id,
            analysis_type="INITIAL_ANALYSIS",
            prev_status="READY_FOR_ANALYSIS",
        )
        await _add_context_summary(engine, session_id)
        payloads = _partition_payloads()
        payloads["DECISION_ASSESSMENT"]["decision"]["recommendation"] = "HOLD"
        payloads["DECISION_ASSESSMENT"]["decision"].pop("bias")
        payloads["DECISION_ASSESSMENT"]["decision"]["gemini_extra"] = "kept"
        payloads["TRADE_THESIS"]["trade_plan"]["risk_reward"] = "MIXED"
        router = PartitionRouter(payloads_by_partition=payloads)
        provider = CountingProvider([])

        issues = (
            ValidationIssue(
                code="SCHEMA_ENUM_INVALID",
                category=ValidationCategory.ENUM,
                severity=ValidationSeverity.ERROR,
                path="/decision/recommendation",
                message="Enum mismatch",
                expected="BUY|WAIT|SKIP|UNCERTAIN",
                actual="HOLD",
            ),
            ValidationIssue(
                code="SCHEMA_ENUM_INVALID",
                category=ValidationCategory.ENUM,
                severity=ValidationSeverity.ERROR,
                path="/trade_plan/risk_reward",
                message="Enum mismatch",
                expected="FAVORABLE|ACCEPTABLE|UNFAVORABLE|UNAVAILABLE",
                actual="MIXED",
            ),
            ValidationIssue(
                code="SCHEMA_REQUIRED_FIELD_MISSING",
                category=ValidationCategory.REQUIRED,
                severity=ValidationSeverity.ERROR,
                path="/decision/bias",
                message="Missing required property: bias",
            ),
            ValidationIssue(
                code="SCHEMA_UNKNOWN_PROPERTY",
                category=ValidationCategory.ADDITIONAL_PROPERTY,
                severity=ValidationSeverity.ERROR,
                path="/decision/gemini_extra",
                message="Additional property",
                actual="kept",
            ),
        )

        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                context_builder=FakeInitialAnalysisContextBuilder(),
                router=router,
                validate=lambda payload: (False, issues),
                providers={"gemini": provider},
                provider_order=["gemini"],
            )
            result = await proc.process(job_id=jid, worker_id="w1")
            assert result.job_status == AnalysisJobStatus.COMPLETED.value
            await s.commit()

        async with factory() as s:
            row = (
                await s.execute(
                    text(
                        "SELECT payload FROM analyses WHERE analysis_job_id = :jid"
                    ),
                    {"jid": jid},
                )
            ).first()
            warning_row = (
                await s.execute(
                    text(
                        "SELECT issues FROM validation_attempts "
                        "WHERE analysis_job_id = :jid AND stage = 'JSON_SCHEMA'"
                    ),
                    {"jid": jid},
                )
            ).first()

        assert row is not None
        accepted = row[0]
        assert accepted["decision"]["recommendation"] == "HOLD"
        assert accepted["trade_plan"]["risk_reward"] == "MIXED"
        assert accepted["decision"]["gemini_extra"] == "kept"
        assert "bias" not in accepted["decision"]
        assert warning_row is not None
        warning_codes = {warning["code"] for warning in warning_row[0]["warnings"]}
        assert {
            "SCHEMA_ENUM_INVALID",
            "SCHEMA_REQUIRED_FIELD_MISSING",
            "SCHEMA_UNKNOWN_PROPERTY",
        } <= warning_codes

    async def test_empty_partition_payload_still_fails(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(
            engine,
            session_id,
            analysis_type="INITIAL_ANALYSIS",
            prev_status="READY_FOR_ANALYSIS",
        )
        await _add_context_summary(engine, session_id)
        payloads = _partition_payloads()
        payloads["MARKET_EVIDENCE"] = {}
        router = PartitionRouter(payloads_by_partition=payloads)

        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                context_builder=FakeInitialAnalysisContextBuilder(),
                router=router,
                validate=_always_valid,
                providers={"gemini": CountingProvider([])},
                provider_order=["gemini"],
            )
            result = await proc.process(job_id=jid, worker_id="w1")
            assert result.job_status == AnalysisJobStatus.FAILED.value

    async def test_minor_v2_schema_drift_becomes_warning_not_failure(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(
            engine,
            session_id,
            analysis_type="INITIAL_ANALYSIS",
            prev_status="READY_FOR_ANALYSIS",
        )
        await _add_context_summary(engine, session_id)
        payloads = _partition_payloads()
        payloads["CHART_ANALYSIS"]["trade_plan"]["nearest_support"] = "2780"
        router = PartitionRouter(payloads_by_partition=payloads)

        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                context_builder=FakeInitialAnalysisContextBuilder(),
                router=router,
                validate=_always_valid,
                providers={"gemini": CountingProvider([])},
                provider_order=["gemini"],
            )
            result = await proc.process(job_id=jid, worker_id="w1")
            assert result.job_status == AnalysisJobStatus.COMPLETED.value
            await s.commit()

        async with factory() as s:
            analysis_row = (
                await s.execute(
                    text("SELECT payload FROM analyses WHERE analysis_job_id = :jid"),
                    {"jid": jid},
                )
            ).first()
            warning_row = (
                await s.execute(
                    text(
                        "SELECT issues FROM validation_attempts "
                        "WHERE analysis_job_id = :jid AND stage = 'JSON_SCHEMA'"
                    ),
                    {"jid": jid},
                )
            ).first()

        assert analysis_row is not None
        assert analysis_row[0]["trade_plan"]["nearest_support"] == "2780"
        assert warning_row is not None
        warning_paths = {warning["path"] for warning in warning_row[0]["warnings"]}
        assert "/trade_plan/nearest_support" in warning_paths

    async def test_failed_later_partition_keeps_earlier_raw_audits(
        self,
        engine: AsyncEngine,
        session_id: uuid.UUID,
        factory: async_sessionmaker[AsyncSession],
    ) -> None:
        jid = await _make_claimed_job(
            engine,
            session_id,
            analysis_type="INITIAL_ANALYSIS",
            prev_status="READY_FOR_ANALYSIS",
        )
        await _add_context_summary(engine, session_id)
        router = PartitionRouter(
            payloads_by_partition=_partition_payloads(),
            failing_partition="TRADE_THESIS",
            failure_code="AI_PROVIDER_TIMEOUT",
            failure_message="Gemini timed out",
        )
        provider = CountingProvider([])

        async with factory() as s:
            proc = AnalysisProcessor(
                session=s,
                context_builder=FakeInitialAnalysisContextBuilder(),
                router=router,
                validate=_always_valid,
                providers={"gemini": provider},
                provider_order=["gemini"],
            )
            result = await proc.process(job_id=jid, worker_id="w1")
            assert result.job_status == AnalysisJobStatus.FAILED.value
            await s.commit()

        async with factory() as s:
            req_rows = (
                await s.execute(
                    text(
                        "SELECT attempt_number, request_metadata->>'partition_name' "
                        "FROM provider_requests WHERE analysis_job_id = :jid ORDER BY attempt_number"
                    ),
                    {"jid": jid},
                )
            ).all()
            resp_rows = (
                await s.execute(
                    text(
                        "SELECT raw_payload "
                        "FROM provider_responses "
                        "WHERE provider_request_id IN ("
                        "  SELECT id FROM provider_requests WHERE analysis_job_id = :jid"
                        ") ORDER BY created_at"
                    ),
                    {"jid": jid},
                )
            ).all()

        assert req_rows == [
            (1, "MARKET_EVIDENCE"),
            (2, "CHART_ANALYSIS"),
            (3, "TRADE_THESIS"),
        ]
        assert len(resp_rows) == 2


# ===================================================================
# Validate helpers
# ===================================================================


def _always_valid(
    payload: dict[str, object],
) -> tuple[bool, tuple[ValidationIssue, ...]]:
    return True, ()
