# **TradePilot AI — Probability and Confidence Specification**

**Document:** `PROBABILITY_CONFIDENCE_SPEC.md`  
**Version:** 1.0  
**Status:** Final  
**Product Name:** TradePilot AI  
**Primary References:** `PRD.md`, `PRODUCT_RULES.md`, `DOMAIN_MODEL.md`, `AI_ANALYSIS_SPEC.md`, `THESIS_ENGINE_SPEC.md`, `CONTEXT_MEMORY_SPEC.md`  
**Purpose:** Define confidence scores, analytical probability estimates, input factors, calculation responsibilities, update behavior, coherence validation, uncertainty handling, calibration requirements, persistence, and user-facing presentation.

---

## **1\. Document Purpose**

This document defines how TradePilot AI produces and manages:

* analysis confidence;  
* evidence confidence;  
* event probabilities;  
* probability changes;  
* uncertainty levels;  
* probability coherence;  
* deterministic calculations;  
* AI-assisted estimates;  
* historical evaluation;  
* future calibration.

The system must provide useful numerical assessments without presenting them as guaranteed or statistically proven outcomes.

Probability and confidence values must help the user understand uncertainty.

They must not create false precision.

---

# **2\. Core Principles**

## **2.1 Confidence and Probability Are Different Concepts**

**Confidence** answers:

Seberapa dapat dipercaya analisis ini berdasarkan kualitas evidence, kelengkapan data, konsistensi histori, dan kejelasan kondisi saat ini?

**Probability** answers:

Berdasarkan informasi yang tersedia, seberapa besar kemungkinan suatu skenario tertentu terjadi?

A high-confidence analysis may estimate a low target-achievement probability.

A low-confidence analysis may estimate a bullish scenario, but with substantial uncertainty.

Example:

Confidence: 82  
Target-achievement probability: 38

Meaning:

* the system is relatively confident in its assessment;  
* the target itself is not currently very likely to be achieved.

---

## **2.2 Probability Is an Analytical Estimate**

MVP probabilities are model-assisted analytical estimates.

They are not initially:

* statistically calibrated forecasts;  
* guarantees;  
* broker recommendations;  
* certified financial probabilities;  
* outputs from a validated quantitative trading model.

The UI must identify them as:

Estimasi AI berdasarkan evidence dan histori Trade Session.

---

## **2.3 No Unsupported Precision**

Probability and confidence should normally be displayed as whole percentages.

Recommended display:

62%

Avoid:

62.4387%

The database may preserve more precision for deterministic calculations, but user-facing estimates should not imply unsupported accuracy.

---

## **2.4 System Calculations Override AI Arithmetic**

The application must deterministically calculate values such as:

* percentage return;  
* distance to stop;  
* distance to target;  
* change from previous score;  
* price change;  
* quantity-based risk;  
* weighted average entry;  
* realized profit and loss.

The AI interprets these values.

The AI must not be the authoritative calculator for them.

---

## **2.5 Every Estimate Requires Reasoning**

Every probability estimate must include:

* reasoning;  
* supporting evidence;  
* uncertainty level;  
* previous value when comparable;  
* change direction;  
* material change explanation when applicable.

A number without reasoning is invalid.

---

# **3\. Definitions**

## **3.1 Analysis Confidence**

The degree to which the current analysis is reliable given the available input and consistency of reasoning.

---

## **3.2 Evidence Quality**

The reliability and readability of evidence supplied to the analysis.

---

## **3.3 Event Probability**

An estimate of the likelihood that a defined market or thesis event occurs within a specified horizon and under specified conditions.

---

## **3.4 Uncertainty Level**

A qualitative assessment of how much uncertainty surrounds a probability estimate.

Allowed values:

LOW  
MODERATE  
HIGH

---

## **3.5 Forecast Horizon**

The time period over which an estimated event is evaluated.

Examples:

* until midday;  
* until market close;  
* next trading session;  
* next trading day;  
* before active target or stop;  
* within the active trade plan.

---

## **3.6 Comparable Probability**

A current and prior estimate that refer to:

* the same probability type;  
* a compatible forecast horizon;  
* the same Trade Session;  
* a sufficiently similar position phase;  
* comparable event definitions.

---

## **3.7 Calibrated Probability**

A probability value demonstrated through historical evaluation to correspond reasonably with observed outcomes.

MVP probability values are not assumed to be calibrated.

---

# **4\. Confidence Model**

## **4.1 Confidence Output Contract**

{  
  "score": 68,  
  "classification": "MODERATE",  
  "previous\_score": 74,  
  "score\_change": \-6,  
  "drivers": \[  
    "Support mayor terlihat jelas pada chart."  
  \],  
  "reducers": \[  
    "Screenshot orderbook hanya menunjukkan satu snapshot."  
  \],  
  "evidence\_quality": "MODERATE\_CONFIDENCE",  
  "context\_quality\_score": 76,  
  "missing\_data": \[  
    "Volume transaksi tidak tersedia."  
  \],  
  "explanation": "Analisis memiliki confidence moderat karena struktur chart cukup jelas, tetapi data orderbook dan volume terbatas."  
}

---

# **5\. Confidence Score Range**

Confidence score uses:

0–100

Classification:

| Score | Classification |
| ----- | ----- |
| 0–39 | `LOW` |
| 40–69 | `MODERATE` |
| 70–100 | `HIGH` |

The stored classification must match the score.

---

# **6\. Confidence Components**

Recommended confidence components:

evidence\_completeness  
evidence\_readability  
source\_reliability  
historical\_continuity  
source\_consistency  
chronology\_quality  
thesis\_clarity  
position\_data\_completeness  
analysis\_reasoning\_completeness  
provider\_output\_quality

---

# **7\. Suggested Confidence Weighting**

Recommended initial configuration:

| Component | Weight |
| ----- | ----- |
| Evidence completeness | 15% |
| Evidence readability | 15% |
| Source reliability | 15% |
| Historical continuity | 10% |
| Source consistency | 10% |
| Chronology quality | 5% |
| Thesis clarity | 10% |
| Position-data completeness | 10% |
| Reasoning completeness | 5% |
| Provider-output quality | 5% |

Total:

100%

