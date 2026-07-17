# SCHEMA_IMPLEMENTATION_PLAN.md

## TradePilot AI Simplified Schema Implementation Plan

**Document Version:** 2.0
**Status:** Revised and Approved Direction
**Supersedes:** Previous 32-schema implementation plan
**Language:** English for technical schemas and engineering documentation
**User-facing analysis language:** Indonesian

---

## 1. Purpose

This document defines the simplified JSON Schema implementation plan for TradePilot AI.

The previous schema plan separated nearly every analytical concept into an independent schema file. Although technically comprehensive, that approach introduced unnecessary complexity and moved the product away from its core purpose.

TradePilot AI is intended to reproduce the practical swing-trading analysis workflow previously conducted through conversational analysis:

1. Create one Trade Session for one ticker.
2. Upload initial orderbook and chart evidence.
3. Receive an initial trading analysis.
4. Decide whether to watch or open a position.
5. Upload new orderbook screenshots during the morning, midday, or afternoon.
6. Compare the latest condition with the full prior session history.
7. Review whether the thesis, stop loss, and target remain realistic.
8. Close the trade and record the result and lessons.

The schema design must therefore follow actual user-facing analysis outputs rather than model every technical concept as a separate domain object.

---

## 2. Core Design Principle

> One schema should represent one meaningful product payload or user workflow, not one small analytical concept.

Examples:

* An Open Position Update should be represented by one main schema.
* Confidence, probabilities, price levels, and recommended actions should be sections inside that update.
* They should not require separate root-level schema files unless they are reused as meaningful standalone records.

The schema system should remain:

* understandable,
* easy to implement,
* easy to validate,
* easy to debug,
* suitable for AI structured output,
* compatible with Gemini and DeepSeek,
* aligned with the Trade Session page,
* flexible enough for future improvements.

---

## 3. Product Scope

The schema system supports the following TradePilot AI workflow:

### 3.1 Initial Analysis

The user provides:

* ticker,
* optional company name,
* orderbook screenshot,
* three-month chart,
* six-month chart,
* optional market notes.

The AI returns:

* market summary,
* orderbook analysis,
* chart analysis,
* support and resistance,
* proposed entry,
* proposed stop loss,
* proposed target,
* initial thesis,
* trading plan,
* directional bias,
* confidence,
* target and downside probabilities.

### 3.2 Watching Update

The user has not entered a position yet.

The AI evaluates:

* what changed since the initial or previous analysis,
* whether the setup improved or weakened,
* whether entry remains attractive,
* whether price should be chased,
* what conditions should trigger entry,
* what conditions should cancel the setup.

### 3.3 Open Position Update

The user has confirmed an actual position.

The AI evaluates:

* today’s market summary,
* latest orderbook condition,
* relevant chart condition,
* position performance,
* thesis condition,
* stop-loss condition,
* target realism,
* current trading plan,
* bullish or bearish bias,
* target probability,
* downside probability,
* changes from the previous update.

### 3.4 Partial Exit Review

The user has sold part of the position.

The AI evaluates:

* realized result,
* remaining quantity,
* remaining position risk,
* revised stop loss,
* remaining target realism,
* whether the rest should be held or closed.

### 3.5 Closing Analysis

The position is fully closed.

The AI records:

* exit information,
* realized profit or loss,
* reason for closing,
* whether the thesis succeeded or failed,
* what worked,
* what did not work,
* lessons for future trades.

---

## 4. Simplified Schema Inventory

The revised implementation uses **11 JSON Schema files**.

### 4.1 Shared Schemas

1. `common.schema.json`
2. `evidence.schema.json`
3. `market_snapshot.schema.json`
4. `trade_state.schema.json`

### 4.2 Analysis Root Schemas

5. `initial_analysis.schema.json`
6. `watching_update.schema.json`
7. `open_position_update.schema.json`
8. `partial_exit_review.schema.json`
9. `closing_analysis.schema.json`

### 4.3 Memory and Registry Schemas

10. `context_summary.schema.json`
11. `manifest.json`

This replaces the previous plan of approximately 32 individual schemas.

---

## 5. Schema Responsibilities

## 5.1 `common.schema.json`

Contains reusable primitive definitions and compact enums.

