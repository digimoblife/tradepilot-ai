# **TradePilot AI — Product Rules**

**Document:** `PRODUCT_RULES.md`  
**Version:** 1.0  
**Status:** Final  
**Product Name:** TradePilot AI  
**Primary Reference:** `PRD.md`  
**Purpose:** Define mandatory product behavior, AI behavior, lifecycle rules, and non-negotiable operating constraints.

---

## **1\. Document Purpose**

This document translates the product principles defined in `PRD.md` into explicit operational rules.

These rules are mandatory for:

* frontend behavior;  
* backend behavior;  
* domain logic;  
* AI prompts;  
* AI response validation;  
* analysis workflows;  
* session lifecycle;  
* thesis management;  
* position management;  
* journal generation;  
* tests;  
* implementation tasks.

When another document conflicts with this document, the following priority applies:

1. `PRD.md`  
2. `PRODUCT_RULES.md`  
3. domain-specific engineering specifications  
4. implementation tasks  
5. source code

Any intentional deviation must be documented and approved before implementation.

---

# **2\. Core Product Rules**

## **RULE-PRODUCT-001 — One Trade Session Represents One Trade Story**

A Trade Session must represent:

* one ticker;  
* one trading setup;  
* one connected trading thesis;  
* one position lifecycle;  
* one final outcome.

A session must not contain unrelated trading ideas.

A new Trade Session must be created when:

* the previous session has been closed;  
* the previous setup was cancelled;  
* the user wants to trade the same ticker using a new thesis;  
* the market structure has changed enough that the previous setup is no longer relevant;  
* the user wants to evaluate an unrelated entry plan.

Additional entries and partial exits belonging to the same thesis may remain in the same session.

---

## **RULE-PRODUCT-002 — One Dedicated Page per Trade Session**

Each Trade Session must have one dedicated page.

The page must contain:

* session identity;  
* current lifecycle status;  
* current position;  
* active thesis;  
* current support and resistance;  
* current stop loss;  
* active targets;  
* latest analysis;  
* historical analysis versions;  
* uploaded evidence;  
* chronological timeline;  
* final journal after closure.

Analysis from other sessions must never appear inside the page except through an explicit historical reference.

---

## **RULE-PRODUCT-003 — TradePilot AI Is Not a Signal Scanner**

TradePilot AI must not behave as:

* an automatic stock scanner;  
* a daily recommendation generator;  
* an autonomous buy/sell signal engine;  
* an auto-trading service;  
* a broker execution platform.

The product may analyze a ticker only after the user creates or opens a Trade Session and provides the required context.

---

## **RULE-PRODUCT-004 — The User Controls Execution**

The system must not automatically:

* open a position;  
* add a position;  
* reduce a position;  
* move a stop loss;  
* change a target;  
* close a position;  
* create a broker order.

The AI may recommend an action, but every position mutation must be explicitly confirmed or recorded by the user.

---

## **RULE-PRODUCT-005 — User-Facing Analysis Must Be in Bahasa Indonesia**

All user-facing analysis narrative must be written in Bahasa Indonesia.

This includes:

* summaries;  
* explanations;  
* warnings;  
* trading plans;  
* thesis descriptions;  
* position assessments;  
* comparison narratives;  
* journal content.

Internal identifiers remain in English.

The application must not display raw internal enum values as the primary user-facing label.

Example:

Internal value: INTACT\_BUT\_WEAKENING  
User-facing label: Thesis Masih Valid, tetapi Mulai Melemah

---

## **RULE-PRODUCT-006 — Engineering Artifacts Must Be in English**

All engineering-facing materials must be written in English, including:

* documentation;  
* prompts;  
* schemas;  
* tests;  
* API contracts;  
* source-code identifiers;  
* enums;  
* database fields;  
* implementation tasks;  
* configuration keys.

---

# **3\. Trade Session Lifecycle Rules**

## **RULE-LIFECYCLE-001 — Every Session Must Have One Valid Status**

A Trade Session must always have exactly one valid lifecycle status.

Allowed values:

* `DRAFT`  
* `READY_FOR_ANALYSIS`  
* `ANALYZING`  
* `WATCHING`  
* `OPEN_POSITION`  
* `PARTIALLY_CLOSED`  
* `CLOSED_TAKE_PROFIT`  
* `CLOSED_STOP_LOSS`  
* `CLOSED_MANUAL`  
* `CANCELLED`  
* `ARCHIVED`

---

## **RULE-LIFECYCLE-002 — DRAFT Status**

A session remains `DRAFT` when one or more required initial inputs are missing.

Required initial inputs:

* ticker;  
* orderbook screenshot;  
* three-month chart screenshot;  
* six-month chart screenshot.

The user may save incomplete sessions.

An AI initial analysis must not run while required evidence is missing.

---

## **RULE-LIFECYCLE-003 — READY\_FOR\_ANALYSIS Status**

A session becomes `READY_FOR_ANALYSIS` when:

* ticker is valid;  
* all required initial evidence exists;  
* no initial analysis is processing;  
* no valid initial analysis has been completed.

---

## **RULE-LIFECYCLE-004 — ANALYZING Is a Temporary State**

A session may temporarily enter `ANALYZING` while an AI analysis job is running.

The system must preserve the previous stable lifecycle state.

After completion:

