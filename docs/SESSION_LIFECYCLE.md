# **TradePilot AI — Session Lifecycle Specification**

**Document:** `SESSION_LIFECYCLE.md`  
**Version:** 1.0  
**Status:** Final  
**Product Name:** TradePilot AI  
**Primary References:** `PRD.md`, `PRODUCT_RULES.md`, `USER_FLOWS.md`, `ARCHITECTURE.md`, `DOMAIN_MODEL.md`  
**Purpose:** Define Trade Session states, valid transitions, transition guards, allowed actions, temporary processing behavior, terminal-state rules, archive behavior, and invalid-transition handling.

---

## **1\. Document Purpose**

This document defines the authoritative lifecycle model for a Trade Session.

It specifies:

* all valid session states;  
* stable and temporary states;  
* transition triggers;  
* required transition guards;  
* valid user actions per state;  
* system-side effects;  
* invalid transitions;  
* failure recovery;  
* terminal-state behavior;  
* archive and restore behavior;  
* lifecycle audit requirements.

The backend must enforce these rules.

Frontend restrictions alone are not sufficient.

---

# **2\. Lifecycle Principles**

## **2.1 One Active Lifecycle per Trade Session**

A Trade Session represents one trade story.

It may move through preparation, analysis, monitoring, active position management, and closure only once.

A completed or cancelled session cannot become a new active trade.

A new trade requires a new Trade Session.

---

## **2.2 Backend State Is Authoritative**

The backend is the source of truth for lifecycle status.

The frontend may:

* display allowed actions;  
* disable unavailable actions;  
* explain transition requirements.

The frontend must not independently assign lifecycle status.

---

## **2.3 Transitions Require Explicit Triggers**

Every transition must be caused by an explicit trigger, such as:

* evidence readiness;  
* analysis request;  
* validated analysis completion;  
* user-confirmed position entry;  
* user-confirmed exit;  
* setup cancellation;  
* archive action.

AI output alone must not directly change the lifecycle.

---

## **2.4 Stable and Temporary States Must Be Separated**

`ANALYZING` is a temporary processing state.

The system must preserve the previous stable business state while analysis is running.

Examples:

lifecycle\_status \= ANALYZING  
stable\_status \= WATCHING

lifecycle\_status \= ANALYZING  
stable\_status \= OPEN\_POSITION

When processing ends, the session returns to the appropriate stable state.

---

## **2.5 Terminal Business States Must Remain Terminal**

The following states are terminal for the trade lifecycle:

* `CLOSED_TAKE_PROFIT`  
* `CLOSED_STOP_LOSS`  
* `CLOSED_MANUAL`  
* `CANCELLED`

Archiving does not create a new trade lifecycle and does not remove terminal status history.

---

# **3\. Lifecycle States**

The authoritative lifecycle states are:

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

# **4\. State Categories**

## **4.1 Preparation States**

DRAFT  
READY\_FOR\_ANALYSIS

These states occur before the first valid canonical analysis.

---

## **4.2 Processing State**

ANALYZING

This is a temporary state used while an AI analysis job is active.

---

## **4.3 Pre-Entry Active State**

WATCHING

The setup has been analyzed but no actual position exists.

---

## **4.4 Position States**

OPEN\_POSITION  
PARTIALLY\_CLOSED

These states contain an active user position.

---

## **4.5 Closed States**

CLOSED\_TAKE\_PROFIT  
CLOSED\_STOP\_LOSS  
CLOSED\_MANUAL

The position is fully closed.

---

## **4.6 Non-Trade Terminal State**

CANCELLED

The setup ended before any position was opened.

---

## **4.7 Visibility State**

ARCHIVED

`ARCHIVED` changes workspace visibility.

It does not erase the underlying previous business state.

The implementation must preserve the pre-archive state.

---

# **5\. Stable Status Model**

## **5.1 Purpose**

Because `ANALYZING` and `ARCHIVED` may temporarily obscure the underlying business condition, the session must preserve its stable business status.

Recommended fields:

lifecycle\_status  
stable\_status  
pre\_archive\_status

---

## **5.2 Stable Status Values**

`stable_status` may contain:

DRAFT  
READY\_FOR\_ANALYSIS  
WATCHING  
OPEN\_POSITION  
PARTIALLY\_CLOSED  
CLOSED\_TAKE\_PROFIT  
CLOSED\_STOP\_LOSS  
CLOSED\_MANUAL  
CANCELLED

It must not contain:

ANALYZING  
ARCHIVED

---

## **5.3 Analysis Example**

During an open-position analysis:

lifecycle\_status \= ANALYZING  
stable\_status \= OPEN\_POSITION

After successful completion:

lifecycle\_status \= OPEN\_POSITION  
stable\_status \= OPEN\_POSITION

After failure:

lifecycle\_status \= OPEN\_POSITION  
stable\_status \= OPEN\_POSITION

---

## **5.4 Archive Example**

Before archive:

lifecycle\_status \= CLOSED\_TAKE\_PROFIT  
stable\_status \= CLOSED\_TAKE\_PROFIT

After archive:

lifecycle\_status \= ARCHIVED  
stable\_status \= CLOSED\_TAKE\_PROFIT  
pre\_archive\_status \= CLOSED\_TAKE\_PROFIT

After restore:

lifecycle\_status \= CLOSED\_TAKE\_PROFIT  
stable\_status \= CLOSED\_TAKE\_PROFIT  
pre\_archive\_status \= null

---

# **6\. State Definitions**

## **6.1 DRAFT**

### **Meaning**