Weights must be configurable.

---

# **8\. Deterministic Confidence Components**

The application should calculate or validate the following deterministically:

* required-evidence completeness;  
* image readability metadata;  
* extraction confidence;  
* missing required fields;  
* chronology integrity;  
* context-summary freshness;  
* source conflicts;  
* position-data completeness;  
* schema completeness;  
* required-section completeness;  
* stale-context status.

---

# **9\. AI-Assisted Confidence Components**

The AI may assess:

* clarity of technical structure;  
* strength of evidence agreement;  
* degree of unresolved market ambiguity;  
* interpretation uncertainty;  
* quality of support and resistance identification;  
* pattern ambiguity.

AI-assisted components remain subject to validation.

---

# **10\. Confidence Calculation Approach**

Recommended hybrid calculation:

final\_confidence \=  
    deterministic\_confidence × deterministic\_weight  
    \+  
    ai\_assessed\_confidence × ai\_weight

Recommended initial weights:

deterministic\_weight \= 0.70  
ai\_weight            \= 0.30

The final configuration may change after evaluation.

The AI must not have unrestricted control over the final score.

---

# **11\. Deterministic Confidence Penalties**

Suggested penalties:

| Condition | Suggested Penalty |
| ----- | ----- |
| Required image unreadable | −20 |
| Critical market value missing | −15 |
| Current evidence timestamp unknown | −10 |
| Material source conflict | −15 |
| Stale Context Summary | −5 |
| No direct comparable update | −5 |
| Position quantity unavailable | −3 to −10 depending on analysis |
| Volume unavailable | −3 to −8 |
| Only one orderbook snapshot | −5 |
| Evidence later excluded | Analysis cannot canonicalize |

Penalties must be capped and configured.

---

# **12\. Confidence Boosting Factors**

Possible positive factors:

| Condition | Suggested Effect |
| ----- | ----- |
| All required evidence available | \+5 |
| User-verified structured values | \+5 |
| Multi-timeframe chart agreement | \+5 |
| Current and prior evidence comparable | \+5 |
| No unresolved conflicts | \+5 |
| Invalidation condition is explicit | \+3 |
| Position records complete | \+5 |

The score must remain within 0–100.

---

# **13\. Confidence Change Rules**

A change is material when:

absolute score change \>= 5

Recommended configuration:

material\_confidence\_change: 5

Changes below the threshold may display as stable.

---

# **14\. Confidence Change Explanation**

When confidence changes materially, the analysis must state:

* previous score;  
* current score;  
* direction;  
* primary drivers;  
* primary reducers;  
* whether change comes from market evidence or data quality.

Example:

Confidence turun dari 74% menjadi 68% karena orderbook terbaru lebih lemah dan volume tidak tersedia. Penurunan ini terutama mencerminkan kualitas konfirmasi, bukan invalidation thesis.

---

# **15\. Confidence Restrictions**

The system must not:

* increase confidence solely because price rose;  
* decrease confidence solely because price fell;  
* equate confidence with expected profit;  
* use confidence as position sizing without a separate risk model;  
* display a high score when critical evidence is unreadable;  
* preserve an old high score after major source conflict;  
* return confidence without an explanation.

---

# **16\. Supported Probability Types**

Required probability types:

BULLISH\_CONTINUATION  
TARGET\_ACHIEVEMENT  
PULLBACK  
STOP\_LOSS\_TOUCH  
THESIS\_REMAINS\_VALID  
THESIS\_INVALIDATION  
MAJOR\_SUPPORT\_BREAK

Additional probability types require schema review.

---

# **17\. Probability Type Definitions**

## **17.1 `BULLISH_CONTINUATION`**

Estimated likelihood that bullish movement or bullish structure continues within the defined analysis horizon.

It does not necessarily mean the final target will be reached.

---

## **17.2 `TARGET_ACHIEVEMENT`**

Estimated likelihood that a specified active target is reached before the relevant competing condition.

The output must identify:

* target price;  
* forecast horizon;  
* competing condition;  
* required market behavior.

---

## **17.3 `PULLBACK`**

Estimated likelihood of a meaningful short-term retracement within the analysis horizon.

The analysis must define what counts as a pullback.

Examples:

* return toward average price;  
* retest of immediate support;  
* configured percentage decline;  
* loss of current intraday support.

---

## **17.4 `STOP_LOSS_TOUCH`**

Estimated likelihood that the active stop-loss price is touched within the defined horizon.

This is not always identical to thesis invalidation.

A stop may be:

* tighter than thesis invalidation;  
* wider than immediate support;  
* execution-based rather than structure-based.

---

## **17.5 `THESIS_REMAINS_VALID`**

Estimated likelihood that the current thesis remains valid through the specified checkpoint.

---

## **17.6 `THESIS_INVALIDATION`**

Estimated likelihood that the explicit invalidation condition occurs through the specified checkpoint.

This should complement `THESIS_REMAINS_VALID` only when both use the exact same event horizon and mutually exclusive definition.

---

## **17.7 `MAJOR_SUPPORT_BREAK`**

Estimated likelihood that the defined major support is broken according to its confirmation type.

The output must distinguish:

* intraday touch;  
* intraday break;  
* closing break;  
* structural confirmation.

---

# **18\. Probability Event Definition**

Every probability must define its event precisely.

Recommended contract:

{  
  "probability\_type": "TARGET\_ACHIEVEMENT",  
  "event\_definition": {  
    "target\_price": 3250,  
    "competing\_condition": "ACTIVE\_STOP\_LOSS",  
    "competing\_price": 2840,  
    "forecast\_horizon": "NEXT\_TRADING\_DAY",  
    "confirmation\_type": "PRICE\_TOUCH"  
  },  
  "percentage": 62  
}

Without a defined event and horizon, the probability is invalid.

---

# **19\. Forecast Horizon Values**

Allowed values:

UNTIL\_MIDDAY  
UNTIL\_MARKET\_CLOSE  
NEXT\_TRADING\_SESSION  
NEXT\_TRADING\_DAY  
UNTIL\_NEXT\_EVIDENCE  
UNTIL\_POSITION\_CLOSE  
CUSTOM

`CUSTOM` requires an explicit description.

---

