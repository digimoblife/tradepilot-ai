# **TradePilot AI — AI Provider Specification**

**Document:** `AI_PROVIDER_SPEC.md`  
**Version:** 1.0  
**Status:** Final  
**Product Name:** TradePilot AI  
**Primary References:** `ARCHITECTURE.md`, `AI_ANALYSIS_SPEC.md`, `THESIS_ENGINE_SPEC.md`, `CONTEXT_MEMORY_SPEC.md`, `PROBABILITY_CONFIDENCE_SPEC.md`  
**Purpose:** Define the provider-neutral AI interface, capability detection, Gemini and DeepSeek adapters, request normalization, structured output, vision handling, timeout, retry, fallback, usage tracking, error normalization, security, and provider evaluation requirements.

---

## **1\. Document Purpose**

This document defines how TradePilot AI communicates with external AI providers.

It specifies:

* provider-neutral interfaces;  
* supported providers;  
* provider capability detection;  
* model selection;  
* text and vision request handling;  
* structured-output enforcement;  
* request and response normalization;  
* timeout behavior;  
* retry policy;  
* fallback policy;  
* provider disagreement handling;  
* token and usage collection;  
* cost estimation;  
* error normalization;  
* credential handling;  
* observability;  
* provider testing;  
* provider replacement strategy.

The rest of the application must not depend directly on Gemini- or DeepSeek-specific SDK objects.

---

# **2\. Provider Design Principles**

## **2.1 Provider Independence**

Application and domain services must communicate through a provider-neutral interface.

Provider SDKs may only appear inside provider adapters.

Prohibited architecture:

Analysis Service  
    → Gemini SDK directly

Required architecture:

Analysis Service  
    → AI Provider Interface  
        → Gemini Adapter  
        → DeepSeek Adapter

---

## **2.2 Capability-Based Dispatch**

A provider must be selected based on required capabilities, not only provider name.

Examples:

* a vision analysis requires image-input support;  
* a large Context Package requires sufficient context capacity;  
* strict JSON output requires structured-output support;  
* fallback requires equivalent minimum capabilities.

---

## **2.3 Structured Output Is Mandatory**

Provider responses used for TradePilot analysis must produce a structured payload matching the requested schema.

Plain narrative text is not sufficient.

When native structured output is unavailable, the adapter must:

* request strict JSON;  
* parse the response;  
* normalize it;  
* pass it through the same validation pipeline.

---

## **2.4 Providers Do Not Control Canonical State**

Provider output is only a candidate analysis result.

The provider cannot directly:

* update a thesis;  
* change stop loss;  
* change targets;  
* open or close a position;  
* become canonical.

Canonicalization remains an application responsibility.

---

## **2.5 Secrets Remain Server-Side**

API keys and provider secrets must never be:

* sent to the browser;  
* stored in frontend bundles;  
* returned through API responses;  
* included in logs;  
* embedded in prompts;  
* committed to source control.

---

# **3\. Supported Providers**

MVP providers:

GEMINI  
DEEPSEEK  
MOCK

`MOCK` is available only for development and testing.

Additional providers may be added through new adapters without changing domain logic.

---

# **4\. Provider Capability Model**

Required capability enum:

TEXT\_REASONING  
VISION\_INPUT  
MULTI\_IMAGE\_INPUT  
STRUCTURED\_OUTPUT  
JSON\_SCHEMA  
LONG\_CONTEXT  
USAGE\_REPORTING  
STREAMING  
SYSTEM\_INSTRUCTION  
REQUEST\_ID\_REPORTING

The application should not assume that every model from one provider has the same capabilities.

Capabilities belong to a provider-and-model combination.

---

# **5\. Capability Descriptor**

Recommended normalized structure:

{  
  "provider": "GEMINI",  
  "model": "configured-model",  
  "capabilities": {  
    "text\_reasoning": true,  
    "vision\_input": true,  
    "multi\_image\_input": true,  
    "structured\_output": true,  
    "json\_schema": true,  
    "long\_context": true,  
    "usage\_reporting": true,  
    "streaming": false,  
    "system\_instruction": true,  
    "request\_id\_reporting": true  
  },  
  "limits": {  
    "maximum\_context\_tokens": 100000,  
    "maximum\_output\_tokens": 8192,  
    "maximum\_images": 10,  
    "maximum\_image\_bytes": 10485760,  
    "supported\_image\_mime\_types": \[  
      "image/jpeg",  
      "image/png",  
      "image/webp"  
    \]  
  }  
}

Actual values must come from provider configuration or runtime capability metadata.

They must not be hard-coded from assumptions inside domain services.

---

# **6\. Provider Configuration Model**

Recommended configuration object:

{  
  "provider": "GEMINI",  
  "model": "configured-model",  
  "enabled": true,  
  "is\_primary": true,  
  "is\_fallback": false,  
  "credential\_reference": "secret-reference",  
  "timeout\_seconds": 120,  
  "connection\_timeout\_seconds": 15,  
  "maximum\_attempts": 3,  
  "temperature": 0.2,  
  "maximum\_output\_tokens": 8192,  
  "structured\_output\_enabled": true,  
  "vision\_enabled": true  
}

The credential reference points to server-side secret storage.

---

# **7\. Provider Interface**

Recommended conceptual Python interface:

from abc import ABC, abstractmethod  
from dataclasses import dataclass  
from typing import Any

class AIProvider(ABC):  
    @abstractmethod  
    def provider\_name(self) \-\> str:  
        ...

    @abstractmethod  
    def model\_name(self) \-\> str:  
        ...

    @abstractmethod  
    def get\_capabilities(self) \-\> "ProviderCapabilities":  
        ...

    @abstractmethod  
    def validate\_configuration(self) \-\> "ProviderValidationResult":  
        ...

    @abstractmethod  
    def generate\_structured\_response(  
        self,  
        request: "AIRequest",  
    ) \-\> "AIProviderResponse":  
        ...

    @abstractmethod  
    def estimate\_request\_size(  
        self,  
        request: "AIRequest",  
    ) \-\> "RequestSizeEstimate":  
        ...

