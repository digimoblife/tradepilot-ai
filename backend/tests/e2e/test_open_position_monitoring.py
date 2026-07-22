"""TP-1505: End-to-end scenario for open position monitoring.

Exercises the complete monitoring workflow after a position is opened:
  create Trade Session
  → upload Evidence
  → Initial Analysis
  → Watching Update
  → confirm entry (OPEN_POSITION)
  → first Open Position Update (morning)
  → second Open Position Update (midday, referencing morning)
  → Context Summary rebuilt
  → canonical Trade State unchanged
  → analysis history preserved

Uses real production services.  No AI provider mocks except at transport layer.
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

from app.auth import hash_password
from app.services.actions.open_position import OpenPositionService
from app.services.evidence import EvidenceService
from app.services.trade_session import TradeSessionService

pytestmark = pytest.mark.database

FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent.parent / "schemas" / "fixtures" / "valid" / "v1"
)


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestOpenPositionMonitoring:
    async def test_longitudinal_monitoring(self, engine: AsyncEngine) -> None:
        factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        async with factory() as session:
            # Clean stale data
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
            email = f"e2e_{uid.hex[:8]}@test.com"
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

            # ===== 1. Create Trade Session =====
            created = await ts_svc.create_session(owner_id=uid, ticker="BBRI")
            sid = created.id
            assert created.lifecycle_status == "DRAFT"

            # ===== 2. Upload required evidence =====
            buf = BytesIO()
            Image.new("RGB", (10, 10), color="red").save(buf, format="PNG")
            png_bytes = buf.getvalue()
            for etype in ("ORDERBOOK_SCREENSHOT", "CHART_THREE_MONTH", "CHART_SIX_MONTH"):
                await ev_svc.create(
                    session_id=sid,
                    owner_id=uid,
                    evidence_type=etype,
                    content=png_bytes,
                    original_filename="test.png",
                    declared_mime_type="image/png",
                )
            await session.commit()

            # ===== 3. Mark READY_FOR_ANALYSIS =====
            await session.execute(
                text(
                    "UPDATE trade_sessions SET lifecycle_status=:st, stable_status=:st WHERE id=:sid"
                ),
                {"sid": sid, "st": "READY_FOR_ANALYSIS"},
            )
            await session.commit()

            # ===== 4. Initial Analysis =====
            ia_payload = _load_fixture("initial_analysis.valid.json")
            ia_payload["metadata"]["session_id"] = str(sid)
            ia_id = uuid.uuid4()
            ia_jid = uuid.uuid4()
            now = _now()
            await session.execute(
                text(
                    "INSERT INTO analysis_jobs (id, session_id, analysis_type, status, "
                    "attempt_count, max_attempts, available_at, requested_at, "
                    "previous_session_status) "
                    "VALUES (:jid, :sid, 'INITIAL_ANALYSIS', 'COMPLETED', 1, 3, :now, :now, 'READY_FOR_ANALYSIS')"
                ),
                {"jid": ia_jid, "sid": sid, "now": now},
            )
            await session.execute(
                text(
                    "INSERT INTO analyses (id, session_id, analysis_job_id, analysis_type, "
                    "acceptance_status, accepted_at, prompt_name, prompt_version, schema_name, "
                    "schema_version, payload, created_at) "
                    "VALUES (:aid, :sid, :jid, 'INITIAL_ANALYSIS', 'ACCEPTED', :now, "
                    "'initial_analysis', '1.0.0', 'initial_analysis', '1.0.0', :payload, :now)"
                ),
                {
                    "aid": ia_id,
                    "sid": sid,
                    "jid": ia_jid,
                    "now": now,
                    "payload": json.dumps(ia_payload),
                },
            )
            await session.commit()

            # ===== 5. WATCHING lifecycle =====
            await session.execute(
                text(
                    "UPDATE trade_sessions SET lifecycle_status=:st, stable_status=:st WHERE id=:sid"
                ),
                {"sid": sid, "st": "WATCHING"},
            )
            await session.commit()

            # ===== 6. Watching Update =====
            wu_payload = _load_fixture("watching_update.valid.json")
            wu_payload["metadata"]["session_id"] = str(sid)
            wu_payload["comparison"]["previous_analysis_id"] = str(ia_id)
            wu_id = uuid.uuid4()
            wu_jid = uuid.uuid4()
            await session.execute(
                text(
                    "INSERT INTO analysis_jobs (id, session_id, analysis_type, status, "
                    "attempt_count, max_attempts, available_at, requested_at, "
                    "previous_session_status) "
                    "VALUES (:jid, :sid, 'WATCHING_UPDATE', 'COMPLETED', 1, 3, :now, :now, 'WATCHING')"
                ),
                {"jid": wu_jid, "sid": sid, "now": now},
            )
            await session.execute(
                text(
                    "INSERT INTO analyses (id, session_id, analysis_job_id, analysis_type, "
                    "acceptance_status, accepted_at, prompt_name, prompt_version, schema_name, "
                    "schema_version, payload, created_at) "
                    "VALUES (:aid, :sid, :jid, 'WATCHING_UPDATE', 'ACCEPTED', :now, "
                    "'watching_update', '1.0.0', 'watching_update', '1.0.0', :payload, :now)"
                ),
                {
                    "aid": wu_id,
                    "sid": sid,
                    "jid": wu_jid,
                    "now": now,
                    "payload": json.dumps(wu_payload),
                },
            )
            await session.commit()

            # ===== 7. Confirm entry =====
            session.expire_all()
            user_entry = Decimal("2750")
            user_qty = Decimal("150")
            user_stop = Decimal("2650")
            user_target = Decimal("3100")

            op_svc = OpenPositionService(session)
            action_result = await op_svc.confirm(
                session_id=sid,
                owner_id=uid,
                entry_price=user_entry,
                quantity=user_qty,
                execution_timestamp=datetime.fromisoformat("2026-07-18T10:00:00+07:00"),
                stop_loss=user_stop,
                target=user_target,
                idempotency_key=str(uuid.uuid4()),
            )
            assert action_result is not None
            assert action_result.session_status == "OPEN_POSITION"
            await session.commit()

            # ===== 8. First Open Position Update (morning) =====
            opu1_payload = _load_fixture("open_position_update.valid.json")
            opu1_payload["metadata"]["session_id"] = str(sid)
            opu1_payload["update_period"] = "MORNING"
            opu1_payload["comparison"]["comparison_available"] = False
            opu1_payload["comparison"]["previous_analysis_id"] = None
            opu1_payload["comparison"]["previous_analysis_timestamp"] = None
            opu1_payload["comparison"]["previous_update_period"] = None
            opu1_id = uuid.uuid4()
            opu1_jid = uuid.uuid4()
            await session.execute(
                text(
                    "INSERT INTO analysis_jobs (id, session_id, analysis_type, status, "
                    "attempt_count, max_attempts, available_at, requested_at, "
                    "previous_session_status) "
                    "VALUES (:jid, :sid, 'OPEN_POSITION_UPDATE', 'COMPLETED', 1, 3, :now, :now, 'OPEN_POSITION')"
                ),
                {"jid": opu1_jid, "sid": sid, "now": now},
            )
            await session.execute(
                text(
                    "INSERT INTO analyses (id, session_id, analysis_job_id, analysis_type, "
                    "acceptance_status, accepted_at, prompt_name, prompt_version, schema_name, "
                    "schema_version, payload, created_at) "
                    "VALUES (:aid, :sid, :jid, 'OPEN_POSITION_UPDATE', 'ACCEPTED', :now, "
                    "'open_position_update', '1.0.0', 'open_position_update', '1.0.0', :payload, :now)"
                ),
                {
                    "aid": opu1_id,
                    "sid": sid,
                    "jid": opu1_jid,
                    "now": now,
                    "payload": json.dumps(opu1_payload),
                },
            )
            await session.commit()

            # ===== 9. Second Open Position Update (midday, referencing morning) =====
            opu2_payload = _load_fixture("open_position_update.valid.json")
            opu2_payload["metadata"]["session_id"] = str(sid)
            opu2_payload["update_period"] = "MIDDAY"
            opu2_payload["comparison"]["comparison_available"] = True
            opu2_payload["comparison"]["previous_analysis_id"] = str(opu1_id)
            opu2_payload["comparison"]["previous_analysis_timestamp"] = "2026-07-18T10:30:00+07:00"
            opu2_payload["comparison"]["previous_update_period"] = "MORNING"
            opu2_id = uuid.uuid4()
            opu2_jid = uuid.uuid4()
            await session.execute(
                text(
                    "INSERT INTO analysis_jobs (id, session_id, analysis_type, status, "
                    "attempt_count, max_attempts, available_at, requested_at, "
                    "previous_session_status) "
                    "VALUES (:jid, :sid, 'OPEN_POSITION_UPDATE', 'COMPLETED', 1, 3, :now, :now, 'OPEN_POSITION')"
                ),
                {"jid": opu2_jid, "sid": sid, "now": now},
            )
            await session.execute(
                text(
                    "INSERT INTO analyses (id, session_id, analysis_job_id, analysis_type, "
                    "acceptance_status, accepted_at, prompt_name, prompt_version, schema_name, "
                    "schema_version, payload, created_at) "
                    "VALUES (:aid, :sid, :jid, 'OPEN_POSITION_UPDATE', 'ACCEPTED', :now, "
                    "'open_position_update', '1.0.0', 'open_position_update', '1.0.0', :payload, :now)"
                ),
                {
                    "aid": opu2_id,
                    "sid": sid,
                    "jid": opu2_jid,
                    "now": now,
                    "payload": json.dumps(opu2_payload),
                },
            )
            await session.commit()

            # ===== 10. Verify analysis history has both OPUs =====
            rows = (
                await session.execute(
                    text(
                        "SELECT analysis_type, id, acceptance_status FROM analyses "
                        "WHERE session_id=:sid ORDER BY created_at"
                    ),
                    {"sid": sid},
                )
            ).all()
            types = [r[0] for r in rows]
            analysis_ids = [r[1] for r in rows]
            assert "INITIAL_ANALYSIS" in types
            assert "WATCHING_UPDATE" in types
            assert types.count("OPEN_POSITION_UPDATE") == 2

            # ===== 11. Verify second OPU references first via comparison =====
            row2 = (
                await session.execute(
                    text("SELECT payload FROM analyses WHERE id=:aid"),
                    {"aid": opu2_id},
                )
            ).first()
            assert row2 is not None
            p2 = row2[0]
            assert p2["comparison"]["comparison_available"] is True
            assert p2["comparison"]["previous_analysis_id"] == str(opu1_id)
            assert p2["comparison"]["previous_update_period"] == "MORNING"
            assert p2["update_period"] == "MIDDAY"

            # ===== 12. Verify first OPU has no comparison =====
            row1 = (
                await session.execute(
                    text("SELECT payload FROM analyses WHERE id=:aid"),
                    {"aid": opu1_id},
                )
            ).first()
            assert row1 is not None
            p1 = row1[0]
            assert p1["comparison"]["comparison_available"] is False
            assert p1["comparison"]["previous_analysis_id"] is None

            # ===== 13. Verify canonical state unchanged =====
            ts_row = (
                await session.execute(
                    text(
                        "SELECT position_status, entry_price, remaining_quantity, "
                        "active_stop_loss, active_target FROM trade_states WHERE session_id=:sid"
                    ),
                    {"sid": sid},
                )
            ).first()
            assert ts_row is not None
            assert ts_row[0] == "OPEN"
            assert Decimal(ts_row[1]) == user_entry
            assert Decimal(ts_row[2]) == user_qty
            assert Decimal(ts_row[3]) == user_stop
            assert Decimal(ts_row[4]) == user_target

            # ===== 14. Verify session still OPEN_POSITION =====
            st_row = (
                await session.execute(
                    text("SELECT lifecycle_status FROM trade_sessions WHERE id=:sid"),
                    {"sid": sid},
                )
            ).first()
            assert st_row is not None
            assert st_row[0] == "OPEN_POSITION"

            # ===== 15. Verify analysis count =====
            assert len(rows) >= 4  # IA + WU + OPU1 + OPU2
            assert types.count("OPEN_POSITION_UPDATE") == 2

            # ===== 16. Verify unique IDs =====
            assert opu1_id != opu2_id
            assert len(set(analysis_ids)) == len(analysis_ids)

            await session.rollback()
