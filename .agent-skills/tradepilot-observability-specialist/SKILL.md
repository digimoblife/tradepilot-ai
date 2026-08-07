# File: `.agent-skills/tradepilot-observability-specialist/SKILL.md`

# TradePilot Observability Specialist

## Purpose

Make TradePilot AI behavior traceable across:

* browser;
* gateway;
* frontend;
* backend API;
* PostgreSQL;
* evidence storage;
* background worker;
* Gemini provider;
* response parsing;
* schema validation;
* analysis persistence;
* job terminalization.

This skill ensures failures can be diagnosed from evidence rather than guesswork, while protecting secrets, user data, evidence files, and provider payloads.

Observability must answer where the first divergence occurred without introducing excessive log noise or changing business behavior.

---

## When to Use

Use this skill for tasks involving:

* structured logging;
* correlation IDs;
* distributed request tracing;
* session and job diagnosis;
* provider failures;
* schema validation failures;
* worker retry loops;
* stale context;
* duplicate frontend requests;
* frontend polling;
* health checks;
* production-like smoke testing;
* deployment verification;
* incident investigation;
* performance timing;
* failure classification;
* error sanitization;
* operational dashboards or alerts.

---

## Required Context

Before implementation or investigation, read:

* `.agent-skills/shared/PROJECT_INVARIANTS.md`;
* `.agent-skills/shared/DEBUGGING_PROTOCOL.md`;
* `.agent-skills/tradepilot-product-guardian/SKILL.md`;
* `.agent-skills/tradepilot-repository-navigator/SKILL.md`;
* `.agent-skills/tradepilot-debugging-investigator/SKILL.md`;
* `.agent-skills/tradepilot-test-engineer/SKILL.md`;
* `.agent-skills/shared/EXIT_REPORT_TEMPLATE.md`;
* current logging configuration;
* gateway configuration;
* backend middleware;
* session and job models;
* worker processing code;
* provider adapter;
* evidence-storage implementation;
* frontend polling logic;
* health-check definitions;
* relevant observability tests.

For production-like verification, also read:

* `.agent-skills/tradepilot-devops-safety/SKILL.md`;
* `.agent-skills/tradepilot-production-smoke-test-engineer/SKILL.md`;
* `.agent-skills/tradepilot-ai-provider-specialist/SKILL.md`.

---

## Core Observability Questions

The system should make it possible to answer:

1. Did the browser send the request?
2. Did the gateway receive it?
3. Did the gateway route it to the correct service?
4. Did the backend accept or reject it?
5. Was the user authorized?
6. Was the session found?
7. Was required evidence available?
8. Was context fresh?
9. Was an analysis job created?
10. Did the worker claim the job?
11. How many attempts occurred?
12. Was Gemini invoked?
13. Which model was used?
14. Was required image evidence included?
15. Did Gemini return success or failure?
16. Did response extraction succeed?
17. Did JSON parsing succeed?
18. Did schema validation succeed?
19. Did domain validation succeed?
20. Was the analysis persisted?
21. Was the job terminalized?
22. Did the frontend observe the terminal state?
23. Did frontend polling stop?
24. Was a duplicate request or job created?
25. Where did the first divergence occur?

Observability is incomplete when these questions require guessing from unrelated logs.

---

## Core Invariants

Observability must preserve:

* secret confidentiality;
* evidence confidentiality;
* user isolation;
* stable correlation identifiers;
* useful root-cause details;
* bounded log volume;
* correct event ordering;
* consistent job terminal state;
* no business-logic changes;
* no success event before transaction commit;
* no false provider invocation claims;
* no raw provider payload dumping;
* no hidden errors behind generic codes.

---

## Correlation Model

Use stable identifiers across boundaries.

Recommended identifiers:

```text id="89v31a"
correlation_id
request_id
user_id
session_id
job_id
analysis_id
evidence_id
analysis_type
provider
model
attempt
service
```

The primary cross-service identifiers are:

```text id="a6hyit"
correlation_id
session_id
job_id
analysis_type
provider
model
```

Do not rely only on timestamps.

Do not create multiple incompatible correlation-ID systems.

---

## Correlation ID Rules

A correlation ID should:

* be created at the external request boundary when absent;
* be accepted from a trusted upstream gateway when present;
* be propagated to backend services;
* be associated with created jobs;
* be available to workers;
* be included in provider boundary events;
* be returned in safe API error metadata when approved;
* remain stable for the logical request.

