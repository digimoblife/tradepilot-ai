# **TradePilot AI — Thesis Engine Specification**

**Document:** `THESIS_ENGINE_SPEC.md`  
**Version:** 1.0  
**Status:** Final  
**Product Name:** TradePilot AI  
**Primary References:** `PRD.md`, `PRODUCT_RULES.md`, `DOMAIN_MODEL.md`, `SESSION_LIFECYCLE.md`, `AI_ANALYSIS_SPEC.md`  
**Purpose:** Define the thesis-state engine, evidence evaluation, state-transition rules, contradiction checks, scoring model, canonicalization guards, recovery behavior, and audit requirements.

---

## **1\. Document Purpose**

This document defines how TradePilot AI manages the active trading thesis throughout one Trade Session.

The Thesis Engine is responsible for determining whether the active thesis is:

* strengthening;  
* intact;  
* intact but weakening;  
* under review;  
* invalidated.

The engine must prevent the AI from:

* changing the thesis without evidence;  
* reversing direction without explanation;  
* forgetting the original invalidation condition;  
* treating minor price movement as thesis failure;  
* restoring an invalidated setup as if nothing happened;  
* replacing canonical thesis state with a stale or contradictory response.

The AI proposes thesis changes.

The application validates and canonicalizes them.

---

# **2\. Thesis Engine Objectives**

The Thesis Engine must answer:

1. What is the current canonical thesis?  
2. Which evidence supports it?  
3. Which evidence conflicts with it?  
4. Has the thesis materially strengthened or weakened?  
5. Has the invalidation condition occurred?  
6. Is evidence sufficient for a definitive status?  
7. Should the previous thesis remain canonical?  
8. Should a new thesis version be created?  
9. What position-management impact follows from the thesis state?

---

# **3\. Thesis Definition**

A trading thesis is the current technical hypothesis explaining why a setup or position remains valid.

A thesis must contain:

directional bias  
thesis statement  
technical rationale  
supporting evidence  
conflicting evidence  
key support  
key resistance  
invalidation level  
invalidation condition  
expected scenario  
confidence score  
status

A thesis is not:

* a ticker description;  
* a generic bullish or bearish label;  
* a standalone BUY recommendation;  
* a price target;  
* an orderbook summary;  
* a temporary observation without invalidation criteria.

---

# **4\. Canonical Thesis Statuses**

Allowed statuses:

STRENGTHENING  
INTACT  
INTACT\_BUT\_WEAKENING  
UNDER\_REVIEW  
INVALIDATED

No additional status may be stored without a schema and migration update.

---

# **5\. Thesis State Meanings**

## **5.1 `STRENGTHENING`**

Use when new evidence materially increases support for the current thesis.

Typical conditions:

* key support becomes more reliable;  
* resistance is absorbed or broken;  
* price structure confirms the expected direction;  
* volume or orderbook behavior confirms continuation;  
* conflicting evidence decreases;  
* target probability improves for supported reasons.

This status must not be used merely because price moved slightly in the expected direction.

---

## **5.2 `INTACT`**

Use when the thesis remains valid and no material strengthening or weakening has occurred.

Typical conditions:

* price remains inside the expected scenario;  
* support remains valid;  
* resistance has not materially changed;  
* risks remain broadly stable;  
* no invalidation condition is present.

`INTACT` is the default stable state after a valid initial analysis unless evidence strongly justifies another status.

---

## **5.3 `INTACT_BUT_WEAKENING`**

Use when the thesis remains technically valid but supporting evidence has deteriorated.

Typical conditions:

* support is tested repeatedly;  
* bid strength decreases;  
* seller pressure increases;  
* momentum slows;  
* target probability decreases;  
* risk rises;  
* price remains above invalidation.

This state must explain:

* what weakened;  
* what remains valid;  
* what could restore strength;  
* what would move the thesis to `UNDER_REVIEW` or `INVALIDATED`.

---

## **5.4 `UNDER_REVIEW`**

Use when evidence is materially conflicting, incomplete, or unresolved.

Typical conditions:

* price is testing invalidation but confirmation is absent;  
* orderbook and chart evidence disagree;  
* new evidence may indicate a structural change but is insufficient;  
* critical screenshots are unreadable;  
* prior analysis and current AI output conflict;  
* market timestamp uncertainty prevents reliable comparison.

This state is not a vague fallback.

It must specify:

* unresolved questions;  
* confirmation required;  
* defensive action;  
* next evidence required.

---

## **5.5 `INVALIDATED`**

Use when the original thesis no longer holds.

Typical conditions:

* explicit invalidation condition is confirmed;  
* key support is materially broken;  
* breakout setup fails and reverses;  
* original expected structure no longer exists;  
* risk-to-reward no longer supports the original plan;  
* seller dominance aligns with structural deterioration;  
* the trade premise has changed materially.

Invalidation must be supported by evidence and must identify the exact failed thesis condition.

---

# **6\. Thesis State Machine**

Recommended conceptual state flow:

                   ┌──────────────────┐  
                    │  STRENGTHENING   │  
                    └───────┬──────────┘  
                            │  
                            ▼  
┌──────────────┐      ┌──────────────┐  
│ UNDER\_REVIEW │◄────►│    INTACT    │  
└──────┬───────┘      └──────┬───────┘  
       │                      │  
       │                      ▼  
       │            ┌──────────────────────┐  
       └───────────►│ INTACT\_BUT\_WEAKENING│  
                    └──────────┬───────────┘  
                               │  
                               ▼  
                     ┌──────────────────┐  
                     │   INVALIDATED    │  
                     └──────────────────┘