### Responsibilities

* UUID
* timestamp
* trading date
* ticker
* language code
* price
* nullable price
* quantity
* percentage
* probability
* confidence score
* short text
* narrative text
* arrays
* analysis type
* session status
* thesis status
* directional bias
* risk level
* recommended action
* evidence type
* timeframe
* update period

### Important rule

Only enums that are shared across multiple schemas should be stored here.

Do not move small, schema-specific enums into `common.schema.json`.

---

## 5.2 `evidence.schema.json`

Represents uploaded evidence and its basic usability.

### Responsibilities

* evidence ID,
* evidence type,
* file reference,
* upload timestamp,
* market timestamp,
* timeframe,
* readability,
* extraction status,
* optional extracted facts,
* user notes,
* whether evidence is active or superseded.

### Supported evidence types

* `ORDERBOOK_SCREENSHOT`
* `CHART_3_MONTH`
* `CHART_6_MONTH`
* `CHART_OTHER`
* `MARKET_SCREENSHOT`
* `USER_NOTE`
* `POSITION_CONFIRMATION`
* `EXIT_CONFIRMATION`

### Design rule

Evidence quality should remain simple.

The schema only needs to indicate whether evidence is:

* usable,
* partially usable,
* unreadable,
* stale,
* superseded.

It does not require detailed institutional-style provenance scoring.

---

## 5.3 `market_snapshot.schema.json`

Represents the market values visible or available for one analysis update.

### Responsibilities

* open,
* high,
* low,
* last,
* close,
* previous close,
* average,
* volume,
* transaction value,
* best bid,
* best offer,
* market timestamp,
* trading date,
* session period,
* data availability,
* concise market summary.

### Design rule

Unknown values must use `null`.

Unknown values must never be replaced with zero.

---

## 5.4 `trade_state.schema.json`

Represents the current confirmed state of one Trade Session.

This is the main canonical business state shared across analysis types.

### Responsibilities

#### Session identity

* session ID,
* ticker,
* company name,
* session status,
* created timestamp,
* updated timestamp.

#### Position state

* position exists,
* entry price,
* entry timestamp,
* original quantity,
* remaining quantity,
* current price,
* active stop loss,
* active target,
* realized profit or loss,
* unrealized profit or loss.

#### Thesis state

* thesis summary,
* thesis status,
* support condition,
* invalidation condition,
* thesis last updated timestamp.

#### Current plan

* current action,
* hold condition,
* exit condition,
* next checkpoint,
* user-confirmed changes.

### Important rule

AI output must not directly overwrite canonical Trade State.

AI may propose changes, but the user must confirm actual:

* entry,
* quantity,
* partial exit,
* full exit,
* stop-loss change,
* target change.

---

## 5.5 `initial_analysis.schema.json`

Represents the first complete analysis of a Trade Session.

### Required output sections

1. Analysis metadata
2. Market summary
3. Evidence summary
4. Orderbook analysis
5. Three-month chart analysis
6. Six-month chart analysis
7. Combined chart view
8. Support and resistance
9. Proposed entry plan
10. Proposed stop loss
11. Proposed target
12. Initial thesis
13. Trading plan
14. AI assessment
15. Missing information
16. Warnings

### AI assessment fields

* directional bias,
* confidence score,
* setup quality,
* target probability,
* downside probability,
* risk level,
* concise conclusion.

### Important rule

The schema must distinguish:

* visible facts,
* AI interpretation,
* recommended plan.

This distinction can be implemented as compact arrays or narrative fields inside the root schema. It does not require an independent evidence-assessment root schema.

---

## 5.6 `watching_update.schema.json`

Represents an update before the user opens a position.

### Required output sections

1. Analysis metadata
2. Current market summary
3. Latest orderbook analysis
4. Relevant chart update
5. Changes from previous analysis
6. Setup status
7. Entry realism
8. Chase risk
9. Updated support and resistance
10. Entry trigger
11. Setup cancellation condition
12. Trading plan
13. AI assessment
14. Missing information
15. Warnings

### Setup status examples

* `IMPROVING`
* `STILL_VALID`
* `WEAKENING`
* `WAITING_FOR_CONFIRMATION`
* `CANCELLED`