# **20\. Confirmation Types**

Suggested values:

PRICE\_TOUCH  
INTRADAY\_BREAK  
CLOSING\_BREAK  
STRUCTURAL\_CONFIRMATION  
ORDERBOOK\_CONFIRMATION  
COMBINED\_CONFIRMATION

The confirmation type must match the event.

---

# **21\. Probability Output Contract**

{  
  "probability\_type": "TARGET\_ACHIEVEMENT",  
  "event\_definition": {  
    "target\_price": 3250,  
    "competing\_condition": "ACTIVE\_STOP\_LOSS",  
    "competing\_price": 2840,  
    "forecast\_horizon": "NEXT\_TRADING\_DAY",  
    "confirmation\_type": "PRICE\_TOUCH"  
  },  
  "percentage": 62,  
  "previous\_percentage": 68,  
  "change\_direction": "DECREASED",  
  "change\_amount": \-6,  
  "reasoning": "Offer meningkat dekat resistance dan buyer persistence menurun.",  
  "supporting\_evidence": \[  
    "Harga masih berada di atas support mayor."  
  \],  
  "opposing\_evidence": \[  
    "Resistance terdekat belum berhasil diserap."  
  \],  
  "uncertainty\_level": "MODERATE",  
  "estimate\_basis": "HYBRID\_AI\_RULE\_BASED"  
}

---

# **22\. Probability Estimate Basis**

Allowed values:

AI\_ASSISTED  
RULE\_BASED  
HYBRID\_AI\_RULE\_BASED  
CALIBRATED\_MODEL

MVP default:

HYBRID\_AI\_RULE\_BASED

`CALIBRATED_MODEL` must not be used until supported by historical evaluation.

---

# **23\. Probability Estimation Factors**

Probability estimates may consider:

* price position relative to entry;  
* distance to target;  
* distance to stop;  
* support integrity;  
* resistance strength;  
* chart structure;  
* momentum;  
* volume behavior;  
* orderbook alignment;  
* buyer persistence;  
* seller aggression;  
* thesis status;  
* risk-reward integrity;  
* evidence quality;  
* market-session timing;  
* previous comparable behavior;  
* known event conditions.

---

# **24\. Deterministic Probability Inputs**

The application should calculate:

* percentage distance to target;  
* percentage distance to stop;  
* distance to support;  
* distance to resistance;  
* price relative to average;  
* previous probability change;  
* target-versus-stop distance ratio;  
* whether a level was touched;  
* whether a closing break occurred;  
* whether position state changed.

These facts are supplied to the AI.

---

# **25\. AI Probability Responsibilities**

The AI may interpret:

* whether support appears durable;  
* whether resistance is likely to impede movement;  
* whether orderbook pressure is meaningful;  
* whether chart momentum supports continuation;  
* whether thesis quality is improving;  
* how evidence conflict affects uncertainty.

---

# **26\. Probability Anchor Model**

To reduce arbitrary estimates, the system should use probability anchors.

Example anchor bands:

VERY\_LOW       5–20  
LOW           21–39  
BALANCED      40–60  
MODERATE\_HIGH 61–75  
HIGH          76–90  
VERY\_HIGH     91–95

Normal analysis should rarely use:

0–4  
96–100

Extreme values require deterministic confirmation or strongly calibrated evidence.

---

# **27\. Default Probability Limits**

Recommended MVP limits:

probability:  
  default\_minimum: 5  
  default\_maximum: 95  
  extreme\_value\_requires\_explanation: true  
  allow\_zero\_for\_confirmed\_impossibility: true  
  allow\_hundred\_for\_already\_occurred\_event: true

Once an event has already occurred, it should usually no longer be presented as a forward probability.

Instead, the event becomes a fact.

---

# **28\. Initial Probability Formation**

For initial analysis, probability estimates should start from a neutral anchor and adjust according to evidence.

Conceptual approach:

base probability  
\+ structural adjustment  
\+ support/resistance adjustment  
\+ momentum adjustment  
\+ orderbook adjustment  
\+ risk-reward adjustment  
\+ evidence-quality moderation

The exact arithmetic does not need to be exposed to the user.

It must be reproducible in configuration and tests.

---

# **29\. Example Rule-Based Adjustments**

Illustrative target-achievement adjustments:

| Factor | Suggested Direction |
| ----- | ----- |
| Target close with weak resistance | Increase |
| Target far beyond major resistance | Decrease |
| Strong trend alignment | Increase |
| Weakening thesis | Decrease |
| High-quality buyer persistence | Increase |
| Heavy nearby offer | Decrease |
| Stop much closer than target | Decrease |
| Evidence quality low | Move toward neutral and increase uncertainty |

These are guidance, not hard-coded trading rules.

---

# **30\. Evidence Quality Moderation**

Low evidence quality must not necessarily push probabilities downward.

Instead, it should generally:

* reduce deviation from a neutral anchor;  
* increase uncertainty;  
* lower confidence;  
* prevent extreme estimates.

Example:

Raw analytical estimate: 78  
Low evidence quality moderation: 65  
Uncertainty: HIGH

---

# **31\. Probability Change Rules**

A current probability may be compared with a previous one only when:

* probability type matches;  
* event definition matches;  
* target or stop reference is unchanged or comparison-adjusted;  
* horizon is compatible;  
* position phase is compatible.

Otherwise:

change\_direction \= NOT\_COMPARABLE  
previous\_percentage \= null

---

# **32\. Material Probability Change**

Recommended threshold:

absolute change \>= 5 percentage points

Configuration:

material\_probability\_change: 5

Changes below five points may be described as broadly stable.

---

# **33\. Probability Change Direction**

Allowed values:

INCREASED  
DECREASED  
UNCHANGED  
NOT\_COMPARABLE

Suggested mapping:

change \>= \+5  → INCREASED  
change \<= \-5  → DECREASED  
otherwise     → UNCHANGED

---

# **34\. Event Definition Change**

When an active target changes from 3,250 to 3,150, the new target-achievement probability is not directly comparable to the old target probability without adjustment.

The system must mark:

NOT\_COMPARABLE

or explicitly state:

Probability meningkat sebagian karena target baru lebih dekat, bukan semata-mata karena kondisi pasar membaik.

