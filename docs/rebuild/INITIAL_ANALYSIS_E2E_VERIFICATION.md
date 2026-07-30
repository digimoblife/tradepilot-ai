# Initial Analysis End-to-End Verification

## 1. Purpose

Gate D verifies the rebuild Initial Analysis MVP across the V2 API contracts, the
rebuild processor, persistence, retry behavior, and the frontend workspace. No
real Gemini request or production service was used.

## 2. Verification Environment

- PostgreSQL: local PostgreSQL on `127.0.0.1:5432`.
- Database isolation: newly created disposable database
  `tradepilot_gate_d_20260730`; only the rebuild migration head
  `c9d0e1f2a3b4` was applied.
- Evidence storage: test fixture paths under isolated local test data; no
  production storage was used.
- Queue: in-memory recording queue boundary; payloads contained only
  `analysis_request_id`.
- Gemini: recording/mock adapter; no network request.
- Frontend: real Next.js route `/trade-workspace` and rebuild feature modules.
- Browser automation: not used; Playwright was not present in the existing
  focused setup, so the existing Vitest/Testing Library mechanics were used.
- External network: none.
- Production services: none.

## 3. Backend Contracts

The verification used the existing rebuild contracts only:

- session creation and list/detail;
- initial evidence upload;
- initial analysis submission;
- initial analysis read;
- manual initial analysis retry.

The processor used the approved rebuild context builder, prompt loader, schema
loader, ordered image resolver, compact response validator, and Gemini-only
adapter boundary with mocks supplied by the focused tests.

## 4. Frontend Flow

The real `/trade-workspace` route provides session list and selection, creation,
three evidence inputs, submission, selected-session polling, completed result
rendering, and manual retry. Frontend state is held per selected session; no
global analysis lock or automatic retry was introduced.

## 5. Successful Initial Analysis

- session created: passed by V2 session API coverage.
- initial session status: `DRAFT`.
- evidence files: exactly `ORDERBOOK`, `CHART_3_MONTH`, `CHART_6_MONTH`.
- evidence rows: exactly three, linked to the request.
- request created: exactly one `INITIAL_ANALYSIS` request.
- request ID: one UUID, reused by queue and retry paths.
- queue calls: exactly one on submission.
- queue payload: `{ "analysis_request_id": "<identifier>" }` only.
- session after submission: `ANALYZING`.
- worker claim: request observed as `PROCESSING` during adapter execution.
- adapter calls: exactly one for the successful attempt.
- prompt/schema: approved prompt version and Initial Analysis schema were
  supplied to the adapter.
- image ordering: `ORDERBOOK`, `CHART_3_MONTH`, `CHART_6_MONTH`.
- validation: compact response validation passed.
- final request status: `COMPLETED`.
- final session status: `ANALYZED` in the dedicated Initial Analysis processor
  success test.
- read endpoint: returns the processed response while redacting internal
  request fields.
- frontend result: completed result view is rendered.
- thirteen sections: all thirteen approved sections are rendered.
- decision controls: none; no BUY, WAIT, or SKIP action is active.

The API submission test and the processor success test are separate focused
tests: the first verifies the real authenticated V2 handoff and `ANALYZING`
transition; the second verifies the claimed request, mocked Gemini processing,
ordered images, persistence, and `ANALYZED` transition.

## 6. Processing Failure

- failure source: mocked invalid compact response.
- final request status: `FAILED`.
- completed_at: set.
- sanitized error: `RESPONSE_VALIDATION_FAILED`; raw response content was not
  copied into the sanitized error message.
- raw response: preserved when safely available.
- processed response: null.
- final session status: `DRAFT`.
- evidence preserved: yes; linked rows are not removed.
- automatic retry: none.
- frontend failure state: Indonesian failure state is rendered.
- retry action: one `Coba Lagi` action is offered.

## 7. Manual Retry

- same request ID: verified.
- new request created: no.
- same evidence: verified; all three links remain attached.
- old fields cleared: failed result/error fields are reset for the retry.
- persisted configuration preserved: provider, model, prompt version, and input
  snapshot are preserved.
- queue calls: exactly one request-ID-only enqueue per explicit retry.
- session after retry: `ANALYZING`.
- adapter calls: one for the new claimed attempt.
- final request status: `COMPLETED` after valid mocked processing.
- final session status: `ANALYZED`.
- frontend recovery: returns to processing and later renders the completed
  result.

## 8. Queue Submission Recovery

- request persisted: yes before queue publication.
- request status after failure: `PENDING`.
- session status after failure: `DRAFT`.
- replacement request: none.
- automatic retry: none.
- frontend retry offered: yes for `PENDING + DRAFT`.
- same request ID enqueued: verified by retry API coverage.
- session after retry: `ANALYZING`.
- new evidence created: no.
- new request created: no.

## 9. Multi-Session Isolation

- sessions used: independent V2 sessions in the retry concurrency/isolation
  tests and the frontend session-list test.
- Session A failure blocks Session B: no.
- Session A retry blocks Session B: no.
- polling isolation: selected session ID is used for reads and polling.
- result isolation: workspace remounts by selected session ID.
- loading-state isolation: local to the selected workspace.
- retry-state isolation: local to the selected workspace.
- global lock: none.
- per-session duplicate protection: verified by focused retry concurrency tests.

## 10. Ownership Isolation

- cross-user session read: rejected with safe not-found behavior.
- cross-user evidence upload: rejected.
- cross-user analysis submission: rejected.
- cross-user analysis read: rejected/redacted by ownership lookup.
- cross-user retry: rejected.
- private data leaked: no.

## 11. Duplicate Protection

- duplicate evidence: rejected by the initial evidence contract.
- duplicate submission: no second active request is created.
- duplicate retry: no second request is created.
- duplicate queue delivery: rejected after the request is no longer pending.
- adapter calls after duplicate delivery: at most one.
- completed request reprocessed: rejected.
- failed request reprocessed without retry: rejected.

## 12. Legacy Isolation

- legacy session APIs used: no.
- legacy analysis APIs used: no.
- old tables used: no for the rebuild flow.
- EvidenceBatch used: no.
- provider router used: no.
- fallback used: no.
- old lifecycle used: no.
- old frontend workflow used: no.

## 13. Issues and Limitations

- Browser automation was unavailable in the existing repository setup, so the
  frontend route and components were verified with focused Vitest/Testing
  Library tests, typecheck, and focused lint.
- The pre-existing Gate C fixture
  `backend/tests/trade_workspace/test_gemini_pipeline_verification.py::test_gate_c_success_path_and_duplicate_protection`
  fails when run in isolation because it submits directly through the low-level
  queue service while leaving the seeded session in `DRAFT`; the processor
  correctly refuses completion unless an Initial Analysis session is
  `ANALYZING`. The approved API submission path sets `ANALYZING`, and the
  dedicated Initial Analysis processor success test passes. No Gate C fixture
  was modified during Gate D.
- No production-like browser/server deployment was started. The verification
  used the real application route and V2 contracts through focused test
  mechanics.

## 14. Gate D Conclusion

PASSED. The approved rebuild Initial Analysis flow is verified through the V2
submission handoff, mocked worker processing, persistence, safe failure and
manual retry, queue-submission recovery, ownership/duplicate protection, and
multi-session frontend state. Phase 6 was not started.
