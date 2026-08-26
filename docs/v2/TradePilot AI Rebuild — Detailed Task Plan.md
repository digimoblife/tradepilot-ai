# **TradePilot AI Rebuild — Detailed Task Plan**

**Document Version:** 1.0  
**Rebuild Goal:** Replace the existing over-complex business workflow with the approved session-based trading analysis workflow.  
**AI Provider:** Gemini only  
**Production Model:** `gemini-3.1-flash-lite`  
**Engineering Document Language:** English  
**User-Facing Analysis Language:** Indonesian

---

# **1\. Rebuild Objective**

The rebuild must implement this approved product flow:

Create Session  
→ Upload Initial Evidence  
→ Initial Analysis  
→ User chooses BUY, WAIT, or SKIP  
→ WAIT may produce repeated WAIT Updates  
→ BUY opens one position  
→ Open Position may produce repeated Position Updates  
→ User clicks CLOSE  
→ Session becomes CLOSED

The rebuild must preserve:

* one trade per session;  
* all uploaded evidence;  
* all Gemini requests and responses;  
* all user decisions;  
* all position facts;  
* all monitoring updates;  
* complete chronological history.

The rebuild must not become:

* a generic workflow engine;  
* a generic lifecycle platform;  
* a multi-provider AI router;  
* a generic validation framework;  
* an automated trading system.

---

# **2\. Execution Rules**

## **2.1 One Prompt, One Small Task**

Each coding prompt must have:

* one primary goal;  
* one bounded code area;  
* one expected checkpoint;  
* focused tests only;  
* no unrelated cleanup;  
* no automatic continuation to the next task.

A prompt must not implement an entire Phase.

## **2.2 Required Task Result**

Every task must return:

Status: COMPLETED | BLOCKED

Goal:  
\- ...

Changed:  
\- file: purpose

Tests:  
\- command:  
\- result:

Behavior Verified:  
\- ...

Not Changed:  
\- ...

Git:  
\- starting commit:  
\- final commit:  
\- push:

Safe Next Task:  
\- ...

## **2.3 Stop Conditions**

The agent must stop and return `BLOCKED` when:

* the task requires changing approved product behavior;  
* the task reveals conflicting product requirements;  
* a database change risks existing data;  
* another lifecycle path must be changed unexpectedly;  
* a second unrelated defect appears;  
* the required fix becomes significantly larger than the task;  
* the task requires adding an unapproved abstraction.

The agent must not silently expand scope.

## **2.4 Git Discipline**

Every completed task should normally produce one commit.

Recommended rule:

One task  
→ focused implementation  
→ focused tests  
→ one commit  
→ push

Do not combine multiple rebuild tasks in one commit.

## **2.5 Database Safety**

During rebuild:

* production data must not be mutated;  
* the current P9 smoke environment must remain isolated;  
* rebuild migrations must first run on a disposable database;  
* existing evidence storage must not be deleted;  
* old business tables should remain available until cutover is verified.

---

# **3\. Phase Overview**

| Phase | Purpose |
| ----- | ----- |
| Phase 0 | Freeze old development and establish rebuild checkpoint |
| Phase 1 | Map reusable and obsolete components |
| Phase 2 | Define the simplified rebuild architecture |
| Phase 3 | Create the simplified database model |
| Phase 4 | Build the shared Gemini analysis pipeline |
| Phase 5 | Implement Initial Analysis |
| Phase 6 | Implement BUY, WAIT, and SKIP decisions |
| Phase 7 | Implement WAIT Updates |
| Phase 8 | Implement Position Updates |
| Phase 9 | Implement CLOSE |
| Phase 10 | Build the complete session page |
| Phase 11 | Verify complete end-to-end paths |
| Phase 12 | Cut over and retire old workflow components |

No Phase may begin before its required dependency checkpoint is completed.

---

# **Phase 0 — Freeze and Protect the Existing System**

## **Goal**

Stop extending the old P9 workflow and preserve the current repository state before the rebuild begins.

## **Deliverable**

A tagged, documented, reversible baseline.

---

## **Task P0.1 — Create Rebuild Baseline**

### **Goal**

Create a clean Git checkpoint before rebuild work.

### **Scope**

* verify current branch;  
* verify current commit;  
* verify tracked and untracked changes;  
* preserve uncommitted P9 work safely;  
* create a rebuild branch;  
* create a baseline tag.

### **Suggested Branch**

rebuild/simple-session-v1

### **Suggested Tag**

pre-simple-session-rebuild

### **Acceptance Criteria**

* current `main` remains unchanged;  
* rebuild branch exists;  
* baseline tag exists;  
* no credential is committed;  
* all untracked diagnostic files are preserved;  
* current Docker volumes remain untouched.

### **Must Not Do**

* delete old code;  
* apply new migrations;  
* change application behavior;  
* run Gemini;  
* modify runtime records.

---

## **Task P0.2 — Record Existing Runtime Assets**

### **Goal**

