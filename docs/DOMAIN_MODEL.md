# **TradePilot AI — Domain Model**

**Document:** `DOMAIN_MODEL.md`  
**Version:** 1.0  
**Status:** Final  
**Product Name:** TradePilot AI  
**Primary References:** `PRD.md`, `PRODUCT_RULES.md`, `USER_FLOWS.md`, `UX_UI_SPEC.md`, `ARCHITECTURE.md`  
**Purpose:** Define the business entities, aggregates, value objects, enums, invariants, domain services, events, and relationships used by TradePilot AI.

---

## **1\. Document Purpose**

This document defines the authoritative domain model for TradePilot AI.

The model translates product behavior into implementation-neutral business concepts.

It defines:

* aggregate boundaries;  
* domain entities;  
* value objects;  
* lifecycle states;  
* controlled enums;  
* business invariants;  
* domain operations;  
* domain events;  
* canonical state;  
* immutable history;  
* relationships between Trade Sessions, positions, evidence, analyses, theses, and journals.

This document does not define physical database tables. Database representation will be defined in:

* `DATABASE_SCHEMA.md`  
* `DATABASE_SCHEMA.sql`

This document does not define REST payloads. API contracts will be defined in:

* `API_SPEC.md`

---

# **2\. Domain Modeling Principles**

## **2.1 Trade Session Is the Central Business Context**

A Trade Session is the main business context that connects:

* one ticker;  
* one trading setup;  
* one thesis;  
* one position lifecycle;  
* one evidence history;  
* one analysis history;  
* one timeline;  
* one final journal.

A Trade Session is not merely a folder or conversation.

It is the authoritative record of one complete trade story.

---

## **2.2 Canonical State Is Separate from Historical State**

The system must distinguish between:

### **Canonical State**

The current authoritative state, such as:

* current lifecycle status;  
* current thesis;  
* current stop loss;  
* active targets;  
* current position;  
* latest valid analysis;  
* current confidence;  
* current probabilities.

### **Historical State**

Immutable or append-only records, such as:

* previous analyses;  
* thesis versions;  
* entries;  
* exits;  
* previous stop losses;  
* previous targets;  
* evidence;  
* timeline events;  
* journal versions.

Canonical state provides efficient current-state access.

Historical state provides traceability and longitudinal reasoning.

---

## **2.3 AI Output Is Not Automatically Domain Truth**

An AI-generated result is initially a proposal.

It becomes canonical only after:

* structured-output validation;  
* required-field validation;  
* language validation;  
* numerical validation;  
* logical validation;  
* contradiction detection;  
* application-level acceptance.

The AI provider cannot directly mutate domain entities.

---

## **2.4 Position Mutations Require User Confirmation**

The following operations require explicit user action:

* opening a position;  
* recording an additional entry;  
* changing stop loss;  
* changing targets;  
* recording a partial exit;  
* closing a position.

AI recommendations may create proposed values but must not create actual position transactions.

---

## **2.5 Domain Models Use English**

All domain object names, properties, enums, event names, and invariants use English.

User-facing Indonesian labels are presentation-layer mappings and are not part of the stored domain identity.

---

# **3\. Domain Context Map**

The TradePilot AI domain is divided into the following logical modules:

Authentication  
    │  
    ▼  
Trade Sessions  
    ├── Evidence  
    ├── Analysis  
    ├── Thesis  
    ├── Position  
    ├── Timeline  
    └── Journal

Supporting Modules  
    ├── AI Orchestration  
    ├── Background Jobs  
    ├── Notifications  
    ├── Audit  
    ├── Configuration  
    └── AI Usage

---

# **4\. Aggregate Overview**

The primary aggregates are:

1. `TradeSession`  
2. `Position`  
3. `AnalysisRequest`  
4. `AnalysisVersion`  
5. `TradingThesis`  
6. `TradingJournal`  
7. `Evidence`  
8. `BackgroundJob`  
9. `UserAccount`  
10. `AIProviderConfiguration`

Not every entity must be implemented as a fully isolated transactional aggregate. The final persistence strategy may use application-service transactions across closely related aggregates.

---

# **5\. TradeSession Aggregate**

## **5.1 Definition**

`TradeSession` represents one ticker, one trading setup, and one complete trade lifecycle.

It is the root context for all trade-related information.

---

## **5.2 Core Properties**

TradeSession  
\- id  
\- owner\_id  
\- ticker  
\- company\_name  
\- market  
\- title  
\- initial\_note  
\- lifecycle\_status  
\- stable\_status  
\- archive\_state  
\- current\_phase  
\- active\_thesis\_id  
\- active\_position\_id  
\- latest\_canonical\_analysis\_id  
\- canonical\_context\_summary\_id  
\- latest\_confidence\_score  
\- latest\_target\_probability  
\- latest\_thesis\_status  
\- latest\_recommended\_action  
\- last\_evidence\_at  
\- last\_analysis\_at  
\- last\_position\_event\_at  
\- created\_at  
\- updated\_at  
\- closed\_at  
\- archived\_at

---

## **5.3 TradeSession Invariants**

### **TS-INV-001**

A Trade Session must belong to exactly one owner.

### **TS-INV-002**

A Trade Session must have exactly one ticker.

### **TS-INV-003**

The ticker cannot be changed after the initial analysis becomes canonical.

A correction workflow may exist before initial analysis.

### **TS-INV-004**

One Trade Session may contain only one connected trading thesis lifecycle.

### **TS-INV-005**

A closed Trade Session cannot return to an active position state.

### **TS-INV-006**

A cancelled session cannot contain a historical position entry.

### **TS-INV-007**

An archived session retains its underlying terminal or stable business state.

### **TS-INV-008**

Only one analysis version may be the latest canonical analysis at a time.

### **TS-INV-009**

Only one thesis version may be the active canonical thesis at a time.

### **TS-INV-010**

Only one position may be active in a Trade Session.

---

## **5.4 TradeSession Lifecycle Status**

DRAFT  
READY\_FOR\_ANALYSIS  
ANALYZING  
WATCHING  
OPEN\_POSITION  
PARTIALLY\_CLOSED  
CLOSED\_TAKE\_PROFIT  
CLOSED\_STOP\_LOSS  
CLOSED\_MANUAL  
CANCELLED  
ARCHIVED

---

## **5.5 Stable Status**

Because `ANALYZING` is temporary, the session should preserve its previous stable status.

Example:

lifecycle\_status \= ANALYZING  
stable\_status \= OPEN\_POSITION

After the job completes or fails, the session returns to an appropriate stable status.

---

## **5.6 TradeSession Operations**

Recommended domain operations:

create\_session()  
update\_draft\_identity()  
mark\_ready\_for\_analysis()  
begin\_analysis()  
complete\_initial\_analysis()  
complete\_follow\_up\_analysis()  
restore\_stable\_status\_after\_failure()  
open\_position()  
mark\_partially\_closed()  
close\_take\_profit()  
close\_stop\_loss()  
close\_manual()  
cancel\_setup()  
archive()  
restore\_from\_archive()  
set\_latest\_canonical\_analysis()  
set\_active\_thesis()  
set\_context\_summary()  
record\_last\_activity()

---

# **6\. MarketIdentity Value Object**

## **6.1 Definition**

`MarketIdentity` identifies the security being analyzed.

---

## **6.2 Properties**

MarketIdentity  
\- ticker  
\- market  
\- company\_name  
\- currency

---

## **6.3 MVP Market Values**

Recommended market enum:

IDX

The enum may later support:

NASDAQ  
NYSE  
AMEX  
OTHER

The primary MVP scope remains Indonesian equities.

---

## **6.4 Invariants**

* ticker must be normalized to uppercase;  
* ticker must not contain unsafe characters;  
* market must use an allowed enum;  
* currency should default according to market;  
* IDX currency defaults to `IDR`.

---

# **7\. Evidence Aggregate**

