# **OPEN\_CODE\_TASKS.md**

## **TradePilot AI Open Code Implementation Tasks**

**Document Version:** 1.0  
**Status:** Ready for Execution  
**Target:** TradePilot AI MVP  
**Source Control:** GitHub  
**Development Environment:** Local machine  
**Deployment Target:** Single VPS  
**Frontend:** Next.js with TypeScript  
**Backend:** FastAPI with Python  
**Database:** PostgreSQL  
**Background Worker:** Python worker  
**Primary AI Provider:** Gemini  
**Fallback AI Provider:** DeepSeek  
**User-Facing Analysis Language:** Indonesian  
**Engineering Language:** English

---

## **1\. Purpose**

This document defines the exact implementation tasks required to build the TradePilot AI MVP.

It is intended to be executed sequentially by Open Code or another coding agent.

Each task includes:

* task ID;  
* task title;  
* objective;  
* dependencies;  
* target files;  
* implementation instructions;  
* constraints;  
* acceptance criteria;  
* test requirements;  
* completion output.

The coding agent must complete one task at a time unless a task explicitly allows parallel execution.

---

## **2\. Product Context**

TradePilot AI is an AI Trading Workspace for following one stock trade from initial observation until closure.

The system does not automatically scan stocks or execute trades.

The core workflow is:

Create Trade Session  
        ↓  
Upload initial evidence  
        ↓  
Initial Analysis  
        ↓  
Watching Updates  
        ↓  
User confirms entry  
        ↓  
Open Position Updates  
        ↓  
Optional stop or target changes  
        ↓  
Optional Partial Exit  
        ↓  
Final Exit  
        ↓  
Closing Analysis  
        ↓  
Trade Journal

The main product principle is:

One Trade, One Story.

Each Trade Session belongs to one ticker and has one dedicated page containing its full longitudinal history.

---

## **3\. Mandatory System Rules**

The implementation must preserve the following rules throughout all tasks.

### **3.1 Canonical state**

`trade_state` is the authoritative current state.

AI output must never directly change:

* entry;  
* quantity;  
* remaining quantity;  
* active stop loss;  
* active target;  
* partial exit;  
* full exit;  
* session lifecycle state.

### **3.2 User confirmation**

The following require explicit user confirmation:

* position opened;  
* position corrected;  
* stop loss confirmed;  
* stop loss changed;  
* target confirmed;  
* target changed;  
* partial exit;  
* full exit;  
* session cancellation.

### **3.3 AI validation**

Every AI result must pass:

1. JSON parsing;  
2. JSON Schema validation;  
3. domain validation;  
4. canonical-state consistency validation;  
5. lifecycle validation.

### **3.4 Language**

All:

* code;  
* database names;  
* technical documentation;  
* JSON keys;  
* prompts;  
* implementation comments;

must use English.

All user-facing analysis generated for the dashboard must use Indonesian.

### **3.5 Deterministic calculations**

The backend owns:

* unrealized P/L;  
* realized P/L;  
* gross and net P/L;  
* return percentages;  
* risk percentage;  
* reward percentage;  
* risk-reward ratio;  
* distance to stop;  
* distance to target;  
* weighted average exit;  
* holding duration.

Use `Decimal`, not binary floating-point arithmetic.

### **3.6 Analysis immutability**

Accepted analyses are immutable.

Corrections must create a new version or superseding analysis rather than silently modifying an accepted historical result.

---

## **4\. Task Execution Protocol**

For every task, Open Code must:

1. read the listed source documents;  
2. inspect existing code before changing files;  
3. avoid unrelated refactoring;  
4. implement only the task scope;  
5. add or update tests;  
6. run relevant checks;  
7. report changed files;  
8. report commands executed;  
9. report test results;  
10. report any unresolved issue honestly.

A task is not complete merely because code was written.

It is complete only when its acceptance criteria pass.

---

## **5\. Global Coding Standards**

### **Python**

Use:

* Python 3.12;  
* type hints;  
* Ruff;  
* MyPy;  
* Pytest;  
* SQLAlchemy 2.x;  
* Pydantic 2.x;  
* async database access where appropriate.

### **TypeScript**

Use:

* strict TypeScript;  
* Next.js App Router;  
* ESLint;  
* Prettier;  
* typed API responses;  
* server components by default;  
* client components only where interaction requires them.

### **Database**

Use:

* PostgreSQL;  
* Alembic;  
* UUID primary keys;  
* timezone-aware timestamps;  
* explicit indexes;  
* transactional service methods.

### **API**

Use:

* predictable REST endpoints;  
* stable machine-readable error codes;  
* Pydantic request and response models;  
* authenticated ownership checks.

---

# **EPIC 0 — Repository Foundation**

## **TP-0001 — Initialize Repository Structure**

**Objective**

Create the initial TradePilot AI monorepo structure.

**Dependencies**

None.

**Target Files**

README.md  
.gitignore  
.env.example  
Makefile  
docker-compose.yml  
backend/  
worker/  
frontend/  
docs/  
schemas/  
scripts/  
infra/  
storage/.gitkeep

**Implementation Instructions**

Create the directory structure defined in `IMPLEMENTATION_PLAN.md`.

Add placeholders for:

* backend;  
* worker;  
* frontend;  
* schema package;  
* documentation;  
* deployment configuration;  
* local file storage.

Add a root `README.md` containing:

* project overview;  
* stack summary;  
* local prerequisites;  
* initial boot instructions;  
* repository structure.

**Constraints**

* Do not add application business logic.  
* Do not commit secrets.  
* Keep storage content excluded from Git.

**Acceptance Criteria**

* all required directories exist;  
* repository structure matches the implementation plan;  
* `.gitignore` excludes environment files, caches, uploads, logs, and database dumps;  
* `.env.example` contains placeholders only.

**Tests**

No automated tests required.

**Completion Output**

Report the created directory tree.

---

## **TP-0002 — Configure Backend Python Project**

**Objective**

Initialize the FastAPI backend Python project.

**Dependencies**

TP-0001.

**Target Files**

backend/pyproject.toml  
backend/app/\_\_init\_\_.py  
backend/app/main.py  
backend/app/config.py  
backend/app/logging.py  
backend/tests/test\_health.py

**Implementation Instructions**

Configure dependencies including:

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
ruff  
mypy

Create:

GET /health

Response:

{  
  "status": "ok",  
  "service": "tradepilot-backend"  
}

Add typed settings loaded from environment variables.

**Acceptance Criteria**

* backend starts locally;  
* `/health` returns HTTP 200;  
* configuration fails clearly when mandatory production settings are absent;  
* tests pass.

**Tests**

backend/tests/test\_health.py

---

## **TP-0003 — Configure Worker Python Project**

**Objective**

Create a separately runnable Python worker service.

**Dependencies**

TP-0001.

**Target Files**

worker/pyproject.toml  
worker/app/\_\_init\_\_.py  
worker/app/main.py  
worker/app/config.py  
worker/app/health.py  
worker/tests/test\_worker\_boot.py

**Implementation Instructions**

Create a worker process that can start, log its worker ID, and remain alive without processing jobs yet.

Configuration must support:

* database URL;  
* worker ID;  
* poll interval;  
* lease duration;  
* log level.

**Acceptance Criteria**

* worker starts independently;  
* worker reports its ID;  
* worker exits cleanly on termination;  
* no queue implementation is added yet.

---

## **TP-0004 — Configure Next.js Frontend**

**Objective**

Initialize the frontend application.

**Dependencies**

TP-0001.

**Target Files**

frontend/package.json  
frontend/next.config.ts  
frontend/tsconfig.json  
frontend/src/app/layout.tsx  
frontend/src/app/page.tsx  
frontend/src/app/health/page.tsx

**Implementation Instructions**

Initialize Next.js with:

* TypeScript;  
* App Router;  
* ESLint;  
* Tailwind CSS;  
* strict mode.

Create a simple TradePilot AI landing page and frontend health page.

**Acceptance Criteria**

* frontend starts;  
* home page loads;  
* TypeScript passes;  
* lint passes;  
* no hardcoded production API URL.

---

## **TP-0005 — Configure Local Docker Environment**

**Objective**

Create a reproducible local environment.

**Dependencies**

TP-0002, TP-0003, TP-0004.

**Target Files**

docker-compose.yml  
backend/Dockerfile  
worker/Dockerfile  
frontend/Dockerfile  
.env.example  
Makefile

**Implementation Instructions**

Configure services:

* PostgreSQL;  
* backend;  
* worker;  
* frontend.

Use persistent PostgreSQL and upload volumes.

Add Makefile commands:

make dev  
make down  
make logs  
make test  
make lint  
make migrate  
make validate-schemas  
make validate-fixtures

**Acceptance Criteria**

* all services start with Docker Compose;  
* backend connects to PostgreSQL;  
* volumes persist after restart;  
* health endpoints are reachable.