The diagram shows common paths, not unrestricted transitions.

---

# **7\. Allowed Thesis Transitions**

| From | To | Allowed |
| ----- | ----- | ----- |
| Initial creation | `INTACT` | Yes |
| Initial creation | `STRENGTHENING` | Rare |
| Initial creation | `UNDER_REVIEW` | Yes |
| Initial creation | `INTACT_BUT_WEAKENING` | Rare |
| Initial creation | `INVALIDATED` | No |
| `INTACT` | `STRENGTHENING` | Yes |
| `INTACT` | `INTACT` | Yes |
| `INTACT` | `INTACT_BUT_WEAKENING` | Yes |
| `INTACT` | `UNDER_REVIEW` | Yes |
| `INTACT` | `INVALIDATED` | Yes |
| `STRENGTHENING` | `STRENGTHENING` | Yes |
| `STRENGTHENING` | `INTACT` | Yes |
| `STRENGTHENING` | `INTACT_BUT_WEAKENING` | Yes |
| `STRENGTHENING` | `UNDER_REVIEW` | Yes |
| `STRENGTHENING` | `INVALIDATED` | Yes, with strong evidence |
| `INTACT_BUT_WEAKENING` | `STRENGTHENING` | Yes, with restoration evidence |
| `INTACT_BUT_WEAKENING` | `INTACT` | Yes |
| `INTACT_BUT_WEAKENING` | `INTACT_BUT_WEAKENING` | Yes |
| `INTACT_BUT_WEAKENING` | `UNDER_REVIEW` | Yes |
| `INTACT_BUT_WEAKENING` | `INVALIDATED` | Yes |
| `UNDER_REVIEW` | `STRENGTHENING` | Rare |
| `UNDER_REVIEW` | `INTACT` | Yes |
| `UNDER_REVIEW` | `INTACT_BUT_WEAKENING` | Yes |
| `UNDER_REVIEW` | `UNDER_REVIEW` | Yes |
| `UNDER_REVIEW` | `INVALIDATED` | Yes |
| `INVALIDATED` | `INVALIDATED` | Yes |
| `INVALIDATED` | Any active status | No, except correction |

---

# **8\. Invalidated Thesis Is Irreversible**

Once a canonical thesis becomes `INVALIDATED`, it must remain invalidated for that Trade Session.

It may return to another status only when:

* source evidence was later proven incorrect;  
* a historical correction invalidates the prior invalidation decision;  
* the application performs an explicit thesis correction workflow;  
* the original invalidated version remains preserved.

A new market setup is not a correction.

A new setup requires a new Trade Session.

---

# **9\. Thesis Engine Inputs**

The engine evaluates a normalized `ThesisEvaluationInput`.

{  
  "session": {  
    "session\_id": "uuid",  
    "lifecycle\_status": "OPEN\_POSITION",  
    "stable\_status": "OPEN\_POSITION",  
    "session\_version": 8  
  },  
  "current\_thesis": {  
    "thesis\_id": "uuid",  
    "version\_number": 3,  
    "status": "INTACT",  
    "directional\_bias": "BULLISH",  
    "statement": "Harga masih membentuk struktur rebound.",  
    "key\_support": {},  
    "key\_resistance": {},  
    "invalidation\_level": {},  
    "invalidation\_condition": "Penutupan valid di bawah support mayor.",  
    "confidence\_score": 72  
  },  
  "previous\_analysis": {},  
  "current\_analysis\_proposal": {},  
  "position": {},  
  "current\_evidence": \[\],  
  "historical\_evidence": \[\],  
  "previous\_probabilities": \[\],  
  "current\_probabilities": \[\],  
  "context\_quality": {}  
}

---

# **10\. Evidence Categories**

The engine must classify evidence into:

SUPPORTING  
WEAKENING  
CONFLICTING  
INVALIDATING  
NEUTRAL  
UNREADABLE  
STALE  
DUPLICATE

---

## **10.1 Supporting Evidence**

Evidence that confirms the thesis.

Examples:

* higher low remains intact;  
* support attracts persistent bids;  
* resistance is absorbed;  
* breakout is confirmed;  
* current price behaves as expected.

---

## **10.2 Weakening Evidence**

Evidence that reduces thesis strength without invalidating it.

Examples:

* bid becomes thinner;  
* support is tested repeatedly;  
* momentum decelerates;  
* offer pressure increases;  
* target probability declines.

---

## **10.3 Conflicting Evidence**

Evidence that materially disagrees with another relevant source.

Examples:

* orderbook appears strong but chart structure breaks;  
* price rises while volume and bid behavior deteriorate;  
* latest screenshot timestamp is earlier than the previous update;  
* AI extraction conflicts with user-provided numbers.

---

## **10.4 Invalidating Evidence**

Evidence directly satisfying the invalidation condition.

Examples:

* valid close below support;  
* confirmed failed breakout;  
* loss of required price structure;  
* active premise no longer exists.

---

## **10.5 Neutral Evidence**

Evidence that provides context but does not materially change the thesis.

---

# **11\. Evidence Weighting Model**

The engine should use explicit evidence weighting.

Each evidence item receives:

relevance score  
reliability score  
recency score  
independence score  
materiality score

Recommended range:

0–100

Conceptual weight:

evidence\_weight \=  
    relevance  
    × reliability  
    × recency  
    × independence  
    × materiality

The implementation may normalize the factors rather than multiply raw percentages.

The scoring model supports consistency but must not replace deterministic invalidation rules.

---

# **12\. Evidence Reliability**

Recommended reliability ranges:

| Evidence Source | Typical Reliability |
| ----- | ----- |
| User-confirmed actual execution | 95–100 |
| User-provided explicit market values | 85–100 |
| Clear chart screenshot | 75–95 |
| Clear orderbook screenshot | 65–90 |
| AI extraction from readable screenshot | 60–90 |
| AI inference | 40–75 |
| Single orderbook snapshot | 35–70 |
| Unreadable or cropped evidence | 0–30 |

These are guidelines, not stored market probabilities.

---

# **13\. Evidence Recency**

Evidence recency must be evaluated relative to analysis purpose.

For intraday orderbook analysis:

* same-session current snapshot has highest recency;  
* prior trading-day orderbook has low direct relevance;  
* initial chart remains structurally relevant.

For closing analysis:

* same-day morning, midday, and closing evidence are all relevant;  
* closing evidence receives highest current-state weight.

---

# **14\. Evidence Independence**

Repeated screenshots showing effectively the same condition must not be counted as fully independent confirmation.

Examples:

* three screenshots taken seconds apart;  
* duplicate upload;  
* resized copy of the same screenshot;  
* AI extraction and image interpretation from the same source.

Independent evidence may include:

* orderbook;  
* three-month chart;  
* six-month chart;  
* user-confirmed price data;  
* later market observation.

---

# **15\. Deterministic Invalidation Rules**

Deterministic invalidation rules take priority over soft scoring.

An invalidation may be confirmed when:

1. the canonical invalidation condition is satisfied;  
2. evidence quality meets the minimum threshold;  
3. market timestamp is reliable;  
4. no unresolved contradiction invalidates the evidence;  
5. the condition is not merely an intraday transient when the thesis requires closing confirmation.

Example:

Thesis condition:  
“Daily close below 3,020 invalidates the rebound thesis.”

Intraday low at 3,010:  
Not sufficient.

Validated market close at 3,000:  
Potentially sufficient.

---

# **16\. Invalidation Confirmation Types**

INTRADAY\_BREAK  
CLOSING\_BREAK  
MULTI\_PERIOD\_CONFIRMATION  
ORDERBOOK\_CONFIRMATION  
STRUCTURAL\_BREAK  
COMBINED\_CONFIRMATION

The thesis must specify which type applies.

---

# **17\. Thesis Status Scoring Model**

The system may calculate a `ThesisHealthScore` from 0 to 100\.

This score is an internal consistency aid.

It is not displayed as a market probability unless separately mapped.

Suggested interpretation:

| Score | Suggested Status |
| ----- | ----- |
| 80–100 | `STRENGTHENING` |
| 60–79 | `INTACT` |
| 40–59 | `INTACT_BUT_WEAKENING` |
| 20–39 | `UNDER_REVIEW` |
| 0–19 | `INVALIDATED` candidate |

The final status must also pass deterministic and contextual rules.

A low score alone must not invalidate a thesis if the explicit invalidation condition has not occurred.

---

# **18\. Thesis Health Components**

Suggested components:

support\_integrity  
structure\_integrity  
momentum\_alignment  
orderbook\_alignment  
resistance\_progress  
risk\_reward\_integrity  
evidence\_consistency  
context\_quality

Suggested weighted model:

support\_integrity          25%  
structure\_integrity        20%  
momentum\_alignment         10%  
orderbook\_alignment        10%  
resistance\_progress        10%  
risk\_reward\_integrity      10%  
evidence\_consistency       10%  
context\_quality             5%

Weights should be configurable and evaluated through testing.

---

# **19\. Support Integrity**

Support integrity should consider:

* whether key support remains unbroken;  
* whether support reactions remain valid;  
* whether support is repeatedly tested;  
* whether bid support is persistent;  
* whether price closes above or below the support;  
* whether the support basis remains relevant.

Suggested states:

STRONG  
INTACT  
TESTED  
WEAKENING  
BROKEN  
UNKNOWN

---

# **20\. Structure Integrity**

Structure integrity should consider:

* higher high or higher low continuity;  
* lower high or lower low development;  
* range integrity;  
* breakout or breakdown;  
* failed breakout;  
* trend alignment across timeframes.

Suggested states:

CONFIRMED  
INTACT  
MIXED  
DETERIORATING  
BROKEN  
UNKNOWN

---

# **21\. Orderbook Alignment**

Orderbook evidence must be treated as temporary.

It may strengthen or weaken a thesis but should rarely invalidate a multi-day swing thesis alone.

Suggested orderbook alignment:

STRONGLY\_SUPPORTIVE  
SUPPORTIVE  
NEUTRAL  
CONFLICTING  
STRONGLY\_CONFLICTING  
UNKNOWN

Orderbook invalidation requires an explicitly orderbook-based thesis or combined structural confirmation.

---

# **22\. Risk-Reward Integrity**

A thesis may weaken even without a support break when expected upside becomes insufficient relative to downside.

The engine should evaluate:

* distance to target;  
* distance to invalidation;  
* new resistance;  
* reduced target realism;  
* worsening entry quality;  
* increased execution risk.

Possible values:

IMPROVING  
ACCEPTABLE  
DETERIORATING  
UNACCEPTABLE  
UNKNOWN