The interface may be asynchronous in the actual FastAPI and worker implementation.

Recommended implementation:

class AIProvider(ABC):  
    @abstractmethod  
    async def generate\_structured\_response(  
        self,  
        request: AIRequest,  
    ) \-\> AIProviderResponse:  
        ...

---

# **8\. Provider Registry**

The Provider Registry resolves configured adapters.

Conceptual interface:

class AIProviderRegistry:  
    def register(self, provider: AIProvider) \-\> None:  
        ...

    def get(  
        self,  
        provider\_name: str,  
        model\_name: str,  
    ) \-\> AIProvider:  
        ...

    def list\_enabled(self) \-\> list\[AIProvider\]:  
        ...

    def find\_compatible(  
        self,  
        requirements: ProviderRequirements,  
    ) \-\> list\[AIProvider\]:  
        ...

The registry must not contain secrets in user-facing output.

---

# **9\. Provider Requirements**

Each analysis job must define its minimum requirements.

Example:

{  
  "required\_capabilities": \[  
    "TEXT\_REASONING",  
    "VISION\_INPUT",  
    "MULTI\_IMAGE\_INPUT",  
    "STRUCTURED\_OUTPUT"  
  \],  
  "minimum\_context\_tokens": 24000,  
  "minimum\_output\_tokens": 6000,  
  "image\_count": 6,  
  "required\_mime\_types": \[  
    "image/webp"  
  \]  
}

The orchestrator must reject incompatible provider selection before making an external request.

---

# **10\. Normalized AI Request**

All adapters receive a normalized `AIRequest`.

{  
  "request\_id": "uuid",  
  "correlation\_id": "uuid",  
  "job\_id": "uuid",  
  "analysis\_request\_id": "uuid",  
  "analysis\_type": "OPEN\_POSITION\_UPDATE",  
  "provider": "GEMINI",  
  "model": "configured-model",  
  "system\_instruction": "string",  
  "context\_package": {},  
  "images": \[\],  
  "output\_schema": {},  
  "schema\_version": "1.0",  
  "temperature": 0.2,  
  "maximum\_output\_tokens": 8192,  
  "timeout\_seconds": 120,  
  "metadata": {}  
}

---

# **11\. Normalized Image Input**

Each image input should use a provider-neutral structure.

{  
  "evidence\_id": "uuid",  
  "evidence\_type": "ORDERBOOK\_SCREENSHOT",  
  "mime\_type": "image/webp",  
  "storage\_reference": "internal-reference",  
  "byte\_size": 842331,  
  "width": 1440,  
  "height": 1920,  
  "market\_timestamp": "timestamp",  
  "context\_role": "PRIMARY\_CURRENT",  
  "display\_order": 1  
}

Adapters are responsible for transforming the internal storage reference into the provider-specific format.

---

# **12\. Image Input Rules**

Before a provider call, the system must verify:

* evidence is available;  
* evidence is not excluded;  
* MIME type is supported;  
* image size is within limits;  
* image count is within limits;  
* processed variant exists;  
* checksum matches stored metadata;  
* image belongs to the correct Trade Session.

The original file remains preserved.

The provider should usually receive the `AI_INPUT` variant.

---

# **13\. Image Ordering**

Image ordering must be deterministic.

Recommended order:

1. current orderbook;  
2. current primary chart;  
3. current secondary chart;  
4. direct comparison orderbook;  
5. direct comparison chart;  
6. initial structural chart;  
7. other material evidence.

The text context must identify each image by evidence ID and role.

---

# **14\. Image Labeling**

Each image must be accompanied by a textual label.

Example:

IMAGE 1  
Evidence ID: ...  
Type: ORDERBOOK\_SCREENSHOT  
Role: PRIMARY\_CURRENT  
Market timestamp: ...

The provider must not be expected to infer chronology solely from image order.

---

# **15\. Structured Output Request**

The normalized request must include the exact output schema.

Recommended:

{  
  "schema\_name": "open\_position\_update",  
  "schema\_version": "1.0",  
  "json\_schema": {},  
  "strict": true  
}

The provider adapter should use native schema enforcement when supported.

---

# **16\. Structured Output Fallback**

When native JSON Schema enforcement is not supported:

1. include strict JSON instructions;  
2. include schema requirements;  
3. prohibit Markdown fences;  
4. parse the response;  
5. extract the JSON object;  
6. validate with application schema;  
7. attempt correction if invalid.

Provider-specific limitations must never weaken application validation.

---

# **17\. Normalized Provider Response**

All adapters must return:

{  
  "provider": "GEMINI",  
  "model": "configured-model",  
  "provider\_request\_id": "provider-id",  
  "response\_status": "COMPLETED",  
  "structured\_payload": {},  
  "raw\_text": null,  
  "finish\_reason": "STOP",  
  "usage": {  
    "input\_tokens": 12345,  
    "output\_tokens": 4567,  
    "total\_tokens": 16912,  
    "image\_count": 6  
  },  
  "latency\_ms": 18420,  
  "warnings": \[\],  
  "provider\_metadata": {}  
}

The adapter must not return provider SDK objects to application services.

---

# **18\. Response Status Values**

COMPLETED  
PARTIAL  
REFUSED  
FAILED  
CANCELLED

`PARTIAL` is not automatically eligible for canonicalization.

---

# **19\. Finish Reason Normalization**

Recommended normalized finish reasons:

