# TradePilot Evidence Expansion Testing

## Purpose

Define focused verification requirements for Evidence Expansion implementation tasks. Ensure acceptance criteria are met without unnecessary broad testing, real Gemini calls, or unrelated coverage expansion.

## When to Use

Use this skill for every test and evaluation task for the Foreign Flow / Broker Flow Evidence Expansion feature.

Load `tradepilot-evidence-expansion-source-lock` and `tradepilot-focused-testing` together with this skill.

---

## Authoritative Source

> `docs/evidence-expansion/TradePilot_AI_PRD_Foreign_Flow_Broker_Flow_Evidence_Expansion.md` — Section 18 (Acceptance Criteria).
> `docs/rebuild/SCOPE_GUARDRAILS.md` — Section 12 (Task Execution Rules).

---

## Test Requirements by Analysis Type

### INITIAL_ANALYSIS

| Test Case | Expected Result |
|---|---|
| Submit Initial Analysis with all 4 evidence items | Submission succeeds |
| Submit Initial Analysis without `FOREIGN_FLOW_1W` | Submission fails; no Gemini request created |
| Submit Initial Analysis without `ORDERBOOK` | Submission fails (existing behavior preserved) |
| Submit Initial Analysis without `CHART_3_MONTH` | Submission fails (existing behavior preserved) |
| Submit Initial Analysis without `CHART_6_MONTH` | Submission fails (existing behavior preserved) |
| `FOREIGN_FLOW_1W` included in Gemini request | Request contains the Foreign Flow image |
| Output contains `Analisa Foreign Flow` section | Section is present in the analysis result |
| `foreign_flow_assessment` value is one of ACCUMULATION / NEUTRAL / DISTRIBUTION | Field value is valid |
| Initial Evidence immutability | After submission, no overwrite, append, replacement, versioning, or new Initial Evidence set is permitted |

---

### WAIT_UPDATE

| Test Case | Expected Result |
|---|---|
| Submit WAIT Update with `ORDERBOOK` only | Submission succeeds |
| Submit WAIT Update without `ORDERBOOK` | Submission fails (existing behavior preserved) |
| Submit WAIT Update with `ORDERBOOK` + `BROKER_FLOW_1D` | Submission succeeds; both images included in Gemini request |
| `BROKER_FLOW_1D` in Gemini request when supplied | Broker Flow image is present in the request |
| `BROKER_FLOW_1D` absent from Gemini request when not supplied | Broker Flow image is not in the request |
| Broker Flow observation association | Broker Flow belongs to the exact WAIT observation containing its Orderbook, never generic session-level evidence or another WAIT observation |
| Output contains `Analisa Broker Flow` when Broker Flow supplied | Section is present |
| Output omits `Analisa Broker Flow` when Broker Flow not supplied | Section is absent or shows unavailable |

---

### POSITION_UPDATE (Position Update)

| Test Case | Expected Result |
|---|---|
| Submit Position Update with `ORDERBOOK` only | Submission succeeds |
| Submit Position Update without `ORDERBOOK` | Submission fails (existing behavior preserved) |
| Submit Position Update with `ORDERBOOK` + `BROKER_FLOW_1D` | Submission succeeds; both images included in Gemini request |
| `BROKER_FLOW_1D` in Gemini request when supplied | Broker Flow image is present in the request |
| `BROKER_FLOW_1D` absent from Gemini request when not supplied | Broker Flow image is not in the request |
| Monitoring slots unchanged | MORNING / MIDDAY / AFTERNOON slots all work as before |
| Broker Flow observation association | Broker Flow belongs to the exact Position Update observation containing its Orderbook; it cannot attach to another observation and preserves MORNING/MIDDAY/AFTERNOON ownership |
| Output contains `Analisa Broker Flow` when Broker Flow supplied | Section is present |
| Output omits `Analisa Broker Flow` when Broker Flow not supplied | Section is absent or shows unavailable |

---

## Regression Tests

These tests verify that nothing existing was broken by the Evidence Expansion changes.

