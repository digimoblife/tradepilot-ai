"""P9 — Production-Like E2E Smoke Test Suite (TP-1509).

Executes the full TradePilot AI lifecycle against the running production-like stack
(Gateway, Frontend, Backend, Worker, PostgreSQL) via HTTP requests and real Gemini API.
"""

import asyncio
import io
import time
import uuid
import httpx
from PIL import Image

GATEWAY_URL = "http://localhost:8181"


def create_synthetic_image_bytes(color: str = "blue") -> bytes:
    """Generate compact PNG image bytes suitable for vision AI upload."""
    img = Image.new("RGB", (100, 100), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def run_p9_smoke_test() -> dict:
    """Run full E2E lifecycle smoke test against gateway at http://localhost:8181."""
    async with httpx.AsyncClient(base_url=GATEWAY_URL, timeout=120.0, follow_redirects=True) as client:
        # 1. Health check
        r = await client.get("/health/ready")
        assert r.status_code == 200, f"Health ready failed: {r.text}"
        print("[PASS] 1. Gateway and Backend health ready")

        # 2. Login / Session Cookie
        user_email = "p9_smoke_user@example.com"
        password = "SmokeTestPassword123!"
        r = await client.post("/api/auth/login", json={"email": user_email, "password": password})
        assert r.status_code == 200, f"Auth login failed: {r.text}"
        print(f"[PASS] 2. User authenticated: {user_email}")

        # 3. Create Session 1 (BBRI)
        r = await client.post("/api/trade-sessions", json={"ticker": "BBRI", "company_name": "Bank Rakyat Indonesia"})
        assert r.status_code == 201, f"Create session failed: {r.text}"
        session1 = r.json()
        s1_id = session1["id"]
        print(f"[PASS] 3. Session 1 created: {s1_id} (BBRI)")

        # 4. Upload Initial Evidence (3 files)
        img_ob = create_synthetic_image_bytes("blue")
        img_3m = create_synthetic_image_bytes("green")
        img_6m = create_synthetic_image_bytes("red")

        for etype, img_bytes, fname in [
            ("ORDERBOOK_SCREENSHOT", img_ob, "ob.png"),
            ("CHART_THREE_MONTH", img_3m, "c3m.png"),
            ("CHART_SIX_MONTH", img_6m, "c6m.png"),
        ]:
            files = {"file": (fname, img_bytes, "image/png")}
            data = {"evidence_type": etype}
            r = await client.post(f"/api/trade-sessions/{s1_id}/evidence", data=data, files=files)
            assert r.status_code == 201, f"Upload evidence {etype} failed: {r.text}"
        print("[PASS] 4. Initial Analysis evidence uploaded (Orderbook, 3M, 6M)")

        # 5. Mark Ready
        r = await client.post(f"/api/trade-sessions/{s1_id}/ready")
        assert r.status_code == 200, f"Mark ready failed: {r.text}"
        print("[PASS] 5. Session marked READY_FOR_INITIAL_ANALYSIS")

        # 6. Request Initial Analysis (Triggers real Gemini API call via worker)
        r = await client.post(f"/api/trade-sessions/{s1_id}/analyses", json={"analysis_type": "INITIAL_ANALYSIS"})
        assert r.status_code == 202, f"Request Initial Analysis failed: {r.text}"
        job_data = r.json()
        job1_id = job_data["job_id"]
        batch1_id = job_data.get("evidence_batch_id")
        print(f"[PASS] 6. Initial Analysis requested (Job: {job1_id})")        # 7. Wait for worker & Gemini analysis completion
        start_t = time.time()
        completed_analysis = None
        while time.time() - start_t < 300:
            r = await client.get(f"/api/analysis-jobs/{job1_id}")
            if r.status_code == 200 and r.json().get("status") == "COMPLETED":
                r_ana = await client.get(f"/api/trade-sessions/{s1_id}/analyses")
                if r_ana.status_code == 200:
                    items = r_ana.json().get("analyses") or r_ana.json().get("items") or []
                    if items:
                        completed_analysis = items[0]
                        break
            await asyncio.sleep(3)
        assert completed_analysis is not None, "Initial Analysis failed to complete within timeout"
        print("[PASS] 7. Real Gemini Initial Analysis completed & accepted")

        # 8. Verify session status INITIAL_ANALYZED
        r = await client.get(f"/api/trade-sessions/{s1_id}")
        assert r.status_code == 200
        sess_data = r.json()
        assert sess_data["session"]["lifecycle_status"] == "INITIAL_ANALYZED"
        print("[PASS] 8. Session status updated to INITIAL_ANALYZED")

        # 9. Action: WAIT -> WATCHING
        r = await client.post("/api/actions/wait", json={"session_id": str(s1_id), "idempotency_key": uuid.uuid4().hex, "confirmed_at": "2026-07-28T09:00:00Z"})
        assert r.status_code == 200, f"Wait action failed: {r.text}"
        print("[PASS] 9. User action WAIT executed -> session WATCHING")

        # 10. Upload Watching Update Evidence
        files = {"file": ("ob_watch.png", create_synthetic_image_bytes("cyan"), "image/png")}
        data = {"evidence_type": "ORDERBOOK_SCREENSHOT"}
        r = await client.post(f"/api/trade-sessions/{s1_id}/evidence", data=data, files=files)
        assert r.status_code == 201, f"Upload watching evidence failed: {r.text}"
        print("[PASS] 10. Watching Update evidence uploaded")

        # 10b. Mark Watching Batch Ready
        import subprocess
        cmd = [
            "docker", "compose", "-p", "tradepilot-p9-smoke", "-f", "docker-compose.production.yml",
            "exec", "-T", "backend", "python", "-c",
            f"import asyncio; from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker; from sqlalchemy import text; main = lambda: async_sessionmaker(create_async_engine('postgresql+asyncpg://tradepilot:change_me@postgres:5432/tradepilot'), class_=AsyncSession)().execute(text(\"SELECT id FROM evidence_batches WHERE session_id = '{s1_id}' AND analysis_type = 'WATCHING_UPDATE' AND status = 'DRAFT' ORDER BY created_at DESC LIMIT 1\")); print(asyncio.run(main()).scalar_one())"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        current_watching_batch_id = res.stdout.strip()
        r = await client.post(f"/api/trade-sessions/{s1_id}/watching-batches/{current_watching_batch_id}/ready")
        assert r.status_code == 200, f"Mark watching batch ready failed: {r.text}"

        # 11. Request Watching Update
        r = await client.post(f"/api/trade-sessions/{s1_id}/analyses", json={"analysis_type": "WATCHING_UPDATE"})
        assert r.status_code == 202, f"Request Watching Update failed: {r.text}"
        job2_id = r.json()["job_id"]

        start_t = time.time()
        completed_watching = None
        while time.time() - start_t < 300:
            r = await client.get(f"/api/analysis-jobs/{job2_id}")
            if r.status_code == 200 and r.json().get("status") == "COMPLETED":
                r_ana = await client.get(f"/api/trade-sessions/{s1_id}/analyses")
                if r_ana.status_code == 200:
                    items = r_ana.json().get("analyses") or r_ana.json().get("items") or []
                    matched = [i for i in items if i.get("analysis_type") == "WATCHING_UPDATE"]
                    if matched:
                        completed_watching = matched[0]
                        break
            await asyncio.sleep(3)
        assert completed_watching is not None, "Watching Update failed to complete"
        print("[PASS] 11. Real Gemini Watching Update completed & accepted")

        # 12. Action: BUY (Enter position) -> OPEN_POSITION
        r = await client.post(
            "/api/actions/open-position",
            json={
                "session_id": str(s1_id),
                "idempotency_key": uuid.uuid4().hex,
                "entry_price": 5000,
                "quantity": 100,
                "executed_at": "2026-07-28T09:00:00Z",
                "stop_loss": 4800,
                "take_profit": 5500,
            },
        )
        assert r.status_code == 200, f"BUY action failed: {r.text}"
        print("[PASS] 12. User action BUY executed -> session OPEN_POSITION")

        # 13. Upload Open Position Evidence & Request Open Position Update
        files = {"file": ("ob_open.png", create_synthetic_image_bytes("yellow"), "image/png")}
        data = {"evidence_type": "ORDERBOOK_SCREENSHOT"}
        r = await client.post(f"/api/trade-sessions/{s1_id}/evidence", data=data, files=files)
        assert r.status_code == 201

        # 13b. Mark Open Position Batch Ready
        cmd_op = [
            "docker", "compose", "-p", "tradepilot-p9-smoke", "-f", "docker-compose.production.yml",
            "exec", "-T", "backend", "python", "-c",
            f"import asyncio; from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker; from sqlalchemy import text; main = lambda: async_sessionmaker(create_async_engine('postgresql+asyncpg://tradepilot:change_me@postgres:5432/tradepilot'), class_=AsyncSession)().execute(text(\"SELECT id FROM evidence_batches WHERE session_id = '{s1_id}' AND analysis_type = 'OPEN_POSITION_UPDATE' AND status = 'DRAFT' ORDER BY created_at DESC LIMIT 1\")); print(asyncio.run(main()).scalar_one())"
        ]
        res_op = subprocess.run(cmd_op, capture_output=True, text=True, check=True)
        current_op_batch_id = res_op.stdout.strip()
        r = await client.post(f"/api/trade-sessions/{s1_id}/open-position-batches/{current_op_batch_id}/ready")
        assert r.status_code == 200, f"Mark open position batch ready failed: {r.text}"

        r = await client.post(f"/api/trade-sessions/{s1_id}/analyses", json={"analysis_type": "OPEN_POSITION_UPDATE"})
        assert r.status_code == 202
        job3_id = r.json()["job_id"]

        start_t = time.time()
        completed_open_pos = None
        while time.time() - start_t < 300:
            r = await client.get(f"/api/analysis-jobs/{job3_id}")
            if r.status_code == 200 and r.json().get("status") == "COMPLETED":
                r_ana = await client.get(f"/api/trade-sessions/{s1_id}/analyses")
                if r_ana.status_code == 200:
                    items = r_ana.json().get("analyses") or r_ana.json().get("items") or []
                    matched = [i for i in items if i.get("analysis_type") == "OPEN_POSITION_UPDATE"]
                    if matched:
                        completed_open_pos = matched[0]
                        break
            await asyncio.sleep(3)
        assert completed_open_pos is not None, "Open Position Update failed to complete"
        print("[PASS] 13. Real Gemini Open Position Update completed & accepted")

        # 14. Adjust Target / Stop Loss
        r = await client.post(
            "/api/actions/change-target",
            json={"session_id": str(s1_id), "idempotency_key": uuid.uuid4().hex, "target": 5600, "confirmed_at": "2026-07-28T09:30:00Z"},
        )
        assert r.status_code == 200, f"Target change failed: {r.text}"
        print("[PASS] 14. Target adjusted to 5600")

        # 15. Action: SELL (Full Exit) -> CLOSED
        r = await client.post(
            "/api/actions/full-exit",
            json={
                "session_id": str(s1_id),
                "idempotency_key": uuid.uuid4().hex,
                "exit_price": 5500,
                "exit_quantity": 100,
                "executed_at": "2026-07-28T10:00:00Z",
                "closing_reason": "TAKE_PROFIT",
            },
        )
        assert r.status_code == 200, f"Full exit failed: {r.text}"
        print("[PASS] 15. User action SELL executed -> session CLOSED")

        # 16. Request Closing Analysis
        r = await client.post(f"/api/trade-sessions/{s1_id}/analyses", json={"analysis_type": "CLOSING_ANALYSIS"})
        assert r.status_code == 202
        job4_id = r.json()["job_id"]

        start_t = time.time()
        completed_closing = None
        while time.time() - start_t < 300:
            r = await client.get(f"/api/analysis-jobs/{job4_id}")
            if r.status_code == 200 and r.json().get("status") == "COMPLETED":
                r_ana = await client.get(f"/api/trade-sessions/{s1_id}/analyses")
                if r_ana.status_code == 200:
                    items = r_ana.json().get("analyses") or r_ana.json().get("items") or []
                    matched = [i for i in items if i.get("analysis_type") == "CLOSING_ANALYSIS"]
                    if matched:
                        completed_closing = matched[0]
                        break
            await asyncio.sleep(3)
        assert completed_closing is not None, "Closing Analysis failed to complete"
        print("[PASS] 16. Real Gemini Closing Analysis completed & accepted")

        # 17. Verify CLOSED session remains read-only
        r = await client.post(
            "/api/actions/wait", json={"session_id": str(s1_id), "idempotency_key": uuid.uuid4().hex, "confirmed_at": "2026-07-28T11:00:00Z"}
        )
        assert r.status_code in (400, 409, 422), "Closed session permitted illegal mutation"
        print("[PASS] 17. Closed session is strictly read-only")

        # 18. Create Second Session for Same Ticker (BBRI)
        r = await client.post("/api/trade-sessions", json={"ticker": "BBRI", "company_name": "Bank Rakyat Indonesia"})
        assert r.status_code == 201
        session2 = r.json()
        s2_id = session2["id"]
        print(f"[PASS] 18. Second session created for BBRI: {s2_id}")

        # 19. Verify Same-Ticker History Context
        r = await client.get(f"/api/trade-sessions/{s2_id}/history")
        assert r.status_code == 200
        hist = r.json()
        assert hist.get("historical_session_count", 0) >= 1
        assert s1_id in hist.get("historical_source_session_ids", [])
        print("[PASS] 19. Same-ticker historical context properly references Session 1")

        # 20. Verify Evaluation Records
        r = await client.get("/api/evaluations")
        assert r.status_code == 200
        eval_data = r.json()
        eval_items = eval_data.get("items", [])
        assert len(eval_items) >= 4
        print(f"[PASS] 20. Evaluation records generated: {len(eval_items)} items")

        return {
            "session_1_id": s1_id,
            "session_2_id": s2_id,
            "job_ids": [job1_id, job2_id, job3_id, job4_id],
            "batch_id": batch1_id,
            "evaluation_count": len(eval_items),
            "same_ticker_count": hist.get("historical_session_count"),
        }


if __name__ == "__main__":
    res = asyncio.run(run_p9_smoke_test())
    print("\n--- P9 SMOKE TEST RESULT ---")
    print(res)