### Important rule

A watching update must not assume that the user has entered a position.

---

## 5.7 `open_position_update.schema.json`

Represents the central TradePilot AI workflow after a real position has been opened.

This is the highest-priority root schema.

### Required output sections

#### 1. Analysis metadata

* analysis ID,
* session ID,
* ticker,
* analysis timestamp,
* update period,
* comparison analysis ID.

#### 2. Today’s market summary

* open,
* high,
* low,
* last or close,
* average,
* change percentage,
* concise summary.

#### 3. Orderbook analysis

* visible buyer condition,
* visible seller condition,
* buyer strength,
* seller pressure,
* bid support,
* offer resistance,
* spread observation,
* important visible changes,
* concise conclusion.

#### 4. Chart update

Chart analysis may be compact during routine Open Position updates.

Fields include:

* short-term trend,
* medium-term trend,
* structure status,
* nearest support,
* nearest resistance,
* breakout or breakdown status,
* concise conclusion.

If no updated chart was uploaded, the system may reuse the last accepted chart context and clearly label it as historical context.

#### 5. Position assessment

* entry price,
* current price,
* stop loss,
* target price,
* remaining quantity,
* unrealized return,
* distance to stop,
* distance to target,
* position health.

#### 6. Thesis assessment

* thesis status,
* thesis summary,
* evidence strengthening thesis,
* evidence weakening thesis,
* invalidation status,
* whether the thesis remains valid.

#### 7. Target realism

* target still realistic,
* target realism classification,
* target probability,
* primary obstacle,
* required condition,
* revised target proposal, if any.

#### 8. Stop-loss assessment

* stop still appropriate,
* stop risk,
* whether stop has been approached,
* whether stop has been triggered,
* revised stop proposal, if any.

#### 9. Trading plan

* current action,
* action rationale,
* plan for the next session,
* hold condition,
* reduce-risk condition,
* exit condition,
* levels to monitor.

#### 10. AI assessment

* directional bias,
* confidence score,
* bullish probability,
* target probability,
* downside probability,
* risk level,
* concise conclusion.

#### 11. Changes from previous update

A simple array of material changes, for example:

* buyer strength increased,
* seller pressure decreased,
* resistance moved higher,
* thesis weakened,
* target probability increased,
* downside risk increased.

Each item may contain:

* category,
* previous value,
* current value,
* direction,
* materiality,
* explanation.

#### 12. Missing information and warnings

The AI must clearly state limitations caused by:

* unreadable screenshots,
* missing timestamp,
* missing position information,
* no comparable prior evidence,
* stale chart context.

### Important rule

This schema must directly support the user-facing analysis structure:

1. Ringkasan hari ini
2. Yang terlihat dari orderbook
3. Apakah TP masih realistis
4. Trading plan selanjutnya
5. Penilaian AI saat ini

---

## 5.8 `partial_exit_review.schema.json`

Represents analysis after part of the position has been closed.

### Required output sections

* partial exit confirmation,
* exit price,
* exited quantity,
* remaining quantity,
* realized return,
* remaining position return,
* thesis status,
* remaining target realism,
* revised stop-loss assessment,
* revised trading plan,
* AI assessment,
* changes from previous update.

### Important rule

The AI must not infer a partial exit from market movement.

The user must confirm the execution.

---

## 5.9 `closing_analysis.schema.json`

Represents the final analysis after the position is fully closed.

### Required output sections

* session identity,
* entry summary,
* exit summary,
* realized result,
* holding duration,
* closing reason,
* final thesis evaluation,
* plan execution evaluation,
* what worked,
* what failed,
* avoidable mistakes,
* lessons learned,
* final journal summary.

### Closing reasons

* `TAKE_PROFIT`
* `STOP_LOSS`
* `MANUAL_EXIT`
* `THESIS_INVALIDATED`
* `RISK_REDUCTION`
* `SESSION_CANCELLED`

---

## 5.10 `context_summary.schema.json`

Represents the compact memory supplied to the AI for the next analysis.

Its purpose is to preserve the “One Trade One Story” continuity without sending the entire raw session history to the AI on every request.

### Responsibilities

