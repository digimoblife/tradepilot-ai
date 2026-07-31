# TradePilot AI P7.2–P8.2 Focused Deviation Review

## 1. Authority and Scope

- Product authority: `docs/TradePilot AI PRD v2 — Authoritative Rebuild.md`
- Sequence authority: `docs/TradePilot AI Rebuild — Detailed Task Plan.md`
- Execution index: `docs/rebuild/AUTHORITATIVE_TASK_LEDGER.md`
- Prior audit: `docs/rebuild/P6_P8_COMMIT_TASK_MAPPING.md`
- Scope: P7.2 — Create WAIT Update Submission; P8.2 — Create Position Update Submission.
- No code, test, schema, prompt, migration, or runtime file is changed by this review.

## 2. Authoritative Contracts

### P7.2 — Create WAIT Update Submission

- Required route: `POST /api/v2/trade-sessions/{session_id}/wait-updates`.
- Required behavior: persist input and image, create `WAIT_UPDATE`, queue one Gemini request, remain `WAITING`, and prevent duplicate active request.

### P8.2 — Create Position Update Submission

- Required route: `POST /api/v2/trade-sessions/{session_id}/position-updates`.
- Required behavior: persist input and image, create `POSITION_UPDATE`, queue exactly one Gemini request, remain `OPEN_POSITION`, and preserve position facts.

## 3. Affected Backend Routes and Services

| Official task | Current route | Affected service | Verified deviation |
|---|---|---|---|
| P7.2 | `POST /{session_id}/wait-update-analysis` in `backend/app/trade_workspace/api/routes/trade_sessions.py` | `WaitUpdateAnalysisSubmissionService.submit` in `backend/app/trade_workspace/services/wait_update_analysis_submission.py` | Uses a non-authoritative endpoint and assigns `ANALYZING` after queueing. |
| P8.2 | `POST /{session_id}/position-update-analysis` in `backend/app/trade_workspace/api/routes/trade_sessions.py` | `PositionUpdateAnalysisSubmissionService.submit` in `backend/app/trade_workspace/services/position_update_analysis_submission.py` | Uses a non-authoritative endpoint and assigns `ANALYZING` after queueing. |

## 4. Frontend and API Callers

### P7.2

- `frontend/src/features/trade-workspace/api.ts` calls `/wait-update-analysis`, reads the same endpoint, and calls `/wait-update-analysis/retry`.
- `frontend/src/features/trade-workspace/wait-update.tsx` accepts `WAITING` and `ANALYZING` during its read/polling state.
- `frontend/src/features/trade-workspace/wait-update.test.tsx` includes `ANALYZING` response fixtures.
- `backend/tests/trade_workspace/test_wait_update_flow_gate_f.py` and `backend/tests/api/test_wait_update_analysis_recovery_v2.py` call the old endpoint and related retry/read endpoints.

### P8.2

- The route is implemented, but the candidate audit found no Position Update frontend task implementation (P8.5 remains not implemented).
- No current `frontend/src/features/trade-workspace/api.ts` Position Update submission caller was identified in this focused review.
- The future P8.5 implementation must use the official `/position-updates` endpoint, not `/position-update-analysis`.

## 5. Tests Expecting the Non-Authoritative ANALYZING Status

| Task | Tests / evidence |
|---|---|
| P7.2 | `backend/tests/api/test_wait_update_analysis_submission_v2.py` posts to `/wait-update-analysis` and expects `session_status: ANALYZING` plus persisted `ANALYZING`; `test_wait_update_analysis_recovery_v2.py` and Gate-F flow tests use the same route family. |
| P8.2 | `backend/tests/api/test_position_update_analysis_submission_v2.py` posts to `/position-update-analysis` and expects `session_status: ANALYZING` plus persisted `ANALYZING`. |

## 6. Worker and Polling Impact

### P7.2

- `backend/app/trade_workspace/workers/analysis_processor.py` requires the WAIT_UPDATE session to be `ANALYZING` before processing, then restores `WAITING` on completion/failure.
- This worker assumption is coupled to the non-authoritative submission transition.
- The WAIT Update frontend reads/polls while the session can be `ANALYZING`; its display logic and API client are coupled to the old route family.

### P8.2

- `PositionUpdateAnalysisSubmissionService` currently returns `ANALYZING`; corresponding API tests assert it.
- The focused review found no completed P8.4 worker-result persistence or P8.5 frontend/polling implementation. Consequently, the P8 worker and polling changes required for the corrected steady `OPEN_POSITION` lifecycle must be specified together with the later official tasks, without pre-implementing P8.4 or P8.5 in the P8.2 correction.

## 7. Minimum Alignment Changes

### P7.2 correction boundary

1. Replace the submission route with the official `/wait-updates` route.
2. Retain the required input/image persistence, `WAIT_UPDATE` request creation, one-queue behavior, and duplicate-active-request protection.
3. Do not change the session from `WAITING` during submission.
4. Update direct route/service tests that assert the old route or `ANALYZING` submission status.
5. Align the worker’s WAIT_UPDATE eligibility/completion/failure lifecycle handling with a session that remains `WAITING`.
6. Update frontend API calls and polling/display assumptions that depend on `/wait-update-analysis` or session `ANALYZING`.

### P8.2 correction boundary

1. Replace the submission route with the official `/position-updates` route.
2. Retain required input/image persistence, `POSITION_UPDATE` creation, exactly-one queue behavior, duplicate-active-request protection, and unchanged position facts.
3. Do not change the session from `OPEN_POSITION` during submission.
4. Update direct route/service tests that assert the old route or `ANALYZING` submission status.
5. Do not implement P8.4 persistence or P8.5 frontend as part of P8.2.

## 8. Correction Independence

P7.2 and P8.2 can be corrected separately. They have different official endpoints, submission services, API tests, and lifecycle states. P7.2 additionally has existing worker and frontend polling coupling that must be addressed inside its correction/verification task. P8.2 can be corrected at its submission boundary without implementing P8.4 or P8.5.

## 9. Sequencing Finding

The source-locked sequence remains:

`Review P7.2 and P8.2 → Correct P7.2 → Verify P7.2 → Correct P8.2 → Verify P8.2 → Continue with P8.4 → Continue with P8.5`

After both corrections are verified, the official resume point is `P8.4 — Persist Position Update Results`, not P8.5.

## 10. Scope Compliance

- Product requirements changed: no
- Official task IDs changed: no
- Official task titles changed: no
- Official sequence changed: no
- Application code changed: no
- Tests changed: no
- Phase 12 audited: no
