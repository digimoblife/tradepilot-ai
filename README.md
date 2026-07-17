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

## Planned Commands

The following commands are planned for later tasks:

```
make install        Install all dependencies
make dev            Start local development environment
make backend        Start the backend server
make worker         Start the background worker
make frontend       Start the frontend dev server
make test           Run all tests
make lint           Run linters
make migrate        Run database migrations
make check-structure  Validate repository structure
```
