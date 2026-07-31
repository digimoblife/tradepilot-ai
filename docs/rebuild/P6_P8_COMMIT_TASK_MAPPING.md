# TradePilot AI P6–P8 Commit-to-Task Mapping

## 1. Authority and Audit Scope

- Product authority: `docs/TradePilot AI PRD v2 — Authoritative Rebuild.md`
- Sequence authority: `docs/TradePilot AI Rebuild — Detailed Task Plan.md`
- Task index: `docs/rebuild/AUTHORITATIVE_TASK_LEDGER.md`
- Historical-only source: `docs/TradePilot AI PRD Amendment.md`
- Audited phases: P6, P7, P8. Phase 12, including P12.5, is out of scope.
- Application changes are prohibited.

## 2. Audit Method

Commit metadata, changed-file lists, and diff statistics were reviewed first. Focused diffs were then reviewed for endpoint, status, input, analysis type, queue behavior, and persistence. No full repository audit or application test was performed; commit titles alone were not treated as evidence.

## 3. Candidate Commit Inventory

All 20 supplied candidate hashes exist. P6 candidates map to decision availability, WAIT, SKIP, BUY, UI, and a Gate-E verification commit. P7 candidates map to evidence metadata/input, submission, prompt/context, worker/result, UI, and Gate-F verification. P8 candidates map to input, submission, prompt, and context. No candidate changes a Position Update result-persistence or Position Update frontend implementation.

## 4. Official Task Mapping

### P6.1 — Add Decision Availability API
- Candidate commits: `c379017f0a87201f3ad36a1017ba4cdca769d720`
- Relevant files: `decision_availability.py`; `trade_sessions.py`
- Classification: MATCH
- Classification reason: `ANALYZED` and `WAITING` return BUY/WAIT/SKIP; `OPEN_POSITION` returns CLOSE; closed sessions return none.
- Evidence confidence: HIGH

### P6.2 — Implement WAIT Decision
- Candidate commits: `b5675ea48e01744b8a4e0b7503ed1816cc476054`
- Relevant files: `wait_decision.py`; decision route and schema
- Classification: MATCH
- Classification reason: WAIT is user-controlled, permitted for ANALYZED/WAITING, persists a WAIT decision, and sets WAITING without a position or Gemini request.
- Evidence confidence: HIGH

### P6.3 — Implement SKIP Decision
- Candidate commits: `03d2ceb7ff90d40597e2de6db1c644b0b80140c2`, `d05a1daf117ae4b8b2a1f949aba5547475e3f1b8`
- Relevant files: `skip_decision.py`; decision route and schema
- Classification: MATCH
- Classification reason: required reason and optional note are persisted; the session becomes CLOSED_SKIPPED and receives a closed timestamp without a position or Gemini request.
- Evidence confidence: HIGH

### P6.4 — Implement BUY Decision
- Candidate commits: `295fce0ac84cde4d2d8faa3f8ccdd77452a31a90`
- Relevant files: `buy_decision.py`; decision route and schema
- Classification: MATCH
- Classification reason: user input creates one BUY decision and one OPEN position, then sets OPEN_POSITION without Gemini.
- Evidence confidence: HIGH

### P6.5 — Build Decision UI
- Candidate commits: `4d25ae9243c62dcd5db9f7b80f888a8a603e57e6`, `d73f5b62df08e5366579724c87a1511a93c941e6`
- Relevant files: `workspace.tsx`; `api.ts`; `decision-ui.test.tsx`
- Classification: MATCH
- Classification reason: candidate UI and focused Gate-E evidence cover decision actions and status behavior.
- Evidence confidence: MEDIUM

### P7.1 — Create WAIT Update Input API
- Candidate commits: `a879c039aff0bac7fd4a8c7d463270dd4906d434`, `0934304fbec49ddac303bb8dbf0319338dd69896`
- Relevant files: evidence model; `wait_update_input.py`
- Classification: MATCH
- Classification reason: candidate changes add required observation metadata and a WAITING/no-position input boundary.
- Evidence confidence: HIGH

