# TradePilot AI — Evidence Expansion Detailed Task Plan

**Feature:** Foreign Flow & Broker Flow Evidence Expansion
**Authoritative Source:** `docs/evidence-expansion/TradePilot_AI_PRD_Foreign_Flow_Broker_Flow_Evidence_Expansion.md`
**Task Discipline Source:** `docs/rebuild/SCOPE_GUARDRAILS.md`
**Document Type:** Authoritative Implementation Task Plan
**Status:** Ready for Product Owner Review

---

## Source Lock

Before executing any task in this plan, read directly:

| Document | Path |
|---|---|
| Evidence Expansion PRD | `docs/evidence-expansion/TradePilot_AI_PRD_Foreign_Flow_Broker_Flow_Evidence_Expansion.md` |
| Scope Guardrails | `docs/rebuild/SCOPE_GUARDRAILS.md` |
| Session Status Rules | `docs/rebuild/SESSION_STATUS_RULES.md` |
| Analysis Input Contracts | `docs/rebuild/ANALYSIS_INPUT_CONTRACTS.md` |
| Simple Architecture | `docs/rebuild/SIMPLE_ARCHITECTURE.md` |
| Requirement Matrix | `docs/evidence-expansion/TradePilot_AI_Evidence_Expansion_Requirement_Matrix.md` |
| Prompt Contract | `docs/evidence-expansion/TradePilot_AI_Evidence_Expansion_Gemini_Prompt_Contract.md` |
| Output Contract | `docs/evidence-expansion/TradePilot_AI_Evidence_Expansion_Output_Contract.md` |
| Impact Audit | `docs/evidence-expansion/TradePilot_AI_Evidence_Expansion_Implementation_Impact_Audit.md` |

Do not rely on memory, prior chat context, or existing code behavior as a proxy for requirements.

---

## Task Discipline Rules

- One task = one small, focused, verifiable unit of implementation.
- No task may silently include unrelated cleanup, refactoring, or additional features.
- Each task must have an explicit Acceptance Criteria section.
- Each task must specify the minimum focused test set.
- Broader regression testing belongs only in the final feature gate task (EE12).
- Task order reflects actual dependency — do not reorder.
- STOP conditions must be evaluated before executing any task.
- Task IDs use the prefix `EE`. Sub-tasks use suffixes (e.g., `EE4a`, `EE4b`).

---

## Phase A: Source Lock and Conflict Identification

### EE1 — Confirm Authoritative Sources and Repository Baseline

**Objective:** Verify that authoritative documents are accessible and consistent, and confirm the exact repository baseline before any change.

**Authoritative Source Lock:**
- Evidence Expansion PRD (all sections)
- `docs/rebuild/SCOPE_GUARDRAILS.md`
- `docs/rebuild/ANALYSIS_INPUT_CONTRACTS.md`

**Scope:**
- Read and confirm the Evidence Expansion PRD is complete.
- Read and confirm all six Evidence Expansion skills are present.
- Identify the exact current values of `EvidenceUploadV2Type` in `backend/app/trade_workspace/models/evidence_upload.py`.
- Identify the exact current values of `AnalysisRequestV2ObservationPeriod` in `backend/app/trade_workspace/models/analysis_request.py`.
- Identify the exact `required_types` in `context_builder.py` `_load_initial_evidence`.
- Identify the linked-evidence count constraint in `_wait_update_evidence` and `_position_update_evidence`.
- Confirm the `additionalProperties: false` constraint in all three JSON schemas under `schemas/rebuild/v1/`.
- Record the current content of all three prompt files under `prompts/rebuild/`.

**Scope Diff:**
- Current: No flow evidence types exist; context builder requires exactly 3 evidence items for Initial Analysis and exactly 1 for WAIT/Position Updates.
- Required: Confirm conflicts and gaps before any implementation begins.
- Smallest change: None — this is an audit task only.

**Dependencies:** None.

**Repository Areas / Expected Files:**
- `backend/app/trade_workspace/models/evidence_upload.py`
- `backend/app/trade_workspace/models/analysis_request.py`
- `backend/app/trade_workspace/ai/context_builder.py`
- `schemas/rebuild/v1/initial_analysis.schema.json`
- `schemas/rebuild/v1/wait_update.schema.json`
- `schemas/rebuild/v1/position_update.schema.json`
- `prompts/rebuild/initial_analysis.md`
- `prompts/rebuild/wait_update.md`
- `prompts/rebuild/position_update.md`

**Implementation Requirements:**
- Document findings only. Do not modify any file.

**Explicit Non-Goals:**
- Do not implement any change.
- Do not add any evidence type.

**Acceptance Criteria:**
- All authoritative documents have been read and their exact contents confirmed.
- Repository baseline is documented with no changes.
- Any conflicts between PRD and repository are identified and recorded.

**Focused Verification:** Visual confirmation only — no automated test is required.

**STOP / BLOCKED Conditions:**
- Any authoritative document is absent or cannot be read.
- Repository contents cannot be confirmed.

---

## Phase B: Evidence Type Support

### EE2 — Add FOREIGN_FLOW_1W and BROKER_FLOW_1D Evidence Types

**Objective:** Extend the `EvidenceUploadV2Type` enum and the corresponding PostgreSQL database enum to include the two new evidence types, while preserving all existing values.

**Authoritative Source Lock:**
- PRD Section 12: Data Model Impact
- PRD Section 5: Evidence Requirements

**Scope:**
- Add `FOREIGN_FLOW_1W = "FOREIGN_FLOW_1W"` to `EvidenceUploadV2Type`.
- Add `BROKER_FLOW_1D = "BROKER_FLOW_1D"` to `EvidenceUploadV2Type`.
- Create an Alembic migration that adds `FOREIGN_FLOW_1W` and `BROKER_FLOW_1D` to the `evidence_upload_v2_type_enum` PostgreSQL enum using `ALTER TYPE ... ADD VALUE`.
- Do not modify `AnalysisRequestV2Type`, `AnalysisRequestV2ObservationPeriod`, or any other enum.

