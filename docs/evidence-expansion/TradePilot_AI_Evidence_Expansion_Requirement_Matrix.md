# TradePilot AI — Evidence Expansion Requirement Matrix

**Feature:** Foreign Flow & Broker Flow Evidence Expansion
**Authoritative Source:** `docs/evidence-expansion/TradePilot_AI_PRD_Foreign_Flow_Broker_Flow_Evidence_Expansion.md`
**Document Type:** Traceability Matrix
**Status:** Ready for Product Owner Review

---

## Purpose

This matrix maps every Evidence Expansion requirement to its authoritative source, implementation task, expected repository area, and verification method. It is the traceability reference for confirming that no PRD requirement is lost during implementation.

Every implementation task in the Detailed Task Plan must trace to at least one requirement in this matrix. Every requirement must trace to at least one implementation task.

---

## Column Definitions

| Column | Meaning |
|---|---|
| **Req ID** | Unique requirement identifier for this document |
| **Requirement** | Exact requirement as stated or derived from the PRD |
| **Authoritative Source** | PRD section number |
| **Analysis Type / Workflow** | Affected workflow |
| **Required or Optional** | Whether the evidence or behavior is required or optional |
| **Expected Repository Area** | Primary files or directories that must change |
| **Task Plan Task ID** | Task(s) from `TradePilot_AI_Evidence_Expansion_Detailed_Task_Plan.md` |
| **Acceptance Criteria** | How to verify the requirement is satisfied |
| **Verification Method** | Test type(s) |
| **Backward Compatibility Impact** | Whether historical data or behavior is affected |
| **Status / Notes** | Current status and any notes |

---

## 1. INITIAL_ANALYSIS Requirements

