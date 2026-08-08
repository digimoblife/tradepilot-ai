# TradePilot AI — Evidence Expansion Output Contract

**Feature:** Foreign Flow & Broker Flow Evidence Expansion
**Authoritative Source:** `docs/evidence-expansion/TradePilot_AI_PRD_Foreign_Flow_Broker_Flow_Evidence_Expansion.md`
**Document Type:** Output Schema & Dashboard Presentation Contract
**Status:** Ready for Product Owner Review

---

## Executive Summary

This contract defines the structured response schema extensions and dashboard rendering requirements for the Evidence Expansion feature.

It establishes a **minimal, backward-compatible extension** of the existing rebuild JSON schemas (`schemas/rebuild/v1/`) and frontend renderers (`frontend/src/features/analysis/`). No existing schema fields are removed, renamed, or modified.

---

## 1. Current Rebuild Schema Architecture

The rebuild flow uses three primary JSON schema contracts under `schemas/rebuild/v1/`:
1. `initial_analysis.schema.json` — compact advisory Initial Analysis schema.
2. `wait_update.schema.json` — compact advisory WAIT Update schema.
3. `position_update.schema.json` — compact advisory Position Update schema.

All three schemas enforce `additionalProperties: false`. Therefore, adding new fields requires explicit property declarations within these schema definitions.

---

## 2. Initial Analysis Output Extension

### 2.1 Schema Definition (`schemas/rebuild/v1/initial_analysis.schema.json`)

For new Initial Analysis generation-time output, add the mandatory `foreign_flow_analysis` property to `properties` and append `"foreign_flow_analysis"` to the top-level `required` array. Historical persisted records are handled separately by the read/render path.

```json
"foreign_flow_analysis": {
  "type": "object",
  "description": "Advisory Foreign Flow 1W assessment and analysis in Indonesian. Required for all new Initial Analysis outputs.",
  "additionalProperties": false,
  "properties": {
    "assessment": {
      "type": "string",
      "enum": ["ACCUMULATION", "NEUTRAL", "DISTRIBUTION"],
      "description": "Semantic classification of net weekly foreign flow."
    },
    "analysis": {
      "type": "string",
      "description": "Concise Indonesian explanation of foreign accumulation/distribution, weekly consistency, volume scale, and alignment with technical thesis."
    }
  },
  "required": ["assessment", "analysis"]
}
```

### 2.2 Preserved Required Fields
The following 13 original fields remain required and unchanged:
`summary`, `orderbook_analysis`, `three_month_chart_analysis`, `six_month_chart_analysis`, `support`, `resistance`, `entry_area`, `stop_recommendation`, `target_recommendation`, `probabilities`, `risks`, `trading_plan`, `conclusion`.

---

## 3. WAIT Update Output Extension

### 3.1 Schema Definition (`schemas/rebuild/v1/wait_update.schema.json`)

Add the optional `broker_flow_analysis` property to `properties`. Do **not** append it to the `required` array.

```json
"broker_flow_analysis": {
  "type": ["object", "null"],
  "description": "Optional advisory Broker Flow 1D assessment and analysis in Indonesian. Present only when Broker Flow evidence was supplied.",
  "additionalProperties": false,
  "properties": {
    "assessment": {
      "type": "string",
      "enum": ["ACCUMULATION", "NEUTRAL", "DISTRIBUTION"],
      "description": "Semantic classification of net daily broker flow."
    },
    "analysis": {
      "type": "string",
      "description": "Concise Indonesian explanation of top broker activity and its impact on the WAIT thesis."
    }
  },
  "required": ["assessment", "analysis"]
}
```

### 3.2 Omitted / Nullable Behavior
When Broker Flow 1D evidence is not uploaded for a WAIT Update:
- Gemini omits `broker_flow_analysis` or sets it to `null`.
- The output validates successfully against the schema because `broker_flow_analysis` is not in `required`.

---

## 4. Position Update Output Extension

### 4.1 Schema Definition (`schemas/rebuild/v1/position_update.schema.json`)

Add the optional `broker_flow_analysis` property to `properties`. Do **not** append it to the `required` array.

```json
"broker_flow_analysis": {
  "type": ["object", "null"],
  "description": "Optional advisory Broker Flow 1D assessment and analysis in Indonesian. Present only when Broker Flow evidence was supplied.",
  "additionalProperties": false,
  "properties": {
    "assessment": {
      "type": "string",
      "enum": ["ACCUMULATION", "NEUTRAL", "DISTRIBUTION"],
      "description": "Semantic classification of net daily broker flow for the open position."
    },
    "analysis": {
      "type": "string",
      "description": "Concise Indonesian explanation of broker accumulation continuity or distribution emergence."
    }
  },
  "required": ["assessment", "analysis"]
}
```