STOP  
MAX\_OUTPUT\_TOKENS  
SAFETY  
CONTENT\_FILTER  
MALFORMED\_OUTPUT  
PROVIDER\_ERROR  
CANCELLED  
UNKNOWN

Provider-native finish reasons must be mapped to these values.

---

# **20\. Gemini Adapter Responsibilities**

The Gemini adapter must handle:

* credential loading;  
* selected Gemini model;  
* system instruction;  
* multi-image request construction;  
* image MIME handling;  
* structured-output configuration;  
* timeout;  
* response parsing;  
* usage extraction;  
* finish-reason mapping;  
* provider request ID extraction;  
* error normalization.

The adapter must expose only normalized structures.

---

# **21\. Gemini Vision Handling**

The Gemini adapter should:

1. load approved AI-input image variants;  
2. validate image MIME and size;  
3. preserve deterministic image order;  
4. attach textual evidence labels;  
5. send the Context Package;  
6. request the required JSON schema;  
7. collect response and usage metadata.

Image bytes must not be written to logs.

---

# **22\. Gemini Structured Output**

When the selected Gemini model supports native structured output, the adapter should:

* pass the JSON schema;  
* use strict response MIME type where supported;  
* disable unnecessary creativity;  
* reject non-object output;  
* preserve the raw provider response only in restricted diagnostics.

Application-side schema validation remains mandatory.

---

# **23\. Gemini Error Mapping**

Potential Gemini errors should map to normalized error codes such as:

AI\_PROVIDER\_AUTHENTICATION\_FAILED  
AI\_PROVIDER\_PERMISSION\_DENIED  
AI\_PROVIDER\_RATE\_LIMITED  
AI\_PROVIDER\_TIMEOUT  
AI\_PROVIDER\_UNAVAILABLE  
AI\_PROVIDER\_INVALID\_REQUEST  
AI\_PROVIDER\_CONTEXT\_LIMIT\_EXCEEDED  
AI\_PROVIDER\_IMAGE\_REJECTED  
AI\_PROVIDER\_CONTENT\_FILTERED  
AI\_RESPONSE\_EMPTY  
AI\_RESPONSE\_SCHEMA\_INVALID

Provider-native error strings should be stored only in restricted operational metadata.

---

# **24\. DeepSeek Adapter Responsibilities**

The DeepSeek adapter must handle:

* credential loading;  
* selected DeepSeek model;  
* system and user messages;  
* structured JSON request instructions;  
* timeout;  
* response parsing;  
* usage extraction;  
* finish-reason mapping;  
* provider request ID extraction;  
* error normalization.

The adapter must verify the capabilities of the selected model at runtime or configuration time.

---

# **25\. DeepSeek Vision Capability**

The system must not assume every DeepSeek model accepts image input.

For a vision-based analysis:

If selected DeepSeek model lacks VISION\_INPUT:  
    do not dispatch the vision request.

Possible alternatives:

* use Gemini as the primary vision provider;  
* use validated extracted evidence text with DeepSeek for text reasoning;  
* reject the request if no compatible provider exists.

The application must clearly record when an analysis used extracted text instead of original images.

---

# **26\. Text-Only DeepSeek Analysis**

A text-only DeepSeek request may be allowed when:

* image extraction has already produced sufficiently reliable structured facts;  
* the analysis type permits text-only processing;  
* provider requirements are satisfied;  
* context quality remains acceptable;  
* the user-facing analysis discloses image limitations.

Text-only processing must not be represented as direct visual inspection.

---

# **27\. DeepSeek Structured Output**

When native schema enforcement is unavailable or limited, the adapter must request:

* one JSON object only;  
* no Markdown;  
* no prose outside the JSON object;  
* exact English keys;  
* allowed enum values only;  
* Bahasa Indonesia narrative fields.

The application must parse and validate the response exactly as it validates Gemini output.

---

# **28\. Mock Provider**

The `MOCK` provider is required for:

* unit tests;  
* integration tests;  
* end-to-end tests;  
* local development without external costs;  
* failure simulation.

The Mock Provider must support deterministic scenarios:

VALID\_INITIAL\_ANALYSIS  
VALID\_OPEN\_POSITION\_UPDATE  
VALID\_CLOSING\_ANALYSIS  
INVALID\_JSON  
INVALID\_SCHEMA  
INVALID\_LANGUAGE  
CONTRADICTORY\_THESIS  
TIMEOUT  
RATE\_LIMIT  
PROVIDER\_UNAVAILABLE  
CONTENT\_FILTER  
STALE\_RESPONSE\_DELAY

---

# **29\. Provider Selection Strategy**

The orchestrator should select providers in this order:

1. requested provider when configured and compatible;  
2. configured primary provider;  
3. configured fallback provider;  
4. fail with no-compatible-provider error.

The requested provider must not bypass capability requirements.

---

# **30\. Default Provider Recommendation**

For image-heavy Trade Session analysis, the primary provider should be a configured model with:

* multi-image vision support;  
* reliable structured output;  
* sufficient context window;  
* usage reporting.

DeepSeek may serve as:

* text-reasoning provider;  
* fallback when capability-compatible;  
* thesis-review provider;  
* context-summary provider.

The exact model identifiers belong in configuration, not this specification.

---

# **31\. Provider Routing by Analysis Type**

Recommended routing policy:

| Analysis Type | Required Capability |
| ----- | ----- |
| Initial Analysis | Vision, multi-image, structured output |
| Watching Update | Vision when screenshots included |
| Open Position Update | Vision when screenshots included |
| Partial Exit Review | Text reasoning; vision optional |
| Closing Analysis | Text reasoning; vision optional |
| Trading Journal | Long context, structured output |
| Context Summary | Long context, structured output |
| Thesis Review | Text reasoning; vision when evidence requires it |

A compatible fallback may differ by analysis type.

---

# **32\. Provider Requirement Resolution**

Conceptual function:

def resolve\_provider\_requirements(  
    analysis\_type: AnalysisType,  
    context\_package: ContextPackage,  
) \-\> ProviderRequirements:  
    ...

Factors:

* image count;  
* token estimate;  
* schema size;  
* analysis type;  
* required reasoning depth;  
* configured output size.

---

# **33\. Request Size Estimation**

Before dispatch, the adapter or orchestrator must estimate:

* text input tokens;  
* schema tokens;  
* image count;  
* image byte size;  
* expected output tokens;  
* total request size.

If the request exceeds limits:

1. return to Context Builder for reduction;  
2. reduce optional images;  
3. use the latest valid Context Summary;  
4. fail if critical context still cannot fit.

The adapter must not silently truncate critical context.

---

# **34\. Timeout Model**

Use separate timeout concepts:

connection\_timeout  
response\_timeout  
total\_job\_timeout

Recommended initial configuration:

ai\_provider:  
  connection\_timeout\_seconds: 15  
  response\_timeout\_seconds: 120  
  total\_job\_timeout\_seconds: 300

Exact values belong in `CONFIG_SPEC.md`.

---

# **35\. Timeout Behavior**

On timeout:

* cancel the provider request when supported;  
* record the attempt as failed;  
* normalize the error;  
* determine retry eligibility;  
* preserve canonical state;  
* avoid duplicate canonicalization if the provider later responds.

A timed-out request result must not become canonical after the job has logically moved to a new attempt.

---

# **36\. Retry Policy**

Provider retry should apply only to retryable failures.

Retryable examples:

AI\_PROVIDER\_TIMEOUT  
AI\_PROVIDER\_RATE\_LIMITED  
AI\_PROVIDER\_UNAVAILABLE  
AI\_PROVIDER\_CONNECTION\_FAILED  
AI\_RESPONSE\_EMPTY  
AI\_RESPONSE\_NOT\_JSON  
AI\_RESPONSE\_SCHEMA\_INVALID  
AI\_RESPONSE\_LANGUAGE\_INVALID

Conditionally retryable:

AI\_PROVIDER\_CONTENT\_FILTERED  
AI\_PROVIDER\_IMAGE\_REJECTED  
AI\_PROVIDER\_CONTEXT\_LIMIT\_EXCEEDED

These may require request modification rather than an identical retry.

---

# **37\. Non-Retryable Provider Errors**

Do not automatically retry identical requests for:

AI\_PROVIDER\_AUTHENTICATION\_FAILED  
AI\_PROVIDER\_PERMISSION\_DENIED  
AI\_PROVIDER\_UNSUPPORTED\_CAPABILITY  
AI\_PROVIDER\_INVALID\_CONFIGURATION  
AI\_PROVIDER\_MODEL\_NOT\_FOUND  
AI\_REQUEST\_DOMAIN\_INVALID  
JOB\_CANCELLED  
ANALYSIS\_REQUEST\_STALE

---

# **38\. Retry Backoff**

Recommended exponential backoff with jitter.

Conceptual schedule:

attempt 1 → immediate  
attempt 2 → approximately 2 seconds  
attempt 3 → approximately 8 seconds

Rate-limit responses may use provider-supplied retry timing.

Worker execution must respect total job timeout.

---

# **39\. Retry Request Identity**

Each attempt belongs to the same logical job but must have:

* unique attempt number;  
* provider;  
* model;  
* provider request ID;  
* start and completion timestamps;  
* error metadata;  
* usage metadata.

The analysis request idempotency key remains the same.

---

# **40\. Response Repair Versus Full Retry**

Use response repair when:

* JSON is almost valid;  
* one required field is missing;  
* enum formatting is incorrect;  
* narrative language is incorrect;  
* provider output contains wrapper text.

Use a full retry when:

* response is empty;  
* output is unrelated;  
* response is severely incomplete;  
* provider connection failed;  
* output stopped because of a temporary error.

---

# **41\. Correction Prompt**

A correction request should include:

* the invalid normalized response or safe excerpt;  
* validation errors;  
* the same required schema;  
* explicit instruction not to change supported facts;  
* instruction to return corrected JSON only.

Correction prompts must not introduce new market evidence.

---

# **42\. Maximum Repair Attempts**

Recommended policy:

structured\_output:  
  deterministic\_parse\_repair\_attempts: 1  
  provider\_correction\_attempts: 1  
  full\_provider\_retries: 2

Exact totals must remain within the configured maximum job attempts.

---

# **43\. Fallback Policy**

Fallback may occur when the primary provider:

* times out after retries;  
* is unavailable;  
* is rate-limited beyond job tolerance;  
* returns repeatedly invalid structured output;  
* lacks a required capability;  
* rejects images that a compatible fallback supports.

Fallback must be explicitly enabled.

---

# **44\. Fallback Requirements**

Before fallback:

1. verify fallback is enabled;  
2. verify fallback provider configuration;  
3. verify required capabilities;  
4. rebuild provider-specific request;  
5. reuse the same normalized Context Package;  
6. recalculate provider-specific limits;  
7. record fallback reason;  
8. create a new `JobAttempt`.

---

# **45\. Fallback Context Consistency**

The same semantic context must be used across providers.

Provider-specific transformation may change:

* message formatting;  
* image encoding;  
* schema declaration;  
* system-prompt placement.

It must not change:

* source evidence;  
* current position;  
* active thesis;  
* event definitions;  
* output requirements.

---

# **46\. Fallback Canonicalization**

Fallback output is subject to the same:

* schema validation;  
* language validation;  
* numerical validation;  
* contradiction detection;  
* thesis-engine checks;  
* probability coherence;  
* stale-state checks.

A fallback result receives no reduced validation standard.

---

# **47\. Provider Disagreement**

Provider disagreement may occur when:

* a primary response is valid but review-required;  
* a second provider is invoked for verification;  
* manual provider comparison is requested.

The system must compare:

* thesis status;  
* directional bias;  
* confidence;  
* probabilities;  
* key levels;  
* recommended action;  
* reasoning.

---

# **48\. Provider Disagreement Thresholds**

Recommended initial thresholds:

provider\_disagreement:  
  confidence\_points: 15  
  probability\_points: 20  
  major\_level\_percentage: 2  
  thesis\_status\_difference: review  
  recommended\_action\_difference: review

Values are finalized in `CONFIG_SPEC.md`.

---

# **49\. Disagreement Handling**

When disagreement is material:

* do not average outputs;  
* preserve each attempt separately;  
* identify conflicting fields;  
* select the result with stronger evidence traceability when rules permit;  
* otherwise return `REVIEW_REQUIRED`.

No automatic “middle answer” should be invented.

---

# **50\. Primary and Fallback Result Persistence**

Every provider attempt must be recorded.

Only accepted normalized output becomes an `AnalysisVersion` eligible for canonical use.

Failed or rejected attempt details belong in:

* `job_attempts`;  
* provider diagnostics;  
* audit records when material.

The system should not create full user-facing analysis versions for every malformed raw attempt.

---

# **51\. Usage Reporting**

The adapter should collect when available:

* input tokens;  
* output tokens;  
* total tokens;  
* cached tokens;  
* reasoning tokens, when exposed;  
* image count;  
* latency;  
* provider request ID;  
* model.

Missing usage values remain null.

They must not be estimated as zero.

---

# **52\. Usage Normalization**

Recommended object:

{  
  "input\_tokens": 12000,  
  "output\_tokens": 4500,  
  "total\_tokens": 16500,  
  "cached\_input\_tokens": null,  
  "reasoning\_tokens": null,  
  "image\_count": 6,  
  "usage\_source": "PROVIDER\_REPORTED"  
}

Usage source values:

PROVIDER\_REPORTED  
APPLICATION\_ESTIMATED  
PARTIAL  
UNAVAILABLE

---

# **53\. Cost Estimation**

Cost may be estimated from:

* provider;  
* model;  
* input tokens;  
* output tokens;  
* image pricing;  
* pricing version;  
* currency.

Cost estimation must preserve:

provider  
model  
pricing version  
calculation timestamp  
currency

A cost estimate is not authoritative billing.

---

# **54\. Pricing Configuration**

Provider prices must not be hard-coded throughout adapter code.

Use versioned configuration such as:

pricing:  
  provider: GEMINI  
  model: configured-model  
  version: 2026-07  
  input\_per\_million\_tokens: null  
  output\_per\_million\_tokens: null  
  image\_pricing\_rule: null  
  currency: USD

Current pricing is external and may change.

---

# **55\. Error Normalization**

All provider errors must map to a common error model.

{  
  "code": "AI\_PROVIDER\_RATE\_LIMITED",  
  "message": "Provider AI sedang membatasi permintaan.",  
  "provider": "GEMINI",  
  "model": "configured-model",  
  "retryable": true,  
  "retry\_after\_seconds": 30,  
  "provider\_status\_code": 429,  
  "provider\_error\_reference": "restricted-reference",  
  "correlation\_id": "uuid"  
}

User-facing messages use Bahasa Indonesia.

Internal error codes remain English.

---

# **56\. Normalized Error Codes**

Required codes:

AI\_PROVIDER\_INVALID\_CONFIGURATION  
AI\_PROVIDER\_AUTHENTICATION\_FAILED  
AI\_PROVIDER\_PERMISSION\_DENIED  
AI\_PROVIDER\_MODEL\_NOT\_FOUND  
AI\_PROVIDER\_UNSUPPORTED\_CAPABILITY  
AI\_PROVIDER\_INVALID\_REQUEST  
AI\_PROVIDER\_CONTEXT\_LIMIT\_EXCEEDED  
AI\_PROVIDER\_IMAGE\_LIMIT\_EXCEEDED  
AI\_PROVIDER\_IMAGE\_REJECTED  
AI\_PROVIDER\_RATE\_LIMITED  
AI\_PROVIDER\_TIMEOUT  
AI\_PROVIDER\_CONNECTION\_FAILED  
AI\_PROVIDER\_UNAVAILABLE  
AI\_PROVIDER\_CONTENT\_FILTERED  
AI\_PROVIDER\_REFUSED  
AI\_RESPONSE\_EMPTY  
AI\_RESPONSE\_PARTIAL  
AI\_RESPONSE\_NOT\_JSON  
AI\_RESPONSE\_SCHEMA\_INVALID  
AI\_RESPONSE\_LANGUAGE\_INVALID  
AI\_RESPONSE\_LOGIC\_INVALID  
AI\_RESPONSE\_CONTRADICTORY  
AI\_RESPONSE\_STALE  
AI\_USAGE\_UNAVAILABLE  
AI\_REQUEST\_CANCELLED

---

# **57\. Error Safety**

Provider errors returned to users must not expose:

* API keys;  
* full provider payloads;  
* internal filesystem paths;  
* stack traces;  
* raw sensitive context;  
* private evidence URLs.

Detailed errors belong in restricted logs.

---

# **58\. Rate Limiting**

The system should support:

* provider-level request limits;  
* model-level limits;  
* user-level limits;  
* concurrent-job limits;  
* token-budget limits.

Redis may coordinate temporary counters.

PostgreSQL remains the authoritative source for completed usage.

---

# **59\. Concurrency Limits**

Recommended configurable limits:

ai\_provider:  
  maximum\_concurrent\_jobs\_per\_user: 2  
  maximum\_concurrent\_jobs\_per\_provider: 4  
  maximum\_concurrent\_vision\_jobs: 2