| Req ID | Requirement | Authoritative Source | Analysis Type / Workflow | Required or Optional | Expected Repository Area | Task ID | Acceptance Criteria | Verification Method | Backward Compat. Impact | Status / Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| REQ-IA-01 | `ORDERBOOK` remains a required evidence item for Initial Analysis | PRD §5.1 | INITIAL_ANALYSIS | Required | `context_builder.py` `_load_initial_evidence` | EE4 | Submission without ORDERBOOK fails with `MissingRequiredEvidenceError` | Unit test, API test | None — existing behavior preserved | No change required |
| REQ-IA-02 | `CHART_3_MONTH` remains a required evidence item for Initial Analysis | PRD §5.1 | INITIAL_ANALYSIS | Required | `context_builder.py` `_load_initial_evidence` | EE4 | Submission without CHART_3_MONTH fails | Unit test, API test | None | No change required |
| REQ-IA-03 | `CHART_6_MONTH` remains a required evidence item for Initial Analysis | PRD §5.1 | INITIAL_ANALYSIS | Required | `context_builder.py` `_load_initial_evidence` | EE4 | Submission without CHART_6_MONTH fails | Unit test, API test | None | No change required |
| REQ-IA-04 | `FOREIGN_FLOW_1W` is a required evidence item for new Initial Analysis submissions | PRD §5.1 | INITIAL_ANALYSIS | Required | `evidence_upload.py`, `context_builder.py`, migration | EE2, EE3, EE4 | Submission without FOREIGN_FLOW_1W fails; submission with all 4 succeeds | Unit test, API test | Only applies to new submissions; see REQ-BC-01 | New requirement |
| REQ-IA-05 | FOREIGN_FLOW_1W belongs to Initial Evidence only; must not appear in WAIT or Position Update uploads | PRD §12 | INITIAL_ANALYSIS | Required | Upload API routes | EE3 | FOREIGN_FLOW_1W rejected at WAIT/Position Update upload endpoints | API test | None | Association rule |
| REQ-IA-06 | Only one `FOREIGN_FLOW_1W` belongs to the Initial Evidence set; it cannot be added, replaced, overwritten, appended, or versioned after Initial Evidence submission | PRD §5.1, §12 | INITIAL_ANALYSIS | Required | Upload API or validation | EE3, EE4 | Attempting to upload another `FOREIGN_FLOW_1W` after Initial Evidence submission is rejected; it is never replaced | API test, regression | None | Strict immutability rule |
| REQ-IA-07 | Initial Evidence is submitted only once per session (existing rule preserved) | PRD §5.1 | INITIAL_ANALYSIS | Required | Submission API | EE4 | Attempting to re-submit Initial Analysis is blocked | API test, regression | None | Preserve existing behavior |
| REQ-IA-08 | Gemini receives all four evidence images for Initial Analysis | PRD §6.1 | INITIAL_ANALYSIS | Required | `context_builder.py`, `gemini_adapter.py` | EE4, EE7 | Gemini request context contains 4 evidence references including FOREIGN_FLOW_1W | Integration test (mocked Gemini) | None | Order: ORDERBOOK, CHART_3_MONTH, CHART_6_MONTH, FOREIGN_FLOW_1W |
| REQ-IA-09 | Gemini classifies Foreign Flow as ACCUMULATION, NEUTRAL, or DISTRIBUTION | PRD §6.1 | INITIAL_ANALYSIS | Required | `prompts/rebuild/initial_analysis.md`, `schemas/rebuild/v1/initial_analysis.schema.json` | EE7, EE9 | Prompt instructs classification; schema enforces enum | Prompt review, schema test | None | Classification is Gemini advisory output |
| REQ-IA-10 | Gemini evaluates consistency of foreign flow across the visible week | PRD §6.1 | INITIAL_ANALYSIS | Required | `prompts/rebuild/initial_analysis.md` | EE7 | Prompt contains instruction to evaluate daily consistency | Prompt review | None | Prompt behavioral contract |
| REQ-IA-11 | Gemini evaluates magnitude of recent inflow/outflow visible in the image | PRD §6.1 | INITIAL_ANALYSIS | Required | `prompts/rebuild/initial_analysis.md` | EE7 | Prompt contains magnitude evaluation instruction | Prompt review | None | |
| REQ-IA-12 | Gemini evaluates relationship between foreign flow direction and price direction | PRD §6.1 | INITIAL_ANALYSIS | Required | `prompts/rebuild/initial_analysis.md` | EE7 | Prompt contains price-flow relationship instruction | Prompt review | None | |
| REQ-IA-13 | Gemini evaluates confirmation or divergence between foreign flow and technical thesis | PRD §6.1 | INITIAL_ANALYSIS | Required | `prompts/rebuild/initial_analysis.md` | EE7 | Prompt contains confirmation/divergence instruction | Prompt review | None | |
| REQ-IA-14 | Gemini must not treat a single large foreign-buying day as automatically bullish | PRD §6.1 | INITIAL_ANALYSIS | Required | `prompts/rebuild/initial_analysis.md` | EE7 | Prompt contains explicit one-day trap prevention instruction | Prompt review | None | Guardrail |
| REQ-IA-15 | Dashboard displays `Analisa Foreign Flow` section in Initial Analysis results | PRD §8.1, §19 | INITIAL_ANALYSIS | Required | `frontend/src/features/analysis/initial-analysis-view.tsx` | EE11b | Section renders with assessment and analysis text | Component test | Graceful fallback needed for historical results (see REQ-BC-02) | New UI section |
| REQ-IA-16 | `Analisa Foreign Flow` section position: after `Analisa Chart`, before Support/Resistance | PRD §19 | INITIAL_ANALYSIS | Required | `initial-analysis-view.tsx` | EE11b | Section appears in correct position in rendered output | Component test / visual review | None | Position: item 4 of 12 |

---

## 2. WAIT_UPDATE Requirements

