# Analysis Types and Input Contracts (System-Acquired Evidence Edition)

## 1. Purpose

Define the approved AI analysis types and their required input contracts under the **System-Acquired Evidence** model. This document defines input eligibility, domain payloads, snapshot structures, and authority boundaries.

## 2. Scope and Authorities

The PRD (`docs/evidence-expansion/TradePilot_AI_PRD_System_Acquired_Evidence.md`) is authoritative. The approved analysis types are:
1. `INITIAL_ANALYSIS`
2. `WATCHING_UPDATE` (or `WAIT_UPDATE`)
3. `OPEN_POSITION_UPDATE` (or `POSITION_UPDATE`)
4. `CLOSING_ANALYSIS`

## 3. Input Contract Principles

- **System-Acquired Evidence is Authoritative**: Market data is automatically ingested from authoritative providers (Pluang, IDX, Stockbit) via ZAPI and stored as immutable `EvidenceSnapshot` records.
- **Structured Tabular / JSON Input**: Analysis requests feed structured domain data (Quote, Orderbook, 6M OHLCV, Foreign Flow, Broker Flow, Market Context) into the AI Context Builder.
- **Evidence Delta for Re-evaluation**: Subsequent updates use `EvidenceDelta` (comparing current snapshot against baseline snapshot) rather than re-reading the full history.
- **Deterministic Validation**: Only sessions with status `EVIDENCE_VALIDATED` proceed to AI analysis. Incomplete or invalid data halts the pipeline with `EVIDENCE_INCOMPLETE`.

## 4. INITIAL_ANALYSIS Input Contract

- **Analysis Type**: `INITIAL_ANALYSIS`
- **Purpose**: Produce the foundational trade thesis, support/resistance levels, entry plan, stop loss, targets, risk/reward assessment, and scenario probabilities.
- **Allowed Session Status**: `EVIDENCE_VALIDATED` (transitioned from `DRAFT` via automated acquisition).
- **Required Snapshot Domains**:
  1. `quote`: Authoritative current price, open, high, low, volume, value, frequency.
  2. `orderbook`: Best Bid/Ask, total Bid/Ask lots, Bid/Ask ratio, top 3-5 bid/ask depth.
  3. `historical_ohlcv`: 130 trading days daily OHLCV bars with computed MA20/50/200, RSI14, ATR14, and Swing High/Low.
  4. `foreign_flow`: 1D, 1W, 1M, 3M Net Foreign volume/value and accumulation status.
  5. `broker_flow`: 1D Broker Summary with Top 3/5 Net Buyers and Sellers, concentration percentages, and Bandar status.
  6. `market_context`: IHSG (COMPOSITE) index performance.
- **User-Provided Context**: Ticker symbol, company name, trading style, and optional setup thesis notes.
- **AI Context Payload**: Serialized compact Markdown tables and canonical fact JSON.

## 5. WATCHING_UPDATE Input Contract

- **Analysis Type**: `WATCHING_UPDATE`
- **Purpose**: Re-evaluate the setup while the user is monitoring the ticker before entering a position.
- **Allowed Session Status**: `WATCHING`.
- **Required Inputs**:
  1. `Previous Analysis`: Initial thesis, key resistance/support, planned entry zone, stop loss plan.
  2. `Current Snapshot`: Fresh quote, live orderbook, and today's broker/foreign flow.
  3. `Evidence Delta`: Mathematical shift in price, bid/ask ratio, foreign flow accumulation, and broker aggression.
- **AI Objective**: Determine if the thesis is `STRENGTHENING`, `INTACT`, `INTACT_BUT_WEAKENING`, `UNDER_REVIEW`, or `INVALIDATED`, and update recommendations (`WAIT` -> `BUY`, etc.).

## 6. OPEN_POSITION_UPDATE Input Contract

- **Analysis Type**: `OPEN_POSITION_UPDATE`
- **Purpose**: Re-evaluate an active trade position based on live market shifts against confirmed position facts.
- **Allowed Session Status**: `OPEN_POSITION`.
- **Required Inputs**:
  1. `Confirmed Position Facts`: Entry price, quantity, confirmed stop loss, confirmed target, unrealized PnL.
  2. `Current Snapshot` & `Evidence Delta`.
  3. `Previous Position Analysis`.
- **AI Objective**: Recommend holding, tightening stop loss, taking partial profit, or full exit based on microstructure & smart money flow.

## 7. Evidence Authority Hierarchy

1. User-confirmed execution records (Entry price, executed lots, confirmed SL/TP).
2. Canonical System-Acquired Snapshot facts (Validated ZAPI data).
3. System-computed technical indicators & flow aggregations.
4. Current canonical thesis and previous accepted analysis.
5. User notes and discretionary context.
6. AI reasoning and inferences.
