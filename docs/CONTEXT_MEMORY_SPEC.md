# **TradePilot AI — Context and Memory Specification**

**Document:** `CONTEXT_MEMORY_SPEC.md`  
**Version:** 1.0  
**Status:** Final  
**Product Name:** TradePilot AI  
**Primary References:** `PRD.md`, `PRODUCT_RULES.md`, `DOMAIN_MODEL.md`, `SESSION_LIFECYCLE.md`, `AI_ANALYSIS_SPEC.md`, `THESIS_ENGINE_SPEC.md`  
**Purpose:** Define how TradePilot AI selects, structures, summarizes, versions, validates, and delivers Trade Session history to AI providers without losing critical trading context.

---

## **1\. Document Purpose**

This document defines the context and memory architecture used for AI analysis.

It specifies:

* what information must be remembered;  
* which records are authoritative;  
* how historical context is selected;  
* how context is prioritized;  
* how long sessions are summarized;  
* which facts may never be removed;  
* how duplicate or repetitive context is compressed;  
* how previous evidence is compared;  
* how stale context is detected;  
* how context versions are recorded;  
* how provider context limits are handled;  
* how analysis reproducibility is preserved.

The goal is to ensure that every AI analysis understands the complete relevant trade story rather than treating each screenshot as an isolated request.

---

# **2\. Core Context Principle**

TradePilot AI must maintain this rule:

The latest evidence is interpreted through the complete relevant history of the Trade Session.

The system must never send only the newest screenshot when prior session context exists.

Every follow-up analysis must know, at minimum:

* why the Trade Session was created;  
* the initial thesis;  
* the current canonical thesis;  
* what changed previously;  
* whether a position exists;  
* the actual average entry;  
* the active stop loss;  
* the active targets;  
* previous partial exits;  
* the latest valid analysis;  
* the latest relevant evidence;  
* the current user request.

---

# **3\. Definitions**

## **3.1 Source Record**

A persisted authoritative record from which context is constructed.

Examples:

* Trade Session;  
* evidence;  
* analysis version;  
* thesis version;  
* position entry;  
* position exit;  
* stop-loss version;  
* target version;  
* timeline event;  
* market snapshot;  
* user note.

---

## **3.2 Canonical Context**

The current authoritative context required to analyze the Trade Session correctly.

Canonical context is assembled from authoritative database records.

It is not stored as one uncontrolled text conversation.

---

## **3.3 Context Summary**

A structured compressed representation of older session history.

A Context Summary is derived data.

It does not replace source records.

---

## **3.4 Critical Fact**

A fact that must remain available in every relevant future analysis.

Examples:

* actual entry;  
* active stop loss;  
* active target;  
* current thesis;  
* invalidation condition;  
* position closure;  
* excluded evidence;  
* material user decision.

---

## **3.5 Comparable Update**

A previous update chosen as the best direct comparison for the current update.

Examples:

* current midday update compared with the same day’s morning update;  
* current closing update compared with the same day’s midday update;  
* current morning update compared with the previous closing update;  
* custom update compared with the latest materially relevant update.

---

## **3.6 Context Package**

The final normalized object delivered to the AI provider.

It contains:

* current request;  
* canonical state;  
* selected recent history;  
* relevant evidence;  
* compressed older history;  
* explicit instructions.

---

# **4\. Context System Objectives**

The Context and Memory system must:

1. preserve the full trade story;  
2. prioritize current authoritative state;  
3. avoid sending irrelevant history;  
4. avoid duplicate context;  
5. preserve evidence traceability;  
6. prevent stale position values;  
7. preserve the initial thesis;  
8. preserve thesis evolution;  
9. keep user execution separate from AI recommendations;  
10. remain within provider context limits;  
11. generate reproducible context packages;  
12. support provider fallback;  
13. support long-running Trade Sessions;  
14. expose context quality and omissions;  
15. preserve Bahasa Indonesia narrative while using English internal keys.

---

# **5\. Source-of-Truth Hierarchy**

When information conflicts, use this priority order:

1. **User-confirmed actual execution records**  
2. **Canonical application state**  
3. **Verified structured market data**  
4. **Current canonical thesis**  
5. **Latest accepted analysis**  
6. **User-provided explicit notes or values**  
7. **Reliable evidence extraction**  
8. **AI interpretation**  
9. **Older context summaries**

Examples:

* an actual recorded entry overrides a previously proposed AI entry;  
* an active user-confirmed stop overrides an AI stop recommendation;  
* a verified closing price overrides an AI visual estimate;  
* an excluded screenshot must not be restored through an old context summary.

---

# **6\. Context Layers**

The Context Package should be divided into distinct layers.

Layer 1 — Current Request  
Layer 2 — Canonical Session State  
Layer 3 — Current Position State  
Layer 4 — Current Thesis State  
Layer 5 — Latest Evidence and Market Data  
Layer 6 — Direct Comparison Context  
Layer 7 — Recent Significant History  
Layer 8 — Initial Trade Context  
Layer 9 — Compressed Older History  
Layer 10 — Analysis Instructions

The provider prompt must clearly label these layers.

---

# **7\. Layer 1 — Current Request**

The Current Request layer must include:

{  
  "analysis\_type": "OPEN\_POSITION\_UPDATE",  
  "update\_classification": "MIDDAY",  
  "requested\_at": "timestamp",  
  "trading\_date": "2026-07-17",  
  "market\_timestamp": "timestamp",  
  "user\_note": "Bid terlihat mulai berkurang.",  
  "requested\_output\_language": "id-ID",  
  "schema\_version": "1.0"  
}

