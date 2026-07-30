from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.api.auth import router as auth_router
from app.api.exception_handlers import register_handlers
from app.auth import hash_password
from app.database.session import get_db_session
from app.models.user import User
from app.storage import LocalFileStorage
from app.trade_workspace.ai.context_builder import (
    RebuildAnalysisContextBuilder,
    RebuildAnalysisType,
)
from app.trade_workspace.ai.gemini_adapter import GeminiAdapterResult, GeminiImagePart
from app.trade_workspace.api.routes.trade_sessions import router as rebuild_router
from app.trade_workspace.models.analysis_request import (
    AnalysisRequestV2,
    AnalysisRequestV2Status,
    AnalysisRequestV2Type,
)
from app.trade_workspace.models.evidence_upload import EvidenceUploadV2
from app.trade_workspace.models.trade_session import TradeSessionV2, TradeSessionV2Status
from app.trade_workspace.queue.analysis_request_queue import AnalysisRequestQueue
from app.trade_workspace.services import wait_update_input as wait_input_module
from app.trade_workspace.workers.analysis_processor import RebuildAnalysisProcessor

pytestmark = pytest.mark.database

OBSERVATION = datetime(2026, 7, 30, 2, 15, tzinfo=timezone.utc)
IMAGE = b"\x89PNG\r\n\x1a\n-gate-f"


class RecordingTransport:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.payloads: list[dict[str, str]] = []

    async def publish(self, payload: bytes) -> None:
        if self.fail:
            raise RuntimeError("isolated queue unavailable")
        self.payloads.append(json.loads(payload))


class RecordingImageResolver:
    def __init__(self) -> None:
        self.calls: list[int] = []

    async def resolve(self, evidence: tuple[object, ...]) -> tuple[GeminiImagePart, ...]:
        self.calls.append(len(evidence))
        return (GeminiImagePart(data=IMAGE, mime_type="image/png"),)


class RecordingAdapter:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.calls = 0

    async def generate(self, **_: object) -> GeminiAdapterResult:
        self.calls += 1
        return GeminiAdapterResult(
            provider="gemini",
            model="gemini-3.1-flash-lite",
            raw_response={"mocked": True},
            processed_response=self.response,
        )


def _valid_response() -> dict[str, object]:
    return {
        "update_summary": "Perubahan terbaru masih terkendali.",
        "current_price": 1234,
        "orderbook_assessment": "Likuiditas cukup seimbang.",
        "change_from_previous_analysis": "Belum ada perubahan material.",
        "current_entry_condition": "Belum ada konfirmasi entry.",
        "key_risks": ["Volatilitas pasar"],
        "upside_probability": 55,
        "downside_probability": 45,
        "recommended_action": "WAIT",
        "next_plan": "Pantau orderbook berikutnya.",
        "conclusion": "Tetap menunggu konfirmasi.",
    }


def _initial_response() -> dict[str, object]:
    return {
        "summary": "Analisis awal selesai.",
        "orderbook_analysis": "Orderbook awal seimbang.",
        "three_month_chart_analysis": "Tren tiga bulan dipantau.",
        "six_month_chart_analysis": "Tren enam bulan dipantau.",
        "support": {"level": 1200},
        "resistance": {"level": 1300},
        "entry_area": {"low": 1210, "high": 1240},
        "stop_recommendation": {"level": 1150},
        "target_recommendation": {"level": 1350},
        "probabilities": {"upside": 55, "downside": 45},
        "risks": ["Volatilitas"],
        "trading_plan": "Tunggu konfirmasi.",
        "conclusion": "WAIT",
    }


async def _seed(
    engine: AsyncEngine,
    *,
    email_prefix: str,
    status: TradeSessionV2Status = TradeSessionV2Status.WAITING,
) -> tuple[uuid.UUID, uuid.UUID, str]:
    user_id, session_id = uuid.uuid4(), uuid.uuid4()
    email = f"{email_prefix}-{user_id}@example.test"
    async with engine.begin() as connection:
        await connection.execute(
            User.__table__.insert().values(
                id=user_id, email=email, password_hash=hash_password("testpass123")
            )
        )
        await connection.execute(
            TradeSessionV2.__table__.insert().values(
                id=session_id,
                user_id=user_id,
                ticker="BBRI",
                company_name="Bank BRI",
                status=status,
            )
        )
        await connection.execute(
            AnalysisRequestV2.__table__.insert().values(
                id=uuid.uuid4(),
                session_id=session_id,
                analysis_type=AnalysisRequestV2Type.INITIAL_ANALYSIS,
                status=AnalysisRequestV2Status.COMPLETED,
                provider="gemini",
                model="gemini-3.1-flash-lite",
                prompt_version="v1",
                input_snapshot={"gate": "f"},
                processed_response=_initial_response(),
                completed_at=OBSERVATION,
            )
        )
    return user_id, session_id, email