**Scope Diff:**
- Current: `EvidenceUploadV2Type` has `ORDERBOOK`, `CHART_3_MONTH`, `CHART_6_MONTH`.
- Required: Add `FOREIGN_FLOW_1W` and `BROKER_FLOW_1D`.
- Behaviors unchanged: All existing evidence type values remain valid.

**Dependencies:** EE1.

**Repository Areas / Expected Files:**
- `backend/app/trade_workspace/models/evidence_upload.py` — extend `EvidenceUploadV2Type`
- `backend/migrations/versions/<new_revision>.py` — new migration adding values to `evidence_upload_v2_type_enum`

**Implementation Requirements:**
- Use `ALTER TYPE evidence_upload_v2_type_enum ADD VALUE IF NOT EXISTS 'FOREIGN_FLOW_1W'`.
- Use `ALTER TYPE evidence_upload_v2_type_enum ADD VALUE IF NOT EXISTS 'BROKER_FLOW_1D'`.
- Migration must be reversible or explicitly document why downgrade is not safe.
- Existing records with existing type values must remain unchanged and readable.

**Explicit Non-Goals:**
- Do not change `AnalysisRequestV2ObservationPeriod`.
- Do not change session status or analysis type enums.
- Do not yet change validation logic, context builder, or API routes.

**Acceptance Criteria:**
- `EvidenceUploadV2Type.FOREIGN_FLOW_1W` and `EvidenceUploadV2Type.BROKER_FLOW_1D` are importable.
- Running the migration on a test database adds the two values to the PostgreSQL enum.
- Existing evidence records with `ORDERBOOK`, `CHART_3_MONTH`, `CHART_6_MONTH` remain readable after migration.
- No other models, schemas, or logic are changed.

**Focused Verification / Tests:**
- Unit test: `EvidenceUploadV2Type.FOREIGN_FLOW_1W` and `EvidenceUploadV2Type.BROKER_FLOW_1D` exist and have the correct string values.
- Migration test: Apply migration; verify `evidence_upload_v2_type_enum` contains all five values.
- Regression: Existing `EvidenceUploadV2Type` values remain importable with unchanged string values.

**STOP / BLOCKED Conditions:**
- PostgreSQL version does not support `ADD VALUE` without a transaction.

---

## Phase C: Initial Analysis Evidence Behavior

### EE3 — Update Initial Analysis Evidence Upload API to Accept FOREIGN_FLOW_1W

**Objective:** Allow the Initial Evidence upload endpoint to accept `FOREIGN_FLOW_1W` as an evidence type, treating it identically to the existing upload flow.

**Authoritative Source Lock:**
- PRD Section 5.1: Initial Analysis evidence requirements
- PRD Section 12: Data model, association rules

**Scope:**
- Identify where the upload API validates or restricts accepted evidence types for Initial Evidence.
- Update the accepted evidence type allowlist so that `FOREIGN_FLOW_1W` is an accepted upload type for Initial Evidence.
- `FOREIGN_FLOW_1W` must be associated with the session at session level (nullable `analysis_request_id`), consistent with how `ORDERBOOK`, `CHART_3_MONTH`, and `CHART_6_MONTH` are currently associated.
- Do not change the upload mechanism, storage, or file-processing logic.

**Scope Diff:**
- Current: Upload API accepts `ORDERBOOK`, `CHART_3_MONTH`, `CHART_6_MONTH` for Initial Evidence.
- Required: Also accept `FOREIGN_FLOW_1W`.
- Behaviors unchanged: Rejection of `BROKER_FLOW_1D` and other unauthorized types at Initial Evidence upload.

**Dependencies:** EE2.

**Repository Areas / Expected Files:**
- `backend/app/trade_workspace/api/routes/trade_sessions.py` — Initial Evidence upload route
- `backend/app/trade_workspace/api/schemas.py` — If evidence type is validated at schema level

**Implementation Requirements:**
- Only `FOREIGN_FLOW_1W` is added to the allowlist for this endpoint — not `BROKER_FLOW_1D`.
- `BROKER_FLOW_1D` must NOT be uploadable via the Initial Evidence endpoint.
- Existing upload validation for `ORDERBOOK`, `CHART_3_MONTH`, `CHART_6_MONTH` must remain unchanged.
- Initial Evidence is submitted exactly once and remains immutable: no overwrite, append, replacement, versioning, or second Initial Evidence set is permitted.

**Explicit Non-Goals:**
- Do not change the context builder yet.
- Do not change submission validation yet (EE4 covers that).
- Do not change WAIT or Position Update upload routes.

**Acceptance Criteria:**
- `FOREIGN_FLOW_1W` can be uploaded via the Initial Evidence upload endpoint.
- `BROKER_FLOW_1D` is rejected at the Initial Evidence upload endpoint.
- `ORDERBOOK`, `CHART_3_MONTH`, `CHART_6_MONTH` continue to upload successfully.
- Any attempt to add or replace Initial Evidence after submission is rejected.

**Focused Verification / Tests:**
- API test: `POST /initial-evidence` with `FOREIGN_FLOW_1W` → `201 Created`.
- API test: `POST /initial-evidence` with `BROKER_FLOW_1D` → `422` or `400` rejection.
- API test: `POST /initial-evidence` with `ORDERBOOK` → `201 Created` (regression).
- API test: a second Initial Evidence upload after submission → rejected; no overwrite, append, replacement, versioning, or second set is created.

**STOP / BLOCKED Conditions:**
- The upload endpoint does not have an accessible evidence type allowlist (i.e., it accepts any `EvidenceUploadV2Type` value without validation). In that case, this task may require no change at the upload level, but the constraint must be confirmed before proceeding.

