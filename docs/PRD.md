# **TradePilot AI — Product Requirements Document**

**Document:** `PRD.md`  
**Version:** 1.0  
**Status:** Final  
**Product Name:** TradePilot AI  
**Product Type:** AI Trading Analysis Workspace  
**Primary Market:** Indonesian equities  
**Primary Trading Style:** Swing trading  
**Deployment Model:** Self-hosted VPS  
**Source Control:** GitHub  
**Core Principle:** One Trade, One Story

---

## **1\. Executive Summary**

TradePilot AI is a web-based AI trading analysis workspace designed to follow one stock position from the initial analysis until the position is closed.

TradePilot AI is not an automated signal generator, stock scanner, broker, or trade execution platform. It acts as an AI Trading Analyst that helps the user analyze, monitor, and document a single trading position over time.

Each position is managed through a dedicated Trade Session.

A Trade Session contains the complete history of one trading idea:

Initial analysis → setup monitoring → position entry → position monitoring → position exit → trading journal.

Every new analysis must consider the entire Trade Session history. The AI must not analyze only the latest screenshot in isolation.

The system must preserve the original trading thesis unless new technical evidence provides a clear reason to weaken, revise, or invalidate it.

The product must use a professional workspace interface similar to a developer tool or analytical dashboard. It must not be designed as a generic chatbot interface.

The main product principle is:

**One Trade, One Story.**

---

## **2\. Product Vision**

The vision of TradePilot AI is to provide an individual trader with a persistent AI analyst that understands the complete context of every active trade.

The AI analyst should be able to answer questions such as:

* What was the original reason for entering this trade?  
* What has changed since the initial analysis?  
* Is the original trading thesis still valid?  
* Is the target profit still realistic?  
* Is the stop loss still technically appropriate?  
* Is the orderbook becoming stronger or weaker?  
* Is the current price movement a normal pullback or a thesis invalidation?  
* What should the user monitor during the next trading session?  
* Did the user follow the original trading plan?  
* What lessons should be recorded after the trade is closed?

TradePilot AI should help the user make more disciplined, evidence-based trading decisions without replacing the user’s responsibility for trade execution.

---

## **3\. Problem Statement**

Traders often use general-purpose AI chat applications by repeatedly uploading screenshots of charts and orderbooks.

This approach creates several problems.

### **3.1 Fragmented Analysis**

Analysis for one stock is often mixed with other stocks, unrelated conversations, and separate trading ideas.

This makes it difficult to reconstruct the full history of a position.

### **3.2 No Persistent Trade Context**

A general chatbot may only analyze the latest screenshot without understanding:

* the original setup;  
* the initial entry plan;  
* previous orderbook conditions;  
* previous support and resistance levels;  
* previous confidence estimates;  
* previous probability estimates;  
* changes in the trading thesis;  
* the user’s actual entry price;  
* the active stop loss;  
* the active target profit.

### **3.3 Inconsistent Trading Thesis**

AI recommendations may change too quickly.

For example, the AI may describe a stock as bullish in the morning and bearish at midday without clearly explaining:

* what technical condition changed;  
* whether the change is temporary;  
* whether support has actually broken;  
* whether the new evidence invalidates the original thesis;  
* whether the price is only experiencing a normal pullback.

### **3.4 No Position Lifecycle**

A normal chatbot does not manage structured trade states such as:

* setup preparation;  
* waiting for entry;  
* open position;  
* partial exit;  
* take profit;  
* stop loss;  
* manual exit;  
* cancelled setup;  
* completed trading journal.

### **3.5 Poor Trading Documentation**

After a position is closed, the user must manually reconstruct:

* the initial thesis;  
* the entry decision;  
* every update;  
* every change in confidence;  
* every change in probability;  
* the exit reason;  
* the final result;  
* the lessons learned.

TradePilot AI solves these problems by creating a persistent, structured, and longitudinal AI trading workspace.

---

## **4\. Product Goals**

### **4.1 Primary Goals**

TradePilot AI must:

1. allow the user to create one Trade Session for one stock and one trading lifecycle;  
2. store all screenshots, notes, AI analyses, and trade decisions chronologically;  
3. generate a detailed initial analysis using orderbook and chart evidence;  
4. allow the user to mark a position as open after entry;  
5. compare every new update with all relevant historical information;  
6. maintain a consistent trading thesis;  
7. explain all recommendations using technical reasoning;  
8. track entry, stop loss, target profit, and position status;  
9. update confidence and probability assessments over time;  
10. provide actionable trading plans for the next relevant time period;  
11. convert a closed Trade Session into an AI Trading Journal;  
12. present the entire trade lifecycle on one dedicated page.

### **4.2 Secondary Goals**

The product should:

* reduce impulsive trading decisions;  
* encourage stop-loss discipline;  
* provide visibility into how a thesis evolves;  
* make AI reasoning auditable;  
* help the user learn from past trades;  
* create reusable historical trading records;  
* support future AI performance evaluation.

---

## **5\. Non-Goals**

The initial version of TradePilot AI will not provide:

* automatic trade execution;  
* broker integration;  
* automatic buy or sell orders;  
* automatic stock scanning;  
* automatic daily stock recommendations;  
* real-time exchange market data;  
* portfolio optimization;  
* copy trading;  
* social trading;  
* high-frequency trading;  
* automated scalping;  
* guaranteed profit predictions;  
* autonomous position sizing;  
* autonomous stop-loss modification;  
* autonomous target modification;  
* investment advisory certification;  
* strategy backtesting;  
* direct financial custody.

The user remains fully responsible for every trading decision and execution.

---

## **6\. Target User**

### **6.1 Primary User**

The primary user is an individual trader who:

* trades Indonesian equities;  
* focuses mainly on swing trading;  
* typically holds positions for several trading days;  
* uses orderbook and chart analysis;  
* requires detailed explanations rather than simple signals;  
* wants to monitor one trade continuously;  
* wants to maintain a structured trading journal;  
* prefers analysis output in Bahasa Indonesia.

### **6.2 Initial User Model**

The MVP is designed as a single-user application.

The architecture should not unnecessarily prevent future multi-user support, but the MVP does not require:

* organizations;  
* team workspaces;  
* complex roles;  
* shared sessions;  
* enterprise permissions.

Authentication is still required because the application will run on a VPS and contain private trading data.

---

## **7\. Core Product Principles**

### **7.1 One Trade, One Story**

One Trade Session must represent:

* one ticker;  
* one trading setup;  
* one active thesis;  
* one connected set of entries and exits;  
* one complete position lifecycle.

If the user wants to trade the same ticker again after the session is closed, a new Trade Session must be created.

Historical sessions for the same ticker must remain separate.

### **7.2 Longitudinal Analysis**

Every AI analysis must consider the relevant history of the Trade Session.