This layer has the highest attention priority.

---

# **8\. Layer 2 — Canonical Session State**

Required fields:

{  
  "session\_id": "uuid",  
  "ticker": "BBRI",  
  "company\_name": "Bank Rakyat Indonesia",  
  "market": "IDX",  
  "currency": "IDR",  
  "lifecycle\_status": "ANALYZING",  
  "stable\_status": "OPEN\_POSITION",  
  "session\_version": 12,  
  "latest\_update\_id": "uuid",  
  "latest\_canonical\_analysis\_id": "uuid",  
  "active\_thesis\_id": "uuid",  
  "active\_position\_id": "uuid"  
}

Raw database internals not useful to the AI should be omitted.

---

# **9\. Layer 3 — Current Position State**

When a position exists, this layer is mandatory.

It must contain authoritative user-confirmed values.

{  
  "position\_status": "OPEN",  
  "position\_version": 5,  
  "average\_entry": 3090,  
  "total\_quantity": 10000,  
  "remaining\_quantity": 10000,  
  "active\_stop\_loss": {  
    "price": 2840,  
    "version": 2,  
    "technical\_basis": "Di bawah support mayor.",  
    "confirmed\_at": "timestamp"  
  },  
  "active\_targets": \[  
    {  
      "target\_type": "TP1",  
      "price": 3250,  
      "priority": 1,  
      "version": 1  
    }  
  \],  
  "entries": \[\],  
  "exits": \[\],  
  "realized\_profit\_loss": 0,  
  "unrealized\_profit\_loss": 300000,  
  "return\_percentage": 0.9709  
}

The AI must be explicitly told:

These are actual user-confirmed position values and override any previous recommendations.

---

# **10\. Layer 4 — Current Thesis State**

Required fields:

{  
  "thesis\_version": 3,  
  "thesis\_status": "INTACT\_BUT\_WEAKENING",  
  "directional\_bias": "BULLISH",  
  "thesis\_statement": "Struktur rebound masih valid selama support mayor bertahan.",  
  "technical\_rationale": "Higher low masih terjaga, tetapi orderbook melemah.",  
  "key\_support": {},  
  "key\_resistance": {},  
  "invalidation\_level": {},  
  "invalidation\_condition": "Penutupan valid di bawah support mayor.",  
  "confidence\_score": 68,  
  "effective\_at": "timestamp"  
}

The current thesis must never be reconstructed only from the latest AI narrative.

It must be loaded from the canonical thesis record.

---

# **11\. Layer 5 — Latest Evidence**

The latest evidence layer includes all evidence for the current update.

Each item must include:

* evidence ID;  
* evidence type;  
* role;  
* market timestamp;  
* upload timestamp;  
* evidence status;  
* extraction quality;  
* extracted facts;  
* image reference;  
* known limitations.

Example:

{  
  "evidence\_id": "uuid",  
  "evidence\_type": "ORDERBOOK\_SCREENSHOT",  
  "evidence\_role": "PRIMARY\_CURRENT",  
  "market\_timestamp": "2026-07-17T05:10:00Z",  
  "evidence\_status": "AVAILABLE",  
  "extraction\_quality": "HIGH\_CONFIDENCE",  
  "extracted\_facts": {  
    "best\_bid": 3110,  
    "best\_offer": 3120  
  },  
  "limitations": \[  
    "Total transaction value is not visible."  
  \]  
}

---

# **12\. Layer 6 — Direct Comparison Context**

Every follow-up analysis must include one primary comparison target.

The comparison record should contain:

{  
  "comparison\_analysis\_id": "uuid",  
  "comparison\_update\_id": "uuid",  
  "classification": "MORNING",  
  "market\_timestamp": "timestamp",  
  "analysis\_summary": {},  
  "market\_snapshot": {},  
  "orderbook\_summary": {},  
  "thesis\_status": "INTACT",  
  "confidence\_score": 74,  
  "probabilities": {},  
  "recommended\_action": "HOLD\_POSITION",  
  "evidence\_references": \[\]  
}

The AI must be instructed to explicitly compare current and previous values.

---

# **13\. Comparable Update Selection Rules**

## **13.1 Initial Analysis**

No comparison update exists.

Use:

* initial evidence only;  
* no invented historical comparison.

---

## **13.2 Morning Update**

Comparison priority:

1. previous trading day closing update;  
2. latest custom update after previous close;  
3. latest accepted open-position or watching analysis;  
4. initial analysis.

---

## **13.3 Midday Update**

Comparison priority:

1. same-day morning update;  
2. latest same-day custom update before midday;  
3. previous accepted analysis.

---

## **13.4 Closing Update**

Comparison priority:

1. same-day midday update;  
2. same-day morning update;  
3. previous trading day closing update;  
4. latest accepted analysis.

---

## **13.5 Custom Update**

Selection should consider:

* closest prior market timestamp;  
* same analytical purpose;  
* same position phase;  
* material relevance;  
* evidence compatibility.

---

# **14\. Comparison Compatibility**

Two updates are directly comparable when:

* they belong to the same Trade Session;  
* chronology is valid;  
* evidence types overlap sufficiently;  
* the position phase has not changed in a way that invalidates direct comparison;  
* market timestamps are known;  
* neither update is based only on excluded evidence.

Example:

A pre-entry watching update should not be used as the sole comparison for a post-partial-exit analysis.

It may remain historical context, but a later open-position update is more directly comparable.

---

# **15\. Layer 7 — Recent Significant History**

Recent history should include:

* latest accepted analyses;  
* recent thesis changes;  
* recent position mutations;  
* recent stop or target changes;  
* recent material user notes;  
* recent warnings;  
* unresolved questions.

Recommended default selection:

latest 3 accepted analyses  
latest 3 thesis versions  
all position events since last accepted analysis  
all stop/target changes since last accepted analysis  
latest unresolved warning

These limits are configurable.

---

# **16\. Layer 8 — Initial Trade Context**

The initial trade context must remain available throughout the session.

Required initial facts:

* initial analysis summary;  
* initial thesis;  
* original support;  
* original resistance;  
* original invalidation;  
* planned entry;  
* planned stop;  
* planned targets;  
* initial confidence;  
* initial probability values;  
* initial evidence references.

The initial context may be compressed but must not disappear.

---

# **17\. Layer 9 — Compressed Older History**

Older history should be represented through a versioned Context Summary.

It may include:

* chronological update summaries;  
* thesis progression;  
* support/resistance evolution;  
* user execution history;  
* major warnings;  
* rejected recommendations;  
* resolved questions;  
* important outcome checkpoints.

It should not include repetitive low-value observations.

---

# **18\. Layer 10 — Analysis Instructions**

The final instruction layer must remind the AI to:

* use current canonical values;  
* compare against the selected prior update;  
* preserve the original thesis history;  
* separate facts from interpretation;  
* state uncertainty;  
* not invent values;  
* not apply position changes;  
* return the required schema;  
* use Bahasa Indonesia narratives.

---

# **19\. Critical Memory Set**

The following values must be included whenever relevant and must never be lost through summarization:

ticker  
market  
session lifecycle  
current position status  
actual average entry  
remaining quantity  
active stop loss  
active targets  
actual entries  
actual exits  
current thesis  
thesis invalidation condition  
latest accepted analysis  
initial thesis  
material thesis changes  
excluded evidence  
user-confirmed corrections  
latest material warning

---

# **20\. Persistent Decision Memory**

User decisions must be stored explicitly and included in context when relevant.

Examples:

* user opened position at a different price from the AI plan;  
* user changed stop loss;  
* user declined a recommended partial exit;  
* user added an entry;  
* user closed the position manually;  
* user marked evidence as incorrect.

The AI must not later treat a rejected recommendation as executed.

---

# **21\. Recommendation Versus Execution Memory**

The context system must maintain separate objects for:

AI proposed action  
user-confirmed action  
actual execution result

Example:

{  
  "ai\_recommendation": {  
    "action": "CONSIDER\_PARTIAL\_PROFIT",  
    "analysis\_id": "uuid"  
  },  
  "user\_execution": null,  
  "execution\_status": "NOT\_EXECUTED"  
}

This distinction is mandatory for journal accuracy.

---

# **22\. Context Summary Aggregate**

The persisted Context Summary should follow a structured schema.

{  
  "schema\_version": "1.0",  
  "session\_id": "uuid",  
  "summary\_version": 4,  
  "source\_cutoff": "timestamp",  
  "active\_thesis\_summary": {},  
  "initial\_thesis\_summary": {},  
  "position\_summary": {},  
  "key\_level\_summary": {},  
  "trade\_plan\_summary": {},  
  "update\_history\_summary": \[\],  
  "thesis\_change\_summary": \[\],  
  "position\_event\_summary": \[\],  
  "resolved\_questions": \[\],  
  "unresolved\_questions": \[\],  
  "current\_risks": \[\],  
  "critical\_facts": \[\],  
  "source\_analysis\_ids": \[\],  
  "source\_event\_ids": \[\]  
}

---

# **23\. Context Summary Generation Triggers**

A new Context Summary should be generated when:

* initial analysis becomes canonical;  
* thesis changes materially;  
* position is opened;  
* stop loss changes;  
* target changes materially;  
* additional entry is recorded;  
* partial exit occurs;  
* session history exceeds context threshold;  
* session closes;  
* evidence correction affects history;  
* current summary is marked stale.

---

# **24\. Context Summary Refresh Policy**

A refresh is not required for every screenshot.

Refresh should occur when new information changes persistent trade meaning.

Examples that usually require refresh:

* thesis weakening;  
* invalidation;  
* new position entry;  
* partial exit;  
* stop change;  
* material target change.

Examples that may not require refresh:

* no-material-change analysis;  
* duplicate evidence;  
* a minor note with no impact.

---

# **25\. Summary Versioning**

Every Context Summary must include:

* version number;  
* source cutoff;  
* source analysis IDs;  
* source timeline cutoff;  
* generation timestamp;  
* generating job;  
* schema version;  
* superseded timestamp.

Previous summaries remain immutable.

---

# **26\. Summary Staleness**

A Context Summary becomes stale when:

* a source record is corrected;  
* evidence used in the summary is excluded;  
* a position transaction changes;  
* thesis is corrected;  
* a journal-affecting correction occurs;  
* current source cutoff predates a critical event.

A stale summary must not be used as the sole context source.

---

# **27\. Summary Validation**

Before becoming canonical, a Context Summary must pass:

1. schema validation;  
2. source-reference validation;  
3. critical-fact presence check;  
4. position-state consistency check;  
5. thesis-state consistency check;  
6. chronology validation;  
7. language validation;  
8. omission detection.