---

### EE4 — Update Initial Analysis Submission to Require FOREIGN_FLOW_1W

**Objective:** Update the Initial Analysis submission validation so that `FOREIGN_FLOW_1W` is required alongside the existing three evidence items.

**Authoritative Source Lock:**
- PRD Section 5.1, 13, 18: Initial Analysis evidence requirements

**Scope:**
- Update `_load_initial_evidence` in `context_builder.py` to add `EvidenceUploadV2Type.FOREIGN_FLOW_1W` to `required_types`.
- The context builder must now require and resolve exactly four evidence items in a defined order.
- Submission must fail with `MissingRequiredEvidenceError` if `FOREIGN_FLOW_1W` is absent.
- The evidence order passed to Gemini must be: `ORDERBOOK`, `CHART_3_MONTH`, `CHART_6_MONTH`, `FOREIGN_FLOW_1W`.

**Scope Diff:**
- Current: `required_types = (ORDERBOOK, CHART_3_MONTH, CHART_6_MONTH)`.
- Required: `required_types = (ORDERBOOK, CHART_3_MONTH, CHART_6_MONTH, FOREIGN_FLOW_1W)`.
- Behaviors unchanged: Existing three evidence types remain required; historical Initial Analyses without `FOREIGN_FLOW_1W` remain readable.

**Dependencies:** EE3.

**Repository Areas / Expected Files:**
- `backend/app/trade_workspace/ai/context_builder.py` — `_load_initial_evidence`
- `backend/tests/trade_workspace/test_context_builder.py` — must be updated for the new requirement

**Implementation Requirements:**
- The context builder returns `FOREIGN_FLOW_1W` as the fourth evidence item.
- The order in the evidence tuple must be deterministic and match the prompt's image role order.
- Initial Evidence remains immutable after its single submission; this task must not authorize overwrite, append, replacement, versioning, or a second Initial Evidence set.
- Historical `AnalysisRequest` records whose `processed_response` does not contain `foreign_flow_analysis` must remain readable — this is output-level backward compatibility, not input-level.

**Explicit Non-Goals:**
- Do not change the Gemini prompt yet (EE7 covers that).
- Do not change the response schema yet (EE9 covers that).

**Acceptance Criteria:**
- Initial Analysis submission with all four evidence items → context built successfully with four evidence references.
- Initial Analysis submission without `FOREIGN_FLOW_1W` → `MissingRequiredEvidenceError`.
- Initial Analysis submission without any of the original three → same error behavior as before.

**Focused Verification / Tests:**
- Unit test: `_load_initial_evidence` with ORDERBOOK+CHART_3_MONTH+CHART_6_MONTH+FOREIGN_FLOW_1W → returns 4 evidence references in correct order.
- Unit test: `_load_initial_evidence` with only 3 items (no FOREIGN_FLOW_1W) → `MissingRequiredEvidenceError`.
- Regression: Existing Initial Analysis tests with 3 images → must fail now (update accordingly).
- Regression: a second Initial Evidence submission is rejected without replacing or appending evidence.

**STOP / BLOCKED Conditions:**
- The context builder pattern does not support a fourth evidence item cleanly.

---

## Phase D: WAIT Update Evidence Behavior

### EE5 — Update WAIT Update to Optionally Accept BROKER_FLOW_1D

**Objective:** Allow `BROKER_FLOW_1D` to be uploaded and linked to a WAIT Update analysis request. Update the context builder to pass both Orderbook and Broker Flow to Gemini when Broker Flow is present.

**Authoritative Source Lock:**
- PRD Section 5.2: WAIT Update evidence requirements
- PRD Section 12: Association rules for `BROKER_FLOW_1D`

**Scope:**
- **Upload API**: Extend the WAIT Update evidence upload endpoint to accept an optional `BROKER_FLOW_1D` upload. It must belong to the exact WAIT Update analysis request and observation containing the corresponding Orderbook, never generic session-level evidence.
- **Context builder**: Update `_wait_update_evidence` to handle 1 or 2 linked evidence items (Orderbook only, or Orderbook + Broker Flow). The required Orderbook must always be present. Broker Flow is optional.
- When `BROKER_FLOW_1D` is present, include it in `AnalysisContext.evidence` after the Orderbook.
- When `BROKER_FLOW_1D` is absent, context builder behavior is unchanged.

**Scope Diff:**
- Current: `_wait_update_evidence` requires `len(linked_evidence) == 1` (exactly one Orderbook).
- Required: Allow `len(linked_evidence)` to be 1 (Orderbook) or 2 (Orderbook + Broker Flow). The Orderbook must be present in both cases.
- Behaviors unchanged: WAIT Update can still be submitted with Orderbook only; the constraint that WAIT Update requires no open position remains.

**Dependencies:** EE2, EE1.

**Repository Areas / Expected Files:**
- `backend/app/trade_workspace/api/routes/trade_sessions.py` — WAIT Update upload endpoint
- `backend/app/trade_workspace/ai/context_builder.py` — `_wait_update_evidence`, `build` method for `WAIT_UPDATE`

**Implementation Requirements:**
- The Orderbook validation must remain strict: absence of Orderbook must still raise `MissingRequiredEvidenceError`.
- `BROKER_FLOW_1D` must be linked to the same `analysis_request_id` and exact WAIT observation as the corresponding Orderbook; it must not attach to another observation.
- The order of evidence passed to Gemini: Orderbook first, Broker Flow second (when present).
- When Broker Flow is absent, `AnalysisContext.evidence` contains only the Orderbook (existing behavior).
- `FOREIGN_FLOW_1W` must not be accepted at the WAIT Update upload endpoint.

**Explicit Non-Goals:**
- Do not change the Gemini prompt yet (EE8 covers that).
- Do not change how WAIT Update history is loaded.
- Do not change Position Update logic.