The Trade Session exists, but the minimum initial analysis requirements are incomplete.

### **Entry Conditions**

A newly created Trade Session begins in `DRAFT`.

### **Required Existing Data**

* owner;  
* ticker;  
* market;  
* creation timestamp.

### **Typical Missing Data**

* orderbook screenshot;  
* three-month chart;  
* six-month chart.

### **Allowed User Actions**

* edit session title;  
* edit company name;  
* edit initial note;  
* correct ticker before initial analysis;  
* upload evidence;  
* replace initial evidence;  
* delete or exclude uncommitted draft evidence;  
* cancel setup;  
* archive, when supported.

### **Prohibited Actions**

* run initial analysis when evidence is incomplete;  
* open a position;  
* add an entry;  
* change stop loss;  
* record an exit;  
* generate a journal.

### **Exit Conditions**

The session becomes `READY_FOR_ANALYSIS` when all required initial evidence is active and available.

---

## **6.2 READY\_FOR\_ANALYSIS**

### **Meaning**

The minimum required initial evidence is available and the session can run its first analysis.

### **Entry Guard**

All must be true:

* ticker exists;  
* market exists;  
* active orderbook screenshot exists;  
* active three-month chart exists;  
* active six-month chart exists;  
* required evidence status is `AVAILABLE`;  
* no initial canonical analysis exists;  
* no analysis job is active.

### **Allowed User Actions**

* inspect evidence;  
* replace evidence;  
* add optional evidence;  
* run initial analysis;  
* add notes;  
* cancel setup.

### **Prohibited Actions**

* open a position;  
* add position transactions;  
* generate follow-up analysis;  
* generate journal.

### **Exit Conditions**

* to `ANALYZING` when initial analysis begins;  
* to `DRAFT` when required evidence becomes unavailable, excluded, or superseded without replacement;  
* to `CANCELLED` when the user cancels the setup.

---

## **6.3 ANALYZING**

### **Meaning**

An AI analysis operation is currently processing.

### **Entry Guard**

All must be true:

* a valid `AnalysisRequest` exists;  
* a valid `BackgroundJob` exists;  
* no conflicting analysis job is active for the same logical update;  
* `stable_status` is preserved.

### **Allowed User Actions**

* view job progress;  
* navigate away;  
* view previous analyses;  
* view existing evidence;  
* add a note when it does not affect the active analysis;  
* cancel the job if the job type supports cancellation.

### **Conditionally Allowed Actions**

New evidence may be uploaded, but it must not be silently included in the already-running analysis unless the job is explicitly rebuilt.

### **Prohibited Actions**

While a conflicting analysis is active:

* start the same analysis again;  
* replace evidence used by the active request;  
* open a position based on an incomplete initial analysis;  
* mutate canonical thesis;  
* perform conflicting position corrections.

Position changes during follow-up analysis should generally be blocked or serialized to prevent analysis using stale position state.

### **Exit Conditions**

* successful initial analysis → `WATCHING`;  
* successful follow-up analysis → previous stable state;  
* failed analysis → previous stable state;  
* cancelled analysis → previous stable state.

---

## **6.4 WATCHING**

### **Meaning**

The initial analysis is complete, but the user has not opened a position.

### **Entry Guard**

All must be true:

* valid canonical initial analysis exists;  
* active canonical thesis exists;  
* no historical actual position exists;  
* setup is not cancelled.

### **Allowed User Actions**

* upload new evidence;  
* create a morning, midday, closing, or custom update;  
* run follow-up analysis;  
* add notes;  
* inspect history;  
* compare analysis versions;  
* mark position as open;  
* cancel setup;  
* archive when appropriate.

### **Position Opening Guard**

The position may be opened only when:

* canonical thesis exists;  
* thesis status is not `INVALIDATED`;  
* actual entry price is provided;  
* entry timestamp is provided;  
* active stop loss is provided;  
* at least one target is provided;  
* no position already exists.

### **Prohibited Actions**

* partial exit;  
* final exit;  
* additional entry;  
* stop-loss version change;  
* target change on an actual position;  
* journal generation.

### **Exit Conditions**

* to `ANALYZING` for a watching update;  
* to `OPEN_POSITION` after user-confirmed entry;  
* to `CANCELLED` after user-confirmed cancellation;  
* to `ARCHIVED` when archived.

---

## **6.5 OPEN\_POSITION**

### **Meaning**

The user has an active position with no recorded partial exit.

### **Entry Guard**

All must be true:

* one Position exists;  
* Position status is `OPEN`;  
* at least one PositionEntry exists;  
* active stop loss exists;  
* at least one active target exists;  
* remaining quantity is positive or unknown in simplified tracking mode;  
* canonical thesis was not invalidated at opening.

### **Allowed User Actions**

* upload evidence;  
* run open-position analysis;  
* add an entry;  
* change stop loss;  
* change targets;  
* record partial exit;  
* record full exit;  
* add notes;  
* inspect analyses;  
* inspect timeline;  
* apply an AI recommendation after confirmation.

### **Conditionally Allowed Actions**

Additional entry is allowed only when:

* position remains active;  
* thesis is not `INVALIDATED`;  
* no conflicting position mutation is in progress;  
* required risk warning has been acknowledged.

### **Prohibited Actions**

* cancel setup;  
* create a second Position;  
* delete the initial entry;  
* archive while an active position exists unless explicitly prohibited or supported as hidden active state;  
* generate final journal.

The MVP should block archiving an active position.

### **Exit Conditions**