* initial analysis normally returns the session to `WATCHING`;  
* monitoring analysis normally returns it to the previous position state;  
* failed jobs return the session to the previous stable state.

The application must not lose the previous state when analysis fails.

---

## **RULE-LIFECYCLE-005 — WATCHING Status**

A session is `WATCHING` when:

* initial analysis exists;  
* the setup remains active;  
* no position has been opened.

While watching, the user may:

* upload updates;  
* run follow-up analysis;  
* modify the planned entry;  
* modify the proposed stop or target;  
* cancel the setup;  
* open the position.

---

## **RULE-LIFECYCLE-006 — OPEN\_POSITION Requirements**

A session may enter `OPEN_POSITION` only when the system has:

* at least one active entry;  
* an entry timestamp;  
* an entry price;  
* an active stop loss;  
* at least one active target.

If quantity is not provided, the position may still be tracked without absolute profit and loss values.

---

## **RULE-LIFECYCLE-007 — PARTIALLY\_CLOSED Requirements**

A session becomes `PARTIALLY_CLOSED` when:

* at least one exit has been recorded;  
* a positive active quantity remains;  
* the trade lifecycle is not complete.

The active thesis must continue to be evaluated for the remaining quantity.

---

## **RULE-LIFECYCLE-008 — Closed Sessions Are Immutable in Lifecycle**

A fully closed session must use one of:

* `CLOSED_TAKE_PROFIT`  
* `CLOSED_STOP_LOSS`  
* `CLOSED_MANUAL`

After closure:

* no new active position may be opened in the same session;  
* no additional entry may be added;  
* historical corrections may be allowed through an explicit correction workflow;  
* new trading activity for the same ticker requires a new Trade Session.

---

## **RULE-LIFECYCLE-009 — CANCELLED Is Only for Pre-Entry Setups**

A session may become `CANCELLED` only if no active position was opened.

A session with a historical entry cannot be cancelled. It must be closed with an appropriate exit status.

---

## **RULE-LIFECYCLE-010 — ARCHIVED Does Not Delete Data**

Archiving must:

* hide the session from active views;  
* preserve all data;  
* preserve evidence;  
* preserve journal content;  
* preserve audit history.

Archiving must not modify the final trade outcome.

---

# **4\. Evidence Rules**

## **RULE-EVIDENCE-001 — Required Initial Evidence**

Initial analysis requires:

* one orderbook screenshot;  
* one three-month chart screenshot;  
* one six-month chart screenshot.

The system may allow additional evidence, but these three remain the minimum requirement for MVP.

---

## **RULE-EVIDENCE-002 — Original Evidence Must Be Preserved**

The original uploaded file must never be overwritten.

Generated derivatives may include:

* thumbnail;  
* compressed preview;  
* normalized image;  
* AI-processing image.

All derivatives must remain linked to the original evidence record.

---

## **RULE-EVIDENCE-003 — Evidence Must Be Timestamped**

Every evidence item must store:

* upload timestamp;  
* user-provided market timestamp when available;  
* evidence type;  
* associated Trade Session;  
* associated update classification.

When market timestamp is unknown, the system must not assume it equals the upload timestamp.

---

## **RULE-EVIDENCE-004 — Evidence Must Be Classified**

Every evidence item must use one evidence type.

Allowed MVP types include:

* `ORDERBOOK_SCREENSHOT`  
* `CHART_THREE_MONTH`  
* `CHART_SIX_MONTH`  
* `CHART_DAILY`  
* `CHART_INTRADAY`  
* `BROKER_SUMMARY`  
* `FOREIGN_FLOW`  
* `NEWS_SCREENSHOT`  
* `CUSTOM_IMAGE`  
* `USER_NOTE`  
* `MARKET_DATA_SNAPSHOT`

---

## **RULE-EVIDENCE-005 — Unreadable Evidence Must Not Be Treated as Reliable**

When evidence is unclear, cropped, incomplete, or unreadable:

* the AI must state the limitation;  
* unreadable values must remain null or unavailable;  
* confidence must be reduced when the missing information is important;  
* the AI must not infer exact numbers without visible support.

---

## **RULE-EVIDENCE-006 — Evidence Is Append-Only by Default**

Uploaded evidence should be append-only.

A user may mark evidence as:

* incorrect;  
* duplicate;  
* irrelevant;  
* superseded.

Evidence should not be permanently deleted from audit history unless an explicit administrative deletion is performed.

---

# **5\. AI Analysis Rules**

## **RULE-AI-001 — Every Analysis Must Use Structured Output**

The AI must return a response matching the active schema.

Free-form text alone is not accepted as a valid analysis result.

Structured output must use:

* English keys;  
* English enum values;  
* Bahasa Indonesia narrative values.

---

## **RULE-AI-002 — The Latest Screenshot Must Never Be Analyzed in Isolation**

Every follow-up analysis must include:

* current canonical session state;  
* active thesis;  
* latest valid analysis;  
* relevant historical analysis;  
* relevant evidence history;  
* active position data;  
* current stop loss;  
* current targets;  
* latest uploaded evidence.

The system must not send only the latest screenshot to the model.

---

## **RULE-AI-003 — Facts and Interpretation Must Be Separated**

The AI must distinguish:

1. visible facts;  
2. extracted numbers;  
3. technical interpretations;  
4. assumptions;  
5. uncertainty;  
6. missing information.

Statements must not present interpretation as certainty.

---