This includes:

* initial evidence;  
* initial analysis;  
* previous orderbook screenshots;  
* previous chart screenshots;  
* previous AI assessments;  
* current thesis;  
* previous thesis states;  
* actual entry details;  
* current stop loss;  
* current targets;  
* previous confidence scores;  
* previous probability assessments;  
* user notes;  
* position changes;  
* previous trading plans.

The AI must never treat the latest screenshot as an isolated analysis request.

### **7.3 Thesis Consistency**

The AI must preserve the current trading thesis while the evidence continues to support it.

The AI must not change the thesis only because:

* the price declines slightly;  
* a temporary pullback occurs;  
* one bid level becomes thinner;  
* one offer level becomes thicker;  
* short-term intraday volatility increases;  
* the latest snapshot contains minor conflicting evidence.

A thesis may be weakened or invalidated only when supported by meaningful technical evidence.

Any thesis change must include:

* the previous thesis;  
* the updated thesis;  
* the evidence that caused the change;  
* the technical reasoning;  
* the impact on the trading plan;  
* the impact on stop loss and target profit;  
* the confidence before and after the change.

### **7.4 Explainability First**

TradePilot AI must not produce unsupported recommendations such as:

* BUY;  
* SELL;  
* HOLD;  
* WAIT;  
* BULLISH;  
* BEARISH.

Every assessment must explain:

* what is visible;  
* what has changed;  
* why it matters;  
* what supports the conclusion;  
* what contradicts the conclusion;  
* what the user should monitor;  
* what action is appropriate;  
* what condition would invalidate the plan.

### **7.5 Probability, Not Certainty**

AI assessments must be probabilistic.

The system must not claim that a price movement will definitely happen.

The AI may estimate:

* probability of bullish continuation;  
* probability of reaching the nearest target;  
* probability of a pullback;  
* probability of testing support;  
* probability of reaching the stop loss;  
* probability of thesis invalidation.

These values are analytical estimates, not statistically guaranteed outcomes.

### **7.6 User-Controlled Execution**

TradePilot AI provides analysis and decision support.

The user controls:

* whether to enter;  
* entry price;  
* position size;  
* whether to add a position;  
* whether to reduce a position;  
* whether to modify the stop loss;  
* whether to modify the target;  
* when to exit;  
* whether to ignore an AI recommendation.

### **7.7 Evidence Before Opinion**

The AI must clearly separate:

* visible facts;  
* extracted numerical data;  
* technical interpretation;  
* assumptions;  
* uncertainty;  
* unavailable information.

The AI must never invent numbers that cannot be read from the supplied evidence.

---

## **8\. Language Policy**

### **8.1 Documentation Language**

All project and engineering materials must be written in English.

This includes:

* product documentation;  
* engineering specifications;  
* architecture documentation;  
* database documentation;  
* API contracts;  
* domain models;  
* configuration documentation;  
* implementation instructions;  
* test cases;  
* repository documentation;  
* OpenCode tasks;  
* AI prompt templates;  
* system prompts;  
* structured-output schemas;  
* internal field names;  
* enum values;  
* error codes;  
* source-code identifiers.

### **8.2 User-Facing Analysis Language**

All user-facing trading analysis displayed in the dashboard must be written in Bahasa Indonesia.

This includes:

* executive summaries;  
* orderbook analysis;  
* chart analysis;  
* support and resistance explanations;  
* position assessments;  
* trading plans;  
* confidence explanations;  
* probability explanations;  
* thesis explanations;  
* update comparisons;  
* risk warnings;  
* trading journals.

### **8.3 Internal and Display Separation**

Internal structured data must use English keys and enums.

Example:

{  
  "thesis\_status": "INTACT",  
  "confidence\_score": 72,  
  "target\_probability": 64,  
  "executive\_summary": "Posisi masih berada dalam kondisi cukup sehat."  
}

The internal enum remains English, while user-facing narrative content is written in Bahasa Indonesia.

### **8.4 UI Language**

The primary UI language for the MVP is Bahasa Indonesia.

Technical identifiers and implementation details must remain in English internally.

---

## **9\. Core Terminology**

### **9.1 Trade Session**

A dedicated workspace representing one ticker, one trading setup, and one trade lifecycle.

### **9.2 Initial Evidence**

The minimum evidence required to generate an initial analysis:

* orderbook screenshot;  
* three-month chart screenshot;  
* six-month chart screenshot.

### **9.3 Evidence**

Any uploaded image, market snapshot, or user note used to support analysis.

### **9.4 Initial Analysis**

The first structured AI assessment generated for a Trade Session.

### **9.5 Session Update**

New evidence or information added after the initial analysis.

### **9.6 Trading Thesis**

The primary technical explanation for why the trade setup is considered valid.

### **9.7 Thesis Invalidation**

A technical condition that makes the current thesis no longer valid.

### **9.8 Position**

The user’s actual trade, including entries, exits, stop loss, targets, and profit or loss.

### **9.9 Analysis Version**

A permanent snapshot of one AI analysis result.

### **9.10 Timeline Event**

A chronological record of an action or state change in a Trade Session.

### **9.11 AI Trading Journal**

The final structured review generated after the position is closed.

---

## **10\. Trade Session Lifecycle**

A Trade Session must use an explicit lifecycle.

### **10.1 DRAFT**

The session exists, but required initial evidence is incomplete.

### **10.2 READY\_FOR\_ANALYSIS**

The ticker and required initial evidence are available.

### **10.3 ANALYZING**

An AI analysis job is currently processing.

### **10.4 WATCHING**

The initial analysis is complete, but the user has not entered a position.

The user may continue monitoring the setup or wait for the recommended entry condition.

### **10.5 OPEN\_POSITION**

The user has entered the trade.

Required position information:

* entry price;  
* entry timestamp;  
* active stop loss;  
* at least one target profit.

### **10.6 PARTIALLY\_CLOSED**

Part of the position has been exited, but an active quantity remains.

### **10.7 CLOSED\_TAKE\_PROFIT**

The position has been fully closed because the target profit was reached.

### **10.8 CLOSED\_STOP\_LOSS**

The position has been fully closed because the stop loss was reached.

### **10.9 CLOSED\_MANUAL**

The position has been fully closed manually.

### **10.10 CANCELLED**

The setup was cancelled before an entry was made.

### **10.11 ARCHIVED**

The session is retained for historical purposes and excluded from the active workspace.

---

## **11\. Primary User Workflow**

### **11.1 Create a New Trade Session**

The user selects:

**New Trade Session**

The user provides:

* ticker;  
* company name, optional;  
* market;  
* session title, optional;  
* initial notes, optional.

The system creates a dedicated Trade Session page.

### **11.2 Upload Initial Evidence**

The user uploads:

* an orderbook screenshot;  
* a three-month chart screenshot;  
* a six-month chart screenshot.