**Acceptance Criteria:**
- WAIT Update submission with Orderbook only → succeeds; context contains 1 evidence reference.
- WAIT Update submission with Orderbook + Broker Flow → succeeds; context contains 2 evidence references (Orderbook first).
- WAIT Update submission without Orderbook → `MissingRequiredEvidenceError`.
- Broker Flow absent from Gemini request when not uploaded.
- Broker Flow present in Gemini request (evidence tuple) when uploaded.
- Broker Flow cannot attach as generic session-level evidence or to another WAIT observation.

**Focused Verification / Tests:**
- Unit test: `_wait_update_evidence` with Orderbook only → returns 1 evidence reference.
- Unit test: `_wait_update_evidence` with Orderbook + Broker Flow → returns 2 evidence references in correct order.
- Unit test: `_wait_update_evidence` without Orderbook → `MissingRequiredEvidenceError`.
- Integration test: WAIT Update submission with Broker Flow → `AnalysisContext.evidence` contains both images.
- Regression: Existing WAIT Update tests pass unchanged (Orderbook only).

**STOP / BLOCKED Conditions:**
- The Gemini adapter or context builder cannot accept a variable-length evidence tuple.

---

## Phase E: Position Update Evidence Behavior

### EE6 — Update Position Update to Optionally Accept BROKER_FLOW_1D

**Objective:** Allow `BROKER_FLOW_1D` to be uploaded and linked to a Position Update analysis request. Update the context builder to pass both Orderbook and Broker Flow to Gemini when Broker Flow is present.

**Authoritative Source Lock:**
- PRD Section 5.3: Position Update evidence requirements
- PRD Section 12: Association rules for `BROKER_FLOW_1D`

**Scope:**
- **Upload API**: Extend the Position Update evidence upload endpoint to accept an optional `BROKER_FLOW_1D` upload. It must belong to the exact Position Update analysis request and observation containing the corresponding Orderbook, never generic session-level evidence.
- **Context builder**: Update `_position_update_evidence` to handle 1 or 2 linked evidence items. The Orderbook must always be present.
- When `BROKER_FLOW_1D` is present, include it in `AnalysisContext.evidence` after the Orderbook.
- When `BROKER_FLOW_1D` is absent, context builder behavior is unchanged.

**Scope Diff:**
- Current: `_position_update_evidence` requires `len(linked_evidence) == 1`.
- Required: Allow 1 (Orderbook) or 2 (Orderbook + Broker Flow).
- Behaviors unchanged: Monitoring slots (`MORNING`, `MIDDAY`, `AFTERNOON`) remain unchanged. Position Update can be submitted with Orderbook only.

**Dependencies:** EE2, EE1.

**Repository Areas / Expected Files:**
- `backend/app/trade_workspace/api/routes/trade_sessions.py` — Position Update upload endpoint
- `backend/app/trade_workspace/ai/context_builder.py` — `_position_update_evidence`, `build` method for `POSITION_UPDATE`

**Implementation Requirements:**
- Same pattern as EE5 but for `POSITION_UPDATE`.
- `BROKER_FLOW_1D` must be linked to the same `analysis_request_id` and exact Position Update observation as the corresponding Orderbook; it must not attach to another observation.
- Observation facts (price, period, timestamp) continue to come from the Orderbook evidence only — not from Broker Flow.
- `FOREIGN_FLOW_1W` must not be accepted at the Position Update upload endpoint.

**Explicit Non-Goals:**
- Do not change monitoring slot handling.
- Do not change how Position Update history is loaded.
- Do not change WAIT Update logic.

**Acceptance Criteria:**
- Position Update submission with Orderbook only → succeeds; context contains 1 evidence reference.
- Position Update submission with Orderbook + Broker Flow → succeeds; context contains 2 evidence references.
- Position Update submission without Orderbook → `MissingRequiredEvidenceError`.
- Observation facts derived from Orderbook only, not Broker Flow.
- Monitoring slots work identically to before.
- Broker Flow cannot attach as generic session-level evidence or to another Position Update observation.

**Focused Verification / Tests:**
- Unit test: `_position_update_evidence` with Orderbook only → 1 evidence reference.
- Unit test: `_position_update_evidence` with Orderbook + Broker Flow → 2 evidence references.
- Unit test: `_position_update_evidence` without Orderbook → `MissingRequiredEvidenceError`.
- Regression: Existing Position Update tests pass unchanged (Orderbook only, all monitoring slots).

**STOP / BLOCKED Conditions:**
- Same as EE5.

---

## Phase F: Gemini Prompts

### EE7 — Update Initial Analysis Gemini Prompt for Foreign Flow Interpretation

**Objective:** Update `prompts/rebuild/initial_analysis.md` to instruct Gemini to receive four images, identify the fourth as Foreign Flow 1W, and evaluate it according to the PRD's specified behavioral contract.

**Authoritative Source Lock:**
- PRD Section 6.1: Initial Analysis Prompt requirements
- PRD Section 7: Gemini reasoning guardrails
- `docs/evidence-expansion/TradePilot_AI_Evidence_Expansion_Gemini_Prompt_Contract.md` — INITIAL_ANALYSIS section

**Scope:**
- Update `prompts/rebuild/initial_analysis.md`:
  - Add `foreign_flow_1w` to the Inputs section (fourth image).
  - Add an Image Role for the fourth image: "Foreign Flow 1W screenshot: assess foreign accumulation/distribution over the recent week."
  - Add Foreign Flow interpretation instructions:
    - Classify as `ACCUMULATION`, `NEUTRAL`, or `DISTRIBUTION`.
    - Evaluate consistency across visible days, magnitude, price-flow relationship, confirmation/divergence.
    - Do not treat a single large buying day as automatically bullish without evaluating preceding days.
    - State the limitation clearly when the image is unreadable.
  - Add the guardrails from PRD Section 7 relevant to Foreign Flow.
  - Update the Output Contract section to reference `foreign_flow_analysis` as a required schema field.
