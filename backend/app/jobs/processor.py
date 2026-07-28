"""Analysis Processor (TP-0804).

Processes one already-claimed Analysis Job from context construction
through validated Analysis persistence and job/session completion.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Mapping, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.context_builder import (
    ProviderContextBuilder,
    ProviderContextStaleError,
)
from app.ai.initial_analysis_partitioning import (
    PARTITIONS,
    build_partition_schemas,
    build_partition_user_prompt,
    decimalize_json_numbers_for_validation,
    merge_partition_payloads,
    select_partition_images,
    validate_partition_payload,
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
from app.lifecycle.restoration import restore_session_status
from app.models.analysis import Analysis
from app.models.analysis_job import AnalysisJob
from app.models.enums import (
    AcceptanceStatus,
    AnalysisJobStatus,
    ProviderResponseStatus,
    ProviderType,
    TradeSessionStatus,
    ValidationStage,
)
from app.models.provider_request import ProviderRequest as DBProviderRequest
from app.models.provider_response import ProviderResponse as DBProviderResponse
from app.models.trade_session import TradeSession
from app.models.validation_attempt import ValidationAttempt
from app.services.context_rebuild import ContextRebuildReason, ContextRebuildService
from app.services.evidence_batches import EvidenceBatchService
from app.validation import ValidationCategory, ValidationIssue, ValidationSeverity

ValidationCallback = Callable[
    [dict[str, object]],
    tuple[bool, tuple[ValidationIssue, ...]],
]
ValidationCallbackFactory = Callable[
    ...,
    ValidationCallback,
]

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
        validate: ValidationCallback | None = None,
        validate_factory: ValidationCallbackFactory | None = None,
        providers: Mapping[str, AIProvider] | None = None,
        provider_order: Sequence[str] | None = None,
        max_repair_attempts: int = 0,
    ) -> None:
        self._log = get_logger(__name__)
        self._session = session
        self._context_builder = context_builder or ProviderContextBuilder(session)
        self._router = router or ProviderRouter()
        self._validate = validate or _always_invalid
        self._validate_factory = validate_factory
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
            evidence_batch_id=job.evidence_batch_id,
            now=now,
        )

        selected_provider_name, selected_provider_model = self._get_selected_provider_audit_values()

        validate = self._build_validate_callback(
            analysis_type=atype,
            session_status_before_job=job.previous_session_status,
            canonical_facts=ctx.canonical_facts,
        )

        if self._should_use_partitioned_initial_analysis(atype):
            return await self._process_partitioned_initial_analysis(
                job=job,
                ts=ts,
                ctx=ctx,
                now=now,
                selected_provider_name=selected_provider_name,
                selected_provider_model=selected_provider_model,
                validate=validate,
            )

        analysis_id = uuid.uuid4()
        request_metadata = dict(ctx.metadata)
        request_metadata.update(
            {
                "canonical_analysis_id": str(analysis_id),
                "canonical_analysis_timestamp": now.isoformat(),
                "provider_model": selected_provider_model,
                "canonical_facts": dict(ctx.canonical_facts),
                "ticker": ctx.canonical_facts.get("ticker"),
                "company_name": ctx.canonical_facts.get("company_name"),
            }
        )

        db_provider_request = self._create_provider_request_record(
            job_id=job_id,
            provider=selected_provider_name,
            provider_model=selected_provider_model,
            attempt_number=1,
            prompt_name=atype,
            prompt_version=ctx.prompt_version,
            schema_name=ctx.expected_schema_name,
            schema_version=ctx.expected_schema_version,
            system_prompt=ctx.system_prompt,
            user_prompt=ctx.user_prompt,
            images=ctx.images,
            metadata=request_metadata,
        )
        self._session.add(db_provider_request)

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
            metadata=request_metadata,
        )
        await self._session.flush()  # ensure DB record exists before router call

        # Call router
        try:
            route_result = await self._router.generate_validated(
                request=router_request,
                providers=self._providers,
                provider_order=self._provider_order,
                max_provider_attempts=1,
                validate=validate,
                canonical_facts=ctx.canonical_facts,
                max_repair_attempts=self._max_repair,
            )
        except ProviderRoutingFailedError as exc:
            await self._persist_route_attempts(
                db_provider_request.id,
                getattr(exc, "attempts", ()),
            )
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
        except Exception as exc:
            routing_error = ProviderRoutingFailedError(
                message=str(exc) or exc.__class__.__name__,
                root_cause_code=exc.__class__.__name__,
                root_cause_message=str(exc) or exc.__class__.__name__,
            )
            await self._fail_job(job, routing_error, ts, now)
            await self._session.flush()
            raise

        # Persist provider responses
        await self._persist_route_attempts(db_provider_request.id, route_result.attempts)

        # Create accepted Analysis
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

        prev = job.previous_session_status
        completion_status = _completion_status_for_analysis(atype, prev)
        if completion_status is not None:
            ts.lifecycle_status = completion_status
            ts.stable_status = completion_status

        await EvidenceBatchService(self._session).freeze(job.evidence_batch_id, now=now)
        await self._session.flush()

        rebuild = ContextRebuildService(self._session)
        await rebuild.rebuild_after_material_event(
            session_id=job.session_id,
            owner_id=ts.owner_id,
            reason=ContextRebuildReason.ANALYSIS_ACCEPTED,
            source_id=analysis_id,
        )

        try:
            from app.services.evaluation_records import EvaluationRecordService
            eval_svc = EvaluationRecordService(self._session)
            await eval_svc.record_prediction_from_analysis(analysis, ts)
            if atype == "CLOSING_ANALYSIS":
                tstate = await self._session.get(TradeState, job.session_id)
                await eval_svc.record_outcome_on_closure(ts, tstate)
        except Exception as eval_exc:
            self._log.warning(
                "Evaluation record projection error during analysis completion",
                extra={"session_id": str(job.session_id), "error": str(eval_exc)},
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
            restored_session_status=(
                completion_status.value if completion_status is not None else prev
            ),
            provider=route_result.provider,
            fallback_used=route_result.fallback_used,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_validate_callback(
        self,
        *,
        analysis_type: str,
        session_status_before_job: str | None,
        canonical_facts: Mapping[str, object],
    ) -> ValidationCallback:
        if self._validate_factory is None:
            return self._validate
        return self._validate_factory(
            analysis_type=analysis_type,
            session_status_before_job=session_status_before_job,
            canonical_facts=canonical_facts,
        )

    def _should_use_partitioned_initial_analysis(self, analysis_type: str) -> bool:
        if analysis_type != "INITIAL_ANALYSIS":
            return False
        if not self._provider_order:
            return False
        return self._provider_order[0] == "gemini"

    def _get_primary_capabilities(self) -> ProviderCapabilities:
        if self._provider_order and self._providers:
            primary_name = self._provider_order[0]
            p = self._providers.get(primary_name)
            if p is not None:
                return p.capabilities
        return ProviderCapabilities()

    def _get_selected_provider_audit_values(self) -> tuple[ProviderType, str | None]:
        if self._provider_order:
            selected_name = self._provider_order[0]
            selected_provider = self._providers.get(selected_name)
            provider_type = _provider_type_from_name(selected_name)
            provider_model = getattr(selected_provider, "model", None) if selected_provider else None
            return provider_type, str(provider_model) if provider_model else None
        return ProviderType.MOCK, None

    def _create_provider_request_record(
        self,
        *,
        job_id: uuid.UUID,
        provider: ProviderType,
        provider_model: str | None,
        attempt_number: int,
        prompt_name: str,
        prompt_version: str,
        schema_name: str,
        schema_version: str,
        system_prompt: str | None,
        user_prompt: str,
        images: Sequence[Any],
        metadata: Mapping[str, object],
    ) -> DBProviderRequest:
        return DBProviderRequest(
            id=uuid.uuid4(),
            analysis_job_id=job_id,
            provider=provider,
            provider_model=provider_model,
            attempt_number=attempt_number,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            schema_name=schema_name,
            schema_version=schema_version,
            request_payload={
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "images": [img.storage_reference for img in images],
            },
            request_metadata=dict(metadata),
        )

    async def _process_partitioned_initial_analysis(
        self,
        *,
        job: AnalysisJob,
        ts: TradeSession,
        ctx: Any,
        now: datetime,
        selected_provider_name: ProviderType,
        selected_provider_model: str | None,
        validate: ValidationCallback,
    ) -> AnalysisProcessingResult:
        partition_schemas = build_partition_schemas()
        partition_payloads: dict[str, dict[str, object]] = {}
        validation_warnings: list[ValidationIssue] = []

        for attempt_number, partition in enumerate(PARTITIONS, start=1):
            validated_context = {
                name: payload for name, payload in partition_payloads.items()
            }
            partition_user_prompt = build_partition_user_prompt(
                base_user_prompt=ctx.user_prompt,
                partition_name=partition.name,
                validated_context=validated_context,
            )
            partition_images = select_partition_images(
                partition_name=partition.name,
                images=ctx.images,
            )
            partition_metadata = dict(ctx.metadata)
            partition_metadata["partition_name"] = partition.name
            partition_metadata["partition_keys"] = list(partition.top_level_keys)
            canonical_chart_timestamps = _canonical_chart_timestamps_for_partition(
                ctx.metadata,
                partition.name,
            )
            if canonical_chart_timestamps is not None:
                partition_metadata["canonical_chart_timestamps"] = canonical_chart_timestamps
            else:
                partition_metadata.pop("canonical_chart_timestamps", None)

            db_provider_request = self._create_provider_request_record(
                job_id=job.id,
                provider=selected_provider_name,
                provider_model=selected_provider_model,
                attempt_number=attempt_number,
                prompt_name=ctx.analysis_type,
                prompt_version=ctx.prompt_version,
                schema_name=ctx.expected_schema_name,
                schema_version=ctx.expected_schema_version,
                system_prompt=ctx.system_prompt,
                user_prompt=partition_user_prompt,
                images=partition_images,
                metadata=partition_metadata,
            )
            self._session.add(db_provider_request)

            router_request = ProviderRequestModel(
                request_id=uuid.uuid4(),
                analysis_type=ctx.analysis_type,
                prompt_version=ctx.prompt_version,
                user_prompt=partition_user_prompt,
                expected_schema_name=ctx.expected_schema_name,
                expected_schema_version=ctx.expected_schema_version,
                system_prompt=ctx.system_prompt,
                images=partition_images,
                structured_output_schema=partition_schemas[partition.name].provider_schema,
                metadata=_provider_request_metadata_for_partition(
                    partition_name=partition.name,
                    model_name=selected_provider_model,
                    canonical_chart_timestamps=canonical_chart_timestamps,
                ),
            )
            await self._session.flush()

            partition_validate = self._make_partition_usable_callback(
                partition_name=partition.name,
            )

            try:
                route_result = await self._router.generate_validated(
                    request=router_request,
                    providers=self._providers,
                    provider_order=self._provider_order,
                    max_provider_attempts=1,
                    validate=partition_validate,
                    canonical_facts=ctx.canonical_facts,
                    max_repair_attempts=0,
                )
            except ProviderRoutingFailedError as exc:
                await self._persist_route_attempts(
                    db_provider_request.id,
                    getattr(exc, "attempts", ()),
                )
                await self._fail_job(job, exc, ts, now)
                await self._session.flush()
                self._log.warning(
                    "Initial analysis partition failed",
                    extra={
                        "analysis_job_id": str(job.id),
                        "session_id": str(job.session_id),
                        "partition_name": partition.name,
                        "root_cause_code": job.last_error_code,
                        "root_cause_message": job.last_error_message,
                    },
                )
                return AnalysisProcessingResult(
                    job_id=job.id,
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

            await self._persist_route_attempts(db_provider_request.id, route_result.attempts)
            partition_valid, partition_issues = validate_partition_payload(
                payload=dict(route_result.payload),
                partition_name=partition.name,
                schemas=partition_schemas,
            )
            if not partition_valid:
                validation_warnings.extend(partition_issues)
            partition_payloads[partition.name] = dict(route_result.payload)

        try:
            merged_payload = merge_partition_payloads(partition_payloads)
        except ValueError as exc:
            routing_error = ProviderRoutingFailedError(
                message="Partition merge failed",
                root_cause_code="INITIAL_ANALYSIS_PARTITION_MERGE_FAILED",
                root_cause_message=str(exc),
                retryable=False,
            )
            await self._fail_job(job, routing_error, ts, now)
            await self._session.flush()
            return AnalysisProcessingResult(
                job_id=job.id,
                session_id=job.session_id,
                analysis_id=None,
                job_status=job.status.value,
                restored_session_status=job.previous_session_status,
                provider=None,
                fallback_used=False,
                error_code=job.last_error_code,
                error_message=job.last_error_message,
            )

        if not _is_usable_initial_analysis_payload(merged_payload):
            routing_error = ProviderRoutingFailedError(
                message="Merged INITIAL_ANALYSIS payload is not usable",
                root_cause_code="INITIAL_ANALYSIS_PAYLOAD_UNUSABLE",
                root_cause_message="Merged INITIAL_ANALYSIS payload has no usable analysis sections.",
                retryable=False,
            )
            await self._fail_job(job, routing_error, ts, now)
            await self._session.flush()
            return AnalysisProcessingResult(
                job_id=job.id,
                session_id=job.session_id,
                analysis_id=None,
                job_status=job.status.value,
                restored_session_status=job.previous_session_status,
                provider=None,
                fallback_used=False,
                error_code=job.last_error_code,
                error_message=job.last_error_message,
            )

        validation_payload = decimalize_json_numbers_for_validation(merged_payload)
        _is_valid, issues = validate(dict(validation_payload))
        validation_warnings.extend(issues)
        if validation_warnings:
            await self._persist_initial_analysis_validation_warnings(
                job_id=job.id,
                parsed_payload=merged_payload,
                validation_payload=merged_payload,
                issues=tuple(validation_warnings),
            )
            self._log.warning(
                "Initial analysis accepted with validation warnings",
                extra={
                    "analysis_job_id": str(job.id),
                    "session_id": str(job.session_id),
                    "warning_count": len(validation_warnings),
                    "warning_codes": [issue.code for issue in validation_warnings[:20]],
                },
            )

        analysis_id = uuid.uuid4()
        analysis = Analysis(
            id=analysis_id,
            session_id=job.session_id,
            analysis_job_id=job.id,
            analysis_type=ctx.analysis_type,
            acceptance_status=AcceptanceStatus.ACCEPTED,
            prompt_name=ctx.analysis_type,
            prompt_version=ctx.prompt_version,
            schema_name=ctx.expected_schema_name,
            schema_version=ctx.expected_schema_version,
            payload=merged_payload,
            accepted_at=now,
        )
        self._session.add(analysis)

        job.status = AnalysisJobStatus.COMPLETED
        job.completed_at = now
        job.lease_owner = None
        job.lease_acquired_at = None
        job.lease_expires_at = None

        prev = job.previous_session_status
        completion_status = _completion_status_for_analysis(ctx.analysis_type, prev)
        if completion_status is not None:
            ts.lifecycle_status = completion_status
            ts.stable_status = completion_status

        await EvidenceBatchService(self._session).freeze(job.evidence_batch_id, now=now)
        await self._session.flush()

        rebuild = ContextRebuildService(self._session)
        await rebuild.rebuild_after_material_event(
            session_id=job.session_id,
            owner_id=ts.owner_id,
            reason=ContextRebuildReason.ANALYSIS_ACCEPTED,
            source_id=analysis_id,
        )

        try:
            from app.services.evaluation_records import EvaluationRecordService
            eval_svc = EvaluationRecordService(self._session)
            await eval_svc.record_prediction_from_analysis(analysis, ts)
        except Exception as eval_exc:
            self._log.warning(
                "Evaluation record projection error during initial analysis completion",
                extra={"session_id": str(job.session_id), "error": str(eval_exc)},
            )

        return AnalysisProcessingResult(
            job_id=job.id,
            session_id=job.session_id,
            analysis_id=analysis_id,
            job_status=AnalysisJobStatus.COMPLETED.value,
            restored_session_status=(
                completion_status.value if completion_status is not None else prev
            ),
            provider=self._provider_order[0] if self._provider_order else None,
            fallback_used=False,
        )

    def _make_partition_validate_callback(
        self,
        *,
        partition_name: str,
        partition_schemas: Mapping[str, object],
    ) -> ValidationCallback:
        def _validate_partition(payload: dict[str, object]) -> tuple[bool, tuple[ValidationIssue, ...]]:
            return validate_partition_payload(
                payload=payload,
                partition_name=partition_name,
                schemas=partition_schemas,  # type: ignore[arg-type]
            )

        return _validate_partition

    def _make_partition_usable_callback(
        self,
        *,
        partition_name: str,
    ) -> ValidationCallback:
        partition = next(item for item in PARTITIONS if item.name == partition_name)

        def _validate_partition(payload: dict[str, object]) -> tuple[bool, tuple[ValidationIssue, ...]]:
            if not isinstance(payload, dict) or not payload:
                return False, (
                    ValidationIssue(
                        code="INITIAL_ANALYSIS_PARTITION_EMPTY",
                        category=ValidationCategory.SCHEMA,
                        severity=ValidationSeverity.ERROR,
                        path="",
                        message=f"{partition.name} returned an empty or unusable JSON object.",
                    ),
                )
            unexpected = sorted(set(payload) - set(partition.top_level_keys))
            if unexpected:
                return False, tuple(
                    ValidationIssue(
                        code="SCHEMA_UNKNOWN_PROPERTY",
                        category=ValidationCategory.ADDITIONAL_PROPERTY,
                        severity=ValidationSeverity.ERROR,
                        path=f"/{key}",
                        message=(
                            f"Partition {partition.name} contains unexpected top-level key: {key}"
                        ),
                        expected="partition-owned top-level keys only",
                        actual=payload.get(key),
                    )
                    for key in unexpected
                )
            if not any(key in payload for key in partition.top_level_keys):
                return False, (
                    ValidationIssue(
                        code="INITIAL_ANALYSIS_PARTITION_NO_USABLE_SECTION",
                        category=ValidationCategory.SCHEMA,
                        severity=ValidationSeverity.ERROR,
                        path="",
                        message=f"{partition.name} returned no usable analysis sections.",
                    ),
                )
            return True, ()

        return _validate_partition

    async def _persist_initial_analysis_validation_warnings(
        self,
        *,
        job_id: uuid.UUID,
        parsed_payload: Mapping[str, object],
        validation_payload: Mapping[str, object],
        issues: Sequence[ValidationIssue],
    ) -> None:
        grouped: dict[ValidationStage, list[ValidationIssue]] = {
            ValidationStage.JSON_SCHEMA: [],
            ValidationStage.DOMAIN: [],
        }
        for issue in issues:
            if issue.category.value == "DOMAIN":
                grouped[ValidationStage.DOMAIN].append(issue)
            else:
                grouped[ValidationStage.JSON_SCHEMA].append(issue)

        attempt_number = 1
        for stage in (ValidationStage.JSON_SCHEMA, ValidationStage.DOMAIN):
            stage_issues = grouped[stage]
            if not stage_issues:
                continue
            self._session.add(
                ValidationAttempt(
                    id=uuid.uuid4(),
                    analysis_job_id=job_id,
                    provider_response_id=None,
                    attempt_number=attempt_number,
                    stage=stage,
                    valid=True,
                    issues={
                        "mode": "INITIAL_ANALYSIS_NON_BLOCKING_MVP",
                        "warning_count": len(stage_issues),
                        "warnings": [_issue_to_warning_dict(issue) for issue in stage_issues],
                    },
                    parsed_payload=dict(parsed_payload),
                    validated_payload=dict(validation_payload),
                )
            )
            attempt_number += 1

    async def _build_fresh_provider_context(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        analysis_type: str,
        evidence_batch_id: uuid.UUID | None,
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
                evidence_batch_id=evidence_batch_id,
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
                    evidence_batch_id=evidence_batch_id,
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
        attempts: Sequence[Any],
    ) -> None:
        for attempt in attempts:
            if attempt.response is None:
                continue
            raw = attempt.response
            raw_payload = None
            if isinstance(raw.metadata, dict):
                provider_payload_raw = raw.metadata.get("provider_payload_raw")
                if isinstance(provider_payload_raw, dict):
                    raw_payload = dict(provider_payload_raw)
            if raw_payload is None and attempt.payload is not None:
                raw_payload = dict(attempt.payload)

            resp = DBProviderResponse(
                id=uuid.uuid4(),
                provider_request_id=db_req_id,
                status=(
                    ProviderResponseStatus.FAILED
                    if attempt.failure_code or attempt.failure_message
                    else ProviderResponseStatus.COMPLETED
                ),
                raw_text=raw.raw_output,
                raw_payload=raw_payload,
                provider_response_id=_normalize_provider_response_id(raw.provider_response_id),
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
                error_code=attempt.failure_code,
                error_message=attempt.failure_message,
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

        job.status = AnalysisJobStatus.FAILED
        job.completed_at = now
        job.lease_owner = None
        job.lease_acquired_at = None
        job.lease_expires_at = None
        job.last_error_code = error_code
        job.last_error_message = error_message

        await restore_session_status(self._session, ts, job.previous_session_status)
        await EvidenceBatchService(self._session).fail(job.evidence_batch_id, now=now)


def _always_invalid(
    payload: dict[str, object],
) -> tuple[bool, tuple[ValidationIssue, ...]]:
    return False, ()


def _completion_status_for_analysis(
    analysis_type: str,
    previous_status: str | None,
) -> TradeSessionStatus | None:
    if analysis_type == "INITIAL_ANALYSIS":
        return TradeSessionStatus.INITIAL_ANALYZED
    if previous_status is None:
        return None
    try:
        return TradeSessionStatus(previous_status)
    except ValueError:
        return None


def _provider_type_from_name(provider_name: str) -> ProviderType:
    try:
        return ProviderType(provider_name.upper())
    except ValueError:
        return ProviderType.MOCK


def _normalize_provider_response_id(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, int):
        return str(value) if value > 0 else None
    return None


def _is_usable_initial_analysis_payload(payload: Mapping[str, object]) -> bool:
    if not isinstance(payload, Mapping) or not payload:
        return False
    usable_sections = (
        "metadata",
        "evidence_summary",
        "market_snapshot",
        "executive_summary",
        "orderbook_analysis",
        "chart_3_month_analysis",
        "chart_6_month_analysis",
        "combined_chart_analysis",
        "price_levels",
        "entry_plan",
        "stop_loss_plan",
        "target_plan",
        "initial_thesis",
        "trading_plan",
        "ai_assessment",
        "warnings_and_missing_information",
        "decision",
        "market_facts",
        "evidence_findings",
        "trade_plan",
        "probabilities",
        "scenarios",
        "next_actions",
    )
    return any(isinstance(payload.get(section), Mapping) for section in usable_sections)


def _canonical_chart_timestamps_for_partition(
    metadata: Mapping[str, object],
    partition_name: str,
) -> dict[str, str] | None:
    if partition_name != "CHART_ANALYSIS":
        return None
    raw = metadata.get("canonical_chart_timestamps")
    if not isinstance(raw, Mapping):
        return None
    allowed = {"chart_3_month_analysis", "chart_6_month_analysis"}
    timestamps = {
        str(key): value
        for key, value in raw.items()
        if key in allowed and isinstance(value, str) and value.strip()
    }
    return timestamps or None


def _provider_request_metadata_for_partition(
    *,
    partition_name: str,
    model_name: str | None,
    canonical_chart_timestamps: Mapping[str, str] | None,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "partition_name": partition_name,
        "model_name": model_name,
    }
    if partition_name == "CHART_ANALYSIS" and canonical_chart_timestamps:
        metadata["canonical_chart_timestamps"] = dict(canonical_chart_timestamps)
    return metadata


def _issue_to_warning_dict(issue: ValidationIssue) -> dict[str, object]:
    return {
        "code": issue.code,
        "category": issue.category.value,
        "severity": ValidationSeverity.WARNING.value,
        "original_severity": issue.severity.value,
        "path": issue.path,
        "message": issue.message,
        "expected": _json_safe_warning_value(issue.expected),
        "actual": _json_safe_warning_value(issue.actual),
    }


def _json_safe_warning_value(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, list):
        return [_json_safe_warning_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe_warning_value(item) for key, item in value.items()}
    return value