* to `ANALYZING` during open-position analysis;  
* to `PARTIALLY_CLOSED` after a valid partial exit;  
* to a closed state after final exit.

---

## **6.6 PARTIALLY\_CLOSED**

### **Meaning**

At least one exit has been recorded and part of the position remains active.

### **Entry Guard**

All must be true:

* at least one partial PositionExit exists;  
* Position status is `PARTIALLY_CLOSED`;  
* remaining quantity is positive;  
* active stop loss exists;  
* at least one active target exists unless explicitly replaced by an exit-only plan.

For MVP consistency, at least one active target remains required.

### **Allowed User Actions**

* upload evidence;  
* run open-position analysis;  
* change stop loss;  
* change targets;  
* add another entry when thesis permits;  
* record another partial exit;  
* record final exit;  
* add notes;  
* inspect realized and unrealized results.

### **Prohibited Actions**

* cancel setup;  
* create a second Position;  
* generate final journal;  
* reopen already exited quantities.

### **Exit Conditions**

* to `ANALYZING` during analysis;  
* remains `PARTIALLY_CLOSED` after another partial exit;  
* to a closed state after final exit.

---

## **6.7 CLOSED\_TAKE\_PROFIT**

### **Meaning**

The position is fully closed and the user identifies take profit as the final closure reason.

### **Entry Guard**

All must be true:

* Position status is `CLOSED`;  
* remaining quantity equals zero or is explicitly finalized in simplified tracking mode;  
* a final exit exists;  
* final exit reason is `TAKE_PROFIT`;  
* final result has been recalculated.

### **Allowed User Actions**

* view closing analysis;  
* generate or regenerate journal;  
* add user reflection;  
* inspect history;  
* correct historical data through correction flow;  
* archive session;  
* create a new Trade Session for the same ticker.

### **Prohibited Actions**

* add entry;  
* change active stop;  
* change active targets;  
* record another active partial exit;  
* reopen the Position;  
* return to `WATCHING`.

---

## **6.8 CLOSED\_STOP\_LOSS**

### **Meaning**

The position is fully closed because stop loss was executed or identified as the exit reason.

### **Entry Guard**

All must be true:

* Position status is `CLOSED`;  
* final exit exists;  
* final exit reason is `STOP_LOSS`;  
* remaining quantity is zero or explicitly finalized;  
* final result has been calculated.

### **Allowed and Prohibited Actions**

The same terminal rules as `CLOSED_TAKE_PROFIT` apply.

Historical correction may change financial details, but changing the final closure category requires an explicit correction with audit history.

---

## **6.9 CLOSED\_MANUAL**

### **Meaning**

The position is fully closed for a reason other than direct take-profit or stop-loss completion.

Possible reasons include:

* thesis invalidation;  
* risk reduction;  
* time-based exit;  
* trailing stop;  
* manual discretion;  
* other.

### **Entry Guard**

All must be true:

* Position status is `CLOSED`;  
* final exit exists;  
* remaining quantity is zero or finalized;  
* final exit reason is not categorized as direct TP or direct SL;  
* final result is calculated.

### **Allowed and Prohibited Actions**

The same terminal rules as other closed states apply.

---

## **6.10 CANCELLED**

### **Meaning**

The setup ended without the user opening a position.

### **Entry Guard**

All must be true:

* no Position exists;  
* no PositionEntry exists;  
* cancellation reason exists;  
* user confirmation exists.

### **Allowed User Actions**

* view session history;  
* add a final note;  
* archive;  
* restore from archive;  
* create a new Trade Session for the same ticker.

### **Prohibited Actions**

* open a position;  
* run active setup analysis;  
* add entry or exit;  
* generate a completed-position journal.

A lightweight cancelled-setup review may be added in future but is not the same as an AI Trading Journal.

---

## **6.11 ARCHIVED**

### **Meaning**

The session is hidden from active operational views while all business history remains preserved.

### **Entry Guard**

Recommended MVP rule:

Archiving is allowed only when the stable status is:

DRAFT  
READY\_FOR\_ANALYSIS  
WATCHING  
CANCELLED  
CLOSED\_TAKE\_PROFIT  
CLOSED\_STOP\_LOSS  
CLOSED\_MANUAL

Archiving is blocked when stable status is:

OPEN\_POSITION  
PARTIALLY\_CLOSED

Archiving is also blocked while:

lifecycle\_status \= ANALYZING

### **Required Data**

* `pre_archive_status`;  
* `archived_at`;  
* actor;  
* archive reason, optional.

### **Allowed User Actions**

* view session;  
* inspect history;  
* restore from archive;  
* inspect journal;  
* add reflection to a closed session when permitted.

### **Prohibited Actions**

* run new analysis while archived;  
* mutate position;  
* upload active evidence;  
* change thesis;  
* open a position.

The session must be restored before non-read-only operations.

---

# **7\. Lifecycle Transition Matrix**