## **RULE-AI-004 — AI Must Not Invent Market Data**

The AI must not invent:

* price;  
* volume;  
* bid quantity;  
* offer quantity;  
* average price;  
* OHLC values;  
* support;  
* resistance;  
* profit and loss;  
* timestamps;  
* ticker identity.

If a value cannot be read or calculated, it must be reported as unavailable.

---

## **RULE-AI-005 — AI Must Provide Technical Reasoning**

Every recommendation must include:

* reason;  
* supporting evidence;  
* risk;  
* invalidation condition;  
* next action.

A recommendation without technical reasoning must fail response-quality validation.

---

## **RULE-AI-006 — AI Must Avoid Absolute Predictions**

The AI must not use claims equivalent to:

* the price will definitely rise;  
* the target will certainly be reached;  
* this trade is guaranteed;  
* there is no risk;  
* the stock cannot fall.

The AI must use probabilistic and conditional language.

---

## **RULE-AI-007 — AI Must Not Provide Unsupported BUY, HOLD, or SELL Outputs**

The system may display an action recommendation, but it must include:

* action;  
* rationale;  
* required condition;  
* risk;  
* invalidation.

A standalone action label is not sufficient.

---

## **RULE-AI-008 — AI Must Respect User Position State**

Analysis must differ based on session state.

For `WATCHING`, the AI focuses on:

* setup quality;  
* entry conditions;  
* cancellation conditions;  
* chase risk.

For `OPEN_POSITION` or `PARTIALLY_CLOSED`, the AI focuses on:

* position health;  
* thesis validity;  
* target realism;  
* stop-loss risk;  
* hold, reduce, partial profit, or exit scenarios.

For closed sessions, the AI must not give active trade management instructions.

---

## **RULE-AI-009 — AI Must Acknowledge Insufficient Context**

When evidence is insufficient, the AI must:

* state what is missing;  
* lower confidence;  
* avoid precise conclusions;  
* explain which additional evidence would be useful.

The AI must not compensate for missing data by becoming more speculative.

---

## **RULE-AI-010 — AI Must Keep Narrative Output in Bahasa Indonesia**

All user-facing narrative fields must use natural Bahasa Indonesia.

English trading terms may be used when common and helpful, but they should be explained when ambiguity is possible.

The AI should prefer:

* “tekanan jual” instead of unexplained “selling pressure”;  
* “penyerapan offer” with context instead of unexplained “absorption”;  
* “thesis masih valid” when the term thesis is used consistently in the product.

---

# **6\. Longitudinal Analysis Rules**

## **RULE-LONGITUDINAL-001 — Every Update Must Compare Against History**

Every follow-up analysis must explicitly compare the latest state with:

* the previous analysis;  
* the previous relevant evidence;  
* the initial thesis;  
* the current position plan.

---

## **RULE-LONGITUDINAL-002 — Every Update Must Contain a Change Summary**

Every follow-up analysis must contain a section equivalent to:

**What Changed Since the Previous Update**

The section must describe material changes in:

* price;  
* average price;  
* bid strength;  
* offer pressure;  
* support;  
* resistance;  
* orderbook imbalance;  
* chart structure when updated;  
* thesis status;  
* confidence;  
* probabilities;  
* risk;  
* recommended action.

---

## **RULE-LONGITUDINAL-003 — No Change Must Also Be Stated**

When no material change exists, the AI must explicitly state that the condition remains broadly unchanged.

The AI must not manufacture differences to make each update appear new.

---

## **RULE-LONGITUDINAL-004 — Historical Context Must Be Relevant**

The context builder must prioritize:

* current canonical state;  
* active thesis;  
* most recent analysis;  
* significant thesis-change events;  
* entry and exit events;  
* active stop and targets;  
* recent comparable evidence;  
* initial evidence.

Low-value repetitive history may be summarized.

---

## **RULE-LONGITUDINAL-005 — Historical Summary Must Not Replace Critical Evidence**

Context summarization may reduce token usage, but the system must preserve:

* original thesis;  
* current thesis;  
* invalidation level;  
* entry;  
* stop loss;  
* targets;  
* meaningful thesis changes;  
* critical warnings;  
* significant analysis contradictions.

---

## **RULE-LONGITUDINAL-006 — AI Must Not Forget User Decisions**

The context must include user decisions such as:

* actual entry;  
* stop-loss changes;  
* target changes;  
* partial exits;  
* manual overrides;  
* notes explaining user intent.

The AI must not recommend based on outdated position parameters.

---

# **7\. Trading Thesis Rules**

## **RULE-THESIS-001 — Every Analyzed Session Must Have One Active Thesis**

After initial analysis, the session must have one canonical active thesis.

The thesis must include:

* directional bias;  
* technical rationale;  
* supporting evidence;  
* key support;  
* key resistance;  
* invalidation condition;  
* expected scenario;  
* confidence.

---

## **RULE-THESIS-002 — Thesis Status Must Use a Controlled Enum**

Allowed values:

* `STRENGTHENING`  
* `INTACT`  
* `INTACT_BUT_WEAKENING`  
* `UNDER_REVIEW`  
* `INVALIDATED`

No other thesis status may be stored without a schema migration.

---

## **RULE-THESIS-003 — STRENGTHENING**

Use `STRENGTHENING` when new evidence materially supports the active thesis.

Examples:

* support becomes stronger;  
* bids move upward and remain persistent;  
* resistance is absorbed;  
* price confirms breakout;  
* volume supports the expected move;  
* conflicting risk decreases.

The AI must explain what strengthened.

---

## **RULE-THESIS-004 — INTACT**

Use `INTACT` when:

* the original thesis remains valid;  
* no major confirmation or deterioration has occurred;  
* current movement remains within the expected scenario.

A minor pullback does not automatically weaken the thesis.

---

## **RULE-THESIS-005 — INTACT\_BUT\_WEAKENING**

Use `INTACT_BUT_WEAKENING` when:

* invalidation has not occurred;  
* risk has increased;  
* supporting evidence is weakening;  
* probability of target achievement has declined;  
* support is being tested more aggressively.

The AI must state what would restore strength and what would cause further deterioration.

---

## **RULE-THESIS-006 — UNDER\_REVIEW**

Use `UNDER_REVIEW` when:

* evidence is materially conflicting;  
* a key level is being tested but not confirmed broken;  
* available evidence is insufficient for a stable conclusion;  
* a possible invalidation is developing.

This status is temporary.

The next analysis must prioritize resolving the uncertainty.

---

## **RULE-THESIS-007 — INVALIDATED**

Use `INVALIDATED` only when meaningful evidence shows that the active thesis no longer holds.

Examples may include:

* confirmed major support break;  
* material change in price structure;  
* failed breakout followed by sustained weakness;  
* dominant seller pressure aligned with chart deterioration;  
* risk-to-reward no longer supports the original plan;  
* original setup conditions no longer exist.

The AI must identify the specific invalidation evidence.

---

## **RULE-THESIS-008 — Thesis Changes Must Be Versioned**

Every thesis change must create a permanent history record containing:

* previous thesis;  
* new thesis;  
* previous status;  
* new status;  
* change reason;  
* supporting evidence;  
* related analysis version;  
* confidence before;  
* confidence after;  
* timestamp.

---

## **RULE-THESIS-009 — Thesis Cannot Change Without Explanation**

If the latest analysis contradicts the canonical thesis without a valid change explanation:

* the result must be flagged;  
* the canonical thesis must not be overwritten automatically;  
* the analysis may require retry or review.

---

## **RULE-THESIS-010 — Thesis Invalidation Must Affect the Trading Plan**

When the thesis becomes `INVALIDATED`, the analysis must:

* stop using the previous bullish or bearish base case as active;  
* explain the required defensive action;  
* reassess the stop and exit plan;  
* avoid recommending blind holding;  
* avoid moving the stop farther only to preserve the position.

---

# **8\. Support and Resistance Rules**

## **RULE-LEVEL-001 — Every Important Level Requires a Reason**

Support and resistance levels must include a technical basis.

Possible bases:

* visible orderbook concentration;  
* repeated price reaction;  
* swing high;  
* swing low;  
* breakout level;  
* breakdown level;  
* historical range boundary;  
* volume-supported zone;  
* average-price area;  
* psychological price level.

---

## **RULE-LEVEL-002 — Levels Must Be Classified**

The system should distinguish:

* immediate support;  
* major support;  
* thesis invalidation;  
* immediate resistance;  
* major resistance;  
* breakout confirmation.

---

## **RULE-LEVEL-003 — Level Changes Must Be Explained**

When a support or resistance level changes materially, the AI must explain:

* previous level;  
* new level;  
* reason for change;  
* whether the change reflects price movement, new evidence, or corrected extraction.

---

## **RULE-LEVEL-004 — Orderbook Levels Must Not Be Treated as Permanent**

Orderbook support and resistance are temporary observations.

The AI must not treat a large queue as guaranteed protection or guaranteed resistance.

---

# **9\. Entry Rules**

## **RULE-ENTRY-001 — AI Entry Is a Plan, Not an Executed Position**

Before user confirmation, all entry values are proposed entry plans.

The system must not treat a proposed entry as an actual entry.

---

## **RULE-ENTRY-002 — Entry Recommendations Must Include Conditions**

An entry recommendation must include:

* entry zone or trigger;  
* technical reason;  
* confirmation condition;  
* invalidation condition;  
* chase limit;  
* risk consideration.

---

## **RULE-ENTRY-003 — The System Must Record Actual Entry Separately**

The actual user entry must be stored separately from the AI-recommended entry.

The system must preserve:

* planned entry;  
* actual entry;  
* difference;  
* user notes.

---

## **RULE-ENTRY-004 — Additional Entries Require Risk Review**

Before recommending an additional entry, the AI must assess:

* whether thesis remains valid;  
* whether the addition improves or worsens average entry;  
* current downside to stop;  
* total position risk;  
* whether the action is averaging up or averaging down;  
* whether the user is reacting emotionally.

The AI must not casually recommend averaging down.

---

# **10\. Stop-Loss Rules**

## **RULE-STOP-001 — Every Open Position Must Have an Active Stop Loss**

A position cannot enter `OPEN_POSITION` without an active stop loss.

---

## **RULE-STOP-002 — Stop Loss Must Have Technical Basis**

A stop-loss recommendation must include:

* level;  
* technical reason;  
* associated invalidation;  
* estimated downside;  
* risk warning.

A percentage-only stop without technical basis is insufficient.

---

## **RULE-STOP-003 — Stop-Loss Changes Must Be Explicit**