A retry attempt may have:

* the same job ID;
* the same original correlation ID;
* a distinct attempt number;
* an optional child request ID.

Do not reuse a correlation ID across unrelated user actions.

---

## Structured Event Model

Prefer structured events over unstructured sentences.

Recommended fields:

```text id="dvtf36"
event_name
service
timestamp
severity
correlation_id
request_id
user_id
session_id
job_id
analysis_id
evidence_id
analysis_type
provider
model
attempt
duration_ms
status
error_code
retryable
root_cause_category
root_cause_message
```

Fields should be omitted when not applicable rather than populated with misleading placeholders.

---

## Recommended Event Names

### Gateway and API

```text id="krdil6"
gateway_request_received
gateway_request_routed
gateway_request_failed
analysis_request_received
analysis_request_rejected
analysis_request_accepted
```

### Context

```text id="txc81m"
context_freshness_started
context_freshness_completed
context_freshness_failed
context_build_started
context_build_completed
context_build_failed
```

### Evidence

```text id="t0mwqb"
evidence_upload_received
evidence_storage_write_started
evidence_storage_write_completed
evidence_storage_write_failed
evidence_read_started
evidence_read_completed
evidence_read_failed
```

### Jobs

```text id="hi3k8v"
analysis_job_created
analysis_job_claim_attempted
analysis_job_claimed
analysis_job_processing_started
analysis_job_retry_scheduled
analysis_job_terminalized
```

### Provider

```text id="bfnmbg"
provider_request_started
provider_request_completed
provider_request_failed
provider_response_empty
provider_response_blocked
provider_response_parse_failed
```

### Validation and Persistence

```text id="4g2v36"
analysis_json_parsed
analysis_json_parse_failed
analysis_schema_validation_started
analysis_schema_validation_completed
analysis_schema_validation_failed
analysis_domain_validation_started
analysis_domain_validation_completed
analysis_domain_validation_failed
analysis_persistence_started
analysis_persisted
analysis_persistence_failed
```

### Frontend

```text id="3cqf4i"
frontend_analysis_request_started
frontend_poll_started
frontend_poll_response_received
frontend_poll_terminal_state
frontend_poll_stopped
frontend_restored_job_loaded
frontend_duplicate_request_detected
```

Use stable event names. Do not rename them casually without considering dashboards, tests, and operational queries.

---

## Mandatory Workflow

### 1. Define the Diagnostic Objective

Before adding logs or metrics, state the concrete question.

Examples:

* Why does the frontend remain in processing?
* Did the worker claim the job?
* Was Gemini actually called?
* Which schema field failed?
* Why was a retry scheduled?
* Did duplicate browser requests create duplicate jobs?
* Was evidence read from the correct storage path?
* Which service first diverged from expected behavior?

Do not instrument broadly without a diagnostic objective.

---

### 2. Map the Observable Path

Trace the active path:

```text id="kfrgwl"
Browser
→ Gateway
→ Frontend
→ Backend
→ Context
→ Database
→ Job
→ Worker
→ Evidence storage
→ Gemini
→ Parser
→ Validator
→ Persistence
→ Terminal job
→ Frontend polling
```

For each boundary, identify:

* existing event;
* missing event;
* current identifiers;
* sensitive fields;
* expected success event;
* expected failure event;
* duration requirement.

---

### 3. Identify the First Missing Evidence

Do not add observability everywhere at once.

Find the first point where diagnosis becomes ambiguous.

Example:

```text id="4wmqg0"
Known:
- Backend accepted the analysis request.
- Job record exists.
- Frontend continues polling.

Unknown:
- Whether the worker claimed the job.

Required observability:
- analysis_job_claim_attempted
- analysis_job_claimed
- analysis_job_claim_failed
```

Add the minimum events needed to close that diagnostic gap.

---

### 4. Instrument Boundary Start and Completion

For important operations, emit:

* start event;
* success event or failure event;
* duration;
* stable identifiers;
* sanitized classification.

Examples:

```text id="s35foo"
provider_request_started
provider_request_completed
```

```text id="4kd67v"
analysis_persistence_started
analysis_persisted
```

Do not emit a success event before the operation is committed or confirmed.

---

### 5. Instrument Request and Session Boundaries

Backend request events should include where available:

* correlation ID;
* request ID;
* route;
* method;
* user ID or safe internal identifier;
* session ID;
* analysis type;
* response status;
* duration.

