# TradePilot Analysis Output Contract — Evidence Expansion

## Purpose

Protect the structured Gemini response and dashboard analysis output while adding the new flow interpretation sections. Define the minimum compatible output changes required by the Evidence Expansion PRD.

## When to Use

Use this skill for every task that touches:
- Gemini response schema definitions;
- analysis output parsing and persistence;
- dashboard rendering of analysis results;
- output fields, sections, or structured JSON shapes for Initial Analysis, WAIT Update, or Position Update.

Load `tradepilot-evidence-expansion-source-lock` first.

---

## Authoritative Sources

- `docs/evidence-expansion/TradePilot_AI_PRD_Foreign_Flow_Broker_Flow_Evidence_Expansion.md` — Sections 8, 9, 19;
- `docs/rebuild/ANALYSIS_INPUT_CONTRACTS.md` — approved analysis types;
- the current structured-output schema — existing field structure and backward-compatible extension point.

---

## Output Changes by Analysis Type

### INITIAL_ANALYSIS Output

**Required addition**: A dedicated `Analisa Foreign Flow` section must be visible in the dashboard output.

**This section must summarize**:
- accumulation / neutral / distribution assessment;
- recent flow pattern observed;
- relationship between foreign flow direction and price direction;
- whether the flow confirms or weakens the technical thesis.

**Structured field** (if a JSON response schema is in use):

```
foreign_flow_assessment
```

Allowed values:
- `ACCUMULATION`
- `NEUTRAL`
- `DISTRIBUTION`

**Preservation rule**: All existing output fields for Initial Analysis must remain unchanged. The `Analisa Foreign Flow` section is an addition, not a replacement.

**Recommended section order** (from PRD Section 19):
1. Ringkasan Hari Ini
2. Analisa Orderbook
3. Analisa Chart
4. **Analisa Foreign Flow** ← new
5. Support / Resistance
6. Entry
7. Stop Loss
8. Target Profit
9. Confidence
10. Probability
11. Trading Plan
12. Penilaian AI

---

### WAIT_UPDATE Output

**Conditional addition**: `Analisa Broker Flow` must appear only when Broker Flow 1D evidence was supplied.

**When Broker Flow is supplied, this section must explain**:
- dominant visible broker behavior;
- accumulation / neutral / distribution assessment;
- whether it supports the current WAIT thesis;
- whether it materially changes confidence.

**When Broker Flow is absent**: the section may be omitted or displayed as unavailable according to the existing dashboard rendering convention. Do not require the section when evidence is not present.

**Preservation rule**: All existing WAIT Update output fields must remain unchanged.

---

### POSITION_UPDATE Output (Position Update)

**Conditional addition**: `Analisa Broker Flow` must appear only when Broker Flow 1D evidence was supplied.

**When Broker Flow is supplied, this section must explain**:
- whether accumulation is continuing;
- whether distribution is appearing;
- whether broker behavior confirms or conflicts with the Orderbook;
- whether risk to the open position has increased or decreased.

**When Broker Flow is absent**: the section may be omitted or displayed as unavailable. Do not require the section when evidence is not present.

**Preservation rule**: The existing Position Update decision framework must remain unchanged. All existing output fields must remain unchanged.

---

## Confidence and Probability Behavior

- New flow evidence **may** influence existing Confidence and Probability outputs.
- **No fixed arithmetic weighting** is required or permitted (e.g., no "+10% if ACCUMULATION").
- Agreement between flow evidence and other evidence may strengthen confidence.
- Conflict between flow evidence and other evidence must reduce confidence, not be ignored.
- Gemini determines confidence holistically from all evidence together.
- Do not create a new confidence framework or scoring system.

---

## Schema Extension Rules

If the repository currently uses a structured JSON response schema:

1. Make only the **minimum compatible extension** required by the PRD.
2. Add `foreign_flow_assessment` as a new optional or required field for `INITIAL_ANALYSIS` output — do not change existing fields.
3. Inspect the current structured-output schema and extend its existing contract minimally for `WAIT_UPDATE` and `POSITION_UPDATE`; the Broker Flow field must be optional when evidence is absent. Do not invent a parallel field structure.
4. Do not remove, rename, or retype any existing schema field.
5. Declare whether the extension is backward-compatible or breaking.
6. Validate the new field using the same validation pipeline used for existing fields.

**Allowed semantic values for both assessment fields**:
- `ACCUMULATION`
- `NEUTRAL`
- `DISTRIBUTION`

---

## Dashboard Rendering Rules

- Show `Analisa Foreign Flow` in all Initial Analysis results — it is always present (evidence is required).
- Show `Analisa Broker Flow` in WAIT Update and Position Update results **only when Broker Flow evidence was supplied**.
- Do not show `Analisa Broker Flow` when no Broker Flow evidence was attached to the update.
- Follow existing dashboard rendering conventions for missing or unavailable sections.
- Preserve existing analysis sections. Do not remove or reorder existing sections outside the PRD-specified position for the new section.

---

## Language Policy

- User-facing analysis sections must be in **Indonesian** (consistent with existing product policy).
- Section names `Analisa Foreign Flow` and `Analisa Broker Flow` are correct per PRD.
- Internal field names (`foreign_flow_assessment`, `broker_flow_assessment`) remain in English.

---

## Prohibited Changes

Do not:
- add a fixed confidence formula or deterministic score boost;
- remove or rename existing output fields;
- require `Analisa Broker Flow` when no Broker Flow evidence was supplied;
- redesign the analysis output layout beyond the specified additions;
- create a new analysis type to carry flow output;
- display Gemini raw OCR output separately from the analysis section;
- change the existing output schema in ways that break historical record readability.

## BLOCKED Conditions

Return **BLOCKED** if authoritative response-schema or output-contract sources conflict, or if the existing schema cannot be extended minimally without inventing a parallel contract. Do not resolve this by following repository implementation alone.