def _app(db_session: AsyncSession, queue: AnalysisRequestQueue) -> FastAPI:
    app = FastAPI()
    register_handlers(app)
    app.include_router(auth_router)
    app.include_router(rebuild_router)
    app.state.rebuild_analysis_queue = queue

    async def override_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db_session] = override_db
    return app


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncSession:
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
def isolated_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LocalFileStorage:
    storage = LocalFileStorage(tmp_path)
    monkeypatch.setattr(wait_input_module, "create_file_storage", lambda _config=None: storage)
    return storage


async def _login(client: AsyncClient, email: str) -> None:
    response = await client.post(
        "/api/auth/login", json={"email": email, "password": "testpass123"}
    )
    assert response.status_code == 200


async def _upload_and_submit(
    client: AsyncClient, session_id: uuid.UUID
) -> tuple[dict[str, object], dict[str, object]]:
    upload = await client.post(
        f"/api/v2/trade-sessions/{session_id}/wait-update-input",
        data={
            "current_price": "1234.00",
            "observation_period": "MIDDAY",
            "observation_timestamp": "2026-07-30T09:15:00+07:00",
        },
        files={"orderbook": ("orderbook.png", IMAGE, "image/png")},
    )
    assert upload.status_code == 201
    submit = await client.post(f"/api/v2/trade-sessions/{session_id}/wait-update-analysis")
    assert submit.status_code == 202
    return upload.json(), submit.json()


async def _process(
    db_session: AsyncSession,
    request_id: uuid.UUID,
    resolver: RecordingImageResolver,
    adapter: RecordingAdapter,
) -> None:
    processor = RebuildAnalysisProcessor(
        db_session,
        image_resolver=resolver,  # type: ignore[arg-type]
        adapter_factory=lambda _model: adapter,  # type: ignore[arg-type]
    )
    result = await processor.process(analysis_request_id=request_id)
    assert result.status is AnalysisRequestV2Status.COMPLETED


async def test_gate_f_success_repeated_cycle_and_decision_compatibility(
    engine: AsyncEngine,
    db_session: AsyncSession,
    isolated_storage: LocalFileStorage,
) -> None:
    user_id, session_id, email = await _seed(engine, email_prefix="gate-f-success")
    transport = RecordingTransport()
    app = _app(db_session, AnalysisRequestQueue(transport))
    resolver, adapter = RecordingImageResolver(), RecordingAdapter(_valid_response())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _login(client, email)
        upload_a, submit_a = await _upload_and_submit(client, session_id)
        request_a = uuid.UUID(submit_a["analysis_request_id"])
        assert upload_a["evidence_id"] == submit_a["evidence_id"]
        assert transport.payloads == [{"analysis_request_id": str(request_a)}]
        await _process(db_session, request_a, resolver, adapter)
        read_a = await client.get(f"/api/v2/trade-sessions/{session_id}/wait-update-analysis")
        assert read_a.status_code == 200
        assert read_a.json()["request_status"] == "COMPLETED"
        assert (await client.get(f"/api/v2/trade-sessions/{session_id}/available-actions")).json()[
            "available_actions"
        ] == ["BUY", "WAIT", "SKIP"]

        duplicate = await client.post(f"/api/v2/trade-sessions/{session_id}/wait-update-analysis")
        assert duplicate.status_code == 409

        # A second WAITING cycle creates new evidence and request rows while preserving A.
        upload_b, submit_b = await _upload_and_submit(client, session_id)
        requests = (
            await db_session.scalars(
                select(AnalysisRequestV2)
                .where(AnalysisRequestV2.session_id == session_id)
                .order_by(AnalysisRequestV2.created_at)
            )
        ).all()
        wait_requests = [
            item for item in requests if item.analysis_type is AnalysisRequestV2Type.WAIT_UPDATE
        ]
        assert len(wait_requests) == 2
        request_b = wait_requests[-1].id
        context_b = await RebuildAnalysisContextBuilder(db_session).build(
            user_id=user_id,
            session_id=session_id,
            analysis_type=RebuildAnalysisType.WAIT_UPDATE,
            analysis_request_id=request_b,
        )
        assert context_b.initial_analysis is not None
        assert context_b.history and context_b.history[0].analysis_id == request_a
        assert context_b.evidence[0].evidence_id == uuid.UUID(upload_b["evidence_id"])
        await _process(db_session, request_b, resolver, adapter)

    evidence_count = await db_session.scalar(
        select(func.count(EvidenceUploadV2.id)).where(EvidenceUploadV2.session_id == session_id)
    )
    assert evidence_count == 2
    assert adapter.calls == 2
    assert resolver.calls == [1, 1]
    assert len(list(isolated_storage._root.rglob("*.png"))) == 2  # noqa: SLF001


