# **IMPLEMENTATION\_PLAN.md**

## **TradePilot AI Implementation Plan**

**Document Version:** 1.0  
**Status:** Ready for Implementation  
**Target:** MVP Production Release  
**Deployment Model:** Single VPS  
**Source Control:** GitHub  
**Primary Development Environment:** Local machine  
**Frontend:** Next.js with TypeScript  
**Backend API:** FastAPI with Python  
**Database:** PostgreSQL  
**Background Processing:** Python worker  
**AI Providers:** Gemini and DeepSeek  
**User-Facing Analysis Language:** Indonesian  
**Engineering Language:** English

---

## **1\. Purpose**

This document defines the implementation sequence for TradePilot AI.

The plan converts the completed product and engineering specifications into an ordered development roadmap covering:

* repository setup;  
* infrastructure foundation;  
* database implementation;  
* production JSON Schemas;  
* schema registry;  
* domain validation;  
* lifecycle management;  
* evidence upload;  
* AI provider integration;  
* background analysis jobs;  
* context-memory generation;  
* Trade Session APIs;  
* user confirmation workflows;  
* frontend implementation;  
* testing;  
* VPS deployment;  
* MVP acceptance.

The system should be implemented incrementally.

Each phase must produce a usable and testable foundation for the next phase.

---

## **2\. Product Objective**

TradePilot AI is an AI Trading Workspace that follows one stock trade from initial observation until the position is closed.

The product is not an automatic signal generator.

Its primary role is to act as an AI Trading Analyst that:

1. receives user-provided evidence;  
2. analyzes one ticker in one dedicated Trade Session;  
3. builds an initial trading thesis;  
4. tracks the setup before entry;  
5. follows an open position longitudinally;  
6. compares each update with prior evidence and analysis;  
7. evaluates target and downside probabilities;  
8. proposes trading actions;  
9. preserves user-confirmed trade facts;  
10. produces a final review after the trade closes.

The product principle is:

One Trade, One Story.

---

## **3\. MVP Scope**

The MVP includes:

* user authentication for one primary user or a small private user set;  
* Trade Session creation;  
* one ticker per session;  
* evidence upload;  
* orderbook screenshot support;  
* three-month chart support;  
* six-month chart support;  
* initial analysis;  
* watching updates;  
* position opening confirmation;  
* Open Position updates;  
* stop-loss confirmation and revision;  
* target confirmation and revision;  
* partial-exit confirmation;  
* final-exit confirmation;  
* closing analysis;  
* context-memory generation;  
* Gemini integration;  
* DeepSeek fallback;  
* structured JSON output validation;  
* complete session timeline;  
* Indonesian user-facing analysis;  
* local and VPS operation.

The MVP does not include:

* broker integration;  
* automatic order execution;  
* portfolio allocation;  
* automatic live orderbook feeds;  
* automated trading signals across many tickers;  
* social or multi-tenant collaboration;  
* mobile application;  
* real-time streaming market data;  
* short selling;  
* options or futures;  
* public SaaS billing.

---

## **4\. Implementation Principles**

### **4.1 Build vertically**

Each phase should connect database, backend, and frontend where practical.

Avoid completing the entire backend before testing actual user flows.

### **4.2 Canonical state first**

User-confirmed Trade State must be implemented before AI recommendations can be trusted.

### **4.3 AI output is untrusted**

All provider output must pass:

1. JSON parsing;  
2. JSON Schema validation;  
3. domain validation;  
4. canonical-state validation;  
5. lifecycle validation.

### **4.4 Deterministic calculations belong to the backend**

The backend owns:

* profit and loss;  
* return percentages;  
* position quantities;  
* distance to stop;  
* distance to target;  
* risk-reward ratio;  
* weighted average exit;  
* holding duration.

### **4.5 AI recommendations require confirmation**

The AI may recommend:

* enter;  
* hold;  
* change stop;  
* change target;  
* partial exit;  
* full exit.

The system must not apply these changes automatically.

### **4.6 Context must remain compact and traceable**

The AI should receive:

* canonical Trade State;  
* latest accepted analysis;  
* compact historical context;  
* new evidence;  
* important confirmed actions.

It should not receive every full historical payload unnecessarily.

---

## **5\. Target Repository Structure**

Recommended monorepo:

tradepilot-ai/  
├── README.md  
├── .env.example  
├── .gitignore  
├── docker-compose.yml  
├── Makefile  
│  
├── docs/  
│   ├── PRD.md  
│   ├── USER\_FLOWS.md  
│   ├── UX\_UI\_SPEC.md  
│   ├── ARCHITECTURE.md  
│   ├── DOMAIN\_MODEL.md  
│   ├── SESSION\_LIFECYCLE.md  
│   ├── DATABASE\_SCHEMA.md  
│   ├── AI\_ANALYSIS\_SPEC.md  
│   ├── THESIS\_ENGINE\_SPEC.md  
│   ├── CONTEXT\_MEMORY\_SPEC.md  
│   ├── PROBABILITY\_CONFIDENCE\_SPEC.md  
│   ├── AI\_PROVIDER\_SPEC.md  
│   ├── ANALYSIS\_SCHEMA\_SPEC.md  
│   ├── SCHEMA\_VALIDATION\_SPEC.md  
│   ├── DOMAIN\_VALIDATION\_RULES.md  
│   ├── SCHEMA\_TEST\_FIXTURES\_SPEC.md  
│   ├── IMPLEMENTATION\_PLAN.md  
│   └── OPEN\_CODE\_TASKS.md  
│  
├── schemas/  
│   └── production/  
│       └── v1/  
│           ├── common.schema.json  
│           ├── market\_snapshot.schema.json  
│           ├── trade\_state.schema.json  
│           ├── evidence.schema.json  
│           ├── initial\_analysis.schema.json  
│           ├── watching\_update.schema.json  
│           ├── open\_position\_update.schema.json  
│           ├── partial\_exit\_review.schema.json  
│           ├── closing\_analysis.schema.json  
│           ├── context\_summary.schema.json  
│           └── manifest.json  
│  
├── backend/  
│   ├── pyproject.toml  
│   ├── alembic.ini  
│   ├── app/  
│   │   ├── main.py  
│   │   ├── config.py  
│   │   ├── logging.py  
│   │   │  
│   │   ├── api/  
│   │   │   ├── dependencies.py  
│   │   │   ├── errors.py  
│   │   │   └── routes/  
│   │   │  
│   │   ├── auth/  
│   │   ├── database/  
│   │   ├── models/  
│   │   ├── repositories/  
│   │   ├── services/  
│   │   ├── schemas/  
│   │   ├── validation/  
│   │   ├── lifecycle/  
│   │   ├── evidence/  
│   │   ├── ai/  
│   │   ├── context/  
│   │   ├── jobs/  
│   │   ├── storage/  
│   │   └── monitoring/  
│   │  
│   ├── migrations/  
│   └── tests/  
│  
├── worker/  
│   ├── pyproject.toml  
│   ├── app/  
│   │   ├── main.py  
│   │   ├── consumers/  
│   │   ├── processors/  
│   │   └── health.py  
│   └── tests/  
│  
├── frontend/  
│   ├── package.json  
│   ├── next.config.ts  
│   ├── tsconfig.json  
│   ├── src/  
│   │   ├── app/  
│   │   ├── components/  
│   │   ├── features/  
│   │   ├── lib/  
│   │   ├── hooks/  
│   │   ├── types/  
│   │   └── test/  
│   └── public/  
│  
├── scripts/  
│   ├── bootstrap.sh  
│   ├── validate\_schemas.py  
│   ├── validate\_fixtures.py  
│   ├── seed\_dev\_data.py  
│   └── backup\_database.sh  
│  
└── infra/  
    ├── nginx/  
    ├── systemd/  
    ├── docker/  
    └── deploy/

