# **TradePilot AI — System Architecture**

**Document:** `ARCHITECTURE.md`  
**Version:** 1.0  
**Status:** Final  
**Product Name:** TradePilot AI  
**Primary References:** `PRD.md`, `PRODUCT_RULES.md`, `USER_FLOWS.md`, `UX_UI_SPEC.md`  
**Purpose:** Define the target system architecture, service boundaries, data flows, infrastructure, deployment model, and technical responsibilities for the TradePilot AI MVP.

---

## **1\. Document Purpose**

This document defines the system architecture for TradePilot AI.

It establishes:

* application boundaries;  
* frontend responsibilities;  
* backend responsibilities;  
* domain-service boundaries;  
* AI orchestration;  
* background job processing;  
* database responsibilities;  
* file-storage responsibilities;  
* provider abstraction;  
* authentication and security boundaries;  
* observability;  
* deployment on a VPS;  
* recovery and scaling considerations.

This document defines the architectural direction. Detailed implementation contracts will be defined in later documents such as:

* `DOMAIN_MODEL.md`  
* `DATABASE_SCHEMA.md`  
* `API_SPEC.md`  
* `BACKGROUND_JOBS_SPEC.md`  
* `FILE_STORAGE_SPEC.md`  
* `AI_PROVIDER_SPEC.md`  
* `AUTH_SECURITY_SPEC.md`  
* `DEPLOYMENT_SPEC.md`

---

# **2\. Architecture Goals**

The TradePilot AI architecture must support the following product requirements:

1. one dedicated workspace for one trade lifecycle;  
2. persistent longitudinal analysis;  
3. immutable analysis versioning;  
4. thesis consistency and history;  
5. user-controlled position changes;  
6. image-based AI analysis;  
7. asynchronous AI processing;  
8. AI provider interchangeability;  
9. secure storage of trading evidence;  
10. reliable deployment on a self-hosted VPS;  
11. clear audit history;  
12. recovery after restart or failure;  
13. structured AI output validation;  
14. Bahasa Indonesia user-facing analysis;  
15. English internal contracts, prompts, and identifiers.

---

# **3\. Architecture Principles**

## **3.1 Modular Monolith First**

The MVP should use a modular monolith rather than independent microservices.

The system may run multiple processes or containers, but the application domain should remain within one repository and one coordinated deployment.

Recommended logical modules:

* authentication;  
* trade sessions;  
* evidence;  
* positions;  
* thesis;  
* analyses;  
* AI orchestration;  
* journals;  
* notifications;  
* audit;  
* settings;  
* usage tracking.

This approach provides:

* simpler development;  
* simpler deployment;  
* lower VPS resource requirements;  
* easier transaction management;  
* fewer distributed-system failure modes;  
* clear boundaries for future extraction if scale requires it.

---

## **3.2 Frontend and Backend Separation**

The frontend and backend must have clearly separated responsibilities.

The frontend handles:

* rendering;  
* local interaction state;  
* form validation for usability;  
* upload progress;  
* API consumption;  
* job-status display;  
* user-facing localization.

The backend handles:

* authorization;  
* authoritative validation;  
* lifecycle transitions;  
* domain rules;  
* data persistence;  
* AI orchestration;  
* job creation;  
* structured-output validation;  
* canonical-state updates;  
* audit records.

The frontend must never be trusted as the authoritative source for domain transitions.

---

## **3.3 Background Processing for AI Work**

AI analysis must not run inside long-lived synchronous HTTP requests.

AI work must run through background jobs because it may involve:

* image preparation;  
* context construction;  
* provider calls;  
* retries;  
* fallback providers;  
* schema repair;  
* language validation;  
* contradiction detection;  
* persistence of multiple related records.

---

## **3.4 Canonical State and Immutable History**

The architecture must separate:

* current canonical session state;  
* immutable historical events;  
* immutable analysis versions;  
* immutable thesis versions;  
* immutable position transactions.

Canonical state enables fast rendering.

Historical records provide traceability and journal reconstruction.

---

## **3.5 Provider Independence**

Gemini and DeepSeek must be accessed through a common provider abstraction.

Domain logic must not depend on provider-specific request or response formats.

Provider-specific behavior belongs only inside provider adapters.

---

## **3.6 Evidence Is a First-Class Domain Object**

Uploaded screenshots are not temporary prompt attachments.

Each evidence item must be:

* persisted;  
* classified;  
* timestamped;  
* linked to a session;  
* linked to analysis versions;  
* auditable;  
* retrievable through authorization.

---

## **3.7 Security by Default**

The system contains private trading information and API credentials.

Security must be enforced at:

* authentication;  
* API authorization;  
* file access;  
* secret management;  
* logging;  
* network exposure;  
* database access;  
* backup handling.

---

# **4\. Recommended Technology Stack**

## **4.1 Frontend**

Recommended:

* Next.js;  
* TypeScript;  
* React;  
* server-side and client-side rendering as appropriate;  
* a typed API client;  
* a component library or internal design system;  
* a query/cache library for server state;  
* schema-based form validation.

The frontend must not contain AI provider credentials.

---

## **4.2 Backend API**

Recommended:

* Python;  
* FastAPI;  
* Pydantic for request, response, and AI-schema validation;  
* SQLAlchemy for database access;  
* Alembic for database migrations.

Python is recommended because:

* AI-provider SDK support is strong;  
* image-processing support is mature;  
* structured validation is convenient;  
* background worker integration is straightforward.

---

## **4.3 Database**

Recommended:

* PostgreSQL.

PostgreSQL stores:

* users;  
* Trade Sessions;  
* evidence metadata;  
* positions;  
* entries;  
* exits;  
* stop-loss versions;  
* target versions;  
* analyses;  
* thesis versions;  
* probability assessments;  
* timeline events;  
* journals;  
* jobs;  
* AI usage;  
* configuration metadata;  
* audit records.

Binary evidence files must not be stored directly in ordinary database columns for the MVP.