| From | To | Trigger | Allowed |
| ----- | ----- | ----- | ----- |
| `DRAFT` | `READY_FOR_ANALYSIS` | Required evidence becomes complete | Yes |
| `DRAFT` | `CANCELLED` | User cancels before entry | Yes |
| `DRAFT` | `ARCHIVED` | User archives draft | Yes |
| `READY_FOR_ANALYSIS` | `DRAFT` | Required evidence becomes unavailable | Yes |
| `READY_FOR_ANALYSIS` | `ANALYZING` | Initial analysis starts | Yes |
| `READY_FOR_ANALYSIS` | `CANCELLED` | User cancels | Yes |
| `READY_FOR_ANALYSIS` | `ARCHIVED` | User archives | Yes |
| `ANALYZING` | `WATCHING` | Initial analysis succeeds | Yes |
| `ANALYZING` | Previous stable state | Follow-up succeeds, fails, or is cancelled | Yes |
| `WATCHING` | `ANALYZING` | Follow-up analysis starts | Yes |
| `WATCHING` | `OPEN_POSITION` | User confirms actual entry | Yes |
| `WATCHING` | `CANCELLED` | User cancels setup | Yes |
| `WATCHING` | `ARCHIVED` | User archives inactive setup | Yes |
| `OPEN_POSITION` | `ANALYZING` | Position update analysis starts | Yes |
| `OPEN_POSITION` | `PARTIALLY_CLOSED` | User records partial exit | Yes |
| `OPEN_POSITION` | `CLOSED_TAKE_PROFIT` | User records final TP exit | Yes |
| `OPEN_POSITION` | `CLOSED_STOP_LOSS` | User records final SL exit | Yes |
| `OPEN_POSITION` | `CLOSED_MANUAL` | User records final manual exit | Yes |
| `PARTIALLY_CLOSED` | `ANALYZING` | Position update analysis starts | Yes |
| `PARTIALLY_CLOSED` | `PARTIALLY_CLOSED` | Another partial exit or active adjustment | Yes |
| `PARTIALLY_CLOSED` | `CLOSED_TAKE_PROFIT` | Final TP exit | Yes |
| `PARTIALLY_CLOSED` | `CLOSED_STOP_LOSS` | Final SL exit | Yes |
| `PARTIALLY_CLOSED` | `CLOSED_MANUAL` | Final manual exit | Yes |
| Closed state | `ARCHIVED` | User archives | Yes |
| `CANCELLED` | `ARCHIVED` | User archives | Yes |
| `ARCHIVED` | `pre_archive_status` | User restores | Yes |

All unlisted transitions are invalid.

---

# **8\. Explicit Invalid Transitions**

The backend must reject at least the following transitions:

DRAFT → OPEN\_POSITION  
DRAFT → PARTIALLY\_CLOSED  
DRAFT → CLOSED\_TAKE\_PROFIT  
DRAFT → CLOSED\_STOP\_LOSS  
DRAFT → CLOSED\_MANUAL

READY\_FOR\_ANALYSIS → OPEN\_POSITION  
READY\_FOR\_ANALYSIS → PARTIALLY\_CLOSED

WATCHING → PARTIALLY\_CLOSED  
WATCHING → CLOSED\_TAKE\_PROFIT  
WATCHING → CLOSED\_STOP\_LOSS  
WATCHING → CLOSED\_MANUAL

OPEN\_POSITION → WATCHING  
OPEN\_POSITION → CANCELLED  
OPEN\_POSITION → DRAFT  
OPEN\_POSITION → READY\_FOR\_ANALYSIS

PARTIALLY\_CLOSED → OPEN\_POSITION  
PARTIALLY\_CLOSED → WATCHING  
PARTIALLY\_CLOSED → CANCELLED

CLOSED\_\* → OPEN\_POSITION  
CLOSED\_\* → PARTIALLY\_CLOSED  
CLOSED\_\* → WATCHING  
CLOSED\_\* → DRAFT  
CLOSED\_\* → READY\_FOR\_ANALYSIS  
CLOSED\_\* → CANCELLED

CANCELLED → WATCHING  
CANCELLED → OPEN\_POSITION  
CANCELLED → READY\_FOR\_ANALYSIS

ARCHIVED → any state other than pre\_archive\_status

---

# **9\. Transition Guards**

## **9.1 Guard: Initial Evidence Complete**

Identifier:

INITIAL\_EVIDENCE\_COMPLETE

Conditions:

* one active `ORDERBOOK_SCREENSHOT`;  
* one active `CHART_THREE_MONTH`;  
* one active `CHART_SIX_MONTH`;  
* all are `AVAILABLE`;  
* none are excluded;  
* none are superseded without replacement.

---

## **9.2 Guard: No Active Analysis Job**

Identifier:

NO\_ACTIVE\_ANALYSIS\_JOB

Conditions:

No job with status below may exist for the same conflicting scope:

QUEUED  
PROCESSING  
RETRYING

---

## **9.3 Guard: Canonical Initial Analysis Exists**

Identifier:

CANONICAL\_INITIAL\_ANALYSIS\_EXISTS

Conditions:

* an `INITIAL_ANALYSIS` version exists;  
* validation status is valid;  
* canonical status is `CANONICAL`;  
* active thesis exists.

---

## **9.4 Guard: Position Opening Requirements**

Identifier:

POSITION\_OPENING\_REQUIREMENTS\_MET

Conditions:

* lifecycle is `WATCHING`;  
* no Position exists;  
* thesis status is not `INVALIDATED`;  
* entry price is valid;  
* entry timestamp is valid;  
* stop loss is valid;  
* one or more valid targets exist;  
* user explicitly confirms.

---

## **9.5 Guard: Active Position Exists**

Identifier:

ACTIVE\_POSITION\_EXISTS

Conditions:

* Position exists;  
* Position status is `OPEN` or `PARTIALLY_CLOSED`;  
* remaining quantity is positive or position is active in simplified tracking mode.

---

## **9.6 Guard: Partial Exit Valid**

Identifier:

PARTIAL\_EXIT\_VALID

Conditions:

* active Position exists;  
* exit quantity is positive;  
* exit quantity is less than remaining quantity;  
* exit price exists;  
* exit timestamp exists;  
* reason exists.

