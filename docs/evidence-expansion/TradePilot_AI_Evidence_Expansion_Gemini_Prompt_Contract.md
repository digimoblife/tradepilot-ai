# TradePilot AI — Evidence Expansion Gemini Prompt Contract

**Feature:** Foreign Flow & Broker Flow Evidence Expansion
**Authoritative Source:** `docs/evidence-expansion/TradePilot_AI_PRD_Foreign_Flow_Broker_Flow_Evidence_Expansion.md`
**Document Type:** Gemini Behavioral Prompt Contract
**Status:** Ready for Product Owner Review

---

## Purpose and Scope

This document specifies the authoritative behavioral contract that Gemini prompt implementations must satisfy for the Evidence Expansion feature.

This document is **not** the literal final prompt text. It defines the required inputs, analysis responsibilities, reasoning rules, guardrails, and output constraints that prompt engineers and developers must encode into `prompts/rebuild/initial_analysis.md`, `prompts/rebuild/wait_update.md`, and `prompts/rebuild/position_update.md`.

---

## 1. Provider Governance

- **Single Provider Policy:** Gemini remains the sole AI provider (`gemini-3.1-flash-lite`).
- **No Provider Abstraction:** No provider fallback, multi-provider routing, or external proxy mechanism is introduced or permitted by this feature.
- **Structured Output:** All Gemini responses must be returned as single, unadorned JSON objects adhering strictly to the JSON schemas defined under `schemas/rebuild/v1/`.

---

## 2. INITIAL_ANALYSIS Prompt Contract

### 2.1 Inputs to Gemini

Gemini receives exactly four evidence images in deterministic order, alongside session facts:
1. **Initial Orderbook screenshot** (Image 1) — evaluate visible market structure, bid/ask depth, and liquidity pressure.
2. **Three-Month Chart screenshot** (Image 2) — evaluate medium-term trend, key price levels, and chart patterns.
3. **Six-Month Chart screenshot** (Image 3) — evaluate macro trend, major support/resistance, and structural context.
4. **Foreign Flow — 1W screenshot** (Image 4, **Required**) — evaluate weekly foreign institutional transaction flow.

Current price is not supplied separately for Initial Analysis. No position exists.

### 2.2 Foreign Flow Analysis Contract

Gemini must perform an explicit analysis of the Foreign Flow 1W evidence across five mandatory dimensions:

1. **Classification:** Classify net weekly foreign transaction activity into exactly one semantic value:
   - `ACCUMULATION`: Consistent net foreign buying across visible days or overwhelming net inflow.
   - `NEUTRAL`: Mixed foreign buying and selling without clear direction, or negligible volume.
   - `DISTRIBUTION`: Consistent net foreign selling across visible days or overwhelming net outflow.

2. **Daily Consistency:** Assess whether foreign accumulation or distribution is sustained across visible trading days in the weekly view, or concentrated in an isolated spike.

3. **Magnitude Evaluation:** Evaluate the volume scale of net foreign inflow or outflow relative to visible historical flow in the screenshot.

4. **Price-Flow Relationship:** Analyze whether foreign net buying/selling aligns with price movement (e.g., price rising on foreign accumulation vs. price rising on foreign distribution).

5. **Confirmation / Divergence:** Determine whether foreign flow confirms or diverges from the technical thesis derived from the orderbook and charts:
   - *Confirmation:* Foreign accumulation accompanying a bullish chart setup or foreign distribution accompanying a bearish setup.
   - *Divergence:* Foreign distribution occurring during a price breakout (potential trap) or foreign accumulation occurring during a price breakdown (potential absorption).

### 2.3 Initial Analysis Guardrails

- **One-Day Trap Prevention:** Gemini must **not** treat a single large foreign-buying day as automatically bullish without evaluating preceding days in the 1W window.
- **No Inferred Facts:** Gemini must not invent foreign net figures, transaction values, or precise lot quantities that are unreadable or absent from the image.
- **Unreadable Evidence:** If the 1W Foreign Flow image is unreadable or insufficient, Gemini must state the limitation in Indonesian (e.g., `"Bukti visual Foreign Flow belum cukup jelas"`) and classify as `NEUTRAL` with a cautious explanation.
- **Advisory Only:** Foreign flow findings must be synthesized into the overall `summary`, `risks`, and `conclusion` fields without asserting deterministic trade outcomes or guaranteed returns.

---

## 3. WAIT_UPDATE Prompt Contract

### 3.1 Inputs to Gemini

Gemini receives:
1. **Current Orderbook screenshot** (Image 1, **Required**) — latest visual orderbook evidence.
2. **Broker Flow — 1D screenshot** (Image 2, **Optional**) — latest daily broker summary evidence, when uploaded by user.
3. **Approved Session Context** — session facts, current confirmed price, observation period, observation timestamp, latest Initial Analysis result, and latest prior WAIT Update result (if available).