---

# **28\. Critical Fact Presence Check**

The validator must confirm that required facts are preserved.

For an open position, the summary must include:

* average entry;  
* active stop;  
* active targets;  
* current thesis;  
* invalidation;  
* remaining quantity when available.

For a closed position, it must include:

* final entry summary;  
* final exit;  
* closure reason;  
* realized outcome;  
* final thesis state.

---

# **29\. Context Budgeting**

The Context Builder must operate within a configured token budget.

Recommended conceptual allocation:

Current request and instructions          10%  
Canonical state                          20%  
Current evidence and extracted facts     25%  
Direct comparison context                15%  
Recent significant history               15%  
Initial context                           5%  
Compressed older history                 10%

The actual token count depends on the model.

Critical layers must not be removed to preserve low-value narrative.

---

# **30\. Context Reduction Order**

When context must be shortened, remove or compress information in this order:

1. duplicate narrative;  
2. repeated no-material-change analyses;  
3. redundant evidence descriptions;  
4. low-importance timeline events;  
5. old non-critical market snapshots;  
6. verbose technical wording;  
7. resolved non-critical questions;  
8. old evidence thumbnails.

Never remove before lower-value context:

* current position;  
* current thesis;  
* invalidation condition;  
* actual execution;  
* current evidence;  
* primary comparison;  
* major thesis changes.

---

# **31\. Evidence Selection Strategy**

The Context Builder should select evidence using:

relevance  
recency  
quality  
comparability  
materiality  
independence

A suggested score:

selection\_score \=  
    relevance\_weight  
  \+ recency\_weight  
  \+ quality\_weight  
  \+ comparability\_weight  
  \+ materiality\_weight  
  \+ independence\_weight

The exact formula must be configurable.

---

# **32\. Evidence Selection Rules**

Always include:

* current update evidence;  
* direct comparison evidence;  
* initial evidence when structurally relevant;  
* evidence supporting the current thesis;  
* evidence supporting material thesis changes;  
* evidence related to active invalidation.

Conditionally include:

* older evidence used in significant analyses;  
* contradictory evidence;  
* user notes.

Exclude:

* evidence marked `EXCLUDED`;  
* deleted evidence;  
* failed uploads;  
* irrelevant duplicates;  
* stale evidence without explanatory purpose.

---

# **33\. Duplicate Evidence Handling**

Duplicate evidence must not be counted as multiple independent confirmations.

The Context Builder should detect duplicates through:

* checksum;  
* perceptual similarity metadata, future;  
* identical market timestamp;  
* identical extraction;  
* explicit duplicate status.

One original may be included with a note that duplicates exist.

---

# **34\. Unreadable Evidence Handling**

Unreadable evidence may be included only to explain limitations.

It must not provide exact values.

Example context:

{  
  "evidence\_id": "uuid",  
  "status": "UNREADABLE",  
  "use": "LIMITATION\_ONLY",  
  "limitations": \[  
    "Angka bid dan offer tidak terbaca."  
  \]  
}

---

# **35\. Excluded Evidence Handling**

Excluded evidence must not be included in new model prompts.

Historical analysis records may still reference it for audit purposes.

The context package may state:

A prior analysis used evidence that was later excluded.

This is important when evaluating historical reliability.

---

# **36\. Chronology Rules**

Context must be sorted primarily by reliable market timestamp.

Fallback order:

1. market timestamp;  
2. trading date plus update classification;  
3. evidence upload timestamp;  
4. analysis completion timestamp.

Upload time must not be interpreted as market time.

---

# **37\. Timezone Rules**

All persisted timestamps use UTC.

The context package should provide:

* UTC timestamps;  
* trading timezone;  
* localized trading date;  
* update classification.

The AI should reason in `Asia/Jakarta` for IDX sessions.

---

# **38\. Future Timestamp Guard**

Evidence with market timestamps in the future relative to the request must be rejected or flagged.

The Context Builder must not silently reorder impossible timestamps.

---

# **39\. Analysis History Selection**

Default accepted-analysis selection:

latest accepted analysis  
previous comparable accepted analysis  
latest material thesis-change analysis  
initial analysis

Additional accepted analyses may be represented through the Context Summary.

Rejected analyses must not be included as authoritative context.

They may be included only under a diagnostic section when contradiction review requires them.

---

# **40\. Non-Canonical Analysis Handling**

A non-canonical or rejected analysis may be included only when:

* resolving a contradiction;  
* explaining a prior system warning;  
* auditing provider disagreement;  
* evaluating a failed recommendation.

It must be clearly labeled:

NON\_CANONICAL  
REJECTED  
OUTDATED

---

# **41\. Position Event Selection**

For an active position, include all material events:

* initial entry;  
* additional entries;  
* partial exits;  
* active stop creation;  
* stop changes;  
* active target creation;  
* target changes.

For very long histories, older event details may be summarized, but the resulting average entry and remaining quantity must remain explicit.

---

# **42\. Position Snapshot at Analysis Time**

Each analysis request must capture:

session version  
position version  
active thesis version  
active stop version  
active target versions  
latest update ID  
context summary version

These references are used for stale-state validation.

---

# **43\. Context Fingerprint**

Each context package should have a deterministic fingerprint.

Suggested inputs:

* session ID;  
* analysis type;  
* update ID;  
* session version;  
* position version;  
* thesis version;  
* evidence IDs and checksums;  
* context summary version;  
* prompt version;  
* schema version.