---

# **EPIC 1 — Database Foundation**

## **TP-0101 — Configure SQLAlchemy and Alembic**

**Objective**

Create database connection and migration foundations.

**Dependencies**

TP-0002, TP-0005.

**Target Files**

backend/app/database/base.py  
backend/app/database/session.py  
backend/app/database/types.py  
backend/alembic.ini  
backend/migrations/env.py

**Implementation Instructions**

Use SQLAlchemy 2.x with PostgreSQL.

Create:

* async application session;  
* migration-compatible sync connection where needed;  
* UUID support;  
* timezone-aware timestamp conventions;  
* Decimal-compatible numeric types.

**Acceptance Criteria**

* backend can connect to PostgreSQL;  
* Alembic can create and apply an empty migration;  
* test transaction rollback works.

---

## **TP-0102 — Implement User and Trade Session Models**

**Objective**

Create users and Trade Session persistence.

**Dependencies**

TP-0101.

**Target Files**

backend/app/models/user.py  
backend/app/models/trade\_session.py  
backend/app/models/enums.py  
backend/migrations/versions/\*\_users\_trade\_sessions.py

**Implementation Instructions**

Implement:

### **`users`**

* id;  
* email;  
* password hash or external identity reference;  
* is active;  
* created at;  
* updated at.

### **`trade_sessions`**

* id;  
* user ID;  
* ticker;  
* company name;  
* exchange;  
* currency;  
* session status;  
* created at;  
* updated at;  
* archived at.

Session statuses must align with specification.

**Acceptance Criteria**

* migration succeeds;  
* ticker is normalized consistently;  
* user ownership is enforced by foreign key;  
* status uses a controlled enum or validated string.

---

## **TP-0103 — Implement Canonical Trade State Model**

**Objective**

Create the authoritative Trade State table.

**Dependencies**

TP-0102.

**Target Files**

backend/app/models/trade\_state.py  
backend/migrations/versions/\*\_trade\_states.py

**Implementation Instructions**

Store:

* session ID;  
* position status;  
* entry price;  
* entry timestamp;  
* original quantity;  
* remaining quantity;  
* active stop loss;  
* active target;  
* average exit price;  
* realized P/L;  
* realized return;  
* thesis status;  
* last confirmed action timestamp;  
* state version;  
* created and updated timestamps.

Use numeric columns suitable for IDR and USD decimal values.

**Acceptance Criteria**

* one active Trade State per Trade Session;  
* quantity cannot be negative;  
* state can represent not opened, open, partial, and closed positions;  
* migration and model tests pass.

---

## **TP-0104 — Implement Trade Action Model**

**Objective**

Persist every user-confirmed state-changing action.

**Dependencies**

TP-0103.

**Target Files**

backend/app/models/trade\_action.py  
backend/migrations/versions/\*\_trade\_actions.py

**Implementation Instructions**

Store:

* action ID;  
* session ID;  
* action type;  
* confirmed timestamp;  
* price;  
* quantity;  
* optional note;  
* related analysis ID;  
* idempotency key;  
* payload JSON;  
* created at.

Add a uniqueness constraint for idempotency per user or session.

**Acceptance Criteria**

* duplicate idempotency keys cannot create duplicate actions;  
* action history can reconstruct canonical position changes;  
* timestamps are timezone-aware.

---

## **TP-0105 — Implement Evidence Models**

**Objective**

Create metadata storage for uploaded evidence.

**Dependencies**

TP-0102.

**Target Files**

backend/app/models/evidence.py  
backend/app/models/uploaded\_file.py  
backend/migrations/versions/\*\_evidence.py

**Implementation Instructions**

Store:

* evidence ID;  
* session ID;  
* evidence type;  
* file reference;  
* MIME type;  
* checksum;  
* upload timestamp;  
* market timestamp;  
* width;  
* height;  
* readability status;  
* extracted facts JSON;  
* active status;  
* replacement relationship.

**Acceptance Criteria**

* evidence belongs to one session;  
* replacement does not destroy audit history;  
* file path is relative rather than absolute.

---

## **TP-0106 — Implement Analysis and Job Models**

**Objective**

Persist analysis jobs, provider attempts, and accepted analyses.

**Dependencies**

TP-0102.

**Target Files**

backend/app/models/analysis\_job.py  
backend/app/models/analysis.py  
backend/app/models/validation\_attempt.py  
backend/app/models/provider\_request.py  
backend/app/models/provider\_response.py  
backend/migrations/versions/\*\_analysis\_models.py

**Implementation Instructions**

Implement job status lifecycle and analysis storage fields from the specifications.

Store separately:

* raw provider response;  
* parsed payload;  
* validated payload;  
* validation issues;  
* provider metadata;  
* prompt version;  
* schema name and version;  
* acceptance status;  
* superseding analysis ID.

**Acceptance Criteria**

* failed provider responses are auditable;  
* accepted analysis cannot be confused with raw output;  
* analysis schema version is mandatory;  
* job records support retry counts and leasing.

---

## **TP-0107 — Implement Context Summary and Session Event Models**

**Objective**

Persist compact memory and timeline events.

**Dependencies**

TP-0103, TP-0104, TP-0106.

**Target Files**

backend/app/models/context\_summary.py  
backend/app/models/session\_event.py  
backend/migrations/versions/\*\_context\_and\_events.py

**Implementation Instructions**

Context Summary must store:

* session ID;  
* context version;  
* source cutoff;  
* payload;  
* quality;  
* stale flag;  
* created at.

Session events must store:

* event type;  
* event timestamp;  
* related action;  
* related analysis;  
* price;  
* quantity;  
* compact summary.

**Acceptance Criteria**

* several Context Summary versions can be retained;  
* one latest context can be selected efficiently;  
* events can be returned chronologically.

---

## **TP-0108 — Implement Repository Layer**

**Objective**

Create typed repositories for persistence operations.

**Dependencies**

TP-0102 through TP-0107.

**Target Files**

backend/app/repositories/trade\_session.py  
backend/app/repositories/trade\_state.py  
backend/app/repositories/trade\_action.py  
backend/app/repositories/evidence.py  
backend/app/repositories/analysis\_job.py  
backend/app/repositories/analysis.py  
backend/app/repositories/context\_summary.py  
backend/app/repositories/session\_event.py

**Implementation Instructions**

Repositories handle persistence only.

Do not put lifecycle policy or financial calculations in repositories.

**Acceptance Criteria**

* repository tests pass;  
* all ownership-sensitive lookups accept user ID;  
* transaction boundaries remain controlled by service layer.

---

# **EPIC 2 — Production Schema Package**

## **TP-0201 — Materialize Production Schema Files**

**Objective**

Create the completed schema package in the repository.

**Dependencies**

TP-0001.

**Target Files**

schemas/production/v1/common.schema.json  
schemas/production/v1/market\_snapshot.schema.json  
schemas/production/v1/trade\_state.schema.json  
schemas/production/v1/evidence.schema.json  
schemas/production/v1/initial\_analysis.schema.json  
schemas/production/v1/watching\_update.schema.json  
schemas/production/v1/open\_position\_update.schema.json  
schemas/production/v1/partial\_exit\_review.schema.json  
schemas/production/v1/closing\_analysis.schema.json  
schemas/production/v1/context\_summary.schema.json  
schemas/production/v1/manifest.json

**Implementation Instructions**

Transfer the approved schema content into actual JSON files.

Ensure files contain plain valid JSON and no Markdown fences.

**Acceptance Criteria**

* all 11 files exist;  
* each JSON file parses successfully;  
* schema files are not modified to simplify implementation without documenting the change.

---

## **TP-0202 — Audit Common Schema Definitions**

**Objective**

Resolve every shared `$ref` before validator implementation.

**Dependencies**

TP-0201.

**Target Files**

schemas/production/v1/common.schema.json  
scripts/audit\_schema\_refs.py  
backend/tests/test\_schema\_references.py

**Implementation Instructions**

Scan every production schema for references into `common.schema.json`.

Verify definitions exist, including at least:

uuid  
nullableUuid  
uuidArray  
timestamp  
nullableTimestamp  
ticker  
companyName  
nullableCompanyName  
price  
nullablePrice  
quantity  
nullableQuantity  
percentage  
nullablePercentage  
probability  
nullableProbability  
confidenceScore  
nullableConfidenceScore  
signedNumber  
nullableSignedNumber  
nonNegativeInteger  
nullableNonNegativeInteger  
nullableNonNegativeNumber  
narrative  
nullableNarrative  
shortText  
nullableShortText  
shortTextArray  
priceLevel  
nullablePriceLevel  
priceLevelArray  
analysisMetadata  
analysisType  
updatePeriod  
sessionStatus  
thesisStatus  
positionHealth  
setupStatus  
setupQuality  
recommendedAction  
closingReason  
warningsAndMissingInformation  
materialChangeArray