Document technical assets that may be reused.

### **Inspect**

* authentication;  
* user isolation;  
* file upload;  
* evidence storage;  
* Gemini SDK adapter;  
* prompt loading;  
* background worker;  
* job polling;  
* frontend layout;  
* Docker Compose;  
* gateway;  
* PostgreSQL;  
* migrations;  
* existing session page.

### **Output**

Create:

docs/rebuild/EXISTING\_ASSET\_INVENTORY.md

### **For Each Asset Record**

* component name;  
* location;  
* current responsibility;  
* reuse candidate: yes/no/partial;  
* dependency risk;  
* old workflow coupling;  
* recommendation.

### **Acceptance Criteria**

The document describes existing code only. It does not propose new product features.

---

## **Task P0.3 — Record Old Workflow Components**

### **Goal**

Identify existing components that belong to the old architecture.

### **Inspect**

* lifecycle enums;  
* transition services;  
* EvidenceBatch state machine;  
* old analysis types;  
* transport schema registry;  
* canonical normalizers;  
* domain validation;  
* evaluation records;  
* provider routing;  
* Partial Exit;  
* Closing Analysis;  
* old WAIT and SKIP implementations.

### **Output**

Create:

docs/rebuild/OLD\_WORKFLOW\_COMPONENTS.md

### **Classifications**

REUSE  
ADAPT  
BYPASS  
DEPRECATE  
REMOVE\_AFTER\_CUTOVER

### **Acceptance Criteria**

No code is deleted.

---

# **Phase 1 — Rebuild Mapping and Boundaries**

## **Goal**

Determine exactly which existing components will support the new PRD and which components will not control the rebuild.

---

## **Task P1.1 — Create PRD-to-Code Mapping**

### **Goal**

Map every approved PRD requirement to existing or new code ownership.

### **Output**

Create:

docs/rebuild/PRD\_CODE\_MAPPING.md

### **Required Mapping Areas**

* create session;  
* initial evidence upload;  
* Initial Analysis;  
* BUY;  
* WAIT;  
* SKIP;  
* WAIT Update;  
* Position Update;  
* CLOSE;  
* complete history;  
* Gemini integration;  
* worker;  
* session page.

### **For Each Requirement Record**

* PRD requirement;  
* existing implementation;  
* reuse decision;  
* required replacement;  
* migration impact;  
* frontend impact;  
* test requirement.

### **Acceptance Criteria**

Every approved PRD flow has an owner.

No out-of-scope feature is mapped.

---

## **Task P1.2 — Define the Rebuild Module Boundary**

### **Goal**

Define where new business code will live without mixing it with old lifecycle code.

### **Recommended Module Boundary**

Backend example:

backend/app/trade\_workspace/

Frontend example:

frontend/src/features/trade-workspace/

### **Output**

Create:

docs/rebuild/REBUILD\_MODULE\_BOUNDARY.md

### **Define**

* backend package boundary;  
* frontend feature boundary;  
* database table ownership;  
* API prefix;  
* old-code access restrictions;  
* allowed shared infrastructure;  
* prohibited dependencies.

### **Recommended API Prefix**

/api/v2/trade-sessions

### **Acceptance Criteria**

New business code does not depend on the old lifecycle engine.

Shared infrastructure may still be reused.

---

## **Task P1.3 — Define Scope Guardrails**

### **Goal**

Create enforceable rebuild guardrails.

### **Output**

Create:

docs/rebuild/SCOPE\_GUARDRAILS.md

### **Required Rules**

Gemini is the only AI provider.

No provider routing or fallback.

No Partial Exit.

No automated BUY, WAIT, SKIP, or CLOSE.

No generic workflow engine.

No generic schema registry.

No lifecycle state beyond the approved statuses.

No analysis type beyond the approved types.

No feature may be added without explicit product approval.

### **Acceptance Criteria**

The document is short and unambiguous.

---

# **Phase 2 — Simplified Architecture**

## **Goal**

Define the minimum technical architecture needed to support the approved PRD.

---

## **Task P2.1 — Define the Simplified Backend Architecture**

### **Goal**

Document the minimal backend flow.

### **Output**

Create:

docs/rebuild/SIMPLE\_ARCHITECTURE.md

### **Required Components**

* API layer;  
* session service;  
* evidence service;  
* decision service;  
* position service;  
* close service;  
* analysis request service;  
* Gemini adapter;  
* worker;  
* storage;  
* PostgreSQL.

### **Required Flow**

API  
→ persist user input  
→ queue analysis request  
→ worker loads data and files  
→ Gemini request  
→ persist response  
→ expose result to frontend

### **Must Not Include**

* provider router;  
* multi-provider retry;  
* generic state-machine framework;  
* generic transport compiler;  
* evaluation platform.

---

## **Task P2.2 — Define Session Status Rules**

### **Goal**

Define the approved status transitions only.

### **Approved Statuses**

