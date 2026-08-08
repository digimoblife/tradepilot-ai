# TradePilot AI — Evidence Expansion Implementation Impact Audit

**Feature:** Foreign Flow & Broker Flow Evidence Expansion
**Authoritative Source:** `docs/evidence-expansion/TradePilot_AI_PRD_Foreign_Flow_Broker_Flow_Evidence_Expansion.md`
**Document Type:** Technical Impact Audit & Repository Mapping
**Status:** Ready for Product Owner Review

---

## Purpose

This document provides a detailed, evidence-based audit of the TradePilot AI repository to identify the exact files, database structures, prompt templates, schemas, frontend components, and tests affected by the Evidence Expansion feature.

---

## 1. Area-by-Area Repository Impact Audit

### 1.1 Evidence Type Definitions / Enums
- **Repository Path:** `backend/app/trade_workspace/models/evidence_upload.py` (`EvidenceUploadV2Type`), `backend/app/models/enums.py` (`EvidenceType`)
- **Current Responsibility:** Defines supported evidence type enums. Rebuild persistence uses `EvidenceUploadV2Type` (`ORDERBOOK`, `CHART_3_MONTH`, `CHART_6_MONTH`).
- **Evidence Expansion Impact:** `EvidenceUploadV2Type` must be extended with `FOREIGN_FLOW_1W` and `BROKER_FLOW_1D`.
- **Expected Change:** Add two new enum values to `EvidenceUploadV2Type`.
- **Risk Level:** LOW.
- **Backward Compatibility Concern:** None; existing enum values remain untouched.
- **Related PRD Requirement:** PRD §12
- **Related Task Plan Task:** EE2

### 1.2 Database Models and Migrations
- **Repository Path:** `backend/app/trade_workspace/models/evidence_upload.py` (`EvidenceUploadV2`), `backend/migrations/versions/9d5e7f1a3c2b_p33_evidence_uploads_v2.py`
- **Current Responsibility:** DB model and PostgreSQL migration for `evidence_uploads_v2` table. Uses native PostgreSQL enum `evidence_upload_v2_type_enum`.
- **Evidence Expansion Impact:** PostgreSQL enum `evidence_upload_v2_type_enum` in database needs `FOREIGN_FLOW_1W` and `BROKER_FLOW_1D`.
- **Expected Change:** Add new Alembic migration containing `ALTER TYPE evidence_upload_v2_type_enum ADD VALUE 'FOREIGN_FLOW_1W';` and `ALTER TYPE evidence_upload_v2_type_enum ADD VALUE 'BROKER_FLOW_1D';`.
- **Risk Level:** LOW.
- **Backward Compatibility Concern:** Existing table records remain valid; enum addition is non-destructive.
- **Related PRD Requirement:** PRD §12
- **Related Task Plan Task:** EE2

### 1.3 Evidence Upload API Routes
- **Repository Path:** `backend/app/trade_workspace/api/routes/trade_sessions.py`
- **Current Responsibility:** Endpoints for session creation, initial evidence upload (`POST /initial-analysis/upload-evidence`), WAIT update submission (`POST /wait-updates`), Position update submission (`POST /position-updates`).
- **Evidence Expansion Impact:**
  - Initial evidence upload route must accept `FOREIGN_FLOW_1W`.
  - WAIT update upload route must accept optional `BROKER_FLOW_1D`.
  - Position update upload route must accept optional `BROKER_FLOW_1D`.
- **Expected Change:** Extend evidence type validation/allowlists in these route handlers.
- **Risk Level:** MEDIUM.
- **Backward Compatibility Concern:** Submissions without optional `BROKER_FLOW_1D` must continue to succeed.
- **Related PRD Requirement:** PRD §5.1, §5.2, §5.3, §13
- **Related Task Plan Task:** EE3, EE5, EE6

### 1.4 Initial Evidence Validation Logic
- **Repository Path:** `backend/app/trade_workspace/ai/context_builder.py` (`_load_initial_evidence`)
- **Current Responsibility:** `_load_initial_evidence` hardcodes `required_types = (ORDERBOOK, CHART_3_MONTH, CHART_6_MONTH)`.
- **Evidence Expansion Impact:** Must add `EvidenceUploadV2Type.FOREIGN_FLOW_1W` to `required_types`.
- **Expected Change:** Update tuple to four required evidence types.
- **Risk Level:** MEDIUM.
- **Backward Compatibility Concern:** Initial Analysis submission fails if `FOREIGN_FLOW_1W` is missing (intended new behavior).
- **Related PRD Requirement:** PRD §5.1, §13
- **Related Task Plan Task:** EE4