Add missing definitions consistently.

**Constraints**

* do not create conflicting duplicate definitions;  
* preserve strict `additionalProperties` behavior;  
* keep enum values aligned across all schemas.

**Acceptance Criteria**

* every `$ref` resolves;  
* audit script exits zero;  
* unresolved references fail CI.

---

## **TP-0203 — Audit Schema Versions and Identifiers**

**Objective**

Ensure manifest, `$id`, file path, and version consistency.

**Dependencies**

TP-0202.

**Target Files**

schemas/production/v1/\*.json  
backend/tests/test\_schema\_manifest.py

**Implementation Instructions**

Verify:

* unique schema IDs;  
* unique schema names;  
* schema ID equals manifest registration;  
* schema version equals manifest version;  
* analysis type maps to correct schema;  
* no schema depends on an unregistered file.

**Acceptance Criteria**

* registry metadata is internally consistent;  
* all tests pass;  
* production package can be loaded without network access.

---

# **EPIC 3 — Schema Registry and Validation**

## **TP-0301 — Implement Manifest Loader**

**Objective**

Load and validate the production manifest.

**Dependencies**

TP-0203.

**Target Files**

backend/app/schemas/manifest.py  
backend/app/schemas/errors.py  
backend/tests/test\_manifest\_loader.py

**Implementation Instructions**

Create typed models for manifest entries and registries.

Validate:

* manifest status;  
* schema uniqueness;  
* active schemas;  
* dependencies;  
* required analysis mappings;  
* file existence.

**Acceptance Criteria**

* valid manifest loads;  
* malformed manifest returns stable error;  
* application startup fails for missing required schema.

---

## **TP-0302 — Implement Local Schema Registry**

**Objective**

Create local schema resolution and compiled-validator caching.

**Dependencies**

TP-0301.

**Target Files**

backend/app/schemas/registry.py  
backend/app/schemas/resolver.py  
backend/tests/test\_schema\_registry.py

**Implementation Instructions**

Use Draft 2020-12 and `referencing`.

The registry must support:

get(name, version)  
get\_by\_analysis\_type(analysis\_type)  
get\_by\_schema\_id(schema\_id)

Remote network schema fetching must be disabled.

**Acceptance Criteria**

* all active schemas compile;  
* local `$ref` values resolve;  
* unknown or inactive versions are rejected;  
* validator cache is reusable.

---

## **TP-0303 — Implement JSON Schema Validation Service**

**Objective**

Validate payloads and normalize errors.

**Dependencies**

TP-0302.

**Target Files**

backend/app/validation/json\_schema.py  
backend/app/validation/issues.py  
backend/app/validation/json\_pointer.py  
backend/tests/test\_json\_schema\_validation.py

**Implementation Instructions**

Return normalized issues containing:

* code;  
* category;  
* severity;  
* JSON Pointer path;  
* message;  
* expected;  
* actual.

Collect multiple errors where practical.

**Acceptance Criteria**

* missing fields are reported;  
* unknown properties are rejected;  
* conditional rules work;  
* invalid UUID and timestamps are detected;  
* paths use JSON Pointer.

---

## **TP-0304 — Implement Decimal Calculation Utilities**

**Objective**

Create authoritative deterministic financial calculations.

**Dependencies**

TP-0103.

**Target Files**

backend/app/calculations/decimal\_utils.py  
backend/app/calculations/market.py  
backend/app/calculations/position.py  
backend/app/calculations/exits.py  
backend/tests/calculations/

**Implementation Instructions**

Implement:

* market change;  
* spread;  
* percentage change;  
* unrealized P/L;  
* unrealized return;  
* distance to stop;  
* distance to target;  
* risk percentage;  
* reward percentage;  
* risk-reward ratio;  
* partial realized P/L;  
* weighted average exit;  
* gross and net closing results.

**Acceptance Criteria**

* calculations use `Decimal`;  
* IDR and USD precision rules pass;  
* BBRI fixture produces weighted exit 2910 and gross P/L 11000;  
* no floating-point artifacts.

---

## **TP-0305 — Implement Market Snapshot Domain Validator**

**Objective**

Validate market relationships and calculations.

**Dependencies**

TP-0303, TP-0304.

**Target Files**

backend/app/validation/market\_snapshot.py  
backend/tests/validation/test\_market\_snapshot.py

**Implementation Instructions**

Implement domain rules from `DOMAIN_VALIDATION_RULES.md`, including:

* OHLC relationships;  
* average range;  
* bid/offer;  
* spread;  
* change;  
* timestamps;  
* update-period consistency.

**Acceptance Criteria**

* valid fixture passes;  
* each blocking market error has a test;  
* stable error codes are returned.

---

## **TP-0306 — Implement Trade State Domain Validator**

**Objective**

Validate canonical position structure.

**Dependencies**

TP-0303, TP-0304.

**Target Files**

backend/app/validation/trade\_state.py  
backend/tests/validation/test\_trade\_state.py

**Implementation Instructions**

Validate:

* not-opened state;  
* open state;  
* partial state;  
* closed state;  
* quantity conservation;  
* active level validity;  
* timestamps;  
* confirmed-action consistency.

**Acceptance Criteria**

* invalid position combinations fail;  
* closed state cannot retain active stop or target;  
* remaining quantity is validated.

---

## **TP-0307 — Implement Entry, Stop, Target, and Risk Validators**

**Objective**

Validate proposed trading plans and price relationships.

**Dependencies**

TP-0304, TP-0305.

**Target Files**

backend/app/validation/entry\_plan.py  
backend/app/validation/stop\_loss.py  
backend/app/validation/target.py  
backend/app/validation/risk\_reward.py  
backend/tests/validation/test\_entry\_stop\_target.py

**Acceptance Criteria**

* exact and zone entries validate;  
* stop below entry is enforced for initial long setup;  
* target above entry is enforced;  
* maximum acceptable entry is validated;  
* 5% risk boundary is tested;  
* risk-reward calculations match backend.

---

## **TP-0308 — Implement Canonical State Consistency Validator**

**Objective**

Prevent AI payloads from contradicting confirmed Trade State.

**Dependencies**

TP-0306, TP-0307.

**Target Files**

backend/app/validation/state\_consistency.py  
backend/tests/validation/test\_state\_consistency.py

**Implementation Instructions**

Compare payload values against canonical state:

* session ID;  
* ticker;  
* entry;  
* original quantity;  
* remaining quantity;  
* active stop;  
* active target;  
* position status.

Distinguish active values from proposals.

**Acceptance Criteria**

* altered AI entry is rejected;  
* altered quantity is rejected;  
* proposed stop may differ but active stop may not;  
* canonical state remains untouched after failure.

---

## **TP-0309 — Implement Partial Exit Validator**

**Objective**

Validate partial-exit transitions and calculations.

**Dependencies**

TP-0304, TP-0306.

**Target Files**

backend/app/validation/partial\_exit.py  
backend/tests/validation/test\_partial\_exit.py

**Acceptance Criteria**

* exited plus remaining quantity equals previous remaining quantity;  
* partial exit cannot reduce remaining to zero;  
* realized P/L matches;  
* average exit across repeated partial exits matches.

---

## **TP-0310 — Implement Closing Validator**

**Objective**

Validate final exit, weighted results, and timeline.

**Dependencies**

TP-0309.

**Target Files**

backend/app/validation/closing.py  
backend/app/validation/timeline.py  
backend/tests/validation/test\_closing.py

**Acceptance Criteria**

* final exit quantity matches remaining quantity;  
* total exits equal original quantity;  
* weighted exit matches;  
* gross and net results match;  
* timeline order is enforced;  
* closing reason maps to session status.

---

## **TP-0311 — Implement Context Summary Validator**

**Objective**

Validate compact memory against canonical sources.

**Dependencies**

TP-0308, TP-0310.

**Target Files**

backend/app/validation/context\_summary.py  
backend/tests/validation/test\_context\_summary\_validation.py

**Acceptance Criteria**

* context cannot override canonical entry or quantity;  
* pending proposals are preserved;  
* cutoff timestamps are enforced;  
* stale context fails before new analysis.

---

## **TP-0312 — Implement Unified Validation Service**

**Objective**

Run all validation layers through one interface.

**Dependencies**

TP-0303 through TP-0311.

**Target Files**

backend/app/validation/service.py  
backend/app/validation/registry.py  
backend/tests/validation/test\_validation\_service.py

**Implementation Instructions**

Implement:

validate(  
    payload,  
    expected\_analysis\_type,  
    trade\_state,  
    session\_status\_before\_job,  
    context\_summary,  
)

Run:

1. schema validation;  
2. domain validators;  
3. state consistency;  
4. lifecycle checks;  
5. narrative checks.

**Acceptance Criteria**

* one result model is returned;  
* all issues are normalized;  
* blocking errors set `valid = false`;  
* warnings remain available.

---

