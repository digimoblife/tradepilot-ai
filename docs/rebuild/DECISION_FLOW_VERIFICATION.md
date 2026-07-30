# Decision Flow Verification

## 1. Purpose

Gate E verifies the user-controlled rebuild decision flow for WAIT, SKIP, and
BUY across the V2 backend routes and the rebuild frontend workspace.

## 2. Verification Environment

- PostgreSQL: disposable local PostgreSQL database `tradepilot_gate_e_20260730`.
- Database isolation: migrated only through rebuild revision `c9d0e1f2a3b4`.
- Backend: real FastAPI V2 routes with real SQLAlchemy persistence.
- Frontend: real `SessionWorkspace` decision component under jsdom, with only
  its HTTP boundary mocked in focused tests.
- Queue: no queue configured or invoked.
- Gemini: no adapter or provider invocation.
- External network: none; frontend tests use mocked API functions.
- Production services: none.

## 3. Decision Availability

The availability endpoint returned the exact backend mapping for owned sessions:

| Session status | Available actions |
| --- | --- |
| ANALYZED | BUY, WAIT, SKIP |
| WAITING | BUY, WAIT, SKIP |
| OPEN_POSITION | CLOSE |
| DRAFT | none |
| ANALYZING | none |
| CLOSED | none |
| CLOSED_SKIPPED | none |

The endpoint was read-only: no decisions, positions, or status changes were
created. Availability remained scoped to each session.

## 4. WAIT Decision

An owned ANALYZED session accepted a bodyless WAIT request, created exactly one
WAIT decision, transitioned to WAITING, and kept `closed_at` null. No position,
closure, analysis request, queue call, or Gemini call occurred. Availability
remained BUY, WAIT, SKIP.

## 5. Repeated WAIT

A second confirmed WAIT request created a second auditable WAIT decision while
preserving the first decision and keeping the session WAITING. Separate WAIT
actions were not incorrectly deduplicated.

## 6. SKIP Decision

An owned WAITING session rejected missing and unsupported reasons with 422. A
valid `RISK_TOO_HIGH` request preserved the exact reason and note, created one
SKIP decision, set `CLOSED_SKIPPED`, and assigned `closed_at`. No position,
closure, analysis request, queue call, or Gemini call occurred. Availability
became empty and a repeated SKIP was rejected.

## 7. BUY Decision

An owned ANALYZED session accepted the confirmed entry price, entry timestamp,
quantity, stop loss, target price, and note exactly as submitted. It created one
BUY decision and exactly one OPEN position for the exact session, transitioned
to OPEN_POSITION, and kept `closed_at` null. Availability became CLOSE. No
closure or analysis request was created. A repeated BUY was rejected, and an
eligible session with an existing position was also rejected.

## 8. Frontend Decision Flow

The focused rebuild frontend test verified that actions come from the backend
availability response, CLOSE is not activated, and BUY/WAIT/SKIP controls are
shown only when returned. WAIT submits once with no body and refreshes actions.
SKIP requires one of the seven approved reasons, accepts an optional note, and
removes actions after CLOSED_SKIPPED. BUY submits exact user-entered facts,
shows the returned OPEN position, and removes the BUY form after success.
Loading states are local to the selected workspace, duplicate submissions are
disabled, and safe API errors are displayed without automatic retry.

## 9. Ownership Isolation

A different authenticated user received safe `SESSION_NOT_FOUND` responses for
availability, WAIT, SKIP, and BUY. No private decision or position data was
exposed and no cross-user record was created.

## 10. Multi-Session Isolation

The backend tests used separate session IDs and session-scoped locks. Actions,
decisions, positions, status transitions, and availability were scoped to the
requested session. The frontend component is keyed by selected session and
keeps form, result, and loading state local; Session A cannot affect Session B.

## 11. Concurrency Protection

Concurrent duplicate SKIP calls produced one success, one conflict, one SKIP
decision, and one terminal transition. Concurrent duplicate BUY calls produced
one success, one conflict, one BUY decision, and one position. Protection uses
the existing per-session advisory transaction lock and row lock; no global
business lock was added.

## 12. Related Data Preservation

WAIT preserved three evidence uploads, the completed Initial Analysis response,
and prior decisions. SKIP and BUY created no unrelated records. No unrelated
session was modified, and no legacy record was created.

## 13. Legacy Isolation

The Gate E flow used only the rebuild V2 routes, models, services, and frontend
feature boundary. It did not use legacy decision APIs, lifecycle services, old
session or position tables, old position services, EvidenceBatch, provider
routing, Gemini recommendation persistence, or the old frontend workflow.

## 14. Issues and Limitations

No product defect or corrective code change was required. The repository has
multiple Alembic heads, so verification explicitly targeted the rebuild head
`c9d0e1f2a3b4` instead of the ambiguous generic `head`. The disposable database
was removed after verification.

## 15. Gate E Conclusion

Gate E PASSED. WAIT, repeated WAIT, SKIP, BUY, ownership, concurrency,
multi-session isolation, related-data preservation, and rebuild frontend
behavior were verified without production services, queue activity, or Gemini.
