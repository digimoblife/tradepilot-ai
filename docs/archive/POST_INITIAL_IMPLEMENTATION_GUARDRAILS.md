# TradePilot AI — Post-Initial Implementation Guardrails

**Status:** Active implementation reference
**Language:** English
**User-facing analysis language:** Indonesian
**Primary source of truth:** `TRADEPILOT_AI_POST_INITIAL_ANALYSIS_PRD.md`

## 1. Purpose

This document provides compact, persistent implementation guardrails for the Post-Initial-Analysis development phase of TradePilot AI.

It exists to reduce repeated prompt context, control scope, preserve compatibility, and keep implementation decisions consistent across milestones.

When a milestone prompt conflicts with this document, the PRD and explicit approved product decisions take precedence.

## 2. Product Principle

One trade session represents:

- one ticker;
- one setup;
- one thesis lifecycle;
- one position lifecycle;
- one final outcome.

A closed or skipped session is immutable. A new trade on the same ticker requires a new session.

## 3. Canonical Lifecycle

```text
DRAFT
→ READY_FOR_INITIAL_ANALYSIS
→ ANALYZING
→ INITIAL_ANALYZED
   ├── user BUY  → OPEN_POSITION
   ├── user WAIT → WATCHING
   └── user SKIP → CLOSED_SKIPPED

WATCHING
   ├── ANALYZING → WATCHING
   ├── user BUY  → OPEN_POSITION
   ├── user WAIT → WATCHING
   └── user SKIP → CLOSED_SKIPPED

OPEN_POSITION
   ├── ANALYZING → OPEN_POSITION
   └── user SELL → CLOSED
```

`ANALYZING` is an internal transient operational state.

Canonical terminal states:

- `CLOSED`
- `CLOSED_SKIPPED`

Legacy lifecycle values may remain readable during staged migration, but new product behavior must use the canonical lifecycle.

## 4. User Authority

AI recommendations never become actual trade actions automatically.

Only explicit user confirmation may create or change:

- Buy;
- Wait;
- Skip;
- actual entry;
- actual exit;
- quantity or lot count;
- confirmed stop-loss;
- confirmed target;
- stop-loss adjustments;
- target adjustments;
- partial or full exits.

Actual user-confirmed execution records have higher authority than AI interpretation.

## 5. Entry and Exit Facts

Required entry facts:

- actual entry price;
- entry timestamp.

Optional entry facts:

- quantity or lot count;
- confirmed stop-loss;
- confirmed target;
- notes.

Required full-exit facts:

- actual exit price;
- exit timestamp.

Closure reason must remain auditable separately from canonical session status.

## 6. Evidence Contract

Required Initial Analysis evidence:

- Orderbook Screenshot;
- Three-Month Chart;
- Six-Month Chart.

Recommended but optional:

- Broker Summary;
- Foreign Flow.

Every new analysis request must use an Evidence Batch representing one analytical moment.

Canonical Evidence Batch statuses:

- `DRAFT`
- `READY`
- `PROCESSING`
- `FROZEN`
- `FAILED`

After accepted analysis persistence, the used batch becomes `FROZEN`.

Frozen means:

- files remain stored;
- files are not moved;
- files are not deleted;
- evidence membership cannot change;
- evidence cannot be replaced or superseded;
- the batch remains readable and auditable.

Historical evidence relationships must not be fabricated when exact membership cannot be proven.

## 7. Application-Owned Facts

The application owns:

- ticker;
- session status;
- position status;
- evidence type;
- evidence timestamp;
- evidence ordering;
- evidence-batch membership;
- monitoring slot;
- actual entry;
- actual exit;
- quantity;
- confirmed stop-loss;
- confirmed target;
- lifecycle transitions;
- user-confirmed decisions;
- job and analysis associations.

Gemini must not infer or mutate these canonical facts.

## 8. Gemini-Owned Interpretation

Gemini may provide:

- orderbook interpretation;
- chart interpretation;
- broker-flow interpretation;
- foreign-flow interpretation;
- thesis;
- recommendation;
- risk assessment;
- probability estimates;
- scenarios;
- explanation;
- monitoring guidance.

Use separate stage-specific prompts for:

- Initial Analysis;
- Watching Update;
- Open Position Update;
- Closing Analysis.

Do not use one lifecycle-wide prompt.

## 9. Context and Token Discipline

Do not resend full session history by default.

Use compact context:

```text
canonical session facts
+ current trade state
+ latest accepted compact analysis summary
+ latest relevant evidence batch
+ only necessary historical facts
```

Do not resend images that are not required for the current analysis stage.

Do not ask Gemini to recalculate application-owned facts.

Each accepted analysis should support:

1. a full normalized result for UI and audit;
2. a compact context summary for later analysis calls.

