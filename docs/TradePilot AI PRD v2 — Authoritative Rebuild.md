# TradePilot AI Product Requirements Document

**Document Version:** 2.0  
**Status:** Authoritative Rebuild Product Definition  
**Product Name:** TradePilot AI  
**AI Provider:** Gemini only  
**Production Model:** `gemini-3.1-flash-lite`  
**Engineering Document Language:** English  
**User-Facing Analysis Language:** Indonesian

---

# 1. Purpose

TradePilot AI is a web-based AI Trading Workspace that helps a user manage one trade idea from initial review through final closure.

The product is an AI trading analyst, not an automated trading system.

Gemini may analyze evidence and provide recommendations, but all trading decisions and execution facts belong to the user.

This document defines the approved rebuild product behavior.

Existing code does not define the product.

Existing components may be reused only when they directly support this PRD without importing unnecessary legacy workflow complexity.

---

# 2. Product Principles

The rebuild must preserve these principles:

- one trade per session;
- one complete chronological trade story;
- all evidence remains preserved;
- all Gemini requests and responses remain preserved;
- all user decisions remain preserved;
- all confirmed position facts remain user-owned;
- all monitoring updates remain preserved;
- all closed-session history remains readable;
- Gemini is advisory only;
- no automated trading action;
- no provider routing or fallback;
- no generic workflow engine;
- no generic lifecycle platform;
- no generic schema registry as product authority;
- no generic validation framework as product authority.

---

# 3. Approved Product Flow

The approved flow is:

```text
Create Session
→ Upload Initial Evidence
→ Initial Analysis
→ User chooses BUY, WAIT, or SKIP
```

The three possible paths are:

## 3.1 Direct BUY

```text
Create Session
→ Initial Analysis
→ BUY
→ Open Position
→ repeated Position Updates
→ CLOSE
→ CLOSED
```

## 3.2 WAIT Then BUY

```text
Create Session
→ Initial Analysis
→ WAIT
→ repeated WAIT Updates
→ BUY
→ Open Position
→ repeated Position Updates
→ CLOSE
→ CLOSED
```

## 3.3 WAIT Then SKIP

```text
Create Session
→ Initial Analysis
→ WAIT
→ repeated WAIT Updates
→ SKIP
→ CLOSED_SKIPPED
```

## 3.4 Direct SKIP

```text
Create Session
→ Initial Analysis
→ SKIP
→ CLOSED_SKIPPED
```

---

# 4. Session Model

Each session represents one ticker and one possible trade.

A session must preserve:

- ticker;
- company name;
- initial note;
- uploaded evidence;
- Initial Analysis;
- user decisions;
- WAIT Updates;
- confirmed position facts, when BUY occurs;
- Position Updates;
- closure information, when CLOSE occurs;
- complete chronological history.

Only one position may exist per session.

---

# 5. Approved Session Statuses

The only approved business statuses are:

```text
DRAFT
ANALYZING
ANALYZED
WAITING
OPEN_POSITION
CLOSED
CLOSED_SKIPPED
```

No additional business status may be added without explicit product approval.

Analysis request failures must be recorded on the analysis request.

A failure must not introduce a new permanent business status.

## 5.1 Status Definitions

### DRAFT

The session exists, but Initial Analysis has not completed.

### ANALYZING

The Initial Analysis request is being processed.

### ANALYZED

Initial Analysis completed successfully, and the user has not yet selected BUY, WAIT, or SKIP.

### WAITING

The user selected WAIT.

No position exists.

The user may submit repeated WAIT Updates and may later choose BUY, WAIT, or SKIP.

### OPEN_POSITION

The user selected BUY and confirmed one position.

The user may submit repeated Position Updates and may later CLOSE the position.

### CLOSED

The user previously opened a position and manually closed it.

### CLOSED_SKIPPED

The user selected SKIP without opening a position.

---

# 6. Approved Status Transitions

Only these business transitions are approved:

```text
DRAFT → ANALYZING
ANALYZING → ANALYZED
ANALYZED → WAITING
ANALYZED → OPEN_POSITION
ANALYZED → CLOSED_SKIPPED
WAITING → WAITING
WAITING → OPEN_POSITION
WAITING → CLOSED_SKIPPED
OPEN_POSITION → OPEN_POSITION
OPEN_POSITION → CLOSED
```

No other business transition may exist.

---

# 7. Approved Analysis Types

The only approved analysis types are:

```text
INITIAL_ANALYSIS
WAIT_UPDATE
POSITION_UPDATE
```

Morning, Midday, and Afternoon are observation-period metadata.

They are not separate analysis types.

---

# 8. Observation Periods

The approved observation periods are:

```text
MORNING
MIDDAY
AFTERNOON
```

Observation period is metadata used for WAIT Updates and Position Updates.

---

# 9. Initial Session Creation

The user creates a session by providing:

Required:

- ticker;
- company name.

Optional:

- initial note.

A new session starts with status:

```text
DRAFT
```

---

# 10. Initial Evidence

Before Initial Analysis, the user must upload:

- one orderbook screenshot;
- one three-month chart screenshot;
- one six-month chart screenshot.

Approved evidence types:

```text
ORDERBOOK
CHART_3_MONTH
CHART_6_MONTH
```

Initial Analysis must not start unless all three required evidence files are present.

Evidence must remain preserved after submission and analysis.

---

# 11. Initial Analysis

## 11.1 Input

Initial Analysis receives:

- ticker;
- company name;
- initial note;
- orderbook image;
- three-month chart image;
- six-month chart image.

No position exists at this stage.

Current price is not required as a separate input for Initial Analysis.

## 11.2 Required User-Facing Output

The dashboard must display the result in Indonesian with these sections:

1. Ringkasan
2. Analisis orderbook
3. Analisis chart tiga bulan
4. Analisis chart enam bulan
5. Support
6. Resistance
7. Area entry
8. Rekomendasi stop
9. Rekomendasi target
10. Probabilitas
11. Risiko
12. Trading plan
13. Kesimpulan

All entry, stop, target, probability, and action content from Gemini is advisory only.

Initial Analysis must not create a position.

## 11.3 Completion

Success:

```text
ANALYZING → ANALYZED
```

Failure:

- the analysis request becomes failed;
- user input and evidence remain preserved;
- the session remains recoverable for explicit retry;
- no provider fallback occurs.

---

# 12. Post-Analysis Decision Authority

After Initial Analysis is displayed, the system must show:

```text
BUY
WAIT
SKIP
```

Gemini may recommend one of these actions.

Gemini must not persist or execute the decision.

Only an explicit user action may change the session business state.

---

# 13. BUY Decision

The user selects BUY when they decide to enter the trade.

## 13.1 Required BUY Input

- entry price;
- quantity;
- entry date and time;
- stop loss;
- target price.

Optional:

- user note.

## 13.2 BUY Behavior

After confirmation:

1. Store the user decision as `BUY`.
2. Create exactly one position.
3. Treat all entered position values as confirmed user-owned facts.
4. Change the session to:

```text
OPEN_POSITION
```

5. Display the Position Update form.
6. Do not call Gemini automatically.

Gemini must not modify:

- entry price;
- quantity;
- entry timestamp;
- stop loss;
- target price;
- position status.

Only one BUY and one position may exist per session.

---

# 14. WAIT Decision

The user selects WAIT when they want more evidence before entering.

WAIT creates no position.

## 14.1 WAIT Behavior

After confirmation:

1. Store the user decision as `WAIT`.
2. Create no position.
3. Change the session to:

```text
WAITING
```

4. Display the WAIT Update form.
5. Do not call Gemini automatically.

Repeated WAIT decisions are allowed and must remain auditable.

---

# 15. WAIT Update

## 15.1 Eligibility

A WAIT Update is allowed only when:

- session status is `WAITING`;
- no position exists.

## 15.2 Required Input

- observation period;
- current price;
- observation date and time;
- orderbook screenshot.

Optional:

- user note.