Do not log:

* authentication tokens;
* cookies;
* request bodies containing evidence or secrets;
* full personal identifiers unnecessarily.

Authorization failure should be distinguishable from missing-session failure internally, while user-facing behavior may intentionally return the same status.

---

### 6. Instrument Context Freshness

Context freshness events should identify:

* session ID;
* requested analysis type;
* current context version;
* required freshness condition;
* rebuild required or not;
* rebuild duration;
* success or failure;
* error category.

Required questions:

* Was freshness checked?
* Was context rebuilt?
* Did rebuilding commit?
* Did failure occur before job creation?
* Did stale context cause retries?

Do not log the full context package.

---

### 7. Instrument Job Lifecycle

Every analysis job should be traceable through:

1. creation;
2. pending state;
3. claim attempt;
4. successful claim;
5. processing start;
6. provider invocation;
7. validation;
8. persistence;
9. retry scheduling or terminalization.

Required fields include:

```text id="d1xjnw"
job_id
session_id
analysis_type
attempt
status
correlation_id
```

For retry events, include:

* error code;
* retryable;
* current attempt;
* next attempt;
* scheduled delay;
* maximum attempts.

For terminal events, include:

* terminal status;
* final error code when failed;
* analysis ID when successful;
* total duration;
* total attempts.

Do not leave a job with no terminal event after a known permanent failure.

---

### 8. Instrument Provider Boundary

Provider events should include:

* provider;
* model;
* analysis type;
* job ID;
* session ID;
* attempt;
* evidence count;
* evidence roles;
* request duration;
* response status;
* usage metadata when available;
* finish reason when safe;
* error classification.

Do not include:

* API keys;
* authorization headers;
* raw image bytes;
* full prompts;
* full context package;
* full raw provider output.

A provider request-start event is required to prove invocation.

A configured model name alone does not prove the provider was called.

---

### 9. Instrument Evidence Flow

Evidence events should identify:

* evidence ID;
* session ID;
* user ownership;
* evidence role;
* MIME type;
* size;
* storage-relative path or safe storage identifier;
* write/read result;
* duration.

Do not log:

* raw file bytes;
* full absolute production paths when sensitive;
* unrestricted user filenames;
* image contents.

Required questions:

* Was the file stored?
* Was it linked to the correct session?
* Could the worker read it?
* Was the correct evidence role included?
* Was the storage path isolated?

---

### 10. Instrument Parsing and Validation

On JSON parsing failure, record:

* job ID;
* analysis type;
* provider;
* model;
* parse error category;
* safe position or offset where available;
* whether markdown-fence normalization was applied;
* whether raw output was stored in protected diagnostics.

On schema validation failure, record:

* schema name or version;
* field path;
* error category;
* error count;
* job ID;
* provider;
* model.

On domain validation failure, record:

* domain rule identifier;
* affected field path;
* safe summary;
* job ID;
* analysis type.

Do not log the complete provider output in ordinary application logs.

---

### 11. Instrument Persistence

Persistence events should identify:

* job ID;
* session ID;
* analysis ID;
* transaction start;
* commit success;
* rollback;
* error category;
* duration.

Emit:

```text id="x7uc0q"
analysis_persisted
```

only after commit succeeds.

If persistence fails after provider success, the logs must distinguish:

* provider success;
* validation success;
* persistence failure;
* job terminalization result.

---

### 12. Instrument Frontend Polling

Frontend diagnostics should identify:

* polling owner;
* session ID;
* job ID;
* initial job state;
* poll start;
* poll interval;
* response state;
* terminal state;
* stop reason;
* restored state;
* retry-key changes;
* duplicate requests;
* component remount when relevant.

Avoid logging every normal React render.

Prefer event-based diagnostics.

Required questions:

* Who owns polling?
* Did polling start once?
* Did it stop on terminal state?
* Did restored failed state restart polling?
* Did a duplicate request create a second job?
* Did full-shell remount occur?

---

### 13. Instrument Gateway Behavior

Gateway observability should distinguish:

* request received;
* route selected;
* upstream service;
* upstream response status;
* connection failure;
* timeout;
* health-check request;
* static asset request when relevant.

Do not treat gateway HTTP 200 as proof that backend, worker, storage, or Gemini are healthy.

Avoid excessive logging of static assets in production unless needed.

---

### 14. Design Health Checks by Depth