---

## **4.4 Background Queue**

Recommended:

* Redis;  
* a Python job worker based on Celery, Dramatiq, RQ, or an equivalent library.

The exact library will be locked in `BACKGROUND_JOBS_SPEC.md`.

Redis responsibilities may include:

* job queue;  
* short-lived distributed locks;  
* idempotency locks;  
* rate-limit counters;  
* temporary job progress;  
* short-lived cache.

Redis must not be treated as the primary persistent store for Trade Session data.

---

## **4.5 File Storage**

MVP recommendation:

* persistent local storage mounted on the VPS;  
* files stored outside the publicly served frontend directory;  
* access through authenticated backend endpoints or signed application URLs;  
* storage abstraction to support future S3-compatible object storage.

Stored objects include:

* original evidence;  
* thumbnails;  
* optimized previews;  
* normalized AI-input variants;  
* optional generated exports.

---

## **4.6 Reverse Proxy and TLS**

Recommended:

* Nginx or Caddy;  
* HTTPS;  
* reverse proxy to frontend and backend;  
* upload-size control;  
* request timeout configuration;  
* secure response headers.

The exact reverse proxy may be selected during deployment design.

---

## **4.7 Containerization**

Recommended:

* Docker;  
* Docker Compose for the MVP.

Primary containers:

* frontend;  
* backend API;  
* background worker;  
* PostgreSQL;  
* Redis;  
* reverse proxy;  
* optional scheduler;  
* optional backup job.

---

# **5\. High-Level Architecture**

┌──────────────────────────────────────────────────────────────┐  
│                         User Browser                         │  
│                                                              │  
│  Dashboard / Trade Session / Evidence / Journal / Settings   │  
└──────────────────────────────┬───────────────────────────────┘  
                               │ HTTPS  
                               ▼  
┌──────────────────────────────────────────────────────────────┐  
│                    Reverse Proxy / Gateway                   │  
│                                                              │  
│     TLS termination, routing, headers, upload limits         │  
└───────────────┬──────────────────────────────┬───────────────┘  
                │                              │  
                ▼                              ▼  
┌──────────────────────────┐      ┌────────────────────────────┐  
│     Next.js Frontend     │      │      FastAPI Backend       │  
│                          │      │                            │  
│ UI rendering             │      │ Authentication             │  
│ Forms                    │      │ Domain services            │  
│ API client               │      │ Lifecycle validation       │  
│ Job status display       │      │ File authorization         │  
└──────────────────────────┘      │ AI job orchestration       │  
                                  │ Canonical state updates    │  
                                  └───────┬─────────┬──────────┘  
                                          │         │  
                               SQL        │         │ Queue  
                                          ▼         ▼  
                              ┌────────────────┐  ┌─────────────┐  
                              │  PostgreSQL    │  │    Redis    │  
                              │                │  │             │  
                              │ Domain data    │  │ Job queue   │  
                              │ History        │  │ Locks       │  
                              │ Audit records  │  │ Progress    │  
                              └────────────────┘  └──────┬──────┘  
                                                        │  
                                                        ▼  
                                             ┌─────────────────────┐  
                                             │ Background Worker   │  
                                             │                     │  
                                             │ Context building    │  
                                             │ Image preparation   │  
                                             │ AI provider calls   │  
                                             │ Output validation   │  
                                             │ Thesis evaluation   │  
                                             │ Journal generation  │  
                                             └───────┬─────────────┘  
                                                     │  
                          ┌──────────────────────────┼──────────────────────┐  
                          │                          │                      │  
                          ▼                          ▼                      ▼  
                 ┌────────────────┐        ┌────────────────┐    ┌────────────────┐  
                 │ Gemini Adapter │        │ DeepSeek       │    │ File Storage   │  
                 │                │        │ Adapter        │    │                │  
                 │ Vision/Text    │        │ Vision/Text\*   │    │ Original files │  
                 │ Structured out │        │ Structured out │    │ Previews       │  
                 └────────────────┘        └────────────────┘    │ AI variants    │  
                                                                └────────────────┘

`*` Provider capabilities must be checked against the configured model before a vision task is assigned.

---

# **6\. Repository Architecture**

Recommended monorepo structure:

tradepilot-ai/  
├── apps/  
│   ├── web/  
│   │   ├── src/  
│   │   ├── public/  
│   │   ├── tests/  
│   │   └── package.json  
│   │  
│   ├── api/  
│   │   ├── app/  
│   │   ├── migrations/  
│   │   ├── tests/  
│   │   └── pyproject.toml  
│   │  
│   └── worker/  
│       ├── worker/  
│       ├── tests/  
│       └── pyproject.toml  
│  
├── packages/  
│   ├── ui/  
│   ├── shared-types/  
│   ├── api-client/  
│   └── configuration/  
│  
├── prompts/  
│   ├── initial\_analysis/  
│   ├── watching\_update/  
│   ├── open\_position\_update/  
│   ├── closing\_analysis/  
│   ├── trading\_journal/  
│   ├── context\_summary/  
│   └── thesis\_review/  
│  
├── schemas/  
│   ├── ai/  
│   ├── api/  
│   └── events/  
│  
├── infrastructure/  
│   ├── docker/  
│   ├── nginx/  
│   ├── scripts/  
│   ├── backups/  
│   └── monitoring/  
│  
├── docs/  
│   ├── PRD.md  
│   ├── PRODUCT\_RULES.md  
│   ├── USER\_FLOWS.md  
│   ├── UX\_UI\_SPEC.md  
│   ├── ARCHITECTURE.md  
│   └── ...  
│  
├── .github/  
│   └── workflows/  
│  
├── docker-compose.yml  
├── docker-compose.production.yml  
├── .env.example  
├── Makefile  
└── README.md

The exact repository structure will be finalized in `GITHUB_REPOSITORY_STRUCTURE.md`.

---

# **7\. Frontend Architecture**

## **7.1 Frontend Responsibilities**