Supporting text for current price:

```text
Masukkan harga terakhir yang terlihat pada orderbook.
```

## 15.3 Authority

The manually entered current price is authoritative.

Gemini must not replace it with a value inferred from the screenshot.

## 15.4 Context

Gemini receives:

- ticker;
- company name;
- current price;
- latest orderbook screenshot;
- observation period;
- observation timestamp;
- Initial Analysis;
- relevant previous WAIT Updates;
- optional user note.

No fabricated position facts may be included.

## 15.5 Required User-Facing Output

The dashboard must display the result in Indonesian with these sections:

1. Ringkasan update
2. Harga saat ini
3. Analisis orderbook
4. Perubahan dibanding analisis sebelumnya
5. Kondisi entry saat ini
6. Risiko utama
7. Peluang kenaikan
8. Peluang penurunan
9. Rekomendasi BUY, WAIT, atau SKIP
10. Trading plan berikutnya
11. Kesimpulan AI

The recommendation is advisory only.

## 15.6 Completion

After a successful WAIT Update:

```text
session.status remains WAITING
```

The user must again be able to choose:

```text
BUY
WAIT
SKIP
```

Multiple WAIT Updates are allowed.

All WAIT Updates must remain visible chronologically.

---

# 16. SKIP Decision

The user selects SKIP when they decide not to enter the trade.

## 16.1 Required SKIP Input

- skip reason.

Optional:

- user note.

Approved skip-reason values:

```text
RISK_TOO_HIGH
SETUP_NOT_ATTRACTIVE
ORDERBOOK_WEAK
MARKET_CONDITION_UNFAVORABLE
WAITING_TOO_LONG
USER_DECISION
OTHER
```

The UI must show readable Indonesian labels.

## 16.2 SKIP Behavior

After confirmation:

1. Store the user decision as `SKIP`.
2. Store the skip reason.
3. Create no position.
4. Require no close price.
5. Change the session to:

```text
CLOSED_SKIPPED
```

6. Store the closure timestamp.
7. Disable further evidence uploads.
8. Disable further Gemini analysis requests.
9. Preserve the complete session history.
10. Clearly show that no trade was opened.
11. Do not call Gemini.

A skipped session must not contain:

- entry price;
- quantity;
- stop loss;
- target price;
- close price;
- realized profit or loss.

SKIP and CLOSE must remain distinguishable in storage and UI.

---

# 17. Position Update

## 17.1 Eligibility

A Position Update is allowed only when:

- session status is `OPEN_POSITION`;
- exactly one open position exists.

## 17.2 Required Input

- observation period;
- current price;
- observation date and time;
- orderbook screenshot.

Optional:

- user note.

## 17.3 Context

Gemini receives:

- ticker;
- company name;
- current price;
- latest orderbook screenshot;
- observation period;
- observation timestamp;
- entry price;
- entry timestamp;
- quantity;
- stop loss;
- target price;
- Initial Analysis;
- relevant WAIT history;
- relevant previous Position Updates;
- optional user note.

## 17.4 Authority

The manually entered current price is authoritative.

Confirmed position facts are authoritative.

Gemini must not modify:

- entry price;
- entry timestamp;
- quantity;
- stop loss;
- target price;
- position status.

## 17.5 Required User-Facing Output

The dashboard must display the result in Indonesian with these sections:

1. Ringkasan update
2. Harga saat ini
3. Kondisi posisi
4. Analisis orderbook
5. Perubahan dibanding analisis sebelumnya
6. Realisme target
7. Risiko penurunan
8. Peluang mencapai target
9. Trading plan
10. Poin pemantauan
11. Peringatan
12. Kesimpulan

## 17.6 Completion

After a successful Position Update:

```text
session.status remains OPEN_POSITION
```

The position remains open and unchanged.

Multiple Position Updates are allowed.

All Position Updates must remain visible chronologically.

---

# 18. CLOSE

The user may close a confirmed open position manually.

CLOSE does not require Gemini.

## 18.1 Required CLOSE Input