Keep narrative output bounded. Prefer small structured fields, short explanations, and limited findings, risks, and monitoring conditions.

## 10. Validation Policy

Blocking failures:

- empty provider response;
- unparseable JSON;
- unusable non-object payload;
- empty analytical content;
- overlapping partition ownership;
- deterministic merge failure;
- database persistence failure.

Non-blocking warnings when analytical output remains usable:

- missing nested field;
- enum mismatch;
- const mismatch;
- additional property;
- minor type mismatch;
- domain inconsistency;
- probability inconsistency;
- unsupported optional field.

Preserve usable provider output instead of failing the whole job for minor contract drift.

## 11. Reliability and Auditability

Every analysis must be traceable to:

- session;
- evidence batch;
- evidence rows;
- analysis job;
- provider request;
- provider response;
- validation attempt;
- accepted analysis;
- prompt version;
- schema version;
- model;
- user action;
- lifecycle state.

Requirements:

- provider calls have hard timeouts;
- retries are bounded;
- duplicate analysis requests are prevented;
- partial provider results never become accepted final analysis;
- raw provider outputs remain auditable;
- accepted analyses are immutable;
- frozen evidence batches are immutable.

## 12. Backward Compatibility

Use additive and staged migrations where practical.

During migration:

- keep legacy status strings readable;
- keep existing accepted analyses unchanged;
- keep old jobs restorable;
- keep legacy evidence readable;
- keep API status serialization as strings unless a later migration explicitly changes it;
- do not destructively rewrite uncertain historical relationships;
- do not remove legacy enum values in the same milestone that introduces replacements.

New writes should prefer canonical contracts.

## 13. Language Rules

Use English for:

- product documents;
- engineering specifications;
- prompts;
- schemas;
- migrations;
- tests;
- implementation instructions;
- code comments.

Use Indonesian for user-facing analysis and lifecycle labels shown in the dashboard.

Missing-data UI should use safe wording such as:

- `Tidak tersedia`
- `Belum ada data`
- `Tidak dapat disimpulkan`

## 14. Scope Control

Each implementation prompt must cover one milestone or one narrowly defined correction.

Do not introduce:

- unrelated refactoring;
- new dependencies unless essential;
- infrastructure changes unless explicitly required;
- future milestone features;
- broker integration;
- automated execution;
- real-time market streaming;
- portfolio optimization;
- machine-learning training;
- partial-exit lifecycle unless explicitly approved;
- frontend redesign unrelated to the current milestone.

Preserve existing working Initial Analysis behavior unless the milestone explicitly changes it.

## 15. Implementation Workflow

For each milestone:

1. Read the PRD, this document, and only relevant code.
2. Inspect current implementation patterns before editing.
3. Implement the smallest compatible change.
4. Add focused tests.
5. Run the smallest relevant test set first.
6. Verify database migrations on an isolated disposable database when applicable.
7. Exclude unrelated local changes.
8. Commit the milestone as a dedicated checkpoint.
9. Do not start the next milestone in the same task.

## 16. Stop Conditions

Stop and request a product decision when:

- the PRD does not define a necessary behavior;
- the repository contract materially contradicts the approved lifecycle;
- a safe migration requires destructive data rewriting;
- historical attribution would need to be fabricated;
- a change would require broad provider, queue, storage, or frontend redesign;
- two implementation attempts produce repeated contract mismatch, circular fixes, or new schema/output failures.

When stopping, report:

- the exact conflict;
- affected files and data;
- smallest viable options;
- recommended option.

Do not silently relax or replace an approved contract.

## 17. Standard Compact Milestone Prompt

Use this structure for future Codex tasks:

```text
Read first:
- TRADEPILOT_AI_POST_INITIAL_ANALYSIS_PRD.md
- docs/POST_INITIAL_IMPLEMENTATION_GUARDRAILS.md
- relevant existing code

Task:
- <one narrow milestone>

Required:
- <essential implementation requirements>

Out of scope:
- <short exclusions>

Tests:
- <focused test targets>

Stop if:
- <material decision or architecture blockers>

Return only:
Status: COMPLETED | BLOCKED
Changed:
Migrations:
Tests:
Acceptance:
Compatibility:
Risks:
Commit:
```

## 18. Current Implementation Checkpoint

P1 lifecycle implementation checkpoint:

```text
82b605fd8a94b215753029c55d0998a4dc06ecd5
```

Implemented at this checkpoint:

- canonical P1 lifecycle states;
- `INITIAL_ANALYZED` completion;
- explicit WAIT and SKIP actions;
- BUY from `INITIAL_ANALYZED` and `WATCHING`;
- canonical `CLOSED` full exit;
- shared lifecycle restoration;
- legacy status compatibility;
- minimal frontend status/action support.

Known deferred compatibility item:

- quantity remains mandatory in the current implementation even though the PRD treats it as optional.