---

## **9.7 Guard: Final Exit Valid**

Identifier:

FINAL\_EXIT\_VALID

Conditions:

* active Position exists;  
* final exit quantity equals remaining quantity;  
* exit price exists;  
* exit timestamp exists;  
* exit reason exists;  
* resulting remaining quantity is zero;  
* user explicitly confirms.

---

## **9.8 Guard: Setup Cancellable**

Identifier:

SETUP\_CANCELLABLE

Conditions:

* no Position exists;  
* no PositionEntry exists;  
* status is `DRAFT`, `READY_FOR_ANALYSIS`, or `WATCHING`;  
* no conflicting job is active;  
* cancellation reason exists.

---

## **9.9 Guard: Session Archivable**

Identifier:

SESSION\_ARCHIVABLE

Conditions:

* no active analysis job;  
* no open or partially closed position;  
* session is not already archived.

---

## **9.10 Guard: Session Restorable**

Identifier:

SESSION\_RESTORABLE

Conditions:

* current status is `ARCHIVED`;  
* `pre_archive_status` exists;  
* preserved status is valid;  
* restore does not reopen a closed position.

---

# **10\. Allowed Actions by State**

| Action | Draft | Ready | Analyzing | Watching | Open | Partial | Closed | Cancelled | Archived |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| Edit draft identity | Yes | Limited | No | No | No | No | No | No | No |
| Upload evidence | Yes | Yes | Limited | Yes | Yes | Yes | Historical only | No | No |
| Replace initial evidence | Yes | Yes | No | Correction flow | Correction flow | Correction flow | Correction flow | No | No |
| Run initial analysis | No | Yes | No | No | No | No | No | No | No |
| Run follow-up analysis | No | No | No | Yes | Yes | Yes | Closing/journal only | No | No |
| Open position | No | No | No | Yes | No | No | No | No | No |
| Add entry | No | No | No | No | Yes | Conditional | No | No | No |
| Change stop | No | No | No | No | Yes | Yes | No | No | No |
| Change target | No | No | No | No | Yes | Yes | No | No | No |
| Partial exit | No | No | No | No | Yes | Yes | No | No | No |
| Final exit | No | No | No | No | Yes | Yes | No | No | No |
| Cancel setup | Yes | Yes | No | Yes | No | No | No | No | No |
| Generate journal | No | No | No | No | No | No | Yes | No | Read-only |
| Add reflection | No | No | No | No | No | No | Yes | Optional note only | Closed journals only |
| Archive | Yes | Yes | No | Yes | No | No | Yes | Yes | No |
| Restore | No | No | No | No | No | No | No | No | Yes |

---

# **11\. Analysis-State Behavior**

## **11.1 Starting Analysis**

When analysis starts, the system must atomically:

1. validate the source stable state;  
2. validate analysis eligibility;  
3. create `AnalysisRequest`;  
4. create `BackgroundJob`;  
5. store the stable status;  
6. set lifecycle status to `ANALYZING`;  
7. create timeline and audit events;  
8. dispatch the job through the queue mechanism.

---

## **11.2 Initial Analysis Success**

On successful initial analysis:

1. validate structured output;  
2. validate Indonesian narrative fields;  
3. validate thesis;  
4. create immutable `AnalysisVersion`;  
5. create initial `TradingThesis`;  
6. mark analysis canonical;  
7. set lifecycle to `WATCHING`;  
8. set stable status to `WATCHING`;  
9. update canonical summary fields;  
10. create timeline events.

---

## **11.3 Follow-Up Analysis Success**

On successful follow-up analysis:

1. create immutable analysis version;  
2. evaluate contradiction result;  
3. create thesis version when applicable;  
4. update canonical metrics;  
5. return lifecycle to preserved stable status;  
6. preserve Position state;  
7. create timeline events.

A follow-up analysis does not automatically change:

* stop loss;  
* targets;  
* entries;  
* exits.

---

## **11.4 Analysis Failure**

On failure:

1. mark job failed;  
2. store error details;  
3. keep latest valid analysis canonical;  
4. keep current thesis unchanged;  
5. restore lifecycle to stable status;  
6. notify the user;  
7. allow retry when eligible.

---

## **11.5 Analysis Cancellation**

When cancellation succeeds:

1. mark job cancelled;  
2. stop canonicalization;  
3. preserve uploaded evidence;  
4. restore stable status;  
5. record cancellation event.

A provider request that cannot be physically cancelled may still complete, but its output must not become canonical after logical cancellation.

---

# **12\. Position Opening Transition**

## **12.1 Source State**

WATCHING

## **12.2 Target State**

OPEN\_POSITION

## **12.3 Required Transaction**

The transition must create or update atomically:

* Position;  
* initial PositionEntry;  
* active StopLossVersion;  
* one or more PositionTargets;  
* entry thesis snapshot;  
* lifecycle status;  
* stable status;  
* timeline event;  
* audit record.

---

## **12.4 Failure Rule**

If any required record fails:

* no Position is considered opened;  
* no partial records may remain canonical;  
* lifecycle remains `WATCHING`.

---

## **12.5 Thesis Guard**

Opening is blocked when thesis status is:

INVALIDATED

When thesis status is:

UNDER\_REVIEW

opening may remain allowed with a strong warning, according to product rules.

The user must explicitly acknowledge the increased uncertainty.

---

# **13\. Partial Exit Transition**

## **13.1 From OPEN\_POSITION**

A valid partial exit changes:

OPEN\_POSITION → PARTIALLY\_CLOSED