`UNACCEPTABLE` does not always mean price thesis invalidation, but it may invalidate the trade plan.

---

# **23\. Thesis Versus Trade Plan**

The engine must distinguish:

## **23.1 Price Thesis**

Example:

Harga masih berpotensi naik selama support utama bertahan.

## **23.2 Trade Plan Validity**

Example:

Potensi naik masih ada, tetapi entry saat ini tidak lagi menawarkan risk-to-reward yang layak.

The price thesis may remain intact while the trade plan is no longer attractive.

The analysis must communicate this distinction.

---

# **24\. Thesis Evaluation Output**

Recommended engine output:

{  
  "previous\_thesis\_status": "INTACT",  
  "proposed\_thesis\_status": "INTACT\_BUT\_WEAKENING",  
  "transition": "WEAKENED",  
  "thesis\_health\_score": 54,  
  "support\_integrity": "TESTED",  
  "structure\_integrity": "INTACT",  
  "orderbook\_alignment": "CONFLICTING",  
  "risk\_reward\_integrity": "DETERIORATING",  
  "supporting\_evidence": \[\],  
  "weakening\_evidence": \[\],  
  "conflicting\_evidence": \[\],  
  "invalidating\_evidence": \[\],  
  "unresolved\_questions": \[\],  
  "change\_reason": "Bid melemah dan offer meningkat, tetapi support mayor belum ditembus.",  
  "position\_impact": {},  
  "canonicalization\_decision": "ACCEPT",  
  "canonicalization\_reasons": \[\],  
  "warnings": \[\]  
}

---

# **25\. State Decision Rules**

## **25.1 Decide `STRENGTHENING`**

Propose `STRENGTHENING` only when:

* no invalidating evidence exists;  
* no critical unresolved contradiction exists;  
* thesis-health score exceeds configured threshold;  
* at least one material new supporting factor exists;  
* confidence is not increasing solely because price moved up;  
* target or structure confirmation improves.

---

## **25.2 Decide `INTACT`**

Propose `INTACT` when:

* invalidation has not occurred;  
* thesis-health remains acceptable;  
* strengthening and weakening evidence are not material;  
* current behavior remains inside expected scenario;  
* no unresolved critical conflict exists.

---

## **25.3 Decide `INTACT_BUT_WEAKENING`**

Propose when:

* invalidation has not occurred;  
* material weakening evidence exists;  
* thesis-health has deteriorated;  
* key support remains valid;  
* risk or target realism worsens;  
* evidence is sufficient to identify deterioration.

---

## **25.4 Decide `UNDER_REVIEW`**

Propose when:

* evidence conflicts materially;  
* invalidation may have occurred but cannot be confirmed;  
* evidence quality is insufficient;  
* current and previous analyses disagree without enough resolution;  
* timestamps are uncertain;  
* structural and orderbook signals conflict significantly.

---

## **25.5 Decide `INVALIDATED`**

Propose only when:

* explicit invalidation condition is met; or  
* the original premise no longer exists;  
* supporting evidence is sufficiently reliable;  
* contradictory evidence has been resolved;  
* the analysis explains the exact invalidation;  
* position and trading-plan impact are provided.

---

# **26\. Canonicalization Decisions**

The Thesis Engine returns one of:

ACCEPT  
KEEP\_PREVIOUS  
REVIEW\_REQUIRED  
REJECT

---

## **26.1 `ACCEPT`**

Use when:

* proposed transition is valid;  
* evidence is sufficient;  
* analysis is not stale;  
* contradictions are adequately explained;  
* status and rationale are coherent.

---

## **26.2 `KEEP_PREVIOUS`**

Use when:

* new evidence is non-material;  
* proposed change is unsupported;  
* AI output drifts without evidence;  
* evidence is too weak to justify a version change.

The new analysis may still be accepted while the canonical thesis remains unchanged.

---

## **26.3 `REVIEW_REQUIRED`**

Use when:

* proposed change may be valid;  
* evidence is materially conflicting;  
* invalidation is near but unconfirmed;  
* human review or focused thesis analysis is required.

The canonical thesis remains unchanged or moves to `UNDER_REVIEW` depending on policy.

---

## **26.4 `REJECT`**

Use when:

* output is logically inconsistent;  
* status reversal lacks evidence;  
* invalidation is contradicted by reliable facts;  
* analysis uses stale position state;  
* evidence references are invalid;  
* mandatory reasoning is missing.

---

# **27\. Canonicalization Guard Sequence**

The application must evaluate guards in this order:

1\. Schema validation  
2\. Required-field validation  
3\. Language validation  
4\. Evidence-reference validation  
5\. Stale-state validation  
6\. Numerical validation  
7\. Deterministic invalidation checks  
8\. Thesis transition validation  
9\. Contradiction detection  
10\. Position-impact validation  
11\. Canonicalization decision  
12\. Transactional persistence

Failure at an earlier stage prevents later canonicalization.

---

# **28\. Thesis Version Creation Rules**

A new thesis version must be created when:

* status changes;  
* directional bias changes;  
* thesis statement changes materially;  
* invalidation condition changes;  
* key support or resistance changes materially;  
* expected scenario changes materially;  
* confidence changes beyond configured threshold;  
* a historical correction is applied.

A new version is optional when:

* status remains unchanged;  
* only minor narrative wording changes;  
* no canonical thesis property changes.

The analysis version still remains preserved.

---

# **29\. Unchanged Thesis Behavior**

When no material thesis change exists:

proposed\_status \= previous\_status  
change\_type \= UNCHANGED  
requires\_thesis\_version \= false

The system should avoid unnecessary thesis versions.

A periodic snapshot version may be supported later, but it is not required for MVP.

---

# **30\. Thesis Directional Bias Changes**

Directional bias changes are high-materiality changes.

Examples:

BULLISH → NEUTRAL  
BULLISH → BEARISH  
NEUTRAL → BULLISH

A directional-bias change requires:

* clear technical explanation;  
* evidence references;  
* relationship to previous thesis;  
* key-level impact;  
* probability impact;  
* trading-plan impact.

A bullish-to-bearish reversal without passing through review or invalidation should be treated as suspicious.

---

# **31\. Bias Reversal Rules**

For one Trade Session:

* a bullish thesis may weaken or invalidate;  
* it should not become a completely new bearish trading thesis;  
* a bearish post-invalidation observation may be recorded;  
* a new active bearish setup requires a new Trade Session.

This preserves one thesis lifecycle per Trade Session.

---

# **32\. Initial Thesis Creation**

Initial analysis should normally create:

status \= INTACT  
change\_type \= CREATED

It may create `UNDER_REVIEW` when evidence is insufficient or materially conflicting.

Initial analysis should not create `INVALIDATED`, because no active canonical thesis existed to invalidate.

If no valid setup exists, the system should create:

* a cautious thesis;  
* a cancellation recommendation; or  
* `UNDER_REVIEW`.

---

# **33\. Strengthening Requirements**

A transition to `STRENGTHENING` must identify at least one new material factor.

Examples:

* resistance breakout;  
* stronger support confirmation;  
* increased buyer persistence;  
* improved multi-timeframe alignment;  
* target probability improvement;  
* reduced invalidation risk.

Invalid example:

Thesis menguat karena harga naik 0,3%.

Price movement without structural context is insufficient.

---

# **34\. Weakening Requirements**

A transition to `INTACT_BUT_WEAKENING` must include:

* weakening factor;  
* evidence reference;  
* still-valid factor;  
* restoration condition;  
* next deterioration condition;  
* probability impact;  
* recommended risk response.

---

# **35\. Under Review Requirements**

`UNDER_REVIEW` output must include:

unresolved questions  
conflicting evidence  
required confirmation  
defensive action  
next checkpoint

Example:

{  
  "unresolved\_questions": \[  
    "Apakah penurunan di bawah support hanya intraday atau akan menjadi penutupan valid?"  
  \],  
  "required\_confirmation": \[  
    "Harga penutupan.",  
    "Orderbook penutupan."  
  \],  
  "defensive\_action": "Jangan menambah posisi."  
}

---

# **36\. Invalidation Requirements**

An invalidation proposal must contain:

original invalidation condition  
observed invalidation evidence  
confirmation type  
evidence quality  
timestamp  
price or structural event  
impact on position  
recommended defensive action

Example:

{  
  "original\_invalidation\_condition": "Penutupan valid di bawah 3.020.",  
  "observed\_event": "Harga ditutup pada 3.000.",  
  "confirmation\_type": "CLOSING\_BREAK",  
  "evidence\_quality": "VERIFIED",  
  "position\_impact": "Thesis rebound tidak lagi valid.",  
  "recommended\_action": "Evaluasi exit dan jangan menambah posisi."  
}

---

# **37\. Position Impact Mapping**

| Thesis Status | Position Impact |
| ----- | ----- |
| `STRENGTHENING` | Hold may remain justified; target expansion may be reviewed |
| `INTACT` | Existing plan remains active |
| `INTACT_BUT_WEAKENING` | Hold with caution; block careless additions |
| `UNDER_REVIEW` | Defensive posture; avoid new exposure |
| `INVALIDATED` | Block additions; review exit immediately |

The engine does not execute position changes.

---

# **38\. Additional Entry Guard**

Additional entry must be blocked when:

thesis\_status \= INVALIDATED

The UI must strongly warn when:

thesis\_status \= UNDER\_REVIEW

For `INTACT_BUT_WEAKENING`, additional entry should normally be discouraged unless specific restoration confirmation exists.

---

# **39\. Stop-Loss Impact Rules**

The Thesis Engine may recommend:

* keeping the current stop;  
* tightening the stop;  
* reviewing the stop basis;  
* exiting because the thesis is invalidated.

It must not recommend widening a stop solely to preserve an invalid thesis.

When thesis invalidates:

recommended\_stop\_direction ≠ WIDEN

unless a historical data correction is being analyzed.

---

# **40\. Target Impact Rules**

The engine must assess whether thesis changes affect:

* target realism;  
* target probability;  
* target sequence;  
* required resistance confirmation.

A weakening thesis may justify:

* keeping the target with conditions;  
* lowering target realism;  
* considering partial profit.

It must not repeatedly lower targets to hide thesis failure.

---

# **41\. Confidence Interaction**

Thesis confidence measures reliability of the thesis assessment.

It should consider:

* evidence quality;  
* evidence agreement;  
* context completeness;  
* invalidation clarity;  
* historical consistency.

Confidence should not automatically rise because thesis status is `STRENGTHENING`.

A strengthening thesis based on one uncertain screenshot may still have moderate confidence.

---

# **42\. Probability Interaction**

The engine should consider:

* thesis-remains-valid probability;  
* thesis-invalidation probability;  
* target-achievement probability;  
* support-break probability.