DRAFT  
ANALYZING  
ANALYZED  
WAITING  
OPEN\_POSITION  
CLOSED  
CLOSED\_SKIPPED

Optional request failure must be stored on the analysis request, not necessarily as a permanent session business state.

### **Approved Transitions**

DRAFT → ANALYZING  
ANALYZING → ANALYZED  
ANALYZED → WAITING  
ANALYZED → OPEN\_POSITION  
ANALYZED → CLOSED\_SKIPPED  
WAITING → WAITING  
WAITING → OPEN\_POSITION  
WAITING → CLOSED\_SKIPPED  
OPEN\_POSITION → OPEN\_POSITION  
OPEN\_POSITION → CLOSED

### **Output**

Create:

docs/rebuild/SESSION\_STATUS\_RULES.md

### **Acceptance Criteria**

No other business transition exists.

---

## **Task P2.3 — Define Analysis Types and Input Contracts**

### **Goal**

Define only the approved AI analysis types.

### **Approved Types**

INITIAL\_ANALYSIS  
WAIT\_UPDATE  
POSITION\_UPDATE

### **Output**

Create:

docs/rebuild/ANALYSIS\_INPUT\_CONTRACTS.md

### **Initial Analysis Input**

* ticker;  
* company name;  
* initial note;  
* orderbook image;  
* three-month chart image;  
* six-month chart image.

### **WAIT Update Input**

* observation period;  
* current price;  
* observation timestamp;  
* orderbook image;  
* optional note;  
* Initial Analysis;  
* prior WAIT Updates.

### **Position Update Input**

* observation period;  
* current price;  
* observation timestamp;  
* orderbook image;  
* optional note;  
* confirmed position facts;  
* Initial Analysis;  
* relevant WAIT history;  
* prior Position Updates.

### **Acceptance Criteria**

User-owned and Gemini-owned data are clearly separated.

---

## **Task P2.4 — Define Compact AI Output Contracts**

### **Goal**

Define one compact response structure per approved analysis type.

### **Output Files**

schemas/rebuild/v1/initial\_analysis.schema.json  
schemas/rebuild/v1/wait\_update.schema.json  
schemas/rebuild/v1/position\_update.schema.json

### **Rules**

* one schema is used for Gemini and persistence;  
* no canonical-versus-transport duality;  
* no external `$ref`;  
* no deep composition;  
* only dashboard-required fields;  
* non-critical fields may be nullable or optional;  
* execution facts must not appear as provider-authoritative output.

### **Acceptance Criteria**

Schemas are compatible with Gemini structured output.

No request is sent yet.

---

# **Phase 3 — Simplified Database Model**

## **Goal**

Create clean rebuild tables without deleting old tables.

---

## **Task P3.1 — Add Rebuild Trade Sessions Table**

### **Goal**

Create the new session table.

### **Suggested Table**

trade\_sessions\_v2

### **Required Fields**

* `id`;  
* `user_id`;  
* `ticker`;  
* `company_name`;  
* `status`;  
* `note`;  
* `created_at`;  
* `updated_at`;  
* `closed_at`.

### **Requirements**

* one owner;  
* valid ticker;  
* approved statuses only;  
* indexed by user and status;  
* no dependency on old lifecycle tables.

### **Tests**

* create;  
* read;  
* ownership;  
* status constraint;  
* historical ordering.

---

## **Task P3.2 — Add Analysis Requests Table**

### **Goal**

Create the new analysis request and response table.

### **Suggested Table**

analysis\_requests\_v2

### **Required Fields**

* `id`;  
* `session_id`;  
* `analysis_type`;  
* `observation_period`;  
* `current_price`;  
* `observation_at`;  
* `status`;  
* `provider`;  
* `model`;  
* `prompt_version`;  
* `input_snapshot`;  
* `raw_response`;  
* `processed_response`;  
* `error_code`;  
* `error_message`;  
* `created_at`;  
* `started_at`;  
* `completed_at`.

### **Analysis Statuses**

PENDING  
PROCESSING  
COMPLETED  
FAILED

### **Requirements**

* Initial Analysis does not require current price;  
* WAIT and Position Updates require current price;  
* one request may reference multiple evidence files;  
* no evaluation record required.

---

## **Task P3.3 — Add Evidence Uploads Table**

### **Goal**

Create simple evidence storage references.

### **Suggested Table**

evidence\_uploads\_v2

### **Required Fields**

* `id`;  
* `session_id`;  
* `analysis_request_id`;  
* `evidence_type`;  
* `observation_period`;  
* `file_path`;  
* `original_filename`;  
* `mime_type`;  
* `size_bytes`;  
* `uploaded_at`.

### **Evidence Types**

ORDERBOOK  
CHART\_3\_MONTH  
CHART\_6\_MONTH

### **Requirements**

* immutable after analysis request submission;  
* no batch state machine;  
* evidence can be prepared before an analysis request;  
* exact session ownership enforced.

---

## **Task P3.4 — Add Session Decisions Table**