---

# **35\. Position Phase Change**

Probability comparisons should normally reset or be marked non-comparable after:

* position opening;  
* major additional entry;  
* partial exit;  
* target replacement;  
* stop replacement;  
* final exit.

Some thesis probabilities may remain comparable if event definitions are unchanged.

---

# **36\. Required Probability Sets**

## **36.1 Initial Analysis**

Required:

BULLISH\_CONTINUATION  
TARGET\_ACHIEVEMENT  
PULLBACK  
MAJOR\_SUPPORT\_BREAK  
THESIS\_INVALIDATION

---

## **36.2 Watching Update**

Required:

BULLISH\_CONTINUATION  
TARGET\_ACHIEVEMENT  
PULLBACK  
THESIS\_REMAINS\_VALID  
THESIS\_INVALIDATION

---

## **36.3 Open Position Update**

Required:

TARGET\_ACHIEVEMENT  
PULLBACK  
STOP\_LOSS\_TOUCH  
THESIS\_REMAINS\_VALID  
THESIS\_INVALIDATION

---

## **36.4 Partial Exit Review**

Recommended:

TARGET\_ACHIEVEMENT  
STOP\_LOSS\_TOUCH  
THESIS\_REMAINS\_VALID

---

## **36.5 Closing Analysis**

Forward probabilities are generally not required.

Closing analysis should evaluate earlier probability quality instead.

---

# **37\. Multiple Target Probabilities**

When multiple active targets exist, the system must estimate each target separately.

Example:

\[  
  {  
    "probability\_type": "TARGET\_ACHIEVEMENT",  
    "target\_type": "TP1",  
    "target\_price": 3250,  
    "percentage": 62  
  },  
  {  
    "probability\_type": "TARGET\_ACHIEVEMENT",  
    "target\_type": "TP2",  
    "target\_price": 3380,  
    "percentage": 38  
  }  
\]

Expected coherence:

P(TP2 reached) \<= P(TP1 reached)

when TP2 is farther in the same direction and no special condition changes the event definition.

---

# **38\. Target Probability Coherence**

For ascending bullish targets:

TP1 probability \>= TP2 probability \>= TP3 probability

For descending bearish targets, analogous ordering applies.

Violation requires explanation or rejection.

---

# **39\. Thesis Probability Coherence**

When `THESIS_REMAINS_VALID` and `THESIS_INVALIDATION` share the same:

* horizon;  
* confirmation definition;  
* mutually exclusive outcome space;

they should approximately complement each other.

Recommended tolerance:

95 \<= remains\_valid \+ invalidation \<= 105

This tolerance accounts for model rounding.

When events are not strictly complementary, the output must explain why.

---

# **40\. Pullback and Target Probability**

`PULLBACK` and `TARGET_ACHIEVEMENT` are not necessarily complementary.

Both may be moderately high if:

* price may pull back first;  
* then recover and reach target within a longer horizon.

The UI must not assume all probability types sum to 100\.

---

# **41\. Stop Touch and Thesis Invalidation**

`STOP_LOSS_TOUCH` and `THESIS_INVALIDATION` may differ.

Example:

* active stop: 3,050;  
* thesis invalidation: closing break below 3,020.

Then:

P(stop touch) may be greater than P(thesis invalidation)

The analysis must preserve this distinction.

---

# **42\. Bullish Continuation and Target Achievement**

Bullish continuation may be more likely than target achievement when:

* bullish movement may continue;  
* but not far enough to reach the active target within the horizon.

Expected relationship:

P(target achievement) \<= P(bullish continuation)

for compatible horizons and definitions.

Exceptions require explanation.

---

# **43\. Probability Coherence Checks**

The validator must check:

1. every percentage is between 0 and 100;  
2. required probability types exist;  
3. event horizons are present;  
4. event definitions are not empty;  
5. multiple target ordering is logical;  
6. thesis-validity relationships are coherent;  
7. stop-touch and invalidation definitions remain separate;  
8. changes match previous values;  
9. extreme values include explanation;  
10. probability values align with thesis status;  
11. closed positions do not receive active forward estimates;  
12. stale position parameters are not used.

---

# **44\. Thesis Status Coherence Bands**

Suggested guidance:

| Thesis Status | `THESIS_REMAINS_VALID` | `THESIS_INVALIDATION` |
| ----- | ----- | ----- |
| `STRENGTHENING` | 70–95 | 5–30 |
| `INTACT` | 55–85 | 15–45 |
| `INTACT_BUT_WEAKENING` | 40–70 | 30–60 |
| `UNDER_REVIEW` | 25–60 | 40–75 |
| `INVALIDATED` | 0–20 | 80–100 or event recorded as fact |

Values outside these bands require strong explanation.

They are validation guidelines, not forced formulas.

---

# **45\. Risk-Level Coherence**

Suggested relationships:

* higher `STOP_LOSS_TOUCH` probability generally increases risk;  
* higher `THESIS_INVALIDATION` probability generally increases thesis risk;  
* high target probability does not automatically imply low risk;  
* a wide stop may lower touch probability while increasing loss magnitude.

Probability of occurrence and impact magnitude must remain separate.

---

# **46\. Uncertainty Level Rules**

## **46.1 `LOW`**

Use when:

* event definition is clear;  
* evidence is complete;  
* sources agree;  
* chronology is reliable;  
* historical comparison is strong.

## **46.2 `MODERATE`**

Use when:

* evidence is broadly useful;  
* some important limitations remain;  
* market behavior is not fully confirmed.

## **46.3 `HIGH`**

Use when:

* evidence is incomplete or conflicting;  
* orderbook is the main signal;  
* timestamp is uncertain;  
* position parameters changed;  
* forecast horizon is long;  
* event definition depends on missing confirmation.

---

# **47\. Uncertainty and Probability Extremes**

High uncertainty should normally prevent extreme probability estimates.

Recommended rule:

If uncertainty \= HIGH:  
    probability should normally remain between 20 and 80\.

Values outside this range require deterministic evidence and explicit reasoning.

---

# **48\. Probability Explanation Requirements**

Each probability explanation must answer:

* what supports the estimate;  
* what opposes it;  
* what changed;  
* which condition would materially change it;  
* how uncertain it is.