# **EPIC 4 — Fixture Suite**

## **TP-0401 — Create Base Fixture Factories**

**Objective**

Create deterministic reusable fixture factories.

**Dependencies**

TP-0304.

**Target Files**

backend/tests/factories/market\_snapshot\_factory.py  
backend/tests/factories/trade\_state\_factory.py  
backend/tests/factories/evidence\_factory.py  
backend/tests/factories/analysis\_factory.py  
backend/tests/factories/context\_factory.py

**Acceptance Criteria**

* factories use fixed IDs and timestamps;  
* deterministic calculations are generated automatically;  
* overrides can modify nested values safely.

---

## **TP-0402 — Create Phase 1 Schema Fixtures**

**Objective**

Create initial valid and invalid fixture set.

**Dependencies**

TP-0401, TP-0312.

**Target Files**

backend/tests/fixtures/manifests/  
backend/tests/fixtures/schemas/  
backend/tests/fixtures/domain/

**Required Initial Fixtures**

* valid manifest;  
* valid Market Snapshot;  
* valid watching Trade State;  
* valid open Trade State;  
* valid partial Trade State;  
* valid closed Trade State;  
* valid Open Position Update;  
* entry mismatch;  
* quantity mismatch;  
* active stop mismatch;  
* active target mismatch;  
* valid partial exit;  
* valid closing result.

**Acceptance Criteria**

* valid fixtures pass;  
* invalid fixtures fail for expected code and path;  
* fixture tests run without live APIs.

---

## **TP-0403 — Implement Fixture Validation CLI**

**Objective**

Add commands to validate all fixtures.

**Dependencies**

TP-0402.

**Target Files**

backend/app/schema\_validation/validate\_fixtures.py  
scripts/validate\_fixtures.py

**Acceptance Criteria**

Commands support filters by:

* schema;  
* category;  
* scenario.

The command exits nonzero on failure.

---

# **EPIC 5 — Lifecycle and Canonical Actions**

## **TP-0501 — Implement Trade Session Service**

**Objective**

Create sessions and initialize canonical state.

**Dependencies**

TP-0108.

**Target Files**

backend/app/services/trade\_session.py  
backend/tests/services/test\_trade\_session.py

**Acceptance Criteria**

* session is created in `DRAFT`;  
* empty Trade State is created atomically;  
* ticker and currency are normalized;  
* session ownership is enforced.

---

## **TP-0502 — Implement Session Lifecycle Service**

**Objective**

Enforce allowed session transitions.

**Dependencies**

TP-0501, TP-0312.

**Target Files**

backend/app/lifecycle/service.py  
backend/app/lifecycle/transitions.py  
backend/tests/lifecycle/test\_transitions.py

**Acceptance Criteria**

* valid transitions succeed;  
* invalid transitions return stable errors;  
* closed and archived sessions cannot reopen;  
* temporary `ANALYZING` preserves prior status.

---

## **TP-0503 — Implement Position Open Confirmation**

**Objective**

Allow a user to confirm a real position.

**Dependencies**

TP-0502.

**Target Files**

backend/app/services/actions/open\_position.py  
backend/tests/services/actions/test\_open\_position.py

**Implementation Instructions**

Atomically:

* validate Watching state;  
* create `POSITION_OPENED` action;  
* set entry and quantities;  
* set confirmed stop and target if supplied;  
* change state to `OPEN`;  
* change session to `OPEN_POSITION`;  
* write event;  
* mark context stale.

**Acceptance Criteria**

* repeated idempotency key is safe;  
* AI proposal is not required to match exactly;  
* user-confirmed values become canonical.

---

## **TP-0504 — Implement Stop and Target Confirmation Actions**

**Objective**

Support confirming and changing stop and target.

**Dependencies**

TP-0503.

**Target Files**

backend/app/services/actions/stop\_loss.py  
backend/app/services/actions/target.py  
backend/tests/services/actions/test\_stop\_target.py

**Acceptance Criteria**

* active levels change only after confirmation;  
* proposals remain separate;  
* invalid long-position relationships fail;  
* events and actions are persisted.

---

## **TP-0505 — Implement Partial Exit Action**

**Objective**

Apply a user-confirmed partial exit.

**Dependencies**

TP-0503, TP-0309.

**Target Files**

backend/app/services/actions/partial\_exit.py  
backend/tests/services/actions/test\_partial\_exit\_action.py

**Acceptance Criteria**

* quantity conservation passes;  
* remaining quantity stays above zero;  
* realized P/L updates;  
* average exit updates;  
* status changes to `PARTIALLY_CLOSED`.

---

## **TP-0506 — Implement Full Exit Action**

**Objective**

Close the remaining position.

**Dependencies**

TP-0505, TP-0310.

**Target Files**

backend/app/services/actions/full\_exit.py  
backend/tests/services/actions/test\_full\_exit\_action.py

**Acceptance Criteria**

* remaining quantity becomes zero;  
* active stop and target become null;  
* final weighted result is stored;  
* correct closed status is assigned;  
* duplicate confirmation is safe.

---

## **TP-0507 — Implement Session Cancellation and Archive Actions**

**Objective**

Support safe cancellation and archiving.

**Dependencies**

TP-0502.

**Target Files**

backend/app/services/actions/cancel.py  
backend/app/services/actions/archive.py  
backend/tests/services/actions/test\_cancel\_archive.py

**Acceptance Criteria**

* unentered Watching session can be cancelled;  
* open positions cannot be cancelled as though no trade existed;  
* terminal sessions can be archived;  
* archived sessions remain read-only.

---

# **EPIC 6 — Evidence Upload**

## **TP-0601 — Implement Local File Storage Adapter**

**Objective**

Create secure filesystem-based evidence storage.

**Dependencies**

TP-0105.

**Target Files**

backend/app/storage/base.py  
backend/app/storage/local.py  
backend/tests/storage/test\_local\_storage.py

**Acceptance Criteria**

* paths are scoped by user and session;  
* path traversal is prevented;  
* files receive generated names;  
* checksum is calculated;  
* original filename is metadata only.

---

## **TP-0602 — Implement Evidence Upload Validation**

**Objective**

Validate uploaded image files.

**Dependencies**

TP-0601.

**Target Files**

backend/app/evidence/upload\_validation.py  
backend/app/evidence/image\_processing.py  
backend/tests/evidence/test\_upload\_validation.py

**Acceptance Criteria**

* PNG, JPEG, and WebP are supported;  
* unsupported types fail;  
* oversized files fail;  
* corrupt images fail;  
* dimensions are stored;  
* original file is preserved.

---

## **TP-0603 — Implement Evidence Service**

**Objective**

Create, replace, list, and deactivate evidence.

**Dependencies**

TP-0602, TP-0108.

**Target Files**

backend/app/services/evidence.py  
backend/tests/services/test\_evidence\_service.py

**Acceptance Criteria**

* evidence belongs to session owner;  
* replacement preserves previous record;  
* required evidence can be queried by analysis type;  
* market timestamp is retained separately from upload timestamp.

---

# **EPIC 7 — AI Provider Layer**

## **TP-0701 — Define Provider Contracts**

**Objective**

Create provider-independent request and response types.

**Dependencies**

TP-0302.

**Target Files**

backend/app/ai/providers/base.py  
backend/app/ai/providers/models.py  
backend/app/ai/providers/capabilities.py  
backend/tests/ai/test\_provider\_contract.py

**Acceptance Criteria**

* provider adapters share one interface;  
* provider response stores raw output and metadata;  
* image support and structured-output capability are declared.

---

## **TP-0702 — Implement Prompt Registry**

**Objective**

Version and load prompts for every analysis type.

**Dependencies**

TP-0701.

**Target Files**

backend/app/ai/prompts/registry.py  
backend/app/ai/prompts/initial\_analysis\_v1.py  
backend/app/ai/prompts/watching\_update\_v1.py  
backend/app/ai/prompts/open\_position\_update\_v1.py  
backend/app/ai/prompts/partial\_exit\_review\_v1.py  
backend/app/ai/prompts/closing\_analysis\_v1.py  
backend/tests/ai/test\_prompt\_registry.py

**Implementation Instructions**

Prompts must:

* instruct Indonesian output;  
* distinguish facts from interpretations;  
* prohibit fabricated unreadable values;  
* preserve canonical state;  
* demand JSON only;  
* identify proposals as non-canonical.

**Acceptance Criteria**

* every analysis type has a registered prompt;  
* prompt version is stored;  
* unknown prompt version fails clearly.

---

## **TP-0703 — Implement Gemini Provider**

**Objective**

Call Gemini with text, image evidence, and structured-output instructions.

**Dependencies**

TP-0701, TP-0702.

**Target Files**

backend/app/ai/providers/gemini.py  
backend/tests/ai/providers/test\_gemini.py

**Acceptance Criteria**