The frontend is responsible for:

* authentication user experience;  
* dashboard rendering;  
* Trade Session rendering;  
* forms;  
* upload workflow;  
* evidence previews;  
* analysis version navigation;  
* timeline display;  
* comparison display;  
* job status polling or event subscription;  
* Indonesian UI labels;  
* client-side interaction validation;  
* responsive behavior.

---

## **7.2 Frontend Non-Responsibilities**

The frontend must not:

* call Gemini or DeepSeek directly;  
* store AI API keys;  
* decide authoritative lifecycle transitions;  
* overwrite canonical thesis;  
* calculate irreversible financial records without backend confirmation;  
* trust hidden form fields for authorization;  
* expose direct private file paths.

---

## **7.3 Rendering Strategy**

Recommended strategy:

* server-render or prefetch dashboard and session shell data;  
* use client components for interactive forms, uploads, comparison controls, and polling;  
* use cached API queries for server state;  
* invalidate queries after confirmed mutations.

---

## **7.4 Server State**

Server-managed state includes:

* sessions;  
* analyses;  
* evidence;  
* positions;  
* timeline;  
* jobs;  
* settings;  
* usage data.

This state should be managed through a query and caching layer rather than global client-only state.

---

## **7.5 Local UI State**

Local state includes:

* selected tabs;  
* expanded sections;  
* unsaved form values;  
* evidence viewer zoom;  
* comparison selections;  
* temporary upload progress.

Local UI state must not replace persisted domain state.

---

## **7.6 Localization Layer**

The frontend must include a mapping layer for:

* lifecycle statuses;  
* thesis statuses;  
* risk levels;  
* action values;  
* job states;  
* evidence states;  
* error codes.

Raw internal enum values must not be displayed directly as the normal label.

---

# **8\. Backend Architecture**

## **8.1 API Layer**

The API layer handles:

* HTTP request parsing;  
* authentication;  
* authorization;  
* input-schema validation;  
* response serialization;  
* transaction boundaries;  
* domain-service invocation;  
* API error mapping.

The API layer must not contain complex business logic.

---

## **8.2 Application Service Layer**

Application services orchestrate use cases.

Recommended services:

* `SessionApplicationService`  
* `EvidenceApplicationService`  
* `AnalysisApplicationService`  
* `PositionApplicationService`  
* `ThesisApplicationService`  
* `JournalApplicationService`  
* `SettingsApplicationService`  
* `NotificationApplicationService`

Responsibilities include:

* loading aggregates;  
* validating permissions;  
* calling domain services;  
* coordinating repositories;  
* creating jobs;  
* recording timeline events;  
* committing transactions.

---

## **8.3 Domain Layer**

The domain layer contains authoritative product rules.

Recommended domain modules:

domain/  
├── sessions/  
├── evidence/  
├── positions/  
├── analyses/  
├── thesis/  
├── journals/  
├── timeline/  
├── jobs/  
└── shared/

The domain layer owns:

* lifecycle transitions;  
* position invariants;  
* closed-session restrictions;  
* thesis-state rules;  
* target and stop history;  
* analysis canonicalization rules;  
* audit event requirements.

---

## **8.4 Infrastructure Layer**

Infrastructure responsibilities include:

* PostgreSQL repositories;  
* Redis queue integration;  
* file-storage adapter;  
* AI-provider adapters;  
* email or notification adapters;  
* logging;  
* metrics;  
* secret loading.

The domain layer must not import provider SDKs or database-specific implementation classes.

---

# **9\. Backend Module Boundaries**

## **9.1 Authentication Module**

Responsibilities:

* account authentication;  
* password verification;  
* session or token creation;  
* logout;  
* rate limiting;  
* current-user resolution.

---

## **9.2 Trade Session Module**

Responsibilities:

* session creation;  
* lifecycle status;  
* archive state;  
* session title and ticker;  
* active canonical references;  
* update classification;  
* session search.

---

## **9.3 Evidence Module**

Responsibilities:

* upload metadata;  
* file validation;  
* evidence type;  
* evidence status;  
* active versus superseded evidence;  
* exclusions;  
* thumbnails and variants;  
* analysis-evidence linking.

---

## **9.4 Position Module**

Responsibilities:

* position creation;  
* entries;  
* weighted average;  
* partial exits;  
* final exits;  
* stop-loss versions;  
* target versions;  
* realized and unrealized calculations;  
* remaining quantity.

---

## **9.5 Analysis Module**

Responsibilities:

* analysis job requests;  
* analysis versions;  
* structured results;  
* canonical analysis;  
* analysis comparison;  
* provider metadata;  
* schema metadata;  
* validation status.

---

## **9.6 Thesis Module**

Responsibilities:

* canonical thesis;  
* thesis versions;  
* thesis statuses;  
* invalidation condition;  
* contradiction handling;  
* change reasons;  
* support and resistance state.

---

## **9.7 Journal Module**

Responsibilities:

* closing analysis;  
* journal generation;  
* journal versions;  
* outdated journal detection;  
* user reflection;  
* canonical journal.

---

## **9.8 Timeline and Audit Module**

Responsibilities:

* user-visible timeline events;  
* internal audit records;  
* actor identity;  
* previous and new values;  
* object references;  
* chronological reconstruction.

Timeline events and audit records may share infrastructure but have different purposes.

---

## **9.9 AI Usage Module**

Responsibilities:

* provider usage;  
* model usage;  
* token estimates;  
* image counts;  
* request duration;  
* estimated cost;  
* session-level cost;  
* monthly summaries.

---

# **10\. Domain Aggregate Strategy**

## **10.1 Trade Session as the Main Aggregate Boundary**

Trade Session is the central aggregate reference.

A Trade Session connects:

* evidence;  
* analyses;  
* thesis;  
* position;  
* timeline;  
* journal.

However, large histories should not be loaded as one giant in-memory object for every request.

The architecture should use:

* a lightweight canonical Trade Session record;  
* related immutable records;  
* focused repositories;  
* transactional application services.