Optional evidence may include:

* intraday chart;  
* daily chart;  
* broker summary;  
* foreign flow;  
* news screenshot;  
* catalyst notes;  
* OHLC values;  
* average price;  
* market statistics;  
* personal notes.

### **11.3 Run Initial Analysis**

The user selects:

**Run Initial Analysis**

The system must:

1. validate the required inputs;  
2. store the original evidence;  
3. create an analysis job;  
4. extract visible information;  
5. construct the analysis context;  
6. call the configured AI provider;  
7. validate the structured response;  
8. store the analysis version;  
9. display the user-facing analysis in Bahasa Indonesia;  
10. update the Trade Session status to `WATCHING`.

### **11.4 Monitor the Setup**

While the session is in `WATCHING`, the user may:

* upload a new orderbook screenshot;  
* add notes;  
* add updated chart evidence;  
* update observed price data;  
* cancel the setup;  
* mark the position as open.

### **11.5 Open a Position**

The user selects:

**Mark as Open Position**

The user provides:

* actual entry price;  
* entry timestamp;  
* quantity, optional;  
* active stop loss;  
* target profit;  
* entry notes, optional.

The system must preserve a snapshot of the active thesis at the moment of entry.

### **11.6 Monitor an Open Position**

During an open position, the user regularly uploads updated orderbook screenshots.

The user may classify an update as:

* Morning Update;  
* Midday Update;  
* Closing Update;  
* Custom Update.

The AI must compare the new update against the full relevant history.

### **11.7 Modify Trade Parameters**

The user may manually modify:

* stop loss;  
* target profit;  
* position quantity;  
* notes;  
* planned action.

Every modification must be stored as a timeline event.

### **11.8 Partially Close a Position**

The user may record:

* quantity sold;  
* exit price;  
* exit timestamp;  
* exit reason;  
* remaining quantity.

The session status becomes `PARTIALLY_CLOSED` if an active quantity remains.

### **11.9 Fully Close a Position**

The user records:

* final exit price;  
* final exit timestamp;  
* exit reason;  
* final quantity;  
* optional notes.

The system selects the appropriate closed status.

### **11.10 Generate the AI Trading Journal**

After the position is fully closed, the system generates an AI Trading Journal using:

* the original thesis;  
* all evidence;  
* all analysis versions;  
* all position events;  
* all thesis changes;  
* the entry and exit results;  
* the user’s notes.

---

## **12\. Initial Analysis Requirements**

The initial analysis must produce a structured and detailed report.

### **12.1 Executive Summary**

The report must summarize:

* current technical condition;  
* dominant bias;  
* setup quality;  
* primary opportunity;  
* primary risk;  
* recommended next action.

### **12.2 Today’s Market Summary**

When visible or provided, the analysis must include:

* Open;  
* High;  
* Low;  
* Close or Last Price;  
* Previous Close;  
* Average Price;  
* price change;  
* percentage change;  
* volume;  
* transaction value;  
* position relative to average price.

If a value is not visible, the AI must state that it is unavailable.

### **12.3 Orderbook Analysis**

The analysis must evaluate:

* best bid;  
* best offer;  
* bid depth;  
* offer depth;  
* bid concentration;  
* offer concentration;  
* bid wall;  
* offer wall;  
* demand zones;  
* supply zones;  
* bid-offer imbalance;  
* buyer persistence;  
* seller pressure;  
* possible absorption;  
* possible distribution;  
* liquidity quality;  
* nearest orderbook support;  
* nearest orderbook resistance;  
* risk of spoofing or temporary queues.

The analysis must distinguish between visible evidence and interpretation.

### **12.4 Three-Month Chart Analysis**

The analysis must evaluate:

* short-term trend;  
* swing structure;  
* higher highs or lower highs;  
* higher lows or lower lows;  
* momentum;  
* volume behavior;  
* nearest support;  
* nearest resistance;  
* chart patterns;  
* breakout or breakdown attempts;  
* price position within the recent range.

### **12.5 Six-Month Chart Analysis**

The analysis must evaluate:

* medium-term trend;  
* major price structure;  
* historical support;  
* historical resistance;  
* accumulation zones;  
* distribution zones;  
* dominant trend;  
* major reversal risk;  
* price position within the six-month range.

### **12.6 Support and Resistance**

The analysis must identify:

* immediate support;  
* major support;  
* thesis invalidation level;  
* immediate resistance;  
* major resistance;  
* breakout confirmation level.

Each level must include a technical explanation.

### **12.7 Entry Plan**

The analysis may define:

* ideal entry zone;  
* aggressive entry;  
* conservative entry;  
* breakout entry;  
* pullback entry;  
* confirmation requirements;  
* conditions for avoiding entry;  
* maximum acceptable chase price.

### **12.8 Stop Loss**

The analysis must provide:

* recommended stop-loss level;  
* technical basis;  
* estimated downside;  
* thesis invalidation reason;  
* risk warning.

The stop loss must not be based only on an arbitrary percentage.

### **12.9 Target Profit**

The analysis must provide:

* TP1;  
* TP2, when relevant;  
* technical basis;  
* resistance reference;  
* expected risk-to-reward;  
* partial profit considerations;  
* conditions requiring target revision.

### **12.10 Confidence Assessment**

Confidence measures the quality and reliability of the current analysis.

It must include:

* score from 0 to 100;  
* classification;  
* confidence drivers;  
* confidence reducers;  
* missing evidence;  
* contradictory signals.

Confidence is not the same as probability of price increase.

### **12.11 Probability Assessment**

The initial analysis must estimate:

* bullish continuation probability;  
* nearest-target achievement probability;  
* pullback probability;  
* major-support-break probability;  
* thesis-invalidation probability.

Every probability must include reasoning.

### **12.12 Trading Plan**

The trading plan must contain three scenarios.

#### **Bullish Scenario**

* required confirmation;  
* expected price behavior;  
* user action;  
* target;  
* stop-loss treatment.

#### **Neutral Scenario**

* expected consolidation behavior;  
* levels to monitor;  
* user action;  
* conditions for continuing to wait.

#### **Bearish Scenario**

* weakness signals;  
* invalidation level;  
* user action;  
* exit or cancellation condition.

---

## **13\. Open Position Analysis Requirements**

When the session status is `OPEN_POSITION` or `PARTIALLY_CLOSED`, every update must follow a consistent analysis structure.

### **13.1 Latest Market Summary**

When available, display:

* Open;  
* High;  
* Low;  
* Last or Close;  
* Average;  
* current price versus entry;  
* unrealized profit or loss;  
* distance to stop loss;  
* distance to target profit.

### **13.2 What the Orderbook Shows**

The AI must explain:

* whether bid strength has increased or decreased;  
* whether offer pressure has increased or decreased;  
* whether buyers are defending support;  
* whether sellers are becoming more aggressive;  
* whether offer levels are being absorbed;  
* whether support queues are moving higher or lower;  
* whether distribution risk is increasing;  
* whether the orderbook supports the current price movement;  
* how the latest orderbook differs from the previous snapshot.

### **13.3 Current Position Assessment**

The AI must assess:

* whether the position is still technically healthy;  
* whether the thesis remains valid;  
* whether the target is still realistic;  
* whether the stop loss remains appropriate;  
* whether the user should hold;  
* whether partial profit should be considered;  
* whether position reduction should be considered;  
* whether averaging down should be avoided;  
* whether an objective exit condition has appeared.

### **13.4 What Changed Since the Previous Update**

Every update must include an explicit comparison section.

The comparison should cover:

* price;  
* average price;  
* best bid;  
* best offer;  
* bid depth;  
* offer depth;  
* orderbook support;  
* orderbook resistance;  
* momentum;  
* confidence;  
* probabilities;  
* thesis status;  
* risk level.

### **13.5 Thesis Status**

Allowed values:

* `STRENGTHENING`  
* `INTACT`  
* `INTACT_BUT_WEAKENING`  
* `UNDER_REVIEW`  
* `INVALIDATED`

The user-facing explanation must be written in Bahasa Indonesia.

### **13.6 Target Realism Assessment**

The analysis must evaluate:

* whether the target remains realistic;  
* whether target probability increased or decreased;  
* the main obstacles before reaching the target;  
* the price behavior required;  
* whether the target should remain unchanged;  
* whether the target should be lowered;  
* whether the target may be raised.

The AI cannot change the target without clear reasoning.

### **13.7 Updated Trading Plan**

The trading plan must be relevant to the update timing.

Examples:

* plan until midday;  
* plan until market close;  
* plan for the next session;  
* plan for the next trading day.

### **13.8 Current AI Assessment**

The analysis must include:

* directional bias;  
* confidence score;  
* probability of reaching target;  
* probability of pullback;  
* probability of stop-loss touch;  
* probability of thesis remaining valid;  
* current risk level.

---

## **14\. Longitudinal Analysis Requirements**

### **14.1 Context Package**

Before every AI analysis, the system must create a context package containing:

* Trade Session metadata;  
* session status;  
* ticker;  
* initial thesis;  
* current thesis;  
* initial analysis;  
* relevant previous analyses;  
* relevant historical evidence;  
* current position;  
* entries;  
* exits;  
* active stop loss;  
* active targets;  
* previous confidence;  
* previous probability assessments;  
* previous trading plan;  
* user notes;  
* current evidence;  
* previous comparison summary.

### **14.2 Chronological Awareness**

The AI must understand:

* the order of updates;  
* the timestamp of each update;  
* whether an update is morning, midday, closing, or custom;  
* when the user entered;  
* when the user changed stop loss;  
* when the user changed target;  
* when the thesis changed;  
* when the position was partially or fully closed.

### **14.3 No Isolated Analysis**

The analysis service must not send only the latest screenshot to the AI provider.

Every request must include the current canonical session state and relevant historical context.

### **14.4 Canonical Session Summary**

The system must maintain a structured summary of the current Trade Session.

The summary should include:

* active thesis;  
* active support;  
* active resistance;  
* active invalidation;  
* active entry;  
* active stop loss;  
* active targets;  
* current position status;  
* latest confidence;  
* latest probabilities;  
* unresolved risks;  
* latest recommended action.

### **14.5 Contradiction Detection**

The system must detect meaningful contradictions between analysis versions.

Examples:

* support changes without explanation;  
* resistance changes without explanation;  
* target becomes unrealistic without new evidence;  
* thesis changes from bullish to bearish without an invalidation event;  
* confidence increases while evidence quality decreases;  
* the latest recommendation conflicts with the active trading plan.

When a contradiction occurs, the AI must explain it or preserve the previous assessment.

---

## **15\. Thesis Management Requirements**

### **15.1 Thesis Creation**

The initial thesis must contain:

* direction;  
* technical rationale;  
* supporting evidence;  
* key support;  
* key resistance;  
* invalidation condition;  
* expected scenario;  
* initial confidence.

### **15.2 Thesis Preservation**

The current thesis remains active until:

* evidence strengthens it;  
* evidence weakens it;  
* evidence requires review;  
* evidence invalidates it.

### **15.3 Thesis Revision**

Every thesis revision must record:

* previous thesis;  
* updated thesis;  
* change type;  
* change reason;  
* supporting evidence;  
* analysis version;  
* confidence before;  
* confidence after;  
* timestamp.

### **15.4 Thesis Invalidation**

A thesis may become invalid when a significant technical condition occurs, such as:

* major support breaks with confirmation;  
* price structure changes materially;  
* seller pressure becomes dominant;  
* expected breakout fails;  
* risk-to-reward becomes unacceptable;  
* orderbook deterioration aligns with chart weakness;  
* the original setup conditions no longer exist.

The exact rules will be defined in `THESIS_ENGINE_SPEC.md`.

---

## **16\. Evidence Management**

### **16.1 Supported Evidence Types**

The system must support:

* `ORDERBOOK_SCREENSHOT`  
* `CHART_THREE_MONTH`  
* `CHART_SIX_MONTH`  
* `CHART_DAILY`  
* `CHART_INTRADAY`  
* `BROKER_SUMMARY`  
* `FOREIGN_FLOW`  
* `NEWS_SCREENSHOT`  
* `CUSTOM_IMAGE`  
* `USER_NOTE`  
* `MARKET_DATA_SNAPSHOT`

### **16.2 Evidence Metadata**

Each evidence record must include:

* evidence ID;  
* session ID;  
* evidence type;  
* original file name;  
* generated storage name;  
* MIME type;  
* file size;  
* upload timestamp;  
* market timestamp, when provided;  
* update classification;  
* user caption;  
* extraction result;  
* extraction confidence;  
* processing status.

### **16.3 Original File Preservation**

The original uploaded file must never be overwritten.

The system may create:

* thumbnails;  
* optimized previews;  
* AI-processing variants.

### **16.4 Missing or Unreadable Data**

When evidence is unclear, the AI must state:

* what cannot be read;  
* which values are unavailable;  
* how this affects confidence;  
* what additional evidence would improve the analysis.

---

## **17\. Dashboard Requirements**

### **17.1 Dashboard Overview**

The dashboard should display:

* open positions;  
* watching sessions;  
* sessions requiring updates;  
* recently analyzed sessions;  
* recently closed sessions;  
* journal summary;  
* recent thesis changes;  
* recent AI assessments.

### **17.2 Trade Session Card**

Each session card should display:

* ticker;  
* company name;  
* session status;  
* position status;  
* entry price;  
* latest price, when available;  
* unrealized profit or loss;  
* thesis status;  
* confidence score;  
* latest recommended action;  
* last update timestamp.

### **17.3 Dashboard Filters**

The user must be able to filter by:

* status;  
* ticker;  
* creation date;  
* result;  
* thesis status;  
* profit or loss;  
* active or closed;  
* last update date.

### **17.4 Dashboard Search**

The user must be able to search by:

* ticker;  
* company name;  
* session title;  
* user notes;  
* thesis text;  
* journal text.

---

## **18\. Trade Session Page Requirements**

The Trade Session page is the primary product workspace.

### **18.1 Header**

The header must display:

* ticker;  
* company name;  
* market;  
* session status;  
* created date;  
* last update;  
* thesis status;  
* confidence;  
* position profit or loss;  
* primary actions.

### **18.2 Primary Actions**

Available actions depend on session status.

Possible actions include:

* Upload Evidence;  
* Run Initial Analysis;  
* Add Update;  
* Mark as Open Position;  
* Add Entry;  
* Update Stop Loss;  
* Update Target;  
* Add Note;  
* Record Partial Exit;  
* Close Position;  
* Cancel Setup;  
* Archive Session.

### **18.3 Desktop Workspace Layout**

The recommended desktop layout contains three areas.

#### **Left Navigation**

* active sessions;  
* watching sessions;  
* closed sessions;  
* search;  
* filters;  
* settings.

#### **Main Analysis Workspace**

* latest analysis;  
* market summary;  
* orderbook analysis;  
* chart analysis;  
* support and resistance;  
* thesis;  
* position assessment;  
* trading plan;  
* update comparison;  
* timeline.

#### **Right Context Panel**

* active position details;  
* entry price;  
* average entry;  
* stop loss;  
* targets;  
* confidence;  
* probabilities;  
* evidence gallery;  
* quick notes.

### **18.4 No Chat-First Design**

The interface must not be dominated by chat bubbles.

AI output must be presented as:

* structured cards;  
* report sections;  
* data tables;  
* badges;  
* comparison panels;  
* probability indicators;  
* timeline events;  
* expandable evidence;  
* version history.

A text input may exist for notes or commands, but it must not define the primary interaction model.

### **18.5 Analysis Versioning**

The user must be able to:

* view the latest analysis;  
* open previous analysis versions;  
* compare two analysis versions;  
* inspect confidence changes;  
* inspect probability changes;  
* inspect thesis changes;  
* inspect evidence used in each analysis.

---

## **19\. Timeline Requirements**

The Trade Session timeline must include:

* Session Created;  
* Evidence Uploaded;  
* Initial Analysis Generated;  
* Setup Updated;  
* Position Opened;  
* Additional Entry Recorded;  
* Orderbook Updated;  
* Chart Updated;  
* AI Analysis Generated;  
* Thesis Strengthened;  
* Thesis Weakened;  
* Thesis Under Review;  
* Thesis Invalidated;  
* Stop Loss Changed;  
* Target Changed;  
* Partial Exit Recorded;  
* Position Closed;  
* Journal Generated;  
* User Note Added;  
* Analysis Failed;  
* Analysis Retried.

Every timeline event must include:

* timestamp;  
* event type;  
* title;  
* description;  
* related evidence;  
* related analysis;  
* actor;  
* change summary.

---

## **20\. Position Management Requirements**

### **20.1 Position Entry**

A position entry must include:

* entry price;  
* entry timestamp;  
* quantity, optional;  
* stop loss;  
* target profit.

Optional fields:

* broker fee;  
* capital allocation;  
* entry reason;  
* user notes.

### **20.2 Multiple Entries**

The system should support:

* initial entry;  
* additional entry;  
* partial additional entry.

The system must calculate weighted average entry when quantity is available.

The AI must not automatically recommend averaging down without technical justification and explicit risk evaluation.

### **20.3 Partial Exit**

A partial exit must record:

* quantity sold;  
* exit price;  
* exit timestamp;  
* reason;  
* realized profit or loss;  
* remaining quantity.

### **20.4 Stop-Loss Modification**

Each stop-loss change must record:

* previous stop;  
* new stop;  
* reason;  
* changed by;  
* timestamp.

The system should warn the user when the stop loss is widened.

### **20.5 Target Modification**

Each target change must record:

* previous target;  
* new target;  
* reason;  
* changed by;  
* timestamp.

---

## **21\. AI Model Requirements**

### **21.1 Supported Providers**

The initial system must support:

* Google Gemini;  
* DeepSeek.

### **21.2 Provider Abstraction**

The application must use an AI Provider Abstraction Layer.

Business logic must not depend directly on one provider.

### **21.3 AI Capabilities**

AI providers may be used for:

* image understanding;  
* orderbook interpretation;  
* chart interpretation;  
* text reasoning;  
* longitudinal comparison;  
* structured output generation;  
* context summarization;  
* trading journal generation.

### **21.4 Provider Configuration**

The system must support configuration for:

* provider;  
* model name;  
* API key;  
* temperature;  
* maximum output tokens;  
* timeout;  
* retry count;  
* fallback provider;  
* vision support;  
* prompt version;  
* output language.

### **21.5 Structured Output**

The AI must return structured data validated against a schema.

The application must not depend only on free-form Markdown.

The schema should include fields for:

* executive summary;  
* market summary;  
* orderbook analysis;  
* chart analysis;  
* support and resistance;  
* entry plan;  
* stop loss;  
* targets;  
* thesis;  
* thesis status;  
* confidence;  
* probabilities;  
* trading plan;  
* risks;  
* comparison;  
* missing data;  
* recommended action.

### **21.6 Provider Failure**

When the AI provider fails:

* the analysis job becomes `FAILED`;  
* the error is recorded;  
* the evidence remains available;  
* the Trade Session remains valid;  
* the user may retry;  
* a configured fallback provider may be used;  
* duplicate analyses must not be created accidentally.

---

## **22\. AI Prompt Requirements**

### **22.1 Prompt Language**

All prompts must be written in English.

### **22.2 Output Language Instruction**

Every user-facing analysis prompt must explicitly instruct the model to write narrative content in clear Bahasa Indonesia.

### **22.3 Required Analysis Prompts**

The system must support separate prompts for:

* Initial Analysis;  
* Watching Update;  
* Open Position Update;  
* Partial Exit Review;  
* Closing Analysis;  
* AI Trading Journal;  
* Context Summary;  
* Thesis Review.

### **22.4 Required AI Behavior**

The AI must:

* use relevant historical context;  
* preserve the active thesis when appropriate;  
* explain changes;  
* separate fact from interpretation;  
* acknowledge missing data;  
* avoid certainty;  
* avoid invented values;  
* provide risk warnings;  
* provide next actions;  
* provide invalidation conditions;  
* produce valid structured output;  
* write user-facing narrative fields in Bahasa Indonesia.