Example:

SHA-256(normalized context manifest)

The fingerprint supports:

* reproducibility;  
* idempotency;  
* debugging;  
* duplicate-job prevention.

---

# **44\. Context Manifest**

Every analysis request should store a manifest.

{  
  "context\_fingerprint": "sha256",  
  "session\_version": 12,  
  "position\_version": 5,  
  "thesis\_version": 3,  
  "context\_summary\_version": 4,  
  "analysis\_ids": \[\],  
  "evidence\_ids": \[\],  
  "timeline\_event\_ids": \[\],  
  "market\_snapshot\_ids": \[\],  
  "excluded\_items": \[\],  
  "token\_estimate": 18400  
}

---

# **45\. Reproducibility Requirement**

Given the same:

* source records;  
* context-selection configuration;  
* prompt version;  
* schema version;

the Context Builder should produce semantically equivalent context.

Ordering must be deterministic.

---

# **46\. Context Builder Pipeline**

Receive analysis request  
        ↓  
Load canonical session  
        ↓  
Load authoritative position  
        ↓  
Load canonical thesis  
        ↓  
Load current update and evidence  
        ↓  
Select comparable update  
        ↓  
Load recent significant history  
        ↓  
Load initial trade context  
        ↓  
Load or refresh Context Summary  
        ↓  
Remove excluded and duplicate evidence  
        ↓  
Validate chronology  
        ↓  
Apply token budgeting  
        ↓  
Create context manifest and fingerprint  
        ↓  
Persist request snapshot  
        ↓  
Send normalized context to provider

---

# **47\. Context Selection Service Interface**

Conceptual interface:

class ContextSelectionService:  
    def build\_context(  
        self,  
        session\_id: UUID,  
        analysis\_type: AnalysisType,  
        current\_update\_id: UUID | None,  
        token\_budget: int,  
    ) \-\> ContextPackage:  
        ...

Supporting methods:

select\_comparable\_update()  
select\_current\_evidence()  
select\_recent\_analysis\_history()  
select\_material\_thesis\_history()  
select\_position\_events()  
load\_initial\_context()  
load\_context\_summary()  
apply\_context\_budget()  
validate\_context()  
create\_manifest()

---

# **48\. Context Package Structure**

Recommended normalized structure:

{  
  "context\_metadata": {},  
  "current\_request": {},  
  "canonical\_session": {},  
  "canonical\_position": {},  
  "canonical\_thesis": {},  
  "current\_update": {},  
  "current\_evidence": \[\],  
  "direct\_comparison": {},  
  "recent\_significant\_history": {},  
  "initial\_trade\_context": {},  
  "compressed\_history": {},  
  "critical\_facts": \[\],  
  "known\_limitations": \[\],  
  "analysis\_instructions": {}  
}

---

# **49\. Critical Fact Object**

Each critical fact should be represented as:

{  
  "fact\_type": "ACTIVE\_STOP\_LOSS",  
  "value": 2840,  
  "source\_type": "USER\_CONFIRMED",  
  "source\_id": "uuid",  
  "effective\_at": "timestamp",  
  "must\_not\_override": true  
}

Possible fact types:

ACTUAL\_ENTRY  
AVERAGE\_ENTRY  
REMAINING\_QUANTITY  
ACTIVE\_STOP\_LOSS  
ACTIVE\_TARGET  
POSITION\_STATUS  
CURRENT\_THESIS  
INVALIDATION\_CONDITION  
FINAL\_EXIT  
USER\_CORRECTION  
EVIDENCE\_EXCLUSION

---

# **50\. Conflict Resolution Rules**

When two context sources conflict:

## **50.1 Actual Execution Versus AI Recommendation**

Use actual execution.

## **50.2 Canonical Thesis Versus Old Analysis**

Use canonical thesis.

## **50.3 Verified Value Versus AI Extraction**

Use verified value.

## **50.4 Current Stop Versus Historical Stop**

Use current stop and preserve historical stop only as history.

## **50.5 User Correction Versus Original Record**

Use corrected canonical calculation and preserve original record in correction history.

## **50.6 Context Summary Versus Source Record**

Use source record.

---

# **51\. Conflict Annotation**

The Context Builder should explicitly annotate unresolved conflicts.

{  
  "conflict\_type": "MARKET\_VALUE\_CONFLICT",  
  "field": "last\_price",  
  "source\_a": {  
    "value": 3120,  
    "source": "USER\_PROVIDED"  
  },  
  "source\_b": {  
    "value": 3110,  
    "source": "AI\_EXTRACTED"  
  },  
  "resolution": "USE\_SOURCE\_A",  
  "reason": "User-provided value has higher authority."  
}

---

# **52\. Missing Context Detection**

The Context Builder must detect missing information required by each analysis type.

Examples:

## **Initial Analysis**

* required chart missing;  
* unreadable orderbook;  
* ticker missing.

## **Open Position Update**

* active stop missing;  
* target missing;  
* position snapshot unavailable;  
* previous analysis missing.

## **Closing Analysis**

* final exit missing;  
* entry history inconsistent;  
* closure reason missing.

---

# **53\. Context Quality Score**

The system may calculate a context quality score from 0 to 100\.

Suggested components:

required data completeness       30%  
evidence readability             20%  
historical continuity            20%  
source consistency               15%  
chronology quality               10%  
context-summary freshness         5%

Suggested classification:

0–39   LOW\_CONFIDENCE  
40–69  MODERATE\_CONFIDENCE  
70–100 HIGH\_CONFIDENCE

This score contributes to analysis confidence.

---

# **54\. Low-Quality Context Behavior**

When context quality is low:

* analysis may still run when safe;  
* confidence must decrease;  
* missing data must be disclosed;  
* deterministic user execution must remain authoritative;  
* thesis invalidation may require review instead of automatic acceptance.

When critical context is missing, analysis must be blocked.

---

# **55\. Context Build Blocking Conditions**

Block analysis when:

* current evidence is unavailable;  
* required initial evidence is incomplete;  
* session ownership cannot be verified;  
* position state cannot be loaded for an open-position analysis;  
* canonical thesis is missing where required;  
* context chronology is irreparably inconsistent;  
* source records fail integrity checks;  
* required evidence was excluded after request creation.

---

# **56\. Context Compression Rules**

Compression should:

* preserve facts;  
* shorten prose;  
* merge repeated unchanged observations;  
* preserve chronology;  
* preserve material changes;  
* preserve source references.

Compression must not:

* invent causal relationships;  
* remove losing decisions;  
* convert recommendations into execution;  
* erase uncertainty;  
* alter numerical values;  
* rewrite an invalidated thesis as active.

---

# **57\. Repeated No-Material-Change Updates**

Multiple repetitive updates may be summarized as:

{  
  "period": {  
    "from": "timestamp",  
    "to": "timestamp"  
  },  
  "summary": "Tiga update berturut-turut tidak menunjukkan perubahan material.",  
  "thesis\_status": "INTACT",  
  "support\_unchanged": true,  
  "target\_unchanged": true,  
  "source\_analysis\_ids": \[\]  
}

The original analyses remain stored.

---

# **58\. Material Event Preservation**

The following events must never be collapsed into an unlabeled generic summary:

* thesis invalidation;  
* position opening;  
* additional entry;  
* stop widening;  
* partial exit;  
* full exit;  
* target removal;  
* evidence exclusion;  
* historical correction;  
* user overriding an AI recommendation.

---

# **59\. Provider Context Limits**

The provider adapter must expose:

maximum context tokens  
maximum image count  
maximum image size  
supported image formats  
maximum output tokens

The Context Builder must use the effective minimum of:

* configured application limit;  
* provider capability;  
* selected model limit.

---

# **60\. Image Budgeting**

When image count exceeds provider limits, prioritize:

1. current primary evidence;  
2. direct comparison evidence;  
3. initial structural charts;  
4. evidence supporting material thesis changes;  
5. older secondary images.

Excluded images may still be represented through validated extracted data and summary references.

---

# **61\. Image Preprocessing Context**

The AI must receive metadata explaining transformations.

Example:

{  
  "original\_evidence\_id": "uuid",  
  "variant": "AI\_INPUT",  
  "orientation\_normalized": true,  
  "resized": true,  
  "cropped": false,  
  "original\_preserved": true  
}

The system must not imply that a processed variant is the original file.

---

# **62\. Context Privacy**

The context package must include only information needed for analysis.

Do not send:

* password data;  
* authentication tokens;  
* API keys;  
* unrelated user profile data;  
* internal server paths;  
* unnecessary IP or audit metadata.

---

# **63\. Provider-Neutral Context**

The normalized Context Package must remain independent of Gemini or DeepSeek formatting.

Provider adapters may transform:

* JSON envelope;  
* image encoding;  
* system prompt format;  
* structured-output settings.

They must not change context meaning.

---

# **64\. Fallback Provider Context**

When a fallback provider is used:

* use the same context manifest;  
* preserve the same source records;  
* preserve the same schema version;  
* record any provider-specific truncation;  
* recalculate token and image budget if necessary.

Fallback output must be comparable with the primary attempt.

---

# **65\. Context Version Metadata in Analysis**

Every analysis version must record:

context fingerprint  
context-summary version  
session version  
position version  
thesis version  
selected comparison update  
selected evidence IDs  
token estimate  
provider-adjusted omissions

---

# **66\. Stale Context Validation**

Before canonicalizing an AI response, compare:

request session version  
current session version  
request position version  
current position version  
request thesis version  
current thesis version  
request evidence set  
current evidence statuses

A mismatch does not always invalidate the entire analysis.

The system must classify the mismatch as:

NON\_CRITICAL  
MATERIAL  
CRITICAL

---

# **67\. Non-Critical Staleness**

Examples:

* session title changed;  
* a non-material note was added;  
* unrelated notification was read.

The analysis may still become canonical.

---

# **68\. Material Staleness**

Examples:

* new evidence uploaded;  
* thesis changed;  
* latest price updated materially;  
* target changed.

Result:

* review applicability;  
* possibly store as non-canonical;  
* optionally rerun.

---

# **69\. Critical Staleness**

Examples:

* position opened or closed;  
* partial exit occurred;  
* stop changed;  
* additional entry changed average price;  
* evidence used by analysis was excluded;  
* thesis invalidated by another accepted analysis.

Result:

Do not canonicalize.

---

# **70\. Context Audit Events**

The system should record internal events such as:

CONTEXT\_BUILD\_STARTED  
CONTEXT\_BUILD\_COMPLETED  
CONTEXT\_SUMMARY\_CREATED  
CONTEXT\_SUMMARY\_SUPERSEDED  
CONTEXT\_SUMMARY\_STALE  
CONTEXT\_TRUNCATED  
CONTEXT\_BUILD\_FAILED  
CONTEXT\_STALE\_AT\_CANONICALIZATION