### 4.2 Omitted / Nullable Behavior
Same as WAIT Update: optional property; omitting or returning `null` when Broker Flow is absent validates without error.

---

## 5. Dashboard Rendering Contract

### 5.1 Initial Analysis View (`frontend/src/features/analysis/initial-analysis-view.tsx`)

- **New Section:** `"Analisa Foreign Flow"`
- **Display Position:** Rendered immediately after Chart Analysis sections and before Support / Resistance.
- **Section Elements:**
  - Badge / Indicator showing `assessment` (`ACCUMULATION` = Green / Positive, `NEUTRAL` = Gray / Neutral, `DISTRIBUTION` = Red / Caution).
  - Narrative body showing `analysis` text in Indonesian.
- **Graceful Fallback:** If `foreign_flow_analysis` is undefined or null (historical record), the renderer skips the section without crashing or displaying empty containers.

### 5.2 WAIT Update View (`frontend/src/features/analysis/watching-update-view.tsx`)

- **Conditional Section:** `"Analisa Broker Flow"`
- **Display Condition:** Rendered **only** when `processed_response.broker_flow_analysis` is present and non-null.
- **Section Elements:**
  - Badge indicating `ACCUMULATION`, `NEUTRAL`, or `DISTRIBUTION`.
  - Narrative body showing `analysis` text.
- **Absent Handling:** When `broker_flow_analysis` is null or undefined, no Broker Flow section is rendered.

### 5.3 Position Update View (`frontend/src/features/analysis/open-position-update-view.tsx`)

- **Conditional Section:** `"Analisa Broker Flow"`
- **Display Condition:** Rendered **only** when `processed_response.broker_flow_analysis` is present and non-null.
- **Section Elements:**
  - Badge indicating `ACCUMULATION`, `NEUTRAL`, or `DISTRIBUTION`.
  - Narrative body showing `analysis` text.
- **Absent Handling:** When `broker_flow_analysis` is null or undefined, no Broker Flow section is rendered.

---

## 6. Backward Compatibility Rules

1. **New Initial Analysis Output:** `foreign_flow_analysis` is required by the generation-time schema for every newly generated Initial Analysis output.
2. **Historical Initial Analysis Records:** Existing persisted JSON payloads may lack `foreign_flow_analysis`. The read/render path must check `if (data.foreign_flow_analysis)` and skip the section without failure; this does not make the field optional in the new generation schema.
3. **Historical WAIT & Position Update Records:** Existing persisted payloads may lack `broker_flow_analysis`. The field remains optional/nullable for WAIT and Position Update outputs, and rendering must tolerate its absence.
4. **No Database Migration:** No backfill or SQL data migration is needed or permitted for historical `analysis_requests_v2` records.

---

## 7. Prohibited Schema Changes

- Do **not** create new schema versions or schema files (e.g., `initial_analysis_v3.json`). Extend `schemas/rebuild/v1/` in-place.
- Do **not** remove or rename any property in existing schemas.
- Do **not** change the enum values for `ACCUMULATION`, `NEUTRAL`, or `DISTRIBUTION`.
- Do **not** introduce numeric foreign flow or broker flow metrics (e.g., net lots, transaction rupiah amounts) into the schema.
- Do **not** weaken `additionalProperties: false`; explicitly declare each new top-level and nested-object property.

---

## 8. Illustrative Response Examples

### 8.1 Initial Analysis (Snippet)
```json
{
  "summary": "Analisis awal menunjukkan pola konsolidasi positif...",
  "orderbook_analysis": "Bid tebal pada level 1450-1460...",
  "three_month_chart_analysis": "Uptrend masih terjaga...",
  "six_month_chart_analysis": "Mendekati resistance kuat...",
  "foreign_flow_analysis": {
    "assessment": "ACCUMULATION",
    "analysis": "Akumulasi asing konsisten terlihat selama 4 hari perdagangan terakhir dengan volume signifikan."
  },
  "support": { "low": 1420, "high": 1450, "note": "Area support kuat" },
  "resistance": { "low": 1550, "high": 1580, "note": "Area resistance swing high" }
}
```

### 8.2 WAIT Update with Broker Flow (Snippet)
```json
{
  "update_summary": "Kondisi penantian masih valid...",
  "current_price": 1485.0,
  "orderbook_assessment": "Penawaran menipis di area 1490...",
  "broker_flow_analysis": {
    "assessment": "ACCUMULATION",
    "analysis": "Broker pembeli utama menunjukkan akumulasi bersih pada sesi perdagangan hari ini."
  },
  "recommended_action": "WAIT"
}
```