| Req ID | Requirement | Authoritative Source | Analysis Type / Workflow | Required or Optional | Expected Repository Area | Task ID | Acceptance Criteria | Verification Method | Backward Compat. Impact | Status / Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| REQ-WU-01 | `ORDERBOOK` remains a required evidence item for WAIT Update | PRD §5.2 | WAIT_UPDATE | Required | `context_builder.py` `_wait_update_evidence` | EE5 | Submission without ORDERBOOK fails | Unit test, API test | None | Preserve existing behavior |
| REQ-WU-02 | `BROKER_FLOW_1D` is an optional supporting evidence item for WAIT Update | PRD §5.2 | WAIT_UPDATE | Optional | `evidence_upload.py`, `context_builder.py`, migration | EE2, EE5 | WAIT Update submits with Orderbook only; submits with Orderbook + Broker Flow | Unit test, API test | None | New optional requirement |
| REQ-WU-03 | WAIT Update can be submitted with Orderbook only (Broker Flow absence does not block) | PRD §5.2, §13 | WAIT_UPDATE | Required | `context_builder.py`, submission API | EE5 | Submission with Orderbook only succeeds | API test | None | Critical: must not become required |
| REQ-WU-04 | When Broker Flow 1D is uploaded, it must be included in the Gemini analysis context | PRD §5.2 | WAIT_UPDATE | Required when present | `context_builder.py` | EE5 | Gemini request context contains Broker Flow image when uploaded | Integration test (mocked Gemini) | None | Order: Orderbook first, Broker Flow second |
| REQ-WU-05 | `BROKER_FLOW_1D` belongs to the exact WAIT Update analysis request and observation containing its corresponding Orderbook | PRD §12 | WAIT_UPDATE | Required | Upload API, `evidence_uploads_v2` table | EE5, EE12 | Broker Flow is linked to the correct `analysis_request_id` and cannot attach to another observation | Unit test, DB test, regression | None | Never generic session-level evidence |
| REQ-WU-06 | Gemini classifies broker activity as ACCUMULATION, NEUTRAL, or DISTRIBUTION when Broker Flow present | PRD §6.2 | WAIT_UPDATE | Required when present | `prompts/rebuild/wait_update.md`, schema | EE8, EE9 | Prompt instructs classification; schema allows broker_flow_analysis field | Prompt review, schema test | None | Advisory output only |
| REQ-WU-07 | Gemini assesses whether Broker Flow confirms or weakens the WAIT thesis | PRD §6.2 | WAIT_UPDATE | Required when present | `prompts/rebuild/wait_update.md` | EE8 | Prompt contains WAIT thesis confirmation/weakening instruction | Prompt review | None | |
| REQ-WU-08 | Gemini must not produce Broker Flow commentary when Broker Flow evidence is absent | PRD §6.2 | WAIT_UPDATE | Required | `prompts/rebuild/wait_update.md` | EE8 | Prompt uses conditional logic; no Broker Flow section in output when absent | Prompt review, output test | Historical records unaffected | Guardrail |
| REQ-WU-09 | Dashboard displays `Analisa Broker Flow` section only when Broker Flow evidence was supplied | PRD §8.2, §19 | WAIT_UPDATE | Conditional | `frontend/src/features/analysis/watching-update-view.tsx` | EE11c | Section renders with Broker Flow; section absent without Broker Flow | Component test | None | Conditional render |
| REQ-WU-10 | Existing WAIT Update workflow and user decisions remain unchanged | PRD §6.2, §16 | WAIT_UPDATE | Required | All WAIT Update components | EE12 | BUY/WAIT/SKIP recommendations work as before; session status transitions unchanged | Regression test | None | Invariant |

---

## 3. POSITION_UPDATE (Position Update) Requirements