These do not all need to appear on the user-facing timeline.

---

# **71\. Context Build Failure Codes**

Recommended codes:

CONTEXT\_SESSION\_NOT\_FOUND  
CONTEXT\_POSITION\_NOT\_FOUND  
CONTEXT\_THESIS\_NOT\_FOUND  
CONTEXT\_CURRENT\_UPDATE\_NOT\_FOUND  
CONTEXT\_REQUIRED\_EVIDENCE\_MISSING  
CONTEXT\_EVIDENCE\_EXCLUDED  
CONTEXT\_CHRONOLOGY\_INVALID  
CONTEXT\_SUMMARY\_INVALID  
CONTEXT\_SUMMARY\_STALE  
CONTEXT\_TOKEN\_LIMIT\_EXCEEDED  
CONTEXT\_IMAGE\_LIMIT\_EXCEEDED  
CONTEXT\_FINGERPRINT\_FAILED  
CONTEXT\_INTEGRITY\_FAILED

---

# **72\. Context Retry Rules**

Retry may occur when:

* temporary database read fails;  
* file metadata is temporarily unavailable;  
* summary-generation job fails;  
* provider token estimation fails.

Retry should not proceed blindly when:

* required evidence is excluded;  
* position state is inconsistent;  
* chronology is invalid;  
* source records violate integrity rules.

---

# **73\. Context Summary Generation by AI**

If AI is used to produce a Context Summary:

* provide structured source facts;  
* require structured output;  
* validate critical facts deterministically;  
* reject unsupported additions;  
* ensure source references are retained.

Deterministic fields such as actual entry and stop must be inserted or validated by the application.

---

# **74\. Hybrid Summary Generation**

Recommended approach:

## **Deterministic Section**

Generated by application:

* position values;  
* active stop;  
* targets;  
* lifecycle;  
* timestamps;  
* source IDs;  
* thesis status;  
* numeric probabilities.

## **AI-Assisted Section**

Generated by AI:

* concise thesis journey;  
* update-history narrative;  
* unresolved questions;  
* current risk summary.

This reduces hallucination risk.

---

# **75\. User Note Handling**

User notes should be classified as:

FACT  
OBSERVATION  
DECISION  
QUESTION  
REFLECTION  
UNKNOWN

The AI should not automatically treat every note as verified market fact.

Example:

“Sepertinya bandar sedang akumulasi.”

This is a user interpretation, not a verified fact.

---

# **76\. Explicit User Facts**

When the user explicitly provides:

* actual entry;  
* stop;  
* target;  
* executed exit;  
* observed market value;

the application should store it in structured form whenever possible.

Structured facts should not remain only inside free-text notes.

---

# **77\. Context for Initial Analysis**

The initial context package must include:

* session identity;  
* all required initial evidence;  
* optional initial note;  
* available market snapshot;  
* no position;  
* no prior thesis;  
* explicit instruction not to fabricate history.

The output must create the first thesis rather than compare against a nonexistent one.

---

# **78\. Context for Watching Update**

Must include:

* initial thesis;  
* current thesis;  
* planned entry;  
* planned stop;  
* planned targets;  
* latest accepted watching analysis;  
* comparable update;  
* current evidence;  
* cancellation conditions.

The AI must assess whether entry conditions remain valid.

---

# **79\. Context for Open-Position Update**

Must include:

* actual average entry;  
* all relevant entries;  
* remaining quantity;  
* active stop;  
* targets;  
* partial exits;  
* entry thesis snapshot;  
* current thesis;  
* latest accepted open-position analysis;  
* comparable evidence;  
* current evidence;  
* user decisions since prior analysis.

---

# **80\. Context for Partial Exit Review**

Must include:

* position before partial exit;  
* actual partial exit;  
* recommendation that preceded it, if any;  
* position after partial exit;  
* realized result;  
* remaining stop and targets;  
* latest thesis.

---

# **81\. Context for Closing Analysis**

Must include:

* all actual entries;  
* all actual exits;  
* stop history;  
* target history;  
* thesis history;  
* latest analysis before exit;  
* final thesis state;  
* actual closure reason;  
* final result;  
* material timeline events.

---

# **82\. Context for Trading Journal**

The journal context must use the complete relevant session history.

Required:

* initial evidence and thesis;  
* all accepted analyses;  
* material non-canonical warnings when relevant;  
* thesis versions;  
* entries and exits;  
* stop changes;  
* target changes;  
* user decisions;  
* AI recommendations;  
* final result;  
* closing analysis;  
* user reflection, when generated after reflection.

The journal context must clearly identify what was known at each point in time.

---

# **83\. Hindsight Protection**

The context package for journal generation must label information by availability time.

Example:

{  
  "fact": "Support eventually failed.",  
  "known\_at": "2026-07-18T09:00:00Z",  
  "available\_during\_initial\_entry": false  
}

The journal must not criticize an earlier decision using information unavailable at that time without labeling it as hindsight.

---

# **84\. Context for Thesis Review**

Must include:

* current thesis;  
* latest contradictory analysis;  
* evidence for both sides;  
* invalidation condition;  
* unresolved questions;  
* current position risk;  
* chronology.

The focused review should omit unrelated verbose history.

---

# **85\. Context Comparison Output Support**

The Context Builder should precompute comparison-friendly facts where deterministic.