The worker must not create unbounded provider calls.

---

# **60\. Provider Circuit Breaker**

A circuit breaker is recommended for repeated provider failures.

Possible states:

CLOSED  
OPEN  
HALF\_OPEN

The breaker may open after:

* repeated timeouts;  
* repeated service-unavailable responses;  
* severe rate limiting;  
* configuration validation failure.

Authentication errors should disable the provider configuration until corrected.

---

# **61\. Circuit Breaker Behavior**

When open:

* do not send new requests to the provider;  
* use compatible fallback when enabled;  
* create a provider warning;  
* periodically test recovery through controlled health checks.

Circuit-breaker state should not be the only record of provider health.

---

# **62\. Configuration Validation**

The system must support provider configuration validation without creating a real Trade Session analysis.

Validation should check:

* credential acceptance;  
* model availability;  
* required capabilities;  
* structured-output support;  
* vision support when configured;  
* basic request success;  
* usage-reporting availability.

Validation must use minimal test data.

---

# **63\. Provider Validation Result**

{  
  "provider": "GEMINI",  
  "model": "configured-model",  
  "status": "VALID",  
  "capabilities": {},  
  "warnings": \[\],  
  "validated\_at": "timestamp"  
}

Statuses:

VALID  
VALID\_WITH\_WARNINGS  
INVALID\_CREDENTIALS  
MODEL\_UNAVAILABLE  
CAPABILITY\_MISMATCH  
REQUEST\_FAILED

---

# **64\. Model Changes**

Changing the configured model must:

* validate the new model;  
* refresh capabilities;  
* preserve previous usage history;  
* apply only to new jobs;  
* not alter historical analysis metadata.

Each Analysis Version records the actual model used.

---

# **65\. Provider Changes**

Changing the primary provider must not:

* rewrite historical analyses;  
* change stored probabilities;  
* change old journals;  
* delete previous provider metadata.

The new provider applies only to future requests.

---

# **66\. Prompt Compatibility**

Provider adapters may need provider-specific wrapping, but prompts must share:

* the same semantic instructions;  
* the same output schema;  
* the same safety rules;  
* the same Context Package.

Provider-specific prompt variants must share one logical prompt version or include an adapter-variant identifier.

---

# **67\. Prompt Metadata**

Each request should record:

prompt name  
logical prompt version  
provider adapter version  
provider prompt variant  
schema version  
context fingerprint

This supports reproducibility.

---

# **68\. Adapter Versioning**

Each provider adapter should expose a version.

Example:

gemini-adapter: 1.0.0  
deepseek-adapter: 1.0.0

Adapter version changes should be recorded when they affect:

* request formatting;  
* image handling;  
* response parsing;  
* usage extraction;  
* error mapping.

---

# **69\. Provider Request Logging**

Structured logs should include:

* provider;  
* model;  
* request ID;  
* job ID;  
* analysis type;  
* image count;  
* token estimate;  
* attempt number;  
* latency;  
* result status;  
* normalized error code.

Logs must not include:

* full prompts by default;  
* image bytes;  
* API keys;  
* complete private analysis payloads.

---

# **70\. Restricted Diagnostics**

A restricted diagnostics mode may store:

* sanitized request manifest;  
* schema validation errors;  
* limited raw response excerpts;  
* provider headers relevant to debugging;  
* adapter transformation details.

Retention must be limited and configurable.

---

# **71\. Raw Response Storage**

Raw provider response storage is optional.

When enabled:

* store outside normal user-facing records;  
* encrypt or restrict access;  
* apply retention;  
* redact secrets;  
* link to job attempt;  
* never treat it as canonical output.

The normalized structured payload remains the main result.

---

# **72\. Cancellation**

The worker must check logical cancellation:

* before provider dispatch;  
* after provider response;  
* before canonicalization.

When provider-side cancellation is supported, attempt it.

Even when physical cancellation fails, logical cancellation must prevent canonicalization.

---

# **73\. Late Responses**

A provider response may arrive after:

* timeout;  
* job cancellation;  
* fallback completion;  
* newer analysis completion.

Late responses must be marked non-applicable.

They may be retained for diagnostics, but must not become canonical.

---

# **74\. Idempotency**

Provider calls should include provider-supported idempotency references where available.

Application idempotency remains authoritative.

Duplicate delivery of the same worker job must not result in:

* duplicate accepted Analysis Versions;  
* duplicate usage counting;  
* duplicate notifications;  
* duplicate canonical state updates.

---

# **75\. Provider Attempt State Machine**

CREATED  
    ↓  
PROCESSING  
    ├── COMPLETED  
    ├── FAILED  
    └── CANCELLED

Job-level retries create new attempt records.

---

# **76\. Provider Response Validation Pipeline**

Provider Response  
        ↓  
Response status validation  
        ↓  
Finish-reason validation  
        ↓  
Payload extraction  
        ↓  
JSON parsing  
        ↓  
Schema validation  
        ↓  
Language validation  
        ↓  
Numerical validation  
        ↓  
Logical validation  
        ↓  
Thesis and probability checks  
        ↓  
Stale-state validation  
        ↓  
Canonicalization eligibility

The adapter is responsible only through payload extraction and normalization.

Business validation remains outside the adapter.

---

# **77\. Content Filtering and Refusal**

If a provider refuses or filters a valid trading-analysis request:

* normalize the refusal;  
* do not treat refusal text as analysis;  
* retry only when request reformatting is safe;  
* use fallback when compatible;  
* record the failure.

The application must not attempt to bypass provider safety systems.

---

# **78\. Partial Responses**

A response is partial when:

* output stops at token limit;  
* JSON is truncated;  
* required sections are missing;  
* provider reports incomplete completion.

Partial responses may enter repair flow.

They cannot become canonical as-is.

---

# **79\. Output Token Limit Handling**

