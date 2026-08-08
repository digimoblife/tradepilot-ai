# TradePilot Evidence Upload Contract — Evidence Expansion

## Purpose

Define the evidence upload, validation, ownership, and association rules introduced by the Foreign Flow / Broker Flow Evidence Expansion feature.

## When to Use

Use this skill for every task that touches evidence upload, evidence validation, evidence type definitions, or evidence-to-analysis association in the context of the Evidence Expansion feature.

Load `tradepilot-evidence-expansion-source-lock` first.

---

## Authoritative Source

> `docs/evidence-expansion/TradePilot_AI_PRD_Foreign_Flow_Broker_Flow_Evidence_Expansion.md` — Sections 5, 12, 13, 14, 15.

---

## Evidence Sets by Analysis Type

### INITIAL_ANALYSIS Evidence

| Evidence Item | Type Identifier | Required |
|---|---|---|
| Orderbook | `ORDERBOOK` | ✅ Required |
| 3-Month Chart | `CHART_3_MONTH` | ✅ Required |
| 6-Month Chart | `CHART_6_MONTH` | ✅ Required |
| Foreign Flow 1W | `FOREIGN_FLOW_1W` | ✅ Required |

**Submission rule**: Initial Analysis must not be submitted if any of the four items is missing. Validation must fail before creating a Gemini request.

**Immutability rule**: Initial Evidence is submitted exactly once per session. `FOREIGN_FLOW_1W` belongs to this initial set. After submission it cannot be overwritten, appended, versioned, or replaced.

---

### WAIT_UPDATE Evidence

| Evidence Item | Type Identifier | Required |
|---|---|---|
| Orderbook | `ORDERBOOK` | ✅ Required |
| Broker Flow 1D | `BROKER_FLOW_1D` | Optional |

**Submission rule**: A WAIT Update may be submitted using only the required Orderbook. Broker Flow 1D is valid supporting evidence but its absence must not block submission.

**When Broker Flow is supplied**: it must belong to the exact WAIT Update observation containing the corresponding Orderbook and be included in that update's Gemini request context. It must not be generic session-level evidence.

---

### POSITION_UPDATE Evidence (Position Update)

| Evidence Item | Type Identifier | Required |
|---|---|---|
| Orderbook | `ORDERBOOK` | ✅ Required |
| Broker Flow 1D | `BROKER_FLOW_1D` | Optional |

**Submission rule**: A Position Update may be submitted using only the required Orderbook. Broker Flow 1D is valid supporting evidence but its absence must not block submission.

**Monitoring slots**: The authoritative rebuild contract defines `MORNING`, `MIDDAY`, and `AFTERNOON`. Evidence Expansion does not change these values.

**When Broker Flow is supplied**: it must belong to the exact Position Update observation containing the corresponding Orderbook. It must not be generic session-level evidence.

---

## Association Rules

### FOREIGN_FLOW_1W Association

- Belongs to the session's **Initial Evidence set** only.
- Only one `FOREIGN_FLOW_1W` is permitted per session's Initial Evidence; it cannot be overwritten, appended, versioned, or replaced after submission.
- Must not be associated with WAIT Updates or Position Updates.
- Must not be treated as update-level evidence.

### BROKER_FLOW_1D Association

- For WAIT Update, belongs to the exact WAIT observation containing the corresponding Orderbook.
- For Position Update, belongs to the exact Position Update observation containing the corresponding Orderbook.
- Is never generic session-level evidence or session-level Initial Evidence.
- Follows the same ownership and association pattern as the Orderbook for that update.

---

## Storage and Model Rules

- Reuse the existing evidence storage model. Do not introduce a separate storage subsystem for these two new evidence types.
- Extend the accepted evidence-type enum/values to include `FOREIGN_FLOW_1W` and `BROKER_FLOW_1D`.
- Evidence metadata, file references, and ownership remain governed by the existing Evidence Service.
- Historical evidence records must remain readable after the model is extended.

---

## Validation Rules

| Context | Validation Requirement |
|---|---|
| Initial Analysis | Fail if `ORDERBOOK`, `CHART_3_MONTH`, `CHART_6_MONTH`, or `FOREIGN_FLOW_1W` is missing |
| WAIT Update | Fail only if `ORDERBOOK` is missing; `BROKER_FLOW_1D` absence is not a failure |
| Position Update | Fail only if `ORDERBOOK` is missing; `BROKER_FLOW_1D` absence is not a failure |

- No image-content validation (OCR, timeframe detection) is required by this feature.
- The system does not need to verify that the uploaded image truly represents the correct Stockbit view or timeframe.
- Validation failures must preserve user-uploaded evidence and must not create a Gemini request.

---

## Error Handling Rules

- If an optional Broker Flow upload fails: user must be able to retry; required Orderbook evidence must not be lost; update must not be submitted with a broken evidence reference.
- If Gemini cannot interpret a flow screenshot: Gemini must state the evidence is unclear; Gemini must not invent values; analysis continues using remaining valid evidence.

---

## Backward Compatibility

- Historical Initial Analyses with only `ORDERBOOK` + `CHART_3_MONTH` + `CHART_6_MONTH` remain valid. Do not invalidate them.
- Historical WAIT Updates and Position Updates without `BROKER_FLOW_1D` remain valid.
- The four-image requirement for Initial Analysis applies only to new submissions after the feature is active.
- Extend the evidence type allowlist; do not replace or restrict existing types.
- No historical AI-output migration is required solely for this feature unless technically unavoidable to preserve compatibility.

---

## Prohibited Changes

Do not:
- introduce a separate evidence subsystem without an explicit authoritative requirement;
- require `BROKER_FLOW_1D` for WAIT Update or Position Update submission;
- associate `FOREIGN_FLOW_1W` with WAIT Update or Position Update;
- associate `BROKER_FLOW_1D` with the Initial Evidence set;
- add OCR or automatic image-content validation logic;
- invalidate historical evidence records by changing existing type semantics;
- require Gemini-generated data to be displayed separately from the analysis section.