Example:

{  
  "previous": {  
    "best\_bid": 3110,  
    "best\_offer": 3120,  
    "confidence": 74  
  },  
  "current": {  
    "best\_bid": 3090,  
    "best\_offer": 3100,  
    "confidence": null  
  },  
  "calculated\_changes": {  
    "best\_bid\_absolute": \-20,  
    "best\_bid\_percentage": \-0.6431  
  }  
}

The AI explains meaning, while the application calculates exact differences.

---

# **86\. Context Configuration**

Recommended configuration:

context\_memory:  
  default\_token\_budget: 24000  
  maximum\_recent\_analyses: 3  
  maximum\_recent\_thesis\_versions: 3  
  maximum\_recent\_timeline\_events: 20  
  maximum\_direct\_comparison\_evidence: 4  
  maximum\_initial\_reference\_images: 3  
  maximum\_total\_images: 10

  include\_initial\_analysis: true  
  include\_initial\_thesis: true  
  include\_rejected\_analyses: false  
  include\_non\_material\_timeline\_events: false

  context\_summary\_refresh\_event\_threshold: 8  
  context\_summary\_refresh\_token\_threshold: 12000  
  context\_summary\_max\_age\_hours: 24

  critical\_staleness\_blocks\_canonicalization: true  
  material\_staleness\_requires\_review: true

Final values will be locked in `CONFIG_SPEC.md`.

---

# **87\. Context Metrics**

The system should track:

context build duration  
context token estimate  
number of selected evidence items  
number of omitted evidence items  
image count  
summary usage  
context quality score  
stale-context frequency  
canonicalization rejection due to staleness  
provider truncation frequency  
context build failure rate

---

# **88\. Context Debug View**

A restricted development or administrative view should display:

* context manifest;  
* selected source records;  
* omitted records and reasons;  
* token budget;  
* context fingerprint;  
* summary version;  
* staleness result;  
* provider transformation details.

This view must not expose secrets or raw private filesystem paths.

---

# **89\. Context Explainability**

For each analysis, the system should be able to answer:

* which evidence was used;  
* which prior analysis was compared;  
* which thesis version was active;  
* which position version was used;  
* whether a Context Summary was used;  
* what was omitted;  
* whether the context was truncated;  
* whether the output later became stale.

---

# **90\. Context Integrity Checks**

Recommended integrity checks:

1. current thesis belongs to session;  
2. current position belongs to session;  
3. active stop belongs to position;  
4. active targets belong to position;  
5. comparison update predates current update;  
6. evidence belongs to session;  
7. excluded evidence is absent;  
8. source analysis is accepted;  
9. summary source IDs exist;  
10. context critical facts match canonical records;  
11. position snapshot matches request version;  
12. initial thesis is preserved.

---

# **91\. Test Requirements**

## **91.1 Selection Tests**

Test:

* morning comparison selection;  
* midday comparison selection;  
* closing comparison selection;  
* custom update selection;  
* comparison across position-phase changes.

## **91.2 Critical Memory Tests**

Test preservation of:

* entry;  
* stop;  
* targets;  
* thesis;  
* invalidation;  
* partial exit;  
* user correction.

## **91.3 Compression Tests**

Test:

* repeated no-change updates;  
* long thesis history;  
* duplicate evidence;  
* large timeline;  
* token-budget reduction.

## **91.4 Conflict Tests**

Test:

* user value versus AI extraction;  
* current stop versus historical stop;  
* canonical thesis versus old analysis;  
* excluded evidence in summary;  
* corrected execution data.

## **91.5 Staleness Tests**

Test:

* stop changed during analysis;  
* partial exit during analysis;  
* new evidence during analysis;  
* non-critical title change;  
* position closure during analysis.

## **91.6 Provider Limit Tests**

Test:

* image-count overflow;  
* token overflow;  
* provider fallback with smaller limits;  
* truncated older history;  
* required-image preservation.

---

# **92\. Context Acceptance Criteria**

The Context and Memory system is accepted when:

1. follow-up analysis never receives only the latest screenshot;  
2. current canonical state is always prioritized;  
3. actual execution overrides AI recommendations;  
4. the initial thesis remains available throughout the session;  
5. the current thesis and invalidation condition cannot be lost;  
6. active stop and targets are always included for open positions;  
7. direct comparison selection is deterministic;  
8. excluded evidence is not used in new prompts;  
9. duplicate evidence is not counted as independent confirmation;  
10. long history can be compressed without losing critical facts;  
11. Context Summaries are structured and versioned;  
12. stale summaries are detected;  
13. every context package has a manifest and fingerprint;  
14. provider token and image limits are respected;  
15. critical context is preserved before low-value history;  
16. context chronology is validated;  
17. stale analysis is blocked from unsafe canonicalization;  
18. journal context protects against hindsight rewriting;  
19. context packages are provider-neutral;  
20. each analysis remains explainable and reproducible.

---

# **93\. Final Context and Memory Statement**

TradePilot AI must remember the trade as a structured sequence of facts, evidence, decisions, analyses, and outcomes.

Its memory must not behave like an uncontrolled chat transcript.

The system must always know:

* what the original plan was;  
* what the user actually did;  
* what the current position is;  
* which thesis is canonical;  
* why that thesis changed;  
* which evidence was used;  
* what remains unresolved;  
* what happened previously.

When the Trade Session becomes long, the system may compress wording, but it must never compress away the truth of the trade.