### **22.5 Forbidden AI Behavior**

The AI must not:

* guarantee profit;  
* claim that a price will definitely increase;  
* give unexplained BUY, HOLD, or SELL instructions;  
* change thesis without evidence;  
* ignore session history;  
* invent market values;  
* present orderbook queues as certainty;  
* hide uncertainty;  
* encourage stop-loss violations without technical justification;  
* automatically execute decisions.

---

## **23\. Confidence Framework**

Confidence represents the reliability of the analysis based on the available evidence.

Factors may include:

* image readability;  
* evidence completeness;  
* timeframe alignment;  
* chart and orderbook alignment;  
* support and resistance clarity;  
* liquidity quality;  
* historical consistency;  
* conflicting signals;  
* evidence freshness;  
* missing data.

Suggested classifications:

* `LOW`: 0–39  
* `MODERATE`: 40–69  
* `HIGH`: 70–100

Every confidence score must include:

* confidence drivers;  
* confidence reducers;  
* comparison with the previous score;  
* explanation of the change.

---

## **24\. Probability Framework**

Required probability fields include:

* bullish continuation;  
* target achievement;  
* pullback;  
* stop-loss touch;  
* thesis invalidation;  
* thesis remaining valid.

Each probability must include:

* percentage;  
* comparison with the previous update;  
* direction of change;  
* reasoning;  
* supporting evidence;  
* uncertainty level.

Probability values must not be presented as mathematically calibrated unless future evaluation proves calibration quality.

---

## **25\. AI Trading Journal Requirements**

When the position is fully closed, the system must generate a final journal.

### **25.1 Trade Summary**

The journal must include:

* ticker;  
* session start date;  
* session end date;  
* holding duration;  
* average entry;  
* average exit;  
* realized profit or loss;  
* return percentage;  
* exit reason;  
* final outcome.

### **25.2 Thesis Review**

The journal must review:

* initial thesis;  
* thesis quality;  
* whether the thesis remained valid;  
* when the thesis strengthened;  
* when the thesis weakened;  
* whether the thesis was invalidated;  
* whether the exit followed the thesis.

### **25.3 Execution Review**

The journal must evaluate:

* entry quality;  
* exit quality;  
* stop-loss discipline;  
* target discipline;  
* timing;  
* position adjustments;  
* partial exits;  
* user deviations from the plan.

### **25.4 AI Review**

The journal should evaluate:

* accurate AI observations;  
* inaccurate AI observations;  
* useful warnings;  
* missed warnings;  
* probability changes;  
* confidence changes;  
* whether invalidation was detected in time;  
* evidence limitations.

### **25.5 Lessons Learned**

The journal must include:

* what worked;  
* what did not work;  
* what should be repeated;  
* what should be avoided;  
* checklist items for future trades.

### **25.6 User Reflection**

The user may add:

* emotional state;  
* personal entry reason;  
* personal exit reason;  
* mistakes;  
* lessons;  
* trade rating;  
* final notes.

---

## **26\. Notifications**

The MVP may include in-app notifications for:

* analysis completed;  
* analysis failed;  
* session requires an update;  
* open position has not been reviewed;  
* thesis weakened;  
* thesis invalidated;  
* stop loss changed;  
* target changed;  
* journal generated.

Telegram and email notifications are future enhancements unless added in a later specification.

---

## **27\. Authentication and Security**

### **27.1 Authentication**

The MVP must provide:

* login;  
* logout;  
* secure session management;  
* password hashing;  
* failed-login protection;  
* rate limiting.

### **27.2 Secrets**

AI API keys and other secrets must not:

* be stored in frontend code;  
* be committed to GitHub;  
* be exposed to the browser;  
* be written to logs.

Secrets must be stored through environment variables or another secure server-side mechanism.

### **27.3 File Security**

Uploaded evidence must:

* use validated MIME types;  
* have configurable size limits;  
* use generated storage names;  
* be stored outside public static directories;  
* be accessed through authenticated endpoints or signed URLs;  
* be protected against executable uploads.

### **27.4 Auditability**

The system must maintain audit records for changes to:

* session status;  
* position status;  
* thesis;  
* stop loss;  
* targets;  
* entries;  
* exits;  
* AI provider;  
* AI model;  
* prompt version.

---

## **28\. Technical Constraints**

### **28.1 Hosting**

The application will be hosted on a Linux VPS.

Recommended infrastructure:

* Ubuntu;  
* Docker;  
* Docker Compose;  
* Nginx;  
* HTTPS;  
* persistent database volume;  
* persistent evidence volume.

### **28.2 Source Control**

The source code will be managed in GitHub.

The minimum workflow should include:

* `main` branch;  
* feature branches;  
* pull requests;  
* tagged releases.

### **28.3 Suggested Application Stack**

The final technical decision will be documented in `ARCHITECTURE.md`, but the recommended starting point is:

Frontend:

* Next.js;  
* TypeScript.

Backend:

* Python;  
* FastAPI.

Background Processing:

* Python worker;  
* Redis-backed job queue.

Database:

* PostgreSQL.

File Storage:

* local persistent VPS storage for MVP;  
* storage abstraction for future S3-compatible storage.

AI:

* Gemini and DeepSeek through provider adapters.

### **28.4 Deployment**

The application must support:

* reproducible Docker builds;  
* database migrations;  
* health checks;  
* safe deployment;  
* rollback;  
* persistent storage.

---

## **29\. Reliability Requirements**

### **29.1 Analysis Jobs**

AI analysis must run as a background job.

Allowed job states:

* `QUEUED`  
* `PROCESSING`  
* `COMPLETED`  
* `FAILED`  
* `RETRYING`  
* `CANCELLED`

### **29.2 Idempotency**

Retrying an operation must not:

* duplicate evidence;  
* duplicate position entries;  
* duplicate exits;  
* duplicate timeline events;  
* create unintended analysis versions;  
* corrupt session state.

### **29.3 Restart Recovery**

After a VPS or container restart:

* database data must remain available;  
* evidence files must remain available;  
* Trade Session states must remain correct;  
* recoverable jobs should resume or become retryable.

### **29.4 Backup**

The system must support:

* scheduled PostgreSQL backups;  
* evidence backups;  
* configuration backup guidance;  
* documented restoration procedures.

---

## **30\. Performance Requirements**

The MVP should target:

* dashboard load under three seconds under normal conditions;  
* Trade Session page load under three seconds under normal conditions;  
* visible upload progress;  
* image preview before AI analysis completes;  
* non-blocking AI jobs;  
* paginated timeline;  
* thumbnail-based evidence gallery;  
* indexed queries for session, ticker, status, and timestamps.

AI processing duration is not required to be real-time, but processing status must always be visible.

