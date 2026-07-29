# Session Status Rules

## 1. Purpose

Define the approved TradePilot AI session business statuses and transitions. This document is normative for the rebuild scope only; it does not implement enums, transition services, constraints, API behavior, frontend logic, or migrations.

## 2. Scope and Authorities

The PRD and the TradePilot AI Rebuild Detailed Task Plan are the authorities. Supporting evidence is `docs/rebuild/SCOPE_GUARDRAILS.md` and `docs/rebuild/SIMPLE_ARCHITECTURE.md`. Existing code and old lifecycle behavior are reference material only. The rules cover only the approved one-session/one-position flow.

## 3. Status Principles

- Only seven business statuses exist: `DRAFT`, `ANALYZING`, `ANALYZED`, `WAITING`, `OPEN_POSITION`, `CLOSED`, and `CLOSED_SKIPPED`.
- Only the ten transitions in Section 5 exist.
- BUY, WAIT, SKIP, and CLOSE are user-controlled decisions.
- Gemini may participate in an analysis request but never chooses or persists a session decision.
- `ANALYSIS_FAILED` is not a business status. Failure belongs to the analysis request while the session preserves or recovers its previous valid status.
- A session has no position before BUY and exactly one position after BUY; Partial Exit is not supported.

## 4. Approved Statuses

### 4.1 DRAFT

Status: `DRAFT`
Meaning: A session exists and is being prepared for Initial Analysis.
Entry Conditions: Session creation succeeds and required initial evidence may still be incomplete.
Allowed User Actions: Upload required evidence and submit a valid Initial Analysis request.
Allowed Analysis Submission: `INITIAL_ANALYSIS` only when required evidence and request conditions are valid.
Position Requirement: No position exists.
Terminal: No.
Allowed Next Statuses: `ANALYZING` only.
Prohibited Behavior: No BUY, WAIT, SKIP, CLOSE, position creation, WAIT Update, Position Update, or direct transition to any other status.

### 4.2 ANALYZING

Status: `ANALYZING`
Meaning: An Initial Analysis request is being processed.
Entry Conditions: A user submitted a valid Initial Analysis request from `DRAFT`.
Allowed User Actions: No session decision while the request is processing.
Allowed Analysis Submission: The submitted `INITIAL_ANALYSIS` request only; no additional analysis request or decision.
Position Requirement: No position exists.
Terminal: No.
Allowed Next Statuses: `ANALYZED` only after successful Initial Analysis completion.
Prohibited Behavior: No transition to WAITING, OPEN_POSITION, CLOSED, or CLOSED_SKIPPED; no permanent analysis-failure status; no automatic decision.

### 4.3 ANALYZED

Status: `ANALYZED`
Meaning: Initial Analysis completed successfully and the user must decide what to do next.
Entry Conditions: Initial Analysis request completed successfully.
Allowed User Actions: Explicit BUY, WAIT, or SKIP.
Allowed Analysis Submission: No new analysis submission before a user decision.
Position Requirement: No position exists.
Terminal: No.
Allowed Next Statuses: `WAITING`, `OPEN_POSITION`, or `CLOSED_SKIPPED`.
Prohibited Behavior: No automatic decision, direct CLOSED transition, position creation without BUY, or Closing Analysis requirement.

### 4.4 WAITING

Status: `WAITING`
Meaning: The user has chosen to wait without opening a position.
Entry Conditions: Explicit user WAIT from `ANALYZED`, or an approved WAIT Update remains unresolved.
Allowed User Actions: Explicit BUY, WAIT, or SKIP.
Allowed Analysis Submission: `WAIT_UPDATE` only; submission/completion does not create a new business status.
Position Requirement: No position exists.
Terminal: No.
Allowed Next Statuses: `WAITING`, `OPEN_POSITION`, or `CLOSED_SKIPPED`.
Prohibited Behavior: A WAIT Update must not create a position; no automatic BUY/WAIT/SKIP; no CLOSE or Partial Exit.

### 4.5 OPEN_POSITION

Status: `OPEN_POSITION`
Meaning: The user has confirmed the one position and it remains open.
Entry Conditions: Explicit user BUY with confirmed position facts from `ANALYZED` or `WAITING`.
Allowed User Actions: Explicit CLOSE and user-provided evidence/current price for Position Updates.
Allowed Analysis Submission: `POSITION_UPDATE` only; submission/completion does not create a new business status.
Position Requirement: Exactly one confirmed open position exists.
Terminal: No.
Allowed Next Statuses: `OPEN_POSITION` or `CLOSED`.
Prohibited Behavior: Position Update cannot modify confirmed facts; no second position, BUY/WAIT/SKIP, Partial Exit, automated CLOSE, or Closing Analysis requirement.

### 4.6 CLOSED

Status: `CLOSED`
Meaning: The one previously opened position has been manually closed by the user.
Entry Conditions: Explicit user CLOSE after closure facts are persisted and an open position exists.
Allowed User Actions: No BUY, WAIT, SKIP, or CLOSE. History remains readable.
Allowed Analysis Submission: None.
Position Requirement: A position previously existed and is now closed.
Terminal: Yes.
Allowed Next Statuses: None.
Prohibited Behavior: No reopening, new analysis, second position, Partial Exit, Closing Analysis requirement, or transition to any status.

### 4.7 CLOSED_SKIPPED