Example:

Peluang mencapai TP1 diperkirakan 62%. Support utama masih bertahan dan target masih berada dalam range tiga bulan, tetapi offer pada resistance terdekat meningkat. Probability akan membaik jika harga menembus resistance dengan buyer persistence yang kuat.

---

# **49\. Probability Presentation Rules**

The UI should display:

* event label;  
* percentage;  
* uncertainty level;  
* previous percentage;  
* change direction;  
* brief reason;  
* forecast horizon;  
* expandable details.

Example:

Peluang Mencapai TP1  
62% — turun 6 poin  
Ketidakpastian: Moderat  
Horizon: hingga sesi berikutnya

---

# **50\. Probability Disclaimer**

A concise disclaimer should appear near probability displays:

Estimasi ini berasal dari analisis AI atas evidence Trade Session dan bukan jaminan hasil pasar.

The disclaimer should be visible without overwhelming the interface.

---

# **51\. Confidence Presentation Rules**

The UI should display:

Confidence Analisis  
68% — Moderat  
Turun 6 poin dari update sebelumnya

Expandable detail:

* drivers;  
* reducers;  
* missing data;  
* context quality;  
* evidence quality.

---

# **52\. Confidence Gauge Restrictions**

Avoid designs that resemble:

* guaranteed win rate;  
* broker conviction;  
* certainty meter;  
* automated buy signal.

The label must always include:

Confidence Analisis

not merely:

Confidence

when ambiguity is possible.

---

# **53\. Probability Bars**

Probability bars may use semantic direction, but:

* bars must include numeric labels;  
* color must not be the only indicator;  
* bullish probability should not automatically use celebratory visual styling;  
* downside probabilities must receive equal prominence;  
* all required probabilities should be visible.

---

# **54\. Bullish and Downside Summary**

For open positions, the summary should present at least:

Peluang mencapai target  
Peluang pullback  
Peluang menyentuh stop  
Peluang thesis tetap valid  
Peluang thesis invalid

The UI must not display only bullish probability.

---

# **55\. Probability Persistence**

Each accepted analysis must store:

* probability type;  
* percentage;  
* event definition;  
* horizon;  
* target or stop reference;  
* previous percentage;  
* change direction;  
* reasoning;  
* supporting evidence;  
* opposing evidence;  
* uncertainty;  
* estimate basis;  
* analysis version.

The current database schema may store extended event details inside JSONB while preserving queryable core columns.

---

# **56\. Probability Versioning**

Probability values belong to an immutable analysis version.

They must not be edited in place.

A new estimate requires:

* a new analysis version;  
* a new probability assessment;  
* updated comparison metadata.

---

# **57\. Confidence Persistence**

The complete confidence object belongs inside the immutable structured analysis payload.

For dashboard access, the current score may also be cached in:

trade\_sessions.latest\_confidence\_score

The source remains the accepted analysis version.

---

# **58\. Probability Canonicalization**

Probability values may update canonical dashboard state only when:

* analysis is accepted;  
* schema validation passes;  
* coherence checks pass;  
* event definitions are complete;  
* analysis is not stale;  
* referenced target, stop, and thesis versions remain current.

---

# **59\. Probability Staleness**

A probability estimate becomes stale when:

* target changes;  
* stop changes;  
* position average materially changes;  
* partial exit changes the plan;  
* thesis status changes;  
* forecast horizon expires;  
* evidence used is excluded;  
* session closes.

Stale probability values remain historical but must not be shown as current.

---

# **60\. Horizon Expiry**

Probability assessments should include an expiry or checkpoint.

Example:

{  
  "forecast\_horizon": "UNTIL\_MARKET\_CLOSE",  
  "valid\_until": "2026-07-17T09:00:00Z"  
}

After expiry:

* the value remains historical;  
* the dashboard should request or encourage an update;  
* it should not be presented as current without an expired indicator.

---

# **61\. Probability Update Frequency**

The system should not regenerate probabilities continuously.

Probabilities update when:

* the user submits new evidence;  
* a scheduled session checkpoint is analyzed;  
* position state changes;  
* thesis review occurs;  
* a material correction is made.

This avoids false precision from excessive updates.

---

# **62\. Probability Reset Conditions**

Previous probability should be set to null and change marked `NOT_COMPARABLE` when:

* event definition changes materially;  
* target price changes materially;  
* stop price changes materially;  
* forecast horizon changes materially;  
* position moves from watching to open;  
* position is partially closed and quantity allocation changes the plan;  
* historical correction changes source facts.

---

# **63\. Probability Materiality Explanation**

A material probability change must explain whether it resulted from:

MARKET\_CONDITION\_CHANGE  
THESIS\_CHANGE  
POSITION\_PARAMETER\_CHANGE  
TARGET\_CHANGE  
STOP\_CHANGE  
EVIDENCE\_QUALITY\_CHANGE  
FORECAST\_HORIZON\_CHANGE  
HISTORICAL\_CORRECTION

---

# **64\. Example: Target Probability Decline**

Previous state:

TP1: 3,250  
Probability: 68%

Current state:

TP1 unchanged  
Offer pressure increased  
Bid strength decreased  
Probability: 60%

Output:

{  
  "percentage": 60,  
  "previous\_percentage": 68,  
  "change\_direction": "DECREASED",  
  "change\_amount": \-8,  
  "change\_driver": "MARKET\_CONDITION\_CHANGE",  
  "reasoning": "Resistance belum ditembus dan tekanan offer meningkat."  
}

---

# **65\. Example: Probability Not Comparable After Target Change**

Previous:

Target: 3,250  
Probability: 54%

New user-confirmed target:

Target: 3,150

New output:

{  
  "percentage": 72,  
  "previous\_percentage": null,  
  "change\_direction": "NOT\_COMPARABLE",  
  "reasoning": "Target telah berubah menjadi lebih dekat sehingga estimasi sebelumnya tidak dapat dibandingkan secara langsung."  
}

---

# **66\. Example: High Confidence, Low Target Probability**