### 1.5 WAIT Update Upload / Validation
- **Repository Path:** `backend/app/trade_workspace/ai/context_builder.py` (`_wait_update_evidence`)
- **Current Responsibility:** Enforces `len(linked_evidence) == 1` (Orderbook only).
- **Evidence Expansion Impact:** Must allow `len(linked_evidence)` to be 1 (Orderbook) or 2 (Orderbook + Broker Flow).
- **Expected Change:** Relax check to allow optional `BROKER_FLOW_1D` when linked to same request. Orderbook remains strictly required.
- **Risk Level:** MEDIUM.
- **Backward Compatibility Concern:** Single Orderbook submission must remain 100% valid.
- **Related PRD Requirement:** PRD §5.2, §13
- **Related Task Plan Task:** EE5

### 1.6 Position Update Upload / Validation
- **Repository Path:** `backend/app/trade_workspace/ai/context_builder.py` (`_position_update_evidence`)
- **Current Responsibility:** Enforces `len(linked_evidence) == 1` (Orderbook only).
- **Evidence Expansion Impact:** Must allow `len(linked_evidence)` to be 1 or 2.
- **Expected Change:** Same pattern as WAIT Update: Orderbook required, Broker Flow optional.
- **Risk Level:** MEDIUM.
- **Backward Compatibility Concern:** Single Orderbook submission remains valid.
- **Related PRD Requirement:** PRD §5.3, §13
- **Related Task Plan Task:** EE6

### 1.7 Monitoring Slot Handling
- **Repository Path:** `backend/app/trade_workspace/models/analysis_request.py` (`AnalysisRequestV2ObservationPeriod`)
- **Current Responsibility:** Enums `MORNING`, `MIDDAY`, `AFTERNOON`.
- **Evidence Expansion Impact:** None. Monitoring slot handling is untouched by Evidence Expansion.
- **Expected Change:** None.
- **Risk Level:** LOW (NO CHANGE).
- **Backward Compatibility Concern:** None.
- **Related PRD Requirement:** PRD §5.3
- **Related Task Plan Task:** EE6

### 1.8 Analysis Request Construction (Context Builder)
- **Repository Path:** `backend/app/trade_workspace/ai/context_builder.py` (`RebuildAnalysisContextBuilder`)
- **Current Responsibility:** Gathers session facts, evidence references, historical analysis summaries, position facts, and constructs `AnalysisContext`.
- **Evidence Expansion Impact:** Context builder must include `FOREIGN_FLOW_1W` image in Initial Analysis context, and optional `BROKER_FLOW_1D` in WAIT/Position context.
- **Expected Change:** Pass expanded evidence tuples to `AnalysisContext`.
- **Risk Level:** MEDIUM.
- **Backward Compatibility Concern:** Ensure historical analysis summary loading remains unaffected.
- **Related PRD Requirement:** PRD §5.1, §5.2, §5.3, §6.1, §6.2, §6.3
- **Related Task Plan Task:** EE4, EE5, EE6

### 1.9 Gemini Prompt Builders / Templates
- **Repository Path:** `prompts/rebuild/initial_analysis.md`, `prompts/rebuild/wait_update.md`, `prompts/rebuild/position_update.md`
- **Current Responsibility:** Markdown prompt templates loaded by `prompt_loader.py`.
- **Evidence Expansion Impact:**
  - `initial_analysis.md`: Add 4th image role (Foreign Flow 1W) and foreign flow reasoning rules.
  - `wait_update.md`: Add conditional 2nd image role (Broker Flow 1D) and broker flow rules.
  - `position_update.md`: Add conditional 2nd image role (Broker Flow 1D) and broker flow rules.
- **Expected Change:** Update text in all three Markdown files.
- **Risk Level:** MEDIUM.
- **Backward Compatibility Concern:** Prompts must handle missing optional images without failing or hallucinating.
- **Related PRD Requirement:** PRD §6.1, §6.2, §6.3, §7
- **Related Task Plan Task:** EE7, EE8