---

## **6\. Delivery Phases**

The recommended implementation contains 12 phases.

Phase 0  — Repository and local environment  
Phase 1  — Database and core domain model  
Phase 2  — Production schema package  
Phase 3  — Schema registry and validation  
Phase 4  — Trade Session lifecycle  
Phase 5  — Evidence upload and storage  
Phase 6  — AI provider abstraction  
Phase 7  — Analysis worker and job pipeline  
Phase 8  — Context memory  
Phase 9  — Backend APIs  
Phase 10 — Frontend Trade Session workspace  
Phase 11 — End-to-end testing and hardening  
Phase 12 — VPS deployment and MVP release

---

# **Phase 0 — Repository and Local Environment**

## **7\. Objectives**

Create a reproducible development environment and initial repository structure.

## **8\. Tasks**

### **8.1 Initialize Git repository**

Create:

git init

Add:

* main branch;  
* development branch if desired;  
* `.gitignore`;  
* initial README;  
* GitHub remote.

### **8.2 Create monorepo folders**

Create:

* `backend`;  
* `worker`;  
* `frontend`;  
* `schemas`;  
* `docs`;  
* `scripts`;  
* `infra`.

### **8.3 Configure Python projects**

Use a supported Python release, preferably Python 3.12.

Backend dependencies should initially include:

fastapi  
uvicorn  
pydantic  
pydantic-settings  
sqlalchemy  
asyncpg  
alembic  
psycopg  
jsonschema  
referencing  
python-multipart  
httpx  
tenacity  
structlog  
pytest  
pytest-asyncio  
hypothesis

### **8.4 Configure frontend**

Initialize Next.js with:

* TypeScript;  
* App Router;  
* ESLint;  
* Tailwind CSS;  
* server and client component conventions.

### **8.5 Configure PostgreSQL**

Use Docker Compose locally.

Initial services:

postgres  
backend  
worker  
frontend

Redis may be added if selected as the job transport.

### **8.6 Add environment configuration**

Create `.env.example` containing placeholders for:

DATABASE\_URL  
APP\_ENV  
APP\_SECRET\_KEY  
GEMINI\_API\_KEY  
DEEPSEEK\_API\_KEY  
AI\_PRIMARY\_PROVIDER  
AI\_FALLBACK\_PROVIDER  
UPLOAD\_STORAGE\_PATH  
PUBLIC\_APP\_URL  
LOG\_LEVEL

Never commit actual secrets.

### **8.7 Configure formatting and linting**

Python:

* Ruff;  
* MyPy;  
* Pytest.

TypeScript:

* ESLint;  
* Prettier;  
* TypeScript strict mode.

### **8.8 Add standard commands**

Recommended Makefile commands:

make install  
make dev  
make backend  
make worker  
make frontend  
make test  
make lint  
make migrate  
make seed  
make validate-schemas  
make validate-fixtures

---

## **9\. Deliverables**

* repository boots locally;  
* backend health endpoint works;  
* worker process starts;  
* frontend home page loads;  
* PostgreSQL connection succeeds;  
* environment configuration is documented.

## **10\. Acceptance Criteria**

* a new developer can start the stack using documented commands;  
* no secrets are committed;  
* lint and basic tests run;  
* all applications expose health status.

---

# **Phase 1 — Database and Core Domain Model**

## **11\. Objectives**

Implement the persistence model and canonical trade entities.

## **12\. Database Tables**

Implement the schema defined in `DATABASE_SCHEMA.md` and `DATABASE_SCHEMA.sql`.

Core tables should include:

users  
trade\_sessions  
trade\_states  
trade\_actions  
evidence\_items  
analysis\_jobs  
analyses  
analysis\_validation\_attempts  
context\_summaries  
session\_events  
schema\_versions

Optional supporting tables:

provider\_requests  
provider\_responses  
uploaded\_files  
application\_settings

---

## **13\. Canonical Data Responsibilities**

### **13.1 `trade_sessions`**

Stores:

* user;  
* ticker;  
* company name;  
* exchange;  
* currency;  
* status;  
* timestamps.

### **13.2 `trade_states`**

Stores the latest canonical state:

* position status;  
* entry;  
* quantity;  
* remaining quantity;  
* stop;  
* target;  
* realized result;  
* average exit;  
* thesis status where canonical.

### **13.3 `trade_actions`**

Stores every user-confirmed change:

* position opened;  
* stop confirmed;  
* stop changed;  
* target confirmed;  
* target changed;  
* partial exit;  
* full exit;  
* session cancelled.

### **13.4 `analyses`**

Stores:

* raw provider response;  
* parsed payload;  
* validated payload;  
* schema version;  
* provider;  
* model;  
* status.

### **13.5 `analysis_jobs`**

Stores:

* requested analysis type;  
* lifecycle state before job;  
* job status;  
* attempt count;  
* error state;  
* worker lease.