{  
  "confidence\_assessment": {  
    "score": 84,  
    "classification": "HIGH",  
    "explanation": "Evidence lengkap dan konsisten."  
  },  
  "target\_probability": {  
    "percentage": 32,  
    "reasoning": "Target berada di atas resistance mayor dan horizon analisis pendek."  
  }  
}

This combination is valid.

---

# **67\. Example: Bullish Bias with High Pullback Probability**

{  
  "directional\_bias": "BULLISH",  
  "bullish\_continuation\_probability": 64,  
  "pullback\_probability": 58,  
  "explanation": "Thesis menengah masih bullish, tetapi harga berpotensi melakukan retest support sebelum melanjutkan kenaikan."  
}

This is valid because the events are not mutually exclusive.

---

# **68\. Example: Invalid Coherence**

Thesis status: INVALIDATED  
Thesis remains valid: 78%  
Recommended action: HOLD\_POSITION

Validator result:

REJECT

Reasons:

* thesis probability conflicts with status;  
* recommended action conflicts with invalidation.

---

# **69\. Probability Validation Pipeline**

Parse probability objects  
        ↓  
Validate required types  
        ↓  
Validate percentages  
        ↓  
Validate event definitions  
        ↓  
Validate horizons  
        ↓  
Validate references  
        ↓  
Calculate deterministic changes  
        ↓  
Run pairwise coherence checks  
        ↓  
Run thesis-status coherence  
        ↓  
Run position-state coherence  
        ↓  
Validate uncertainty  
        ↓  
Accept, warn, review, or reject

---

# **70\. Probability Validation Outcomes**

Allowed outcomes:

PASS  
PASS\_WITH\_WARNINGS  
REVIEW\_REQUIRED  
REJECT

---

# **71\. Warning-Level Conditions**

May pass with warning:

* small rounding inconsistency;  
* probability outside guidance band with good explanation;  
* uncertainty missing but derivable;  
* previous estimate unavailable;  
* minor event-definition wording difference.

---

# **72\. Review-Required Conditions**

Require review:

* large probability change without sufficient evidence;  
* unusual relationship between target levels;  
* high confidence despite conflicting sources;  
* remains-valid and invalidation estimates significantly inconsistent;  
* estimate uses changed target but is marked comparable;  
* extreme probability under high uncertainty.

---

# **73\. Reject Conditions**

Reject when:

* percentage is outside 0–100;  
* required probability is absent;  
* event horizon is absent;  
* target or stop reference is stale;  
* thesis-status contradiction is critical;  
* closed position receives active hold probabilities;  
* AI invents unsupported target or stop values;  
* extreme estimate has no basis;  
* position version changed critically during processing.

---

# **74\. Probability Repair**

Repair sequence:

1. deterministic correction of change values;  
2. deterministic correction of classification;  
3. request missing event definition;  
4. request AI correction for coherence;  
5. fallback-provider attempt;  
6. reject analysis.

The application may correct arithmetic but must not invent analytical reasoning.

---

# **75\. Evaluation and Calibration Dataset**

Every accepted probability should later be evaluable.

Store or derive:

* probability type;  
* predicted percentage;  
* prediction timestamp;  
* horizon;  
* event definition;  
* evidence quality;  
* thesis status;  
* provider;  
* model;  
* eventual event outcome;  
* outcome timestamp;  
* whether prediction expired;  
* whether parameters changed before outcome.

---

# **76\. Outcome Labeling**

Examples:

## **Target Achievement**

Outcome is positive when:

* target price is reached according to confirmation type;  
* within the stated horizon;  
* before the defined competing event, when applicable.

## **Stop-Loss Touch**

Outcome is positive when:

* stop price is touched within the horizon.

## **Thesis Invalidation**

Outcome is positive when:

* explicit invalidation condition is confirmed within the horizon.

Ambiguous outcomes must be labeled separately.

---

# **77\. Outcome Statuses**

Recommended values:

OCCURRED  
DID\_NOT\_OCCUR  
AMBIGUOUS  
CANCELLED\_BY\_PARAMETER\_CHANGE  
EXPIRED\_WITHOUT\_RESOLUTION  
NOT\_EVALUABLE

---

# **78\. Calibration Metrics**

Future evaluation should include:

* Brier score;  
* log loss, where appropriate;  
* calibration curve;  
* expected calibration error;  
* reliability by probability band;  
* directional accuracy;  
* provider comparison;  
* confidence-versus-error relationship;  
* performance by thesis status;  
* performance by evidence quality.

These metrics must not be claimed before sufficient data exists.

---

# **79\. Brier Score Concept**

For a binary event:

Brier score \= average squared difference  
between predicted probability and actual outcome.

Lower is better.

This metric may be used internally in `AI_EVALUATION_PLAN.md`.

---

# **80\. Confidence Evaluation**

Confidence should be evaluated against analysis reliability rather than market direction alone.

Possible measures:

* schema-validation success;  
* contradiction rate;  
* factual extraction error;  
* thesis-status correction rate;  
* unsupported-level change rate;  
* prediction calibration;  
* user correction frequency.

A high-confidence analysis that is frequently corrected indicates poor confidence calibration.

---

# **81\. Probability Recalibration**

When sufficient evaluated history exists, the system may map raw model estimates to calibrated probabilities.

Possible future approaches:

* isotonic regression;  
* Platt scaling;  
* probability-band adjustment;  
* provider-specific calibration;  
* analysis-type-specific calibration.

Calibration is out of scope for MVP implementation but the data model must support it.

---

# **82\. Calibration Versioning**

A calibrated probability must record:

raw probability  
calibrated probability  
calibration method  
calibration version  
training cutoff  
sample size

The application must never replace historical raw estimates silently.

---

# **83\. Provider Comparison**

Evaluation should compare Gemini and DeepSeek on:

* confidence stability;  
* probability calibration;  
* evidence traceability;  
* contradiction frequency;  
* target-probability realism;  
* invalidation timeliness;  
* output repair rate.

Provider selection must not be based solely on which provider returns more bullish probabilities.

---

# **84\. Confidence and Provider Fallback**

When fallback is used:

* confidence should account for provider attempt issues only if they affect output quality;  
* fallback itself does not automatically lower trading confidence;  
* provider disagreement may reduce source consistency;  
* only the accepted result becomes current.