## **7.1 Definition**

`Evidence` represents one persisted item used to support analysis or record user context.

Evidence may be an uploaded image, structured market snapshot, or text note.

---

## **7.2 Core Properties**

Evidence  
\- id  
\- session\_id  
\- owner\_id  
\- evidence\_type  
\- evidence\_status  
\- update\_classification  
\- original\_filename  
\- storage\_object\_key  
\- mime\_type  
\- file\_size\_bytes  
\- checksum  
\- market\_timestamp  
\- uploaded\_at  
\- caption  
\- source\_note  
\- extraction\_status  
\- extraction\_payload  
\- extraction\_confidence  
\- supersedes\_evidence\_id  
\- exclusion\_reason  
\- excluded\_at  
\- created\_at  
\- updated\_at

Text-only evidence may omit file-related values.

---

## **7.3 Evidence Types**

ORDERBOOK\_SCREENSHOT  
CHART\_THREE\_MONTH  
CHART\_SIX\_MONTH  
CHART\_DAILY  
CHART\_INTRADAY  
BROKER\_SUMMARY  
FOREIGN\_FLOW  
NEWS\_SCREENSHOT  
CUSTOM\_IMAGE  
USER\_NOTE  
MARKET\_DATA\_SNAPSHOT

---

## **7.4 Evidence Statuses**

PENDING  
AVAILABLE  
PROCESSING  
UNREADABLE  
SUPERSEDED  
EXCLUDED  
DUPLICATE  
FAILED  
DELETED

`DELETED` should be reserved for an explicit administrative deletion workflow.

---

## **7.5 Evidence Extraction Status**

NOT\_REQUESTED  
PENDING  
PROCESSING  
COMPLETED  
PARTIAL  
FAILED

---

## **7.6 Evidence Invariants**

### **EV-INV-001**

Evidence must belong to one Trade Session.

### **EV-INV-002**

Evidence cannot be reassigned to another session.

### **EV-INV-003**

Original uploaded files must not be overwritten.

### **EV-INV-004**

Evidence marked `EXCLUDED` must not be included in future AI context.

### **EV-INV-005**

Evidence marked `SUPERSEDED` remains available for audit history.

### **EV-INV-006**

Unreadable evidence cannot contribute exact numerical values unless separately supplied by the user.

### **EV-INV-007**

Market timestamp and upload timestamp are separate concepts.

### **EV-INV-008**

An analysis must reference the exact evidence IDs it used.

---

## **7.7 Evidence Operations**

create\_pending()  
mark\_available()  
mark\_processing()  
mark\_unreadable()  
mark\_failed()  
supersede()  
exclude()  
restore\_from\_exclusion()  
record\_extraction()  
attach\_variant()

---

# **8\. EvidenceVariant Entity**

## **8.1 Definition**

`EvidenceVariant` represents a generated file derived from original evidence.

---

## **8.2 Properties**

EvidenceVariant  
\- id  
\- evidence\_id  
\- variant\_type  
\- storage\_object\_key  
\- mime\_type  
\- file\_size\_bytes  
\- width  
\- height  
\- checksum  
\- created\_at

---

## **8.3 Variant Types**

ORIGINAL  
THUMBNAIL  
PREVIEW  
AI\_INPUT  
NORMALIZED

The original may be represented on the parent Evidence object or as a variant, depending on persistence design.

---

# **9\. SessionUpdate Entity**

## **9.1 Definition**

`SessionUpdate` groups new evidence and user-provided values into one chronological update.

It represents a meaningful observation point such as morning, midday, or closing.

---

## **9.2 Properties**

SessionUpdate  
\- id  
\- session\_id  
\- update\_classification  
\- custom\_label  
\- market\_timestamp  
\- trading\_date  
\- user\_note  
\- provided\_market\_snapshot\_id  
\- created\_by  
\- created\_at  
\- analysis\_requested\_at

---

## **9.3 Update Classifications**

INITIAL  
MORNING  
MIDDAY  
CLOSING  
CUSTOM

---

## **9.4 Invariants**

* `CUSTOM` requires a custom label or explanation;  
* `INITIAL` may occur only once per Trade Session;  
* an update may link to multiple evidence items;  
* an update must not modify previous update contents destructively;  
* a follow-up analysis request should reference one update ID.

---

# **10\. MarketSnapshot Value Object**

## **10.1 Definition**

`MarketSnapshot` contains user-provided or reliably extracted market values for one observation point.

---

## **10.2 Properties**

MarketSnapshot  
\- open\_price  
\- high\_price  
\- low\_price  
\- last\_price  
\- close\_price  
\- previous\_close  
\- average\_price  
\- absolute\_change  
\- percentage\_change  
\- volume  
\- transaction\_value  
\- best\_bid  
\- best\_offer  
\- bid\_quantity  
\- offer\_quantity  
\- observed\_at  
\- data\_source  
\- data\_quality

---

## **10.3 Data Sources**

USER\_PROVIDED  
AI\_EXTRACTED  
SYSTEM\_CALCULATED  
MARKET\_API  
UNKNOWN

---

## **10.4 Data Quality**

VERIFIED  
HIGH\_CONFIDENCE  
MODERATE\_CONFIDENCE  
LOW\_CONFIDENCE  
UNREADABLE  
UNKNOWN

---

## **10.5 Invariants**

* exact values must preserve their source;  
* AI-extracted values must preserve extraction confidence;  
* unknown values remain null;  
* `close_price` and `last_price` must not be treated as interchangeable without context;  
* calculated change values must be reproducible.

---

# **11\. AnalysisRequest Aggregate**

## **11.1 Definition**

`AnalysisRequest` represents one user or system request to generate an AI analysis.

It is distinct from the resulting `AnalysisVersion`.

---

## **11.2 Properties**

AnalysisRequest  
\- id  
\- session\_id  
\- session\_update\_id  
\- requested\_by  
\- analysis\_type  
\- request\_status  
\- idempotency\_key  
\- requested\_provider  
\- requested\_model  
\- fallback\_allowed  
\- prompt\_name  
\- prompt\_version  
\- schema\_version  
\- context\_summary\_version  
\- created\_at  
\- queued\_at  
\- completed\_at  
\- failed\_at

---

## **11.3 Analysis Types**

INITIAL\_ANALYSIS  
WATCHING\_UPDATE  
OPEN\_POSITION\_UPDATE  
PARTIAL\_EXIT\_REVIEW  
CLOSING\_ANALYSIS  
TRADING\_JOURNAL  
CONTEXT\_SUMMARY  
THESIS\_REVIEW

---

## **11.4 Request Statuses**

CREATED  
QUEUED  
PROCESSING  
COMPLETED  
FAILED  
CANCELLED

---

## **11.5 Invariants**

* one idempotency key must represent one logical request scope;  
* an initial analysis requires minimum active evidence;  
* a watching update requires a canonical initial analysis;  
* an open-position update requires an active position;  
* closing analysis requires a fully closed position;  
* journal generation requires a closed session;  
* request completion does not guarantee canonical analysis acceptance.

---

# **12\. AnalysisVersion Aggregate**

## **12.1 Definition**

`AnalysisVersion` represents one immutable AI-generated analysis result.

It contains the normalized structured response and related metadata.

---

## **12.2 Core Properties**

AnalysisVersion  
\- id  
\- session\_id  
\- analysis\_request\_id  
\- analysis\_type  
\- version\_number  
\- canonical\_status  
\- validation\_status  
\- provider  
\- model  
\- provider\_request\_id  
\- prompt\_name  
\- prompt\_version  
\- schema\_version  
\- context\_summary\_version  
\- session\_status\_snapshot  
\- position\_snapshot  
\- structured\_payload  
\- narrative\_language  
\- contradiction\_status  
\- contradiction\_details  
\- generated\_at  
\- validated\_at  
\- canonicalized\_at  
\- created\_at