### **13.6 `context_summaries`**

Stores the latest compact memory and historical versions if required.

---

## **14\. Database Constraints**

Implement database-level constraints for:

* positive prices;  
* nonnegative quantities;  
* unique IDs;  
* valid session ownership;  
* one current Trade State per session;  
* remaining quantity not negative;  
* unique action idempotency keys;  
* unique accepted analysis ordering where relevant.

Not all lifecycle rules should be database constraints; some belong in services.

---

## **15\. Repository Layer**

Create repositories for:

TradeSessionRepository  
TradeStateRepository  
TradeActionRepository  
EvidenceRepository  
AnalysisJobRepository  
AnalysisRepository  
ContextSummaryRepository  
SessionEventRepository

Repositories should not contain business-policy decisions.

---

## **16\. Service Layer**

Create initial services:

TradeSessionService  
TradeStateService  
TradeActionService  
AnalysisJobService

All canonical state changes must go through services, not direct route-level database updates.

---

## **17\. Deliverables**

* Alembic migrations;  
* SQLAlchemy models;  
* repository interfaces;  
* service skeletons;  
* development seed script;  
* database tests.

## **18\. Acceptance Criteria**

* migrations run on an empty database;  
* migrations can be rolled back in development;  
* one Trade Session can be created;  
* a canonical Trade State is created with it;  
* confirmed actions can be stored idempotently;  
* transaction rollback works on invalid state changes.

---

# **Phase 2 — Production Schema Package**

## **19\. Objectives**

Materialize all completed schemas as actual files and ensure the package is internally consistent.

## **20\. Tasks**

Create:

schemas/production/v1/

Add all 10 JSON Schemas and `manifest.json`.

### **20.1 Audit common definitions**

Before coding validators, verify every referenced `$defs` entry exists in `common.schema.json`.

Particular attention should be paid to definitions such as:

uuidArray  
nullableNarrative  
nullableQuantity  
nullableNonNegativeInteger  
nullableConfidenceScore  
warningsAndMissingInformation  
closingReason  
sessionStatus  
positionHealth  
setupQuality  
recommendedAction  
materialChangeArray

Any missing definition must be added before schema compilation.

### **20.2 Audit schema identifiers**

Verify:

* every `$id` is unique;  
* every `$id` matches the manifest;  
* every schema uses the same production base URI;  
* version naming is consistent.

### **20.3 Validate JSON syntax**

Every file must parse as valid JSON.

### **20.4 Validate reference graph**

All `$ref` values must resolve locally.

### **20.5 Add schema package tests**

Tests should verify:

* manifest loads;  
* every active file exists;  
* every schema compiles;  
* no network resolution is attempted;  
* dependency graph has no cycle that breaks resolution.

---

## **21\. Deliverables**

* complete production schema directory;  
* corrected common definitions;  
* schema registry fixture;  
* schema compilation test.

## **22\. Acceptance Criteria**

* all schemas compile under Draft 2020-12;  
* zero unresolved references;  
* manifest and file versions match;  
* startup can fail clearly if a schema is missing.

---

# **Phase 3 — Schema Registry and Validation**

## **23\. Objectives**

Implement the validation foundation described in:

* `SCHEMA_VALIDATION_SPEC.md`;  
* `DOMAIN_VALIDATION_RULES.md`;  
* `SCHEMA_TEST_FIXTURES_SPEC.md`.

---

## **24\. Schema Registry**

Implement:

SchemaManifestLoader  
SchemaRegistry  
SchemaResourceResolver  
CompiledValidatorCache

Required capabilities:

* load schema by name and version;  
* resolve schema by analysis type;  
* resolve `$ref` locally;  
* reject inactive schemas;  
* retain older versions later;  
* expose registry health.

---

## **25\. JSON Schema Validation**

Implement:

JsonSchemaValidationService  
SchemaErrorNormalizer  
JsonPointerBuilder

Validation output must use stable issue codes and paths.

---

## **26\. Domain Validators**

Implement in priority order.

### **Priority A**

* Market Snapshot;  
* Trade State;  
* position calculations;  
* canonical entry;  
* canonical quantity;  
* active stop;  
* active target.

### **Priority B**

* initial entry plan;  
* stop plan;  
* target plan;  
* risk-reward;  
* Open Position assessment.

### **Priority C**

* partial exit;  
* weighted average exit;  
* closing result;  
* context summary;  
* lifecycle.

### **Priority D**

* probability consistency;  
* narrative warnings;  
* evidence staleness;  
* historical context warnings.

---

## **27\. Deterministic Calculation Service**

Create:

PositionCalculationService  
ExitCalculationService  
MarketCalculationService  
HoldingDurationService

Use Decimal arithmetic.

The service must own:

* unrealized P/L;  
* realized P/L;  
* return percentages;  
* weighted average exits;  
* distances;  
* risk-reward.

---

## **28\. Fixture Suite**

Implement Phase 1 fixtures from `SCHEMA_TEST_FIXTURES_SPEC.md` first.

At minimum:

* valid manifest;  
* valid Market Snapshot;  
* valid watching Trade State;  
* valid open Trade State;  
* valid partial Trade State;  
* valid closed Trade State;  
* valid Open Position update;  
* entry mismatch;  
* quantity mismatch;  
* stop mismatch;  
* target mismatch;  
* valid partial exit;  
* valid closing result.

---

## **29\. Deliverables**

* schema registry;  
* compiled validators;  
* normalized validation errors;  
* calculation services;  
* initial domain validators;  
* fixture runner;  
* CI schema tests.

## **30\. Acceptance Criteria**

* invalid AI payload cannot become accepted analysis;  
* canonical conflicts are detected;  
* calculations are deterministic;  
* fixture test command succeeds;  
* validation errors contain stable code and JSON Pointer path.

---

# **Phase 4 — Trade Session Lifecycle**

## **31\. Objectives**

Implement the complete session-state machine and user-confirmed actions.

---

## **32\. Lifecycle State Machine**

Implement states:

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

## **33\. Lifecycle Service**

Create:

SessionLifecycleService

Responsibilities:

* validate allowed transitions;  
* preserve previous status during analysis jobs;  
* require user confirmation;  
* reject invalid transitions;  
* write session events;  
* update Trade State atomically.

---

## **34\. User Action Commands**

Implement commands:

CreateTradeSession  
MarkSessionReady  
ConfirmPositionOpened  
ConfirmStopLoss  
ChangeStopLoss  
ConfirmTarget  
ChangeTarget  
ConfirmPartialExit  
ConfirmFullExit  
CancelSession  
ArchiveSession

Each command must:

1. validate current state;  
2. validate inputs;  
3. create a confirmed action;  
4. update Trade State;  
5. update session status;  
6. emit session event;  
7. trigger Context Summary rebuild.

---

## **35\. Idempotency**

Every action endpoint must accept an idempotency key.

Repeated requests must not create duplicate actions.

---

## **36\. Deliverables**

* lifecycle transition implementation;  
* command services;  
* state transition tests;  
* idempotency support;  
* session-event history.

## **37\. Acceptance Criteria**

* AI cannot change lifecycle directly;  
* duplicate confirmation is safe;  
* partial exit correctly updates remaining quantity;  
* full exit sets quantity to zero;  
* closed sessions cannot reopen.

---

# **Phase 5 — Evidence Upload and Storage**

## **38\. Objectives**

Allow users to upload screenshots and notes safely.

---

## **39\. Evidence Types**

Support:

ORDERBOOK\_SCREENSHOT  
CHART\_3\_MONTH  
CHART\_6\_MONTH  
CHART\_OTHER  
MARKET\_SCREENSHOT  
USER\_NOTE  
POSITION\_OPEN\_CONFIRMATION  
PARTIAL\_EXIT\_CONFIRMATION  
EXIT\_CONFIRMATION

Confirmation evidence may be represented by structured actions rather than file uploads, but both must be linked consistently.

---

## **40\. File Storage**

For MVP VPS deployment, use local filesystem storage.

Recommended structure:

storage/  
└── users/  
    └── \<user\_id\>/  
        └── sessions/  
            └── \<session\_id\>/  
                └── evidence/  
                    └── \<evidence\_id\>.\<extension\>

Store only relative paths in the database.

---

## **41\. Upload Validation**

Validate:

* supported MIME type;  
* maximum file size;  
* extension consistency;  
* image decode success;  
* session ownership;  
* ticker relationship;  
* upload timestamp;  
* evidence category.

Recommended image types:

image/png  
image/jpeg  
image/webp

---

## **42\. Image Preprocessing**

Optional MVP preprocessing:

* normalize image orientation;  
* compress oversized images;  
* generate thumbnail;  
* preserve original;  
* calculate checksum;  
* record width and height.

Do not use destructive processing that makes orderbook text unreadable.

---

## **43\. Evidence API**

Implement endpoints for:

* create evidence upload;  
* list session evidence;  
* get evidence metadata;  
* serve authorized evidence;  
* mark evidence inactive;  
* replace evidence.

Deletion should be soft where audit history matters.

---

## **44\. Deliverables**

* upload service;  
* filesystem storage adapter;  
* evidence metadata persistence;  
* image validation;  
* secured file serving;  
* evidence list UI foundation.

## **45\. Acceptance Criteria**

* user can upload required initial evidence;  
* unsupported files are rejected;  
* evidence belongs to one session;  
* files cannot be accessed across users;  
* replaced evidence remains auditable.

---

# **Phase 6 — AI Provider Abstraction**

## **46\. Objectives**

Implement provider-independent AI access.

---

## **47\. Provider Interface**

Create:

class AIProvider:  
    async def generate\_structured\_analysis(  
        self,  
        request: AnalysisProviderRequest,  
    ) \-\> ProviderResponse:  
        ...

Implement adapters:

GeminiProvider  
DeepSeekProvider

---

## **48\. Provider Request Model**

Include:

* analysis type;  
* system prompt version;  
* schema name;  
* schema version;  
* structured output schema where supported;  
* canonical facts;  
* context summary;  
* evidence;  
* output language;  
* provider timeout;  
* provider metadata.

---

## **49\. Provider Response Model**

Store:

* provider;  
* model;  
* raw response;  
* extracted content;  
* token usage if available;  
* finish reason;  
* latency;  
* refusal status;  
* transport errors.

---

## **50\. Provider Selection**

Configuration:

primary provider \= Gemini  
fallback provider \= DeepSeek

This may be reversed by configuration.

---

## **51\. Provider Capabilities**

Create a provider capability map:

structured\_output\_supported  
image\_input\_supported  
maximum\_images  
maximum\_context  
supports\_json\_schema  
supports\_retry\_instructions

The context builder should adapt to provider limits without changing the output contract.

---

## **52\. Prompt Versioning**

Every request must store:

* prompt name;  
* prompt version;  
* schema name;  
* schema version.

Prompts should be stored as versioned files or Python modules.

---

## **53\. Deliverables**

* common provider interface;  
* Gemini adapter;  
* DeepSeek adapter;  
* provider configuration;  
* mocked contract tests;  
* raw request and response logging.

## **54\. Acceptance Criteria**

* both providers return the same application-level response structure;  
* provider selection is configuration-driven;  
* provider errors are classified;  
* API keys are never logged;  
* image inputs can be sent for analysis.

---

# **Phase 7 — Analysis Worker and Job Pipeline**

## **55\. Objectives**

Process AI analysis outside the request-response cycle.

---

## **56\. Job Queue Strategy**

For MVP, choose one of:

### **Option A — PostgreSQL-backed jobs**

Advantages:

* fewer infrastructure components;  
* reliable enough for low volume;  
* easy VPS operation.

Recommended for the first MVP.

### **Option B — Redis queue**

Advantages:

* mature queue behavior;  
* easier retries and concurrency.

Adds infrastructure complexity.

The initial implementation should use PostgreSQL job leasing unless a Redis requirement already exists.

---

## **57\. Job Lifecycle**

Recommended statuses:

PENDING  
CLAIMED  
BUILDING\_CONTEXT  
CALLING\_PROVIDER  
PARSING  
VALIDATING  
REPAIRING  
FALLBACK  
ACCEPTING  
COMPLETED  
FAILED  
CANCELLED

---

## **58\. Worker Responsibilities**

The worker must:

1. claim one job atomically;  
2. load session and canonical Trade State;  
3. validate requested analysis type;  
4. load required evidence;  
5. rebuild stale context if necessary;  
6. build provider request;  
7. call primary provider;  
8. parse JSON;  
9. validate output;  
10. run repair if needed;  
11. call fallback if needed;  
12. inject deterministic values;  
13. validate final payload;  
14. store accepted analysis;  
15. rebuild context;  
16. update job status;  
17. restore session lifecycle state.

