# Gemini Pipeline Verification

## 1. Purpose

Gate C verifies that the rebuild Gemini processing path is internally ready for
later API integration without calling Gemini, a production queue, or a
production database.

## 2. Verification Environment

- Disposable PostgreSQL 15 container: `tradepilot-gate-c-postgres`, port 55445.
- Database: `tradepilot_gate_c`, rebuilt from a clean database using the
  rebuild migration branch through `c9d0e1f2a3b4`.
- Queue, image resolution, and Gemini adapter boundaries were mocked.
- No persistent Docker volume or external network request was used.
- The repository has an unrelated second Alembic head (`a1b2c3d4e5f6`); the
  rebuild head was selected explicitly and no migration was changed.

## 3. Components Verified

- P4.1 Gemini-only adapter boundary.
- P4.2 explicit loader for the three approved prompts.
- P4.3 rebuild-only context builder.
- P4.4a request-ID-only enqueue boundary.
- P4.4 request creation, evidence linking, and enqueue service.
- P4.5 one-request worker claim and processing flow.
- P4.6 compact response validation and terminal failure handling.

## 4. Request Creation and Queue Submission

The test creates one rebuild session and three valid initial-analysis evidence
records. The request service persists one `PENDING` request and links all three
evidence records before invoking the mocked queue. Exactly one call is made,
with the payload containing only `analysis_request_id`. A second active
submission is rejected and does not create another request.

## 5. Worker Claiming

The worker receives only the request identifier. It changes the request to
`PROCESSING`, commits that claim, and the observer sees `PROCESSING` before the
mocked adapter is entered. A duplicate delivery of the completed request is
rejected without another adapter call.

## 6. Context Construction

The real `RebuildAnalysisContextBuilder` runs for the success scenario. It
loads the rebuild session, current request, and linked rebuild evidence only.
No legacy session, `analysis_jobs`, or `EvidenceBatch` data is supplied or
required.

## 7. Prompt and Schema Selection

The real prompt loader selects `prompts/rebuild/initial_analysis.md` at `v1`.
The worker selects `schemas/rebuild/v1/initial_analysis.schema.json` explicitly.
The existing focused P4.2/P4.5 tests provide evidence for the corresponding
WAIT_UPDATE and POSITION_UPDATE mappings. No fallback prompt or schema exists.

## 8. Image Ordering

The mocked resolver receives the context evidence in the required order:
`ORDERBOOK`, `CHART_3_MONTH`, `CHART_6_MONTH`. The adapter receives exactly
three image parts in that same order.

## 9. Gemini Adapter Invocation

The adapter boundary is mocked and called exactly once for the claimed request.
The persisted Gemini model is used, and the call contains the composed prompt,
ordered image parts, and the selected schema. No Gemini SDK request is made.

## 10. Compact Response Validation

The valid mocked initial-analysis response passes the P4.6 validator. The
failure scenario omits required critical sections and is rejected as
`RESPONSE_VALIDATION_FAILED`.

## 11. Success Path

The valid response is persisted with both raw and processed responses. The
request reaches `COMPLETED` with `completed_at` set and no error fields. The
session remains `DRAFT`.

## 12. Failure Path

The invalid critical response is processed once, then persisted as `FAILED`
with `completed_at` set. The serializable raw response is preserved, the
processed response is cleared, and the bounded error message contains no
mocked secret value. No retry, replacement request, or fallback occurs.

## 13. Duplicate Protection

- Active duplicate submission is rejected by the existing service guard.
- One service invocation creates one request and one enqueue call.
- `PROCESSING`, `COMPLETED`, and `FAILED` requests are protected from reclaim
  by the worker’s existing `PENDING` check; the completed duplicate delivery
  is exercised in the Gate C test.
- No new idempotency mechanism was added.

## 14. Legacy Isolation

The verified path uses rebuild models, rebuild context construction, the
explicit rebuild prompt loader, the Gemini-only adapter boundary, and the
rebuild request status flow. It does not use legacy `analysis_jobs`, old
session persistence, `EvidenceBatch`, a provider router, provider fallback,
the old context builder, old prompt registry, old lifecycle coordinator, or
old response evaluator.

## 15. Issues and Limitations

The repository currently has two Alembic heads because an unrelated legacy
revision branches from the common migration history. Gate C used the explicit
rebuild head in the disposable database and did not alter migration history.
No product defect or permitted P4.1–P4.6 correction was required.

## 16. Gate C Conclusion

PASSED. The rebuild request service and worker complete a fully mocked,
rebuild-only Gemini pipeline for a valid request, reject critically invalid
output as a terminal failure, and prevent duplicate submission and processing.
The pipeline is ready for later API integration. No real Gemini request was
made.
