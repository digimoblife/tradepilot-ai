from __future__ import annotations

import enum
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2ObservationPeriod,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2, EvidenceUploadV2Type
from app.trade_workspace.models.position import PositionV2, PositionV2Status
from app.trade_workspace.models.trade_session import TradeSessionV2

HISTORY_LIMIT = 5


class ContextBuilderError(Exception):
    """Base error for rebuild context construction."""


class SessionNotFoundError(ContextBuilderError):
    pass


class OwnershipMismatchError(ContextBuilderError):
    pass


class AnalysisRequestNotFoundError(ContextBuilderError):
    pass


class AnalysisRequestOwnershipMismatchError(ContextBuilderError):
    pass


class EvidenceOwnershipMismatchError(ContextBuilderError):
    pass


class UnsupportedAnalysisTypeError(ContextBuilderError):
    pass


class MissingRequiredEvidenceError(ContextBuilderError):
    pass


class MissingObservationFactsError(ContextBuilderError):
    pass


class UnexpectedPositionError(ContextBuilderError):
    pass


class MissingPositionError(ContextBuilderError):
    pass


class MultiplePositionsError(ContextBuilderError):
    pass


class PositionNotOpenError(ContextBuilderError):
    pass


class PositionRequestMismatchError(ContextBuilderError):
    pass


class MissingInitialAnalysisError(ContextBuilderError):
    pass


class RebuildAnalysisType(str, enum.Enum):
    INITIAL_ANALYSIS = "INITIAL_ANALYSIS"
    WAIT_UPDATE = "WAIT_UPDATE"
    POSITION_UPDATE = "POSITION_UPDATE"


@dataclass(frozen=True, slots=True)
class SessionFacts:
    session_id: uuid.UUID
    ticker: str
    company_name: str
    note: str | None


@dataclass(frozen=True, slots=True)
class ObservationFacts:
    current_price: Decimal
    observation_period: AnalysisRequestV2ObservationPeriod
    observation_at: datetime
    user_note: object | None


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    evidence_id: uuid.UUID
    evidence_type: EvidenceUploadV2Type
    analysis_request_id: uuid.UUID | None
    file_path: str
    original_filename: str
    mime_type: str
    observation_period: AnalysisRequestV2ObservationPeriod | None
    uploaded_at: datetime


@dataclass(frozen=True, slots=True)
class AnalysisSummary:
    analysis_id: uuid.UUID
    analysis_type: AnalysisRequestV2Type
    created_at: datetime
    observation_period: AnalysisRequestV2ObservationPeriod | None
    observation_at: datetime | None
    processed_response: dict[str, object]


@dataclass(frozen=True, slots=True)
class PositionFacts:
    position_id: uuid.UUID
    session_id: uuid.UUID
    entry_price: Decimal
    entry_at: datetime
    quantity: Decimal
    stop_loss: Decimal
    target_price: Decimal
    status: PositionV2Status


@dataclass(frozen=True, slots=True)
class AnalysisContext:
    analysis_type: RebuildAnalysisType
    session: SessionFacts
    current_observation: ObservationFacts | None
    evidence: tuple[EvidenceReference, ...]
    initial_analysis: AnalysisSummary | None
    history: tuple[AnalysisSummary, ...]
    position: PositionFacts | None