### **Goal**

Store BUY, WAIT, and SKIP user decisions independently from Gemini recommendations.

### **Suggested Table**

session\_decisions\_v2

### **Required Fields**

* `id`;  
* `session_id`;  
* `decision`;  
* `reason`;  
* `note`;  
* `created_at`.

### **Decisions**

BUY  
WAIT  
SKIP

### **Requirements**

* repeated WAIT records allowed;  
* only one BUY allowed;  
* SKIP only before BUY;  
* no decision may be created by Gemini.

---

## **Task P3.5 — Add Positions Table**

### **Goal**

Store one confirmed position per session.

### **Suggested Table**

positions\_v2

### **Required Fields**

* `id`;  
* `session_id`;  
* `entry_price`;  
* `entry_at`;  
* `quantity`;  
* `stop_loss`;  
* `target_price`;  
* `note`;  
* `status`;  
* `created_at`;  
* `closed_at`.

### **Position Statuses**

OPEN  
CLOSED

### **Requirements**

* one position per session;  
* user-owned facts;  
* created only through BUY;  
* not writable by Gemini.

---

## **Task P3.6 — Add Trade Closures Table**

### **Goal**

Store manual closure data.

### **Suggested Table**

trade\_closures\_v2

### **Required Fields**

* `id`;  
* `session_id`;  
* `position_id`;  
* `close_price`;  
* `close_at`;  
* `close_reason`;  
* `note`;  
* `realized_profit_loss`;  
* `created_at`.

### **Requirements**

* one closure per open position;  
* CLOSE does not require Gemini;  
* session becomes CLOSED after persistence.

---

## **Task P3.7 — Verify Full Migration Chain**

### **Goal**

Verify all new tables on a disposable database.

### **Verification**

* upgrade from current head;  
* new database from zero;  
* rollback of rebuild migrations;  
* historical tables remain untouched;  
* old records remain readable;  
* no production database used.

### **Deliverable**

docs/rebuild/MIGRATION\_VERIFICATION.md

---

# **Phase 4 — Shared Gemini Analysis Pipeline**

## **Goal**

Create one simple pipeline that supports all three analysis types.

---

## **Task P4.1 — Create Gemini-Only Adapter Boundary**

### **Goal**

Expose one explicit Gemini client for the rebuild.

### **Requirements**

* provider hardcoded/configured as Gemini;  
* model from environment;  
* production default `gemini-3.1-flash-lite`;  
* text and image parts supported;  
* structured JSON output supported;  
* no provider router;  
* no fallback.

### **Tests**

* correct model;  
* images included;  
* prompt included;  
* invalid credentials handled;  
* no real request in unit tests.

---

## **Task P4.2 — Create Prompt Loader**

### **Goal**

Load exactly three approved prompts.

### **Prompt Files**

prompts/rebuild/initial\_analysis.md  
prompts/rebuild/wait\_update.md  
prompts/rebuild/position\_update.md

### **Requirements**

* versioned;  
* English implementation instructions;  
* Indonesian output required;  
* concise output;  
* user-owned facts protected;  
* image roles explicitly stated.

---

## **Task P4.3 — Create Analysis Context Builder**

### **Goal**

Build the correct request context for each analysis type.

### **Context Builder Responsibilities**

* load session;  
* verify owner;  
* load evidence;  
* load previous analyses;  
* load position facts when applicable;  
* include user-entered current price;  
* build a bounded history summary;  
* never invent missing facts.

### **Tests**

* Initial context;  
* WAIT context without position;  
* Position context with position;  
* correct images;  
* history ordering;  
* authority fields.

---

## **Task P4.4 — Create Analysis Request Queue Service**

### **Goal**

Create one analysis request with status `PENDING` in `analysis_requests_v2` as the durable database-backed queue source.

### **Backend Submission Flow**

validate ownership, lifecycle eligibility, and evidence
→ reject duplicate active requests
→ create exactly one `analysis_requests_v2` row with status `PENDING`
→ assign selected evidence to the request
→ transition session to `ANALYZING` within transaction boundary
→ commit durable state
→ return HTTP 202

### **Requirements**

* `analysis_requests_v2` is the sole durable queue source;  
* validate ownership, lifecycle eligibility, and evidence;  
* reject duplicate active submissions;  
* create exactly one `analysis_requests_v2` row with status `PENDING`;  
* assign selected evidence to the request;  
* transition session to `ANALYZING` in the approved transaction boundary;  
* commit durable state and return HTTP 202;  
* do not publish to another transport (no Redis, RabbitMQ, external broker, or in-process queue);  
* no hidden retry;  
* no legacy `analysis_jobs` delegation;  
* no session duplication.

---

## **Task P4.5 — Create Worker Processing Flow**

### **Goal**

Process one queued analysis request from `analysis_requests_v2` via worker polling.

### **Worker Flow**

