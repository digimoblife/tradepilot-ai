"""Provider context builder (TP-0803).

Constructs the full provider-ready AI request context for one Analysis Job.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from app.ai.prompts import PromptRegistry
from app.ai.providers import (
    ProviderCapabilities,
    ProviderImage,
)
from app.ai.providers.capabilities import ensure_request_supported
from app.models.analysis import Analysis
from app.models.context_summary import ContextSummary
from app.models.enums import AnalysisType, EvidenceType
from app.models.evidence import Evidence
from app.models.trade_session import TradeSession
from app.models.trade_state import TradeState
from app.repositories.analysis import AnalysisRepository
from app.repositories.evidence import EvidenceRepository
from app.repositories.trade_session import TradeSessionRepository

# ---------------------------------------------------------------------------
# Context result
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ProviderContext:
    """Immutable result of a successful context build."""

    session_id: uuid.UUID
    analysis_type: str
    prompt_version: str
    system_prompt: str
    user_prompt: str
    expected_schema_name: str
    expected_schema_version: str
    structured_output_schema: dict[str, object] | None
    canonical_facts: dict[str, object]
    images: tuple[ProviderImage, ...]
    metadata: dict[str, object]


# ---------------------------------------------------------------------------
# Stable errors
# ---------------------------------------------------------------------------


class ProviderContextError(Exception):
    code: str = "PROVIDER_CONTEXT_ERROR"

    def __init__(self, code: str | None = None, message: str = "") -> None:
        self.code = code or self.code
        self.message = message
        super().__init__(f"[{self.code}] {message}" if message else f"[{self.code}]")


class ProviderContextSessionNotFoundError(ProviderContextError):
    code: str = "PROVIDER_CONTEXT_SESSION_NOT_FOUND_OR_NOT_OWNED"


class ProviderContextStaleError(ProviderContextError):
    code: str = "PROVIDER_CONTEXT_STALE"


class ProviderContextProviderIncompatibleError(ProviderContextError):
    code: str = "PROVIDER_CONTEXT_PROVIDER_INCOMPATIBLE"


class ProviderContextPromptRenderFailedError(ProviderContextError):
    code: str = "PROVIDER_CONTEXT_PROMPT_RENDER_FAILED"


# ---------------------------------------------------------------------------
# Required evidence ordering
# ---------------------------------------------------------------------------

_EVIDENCE_TYPE_ORDER: dict[str, int] = {
    EvidenceType.ORDERBOOK_SCREENSHOT.value: 0,
    EvidenceType.CHART_THREE_MONTH.value: 1,
    EvidenceType.CHART_SIX_MONTH.value: 2,
    EvidenceType.CHART_DAILY.value: 3,
    EvidenceType.CHART_INTRADAY.value: 4,
    EvidenceType.BROKER_SUMMARY.value: 5,
    EvidenceType.FOREIGN_FLOW.value: 6,
    EvidenceType.NEWS_SCREENSHOT.value: 7,
    EvidenceType.CUSTOM_IMAGE.value: 8,
    EvidenceType.USER_NOTE.value: 9,
    EvidenceType.MARKET_DATA_SNAPSHOT.value: 10,
}

_DEFAULT_PROMPTS_ROOT = (
    Path(__file__).resolve().parent.parent.parent.parent / "prompts" / "production" / "v1"
)


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


class ProviderContextBuilder:
    """Constructs the full provider-ready AI request context."""

    def __init__(
        self,
        session: Any,
        prompts_root: Path | None = None,
    ) -> None:
        self._session = session
        self._session_repo = TradeSessionRepository(session)
        self._evidence_repo = EvidenceRepository(session)
        self._analysis_repo = AnalysisRepository(session)
        root = prompts_root or _DEFAULT_PROMPTS_ROOT
        self._prompt_registry = PromptRegistry(prompts_root=root)

    async def build(
        self,
        *,
        session_id: uuid.UUID,
        owner_id: uuid.UUID,
        analysis_type: AnalysisType | str,
        provider_capabilities: ProviderCapabilities,
        now: datetime | None = None,
    ) -> ProviderContext:
        atype = _normalize_type(analysis_type)
        now = now or datetime.now(timezone.utc)

        # 1. Load owned session + trade state
        ts = await self._session_repo.get_by_id_for_user(session_id, owner_id)
        if ts is None:
            raise ProviderContextSessionNotFoundError(
                message="Trade Session not found or not owned",
            )

        # 2. Load canonical Trade State
        trade_state = await self._session.get(TradeState, session_id)
        canonical_facts = _build_canonical_facts(ts, trade_state)

        # 3. Load Context Summary — reject stale
        context_summary = await _load_latest_context(self._session, session_id)
        if context_summary is not None and context_summary.is_stale:
            raise ProviderContextStaleError(
                message="Context Summary is stale; rebuild required",
            )

        # 4. Load latest accepted analysis by type
        latest_analysis = await self._analysis_repo.get_latest_accepted_by_type_for_user(
            session_id=session_id,
            user_id=owner_id,
            analysis_type=atype,
        )

        # 5. Load active evidence (deterministic order)
        all_active = await self._evidence_repo.list_active_for_session_for_user(
            session_id,
            owner_id,
        )
        ordered_evidence = _order_evidence(all_active, atype)

        # 6. Check provider capabilities
        images = await _build_images(ordered_evidence, provider_capabilities)

        # Build a temporary request-like object for capability check
        temp_req = _RequestStub(
            images=images,
            structured_output_schema={},
            system_prompt="",
        )
        if provider_capabilities.supports_structured_output:
            temp_req.structured_output_schema = {}

        ensure_request_supported(temp_req, provider_capabilities)  # type: ignore[arg-type]

        # 7. Resolve and render prompt
        try:
            rendered = self._prompt_registry.render(
                analysis_type=atype,
                variables=_build_prompt_variables(
                    ts,
                    trade_state,
                    context_summary,
                    latest_analysis,
                ),
            )
        except Exception as exc:
            raise ProviderContextPromptRenderFailedError(
                message=f"Prompt rendering failed: {exc}",
            ) from exc

        # 8. Structured output schema
        structured_schema = None
        if provider_capabilities.supports_structured_output:
            structured_schema = _resolve_structured_schema(rendered.expected_schema_name)

        # 9. Build metadata
        metadata: dict[str, object] = {
            "session_id": str(session_id),
            "analysis_type": atype,
            "prompt_version": rendered.prompt_version,
            "schema_name": rendered.expected_schema_name,
            "schema_version": rendered.expected_schema_version,
            "output_language": "id",
            "context_summary_id": str(context_summary.id) if context_summary else None,
            "latest_analysis_id": str(latest_analysis.id) if latest_analysis else None,
            "evidence_ids": [str(e.id) for e in ordered_evidence],
        }

        return ProviderContext(
            session_id=session_id,
            analysis_type=atype,
            prompt_version=rendered.prompt_version,
            system_prompt=rendered.system_prompt,
            user_prompt=rendered.user_prompt,
            expected_schema_name=rendered.expected_schema_name,
            expected_schema_version=rendered.expected_schema_version,
            structured_output_schema=structured_schema,
            canonical_facts=canonical_facts,
            images=images,
            metadata=metadata,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_type(atype: AnalysisType | str) -> str:
    if isinstance(atype, str):
        return atype
    return atype.value


def _build_canonical_facts(
    ts: TradeSession,
    trade_state: TradeState | None,
) -> dict[str, object]:
    facts: dict[str, object] = {
        "session_id": str(ts.id),
        "ticker": ts.ticker,
        "currency": ts.currency.value if hasattr(ts.currency, "value") else str(ts.currency),
        "lifecycle_status": ts.lifecycle_status.value
        if hasattr(ts.lifecycle_status, "value")
        else str(ts.lifecycle_status),  # noqa: E501
    }
    if ts.company_name:
        facts["company_name"] = ts.company_name

    if trade_state is not None:
        facts["position_status"] = (
            trade_state.position_status.value
            if hasattr(trade_state.position_status, "value")
            else str(trade_state.position_status)
        )  # noqa: E501
        facts["thesis_status"] = (
            trade_state.thesis_status.value
            if hasattr(trade_state.thesis_status, "value")
            else str(trade_state.thesis_status)
        )  # noqa: E501

        for field, key in [
            ("entry_price", "entry_price"),
            ("entry_at", "entry_at"),
            ("original_quantity", "original_quantity"),
            ("remaining_quantity", "remaining_quantity"),
            ("active_stop_loss", "active_stop_loss"),
            ("active_target", "active_target"),
            ("average_exit_price", "average_exit_price"),
            ("realized_pnl", "realized_pnl"),
        ]:
            val = getattr(trade_state, field, None)
            if val is not None:
                facts[key] = _decimal_or_none(val)

    return facts


def _decimal_or_none(val: Any) -> Any:
    from decimal import Decimal

    if isinstance(val, Decimal):
        return str(val) if val is not None else None
    return val


async def _load_latest_context(
    session: Any,
    session_id: uuid.UUID,
) -> ContextSummary | None:
    from sqlalchemy import select

    result = await session.execute(
        select(ContextSummary)
        .where(ContextSummary.session_id == session_id)
        .order_by(ContextSummary.context_version.desc())
        .limit(1)
    )
    return result.unique().scalar_one_or_none()  # type: ignore[no-any-return]


async def _build_images(
    evidence_list: Sequence[Evidence],
    capabilities: ProviderCapabilities,
) -> tuple[ProviderImage, ...]:
    if not capabilities.supports_images:
        if evidence_list:
            raise ProviderContextProviderIncompatibleError(
                message="Provider does not support images but evidence is required",
            )
        return ()

    images: list[ProviderImage] = []
    for ev in evidence_list:
        if ev.mime_type and ev.mime_type.startswith("image/"):
            images.append(
                ProviderImage(
                    evidence_id=ev.id,
                    mime_type=ev.mime_type,
                    storage_reference=ev.storage_object_key or "",
                    byte_size=ev.file_size_bytes or 0,
                )
            )

    max_images = capabilities.maximum_images
    if max_images is not None and len(images) > max_images:
        images = images[:max_images]

    return tuple(images)


def _order_evidence(
    evidence_list: Sequence[Evidence],
    analysis_type: str,
) -> list[Evidence]:
    def sort_key(ev: Evidence) -> tuple[Any, ...]:
        type_order = _EVIDENCE_TYPE_ORDER.get(
            ev.evidence_type.value
            if hasattr(ev.evidence_type, "value")
            else str(ev.evidence_type),  # noqa: E501
            99,
        )
        mkt_ts = ev.market_timestamp or datetime.min.replace(tzinfo=timezone.utc)
        upl_ts = ev.uploaded_at or datetime.min.replace(tzinfo=timezone.utc)
        return (type_order, -mkt_ts.timestamp(), -upl_ts.timestamp(), str(ev.id))

    return sorted(evidence_list, key=sort_key)


def _build_prompt_variables(
    ts: TradeSession,
    trade_state: TradeState | None,
    context_summary: ContextSummary | None,
    latest_analysis: Analysis | None,
) -> dict[str, str]:
    import json

    variables: dict[str, str] = {}

    variables["session_identity"] = json.dumps(
        {
            "session_id": str(ts.id),
            "ticker": ts.ticker,
        },
        ensure_ascii=False,
    )

    trade_state_json = {}
    if trade_state is not None:
        for col in [
            "position_status",
            "entry_price",
            "entry_at",
            "original_quantity",
            "remaining_quantity",
            "active_stop_loss",
            "active_target",
            "thesis_status",
            "realized_pnl",
            "average_exit_price",
        ]:
            val = getattr(trade_state, col, None)
            if val is not None:
                trade_state_json[col] = (
                    str(val) if not isinstance(val, (str, int, float, bool)) else val
                )  # noqa: E501
    variables["trade_state_json"] = json.dumps(trade_state_json, ensure_ascii=False)

    evidence_list_json: list[dict[str, object]] = []
    variables["evidence_manifest_json"] = json.dumps(evidence_list_json, ensure_ascii=False)

    context_summary_json = {}
    if context_summary is not None and context_summary.payload:
        context_summary_json = dict(context_summary.payload)
    variables["context_summary_json"] = json.dumps(context_summary_json, ensure_ascii=False)

    market_snapshot_json = {}
    if context_summary is not None and context_summary.payload:
        ms = context_summary.payload.get("market_snapshot")
        if ms is not None and isinstance(ms, dict):
            market_snapshot_json = dict(ms)
    variables["market_snapshot_json"] = json.dumps(market_snapshot_json, ensure_ascii=False)

    latest_analysis_json = {}
    if latest_analysis is not None and latest_analysis.payload:
        latest_analysis_json = dict(latest_analysis.payload)
    variables["latest_analysis_json"] = json.dumps(latest_analysis_json, ensure_ascii=False)

    user_notes_json: list[dict[str, object]] = []
    variables["user_notes"] = json.dumps(user_notes_json, ensure_ascii=False)

    return variables


def _resolve_structured_schema(schema_name: str) -> dict[str, object]:
    import json
    from pathlib import Path

    schema_path = Path("schemas/production/v1") / f"{schema_name}.schema.json"
    if not schema_path.is_file():
        raise ProviderContextError(
            code="PROVIDER_CONTEXT_SCHEMA_INVALID",
            message=f"Schema file not found: {schema_path}",
        )
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)  # type: ignore[no-any-return]


# Stub for capability checking without creating a full ProviderRequest
@dataclass
class _RequestStub:
    images: tuple[ProviderImage, ...] = ()
    structured_output_schema: dict[str, object] | None = None
    system_prompt: str | None = None