- close price;
- close date and time;
- close reason.

Optional:

- user note.

## 18.2 CLOSE Behavior

After confirmation:

1. Validate that one open position exists.
2. Store the closure record.
3. Calculate the realized result.
4. Mark the position as `CLOSED`.
5. Change the session to:

```text
CLOSED
```

6. Disable further analysis submissions.
7. Preserve the complete session history.

Only one closure may exist per open position.

---

# 19. Complete Session Page

Each session must have one dedicated detail page showing the complete trade story.

## 19.1 Required Data Sections

- session information;
- initial evidence;
- Initial Analysis;
- user decisions;
- WAIT Updates;
- confirmed position;
- Position Updates;
- closure information.

## 19.2 Status-Based Actions

### DRAFT

Display the initial evidence and Initial Analysis submission flow.

### ANALYZING

Display processing status.

### ANALYZED

Display:

- Initial Analysis;
- BUY;
- WAIT;
- SKIP.

### WAITING

Display:

- Initial Analysis;
- chronological WAIT Updates;
- WAIT Update form;
- BUY;
- WAIT or Submit Another Update;
- SKIP.

Do not display a position summary.

### OPEN_POSITION

Display:

- Initial Analysis;
- relevant WAIT history;
- confirmed position summary;
- chronological Position Updates;
- Position Update form;
- CLOSE.

Do not display BUY, WAIT, or SKIP.

### CLOSED_SKIPPED

Display:

- Initial Analysis;
- WAIT history, when available;
- SKIP decision;
- skip reason;
- closure timestamp;
- clear indication that no trade was opened.

Disable new submissions.

### CLOSED

Display:

- Initial Analysis;
- WAIT history, when available;
- position details;
- all Position Updates;
- close information;
- realized result, when available.

Disable new submissions.

---

# 20. Chronological History

The session page must preserve and display all events chronologically.

Possible timeline items:

- session created;
- initial evidence uploaded;
- Initial Analysis completed;
- WAIT decision;
- WAIT Update completed;
- BUY decision;
- position created;
- Position Update completed;
- SKIP decision;
- CLOSE completed.

Earlier evidence, analysis, decisions, and position facts must not be overwritten.

---

# 21. Gemini Integration

Gemini is the only approved AI provider.

Production model:

```text
gemini-3.1-flash-lite
```

The rebuild must not include:

- provider routing;
- provider fallback;
- provider selection;
- multi-provider retry;
- DeepSeek;
- OpenAI;
- any other AI provider.

Gemini requests may include text and image inputs.

Structured JSON output is required for the three approved analysis types.

No real Gemini request may be made unless an explicit end-to-end task authorizes it.

---

# 22. Analysis Request Behavior

Approved analysis request statuses:

```text
PENDING
PROCESSING
COMPLETED
FAILED
```

Each request must preserve:

- analysis type;
- provider;
- actual model;
- prompt version;
- input snapshot;
- raw response;
- processed response;
- error information;
- timestamps;
- associated evidence.

One user action must create one analysis request.

Duplicate active submissions must be rejected.

No hidden provider fallback is allowed.

No automatic duplicate analysis may be created.

---

# 23. Evidence Rules

Evidence must:

- belong to the exact user-owned session;
- preserve original file metadata;
- remain available after analysis;
- remain immutable after the related analysis request is submitted;
- remain preserved through failure and retry;
- not depend on a generic EvidenceBatch state machine.

Old evidence and storage must not be deleted during the rebuild.

---

# 24. Data Authority

## 24.1 User-Owned Facts

The following are authoritative user-owned data:

- ticker;
- company name;
- initial note;
- current price;
- observation period;
- observation timestamp;
- uploaded evidence;
- BUY decision;
- WAIT decision;
- SKIP decision;
- CLOSE decision;
- entry price;
- entry timestamp;
- quantity;
- stop loss;
- target price;
- position status;
- close price;
- close timestamp;
- close reason;
- user notes.

## 24.2 Gemini-Owned Output

Gemini may provide:

- summaries;
- observations;
- probabilities;
- risks;
- recommendations;
- trading plans;
- conclusions.

Gemini output is advisory.

Gemini must not overwrite user-owned facts.

---

# 25. Required Rebuild Data Entities

The rebuild requires these logical entities:

```text
trade_sessions_v2
analysis_requests_v2
evidence_uploads_v2
session_decisions_v2
positions_v2
trade_closures_v2
```

The exact database implementation must follow the Detailed Task Plan.

Old business tables must remain available until cutover is verified.

No old table or historical record may be deleted during initial rebuild implementation.

---

# 26. API Boundary

All new rebuild business endpoints must live under:

```text
/api/v2/trade-sessions
```

Old APIs may remain temporarily during verification.

New and old workflow data must not be mixed.

---

# 27. Rebuild Module Boundary

Recommended backend ownership:

```text
backend/app/trade_workspace/
```

Recommended frontend ownership:

```text
frontend/src/features/trade-workspace/
```

The rebuild may reuse general infrastructure such as:

- authentication;
- user identity;
- ownership checks;
- PostgreSQL connection mechanics;
- file-storage mechanics;
- queue mechanics;
- worker runtime mechanics;
- migration tooling;
- Docker Compose runtime;
- gateway routing;
- logging.

The rebuild must not delegate new business behavior to the old lifecycle engine.

---

# 28. Prohibited Product Features

The rebuild must not include:

- Partial Exit;
- Closing Analysis as a required step;
- automated BUY;
- automated WAIT;
- automated SKIP;
- automated CLOSE;
- multiple positions per session;
- automated order execution;
- brokerage integration;
- portfolio management;
- generic trading signals;
- generic workflow configuration;
- additional statuses;
- additional analysis types;
- additional observation periods;
- additional providers;
- additional features without explicit product approval.

---

# 29. Prohibited Technical Architecture

The rebuild must not depend on:

- old lifecycle transition engine;
- EvidenceBatch state machine;
- multi-provider router;
- provider fallback;
- generic workflow engine;
- generic lifecycle platform;
- generic state-machine framework;
- generic schema registry as product authority;
- canonical-versus-transport dual schemas;
- generic domain validation framework as product authority;
- evaluation platform as a runtime requirement;
- Partial Exit workflow;
- Closing Analysis workflow.

---

# 30. Failure and Retry

For analysis failure:

- mark the analysis request as `FAILED`;
- preserve user input;
- preserve evidence;
- preserve previous valid business status;
- preserve confirmed position facts;
- store sanitized error information;
- do not call another provider;
- do not create a duplicate analysis automatically;
- permit explicit manual retry where the UI supports it.

---

# 31. Language Rules

All technical documents, engineering specifications, code instructions, schemas, and prompts must be written in English.

All user-facing Gemini analysis displayed in TradePilot AI must be written in Indonesian.

UI labels may use Indonesian where user-facing.

---

# 32. Definition of Done

The rebuild is complete when all of the following work:

- session creation;
- initial evidence upload;
- Initial Analysis;
- BUY after Initial Analysis;
- WAIT after Initial Analysis;
- repeated WAIT Updates;
- BUY after one or more WAIT Updates;
- SKIP directly after Initial Analysis;
- SKIP after one or more WAIT Updates;
- repeated Position Updates after BUY;
- CLOSE after BUY;
- complete chronological history;
- user-owned facts remain authoritative;
- Gemini does not execute decisions;
- skipped sessions remain distinguishable from closed trades;
- Gemini remains the only AI provider;
- production model is `gemini-3.1-flash-lite`;
- no old workflow dependency controls the rebuild;
- all approved end-to-end paths pass.

---

# 33. Final Product Rule

This PRD is the authoritative product definition for the TradePilot AI rebuild.

The Detailed Task Plan is the authoritative implementation sequence.

When existing code conflicts with this PRD, this PRD wins.

When implementation work requires behavior not explicitly approved here, the task must stop and return:

```text
BLOCKED
```

No scope expansion may be implemented without explicit product-owner approval.