poll `analysis_requests_v2` using configured worker interval  
→ atomically claim one eligible `PENDING` request using PostgreSQL locking  
→ mark `PROCESSING`  
→ build context  
→ call Gemini once  
→ parse JSON  
→ validate critical sections  
→ store raw and processed response  
→ mark `COMPLETED`  
→ transition session to approved resulting status

Failure:

store sanitized error  
→ mark `FAILED`  
→ preserve session, user facts, and request for explicit retry

### **Requirements**

* poll `analysis_requests_v2` at configured worker interval;  
* atomically claim at-most-one request per tick using PostgreSQL locking (prevent concurrent worker processing);  
* one Gemini request (no fallback or automatic retry);  
* durable across backend and worker restarts;  
* no legacy `analysis_jobs` reuse;  
* no external queue infrastructure;  
* terminal status guaranteed (`COMPLETED` or `FAILED`).

---

## **Task P4.6 — Create Compact Response Validation**

### **Goal**

Validate only fields required by the dashboard.

### **Rules**

Critical missing field:

request → FAILED

Non-critical missing field:

response saved  
→ missing display section remains empty or warning shown

### **Must Not Add**

* separate canonical schema;  
* separate transport schema;  
* domain validation framework;  
* evaluation record.

---

# **Phase 5 — Initial Analysis**

## **Goal**

Complete the first user-visible happy path.

---

## **Task P5.1 — Create Session API**

### **Endpoints**

POST /api/v2/trade-sessions  
GET /api/v2/trade-sessions  
GET /api/v2/trade-sessions/{session\_id}

### **Verify**

* ownership;  
* ticker;  
* company name;  
* status `DRAFT`;  
* session detail response.

---

## **Task P5.2 — Create Initial Evidence Upload API**

### **Goal**

Upload the three required evidence types.

### **Verify**

* exact session;  
* file validation;  
* storage;  
* evidence type;  
* duplicate replacement behavior;  
* cross-user access;  
* no Gemini request.

---

## **Task P5.3 — Create Initial Analysis Submission API**

### **Endpoint**

POST /api/v2/trade-sessions/{session\_id}/initial-analysis

### **Behavior**

* require all three evidence files;  
* create one analysis request;  
* set session to `ANALYZING`;  
* queue one request;  
* block duplicate active submission.

---

## **Task P5.4 — Implement Initial Analysis Prompt**

### **Required Output**

* summary;  
* orderbook analysis;  
* three-month chart analysis;  
* six-month chart analysis;  
* support;  
* resistance;  
* entry area;  
* stop recommendation;  
* target recommendation;  
* probabilities;  
* risks;  
* trading plan;  
* conclusion.

### **Authority**

These are recommendations only.

No position is created.

---

## **Task P5.5 — Persist and Complete Initial Analysis**

### **Behavior**

Success:

analysis COMPLETED  
session ANALYZED

Failure:

analysis FAILED  
session returns to DRAFT or preserves retryable state

### **Verify**

* raw response stored;  
* processed response stored;  
* actual model stored;  
* prompt version stored;  
* Indonesian output;  
* files remain linked.

---

## **Task P5.6 — Build Initial Analysis Frontend**

### **UI**

* create session;  
* initial upload form;  
* upload progress;  
* Submit button;  
* processing state;  
* completed analysis sections;  
* readable failure state;  
* manual retry.

### **Acceptance**

The complete initial flow works through the browser.

---

# **Phase 6 — BUY, WAIT, and SKIP**

## **Goal**

Implement only user-controlled post-analysis decisions.

---

## **Task P6.1 — Add Decision Availability API**

### **Goal**

Expose valid actions based on session status.

### **Rules**

For `ANALYZED`:

BUY  
WAIT  
SKIP

For `WAITING`:

BUY  
WAIT  
SKIP

For `OPEN_POSITION`:

CLOSE

For closed sessions:

none

---

## **Task P6.2 — Implement WAIT Decision**

### **Endpoint**

POST /api/v2/trade-sessions/{session\_id}/decisions/wait

### **Behavior**

* store WAIT decision;  
* set session `WAITING`;  
* create no position;  
* call no Gemini request;  
* expose WAIT Update form.

---

## **Task P6.3 — Implement SKIP Decision**

### **Endpoint**

POST /api/v2/trade-sessions/{session\_id}/decisions/skip

### **Input**

* skip reason;  
* optional note.

### **Behavior**

* store SKIP;  
* create no position;  
* set session `CLOSED_SKIPPED`;  
* set closed timestamp;  
* disable uploads;  
* call no Gemini request.

---

## **Task P6.4 — Implement BUY Decision**

### **Endpoint**

POST /api/v2/trade-sessions/{session\_id}/decisions/buy

### **Input**

* entry price;  
* entry timestamp;  
* quantity;  
* stop loss;  
* target price;  
* optional note.

### **Behavior**

* store BUY decision;  
* create one position;  
* set session `OPEN_POSITION`;  
* call no Gemini request.

---

## **Task P6.5 — Build Decision UI**