---

## **31\. Observability Requirements**

The system must provide:

* application logs;  
* structured error logs;  
* analysis job logs;  
* AI provider logs;  
* AI usage logs;  
* response duration;  
* retry count;  
* health endpoint;  
* database health checks;  
* worker health checks.

AI request logs should record:

* provider;  
* model;  
* prompt version;  
* estimated input tokens;  
* estimated output tokens;  
* image count;  
* duration;  
* status;  
* retry count;  
* estimated cost.

Secrets and sensitive user data must not be logged unnecessarily.

---

## **32\. Cost Visibility**

The system should record:

* number of AI requests;  
* provider;  
* model;  
* token usage;  
* image usage;  
* estimated request cost;  
* estimated session cost;  
* estimated monthly cost.

The user should be able to inspect AI usage from a settings or administration page.

---

## **33\. Functional Requirements**

### **FR-001 — Create Trade Session**

The user can create a Trade Session for one ticker.

### **FR-002 — Upload Initial Evidence**

The user can upload an orderbook screenshot, a three-month chart, and a six-month chart.

### **FR-003 — Generate Initial Analysis**

The system can generate a structured initial analysis.

### **FR-004 — Display Indonesian Analysis**

All user-facing analysis narrative is displayed in Bahasa Indonesia.

### **FR-005 — View Dedicated Session Workspace**

The user can view the complete lifecycle of one trade on one page.

### **FR-006 — Add Session Update**

The user can add new orderbook screenshots, charts, market data, or notes.

### **FR-007 — Compare Historical Context**

The AI compares the latest update with relevant historical evidence and analyses.

### **FR-008 — Maintain Trading Thesis**

The system stores and evaluates the current trading thesis.

### **FR-009 — Open Position**

The user can mark a session as an open position.

### **FR-010 — Track Position**

The system can track entries, stop loss, targets, and position status.

### **FR-011 — Update Stop Loss**

The user can modify the stop loss with full history.

### **FR-012 — Update Target Profit**

The user can modify targets with full history.

### **FR-013 — Record Additional Entry**

The user can record an additional position entry.

### **FR-014 — Record Partial Exit**

The user can record a partial exit.

### **FR-015 — Close Position**

The user can fully close a position.

### **FR-016 — Generate Trading Journal**

The system generates an AI Trading Journal after closure.

### **FR-017 — View Timeline**

The user can view all session events chronologically.

### **FR-018 — Version AI Analyses**

Each AI analysis is stored as an immutable version.

### **FR-019 — Compare Analysis Versions**

The user can compare two analysis versions.

### **FR-020 — Retry Failed Analysis**

The user can retry a failed analysis job.

### **FR-021 — Search Sessions**

The user can search historical and active sessions.

### **FR-022 — Archive Session**

The user can archive a session.

### **FR-023 — Configure AI Provider**

The system can use Gemini or DeepSeek.

### **FR-024 — View AI Usage**

The user can inspect AI usage and estimated cost.

---

## **34\. Non-Functional Requirements**

### **NFR-001 — Security**

All pages, APIs, and evidence files must require authorization.

### **NFR-002 — Data Durability**

Trade Session data must survive restarts and deployments.

### **NFR-003 — Explainability**

Every meaningful AI recommendation must include reasoning.

### **NFR-004 — Traceability**

Every thesis, position, stop-loss, target, entry, exit, and analysis change must be traceable.

### **NFR-005 — Provider Independence**

Core application logic must not be tightly coupled to one AI provider.

### **NFR-006 — Responsive Interface**

The product must support desktop, tablet, and mobile, with desktop as the primary experience.

### **NFR-007 — Accessibility**

The interface should use semantic HTML, keyboard navigation, and sufficient contrast.

### **NFR-008 — Maintainability**

Frontend, backend, worker, AI integration, storage, and domain logic must have clear boundaries.

### **NFR-009 — Structured AI Output**

AI responses must be validated against a schema.

### **NFR-010 — Historical Consistency**

Every analysis must be traceable to the session context and evidence used.

### **NFR-011 — Language Consistency**

Engineering artifacts must use English, while user-facing trading analysis must use Bahasa Indonesia.

---

## **35\. MVP Scope**

The MVP includes:

1. single-user authentication;  
2. dashboard;  
3. Trade Session creation;  
4. initial evidence upload;  
5. initial analysis;  
6. `WATCHING` state;  
7. `OPEN_POSITION` state;  
8. `PARTIALLY_CLOSED` state;  
9. morning updates;  
10. midday updates;  
11. closing updates;  
12. custom updates;  
13. longitudinal analysis;  
14. thesis tracking;  
15. confidence tracking;  
16. probability tracking;  
17. entry management;  
18. stop-loss management;  
19. target management;  
20. additional entries;  
21. partial exits;  
22. full exits;  
23. AI Trading Journal;  
24. analysis versioning;  
25. evidence history;  
26. Gemini provider support;  
27. DeepSeek provider support;  
28. PostgreSQL;  
29. background jobs;  
30. persistent file storage;  
31. Docker deployment;  
32. GitHub repository;  
33. basic CI/CD;  
34. logging;  
35. AI usage tracking;  
36. professional workspace UI;  
37. Bahasa Indonesia user-facing analysis.

---

## **36\. Future Scope**

Potential future features include:

* OCR-based orderbook extraction;  
* automatic table extraction;  
* broker summary analysis;  
* foreign-flow analysis;  
* real-time market data;  
* historical price API integration;  
* corporate action data;  
* news ingestion;  
* catalyst monitoring;  
* Telegram notifications;  
* email notifications;  
* mobile application;  
* multi-user support;  
* portfolio risk dashboard;  
* trade statistics;  
* AI calibration;  
* prompt evaluation;  
* automated screenshot comparison;  
* visual orderbook diff;  
* chart annotation;  
* journal PDF export;  
* broker integration;  
* strategy backtesting;  
* automatic stock scanner.

These features must not delay the MVP.

---

## **37\. Success Metrics**

### **37.1 Product Usage Metrics**

* number of Trade Sessions created;  
* percentage of sessions reaching initial analysis;  
* percentage of sessions becoming open positions;  
* percentage of closed sessions receiving a journal;  
* average updates per open position;  
* session completion rate.

### **37.2 Analysis Quality Metrics**

* structured-response validation rate;  
* percentage of analyses using historical context;  
* percentage of thesis changes with valid reasons;  
* number of unsupported numeric claims;  
* user usefulness rating;  
* user consistency rating.

### **37.3 Reliability Metrics**

* analysis completion rate;  
* analysis failure rate;  
* retry rate;  
* upload failure rate;  
* worker availability;  
* backup success rate;  
* deployment success rate.

### **37.4 Trading Discipline Metrics**