---

## **59\. Repair Flow**

Maximum provider attempts:

1 initial primary call  
1 primary repair call  
1 fallback call

No unlimited retries.

---

## **60\. Worker Leasing**

Each job claim should record:

* worker ID;  
* lease expiration;  
* claimed timestamp;  
* heartbeat.

Expired jobs may be reclaimed safely.

---

## **61\. Atomic Acceptance**

The following should occur in one database transaction:

* accepted analysis persistence;  
* latest-analysis pointer update;  
* non-canonical proposal storage;  
* context rebuild or rebuild request;  
* job completion.

Canonical Trade State must not be mutated.

---

## **62\. Deliverables**

* PostgreSQL job queue;  
* worker polling loop;  
* job processor;  
* repair service;  
* fallback flow;  
* worker health endpoint;  
* failure logging.

## **63\. Acceptance Criteria**

* web requests do not wait for AI completion;  
* jobs survive backend restarts;  
* validation failure triggers bounded repair;  
* failed jobs do not create accepted analyses;  
* duplicate job processing is prevented.

---

# **Phase 8 — Context Memory**

## **64\. Objectives**

Create compact longitudinal memory for each Trade Session.

---

## **65\. Context Builder Inputs**

The builder uses:

* canonical Trade State;  
* original thesis;  
* latest accepted analysis;  
* accepted analysis history;  
* user-confirmed actions;  
* active stop and target;  
* pending proposals;  
* latest evidence metadata;  
* material historical changes;  
* closing result if available.

---

## **66\. Context Builder Output**

Produce `context_summary.schema.json`.

The builder should primarily be deterministic.

AI may assist with summarization later, but canonical facts must be injected and validated by backend.

---

## **67\. History Compression**

Preserve:

* initial setup;  
* position opening;  
* thesis changes;  
* support and resistance shifts;  
* stop changes;  
* target changes;  
* partial exits;  
* final exit.

Compress repetitive observations.

---

## **68\. Context Freshness**

Context must be rebuilt after:

* accepted analysis;  
* user-confirmed action;  
* evidence replacement;  
* stop or target change;  
* partial exit;  
* full exit.

Before analysis, stale context must be rejected or rebuilt.

---

## **69\. Deliverables**

* Context Summary builder;  
* material-event selector;  
* pending-proposal manager;  
* freshness checker;  
* context version persistence;  
* context fixture tests.

## **70\. Acceptance Criteria**

* context matches canonical Trade State;  
* proposal never becomes active automatically;  
* original thesis is preserved;  
* chart timestamp remains visible;  
* stale context cannot silently enter a new AI request.

---

# **Phase 9 — Backend APIs**

## **71\. Objectives**

Expose the core workflow to the frontend.

---

## **72\. API Groups**

### **72.1 Session APIs**

POST   /api/trade-sessions  
GET    /api/trade-sessions  
GET    /api/trade-sessions/{session\_id}  
PATCH  /api/trade-sessions/{session\_id}  
POST   /api/trade-sessions/{session\_id}/ready  
POST   /api/trade-sessions/{session\_id}/archive

### **72.2 Evidence APIs**

POST   /api/trade-sessions/{session\_id}/evidence  
GET    /api/trade-sessions/{session\_id}/evidence  
GET    /api/evidence/{evidence\_id}  
DELETE /api/evidence/{evidence\_id}

### **72.3 Analysis APIs**

POST /api/trade-sessions/{session\_id}/analyses  
GET  /api/trade-sessions/{session\_id}/analyses  
GET  /api/analyses/{analysis\_id}  
GET  /api/analysis-jobs/{job\_id}  
POST /api/analysis-jobs/{job\_id}/retry

### **72.4 Trade Action APIs**

POST /api/trade-sessions/{session\_id}/actions/open-position  
POST /api/trade-sessions/{session\_id}/actions/confirm-stop  
POST /api/trade-sessions/{session\_id}/actions/change-stop  
POST /api/trade-sessions/{session\_id}/actions/confirm-target  
POST /api/trade-sessions/{session\_id}/actions/change-target  
POST /api/trade-sessions/{session\_id}/actions/partial-exit  
POST /api/trade-sessions/{session\_id}/actions/full-exit  
POST /api/trade-sessions/{session\_id}/actions/cancel

### **72.5 Context and Timeline APIs**

GET /api/trade-sessions/{session\_id}/context  
GET /api/trade-sessions/{session\_id}/timeline

---

## **73\. Session Detail Response**

The session detail endpoint should provide:

* session metadata;  
* canonical Trade State;  
* active stop and target;  
* latest accepted analysis;  
* analysis history summaries;  
* pending proposals;  
* evidence index;  
* current job;  
* timeline;  
* allowed actions.

The frontend should not need to reconstruct lifecycle logic independently.

---

## **74\. Authorization**

Every query must be scoped by authenticated user.

No user may access another user's:

* session;  
* evidence;  
* analysis;  
* file;  
* context.

---

## **75\. Error Contract**

Use consistent API errors:

{  
  "error": {  
    "code": "INVALID\_SESSION\_STATUS\_TRANSITION",  
    "message": "This action is not allowed for the current session state.",  
    "details": {}  
  }  
}

User-facing messages should be Indonesian where returned directly to the UI.

---

## **76\. Deliverables**

* REST API routes;  
* request and response Pydantic models;  
* authentication dependencies;  
* authorization tests;  
* OpenAPI documentation;  
* integration tests.

## **77\. Acceptance Criteria**

* all primary lifecycle actions are available;  
* session detail supplies enough data for the frontend;  
* invalid actions return stable error codes;  
* ownership is enforced;  
* OpenAPI spec is generated.

---

# **Phase 10 — Frontend Trade Session Workspace**

## **78\. Objectives**

Build the user experience defined in `UX_UI_SPEC.md`.

---

## **79\. Primary Pages**

### **79.1 Session list**

Displays:

* ticker;  
* session status;  
* current price where available;  
* active entry;  
* target;  
* stop;  
* latest recommendation;  
* last update timestamp.

### **79.2 New Session page**

Fields:

* ticker;  
* company name;  
* exchange;  
* currency;  
* optional note.