- Update the schema field reference list to include `foreign_flow_analysis`.
- Do NOT change existing field references (summary, orderbook_analysis, etc.).

**Scope Diff:**
- Current: Three images, no flow analysis instructions.
- Required: Four images, Foreign Flow interpretation required.
- Behaviors unchanged: All existing analysis instructions remain.

**Dependencies:** EE4 (context builder must pass FOREIGN_FLOW_1W before prompt is deployed).

**Repository Areas / Expected Files:**
- `prompts/rebuild/initial_analysis.md`

**Implementation Requirements:**
- Prompt must be consistent with `TradePilot_AI_Evidence_Expansion_Gemini_Prompt_Contract.md`.
- Prompt must preserve all existing instructions and output field references.
- No new analysis type or new schema is created — `foreign_flow_analysis` is a new field within the existing `INITIAL_ANALYSIS` schema contract (see EE9).

**Explicit Non-Goals:**
- Do not change WAIT Update or Position Update prompts here.
- Do not change the JSON schema file here (EE9 covers that).

**Acceptance Criteria:**
- Prompt references four images with correct roles.
- Prompt instructs Gemini to classify Foreign Flow as `ACCUMULATION`, `NEUTRAL`, or `DISTRIBUTION`.
- Prompt includes all five evaluation dimensions from the PRD.
- Prompt includes the one-day trap prevention instruction.
- Prompt includes the unreadable-evidence instruction.
- All existing prompt instructions remain.

**Focused Verification / Tests:**
- Review test: Read the updated prompt and verify all PRD Section 6.1 requirements are covered.
- Prompt loader test: `prompt_loader` can still load `initial_analysis` without error.
- Regression: `test_prompt_loader.py` passes.

**STOP / BLOCKED Conditions:**
- The PRD requires a behavior that conflicts with the existing advisory-only prompt framework.

---

### EE8 — Update WAIT Update and Position Update Gemini Prompts for Broker Flow Interpretation

**Objective:** Update `prompts/rebuild/wait_update.md` and `prompts/rebuild/position_update.md` to conditionally instruct Gemini to interpret Broker Flow 1D when it is present.

**Authoritative Source Lock:**
- PRD Sections 6.2, 6.3: WAIT Update and Position Update prompt requirements
- PRD Section 7: Gemini reasoning guardrails
- `docs/evidence-expansion/TradePilot_AI_Evidence_Expansion_Gemini_Prompt_Contract.md` — WAIT_UPDATE and POSITION_UPDATE sections

**Scope:**
- Update `prompts/rebuild/wait_update.md`:
  - Add a conditional section: "If a Broker Flow 1D image is supplied as the second image..."
  - Instruct Gemini to classify visible broker activity as `ACCUMULATION`, `NEUTRAL`, or `DISTRIBUTION`.
  - Instruct Gemini to assess confirmation/weakening of the WAIT thesis.
  - Add relevant guardrails: broker codes do not prove identity; one-day flow is noisy; do not invent values.
  - Update the Inputs section to note that a second image (Broker Flow 1D) may optionally be present.
  - Update the Output Contract to reference `broker_flow_analysis` as a conditional field.
- Update `prompts/rebuild/position_update.md`:
  - Same pattern: conditional second image, ACCUMULATION/NEUTRAL/DISTRIBUTION, accumulation-vs-distribution assessment, risk implication.
  - Update the Inputs section and Output Contract accordingly.

**Scope Diff:**
- Current: One image (Orderbook) for both WAIT and Position Updates; no flow instructions.
- Required: Conditionally one or two images; Broker Flow instructions apply when the second image is present.
- Behaviors unchanged: When Broker Flow is absent, all existing prompt analysis instructions apply exactly as before.

**Dependencies:** EE5, EE6.

**Repository Areas / Expected Files:**
- `prompts/rebuild/wait_update.md`
- `prompts/rebuild/position_update.md`

**Implementation Requirements:**
- When Broker Flow is absent, the prompts must not hallucinate Broker Flow commentary.
- The conditional section must be clearly delimited so Gemini does not produce `broker_flow_analysis` output when no second image was provided.
- All existing prompt sections must remain intact.

**Explicit Non-Goals:**
- Do not change the Initial Analysis prompt.
- Do not require Broker Flow to be present.

**Acceptance Criteria:**
- WAIT Update prompt correctly describes optional second image and conditional analysis.
- Position Update prompt correctly describes optional second image and conditional analysis.
- Both prompts include broker code guardrails and one-day noise warning.
- Both prompts instruct Gemini not to invent values when image is unreadable.
- Existing prompt instructions remain unchanged.

**Focused Verification / Tests:**
- Review test: Verify all PRD Section 6.2/6.3 requirements are covered.
- Prompt loader test: Both updated prompts load without error.
- Regression: `test_prompt_loader.py` passes.

**STOP / BLOCKED Conditions:**
- The prompt architecture does not support conditional analysis sections.

---

## Phase G: Structured Output and Schema

### EE9 — Extend Gemini Response Schemas for Flow Analysis Fields

**Objective:** Add `foreign_flow_analysis` to the Initial Analysis JSON schema. Add `broker_flow_analysis` to the WAIT Update and Position Update JSON schemas. All new fields must be backward compatible.

**Authoritative Source Lock:**
- PRD Sections 8.1, 8.2, 8.3: Analysis output contract changes
- `docs/evidence-expansion/TradePilot_AI_Evidence_Expansion_Output_Contract.md`