When output reaches the maximum token limit:

1. mark response partial;  
2. attempt structured correction with more concise output;  
3. reduce narrative verbosity, not required fields;  
4. increase configured output limit if provider allows;  
5. fallback or fail.

Required schema fields must not be removed merely to fit.

---

# **80\. Context Limit Handling**

When provider context limit is exceeded:

* return request to Context Builder;  
* preserve critical facts;  
* compress older history;  
* reduce non-critical images;  
* retry with a new context fingerprint.

The adapter must not independently remove arbitrary prompt sections.

---

# **81\. Vision Degradation Strategy**

When no compatible vision provider is available:

1. check whether reliable extraction exists;  
2. determine whether analysis type permits text-only reasoning;  
3. lower context quality and analysis confidence;  
4. disclose that the provider did not inspect images directly;  
5. block analysis when direct image interpretation is required.

Initial analysis should normally require direct vision capability.

---

# **82\. Provider-Specific Schema Transformation**

The adapter may transform standard JSON Schema into provider-compatible schema.

The transformation must preserve:

* required fields;  
* enum restrictions;  
* numeric ranges where supported;  
* object nesting;  
* array structures;  
* nullability semantics.

Unsupported constraints remain enforced application-side.

---

# **83\. Schema Transformation Validation**

Automated tests must verify that provider-specific schema transformations remain semantically equivalent to the canonical application schema.

---

# **84\. Provider Security**

## **84.1 Outbound Data Minimization**

Send only context needed for the analysis.

Do not send:

* password hashes;  
* API secrets;  
* authentication sessions;  
* unrelated Trade Sessions;  
* unnecessary personal data;  
* infrastructure details.

## **84.2 TLS**

All provider calls must use secure TLS connections.

## **84.3 Secret Access**

Only backend and worker processes may resolve provider credentials.

---

# **85\. Secret Storage**

MVP options:

* environment variables;  
* encrypted application secret storage;  
* Docker secrets;  
* VPS secret manager.

The application database should store a secret reference or encrypted value, not expose plaintext through ordinary queries.

---

# **86\. Credential Masking**

Settings API may return:

{  
  "provider": "GEMINI",  
  "configured": true,  
  "credential\_display": "••••••••abcd"  
}

It must never return the full key after storage.

---

# **87\. Credential Rotation**

Credential rotation should:

* validate the new credential;  
* replace the secret atomically;  
* preserve previous analysis history;  
* invalidate old cached clients;  
* log an audit record;  
* never record the full key.

---

# **88\. Health Monitoring**

Provider health metrics should include:

request count  
success rate  
timeout rate  
rate-limit rate  
schema failure rate  
language failure rate  
average latency  
p95 latency  
fallback frequency  
circuit-breaker state  
configuration validity

---

# **89\. Provider Status UI**

Settings may display:

Tersedia  
Tersedia dengan Peringatan  
Konfigurasi Bermasalah  
Sementara Tidak Tersedia  
Dinonaktifkan

The UI must avoid exposing internal errors unnecessarily.

---

# **90\. Provider Usage UI**

Usage views may show:

* requests by provider;  
* tokens;  
* image count;  
* average latency;  
* estimated cost;  
* failure rate;  
* fallback count.

Cost values must be labeled estimates.

---

# **91\. Provider Evaluation**

Providers should be evaluated on:

* schema compliance;  
* factual consistency;  
* visual extraction quality;  
* thesis consistency;  
* probability coherence;  
* language compliance;  
* latency;  
* cost;  
* repair frequency;  
* fallback frequency;  
* user correction frequency.

---

# **92\. Provider Selection Must Not Optimize Bullishness**

A provider must not be preferred because it:

* returns higher target probabilities;  
* recommends holding more often;  
* produces more optimistic narratives.

Provider quality is determined by consistency, evidence use, calibration, and reliability.

---

# **93\. Adapter Unit Tests**

Each adapter must test:

* valid text request;  
* valid vision request;  
* multiple images;  
* structured output;  
* malformed output;  
* timeout;  
* rate limit;  
* authentication failure;  
* context overflow;  
* image rejection;  
* usage extraction;  
* finish-reason mapping;  
* request ID extraction;  
* cancellation.

---

# **94\. Provider Contract Tests**

Run the same normalized test suite against all compatible providers.

Test fixtures should include:

* initial analysis;  
* watching update;  
* open-position update;  
* thesis review;  
* journal summary.

Expected semantic fields must remain consistent across adapters.

---

# **95\. Mock Provider Tests**

The Mock Provider must test:

* deterministic valid result;  
* retry path;  
* correction path;  
* fallback path;  
* cancellation;  
* stale response;  
* provider disagreement;  
* idempotent duplicate delivery.

---

# **96\. Integration Tests**

Integration tests should verify:

1. context package reaches adapter;  
2. images are loaded in correct order;  
3. schema is passed correctly;  
4. response is normalized;  
5. usage is persisted;  
6. errors are normalized;  
7. retry creates a new attempt;  
8. fallback preserves semantic context;  
9. canonicalization uses only accepted output;  
10. late response cannot overwrite canonical state.

---

# **97\. End-to-End Tests**

Required end-to-end cases:

## **97.1 Successful Gemini Vision Analysis**

* upload evidence;  
* queue analysis;  
* call Gemini adapter;  
* validate output;  
* canonicalize analysis;  
* persist usage.

## **97.2 DeepSeek Text-Only Analysis**

* use validated extracted evidence;  
* dispatch compatible text analysis;  
* disclose text-only limitation;  
* validate result.

## **97.3 Primary Failure and Fallback Success**

* primary times out;  
* retry fails;  
* fallback succeeds;  
* fallback result canonicalized;  
* all attempts preserved.

## **97.4 Both Providers Fail**

