# TradePilot AI

**AI Trading Analysis Workspace**

TradePilot AI is a web-based AI trading analysis workspace designed to follow one stock position from initial analysis until the position is closed. Each position is managed through a dedicated Trade Session containing the complete history of one trading idea.

**One Trade, One Story.**

## Approved Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js, TypeScript |
| Backend | FastAPI, Python, SQLAlchemy, Alembic |
| Worker | Python background worker |
| Database | PostgreSQL |
| Queue | PostgreSQL-backed job queue |
| Primary AI | Gemini |
| Fallback AI | DeepSeek |
| Deployment | Single VPS |
| Evidence Storage | VPS filesystem / local storage |

## Repository Map

```
tradepilot-ai/
├── backend/                    — FastAPI backend application & services
├── worker/                     — Python background worker for analysis jobs
├── frontend/                   — Next.js frontend application & features
├── schemas/
│   └── production/v1/          — Production JSON Schema package
├── prompts/
│   └── production/v1/          — Versioned production system & user prompts
├── infra/
│   ├── docker/                 — Docker / Compose configuration
│   └── deployment/             — VPS deployment configuration
├── scripts/                    — Development and maintenance scripts
├── tests/                      — Backend & integration tests
├── docs/                       — Engineering documentation & PRDs
├── storage/                    — Local evidence & file storage
├── .editorconfig
├── .env.example
├── .gitignore
└── Makefile
```

## Implementation Status

**Backend: 115 tests passing in Pytest across 8 test suites.**  
**Frontend: 655 tests passing across 26 test files in Vitest (0 errors, 100% clean typecheck and Next.js build).**

### Milestone Features (P1 – P7 Complete)

| Milestone | Feature | Key Capabilities | Backend Tests | Frontend Tests |
|-----------|---------|------------------|---------------|----------------|
| **P1** | **Lifecycle & Core State** | Canonical lifecycle (`DRAFT`, `READY`, `WATCHING`, `OPEN_POSITION`, `CLOSED`), deterministic allowed actions, strict ownership. | 54 | 27 |
| **P2 / P2.1** | **Evidence & Batch Integrity** | Idempotent evidence batches, file upload validation, monitoring slot selection (`MORNING`, `MIDDAY`, `CLOSE`), draft index integrity. | 12 | 17 |
| **P3** | **Watching Update Flow** | Repeated watching updates, compact context summaries, catalog prompt selection, schema validation, batch freezing. | 10 | 37 |
| **P4** | **Open Position Update** | User `BUY` entry confirmation, slot-based open position evidence batches, active stop/target audit logging. | 12 | 43 |
| **P5** | **Sell & Closing Analysis** | Full exit confirmation (`SELL`), application-calculated return % & duration, atomic closure transactions, post-trade Closing Analysis. | 10 | 45 |
| **P6** | **Historical Same-Ticker Context** | Secondary same-ticker prior terminal session lookup (max 5, newest-first), compact summaries, prompt authority enforcement, secondary UI history drawer. | 11 | 2 |
| **P7** | **ML-Ready Dataset & Evaluation Records** | `evaluation_records` model, structured prediction/user decision/outcome tracking, completeness markers (`COMPLETE`, `PARTIAL`), JSON/CSV bounded export, `/evaluations` dashboard. | 8 | 1 |

### Backend / Worker / Schemas

- **FastAPI backend**: Full REST API with authentication, session state management, evidence uploading, job creation, and evaluation endpoints.
- **Worker engine**: Background job polling, Gemini provider integration, schema validation, fallback logic, and analysis persistence.
- **Production JSON Schemas**: 11 production schemas registered in schema catalog and manifest.
- **Evaluation & Dataset**: Bounded JSON/CSV exports (`/api/evaluation-records/export/json` and `/export/csv`), on-demand backfill service.

### Frontend (Next.js / TypeScript)

- **655 Vitest tests** passing with 100% clean typecheck (`tsc --noEmit`) and Next.js production build (`next build`).
- **5 Analysis Views**: Initial Analysis, Watching Update, Open Position Update, Partial Exit Review, Closing Analysis.
- **Interactive Action Modals**: Open Position, Confirm Stop, Change Stop, Confirm Target, Change Target, Partial Exit, Full Exit.
- **Same-Ticker History Panel**: Compact secondary history indicator badge (`Riwayat ticker digunakan: N sesi sebelumnya`) and expandable drawer.
- **Evaluation Dashboard**: Dedicated `/evaluations` view with record metrics, filters, data table, and JSON/CSV export actions.

## Language Policy

- **User-facing analysis & dashboard output:** Indonesian (Bahasa Indonesia)
- **Engineering documents, code, comments, schemas, prompts, field names, and API contracts:** English

## Docker Development

```bash
cp .env.example .env          # Configure environment
make docker-build              # Build all container images
make docker-up                 # Start all services
make docker-logs               # Tail logs
make docker-down               # Stop (preserves volumes)
make docker-reset              # Stop and wipe persistent data
```

| Service  | URL                          |
|----------|------------------------------|
| Frontend | http://localhost:3000         |
| Backend  | http://localhost:8000         |
| Health   | http://localhost:8000/health  |
| Postgres | localhost:5432                |

## Native Development

```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
DATABASE_SYNC_URL="postgresql+psycopg://cahyo@localhost:5432/tradepilot_test" uvicorn app.main:app --reload

# Worker
cd worker && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m app.main

# Frontend
cd frontend && npm install
npm run dev
```

## Testing Commands

```bash
# Backend Pytest (Full P1–P7 suite)
DATABASE_SYNC_URL="postgresql+psycopg://cahyo@localhost:5432/tradepilot_test" backend/.venv/bin/python -m pytest backend/tests/ -v

# Frontend Vitest Suite
cd frontend && npx vitest run

# Frontend Typecheck & Production Build
cd frontend && npm run typecheck && NEXT_PUBLIC_API_BASE_URL="http://localhost:8000" npm run build
```
