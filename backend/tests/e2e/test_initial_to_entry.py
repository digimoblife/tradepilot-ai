"""TP-1504: End-to-end from session creation through confirmed entry.

Exercises the full backend workflow using service classes and direct
DB manipulation for analysis acceptance, with mocked AI output.
No real Gemini/DeepSeek calls.
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


class TestInitialToEntry:
    async def test_full_flow(self, engine: AsyncEngine) -> None:
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

            # ========== Step 1: Create Trade Session ==========
            created = await ts_svc.create_session(owner_id=uid, ticker="BBRI")
            sid = created.id
            assert created.lifecycle_status == "DRAFT"

            # ========== Step 2: Upload required Evidence ==========
            ev_svc = EvidenceService(session, storage_root=Path("/tmp"))
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

            # ========== Step 3: Mark READY_FOR_ANALYSIS ==========
            await session.execute(
                text(
                    "UPDATE trade_sessions SET lifecycle_status=:st, stable_status=:st "
                    "WHERE id=:sid"
                ),
                {"sid": sid, "st": "READY_FOR_ANALYSIS"},
            )
            await session.commit()

            # ========== Step 4: Create and accept Initial Analysis ==========
            ia_payload = _load_fixture("initial_analysis.valid.json")
            ia_payload["metadata"]["session_id"] = str(sid)
            ia_id = uuid.uuid4()
            jid = uuid.uuid4()
            now = _now()
            await session.execute(
                text(
                    "INSERT INTO analysis_jobs (id, session_id, analysis_type, status, "
                    "attempt_count, max_attempts, available_at, requested_at, "
                    "previous_session_status) "
                    "VALUES (:jid, :sid, 'INITIAL_ANALYSIS', 'COMPLETED', 1, 3, :now, :now, 'READY_FOR_ANALYSIS')"
                ),
                {"jid": jid, "sid": sid, "now": now},
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
                    "jid": jid,
                    "now": now,
                    "payload": json.dumps(ia_payload),
                },
            )
            await session.commit()

            # ========== Step 5: Accept IA → triggers WATCHING lifecycle ==========
            await session.execute(
                text(
                    "UPDATE trade_sessions SET lifecycle_status=:st, stable_status=:st "
                    "WHERE id=:sid"
                ),
                {"sid": sid, "st": "WATCHING"},
            )
            await session.commit()

            # ========== Step 6: Create and accept Watching Update ==========
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

            # ========== Step 7: Confirm entry — user values differ from AI proposals ==========
            # Force fresh read: expire ORM cache
            session.expire_all()
            st_row = (
                await session.execute(
                    text("SELECT lifecycle_status FROM trade_sessions WHERE id=:sid"),
                    {"sid": sid},
                )
            ).first()
            assert st_row is not None, "Session not found"
            assert st_row[0] == "WATCHING", f"Expected WATCHING, got {st_row[0]}"

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
            await session.commit()

            # ========== Step 8: Verify canonical state ==========
            ts = action_result.trade_state
            assert ts.position_status == "OPEN"
            assert Decimal(ts.entry_price) == user_entry
            assert Decimal(ts.original_quantity) == user_qty
            assert Decimal(ts.remaining_quantity) == user_qty
            assert Decimal(ts.active_stop_loss) == user_stop
            assert Decimal(ts.active_target) == user_target
            assert action_result.session_status == "OPEN_POSITION"

            detail = (
                await session.execute(
                    text("SELECT lifecycle_status FROM trade_sessions WHERE id=:sid"),
                    {"sid": sid},
                )
            ).first()
            assert detail is not None
            assert detail[0] == "OPEN_POSITION"
            ts_row = (
                await session.execute(
                    text(
                        "SELECT position_status, entry_price, remaining_quantity FROM trade_states WHERE session_id=:sid"
                    ),
                    {"sid": sid},
                )
            ).first()
            assert ts_row is not None
            assert ts_row[0] == "OPEN"
            assert Decimal(ts_row[1]) == user_entry
            assert Decimal(ts_row[2]) == user_qty

            # ========== Step 9: Verify analysis history ==========
            rows = (
                await session.execute(
                    text(
                        "SELECT analysis_type, acceptance_status FROM analyses "
                        "WHERE session_id=:sid ORDER BY created_at"
                    ),
                    {"sid": sid},
                )
            ).all()
            assert len(rows) >= 2
            types = [r[0] for r in rows]
            assert "INITIAL_ANALYSIS" in types
            assert "WATCHING_UPDATE" in types

            # ========== Step 10: Verify action/event records ==========
            ar = (
                await session.execute(
                    text(
                        "SELECT action_type, price, quantity FROM trade_actions "
                        "WHERE session_id=:sid"
                    ),
                    {"sid": sid},
                )
            ).first()
            assert ar is not None
            assert ar[0] == "POSITION_OPENED"
            assert Decimal(ar[1]) == user_entry
            assert Decimal(ar[2]) == user_qty

            # ========== Step 11: Proposal vs canonical separation ==========
            # WU payload reference_entry_price is ~2480, user entry is 2750
            assert user_entry != Decimal(
                str(wu_payload.get("entry_assessment", {}).get("reference_entry_price", 0))
            )

            await session.rollback()