| Req ID | Requirement | Authoritative Source | Analysis Type / Workflow | Required or Optional | Expected Repository Area | Task ID | Acceptance Criteria | Verification Method | Backward Compat. Impact | Status / Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| REQ-PU-01 | `ORDERBOOK` remains a required evidence item for Position Update | PRD §5.3 | POSITION_UPDATE | Required | `context_builder.py` `_position_update_evidence` | EE6 | Submission without ORDERBOOK fails | Unit test, API test | None | Preserve existing behavior |
| REQ-PU-02 | `BROKER_FLOW_1D` is an optional supporting evidence item for Position Update | PRD §5.3 | POSITION_UPDATE | Optional | `evidence_upload.py`, `context_builder.py`, migration | EE2, EE6 | Position Update submits with Orderbook only or with Broker Flow | Unit test, API test | None | New optional requirement |
| REQ-PU-03 | Position Update can be submitted with Orderbook only | PRD §5.3, §13 | POSITION_UPDATE | Required | `context_builder.py`, submission API | EE6 | Submission with Orderbook only succeeds | API test | None | Must not become required |
| REQ-PU-04 | Existing monitoring slots remain unchanged | PRD §5.3 | POSITION_UPDATE | Required | `analysis_request.py` `AnalysisRequestV2ObservationPeriod`, upload API | EE6, EE12 | All approved monitoring slot values work identically | Regression test | None | MORNING, MIDDAY, AFTERNOON (authoritative rebuild contract) |
| REQ-PU-05 | When Broker Flow 1D is uploaded, it must be included in the Gemini analysis context | PRD §5.3 | POSITION_UPDATE | Required when present | `context_builder.py` | EE6 | Gemini request context contains Broker Flow image when uploaded | Integration test (mocked Gemini) | None | |
| REQ-PU-06 | `BROKER_FLOW_1D` belongs to the exact Position Update analysis request and observation containing its corresponding Orderbook | PRD §12 | POSITION_UPDATE | Required | Upload API | EE6, EE12 | Broker Flow is linked to the correct `analysis_request_id` and cannot attach to another observation | Unit test, regression | None | Never generic session-level evidence |
| REQ-PU-07 | Gemini classifies broker activity as ACCUMULATION, NEUTRAL, or DISTRIBUTION when Broker Flow present | PRD §6.3 | POSITION_UPDATE | Required when present | `prompts/rebuild/position_update.md`, schema | EE8, EE9 | Prompt instructs classification; schema allows field | Prompt review, schema test | None | |
| REQ-PU-08 | Gemini assesses accumulation continuity and distribution emergence | PRD §6.3 | POSITION_UPDATE | Required when present | `prompts/rebuild/position_update.md` | EE8 | Prompt contains accumulation/distribution assessment instruction | Prompt review | None | |
| REQ-PU-09 | Gemini assesses risk implication when Broker Flow is present | PRD §6.3 | POSITION_UPDATE | Required when present | `prompts/rebuild/position_update.md` | EE8 | Prompt contains risk implication instruction | Prompt review | None | |
| REQ-PU-10 | Dashboard displays `Analisa Broker Flow` section only when Broker Flow evidence was supplied | PRD §8.3, §19 | POSITION_UPDATE | Conditional | `frontend/src/features/analysis/open-position-update-view.tsx` | EE11c | Section renders with Broker Flow; absent without | Component test | None | |
| REQ-PU-11 | Existing Position Update decision framework remains unchanged | PRD §8.3, §16 | POSITION_UPDATE | Required | All Position Update components | EE12 | CLOSE and position management work identically | Regression test | None | Invariant |

---

## 4. Gemini Reasoning Guardrails

| Req ID | Requirement | Authoritative Source | Analysis Type / Workflow | Required or Optional | Expected Repository Area | Task ID | Acceptance Criteria | Verification Method | Backward Compat. Impact | Status / Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| REQ-GM-01 | Gemini must not invent broker values, foreign-flow numbers, or price facts from unreadable screenshots | PRD §7 | All flow analysis | Required | All three prompts | EE7, EE8 | Prompts contain explicit fabrication prohibition | Prompt review | None | Guardrail |
| REQ-GM-02 | Gemini must state clearly when flow evidence is unclear | PRD §7, §14 | All flow analysis | Required | All three prompts | EE7, EE8 | Prompts contain unclear-evidence instruction | Prompt review | None | |
| REQ-GM-03 | Gemini must use cautious language: supports, weakens, confirms, conflicts with, indicates, suggests | PRD §7 | All flow analysis | Required | All three prompts | EE7, EE8 | Prompts contain language register instruction | Prompt review | None | |
| REQ-GM-04 | Gemini must not claim certainty from screenshots | PRD §7 | All flow analysis | Required | All three prompts | EE7, EE8 | Prompts contain no-certainty guardrail | Prompt review | None | |
| REQ-GM-05 | Broker codes do not necessarily represent a single investor or institution | PRD §7 | WAIT_UPDATE, POSITION_UPDATE | Required | WAIT and Position Update prompts | EE8 | Prompts contain broker code interpretation guardrail | Prompt review | None | |
| REQ-GM-06 | One-day broker flow can be noisy | PRD §7 | WAIT_UPDATE, POSITION_UPDATE | Required | WAIT and Position Update prompts | EE8 | Prompts contain one-day noise guardrail | Prompt review | None | |
| REQ-GM-07 | Conflicting flow evidence must reduce confidence rather than being ignored | PRD §7, §9 | All flow analysis | Required | All three prompts | EE7, EE8 | Prompts instruct confidence reduction on conflict | Prompt review | None | |
| REQ-GM-08 | No fixed arithmetic confidence bonus or penalty for flow evidence | PRD §9 | All flow analysis | Required | All three prompts, schemas | EE7, EE8, EE9 | No hardcoded +X% instruction in prompts; no arithmetic formula in schema | Prompt review, schema review | None | |