* adapter supports mocked successful response;  
* timeout, refusal, and rate-limit errors are classified;  
* API key is not logged;  
* request includes schema contract.

---

## **TP-0704 — Implement DeepSeek Provider**

**Objective**

Implement DeepSeek as fallback using the same output contract.

**Dependencies**

TP-0701, TP-0702.

**Target Files**

backend/app/ai/providers/deepseek.py  
backend/tests/ai/providers/test\_deepseek.py

**Acceptance Criteria**

* response model matches Gemini adapter;  
* output schema expectations are identical;  
* provider-specific limitations are handled without changing application payload.

---

## **TP-0705 — Implement JSON Extraction and Parsing**

**Objective**

Extract exactly one valid JSON object from provider output.

**Dependencies**

TP-0703.

**Target Files**

backend/app/ai/parsing/json\_extractor.py  
backend/app/ai/parsing/json\_parser.py  
backend/tests/ai/parsing/

**Acceptance Criteria**

* plain JSON parses;  
* Markdown fences are removed;  
* leading or trailing commentary can be isolated safely;  
* multiple objects fail;  
* arrays fail;  
* NaN and Infinity fail;  
* duplicate critical keys fail.

---

## **TP-0706 — Implement Provider Repair Service**

**Objective**

Repair invalid provider output with bounded retries.

**Dependencies**

TP-0705, TP-0312.

**Target Files**

backend/app/ai/repair/service.py  
backend/app/ai/repair/prompt\_builder.py  
backend/tests/ai/test\_repair\_service.py

**Acceptance Criteria**

* repair prompt includes normalized validation errors;  
* canonical facts are explicitly protected;  
* repaired response must return JSON only;  
* maximum attempts are enforced.

---

## **TP-0707 — Implement Provider Fallback Service**

**Objective**

Use DeepSeek when Gemini and repair fail.

**Dependencies**

TP-0704, TP-0706.

**Target Files**

backend/app/ai/providers/router.py  
backend/tests/ai/test\_provider\_fallback.py

**Acceptance Criteria**

* configured provider order is respected;  
* raw responses from all attempts are stored;  
* only validated final response is accepted;  
* all failures produce one final job error.

---

# **EPIC 8 — Job Queue and Worker**

## **TP-0801 — Implement PostgreSQL Job Queue**

**Objective**

Create durable background job claiming.

**Dependencies**

TP-0106.

**Target Files**

backend/app/jobs/queue.py  
backend/app/jobs/lease.py  
backend/tests/jobs/test\_job\_queue.py

**Acceptance Criteria**

* one worker claims a job atomically;  
* duplicate concurrent claims are prevented;  
* expired lease can be reclaimed;  
* job attempts are tracked.

---

## **TP-0802 — Implement Analysis Job Creation Service**

**Objective**

Validate and enqueue requested analyses.

**Dependencies**

TP-0502, TP-0603, TP-0801.

**Target Files**

backend/app/services/analysis\_jobs.py  
backend/tests/services/test\_analysis\_job\_creation.py

**Acceptance Criteria**

* analysis type is valid for lifecycle;  
* required evidence is present;  
* duplicate active jobs are prevented;  
* previous status is stored before entering `ANALYZING`.

---

## **TP-0803 — Implement Provider Context Builder**

**Objective**

Construct the full AI request context.

**Dependencies**

TP-0702, TP-0603.

**Target Files**

backend/app/ai/context\_builder.py  
backend/tests/ai/test\_context\_builder.py

**Context Includes**

* canonical Trade State;  
* current session metadata;  
* Context Summary;  
* latest accepted analysis;  
* new evidence;  
* required schema;  
* deterministic market values;  
* output language.

**Acceptance Criteria**

* canonical facts are clearly separated;  
* stale context fails;  
* evidence order is deterministic;  
* provider limits are respected.

---

## **TP-0804 — Implement Analysis Processor**

**Objective**

Run one complete analysis job.

**Dependencies**

TP-0802, TP-0803, TP-0707, TP-0312.

**Target Files**

worker/app/processors/analysis.py  
backend/app/ai/analysis\_pipeline.py  
backend/tests/ai/test\_analysis\_pipeline.py

**Processing Steps**

1. claim job;  
2. load canonical state;  
3. load context;  
4. load evidence;  
5. call provider;  
6. parse response;  
7. inject backend-owned fields;  
8. validate;  
9. repair if needed;  
10. fallback if needed;  
11. persist accepted analysis;  
12. rebuild context;  
13. complete job;  
14. restore session status.

**Acceptance Criteria**

* failed validation never creates accepted analysis;  
* canonical state is not mutated;  
* accepted analysis is immutable;  
* job status reflects exact processing stage.

---

## **TP-0805 — Implement Worker Polling and Heartbeat**

**Objective**

Run analysis processing continuously and safely.

**Dependencies**

TP-0804.

**Target Files**

worker/app/main.py  
worker/app/consumers/analysis\_jobs.py  
worker/app/heartbeat.py  
worker/tests/test\_worker\_processing.py

**Acceptance Criteria**

* worker polls at configured interval;  
* heartbeat is stored;  
* graceful shutdown releases or expires leases safely;  
* processing errors do not crash the worker loop.

---

# **EPIC 9 — Context Memory**

## **TP-0901 — Implement Material History Selector**

**Objective**

Select important events for longitudinal memory.

**Dependencies**

TP-0107, TP-0506.

**Target Files**

backend/app/context/history\_selector.py  
backend/tests/context/test\_history\_selector.py

**Preserve**

* original setup;  
* valid entry signal;  
* position opened;  
* thesis changes;  
* support and resistance changes;  
* stop changes;  
* target changes;  
* partial exits;  
* final exit.

**Acceptance Criteria**

* repeated minor updates are compressed;  
* user-confirmed actions are never removed;  
* maximum event count is respected.

---

## **TP-0902 — Implement Context Summary Builder**

**Objective**

Generate `context_summary.schema.json` from canonical data.

**Dependencies**

TP-0901, TP-0311.

**Target Files**

backend/app/context/builder.py  
backend/tests/context/test\_context\_builder.py

**Acceptance Criteria**

* canonical facts match Trade State;  
* latest accepted analysis is represented;  
* pending proposals remain unresolved;  
* original thesis is preserved;  
* chart timestamps and limitations are retained;  
* output validates.

---

## **TP-0903 — Implement Context Freshness Service**

**Objective**

Detect and rebuild stale context.

**Dependencies**

TP-0902.

**Target Files**

backend/app/context/freshness.py  
backend/tests/context/test\_context\_freshness.py

**Acceptance Criteria**

* new accepted analysis makes previous context stale;  
* user action makes previous context stale;  
* evidence replacement makes context stale;  
* stale context is rebuilt before analysis.

---

## **TP-0904 — Integrate Context Rebuild Triggers**

**Objective**

Rebuild context after every material event.

**Dependencies**

TP-0903, TP-0804.

**Target Files**

backend/app/services/context\_rebuild.py  
backend/tests/context/test\_rebuild\_triggers.py

**Acceptance Criteria**

Context is rebuilt after:

* accepted analysis;  
* entry confirmation;  
* stop change;  
* target change;  
* partial exit;  
* full exit;  
* evidence replacement.

---

# **EPIC 10 — API Layer**

## **TP-1001 — Implement Authentication Foundation**

**Objective**

Provide secure access for the private MVP.

**Dependencies**

TP-0102.

**Target Files**

backend/app/auth/  
backend/app/api/dependencies.py  
backend/tests/auth/

**Implementation Instructions**

Use either:

* local email/password with secure hashing and HTTP-only session cookies; or  
* approved external identity provider.

Document the selected approach.

**Acceptance Criteria**

* unauthenticated users cannot access session data;  
* ownership is available in route dependencies;  
* secrets and password hashes are protected.

---

## **TP-1002 — Implement Trade Session APIs**

**Objective**

Create and retrieve Trade Sessions.

**Dependencies**

TP-0501, TP-1001.

**Target Files**

backend/app/api/routes/trade\_sessions.py  
backend/app/api/models/trade\_sessions.py  
backend/tests/api/test\_trade\_sessions.py

**Endpoints**

POST /api/trade-sessions  
GET /api/trade-sessions  
GET /api/trade-sessions/{session\_id}  
PATCH /api/trade-sessions/{session\_id}  
POST /api/trade-sessions/{session\_id}/ready  
POST /api/trade-sessions/{session\_id}/archive

**Acceptance Criteria**

* all queries are user-scoped;  
* session detail includes canonical state and allowed actions;  
* invalid transitions return stable codes.

---

## **TP-1003 — Implement Evidence APIs**

**Objective**

Expose evidence upload and listing.

**Dependencies**

TP-0603, TP-1001.

**Target Files**

backend/app/api/routes/evidence.py  
backend/tests/api/test\_evidence.py

**Acceptance Criteria**