Health checks should distinguish:

#### Liveness

Answers:

* Is the process running?
* Can the service respond?

#### Readiness

Answers:

* Is required configuration present?
* Is the database reachable?
* Is the service ready to accept work?

#### Dependency Readiness

May check:

* database;
* evidence storage;
* worker availability;
* queue access;
* gateway upstream routing.

Routine health checks should not make expensive real Gemini calls unless explicitly designed.

Provider configuration presence is not the same as provider availability.

---

### 15. Add Timing Where Useful

Capture `duration_ms` for:

* gateway routing;
* backend request processing;
* context freshness;
* context build;
* evidence read;
* provider request;
* parsing;
* schema validation;
* domain validation;
* persistence;
* total job processing;
* frontend time to terminal state.

Do not add high-cardinality metrics without operational value.

Use consistent time units.

---

## Log Severity Guidance

Use:

### DEBUG

For detailed local or diagnostic events that are normally disabled in production.

Examples:

* context section counts;
* polling ownership details;
* safe provider response shape metadata.

### INFO

For normal lifecycle milestones.

Examples:

* job created;
* job claimed;
* provider request completed;
* analysis persisted;
* job terminalized successfully.

### WARNING

For recoverable anomalies.

Examples:

* retry scheduled;
* incomplete historical context;
* optional evidence unreadable;
* duplicated frontend request prevented.

### ERROR

For terminal operation failures.

Examples:

* provider authentication failure;
* schema validation terminal failure;
* persistence failure;
* job terminalization failure.

### CRITICAL

Only for system-wide integrity or availability threats.

Examples:

* database corruption;
* broad secret exposure;
* inability to protect production isolation;
* system-wide job processing failure.

Do not mark expected user-input validation failures as critical.

---

## Error Classification

Use stable application error categories.

Suggested categories:

```text id="55lttk"
AUTHORIZATION_FAILED
SESSION_NOT_FOUND
EVIDENCE_MISSING
EVIDENCE_READ_FAILED
CONTEXT_STALE
CONTEXT_BUILD_FAILED
JOB_CLAIM_FAILED
PROVIDER_AUTH_FAILED
PROVIDER_MODEL_INVALID
PROVIDER_RATE_LIMITED
PROVIDER_UNAVAILABLE
PROVIDER_TIMEOUT
PROVIDER_RESPONSE_EMPTY
PROVIDER_RESPONSE_BLOCKED
PROVIDER_RESPONSE_MALFORMED
SCHEMA_VALIDATION_FAILED
DOMAIN_VALIDATION_FAILED
PERSISTENCE_FAILED
JOB_TERMINALIZATION_FAILED
FRONTEND_POLLING_LOOP
DUPLICATE_ANALYSIS_REQUEST
```

Do not collapse unrelated failures into one generic error code.

A generic top-level code may exist, but the sanitized root-cause category must remain available internally.

---

## Root-Cause Preservation

For a failure, preserve:

* stable application error code;
* root-cause category;
* sanitized root-cause message;
* service;
* operation;
* retryable;
* attempt;
* job ID;
* session ID;
* provider and model when relevant.

Example:

```text id="ld92aa"
error_code: PROVIDER_REQUEST_FAILED
root_cause_category: PROVIDER_MODEL_INVALID
root_cause_message: Configured Gemini model was not found.
retryable: false
```

Do not expose provider credentials or complete raw exceptions.

---

## Secret and Sensitive-Data Rules

Always redact:

* API keys;
* access tokens;
* refresh tokens;
* passwords;
* database credentials;
* authorization headers;
* cookies;
* secret environment variables;
* private keys;
* raw uploaded evidence;
* full provider prompts;
* unrestricted raw provider responses.

Minimize:

* email addresses;
* user display names;
* original filenames;
* external request content;
* absolute host paths.

Prefer:

* internal user ID;
* session ID;
* job ID;
* evidence ID;
* safe storage-relative path.

---

## Redaction Requirements

Redaction should occur before log emission.

Do not rely only on downstream log processors.

Tests should include known fake secrets and verify they do not appear in:

* logs;
* API error responses;
* job failure messages;
* frontend-visible errors;
* Playwright artifacts;
* exit reports.

When an exception object may contain request data, sanitize explicit fields rather than serializing the entire object.

---

## Log Volume Control

Observability must remain bounded.

Avoid:

* logging on every React render;
* full payload dumps;
* repeated identical polling logs;
* high-frequency success logs without operational value;
* duplicate events across several wrappers;
* unrestricted stack traces for expected failures.

Use:

* event sampling where appropriate;
* DEBUG level for noisy local details;
* one event per meaningful transition;
* aggregated counts;
* rate-limited warning logs;
* terminal summary events.

Report expected log-volume impact for new instrumentation.

---

## Metrics Guidance

Useful metrics may include:

* analysis requests;
* jobs created;
* jobs completed;
* jobs failed;
* jobs retried;
* provider request duration;
* provider error count by category;
* schema validation failures;
* context freshness failures;
* evidence read failures;
* frontend time to terminal;
* duplicate request prevention count;
* jobs stuck beyond threshold.

Avoid high-cardinality labels such as:

* raw user email;
* full session title;
* full error message;
* evidence filename;
* full URL query string.

IDs may be used in logs, but generally should not be metric labels.

---

## Tracing Guidance

When distributed tracing is available, create spans for:

```text id="q7etfl"
gateway.request
backend.analysis_request
context.freshness
context.build
job.create
worker.process
evidence.read
provider.generate
response.parse
schema.validate
domain.validate
analysis.persist
frontend.poll
```

Propagate trace context through job metadata where architecture permits.

Do not block implementation solely because a tracing platform is unavailable. Structured logs with stable correlation IDs remain acceptable.

---

## Failure Diagnosis Workflow

For an incident:

1. obtain session ID, job ID, or correlation ID;
2. locate request-received event;
3. trace events chronologically;
4. identify the first expected event that is missing;
5. identify the first explicit failure event;
6. inspect root-cause classification;
7. verify retry decisions;
8. verify terminal job state;
9. compare database state;
10. compare frontend-observed state;
11. form one falsifiable hypothesis;
12. follow `DEBUGGING_PROTOCOL.md`;
13. add regression protection.

Do not start by editing the component that displays the final symptom.

---

## Production-Like Smoke-Test Observability

For a complete smoke test, capture evidence for:

```text id="a0p7sw"
gateway_request_received
analysis_request_accepted
evidence_storage_write_completed
analysis_job_created
analysis_job_claimed
provider_request_started
provider_request_completed
analysis_schema_validation_completed
analysis_domain_validation_completed
analysis_persisted
analysis_job_terminalized
frontend_poll_terminal_state
frontend_poll_stopped
```

Each should be correlated through session ID and job ID where applicable.

This event chain is stronger proof than a final screenshot alone.

---

## Failure-Scenario Observability

### Invalid Model

Expected events:

```text id="1a7rcj"
provider_request_started
provider_request_failed
analysis_job_terminalized
frontend_poll_terminal_state
frontend_poll_stopped
```

Required classification:

```text id="vtdfqp"
PROVIDER_MODEL_INVALID
retryable: false
```

### Invalid API Key

Required classification:

```text id="yheiei"
PROVIDER_AUTH_FAILED
retryable: false
```

Secret value must not appear anywhere.

### Schema Failure

Expected events:

```text id="mv9p20"
provider_request_completed
analysis_json_parsed
analysis_schema_validation_failed
analysis_job_terminalized
```

Required data:

* field path;
* schema version;
* validation error count.

### Frontend Retry Loop

Expected diagnostics:

* restored job state;
* poll start count;
* retry-key changes;
* terminal state received;
* poll stop missing or present;
* duplicate fetch count.

---

## Testing Requirements

Observability changes should include relevant tests.

### Correlation Tests

Verify:

* correlation ID is created;
* propagated to job;
* available in worker events;
* present at provider boundary;
* stable through terminalization.

### Redaction Tests

Verify fake secrets do not appear.

### Error-Preservation Tests

Verify:

* generic outer error does not discard root cause;
* provider message is sanitized;
* validation field path is retained.

### Terminal-Event Tests

Verify:

* success emits one terminal event;
* failure emits one terminal event;
* retry does not emit false terminal success;
* persistence success precedes successful terminalization.

### Frontend Polling Tests

Verify:

* polling starts once;
* terminal response stops polling;
* restored failed jobs do not loop;
* duplicate request is prevented or detected.

### Event-Shape Tests

Verify required fields for critical events.

Do not make tests dependent on incidental log formatting when structured fields are available.

---

## Observability Changes Must Not Alter Business Logic

Instrumentation must not:

* change lifecycle transitions;
* change provider retry policy unintentionally;
* swallow exceptions;
* change transaction boundaries;
* create duplicate writes;
* delay terminalization materially;
* expose internal diagnostics to users without approval;
* turn expected failure into success.

When instrumentation requires a code-path refactor, declare the blast radius and add behavior regression tests.

---

## Contract Impact Requirement

Every observability task must classify its impact as one of:

* no contract change;
* internal logging-only change;
* backward-compatible error metadata change;
* backward-compatible API diagnostic change;
* backward-compatible job metadata change;
* backward-compatible health-check change;
* breaking operational contract change;
* test-only change.

Identify affected:

* log events;
* error codes;
* API response metadata;
* job fields;
* health endpoints;
* frontend diagnostics;
* dashboards or alerts.

Do not assume observability is always contract-free.

Stable event names and error codes may be operational contracts.

---

## Required Pre-Implementation Output

Before editing, report:

```text id="n7ukzu"
Diagnostic objective:
Affected flow:
First ambiguous boundary:
Existing events:
Missing events:
Correlation identifiers:
Error classifications:
Sensitive fields:
Redaction plan:
New or changed events:
Metrics or timings:
Tests:
Expected log-volume impact:
Expected contract impact:
Blast radius:
```

---

## Required Completion Output

Use:

```text id="skc8bl"
.agent-skills/shared/EXIT_REPORT_TEMPLATE.md
```

Additionally report:

* diagnostic objective;
* events added;
* events changed;
* event fields;
* services instrumented;
* correlation propagation;
* error codes;
* redaction behavior;
* tests executed;
* exact commands;
* sample sanitized event shapes;
* metrics or timings added;
* log-volume impact;
* operational questions now answerable;
* remaining blind spots;
* final Git working-tree status;
* blocking risks;
* non-blocking residual risks.

---

## Verification Claims

### TESTED

Use when:

* observability unit or integration tests pass;
* event shapes are verified;
* redaction is verified;
* the target production-like flow was not executed.

### VERIFIED

Use only when:

* the relevant real flow was executed;
* events appeared at required boundaries;
* correlation IDs connected the flow;
* first divergence could be identified;
* terminal state was observable;
* sensitive data remained redacted;
* expected log volume remained acceptable.

### IMPLEMENTED_NOT_FULLY_VERIFIED

Use when instrumentation exists but the target real flow could not be exercised.

---

## Residual Risk Requirement

Do not default to:

```text id="91bpwd"
Risks: None
```

Consider:

* uninstrumented boundaries;
* missing correlation propagation;
* provider SDK metadata unavailable;
* frontend logs disabled in production;
* high-cardinality fields;
* log-volume growth;
* redaction gaps;
* dashboard or alert rules not updated;
* local-only verification;
* events not covered by integration tests;
* health checks that remain shallow;
* asynchronous event ordering ambiguity.

Use:

```text id="62blv9"
No blocking risks identified.
```

only when justified, followed by realistic residual risks.

---

## Prohibited Actions

Do not:

* log API keys;
* log complete environment files;
* log authorization headers;
* log raw evidence;
* log full provider prompts;
* log full provider output by default;
* emit success before commit;
* add noisy per-render frontend logs;
* use different correlation IDs at every layer;
* hide root causes behind generic error codes;
* change business logic under the guise of observability;
* claim Gemini invocation without a provider request event;
* claim end-to-end traceability when a required boundary is missing;
* mark unexecuted instrumentation as `VERIFIED`.

---

## Escalation Rules

Stop and request direction when:

* required diagnostics would expose sensitive data;
* current error contract intentionally hides details needed for operations;
* adding identifiers requires a schema or API contract change;
* log volume would become operationally unsafe;
* provider SDK does not expose required metadata;
* frontend production logging policy is undefined;
* multiple services define conflicting correlation IDs;
* two fixes move the failure between layers without identifying root cause;
* observability requirements conflict with privacy or security policy.

Present safe alternatives and their consequences.

---

## Exit Criteria

This skill is complete when:

* the target flow is traceable across relevant boundaries;
* stable identifiers correlate session and job events;
* provider invocation can be proven when required;
* parsing, validation, persistence, and terminalization are observable;
* the first failing boundary can be identified;
* root-cause classifications remain useful;
* secrets and evidence remain protected;
* log volume remains controlled;
* observability changes are tested;
* verification claims match the real flow exercised.
