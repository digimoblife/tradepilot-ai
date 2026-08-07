# File: `.agent-skills/tradepilot-production-smoke-test-engineer/SKILL.md`

# TradePilot Production Smoke Test Engineer

## Purpose

Design and execute visible, production-like end-to-end smoke tests that prove the real TradePilot AI application flow across:

* browser;
* gateway;
* frontend;
* backend API;
* PostgreSQL;
* evidence storage;
* background worker;
* Gemini provider;
* schema validation;
* analysis persistence;
* frontend terminal state.

This skill complements `tradepilot-test-engineer`.

The general test skill defines testing standards. This specialist skill defines how to prove that the integrated TradePilot AI system works through its real production-like architecture.

---

## When to Use

Use this skill for tasks involving:

* local production-like environments;
* full-stack smoke testing;
* Playwright browser automation;
* real Gemini provider calls;
* evidence upload verification;
* asynchronous analysis jobs;
* frontend polling;
* gateway routing;
* isolated PostgreSQL;
* isolated evidence storage;
* release-readiness verification;
* deployment acceptance;
* browser-visible failure handling.

---

## Required Context

Before planning or executing the smoke test, read:

* `.agent-skills/shared/PROJECT_INVARIANTS.md`;
* `.agent-skills/tradepilot-product-guardian/SKILL.md`;
* `.agent-skills/tradepilot-repository-navigator/SKILL.md`;
* `.agent-skills/tradepilot-test-engineer/SKILL.md`;
* `.agent-skills/tradepilot-devops-safety/SKILL.md`;
* `.agent-skills/shared/EXIT_REPORT_TEMPLATE.md`;
* relevant user-flow documentation;
* deployment architecture;
* API specifications;
* job lifecycle documentation;
* evidence requirements;
* Playwright configuration;
* production prompt configuration;
* Gemini provider configuration;
* current Docker Compose files.

If failures must be investigated, also read:

* `.agent-skills/tradepilot-debugging-investigator/SKILL.md`;
* `.agent-skills/shared/DEBUGGING_PROTOCOL.md`.

---

## Production-Like System Boundary

A complete smoke test should exercise the actual path:

```text
Playwright browser
→ Gateway
→ Frontend
→ Backend API
→ PostgreSQL
→ Evidence storage
→ Analysis job
→ Worker
→ Gemini provider
→ Response parser
→ JSON Schema validation
→ Domain validation
→ Analysis persistence
→ Job terminalization
→ Frontend polling
→ Browser rendering
```

Do not claim full end-to-end verification when a required boundary is bypassed or mocked.

---

## Production-Like Definition

A production-like environment should preserve the production architecture where practical:

* the same service boundaries;
* the same gateway routing pattern;
* the same frontend application;
* the same backend entry point;
* the same worker process;
* the same PostgreSQL engine;
* the same evidence-storage abstraction;
* the same production prompts;
* the same canonical schemas;
* the same provider adapter;
* the same model configuration path;
* the same job lifecycle;
* the same frontend polling behavior.

The environment must remain isolated from production infrastructure and data.

Production-like does not mean production-connected.

---

## Core Invariants

The smoke test must preserve:

* One Trade One Story;
* one isolated user and session lifecycle;
* no production database use;
* no production evidence reuse;
* real application-calculated trade facts;
* validated provider output;
* Indonesian user-facing analysis;
* bounded retries;
* correct terminal job state;
* no duplicate analysis creation;
* no infinite frontend polling;
* safe secret handling;
* no destructive infrastructure commands.

---

## Mandatory Workflow

### 1. Define the Target Flow

Translate the requested user journey into explicit steps.

For an Initial Analysis smoke test, the expected flow may be:

1. open the application through the gateway;
2. authenticate as the smoke-test user;
3. create a new trade session;
4. enter the ticker;
5. upload the required orderbook image;
6. upload the required three-month chart;
7. upload the required six-month chart;
8. verify evidence records and storage;
9. mark the evidence ready;
10. request Initial Analysis;
11. verify backend job creation;
12. verify worker job claim;
13. verify a real Gemini request;
14. verify response parsing;
15. verify schema and domain validation;
16. verify accepted analysis persistence;
17. verify successful job terminalization;
18. verify the frontend stops processing;
19. verify completed Indonesian analysis is visible;
20. refresh the page and verify the result persists.

The exact flow must match the approved task and current product behavior.

---

### 2. Define Observable Checkpoints

Every meaningful step must have an observable result.

Examples:

| Step              | Observable checkpoint                                  |
| ----------------- | ------------------------------------------------------ |
| Open application  | Gateway URL returns the frontend                       |
| Login             | Authenticated user state is visible                    |
| Create session    | New session ID exists                                  |
| Upload evidence   | UI confirms upload and file exists in isolated storage |
| Mark ready        | Session or evidence status changes                     |
| Request analysis  | New job ID exists                                      |
| Worker processing | Worker claim event exists                              |
| Gemini call       | Provider request event identifies Gemini and model     |
| Validation        | Analysis passes canonical schema and domain validation |
| Persistence       | Analysis ID exists in the isolated database            |
| UI completion     | Processing state disappears and analysis renders       |
| Refresh           | Persisted analysis remains visible                     |

Avoid relying on one UI success message as proof of the entire backend path.

---

### 3. Define Proof for Each Boundary

Before execution, specify how each system boundary will be proven.

Example:

```text
Browser → Gateway:
Playwright opens the gateway URL successfully.

Gateway → Frontend:
Frontend assets and application shell load through the gateway.

Frontend → Backend:
Network request or backend correlation event confirms API receipt.

Backend → PostgreSQL:
Session and job records exist in the isolated database.

Upload → Evidence Storage:
Files exist under the isolated evidence-storage root.

Worker → Gemini:
Provider request-start event contains job ID, provider, and model.

Gemini → Worker:
Provider success or classified failure event exists.

Worker → Persistence:
Analysis record and terminal job state exist.

Backend → Frontend:
Polling receives the terminal state.

Frontend → User:
Completed Indonesian analysis appears in the browser.
```

---

### 4. Establish an Isolated Run Identity

Every smoke-test run should use a unique identifier.

Recommended format:

```text
smoke-<date>-<short-random-id>
```

Use the run identifier in:

* test user metadata when practical;
* ticker-session notes when available;
* Playwright artifact folders;
* evidence-storage folders;
* logs;
* screenshots;
* exit reports.

The run identity should make artifacts and database records traceable.

---

### 5. Prepare Isolated Test Resources

Use:

* a dedicated smoke-test user;
* a dedicated database;
* a dedicated Compose project;
* dedicated PostgreSQL volume;
* dedicated evidence-storage root;
* dedicated Docker network;
* known non-sensitive evidence fixtures;
* a dedicated environment file;
* unique session and job records.

Do not use:

* production users;
* production sessions;
* production databases;
* production evidence;
* production volumes;
* shared test data whose ownership is unclear.

---

### 6. Confirm Stack Readiness

Before running Playwright, verify:

* PostgreSQL is healthy;
* migrations are current;
* backend health passes;
* worker is running;
* frontend is reachable;
* gateway is reachable;
* evidence storage is writable;
* selected Gemini provider configuration is present;
* selected model is visible through sanitized configuration;
* no fake provider is enabled;
* required test fixtures exist;
* the browser test points to the gateway URL.

Do not begin browser testing against a partially healthy stack.

---

### 7. Execute Through the Browser

Use Playwright for the user-visible acceptance flow.

The browser test must:

* open the application through the gateway;
* interact with the actual frontend;
* use real authentication behavior;
* create a real session;
* upload real fixture files;
* trigger the actual analysis action;
* observe state transitions;
* verify terminal success or failure;
* verify the final user-facing result;
* preserve diagnostics on failure.

Do not replace browser actions with direct API calls when the requirement is browser verification.

API calls may be used for setup only when explicitly allowed and when they do not bypass the behavior being tested.

---

## Playwright Selector Rules

Prefer selectors based on:

1. role;
2. accessible name;
3. label;
4. stable test identifier.

Examples:

```text
getByRole("button", { name: "Buat Sesi" })
getByLabel("Ticker")
getByTestId("initial-analysis-status")
```

Avoid:

* fragile nested CSS selectors;
* positional selectors;
* text selectors that depend on incidental layout;
* arbitrary DOM traversal.

When a stable selector does not exist, add a minimal semantic or test identifier rather than writing a brittle test.

---

## Waiting and Timeout Rules

Use observable application conditions.

Prefer:

* waiting for a status element to change;
* waiting for a specific network response;
* waiting for a terminal job state;
* waiting for a final analysis section;
* polling a known API state through the browser flow when appropriate.

Avoid arbitrary sleeps such as:

```text
waitForTimeout(30000)
```

unless no observable condition exists and the reason is documented.

Real Gemini calls may require longer timeouts, but those timeouts must remain bounded.

A test must not wait indefinitely on a processing state.

---

### 8. Verify Authentication and Ownership

Confirm:

* the browser is authenticated as the intended smoke-test user;
* the created session belongs to that user;
* uploaded evidence belongs to that session;
* the analysis job belongs to that session;
* another user cannot access the session or evidence;
* test data does not leak across accounts.

When cross-user isolation is part of the requested scope, include an explicit negative test.

---

### 9. Verify Evidence Storage

UI upload success is not sufficient.

Confirm:

* the evidence record exists;
* the stored file exists;
* the file is under the isolated evidence root;
* the file is linked to the correct user and session;
* the file MIME type is accepted;
* the worker can read the file;
* production evidence paths were not touched;
* repeated runs do not overwrite unrelated evidence.

Record only safe metadata:

* evidence ID;
* file type;
* storage-relative path;
* size;
* session ID.

Do not expose raw evidence content in logs.

---

### 10. Verify Job Creation and Claim

After the analysis request:

* capture the job ID;
* verify the job analysis type;
* verify the job belongs to the correct session;
* verify the job begins in the expected pending state;
* verify one worker claims it;
* verify claim time and attempt count;
* verify no duplicate job is created by repeated frontend requests;
* verify no second worker processes the same job concurrently.

Do not infer job creation solely from the frontend processing indicator.

---

### 11. Verify Real Gemini Invocation

When the task requires a real provider call, prove:

* provider is Gemini;
* the expected configured model is used;
* no mock or fake provider is enabled;
* the provider adapter is invoked;
* required image evidence is included;
* production prompts are used;
* a real provider response or provider-classified failure is received.

Configuration alone is not proof of invocation.

The verification should rely on sanitized provider boundary events, job metadata, or equivalent evidence.

Never print the API key.

---

### 12. Verify Provider Response Handling

Confirm:

* provider response content is extracted;
* empty or blocked responses are handled;
* JSON parsing runs;
* canonical schema validation runs;
* domain validation runs;
* rejected output is not persisted as accepted analysis;
* accepted analysis is persisted only after validation;
* application-calculated deterministic fields remain application-owned.

When validation fails, capture the field path and classification without dumping sensitive raw output.

---

### 13. Verify Persistence

For successful analysis, confirm:

* analysis record exists;
* analysis type is correct;
* session relationship is correct;
* accepted payload is present;
* provider metadata is recorded when designed;
* job references the resulting analysis when designed;
* session state is consistent;
* no duplicate accepted analysis exists for the same request.

Use the isolated database as evidence, not production.

---

### 14. Verify Terminal State Consistency

At the end of a successful run, verify agreement among:

* database job status;
* persisted analysis state;
* session state;
* backend API response;
* frontend UI.

Confirm:

* job is terminal success;
* frontend processing indicator disappears;
* polling stops;
* completed analysis is visible;
* browser refresh preserves the analysis;
* no duplicate request begins after refresh;
* no failed restored job loop occurs.

A browser that still displays “processing” while the database is terminal is a failed smoke test.

---

### 15. Verify User-Facing Analysis

The browser should verify the required visible sections rather than only generic success text.

For Initial Analysis, relevant sections may include:

* decision;
* market facts;
* evidence findings;
* trade plan;
* probabilities;
* scenarios;
* next action.

User-facing content must be Indonesian.

The test should not require exact AI prose unless the contract requires deterministic text.

Prefer structural assertions:

* section exists;
* section is non-empty;
* required labels are present;
* probability values are within valid bounds;
* no raw JSON is displayed;
* no provider error is shown on success.

---

### 16. Verify Page Refresh and Recovery

After successful completion:

* refresh the browser;
* reopen the session;
* verify the persisted analysis loads;
* verify no new job is created;
* verify no stale processing state returns;
* verify terminal status remains stable.

This proves persistence and frontend recovery behavior.

---

## Required Failure Scenarios

The exact failure scenarios depend on the task. For production-like Gemini smoke testing, prioritize the following.

### A. Invalid Gemini Model

Expected behavior:

* the configured invalid model reaches the provider boundary;
* provider or configuration failure is classified;
* the sanitized model name may be visible;
* the underlying error is preserved internally;
* the job reaches terminal failure;
* no infinite retry occurs;
* no analysis is marked successful;
* the frontend exits processing;
* the user sees a useful failure state;
* no secret is exposed.

---

### B. Invalid Gemini API Key

Expected behavior:

* authentication failure is classified;
* the API key is never printed;
* retry behavior follows policy;
* permanent authentication failure does not loop rapidly;
* the job terminalizes;
* no successful analysis record is created;
* the frontend exits processing;
* the user sees a safe corrective message.

---

### C. Missing Required Evidence