### **UI for `ANALYZED` and `WAITING`**

Buttons:

BUY  
WAIT  
SKIP

### **Forms**

* BUY modal;  
* SKIP confirmation;  
* WAIT confirmation.

### **Verify**

* no hidden AI call;  
* correct status;  
* buttons disabled after final decision;  
* position shown only after BUY.

---

# **Phase 7 — WAIT Updates**

## **Goal**

Allow repeated pre-entry analysis without a position.

---

## **Task P7.1 — Create WAIT Update Input API**

### **Required Input**

* observation period;  
* current price;  
* observation timestamp;  
* orderbook screenshot;  
* optional note.

### **Conditions**

* session status must be `WAITING`;  
* no position may exist;  
* current price required;  
* orderbook required.

---

## **Task P7.2 — Create WAIT Update Submission**

### **Endpoint**

POST /api/v2/trade-sessions/{session\_id}/wait-updates

### **Behavior**

* persist input;  
* persist image;  
* create `WAIT_UPDATE`;  
* queue one Gemini request;  
* session remains `WAITING`;  
* prevent duplicate active request.

---

## **Task P7.3 — Implement WAIT Update Prompt**

### **Context**

* ticker;  
* company name;  
* current price;  
* latest orderbook;  
* Initial Analysis;  
* previous WAIT Updates;  
* period;  
* optional note.

### **Required Output**

* update summary;  
* current price;  
* orderbook assessment;  
* change from previous analysis;  
* current entry condition;  
* upside probability;  
* downside probability;  
* key risks;  
* whether to BUY, WAIT, or SKIP;  
* next plan;  
* conclusion.

Gemini recommendation is non-authoritative.

---

## **Task P7.4 — Persist WAIT Update Results**

### **Verify**

* new analysis record;  
* earlier updates unchanged;  
* session remains `WAITING`;  
* no position created;  
* user decisions remain separate;  
* Indonesian output.

---

## **Task P7.5 — Build WAIT Update Frontend**

### **UI**

* observation period;  
* current price;  
* orderbook upload;  
* observation time;  
* note;  
* submit;  
* processing state;  
* chronological WAIT timeline;  
* BUY/WAIT/SKIP remains available.

---

# **Phase 8 — Position Updates**

## **Goal**

Allow repeated analysis while one confirmed position is open.

---

## **Task P8.1 — Create Position Update Input API**

### **Required Input**

* observation period;  
* current price;  
* observation timestamp;  
* orderbook screenshot;  
* optional note.

### **Conditions**

* session `OPEN_POSITION`;  
* one open position exists;  
* current price required;  
* orderbook required.

---

## **Task P8.2 — Create Position Update Submission**

### **Endpoint**

POST /api/v2/trade-sessions/{session\_id}/position-updates

### **Behavior**

* persist input and image;  
* create `POSITION_UPDATE`;  
* queue exactly one Gemini request;  
* session remains `OPEN_POSITION`;  
* position facts remain unchanged.

---

## **Task P8.3 — Implement Position Update Prompt**

### **Context**

* ticker;  
* company name;  
* user-entered current price;  
* latest orderbook image;  
* period;  
* entry price;  
* entry timestamp;  
* quantity;  
* stop loss;  
* target price;  
* Initial Analysis;  
* relevant WAIT history;  
* prior Position Updates.

### **Required Output**

* update summary;  
* current price;  
* position condition;  
* orderbook assessment;  
* change from previous analysis;  
* target realism;  
* downside risk;  
* target probability;  
* trading plan;  
* monitoring points;  
* warnings;  
* conclusion.

### **Authority Rule**

Gemini cannot change position facts.

---

## **Task P8.4 — Persist Position Update Results**

### **Verify**

* one new analysis record;  
* accepted output stored;  
* model and prompt version stored;  
* previous analyses unchanged;  
* session remains `OPEN_POSITION`;  
* position remains open.

---

## **Task P8.5 — Build Position Update Frontend**

### **UI**

* position summary;  
* update form;  
* timeline;  
* current price;  
* period;  
* analysis sections;  
* CLOSE button;  
* no BUY/WAIT/SKIP buttons.

---

# **Phase 9 — CLOSE**

## **Goal**

Allow the user to close a confirmed open position without Gemini dependency.

---

## **Task P9.1 — Create CLOSE API**

### **Endpoint**

POST /api/v2/trade-sessions/{session\_id}/close

### **Required Input**

* close price;  
* close timestamp;  
* close reason.

### **Optional**

* note.

### **Behavior**

* validate open position;  
* create closure record;  
* calculate realized result;  
* mark position `CLOSED`;  
* mark session `CLOSED`;  
* disable further updates.

No Gemini request.

---

## **Task P9.2 — Verify Close Calculations**

### **Verify**

* realized price difference;  
* percentage result;  
* quantity handling;  
* decimal precision;  
* timezone;  
* no position overwrite;  
* one closure only.

---