### 3.2 Broker Flow Analysis Contract (When Present)

When Image 2 (Broker Flow 1D) is supplied in the request context:

1. **Classification:** Classify visible daily broker activity as `ACCUMULATION`, `NEUTRAL`, or `DISTRIBUTION`.
2. **Dominant Activity:** Identify whether top buyer/seller brokers exhibit concentrated accumulation or distribution.
3. **Thesis Impact:** Evaluate whether 1D Broker Flow confirms, weakens, or leaves unchanged the current WAIT thesis established in prior analyses.
4. **Readiness Signal:** Assess whether broker activity indicates that entry conditions are nearing (strengthening thesis) or deteriorating (weakening thesis).

### 3.3 Conditional Handling (When Absent)

When Image 2 (Broker Flow 1D) is **not** supplied:
- Gemini must perform WAIT Update analysis using only Image 1 (Orderbook) and session context (existing baseline behavior).
- Gemini must **not** fabricate Broker Flow commentary or generate a `broker_flow_analysis` section in the output.
- Analysis execution must proceed normally without penalty or failure.

---

## 4. POSITION_UPDATE Prompt Contract

### 4.1 Inputs to Gemini

Gemini receives:
1. **Current Orderbook screenshot** (Image 1, **Required**) — latest visual orderbook evidence.
2. **Broker Flow — 1D screenshot** (Image 2, **Optional**) — latest daily broker summary evidence, when uploaded by user.
3. **Approved Position Context** — session facts, confirmed OPEN position facts (entry price, entry timestamp, quantity, stop loss, target price), current price, observation period, observation timestamp, latest Initial Analysis, latest prior WAIT Update (if any), and latest prior Position Update (if any).

### 4.2 Broker Flow Analysis Contract (When Present)

When Image 2 (Broker Flow 1D) is supplied in the request context:

1. **Classification:** Classify visible daily broker activity as `ACCUMULATION`, `NEUTRAL`, or `DISTRIBUTION`.
2. **Accumulation Continuity vs. Distribution Emergence:** Evaluate whether institutional/broker support for the open position is continuing or if early distribution by top brokers is emerging.
3. **Orderbook Alignment:** Check whether broker flow aligns with orderbook pressure (e.g., bid stacking matched by top broker accumulation vs. bid weakness matched by broker distribution).
4. **Position Risk Implication:** Evaluate whether broker flow increases risk to the target price or increases probability of stop loss threat.

### 4.3 Conditional Handling (When Absent)

When Image 2 (Broker Flow 1D) is **not** supplied:
- Gemini performs Position Update analysis using Image 1 (Orderbook), confirmed position facts, and historical context.
- Gemini must **not** fabricate Broker Flow commentary or output `broker_flow_analysis`.
- Position monitoring proceeds normally.

---

## 5. General Broker Flow Guardrails

Every prompt dealing with Broker Flow (`wait_update.md`, `position_update.md`) must include the following explicit instructions:

1. **Broker Identity Non-Certainty:** Broker codes represent brokerage firms, not individual traders or single institutions. A net-buying broker code may reflect multiple retail clients or one institutional buyer. Gemini must not assert institutional identity as absolute fact.
2. **Daily Noise Warning:** 1D Broker Flow represents a short timeframe (one trading day or session) and is inherently noisier than weekly foreign flow. Gemini must not treat 1D broker accumulation as a permanent structural shift.
3. **Unreadable Evidence:** If a Broker Flow screenshot is unreadable, state the limitation in Indonesian rather than guessing broker codes or transaction values.
4. **No Invented Values:** Never fabricate broker names, transaction volumes, average prices, or lot totals that are not clearly visible in the image.

---

## 6. Reasoning Guidelines for Confidence and Probabilities

- **Evidence Confluence:** When independent evidence sources agree (e.g., orderbook bid strength + technical support + foreign accumulation), Gemini may reflect higher thesis confidence in advisory probability fields (`upside_probability`, `target_probability`).
- **Evidence Conflict:** When evidence sources conflict (e.g., price at resistance + foreign distribution + orderbook bid stacking), Gemini must reflect increased uncertainty by lowering upside/target probability or expanding key risks.
- **No Hard-Coded Formulas:** Gemini prompt instructions must **not** specify arbitrary arithmetic rules (such as "+15% probability if foreign flow is ACCUMULATION"). All probability adjustments must stem from qualitative synthesis.
- **Advisory Scoping:** Probabilities and confidence assessments remain advisory content only. They do not constitute automated trading commands, stop-loss triggers, or decision overrides.