Expected behavior:

* the request is blocked before provider invocation;
* the user sees which evidence is missing;
* no unnecessary job is created, unless the approved architecture intentionally creates a failed validation job;
* Gemini is not called;
* session state remains consistent.

---

### D. Malformed Provider Output

Expected behavior:

* provider response is received;
* JSON or schema validation fails;
* rejected output is not accepted;
* validation path is observable;
* job terminalizes according to policy;
* no infinite prompt/schema correction loop occurs;
* the two-fix escalation rule applies during debugging.

This scenario may use a controlled test provider or fixture when a real provider cannot reliably be instructed to return malformed output. The mocked boundary must be disclosed.

---

### E. Empty or Blocked Provider Response

Expected behavior:

* response extraction detects missing usable content;
* no null-reference crash occurs;
* job receives the correct failure classification;
* frontend exits processing;
* no false success is persisted.

---

### F. Worker Interruption

When requested, verify:

* a claimed job does not become silently lost;
* recovery or terminalization follows the approved policy;
* duplicate processing does not occur;
* the frontend does not poll indefinitely.

---

## Failure Diagnostics

On browser test failure, collect the minimum useful artifacts:

* screenshot;
* Playwright trace when enabled;
* browser console errors;
* failed network request summary;
* current page URL;
* current visible state;
* smoke-test run ID;
* session ID;
* job ID;
* analysis ID when created;
* relevant gateway logs;
* relevant backend logs;
* relevant worker logs;
* provider failure classification;
* database state;
* evidence-storage state.

Do not capture:

* API keys;
* authorization headers;
* passwords;
* full secret-bearing environment files;
* raw image bytes;
* full sensitive provider prompts;
* unrestricted database dumps.

---

## Browser Artifact Rules

Store artifacts under a run-specific path, for example:

```text
artifacts/smoke/<run-id>/
├── screenshots/
├── traces/
├── videos/
├── logs/
└── summary.json
```

Artifacts must:

* be excluded from source control unless explicitly required;
* avoid secrets;
* be referenced in the exit report;
* be retained long enough for diagnosis;
* not overwrite prior runs unintentionally.

---

## Mocking Rules

Every boundary must be classified as:

* real;
* mocked;
* bypassed;
* not applicable.

For a full real-provider smoke test:

```text
Browser: real
Gateway: real
Frontend: real
Backend: real
PostgreSQL: real isolated instance
Evidence storage: real isolated storage
Worker: real
Gemini: real
Schema validation: real
```

Do not describe the flow as fully verified if Gemini or the browser is mocked.

Mocks are appropriate for targeted failure cases that cannot be reliably produced with the live provider, but the report must distinguish them from the real success flow.

---

## Test Repeatability

The smoke test should support repeated execution.

Requirements:

* unique user or run identity;
* unique session;
* isolated evidence path;
* deterministic fixture selection;
* no dependence on prior job state;
* cleanup or archival plan;
* bounded provider calls;
* no duplicate analysis caused by reruns;
* clear handling of existing test accounts.

A repeat run should not require manual database repair.

---

## Acceptance Evidence Matrix

At completion, map every acceptance criterion to concrete evidence.

Required format:

| Acceptance criterion              | Verification method         | Result | Evidence                          |
| --------------------------------- | --------------------------- | ------ | --------------------------------- |
| Application loads through gateway | Playwright                  | PASS   | Gateway URL and browser assertion |
| User login succeeds               | Playwright                  | PASS   | Authenticated session visible     |
| Trade session is created          | UI + database               | PASS   | Session ID                        |
| Evidence is uploaded              | UI + storage inspection     | PASS   | Evidence IDs and isolated paths   |
| Analysis job is created           | API + database              | PASS   | Job ID                            |
| Worker claims job                 | Worker observability        | PASS   | Claim event                       |
| Gemini is called                  | Provider observability      | PASS   | Provider and model event          |
| Output is validated               | Backend observability       | PASS   | Validation success event          |
| Analysis is persisted             | Database/API                | PASS   | Analysis ID                       |
| Frontend renders completion       | Playwright                  | PASS   | Final UI assertion                |
| Polling stops                     | Browser/network observation | PASS   | No continued terminal polling     |
| Refresh preserves result          | Playwright                  | PASS   | Reload assertion                  |

Do not report only:

```text
AC1–AC25: PASS
```

without traceable evidence.

---

## Verification Classification

### TESTED

Use when:

* component tests pass;
* API tests pass;
* worker tests pass;
* Playwright may run against mocked boundaries;
* the full requested production-like flow was not exercised.

### VERIFIED