The AI must not silently change the stop loss.

Every recommended change must include:

* old stop;  
* proposed stop;  
* reason;  
* risk impact;  
* thesis impact.

The user must explicitly apply the change.

---

## **RULE-STOP-004 — Widening the Stop Requires a Warning**

When the user or AI proposes a wider stop, the system must explain:

* additional risk;  
* new downside;  
* whether the original thesis has changed;  
* whether widening is technically justified.

Widening a stop only to avoid realizing a loss is not a valid technical reason.

---

## **RULE-STOP-005 — Invalidated Thesis Must Not Be Protected by an Arbitrarily Wider Stop**

When the thesis is invalidated, the AI must not recommend moving the stop farther simply to keep the position open.

---

# **11\. Target-Profit Rules**

## **RULE-TARGET-001 — Every Open Position Must Have at Least One Active Target**

The user must record at least one target before opening the position.

---

## **RULE-TARGET-002 — Target Must Have Technical Basis**

Targets must be linked to:

* resistance;  
* historical structure;  
* measured price range;  
* breakout objective;  
* risk-to-reward logic;  
* another explicit technical basis.

---

## **RULE-TARGET-003 — Every Open-Position Analysis Must Assess Target Realism**

Every open-position update must answer:

* Is the active target still realistic?  
* Has target probability increased or decreased?  
* What is the nearest obstacle?  
* What conditions are required to reach the target?  
* Should the target remain unchanged?

---

## **RULE-TARGET-004 — Target Changes Must Be Explained**

The AI must not silently change a target.

Every proposed change must include:

* previous target;  
* proposed target;  
* technical reason;  
* probability impact;  
* risk-to-reward impact.

---

## **RULE-TARGET-005 — Higher Targets Require New Confirmation**

A target may be raised only when new evidence supports stronger continuation.

Examples:

* resistance breakout;  
* sustained volume;  
* stronger orderbook structure;  
* new chart structure;  
* reduced downside risk.

---

## **RULE-TARGET-006 — Lower Targets Must Not Hide Thesis Failure**

Lowering a target is valid only when:

* the thesis remains valid;  
* the expected upside has decreased;  
* new resistance or weakness justifies the change.

If the thesis is invalidated, the AI must discuss exit risk rather than repeatedly lowering the target.

---

# **12\. Position Assessment Rules**

## **RULE-POSITION-001 — Every Open-Position Analysis Must Address the User’s Actual Position**

The analysis must consider:

* actual average entry;  
* current price when available;  
* unrealized result;  
* active stop;  
* active targets;  
* remaining quantity;  
* previous partial exits;  
* user-specific risk.

---

## **RULE-POSITION-002 — Open-Position Analysis Must Include a Clear Health Assessment**

Allowed position-health values may include:

* `HEALTHY`  
* `HEALTHY_BUT_VOLATILE`  
* `WEAKENING`  
* `HIGH_RISK`  
* `EXIT_CONDITION_TRIGGERED`

The final enum will be defined in the relevant schema specification.

---

## **RULE-POSITION-003 — The AI Must Explain Whether Holding Is Still Rational**

The AI must distinguish between:

* holding because the thesis remains valid;  
* holding because confirmation is pending;  
* holding despite increasing risk;  
* emotionally refusing to exit.

---

## **RULE-POSITION-004 — Partial Profit Recommendations Require Rationale**

A partial-profit recommendation must include:

* resistance or risk reason;  
* suggested purpose;  
* effect on remaining position;  
* treatment of stop loss;  
* conditions for holding the remainder.

---

## **RULE-POSITION-005 — Exit Recommendations Require Objective Conditions**

An exit recommendation must reference:

* thesis invalidation;  
* stop-loss trigger;  
* confirmed technical weakness;  
* unacceptable risk;  
* completed target;  
* another explicit rule.

---

# **13\. Confidence Rules**

## **RULE-CONFIDENCE-001 — Confidence Measures Analysis Reliability**

Confidence does not represent:

* probability of profit;  
* probability of price increase;  
* certainty of target achievement.

Confidence represents the reliability of the analysis given the available evidence.

---

## **RULE-CONFIDENCE-002 — Confidence Must Be Between 0 and 100**

Allowed classifications:

* `LOW`: 0–39  
* `MODERATE`: 40–69  
* `HIGH`: 70–100

---

## **RULE-CONFIDENCE-003 — Every Confidence Score Requires Explanation**

The analysis must include:

* confidence drivers;  
* confidence reducers;  
* evidence quality;  
* comparison with the previous score;  
* explanation of material change.

---

## **RULE-CONFIDENCE-004 — Confidence Must Decrease When Evidence Quality Declines**

Confidence should decrease when:

* screenshots are unreadable;  
* required data is missing;  
* signals conflict;  
* market timestamps are uncertain;  
* historical comparison is unavailable;  
* AI extraction is unreliable.

---

## **RULE-CONFIDENCE-005 — Confidence Must Not Increase Without Supporting Reasons**

An increased score must be supported by improved evidence, confirmation, or reduced uncertainty.

---

# **14\. Probability Rules**

## **RULE-PROBABILITY-001 — Probability Values Must Be Analytical Estimates**

Probability values are not guaranteed statistical forecasts.

The user-facing analysis must communicate this limitation.

---

## **RULE-PROBABILITY-002 — Required Probability Set**

Open-position analysis must include:

* target achievement probability;  
* pullback probability;  
* stop-loss touch probability;  
* thesis remaining valid probability;  
* thesis invalidation probability.

Initial analysis must also include bullish continuation probability.

---

## **RULE-PROBABILITY-003 — Related Probabilities Must Be Logically Coherent**

Probabilities do not always need to sum to 100 because events may overlap.

However, the result must avoid obvious contradictions.

Example of invalid logic:

* target probability: 85%;  
* thesis invalidation probability: 80%;  
* no explanation of overlapping scenarios.

---

## **RULE-PROBABILITY-004 — Probability Changes Must Be Explained**

Every material probability change must include:

* previous value;  
* current value;  
* change direction;  
* evidence;  
* reasoning.

---

## **RULE-PROBABILITY-005 — Avoid False Precision**

Probability values should not imply unjustified mathematical precision.

The final specification may use whole percentages or predefined bands.

---

# **15\. Trading Plan Rules**

## **RULE-PLAN-001 — Every Analysis Must End With an Actionable Plan**

The trading plan must state what the user should monitor or do next.

---

## **RULE-PLAN-002 — Initial Analysis Must Include Three Scenarios**

Required scenarios:

* bullish;  
* neutral;  
* bearish.

Each scenario must include:

* trigger;  
* expected behavior;  
* user action;  
* invalidation or next checkpoint.

---

## **RULE-PLAN-003 — Open-Position Plans Must Match the Update Time**

Examples:

* morning plan;  
* plan until midday;  
* plan until market close;  
* plan for the next trading day.

The plan must not use vague timing when the update classification is known.

---

## **RULE-PLAN-004 — Plan Must Reference Actual Levels**

When reliable values are available, the plan must reference:

* support;  
* resistance;  
* stop loss;  
* target;  
* confirmation level.

When values are unavailable, the AI must state the limitation.

---

## **RULE-PLAN-005 — Plan Must Include “Do Not” Conditions**

The plan should explicitly state prohibited or discouraged actions when relevant.

Examples:

* do not chase above a defined level;  
* do not average down while thesis is weakening;  
* do not widen stop without new technical evidence;  
* do not assume a large bid queue will remain.

---

# **16\. Analysis Versioning Rules**

## **RULE-VERSION-001 — Every Completed Analysis Is Immutable**

A completed analysis version must not be overwritten.

Corrections require:

* a new analysis version;  
* a correction reason;  
* a reference to the corrected version.

---

## **RULE-VERSION-002 — Analysis Version Must Record Its Inputs**

Each analysis version must record:

* prompt version;  
* AI provider;  
* model;  
* schema version;  
* evidence IDs;  
* context-summary version;  
* session state;  
* position snapshot;  
* generation timestamp.

---

## **RULE-VERSION-003 — Only Validated Analyses Become Canonical**

An analysis becomes the latest canonical analysis only after:

* provider call succeeds;  
* structured output parses successfully;  
* schema validation passes;  
* required fields exist;  
* critical contradictions are handled.

---

## **RULE-VERSION-004 — Failed Analyses Must Remain Traceable**

Failed analysis jobs must record:

* failure stage;  
* error type;  
* provider;  
* model;  
* retry count;  
* timestamp.

A failed result must not replace the latest valid analysis.

---

# **17\. Contradiction Rules**

## **RULE-CONTRADICTION-001 — Material Contradictions Must Be Detected**

The system should detect contradictions involving:

* thesis direction;  
* thesis status;  
* support;  
* resistance;  
* stop loss;  
* targets;  
* recommended action;  
* confidence;  
* probability;  
* position health.

---

## **RULE-CONTRADICTION-002 — Contradictions Require Resolution**

When a contradiction exists, the AI must:

* explain the new evidence;  
* state why the previous assessment changed;  
* preserve the old assessment if evidence is insufficient;  
* mark uncertainty when appropriate.

---

## **RULE-CONTRADICTION-003 — Contradictory AI Output Must Not Automatically Overwrite Canonical State**

When contradiction validation fails:

* the analysis may be stored as non-canonical;  
* the job may be retried;  
* the previous canonical state must remain active.

---

# **18\. Journal Rules**

## **RULE-JOURNAL-001 — Closed Positions Must Generate a Journal**

A fully closed position must become eligible for AI Trading Journal generation.

---

## **RULE-JOURNAL-002 — Journal Must Use the Full Session History**

The journal must use:

* initial evidence;  
* initial thesis;  
* all thesis changes;  
* all analyses;  
* all entries;  
* all exits;  
* all stop changes;  
* all target changes;  
* user notes;  
* final result.

---

## **RULE-JOURNAL-003 — Journal Must Separate AI Performance and User Execution**

The journal must evaluate separately:

* analysis quality;  
* thesis quality;  
* AI warning quality;  
* user entry quality;  
* user exit quality;  
* discipline;  
* deviations from plan.

---

## **RULE-JOURNAL-004 — Journal Must Not Rewrite History**

The journal must not present later knowledge as if it were known at the time of the original analysis.

It must distinguish:

* information available at the time;  
* later developments;  
* hindsight conclusions.

---

## **RULE-JOURNAL-005 — Journal Narrative Must Be in Bahasa Indonesia**

Internal journal fields remain in English.

All user-facing review content must be in Bahasa Indonesia.

---

# **19\. UI and Interaction Rules**