---

## **10.2 Canonical State References**

The Trade Session record should reference or expose:

* current lifecycle status;  
* latest canonical analysis ID;  
* active thesis ID;  
* active position ID;  
* latest confidence;  
* latest key probabilities;  
* last update timestamp;  
* journal status.

This enables efficient dashboard queries.

---

## **10.3 Immutable Supporting Records**

Prefer append-only records for:

* analysis versions;  
* thesis versions;  
* entries;  
* exits;  
* stop changes;  
* target changes;  
* evidence status changes;  
* journal versions;  
* timeline events.

---

# **11\. AI Orchestration Architecture**

## **11.1 AI Orchestrator**

The AI Orchestrator coordinates AI-related processing.

Responsibilities:

1. load job data;  
2. load session canonical state;  
3. select relevant evidence;  
4. construct historical context;  
5. choose prompt template;  
6. choose provider and model;  
7. prepare image inputs;  
8. call provider adapter;  
9. normalize response;  
10. validate schema;  
11. validate user-facing language;  
12. validate required sections;  
13. detect contradictions;  
14. persist analysis version;  
15. update canonical state;  
16. create timeline and audit events;  
17. record usage;  
18. complete or fail the job.

---

## **11.2 Prompt Registry**

Prompts must be managed through a prompt registry.

Each prompt definition includes:

* prompt name;  
* prompt version;  
* analysis type;  
* system instructions;  
* user template;  
* structured-output schema version;  
* supported provider capabilities;  
* active status.

Prompts must be stored in English.

Prompt changes must be versioned.

---

## **11.3 Analysis Types**

Required analysis types:

* `INITIAL_ANALYSIS`  
* `WATCHING_UPDATE`  
* `OPEN_POSITION_UPDATE`  
* `PARTIAL_EXIT_REVIEW`  
* `CLOSING_ANALYSIS`  
* `TRADING_JOURNAL`  
* `CONTEXT_SUMMARY`  
* `THESIS_REVIEW`

---

## **11.4 Context Builder**

The Context Builder constructs a model-ready package.

Inputs may include:

* session metadata;  
* canonical thesis;  
* canonical support and resistance;  
* position snapshot;  
* latest valid analysis;  
* selected prior analysis summaries;  
* selected historical evidence;  
* user notes;  
* latest evidence;  
* previous probabilities;  
* previous confidence;  
* previous plan;  
* relevant timeline events.

---

## **11.5 Context Prioritization**

Context should be prioritized in this order:

1. current request and latest evidence;  
2. current canonical position state;  
3. current canonical thesis;  
4. latest valid analysis;  
5. previous comparable update;  
6. significant thesis changes;  
7. initial analysis;  
8. compressed older history.

Critical information must not be removed by summarization.

---

## **11.6 Context Summary**

Long sessions require a persisted canonical context summary.

The summary should be:

* structured;  
* versioned;  
* linked to the analysis that produced it;  
* updated after meaningful events;  
* reproducible from source history.

The context summary is not a replacement for immutable source data.

---

# **12\. AI Provider Abstraction**

## **12.1 Common Interface**

Recommended conceptual interface:

class AIProvider:  
    def validate\_configuration(self) \-\> ProviderValidationResult:  
        ...

    def supports(self, capability: AICapability) \-\> bool:  
        ...

    def generate\_structured\_response(  
        self,  
        request: AIRequest,  
    ) \-\> AIProviderResponse:  
        ...

---

## **12.2 Common Capabilities**

TEXT\_REASONING  
VISION\_INPUT  
STRUCTURED\_OUTPUT  
LONG\_CONTEXT  
JSON\_SCHEMA  
STREAMING

The orchestrator must verify required capabilities before dispatch.

---

## **12.3 Provider Adapter Responsibilities**

Each adapter handles:

* provider authentication;  
* provider request format;  
* image encoding or upload;  
* timeout handling;  
* provider-specific retries;  
* structured-output configuration;  
* provider error normalization;  
* response extraction;  
* usage extraction.

---

## **12.4 Provider-Neutral Response**

The adapter must return a normalized response containing:

* raw provider request ID;  
* text or structured payload;  
* model;  
* provider;  
* usage;  
* finish reason;  
* latency;  
* warnings;  
* raw response reference where safe.

---

## **12.5 Fallback Provider**

Fallback is optional and configurable.

Fallback rules:

* only eligible failures trigger fallback;  
* attempts must be logged separately;  
* the same job remains the logical operation;  
* only one validated result becomes canonical;  
* fallback must satisfy required capabilities;  
* provider differences must not bypass validation.

---

# **13\. Structured AI Output Pipeline**

## **13.1 Pipeline Stages**

Provider Response  
      ↓  
Provider Normalization  
      ↓  
JSON Extraction  
      ↓  
Schema Validation  
      ↓  
Required-Field Validation  
      ↓  
Indonesian Narrative Validation  
      ↓  
Numerical and Logical Validation  
      ↓  
Contradiction Detection  
      ↓  
Canonicalization Decision  
      ↓  
Persistence

---

## **13.2 Invalid Output Handling**

Possible recovery sequence:

1. local deterministic parsing repair;  
2. provider-supported schema retry;  
3. correction prompt;  
4. fallback provider;  
5. job failure.

Invalid output must never replace the latest canonical analysis.

---

## **13.3 Language Validation**

Narrative fields should be checked for expected Bahasa Indonesia output.

Validation may use:

* deterministic field checks;  
* language detection;  
* terminology checks;  
* retry prompt.

Technical enums and keys remain English.

---

## **13.4 Logical Validation**

Examples:

* confidence must be between 0 and 100;  
* probability must be between 0 and 100;  
* required thesis status must be valid;  
* recommended action must use allowed enum;  
* stop and target values must be valid when provided;  
* current state must match analysis type;  
* closed-position analysis must not recommend opening the same position.

---

# **14\. Contradiction Detection Architecture**