* multipart uploads work;  
* files are served only to owner;  
* invalid file returns clear Indonesian user message;  
* evidence listing is chronological.

---

## **TP-1004 — Implement Analysis APIs**

**Objective**

Create jobs and retrieve results.

**Dependencies**

TP-0802, TP-1001.

**Target Files**

backend/app/api/routes/analyses.py  
backend/app/api/routes/analysis\_jobs.py  
backend/tests/api/test\_analyses.py

**Endpoints**

POST /api/trade-sessions/{session\_id}/analyses  
GET /api/trade-sessions/{session\_id}/analyses  
GET /api/analyses/{analysis\_id}  
GET /api/analysis-jobs/{job\_id}  
POST /api/analysis-jobs/{job\_id}/retry

**Acceptance Criteria**

* request returns job immediately;  
* duplicate running job is rejected;  
* accepted analysis payload is returned;  
* raw provider response is not exposed to normal users.

---

## **TP-1005 — Implement Trade Action APIs**

**Objective**

Expose user confirmation workflows.

**Dependencies**

TP-0503 through TP-0507.

**Target Files**

backend/app/api/routes/trade\_actions.py  
backend/tests/api/test\_trade\_actions.py

**Endpoints**

POST /actions/open-position  
POST /actions/confirm-stop  
POST /actions/change-stop  
POST /actions/confirm-target  
POST /actions/change-target  
POST /actions/partial-exit  
POST /actions/full-exit  
POST /actions/cancel

**Acceptance Criteria**

* idempotency key is accepted;  
* confirmed values become canonical;  
* AI proposals are optional defaults only;  
* invalid lifecycle action fails safely.

---

## **TP-1006 — Implement Context and Timeline APIs**

**Objective**

Expose longitudinal session information.

**Dependencies**

TP-0904.

**Target Files**

backend/app/api/routes/context.py  
backend/app/api/routes/timeline.py  
backend/tests/api/test\_context\_timeline.py

**Acceptance Criteria**

* latest Context Summary can be retrieved;  
* session timeline is chronological;  
* each event includes related action or analysis when available.

---

## **TP-1007 — Implement Unified API Error Contract**

**Objective**

Return stable errors across all APIs.

**Dependencies**

TP-1002 through TP-1006.

**Target Files**

backend/app/api/errors.py  
backend/app/api/exception\_handlers.py  
backend/tests/api/test\_error\_contract.py

**Acceptance Criteria**

Response contains:

{  
  "error": {  
    "code": "STABLE\_CODE",  
    "message": "Indonesian user-facing message",  
    "details": {}  
  }  
}

Detailed internal stack traces are never exposed.

---

# **EPIC 11 — Frontend Foundation**

## **TP-1101 — Implement Typed API Client**

**Objective**

Create a typed frontend client for backend endpoints.

**Dependencies**

TP-1002 through TP-1006.

**Target Files**

frontend/src/lib/api/  
frontend/src/types/

**Acceptance Criteria**

* all responses are typed;  
* authentication errors are handled;  
* API base URL comes from configuration;  
* no duplicated request logic across components.

---

## **TP-1102 — Implement Session List Page**

**Objective**

Display all Trade Sessions.

**Dependencies**

TP-1101.

**Target Files**

frontend/src/app/sessions/page.tsx  
frontend/src/features/sessions/

**Display**

* ticker;  
* company;  
* status;  
* entry;  
* stop;  
* target;  
* latest recommendation;  
* last updated time.

**Acceptance Criteria**

* sessions link to dedicated detail pages;  
* terminal and active sessions are visually distinguishable;  
* empty state is implemented.

---

## **TP-1103 — Implement New Trade Session Page**

**Objective**

Allow creation of one ticker session.

**Dependencies**

TP-1101.

**Target Files**

frontend/src/app/sessions/new/page.tsx  
frontend/src/features/sessions/create-session-form.tsx

**Acceptance Criteria**

* ticker, company, exchange, and currency can be entered;  
* successful creation redirects to session detail;  
* validation messages are clear.

---

## **TP-1104 — Implement Trade Session Page Shell**

**Objective**

Create the dedicated One Trade One Story page.

**Dependencies**

TP-1102.

**Target Files**

frontend/src/app/sessions/\[sessionId\]/page.tsx  
frontend/src/features/trade-session/

**Sections**

* session header;  
* canonical position summary;  
* current lifecycle status;  
* evidence area;  
* latest analysis;  
* trading plan;  
* probability panel;  
* timeline;  
* analysis history;  
* pending actions;  
* warnings.

**Acceptance Criteria**

* each session has isolated context;  
* no analysis from another session appears;  
* canonical values are clearly labeled.

---

## **TP-1105 — Implement Evidence Upload UI**

**Objective**

Allow users to upload initial and update screenshots.

**Dependencies**

TP-1104, TP-1003.

**Target Files**

frontend/src/features/evidence/

**Acceptance Criteria**

* required initial evidence types are clear;  
* orderbook-only update workflow is supported;  
* upload progress and errors are shown;  
* image preview is available.

---

# **EPIC 12 — Analysis Rendering**

## **TP-1201 — Add Frontend Golden Fixtures**

**Objective**

Use validated fixtures as frontend mock data.

**Dependencies**

TP-0402.

**Target Files**

frontend/src/test/fixtures/

**Required Fixtures**

* Initial Analysis;  
* Watching Update;  
* Open Position Update;  
* Partial Exit Review;  
* Closing Analysis.

**Acceptance Criteria**

* fixture structure matches backend schema;  
* fixtures are not manually simplified for UI.

---

## **TP-1202 — Implement Initial Analysis View**

**Objective**

Render the complete initial setup analysis.

**Dependencies**

TP-1201, TP-1104.

**Target Files**

frontend/src/features/analysis/initial-analysis-view.tsx

**Display**

* executive summary;  
* orderbook analysis;  
* three-month chart analysis;  
* six-month chart analysis;  
* combined chart assessment;  
* support and resistance;  
* entry;  
* stop loss;  
* target;  
* thesis;  
* plan;  
* probability and confidence;  
* warnings.

---

## **TP-1203 — Implement Watching Update View**

**Objective**

Render setup changes before entry.

**Dependencies**

TP-1202.

**Target Files**

frontend/src/features/analysis/watching-update-view.tsx

**Display**

* current setup status;  
* comparison with previous analysis;  
* entry validity;  
* confirmation status;  
* chase risk;  
* proposed levels;  
* recommended action.

---

## **TP-1204 — Implement Open Position Update View**

**Objective**

Render the primary active-position experience.

**Dependencies**

TP-1202.

**Target Files**

frontend/src/features/analysis/open-position-update-view.tsx

**Display Requirements**

* Open;  
* High;  
* Low;  
* Last or Close;  
* Average;  
* orderbook observations;  
* position status;  
* whether TP remains realistic;  
* stop-loss status;  
* trading plan for later today or tomorrow;  
* bullish or bearish assessment;  
* target probability;  
* downside probability;  
* confidence;  
* material changes from previous update.

**Acceptance Criteria**

* this view matches the user’s preferred BBRI-style workflow;  
* active and proposed levels are visually distinct;  
* percentages are presented as estimates.

---

## **TP-1205 — Implement Partial Exit Review View**

**Objective**

Render realized and remaining-position analysis.

**Dependencies**

TP-1204.

**Target Files**

frontend/src/features/analysis/partial-exit-review-view.tsx

**Display**

* partial execution;  
* realized P/L;  
* remaining quantity;  
* unrealized P/L;  
* total trade result;  
* remaining target realism;  
* proposed protective stop;  
* remaining-position plan.

---

## **TP-1206 — Implement Closing Analysis View**

**Objective**

Render the final Trade Session review.

**Dependencies**

TP-1205.

**Target Files**

frontend/src/features/analysis/closing-analysis-view.tsx

**Display**

* final result;  
* weighted exit;  
* timeline;  
* thesis evaluation;  
* execution quality;  
* risk-management quality;  
* what worked;  
* what failed;  
* avoidable mistakes;  
* lessons;  
* grade;  
* journal summary.

---

## **TP-1207 — Implement Analysis History and Comparison**

**Objective**

Allow users to review each session update separately.

**Dependencies**

TP-1203 through TP-1206.

**Target Files**

frontend/src/features/analysis/history/

**Acceptance Criteria**

* each analysis has its own timestamp and period;  
* user can open prior analyses;  
* latest view does not overwrite historical content;  
* material-change comparisons are readable.

---

# **EPIC 13 — User Confirmation UI**

## **TP-1301 — Implement Position Open Confirmation Modal**

**Objective**

Convert a watched setup into a confirmed position.

**Dependencies**

TP-1005, TP-1203.

**Target Files**

frontend/src/features/trade-actions/open-position-modal.tsx

**Fields**

* actual entry price;  
* quantity;  
* stop loss;  
* target;  
* execution timestamp;  
* note.