* canonical state unchanged;  
* job fails;  
* notification created;  
* retry remains available when eligible.

---

# **98\. Configuration Example**

ai\_providers:  
  primary:  
    provider: GEMINI  
    model: ${GEMINI\_MODEL}  
    enabled: true  
    credential\_reference: GEMINI\_API\_KEY  
    timeout\_seconds: 120  
    connection\_timeout\_seconds: 15  
    maximum\_attempts: 3  
    temperature: 0.2  
    maximum\_output\_tokens: 8192  
    require\_structured\_output: true

  fallback:  
    provider: DEEPSEEK  
    model: ${DEEPSEEK\_MODEL}  
    enabled: true  
    credential\_reference: DEEPSEEK\_API\_KEY  
    timeout\_seconds: 120  
    connection\_timeout\_seconds: 15  
    maximum\_attempts: 2  
    temperature: 0.2  
    maximum\_output\_tokens: 8192  
    require\_structured\_output: true

provider\_routing:  
  initial\_analysis:  
    require\_vision: true  
    require\_multi\_image: true  
    allow\_text\_only\_fallback: false

  open\_position\_update:  
    require\_vision\_when\_images\_present: true  
    allow\_text\_only\_fallback: true  
    minimum\_extraction\_quality: 80

  trading\_journal:  
    require\_vision: false  
    require\_long\_context: true

provider\_disagreement:  
  confidence\_points: 15  
  probability\_points: 20  
  require\_review\_on\_thesis\_status\_difference: true

Exact environment values will be finalized in `CONFIG_SPEC.md`.

---

# **99\. Suggested Backend Package Structure**

app/  
├── ai/  
│   ├── providers/  
│   │   ├── base.py  
│   │   ├── registry.py  
│   │   ├── gemini.py  
│   │   ├── deepseek.py  
│   │   └── mock.py  
│   │  
│   ├── models/  
│   │   ├── requests.py  
│   │   ├── responses.py  
│   │   ├── capabilities.py  
│   │   ├── usage.py  
│   │   └── errors.py  
│   │  
│   ├── routing/  
│   │   ├── requirements.py  
│   │   ├── selector.py  
│   │   └── fallback.py  
│   │  
│   ├── structured\_output/  
│   │   ├── schema\_registry.py  
│   │   ├── parser.py  
│   │   ├── repair.py  
│   │   └── validator.py  
│   │  
│   └── diagnostics/  
│       ├── logging.py  
│       └── metrics.py

---

# **100\. Conceptual Adapter Example**

class GeminiProvider(AIProvider):  
    def \_\_init\_\_(  
        self,  
        configuration: ProviderConfiguration,  
        client: GeminiClient,  
    ) \-\> None:  
        self.\_configuration \= configuration  
        self.\_client \= client

    def provider\_name(self) \-\> str:  
        return "GEMINI"

    def model\_name(self) \-\> str:  
        return self.\_configuration.model

    def get\_capabilities(self) \-\> ProviderCapabilities:  
        return self.\_configuration.capabilities

    async def validate\_configuration(  
        self,  
    ) \-\> ProviderValidationResult:  
        return await validate\_gemini\_configuration(  
            client=self.\_client,  
            configuration=self.\_configuration,  
        )

    async def generate\_structured\_response(  
        self,  
        request: AIRequest,  
    ) \-\> AIProviderResponse:  
        self.\_validate\_request\_capabilities(request)

        provider\_request \= build\_gemini\_request(  
            normalized\_request=request,  
            configuration=self.\_configuration,  
        )

        started\_at \= monotonic()

        try:  
            provider\_response \= await self.\_client.generate(  
                provider\_request,  
                timeout=request.timeout\_seconds,  
            )  
        except Exception as error:  
            raise normalize\_gemini\_error(error) from error

        latency\_ms \= elapsed\_milliseconds(started\_at)

        return normalize\_gemini\_response(  
            provider\_response=provider\_response,  
            latency\_ms=latency\_ms,  
            expected\_schema=request.output\_schema,  
        )

The actual adapter must include robust typing, cancellation, logging, and error handling.

---

# **101\. Provider Acceptance Criteria**

The provider layer is accepted when:

1. domain and application services do not import provider SDKs;  
2. Gemini and DeepSeek use a shared provider-neutral interface;  
3. provider capabilities are checked before dispatch;  
4. selected models are not assumed to share provider-wide capabilities;  
5. image limits and context limits are validated;  
6. all analysis responses use structured output;  
7. provider-native structured output does not replace application validation;  
8. Gemini supports the required vision-analysis path;  
9. DeepSeek vision use depends on actual model capability;  
10. text-only fallback is explicitly disclosed;  
11. retries apply only to retryable failures;  
12. every retry creates a distinct attempt record;  
13. fallback uses the same semantic Context Package;  
14. fallback output passes the same validation;  
15. provider disagreement is surfaced rather than averaged;  
16. timeout and late-response behavior cannot corrupt canonical state;  
17. usage and estimated cost are recorded;  
18. provider errors use normalized codes;  
19. credentials remain server-side and masked;  
20. provider health and latency are observable;  
21. Mock Provider supports deterministic failure scenarios;  
22. provider configuration can be validated safely;  
23. model and adapter versions are recorded;  
24. provider history remains immutable;  
25. adding a new provider does not require domain-model changes.

---

# **102\. Final AI Provider Statement**

TradePilot AI must treat AI providers as replaceable external reasoning engines, not as owners of application state.

Every provider receives the same authoritative Trade Session context and must return the same structured analytical contract.

Provider-specific differences in SDKs, image handling, schema support, error formats, and usage reporting must be isolated inside adapters.

Regardless of which provider is used, no result may influence the active trade story until it has passed TradePilot AI’s own validation, contradiction, staleness, and canonicalization rules.

