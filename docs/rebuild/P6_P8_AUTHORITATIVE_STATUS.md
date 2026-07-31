# TradePilot AI P6–P8 Authoritative Status

## Source Lock

- Product authority: `docs/TradePilot AI PRD v2 — Authoritative Rebuild.md`
- Implementation-sequence authority: `docs/TradePilot AI Rebuild — Detailed Task Plan.md`
- Execution index: `docs/rebuild/AUTHORITATIVE_TASK_LEDGER.md`
- Commit-to-task evidence: `docs/rebuild/P6_P8_COMMIT_TASK_MAPPING.md`
- Historical-only document: `docs/TradePilot AI PRD Amendment.md`

This document reports only P6–P8, the scope covered by the existing commit-to-task audit. It does not determine completion for other official tasks.

## Done Exactly as the Authoritative Plan Requires

| Official task | Exact official title | Evidence commits |
|---|---|---|
| P6.1 | Add Decision Availability API | c379017f |
| P6.2 | Implement WAIT Decision | b5675ea4 |
| P6.3 | Implement SKIP Decision | 03d2ceb7, d05a1daf |
| P6.4 | Implement BUY Decision | 295fce0a |
| P6.5 | Build Decision UI | 4d25ae92, d73f5b62 |
| P7.1 | Create WAIT Update Input API | a879c039, 0934304f |
| P7.3 | Implement WAIT Update Prompt | 138465ed, 1c7d728b |
| P7.5 | Build WAIT Update Frontend | 1efc09f8, 14fd2349 |
| P8.1 | Create Position Update Input API | 23c34c5b |
| P8.3 | Implement Position Update Prompt | b5aee296, 0026a440 |

## Done with Historical Numbering Drift Only

| Official task | Exact official title | Evidence commits | Authoritative result |
|---|---|---|---|
| P7.4 | Persist WAIT Update Results | 85173c10, 2a4bce8c | The work maps to the official persistence task; the historical internal labels do not change official scope. |

## Not Matching the Authoritative Plan

### P7.2 — Create WAIT Update Submission

- Authoritative endpoint: `POST /api/v2/trade-sessions/{session_id}/wait-updates`
- Authoritative lifecycle: session remains `WAITING`.
- Observed evidence: commit `dfed279dd792ee464119c30aec5a9e92e858c324` adds `POST /{session_id}/wait-update-analysis` and `WaitUpdateAnalysisSubmissionService.submit` assigns `ANALYZING`.
- Status: BEHAVIOR_DEVIATION

### P8.2 — Create Position Update Submission

- Authoritative endpoint: `POST /api/v2/trade-sessions/{session_id}/position-updates`
- Authoritative lifecycle: session remains `OPEN_POSITION`; position facts remain unchanged.
- Observed evidence: commit `95fa494e3e154e1b0ed34394c83fdb77912cb5fd` adds `POST /{session_id}/position-update-analysis` and `PositionUpdateAnalysisSubmissionService.submit` assigns `ANALYZING`.
- Status: BEHAVIOR_DEVIATION

## Not Done Yet

| Official task | Exact official title | Basis |
|---|---|---|
| P8.4 | Persist Position Update Results | No matching candidate commit or changed file in the authoritative Stage 2 audit. |
| P8.5 | Build Position Update Frontend | No matching candidate commit or changed file in the authoritative Stage 2 audit. |

## Current Audit Finding

P6 is aligned. P7 has one verified behavior deviation (P7.2), and P8 has one verified behavior deviation (P8.2) plus two tasks not implemented (P8.4 and P8.5). A resume point must not be selected from this document: the deviations require the deeper audit stage before implementation decisions are made.

## Scope Compliance

- Product requirements changed: no
- Official task IDs changed: no
- Official task titles changed: no
- Official sequence changed: no
- Implementation changed: no
- Phase 12 audited: no