---

## **12.3 Canonical Status**

PENDING  
CANONICAL  
NON\_CANONICAL  
SUPERSEDED  
REJECTED

Completed historical analyses generally remain immutable. `SUPERSEDED` means a later correction or regeneration replaced the canonical role, not that history was deleted.

---

## **12.4 Validation Status**

PENDING  
VALID  
VALID\_WITH\_WARNINGS  
INVALID\_SCHEMA  
INVALID\_LANGUAGE  
INVALID\_LOGIC  
CONTRADICTORY  
FAILED

---

## **12.5 Contradiction Status**

NOT\_CHECKED  
PASS  
PASS\_WITH\_EXPLANATION  
REVIEW\_REQUIRED  
REJECT

---

## **12.6 AnalysisVersion Invariants**

### **AN-INV-001**

An analysis version is immutable after creation and validation.

### **AN-INV-002**

A correction creates a new version.

### **AN-INV-003**

Only a valid analysis may become canonical.

### **AN-INV-004**

A rejected analysis must not update Trade Session canonical state.

### **AN-INV-005**

Each analysis must record exact evidence references.

### **AN-INV-006**

Each analysis must record the position snapshot used.

### **AN-INV-007**

Each analysis must record provider, model, prompt, and schema versions.

### **AN-INV-008**

Narrative fields intended for user display must be in Bahasa Indonesia.

### **AN-INV-009**

Structured keys and enum values must remain English.

---

# **13\. AnalysisEvidenceLink Entity**

## **13.1 Definition**

Links an analysis version to the exact evidence used.

---

## **13.2 Properties**

AnalysisEvidenceLink  
\- analysis\_version\_id  
\- evidence\_id  
\- evidence\_role  
\- context\_priority  
\- included\_as\_image  
\- included\_as\_extracted\_text  
\- created\_at

---

## **13.3 Evidence Roles**

PRIMARY\_CURRENT  
PRIMARY\_PREVIOUS  
INITIAL\_REFERENCE  
HISTORICAL\_REFERENCE  
SUPPORTING  
CONTRADICTORY  
USER\_NOTE\_REFERENCE

---

# **14\. Analysis Structured Components**

The structured analysis payload should conceptually include the following domain components.

These may be represented as embedded structured objects rather than separate persisted entities where appropriate.

---

## **14.1 ExecutiveSummary**

ExecutiveSummary  
\- condition\_summary  
\- directional\_bias  
\- setup\_quality  
\- primary\_opportunity  
\- primary\_risk  
\- recommended\_next\_action

---

## **14.2 OrderbookAssessment**

OrderbookAssessment  
\- visible\_facts  
\- interpretation  
\- best\_bid  
\- best\_offer  
\- bid\_strength  
\- offer\_pressure  
\- bid\_concentration  
\- offer\_concentration  
\- buyer\_persistence  
\- seller\_aggression  
\- absorption\_assessment  
\- distribution\_assessment  
\- nearest\_support  
\- nearest\_resistance  
\- liquidity\_quality  
\- spoofing\_risk  
\- limitations

---

## **14.3 ChartAssessment**

ChartAssessment  
\- timeframe  
\- trend  
\- swing\_structure  
\- momentum  
\- volume\_behavior  
\- patterns  
\- support\_levels  
\- resistance\_levels  
\- breakout\_assessment  
\- breakdown\_assessment  
\- risk\_notes

---

## **14.4 PositionAssessment**

PositionAssessment  
\- position\_health  
\- thesis\_validity  
\- target\_realism  
\- stop\_appropriateness  
\- averaging\_down\_assessment  
\- partial\_profit\_assessment  
\- exit\_assessment  
\- rationale

---

## **14.5 ChangeSummary**

ChangeSummary  
\- price\_change  
\- average\_price\_change  
\- best\_bid\_change  
\- best\_offer\_change  
\- bid\_strength\_change  
\- offer\_pressure\_change  
\- support\_change  
\- resistance\_change  
\- momentum\_change  
\- thesis\_change  
\- confidence\_change  
\- probability\_changes  
\- risk\_change  
\- recommendation\_change  
\- material\_change\_exists

---

## **14.6 TradingPlan**

TradingPlan  
\- plan\_horizon  
\- bullish\_scenario  
\- neutral\_scenario  
\- bearish\_scenario  
\- prohibited\_actions  
\- next\_checkpoint  
\- recommended\_action

---

# **15\. TradingThesis Aggregate**

## **15.1 Definition**

`TradingThesis` is the canonical technical hypothesis that explains why the setup or position remains valid.

The thesis is versioned over time.

---

## **15.2 Core Properties**

TradingThesis  
\- id  
\- session\_id  
\- version\_number  
\- thesis\_status  
\- directional\_bias  
\- thesis\_statement  
\- technical\_rationale  
\- supporting\_evidence\_summary  
\- conflicting\_evidence\_summary  
\- key\_support  
\- key\_resistance  
\- invalidation\_level  
\- invalidation\_condition  
\- expected\_scenario  
\- confidence\_score  
\- source\_analysis\_version\_id  
\- previous\_thesis\_id  
\- change\_type  
\- change\_reason  
\- effective\_at  
\- created\_at

---

## **15.3 Thesis Statuses**

STRENGTHENING  
INTACT  
INTACT\_BUT\_WEAKENING  
UNDER\_REVIEW  
INVALIDATED

---

## **15.4 Thesis Change Types**

CREATED  
STRENGTHENED  
UNCHANGED  
WEAKENED  
PLACED\_UNDER\_REVIEW  
INVALIDATED  
CORRECTED

---

## **15.5 Directional Bias**

BULLISH  
NEUTRAL  
BEARISH  
MIXED

Directional bias is not equivalent to an action recommendation.

---

## **15.6 Thesis Invariants**

### **TH-INV-001**

A session with a canonical analysis must have one active thesis.

### **TH-INV-002**

Only one thesis version may be canonical at a time.

### **TH-INV-003**

A thesis change requires a source analysis or explicit correction record.

### **TH-INV-004**

A material status change requires a reason.

### **TH-INV-005**

An invalidated thesis cannot return to `INTACT` in the same trade lifecycle without an explicit correction of invalid input.

A genuinely new setup requires a new Trade Session.

### **TH-INV-006**

Thesis history is immutable.

### **TH-INV-007**

The invalidation condition must remain explicit.

### **TH-INV-008**

A minor market fluctuation alone is insufficient for invalidation.

---

# **16\. PriceLevel Value Object**

## **16.1 Definition**

`PriceLevel` represents a technically meaningful price or price zone.

---

## **16.2 Properties**

PriceLevel  
\- exact\_price  
\- lower\_bound  
\- upper\_bound  
\- level\_type  
\- basis  
\- source\_type  
\- status  
\- confidence  
\- observed\_at

A level may be an exact value or a zone.

---

## **16.3 Level Types**

IMMEDIATE\_SUPPORT  
MAJOR\_SUPPORT  
THESIS\_INVALIDATION  
IMMEDIATE\_RESISTANCE  
MAJOR\_RESISTANCE  
BREAKOUT\_CONFIRMATION  
ENTRY\_ZONE  
CHASE\_LIMIT  
STOP\_LOSS  
TARGET

---

## **16.4 Level Sources**

ORDERBOOK  
CHART\_STRUCTURE  
SWING\_HIGH  
SWING\_LOW  
HISTORICAL\_RANGE  
AVERAGE\_PRICE  
VOLUME\_ZONE  
PSYCHOLOGICAL\_LEVEL  
USER\_DEFINED  
AI\_INFERRED

---

## **16.5 Level Statuses**

ACTIVE  
BEING\_TESTED  
BROKEN  
CONFIRMED  
NO\_LONGER\_RELEVANT  
UNCONFIRMED

---

## **16.6 Invariants**