**Scope:**
- **`schemas/rebuild/v1/initial_analysis.schema.json`**:
  - Add `foreign_flow_analysis` as a required object with at minimum:
    - `assessment` (string, enum: `ACCUMULATION`, `NEUTRAL`, `DISTRIBUTION`)
    - `analysis` (string, Indonesian)
  - Preserve `additionalProperties: false`; explicitly declare `foreign_flow_analysis` in the existing schema and keep its nested object explicit and strict.
  - Add `foreign_flow_analysis` to the `required` array.
- **`schemas/rebuild/v1/wait_update.schema.json`**:
  - Add `broker_flow_analysis` as an optional (nullable) object:
    - `assessment` (string, enum: `ACCUMULATION`, `NEUTRAL`, `DISTRIBUTION`)
    - `analysis` (string, Indonesian)
  - Preserve `additionalProperties: false`; explicitly declare the property and keep its nested object explicit and strict.
  - Do NOT add to `required` array — it is conditional.
- **`schemas/rebuild/v1/position_update.schema.json`**:
  - Same as WAIT Update: add `broker_flow_analysis` as optional/nullable while preserving `additionalProperties: false` and an explicit, strict nested object.

**Scope Diff:**
- Current: Schemas have `additionalProperties: false` and no flow fields.
- Required: New fields added with minimum extension; backward compatibility maintained.
- Behaviors unchanged: All existing required fields remain. `foreign_flow_analysis` is required for new Initial Analysis generation-time schema validation; historical persisted records lacking it remain readable through backward-compatible read/render behavior without backfill.

**Dependencies:** EE7, EE8.

**Repository Areas / Expected Files:**
- `schemas/rebuild/v1/initial_analysis.schema.json`
- `schemas/rebuild/v1/wait_update.schema.json`
- `schemas/rebuild/v1/position_update.schema.json`

**Implementation Requirements:**
- `foreign_flow_analysis` must be required for `INITIAL_ANALYSIS` (because the evidence is required).
- `broker_flow_analysis` must be optional/nullable for `WAIT_UPDATE` and `POSITION_UPDATE`.
- Historical `processed_response` JSONB records without flow fields must remain readable through backward-compatible read/render behavior; do not make `foreign_flow_analysis` optional in the new schema or backfill historical records.
- Schema validation in `response_validator.py` and `schema_validation` must be confirmed to use the same schema file path — no separate validation logic is to be added.

**Explicit Non-Goals:**
- Do not create new schema files.
- Do not backfill historical AI analysis records.
- Do not change `AnalysisRequestV2` database columns.

**Acceptance Criteria:**
- `initial_analysis.schema.json` contains `foreign_flow_analysis` as a required object.
- `wait_update.schema.json` contains `broker_flow_analysis` as an optional/nullable field.
- `position_update.schema.json` contains `broker_flow_analysis` as an optional/nullable field.
- All existing required fields remain in all three schemas.
- Schema validation tests pass with the new fields.
- Historical records without the new fields do not cause schema validation errors on read (backward-compatible read path).

**Focused Verification / Tests:**
- Schema test: Validate a sample Initial Analysis JSON with `foreign_flow_analysis` → valid.
- Schema test: Validate a sample Initial Analysis JSON without `foreign_flow_analysis` → invalid (it is required).
- Schema test: Validate a sample WAIT Update JSON with `broker_flow_analysis` → valid.
- Schema test: Validate a sample WAIT Update JSON without `broker_flow_analysis` → valid (it is optional).
- Schema test: Validate a sample historical WAIT Update JSON (no `broker_flow_analysis`) → valid.
- Regression: `test_schemas.py`, `test_json_schema_validation.py` pass.

**STOP / BLOCKED Conditions:**
- The existing schemas cannot be extended by weakening `additionalProperties: false`; new properties must be declared explicitly and historical compatibility must be handled by the read/render path.

---

## Phase H: Dashboard and UI

### EE10 — Add Foreign Flow Upload Control to Initial Analysis Form

**Objective:** Add a required Foreign Flow 1W upload control to the Initial Analysis (Initial Evidence) form in the frontend.

**Authoritative Source Lock:**
- PRD Section 10: Dashboard requirements
- PRD Section 17: UI/UX principles
- `.agent-skills/tradepilot-evidence-expansion-ui/SKILL.md`

**Scope:**
- Add one required upload control labeled **"Foreign Flow — 1W"** to the Initial Evidence upload form.
- Reuse the existing upload component/pattern already used for Orderbook, Chart 3M, Chart 6M.
- Validation: submission must fail with a clear error message if the Foreign Flow field is not provided.
- After upload, display the evidence type label consistent with existing evidence display.
- Mobile-first: single-column layout.

**Scope Diff:**
- Current: Initial Evidence form has 3 upload controls.
- Required: Initial Evidence form has 4 upload controls (Foreign Flow is the fourth).
- Behaviors unchanged: Existing 3 controls remain required with unchanged behavior.

**Dependencies:** EE3 (backend must accept the upload).

**Repository Areas / Expected Files:**
- `frontend/src/features/trade-workspace/` — Initial Analysis form component
- `frontend/src/features/trade-workspace/types.ts` — Evidence type definitions if used in frontend
- `frontend/src/features/trade-workspace/workspace.tsx` or equivalent initial evidence form

**Implementation Requirements:**
- Reuse the existing upload component. Do not design a new one.
- The evidence type sent to the backend must be `FOREIGN_FLOW_1W` (exact string).
- The field must be clearly labeled "Foreign Flow — 1W".
- Required validation: form must not be submittable if this field is missing.

**Explicit Non-Goals:**
- Do not add BROKER_FLOW_1D to the Initial Analysis form.
- Do not redesign the form layout beyond adding the new control.
- Do not add tooltip, modal, or OCR feedback.

**Acceptance Criteria:**
- "Foreign Flow — 1W" upload control appears in the Initial Evidence form.
- Attempting to submit without it shows a clear error.
- Uploading a valid image and submitting succeeds.
- Existing three upload controls work unchanged.