## **14.1 Purpose**

Contradiction detection prevents unsupported AI drift.

---

## **14.2 Inputs**

The detector compares:

* previous canonical thesis;  
* proposed thesis;  
* previous support and resistance;  
* proposed levels;  
* previous stop and target assessment;  
* current recommendation;  
* previous confidence and probability;  
* latest evidence summary.

---

## **14.3 Detection Types**

Possible contradiction types:

* thesis-direction reversal;  
* unsupported thesis-status change;  
* unexplained level change;  
* unexplained target change;  
* unexplained stop change;  
* recommendation conflict;  
* probability inconsistency;  
* position-state mismatch;  
* missing history comparison.

---

## **14.4 Outcomes**

The detector may return:

* `PASS`  
* `PASS_WITH_EXPLANATION`  
* `REVIEW_REQUIRED`  
* `REJECT`

Only passing analyses may automatically update canonical state.

---

## **14.5 Non-Canonical Analysis**

A rejected or review-required analysis may be stored for debugging, but:

* it must not become the latest canonical analysis;  
* it must not change the thesis;  
* it must not change support or resistance;  
* it must not create user-facing trade instructions as authoritative.

---

# **15\. File Storage Architecture**

## **15.1 Storage Interface**

Recommended conceptual interface:

class FileStorage:  
    def save\_original(self, file: UploadFile, metadata: FileMetadata) \-\> StoredObject:  
        ...

    def save\_variant(self, source\_id: str, variant: FileVariant) \-\> StoredObject:  
        ...

    def open(self, object\_key: str) \-\> BinaryIO:  
        ...

    def delete(self, object\_key: str) \-\> None:  
        ...

    def create\_authorized\_access(self, object\_key: str) \-\> AccessReference:  
        ...

---

## **15.2 Local MVP Storage Layout**

Recommended layout:

/data/tradepilot/  
├── evidence/  
│   └── \<user-id\>/  
│       └── \<session-id\>/  
│           └── \<evidence-id\>/  
│               ├── original.\<ext\>  
│               ├── preview.webp  
│               ├── thumbnail.webp  
│               └── ai-input.webp  
├── exports/  
├── temporary/  
└── backups/

Application code must not depend directly on this path structure.

---

## **15.3 File Access**

The frontend must access private files through:

* an authenticated backend streaming endpoint; or  
* a short-lived signed application URL.

Direct public web-server exposure is prohibited.

---

## **15.4 File Processing**

File-processing steps may include:

* MIME validation;  
* image decode validation;  
* EXIF removal when appropriate;  
* orientation normalization;  
* thumbnail generation;  
* size normalization;  
* AI-input optimization;  
* checksum generation.

Original files remain unchanged.

---

# **16\. Database Architecture**

## **16.1 Database Role**

PostgreSQL is the source of truth for application state.

---

## **16.2 Transaction Boundaries**

Operations requiring a database transaction include:

* session creation;  
* position opening;  
* stop change;  
* target change;  
* partial exit;  
* final exit;  
* canonical analysis update;  
* thesis version update;  
* journal canonicalization.

File uploads require coordination between object storage and database records.

---

## **16.3 File and Database Consistency**

Recommended upload sequence:

1. create pending evidence record;  
2. store file;  
3. verify file;  
4. update evidence record to available;  
5. create timeline event.

Cleanup jobs must remove orphaned temporary files.

---

## **16.4 Database Access**

Only backend and worker services may access PostgreSQL.

The frontend must never connect directly to the database.

---

## **16.5 Connection Pooling**

Backend and worker must use bounded connection pools appropriate for VPS resources.

The architecture must avoid opening one unbounded connection per background job.

---

# **17\. Job Queue Architecture**

## **17.1 Job Categories**

Required job types:

* initial analysis;  
* watching update analysis;  
* open-position update analysis;  
* closing analysis;  
* journal generation;  
* context summary refresh;  
* image variant generation;  
* cleanup;  
* backup;  
* notification delivery.

---

## **17.2 Job Payload Design**

Queue payloads should contain identifiers, not full domain objects or image binaries.

Example:

{  
  "job\_id": "uuid",  
  "job\_type": "OPEN\_POSITION\_UPDATE",  
  "session\_id": "uuid",  
  "analysis\_request\_id": "uuid",  
  "requested\_by": "uuid"  
}

The worker loads authoritative data from PostgreSQL and file storage.

---

## **17.3 Job Persistence**

PostgreSQL must store authoritative job records.

Redis contains execution queue state, but PostgreSQL must retain:

* job ID;  
* job type;  
* status;  
* attempt count;  
* request metadata;  
* error metadata;  
* created time;  
* started time;  
* completed time.

---

## **17.4 Job Idempotency**

Each logical operation requires an idempotency key.

Examples:

initial-analysis:\<session-id\>:\<evidence-set-hash\>  
update-analysis:\<session-id\>:\<update-id\>  
journal-generation:\<session-id\>:\<position-version\>

---

## **17.5 Job Locks**

Distributed locks may be used to prevent:

* two canonical analyses for one update;  
* two journal generations for the same session state;  
* simultaneous conflicting position recalculations.

Locks must have expiry and safe ownership handling.

---

## **17.6 Job Progress**

Progress may be stored temporarily in Redis and finalized in PostgreSQL.

Suggested stages:

* `PREPARING_EVIDENCE`  
* `BUILDING_CONTEXT`  
* `CALLING_PROVIDER`  
* `VALIDATING_OUTPUT`  
* `SAVING_ANALYSIS`  
* `COMPLETED`

---

# **18\. Primary Data Flows**

## **18.1 Create Session Flow**

Browser  
  → Frontend  
  → POST /sessions  
  → API validation  
  → Session application service  
  → PostgreSQL transaction  
  → Timeline event  
  → Response  
  → Session page

---

## **18.2 Evidence Upload Flow**

