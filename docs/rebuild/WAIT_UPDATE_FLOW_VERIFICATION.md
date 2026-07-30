# WAIT Update Flow Verification

## 1. Purpose

Gate F verifies the rebuild-owned WAIT Update flow from authenticated input persistence through queue submission, worker processing, result recovery, repeated cycles, and frontend rendering. The verification does not implement Position Update, CLOSE, or Phase 8 behavior.

## 2. Verification Environment

- Branch: `main`.
- Starting commit and P7.7 checkpoint: `1efc09f8eaf53bf9405e81f0813a6b7e22a65911`.
- PostgreSQL: disposable local database `tradepilot_gate_f_20260730`.
- Migration revision: `d0e1f2a3b4c5`.
- Evidence storage: pytest temporary directory via `LocalFileStorage`.
- Queue: rebuild `AnalysisRequestQueue` with an in-memory recording transport, including a failing transport for recovery.
- Gemini: mocked adapter; no network client or credential was constructed.
- Backend: real V2 FastAPI routes and real `RebuildAnalysisProcessor`.
- Frontend: focused Vitest/Testing Library checks for the real WAIT Update component boundary.
- External network and production services: not used.

## 3. Input Persistence

The real authenticated `/api/v2/trade-sessions/{id}/wait-update-input` route persisted one ORDERBOOK evidence row with current price, MIDDAY observation period, timezone-aware observation timestamp, and one temporary PNG file. The session remained `WAITING`; no analysis request or later lifecycle record was created. A second cycle created a second evidence row and preserved the first. Storage failure cleanup remains covered by the existing focused P7.1 tests.

## 4. Analysis Submission

The real `/wait-update-analysis` route created one `WAIT_UPDATE` request, linked exactly the latest unlinked evidence, and transitioned the session to `ANALYZING`. The rebuild queue boundary published exactly `{"analysis_request_id":"<id>"}`. A duplicate active submission returned `409` and did not create another request.

## 5. Context and Prompt

The real `RebuildAnalysisContextBuilder` resolved the current session, current evidence, initial analysis, and prior completed WAIT Update. In the repeated-cycle assertion, Request B contained the completed Request A in bounded history and only B's evidence as the current image. The real `RebuildPromptLoader` resolved the approved WAIT Update prompt at `v1`, and the worker resolved the approved WAIT Update JSON schema. No external data, cross-session data, legacy prompt registry, or legacy context builder was used.

## 6. Worker Processing

The real rebuild worker claimed each pending request as `PROCESSING`, resolved one current image, called only the injected mock Gemini adapter, validated the compact response, and finalized the request transactionally. Duplicate submission was rejected before queueing; completed-request reprocessing protection remains covered by the focused P7.5 worker tests.

## 7. Successful Completion

Both WAIT Update cycles completed with `COMPLETED` requests, persisted processed responses, non-null completion timestamps, and session status `WAITING`. `closed_at` remained null. The read route returned the processed result, and available actions remained `BUY`, `WAIT`, and `SKIP`. No position or closure record was created.

## 8. Processing Failure

An injected invalid compact response caused validation failure. The worker persisted `FAILED`, a sanitized error, no processed response, and returned the session to `WAITING`. The linked evidence remained intact. No automatic retry occurred. The focused frontend checks rendered the safe failed state without exposing raw response or input snapshot fields.

## 9. Manual Retry

The real `/wait-update-analysis/retry` route reused the same failed request ID and the same linked evidence, cleared transient result/error fields, queued once, and moved the session to `ANALYZING`. A subsequent mocked successful worker run completed that same request. No new evidence or request was created.

## 10. Queue Submission Recovery

With the isolated transport failing, submission returned `503` while the persisted request stayed `PENDING`, the evidence remained linked, and the session stayed `WAITING`. Retry reused that same request and evidence after the transport was restored; it did not create replacement input. The frontend retry path sends no request body and does not request re-upload.

## 11. Repeated WAIT Update Cycle

Two complete cycles were verified. Input A, Request A, and its result remained preserved while Input B linked to Request B. Context B included the initial analysis and prior completed WAIT Update while using only B's current image. The final session status was `WAITING`.

## 12. Frontend Flow

The focused frontend tests verified the WAITING form has exactly orderbook, current price, observation period, and observation timestamp; no chart inputs; upload does not submit automatically; explicit submission is bodyless; polling and result reads are session-scoped; completed output shows the approved sections only; failures expose a safe retry state; retry does not upload again; and raw response/input snapshot fields are not rendered. Existing P7.7 tests also cover duplicate submission clicks and terminal polling behavior.

## 13. Decision Compatibility

The completed WAIT Update left the session eligible for the existing `BUY`, `WAIT`, and `SKIP` decision actions. WAIT Update remained advisory and did not automatically create a decision, position, or closure. Position Update and CLOSE were not invoked.

## 14. Ownership Isolation

Authenticated access by another user to the first user's WAIT Update submission, read, and retry routes returned `404`. No private evidence, request, or result data was returned.

## 15. Multi-Session Isolation

Two independently seeded sessions were used. Evidence, requests, result reads, queue payloads, and retry operations were session-scoped. The frontend component receives the selected session ID and remount key from the workspace, preventing stale selected-session results from being reused.

## 16. Duplicate Protection

Duplicate active submission was rejected; separate uploads were retained as separate cycle inputs; retry reused the same request/evidence; and no automatic retry or fallback was observed. Existing focused P7.5/P7.6 tests cover worker claim protection, duplicate queue delivery, and concurrent retry protections.

## 17. Legacy Isolation

The Gate F flow used only rebuild V2 routes, rebuild services, rebuild models, rebuild evidence storage, the rebuild queue boundary, the rebuild context builder, the rebuild prompt loader, and the rebuild worker. It did not use `EvidenceBatch`, legacy analysis jobs, legacy lifecycle services, old frontend screens, provider routing, fallback, or production storage.

## 18. Issues and Limitations

No direct Phase 7 correction was required. Verification used mocked queue transport and Gemini adapter by design. It did not call real Gemini, deploy the application, run the full backend/frontend suites, or verify Phase 8 behavior.

## 19. Gate F Conclusion

Gate F passed. The rebuild WAIT Update flow is verified for authenticated persistence, queue submission, context/prompt assembly, successful and failed worker processing, manual retry, queue recovery, repeated cycles, frontend behavior, decision compatibility, ownership isolation, multi-session isolation, duplicate protection, and legacy isolation.