---

## 5. Output Requirements

| Req ID | Requirement | Authoritative Source | Analysis Type / Workflow | Required or Optional | Expected Repository Area | Task ID | Acceptance Criteria | Verification Method | Backward Compat. Impact | Status / Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| REQ-OP-01 | All existing Initial Analysis output fields remain unchanged | PRD §8.1 | INITIAL_ANALYSIS | Required | `schemas/rebuild/v1/initial_analysis.schema.json` | EE9 | All current required fields still present and required in schema | Schema test | None | Preservation rule |
| REQ-OP-02 | `foreign_flow_analysis` with `assessment` and `analysis` added to the new Initial Analysis generation schema | PRD §8.1 | INITIAL_ANALYSIS | Required | `schemas/rebuild/v1/initial_analysis.schema.json` | EE9 | Field is present and required for new schema validation; enum values ACCUMULATION/NEUTRAL/DISTRIBUTION | Schema test | Historical persisted records lacking the field remain readable through backward-compatible rendering/read behavior | New required generation-time field |
| REQ-OP-03 | `broker_flow_analysis` added as optional/nullable to WAIT Update schema | PRD §8.2 | WAIT_UPDATE | Optional | `schemas/rebuild/v1/wait_update.schema.json` | EE9 | Field present; absent from `required` array; validates correctly when present | Schema test | None — optional field | New optional field |
| REQ-OP-04 | `broker_flow_analysis` added as optional/nullable to Position Update schema | PRD §8.3 | POSITION_UPDATE | Optional | `schemas/rebuild/v1/position_update.schema.json` | EE9 | Field present; absent from `required` array; validates correctly when present | Schema test | None | New optional field |
| REQ-OP-05 | All existing WAIT Update output fields remain unchanged | PRD §8.2 | WAIT_UPDATE | Required | `schemas/rebuild/v1/wait_update.schema.json` | EE9 | All current required fields still present and required | Schema test | None | Preservation rule |
| REQ-OP-06 | All existing Position Update output fields remain unchanged | PRD §8.3 | POSITION_UPDATE | Required | `schemas/rebuild/v1/position_update.schema.json` | EE9 | All current required fields still present and required | Schema test | None | Preservation rule |
| REQ-OP-07 | Confidence and probability may change but without hard-coded arithmetic weighting | PRD §9 | All analysis types | Required | All three prompts | EE7, EE8 | No arithmetic formula in any prompt or schema | Prompt review | None | |
| REQ-OP-08 | `Analisa Foreign Flow` section label used in dashboard | PRD §8.1, §19 | INITIAL_ANALYSIS | Required | `initial-analysis-view.tsx` | EE11b | Section renders with label "Analisa Foreign Flow" | Component test | None | |
| REQ-OP-09 | `Analisa Broker Flow` section label used in dashboard when present | PRD §8.2, §8.3, §19 | WAIT_UPDATE, POSITION_UPDATE | Conditional | `watching-update-view.tsx`, `open-position-update-view.tsx` | EE11c | Section renders with label "Analisa Broker Flow" only when Broker Flow evidence was supplied | Component test | None | |

---

## 6. Backward Compatibility Requirements

