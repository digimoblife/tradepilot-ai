# TradePilot AI — Backend API

FastAPI backend for the TradePilot AI trading analysis workspace.

## Package Structure

```
backend/
├── pyproject.toml
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py            — Uvicorn entry point
│   ├── application.py     — FastAPI application factory
│   ├── config.py          — Pydantic Settings configuration
│   ├── logging.py         — Logging configuration
│   └── api/
│       ├── __init__.py
│       └── health.py      — GET /health endpoint
└── tests/
    ├── __init__.py
    ├── test_application.py
    ├── test_config.py
    └── test_health.py
```

## Local Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Commands

```bash
# Lint
ruff check .

# Format check
ruff format --check .

# Type check
mypy app tests

# Run tests
pytest

# Start server
uvicorn app.main:app --reload
```

## Health Endpoint

```bash
curl http://127.0.0.1:8000/health
```

Response: `{"status":"ok","service":"tradepilot-backend"}`

## Current Scope

This task (TP-0002) configures only the backend project skeleton:

- Python project configuration with pyproject.toml
- FastAPI application factory
- Typed settings via Pydantic Settings
- GET /health endpoint
- Logging foundation
- Development tooling (Ruff, Mypy, Pytest)

## Deferred Capabilities

The following are **not yet implemented** and will be added in later tasks:

- PostgreSQL integration
- Database models and migrations
- API router for trade-session endpoints
- Canonical trade_state persistence
- Session lifecycle transitions
- Evidence upload and storage
- AI provider integration (Gemini, DeepSeek)
- JSON Schema validation pipeline
- Background worker execution
- Authentication and authorization
- Docker configuration
- Production deployment