## **RULE-UI-001 — The Product Must Not Use a Chat-First Layout**

The primary Trade Session interface must use:

* structured sections;  
* cards;  
* tables;  
* timeline;  
* status badges;  
* comparison panels;  
* evidence gallery;  
* version history.

A conversation composer may exist, but it must not be the main interface.

---

## **RULE-UI-002 — Latest State Must Be Immediately Visible**

The Trade Session page must prominently show:

* status;  
* active thesis;  
* position health;  
* entry;  
* stop loss;  
* target;  
* confidence;  
* key probabilities;  
* latest recommended action.

---

## **RULE-UI-003 — Historical Evidence Must Be Accessible**

The user must be able to inspect:

* earlier screenshots;  
* earlier analysis versions;  
* earlier plans;  
* thesis changes;  
* stop and target changes.

---

## **RULE-UI-004 — Internal Enums Must Have Indonesian Labels**

The UI must map internal values to clear Bahasa Indonesia labels.

Example:

OPEN\_POSITION → Posisi Terbuka  
PARTIALLY\_CLOSED → Ditutup Sebagian  
INVALIDATED → Thesis Tidak Valid

---

## **RULE-UI-005 — Risk Warnings Must Be Visually Distinct**

Warnings involving:

* thesis invalidation;  
* stop-loss risk;  
* widened stop;  
* missing evidence;  
* high uncertainty;  
* provider failure;

must be visually distinguishable from normal analysis.

---

# **20\. AI Provider Rules**

## **RULE-PROVIDER-001 — Provider Abstraction Is Mandatory**

Application logic must not call Gemini or DeepSeek directly from domain services.

All provider calls must pass through a common adapter interface.

---

## **RULE-PROVIDER-002 — Provider Capability Must Be Verified**

Before assigning a task, the system must verify whether the selected provider and model support:

* image input;  
* structured output;  
* sufficient context size;  
* required response length.

---

## **RULE-PROVIDER-003 — Fallback Must Not Create Duplicate Canonical Results**

When fallback is enabled:

* the primary attempt must be recorded;  
* the fallback attempt must be recorded;  
* only one validated result becomes canonical;  
* duplicate timeline events must not be created.

---

## **RULE-PROVIDER-004 — Prompt and Schema Must Be Provider-Neutral**

Prompts and schemas should avoid unnecessary provider-specific assumptions.

Provider-specific formatting may exist only in adapter-level code.

---

# **21\. Background Job Rules**

## **RULE-JOB-001 — AI Analysis Must Run as a Background Job**

The user interface must not block while analysis is running.

---

## **RULE-JOB-002 — Jobs Must Be Idempotent**

Retrying a job must not duplicate:

* analysis versions;  
* thesis events;  
* timeline events;  
* evidence records;  
* position changes.

---

## **RULE-JOB-003 — Job State Must Be Visible**

The UI must show meaningful states such as:

* queued;  
* processing;  
* retrying;  
* completed;  
* failed.

---

## **RULE-JOB-004 — Failed Jobs Must Be Retryable**

A failed AI job must not damage the Trade Session.

The user must be able to retry when appropriate.

---

# **22\. Security and Audit Rules**

## **RULE-SECURITY-001 — All Trade Data Requires Authentication**

Trade Sessions, evidence, analyses, journals, and APIs must not be publicly accessible.

---

## **RULE-SECURITY-002 — Secrets Must Never Reach the Browser**

AI API keys and server credentials must remain server-side.

---

## **RULE-SECURITY-003 — Sensitive Values Must Not Be Logged**

Logs must not expose:

* API keys;  
* passwords;  
* authentication tokens;  
* private file URLs;  
* unnecessary private trading notes.

---

## **RULE-AUDIT-001 — Critical Changes Require Audit Records**

Audit history is required for:

* lifecycle status;  
* thesis;  
* entry;  
* additional entry;  
* stop loss;  
* target;  
* partial exit;  
* final exit;  
* AI provider;  
* prompt version;  
* analysis correction.

---

# **23\. Data Integrity Rules**

## **RULE-DATA-001 — Canonical State Must Be Explicit**

The system must maintain one canonical value for:

* session status;  
* active thesis;  
* active stop;  
* active targets;  
* active position;  
* latest valid analysis;  
* latest confidence;  
* latest probabilities.

Historical records must remain separate from canonical current state.

---

## **RULE-DATA-002 — Historical Records Must Be Append-Only Where Possible**

The system should favor event and version records over destructive updates.

---

## **RULE-DATA-003 — Calculated Values Must Be Reproducible**

Calculated values such as:

* weighted average entry;  
* realized profit and loss;  
* unrealized profit and loss;  
* distance to stop;  
* distance to target;

must be reproducible from stored source data.

---

## **RULE-DATA-004 — Unknown Values Must Remain Unknown**

The system must use null or an explicit unavailable state rather than fabricated defaults.

---

# **24\. Error Handling Rules**

## **RULE-ERROR-001 — User Errors Must Be Actionable**

Error messages displayed to the user must explain:

* what failed;  
* why it may have failed;  
* what the user can do next.

User-facing errors must be in Bahasa Indonesia.

---

## **RULE-ERROR-002 — Internal Error Codes Must Be in English**

Internal error codes must remain stable and English-based.

Example:

EVIDENCE\_REQUIRED  
ANALYSIS\_SCHEMA\_INVALID  
AI\_PROVIDER\_TIMEOUT  
POSITION\_ALREADY\_CLOSED  
INVALID\_STATUS\_TRANSITION

---

## **RULE-ERROR-003 — AI Failure Must Not Remove User Data**

Provider or parsing failures must not delete:

* uploads;  
* notes;  
* position data;  
* prior analyses;  
* timeline history.

---

# **25\. Prohibited Product Behavior**

The following behavior is explicitly prohibited:

1. analyzing only the latest screenshot without session history;  
2. silently changing the thesis;  
3. silently changing stop loss;  
4. silently changing target profit;  
5. inventing unreadable market data;  
6. guaranteeing profit;  
7. opening or closing trades automatically;  
8. mixing multiple trade stories into one session;  
9. overwriting completed analyses;  
10. deleting historical changes without audit history;  
11. presenting raw model output without schema validation;  
12. presenting English analysis narrative as the normal dashboard output;  
13. treating orderbook queues as guaranteed market intent;  
14. encouraging the user to ignore an invalidated thesis;  
15. widening a stop solely to avoid realizing a loss;  
16. generating an AI Trading Journal without using the full session history;  
17. allowing a closed session to become an active position again;  
18. treating a planned entry as an actual entry;  
19. replacing the latest valid analysis with a failed or invalid result;  
20. hiding uncertainty when evidence is incomplete.

---

# **26\. Required Analysis Output Sections**

## **26.1 Initial Analysis**

Every initial analysis must include:

1. Executive Summary  
2. Today’s Market Summary  
3. Orderbook Analysis  
4. Three-Month Chart Analysis  
5. Six-Month Chart Analysis  
6. Support and Resistance  
7. Entry Plan  
8. Stop Loss  
9. Target Profit  
10. Confidence Assessment  
11. Probability Assessment  
12. Bullish Scenario  
13. Neutral Scenario  
14. Bearish Scenario  
15. Risks and Missing Data  
16. Recommended Next Action

---

## **26.2 Watching Update**

Every watching update must include:

1. Latest Market Summary  
2. Latest Orderbook Assessment  
3. What Changed Since the Previous Update  
4. Setup Quality  
5. Entry Realism  
6. Thesis Status  
7. Updated Confidence  
8. Updated Probabilities  
9. Updated Trading Plan  
10. Entry or Cancellation Conditions

---

## **26.3 Open Position Update**

Every open-position update must include:

1. Latest Market Summary  
2. What the Orderbook Shows  
3. What Changed Since the Previous Update  
4. Current Position Assessment  
5. Thesis Status  
6. Target Realism Assessment  
7. Stop-Loss Assessment  
8. Updated Confidence  
9. Updated Probabilities  
10. Current Risk Level  
11. Trading Plan  
12. Clear Recommended Action

---

## **26.4 Closing Analysis**

Every closing analysis must include:

1. Exit Summary  
2. Final Trade Result  
3. Final Thesis Assessment  
4. Exit Quality  
5. Plan Compliance  
6. Significant Timeline Events  
7. Preliminary Lessons  
8. Journal Generation Status

---

# **27\. Minimum Quality Validation**

An AI analysis must be rejected or flagged when:

* required sections are missing;  
* structured output is invalid;  
* narrative fields are not in Bahasa Indonesia;  
* unsupported exact values are introduced;  
* thesis status is missing;  
* confidence lacks explanation;  
* probability lacks reasoning;  
* open-position analysis ignores actual entry;  
* latest update lacks historical comparison;  
* the recommendation lacks an invalidation condition;  
* a material thesis change lacks explanation;  
* output contains prohibited certainty or guaranteed-return language.

---

# **28\. Product Rule Enforcement**

These rules must be enforced through a combination of:

* domain validation;  
* database constraints;  
* API validation;  
* AI prompt instructions;  
* structured-output validation;  
* contradiction detection;  
* automated tests;  
* UI restrictions;  
* audit logs.

Prompt instructions alone are not sufficient enforcement.

---

# **29\. Locked Decisions**

This document locks the following operational decisions:

1. One session contains one trade story.  
2. Analysis is always longitudinal.  
3. The active thesis is canonical and versioned.  
4. Thesis changes require evidence and explanation.  
5. User-facing analysis is always in Bahasa Indonesia.  
6. Prompts and engineering documents are always in English.  
7. Internal schemas and enums use English.  
8. AI responses require structured validation.  
9. Every open position requires an active stop and target.  
10. The user controls all position mutations.  
11. Completed analyses are immutable.  
12. Closed sessions cannot be reopened as active positions.  
13. Every open-position update must assess target realism.  
14. Every update must explain what changed.  
15. Confidence and probability are separate concepts.  
16. Orderbook evidence is treated as temporary and uncertain.  
17. Missing information must never be fabricated.  
18. AI provider integration must use an abstraction layer.  
19. AI jobs run asynchronously through a background worker.  
20. A closed session becomes an AI Trading Journal.

---

# **30\. Final Rule Statement**

TradePilot AI must behave as a disciplined, persistent, and explainable AI Trading Analyst.

It must remember the trade story, preserve the trading thesis, recognize meaningful change, communicate uncertainty, and help the user make a disciplined decision based on the complete Trade Session history.

It must never reduce the trade journey to an isolated screenshot or an unexplained BUY, HOLD, or SELL label.