**Focused Verification / Tests:**
- Component test: Foreign Flow upload control is rendered.
- Component test: Submit without Foreign Flow → validation error visible.
- Component test: Submit with all 4 → no validation error.
- Regression: Existing evidence upload component tests pass.

**STOP / BLOCKED Conditions:**
- The backend EE3 changes are not yet deployed.
- The existing upload component cannot be parameterized with a new evidence type.

---

### EE11 — Add Optional Broker Flow Upload Control to WAIT Update and Position Update Forms

**Objective:** Add an optional Broker Flow 1D upload control to both the WAIT Update form and the Position Update form.

**Authoritative Source Lock:**
- PRD Sections 10, 17: Dashboard and UI requirements

**Scope:**
- Add one optional upload control labeled **"Broker Flow — 1D (Optional)"** to the WAIT Update form.
- Add one optional upload control labeled **"Broker Flow — 1D (Optional)"** to the Position Update form.
- Both controls: optional — form must remain submittable when they are absent.
- Reuse the existing upload pattern.
- When upload succeeds, display the evidence type label "Broker Flow 1D".

**Scope Diff:**
- Current: WAIT Update form has 1 upload control (Orderbook); Position Update form has 1 upload control (Orderbook).
- Required: Both forms have 2 upload controls (Orderbook required, Broker Flow optional).
- Behaviors unchanged: Existing Orderbook controls remain required; monitoring slots unchanged.

**Dependencies:** EE5 (WAIT backend), EE6 (Position backend).

**Repository Areas / Expected Files:**
- `frontend/src/features/trade-workspace/wait-update.tsx`
- `frontend/src/features/trade-workspace/position-update.tsx`

**Implementation Requirements:**
- "Broker Flow — 1D (Optional)" must be clearly labeled as optional.
- If Broker Flow upload fails: allow retry; Orderbook evidence must not be lost; form must not submit with a broken Broker Flow reference.
- The evidence type sent to the backend must be `BROKER_FLOW_1D`.

**Explicit Non-Goals:**
- Do not add FOREIGN_FLOW_1W to WAIT or Position Update forms.
- Do not redesign form layout beyond adding the new control.

**Acceptance Criteria:**
- "Broker Flow — 1D (Optional)" upload control appears in both forms.
- Forms can be submitted with only Orderbook.
- Forms submit Broker Flow evidence when provided.
- Existing Orderbook controls and monitoring slot controls work unchanged.

**Focused Verification / Tests:**
- Component test: Optional Broker Flow control renders in WAIT Update form.
- Component test: Optional Broker Flow control renders in Position Update form.
- Component test: WAIT Update can be submitted without Broker Flow.
- Component test: WAIT Update can be submitted with Broker Flow.
- Regression: Existing WAIT Update and Position Update form tests pass.

**STOP / BLOCKED Conditions:**
- EE5 or EE6 backend changes are not yet deployed.

---

### EE11b — Render Analisa Foreign Flow in Initial Analysis Dashboard Output

**Objective:** Display the `Analisa Foreign Flow` section in the dashboard whenever an Initial Analysis result is shown.

**Authoritative Source Lock:**
- PRD Section 8.1, 19: Output and recommended presentation
- `.agent-skills/tradepilot-analysis-output-contract/SKILL.md`

**Scope:**
- In `initial-analysis-view.tsx`, add rendering of the `foreign_flow_analysis` field from `processed_response`.
- Display the section as "Analisa Foreign Flow" in the correct position per PRD Section 19:
  1. Ringkasan Hari Ini / summary
  2. Analisa Orderbook
  3. Analisa Chart
  4. **Analisa Foreign Flow** ← new
  5. Support/Resistance
  6. Entry ... (remainder unchanged)
- Show `assessment` and `analysis` sub-fields.
- The section is always present for Initial Analysis results (because `FOREIGN_FLOW_1W` is required).
- Follow existing rendering conventions for section containers and typography.

**Dependencies:** EE9 (schema defines the field), EE10 (frontend can upload).

**Repository Areas / Expected Files:**
- `frontend/src/features/analysis/initial-analysis-view.tsx`

**Explicit Non-Goals:**
- Do not change rendering of any other section.
- Do not render `Analisa Broker Flow` here (EE11c covers that).

**Acceptance Criteria:**
- Initial Analysis result shows "Analisa Foreign Flow" section.
- Assessment value (`ACCUMULATION` / `NEUTRAL` / `DISTRIBUTION`) is displayed.
- Analysis text is displayed in Indonesian.
- Section appears in the correct position.
- Historical Initial Analysis results without the field do not crash the renderer (graceful fallback).

**Focused Verification / Tests:**
- Component test: `initial-analysis-view.tsx` with `foreign_flow_analysis` in response → renders section.
- Component test: Without `foreign_flow_analysis` → renders gracefully without crash.

---

### EE11c — Render Conditional Analisa Broker Flow in WAIT and Position Update Dashboard Output

**Objective:** Display `Analisa Broker Flow` only when a WAIT Update or Position Update result contains `broker_flow_analysis` from a Broker Flow-enabled submission.

**Authoritative Source Lock:**
- PRD Sections 8.2, 8.3, 19: Output contract and recommended presentation

**Scope:**
- In `watching-update-view.tsx` (or equivalent), add conditional rendering of `broker_flow_analysis` when present.
- In `open-position-update-view.tsx`, add conditional rendering of `broker_flow_analysis` when present.
- When `broker_flow_analysis` is null/absent: do not show the section, or show a minimal "not available" indicator per existing dashboard convention.
- When present: show "Analisa Broker Flow" with `assessment` and `analysis`.

**Dependencies:** EE9.

**Repository Areas / Expected Files:**
- `frontend/src/features/analysis/watching-update-view.tsx`
- `frontend/src/features/analysis/open-position-update-view.tsx`