* a level must contain a basis;  
* a changed canonical level requires explanation;  
* orderbook levels are temporary observations;  
* exact precision must not exceed evidence quality;  
* a zone should be used when the evidence does not support one exact number.

---

# **17\. Position Aggregate**

## **17.1 Definition**

`Position` represents the user’s actual trading position inside one Trade Session.

It is separate from the AI’s proposed trade plan.

---

## **17.2 Core Properties**

Position  
\- id  
\- session\_id  
\- position\_status  
\- currency  
\- total\_entry\_quantity  
\- remaining\_quantity  
\- weighted\_average\_entry  
\- total\_entry\_cost  
\- realized\_proceeds  
\- realized\_profit\_loss  
\- unrealized\_profit\_loss  
\- total\_profit\_loss  
\- return\_percentage  
\- active\_stop\_loss\_id  
\- opened\_at  
\- partially\_closed\_at  
\- closed\_at  
\- created\_at  
\- updated\_at

Some calculated values remain null when quantity is not provided.

---

## **17.3 Position Statuses**

OPEN  
PARTIALLY\_CLOSED  
CLOSED

Trade Session closure reason remains represented by session lifecycle status and final exit reason.

---

## **17.4 Position Invariants**

### **POS-INV-001**

A Trade Session may have no more than one Position.

### **POS-INV-002**

A Position requires at least one entry.

### **POS-INV-003**

An open Position requires an active stop loss.

### **POS-INV-004**

An open Position requires at least one active target.

### **POS-INV-005**

Remaining quantity cannot be negative.

### **POS-INV-006**

Exit quantity cannot exceed remaining quantity.

### **POS-INV-007**

A closed Position cannot receive new entries.

### **POS-INV-008**

A position cannot be opened when the canonical thesis is `INVALIDATED`.

### **POS-INV-009**

Additional entries are blocked when the canonical thesis is `INVALIDATED`.

### **POS-INV-010**

All calculated financial values must be reproducible from transactions.

---

## **17.5 Position Operations**

open()  
add\_entry()  
change\_stop\_loss()  
add\_target()  
change\_target()  
deactivate\_target()  
record\_partial\_exit()  
record\_final\_exit()  
recalculate()  
apply\_correction()

---

# **18\. PositionEntry Entity**

## **18.1 Definition**

`PositionEntry` records one actual user-executed purchase within the position.

---

## **18.2 Properties**

PositionEntry  
\- id  
\- position\_id  
\- entry\_sequence  
\- entry\_type  
\- price  
\- quantity  
\- gross\_value  
\- broker\_fee  
\- net\_cost  
\- executed\_at  
\- user\_reason  
\- related\_analysis\_version\_id  
\- planned\_entry\_reference  
\- created\_at  
\- corrected\_by\_entry\_id

---

## **18.3 Entry Types**

INITIAL  
ADDITIONAL  
CORRECTION

---

## **18.4 Entry Classification**

An additional entry may be calculated as:

AVERAGING\_UP  
AVERAGING\_DOWN  
NEUTRAL\_ADDITION  
UNKNOWN

---

## **18.5 Invariants**

* initial entry occurs only once;  
* actual entry is distinct from proposed entry;  
* quantity may be optional for simplified tracking;  
* financial calculations requiring quantity remain unavailable when quantity is absent;  
* historical entries are not silently overwritten;  
* correction creates a linked correction record or audit-safe replacement.

---

# **19\. PositionExit Entity**

## **19.1 Definition**

`PositionExit` records one actual user-executed sale.

---

## **19.2 Properties**

PositionExit  
\- id  
\- position\_id  
\- exit\_sequence  
\- exit\_type  
\- exit\_reason  
\- price  
\- quantity  
\- gross\_value  
\- broker\_fee  
\- net\_proceeds  
\- realized\_profit\_loss  
\- executed\_at  
\- user\_note  
\- related\_analysis\_version\_id  
\- active\_stop\_at\_exit  
\- active\_target\_at\_exit  
\- created\_at  
\- corrected\_by\_exit\_id

---

## **19.3 Exit Types**

PARTIAL  
FINAL  
CORRECTION

---

## **19.4 Exit Reasons**

TAKE\_PROFIT  
STOP\_LOSS  
THESIS\_INVALIDATED  
RISK\_REDUCTION  
TIME\_BASED\_EXIT  
TRAILING\_STOP  
MANUAL\_DISCRETION  
OTHER

---

## **19.5 Invariants**

* exit quantity cannot exceed remaining quantity;  
* a final exit must close the remaining position;  
* actual exit price may differ from stop or target;  
* exit reason is user-confirmed;  
* stop and target snapshots must be preserved at exit;  
* historical exits are not silently overwritten.

---

# **20\. StopLossVersion Entity**

## **20.1 Definition**

`StopLossVersion` represents one active or historical stop-loss level confirmed by the user.

---

## **20.2 Properties**

StopLossVersion  
\- id  
\- position\_id  
\- version\_number  
\- price  
\- technical\_basis  
\- change\_reason  
\- risk\_amount  
\- risk\_percentage  
\- is\_wider\_than\_previous  
\- recommended\_by\_analysis\_id  
\- confirmed\_by\_user\_id  
\- effective\_from  
\- effective\_to  
\- is\_active  
\- created\_at

---

## **20.3 Stop-Loss Invariants**

### **SL-INV-001**

An open position must have exactly one active stop loss.

### **SL-INV-002**

Changing a stop creates a new version.

### **SL-INV-003**

A previous active stop receives an end timestamp.

### **SL-INV-004**

Widening the stop requires an explicit reason.

### **SL-INV-005**

An AI recommendation cannot activate a stop automatically.

### **SL-INV-006**

A thesis invalidation must not be managed only by arbitrarily widening the stop.

---

# **21\. PositionTarget Entity**

## **21.1 Definition**

`PositionTarget` represents one user-confirmed target for an active position.

Multiple targets may exist.

---

## **21.2 Properties**

PositionTarget  
\- id  
\- position\_id  
\- target\_group\_id  
\- version\_number  
\- priority  
\- price  
\- target\_type  
\- technical\_basis  
\- planned\_quantity  
\- planned\_percentage  
\- status  
\- change\_reason  
\- recommended\_by\_analysis\_id  
\- confirmed\_by\_user\_id  
\- effective\_from  
\- effective\_to  
\- reached\_at  
\- is\_active  
\- created\_at

---

## **21.3 Target Types**

TP1  
TP2  
TP3  
CUSTOM

---

## **21.4 Target Statuses**

ACTIVE  
PARTIALLY\_ACHIEVED  
ACHIEVED  
DEACTIVATED  
SUPERSEDED  
MISSED

---

## **21.5 Target Invariants**

* an open position requires at least one active target;  
* changing a target creates a new version;  
* target basis must be recorded;  
* AI cannot activate a new target automatically;  
* raising or lowering a target requires a reason;  
* lowering a target cannot be used to conceal invalidated thesis risk;  
* target achievement does not automatically create an exit record.

The user records actual execution.

---

# **22\. ProposedTradePlan Value Object**

## **22.1 Definition**

`ProposedTradePlan` represents AI-recommended trade parameters before or during a position.

It is advisory and distinct from user-confirmed position state.

---

## **22.2 Properties**

ProposedTradePlan  
\- ideal\_entry\_zone  
\- aggressive\_entry  
\- conservative\_entry  
\- breakout\_entry  
\- pullback\_entry  
\- chase\_limit  
\- recommended\_stop  
\- recommended\_targets  
\- bullish\_scenario  
\- neutral\_scenario  
\- bearish\_scenario  
\- prohibited\_actions  
\- plan\_horizon  
\- next\_checkpoint

---

## **22.3 Invariant**

No value inside `ProposedTradePlan` becomes an actual position mutation until user confirmation.

---

# **23\. PositionSnapshot Value Object**

## **23.1 Definition**

