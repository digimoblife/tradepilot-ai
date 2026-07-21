# TradePilot AI

**AI Trading Analysis Workspace**

TradePilot AI is a web-based AI trading analysis workspace designed to follow one stock position from initial analysis until the position is closed. Each position is managed through a dedicated Trade Session containing the complete history of one trading idea.

**One Trade, One Story.**

## Approved Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js, TypeScript |
| Backend | FastAPI, Python |
| Worker | Python background worker |
| Database | PostgreSQL |
| Queue (MVP) | PostgreSQL-backed job queue |
| Primary AI | Gemini |
| Fallback AI | DeepSeek |
| Deployment | Single VPS |
| Evidence Storage (MVP) | VPS filesystem |

## Repository Map

```
tradepilot-ai/
├── backend/                    — FastAPI backend (reserved)
├── worker/                     — Python background worker (reserved)
├── frontend/                   — Next.js frontend (reserved)
├── schemas/
│   └── production/v1/          — Production JSON Schema package
├── infra/
│   ├── docker/                 — Docker / Compose configuration (reserved)
│   └── deployment/             — VPS deployment configuration (reserved)
├── scripts/                    — Development and maintenance scripts (reserved)
├── tests/
│   ├── integration/            — Cross-service integration tests (reserved)
│   └── fixtures/               — Shared test fixtures (reserved)
├── docs/                       — Engineering documentation
├── storage/
│   └── evidence/               — Local development evidence files
├── .editorconfig
├── .env.example
├── .gitignore
└── Makefile
```

## Implementation Status

**Frontend actively developed — 505 tests passing across 17 test files.**

### Frontend (Next.js / TypeScript)

| Task | Status | Tests |
|------|--------|-------|
| TP-1101 Core API client & typed errors | Complete | 21 |
| TP-1102 Auth UI | Complete | — |
| TP-1103 New Trade Session Page | Complete | 27 |
| TP-1104 Trade Session Page Shell | Complete | 27 |
| TP-1105 Evidence Upload UI | Complete | 16 |
| TP-1201 Golden test fixtures (5 types, schema-valid) | Complete | 67 + 9 |
| TP-1202 Initial Analysis View (41 tests) | Complete | 41 |
| TP-1203 Watching Update View (37 tests) | Complete | 37 |
| TP-1204 Open Position Update View (43 tests) | Complete | 43 |
| TP-1205 Partial Exit Review View (48 tests) | Complete | 48 |
| TP-1206 Closing Analysis View (45 tests) | Complete | 45 |
| TP-1207 Analysis History & Comparison (38 tests) | Complete | 38 |
| TP-1301 Position Open Confirmation Modal (22 tests) | Complete | 22 |
| TP-1302 Stop & Target Modals (30 tests) | Complete | 30 |
| TP-1303 Partial Exit Modal (15 tests) | Complete | 15 |

### Backend / Worker / Schema

| Task | Status |
|------|--------|
| Production JSON Schema package (11 schemas) | Complete |
| Schema registry & validation service | Reserved |
| FastAPI backend | Reserved |
| Python background worker | Reserved |
| PostgreSQL-backed job queue | Reserved |

### Stacks Completed

- Frontend: 505 tests, 0 errors (TypeScript, ESLint)
- 5 golden fixtures validated against all 11 production schemas
- 5 analysis views: Initial Analysis, Watching Update, Open Position Update, Partial Exit Review, Closing Analysis
- Analysis History with per-type payload viewers, period badges, material-change rendering
- 6 interactive modals: Open Position, Confirm Stop, Change Stop, Confirm Target, Change Target, Partial Exit

## Language

- **Dashboard output:** Indonesian (Bahasa Indonesia)
- **Engineering documents, code, schemas, prompts, field names, and implementation instructions:** English

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
uvicorn app.main:app --reload

# Worker
cd worker && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m app.main

# Frontend
cd frontend && npm install
npm run dev
```

## Makefile Commands

```bash
make check-structure   Validate repository structure
make docker-build      Build container images
make docker-up         Start Docker environment
make docker-down       Stop Docker environment
make docker-logs       Tail Docker logs
make docker-ps         List Docker containers
make docker-reset      Reset Docker environment (removes volumes)
```