### 1.10 Gemini Image Attachment Composition
- **Repository Path:** `backend/app/trade_workspace/ai/gemini_adapter.py` (`RebuildGeminiAdapter`)
- **Current Responsibility:** Encodes evidence images into Gemini API inline content parts.
- **Evidence Expansion Impact:** None directly to code logic. Adapter already iterates dynamically over all `EvidenceReference` items in `context.evidence`.
- **Expected Change:** None (existing iteration automatically handles 4 images for Initial Analysis and 2 images for WAIT/Position Updates).
- **Risk Level:** LOW.
- **Backward Compatibility Concern:** None.
- **Related PRD Requirement:** PRD §6.1, §6.2, §6.3
- **Related Task Plan Task:** EE4, EE5, EE6

### 1.11 Structured Response Schemas
- **Repository Path:** `schemas/rebuild/v1/initial_analysis.schema.json`, `schemas/rebuild/v1/wait_update.schema.json`, `schemas/rebuild/v1/position_update.schema.json`
- **Current Responsibility:** Defines structured JSON schemas for Gemini response validation.
- **Evidence Expansion Impact:**
  - `initial_analysis.schema.json`: Add required `foreign_flow_analysis` object for newly generated Initial Analysis output.
  - `wait_update.schema.json`: Add optional/nullable `broker_flow_analysis` object.
  - `position_update.schema.json`: Add optional/nullable `broker_flow_analysis` object.
- **Expected Change:** Update JSON schema files in-place.
- **Risk Level:** LOW.
- **Backward Compatibility Concern:** `foreign_flow_analysis` is required in the new Initial Analysis generation schema. `broker_flow_analysis` must not be in the WAIT or Position Update `required` arrays. Historical persisted records lacking either field remain readable through backward-compatible rendering/read behavior without JSONB backfill.
- **Related PRD Requirement:** PRD §8.1, §8.2, §8.3
- **Related Task Plan Task:** EE9

### 1.12 Response Validation / Parsing
- **Repository Path:** `backend/app/trade_workspace/ai/response_validator.py`
- **Current Responsibility:** Validates JSON string returned by Gemini against `schemas/rebuild/v1/` JSON schemas using `jsonschema`.
- **Evidence Expansion Impact:** Validator logic requires no code change; it dynamically loads updated JSON schema files.
- **Expected Change:** None to Python code; schema file update handles validation automatically.
- **Risk Level:** LOW.
- **Backward Compatibility Concern:** None.
- **Related PRD Requirement:** PRD §8.1, §8.2, §8.3
- **Related Task Plan Task:** EE9

### 1.13 Persistence of AI Analysis Results
- **Repository Path:** `backend/app/trade_workspace/models/analysis_request.py` (`AnalysisRequestV2`)
- **Current Responsibility:** Stores raw and processed JSON response in `processed_response` JSONB column.
- **Evidence Expansion Impact:** JSONB natively supports storing the new `foreign_flow_analysis` and `broker_flow_analysis` fields.
- **Expected Change:** None to DB model or column definitions.
- **Risk Level:** LOW.
- **Backward Compatibility Concern:** `broker_flow_analysis` is optional for WAIT and Position Update outputs. `foreign_flow_analysis` is required for newly generated Initial Analysis output, while historical Initial Analysis JSONB may lack it and remains readable through the rendering/read path. No historical `processed_response` backfill is required.
- **Related PRD Requirement:** PRD §12, §15
- **Related Task Plan Task:** EE9

### 1.14 Initial Analysis Dashboard Renderer
- **Repository Path:** `frontend/src/features/analysis/initial-analysis-view.tsx`
- **Current Responsibility:** Renders Initial Analysis advisory sections.
- **Evidence Expansion Impact:** Must render new `"Analisa Foreign Flow"` section.
- **Expected Change:** Add section display logic with fallback check `if (data.foreign_flow_analysis)`.
- **Risk Level:** LOW.
- **Backward Compatibility Concern:** Must not crash on historical records where field is missing.
- **Related PRD Requirement:** PRD §8.1, §10, §19
- **Related Task Plan Task:** EE11b

