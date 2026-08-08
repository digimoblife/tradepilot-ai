# TradePilot AI — Feature PRD
## Foreign Flow & Broker Flow Evidence Expansion

**Document Type:** Product Requirements Document
**Status:** Approved for Implementation Planning
**Scope:** Evidence expansion for existing analysis workflows only
**Language:** English
**Target Product:** TradePilot AI

---

## 1. Purpose

This PRD defines a focused enhancement to TradePilot AI's existing evidence-driven analysis workflow by adding:

1. **Foreign Flow 1W** as an additional evidence input for **Initial Analysis**.
2. **Broker Flow 1D** as an additional supporting evidence input for **WAIT Update** and **Position Update**.

The goal is to improve the quality of Gemini's analysis by adding market-flow context that is not fully represented by price charts and orderbook evidence alone.

This PRD defines the Evidence Expansion delta only. It does not override unchanged authoritative rebuild contracts.

This feature must not introduce or modify session statuses, analysis types, monitoring-slot values, decision actions, provider architecture, queue architecture, or a trading workflow.

---

## 2. Product Rationale

The existing evidence set provides three important perspectives:

- **Orderbook** → current supply-demand condition.
- **3-Month Chart** → medium-term price structure.
- **6-Month Chart** → broader technical context.

However, the existing evidence does not directly show whether foreign participants are accumulating or distributing the stock over the recent trading week.

Adding **Foreign Flow 1W** provides a new market-participant perspective during Initial Analysis.

For subsequent monitoring:

- Orderbook remains the primary tactical evidence.
- **Broker Flow 1D** provides additional confirmation of whether visible broker activity supports accumulation, distribution, or a mixed/unclear condition.

The enhancement is intended to improve evidence diversity, not simply increase the number of screenshots sent to Gemini.

---

## 3. Goals

### 3.1 Primary Goals

The feature must:

- add Foreign Flow 1W to Initial Analysis evidence;
- add Broker Flow 1D to WAIT Update evidence;
- add Broker Flow 1D to Position Update evidence;
- allow Gemini to explicitly interpret foreign accumulation/distribution;
- allow Gemini to explicitly interpret broker accumulation/distribution;
- incorporate those interpretations into the existing trading analysis;
- surface the relevant interpretation clearly in the dashboard;
- preserve all existing TradePilot AI lifecycle and analysis behavior.

### 3.2 Non-Goals

This feature must not:

- create a new analysis type;
- create a new session status;
- create new BUY / WAIT / SKIP / CLOSE actions;
- add automatic broker identification logic outside Gemini;
- calculate foreign flow numerically from raw market data;
- calculate broker flow numerically from raw market data;
- introduce automatic trading signals;
- replace the existing chart or orderbook evidence;
- redesign the entire dashboard;
- change the current queue architecture;
- change the Gemini provider;
- introduce another AI provider.

---

## 4. Existing Analysis Types

The approved analysis types remain unchanged:

- `INITIAL_ANALYSIS`
- `WAIT_UPDATE`
- `POSITION_UPDATE`

No additional analysis type is introduced by this feature.

---

## 5. Evidence Requirements

## 5.1 Initial Analysis

### Existing Evidence

Initial Analysis currently uses:

1. `ORDERBOOK`
2. `CHART_3_MONTH`
3. `CHART_6_MONTH`

### New Evidence Set

Initial Analysis must use:

1. `ORDERBOOK`
2. `CHART_3_MONTH`
3. `CHART_6_MONTH`
4. `FOREIGN_FLOW_1W`

### Foreign Flow Evidence Definition

`FOREIGN_FLOW_1W` represents a screenshot of the stock's **1-week Foreign Flow view**.

The screenshot should visibly contain enough information for Gemini to interpret:

- daily foreign buy/sell direction;
- net foreign flow;
- price movement during the same period;
- recent accumulation or distribution tendency;
- possible divergence between price movement and foreign flow.

### Requirement

`FOREIGN_FLOW_1W` is a **required Initial Analysis evidence item**.

Initial Analysis must not be submitted until all four required evidence items are present.

Initial Evidence is submitted exactly once per session. After submission, the Initial Evidence set is immutable: it cannot be overwritten, appended, versioned, or replaced.

---

## 5.2 WAIT Update

### Existing Evidence

WAIT Update currently uses:

- one `ORDERBOOK` screenshot for the update.

### Enhanced Evidence

WAIT Update must support:

- `ORDERBOOK` — required;
- `BROKER_FLOW_1D` — optional supporting evidence.

### Broker Flow Evidence Definition

`BROKER_FLOW_1D` represents a screenshot of the stock's **1-day Broker Flow view**.

Gemini should use the screenshot to identify:

- dominant visible buying brokers;
- dominant visible selling brokers;
- whether buying or selling appears concentrated;
- whether broker activity appears consistent with accumulation;
- whether broker activity appears consistent with distribution;
- whether broker activity confirms or conflicts with the orderbook and previous analysis.

### Requirement

The user must still be able to submit a WAIT Update using only the required Orderbook evidence.

If Broker Flow 1D is uploaded, it must belong to the exact WAIT Update observation containing the corresponding Orderbook and be included in that update's Gemini analysis context. It must not be treated as generic session-level evidence.

---

## 5.3 Position Update

### Existing Evidence

Position Update currently uses:

- one `ORDERBOOK` screenshot for the selected monitoring slot.

### Enhanced Evidence

Position Update must support:

- `ORDERBOOK` — required;
- `BROKER_FLOW_1D` — optional supporting evidence.

The existing authoritative Position Update monitoring slots remain unchanged:

- `MORNING`
- `MIDDAY`
- `AFTERNOON`

Evidence Expansion does not modify monitoring slots. Broker Flow 1D must belong to the exact Position Update observation containing the corresponding Orderbook evidence; it must not be treated as generic session-level evidence.

### Requirement

The user must still be able to submit a Position Update using only the required Orderbook evidence.

If Broker Flow 1D is provided, Gemini must use it as supporting confirmation.

---

Closing Analysis is outside this feature scope.

---

## 6. Gemini Prompt Requirements

This feature requires changes to the prompts sent to Gemini.

The changes must be scoped to the relevant existing analysis types.

---

## 6.1 Initial Analysis Prompt

The Initial Analysis prompt must explicitly tell Gemini that it receives:

- Orderbook;
- 3-Month Chart;
- 6-Month Chart;
- Foreign Flow 1W.

Gemini must evaluate Foreign Flow separately before combining it with the other evidence.

The prompt must instruct Gemini to determine whether the recent foreign flow condition is best described as:

- `ACCUMULATION`
- `NEUTRAL`
- `DISTRIBUTION`

The prompt must also require Gemini to evaluate:

- consistency of foreign flow across the week;
- magnitude of recent inflow/outflow visible in the image;
- relationship between foreign flow and price direction;
- confirmation or divergence between price and foreign flow;
- whether foreign activity strengthens or weakens the current trading thesis.

Gemini must not treat one large foreign-buying day as automatically bullish without considering the preceding days.

---

## 6.2 WAIT Update Prompt

If Broker Flow 1D is present, the WAIT Update prompt must tell Gemini to interpret it as supporting evidence.

Gemini should classify the visible broker activity as:

- `ACCUMULATION`
- `NEUTRAL`
- `DISTRIBUTION`

Gemini must compare Broker Flow against:

- current Orderbook;
- previous session analysis;
- current price context;
- the reason the session is still in WAIT.

The prompt should explicitly ask:

- Is the expected confirmation beginning to appear?
- Does broker activity support continued waiting?
- Does broker activity weaken the previous thesis?
- Is the flow strong enough to materially affect the current conclusion?

The existing WAIT workflow and user decision remain unchanged.

---

## 6.3 Position Update Prompt

If Broker Flow 1D is present, the Position Update prompt must use it to assess whether market-participant activity supports or threatens the open-position thesis.

Gemini must consider:

- accumulation continuity;
- emerging distribution;
- broker-flow confirmation of orderbook behavior;
- conflict between price movement and broker flow;
- whether the new evidence changes the risk assessment.

Broker Flow must support the existing Position Update analysis. It must not independently create a new action or lifecycle state.

---

## 7. Gemini Reasoning Guardrails

The prompt must prevent overconfidence based on flow screenshots.

Gemini must be instructed that:

- broker codes do not necessarily represent a single investor;
- visible broker activity may include different clients and trading behaviors;
- one-day broker flow can be noisy;
- foreign flow is supporting evidence, not proof of future price direction;
- price action, technical structure, orderbook, and flow evidence must be evaluated together;
- conflicting evidence must reduce confidence rather than being ignored;
- the model must not claim certainty from screenshots.

The system should prefer language such as:

- supports;
- weakens;
- confirms;
- conflicts with;
- indicates;
- suggests;

rather than presenting flow evidence as deterministic proof.

---

## 8. Analysis Output Contract Changes

Yes, the dashboard analysis output should change because the new evidence adds information that users need to see.

However, the changes should remain small and focused.

---

## 8.1 Initial Analysis Output

Add a dedicated section:

### `Analisa Foreign Flow`

This section should summarize:

- accumulation / neutral / distribution assessment;
- recent flow pattern;
- relationship between foreign flow and price;
- whether the flow confirms or weakens the technical thesis.