**Acceptance Criteria**

* AI values are prefilled as proposals;  
* user can change values;  
* confirmation is explicit;  
* successful action refreshes canonical state.

---

## **TP-1302 — Implement Stop and Target Modals**

**Objective**

Confirm or change active risk levels.

**Dependencies**

TP-1005, TP-1204.

**Target Files**

frontend/src/features/trade-actions/stop-loss-modal.tsx  
frontend/src/features/trade-actions/target-modal.tsx

**Acceptance Criteria**

* current active value is shown;  
* AI proposed value is shown separately;  
* confirmed value is editable;  
* state changes only after submission.

---

## **TP-1303 — Implement Partial Exit Modal**

**Objective**

Confirm selling part of the position.

**Dependencies**

TP-1005, TP-1205.

**Target Files**

frontend/src/features/trade-actions/partial-exit-modal.tsx

**Fields**

* exit price;  
* exited quantity;  
* timestamp;  
* reason;  
* note.

**Acceptance Criteria**

* remaining quantity preview is calculated;  
* full remaining quantity cannot be submitted as partial exit;  
* result refreshes after confirmation.

---

## **TP-1304 — Implement Full Exit Modal**

**Objective**

Close the remaining position.

**Dependencies**

TP-1005, TP-1205.

**Target Files**

frontend/src/features/trade-actions/full-exit-modal.tsx

**Fields**

* final exit price;  
* final quantity;  
* timestamp;  
* closing reason;  
* note.

**Acceptance Criteria**

* final quantity defaults to remaining quantity;  
* result preview is shown;  
* confirmation changes session to terminal status.

---

# **EPIC 14 — Job Progress and Failure UX**

## **TP-1401 — Implement Analysis Request Controls**

**Objective**

Request the appropriate analysis for current lifecycle state.

**Dependencies**

TP-1004, TP-1104.

**Target Files**

frontend/src/features/analysis/request-analysis.tsx

**Acceptance Criteria**

* allowed analysis type comes from backend;  
* duplicate request is prevented;  
* missing evidence is shown before submission.

---

## **TP-1402 — Implement Job Status Polling**

**Objective**

Display background progress.

**Dependencies**

TP-1401.

**Target Files**

frontend/src/features/jobs/

**Display States**

* queued;  
* building context;  
* calling provider;  
* validating;  
* repairing;  
* fallback;  
* completed;  
* failed.

**Acceptance Criteria**

* polling stops after terminal status;  
* page can be refreshed without losing job;  
* completed analysis appears automatically.

---

## **TP-1403 — Implement Analysis Failure Handling**

**Objective**

Present safe, understandable failures.

**Dependencies**

TP-1402, TP-1007.

**Acceptance Criteria**

* user sees Indonesian summary;  
* technical validation details are hidden in normal mode;  
* retry is available when permitted;  
* uploaded evidence remains intact.

---

# **EPIC 15 — Complete Fixture and Integration Coverage**

## **TP-1501 — Complete Valid Schema Fixture Set**

**Objective**

Implement all valid fixtures listed in `SCHEMA_TEST_FIXTURES_SPEC.md`.

**Dependencies**

TP-0403.

**Acceptance Criteria**

* every production schema has multiple valid fixtures;  
* all conditional branches are covered;  
* golden fixtures are designated.

---

## **TP-1502 — Complete Invalid Schema and Domain Fixtures**

**Objective**

Cover every blocking validation code.

**Dependencies**

TP-1501.

**Acceptance Criteria**

* every blocking code has a test;  
* warning codes have tests where practical;  
* expected code and path are asserted.

---

## **TP-1503 — Implement Provider Contract Tests**

**Objective**

Test Gemini and DeepSeek with the same contract suite.

**Dependencies**

TP-0707.

**Acceptance Criteria**

Coverage includes:

* valid JSON;  
* fenced JSON;  
* commentary;  
* missing property;  
* invalid enum;  
* extra property;  
* malformed JSON;  
* refusal;  
* state conflict;  
* repair;  
* fallback.

---

## **TP-1504 — Implement End-to-End Scenario: Initial to Entry**

**Objective**

Test session creation through position confirmation.

**Dependencies**

TP-1301, TP-1402.

**Acceptance Criteria**

Scenario covers:

* create session;  
* upload evidence;  
* Initial Analysis;  
* Watching Update;  
* confirm entry;  
* canonical state becomes open.

---

## **TP-1505 — Implement End-to-End Scenario: Open Position Monitoring**

**Objective**

Test multiple longitudinal updates.

**Dependencies**

TP-1204, TP-1402.

**Acceptance Criteria**

* morning and midday updates are distinct;  
* latest update compares with prior context;  
* target probability and downside probability render;  
* Context Summary updates.

---

## **TP-1506 — Implement End-to-End Scenario: Partial and Full Exit**

**Objective**

Test the complete closing lifecycle.

**Dependencies**

TP-1303, TP-1304, TP-1206.

**Acceptance Criteria**

* partial quantity reconciles;  
* Partial Exit Review validates;  
* full exit closes session;  
* Closing Analysis and journal render.

---

## **TP-1507 — Implement State Conflict Regression Scenario**

**Objective**

Prove canonical state cannot be overwritten by AI.

**Dependencies**

TP-0804.

**Acceptance Criteria**

* provider returns wrong entry;  
* validation rejects response;  
* repair or fallback occurs;  
* canonical state remains unchanged;  
* only valid payload is accepted.

---

# **EPIC 16 — Operational Readiness**

## **TP-1601 — Implement Structured Logging**

**Objective**

Add consistent application, job, provider, and validation logs.

**Dependencies**

TP-0805, TP-1007.

**Target Files**

backend/app/logging.py  
worker/app/logging.py

**Log Fields**

* request ID;  
* session ID;  
* analysis job ID;  
* provider;  
* model;  
* schema;  
* attempt;  
* validation result;  
* duration.

**Acceptance Criteria**

* secrets are redacted;  
* logs are structured;  
* provider prompts are not logged by default in production.

---

## **TP-1602 — Implement Health and Readiness Checks**

**Objective**

Expose operational status.

**Dependencies**

TP-0805, TP-0302.

**Endpoints**

GET /health  
GET /health/ready  
GET /health/schema-registry  
GET /health/worker

**Acceptance Criteria**

* readiness checks database and schema registry;  
* worker heartbeat is visible;  
* temporary provider outage does not necessarily make the application unready.

---

## **TP-1603 — Implement Backup Scripts**

**Objective**

Back up PostgreSQL and uploaded evidence.

**Dependencies**

TP-0005.

**Target Files**

scripts/backup\_database.sh  
scripts/backup\_storage.sh  
scripts/restore\_database.sh  
docs/BACKUP\_RESTORE.md

**Acceptance Criteria**

* backup files are timestamped;  
* restore procedure is tested;  
* backup destination can be configured;  
* secrets are not embedded in scripts.

---

## **TP-1604 — Implement Security Hardening**

**Objective**

Apply MVP production security controls.

**Dependencies**

TP-1001, TP-1003.

**Requirements**

* HTTPS support;  
* secure cookies;  
* CSRF protection where relevant;  
* authorization on all resources;  
* upload-size limits;  
* MIME validation;  
* path traversal prevention;  
* secret redaction;  
* rate limiting;  
* trusted hosts;  
* security headers.

**Acceptance Criteria**

* cross-user resource access fails;  
* unauthorized evidence access fails;  
* unsafe upload paths fail;  
* security tests pass.

---

# **EPIC 17 — VPS Deployment**

## **TP-1701 — Create Production Docker Configuration**

**Objective**

Prepare containers for VPS deployment.

**Dependencies**

TP-1602.

**Target Files**

docker-compose.production.yml  
infra/docker/

**Acceptance Criteria**

* persistent volumes are configured;  
* restart policies exist;  
* environment variables are external;  
* containers do not run unnecessary development services.

---

## **TP-1702 — Configure Nginx and HTTPS**

**Objective**

Route frontend and backend securely.

**Dependencies**

TP-1701.

**Target Files**

infra/nginx/tradepilot.conf

**Acceptance Criteria**

* HTTPS works;  
* API reverse proxy works;  
* upload limit is configured;  
* security headers are present;  
* evidence cannot be served publicly without authorization.

---

## **TP-1703 — Create VPS Deployment Scripts**

**Objective**

Provide repeatable deployment and rollback.

**Dependencies**

TP-1701, TP-1702.

**Target Files**

infra/deploy/deploy.sh  
infra/deploy/rollback.sh  
docs/DEPLOYMENT.md

**Deployment Flow**

git pull  
build images  
run migrations  
restart services  
run health checks

**Acceptance Criteria**

* failed health check stops release;  
* previous image or Git revision can be restored;  
* deployment instructions are documented.

---

## **TP-1704 — Run Production Smoke Test**

**Objective**

Verify one full session on the VPS.