| Req ID | Requirement | Authoritative Source | Analysis Type / Workflow | Required or Optional | Expected Repository Area | Task ID | Acceptance Criteria | Verification Method | Backward Compat. Impact | Status / Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| REQ-BC-01 | Historical Initial Analyses with only ORDERBOOK + CHART_3_MONTH + CHART_6_MONTH remain valid and readable | PRD §15 | INITIAL_ANALYSIS | Required | All rendering code, schema read path | EE12 | Historical sessions display without errors | Regression test | Existing records unaffected | No data migration |
| REQ-BC-02 | Historical Initial Analysis `processed_response` records without `foreign_flow_analysis` do not cause display errors | PRD §15 | INITIAL_ANALYSIS | Required | `initial-analysis-view.tsx` | EE11b | Renderer gracefully handles absent field | Component test | Graceful fallback required | Frontend handles null/absent |
| REQ-BC-03 | Historical WAIT Updates without `BROKER_FLOW_1D` remain valid and readable | PRD §15 | WAIT_UPDATE | Required | All rendering code | EE12 | Historical WAIT Updates display without errors | Regression test | None | |
| REQ-BC-04 | Historical Position Updates without `BROKER_FLOW_1D` remain valid and readable | PRD §15 | POSITION_UPDATE | Required | All rendering code | EE12 | Historical Position Updates display without errors | Regression test | None | |
| REQ-BC-05 | No new session lifecycle status is introduced | PRD §3.2, §16 | All | Required | `analysis_request.py`, session models | EE12 | `DRAFT`, `ANALYZING`, `ANALYZED`, `WAITING`, `OPEN_POSITION`, `CLOSED`, `CLOSED_SKIPPED` only | Regression test | None | Lifecycle invariant |
| REQ-BC-06 | No new analysis type is introduced | PRD §4, §3.2 | All | Required | `analysis_request.py` | EE12 | Only `INITIAL_ANALYSIS`, `WAIT_UPDATE`, `POSITION_UPDATE` exist in rebuild models | Code review | None | Analysis type invariant |
| REQ-BC-07 | No new trading action (BUY/WAIT/SKIP/CLOSE) is introduced | PRD §3.2 | All | Required | Decision API | EE12 | Only existing decisions function | Regression test | None | Decision invariant |
| REQ-BC-08 | Gemini remains the only AI provider | PRD §3.2, §16 | All | Required | `gemini_adapter.py`, `analysis_request.py` CHECK constraint | EE12 | `provider = 'gemini'` constraint remains; no other provider active | Code review, regression | None | Provider invariant |
| REQ-BC-09 | No new navigation items or routes are introduced | PRD §10, §3.2 | All | Required | `frontend/src/app/` | EE12 | Same routes before and after feature | Code review | None | Navigation invariant |

---

## 7. Data Model Requirements

| Req ID | Requirement | Authoritative Source | Analysis Type / Workflow | Required or Optional | Expected Repository Area | Task ID | Acceptance Criteria | Verification Method | Backward Compat. Impact | Status / Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| REQ-DM-01 | Existing evidence storage model is reused; no new subsystem | PRD §12 | All | Required | `evidence_upload.py`, `evidence_uploads_v2` table | EE2 | `FOREIGN_FLOW_1W` and `BROKER_FLOW_1D` added to existing enum only | Code review, migration test | None | |
| REQ-DM-02 | `evidence_upload_v2_type_enum` PostgreSQL enum extended to include `FOREIGN_FLOW_1W` | PRD §12 | All | Required | Migration | EE2 | Migration adds values; existing records readable | Migration test | None | ALTER TYPE ADD VALUE |
| REQ-DM-03 | `evidence_upload_v2_type_enum` PostgreSQL enum extended to include `BROKER_FLOW_1D` | PRD §12 | All | Required | Migration | EE2 | Same as above | Migration test | None | |
| REQ-DM-04 | No data migration is required for historical `processed_response` JSONB records | PRD §15 | All | Required | `analysis_requests_v2` table | EE9 | Schema extension is backward-compatible for reads | Schema test | None | No migration needed |

---

## 8. UI/UX Requirements