If both providers return materially different valid probabilities, the result may require review.

---

# **85\. Provider Disagreement**

Suggested disagreement thresholds:

provider\_disagreement:  
  confidence\_points: 15  
  probability\_points: 20

When exceeded:

* create a diagnostic warning;  
* compare reasoning;  
* reduce confidence or mark review required;  
* do not average values blindly.

---

# **86\. Probability Aggregation Prohibition**

The MVP must not average provider probabilities automatically.

Invalid approach:

Gemini: 70%  
DeepSeek: 40%  
Final: 55%

Averaging hides disagreement.

The system should select one accepted analysis or require review.

---

# **87\. User Override**

The user cannot directly change an AI probability as if it were an execution value.

The user may:

* add notes;  
* mark analysis incorrect;  
* request another analysis;  
* correct source data;  
* choose not to follow the recommendation.

Probability history remains immutable.

---

# **88\. Historical Analysis Display**

Historical probabilities must display:

* their original forecast horizon;  
* original target and stop references;  
* whether they expired;  
* whether they became stale;  
* eventual outcome when available.

Do not compare expired historical values as if they were current.

---

# **89\. Closing Analysis Probability Review**

Closing analysis should evaluate:

* which predictions were correct;  
* which were wrong;  
* whether warning timing was useful;  
* whether probability changes were directionally sensible;  
* whether the AI became overconfident;  
* whether target probability remained too high after thesis deterioration.

It must not claim calibration from one trade.

---

# **90\. Journal Probability Review**

The AI Trading Journal may include:

{  
  "probability\_review": {  
    "well\_assessed": \[  
      "Peluang pullback meningkat sebelum support ditembus."  
    \],  
    "poorly\_assessed": \[  
      "Peluang mencapai target tetap terlalu tinggi setelah bid melemah."  
    \],  
    "calibration\_claim": "NOT\_ENOUGH\_DATA",  
    "lesson": "Penurunan buyer persistence perlu memberi dampak lebih besar pada target probability."  
  }  
}

---

# **91\. Probability Configuration**

Recommended initial configuration:

probability\_confidence:  
  confidence:  
    low\_max: 39  
    moderate\_max: 69  
    high\_max: 100

    deterministic\_weight: 0.70  
    ai\_weight: 0.30  
    material\_change\_points: 5

  probability:  
    default\_minimum: 5  
    default\_maximum: 95  
    material\_change\_points: 5  
    comparison\_tolerance\_points: 2  
    complement\_tolerance\_points: 5  
    high\_uncertainty\_minimum: 20  
    high\_uncertainty\_maximum: 80

  coherence:  
    target\_ordering\_required: true  
    thesis\_complement\_check: true  
    bullish\_target\_relationship\_check: true  
    stale\_reference\_blocks\_canonicalization: true

  provider\_disagreement:  
    confidence\_points: 15  
    probability\_points: 20

Final configuration values will be locked in `CONFIG_SPEC.md`.

---

# **92\. API Requirements**

The API should return confidence and probability objects with:

* current value;  
* classification or uncertainty;  
* previous value;  
* change;  
* event definition;  
* horizon;  
* reason;  
* status;  
* expiry;  
* stale indicator.

Example:

{  
  "percentage": 62,  
  "previous\_percentage": 68,  
  "change": \-6,  
  "change\_direction": "DECREASED",  
  "uncertainty\_level": "MODERATE",  
  "forecast\_horizon": "NEXT\_TRADING\_DAY",  
  "is\_current": true,  
  "is\_stale": false  
}

---

# **93\. UI Statuses**

Probability display state:

CURRENT  
EXPIRED  
STALE  
NOT\_COMPARABLE  
HISTORICAL  
UNAVAILABLE

Confidence display state:

CURRENT  
STALE  
HISTORICAL  
UNAVAILABLE

---

# **94\. Missing Probability Behavior**

When a required probability cannot be estimated reliably:

* do not insert zero;  
* use null;  
* include missing-data reason;  
* reduce confidence;  
* possibly fail required-field validation when analysis type demands it.

Example:

{  
  "probability\_type": "STOP\_LOSS\_TOUCH",  
  "percentage": null,  
  "unavailable\_reason": "Active stop loss tidak tersedia."  
}

For an open position, a missing active stop is a domain integrity problem and should usually block analysis.

---

# **95\. Testing Requirements**

## **95.1 Confidence Tests**

Test:

* classification boundaries;  
* deterministic penalties;  
* evidence-quality effects;  
* missing-data effects;  
* source-conflict effects;  
* score clamping;  
* material change detection.

## **95.2 Probability Validation Tests**

Test:

* percentages outside range;  
* required types missing;  
* missing horizons;  
* target ordering;  
* thesis complement relationship;  
* stop versus invalidation distinction;  
* high uncertainty with extreme values.

## **95.3 Comparison Tests**

Test:

* comparable same target;  
* changed target;  
* changed stop;  
* position opening;  
* partial exit;  
* expired horizon;  
* custom event definition.

## **95.4 Staleness Tests**

Test:

* target changes during analysis;  
* stop changes during analysis;  
* position closes;  
* evidence is excluded;  
* non-critical title changes.

## **95.5 Evaluation Tests**

Test:

* target outcome labeling;  
* stop-touch labeling;  
* thesis-invalidation labeling;  
* ambiguous outcome;  
* parameter-change cancellation;  
* expiry without resolution.

---

# **96\. Example Complete Probability Summary**