Browser  
  → Upload request  
  → Backend authorization  
  → File validation  
  → Pending evidence record  
  → Persistent file storage  
  → Preview/thumbnail generation  
  → Evidence record completed  
  → Timeline event  
  → Frontend preview

Large-file upload design may later use direct signed upload to object storage, but local MVP storage should remain backend-controlled.

---

## **18.3 Initial Analysis Flow**

User submits initial analysis  
  → API validates readiness  
  → Analysis request created  
  → Job record created  
  → Queue message sent  
  → Worker loads session and evidence  
  → Context built  
  → Provider selected  
  → AI request executed  
  → Response normalized  
  → Schema and language validated  
  → Thesis created  
  → Analysis version persisted  
  → Canonical session state updated  
  → Timeline events created  
  → Job completed  
  → UI receives/polls completion

---

## **18.4 Follow-Up Update Flow**

New evidence uploaded  
  → Update record created  
  → Analysis job queued  
  → Worker loads canonical state  
  → Relevant history selected  
  → Latest and previous evidence compared  
  → Provider returns structured result  
  → Contradiction detection  
  → New analysis version persisted  
  → Thesis version updated when valid  
  → Canonical metrics updated  
  → Timeline updated

---

## **18.5 Position Opening Flow**

User submits actual entry  
  → API validates session state  
  → Position domain service validates  
  → Position created  
  → Entry created  
  → Stop created  
  → Targets created  
  → Entry thesis snapshot recorded  
  → Session becomes OPEN\_POSITION  
  → Timeline and audit records created  
  → Transaction committed

---

## **18.6 Position Closure and Journal Flow**

User records final exit  
  → Position recalculated  
  → Session closed  
  → Closing event persisted  
  → Closing analysis job queued  
  → Closing analysis completed  
  → Journal job queued  
  → Full session context built  
  → Journal generated and validated  
  → Journal version persisted  
  → User notified

---

# **19\. Authentication Architecture**

## **19.1 Recommended MVP Approach**

Use secure cookie-based authentication or an equivalent server-managed session strategy.

Requirements:

* HTTP-only cookies;  
* secure cookies in production;  
* same-site protection;  
* password hashing;  
* session expiry;  
* logout invalidation;  
* rate-limited login.

---

## **19.2 Authorization**

Every resource request must verify:

* authenticated user;  
* resource ownership;  
* allowed operation for current lifecycle state.

Single-user MVP does not remove the requirement for ownership checks.

---

## **19.3 Service-to-Service Trust**

Backend and worker may share:

* private application network;  
* database credentials;  
* queue credentials;  
* file-volume access.

These services must not be exposed publicly unless required.

---

# **20\. API Architecture**

## **20.1 API Style**

Recommended:

* REST-style JSON API;  
* versioned base path.

Example:

/api/v1/

---

## **20.2 Resource Groups**

/auth  
/sessions  
/evidence  
/analyses  
/positions  
/theses  
/journals  
/jobs  
/notifications  
/settings  
/usage

Detailed contracts will be defined in `API_SPEC.md`.

---

## **20.3 Error Contract**

API errors must include:

* stable English error code;  
* Indonesian user-facing message;  
* optional field errors;  
* correlation ID;  
* optional retryability indicator.

Example:

{  
  "error": {  
    "code": "INVALID\_STATUS\_TRANSITION",  
    "message": "Status session tidak memungkinkan tindakan ini.",  
    "correlation\_id": "uuid",  
    "retryable": false  
  }  
}

---

# **21\. Timeline and Audit Architecture**

## **21.1 Timeline Events**

Timeline events are user-facing historical records.

Examples:

* position opened;  
* evidence uploaded;  
* thesis weakened;  
* analysis completed;  
* stop changed;  
* position closed.

---

## **21.2 Audit Records**

Audit records provide technical traceability.

They may include:

* API actor;  
* request ID;  
* previous value;  
* new value;  
* source IP where appropriate;  
* job ID;  
* provider;  
* prompt version.

---

## **21.3 Event Creation**

Timeline and audit records should be created in the same transaction as the domain mutation when possible.

---

# **22\. Notification Architecture**

## **22.1 MVP Notifications**

MVP notifications are persisted in PostgreSQL and displayed in-app.

Events include:

* analysis completed;  
* analysis failed;  
* thesis weakened;  
* thesis invalidated;  
* journal generated;  
* provider configuration error.

---

## **22.2 Future Channels**

Future adapters may support:

* Telegram;  
* email;  
* browser push.

Notification generation should use an internal event interface so new channels do not modify domain logic.

---

# **23\. Observability Architecture**

## **23.1 Structured Logging**

All services must produce structured logs.

Recommended log fields:

* timestamp;  
* level;  
* service;  
* environment;  
* correlation ID;  
* user ID where safe;  
* session ID;  
* job ID;  
* provider;  
* model;  
* duration;  
* error code.

---

## **23.2 Correlation IDs**

Every API request and background job should have a correlation ID.

The ID should propagate through:

* API;  
* application service;  
* job record;  
* worker;  
* provider request;  
* error response.

---

## **23.3 Metrics**

Recommended metrics:

* API request count;  
* API latency;  
* API error rate;  
* upload count;  
* upload failure rate;  
* active jobs;  
* job duration;  
* job failure rate;  
* provider latency;  
* provider failure rate;  
* schema-validation failure rate;  
* language-validation failure rate;  
* fallback usage;  
* database pool usage;  
* storage usage.

---

## **23.4 Health Checks**

Required endpoints or checks:

* frontend health;  
* backend health;  
* database connectivity;  
* Redis connectivity;  
* worker heartbeat;  
* file-storage writeability;  
* provider configuration status, optional and non-blocking.

---

# **24\. Deployment Architecture**

## **24.1 VPS Topology**

Recommended single-VPS MVP topology:

Internet  
   │  
   ▼  
Reverse Proxy  
   ├── Next.js Frontend  
   └── FastAPI Backend