## **Task P9.3 — Build CLOSE Frontend**

### **UI**

* CLOSE button;  
* confirmation form;  
* close price;  
* close time;  
* reason;  
* optional note;  
* result summary.

### **Verify**

* session becomes closed;  
* forms disabled;  
* history remains visible.

---

# **Phase 10 — Complete Session Page**

## **Goal**

Provide one page containing the complete trade story.

---

## **Task P10.1 — Create Session Detail Aggregate API**

### **Response Sections**

* session;  
* initial evidence;  
* Initial Analysis;  
* decisions;  
* WAIT Updates;  
* position;  
* Position Updates;  
* closure.

### **Requirements**

* chronological;  
* ownership-safe;  
* no old workflow records;  
* efficient bounded queries.

---

## **Task P10.2 — Build Session Header and Status Display**

### **Display**

* ticker;  
* company name;  
* current status;  
* created time;  
* latest update;  
* closed time;  
* active decision state.

---

## **Task P10.3 — Build Chronological Timeline**

### **Timeline Items**

* initial evidence uploaded;  
* Initial Analysis;  
* WAIT decision;  
* WAIT Update;  
* BUY decision;  
* Position Update;  
* SKIP decision;  
* CLOSE.

### **Requirements**

* oldest to newest or clear reversible order;  
* no overwritten analysis;  
* readable Indonesian labels.

---

## **Task P10.4 — Build Status-Based Action Panel**

### **Rules**

* DRAFT: initial upload;  
* ANALYZING: processing indicator;  
* ANALYZED: BUY / WAIT / SKIP;  
* WAITING: WAIT form \+ BUY / SKIP;  
* OPEN\_POSITION: update form \+ CLOSE;  
* CLOSED: read-only;  
* CLOSED\_SKIPPED: read-only.

---

## **Task P10.5 — Build Failure and Retry UI**

### **Behavior**

* failed analysis shown clearly;  
* evidence preserved;  
* user input preserved;  
* manual retry;  
* no duplicate request;  
* no status corruption.

---

# **Phase 11 — End-to-End Verification**

## **Goal**

Prove the exact approved product paths in a production-like environment.

Each path must be a separate task and separate prompt.

---

## **Task P11.1 — Verify Direct BUY Path**

### **Path**

Create  
→ Initial Analysis  
→ BUY  
→ Position Update  
→ CLOSE

### **Real Gemini Requests**

* one Initial Analysis;  
* one Position Update.

### **Verify**

* files sent;  
* responses stored;  
* Indonesian output;  
* user facts preserved;  
* session closes.

---

## **Task P11.2 — Verify WAIT Then BUY Path**

### **Path**

Create  
→ Initial Analysis  
→ WAIT  
→ WAIT Update  
→ BUY  
→ Position Update  
→ CLOSE

### **Real Gemini Requests**

* one Initial Analysis;  
* one WAIT Update;  
* one Position Update.

---

## **Task P11.3 — Verify WAIT Then SKIP Path**

### **Path**

Create  
→ Initial Analysis  
→ WAIT  
→ WAIT Update  
→ SKIP

### **Verify**

* no position;  
* status `CLOSED_SKIPPED`;  
* history preserved;  
* no further uploads.

---

## **Task P11.4 — Verify Direct SKIP Path**

### **Path**

Create  
→ Initial Analysis  
→ SKIP

### **Verify**

* no position;  
* no close price;  
* skip reason stored;  
* session read-only.

---

## **Task P11.5 — Verify Multiple Updates**

### **Goal**

Verify repeated update behavior.

### **Scenarios**

* multiple WAIT Updates;  
* Morning, Midday, Afternoon;  
* multiple Position Updates;  
* chronological ordering;  
* no overwritten evidence;  
* no duplicate request.

---

## **Task P11.6 — Verify Failure Recovery**

### **Cases**

* invalid image;  
* Gemini error;  
* malformed Gemini response;  
* interrupted worker;  
* manual retry;  
* duplicate submit;  
* frontend refresh during processing.

### **Verify**

* user data preserved;  
* no duplicate lifecycle action;  
* session remains usable.

---

# **Phase 12 — Cutover and Cleanup**

## **Goal**

Switch the application to the rebuilt workflow and remove obsolete code only after verification.

---

## **Task P12.1 — Add Rebuild Feature Switch**

### **Goal**

Allow controlled routing to the new workflow.

### **Requirements**

* environment-controlled;  
* default safe;  
* old system remains available during verification;  
* no data mixing.

---

## **Task P12.2 — Switch Frontend to V2 APIs**

### **Goal**

Move session creation and session detail to the rebuild flow.

### **Verify**

* no old lifecycle call;  
* no old EvidenceBatch API;  
* no provider router dependency;  
* all approved paths work.

---

## **Task P12.3 — Mark Old APIs Deprecated**

### **Goal**

Prevent new usage of old business endpoints.

### **Behavior**