Use only when:

* the isolated production-like stack ran;
* Playwright exercised the actual browser flow;
* the gateway was used;
* backend and PostgreSQL were real;
* evidence storage was real and isolated;
* the real worker processed the job;
* real Gemini was called when required;
* output validation and persistence were confirmed;
* the browser observed the terminal result;
* acceptance evidence was recorded.

### IMPLEMENTED_NOT_FULLY_VERIFIED

Use when infrastructure or code is prepared, but one or more required boundaries could not be exercised.

Examples:

* Gemini credentials unavailable;
* Playwright environment unavailable;
* provider rate limit prevented completion;
* browser flow stopped before terminal state;
* worker could not be started.

---

## Contract Impact Requirement

Every smoke-test task must classify its impact as one of:

* no contract change;
* test-only change;
* backward-compatible testability change;
* backward-compatible observability change;
* environment-only change;
* production-like infrastructure change;
* breaking contract change.

Examples of potentially contract-impacting changes:

* adding stable test identifiers;
* adding health endpoints;
* adding provider metadata;
* adding job-state API fields;
* changing evidence validation;
* changing polling behavior.

Do not treat all smoke-test-support changes as automatically internal.

---

## Prohibited Actions

Do not:

* use production databases;
* use production evidence files;
* reuse production volumes;
* point local services to production URLs;
* mock a boundary required to be real;
* bypass the gateway when the gateway is part of acceptance;
* replace browser interaction with direct API calls;
* claim Gemini verification from configuration inspection;
* claim browser verification from backend tests;
* ignore worker claim verification;
* accept unvalidated provider output;
* leave tests waiting indefinitely;
* use destructive Docker cleanup;
* expose secrets in artifacts;
* mark a partially exercised flow as `VERIFIED`.

---

## Escalation Rules

Stop and request direction when:

* the environment points to production;
* a required real provider call cannot be made safely;
* the only available database contains production data;
* evidence-storage isolation cannot be proven;
* browser verification requires bypassing the approved gateway;
* a failure cannot be reproduced without destructive action;
* two fixes create repeated schema or provider mismatch;
* the expected lifecycle behavior conflicts with current approved specifications;
* full verification requires changing product behavior.

Present safe options and their consequences.

---

## Expected Pre-Implementation Output

Before editing or execution, report:

```text
Target flow:
Environment:
Production-like boundaries:
Real boundaries:
Mocked boundaries:
Gateway URL plan:
Database isolation:
Evidence-storage isolation:
Smoke-test user:
Evidence fixtures:
Playwright plan:
Backend checkpoints:
Worker checkpoints:
Gemini verification:
Failure scenarios:
Observability evidence:
Expected contract impact:
Blast radius:
Verification threshold:
```

If no boundaries are mocked, state:

```text
Mocked boundaries: None
```

---

## Expected Completion Output

Use:

```text
.agent-skills/shared/EXIT_REPORT_TEMPLATE.md
```

Additionally report:

* smoke-test run ID;
* environment topology;
* Compose project name;
* gateway URL;
* database name;
* evidence-storage root;
* Playwright command;
* browser used;
* success-flow result;
* failure-flow results;
* session ID;
* job ID;
* analysis ID;
* provider;
* model;
* prompt version;
* real and mocked boundaries;
* acceptance evidence matrix;
* captured artifact paths;
* terminal database state;
* terminal frontend state;
* cleanup status;
* exact commands for all test-suite claims;
* final Git working-tree status;
* blocking risks;
* non-blocking residual risks;
* untested boundaries.

---

## Residual Risk Requirement

Do not default to:

```text
Risks: None
```

Consider realistic residual risks such as:

* provider latency variability;
* provider rate limits;
* browser timing sensitivity;
* incomplete browser coverage;
* fixture representativeness;
* token-cost variability;
* untested concurrency;
* host-specific Docker differences;
* structural payload bounds without explicit byte ceilings;
* differences between local and production secret delivery;
* missing external TLS or reverse-proxy behavior.

Use:

```text
No blocking risks identified.
```

only when supported, followed by remaining non-blocking risks.

---

## Exit Criteria

This skill is complete when:

* the browser exercised the approved user flow;
* the gateway was included when required;
* the isolated database was verified;
* evidence storage was verified as isolated;
* the worker claimed and processed the job;
* real Gemini use was proven when required;
* provider output was validated before persistence;
* terminal job and UI states were consistent;
* required failure scenarios were exercised;
* acceptance criteria were mapped to evidence;
* no production resource was affected;
* the verification status accurately reflects the boundaries exercised.
