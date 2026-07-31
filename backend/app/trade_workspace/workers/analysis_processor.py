from __future__ import annotations

import dataclasses
import enum
import json
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.trade_workspace.ai.context_builder import (
    AnalysisContext,
    RebuildAnalysisContextBuilder,
    RebuildAnalysisType,
)
from app.trade_workspace.ai.gemini_adapter import (
    GeminiAdapter,
    GeminiAdapterError,
    GeminiAdapterResult,
    GeminiImagePart,
)
from app.trade_workspace.ai.prompt_loader import (
    PromptLoaderError,
    RebuildPrompt,
    RebuildPromptLoader,
)
from app.trade_workspace.ai.response_validator import (
    RebuildResponseValidator,
    ResponseValidationError,
    critical_validation_error,
)
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status


class AnalysisImageResolver(Protocol):
    async def resolve(self, evidence: Sequence[object]) -> Sequence[GeminiImagePart]:
        """Resolve ordered evidence references into ordered Gemini image parts."""


class AnalysisProcessorError(Exception):
    """Base error for rebuild worker processing."""


class AnalysisRequestNotFoundError(AnalysisProcessorError):
    pass


class AnalysisRequestNotPendingError(AnalysisProcessorError):
    pass


class RequestSessionMismatchError(AnalysisProcessorError):
    pass


class UnsupportedAnalysisTypeError(AnalysisProcessorError):
    pass


class PromptVersionMismatchError(AnalysisProcessorError):
    pass


class SchemaLoadError(AnalysisProcessorError):
    pass


class ClaimPersistenceError(AnalysisProcessorError):
    pass


class CompletionPersistenceError(AnalysisProcessorError):
    pass


class InvalidWaitUpdateImageCountError(AnalysisProcessorError):
    pass


@dataclass(frozen=True, slots=True)
class AnalysisProcessorResult:
    request_id: uuid.UUID
    status: AnalysisRequestV2Status
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class _ClaimedRequest:
    request_id: uuid.UUID
    session_id: uuid.UUID
    user_id: uuid.UUID
    analysis_type: RebuildAnalysisType
    prompt_version: str
    model: str


_SCHEMA_FILES: dict[RebuildAnalysisType, str] = {
    RebuildAnalysisType.INITIAL_ANALYSIS: "initial_analysis.schema.json",
    RebuildAnalysisType.WAIT_UPDATE: "wait_update.schema.json",
    RebuildAnalysisType.POSITION_UPDATE: "position_update.schema.json",
}