async def test_gate_f_failure_retry_queue_recovery_and_ownership(
    engine: AsyncEngine,
    db_session: AsyncSession,
    isolated_storage: LocalFileStorage,
) -> None:
    _, session_id, owner_email = await _seed(engine, email_prefix="gate-f-owner")
    _, other_session_id, other_email = await _seed(engine, email_prefix="gate-f-other")
    failing_transport = RecordingTransport(fail=True)
    app = _app(db_session, AnalysisRequestQueue(failing_transport))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as owner:
        await _login(owner, owner_email)
        # Submit separately so the queue-failure state is observable.
        upload_response = await owner.post(
            f"/api/v2/trade-sessions/{session_id}/wait-update-input",
            data={
                "current_price": "1234.00",
                "observation_period": "MIDDAY",
                "observation_timestamp": "2026-07-30T09:15:00+07:00",
            },
            files={"orderbook": ("orderbook.png", IMAGE, "image/png")},
        )
        assert upload_response.status_code == 201
        failed_queue = await owner.post(
            f"/api/v2/trade-sessions/{session_id}/wait-update-analysis"
        )
        assert failed_queue.status_code == 503
        pending = await owner.get(f"/api/v2/trade-sessions/{session_id}/wait-update-analysis")
        assert pending.json()["request_status"] == "PENDING"
        assert pending.json()["session_status"] == "WAITING"
        request_id = uuid.UUID(pending.json()["analysis_request_id"])

        # The same request and evidence are recovered without another upload.
        good_transport = RecordingTransport()
        app.state.rebuild_analysis_queue = AnalysisRequestQueue(good_transport)
        recovered = await owner.post(
            f"/api/v2/trade-sessions/{session_id}/wait-update-analysis/retry"
        )
        assert recovered.status_code == 202
        assert uuid.UUID(recovered.json()["analysis_request_id"]) == request_id
        assert good_transport.payloads == [{"analysis_request_id": str(request_id)}]

        resolver, invalid_adapter = RecordingImageResolver(), RecordingAdapter({"bad": "response"})
        failed_result = RebuildAnalysisProcessor(
            db_session,
            image_resolver=resolver,  # type: ignore[arg-type]
            adapter_factory=lambda _model: invalid_adapter,  # type: ignore[arg-type]
        )
        processed = await failed_result.process(analysis_request_id=request_id)
        assert processed.status is AnalysisRequestV2Status.FAILED
        failure = await owner.get(f"/api/v2/trade-sessions/{session_id}/wait-update-analysis")
        assert failure.json()["request_status"] == "FAILED"
        assert failure.json()["processed_response"] is None

        good_adapter = RecordingAdapter(_valid_response())
        retry = await owner.post(
            f"/api/v2/trade-sessions/{session_id}/wait-update-analysis/retry"
        )
        assert retry.status_code == 202
        await _process(db_session, request_id, resolver, good_adapter)
        assert good_adapter.calls == 1

    # Real authentication plus ownership filters protect every WAIT route.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as other:
        await _login(other, other_email)
        for method, path in (
            ("post", f"/api/v2/trade-sessions/{session_id}/wait-update-analysis"),
            ("get", f"/api/v2/trade-sessions/{session_id}/wait-update-analysis"),
            ("post", f"/api/v2/trade-sessions/{session_id}/wait-update-analysis/retry"),
        ):
            response = await getattr(other, method)(path)
            assert response.status_code == 404
        assert other_session_id != session_id