A structured internal field may use:

`foreign_flow_assessment`

Allowed semantic values:

- `ACCUMULATION`
- `NEUTRAL`
- `DISTRIBUTION`

If the existing response schema requires structured JSON, this field must be added without changing unrelated fields.

---

## 8.2 WAIT Update Output

When Broker Flow 1D is supplied, add:

### `Analisa Broker Flow`

This section should explain:

- dominant visible broker behavior;
- accumulation / neutral / distribution assessment;
- whether it supports the current WAIT thesis;
- whether it materially changes confidence.

If Broker Flow is not supplied, the Broker Flow section may be omitted or displayed as unavailable according to the existing dashboard rendering convention.

---

## 8.3 Position Update Output

When Broker Flow 1D is supplied, add:

### `Analisa Broker Flow`

This section should explain:

- whether accumulation is continuing;
- whether distribution is appearing;
- whether broker behavior confirms or conflicts with the Orderbook;
- whether risk to the open position has increased or decreased.

The existing Position Update decision framework must remain unchanged.

---

## 9. Confidence and Probability Behavior

The new evidence may influence existing Confidence and Probability outputs.

However:

- no fixed arithmetic weighting is required by this PRD;
- no deterministic percentage increase should be hard-coded;
- Gemini should adjust confidence based on agreement or conflict across evidence;
- contradictory Foreign Flow or Broker Flow should be allowed to reduce confidence;
- supportive flow may increase confidence only when consistent with the broader evidence.

The product must not claim that the additional screenshot guarantees a specific improvement in prediction accuracy.

---

## 10. Dashboard Requirements

The dashboard changes should remain minimal.

### Initial Evidence Form

Add one new upload control:

**Foreign Flow — 1W**

The form should clearly distinguish it from:

- Orderbook;
- Chart 3M;
- Chart 6M.

The user should understand that a 1-week Foreign Flow screenshot is expected.

### WAIT Update Form

Add one optional upload control:

**Broker Flow — 1D (Optional)**

### Position Update Form

Add one optional upload control:

**Broker Flow — 1D (Optional)**

No new page or navigation item is required.

---

## 11. Evidence Display

After upload, the dashboard should preserve the same evidence-display behavior used for existing screenshots.

The evidence label must make the evidence type clear:

- `Foreign Flow 1W`
- `Broker Flow 1D`

The system should not require Gemini-generated OCR data to be displayed separately.

---

## 12. Data Model Impact

The implementation should reuse the existing evidence storage model whenever possible.

The preferred change is to extend the accepted evidence-type values with:

- `FOREIGN_FLOW_1W`
- `BROKER_FLOW_1D`

The implementation should not introduce a separate storage subsystem solely for these screenshots.

### Association Rules

`FOREIGN_FLOW_1W`:
- belongs to Initial Evidence;
- only one is allowed for the session's Initial Evidence set.
- is submitted exactly once and cannot be overwritten, appended, versioned, or replaced.

`BROKER_FLOW_1D`:
- belongs to the exact WAIT Update or Position Update observation containing the corresponding Orderbook;
- must not be treated as session-level Initial Evidence;
- must not be attached to another observation or treated as generic session-level evidence.

---

## 13. Validation

### Initial Analysis

Submission must fail if any of the following required evidence is missing:

- Orderbook;
- Chart 3M;
- Chart 6M;
- Foreign Flow 1W.

### WAIT Update

Submission must require:

- Orderbook.

Broker Flow 1D is optional.

### Position Update

Submission must require:

- Orderbook.

Broker Flow 1D is optional.

No image-content validation beyond the system's existing practical upload validation is required by this PRD.

The product does not need to prove that the uploaded image truly represents a specific Stockbit tab or timeframe.

---

## 14. Error Handling

If an optional Broker Flow image fails to upload:

- the user should be able to retry;
- the required Orderbook evidence must not be lost;
- the update should not be submitted with a partially attached broken evidence reference.

If Gemini cannot confidently interpret a flow screenshot:

- Gemini should state that the flow evidence is unclear;
- Gemini should not invent broker values or foreign-flow numbers;
- analysis should continue using the remaining valid evidence.

---

## 15. Backward Compatibility

Existing sessions created before this feature must remain readable.

The implementation must not invalidate historical Initial Analyses that contain only:

- Orderbook;
- Chart 3M;
- Chart 6M.

The four-image requirement applies only to new Initial Analysis submissions after the feature becomes active.

Historical WAIT Updates and Position Updates without Broker Flow remain valid.

No migration of historical AI output is required solely for this feature unless it is technically unavoidable to preserve compatibility.

---

## 16. Lifecycle Impact