* percentage of positions with a stop loss;  
* percentage of exits following the active plan;  
* number of widened stop losses;  
* number of target changes without documented reasons;  
* number of closed sessions without reflection.

---

## **38\. MVP Acceptance Criteria**

The MVP is accepted when:

1. the user can securely log in;  
2. the user can create a Trade Session;  
3. one Trade Session represents one ticker and one trading lifecycle;  
4. the user can upload the three required initial evidence files;  
5. the system can generate a structured initial analysis;  
6. the user-facing analysis is displayed in Bahasa Indonesia;  
7. the initial analysis includes market summary, orderbook, charts, support, resistance, entry, stop loss, target, confidence, probabilities, and trading plan;  
8. the user can mark a position as open;  
9. the user can upload multiple new orderbook screenshots;  
10. each new analysis compares the latest update with relevant history;  
11. the AI explains what changed since the previous update;  
12. the AI preserves or revises the thesis with technical reasoning;  
13. the user can view the entire timeline;  
14. the user can modify stop loss and targets;  
15. the user can record additional entries;  
16. the user can record partial exits;  
17. the user can fully close a position;  
18. the system generates an AI Trading Journal;  
19. the closed session remains accessible as history;  
20. AI responses are stored as structured data;  
21. evidence files remain available after restart;  
22. database data remains available after restart;  
23. the application is deployed on a VPS;  
24. the source code is managed in GitHub;  
25. Gemini and DeepSeek can be configured through provider abstraction.

---

## **39\. Key Product Risks**

### **39.1 AI Hallucination**

The AI may misread or invent values.

Mitigation:

* structured extraction;  
* explicit missing-data reporting;  
* evidence confidence;  
* schema validation;  
* original file preservation;  
* user correction workflow.

### **39.2 Orderbook Misinterpretation**

An orderbook is only a temporary snapshot.

Mitigation:

* explain orderbook limitations;  
* compare multiple snapshots;  
* combine orderbook with chart evidence;  
* avoid treating large queues as certainty;  
* reduce confidence when evidence is ambiguous.

### **39.3 Context Window Limitations**

Long sessions may exceed model context limits.

Mitigation:

* canonical session summary;  
* rolling historical summary;  
* structured state;  
* relevant evidence selection;  
* analysis compression;  
* immutable core thesis history.

### **39.4 Thesis Drift**

The AI may change its opinion without justification.

Mitigation:

* thesis state model;  
* contradiction detection;  
* mandatory change reason;  
* historical comparison;  
* prompt governance;  
* analysis versioning.

### **39.5 Provider Dependency**

Provider changes may affect response quality or availability.

Mitigation:

* provider abstraction;  
* fallback provider;  
* prompt versioning;  
* response normalization;  
* retry policies;  
* provider evaluation.

### **39.6 User Over-Reliance**

The user may treat AI analysis as certainty.

Mitigation:

* probability language;  
* clear risk explanations;  
* no guaranteed returns;  
* user-controlled execution;  
* explicit decision-support positioning.

### **39.7 Inconsistent Indonesian Output**

The AI may return mixed English and Indonesian narrative.

Mitigation:

* explicit output-language rules;  
* schema-level language validation where possible;  
* prompt tests;  
* response review;  
* terminology guidelines.

---

## **40\. Locked Product Decisions**

The following decisions are locked by this PRD:

1. The product name is TradePilot AI.  
2. TradePilot AI is an AI Trading Analysis Workspace.  
3. It is not an automated signal generator.  
4. It is not an auto-trading system.  
5. The core principle is One Trade, One Story.  
6. One Trade Session represents one ticker and one trading lifecycle.  
7. Analysis must be longitudinal.  
8. The AI must preserve the active trading thesis unless evidence justifies a change.  
9. Thesis changes must be explained and recorded.  
10. AI output must provide detailed technical reasoning.  
11. The initial evidence consists of an orderbook screenshot, a three-month chart, and a six-month chart.  
12. Open-position analysis must include detailed position, orderbook, target, probability, and trading-plan assessments.  
13. The user uploads market evidence manually in the MVP.  
14. AI output must use a structured schema.  
15. Gemini and DeepSeek must be supported through provider abstraction.  
16. The application runs on a VPS.  
17. The source code is managed in GitHub.  
18. The interface must be a professional analytical workspace, not a generic chatbot.  
19. A closed Trade Session becomes an AI Trading Journal.  
20. The user remains responsible for all trade execution.  
21. All engineering documents and prompts must be written in English.  
22. All user-facing trading analysis must be written in Bahasa Indonesia.  
23. Internal keys, enums, and technical identifiers must remain in English.  
24. The primary MVP market is Indonesian equities.  
25. The primary trading style is swing trading.

---

## **41\. Required Engineering Documentation**

The following documents must be created after this PRD:

1. `PRODUCT_RULES.md`  
2. `USER_FLOWS.md`  
3. `UX_UI_SPEC.md`  
4. `ARCHITECTURE.md`  
5. `DOMAIN_MODEL.md`  
6. `SESSION_LIFECYCLE.md`  
7. `DATABASE_SCHEMA.md`  
8. `DATABASE_SCHEMA.sql`  
9. `AI_ANALYSIS_SPEC.md`  
10. `THESIS_ENGINE_SPEC.md`  
11. `CONTEXT_MEMORY_SPEC.md`  
12. `PROBABILITY_CONFIDENCE_SPEC.md`  
13. `VISION_INPUT_SPEC.md`  
14. `PROMPT_SPEC.md`  
15. `AI_PROVIDER_SPEC.md`  
16. `API_SPEC.md`  
17. `BACKGROUND_JOBS_SPEC.md`  
18. `FILE_STORAGE_SPEC.md`  
19. `AUTH_SECURITY_SPEC.md`  
20. `CONFIG_SPEC.md`  
21. `OBSERVABILITY_SPEC.md`  
22. `TEST_PLAN.md`  
23. `AI_EVALUATION_PLAN.md`  
24. `DEPLOYMENT_SPEC.md`  
25. `CI_CD_SPEC.md`  
26. `BACKUP_RECOVERY_SPEC.md`  
27. `GITHUB_REPOSITORY_STRUCTURE.md`  
28. `MVP_IMPLEMENTATION_PLAN.md`  
29. `OPEN_CODE_TASKS.md`  
30. `README.md`

---

## **42\. Final Product Statement**

TradePilot AI is a dedicated workspace where every trade has its own memory, evidence, thesis, timeline, decisions, and final evaluation.

The product must not only answer:

“Should I buy, hold, or sell this stock?”

It must be able to explain:

“What was the original thesis, what has changed since the first analysis, whether the thesis remains valid, whether the target is still realistic, which risks are increasing, and what disciplined action should be taken based on the complete history of the position.”

That is the meaning of:

**One Trade, One Story.**