| Req ID | Requirement | Authoritative Source | Analysis Type / Workflow | Required or Optional | Expected Repository Area | Task ID | Acceptance Criteria | Verification Method | Backward Compat. Impact | Status / Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| REQ-UI-01 | Initial Analysis form adds "Foreign Flow — 1W" required upload control | PRD §10 | INITIAL_ANALYSIS | Required | Initial Evidence upload form | EE10 | Control renders; submission blocked without it | Component test | None | |
| REQ-UI-02 | WAIT Update form adds "Broker Flow — 1D (Optional)" upload control | PRD §10 | WAIT_UPDATE | Required (control must exist) | WAIT Update form | EE11 | Control renders; form submits with or without it | Component test | None | |
| REQ-UI-03 | Position Update form adds "Broker Flow — 1D (Optional)" upload control | PRD §10 | POSITION_UPDATE | Required (control must exist) | Position Update form | EE11 | Control renders; form submits with or without it | Component test | None | |
| REQ-UI-04 | Existing upload interaction pattern reused; no new upload component | PRD §17 | All | Required | All upload form components | EE10, EE11 | Same upload component used for new controls | Code review | None | |
| REQ-UI-05 | Labels are clear and mobile-friendly; single-column layout on mobile | PRD §17 | All | Required | All upload form components | EE10, EE11 | Forms display correctly on narrow viewports | Visual review | None | |
| REQ-UI-06 | Evidence type labels shown after upload: "Foreign Flow 1W", "Broker Flow 1D" | PRD §11 | All | Required | All upload form components | EE10, EE11 | Correct labels visible after upload | Component test | None | |
| REQ-UI-07 | No new pages, navigation items, or routes are added | PRD §10 | All | Required | `frontend/src/app/` routing | EE12 | No new routes in frontend | Code review | None | |

---

## 9. Requirement-to-Task Coverage Map

| Task ID | Requirements Covered |
|---|---|
| EE1 | Baseline confirmation for all requirements |
| EE2 | REQ-DM-01, REQ-DM-02, REQ-DM-03 |
| EE3 | REQ-IA-04, REQ-IA-05, REQ-IA-06 |
| EE4 | REQ-IA-01, REQ-IA-02, REQ-IA-03, REQ-IA-04, REQ-IA-07, REQ-IA-08 |
| EE5 | REQ-WU-01, REQ-WU-02, REQ-WU-03, REQ-WU-04, REQ-WU-05 |
| EE6 | REQ-PU-01, REQ-PU-02, REQ-PU-03, REQ-PU-04, REQ-PU-05, REQ-PU-06 |
| EE7 | REQ-IA-09, REQ-IA-10, REQ-IA-11, REQ-IA-12, REQ-IA-13, REQ-IA-14, REQ-GM-01, REQ-GM-02, REQ-GM-03, REQ-GM-04, REQ-GM-07, REQ-GM-08, REQ-OP-07 |
| EE8 | REQ-WU-06, REQ-WU-07, REQ-WU-08, REQ-PU-07, REQ-PU-08, REQ-PU-09, REQ-GM-01–REQ-GM-08 |
| EE9 | REQ-OP-01–REQ-OP-09, REQ-DM-04 |
| EE10 | REQ-UI-01, REQ-UI-04, REQ-UI-05, REQ-UI-06 |
| EE11 | REQ-UI-02, REQ-UI-03, REQ-UI-04, REQ-UI-05, REQ-UI-06 |
| EE11b | REQ-IA-15, REQ-IA-16, REQ-OP-08, REQ-BC-01, REQ-BC-02 |
| EE11c | REQ-WU-09, REQ-PU-10, REQ-OP-09, REQ-BC-03, REQ-BC-04 |
| EE12 | REQ-IA-06, REQ-IA-07, REQ-WU-05, REQ-WU-10, REQ-PU-06, REQ-PU-11, REQ-BC-01–REQ-BC-09, REQ-UI-07 |

---

## 10. Requirements Not Covered by Implementation Tasks (No-Code Requirements)

The following requirements require no code change; they are enforced by the PRD's explicit non-goals:

| Req ID | Statement | Enforcement |
|---|---|---|
| NO-01 | No new analysis type created | PRD §3.2; enforced by task discipline rule |
| NO-02 | No new session status created | PRD §3.2; enforced by task discipline rule |
| NO-03 | No automatic broker identification outside Gemini | PRD §3.2 |
| NO-04 | No numerical calculation of foreign or broker flow from raw data | PRD §3.2 |
| NO-05 | No new queue architecture | PRD §3.2 |
| NO-06 | No change to the Gemini provider or model | PRD §3.2 |
| NO-07 | No image-content OCR validation required | PRD §13 |
| NO-08 | No redesign of unrelated dashboard components | PRD §3.2, §10 |