class RebuildAnalysisContextBuilder:
    """Build bounded contexts from rebuild-owned persistence only."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def build(
        self,
        *,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        analysis_type: RebuildAnalysisType | AnalysisRequestV2Type | str,
        analysis_request_id: uuid.UUID,
    ) -> AnalysisContext:
        resolved_type = self._resolve_analysis_type(analysis_type)
        trade_session = await self._load_owned_session(user_id, session_id)
        request = await self._load_current_request(analysis_request_id, session_id)
        linked_evidence = await self._load_linked_evidence(request.id, session_id)
        session_facts = SessionFacts(
            session_id=trade_session.id,
            ticker=trade_session.ticker,
            company_name=trade_session.company_name,
            note=trade_session.note,
        )

        if request.analysis_type.value != resolved_type.value:
            raise UnsupportedAnalysisTypeError(
                f"Analysis request type {request.analysis_type.value!r} does not match "
                f"requested type {resolved_type.value!r}"
            )

        if resolved_type is RebuildAnalysisType.INITIAL_ANALYSIS:
            evidence = await self._load_initial_evidence(session_id, request.id)
            return AnalysisContext(
                analysis_type=resolved_type,
                session=session_facts,
                current_observation=None,
                evidence=tuple(evidence),
                initial_analysis=None,
                history=(),
                position=None,
            )

        if resolved_type is RebuildAnalysisType.WAIT_UPDATE:
            current_evidence = self._wait_update_evidence(linked_evidence, request.id)
            observation = self._wait_update_observation_facts(request, current_evidence[0])
            current_position = await self._load_positions(session_id)
            if current_position:
                raise UnexpectedPositionError(
                    "WAIT_UPDATE context cannot be built for a session with a position"
                )
            initial_analysis, prior_wait = await self._load_wait_update_history(
                session_id=session_id,
                current_request=request,
            )
            return AnalysisContext(
                analysis_type=resolved_type,
                session=session_facts,
                current_observation=observation,
                evidence=tuple(self._evidence_reference(item) for item in current_evidence),
                initial_analysis=initial_analysis,
                history=(prior_wait,) if prior_wait is not None else (),
                position=None,
            )

        current_position = await self._load_positions(session_id)
        position = self._position_update_position(current_position, request, session_id)
        current_evidence = self._position_update_evidence(linked_evidence, request.id)
        observation = self._position_update_observation_facts(request, current_evidence[0])
        (
            initial_analysis,
            prior_wait,
            prior_position_update,
        ) = await self._load_position_update_history(
            session_id=session_id,
            current_request=request,
        )
        history = tuple(item for item in (prior_wait, prior_position_update) if item is not None)

        return AnalysisContext(
            analysis_type=resolved_type,
            session=session_facts,
            current_observation=observation,
            evidence=tuple(self._evidence_reference(item) for item in current_evidence),
            initial_analysis=initial_analysis,
            history=history,
            position=position,
        )

    async def _load_owned_session(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> TradeSessionV2:
        trade_session = await self._session.scalar(
            select(TradeSessionV2).where(TradeSessionV2.id == session_id)
        )
        if trade_session is None:
            raise SessionNotFoundError(f"Rebuild session not found: {session_id}")
        if trade_session.user_id != user_id:
            raise OwnershipMismatchError("Rebuild session ownership mismatch")
        return trade_session

    async def _load_current_request(
        self,
        analysis_request_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> AnalysisRequestV2:
        request = await self._session.scalar(
            select(AnalysisRequestV2).where(AnalysisRequestV2.id == analysis_request_id)
        )
        if request is None:
            raise AnalysisRequestNotFoundError(
                f"Analysis request not found: {analysis_request_id}"
            )
        if request.session_id != session_id:
            raise AnalysisRequestOwnershipMismatchError(
                "Analysis request does not belong to the rebuild session"
            )
        return request

    async def _load_linked_evidence(
        self,
        analysis_request_id: uuid.UUID,
        session_id: uuid.UUID,
    ) -> list[EvidenceUploadV2]:
        linked = list(
            (
                await self._session.scalars(
                    select(EvidenceUploadV2)
                    .where(EvidenceUploadV2.analysis_request_id == analysis_request_id)
                    .order_by(EvidenceUploadV2.uploaded_at.asc(), EvidenceUploadV2.id.asc())
                )
            ).all()
        )
        if any(item.session_id != session_id for item in linked):
            raise EvidenceOwnershipMismatchError(
                "Evidence linked to the analysis request belongs to another session"
            )
        return linked

    async def _load_initial_evidence(
        self,
        session_id: uuid.UUID,
        analysis_request_id: uuid.UUID,
    ) -> list[EvidenceReference]:
        required_types = (
            EvidenceUploadV2Type.ORDERBOOK,
            EvidenceUploadV2Type.CHART_3_MONTH,
            EvidenceUploadV2Type.CHART_6_MONTH,
            EvidenceUploadV2Type.FOREIGN_FLOW_1W,
        )
        evidence = list(
            (
                await self._session.scalars(
                    select(EvidenceUploadV2)
                    .where(
                        EvidenceUploadV2.session_id == session_id,
                        EvidenceUploadV2.evidence_type.in_(required_types),
                        or_(
                            EvidenceUploadV2.analysis_request_id.is_(None),
                            EvidenceUploadV2.analysis_request_id == analysis_request_id,
                        ),
                    )
                    .order_by(EvidenceUploadV2.uploaded_at.desc(), EvidenceUploadV2.id.desc())
                )
            ).all()
        )
        selected: list[EvidenceUploadV2] = []
        for evidence_type in required_types:
            match = next(
                (item for item in evidence if item.evidence_type is evidence_type),
                None,
            )
            if match is None:
                raise MissingRequiredEvidenceError(
                    f"Initial Analysis evidence is missing: {evidence_type.value}"
                )
            selected.append(match)
        return [self._evidence_reference(item) for item in selected]

    @staticmethod
    def _latest_orderbook(linked_evidence: list[EvidenceUploadV2]) -> EvidenceReference:
        orderbooks = [
            item
            for item in linked_evidence
            if item.evidence_type is EvidenceUploadV2Type.ORDERBOOK
        ]
        if not orderbooks:
            raise MissingRequiredEvidenceError(
                "Current analysis request has no linked ORDERBOOK evidence"
            )
        return RebuildAnalysisContextBuilder._evidence_reference(orderbooks[-1])

    @staticmethod
    def _wait_update_evidence(
        linked_evidence: list[EvidenceUploadV2],
        analysis_request_id: uuid.UUID,
    ) -> tuple[EvidenceUploadV2, ...]:
        if len(linked_evidence) not in (1, 2):
            raise MissingRequiredEvidenceError(
                "WAIT_UPDATE requires ORDERBOOK and at most one BROKER_FLOW_1D"
            )
        orderbooks = [
            item
            for item in linked_evidence
            if item.evidence_type is EvidenceUploadV2Type.ORDERBOOK
        ]
        broker_flows = [
            item
            for item in linked_evidence
            if item.evidence_type is EvidenceUploadV2Type.BROKER_FLOW_1D
        ]
        if len(orderbooks) != 1 or len(broker_flows) != len(linked_evidence) - 1:
            raise MissingRequiredEvidenceError(
                "WAIT_UPDATE requires ORDERBOOK and optionally BROKER_FLOW_1D"
            )
        evidence = orderbooks[0]
        if (
            evidence.analysis_request_id != analysis_request_id
            or evidence.session_id is None
            or evidence.evidence_type is not EvidenceUploadV2Type.ORDERBOOK
            or evidence.current_price is None
            or evidence.observation_period is None
            or evidence.observation_timestamp is None
            or not evidence.file_path.strip()
            or Path(evidence.file_path).is_absolute()
        ):
            raise MissingRequiredEvidenceError(
                "WAIT_UPDATE current evidence is missing required persisted facts"
            )
        for broker_flow in broker_flows:
            if (
                broker_flow.analysis_request_id != analysis_request_id
                or broker_flow.session_id != evidence.session_id
                or not broker_flow.file_path.strip()
                or Path(broker_flow.file_path).is_absolute()
            ):
                raise MissingRequiredEvidenceError(
                    "WAIT_UPDATE Broker Flow evidence is not owned by this request"
                )
        return (evidence, *broker_flows)

    @staticmethod
    def _wait_update_observation_facts(
        request: AnalysisRequestV2,
        evidence: EvidenceUploadV2,
    ) -> ObservationFacts:
        request_observation = RebuildAnalysisContextBuilder._observation_facts(request)
        if (
            evidence.current_price != request_observation.current_price
            or evidence.observation_period is not request_observation.observation_period
            or evidence.observation_timestamp != request_observation.observation_at
        ):
            raise MissingObservationFactsError(
                "WAIT_UPDATE request and evidence observation facts do not match"
            )
        return ObservationFacts(
            current_price=evidence.current_price,
            observation_period=evidence.observation_period,
            observation_at=evidence.observation_timestamp,
            user_note=request_observation.user_note,
        )

    @staticmethod
    def _position_update_evidence(
        linked_evidence: list[EvidenceUploadV2],
        analysis_request_id: uuid.UUID,
    ) -> tuple[EvidenceUploadV2, ...]:
        if len(linked_evidence) not in (1, 2):
            raise MissingRequiredEvidenceError(
                "POSITION_UPDATE requires ORDERBOOK and at most one BROKER_FLOW_1D"
            )
        orderbooks = [
            item
            for item in linked_evidence
            if item.evidence_type is EvidenceUploadV2Type.ORDERBOOK
        ]
        broker_flows = [
            item
            for item in linked_evidence
            if item.evidence_type is EvidenceUploadV2Type.BROKER_FLOW_1D
        ]
        if len(orderbooks) != 1 or len(broker_flows) != len(linked_evidence) - 1:
            raise MissingRequiredEvidenceError(
                "POSITION_UPDATE requires ORDERBOOK and optionally BROKER_FLOW_1D"
            )
        evidence = orderbooks[0]
        if (
            evidence.analysis_request_id != analysis_request_id
            or evidence.session_id is None
            or evidence.evidence_type is not EvidenceUploadV2Type.ORDERBOOK
            or evidence.current_price is None
            or evidence.observation_period is None
            or evidence.observation_timestamp is None
            or not evidence.file_path.strip()
            or Path(evidence.file_path).is_absolute()
        ):
            raise MissingRequiredEvidenceError(
                "POSITION_UPDATE current evidence is missing required persisted facts"
            )
        for broker_flow in broker_flows:
            if (
                broker_flow.analysis_request_id != analysis_request_id
                or broker_flow.session_id != evidence.session_id
                or not broker_flow.file_path.strip()
                or Path(broker_flow.file_path).is_absolute()
            ):
                raise MissingRequiredEvidenceError(
                    "POSITION_UPDATE Broker Flow evidence is not owned by this request"
                )
        return (evidence, *broker_flows)

    @staticmethod
    def _position_update_observation_facts(
        request: AnalysisRequestV2,
        evidence: EvidenceUploadV2,
    ) -> ObservationFacts:
        request_observation = RebuildAnalysisContextBuilder._observation_facts(request)
        if (
            evidence.current_price != request_observation.current_price
            or evidence.observation_period is not request_observation.observation_period
            or evidence.observation_timestamp != request_observation.observation_at
        ):
            raise MissingObservationFactsError(
                "POSITION_UPDATE request and evidence observation facts do not match"
            )
        return ObservationFacts(
            current_price=evidence.current_price,
            observation_period=evidence.observation_period,
            observation_at=evidence.observation_timestamp,
            user_note=request_observation.user_note,
        )

    @staticmethod
    def _evidence_reference(evidence: EvidenceUploadV2) -> EvidenceReference:
        return EvidenceReference(
            evidence_id=evidence.id,
            evidence_type=evidence.evidence_type,
            analysis_request_id=evidence.analysis_request_id,
            file_path=evidence.file_path,
            original_filename=evidence.original_filename,
            mime_type=evidence.mime_type,
            observation_period=evidence.observation_period,
            uploaded_at=evidence.uploaded_at,
        )

    @staticmethod
    def _observation_facts(request: AnalysisRequestV2) -> ObservationFacts:
        if (
            request.current_price is None
            or request.observation_period is None
            or request.observation_at is None
        ):
            raise MissingObservationFactsError(
                "WAIT_UPDATE and POSITION_UPDATE require price, period, and timestamp"
            )
        return ObservationFacts(
            current_price=request.current_price,
            observation_period=request.observation_period,
            observation_at=request.observation_at,
            user_note=_user_note(request.input_snapshot),
        )

    async def _load_history(
        self,
        session_id: uuid.UUID,
        current_request_id: uuid.UUID,
        analysis_type: RebuildAnalysisType,
    ) -> list[AnalysisSummary]:
        relevant_types = (
            AnalysisRequestV2Type.INITIAL_ANALYSIS,
            AnalysisRequestV2Type.WAIT_UPDATE,
        )
        if analysis_type is RebuildAnalysisType.POSITION_UPDATE:
            relevant_types += (AnalysisRequestV2Type.POSITION_UPDATE,)

        request_query: Select[tuple[AnalysisRequestV2]] = (
            select(AnalysisRequestV2)
            .where(
                AnalysisRequestV2.session_id == session_id,
                AnalysisRequestV2.id != current_request_id,
                AnalysisRequestV2.analysis_type.in_(relevant_types),
                AnalysisRequestV2.status == AnalysisRequestV2Status.COMPLETED,
                AnalysisRequestV2.processed_response.is_not(None),
            )
            .order_by(AnalysisRequestV2.created_at.asc(), AnalysisRequestV2.id.asc())
        )
        requests = list((await self._session.scalars(request_query)).all())
        summaries = [self._analysis_summary(request) for request in requests]
        initial = self._find_initial_analysis(summaries)
        if initial is None:
            raise MissingInitialAnalysisError(
                "No completed Initial Analysis is available for this session"
            )
        return _bound_history(summaries, initial)

    async def _load_wait_update_history(
        self,
        *,
        session_id: uuid.UUID,
        current_request: AnalysisRequestV2,
    ) -> tuple[AnalysisSummary, AnalysisSummary | None]:
        initial_request = await self._session.scalar(
            select(AnalysisRequestV2)
            .where(
                AnalysisRequestV2.session_id == session_id,
                AnalysisRequestV2.analysis_type == AnalysisRequestV2Type.INITIAL_ANALYSIS,
                AnalysisRequestV2.status == AnalysisRequestV2Status.COMPLETED,
                AnalysisRequestV2.processed_response.is_not(None),
            )
            .order_by(
                AnalysisRequestV2.completed_at.desc().nullslast(),
                AnalysisRequestV2.created_at.desc(),
                AnalysisRequestV2.id.desc(),
            )
            .limit(1)
        )
        if initial_request is None:
            raise MissingInitialAnalysisError(
                "No completed Initial Analysis is available for this session"
            )

        prior_request = await self._session.scalar(
            select(AnalysisRequestV2)
            .where(
                AnalysisRequestV2.session_id == session_id,
                AnalysisRequestV2.id != current_request.id,
                AnalysisRequestV2.analysis_type == AnalysisRequestV2Type.WAIT_UPDATE,
                AnalysisRequestV2.status == AnalysisRequestV2Status.COMPLETED,
                AnalysisRequestV2.processed_response.is_not(None),
                (AnalysisRequestV2.created_at < current_request.created_at)
                | (
                    (AnalysisRequestV2.created_at == current_request.created_at)
                    & (AnalysisRequestV2.id < current_request.id)
                ),
            )
            .order_by(
                AnalysisRequestV2.completed_at.desc().nullslast(),
                AnalysisRequestV2.created_at.desc(),
                AnalysisRequestV2.id.desc(),
            )
            .limit(1)
        )
        return self._analysis_summary(initial_request), (
            self._analysis_summary(prior_request) if prior_request is not None else None
        )

    async def _load_position_update_history(
        self,
        *,
        session_id: uuid.UUID,
        current_request: AnalysisRequestV2,
    ) -> tuple[AnalysisSummary, AnalysisSummary | None, AnalysisSummary | None]:
        initial_request = await self._session.scalar(
            select(AnalysisRequestV2)
            .where(
                AnalysisRequestV2.session_id == session_id,
                AnalysisRequestV2.analysis_type == AnalysisRequestV2Type.INITIAL_ANALYSIS,
                AnalysisRequestV2.status == AnalysisRequestV2Status.COMPLETED,
                AnalysisRequestV2.processed_response.is_not(None),
            )
            .order_by(
                AnalysisRequestV2.completed_at.desc().nullslast(),
                AnalysisRequestV2.created_at.desc(),
                AnalysisRequestV2.id.desc(),
            )
            .limit(1)
        )
        if initial_request is None:
            raise MissingInitialAnalysisError(
                "No completed Initial Analysis is available for this session"
            )

        prior_filter = (AnalysisRequestV2.created_at < current_request.created_at) | (
            (AnalysisRequestV2.created_at == current_request.created_at)
            & (AnalysisRequestV2.id < current_request.id)
        )

        async def latest_completed(
            analysis_type: AnalysisRequestV2Type,
        ) -> AnalysisSummary | None:
            prior_request = await self._session.scalar(
                select(AnalysisRequestV2)
                .where(
                    AnalysisRequestV2.session_id == session_id,
                    AnalysisRequestV2.id != current_request.id,
                    AnalysisRequestV2.analysis_type == analysis_type,
                    AnalysisRequestV2.status == AnalysisRequestV2Status.COMPLETED,
                    AnalysisRequestV2.processed_response.is_not(None),
                    prior_filter,
                )
                .order_by(
                    AnalysisRequestV2.completed_at.desc().nullslast(),
                    AnalysisRequestV2.created_at.desc(),
                    AnalysisRequestV2.id.desc(),
                )
                .limit(1)
            )
            return self._analysis_summary(prior_request) if prior_request is not None else None

        return (
            self._analysis_summary(initial_request),
            await latest_completed(AnalysisRequestV2Type.WAIT_UPDATE),
            await latest_completed(AnalysisRequestV2Type.POSITION_UPDATE),
        )

    @staticmethod
    def _find_initial_analysis(
        summaries: list[AnalysisSummary] | tuple[AnalysisSummary, ...],
    ) -> AnalysisSummary | None:
        return next(
            (
                summary
                for summary in summaries
                if summary.analysis_type is AnalysisRequestV2Type.INITIAL_ANALYSIS
            ),
            None,
        )

    @staticmethod
    def _analysis_summary(request: AnalysisRequestV2) -> AnalysisSummary:
        processed_response = request.processed_response
        if not isinstance(processed_response, dict):
            raise MissingInitialAnalysisError(
                f"Completed analysis has no processed response: {request.id}"
            )
        return AnalysisSummary(
            analysis_id=request.id,
            analysis_type=request.analysis_type,
            created_at=request.created_at,
            observation_period=request.observation_period,
            observation_at=request.observation_at,
            processed_response=dict(processed_response),
        )

    async def _load_positions(self, session_id: uuid.UUID) -> list[PositionV2]:
        return list(
            (
                await self._session.scalars(
                    select(PositionV2)
                    .where(PositionV2.session_id == session_id)
                    .order_by(PositionV2.created_at.asc(), PositionV2.id.asc())
                )
            ).all()
        )

    @staticmethod
    def _position_facts(position: PositionV2, session_id: uuid.UUID) -> PositionFacts:
        if position.session_id != session_id:
            raise OwnershipMismatchError("Position ownership mismatch")
        return PositionFacts(
            position_id=position.id,
            session_id=position.session_id,
            entry_price=position.entry_price,
            entry_at=position.entry_at,
            quantity=position.quantity,
            stop_loss=position.stop_loss,
            target_price=position.target_price,
            status=position.status,
        )

    @staticmethod
    def _position_update_position(
        positions: list[PositionV2],
        request: AnalysisRequestV2,
        session_id: uuid.UUID,
    ) -> PositionFacts:
        if not positions:
            raise MissingPositionError("POSITION_UPDATE context requires one position")
        if len(positions) > 1:
            raise MultiplePositionsError("POSITION_UPDATE context requires exactly one position")

        position = positions[0]
        if position.session_id != session_id:
            raise OwnershipMismatchError("Position ownership mismatch")
        if position.status is not PositionV2Status.OPEN:
            raise PositionNotOpenError("POSITION_UPDATE context requires an OPEN position")

        snapshot = request.input_snapshot
        position_id = snapshot.get("position_id") if isinstance(snapshot, Mapping) else None
        try:
            expected_position_id = uuid.UUID(str(position_id))
        except (TypeError, ValueError, AttributeError) as exc:
            raise PositionRequestMismatchError(
                "POSITION_UPDATE request has no valid position reference"
            ) from exc
        if position.id != expected_position_id:
            raise PositionRequestMismatchError(
                "POSITION_UPDATE request position reference does not match the session position"
            )
        return RebuildAnalysisContextBuilder._position_facts(position, session_id)

    @staticmethod
    def _resolve_analysis_type(
        analysis_type: RebuildAnalysisType | AnalysisRequestV2Type | str,
    ) -> RebuildAnalysisType:
        try:
            value = analysis_type.value if isinstance(analysis_type, enum.Enum) else analysis_type
            return RebuildAnalysisType(value)
        except (TypeError, ValueError) as exc:
            raise UnsupportedAnalysisTypeError(
                f"Unsupported rebuild analysis type: {analysis_type!r}"
            ) from exc


def _bound_history(
    summaries: list[AnalysisSummary],
    initial: AnalysisSummary,
) -> list[AnalysisSummary]:
    if len(summaries) <= HISTORY_LIMIT:
        return summaries
    updates = [summary for summary in summaries if summary.analysis_id != initial.analysis_id]
    retained = [initial, *updates[-(HISTORY_LIMIT - 1) :]]
    return sorted(retained, key=lambda summary: (summary.created_at, summary.analysis_id))


def _user_note(input_snapshot: Mapping[str, object]) -> object | None:
    for key in ("user_note", "note"):
        if key in input_snapshot:
            return input_snapshot[key]
    return None
