# TradePilot Evidence Expansion UI

## Purpose

Define the minimal frontend changes required to support the Foreign Flow / Broker Flow Evidence Expansion feature without redesigning the product.

## When to Use

Use this skill for every frontend task that touches:
- Initial Analysis form (adding Foreign Flow upload);
- WAIT Update form (adding optional Broker Flow upload);
- Position Update form (adding optional Broker Flow upload);
- dashboard display of Foreign Flow or Broker Flow analysis sections.

Load `tradepilot-evidence-expansion-source-lock` and `tradepilot-ui-ux-implementation` together with this skill.

---

## Authoritative Source

> `docs/evidence-expansion/TradePilot_AI_PRD_Foreign_Flow_Broker_Flow_Evidence_Expansion.md` — Sections 10, 11, 17.

---

## Form Changes by Analysis Type

### Initial Analysis Form

**Required addition**: One new upload control for **Foreign Flow — 1W**.

**Rules**:
- Required field. Submission must fail if not provided.
- Label must be clear: **"Foreign Flow — 1W"** (so users understand a 1-week Foreign Flow screenshot is expected).
- Must be visually distinct from Orderbook, Chart 3M, and Chart 6M controls.
- Reuse existing upload interaction pattern — do not design a new upload mechanism.

**Preserved behavior**:
- Orderbook, Chart 3M, and Chart 6M upload controls remain required and unchanged.
- Existing validation and error behavior for those controls remains unchanged.

---

### WAIT Update Form

**Required addition**: One optional upload control for **Broker Flow — 1D (Optional)**.

**Rules**:
- Optional. Submission must still succeed if not provided.
- Label must be clear: **"Broker Flow — 1D (Optional)"**.
- Clearly marked as optional to avoid user confusion.
- Reuse existing upload interaction pattern.

**Preserved behavior**:
- Orderbook upload control remains required and unchanged.
- Existing WAIT Update form behavior and validation remain unchanged.

---

### Position Update Form

**Required addition**: One optional upload control for **Broker Flow — 1D (Optional)**.

**Rules**:
- Optional. Submission must still succeed if not provided.
- Label must be clear: **"Broker Flow — 1D (Optional)"**.
- Reuse existing upload interaction pattern.

**Preserved behavior**:
- Orderbook upload control remains required and unchanged.
- The authoritative monitoring slots (`MORNING`, `MIDDAY`, `AFTERNOON`) remain unchanged. Evidence Expansion does not modify monitoring slots.
- Existing Position Update form behavior and validation remain unchanged.

---

## Dashboard Display Rules

### Analisa Foreign Flow

- Display in all Initial Analysis results — it is always present because evidence is required.
- The section must be clearly visible in the analysis output.
- Follow the section order from the PRD (see `tradepilot-analysis-output-contract`).

### Analisa Broker Flow

- Display in WAIT Update and Position Update results **only when Broker Flow 1D evidence was attached to that specific update**.
- When Broker Flow evidence was not supplied, the section may be omitted or shown as unavailable per existing rendering conventions.
- Do not display `Analisa Broker Flow` when there is no Broker Flow evidence for that update.

---

## UI Implementation Rules

### Component Reuse

- Reuse the existing file upload component / upload interaction pattern for all new upload controls.
- Do not design or build a new upload component for flow evidence.

### Mobile-First

- All form changes must be designed for narrow mobile screens first.
- Single-column layout on mobile.
- Labels must appear above inputs.
- Touch-safe tap targets.
- No horizontal scrolling introduced.

### Evidence Labels

- After upload, display the evidence type clearly: **"Foreign Flow 1W"** or **"Broker Flow 1D"**.
- Consistent with how existing evidence labels (Orderbook, Chart 3M, Chart 6M) are displayed.

### Loading / Error / Feedback Conventions

- Preserve existing loading, error, and success feedback conventions.
- Optional Broker Flow upload failure: allow retry; must not lose required Orderbook evidence; must not submit with a broken reference.
- Do not introduce new modal flows, overlays, or interaction patterns unless already used by the existing UI.

### Validation Feedback

- Required field validation for `FOREIGN_FLOW_1W`: clear error message if missing on Initial Analysis submission.
- Optional field (`BROKER_FLOW_1D`): no error if absent; error only if upload is partially broken.

---

## Scope Boundaries

### What this task IS

- Add one required upload control to the Initial Analysis form.
- Add one optional upload control to the WAIT Update form.
- Add one optional upload control to the Position Update form.
- Conditionally display `Analisa Broker Flow` in the analysis output.
- Always display `Analisa Foreign Flow` in Initial Analysis output.

### What this task IS NOT

Do not:
- redesign any unrelated page or form;
- add new navigation items, routes, or pages;
- change routing or navigation structure;
- redesign the session list, session detail header, or timeline;
- add advanced image validation, preview, or OCR feedback;
- add tooltip, modal, or guided-upload flows unless the existing UI already uses them;
- change evidence display for existing evidence types (Orderbook, Charts);
- introduce responsive or layout changes to unrelated screens.

---

## BLOCKED Conditions

Return **BLOCKED** when:
- the required upload control cannot be added without a new backend API endpoint not yet implemented;
- adding the upload control requires changing lifecycle or evidence eligibility rules not yet approved;
- the existing upload component cannot support a new evidence type without redesigning the component itself;
- the dashboard output section cannot be conditionally rendered without a schema change not yet implemented.
- authoritative monitoring-slot requirements differ from repository behavior; do not silently follow the implementation.
