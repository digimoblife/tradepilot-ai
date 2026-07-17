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

**Foundation stage — no services configured yet.**

- TP-0001: Repository structure initialized
- TP-0002+: Not started

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
