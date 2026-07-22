"""TP-1507: State conflict regression — AI cannot overwrite canonical state.

Proves that the real ProviderRepairService + validate_state_consistency
prevent AI output with a wrong entry price from becoming accepted.
The invalid payload is rejected, repair produces a corrected payload,
and canonical Trade State in the database remains unchanged.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.ai.providers.models import ProviderRequest, ProviderResponse
from app.ai.repair import ProviderRepairService
from app.auth import hash_password
from app.services.actions.open_position import OpenPositionService
from app.services.evidence import EvidenceService
from app.services.trade_session import TradeSessionService
from app.validation.state_consistency import (
    STATE_ENTRY_PRICE_MISMATCH,
    validate_state_consistency,
)

pytestmark = pytest.mark.database

FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent.parent / "schemas" / "fixtures" / "valid" / "v1"
)

CANONICAL_ENTRY = 2800
CANONICAL_QTY = 100
CANONICAL_STOP = 2650
CANONICAL_TARGET = 3100
WRONG_ENTRY = 9999


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _build_canonical_state(session_id: str) -> dict:
    return {
        "session_id": session_id,
        "ticker": "BBRI",
        "position": {
            "position_status": "OPEN",
            "entry_price": str(CANONICAL_ENTRY),
            "original_quantity": str(CANONICAL_QTY),
            "remaining_quantity": str(CANONICAL_QTY),
            "active_stop_loss": str(CANONICAL_STOP),
            "active_target": str(CANONICAL_TARGET),
        },
    }


def _build_wrong_payload(session_id: str) -> dict:
    return {
        "metadata": {
            "session_id": session_id,
            "ticker": "BBRI",
            "original_quantity": CANONICAL_QTY,
            "analysis_id": str(uuid.uuid4()),
            "analysis_type": "OPEN_POSITION_UPDATE",
            "generated_at": _now().isoformat(),
        },
        "position_assessment": {
            "entry_price": WRONG_ENTRY,
            "remaining_quantity": CANONICAL_QTY,
            "active_stop_loss": CANONICAL_STOP,
            "active_target": CANONICAL_TARGET,
            "target_probability": 62,
            "downside_probability": 28,
        },
        "position_status": "OPEN",
    }


class TestStateConflictRegression:
    async def test_wrong_entry_rejected_then_fixed(self, engine: AsyncEngine) -> None:
        factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        async with factory() as session:
            for tbl in (
                "session_events",
                "trade_actions",
                "validation_attempts",
                "provider_requests",
                "context_summaries",
                "analyses",
                "analysis_jobs",
                "evidence",
                "trade_states",
                "trade_sessions",
                "user_sessions",
                "users",
            ):
                await session.execute(text(f"DELETE FROM {tbl}"))
            await session.commit()

            uid = uuid.uuid4()
            email = f"sc_{uid.hex[:8]}@test.com"
            await session.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, account_status) "
                    "VALUES (:id, :e, :ph, 'ACTIVE')"
                ),
                {"id": uid, "e": email, "ph": hash_password("pass")},
            )
            await session.commit()

            ts_svc = TradeSessionService(session)
            ev_svc = EvidenceService(session, storage_root=Path("/tmp"))

            s = await ts_svc.create_session(owner_id=uid, ticker="BBRI")
            sid = s.id

            buf = BytesIO()
            Image.new("RGB", (10, 10), color="red").save(buf, format="PNG")
            png_bytes = buf.getvalue()
            for etype in ("ORDERBOOK_SCREENSHOT", "CHART_THREE_MONTH", "CHART_SIX_MONTH"):
                await ev_svc.create(
                    session_id=sid,
                    owner_id=uid,
                    evidence_type=etype,
                    content=png_bytes,
                    original_filename="t.png",
                    declared_mime_type="image/png",
                )
            await session.commit()

            # --- READY_FOR_ANALYSIS ---
            await session.execute(
                text(
                    "UPDATE trade_sessions SET lifecycle_status=:st, stable_status=:st WHERE id=:s"
                ),
                {"s": sid, "st": "READY_FOR_ANALYSIS"},
            )
            await session.commit()

            # --- Initial Analysis ---
            ia_payload = json.loads((FIXTURE_DIR / "initial_analysis.valid.json").read_text())
            ia_payload["metadata"]["session_id"] = str(sid)
            now = _now()
            ia_id = uuid.uuid4()
            ia_jid = uuid.uuid4()
            await session.execute(
                text(
                    "INSERT INTO analysis_jobs "
                    "(id, session_id, analysis_type, status, "
                    "attempt_count, max_attempts, "
                    "available_at, requested_at, previous_session_status) "
                    "VALUES "
                    "(:j, :s, 'INITIAL_ANALYSIS', 'COMPLETED', "
                    "1, 3, :n, :n, 'READY_FOR_ANALYSIS')"
                ),
                {"j": ia_jid, "s": sid, "n": now},
            )
            await session.execute(
                text(
                    "INSERT INTO analyses "
                    "(id, session_id, analysis_job_id, analysis_type, "
                    "acceptance_status, accepted_at, "
                    "prompt_name, prompt_version, "
                    "schema_name, schema_version, payload, created_at) "
                    "VALUES "
                    "(:a, :s, :j, 'INITIAL_ANALYSIS', 'ACCEPTED', :n, "
                    "'initial_analysis', '1.0.0', "
                    "'initial_analysis', '1.0.0', :p, :n)"
                ),
                {
                    "a": ia_id,
                    "s": sid,
                    "j": ia_jid,
                    "n": now,
                    "p": json.dumps(ia_payload),
                },
            )
            await session.commit()

            # --- WATCHING ---
            await session.execute(
                text(
                    "UPDATE trade_sessions SET lifecycle_status=:st, stable_status=:st WHERE id=:s"
                ),
                {"s": sid, "st": "WATCHING"},
            )
            await session.commit()

            # --- Watching Update ---
            wu_payload = json.loads((FIXTURE_DIR / "watching_update.valid.json").read_text())
            wu_payload["metadata"]["session_id"] = str(sid)
            wu_payload["comparison"]["previous_analysis_id"] = str(ia_id)
            wu_id = uuid.uuid4()
            wu_jid = uuid.uuid4()
            await session.execute(
                text(
                    "INSERT INTO analysis_jobs "
                    "(id, session_id, analysis_type, status, "
                    "attempt_count, max_attempts, "
                    "available_at, requested_at, previous_session_status) "
                    "VALUES "
                    "(:j, :s, 'WATCHING_UPDATE', 'COMPLETED', "
                    "1, 3, :n, :n, 'WATCHING')"
                ),
                {"j": wu_jid, "s": sid, "n": now},
            )
            await session.execute(
                text(
                    "INSERT INTO analyses "
                    "(id, session_id, analysis_job_id, analysis_type, "
                    "acceptance_status, accepted_at, "
                    "prompt_name, prompt_version, "
                    "schema_name, schema_version, payload, created_at) "
                    "VALUES "
                    "(:a, :s, :j, 'WATCHING_UPDATE', 'ACCEPTED', :n, "
                    "'watching_update', '1.0.0', "
                    "'watching_update', '1.0.0', :p, :n)"
                ),
                {
                    "a": wu_id,
                    "s": sid,
                    "j": wu_jid,
                    "n": now,
                    "p": json.dumps(wu_payload),
                },
            )
            await session.commit()

            # --- Open position with canonical values ---
            session.expire_all()
            op = OpenPositionService(session)
            await op.confirm(
                session_id=sid,
                owner_id=uid,
                entry_price=Decimal(str(CANONICAL_ENTRY)),
                quantity=Decimal(str(CANONICAL_QTY)),
                execution_timestamp=datetime.fromisoformat("2026-07-18T10:00:00+07:00"),
                stop_loss=Decimal(str(CANONICAL_STOP)),
                target=Decimal(str(CANONICAL_TARGET)),
                idempotency_key=str(uuid.uuid4()),
            )
            await session.commit()

            # ===== CANONICAL STATE BEFORE =====
            before = (
                await session.execute(
                    text(
                        "SELECT entry_price, original_quantity, "
                        "remaining_quantity, active_stop_loss, "
                        "active_target, position_status "
                        "FROM trade_states WHERE session_id=:s"
                    ),
                    {"s": sid},
                )
            ).first()
            assert before is not None
            assert Decimal(before[0]) == Decimal(str(CANONICAL_ENTRY))

            canonical_state = _build_canonical_state(str(sid))

            # ===== STEP 1: Build payload with wrong entry =====
            wrong_payload = _build_wrong_payload(str(sid))

            # ===== STEP 2: validate_state_consistency rejects =====
            result = validate_state_consistency(wrong_payload, canonical_state)
            assert not result.valid
            codes = {i.code for i in result.issues}
            assert STATE_ENTRY_PRICE_MISMATCH in codes
            entry_issues = [i for i in result.issues if i.code == STATE_ENTRY_PRICE_MISMATCH]
            assert len(entry_issues) >= 1
            issue = entry_issues[0]
            assert issue.expected == str(CANONICAL_ENTRY)
            assert issue.actual == str(WRONG_ENTRY)

            # ===== STEP 3: Mock provider that returns valid OPU =====
            from unittest.mock import AsyncMock, MagicMock

            valid_opu = json.loads((FIXTURE_DIR / "open_position_update.valid.json").read_text())
            valid_opu["metadata"]["session_id"] = str(sid)
            valid_opu["position_assessment"]["entry_price"] = CANONICAL_ENTRY
            valid_opu["position_assessment"]["remaining_quantity"] = CANONICAL_QTY
            valid_opu["position_assessment"]["active_stop_loss"] = CANONICAL_STOP
            valid_opu["position_assessment"]["active_target"] = CANONICAL_TARGET
            valid_opu["position_status"] = "OPEN"
            valid_opu["metadata"]["original_quantity"] = CANONICAL_QTY
            valid_opu_raw = json.dumps(valid_opu)

            mock_client = MagicMock()
            choice = MagicMock()
            choice.message.content = valid_opu_raw
            choice.finish_reason = "stop"
            response = MagicMock()
            response.choices = [choice]
            response.id = "chatcmpl-mock"
            response.model = "deepseek-chat"
            response.created = 1234567890
            usage = MagicMock()
            usage.prompt_tokens = 100
            usage.completion_tokens = 20
            usage.total_tokens = 120
            response.usage = usage
            mock_client.chat_completions_create = AsyncMock(return_value=response)

            from app.ai.providers.deepseek import DeepSeekProvider

            provider = DeepSeekProvider(
                api_key="test-key",
                model_name="deepseek-chat",
                client=mock_client,
            )

            original_resp = ProviderResponse(
                provider=provider.name,
                model=provider.model,
                raw_output=json.dumps(wrong_payload),
                request_id=uuid.uuid4(),
            )

            validation_errors = result.issues

            def validate_fn(p: dict) -> tuple[bool, tuple]:
                sc_result = validate_state_consistency(p, canonical_state)
                return sc_result.valid, tuple(sc_result.issues)

            # ===== STEP 4: Invoke repair =====
            repair_svc = ProviderRepairService()
            repair_result = await repair_svc.repair(
                provider=provider,
                original_request=ProviderRequest(
                    request_id=uuid.uuid4(),
                    analysis_type="OPEN_POSITION_UPDATE",
                    prompt_version="1.0.0",
                    user_prompt="Analyze position.",
                    expected_schema_name="open_position_update",
                    expected_schema_version="1.0.0",
                ),
                original_response=original_resp,
                validation_errors=validation_errors,
                canonical_facts=canonical_state,
                validate=validate_fn,
                max_attempts=3,
            )

            # ===== VERIFICATIONS =====

            # 4. Repair was invoked and succeeded
            assert repair_result is not None
            assert len(repair_result.attempts) >= 1

            # 5. Final accepted payload entry matches canonical
            repaired_entry = repair_result.payload.get("position_assessment", {}).get(
                "entry_price"
            )
            assert repaired_entry == CANONICAL_ENTRY
            assert repaired_entry != WRONG_ENTRY

            # 6. Invalid payload never became accepted
            wrong_stored = await session.execute(
                text("SELECT 1 FROM analyses WHERE session_id=:s AND payload::text LIKE :e"),
                {"s": sid, "e": f"%{WRONG_ENTRY}%"},
            )
            assert wrong_stored.first() is None

            # 7-9. Canonical state entirely unchanged
            after = (
                await session.execute(
                    text(
                        "SELECT entry_price, original_quantity, "
                        "remaining_quantity, active_stop_loss, "
                        "active_target, position_status "
                        "FROM trade_states WHERE session_id=:s"
                    ),
                    {"s": sid},
                )
            ).first()
            assert after is not None
            assert Decimal(after[0]) == Decimal(str(CANONICAL_ENTRY))
            assert Decimal(after[1]) == Decimal(str(CANONICAL_QTY))
            assert Decimal(after[2]) == Decimal(str(CANONICAL_QTY))
            assert Decimal(after[3]) == Decimal(str(CANONICAL_STOP))
            assert Decimal(after[4]) == Decimal(str(CANONICAL_TARGET))
            assert after[5] == "OPEN"

            # 10. Session lifecycle unchanged
            sess_row = (
                await session.execute(
                    text("SELECT lifecycle_status FROM trade_sessions WHERE id=:s"),
                    {"s": sid},
                )
            ).first()
            assert sess_row is not None
            assert sess_row[0] == "OPEN_POSITION"

            await session.rollback()