{  
  "confidence\_assessment": {  
    "score": 68,  
    "classification": "MODERATE",  
    "previous\_score": 74,  
    "score\_change": \-6,  
    "drivers": \[  
      "Support mayor masih terlihat jelas."  
    \],  
    "reducers": \[  
      "Orderbook hanya berupa satu snapshot.",  
      "Volume transaksi tidak tersedia."  
    \],  
    "context\_quality\_score": 76,  
    "explanation": "Analisis cukup dapat dipercaya, tetapi konfirmasi intraday masih terbatas."  
  },  
  "probability\_assessments": \[  
    {  
      "probability\_type": "TARGET\_ACHIEVEMENT",  
      "event\_definition": {  
        "target\_type": "TP1",  
        "target\_price": 3250,  
        "competing\_condition": "ACTIVE\_STOP\_LOSS",  
        "competing\_price": 2840,  
        "forecast\_horizon": "NEXT\_TRADING\_DAY",  
        "confirmation\_type": "PRICE\_TOUCH"  
      },  
      "percentage": 62,  
      "previous\_percentage": 68,  
      "change\_direction": "DECREASED",  
      "change\_amount": \-6,  
      "reasoning": "Offer meningkat dekat resistance dan buyer persistence menurun.",  
      "supporting\_evidence": \[  
        "Support mayor masih bertahan."  
      \],  
      "opposing\_evidence": \[  
        "Resistance terdekat belum berhasil diserap."  
      \],  
      "uncertainty\_level": "MODERATE",  
      "estimate\_basis": "HYBRID\_AI\_RULE\_BASED"  
    },  
    {  
      "probability\_type": "PULLBACK",  
      "event\_definition": {  
        "definition": "Retest area 3.100.",  
        "forecast\_horizon": "UNTIL\_MARKET\_CLOSE",  
        "confirmation\_type": "PRICE\_TOUCH"  
      },  
      "percentage": 48,  
      "previous\_percentage": 38,  
      "change\_direction": "INCREASED",  
      "change\_amount": 10,  
      "reasoning": "Bid intraday lebih tipis dibandingkan update pagi.",  
      "supporting\_evidence": \[  
        "Tekanan offer meningkat."  
      \],  
      "opposing\_evidence": \[  
        "Harga masih berada di atas average."  
      \],  
      "uncertainty\_level": "MODERATE",  
      "estimate\_basis": "HYBRID\_AI\_RULE\_BASED"  
    },  
    {  
      "probability\_type": "STOP\_LOSS\_TOUCH",  
      "event\_definition": {  
        "stop\_price": 2840,  
        "forecast\_horizon": "NEXT\_TRADING\_DAY",  
        "confirmation\_type": "PRICE\_TOUCH"  
      },  
      "percentage": 22,  
      "previous\_percentage": 18,  
      "change\_direction": "UNCHANGED",  
      "change\_amount": 4,  
      "reasoning": "Risiko meningkat, tetapi jarak ke stop masih relatif lebar.",  
      "supporting\_evidence": \[\],  
      "opposing\_evidence": \[  
        "Support mayor belum ditembus."  
      \],  
      "uncertainty\_level": "HIGH",  
      "estimate\_basis": "HYBRID\_AI\_RULE\_BASED"  
    },  
    {  
      "probability\_type": "THESIS\_REMAINS\_VALID",  
      "event\_definition": {  
        "thesis\_version": 3,  
        "forecast\_horizon": "NEXT\_TRADING\_DAY",  
        "confirmation\_type": "STRUCTURAL\_CONFIRMATION"  
      },  
      "percentage": 70,  
      "previous\_percentage": 76,  
      "change\_direction": "DECREASED",  
      "change\_amount": \-6,  
      "reasoning": "Support mayor masih valid, tetapi orderbook melemah.",  
      "supporting\_evidence": \[  
        "Struktur higher low belum rusak."  
      \],  
      "opposing\_evidence": \[  
        "Buyer persistence menurun."  
      \],  
      "uncertainty\_level": "MODERATE",  
      "estimate\_basis": "HYBRID\_AI\_RULE\_BASED"  
    },  
    {  
      "probability\_type": "THESIS\_INVALIDATION",  
      "event\_definition": {  
        "thesis\_version": 3,  
        "invalidation\_condition": "Penutupan valid di bawah support mayor.",  
        "forecast\_horizon": "NEXT\_TRADING\_DAY",  
        "confirmation\_type": "CLOSING\_BREAK"  
      },  
      "percentage": 30,  
      "previous\_percentage": 24,  
      "change\_direction": "INCREASED",  
      "change\_amount": 6,  
      "reasoning": "Risiko meningkat karena orderbook melemah, tetapi invalidation belum terjadi.",  
      "supporting\_evidence": \[  
        "Tekanan jual meningkat."  
      \],  
      "opposing\_evidence": \[  
        "Harga masih di atas support mayor."  
      \],  
      "uncertainty\_level": "MODERATE",  
      "estimate\_basis": "HYBRID\_AI\_RULE\_BASED"  
    }  
  \]  
}

---

# **97\. Acceptance Criteria**

The probability and confidence system is accepted when:

1. confidence and probability are treated as separate concepts;  
2. confidence measures analysis reliability rather than expected profit;  
3. every probability has a defined event and horizon;  
4. every probability includes reasoning and uncertainty;  
5. required probability types exist for each analysis;  
6. system arithmetic overrides AI arithmetic;  
7. unsupported decimal precision is not displayed;  
8. probability changes are compared only when event definitions are compatible;  
9. changed targets and stops reset comparability when required;  
10. multiple target probabilities follow logical ordering;  
11. thesis-validity probabilities align with thesis status;  
12. pullback and target probabilities are not falsely treated as complements;  
13. stop-touch and thesis-invalidation probabilities remain distinct;  
14. low evidence quality increases uncertainty and reduces extreme estimates;  
15. stale estimates cannot update canonical state;  
16. expired estimates remain historical;  
17. zero is not used for unavailable probabilities;  
18. extreme estimates require strong explanation;  
19. provider disagreement is surfaced rather than averaged blindly;  
20. accepted estimates retain provider, model, evidence, and version metadata;  
21. future outcome labeling is supported;  
22. probability calibration is not claimed before evaluation;  
23. UI displays both upside and downside estimates;  
24. probability numbers are presented with an explicit non-guarantee disclaimer;  
25. the full system remains auditable and provider-independent.

---

# **98\. Final Probability and Confidence Statement**

TradePilot AI must use confidence and probability to communicate uncertainty, not to disguise uncertainty.

Confidence must explain how reliable the analysis is.

Probability must define which event is being estimated, over what horizon, and under which conditions.

Every number must remain connected to:

* evidence;  
* current thesis;  
* actual position;  
* forecast horizon;  
* uncertainty;  
* historical comparison;  
* eventual evaluation.

The system must prefer an honest, explainable estimate over a precise-looking number that cannot be supported.

