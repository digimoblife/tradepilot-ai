"""Analysis Processor (TP-0804).

Processes one already-claimed Analysis Job from context construction
through validated Analysis persistence and job/session completion.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context_builder import (
    ProviderContextBuilder,
    ProviderContextStaleError,
)
from app.ai.providers import (
    AIProvider,
    ProviderCapabilities,
)
from app.ai.providers import (
    ProviderRequest as ProviderRequestModel,
)
from app.ai.providers.router import (
    ProviderRouter,
    ProviderRoutingFailedError,
    ProviderRoutingResult,
)
from app.context import ContextFreshnessService
from app.logging import get_logger
from app.models.analysis import Analysis
from app.models.analysis_job import AnalysisJob
from app.models.enums import (
    AcceptanceStatus,
    AnalysisJobStatus,
    ProviderResponseStatus,
    ProviderType,
    TradeSessionStatus,
)
from app.models.provider_request import ProviderRequest as DBProviderRequest
from app.models.provider_response import ProviderResponse as DBProviderResponse
from app.models.trade_session import TradeSession
from app.services.context_rebuild import ContextRebuildReason, ContextRebuildService
from app.validation import ValidationIssue

# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AnalysisProcessingResult:
    job_id: uuid.UUID
    session_id: uuid.UUID
    analysis_id: uuid.UUID | None
    job_status: str
    restored_session_status: str | None
    provider: str | None
    fallback_used: bool
    error_code: str | None = None
    error_message: str | None = None


# ---------------------------------------------------------------------------
# Stable errors
# ---------------------------------------------------------------------------


class AnalysisProcessorError(Exception):
    code: str = "ANALYSIS_PROCESSOR_ERROR"

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class AnalysisProcessorJobNotFoundError(AnalysisProcessorError):
    code: str = "ANALYSIS_PROCESSOR_JOB_NOT_FOUND"


class AnalysisProcessorJobNotClaimedError(AnalysisProcessorError):
    code: str = "ANALYSIS_PROCESSOR_JOB_NOT_CLAIMED"


class AnalysisProcessorLeaseNotOwnedError(AnalysisProcessorError):
    code: str = "ANALYSIS_PROCESSOR_LEASE_NOT_OWNED"


class AnalysisProcessorLeaseExpiredError(AnalysisProcessorError):
    code: str = "ANALYSIS_PROCESSOR_LEASE_EXPIRED"


class AnalysisProcessorSessionInvalidError(AnalysisProcessorError):
    code: str = "ANALYSIS_PROCESSOR_SESSION_INVALID"


class AnalysisProcessorAlreadyTerminalError(AnalysisProcessorError):
    code: str = "ANALYSIS_PROCESSOR_ALREADY_TERMINAL"


class AnalysisProcessorPersistenceFailedError(AnalysisProcessorError):
    code: str = "ANALYSIS_PROCESSOR_PERSISTENCE_FAILED"


class AnalysisProcessorContextRebuildFailedError(AnalysisProcessorError):
    code: str = "PROVIDER_CONTEXT_REBUILD_FAILED"


# ---------------------------------------------------------------------------
# Processor
# ---------------------------------------------------------------------------


class AnalysisProcessor:
    """Processes one claimed Analysis Job through the full analysis pipeline."""

    def __init__(
        self,
        session: AsyncSession,
        context_builder: ProviderContextBuilder | None = None,
        router: ProviderRouter | None = None,
        validate: Callable[
            [dict[str, object]],
            tuple[bool, tuple[ValidationIssue, ...]],
        ]
        | None = None,
        providers: Mapping[str, AIProvider] | None = None,
        provider_order: Sequence[str] | None = None,
        max_repair_attempts: int = 2,
    ) -> None:
        self._log = get_logger(__name__)
        self._session = session
        self._context_builder = context_builder or ProviderContextBuilder(session)
        self._router = router or ProviderRouter()
        self._validate = validate or _always_invalid
        self._providers = providers or {}
        self._provider_order = list(provider_order or [])
        self._max_repair = max_repair_attempts

    async def process(
        self,
        *,
        job_id: uuid.UUID,
        worker_id: str,
    ) -> AnalysisProcessingResult:
        job = await self._session.get(AnalysisJob, job_id)
        if job is None:
            raise AnalysisProcessorJobNotFoundError(
                message=f"Analysis job {job_id} not found",
            )

        if job.status in (
            AnalysisJobStatus.COMPLETED,
            AnalysisJobStatus.FAILED,
            AnalysisJobStatus.CANCELLED,
        ):
            raise AnalysisProcessorAlreadyTerminalError(
                message=f"Job {job_id} is already terminal ({job.status.value})",
            )

        if job.status != AnalysisJobStatus.PROCESSING:
            raise AnalysisProcessorJobNotClaimedError(
                message=f"Job {job_id} is in status {job.status.value}, expected PROCESSING",
            )

        if job.lease_owner != worker_id:
            raise AnalysisProcessorLeaseNotOwnedError(
                message=f"Worker {worker_id!r} does not own lease for job {job_id}",
            )

        now = datetime.now(timezone.utc)
        if job.lease_expires_at is not None and job.lease_expires_at <= now:
            raise AnalysisProcessorLeaseExpiredError(
                message=f"Lease for job {job_id} has expired",
            )

        # Load linked session
        ts = await self._session.get(TradeSession, job.session_id)
        if ts is None or ts.lifecycle_status != TradeSessionStatus.ANALYZING:
            raise AnalysisProcessorSessionInvalidError(
                message="Session is not in ANALYZING state",
            )

        atype = (
            job.analysis_type.value
            if hasattr(job.analysis_type, "value")
            else str(job.analysis_type)
        )  # noqa: E501

        ctx = await self._build_fresh_provider_context(
            session_id=job.session_id,
            owner_id=ts.owner_id,
            analysis_type=atype,
            now=now,
        )

        # Create ProviderRequest DB record
        db_provider_request = DBProviderRequest(
            id=uuid.uuid4(),
            analysis_job_id=job_id,
            provider=ProviderType.MOCK,
            provider_model=None,
            attempt_number=1,
            prompt_name=atype,
            prompt_version=ctx.prompt_version,
            schema_name=ctx.expected_schema_name,
            schema_version=ctx.expected_schema_version,
            request_payload={
                "system_prompt": ctx.system_prompt,
                "user_prompt": ctx.user_prompt,
                "images": [img.storage_reference for img in ctx.images],
            },
            request_metadata=dict(ctx.metadata),
        )
        self._session.add(db_provider_request)

        # Create ProviderRequest for router
        router_request = ProviderRequestModel(
            request_id=uuid.uuid4(),
            analysis_type=atype,
            prompt_version=ctx.prompt_version,
            user_prompt=ctx.user_prompt,
            expected_schema_name=ctx.expected_schema_name,
            expected_schema_version=ctx.expected_schema_version,
            system_prompt=ctx.system_prompt,
            images=ctx.images,
            structured_output_schema=ctx.structured_output_schema,
        )
        await self._session.flush()  # ensure DB record exists before router call

        # Call router
        try:
            route_result = await self._router.generate_validated(
                request=router_request,
                providers=self._providers,
                provider_order=self._provider_order,
                validate=self._validate,
                canonical_facts=ctx.canonical_facts,
                max_repair_attempts=self._max_repair,
            )
        except ProviderRoutingFailedError as exc:
            await self._fail_job(job, exc, ts, now)
            await self._session.flush()
            self._log.warning(
                "Analysis routing failed",
                extra={
                    "analysis_job_id": str(job_id),
                    "session_id": str(job.session_id),
                    "job_status": job.status.value,
                    "root_cause_code": job.last_error_code,
                    "root_cause_message": job.last_error_message,
                },
            )
            return AnalysisProcessingResult(
                job_id=job_id,
                session_id=job.session_id,
                analysis_id=None,
                job_status=job.status.value,
                restored_session_status=(
                    job.previous_session_status
                    if job.status == AnalysisJobStatus.FAILED
                    else None
                ),
                provider=None,
                fallback_used=False,
                error_code=job.last_error_code,
                error_message=job.last_error_message,
            )
        except Exception:
            await self._fail_job(job, [], ts, atype, now)
            await self._session.flush()
            raise

        # Persist provider responses
        await self._persist_route_attempts(db_provider_request.id, route_result, atype)

        # Create accepted Analysis
        analysis_id = uuid.uuid4()
        analysis = Analysis(
            id=analysis_id,
            session_id=job.session_id,
            analysis_job_id=job_id,
            analysis_type=atype,
            acceptance_status=AcceptanceStatus.ACCEPTED,
            prompt_name=atype,
            prompt_version=ctx.prompt_version,
            schema_name=ctx.expected_schema_name,
            schema_version=ctx.expected_schema_version,
            payload=dict(route_result.payload),
            accepted_at=now,
        )
        self._session.add(analysis)

        # Complete job
        job.status = AnalysisJobStatus.COMPLETED
        job.completed_at = now
        job.lease_owner = None
        job.lease_acquired_at = None
        job.lease_expires_at = None

        # Restore session
        prev = job.previous_session_status
        if prev:
            try:
                restored = TradeSessionStatus(prev)
                ts.lifecycle_status = restored
                ts.stable_status = restored
            except ValueError:
                pass

        await self._session.flush()

        rebuild = ContextRebuildService(self._session)
        await rebuild.rebuild_after_material_event(
            session_id=job.session_id,
            owner_id=ts.owner_id,
            reason=ContextRebuildReason.ANALYSIS_ACCEPTED,
            source_id=analysis_id,
        )

        self._log.info(
            "Analysis job processed successfully",
            extra={
                "analysis_job_id": str(job_id),
                "session_id": str(job.session_id),
                "schema": ctx.expected_schema_name,
                "provider": route_result.provider,
                "model": getattr(route_result.response, "model", None),
            },
        )

        return AnalysisProcessingResult(
            job_id=job_id,
            session_id=job.session_id,
            analysis_id=analysis_id,
            job_status=AnalysisJobStatus.COMPLETED.value,
            restored_session_status=prev,
            provider=route_result.provider,
            fallback_used=route_result.fallback_used,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_primary_capabilities(self) -> ProviderCapabilities:
        if self._provider_order and self._providers:
            primary_name = self._provider_order[0]
            p = self._providers.get(primary_name)
            if p is not None:
                return p.capabilities
        return ProviderCapabilities()

    async def _build_fresh_provider_context(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        analysis_type: str,
        now: datetime,
    ) -> Any:
        capabilities = self._get_primary_capabilities()
        freshness = ContextFreshnessService(self._session)
        try:
            await freshness.ensure_fresh(session_id=session_id, owner_id=owner_id)
        except Exception as exc:
            raise AnalysisProcessorContextRebuildFailedError(
                code=getattr(exc, "code", None),
                message=f"Context Summary rebuild failed before analysis: {exc}",
            ) from exc

        try:
            return await self._context_builder.build(
                session_id=session_id,
                owner_id=owner_id,
                analysis_type=analysis_type,
                provider_capabilities=capabilities,
                now=now,
            )
        except ProviderContextStaleError:
            try:
                await freshness.ensure_fresh(session_id=session_id, owner_id=owner_id)
                return await self._context_builder.build(
                    session_id=session_id,
                    owner_id=owner_id,
                    analysis_type=analysis_type,
                    provider_capabilities=capabilities,
                    now=now,
                )
            except Exception as exc:
                raise AnalysisProcessorContextRebuildFailedError(
                    code=getattr(exc, "code", None),
                    message=f"Context Summary remained stale after rebuild: {exc}",
                ) from exc

    async def _persist_route_attempts(
        self,
        db_req_id: uuid.UUID,
        route_result: ProviderRoutingResult,
        analysis_type: str,
    ) -> None:
        for attempt in route_result.attempts:
            if attempt.response is None:
                continue
            raw = attempt.response

            try:
                ProviderType(raw.provider.upper())
            except ValueError:
                pass

            resp = DBProviderResponse(
                id=uuid.uuid4(),
                provider_request_id=db_req_id,
                status=ProviderResponseStatus.COMPLETED,
                raw_text=raw.raw_output,
                provider_response_id=raw.provider_response_id,
                model_name=raw.model,
                finish_reason=raw.finish_reason,
                latency_ms=raw.latency_ms,
                input_tokens=raw.usage.input_tokens if raw.usage else None,
                output_tokens=raw.usage.output_tokens if raw.usage else None,
                total_tokens=raw.usage.total_tokens if raw.usage else None,
                usage_metadata=(
                    {
                        "input_tokens": raw.usage.input_tokens,
                        "output_tokens": raw.usage.output_tokens,
                        "total_tokens": raw.usage.total_tokens,
                    }
                    if raw.usage
                    else None
                ),
            )
            self._session.add(resp)
        await self._session.flush()

    async def _fail_job(
        self,
        job: AnalysisJob,
        routing_error: ProviderRoutingFailedError,
        ts: TradeSession,
        now: datetime,
    ) -> None:
        error_code = routing_error.root_cause_code or routing_error.code
        error_message = routing_error.root_cause_message or routing_error.message
        attempts_remain = routing_error.retryable and job.attempt_count < job.max_attempts

        if attempts_remain:
            job.status = AnalysisJobStatus.RETRYING
            job.lease_owner = None
            job.lease_acquired_at = None
            job.lease_expires_at = None
            job.last_error_code = error_code
            job.last_error_message = error_message
            job.available_at = now
        else:
            job.status = AnalysisJobStatus.FAILED
            job.completed_at = now
            job.lease_owner = None
            job.lease_acquired_at = None
            job.lease_expires_at = None
            job.last_error_code = error_code
            job.last_error_message = error_message

            prev = job.previous_session_status
            if prev:
                try:
                    restored = TradeSessionStatus(prev)
                    ts.lifecycle_status = restored
                    ts.stable_status = restored
                except ValueError:
                    pass


def _always_invalid(
    payload: dict[str, object],
) -> tuple[bool, tuple[ValidationIssue, ...]]:
    return False, ()