* session identity,
* current session status,
* latest confirmed position,
* original thesis,
* current thesis,
* active stop and target,
* latest market snapshot,
* latest orderbook conclusion,
* latest chart conclusion,
* latest AI assessment,
* important historical changes,
* user-confirmed actions,
* unresolved warnings,
* last update timestamp.

### Important rule

The context summary must preserve critical facts and user decisions.

It must not silently replace canonical database records.

---

## 5.11 `manifest.json`

Registers all production schemas and their versions.

### Responsibilities

* schema name,
* schema ID,
* version,
* local file path,
* schema category,
* root or shared classification,
* active status,
* compatible analysis types,
* dependency list.

---

## 6. Files Removed from the Production Plan

The following previously planned standalone schemas are no longer required as independent production files:

* `primitives.schema.json`
* `enums.schema.json`
* `base_analysis.schema.json`
* `missing_data.schema.json`
* `warnings.schema.json`
* `data_quality.schema.json`
* `executive_summary.schema.json`
* `market_summary.schema.json`
* `evidence_assessment.schema.json`
* `price_levels.schema.json`
* `orderbook_analysis.schema.json`
* `chart_analysis.schema.json`
* `change_summary.schema.json`
* `confidence.schema.json`
* `probability.schema.json`
* `risk.schema.json`
* `trading_plan.schema.json`
* `recommended_action.schema.json`
* `thesis_assessment.schema.json`
* `position_assessment.schema.json`
* `stop_loss.schema.json`
* `target_assessment.schema.json`
* `canonical_state_proposal.schema.json`
* `thesis_review.schema.json`
* `trading_journal.schema.json`

Their useful concepts may be reused as compact definitions inside the revised schemas.

They should not be used directly as the production AI output contract.

---

## 7. Handling Existing Complex Schemas

Existing schemas created under the previous plan should be moved to:

```text
schemas/experimental/v1/
```

Recommended directory:

```text
schemas/
├── production/
│   └── v1/
└── experimental/
    └── enterprise-draft/
```

They may be retained for:

* design reference,
* future enterprise features,
* validator ideas,
* audit concepts,
* possible later extraction of reusable definitions.

They must not be loaded by the production manifest.

---

## 8. Proposed Directory Structure

```text
schemas/
├── production/
│   └── v1/
│       ├── common.schema.json
│       ├── evidence.schema.json
│       ├── market_snapshot.schema.json
│       ├── trade_state.schema.json
│       ├── initial_analysis.schema.json
│       ├── watching_update.schema.json
│       ├── open_position_update.schema.json
│       ├── partial_exit_review.schema.json
│       ├── closing_analysis.schema.json
│       ├── context_summary.schema.json
│       └── manifest.json
│
├── examples/
│   └── v1/
│       ├── initial_analysis.example.json
│       ├── watching_update.example.json
│       ├── open_position_update.example.json
│       ├── partial_exit_review.example.json
│       ├── closing_analysis.example.json
│       └── context_summary.example.json
│
├── fixtures/
│   └── invalid/
│
└── experimental/
    └── enterprise-draft/
```

---

## 9. New Implementation Sequence

The revised schema implementation must follow this order.

### Phase 1 — Lock Real Product Payloads

Before creating production schemas, create example JSON payloads for:

1. `open_position_update.example.json`
2. `initial_analysis.example.json`
3. `watching_update.example.json`
4. `partial_exit_review.example.json`
5. `closing_analysis.example.json`
6. `context_summary.example.json`

The Open Position example is created first because it represents the most important and most frequently used analysis workflow.

### Phase 2 — Shared Foundations

Create:

1. `common.schema.json`
2. `evidence.schema.json`
3. `market_snapshot.schema.json`
4. `trade_state.schema.json`

### Phase 3 — Root Analysis Schemas

Create:

1. `open_position_update.schema.json`
2. `initial_analysis.schema.json`
3. `watching_update.schema.json`
4. `partial_exit_review.schema.json`
5. `closing_analysis.schema.json`

### Phase 4 — AI Memory and Registry

Create:

1. `context_summary.schema.json`
2. `manifest.json`

### Phase 5 — Validation

Create:

* valid fixtures,
* invalid fixtures,
* schema registry tests,
* cross-field domain validators,
* provider structured-output tests.