### **79.3 Trade Session detail page**

One dedicated page per stock session.

Core regions:

Header  
Canonical position summary  
Evidence upload area  
Latest AI analysis  
Trading plan  
Probability and confidence  
Target and stop assessment  
Timeline  
Analysis history  
User confirmation actions  
Warnings and missing information

---

## **80\. Status-Specific UI**

### **80.1 Watching**

Show:

* initial thesis;  
* current setup;  
* proposed entry;  
* proposed stop;  
* proposed target;  
* confirmation condition;  
* do-not-chase warning;  
* button to confirm position opened.

### **80.2 Open Position**

Show:

* entry;  
* quantity;  
* current price;  
* unrealized P/L;  
* active stop;  
* active target;  
* target realism;  
* thesis status;  
* recommended action;  
* target probability;  
* downside probability;  
* buttons for stop, target, partial exit, full exit.

### **80.3 Partially Closed**

Show:

* realized result;  
* remaining quantity;  
* remaining target;  
* protective stop;  
* total current trade result;  
* second partial exit and final exit actions.

### **80.4 Closed**

Show:

* final result;  
* weighted average exit;  
* thesis evaluation;  
* process grade;  
* lessons;  
* complete timeline;  
* journal summary.

---

## **81\. Analysis Rendering**

Render sections based on analysis type.

Do not display raw JSON.

Create typed components:

InitialAnalysisView  
WatchingUpdateView  
OpenPositionUpdateView  
PartialExitReviewView  
ClosingAnalysisView

Use golden fixtures for frontend development.

---

## **82\. Job Progress UI**

When analysis is running:

* show job state;  
* poll job status;  
* prevent duplicate submission;  
* allow retry after failure;  
* preserve uploaded evidence;  
* show clear Indonesian error message.

---

## **83\. User Confirmation Modals**

Confirmation forms must clearly distinguish AI proposals from user actions.

Example stop-change modal:

Current active stop: 2,840  
AI proposed stop: 2,880  
New confirmed stop: \[2,880\]

The user may modify the proposed value before confirming.

---

## **84\. Responsive Design**

Desktop is the primary MVP target.

Mobile should remain usable for:

* viewing session;  
* uploading screenshot;  
* confirming actions.

---

## **85\. Deliverables**

* session list;  
* new-session flow;  
* Trade Session page;  
* evidence uploader;  
* analysis renderer;  
* job-progress components;  
* confirmation dialogs;  
* frontend API client;  
* golden-fixture component tests.

## **86\. Acceptance Criteria**

* each session has a dedicated page;  
* user can upload initial and update evidence;  
* all lifecycle actions are accessible;  
* canonical and proposed values are visually distinct;  
* analysis is readable in Indonesian;  
* historical updates do not mix across sessions.

---

# **Phase 11 — End-to-End Testing and Hardening**

## **87\. Objectives**

Validate the complete MVP workflow.

---

## **88\. Required End-to-End Scenarios**

### **Scenario A — Initial analysis to open position**

1. create session;  
2. upload orderbook;  
3. upload three-month chart;  
4. upload six-month chart;  
5. request initial analysis;  
6. receive Watching state;  
7. upload new orderbook;  
8. request Watching Update;  
9. confirm position opened.

### **Scenario B — Open Position monitoring**

1. upload morning orderbook;  
2. request Open Position update;  
3. upload midday orderbook;  
4. request another update;  
5. verify comparison;  
6. change stop after confirmation.

### **Scenario C — Partial exit**

1. confirm partial exit;  
2. verify remaining quantity;  
3. request Partial Exit Review;  
4. confirm protective stop.

### **Scenario D — Full close**

1. confirm full exit;  
2. verify remaining quantity zero;  
3. request Closing Analysis;  
4. verify journal and lessons.

### **Scenario E — Invalid provider payload**

1. primary provider returns invalid payload;  
2. repair fails;  
3. fallback succeeds;  
4. only fallback payload is accepted.

### **Scenario F — State conflict**

1. provider changes entry price;  
2. validator detects mismatch;  
3. payload is rejected;  
4. canonical state remains unchanged.

---

## **89\. Security Hardening**

Implement:

* secure password handling or trusted identity provider;  
* HTTP-only session cookies;  
* CSRF protection where applicable;  
* file upload restrictions;  
* ownership checks;  
* path traversal prevention;  
* request-size limits;  
* rate limiting;  
* secret redaction;  
* database least privilege;  
* HTTPS.

---

## **90\. Operational Hardening**

Implement:

* structured logging;  
* request IDs;  
* job IDs;  
* worker heartbeat;  
* health endpoints;  
* database backup script;  
* storage backup procedure;  
* log rotation;  
* disk usage alerts;  
* failed-job inspection.

---

## **91\. Performance Checks**

MVP targets:

* session page API response under normal load should be responsive;  
* upload should support common screenshot sizes;  
* schema validation should complete quickly;  
* one worker should process jobs sequentially without blocking the API;  
* frontend should render long analyses without severe layout issues.

---

## **92\. Deliverables**

* complete fixture suite;  
* API integration tests;  
* end-to-end browser tests;  
* security checklist;  
* failure recovery tests;  
* backup and restore test;  
* release candidate.

## **93\. Acceptance Criteria**

* all core scenarios pass;  
* invalid AI output cannot leak to the user as accepted analysis;  
* canonical state remains correct after failures;  
* backups can be restored;  
* worker restart does not lose pending jobs.

---

# **Phase 12 — VPS Deployment and MVP Release**

## **94\. Objectives**

Deploy the production MVP to one VPS.

---

## **95\. Production Components**

Recommended services:

nginx  
frontend  
backend  
worker  
postgres

Optional:

redis

---

## **96\. Deployment Strategy**

Use Docker Compose or systemd-managed services.

For a small private deployment, Docker Compose is acceptable if:

* persistent volumes are configured;  
* restart policies are enabled;  
* logs are rotated;  
* backups are externalized.

---

## **97\. Nginx Responsibilities**

* HTTPS termination;  
* frontend routing;  
* backend reverse proxy;  
* upload-size configuration;  
* static evidence authorization through backend or protected internal route;  
* security headers.

---

## **98\. Persistent Data**

Persist:

PostgreSQL data  
uploaded evidence  
application logs  
schema files  
backup archives

Do not store production data only inside ephemeral containers.

---

## **99\. Backup Strategy**