class RebuildAnalysisProcessor:
    """Process exactly one claimed rebuild analysis request."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        image_resolver: AnalysisImageResolver,
        context_builder: RebuildAnalysisContextBuilder | None = None,
        prompt_loader: RebuildPromptLoader | None = None,
        validator: RebuildResponseValidator | None = None,
        adapter_factory: Callable[[str], GeminiAdapter] | None = None,
        schemas_root: Path | None = None,
    ) -> None:
        self._session = session
        self._image_resolver = image_resolver
        self._context_builder = context_builder
        self._prompt_loader = prompt_loader or RebuildPromptLoader()
        self._validator = validator or RebuildResponseValidator()
        self._adapter_factory = adapter_factory or (lambda model: GeminiAdapter(model=model))
        repository_root = Path(__file__).resolve().parents[4]
        self._schemas_root = schemas_root or repository_root / "schemas" / "rebuild" / "v1"

    async def process(self, *, analysis_request_id: uuid.UUID) -> AnalysisProcessorResult:
        claim = await self._claim(analysis_request_id)
        result: GeminiAdapterResult | None = None
        try:
            result = await self._run(claim)
            validation = self._validator.validate(claim.analysis_type, result.processed_response)
            if not validation.is_valid:
                raise critical_validation_error(claim.analysis_type, validation)
        except Exception as exc:
            error_code, error_message = _sanitize_failure(exc)
            raw_response = _json_safe(result.raw_response) if result is not None else None
            await self._mark_failed(
                claim.request_id,
                error_code,
                error_message,
                raw_response=raw_response,
            )
            return AnalysisProcessorResult(
                request_id=claim.request_id,
                status=AnalysisRequestV2Status.FAILED,
                error_code=error_code,
            )

        try:
            await self._mark_completed(claim.request_id, result)
        except Exception as exc:
            error_code, error_message = _sanitize_failure(exc)
            await self._mark_failed(claim.request_id, error_code, error_message)
            return AnalysisProcessorResult(
                request_id=claim.request_id,
                status=AnalysisRequestV2Status.FAILED,
                error_code=error_code,
            )
        return AnalysisProcessorResult(
            request_id=claim.request_id,
            status=AnalysisRequestV2Status.COMPLETED,
        )

    async def _claim(self, analysis_request_id: uuid.UUID) -> _ClaimedRequest:
        request = await self._session.scalar(
            select(AnalysisRequestV2)
            .where(AnalysisRequestV2.id == analysis_request_id)
            .with_for_update()
        )
        if request is None:
            raise AnalysisRequestNotFoundError("Rebuild analysis request was not found")
        if request.status is not AnalysisRequestV2Status.PENDING:
            raise AnalysisRequestNotPendingError("Rebuild analysis request is not pending")

        analysis_type = _resolve_analysis_type(request.analysis_type)
        trade_session = await self._session.scalar(
            select(TradeSessionV2).where(TradeSessionV2.id == request.session_id)
        )
        if trade_session is None:
            raise RequestSessionMismatchError("Rebuild analysis request session was not found")

        request.status = AnalysisRequestV2Status.PROCESSING
        request.started_at = datetime.now(timezone.utc)
        try:
            await self._session.flush()
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise ClaimPersistenceError("Rebuild analysis request could not be claimed") from exc

        return _ClaimedRequest(
            request_id=request.id,
            session_id=request.session_id,
            user_id=trade_session.user_id,
            analysis_type=analysis_type,
            prompt_version=request.prompt_version,
            model=request.model,
        )

    async def _run(self, claim: _ClaimedRequest) -> GeminiAdapterResult:
        context_builder = self._context_builder or RebuildAnalysisContextBuilder(self._session)
        context = await context_builder.build(
            user_id=claim.user_id,
            session_id=claim.session_id,
            analysis_type=claim.analysis_type,
            analysis_request_id=claim.request_id,
        )
        prompt = self._prompt_loader.load(claim.analysis_type.value)
        if prompt.prompt_version != claim.prompt_version:
            raise PromptVersionMismatchError(
                "Persisted prompt version does not match approved prompt"
            )
        schema = _load_schema(self._schemas_root, claim.analysis_type)
        image_parts = await self._image_resolver.resolve(context.evidence)
        if claim.analysis_type is RebuildAnalysisType.WAIT_UPDATE and len(image_parts) != 1:
            raise InvalidWaitUpdateImageCountError(
                "WAIT_UPDATE requires exactly one current orderbook image"
            )
        prompt_text = _compose_prompt(prompt, context)
        adapter = self._adapter_factory(claim.model)
        return await adapter.generate(
            prompt_text=prompt_text,
            image_parts=image_parts,
            output_schema=schema,
        )

    async def _mark_completed(
        self,
        request_id: uuid.UUID,
        result: GeminiAdapterResult,
    ) -> None:
        request = await self._session.scalar(
            select(AnalysisRequestV2)
            .where(AnalysisRequestV2.id == request_id)
            .with_for_update()
        )
        if request is None:
            raise CompletionPersistenceError(
                "Rebuild analysis request disappeared before completion"
            )
        trade_session = await self._session.scalar(
            select(TradeSessionV2)
            .where(TradeSessionV2.id == request.session_id)
            .with_for_update()
        )
        if trade_session is None:
            await self._session.rollback()
            raise CompletionPersistenceError(
                "Rebuild analysis session disappeared before completion"
            )
        if request.analysis_type is AnalysisRequestV2Type.INITIAL_ANALYSIS:
            if trade_session.status is not TradeSessionV2Status.ANALYZING:
                await self._session.rollback()
                raise CompletionPersistenceError(
                    "Initial Analysis session is not in ANALYZING status"
                )
        elif request.analysis_type is AnalysisRequestV2Type.WAIT_UPDATE:
            if trade_session.status is not TradeSessionV2Status.ANALYZING:
                await self._session.rollback()
                raise CompletionPersistenceError(
                    "WAIT_UPDATE session is not in ANALYZING status"
                )
        elif request.analysis_type is AnalysisRequestV2Type.POSITION_UPDATE:
            if trade_session.status is not TradeSessionV2Status.ANALYZING:
                await self._session.rollback()
                raise CompletionPersistenceError(
                    "POSITION_UPDATE session is not in ANALYZING status"
                )
        request.raw_response = _json_safe(result.raw_response)
        request.processed_response = _json_safe(result.processed_response)
        request.status = AnalysisRequestV2Status.COMPLETED
        request.completed_at = datetime.now(timezone.utc)
        request.error_code = None
        request.error_message = None
        # Transition session from ANALYZING to its approved resulting status.
        if request.analysis_type is AnalysisRequestV2Type.INITIAL_ANALYSIS:
            trade_session.status = TradeSessionV2Status.ANALYZED
        elif request.analysis_type is AnalysisRequestV2Type.WAIT_UPDATE:
            # ANALYZING is temporary; restore WAITING so the next update cycle can proceed.
            trade_session.status = TradeSessionV2Status.WAITING
        elif request.analysis_type is AnalysisRequestV2Type.POSITION_UPDATE:
            # ANALYZING is temporary; restore OPEN_POSITION so the next update can proceed.
            trade_session.status = TradeSessionV2Status.OPEN_POSITION
        try:
            await self._session.flush()
            await self._session.commit()
        except SQLAlchemyError as exc:
            await self._session.rollback()
            raise CompletionPersistenceError(
                "Rebuild analysis response could not be persisted"
            ) from exc

    async def _mark_failed(
        self,
        request_id: uuid.UUID,
        error_code: str,
        error_message: str,
        raw_response: object | None = None,
    ) -> None:
        request = await self._session.scalar(
            select(AnalysisRequestV2)
            .where(AnalysisRequestV2.id == request_id)
            .with_for_update()
        )
        if request is None:
            return
        trade_session = await self._session.scalar(
            select(TradeSessionV2)
            .where(TradeSessionV2.id == request.session_id)
            .with_for_update()
        )
        request.status = AnalysisRequestV2Status.FAILED
        request.completed_at = datetime.now(timezone.utc)
        request.error_code = error_code
        request.error_message = error_message
        if raw_response is not None:
            request.raw_response = raw_response
        request.processed_response = None
        if trade_session is not None and trade_session.status is TradeSessionV2Status.ANALYZING:
            # Restore session from temporary ANALYZING to its prior stable status.
            if request.analysis_type is AnalysisRequestV2Type.INITIAL_ANALYSIS:
                trade_session.status = TradeSessionV2Status.DRAFT
            elif request.analysis_type is AnalysisRequestV2Type.WAIT_UPDATE:
                # Preserve WAITING so the user can request an explicit retry.
                trade_session.status = TradeSessionV2Status.WAITING
            elif request.analysis_type is AnalysisRequestV2Type.POSITION_UPDATE:
                # Preserve OPEN_POSITION so the user can request an explicit retry.
                trade_session.status = TradeSessionV2Status.OPEN_POSITION
        try:
            await self._session.flush()
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()


def _resolve_analysis_type(value: AnalysisRequestV2Type | str) -> RebuildAnalysisType:
    try:
        return RebuildAnalysisType(value.value if isinstance(value, enum.Enum) else value)
    except (TypeError, ValueError) as exc:
        raise UnsupportedAnalysisTypeError("Unsupported rebuild analysis type") from exc


def _load_schema(schemas_root: Path, analysis_type: RebuildAnalysisType) -> Mapping[str, object]:
    schema_path = schemas_root / _SCHEMA_FILES[analysis_type]
    try:
        raw = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError) as exc:
        raise SchemaLoadError("Approved rebuild output schema could not be loaded") from exc
    if not isinstance(raw, Mapping) or not raw:
        raise SchemaLoadError("Approved rebuild output schema is malformed")
    return raw


def _compose_prompt(prompt: RebuildPrompt, context: AnalysisContext) -> str:
    serialized_context = json.dumps(
        _json_safe(context),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"{prompt.prompt_text.rstrip()}\n\nCanonical rebuild context:\n{serialized_context}"


def _json_safe(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return _json_safe(dataclasses.asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, enum.Enum):
        return _json_safe(value.value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return _json_safe(model_dump(mode="json"))
    return str(value)


def _sanitize_failure(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, PromptVersionMismatchError):
        return "PROMPT_VERSION_MISMATCH", "Approved prompt version does not match the request"
    if isinstance(exc, SchemaLoadError):
        return "SCHEMA_LOAD_FAILED", "Approved output schema could not be loaded"
    if isinstance(exc, GeminiAdapterError):
        return "GEMINI_REQUEST_FAILED", "Gemini processing failed"
    if isinstance(exc, PromptLoaderError):
        return "PROMPT_LOAD_FAILED", "Approved prompt could not be loaded"
    if isinstance(exc, UnsupportedAnalysisTypeError):
        return "UNSUPPORTED_ANALYSIS_TYPE", "Unsupported rebuild analysis type"
    if isinstance(exc, CompletionPersistenceError):
        return "RESPONSE_PERSISTENCE_FAILED", "Analysis response could not be persisted"
    if isinstance(exc, ResponseValidationError):
        return "RESPONSE_VALIDATION_FAILED", str(exc)[:500]
    if isinstance(exc, AnalysisProcessorError):
        return "PROCESSING_FAILED", "Rebuild analysis processing failed"
    return "PROCESSING_FAILED", f"Rebuild analysis processing failed ({type(exc).__name__})"