---

## 10. Why Open Position Comes First

The Open Position workflow is the clearest representation of the TradePilot AI product.

It already has a proven conversational structure based on real swing-trading analysis:

* morning update,
* midday update,
* closing update,
* longitudinal orderbook comparison,
* position review,
* TP realism review,
* next-session planning,
* probability and risk review.

By locking the Open Position payload first, the rest of the schema system can reuse its vocabulary and structure.

This prevents abstract schema design from controlling the product.

---

## 11. AI Output Design Rules

All root analysis schemas must follow these rules.

### 11.1 User-facing text

Narrative analysis fields must be written in Indonesian.

Technical field names and enum values remain in English.

Example:

```json
{
  "bias": "BULLISH",
  "summary": "Buyer masih bertahan, tetapi offer di area 2.900 menjadi hambatan utama."
}
```

### 11.2 Facts versus interpretation

The output should keep a practical distinction between:

* `observations`
* `interpretation`
* `conclusion`

This may be represented as simple arrays and narratives.

It does not require a complex statement-provenance graph.

### 11.3 Probabilities

Probability values use integers from `0` to `100`.

The AI must explain the main reason behind each important probability.

The following values do not need to total 100 because they may represent different events:

* bullish probability,
* target probability,
* downside probability.

### 11.4 Confidence

Confidence uses an integer from `0` to `100`.

Confidence reflects the quality of the analysis basis, not market direction.

A bullish analysis may still have low confidence.

### 11.5 Unknown values

Unknown values must use:

```json
null
```

The AI must not use:

```json
0
```

to represent unknown price, quantity, percentage, or probability values.

### 11.6 Recommended action

Recommended actions are analytical guidance.

They are not confirmed executions.

Examples:

* `WAIT`
* `ENTER_IF_CONFIRMED`
* `HOLD`
* `HOLD_WITH_CAUTION`
* `DO_NOT_ADD`
* `REDUCE_RISK`
* `CONSIDER_PARTIAL_EXIT`
* `REVIEW_EXIT`
* `CANCEL_SETUP`

### 11.7 User confirmation

Actual trade-state changes require explicit user confirmation.

Examples:

* position opened,
* entry price,
* quantity,
* stop-loss update,
* target update,
* partial exit,
* full exit.

---

## 12. Domain Validation

JSON Schema handles:

* required fields,
* data types,
* enum values,
* nullability,
* ranges,
* basic conditional requirements.

Application-level validators handle:

* high must be greater than or equal to low,
* stop loss must be logically positioned relative to entry,
* target must be logically positioned relative to entry,
* remaining quantity cannot exceed original quantity,
* realized and unrealized return calculations,
* distance-to-stop calculations,
* distance-to-target calculations,
* comparison with previous updates,
* probability changes,
* session-status transition rules,
* user-confirmation requirements,
* stale-state detection.

The JSON Schema must not attempt to encode every mathematical or workflow rule.

---

## 13. Versioning

Production schema versions use semantic versioning.

Initial version:

```text
1.0.0
```

Version changes:

* Patch: descriptions, examples, non-breaking validation improvements.
* Minor: backward-compatible optional fields or enum additions.
* Major: required-field changes, renamed fields, structural changes, or incompatible enum changes.

Each stored analysis must record:

* schema name,
* schema version,
* prompt version,
* model provider,
* model name,
* analysis timestamp.

---

## 14. Definition of Done

The revised schema implementation is complete when:

1. All 11 production schema files exist.
2. All six example payloads validate successfully.
3. Invalid fixtures fail for the expected reason.
4. Gemini output validates against the root schemas.
5. DeepSeek output validates against the same schemas.
6. Provider fallback does not alter the business contract.
7. Open Position output renders all expected UI sections.
8. The AI can compare the latest update with prior session context.
9. User-confirmed trade actions update canonical Trade State.
10. Closing analysis can reconstruct the complete trade story.

---

## 15. Immediate Next Step

The next implementation artifact must be:

```text
open_position_update.example.json
```

This example will define the actual final payload expected from the AI during an Open Position analysis.

It must be modeled directly from the swing-trading analysis workflow already used successfully in conversational sessions.

Only after this example is approved should the new production schemas be written.