Daily backup:

* PostgreSQL dump;  
* uploaded evidence archive or incremental sync.

Keep at least:

7 daily backups  
4 weekly backups  
3 monthly backups

Store at least one copy outside the VPS.

---

## **100\. Deployment Pipeline**

Initial manual flow:

git pull  
docker compose build  
docker compose run backend alembic upgrade head  
docker compose up \-d  
run health checks

Later GitHub Actions may automate deployment.

---

## **101\. Production Environment Variables**

Required:

APP\_ENV=production  
DATABASE\_URL  
APP\_SECRET\_KEY  
GEMINI\_API\_KEY  
DEEPSEEK\_API\_KEY  
AI\_PRIMARY\_PROVIDER  
AI\_FALLBACK\_PROVIDER  
UPLOAD\_STORAGE\_PATH  
PUBLIC\_APP\_URL  
ALLOWED\_HOSTS  
LOG\_LEVEL

---

## **102\. Production Health Checks**

Endpoints:

GET /health  
GET /health/ready  
GET /health/schema-registry  
GET /health/worker

Checks should cover:

* backend process;  
* database;  
* schema registry;  
* storage write access;  
* worker heartbeat.

AI providers should not necessarily block readiness if temporarily unavailable, but their status should be visible.

---

## **103\. Release Checklist**

Before release:

* migrations applied;  
* schema package validated;  
* fixture tests passing;  
* production secrets configured;  
* HTTPS active;  
* upload permissions verified;  
* backup tested;  
* worker heartbeat visible;  
* one complete test session executed;  
* rollback procedure documented.

---

# **Cross-Phase Technical Decisions**

## **104\. Authentication**

For a private MVP, acceptable options:

### **Option A — Local email and password**

Implement directly in backend.

### **Option B — External identity provider**

Use a provider that supports a small private app.

The implementation should avoid blocking the core workflow on complex account management.

---

## **105\. Queue Selection**

Recommended MVP choice:

PostgreSQL-backed queue.

Reasons:

* already required;  
* sufficient for low request volume;  
* simpler VPS operation;  
* supports transactional job creation.

Redis can be introduced later.

---

## **106\. File Storage Selection**

Recommended MVP choice:

VPS filesystem with storage abstraction.

The code must use an interface such as:

FileStorage  
LocalFileStorage

This allows migration to S3-compatible object storage later.

---

## **107\. Market Data**

The MVP relies primarily on user-uploaded screenshots and structured user input.

External market-data enrichment may be added later but must not delay MVP.

Where deterministic values are available from extracted evidence, the backend stores their source and confidence.

---

## **108\. AI Image Interpretation**

For initial and update analyses:

* provider receives screenshots directly if image input is supported;  
* prompts instruct the model to distinguish visible facts from interpretation;  
* low readability must be reported;  
* AI must not fabricate unreadable orderbook values.

A future OCR preprocessing layer is optional and not required for the first implementation.

---

## **109\. Proposal Storage**

AI proposals should be stored separately from canonical Trade State.

Recommended proposal entity:

analysis\_proposals

Potential proposal types:

ENTRY  
STOP\_LOSS  
TARGET  
PARTIAL\_EXIT  
FULL\_EXIT  
CANCEL\_SETUP

Each proposal should record:

* source analysis;  
* proposed value;  
* status;  
* confirmed action if accepted;  
* superseded timestamp.

---

## **110\. Analysis Immutability**

Accepted analysis payloads should be immutable.

Corrections should create:

* a replacement analysis;  
* a superseding relationship;  
* an audit note.

Do not mutate old accepted analyses silently.

---

# **Implementation Priorities**

## **111\. MVP Critical Path**

The shortest critical path is:

Repository  
→ Database  
→ Trade State  
→ Production Schemas  
→ Validation  
→ Lifecycle  
→ Evidence Upload  
→ Gemini Provider  
→ Worker  
→ Initial Analysis  
→ Open Position Update  
→ Session UI  
→ Confirmation Actions  
→ Partial and Closing Flows  
→ DeepSeek Fallback  
→ Deployment

---

## **112\. Features That Must Not Delay Initial Vertical Slice**

These may be added after the first working analysis flow:

* full migration tooling;  
* advanced provider metrics;  
* sophisticated journal reporting;  
* multiple users;  
* external market-data integration;  
* extensive chart extraction;  
* advanced monitoring dashboards;  
* automated GitHub deployment.

---

## **113\. First Vertical Slice**

The first end-to-end slice should support:

1. create Trade Session;  
2. upload three images;  
3. request Initial Analysis;  
4. worker calls Gemini;  
5. output validates;  
6. result appears on session page;  
7. context summary is generated.

This slice proves:

* repository;  
* database;  
* uploads;  
* provider;  
* worker;  
* schema validation;  
* API;  
* frontend rendering.

---

## **114\. Second Vertical Slice**

Support:

1. Watching Update;  
2. position-opening confirmation;  
3. canonical Trade State update;  
4. Open Position update;  
5. morning and midday comparison.

This proves the primary product value.

---

## **115\. Third Vertical Slice**

Support:

1. stop and target changes;  
2. partial exit;  
3. final exit;  
4. Closing Analysis;  
5. journal summary.

This completes the Trade Session lifecycle.

---

# **Suggested Milestone Structure**

## **116\. Milestone 1 — Foundation**

Includes:

* Phase 0;  
* Phase 1;  
* Phase 2\.

Exit criteria:

* database and schemas are ready;  
* repository boots;  
* schema package compiles.

---

## **117\. Milestone 2 — Validation and Lifecycle**

Includes:

* Phase 3;  
* Phase 4\.

Exit criteria:

* canonical Trade State is enforced;  
* validation is operational;  
* user-confirmed actions work.

---

## **118\. Milestone 3 — Initial AI Workflow**

Includes:

* Phase 5;  
* Phase 6;  
* initial portion of Phase 7;  
* initial portion of Phase 9;  
* initial portion of Phase 10\.

Exit criteria:

* Initial Analysis works end to end.

---

## **119\. Milestone 4 — Open Position Workspace**

Includes:

* Context Summary;  
* Watching Update;  
* Open Position Update;  
* longitudinal comparison;  
* full Open Position UI.

Exit criteria:

* user can follow an active position morning, midday, and afternoon.

---

## **120\. Milestone 5 — Complete Trade Lifecycle**