Status: `CLOSED_SKIPPED`
Meaning: The user skipped the setup without opening a position.
Entry Conditions: Explicit user SKIP from `ANALYZED` or `WAITING`.
Allowed User Actions: No BUY, WAIT, SKIP, or CLOSE. History remains readable.
Allowed Analysis Submission: None.
Position Requirement: No position exists; no close price or realized result exists.
Terminal: Yes.
Allowed Next Statuses: None.
Prohibited Behavior: No reopening, position creation, new analysis, close facts, Partial Exit, Closing Analysis requirement, or transition to any status.

## 5. Approved Transition Matrix

| Current Status | Trigger | Next Status | Position Required | Gemini Request Triggered by Transition | Authority |
|---|---|---|---|---|---|
| `DRAFT` | Valid Initial Analysis submission | `ANALYZING` | None | YES — analysis request only | USER submission |
| `ANALYZING` | Successful Initial Analysis completion | `ANALYZED` | None | YES — completes the analysis request only | ANALYSIS REQUEST |
| `ANALYZED` | Explicit BUY with confirmed facts | `OPEN_POSITION` | New one position | NO | USER |
| `ANALYZED` | Explicit WAIT | `WAITING` | None | NO | USER |
| `ANALYZED` | Explicit SKIP | `CLOSED_SKIPPED` | None | NO | USER |
| `WAITING` | WAIT decision or WAIT Update remains waiting | `WAITING` | None | NO — update request is tracked separately | USER / ANALYSIS REQUEST |
| `WAITING` | Explicit BUY with confirmed facts | `OPEN_POSITION` | New one position | NO | USER |
| `WAITING` | Explicit SKIP | `CLOSED_SKIPPED` | None | NO | USER |
| `OPEN_POSITION` | Position Update remains open | `OPEN_POSITION` | Existing one position | NO — update request is tracked separately | ANALYSIS REQUEST |
| `OPEN_POSITION` | Explicit CLOSE after facts persist | `CLOSED` | Existing position | NO | USER |

For WAIT Update and Position Update, submission and completion do not create a new business status; the separate analysis request records request state. Gemini participates only in the analysis request, never in the decision authority.

## 6. Transition Rules

- `DRAFT → ANALYZING` occurs when the user submits a valid Initial Analysis request.
- `ANALYZING → ANALYZED` occurs only after successful Initial Analysis completion.
- `ANALYZED → WAITING` occurs only on explicit user WAIT.
- `ANALYZED → OPEN_POSITION` occurs only on explicit user BUY with confirmed facts.
- `ANALYZED → CLOSED_SKIPPED` occurs only on explicit user SKIP.
- `WAITING → WAITING` occurs on explicit repeated WAIT or a WAIT Update that leaves the session waiting. A WAIT Update never creates a position.
- `WAITING → OPEN_POSITION` occurs only on explicit user BUY with confirmed facts.
- `WAITING → CLOSED_SKIPPED` occurs only on explicit user SKIP.
- `OPEN_POSITION → OPEN_POSITION` occurs when a Position Update leaves the confirmed position open. It cannot modify confirmed position facts.
- `OPEN_POSITION → CLOSED` occurs only on explicit user CLOSE after closure facts are persisted.

No recovery transition outside this list is approved.

## 7. User Decision Authority

- Only the user may persist BUY.
- Only the user may persist WAIT.
- Only the user may persist SKIP.
- Only the user may persist CLOSE.
- Gemini recommendations are non-authoritative.
- No analysis response may directly change the session to `WAITING`, `OPEN_POSITION`, `CLOSED`, or `CLOSED_SKIPPED`.

## 8. Analysis Request Failure Handling

- Failure is stored on the analysis request.
- The session does not become a new or unapproved business status.
- Initial Analysis failure preserves a retryable business condition around the prior valid state.
- WAIT Update failure preserves `WAITING`.
- Position Update failure preserves `OPEN_POSITION`.
- User-owned facts and evidence remain preserved.
- No automatic fallback provider is attempted.
- No duplicate analysis is created automatically.

Retry implementation details are not defined here.

## 9. Terminal-State Rules

`CLOSED` requires a previously opened position. It permits no further analysis submission or BUY, WAIT, SKIP, or CLOSE action. Complete history remains readable.

`CLOSED_SKIPPED` requires that no position exists. It has no close price or realized result. It permits no further analysis submission or BUY, WAIT, SKIP, or CLOSE action. Complete history remains readable.

## 10. Prohibited Transitions and Behaviors

The following transitions are prohibited:

```text
DRAFT → WAITING
DRAFT → OPEN_POSITION
DRAFT → CLOSED
DRAFT → CLOSED_SKIPPED
ANALYZING → WAITING
ANALYZING → OPEN_POSITION
ANALYZING → CLOSED
ANALYZING → CLOSED_SKIPPED
ANALYZED → CLOSED
WAITING → CLOSED
OPEN_POSITION → WAITING
OPEN_POSITION → CLOSED_SKIPPED
CLOSED → any status
CLOSED_SKIPPED → any status
```

The following behaviors are also prohibited: automatic BUY, WAIT, SKIP, or CLOSE; position creation before BUY; SKIP after BUY; CLOSE without an open position; Partial Exit; Closing Analysis as a required transition; any additional lifecycle status; and the old lifecycle transition engine controlling rebuild behavior.

## 11. Unresolved Status Questions

- Exact persistence representation for analysis-request failure while preserving the previous valid session status.
- Exact compatibility handling for historical old statuses during cutover.
- Exact eligibility checks for repeated WAIT/Position Updates, deferred to later implementation tasks.

## 12. P2.2 Conclusion

The rebuild has exactly seven approved business statuses and ten approved transitions. User decisions remain authoritative, analysis-request failures remain separate from session business state, terminal history remains readable, and no old lifecycle authority or unapproved recovery behavior is introduced.