`PositionSnapshot` captures the authoritative position state used during an analysis.

---

## **23.2 Properties**

PositionSnapshot  
\- position\_id  
\- position\_status  
\- weighted\_average\_entry  
\- total\_quantity  
\- remaining\_quantity  
\- realized\_profit\_loss  
\- unrealized\_profit\_loss  
\- active\_stop  
\- active\_targets  
\- opened\_at  
\- snapshot\_at

---

## **23.3 Purpose**

The snapshot ensures each analysis remains reproducible even if the position changes later.

---

# **24\. ConfidenceAssessment Value Object**

## **24.1 Definition**

`ConfidenceAssessment` describes the reliability of an AI analysis given the available evidence.

It does not represent probability of profit.

---

## **24.2 Properties**

ConfidenceAssessment  
\- score  
\- classification  
\- previous\_score  
\- score\_change  
\- drivers  
\- reducers  
\- evidence\_quality  
\- missing\_data  
\- explanation

---

## **24.3 Classifications**

LOW  
MODERATE  
HIGH

---

## **24.4 Invariants**

* score must be between 0 and 100;  
* classification must match score range;  
* a material score change requires explanation;  
* insufficient evidence should reduce confidence;  
* confidence is separate from directional probability.

---

# **25\. ProbabilityAssessment Entity or Value Object**

## **25.1 Definition**

A `ProbabilityAssessment` represents one estimated event probability produced by AI analysis.

Depending on query requirements, assessments may be stored as separate rows or as structured analysis payload components.

---

## **25.2 Properties**

ProbabilityAssessment  
\- probability\_type  
\- percentage  
\- previous\_percentage  
\- change  
\- direction  
\- reasoning  
\- supporting\_evidence  
\- uncertainty\_level

---

## **25.3 Probability Types**

BULLISH\_CONTINUATION  
TARGET\_ACHIEVEMENT  
PULLBACK  
STOP\_LOSS\_TOUCH  
THESIS\_REMAINS\_VALID  
THESIS\_INVALIDATION  
MAJOR\_SUPPORT\_BREAK

---

## **25.4 Change Direction**

INCREASED  
DECREASED  
UNCHANGED  
NOT\_COMPARABLE

---

## **25.5 Uncertainty Level**

LOW  
MODERATE  
HIGH

---

## **25.6 Invariants**

* percentage must be between 0 and 100;  
* probabilities are analytical estimates;  
* material changes require reasoning;  
* obvious logical contradictions must be flagged;  
* overlapping event probabilities are allowed when explained;  
* false precision should be avoided.

---

# **26\. RecommendedAction Value Object**

## **26.1 Definition**

`RecommendedAction` represents the AI’s current advisory action.

It is not an executed trade instruction.

---

## **26.2 Action Values**

WAIT\_FOR\_CONFIRMATION  
HOLD\_POSITION  
HOLD\_WITH\_CAUTION  
CONSIDER\_PARTIAL\_PROFIT  
REDUCE\_RISK  
REVIEW\_EXIT  
DO\_NOT\_ADD  
CANCEL\_SETUP  
NO\_MATERIAL\_CHANGE

Future expansion requires schema changes.

---

## **26.3 Properties**

RecommendedAction  
\- action  
\- rationale  
\- conditions  
\- invalidation  
\- time\_horizon  
\- risk\_level

---

## **26.4 Invariants**

* action must include rationale;  
* action must include relevant conditions;  
* action must not execute a mutation;  
* standalone BUY, HOLD, or SELL is prohibited.

---

# **27\. RiskAssessment Value Object**

## **27.1 Definition**

`RiskAssessment` describes current trade or setup risk.

---

## **27.2 Risk Levels**

LOW  
MODERATE  
ELEVATED  
HIGH  
CRITICAL

---

## **27.3 Properties**

RiskAssessment  
\- level  
\- primary\_risks  
\- stop\_proximity  
\- thesis\_risk  
\- evidence\_risk  
\- execution\_risk  
\- mitigation

---

# **28\. PositionHealth Value Object**

## **28.1 Allowed Values**

HEALTHY  
HEALTHY\_BUT\_VOLATILE  
WEAKENING  
HIGH\_RISK  
EXIT\_CONDITION\_TRIGGERED  
NOT\_APPLICABLE

---

## **28.2 Properties**

PositionHealthAssessment  
\- status  
\- rationale  
\- supporting\_factors  
\- warning\_factors  
\- required\_action

---

# **29\. ContextSummary Aggregate**

## **29.1 Definition**

`ContextSummary` is a structured, versioned summary used to keep long Trade Sessions within model context limits.

It is derived from source history and is not the source of truth itself.

---

## **29.2 Properties**

ContextSummary  
\- id  
\- session\_id  
\- version\_number  
\- active\_thesis\_summary  
\- position\_summary  
\- key\_level\_summary  
\- update\_history\_summary  
\- thesis\_change\_summary  
\- current\_risks  
\- unresolved\_questions  
\- latest\_plan\_summary  
\- source\_analysis\_version\_ids  
\- source\_timeline\_cutoff  
\- generated\_by  
\- generated\_at  
\- superseded\_at

---

## **29.3 Invariants**

* source references must be preserved;  
* critical trade values must not be omitted;  
* a context summary cannot replace immutable records;  
* summaries must be versioned;  
* a newer summary supersedes but does not delete previous versions.

---

# **30\. TradingJournal Aggregate**

## **30.1 Definition**

`TradingJournal` represents the final AI-generated review of a completed Trade Session.

---

## **30.2 Properties**

TradingJournal  
\- id  
\- session\_id  
\- version\_number  
\- journal\_status  
\- canonical\_status  
\- source\_position\_version  
\- source\_analysis\_cutoff  
\- trade\_summary  
\- initial\_thesis\_review  
\- thesis\_journey\_review  
\- entry\_review  
\- position\_management\_review  
\- exit\_review  
\- plan\_compliance\_review  
\- ai\_performance\_review  
\- what\_worked  
\- what\_did\_not\_work  
\- key\_lessons  
\- next\_trade\_checklist  
\- narrative\_language  
\- generated\_by\_analysis\_request\_id  
\- generated\_at  
\- outdated\_at  
\- outdated\_reason  
\- created\_at

---

## **30.3 Journal Statuses**

PENDING  
GENERATING  
COMPLETED  
FAILED  
OUTDATED

---

## **30.4 Canonical Status**

CANONICAL  
SUPERSEDED  
REJECTED

---

## **30.5 Journal Invariants**

### **JR-INV-001**

A journal may be generated only for a fully closed position.

### **JR-INV-002**

Journal generation must use the full relevant session history.

### **JR-INV-003**

AI performance and user execution must be evaluated separately.

### **JR-INV-004**

The journal must distinguish contemporaneous information from hindsight.

### **JR-INV-005**

User-facing journal narrative must use Bahasa Indonesia.

### **JR-INV-006**

Regeneration creates a new journal version.

### **JR-INV-007**

Historical corrections may mark the current journal `OUTDATED`.

---

# **31\. UserReflection Entity**

## **31.1 Definition**

`UserReflection` contains the user’s own post-trade observations.

It remains distinct from the AI-generated journal.

---

## **31.2 Properties**

UserReflection  
\- id  
\- session\_id  
\- journal\_id  
\- emotional\_state  
\- personal\_entry\_reason  
\- personal\_exit\_reason  
\- mistakes  
\- lessons  
\- trade\_rating  
\- final\_note  
\- created\_at  
\- updated\_at

---

## **31.3 Invariants**

* user reflection must not overwrite AI journal content;  
* trade rating must use a controlled range;  
* edits should retain audit history when required.

---

# **32\. TimelineEvent Entity**

## **32.1 Definition**

`TimelineEvent` is a user-visible chronological record of a meaningful Trade Session event.

---

## **32.2 Properties**