**Acceptance Criteria:**
- WAIT Update with Broker Flow → "Analisa Broker Flow" section is visible.
- WAIT Update without Broker Flow → section is absent.
- Position Update with Broker Flow → "Analisa Broker Flow" section is visible.
- Position Update without Broker Flow → section is absent.
- Existing sections unchanged.

**Focused Verification / Tests:**
- Component test: WAIT Update result with `broker_flow_analysis` → renders section.
- Component test: WAIT Update result without `broker_flow_analysis` → no section rendered.
- Component test: Position Update result with `broker_flow_analysis` → renders section.
- Component test: Position Update result without `broker_flow_analysis` → no section rendered.

---

## Phase I: Focused Tests

### EE12 — Evidence Expansion Feature Gate Verification

**Objective:** Run the complete acceptance test matrix from the PRD and perform focused regression verification of all invariants.

**Authoritative Source Lock:**
- PRD Section 18: Acceptance Criteria
- `.agent-skills/tradepilot-evidence-expansion-testing/SKILL.md`

**Scope:**
- Run all focused acceptance tests defined per phase above.
- Verify all PRD Section 18 acceptance criteria explicitly (PASS / FAIL / NOT VERIFIED per criterion).
- Verify lifecycle invariants: no new statuses, no new analysis types, BUY/WAIT/SKIP/CLOSE unchanged.
- Verify Initial Evidence immutability and exact WAIT/Position Update Broker Flow observation association.
- Verify historical sessions load correctly.
- Verify Gemini remains the only provider.
- Verify no new routes or navigation items were introduced.
- Use mocked Gemini for all evidence composition tests; real Gemini calls only if explicitly authorized.

**Dependencies:** All EE1 through EE11c tasks completed.

**Repository Areas / Expected Files:**
- `backend/tests/trade_workspace/` — all evidence and context builder tests
- `frontend/src/features/` — all updated component tests

**Acceptance Criteria (from PRD Section 18):**
- [ ] Initial Analysis form has Foreign Flow 1W upload.
- [ ] Foreign Flow 1W is required.
- [ ] Initial Analysis cannot be submitted without Foreign Flow 1W.
- [ ] Gemini receives the Foreign Flow image.
- [ ] Gemini explicitly analyzes Foreign Flow.
- [ ] Dashboard displays `Analisa Foreign Flow` section.
- [ ] Existing Orderbook, Chart 3M, Chart 6M behavior continues.
- [ ] WAIT Update supports optional Broker Flow 1D upload.
- [ ] Orderbook remains required for WAIT Update.
- [ ] WAIT Update submits without Broker Flow.
- [ ] When Broker Flow supplied, Gemini receives it.
- [ ] Dashboard displays `Analisa Broker Flow` when evidence present.
- [ ] Existing WAIT behavior unchanged.
- [ ] Position Update supports optional Broker Flow 1D upload.
- [ ] Orderbook remains required for Position Update.
- [ ] Position Update submits without Broker Flow.
- [ ] Dashboard displays `Analisa Broker Flow` when evidence present.
- [ ] Existing monitoring slots unchanged.
- [ ] Existing session lifecycle unchanged.
- [ ] Existing analysis types unchanged.
- [ ] Existing BUY/WAIT/SKIP/CLOSE actions unchanged.
- [ ] Historical sessions remain readable.
- [ ] Gemini remains the only AI provider.

**Focused Verification / Tests:**
- All focused tests from EE2 through EE11c.
- Backend: `pytest backend/tests/trade_workspace/ -k "evidence or context_builder or analysis"`.
- Frontend: component tests for modified components.
- No full test suite expansion.
- No real Gemini calls unless explicitly authorized.

**STOP / BLOCKED Conditions:**
- Any acceptance criterion in PRD Section 18 fails.
- Any lifecycle invariant is violated.
- Historical sessions are unreadable.

---

## Task Summary

| Task ID | Title | Phase | Dependencies |
|---|---|---|---|
| EE1 | Confirm Authoritative Sources and Repository Baseline | A — Source Lock | None |
| EE2 | Add FOREIGN_FLOW_1W and BROKER_FLOW_1D Evidence Types | B — Evidence Types | EE1 |
| EE3 | Update Initial Analysis Evidence Upload API | C — Initial Analysis | EE2 |
| EE4 | Update Initial Analysis Submission to Require FOREIGN_FLOW_1W | C — Initial Analysis | EE3 |
| EE5 | Update WAIT Update to Optionally Accept BROKER_FLOW_1D | D — WAIT Update | EE2 |
| EE6 | Update Position Update to Optionally Accept BROKER_FLOW_1D | E — Position Update | EE2 |
| EE7 | Update Initial Analysis Gemini Prompt | F — Prompts | EE4 |
| EE8 | Update WAIT Update and Position Update Gemini Prompts | F — Prompts | EE5, EE6 |
| EE9 | Extend Gemini Response Schemas | G — Schema | EE7, EE8 |
| EE10 | Add Foreign Flow Upload Control (Initial Analysis Form) | H — UI | EE3 |
| EE11 | Add Optional Broker Flow Upload Control (WAIT and Position Forms) | H — UI | EE5, EE6 |
| EE11b | Render Analisa Foreign Flow in Initial Analysis Output | H — UI | EE9, EE10 |
| EE11c | Render Conditional Analisa Broker Flow in WAIT/Position Output | H — UI | EE9 |
| EE12 | Feature Gate Verification | I — Testing | EE1–EE11c |

---

## Prohibited Changes (All Tasks)

No task in this plan may:
- Introduce a new session lifecycle status.
- Introduce a new analysis type.
- Introduce a new user decision action.
- Change the Gemini provider or add a second provider.
- Create a new route, navigation item, or page.
- Redesign unrelated UI components.
- Backfill or migrate historical AI analysis records.
- Add OCR or automatic image-content validation.
- Change the queue architecture.