## **13.2 From PARTIALLY\_CLOSED**

Another partial exit keeps:

PARTIALLY\_CLOSED → PARTIALLY\_CLOSED

## **13.3 Required Transaction**

The system must atomically:

* create PositionExit;  
* calculate realized result;  
* calculate remaining quantity;  
* update Position status;  
* update Trade Session lifecycle;  
* create timeline event;  
* create audit record.

---

## **13.4 Active Controls After Partial Exit**

The system must confirm:

* remaining quantity is positive;  
* one active stop remains;  
* at least one active target remains;  
* future analyses use the remaining position.

---

# **14\. Final Closure Transition**

## **14.1 Closure Classification**

The target session state is selected from the final user-confirmed exit reason.

### **Take Profit**

exit\_reason \= TAKE\_PROFIT  
session\_status \= CLOSED\_TAKE\_PROFIT

### **Stop Loss**

exit\_reason \= STOP\_LOSS  
session\_status \= CLOSED\_STOP\_LOSS

### **Other Final Exit**

session\_status \= CLOSED\_MANUAL

Examples include:

* thesis invalidation;  
* risk reduction;  
* time-based exit;  
* trailing stop;  
* manual discretion;  
* other.

---

## **14.2 Required Transaction**

The system must atomically:

* create final PositionExit;  
* set remaining quantity to zero;  
* calculate realized result;  
* close active stop;  
* resolve active targets;  
* set Position status to `CLOSED`;  
* set Position closed timestamp;  
* set Trade Session closed status;  
* set stable status;  
* set closed timestamp;  
* create timeline event;  
* create audit record;  
* create closing-analysis outbox event.

---

## **14.3 Post-Closure Side Effects**

After closure:

* active-management actions are disabled;  
* closing analysis becomes eligible;  
* AI Trading Journal becomes eligible;  
* position parameters become historical;  
* new trading activity requires a new Trade Session.

---

# **15\. Cancellation Transition**

## **15.1 Allowed Source States**

DRAFT  
READY\_FOR\_ANALYSIS  
WATCHING

## **15.2 Target State**

CANCELLED

## **15.3 Required Guard**

No historical Position or PositionEntry may exist.

## **15.4 Required Data**

* cancellation reason;  
* actor;  
* timestamp.

## **15.5 Side Effects**

* active setup reminders stop;  
* new setup analyses are disabled;  
* history remains visible;  
* session may later be archived.

---

# **16\. Archive and Restore**

## **16.1 Archive Is Not Deletion**

Archive must preserve:

* evidence;  
* analyses;  
* thesis history;  
* position history;  
* journal;  
* timeline;  
* audit records;  
* final result.

---

## **16.2 Archive Transition**

Before archiving:

pre\_archive\_status \= lifecycle\_status  
stable\_status \= current stable business state

After archiving:

lifecycle\_status \= ARCHIVED  
archived\_at \= current timestamp

---

## **16.3 Restore Transition**

Restore must:

1. validate `pre_archive_status`;  
2. restore lifecycle to the preserved state;  
3. keep terminal state terminal;  
4. clear `archived_at` or preserve it in archive history;  
5. clear active `pre_archive_status`;  
6. create timeline and audit records.

---

## **16.4 Repeated Archive History**

If the user archives and restores multiple times, each event must remain traceable.

A separate archive-event history or audit records should preserve every change.

---

# **17\. Historical Correction Behavior**

## **17.1 Corrections Do Not Reverse Lifecycle by Default**

Correcting:

* entry price;  
* exit price;  
* quantity;  
* fee;  
* timestamp;

must not automatically reopen or reverse the trade lifecycle.

---

## **17.2 Correction May Reclassify Closure**

Changing the final exit reason may require changing:

CLOSED\_TAKE\_PROFIT  
CLOSED\_STOP\_LOSS  
CLOSED\_MANUAL

This must occur only through an explicit correction workflow.

Requirements:

* correction reason;  
* preserved previous value;  
* recalculated result;  
* new audit record;  
* journal marked outdated;  
* closing analysis optionally regenerated.

---

## **17.3 Invalid Correction**

A correction must not result in:

* negative remaining quantity;  
* active quantity in a closed position;  
* partial exit greater than total entries;  
* missing final exit in a closed session;  
* cancellation after a historical entry.

---

# **18\. Journal Lifecycle Relationship**

The journal is not the primary Trade Session lifecycle.

It has its own status:

PENDING  
GENERATING  
COMPLETED  
FAILED  
OUTDATED

A closed Trade Session remains closed regardless of journal-generation status.

Examples:

TradeSession \= CLOSED\_TAKE\_PROFIT  
Journal \= GENERATING

TradeSession \= CLOSED\_STOP\_LOSS  
Journal \= FAILED

Journal failure must not change the closed session status.

---

# **19\. Thesis Lifecycle Relationship**

Thesis status is separate from Trade Session lifecycle.

Valid examples:

TradeSession \= WATCHING  
Thesis \= INTACT

TradeSession \= OPEN\_POSITION  
Thesis \= INTACT\_BUT\_WEAKENING

TradeSession \= PARTIALLY\_CLOSED  
Thesis \= UNDER\_REVIEW

TradeSession \= OPEN\_POSITION  
Thesis \= INVALIDATED

A thesis becoming `INVALIDATED` does not automatically close the Position.

It must:

* create a critical warning;  
* change the trading recommendation;  
* block additional entries;  
* require user review.

The user still records actual execution.

---

# **20\. Evidence Readiness Recalculation**

## **20.1 Before Initial Analysis**