Private Docker Network  
   ├── PostgreSQL  
   ├── Redis  
   ├── Worker  
   ├── Scheduler  
   └── Backup Job

Persistent Volumes  
   ├── PostgreSQL Data  
   ├── Evidence Storage  
   ├── Backup Storage  
   └── Proxy Certificates

---

## **24.2 Publicly Exposed Services**

Only the reverse proxy should be publicly exposed.

PostgreSQL and Redis must not be publicly reachable.

---

## **24.3 Deployment Units**

Recommended containers:

tradepilot-web  
tradepilot-api  
tradepilot-worker  
tradepilot-scheduler  
tradepilot-postgres  
tradepilot-redis  
tradepilot-proxy  
tradepilot-backup

The scheduler and backup containers may be introduced when required.

---

## **24.4 Persistent Volumes**

Required persistent volumes:

* PostgreSQL data;  
* evidence storage;  
* backup storage;  
* reverse-proxy certificates.

Application containers should otherwise be replaceable.

---

## **24.5 Environment Separation**

Recommended environments:

* local development;  
* test;  
* production.

A staging environment is optional for MVP but recommended before major releases.

---

# **25\. Configuration Architecture**

## **25.1 Environment Variables**

Environment variables should configure:

* application environment;  
* database connection;  
* Redis connection;  
* authentication secrets;  
* AI provider secrets;  
* active provider;  
* active model;  
* upload limits;  
* storage paths;  
* logging;  
* backup paths;  
* allowed origins.

---

## **25.2 Database-Backed Configuration**

Non-secret user-changeable settings may be stored in PostgreSQL.

Examples:

* active provider;  
* active model;  
* fallback enabled;  
* default output language;  
* reminder interval;  
* UI preferences.

---

## **25.3 Secret Handling**

Secrets must:

* remain server-side;  
* not be committed;  
* not be returned through API responses;  
* be masked in settings;  
* be excluded from logs.

---

# **26\. Reliability Architecture**

## **26.1 Failure Isolation**

A provider failure must not make the rest of the application unavailable.

The user must still be able to:

* open sessions;  
* view prior analyses;  
* upload evidence;  
* record positions;  
* inspect journals.

---

## **26.2 Database Failure**

When PostgreSQL is unavailable:

* write operations fail safely;  
* jobs should pause or retry;  
* no partial canonical state should be created;  
* the system must return a clear service-unavailable response.

---

## **26.3 Redis Failure**

When Redis is unavailable:

* analysis submission should fail clearly or remain pending in PostgreSQL;  
* existing domain data remains accessible;  
* the system must not pretend a job was queued successfully.

A later design may include a queue-outbox recovery mechanism.

---

## **26.4 Storage Failure**

If file storage fails:

* evidence record must not become available;  
* analysis must not start using incomplete evidence;  
* temporary database state must be marked failed or cleaned up.

---

## **26.5 Provider Failure**

Provider failure may trigger:

* retry;  
* fallback;  
* final job failure.

Previous canonical analysis remains valid.

---

# **27\. Transactional Outbox Recommendation**

The system should use a transactional outbox pattern for critical asynchronous operations.

Examples:

* analysis job dispatch;  
* journal-generation dispatch;  
* notification dispatch.

Flow:

1. domain mutation and outbox event are committed together;  
2. dispatcher reads unpublished outbox records;  
3. event is sent to Redis;  
4. outbox record is marked published.

This prevents a state where:

* the database says a job exists;  
* but the queue message was never delivered.

The exact implementation may be phased into MVP if complexity must be controlled, but job consistency must still be guaranteed.

---

# **28\. Cache Strategy**

## **28.1 Allowed Cache Uses**

Redis or application cache may store:

* dashboard query results;  
* session-summary queries;  
* job progress;  
* short-lived provider capability metadata;  
* rate-limit counters.

---

## **28.2 Prohibited Cache Uses**

Cache must not be the only copy of:

* session status;  
* active thesis;  
* positions;  
* analyses;  
* journals;  
* evidence metadata;  
* audit records.

---

## **28.3 Cache Invalidation**

Canonical mutations must invalidate related:

* dashboard summaries;  
* session details;  
* position summaries;  
* journal lists.

---

# **29\. Search Architecture**

MVP search may use PostgreSQL capabilities.

Searchable content includes:

* ticker;  
* company name;  
* session title;  
* notes;  
* thesis narrative;  
* journal narrative.

Future scale may justify a dedicated search engine, but it is not required for MVP.

---

# **30\. Data Retention**

## **30.1 Default Retention**

Trade Session data and evidence are retained indefinitely unless the user performs an explicit deletion through a future administrative workflow.

---

## **30.2 Archive**

Archive changes visibility, not retention.

---

## **30.3 Temporary Files**

Temporary upload and processing files should be removed after:

* successful processing;  
* job failure after retention period;  
* scheduled cleanup.

---

# **31\. Backup and Recovery Architecture**

## **31.1 Backup Scope**

Backups must include:

* PostgreSQL;  
* original evidence;  
* relevant configuration;  
* prompt files;  
* deployment configuration.

---

## **31.2 Backup Coordination**

Database and evidence backups should be timestamped and coordinated sufficiently to restore a consistent application state.

---

## **31.3 Restore Testing**

A backup is not considered reliable until restoration is tested.

Detailed procedures will be defined in `BACKUP_RECOVERY_SPEC.md`.

---

# **32\. Scaling Strategy**

## **32.1 MVP Scale**

Expected MVP scale:

* one primary user;  
* limited active Trade Sessions;  
* several daily image uploads;  
* low concurrent AI jobs;  
* one VPS.

---

## **32.2 Vertical Scaling**

Initial scaling should use:

* additional VPS CPU;  
* additional memory;  
* faster storage;  
* worker concurrency tuning;  
* database index optimization.

---

## **32.3 Horizontal Worker Scaling**

Workers may later scale independently because they consume Redis jobs.

Requirements:

* idempotent jobs;  
* distributed locks;  
* shared database;  
* shared file storage;  
* provider rate-limit coordination.