Expected logical relationships:

* stronger thesis usually increases validity probability;  
* weakening thesis usually increases invalidation risk;  
* invalidated thesis should have very low remains-valid probability;  
* target probability may remain moderate even when thesis weakens, but requires explanation.

---

# **43\. Contradiction Detection Categories**

The Thesis Engine must detect:

STATUS\_CONTRADICTION  
BIAS\_CONTRADICTION  
LEVEL\_CONTRADICTION  
INVALIDATION\_CONTRADICTION  
EVIDENCE\_CONTRADICTION  
PROBABILITY\_CONTRADICTION  
ACTION\_CONTRADICTION  
POSITION\_STATE\_CONTRADICTION  
HISTORY\_CONTRADICTION  
TIMESTAMP\_CONTRADICTION

---

# **44\. Status Contradiction**

Example:

Previous: INTACT  
Current: INVALIDATED  
Reason: “Bid sedikit melemah.”

Result:

REJECT or REVIEW\_REQUIRED

The reason does not support invalidation.

---

# **45\. Bias Contradiction**

Example:

Thesis status: STRENGTHENING  
Directional bias: BEARISH  
Original thesis: BULLISH  
No explanation

Result:

REJECT

---

# **46\. Level Contradiction**

Example:

Previous major support: 3,020  
Current major support: 2,840  
No new chart evidence

Result:

REVIEW\_REQUIRED or KEEP\_PREVIOUS

---

# **47\. Invalidation Contradiction**

Example:

Thesis marked INVALIDATED  
Price remains above invalidation  
No structural failure

Result:

REJECT

unless another explicit invalidation condition is documented.

---

# **48\. Probability Contradiction**

Example:

Thesis status: INVALIDATED  
Thesis remains valid probability: 78%

Result:

REJECT

Suggested coherence guidance:

| Thesis Status | Typical Remains Valid Probability |
| ----- | ----- |
| `STRENGTHENING` | 70–95 |
| `INTACT` | 55–85 |
| `INTACT_BUT_WEAKENING` | 40–70 |
| `UNDER_REVIEW` | 25–60 |
| `INVALIDATED` | 0–20 |

These are validation bands, not mandatory predictions.

Values outside the bands require explanation.

---

# **49\. Action Contradiction**

Example:

Thesis status: INVALIDATED  
Recommended action: ADD\_POSITION

Result:

REJECT

Example:

Thesis status: UNDER\_REVIEW  
Recommended action: HOLD\_WITH\_CAUTION

Result:

Potentially valid with defensive conditions.

---

# **50\. Position State Contradiction**

Example:

Position is closed.  
Thesis output recommends moving stop loss.

Result:

REJECT

---

# **51\. Timestamp Contradiction**

The engine must detect:

* evidence older than the previous update;  
* future market timestamps;  
* upload time being mistaken for market time;  
* incorrect intraday ordering.

When chronology is uncertain, prefer `UNDER_REVIEW` or `KEEP_PREVIOUS`.

---

# **52\. Contradiction Severity**

Allowed severity:

LOW  
MODERATE  
HIGH  
CRITICAL

Suggested handling:

| Severity | Handling |
| ----- | ----- |
| Low | Accept with warning |
| Moderate | Pass with explanation or keep previous |
| High | Review required |
| Critical | Reject |

---

# **53\. Contradiction Score**

The engine may calculate an internal score from 0 to 100\.

0–19    no meaningful contradiction  
20–39   low  
40–59   moderate  
60–79   high  
80–100  critical

The score should combine:

* status mismatch;  
* level drift;  
* probability mismatch;  
* action mismatch;  
* evidence disagreement;  
* stale-state risk.

---

# **54\. Stale-State Guard**

Before canonicalization, verify:

analysis.session\_version\_snapshot  
analysis.position\_version\_snapshot  
current session version  
current position version

If position-critical state changed during AI processing, the thesis proposal may be stale.

Critical changes include:

* new entry;  
* partial exit;  
* final exit;  
* stop change;  
* target change;  
* evidence exclusion;  
* session closure.

Stale thesis output must not become canonical automatically.

---

# **55\. Evidence Exclusion Guard**

When evidence used by a pending analysis becomes excluded:

* analysis must be marked stale or non-canonical;  
* thesis change must not be applied;  
* retry may be offered with valid evidence.

Historical accepted analyses remain preserved.

---

# **56\. Thesis Correction Workflow**

A correction is different from a normal transition.

Use when:

* wrong evidence was used;  
* ticker was incorrect;  
* market data extraction was materially wrong;  
* invalidation was based on an invalid screenshot;  
* a historical value was corrected.

Correction requires:

correction reason  
original thesis version  
corrected evidence  
new analysis version  
new thesis version  
audit record

The original thesis remains historical.

---

# **57\. Thesis Engine Processing Flow**

Load current canonical thesis  
        ↓  
Load latest valid analysis and evidence  
        ↓  
Validate chronology and session versions  
        ↓  
Classify evidence  
        ↓  
Check deterministic invalidation  
        ↓  
Calculate thesis-health components  
        ↓  
Evaluate proposed status  
        ↓  
Detect contradictions  
        ↓  
Assess position impact  
        ↓  
Return canonicalization decision  
        ↓  
Persist new thesis version if approved

---

# **58\. Transactional Canonicalization**

When a new thesis is accepted, one transaction must:

1. insert new `trading_theses` record;  
2. link supporting and conflicting evidence;  
3. create or supersede price levels where applicable;  
4. update `trade_sessions.active_thesis_id`;  
5. update `trade_sessions.latest_thesis_status`;  
6. update confidence cache;  
7. update risk and action cache;  
8. create timeline event;  
9. create audit record;  
10. create notification when required;  
11. request context-summary refresh if needed.

Failure must roll back all changes.

---

# **59\. Timeline Event Mapping**

| Transition | Event |
| ----- | ----- |
| Initial thesis created | `THESIS_CREATED` |
| Thesis strengthens | `THESIS_STRENGTHENED` |
| Thesis unchanged | `THESIS_UNCHANGED`, optional |
| Thesis weakens | `THESIS_WEAKENED` |
| Thesis under review | `THESIS_UNDER_REVIEW` |
| Thesis invalidated | `THESIS_INVALIDATED` |
| Thesis corrected | `THESIS_CORRECTED` |

Avoid timeline noise from repeated non-material unchanged events.

---

# **60\. Notification Rules**

Create in-app notification when:

* thesis becomes `INTACT_BUT_WEAKENING`;  
* thesis becomes `UNDER_REVIEW`;  
* thesis becomes `INVALIDATED`;  
* contradiction requires review.

Suggested priority:

| Thesis Event | Priority |
| ----- | ----- |
| Strengthened | Informational |
| Weakened | Warning |
| Under Review | Warning |
| Invalidated | Critical |

---

# **61\. UI Requirements**

The UI must display:

* current thesis status;  
* thesis statement;  
* change from previous status;  
* reason for change;  
* supporting evidence;  
* conflicting evidence;  
* invalidation condition;  
* last thesis update;  
* impact on position;  
* recommended next action.

The UI must allow the user to inspect previous thesis versions.

---

# **62\. Thesis Comparison UI Data**

The engine should provide structured comparison:

{  
  "previous": {  
    "status": "INTACT",  
    "confidence": 74,  
    "key\_support": 3020,  
    "target\_probability": 68  
  },  
  "current": {  
    "status": "INTACT\_BUT\_WEAKENING",  
    "confidence": 68,  
    "key\_support": 3020,  
    "target\_probability": 62  
  },  
  "changes": \[  
    {  
      "field": "status",  
      "change": "WEAKENED",  
      "reason": "Offer meningkat dan bid menipis."  
    }  
  \]  
}

---

# **63\. Thesis Version Metadata**

Every thesis version must record:

version number  
source analysis version  
previous thesis version  
status  
directional bias  
statement  
rationale  
support  
resistance  
invalidation  
confidence  
change type  
change reason  
effective timestamp  
evidence links

---

# **64\. Default Threshold Configuration**

Recommended initial configuration:

thesis\_engine:  
  strengthening\_score\_min: 80  
  intact\_score\_min: 60  
  weakening\_score\_min: 40  
  under\_review\_score\_min: 20

  material\_confidence\_change: 5  
  material\_probability\_change: 5  
  material\_level\_change\_percentage: 1.5

  minimum\_invalidation\_evidence\_quality: 70  
  maximum\_unresolved\_critical\_conflicts: 0

  require\_closing\_confirmation\_for\_daily\_support\_break: true  
  block\_additional\_entry\_when\_under\_review: false  
  block\_additional\_entry\_when\_invalidated: true

Final configuration will be defined in `CONFIG_SPEC.md`.

---

# **65\. Provider Independence**

The Thesis Engine operates on normalized analysis output.

It must not depend on:

* Gemini field names;  
* DeepSeek response format;  
* provider-specific confidence;  
* provider-native tool calls.

All provider responses must be normalized before thesis evaluation.

---

# **66\. Deterministic Versus AI Responsibilities**

## **66.1 AI Responsibilities**

The AI may:

* interpret chart and orderbook;  
* propose evidence classification;  
* explain technical changes;  
* propose thesis status;  
* identify uncertainty;  
* propose position impact.

## **66.2 Deterministic Application Responsibilities**

The application must:

* validate enums;  
* verify evidence references;  
* calculate scores and distances;  
* check timestamps;  
* detect stale versions;  
* enforce transition rules;  
* block invalid actions;  
* canonicalize transactionally.

---

# **67\. Thesis Engine Failure Codes**

Recommended error codes:

THESIS\_NOT\_AVAILABLE  
THESIS\_PROPOSAL\_MISSING  
THESIS\_STATUS\_INVALID  
THESIS\_CHANGE\_REASON\_REQUIRED  
THESIS\_EVIDENCE\_INSUFFICIENT  
THESIS\_INVALIDATION\_UNCONFIRMED  
THESIS\_INVALIDATION\_CONTRADICTED  
THESIS\_REVERSAL\_NOT\_ALLOWED  
THESIS\_PROPOSAL\_STALE  
THESIS\_EVIDENCE\_EXCLUDED  
THESIS\_CONTRADICTION\_HIGH  
THESIS\_CANONICALIZATION\_REJECTED  
THESIS\_VERSION\_CONFLICT  
THESIS\_CORRECTION\_REQUIRED

---

# **68\. Retry and Review Rules**

Automatic retry may occur when:

* thesis output is structurally incomplete;  
* change reason is missing;  
* provider response is malformed;  
* evidence references are not formatted correctly.

Automatic retry should not resolve:

* real evidence conflict;  
* stale position state;  
* unconfirmed invalidation;  
* forbidden bias reversal;  
* historical correction requirement.

These require review or a new analysis request.