| Test Case | Expected Result |
|---|---|
| Historical sessions load and display correctly | Readable without errors |
| Historical Initial Analyses with 3 evidence items (no Foreign Flow) remain valid | Displayed correctly |
| Historical WAIT Updates without Broker Flow remain valid | Displayed correctly |
| Historical Position Updates without Broker Flow remain valid | Displayed correctly |
| Session lifecycle statuses unchanged | `DRAFT`, `ANALYZING`, `ANALYZED`, `WAITING`, `OPEN_POSITION`, `CLOSED`, `CLOSED_SKIPPED` only |
| Analysis types unchanged | `INITIAL_ANALYSIS`, `WAIT_UPDATE`, `POSITION_UPDATE` only |
| BUY / WAIT / SKIP / CLOSE behavior unchanged | All user decisions work as before |
| Gemini remains the only provider | No secondary provider active |
| No new session status introduced | Zero new statuses |
| No new analysis type introduced | Zero new types |

---

## Test Discipline Rules

### Use focused tests only

- Run the smallest test set that can prove the acceptance criteria and detect likely regressions.
- Do not run the full repository test suite unless a phase gate explicitly requires it.
- Do not expand test coverage to unrelated areas merely because they exist.

### No real Gemini calls unless explicitly authorized

- Use mocks, fixtures, or fake providers for unit and integration tests.
- Do not make real Gemini API requests unless the active task explicitly requires an end-to-end Gemini test.
- A mocked provider test does not prove real Gemini compatibility; a real call does not replace deterministic fixtures.

### Evidence assembly tests

- Verify that the evidence included in the Gemini request context matches expectations for each evidence type.
- Use controlled test fixtures to prove evidence is present or absent in the request without invoking real Gemini.

### Static prompt-contract tests

Use prompt-text assertions or equivalent non-real-API checks. Verify Foreign Flow requires `ACCUMULATION`, `NEUTRAL`, `DISTRIBUTION`, price/flow confirmation or divergence, no automatic bullish conclusion from one large foreign-buying day, and no invented unreadable values. Verify Broker Flow requires the same classifications, one-day noise caution, broker-code identity caution, and unclear-evidence handling. Verify no fixed arithmetic confidence boost or penalty and that conflicting evidence may reduce confidence.

### Test levels to use

| Level | Use For |
|---|---|
| Unit | Evidence type validation, evidence association rules, `foreign_flow_assessment` enum validation |
| Service / Repository | Evidence persistence, WAIT/Position Update association correctness |
| API | Submission validation (required/optional), error responses, lifecycle eligibility |
| Component | Upload control rendering, optional label, required label, conditional `Analisa Broker Flow` display |
| Focused integration | Evidence-to-Gemini-request composition, output-to-dashboard rendering |

---

## Evidence Composition Verification

For each analysis type, verify that the Gemini request context contains the correct evidence items:

| Analysis Type | Expected in Gemini Request |
|---|---|
| `INITIAL_ANALYSIS` | `ORDERBOOK`, `CHART_3_MONTH`, `CHART_6_MONTH`, `FOREIGN_FLOW_1W` |
| `WAIT_UPDATE` (no Broker Flow) | `ORDERBOOK` only |
| `WAIT_UPDATE` (with Broker Flow) | `ORDERBOOK`, `BROKER_FLOW_1D` |
| `POSITION_UPDATE` (no Broker Flow) | `ORDERBOOK` only |
| `POSITION_UPDATE` (with Broker Flow) | `ORDERBOOK`, `BROKER_FLOW_1D` |

---

## BLOCKED Conditions

Return **BLOCKED** when:
- a required test would need a real Gemini call but the task does not authorize it;
- a failing regression test requires an out-of-scope fix;
- the verification cannot be completed without modifying existing authoritative behavior;
- an acceptance criterion cannot be located in the authoritative PRD.

---

## Required Test Report Fields

Every test report for an Evidence Expansion task must include:
- focused test matrix used;
- exact commands executed;
- pass / fail / skip counts;
- whether any real Gemini request occurred;
- acceptance-criteria evaluation (PASS / FAIL / NOT VERIFIED per criterion);
- regression boundary result;
- limitations and deviations.