* documentation warning;  
* optional read-only access;  
* no new old-workflow sessions;  
* existing historical records preserved.

---

## **Task P12.4 — Remove Old Frontend Workflow**

### **Remove or Disable**

* old lifecycle controls;  
* Partial Exit UI;  
* old analysis types;  
* old batch controls;  
* provider selection;  
* unused polling loops.

### **Verify**

New workflow remains complete.

---

## **Task P12.5 — Remove Unused Backend Business Components**

This task must be split further by component.

Possible separate tasks:

P12.5a — remove Partial Exit routes  
P12.5b — remove old Closing Analysis requirement  
P12.5c — remove unused provider routing  
P12.5d — remove old transport registry  
P12.5e — remove unused canonical normalizers  
P12.5f — remove old lifecycle transitions  
P12.5g — remove obsolete evaluation flow

Each removal must have focused dependency tests.

Do not remove multiple subsystems in one prompt.

---

## **Task P12.6 — Final Production-Like Acceptance**

### **Goal**

Run one complete clean session after cutover.

### **Required Path**

Initial Analysis  
→ WAIT  
→ WAIT Update  
→ BUY  
→ Position Update  
→ CLOSE

### **Verify**

* correct images sent;  
* Gemini only;  
* all data stored;  
* no old workflow dependency;  
* session complete;  
* database and storage preserved;  
* frontend shows full history.

---

# **4\. Recommended Prompt Sequence**

The recommended execution sequence is:

P0.1  
P0.2  
P0.3

P1.1  
P1.2  
P1.3

P2.1  
P2.2  
P2.3  
P2.4

P3.1  
P3.2  
P3.3  
P3.4  
P3.5  
P3.6  
P3.7

P4.1  
P4.2  
P4.3  
P4.4  
P4.5  
P4.6

P5.1  
P5.2  
P5.3  
P5.4  
P5.5  
P5.6

P6.1  
P6.2  
P6.3  
P6.4  
P6.5

P7.1  
P7.2  
P7.3  
P7.4  
P7.5

P8.1  
P8.2  
P8.3  
P8.4  
P8.5

P9.1  
P9.2  
P9.3

P10.1  
P10.2  
P10.3  
P10.4  
P10.5

P11.1  
P11.2  
P11.3  
P11.4  
P11.5  
P11.6

P12.1  
P12.2  
P12.3  
P12.4  
P12.5a–P12.5g  
P12.6

---

# **5\. Phase Gates**

## **Gate A — Architecture Approved**

Required before Phase 3:

* P0 completed;  
* PRD mapping completed;  
* module boundary approved;  
* scope guardrails approved;  
* simplified architecture approved.

## **Gate B — Database Ready**

Required before Phase 4:

* all V2 tables created;  
* migrations verified;  
* ownership verified;  
* old tables untouched.

## **Gate C — Gemini Pipeline Ready**

Required before Phase 5:

* Gemini-only adapter;  
* prompts;  
* context builder;  
* queue;  
* worker;  
* compact validation.

## **Gate D — Initial Analysis Ready**

Required before decisions:

* one real Initial Analysis completes;  
* three images reach Gemini;  
* response stored;  
* Indonesian output displayed.

## **Gate E — Decisions Ready**

Required before WAIT and Position Update:

* BUY works;  
* WAIT works;  
* SKIP works;  
* no decision triggers Gemini automatically.

## **Gate F — Full Workflow Ready**

Required before cutover:

* Direct BUY path passes;  
* WAIT then BUY passes;  
* WAIT then SKIP passes;  
* Direct SKIP passes;  
* CLOSE passes;  
* repeated updates pass.

## **Gate G — Cleanup Allowed**

Old workflow code may only be removed after Gate F passes.

---

# **6\. Token and Time Efficiency Rules**

To keep agent usage efficient:

1. Do not ask the agent to reread the entire repository on every task.  
2. Each task prompt should list the exact files or module area to inspect.  
3. Reuse previous task checkpoints.  
4. Run focused tests only.  
5. Do not run full test suites until a Phase gate.  
6. Do not rebuild the full Docker stack for offline tasks.  
7. Do not make real Gemini requests during implementation tasks.  
8. Real Gemini requests occur only during explicit end-to-end tasks.  
9. Do not request large reports after every task.  
10. Use compact result templates.  
11. One task should normally create one commit.  
12. Stop after the requested acceptance criteria pass.

---

# **7\. Recommended First Tasks**

The rebuild should begin with:

P0.1 — Create Rebuild Baseline  
P0.2 — Record Existing Runtime Assets  
P0.3 — Record Old Workflow Components  
P1.1 — Create PRD-to-Code Mapping

Do not begin database or implementation work before these four tasks establish what can safely be reused.

---

# **8\. Final Rebuild Rule**

The approved PRD defines the product.

Existing code does not define the product.

Existing components may be reused only when they directly support the approved  
PRD without importing unnecessary workflow complexity.

No scope expansion may be implemented without explicit product-owner approval.