---

# **69\. Example: Intact to Weakening**

Input:

Previous thesis: INTACT  
Major support: 3,020  
Current price: 3,110  
Bid strength: decreased  
Offer pressure: increased  
Support: not broken

Output:

{  
  "proposed\_thesis\_status": "INTACT\_BUT\_WEAKENING",  
  "change\_type": "WEAKENED",  
  "change\_reason": "Orderbook melemah, tetapi harga masih berada di atas support mayor.",  
  "canonicalization\_decision": "ACCEPT"  
}

---

# **70\. Example: Weakening to Under Review**

Input:

Previous thesis: INTACT\_BUT\_WEAKENING  
Price trades below support intraday  
Closing price unavailable  
Orderbook shows conflicting buyer recovery

Output:

{  
  "proposed\_thesis\_status": "UNDER\_REVIEW",  
  "unresolved\_questions": \[  
    "Apakah support benar-benar ditembus pada penutupan?"  
  \],  
  "required\_confirmation": \[  
    "Data harga penutupan."  
  \],  
  "canonicalization\_decision": "ACCEPT"  
}

---

# **71\. Example: Under Review to Invalidated**

Input:

Previous thesis: UNDER\_REVIEW  
Invalidation requires close below 3,020  
Verified close: 3,000  
Chart structure breaks

Output:

{  
  "proposed\_thesis\_status": "INVALIDATED",  
  "change\_type": "INVALIDATED",  
  "change\_reason": "Harga ditutup di bawah support mayor sehingga struktur rebound gagal.",  
  "canonicalization\_decision": "ACCEPT"  
}

---

# **72\. Example: Unsupported Invalidation**

Input:

Previous thesis: INTACT  
Support: 3,020  
Current price: 3,100  
Only evidence: slightly thinner bid  
AI proposes INVALIDATED

Engine result:

{  
  "canonicalization\_decision": "REJECT",  
  "reasons": \[  
    "Invalidation condition has not occurred.",  
    "Orderbook weakening alone is insufficient."  
  \]  
}

The canonical thesis remains `INTACT`.

---

# **73\. Example: Invalidated Thesis Cannot Recover**

Input:

Canonical thesis: INVALIDATED  
Next day price rebounds  
AI proposes INTACT

Engine result:

{  
  "canonicalization\_decision": "REJECT",  
  "reasons": \[  
    "An invalidated thesis cannot be restored in the same Trade Session.",  
    "A new setup requires a new Trade Session."  
  \]  
}

---

# **74\. Test Requirements**

## **74.1 Status Tests**

Test:

* initial thesis creation;  
* intact to strengthening;  
* intact to weakening;  
* weakening to review;  
* review to invalidated;  
* unchanged status;  
* invalidated irreversibility.

## **74.2 Invalidation Tests**

Test:

* intraday break versus closing break;  
* unreadable evidence;  
* contradictory evidence;  
* exact invalidation confirmation;  
* invalidation without sufficient quality.

## **74.3 Contradiction Tests**

Test:

* unsupported status change;  
* bias reversal;  
* support-level drift;  
* probability mismatch;  
* action mismatch;  
* stale-state mismatch.

## **74.4 Canonicalization Tests**

Test:

* accept;  
* keep previous;  
* review required;  
* reject;  
* transaction rollback;  
* duplicate version conflict.

## **74.5 Position Impact Tests**

Test:

* additional-entry block;  
* under-review warning;  
* invalidation exit review;  
* stop-widening prohibition;  
* target realism deterioration.

---

# **75\. Evaluation Metrics**

The Thesis Engine should later be evaluated using:

status consistency  
invalidation precision  
invalidation recall  
false invalidation rate  
warning timeliness  
status transition stability  
contradiction detection rate  
unsupported reversal rate  
evidence traceability  
provider agreement

These metrics will be expanded in `AI_EVALUATION_PLAN.md`.

---

# **76\. Thesis Engine Acceptance Criteria**

The Thesis Engine is accepted when:

1. one Trade Session has one canonical active thesis;  
2. all thesis statuses use controlled enums;  
3. every material change requires evidence and explanation;  
4. unchanged conditions do not create artificial changes;  
5. weakening does not automatically mean invalidation;  
6. invalidation requires explicit confirmation;  
7. orderbook evidence alone does not casually invalidate a swing thesis;  
8. conflicting evidence can place the thesis under review;  
9. invalidated thesis cannot become active again in the same session;  
10. directional reversal is blocked without correction or a new session;  
11. stale analysis cannot replace canonical thesis;  
12. excluded evidence cannot support a new thesis version;  
13. additional entries are blocked after invalidation;  
14. position-management impact is always provided;  
15. stop widening cannot be used to preserve invalid thesis;  
16. target realism responds to thesis deterioration;  
17. canonicalization decisions are deterministic and auditable;  
18. all thesis versions remain immutable;  
19. timeline and notification events are generated correctly;  
20. the engine remains provider-independent.

---

# **77\. Final Thesis Engine Statement**

The TradePilot AI Thesis Engine must preserve continuity and discipline throughout the complete trade lifecycle.

It must recognize the difference between:

* normal volatility;  
* strengthening confirmation;  
* gradual deterioration;  
* unresolved conflict;  
* true invalidation.

The engine must never let one isolated screenshot, one unsupported AI response, or one emotional market reaction silently rewrite the active trading thesis.

Every canonical thesis change must be evidence-based, explainable, versioned, and auditable.