### P7.2 — Create WAIT Update Submission
- Candidate commits: `dfed279dd792ee464119c30aec5a9e92e858c324`
- Relevant files: `wait_update_analysis_submission.py`; route and schema
- Classification: BEHAVIOR_DEVIATION
- Classification reason: the official endpoint is `/wait-updates` and the session must remain WAITING; the candidate exposes `/wait-update-analysis` and assigns ANALYZING after queueing.
- Evidence confidence: HIGH

### P7.3 — Implement WAIT Update Prompt
- Candidate commits: `138465edab362bc2a292122ad01f3abd55975c23`, `1c7d728b1e4efda1382ed7242a382b06b20c9a98`
- Relevant files: `prompts/rebuild/wait_update.md`; `context_builder.py`
- Classification: MATCH
- Classification reason: prompt and context commits jointly implement the official context/output work; the split is internal only.
- Evidence confidence: MEDIUM

### P7.4 — Persist WAIT Update Results
- Candidate commits: `85173c1072842f7c438d1d53ca28ba3caf55eda6`, `2a4bce8c983678996816406696163729d49273b4`
- Relevant files: `analysis_processor.py`; wait-update read/retry services
- Classification: NUMBERING_ONLY
- Classification reason: processing and persisted-result work is distributed under historical labels, but maps to the official persistence task.
- Evidence confidence: MEDIUM

### P7.5 — Build WAIT Update Frontend
- Candidate commits: `1efc09f8eaf53bf9405e81f0813a6b7e22a65911`, `14fd234904411b9e1c2bd4bb9db35c792d83b01e`
- Relevant files: `wait-update.tsx`; `workspace.tsx`
- Classification: MATCH
- Classification reason: frontend and Gate-F evidence map to the required WAIT update UI.
- Evidence confidence: MEDIUM

### P8.1 — Create Position Update Input API
- Candidate commits: `23c34c5bdfdf2933cab387b907add79a42641a63`
- Relevant files: `position_update_input.py`; route and schema
- Classification: MATCH
- Classification reason: requires OPEN_POSITION, exactly one OPEN position, current price, orderbook evidence, period, and timestamp.
- Evidence confidence: HIGH

### P8.2 — Create Position Update Submission
- Candidate commits: `95fa494e3e154e1b0ed34394c83fdb77912cb5fd`
- Relevant files: `position_update_analysis_submission.py`
- Classification: BEHAVIOR_DEVIATION
- Classification reason: the plan requires session remains OPEN_POSITION; the submission service assigns `TradeSessionV2Status.ANALYZING` after queueing.
- Evidence confidence: HIGH

### P8.3 — Implement Position Update Prompt
- Candidate commits: `b5aee29604bcc1a0966537569c11e8cfdeef4410`, `0026a440b94c015e5af15bb441ff29ae81350c2f`
- Relevant files: `prompts/rebuild/position_update.md`; `context_builder.py`
- Classification: MATCH
- Classification reason: prompt and context split is internal; candidate work covers the official prompt/context contract.
- Evidence confidence: MEDIUM

### P8.4 — Persist Position Update Results
- Candidate commits: none
- Relevant files: none in candidate inventory
- Classification: NOT_IMPLEMENTED
- Classification reason: no candidate commit changes Position Update result persistence.
- Evidence confidence: HIGH

### P8.5 — Build Position Update Frontend
- Candidate commits: none
- Relevant files: none in candidate inventory
- Classification: NOT_IMPLEMENTED
- Classification reason: no candidate commit changes a Position Update frontend.
- Evidence confidence: HIGH

## 5. Deviations and Unknowns