### 1.15 WAIT Update Dashboard Renderer
- **Repository Path:** `frontend/src/features/analysis/watching-update-view.tsx`
- **Current Responsibility:** Renders WAIT Update advisory sections.
- **Evidence Expansion Impact:** Must conditionally render `"Analisa Broker Flow"` section when `broker_flow_analysis` is present.
- **Expected Change:** Add conditional section renderer `if (data.broker_flow_analysis)`.
- **Risk Level:** LOW.
- **Backward Compatibility Concern:** Hides section cleanly when field is missing/null.
- **Related PRD Requirement:** PRD §8.2, §10, §19
- **Related Task Plan Task:** EE11c

### 1.16 Position Update Dashboard Renderer
- **Repository Path:** `frontend/src/features/analysis/open-position-update-view.tsx`
- **Current Responsibility:** Renders Position Update advisory sections.
- **Evidence Expansion Impact:** Must conditionally render `"Analisa Broker Flow"` section when `broker_flow_analysis` is present.
- **Expected Change:** Add conditional section renderer `if (data.broker_flow_analysis)`.
- **Risk Level:** LOW.
- **Backward Compatibility Concern:** Hides section cleanly when field is missing/null.
- **Related PRD Requirement:** PRD §8.3, §10, §19
- **Related Task Plan Task:** EE11c

### 1.17 Upload UI Components
- **Repository Path:** `frontend/src/features/trade-workspace/` forms (`workspace.tsx`, `wait-update.tsx`, `position-update.tsx`)
- **Current Responsibility:** Manages file selection and upload for trade session evidence.
- **Evidence Expansion Impact:**
  - Initial evidence form adds "Foreign Flow — 1W" required field.
  - WAIT Update form adds "Broker Flow — 1D (Optional)" field.
  - Position Update form adds "Broker Flow — 1D (Optional)" field.
- **Expected Change:** Add file input fields reusing existing upload UI components.
- **Risk Level:** MEDIUM.
- **Backward Compatibility Concern:** Ensure existing Orderbook, Chart 3M, Chart 6M controls remain functional.
- **Related PRD Requirement:** PRD §10, §17
- **Related Task Plan Task:** EE10, EE11

### 1.18 Existing Focused Tests
- **Repository Path:** `backend/tests/trade_workspace/` (`test_context_builder.py`, `test_wait_update_context.py`, `test_position_update_context.py`, `test_response_validator.py`, `test_schemas.py`)
- **Current Responsibility:** Unit and integration tests for rebuild backend.
- **Evidence Expansion Impact:** Tests must be updated/added to cover:
  - 4-evidence Initial Analysis context construction.
  - Optional 2-evidence WAIT and Position Update context construction.
  - Validation of updated JSON schemas.
- **Expected Change:** Add new test functions and update existing fixture assertions.
- **Risk Level:** LOW.
- **Backward Compatibility Concern:** None.
- **Related PRD Requirement:** PRD §18
- **Related Task Plan Task:** EE1–EE12

---

## 2. Synthesis of Findings

1. **Explicitly NOT Impacted:**
   - Session lifecycle status machine (`TradeSessionV2Status`): no new statuses added.
   - Analysis types (`AnalysisRequestV2Type`): remains `INITIAL_ANALYSIS`, `WAIT_UPDATE`, `POSITION_UPDATE`.
   - Decision engine (`SessionDecisionV2Decision`): `BUY`, `WAIT`, `SKIP`, `CLOSE` remain unchanged.
   - AI Provider (`gemini-3.1-flash-lite`): remains sole provider.
   - Navigation and page routes: no new pages created.

2. **Existing Reusable Components:**
   - `RebuildGeminiAdapter` dynamically handles variable length image arrays.
   - Response validator dynamically uses JSON schemas without code changes.
   - Frontend file upload components can be reused by passing new labels and evidence type strings.

3. **Potential Hidden Coupling:**
   - `context_builder.py` hardcodes evidence count checks (`len(linked_evidence) == 1`). Changing these checks requires updating `test_wait_update_context.py` and `test_position_update_context.py`.

4. **Monitoring Slots:**
   - The authoritative rebuild contract uses `MORNING`, `MIDDAY`, `AFTERNOON`. Evidence Expansion does not modify these values.

5. **Migration Requirement:**
   - One database migration required to add `'FOREIGN_FLOW_1W'` and `'BROKER_FLOW_1D'` to `evidence_upload_v2_type_enum`.

6. **Task Plan Alignment:**
   - The task sequence in `TradePilot_AI_Evidence_Expansion_Detailed_Task_Plan.md` (EE1 through EE12) accurately reflects repository architecture and dependencies.
