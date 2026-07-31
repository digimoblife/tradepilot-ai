# TradePilot AI

**AI Trading Analysis Workspace (Authoritative Rebuild V2)**

TradePilot AI is a web-based AI trading analysis workspace designed to follow one stock position from initial analysis until the position is closed. Each position is managed through a dedicated Trade Session containing the complete history of one trading decision and lifecycle.

**One Trade, One Story.**

---

## Approved Technology Stack & Architecture

| Layer | Technology / Implementation |
|-------|-----------------------------|
| **Frontend** | Next.js 16, React 19, TypeScript, Vanilla CSS |
| **Backend** | FastAPI, Python 3.14, AsyncSQLAlchemy 2, PostgreSQL (`psycopg`), Alembic |
| **Worker Engine** | Dedicated background worker with atomic PostgreSQL row locking (`analysis_requests_v2`) |
| **Database & Queue** | PostgreSQL (`trade_sessions_v2`, `analysis_requests_v2`, `evidence_uploads_v2`, `session_decisions_v2`, `positions_v2`, `trade_closures_v2`) |
| **Concurrency Control** | Transaction-scoped PostgreSQL advisory locks (`pg_advisory_xact_lock`) |
| **Primary AI Provider** | Direct Gemini API Integration (`gemini-3.1-flash-lite`) |
| **Evidence Storage** | Local VPS Storage (`LocalFileStorage`) |

---

## Repository Map

```
tradepilot-ai/
├── backend/                    — FastAPI backend application, V2 rebuild services & endpoints
│   └── app/
│       ├── database/           — Database engine and cancellation-safe async session dependency
│       └── trade_workspace/    — Rebuild models, schemas, services, and V2 API routes (`/api/v2/trade-sessions`)
├── worker/                     — Python background worker for rebuild request queue processing
│   └── app/
│       ├── consumers/          — Rebuild analysis request queue consumer (`analysis_requests_v2`)
│       └── runtime.py          — Worker loop and consumer initialization
├── frontend/                   — Next.js frontend application & features
│   └── src/
│       └── features/
│           ├── trade-workspace/— V2 Trade Workspace (Session list, Initial Analysis, BUY/WAIT/SKIP, WAIT/Position updates, CLOSE)
│           └── analysis/       — Analysis components and request forms
├── schemas/
│   └── rebuild/v1/             — Compact JSON Schemas for AI output validation
├── prompts/                    — Versioned system and user prompts
├── infra/                      — Docker & Compose configuration
├── docs/
│   ├── TradePilot AI PRD v2 — Authoritative Rebuild.md
│   ├── TradePilot AI Rebuild — Detailed Task Plan.md
│   └── rebuild/AUTHORITATIVE_TASK_LEDGER.md
└── storage/                    — Local evidence & file storage
```

---

## Rebuild Lifecycle & Key Workflows (V2)

The V2 rebuild architecture replaces broker dependencies and legacy polling with a durable database-backed queue and transaction-scoped concurrency control.

```
   [ DRAFT ] ───────────► [ ANALYZING ] ───────────► [ ANALYZED ]
(Upload Evidence)      (Queue Request V2)           (Gemini Complete)
                                                           │
                                            ┌──────────────┼──────────────┐
                                            ▼              ▼              ▼
                                         [ BUY ]        [ WAIT ]       [ SKIP ]
                                            │              │              │
                                            ▼              ▼              ▼
                                    [ OPEN_POSITION ]  [ WAITING ] [ CLOSED_SKIPPED ]
                                            │              │
                                            │       (WAIT Update)
                                            ▼              │
                                     (Position Update)     │
                                            │              │
                                            ▼              │
                                        [ CLOSE ] ◄────────┘
                                            │
                                            ▼
                                        [ CLOSED ]
```

### Core V2 Workflows

1. **Initial Analysis**: Upload orderbook, 3-month chart, and 6-month chart evidence $\to$ queue `INITIAL_ANALYSIS` request $\to$ worker processes with Gemini $\to$ transition to `ANALYZED`.
2. **Post-Analysis Decisions**:
   - **BUY**: Submit entry facts (price, quantity, stop-loss, target) $\to$ transition to `OPEN_POSITION`.
   - **WAIT**: Confirm wait $\to$ transition to `WAITING`.
   - **SKIP**: Select reason & note $\to$ transition to `CLOSED_SKIPPED`.
3. **WAIT Updates**: Upload updated orderbook & price $\to$ queue `WAIT_UPDATE` request $\to$ re-evaluate trading setup.
4. **Position Updates**: Monitor open position with updated orderbook & price $\to$ queue `POSITION_UPDATE` request.
5. **CLOSE**: Confirm position exit facts $\to$ calculate realized PnL $\to$ transition to `CLOSED`.

---

## Technical Highlights

- **Durable Database-Backed Queue**: Requests are inserted into `analysis_requests_v2` with state `PENDING`. Worker atomically claims requests using `FOR UPDATE SKIP LOCKED` into state `PROCESSING`.
- **Transaction-Scoped Concurrency**: Session mutations and queues use `pg_advisory_xact_lock`, eliminating connection lock leaks on task cancellation or client disconnect.
- **Cancellation-Safe Database Sessions**: FastAPI dependency `get_db_session` catches `BaseException` (including `asyncio.CancelledError`) to execute clean transaction rollbacks.
- **Controlled Frontend Polling**: Polling loops poll at controlled 5-second intervals with primitive state dependencies, preventing high-frequency request loops and stopping immediately on terminal status.

---

## Development & Testing

### Backend & Worker Testing

```bash
# Run V2 Rebuild database & concurrency tests using local virtualenv
DATABASE_SYNC_URL="postgresql+psycopg://cahyo@localhost:5432/tradepilot_test" \
backend/.venv/bin/pytest backend/tests/trade_workspace/
```

### Frontend Testing & Build

```bash
# Run Vitest test suite
cd frontend && npm test

# Typecheck and production build
cd frontend && npx tsc --noEmit
cd frontend && NEXT_PUBLIC_API_BASE_URL="http://localhost:8000" npm run build
```

---

## Language Policy

- **User-facing analysis & workspace UI:** Indonesian (Bahasa Indonesia)
- **Engineering documentation, codebase, comments, schemas, prompts, and API contracts:** English