### P7.2
- Classification: BEHAVIOR_DEVIATION
- Authoritative requirement: `POST /api/v2/trade-sessions/{session_id}/wait-updates`; session remains `WAITING`.
- Observed implementation: `POST /{session_id}/wait-update-analysis`; `WaitUpdateAnalysisSubmissionService.submit` assigns `TradeSessionV2Status.ANALYZING`.
- Commit: `dfed279dd792ee464119c30aec5a9e92e858c324`
- File and symbol: `WaitUpdateAnalysisSubmissionService.submit`
- Behavioral impact: changes both the official endpoint and the required WAITING lifecycle behavior.
- Deep review required: yes

### P8.2
- Classification: BEHAVIOR_DEVIATION
- Authoritative requirement: session remains `OPEN_POSITION`.
- Observed implementation: `POST /{session_id}/position-update-analysis` and assigns `TradeSessionV2Status.ANALYZING` after queueing.
- Commit: `95fa494e3e154e1b0ed34394c83fdb77912cb5fd`
- File and symbol: `PositionUpdateAnalysisSubmissionService.submit`
- Behavioral impact: introduces an unapproved session lifecycle transition during Position Update submission.
- Deep review required: yes

### P8.4
- Classification: NOT_IMPLEMENTED
- Authoritative requirement: persist Position Update results.
- Observed implementation: no matching candidate commit or changed file.
- Commit: none
- File and symbol: none
- Behavioral impact: required task lacks candidate evidence.
- Deep review required: no

### P8.5
- Classification: NOT_IMPLEMENTED
- Authoritative requirement: Build Position Update Frontend.
- Observed implementation: no matching candidate commit or changed file.
- Commit: none
- File and symbol: none
- Behavioral impact: required task lacks candidate evidence.
- Deep review required: no

## 6. Coverage Summary

| Official task | Classification | Commits | Confidence |
|---|---|---|---|
| P6.1 | MATCH | c379017 | HIGH |
| P6.2 | MATCH | b5675ea | HIGH |
| P6.3 | MATCH | 03d2ceb, d05a1da | HIGH |
| P6.4 | MATCH | 295fce0 | HIGH |
| P6.5 | MATCH | 4d25ae9, d73f5b6 | MEDIUM |
| P7.1 | MATCH | a879c03, 0934304 | HIGH |
| P7.2 | BEHAVIOR_DEVIATION | dfed279 | HIGH |
| P7.3 | MATCH | 138465e, 1c7d728 | MEDIUM |
| P7.4 | NUMBERING_ONLY | 85173c1, 2a4bce8 | MEDIUM |
| P7.5 | MATCH | 1efc09f, 14fd234 | MEDIUM |
| P8.1 | MATCH | 23c34c5 | HIGH |
| P8.2 | BEHAVIOR_DEVIATION | 95fa494 | HIGH |
| P8.3 | MATCH | b5aee29, 0026a44 | MEDIUM |
| P8.4 | NOT_IMPLEMENTED | none | HIGH |
| P8.5 | NOT_IMPLEMENTED | none | HIGH |

- MATCH: 10
- NUMBERING_ONLY: 1
- BEHAVIOR_DEVIATION: 2
- UNKNOWN: 0
- NOT_IMPLEMENTED: 2
- Total official tasks audited: 15

## 7. Audit Conclusion

P6 is behaviorally aligned. P7 has a verified P7.2 endpoint and lifecycle deviation. P8 has a verified P8.2 endpoint and lifecycle deviation; P8.4/P8.5 are not implemented in the candidate evidence. It is not safe to determine a resume point while P7.2 and P8.2 require deeper review.

## 8. Scope Compliance

- Product requirements changed: no
- Official task IDs changed: no
- Official task titles changed: no
- Official sequence changed: no
- Acceptance criteria changed: no
- New official tasks created: no
- Application code changed: no
- Tests changed: no
- Schemas changed: no
- Prompts changed: no
- Migrations changed: no
- Runtime files changed: no
- Phase 12 audited: no
- P12.5 interpreted: no