TimelineEvent  
\- id  
\- session\_id  
\- event\_type  
\- event\_category  
\- actor\_type  
\- actor\_id  
\- title  
\- description  
\- related\_entity\_type  
\- related\_entity\_id  
\- change\_summary  
\- occurred\_at  
\- created\_at

---

## **32.3 Event Categories**

SESSION  
EVIDENCE  
ANALYSIS  
THESIS  
POSITION  
STOP\_LOSS  
TARGET  
EXIT  
JOURNAL  
SYSTEM

---

## **32.4 Actor Types**

USER  
SYSTEM  
AI  
WORKER  
ADMIN

The AI may be identified as the source of a recommendation, but the system remains the actor that commits canonical state after validation.

---

# **33\. Domain Event Catalog**

Recommended domain events include:

## **33.1 Session Events**

SESSION\_CREATED  
SESSION\_READY\_FOR\_ANALYSIS  
SESSION\_ANALYSIS\_STARTED  
SESSION\_ANALYSIS\_COMPLETED  
SESSION\_ANALYSIS\_FAILED  
SETUP\_CANCELLED  
SESSION\_ARCHIVED  
SESSION\_RESTORED

## **33.2 Evidence Events**

EVIDENCE\_UPLOADED  
EVIDENCE\_PROCESSED  
EVIDENCE\_UNREADABLE  
EVIDENCE\_SUPERSEDED  
EVIDENCE\_EXCLUDED  
EVIDENCE\_RESTORED

## **33.3 Analysis Events**

ANALYSIS\_REQUESTED  
ANALYSIS\_QUEUED  
ANALYSIS\_PROCESSING  
INITIAL\_ANALYSIS\_GENERATED  
UPDATE\_ANALYSIS\_GENERATED  
ANALYSIS\_REJECTED  
ANALYSIS\_RETRIED  
ANALYSIS\_CANONICALIZED

## **33.4 Thesis Events**

THESIS\_CREATED  
THESIS\_STRENGTHENED  
THESIS\_UNCHANGED  
THESIS\_WEAKENED  
THESIS\_UNDER\_REVIEW  
THESIS\_INVALIDATED  
THESIS\_CORRECTED

## **33.5 Position Events**

POSITION\_OPENED  
ADDITIONAL\_ENTRY\_RECORDED  
POSITION\_RECALCULATED  
PARTIAL\_EXIT\_RECORDED  
POSITION\_CLOSED\_TAKE\_PROFIT  
POSITION\_CLOSED\_STOP\_LOSS  
POSITION\_CLOSED\_MANUAL  
POSITION\_DATA\_CORRECTED

## **33.6 Stop and Target Events**

STOP\_LOSS\_CREATED  
STOP\_LOSS\_CHANGED  
STOP\_LOSS\_WIDENED  
TARGET\_CREATED  
TARGET\_CHANGED  
TARGET\_DEACTIVATED  
TARGET\_ACHIEVED

## **33.7 Journal Events**

CLOSING\_ANALYSIS\_GENERATED  
JOURNAL\_GENERATION\_REQUESTED  
JOURNAL\_GENERATED  
JOURNAL\_FAILED  
JOURNAL\_MARKED\_OUTDATED  
JOURNAL\_REGENERATED  
USER\_REFLECTION\_ADDED

---

# **34\. AuditRecord Entity**

## **34.1 Definition**

`AuditRecord` provides technical traceability beyond the user-facing timeline.

---

## **34.2 Properties**

AuditRecord  
\- id  
\- owner\_id  
\- session\_id  
\- actor\_type  
\- actor\_id  
\- action  
\- entity\_type  
\- entity\_id  
\- previous\_values  
\- new\_values  
\- reason  
\- request\_id  
\- correlation\_id  
\- job\_id  
\- source\_ip  
\- user\_agent  
\- created\_at

Sensitive data should be minimized.

---

## **34.3 Difference from TimelineEvent**

`TimelineEvent` is optimized for user comprehension.

`AuditRecord` is optimized for technical accountability and debugging.

Not every audit record must be visible on the user timeline.

---

# **35\. BackgroundJob Aggregate**

## **35.1 Definition**

`BackgroundJob` represents one asynchronously executed operation.

---

## **35.2 Properties**

BackgroundJob  
\- id  
\- owner\_id  
\- session\_id  
\- job\_type  
\- job\_status  
\- progress\_stage  
\- idempotency\_key  
\- priority  
\- attempt\_count  
\- max\_attempts  
\- requested\_by  
\- payload\_reference  
\- result\_reference  
\- error\_code  
\- error\_message  
\- retryable  
\- queued\_at  
\- started\_at  
\- heartbeat\_at  
\- completed\_at  
\- failed\_at  
\- cancelled\_at  
\- created\_at

---

## **35.3 Job Types**

INITIAL\_ANALYSIS  
WATCHING\_UPDATE\_ANALYSIS  
OPEN\_POSITION\_UPDATE\_ANALYSIS  
PARTIAL\_EXIT\_REVIEW  
CLOSING\_ANALYSIS  
TRADING\_JOURNAL\_GENERATION  
CONTEXT\_SUMMARY\_REFRESH  
EVIDENCE\_VARIANT\_GENERATION  
EVIDENCE\_EXTRACTION  
CLEANUP  
BACKUP  
NOTIFICATION\_DELIVERY

---

## **35.4 Job Statuses**

CREATED  
QUEUED  
PROCESSING  
RETRYING  
COMPLETED  
FAILED  
CANCELLED

---

## **35.5 Progress Stages**

PREPARING\_EVIDENCE  
BUILDING\_CONTEXT  
CALLING\_PROVIDER  
VALIDATING\_OUTPUT  
CHECKING\_CONTRADICTIONS  
SAVING\_RESULT  
COMPLETED

---

## **35.6 Invariants**

* idempotency keys must prevent duplicate logical work;  
* failed jobs must not alter canonical state partially;  
* one job may have multiple attempts;  
* only validated results may be referenced as successful output;  
* PostgreSQL stores authoritative job status.

---

# **36\. JobAttempt Entity**

## **36.1 Definition**

`JobAttempt` records one execution attempt, including fallback-provider attempts.

---

## **36.2 Properties**

JobAttempt  
\- id  
\- job\_id  
\- attempt\_number  
\- provider  
\- model  
\- started\_at  
\- completed\_at  
\- status  
\- error\_code  
\- provider\_request\_id  
\- latency\_ms  
\- input\_token\_estimate  
\- output\_token\_estimate  
\- image\_count  
\- estimated\_cost  
\- created\_at

---

# **37\. AIProviderConfiguration Aggregate**

## **37.1 Definition**

Represents server-side AI provider configuration.

---

## **37.2 Properties**

AIProviderConfiguration  
\- id  
\- owner\_id  
\- provider  
\- model  
\- is\_primary  
\- is\_fallback  
\- enabled  
\- supports\_vision  
\- supports\_structured\_output  
\- supports\_long\_context  
\- encrypted\_secret\_reference  
\- timeout\_seconds  
\- max\_attempts  
\- temperature  
\- max\_output\_tokens  
\- last\_validation\_status  
\- last\_validated\_at  
\- created\_at  
\- updated\_at

---

## **37.3 Provider Values**

GEMINI  
DEEPSEEK  
MOCK

`MOCK` is intended for development and testing.

---

## **37.4 Invariants**

* secrets must remain server-side;  
* a provider assigned a vision analysis must support image input;  
* at most one primary provider is active per configuration scope;  
* fallback must not be identical to the primary provider and model unless explicitly supported;  
* disabled providers cannot receive new jobs.

---

# **38\. AIUsageRecord Entity**

## **38.1 Definition**

Records AI usage and cost information for one provider request.

---

## **38.2 Properties**

