"""TP-1506: End-to-end from open position through partial/full exit.

Exercises the complete closing lifecycle:
  OPEN_POSITION
  → partial exit
  → Partial Exit Review
  → full exit
  → Closing Analysis + journal
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
from app.services.actions.partial_exit import PartialExitActionService
from app.services.actions.full_exit import FullExitActionService
from app.services.context_rebuild import ContextRebuildService, ContextRebuildReason
from app.services.evidence import EvidenceService
from app.services.trade_session import TradeSessionService

pytestmark = pytest.mark.database
FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent.parent / "schemas" / "fixtures" / "valid" / "v1"
)
ORIG = 100
PE_QTY = 40
FE_QTY = 60


def _load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestPartialAndFullExit:
    async def test_full_closing_lifecycle(self, engine: AsyncEngine) -> None:
        factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        async with factory() as session:
            for t in (
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
                await session.execute(text(f"DELETE FROM {t}"))
            await session.commit()

            uid = uuid.uuid4()
            await session.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, account_status) "
                    "VALUES (:id, :e, :ph, 'ACTIVE')"
                ),
                {"id": uid, "e": f"e2e_{uid.hex[:8]}@t.com", "ph": hash_password("p")},
            )
            await session.commit()

            ts_svc = TradeSessionService(session)
            ev_svc = EvidenceService(session, storage_root=Path("/tmp"))

            # -- DRAFT session --
            s = await ts_svc.create_session(owner_id=uid, ticker="BBRI")
            sid = s.id
            assert s.lifecycle_status == "DRAFT"

            # -- Evidence --
            buf = BytesIO()
            Image.new("RGB", (10, 10), color="red").save(buf, format="PNG")
            png = buf.getvalue()
            for et in ("ORDERBOOK_SCREENSHOT", "CHART_THREE_MONTH", "CHART_SIX_MONTH"):
                await ev_svc.create(
                    session_id=sid,
                    owner_id=uid,
                    evidence_type=et,
                    content=png,
                    original_filename="t.png",
                    declared_mime_type="image/png",
                )
            await session.commit()

            # -- READY + IA --
            await session.execute(
                text(
                    "UPDATE trade_sessions SET lifecycle_status='READY_FOR_ANALYSIS', stable_status='READY_FOR_ANALYSIS' WHERE id=:sid"
                ),
                {"sid": sid},
            )
            await session.commit()

            ia_j = uuid.uuid4()
            ia = _load("initial_analysis.valid.json")
            ia["metadata"]["session_id"] = str(sid)
            ts1 = _now()
            await session.execute(
                text(
                    "INSERT INTO analysis_jobs (id, session_id, analysis_type, status, attempt_count, max_attempts, available_at, requested_at, previous_session_status) VALUES (:j,:s,'INITIAL_ANALYSIS','COMPLETED',1,3,:n,:n,'READY_FOR_ANALYSIS')"
                ),
                {"j": ia_j, "s": sid, "n": ts1},
            )
            await session.execute(
                text(
                    "INSERT INTO analyses (id, session_id, analysis_job_id, analysis_type, acceptance_status, accepted_at, prompt_name, prompt_version, schema_name, schema_version, payload, created_at) VALUES (:a,:s,:j,'INITIAL_ANALYSIS','ACCEPTED',:n,'initial_analysis','1.0.0','initial_analysis','1.0.0',:p,:n)"
                ),
                {"a": uuid.uuid4(), "s": sid, "j": ia_j, "n": ts1, "p": json.dumps(ia)},
            )
            await session.commit()

            # -- WATCHING + WU --
            await session.execute(
                text(
                    "UPDATE trade_sessions SET lifecycle_status='WATCHING', stable_status='WATCHING' WHERE id=:sid"
                ),
                {"sid": sid},
            )
            await session.commit()

            wu_j = uuid.uuid4()
            wu_a = uuid.uuid4()
            wu = _load("watching_update.valid.json")
            wu["metadata"]["session_id"] = str(sid)
            await session.execute(
                text(
                    "INSERT INTO analysis_jobs (id, session_id, analysis_type, status, attempt_count, max_attempts, available_at, requested_at, previous_session_status) VALUES (:j,:s,'WATCHING_UPDATE','COMPLETED',1,3,:n,:n,'WATCHING')"
                ),
                {"j": wu_j, "s": sid, "n": _now()},
            )
            await session.execute(
                text(
                    "INSERT INTO analyses (id, session_id, analysis_job_id, analysis_type, acceptance_status, accepted_at, prompt_name, prompt_version, schema_name, schema_version, payload, created_at) VALUES (:a,:s,:j,'WATCHING_UPDATE','ACCEPTED',:n,'watching_update','1.0.0','watching_update','1.0.0',:p,:n)"
                ),
                {"a": wu_a, "s": sid, "j": wu_j, "n": _now(), "p": json.dumps(wu)},
            )
            await session.commit()

            # -- OPEN position --
            session.expire_all()

            entry = Decimal("2800")
            stop = Decimal("2650")
            tgt = Decimal("3100")
            op = OpenPositionService(session)
            or_ = await op.confirm(
                session_id=sid,
                owner_id=uid,
                entry_price=entry,
                quantity=Decimal(str(ORIG)),
                execution_timestamp=datetime.fromisoformat("2026-07-18T10:00:00+07:00"),
                stop_loss=stop,
                target=tgt,
                idempotency_key=str(uuid.uuid4()),
            )
            assert or_.session_status == "OPEN_POSITION"
            await session.commit()

            # -- PARTIAL exit --
            pe_px = Decimal("2950")
            pe = PartialExitActionService(session)
            per = await pe.confirm(
                session_id=sid,
                owner_id=uid,
                exit_price=pe_px,
                exit_quantity=Decimal(str(PE_QTY)),
                executed_at=datetime.fromisoformat("2026-07-21T10:00:00+07:00"),
                reason="PARTIAL_TAKE_PROFIT",
                idempotency_key=str(uuid.uuid4()),
            )
            assert Decimal(per.remaining_quantity) == Decimal(str(ORIG - PE_QTY))
            assert Decimal(per.realized_pnl) > 0
            await session.commit()

            # -- PER --
            per_p = _load("partial_exit_review.valid.json")
            per_p["metadata"]["session_id"] = str(sid)
            per_p["partial_exit_confirmation"]["exited_quantity"] = PE_QTY
            per_p["partial_exit_confirmation"]["remaining_quantity"] = FE_QTY
            per_p["result_summary"]["exited_quantity"] = PE_QTY
            per_p["result_summary"]["remaining_quantity"] = FE_QTY
            per_p["result_summary"]["entry_price"] = int(entry)
            per_p["result_summary"]["partial_exit_price"] = int(pe_px)
            per_p["remaining_position_assessment"]["entry_price"] = int(entry)
            per_p["remaining_position_assessment"]["original_quantity"] = ORIG
            per_p["remaining_position_assessment"]["exited_quantity"] = PE_QTY
            per_p["remaining_position_assessment"]["remaining_quantity"] = FE_QTY
            per_p["remaining_position_assessment"]["active_stop_loss"] = int(stop)
            per_p["remaining_position_assessment"]["active_target"] = int(tgt)
            per_id = uuid.uuid4()
            per_j = uuid.uuid4()
            await session.execute(
                text(
                    "INSERT INTO analysis_jobs (id,session_id,analysis_type,status,attempt_count,max_attempts,available_at,requested_at,previous_session_status) VALUES (:j,:s,'PARTIAL_EXIT_REVIEW','COMPLETED',1,3,:n,:n,'PARTIALLY_CLOSED')"
                ),
                {"j": per_j, "s": sid, "n": _now()},
            )
            await session.execute(
                text(
                    "INSERT INTO analyses (id,session_id,analysis_job_id,analysis_type,acceptance_status,accepted_at,prompt_name,prompt_version,schema_name,schema_version,payload,created_at) VALUES (:a,:s,:j,'PARTIAL_EXIT_REVIEW','PENDING',:n,'partial_exit_review','1.0.0','partial_exit_review','1.0.0',:p,:n)"
                ),
                {"a": per_id, "s": sid, "j": per_j, "n": _now(), "p": json.dumps(per_p)},
            )
            await session.commit()
            # accept + rebuild
            await session.execute(
                text(
                    "UPDATE analyses SET acceptance_status='ACCEPTED', accepted_at=:n WHERE id=:a"
                ),
                {"a": per_id, "n": _now()},
            )
            await session.commit()
            rb = ContextRebuildService(session)
            await rb.rebuild_after_material_event(
                session_id=sid,
                owner_id=uid,
                reason=ContextRebuildReason.PARTIAL_EXIT,
                source_id=per_id,
            )
            await session.commit()

            # verify PER
            pr = (
                await session.execute(
                    text("SELECT payload FROM analyses WHERE id=:a"), {"a": per_id}
                )
            ).first()
            assert pr[0]["partial_exit_confirmation"]["exited_quantity"] == PE_QTY
            assert pr[0]["partial_exit_confirmation"]["remaining_quantity"] == FE_QTY

            # -- FULL exit --
            fe = FullExitActionService(session)
            fer = await fe.confirm(
                session_id=sid,
                owner_id=uid,
                exit_price=Decimal("2910"),
                exit_quantity=Decimal(str(FE_QTY)),
                executed_at=datetime.fromisoformat("2026-07-25T14:30:00+07:00"),
                closing_reason="TAKE_PROFIT",
                idempotency_key=str(uuid.uuid4()),
            )
            assert fer.gross_pnl is not None
            assert Decimal(str(fer.gross_pnl)) > 0
            await session.commit()

            # -- Closing Analysis --
            ca_p = _load("closing_analysis.valid.json")
            ca_p["metadata"]["session_id"] = str(sid)
            ca_id = uuid.uuid4()
            ca_j = uuid.uuid4()
            await session.execute(
                text(
                    "INSERT INTO analysis_jobs (id,session_id,analysis_type,status,attempt_count,max_attempts,available_at,requested_at,previous_session_status) VALUES (:j,:s,'CLOSING_ANALYSIS','COMPLETED',1,3,:n,:n,'CLOSED_TAKE_PROFIT')"
                ),
                {"j": ca_j, "s": sid, "n": _now()},
            )
            await session.execute(
                text(
                    "INSERT INTO analyses (id,session_id,analysis_job_id,analysis_type,acceptance_status,accepted_at,prompt_name,prompt_version,schema_name,schema_version,payload,created_at) VALUES (:a,:s,:j,'CLOSING_ANALYSIS','PENDING',:n,'closing_analysis','1.0.0','closing_analysis','1.0.0',:p,:n)"
                ),
                {"a": ca_id, "s": sid, "j": ca_j, "n": _now(), "p": json.dumps(ca_p)},
            )
            await session.commit()
            # accept + rebuild
            await session.execute(
                text(
                    "UPDATE analyses SET acceptance_status='ACCEPTED', accepted_at=:n WHERE id=:a"
                ),
                {"a": ca_id, "n": _now()},
            )
            await session.commit()
            await rb.rebuild_after_material_event(
                session_id=sid,
                owner_id=uid,
                reason=ContextRebuildReason.FULL_EXIT,
                source_id=ca_id,
            )
            await session.commit()

            # -- Verify CA --
            cr = (
                await session.execute(
                    text("SELECT payload FROM analyses WHERE id=:a"), {"a": ca_id}
                )
            ).first()
            assert cr[0]["closing_confirmation"]["closing_reason"] in (
                "TAKE_PROFIT",
                "MANUAL_EXIT",
            )
            assert len(cr[0]["journal_summary"]["one_sentence_review"]) > 0

            # -- Canonical state --
            tr = (
                await session.execute(
                    text(
                        "SELECT position_status,entry_price,remaining_quantity,active_stop_loss,active_target FROM trade_states WHERE session_id=:s"
                    ),
                    {"s": sid},
                )
            ).first()
            assert tr[0] == "CLOSED"
            assert Decimal(tr[1]) == entry
            assert Decimal(tr[2]) == Decimal("0")
            assert tr[3] is None
            assert tr[4] is None

            # -- Lifecycle --
            sr = (
                await session.execute(
                    text("SELECT lifecycle_status FROM trade_sessions WHERE id=:s"), {"s": sid}
                )
            ).first()
            assert sr[0] in ("CLOSED_TAKE_PROFIT", "CLOSED_MANUAL", "CLOSED_STOP_LOSS")

            # -- Analysis history --
            rs = (
                await session.execute(
                    text(
                        "SELECT analysis_type FROM analyses WHERE session_id=:s ORDER BY created_at"
                    ),
                    {"s": sid},
                )
            ).all()
            at = [r[0] for r in rs]
            for t in (
                "INITIAL_ANALYSIS",
                "WATCHING_UPDATE",
                "PARTIAL_EXIT_REVIEW",
                "CLOSING_ANALYSIS",
            ):
                assert t in at

            # -- Actions --
            ac = (
                await session.execute(
                    text(
                        "SELECT action_type, price, quantity FROM trade_actions WHERE session_id=:s ORDER BY created_at"
                    ),
                    {"s": sid},
                )
            ).all()
            assert len(ac) >= 3
            assert ac[0][0] == "POSITION_OPENED"
            assert ac[1][0] == "PARTIAL_EXIT"
            assert ac[2][0] == "FULL_EXIT"

            # -- Quantity reconciliation --
            qtotal = sum(Decimal(str(a[2])) for a in ac if a[0] in ("PARTIAL_EXIT", "FULL_EXIT"))
            assert qtotal == Decimal(str(ORIG))

            await session.rollback()