No lifecycle change is allowed.

The existing session lifecycle remains authoritative.

This enhancement only changes evidence available to existing analysis stages.

---

## 17. UI / UX Principles

The implementation should remain simple and mobile-friendly.

The feature should:

- add only the required upload controls;
- reuse existing upload interaction patterns;
- clearly label timeframe requirements;
- avoid advanced validation;
- avoid additional modal flows unless already used by the current UI;
- avoid increasing user effort beyond the new screenshots themselves.

---

## 18. Acceptance Criteria

### Initial Analysis

- A new Initial Analysis form contains Foreign Flow 1W upload.
- Foreign Flow 1W is required.
- Initial Analysis cannot be submitted without it.
- Gemini receives the Foreign Flow image.
- Gemini explicitly analyzes Foreign Flow.
- Dashboard displays an `Analisa Foreign Flow` section.
- Existing Orderbook, Chart 3M, and Chart 6M behavior continues to work.

### WAIT Update

- WAIT Update supports an optional Broker Flow 1D upload.
- Orderbook remains required.
- WAIT Update can still be submitted without Broker Flow.
- When Broker Flow is supplied, Gemini receives it.
- Gemini explicitly analyzes Broker Flow.
- Dashboard displays `Analisa Broker Flow` when evidence is present.
- Existing WAIT behavior remains unchanged.

### Position Update

- Position Update supports an optional Broker Flow 1D upload.
- Orderbook remains required.
- Position Update can still be submitted without Broker Flow.
- When Broker Flow is supplied, Gemini receives it.
- Gemini explicitly analyzes Broker Flow.
- Dashboard displays `Analisa Broker Flow` when evidence is present.
- Existing monitoring slots remain unchanged.

### Regression

- Existing session lifecycle remains unchanged.
- Existing analysis types remain unchanged.
- Existing BUY / WAIT / SKIP / CLOSE actions remain unchanged.
- Historical sessions remain readable.
- Gemini remains the only AI provider.
- No unrelated dashboard redesign is introduced.

---

## 19. Recommended Analysis Presentation

### Initial Analysis

Recommended visible analysis structure:

1. Ringkasan Hari Ini
2. Analisa Orderbook
3. Analisa Chart
4. **Analisa Foreign Flow**
5. Support / Resistance
6. Entry
7. Stop Loss
8. Target Profit
9. Confidence
10. Probability
11. Trading Plan
12. Penilaian AI

### WAIT Update

Recommended visible additions:

1. Update Summary
2. Analisa Orderbook
3. **Analisa Broker Flow** — only when provided
4. Updated support/resistance or relevant tactical levels
5. Confidence / Probability update
6. Updated Trading Plan

### Position Update

Recommended visible additions:

1. Position Update Summary
2. Analisa Orderbook
3. **Analisa Broker Flow** — only when provided
4. Current risk assessment
5. Confidence / Probability update
6. Updated Trading Plan

The exact naming may be aligned with the existing dashboard output contract during implementation, but the new flow analysis must remain clearly visible.

---

## 20. Implementation Impact Summary

This feature is expected to affect the following areas:

1. **Evidence type definitions**
2. **Evidence upload validation**
3. **Initial Analysis form**
4. **WAIT Update form**
5. **Position Update form**
6. **Gemini Initial Analysis prompt**
7. **Gemini WAIT Update prompt**
8. **Gemini Position Update prompt**
9. **Structured Gemini response schema, if applicable**
10. **Analysis result rendering**
11. **Focused tests for evidence and prompt composition**

It should not require a new queue architecture, new lifecycle logic, new routes, or broad backend redesign.

---

## 21. Product Decision Summary

Approved feature direction:

- **Initial Analysis**
  - Add `FOREIGN_FLOW_1W`
  - Required evidence

- **WAIT Update**
  - Add `BROKER_FLOW_1D`
  - Optional supporting evidence

- **Position Update**
  - Add `BROKER_FLOW_1D`
  - Optional supporting evidence

- **Gemini prompts**
  - Must explicitly interpret the new evidence.
  - Must evaluate confirmation and divergence.
  - Must avoid deterministic conclusions.

- **Dashboard**
  - Add visible Foreign Flow analysis for Initial Analysis.
  - Add visible Broker Flow analysis when Broker Flow evidence is supplied.
  - Preserve all existing workflows and lifecycle behavior.

---

## 22. Success Definition

The feature is successful when TradePilot AI can use flow evidence to produce a more context-aware analysis without making the workflow materially more complex.

The desired improvement is not simply “more screenshots.”

The desired improvement is:

**better evidence diversity → better cross-confirmation → more defensible confidence and trading-plan reasoning.**