**Dependencies**

TP-1703, TP-1506.

**Smoke Test**

1. log in;  
2. create session;  
3. upload three images;  
4. run Initial Analysis;  
5. confirm entry;  
6. run Open Position Update;  
7. confirm full exit;  
8. run Closing Analysis;  
9. verify timeline and context;  
10. verify backup.

**Acceptance Criteria**

* complete workflow succeeds;  
* no critical errors appear in logs;  
* worker processes jobs;  
* evidence remains after restart;  
* database survives container restart.

---

# **EPIC 18 — Documentation and Handoff**

## **TP-1801 — Finalize Root README**

**Objective**

Document how to run and operate the MVP.

**Dependencies**

TP-1704.

**Target Files**

README.md

**Include**

* product overview;  
* architecture;  
* local setup;  
* environment variables;  
* migrations;  
* tests;  
* schema validation;  
* worker operation;  
* deployment links;  
* troubleshooting.

---

## **TP-1802 — Create Developer Troubleshooting Guide**

**Objective**

Document common failures.

**Dependencies**

TP-1704.

**Target Files**

docs/TROUBLESHOOTING.md

**Include**

* schema reference failures;  
* invalid AI JSON;  
* provider refusal;  
* stale context;  
* stuck job lease;  
* failed migration;  
* file permission issue;  
* worker heartbeat missing;  
* provider fallback behavior.

---

## **TP-1803 — Create MVP Release Checklist**

**Objective**

Define the final go-live checklist.

**Dependencies**

TP-1801, TP-1802.

**Target Files**

docs/MVP\_RELEASE\_CHECKLIST.md

**Acceptance Criteria**

Checklist includes:

* all migrations applied;  
* schema compilation pass;  
* fixture tests pass;  
* integration tests pass;  
* secrets configured;  
* HTTPS enabled;  
* backup restored successfully;  
* full smoke test completed.

---

# **6\. Task Dependency Summary**

The critical execution chain is:

TP-0001  
→ TP-0002 / TP-0003 / TP-0004  
→ TP-0005  
→ TP-0101  
→ TP-0102  
→ TP-0103  
→ TP-0104  
→ TP-0105  
→ TP-0106  
→ TP-0107  
→ TP-0108  
→ TP-0201  
→ TP-0202  
→ TP-0203  
→ TP-0301  
→ TP-0302  
→ TP-0303  
→ TP-0304  
→ TP-0305 through TP-0312  
→ TP-0501 through TP-0507  
→ TP-0601 through TP-0603  
→ TP-0701 through TP-0707  
→ TP-0801 through TP-0805  
→ TP-0901 through TP-0904  
→ TP-1001 through TP-1007  
→ TP-1101 through TP-1105  
→ TP-1201 through TP-1207  
→ TP-1301 through TP-1304  
→ TP-1401 through TP-1403  
→ TP-1501 through TP-1507  
→ TP-1601 through TP-1604  
→ TP-1701 through TP-1704  
→ TP-1801 through TP-1803

---

# **7\. Recommended First Coding Session**

The first Open Code session should execute only:

TP-0001 — Initialize Repository Structure  
TP-0002 — Configure Backend Python Project  
TP-0003 — Configure Worker Python Project  
TP-0004 — Configure Next.js Frontend  
TP-0005 — Configure Local Docker Environment

Do not start database models, schemas, AI providers, or frontend product features in the same first session.

The objective of the first session is only to create a clean, reproducible project foundation.

---

# **8\. Recommended Open Code Prompt Format**

For each task, use a prompt in this format:

You are implementing TradePilot AI.

Read these documents first:  
\- docs/IMPLEMENTATION\_PLAN.md  
\- docs/OPEN\_CODE\_TASKS.md  
\- any task-specific specification listed below.

Implement only task TP-XXXX: \<TASK TITLE\>.

Requirements:  
\- Follow the task scope exactly.  
\- Inspect existing code before changing files.  
\- Do not implement later tasks.  
\- Use English for code and technical text.  
\- Add or update tests.  
\- Run all relevant tests and lint checks.  
\- Do not claim completion if a test fails.  
\- At the end, report:  
  1\. Files created or changed  
  2\. Key implementation decisions  
  3\. Commands executed  
  4\. Test results  
  5\. Remaining issues

Task-specific source documents:  
\- \<DOCUMENT LIST\>

Acceptance criteria:  
\- \<COPY FROM TASK\>

---

# **9\. First Task Prompt**

Use the following prompt to begin implementation:

You are implementing TradePilot AI.

Read:  
\- docs/IMPLEMENTATION\_PLAN.md  
\- docs/OPEN\_CODE\_TASKS.md  
\- README.md if it already exists.

Implement only task TP-0001: Initialize Repository Structure.

Create the TradePilot AI monorepo structure defined in the task.

Requirements:  
\- Do not add database models.  
\- Do not add AI provider code.  
\- Do not add business logic.  
\- Do not initialize application frameworks beyond placeholder directories.  
\- Add a useful root README.md.  
\- Add .gitignore and .env.example.  
\- Ensure runtime storage and secrets are excluded from Git.  
\- Use English for all technical content.

At the end, report:  
1\. Files created  
2\. Directory structure  
3\. Important assumptions  
4\. Any issue that remains

Acceptance criteria:  
\- All required root directories exist.  
\- Repository structure matches OPEN\_CODE\_TASKS.md.  
\- .gitignore excludes environment files, caches, uploads, logs, and backups.  
\- .env.example contains placeholders only.

---

# **10\. Milestone Checkpoints**

## **Checkpoint A — Foundation Ready**

Completed tasks:

TP-0001 through TP-0203

Expected outcome:

* repository starts;  
* database exists;  
* canonical models exist;  
* production schemas compile.

---

## **Checkpoint B — Validation Ready**

Completed tasks:

TP-0301 through TP-0403

Expected outcome:

* schemas load;  
* deterministic calculations work;  
* invalid AI payloads can be rejected;  
* fixture suite is operational.

---

## **Checkpoint C — Canonical Workflow Ready**

Completed tasks:

TP-0501 through TP-0603

Expected outcome:

* sessions and evidence work;  
* entry, stop, target, partial exit, and full exit are user-confirmed;  
* lifecycle is protected.

---

## **Checkpoint D — Initial Analysis Vertical Slice**

Completed tasks:

TP-0701 through TP-0805  
TP-1001 through TP-1004  
TP-1101 through TP-1105  
TP-1201 through TP-1202  
TP-1401 through TP-1403

Expected outcome:

* create session;  
* upload initial evidence;  
* call Gemini;  
* validate output;  
* render Initial Analysis.

---

## **Checkpoint E — Open Position Workspace**

Completed tasks:

TP-0901 through TP-0904  
TP-1203 through TP-1204  
TP-1301 through TP-1302

Expected outcome:

* Watching Update;  
* entry confirmation;  
* Open Position Updates;  
* morning, midday, and afternoon longitudinal analysis.

---

## **Checkpoint F — Full Lifecycle**

Completed tasks:

TP-1205 through TP-1207  
TP-1303 through TP-1304  
TP-1504 through TP-1507

Expected outcome:

* partial exit;  
* final exit;  
* Closing Analysis;  
* One Trade One Story timeline.

---

## **Checkpoint G — Production MVP**

Completed tasks:

TP-1501 through TP-1803

Expected outcome:

* complete tests;  
* provider fallback;  
* security;  
* backups;  
* VPS deployment;  
* release documentation.

---

# **11\. Final Definition of Done**

TradePilot AI MVP is complete only when all the following are true:

1. A user can create one Trade Session for one ticker.  
2. Initial orderbook and chart evidence can be uploaded.  
3. Initial Analysis is generated in Indonesian.  
4. AI output passes production schema validation.  
5. A watched setup can receive longitudinal updates.  
6. A user can confirm actual entry and quantity.  
7. Canonical Trade State is updated only by confirmed actions.  
8. Open Position updates show:  
   * Open;  
   * High;  
   * Low;  
   * Last or Close;  
   * Average;  
   * orderbook interpretation;  
   * TP realism;  
   * trading plan;  
   * bullish or bearish assessment;  
   * target probability;  
   * downside probability.  
9. Stop and target changes require user confirmation.  
10. Partial exits reconcile quantities and results.  
11. Full exit closes the position correctly.  
12. Closing Analysis evaluates result and process separately.  
13. Context Summary preserves the complete trade story.  
14. Gemini and DeepSeek use the same schema contract.  
15. Invalid AI output cannot become accepted analysis.  
16. The complete Trade Session is displayed on one dedicated page.  
17. Automated fixture and integration tests pass.  
18. The system runs securely on the VPS.  
19. Database and evidence backups can be restored.  
20. The full production smoke test passes.

---

## **12\. Implementation Start**

The documentation phase is complete.

Implementation begins with:

TP-0001 — Initialize Repository Structure