---

## **32.4 Future Service Extraction**

Possible future extractions:

* AI orchestration service;  
* notification service;  
* file-processing service;  
* search service.

Extraction is not required until operational scale justifies it.

---

# **33\. Security Boundaries**

## **33.1 Public Boundary**

Public:

* reverse proxy;  
* frontend routes;  
* authorized API routes.

---

## **33.2 Private Boundary**

Private network only:

* PostgreSQL;  
* Redis;  
* worker control;  
* internal metrics;  
* storage paths.

---

## **33.3 External Boundary**

External outbound connections:

* Gemini;  
* DeepSeek;  
* future notification providers.

Outbound requests must use configured timeouts and must not expose unnecessary user data.

---

## **33.4 File Upload Boundary**

All uploaded files must be treated as untrusted.

Required controls:

* content-type validation;  
* image decode validation;  
* size limits;  
* generated filenames;  
* no executable serving;  
* optional malware scanning in future.

---

# **34\. Development Architecture**

## **34.1 Local Development**

Local development should run through Docker Compose or a documented hybrid setup.

Recommended local services:

* PostgreSQL;  
* Redis;  
* API;  
* worker;  
* frontend.

AI providers may be:

* called through real development credentials;  
* replaced by a mock provider for tests.

---

## **34.2 Mock AI Provider**

A deterministic mock provider is required for reliable development and automated tests.

The mock provider should support:

* valid structured output;  
* invalid schema simulation;  
* timeout simulation;  
* English-output error simulation;  
* contradiction simulation;  
* provider failure simulation.

---

## **34.3 Seed Data**

Development seed data should include:

* draft session;  
* watching session;  
* open position;  
* weakening thesis;  
* invalidated thesis;  
* partially closed position;  
* completed journal;  
* failed analysis.

---

# **35\. Testing Architecture**

## **35.1 Test Layers**

Required layers:

* domain unit tests;  
* application-service tests;  
* repository integration tests;  
* API tests;  
* job-worker tests;  
* provider-adapter contract tests;  
* structured-output validation tests;  
* frontend component tests;  
* end-to-end user-flow tests.

---

## **35.2 Critical Architecture Tests**

Must test:

* invalid lifecycle transitions;  
* duplicate job submission;  
* provider timeout;  
* fallback behavior;  
* schema failure;  
* contradiction rejection;  
* session restart recovery;  
* file access authorization;  
* analysis canonicalization;  
* transactional position updates;  
* journal regeneration after correction.

Detailed testing requirements will be defined in `TEST_PLAN.md`.

---

# **36\. Architecture Decision Records**

Important architectural decisions should be documented as ADRs.

Suggested initial ADRs:

ADR-001 Modular Monolith  
ADR-002 Next.js Frontend  
ADR-003 FastAPI Backend  
ADR-004 PostgreSQL as Source of Truth  
ADR-005 Redis-Backed Background Jobs  
ADR-006 Local Persistent File Storage for MVP  
ADR-007 AI Provider Abstraction  
ADR-008 Structured AI Output  
ADR-009 Canonical State Plus Immutable History  
ADR-010 Docker Compose VPS Deployment

ADRs should document:

* context;  
* decision;  
* alternatives;  
* consequences;  
* status.

---

# **37\. Architecture Constraints**

The implementation must comply with the following constraints:

1. no direct AI provider calls from the browser;  
2. no direct database access from the frontend;  
3. no public PostgreSQL or Redis exposure;  
4. no AI analysis in a blocking HTTP request;  
5. no binary evidence stored as the primary copy in PostgreSQL;  
6. no provider-specific logic inside domain services;  
7. no canonical state update before AI response validation;  
8. no closed-session reopening;  
9. no destructive overwrite of analysis history;  
10. no raw public access to private evidence;  
11. no API secrets committed to GitHub;  
12. no Redis-only authoritative domain state;  
13. no user-facing English AI narrative as the default output;  
14. no unbounded worker concurrency;  
15. no lifecycle mutation based only on frontend state.

---

# **38\. MVP Architecture Acceptance Criteria**

The architecture is accepted when:

1. frontend, API, worker, PostgreSQL, Redis, and storage responsibilities are clearly separated;  
2. Trade Session data persists across container restarts;  
3. evidence persists across deployments;  
4. AI jobs run asynchronously;  
5. Gemini and DeepSeek are accessed through provider adapters;  
6. structured AI responses are validated before persistence;  
7. invalid AI output cannot replace canonical analysis;  
8. every analysis version records its provider, model, prompt, schema, and evidence;  
9. canonical thesis and historical thesis versions are separated;  
10. position mutations are transactional;  
11. files are available only through authorized access;  
12. background jobs are idempotent;  
13. failed jobs are retryable;  
14. the system can recover after VPS restart;  
15. PostgreSQL and Redis are not publicly exposed;  
16. user-facing analysis remains in Bahasa Indonesia;  
17. internal engineering contracts remain in English;  
18. the architecture supports complete timeline and audit reconstruction;  
19. local development can run with documented services;  
20. the production stack can be deployed through Docker Compose on a VPS.

---

# **39\. Final Architecture Decision**

TradePilot AI will be implemented as a modular monolith deployed through Docker Compose on a self-hosted VPS.

The main runtime components are:

* Next.js frontend;  
* FastAPI backend;  
* Python background worker;  
* PostgreSQL;  
* Redis;  
* persistent private file storage;  
* reverse proxy;  
* Gemini and DeepSeek provider adapters.

PostgreSQL is the authoritative source of truth.

Redis supports asynchronous execution and temporary coordination.

Evidence is stored as private persistent files.

AI analyses are executed asynchronously, validated as structured output, checked for language and consistency, and stored as immutable versions before canonical Trade Session state is updated.

This architecture is designed to keep the MVP operationally simple while preserving the product’s most important requirement:

Every trade must retain its complete, consistent, and auditable story.