When required evidence changes, readiness must be recalculated.

Possible transitions:

DRAFT → READY\_FOR\_ANALYSIS  
READY\_FOR\_ANALYSIS → DRAFT

---

## **20.2 After Initial Analysis**

Excluding or correcting historical initial evidence must not automatically return the session to `DRAFT`.

Instead:

* existing analysis remains historical;  
* canonical analysis may be marked for review;  
* the user may run a correction analysis;  
* audit history must explain the change.

---

# **21\. Concurrent Action Rules**

## **21.1 One Conflicting Analysis at a Time**

Only one canonical analysis operation may be active for the same session update.

---

## **21.2 Position Mutation Serialization**

The following operations must not execute concurrently for the same Position:

* additional entry;  
* stop change;  
* target change;  
* partial exit;  
* final exit;  
* historical correction.

Use:

* row locking;  
* optimistic version checking;  
* application-level locks;

as defined by implementation.

---

## **21.3 Stale Update Protection**

Position mutations should include an expected version.

Example:

expected\_position\_version \= 7

If the current version is 8, reject with a conflict response.

This prevents overwriting newer position state.

---

## **21.4 Analysis Snapshot Consistency**

Each analysis request must preserve the session and position version it used.

If the Position changes before canonicalization:

* analysis may remain historical;  
* canonicalization must verify whether it is still applicable;  
* stale trade-management recommendations may be rejected or marked outdated.

---

# **22\. Invalid Transition Handling**

## **22.1 API Response**

Invalid transitions must return a stable error contract.

Example:

{  
  "error": {  
    "code": "INVALID\_STATUS\_TRANSITION",  
    "message": "Status Trade Session saat ini tidak memungkinkan tindakan tersebut.",  
    "details": {  
      "current\_status": "CLOSED\_STOP\_LOSS",  
      "requested\_transition": "OPEN\_POSITION"  
    },  
    "retryable": false,  
    "correlation\_id": "uuid"  
  }  
}

---

## **22.2 No Partial Mutation**

When a transition is rejected:

* lifecycle status remains unchanged;  
* stable status remains unchanged;  
* no partial position transaction is created;  
* no misleading timeline success event is created.

A failed-attempt audit record may still be stored when appropriate.

---

## **22.3 Frontend Response**

The frontend should:

* display the Indonesian message;  
* refresh canonical state if stale;  
* disable invalid actions;  
* avoid silently retrying non-retryable domain errors.

---

# **23\. Lifecycle Domain Events**

Every successful transition must emit an appropriate domain event.

## **23.1 Preparation Events**

SESSION\_CREATED  
SESSION\_READY\_FOR\_ANALYSIS  
SESSION\_RETURNED\_TO\_DRAFT

## **23.2 Analysis Events**

SESSION\_ANALYSIS\_STARTED  
SESSION\_ANALYSIS\_COMPLETED  
SESSION\_ANALYSIS\_FAILED  
SESSION\_ANALYSIS\_CANCELLED

## **23.3 Position Events**

POSITION\_OPENED  
PARTIAL\_EXIT\_RECORDED  
POSITION\_CLOSED\_TAKE\_PROFIT  
POSITION\_CLOSED\_STOP\_LOSS  
POSITION\_CLOSED\_MANUAL

## **23.4 Terminal and Visibility Events**

SETUP\_CANCELLED  
SESSION\_ARCHIVED  
SESSION\_RESTORED

---

# **24\. Audit Requirements**

Each lifecycle transition must record:

* session ID;  
* previous lifecycle status;  
* new lifecycle status;  
* previous stable status;  
* new stable status;  
* actor;  
* trigger;  
* related entity ID;  
* reason when required;  
* timestamp;  
* request ID;  
* correlation ID;  
* job ID when applicable.

---

# **25\. Dashboard Classification Rules**

## **25.1 Active Sessions**

Include stable statuses:

DRAFT  
READY\_FOR\_ANALYSIS  
WATCHING  
OPEN\_POSITION  
PARTIALLY\_CLOSED

An `ANALYZING` session should appear in its relevant active category with a processing indicator.

---

## **25.2 Open Positions**

Include:

OPEN\_POSITION  
PARTIALLY\_CLOSED

If lifecycle is `ANALYZING` and stable status is one of these, the session remains visible under open positions.

---

## **25.3 Completed Sessions**

Include:

CLOSED\_TAKE\_PROFIT  
CLOSED\_STOP\_LOSS  
CLOSED\_MANUAL  
CANCELLED

---

## **25.4 Archived Sessions**

Include:

lifecycle\_status \= ARCHIVED

The UI should also display the preserved business status.

Example:

Diarsipkan — sebelumnya Selesai, Take Profit

---

# **26\. State-to-UI Label Mapping**

| Internal Status | User-Facing Label |
| ----- | ----- |
| `DRAFT` | Draft |
| `READY_FOR_ANALYSIS` | Siap Dianalisis |
| `ANALYZING` | Sedang Dianalisis |
| `WATCHING` | Memantau Setup |
| `OPEN_POSITION` | Posisi Terbuka |
| `PARTIALLY_CLOSED` | Ditutup Sebagian |
| `CLOSED_TAKE_PROFIT` | Selesai — Take Profit |
| `CLOSED_STOP_LOSS` | Selesai — Stop Loss |
| `CLOSED_MANUAL` | Selesai — Exit Manual |
| `CANCELLED` | Setup Dibatalkan |
| `ARCHIVED` | Diarsipkan |

---

# **27\. Transition Pseudocode**

## **27.1 Initial Readiness**