Includes:

* partial exit;  
* final exit;  
* Closing Analysis;  
* journal;  
* timeline.

Exit criteria:

* one Trade Session can be completed from creation to close.

---

## **121\. Milestone 6 — Production Readiness**

Includes:

* fallback provider;  
* full testing;  
* security;  
* backups;  
* VPS deployment.

Exit criteria:

* production MVP is usable and recoverable.

---

# **Testing Strategy by Phase**

## **122\. Phase Testing Expectations**

### **Foundation**

* database unit tests;  
* migration tests;  
* schema compilation tests.

### **Validation**

* schema fixtures;  
* domain fixtures;  
* state conflict tests.

### **Lifecycle**

* state-transition tests;  
* idempotency tests;  
* transaction tests.

### **AI**

* provider mock tests;  
* parser tests;  
* repair tests;  
* fallback tests.

### **Context**

* rebuild tests;  
* staleness tests;  
* canonical consistency tests.

### **API**

* authenticated integration tests;  
* ownership tests;  
* error-contract tests.

### **Frontend**

* component tests;  
* API-state tests;  
* confirmation modal tests.

### **Deployment**

* health checks;  
* backup restore;  
* process restart;  
* worker recovery.

---

# **Development Data**

## **123\. Seed Scenario**

Create one complete development scenario based on BBRI:

Entry: 2800  
Quantity: 100  
Stop: 2700, later 2840  
Target: 2920  
Partial exit: 50 at 2920  
Final exit: 50 at 2900

This scenario should be reusable for:

* backend tests;  
* frontend mock data;  
* provider prompts;  
* fixture validation;  
* demo sessions.

---

# **Definition of Done**

## **124\. Task-Level Definition of Done**

A coding task is complete when:

* implementation exists;  
* type checking passes;  
* lint passes;  
* tests exist;  
* tests pass;  
* error behavior is defined;  
* logs are appropriate;  
* documentation is updated where necessary;  
* no unresolved TODO affects the acceptance criteria.

---

## **125\. Phase-Level Definition of Done**

A phase is complete when:

* all phase deliverables exist;  
* acceptance criteria pass;  
* integration with previous phases works;  
* no critical blocker is deferred;  
* a manual demonstration can be performed.

---

# **Risk Register**

## **126\. Schema Inconsistency Risk**

Risk:

* references may point to missing common definitions.

Mitigation:

* complete schema audit before validator implementation;  
* compile all schemas in CI.

---

## **127\. AI Structured Output Risk**

Risk:

* providers may return invalid or incomplete JSON.

Mitigation:

* structured-output mode;  
* schema validation;  
* repair attempt;  
* fallback provider;  
* bounded failure handling.

---

## **128\. Image Readability Risk**

Risk:

* screenshots may be too small or unclear.

Mitigation:

* upload quality checks;  
* image dimensions;  
* unreadable-evidence state;  
* user-facing warning;  
* no fabricated values.

---

## **129\. Context Drift Risk**

Risk:

* new analysis may ignore or contradict earlier facts.

Mitigation:

* canonical Trade State injection;  
* Context Summary;  
* user-confirmed action history;  
* state consistency validator.

---

## **130\. Lifecycle Corruption Risk**

Risk:

* partial or full exit may produce incorrect quantities.

Mitigation:

* transactional action service;  
* quantity conservation rules;  
* idempotency;  
* domain tests.

---

## **131\. VPS Data Loss Risk**

Risk:

* database or evidence may be lost.

Mitigation:

* persistent volumes;  
* external backups;  
* tested restore procedure.

---

## **132\. Scope Expansion Risk**

Risk:

* adding real-time data, portfolios, and automation before MVP.

Mitigation:

* preserve the defined MVP;  
* complete one Trade Session lifecycle first.

---

# **Implementation Order Summary**

## **133\. Ordered Execution**

The development team should execute in this order:

1. Repository scaffolding.  
2. Local Docker environment.  
3. Database migrations.  
4. Canonical domain models.  
5. Production schema files.  
6. Schema audit.  
7. Manifest and registry.  
8. JSON Schema validation.  
9. deterministic calculation services.  
10. domain validators.  
11. lifecycle and confirmed actions.  
12. evidence upload.  
13. Gemini adapter.  
14. analysis job queue.  
15. worker pipeline.  
16. Initial Analysis end to end.  
17. Context Summary builder.  
18. Watching Update.  
19. position-opening confirmation.  
20. Open Position Update.  
21. stop and target workflows.  
22. partial-exit workflow.  
23. final-exit workflow.  
24. Closing Analysis.  
25. DeepSeek fallback.  
26. full fixture suite.  
27. frontend completion.  
28. security and operational hardening.  
29. VPS deployment.  
30. production smoke test.

---

# **Acceptance Criteria for the Complete MVP**

## **134\. Product Acceptance**

The MVP is complete when the user can:

1. create a dedicated session for one ticker;  
2. upload initial orderbook and charts;  
3. receive an Initial Analysis in Indonesian;  
4. continue watching the setup;  
5. confirm a real entry;  
6. receive Open Position analysis during multiple daily periods;  
7. view Open, High, Low, Close or Last, and Average;  
8. view orderbook interpretation;  
9. view whether target remains realistic;  
10. view target and downside probabilities;  
11. view the current trading plan;  
12. confirm stop or target changes;  
13. confirm partial exit;  
14. confirm full exit;  
15. receive a Closing Analysis;  
16. review the entire trade story on one page.

---

## **135\. Engineering Acceptance**

The MVP is complete when:

1. canonical Trade State cannot be changed by AI;  
2. all AI output is schema validated;  
3. domain calculations use Decimal;  
4. invalid provider output is rejected;  
5. repair and fallback are bounded;  
6. context remains consistent with confirmed actions;  
7. session ownership is enforced;  
8. uploads are secured;  
9. worker jobs survive restart;  
10. backups are available and restorable;  
11. fixture and integration tests pass;  
12. the application runs on the VPS through HTTPS.

---

## **136\. Next Document**

The final planning artifact before implementation is:

OPEN\_CODE\_TASKS.md

It should translate this plan into small, ordered coding tasks with:

* task IDs;  
* dependencies;  
* exact objectives;  
* target files;  
* implementation instructions;  
* acceptance criteria;  
* test requirements;  
* completion checkpoints.