AIUsageRecord  
\- id  
\- owner\_id  
\- session\_id  
\- job\_id  
\- job\_attempt\_id  
\- analysis\_version\_id  
\- provider  
\- model  
\- request\_type  
\- input\_tokens  
\- output\_tokens  
\- image\_count  
\- latency\_ms  
\- estimated\_cost  
\- currency  
\- request\_status  
\- recorded\_at

---

## **38.3 Invariants**

* usage records are append-only;  
* estimated cost must preserve pricing assumption version where possible;  
* failed requests may still have usage;  
* provider credentials must never be included.

---

# **39\. Notification Entity**

## **39.1 Definition**

Represents one user-facing system notification.

---

## **39.2 Properties**

Notification  
\- id  
\- owner\_id  
\- session\_id  
\- notification\_type  
\- priority  
\- title  
\- message  
\- related\_entity\_type  
\- related\_entity\_id  
\- read\_at  
\- dismissed\_at  
\- created\_at

---

## **39.3 Notification Types**

ANALYSIS\_COMPLETED  
ANALYSIS\_FAILED  
THESIS\_WEAKENED  
THESIS\_INVALIDATED  
SESSION\_REQUIRES\_UPDATE  
JOURNAL\_GENERATED  
PROVIDER\_CONFIGURATION\_ERROR

---

## **39.4 Notification Priorities**

INFORMATIONAL  
SUCCESS  
WARNING  
CRITICAL

---

# **40\. UserAccount Aggregate**

## **40.1 Definition**

Represents an authenticated TradePilot AI user.

The MVP has one primary user but still requires proper ownership modeling.

---

## **40.2 Properties**

UserAccount  
\- id  
\- email  
\- username  
\- password\_hash  
\- account\_status  
\- preferred\_ui\_language  
\- timezone  
\- last\_login\_at  
\- created\_at  
\- updated\_at

---

## **40.3 Account Statuses**

ACTIVE  
LOCKED  
DISABLED

---

## **40.4 MVP Defaults**

preferred\_ui\_language \= id-ID  
timezone \= Asia/Jakarta

---

# **41\. Domain Services**

Domain services are used when logic does not naturally belong to one entity.

---

## **41.1 SessionLifecycleService**

Responsibilities:

* validate lifecycle transitions;  
* calculate stable status;  
* block reopening closed sessions;  
* determine terminal state;  
* handle archive restoration.

---

## **41.2 PositionCalculationService**

Responsibilities:

* weighted average entry;  
* remaining quantity;  
* realized profit and loss;  
* unrealized profit and loss;  
* return percentage;  
* broker fee effects;  
* stop distance;  
* target distance.

---

## **41.3 AnalysisCanonicalizationService**

Responsibilities:

* validate whether an analysis may become canonical;  
* verify validation status;  
* verify contradiction result;  
* apply proposed canonical values;  
* preserve previous canonical state on failure.

---

## **41.4 ThesisTransitionService**

Responsibilities:

* validate thesis status changes;  
* require change reasons;  
* compare previous and proposed thesis;  
* block unsupported reversal;  
* create thesis versions;  
* classify thesis events.

---

## **41.5 ContradictionDetectionService**

Responsibilities:

* compare analysis versions;  
* detect unexplained level changes;  
* detect unsupported thesis changes;  
* detect action conflicts;  
* detect probability conflicts;  
* return canonicalization recommendation.

---

## **41.6 ContextSelectionService**

Responsibilities:

* select relevant analysis history;  
* select comparable evidence;  
* prioritize current state;  
* preserve critical thesis events;  
* avoid context-window overflow.

---

## **41.7 JournalEligibilityService**

Responsibilities:

* verify session closure;  
* verify final position state;  
* identify stale or corrected source data;  
* determine journal-generation eligibility.

---

## **41.8 EvidenceReadinessService**

Responsibilities:

* identify required evidence;  
* select active non-superseded evidence;  
* determine initial-analysis readiness;  
* block unreadable or unavailable required evidence.

---

# **42\. Canonical State Model**

The Trade Session should expose a denormalized canonical state for fast access.

Recommended canonical state:

CanonicalTradeState  
\- session\_id  
\- lifecycle\_status  
\- ticker  
\- active\_thesis\_id  
\- active\_thesis\_status  
\- active\_thesis\_statement  
\- position\_id  
\- position\_status  
\- weighted\_average\_entry  
\- remaining\_quantity  
\- active\_stop  
\- nearest\_active\_target  
\- latest\_price  
\- latest\_unrealized\_profit\_loss  
\- latest\_confidence  
\- latest\_target\_probability  
\- latest\_risk\_level  
\- latest\_recommended\_action  
\- latest\_analysis\_id  
\- latest\_update\_id  
\- last\_updated\_at

This representation must be derived from authoritative records.

It must not become an independent source of unreconciled truth.

---

# **43\. Aggregate Relationship Map**

UserAccount  
    │  
    └── owns many TradeSessions  
                │  
                ├── has many Evidence  
                │       └── has many EvidenceVariants  
                │  
                ├── has many SessionUpdates  
                │       └── groups many Evidence  
                │  
                ├── has many AnalysisRequests  
                │       └── may produce AnalysisVersion  
                │  
                ├── has many AnalysisVersions  
                │       └── references many Evidence  
                │  
                ├── has many TradingThesis versions  
                │  
                ├── has zero or one Position  
                │       ├── has many PositionEntries  
                │       ├── has many PositionExits  
                │       ├── has many StopLossVersions  
                │       └── has many PositionTargets  
                │  
                ├── has many ContextSummaries  
                │  
                ├── has many TimelineEvents  
                │  
                ├── has many AuditRecords  
                │  
                ├── has many BackgroundJobs  
                │  
                └── has many TradingJournal versions  
                        └── may have UserReflection

---

# **44\. Domain Transition Examples**

## **44.1 Initial Analysis Completion**

TradeSession: READY\_FOR\_ANALYSIS  
AnalysisRequest: PROCESSING  
Evidence: AVAILABLE

Validated AI output  
    ↓

AnalysisVersion: CANONICAL  
TradingThesis: version 1, INTACT  
TradeSession:  
\- lifecycle\_status \= WATCHING  
\- latest\_canonical\_analysis\_id \= analysis\_v1  
\- active\_thesis\_id \= thesis\_v1

---

## **44.2 Open Position**

TradeSession: WATCHING  
TradingThesis: not INVALIDATED

User confirms entry, stop, and target  
    ↓

Position: OPEN  
PositionEntry: INITIAL  
StopLossVersion: active  
PositionTarget: active  
TradeSession:  
\- lifecycle\_status \= OPEN\_POSITION  
\- active\_position\_id \= position

---

## **44.3 Thesis Weakening**

Previous thesis: INTACT  
New validated analysis: INTACT\_BUT\_WEAKENING  
Contradiction status: PASS\_WITH\_EXPLANATION  
    ↓

New TradingThesis version created  
Old thesis remains historical  
TradeSession.active\_thesis\_id updated  
TimelineEvent: THESIS\_WEAKENED

---

## **44.4 Partial Exit**

Position: OPEN  
Remaining quantity: 100

User records exit quantity: 40  
    ↓

PositionExit: PARTIAL  
Remaining quantity: 60  
Position status: PARTIALLY\_CLOSED  
TradeSession lifecycle: PARTIALLY\_CLOSED

---

## **44.5 Final Closure**

Position remaining quantity: 60

User records final exit: 60  
Exit reason: STOP\_LOSS  
    ↓

Position: CLOSED  
TradeSession: CLOSED\_STOP\_LOSS  
Closing analysis eligible  
Trading journal eligible

---

# **45\. Invalid Domain Operations**

The model must reject:

1. initial analysis without minimum evidence;  
2. opening a position in a `DRAFT` session;  
3. opening a position when thesis is `INVALIDATED`;  
4. creating a second Position in the same Trade Session;  
5. adding an entry after full closure;  
6. adding an entry during invalidated thesis;  
7. exiting more than the remaining quantity;  
8. cancelling a session after an entry exists;  
9. reopening a closed session;  
10. changing a stop without creating a new version;  
11. removing the only active target from an open position;  
12. canonicalizing an invalid analysis;  
13. replacing a thesis without a new version;  
14. deleting evidence references from a historical analysis;  
15. generating a journal for an open position;  
16. treating AI-recommended parameters as actual execution;  
17. setting unavailable numeric values to zero;  
18. mutating history without audit records;  
19. using excluded evidence in a new analysis;  
20. overwriting a completed journal.

---

# **46\. Nullability and Unknown Values**

The domain must distinguish:

* zero;  
* not applicable;  
* not provided;  
* unreadable;  
* not yet calculated;  
* unknown.

Examples:

* missing quantity is null, not zero;  
* unavailable last price is null, not zero;  
* no previous confidence is null, not zero;  
* a closed position may have unrealized P/L as not applicable;  
* unreadable bid quantity must include evidence-quality status.

---

# **47\. Monetary Value Object**

## **47.1 Definition**

`Money` represents a monetary amount and currency.

---

## **47.2 Properties**

Money  
\- amount  
\- currency

---

## **47.3 Invariants**

* use decimal representation, not floating-point binary arithmetic;  
* currency must be explicit;  
* IDR prices may follow exchange tick rules in future validation;  
* rounding rules must be centralized.

---

# **48\. Quantity Value Object**

## **48.1 Definition**

Represents position quantity.

For Indonesian equities, future configuration may distinguish shares and lots.

---

## **48.2 Properties**

Quantity  
\- value  
\- unit

---

## **48.3 Units**

SHARE  
LOT  
UNKNOWN

The MVP should choose one canonical storage unit and convert presentation values consistently.

Recommended canonical storage unit:

SHARE

---

# **49\. Percentage Value Object**

## **49.1 Definition**

Represents percentage-based values.

---

## **49.2 Uses**

* confidence;  
* probability;  
* profit and loss percentage;  
* risk percentage;  
* target allocation percentage.

---

## **49.3 Invariants**

* confidence and probability use range 0–100;  
* return percentage may be negative;  
* values must preserve intended precision;  
* UI rounding must not alter stored canonical values.

---

# **50\. Time and Trading Date Model**

## **50.1 Timestamps**

Persist timestamps in UTC.

Convert to the user’s timezone for display.

---

## **50.2 Default User Timezone**

Asia/Jakarta

---

## **50.3 Trading Date**

`trading_date` represents the Indonesian market date associated with an update.

It is distinct from:

* file upload date;  
* AI analysis completion date;  
* user record creation date.

---

## **50.4 Invariants**

* market timestamps preserve source timezone or offset;  
* unknown market time must remain null;  
* chronology should prioritize market timestamp when reliable;  
* audit chronology always preserves system creation timestamp.

---

# **51\. Domain Error Codes**

Recommended domain-level error codes:

SESSION\_NOT\_FOUND  
SESSION\_NOT\_OWNED  
INVALID\_STATUS\_TRANSITION  
SESSION\_ALREADY\_CLOSED  
SESSION\_CANCELLED  
SESSION\_ARCHIVED  
TICKER\_LOCKED  
INITIAL\_EVIDENCE\_INCOMPLETE  
REQUIRED\_EVIDENCE\_UNAVAILABLE  
ANALYSIS\_ALREADY\_RUNNING  
ANALYSIS\_NOT\_VALID  
ANALYSIS\_NOT\_CANONICAL  
THESIS\_NOT\_AVAILABLE  
THESIS\_INVALIDATED  
THESIS\_CHANGE\_REASON\_REQUIRED  
POSITION\_ALREADY\_EXISTS  
POSITION\_NOT\_OPEN  
POSITION\_ALREADY\_CLOSED  
ENTRY\_NOT\_ALLOWED  
STOP\_LOSS\_REQUIRED  
ACTIVE\_TARGET\_REQUIRED  
INVALID\_STOP\_LOSS  
STOP\_CHANGE\_REASON\_REQUIRED  
INVALID\_TARGET  
TARGET\_CHANGE\_REASON\_REQUIRED  
INVALID\_EXIT\_QUANTITY  
FINAL\_EXIT\_QUANTITY\_MISMATCH  
JOURNAL\_NOT\_ELIGIBLE  
EVIDENCE\_EXCLUDED  
EVIDENCE\_NOT\_AVAILABLE  
CORRECTION\_REASON\_REQUIRED

User-facing messages will be defined in the API and UI specifications.

---

# **52\. Persistence Recommendations**

The following should generally be stored as separate records:

* Trade Session;  
* Evidence;  
* Session Update;  
* Analysis Request;  
* Analysis Version;  
* Trading Thesis version;  
* Position;  
* Position Entry;  
* Position Exit;  
* Stop-Loss Version;  
* Position Target version;  
* Context Summary;  
* Trading Journal version;  
* User Reflection;  
* Timeline Event;  
* Audit Record;  
* Background Job;  
* Job Attempt;  
* AI Usage Record;  
* Notification.

Structured subcomponents may use JSON fields where:

* schema is versioned;  
* querying individual fields is not frequently required;  
* immutable payload preservation is valuable.

Canonical values needed for dashboard filtering should use typed columns.

---

# **53\. Domain Model Testing Requirements**

Tests must cover:

## **53.1 TradeSession Tests**

* creation;  
* ticker locking;  
* readiness;  
* lifecycle transition validation;  
* cancellation;  
* archive restoration;  
* closed-session restrictions.

## **53.2 Evidence Tests**

* required evidence selection;  
* superseding;  
* exclusion;  
* unreadable evidence;  
* analysis-evidence links.

## **53.3 Analysis Tests**

* immutable version creation;  
* validation status;  
* canonicalization;  
* contradiction rejection;  
* evidence traceability.

## **53.4 Thesis Tests**

* creation;  
* strengthening;  
* weakening;  
* review;  
* invalidation;  
* unsupported reversal rejection.

## **53.5 Position Tests**

* initial entry;  
* weighted average;  
* additional entry;  
* stop versioning;  
* target versioning;  
* partial exit;  
* final exit;  
* excessive exit rejection.

## **53.6 Journal Tests**

* eligibility;  
* full-history source;  
* outdated status;  
* regeneration;  
* user-reflection separation.

---

# **54\. Domain Model Acceptance Criteria**

The domain model is accepted when:

1. one Trade Session represents one complete trade story;  
2. Trade Session, Position, Evidence, Analysis, Thesis, and Journal boundaries are explicit;  
3. canonical state is separated from immutable history;  
4. AI output is treated as proposed state before validation;  
5. user-confirmed execution is separated from AI recommendations;  
6. all lifecycle and thesis enums are controlled;  
7. all position mutations preserve history;  
8. analysis versions are immutable;  
9. thesis changes are versioned;  
10. evidence used by analysis is traceable;  
11. open positions require stop loss and target;  
12. closed positions cannot reopen;  
13. journal generation requires closure;  
14. unknown values remain null or explicitly unknown;  
15. financial calculations are reproducible;  
16. domain events support timeline and audit reconstruction;  
17. provider-specific concerns remain outside the domain;  
18. user-facing language does not alter English internal identifiers;  
19. the model can support longitudinal context construction;  
20. the model can be represented cleanly in PostgreSQL.

---

# **55\. Final Domain Statement**

The TradePilot AI domain is centered on the Trade Session as one persistent and auditable trade story.

The model separates:

* proposed analysis from confirmed action;  
* canonical state from immutable history;  
* AI recommendation from user execution;  
* current thesis from thesis evolution;  
* active position management from post-trade review.

Every important decision, observation, and change must remain traceable from initial evidence through final journal generation.

The domain model must ensure that the complete trade story is never reduced to the latest screenshot or overwritten by the latest AI response.