def recalculate\_initial\_readiness(session, evidence):  
    if session.has\_canonical\_initial\_analysis:  
        return session.lifecycle\_status

    if evidence.has\_all\_required\_active\_items():  
        session.transition\_to("READY\_FOR\_ANALYSIS")  
    else:  
        session.transition\_to("DRAFT")

    return session.lifecycle\_status

---

## **27.2 Begin Analysis**

def begin\_analysis(session, analysis\_request):  
    assert no\_conflicting\_active\_job(session, analysis\_request)  
    assert analysis\_is\_allowed(session, analysis\_request.analysis\_type)

    session.stable\_status \= resolve\_stable\_status(session)  
    session.lifecycle\_status \= "ANALYZING"

    create\_job(analysis\_request)  
    emit("SESSION\_ANALYSIS\_STARTED")

---

## **27.3 Complete Analysis**

def complete\_analysis(session, result):  
    assert result.is\_valid  
    assert result.canonicalization\_allowed

    persist\_analysis\_version(result)  
    apply\_valid\_canonical\_changes(session, result)

    if result.analysis\_type \== "INITIAL\_ANALYSIS":  
        session.lifecycle\_status \= "WATCHING"  
        session.stable\_status \= "WATCHING"  
    else:  
        session.lifecycle\_status \= session.stable\_status

    emit("SESSION\_ANALYSIS\_COMPLETED")

---

## **27.4 Open Position**

def open\_position(session, command):  
    assert session.lifecycle\_status \== "WATCHING"  
    assert session.active\_thesis\_status \!= "INVALIDATED"  
    assert command.has\_entry  
    assert command.has\_stop  
    assert command.has\_target  
    assert session.position is None

    with transaction():  
        position \= create\_position(command)  
        create\_initial\_entry(position, command)  
        create\_active\_stop(position, command)  
        create\_active\_targets(position, command)

        session.active\_position\_id \= position.id  
        session.lifecycle\_status \= "OPEN\_POSITION"  
        session.stable\_status \= "OPEN\_POSITION"

        emit("POSITION\_OPENED")

---

## **27.5 Final Exit**

def close\_position(session, position, exit\_command):  
    assert session.stable\_status in {  
        "OPEN\_POSITION",  
        "PARTIALLY\_CLOSED",  
    }  
    assert exit\_command.quantity \== position.remaining\_quantity

    with transaction():  
        record\_final\_exit(position, exit\_command)  
        position.close()

        session.lifecycle\_status \= map\_exit\_reason\_to\_session\_status(  
            exit\_command.reason  
        )  
        session.stable\_status \= session.lifecycle\_status  
        session.closed\_at \= exit\_command.executed\_at

        emit\_closure\_event(session.lifecycle\_status)  
        enqueue\_closing\_analysis()

---

# **28\. Lifecycle Testing Requirements**

## **28.1 State Transition Tests**

Test every valid transition.

Test every explicitly invalid transition.

---

## **28.2 Guard Tests**

Test:

* missing initial evidence;  
* excluded initial evidence;  
* duplicate active analysis;  
* invalidated thesis at entry;  
* missing stop;  
* missing target;  
* excessive partial exit;  
* final exit mismatch;  
* cancellation after entry;  
* archive during active position;  
* restore without preserved status.

---

## **28.3 Failure Recovery Tests**

Test:

* initial analysis timeout;  
* follow-up analysis schema failure;  
* job cancellation;  
* worker restart;  
* Redis interruption;  
* database transaction rollback;  
* stale position version.

---

## **28.4 Terminal-State Tests**

Test that closed and cancelled sessions cannot return to active trading states.

---

## **28.5 Archive Tests**

Test:

* archive allowed states;  
* archive blocked states;  
* restore exact previous state;  
* restore closed state without reopening;  
* repeated archive and restore audit history.

---

## **28.6 Concurrency Tests**

Test:

* double analysis submission;  
* simultaneous partial and final exit;  
* stop update racing with final exit;  
* analysis canonicalization after position version changed;  
* double-click position opening.

---

# **29\. Lifecycle Acceptance Criteria**

The lifecycle implementation is accepted when:

1. every Trade Session always has one valid lifecycle status;  
2. temporary processing preserves stable business state;  
3. all valid transitions are explicitly supported;  
4. all unlisted transitions are rejected;  
5. initial analysis cannot run without required evidence;  
6. position opening requires actual entry, stop, and target;  
7. an invalidated thesis blocks position opening and additional entries;  
8. partial exits preserve an active remaining position;  
9. final exit closes all remaining quantity;  
10. closure reason maps to the correct terminal state;  
11. cancelled sessions contain no historical position;  
12. closed sessions cannot reopen;  
13. archive preserves underlying status and all data;  
14. restoring an archive returns to the exact preserved state;  
15. failed analysis returns to the previous stable state;  
16. failed transitions create no partial canonical mutation;  
17. lifecycle transitions are transactional;  
18. lifecycle events are auditable;  
19. concurrent conflicting actions are prevented;  
20. journal status does not alter closed-session status.

---

# **30\. Final Lifecycle Statement**

A Trade Session must move through a controlled, auditable, and irreversible trade lifecycle.

The system must allow the user to progress naturally from setup preparation to analysis, monitoring, position management, closure, and journal generation while preventing invalid state changes.

The lifecycle must preserve three critical truths:

1. temporary AI processing must never corrupt the underlying trade state;  
2. AI recommendations must never replace user-confirmed execution;  
3. a completed trade story must never be reopened or rewritten as a new active trade.

