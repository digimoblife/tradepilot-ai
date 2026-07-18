# TradePilot AI — Backend API

FastAPI backend for the TradePilot AI trading analysis workspace.

## Package Structure

```
backend/
├── pyproject.toml
├── alembic.ini
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── application.py
│   ├── config.py
│   ├── logging.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── health.py
│   └── database/
│       ├── __init__.py
│       ├── base.py
│       ├── session.py
│       └── types.py
└── tests/
    ├── __init__.py
    ├── test_application.py
    ├── test_config.py
    ├── test_health.py
    └── database/
        ├── __init__.py
        ├── test_session.py
        ├── test_types.py
        └── test_migrations.py
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

# Run tests (non-database)
pytest -v -m "not database"

# Run all tests including database (requires Docker PostgreSQL and APP_ENV=test)
APP_ENV=test DATABASE_URL=postgresql+asyncpg://tradepilot:change_me@localhost:5432/tradepilot_test pytest -v

# Start server
uvicorn app.main:app --reload
```

## Database

### Architecture

- **Async access** (application): `asyncpg` driver via `DATABASE_URL`
- **Sync access** (Alembic): `psycopg` driver via `DATABASE_SYNC_URL`
- SQLAlchemy 2.x declarative base with metadata naming conventions
- PostgreSQL-native UUID primary keys
- Timezone-aware UTC timestamps
- Decimal types for financial values

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async application connection |
| `DATABASE_SYNC_URL` | `postgresql+psycopg://...` | Sync migration connection |
| `DB_POOL_SIZE` | `5` | Connection pool size |
| `DB_MAX_OVERFLOW` | `10` | Max pool overflow |
| `DB_POOL_TIMEOUT_SECONDS` | `30` | Pool connection timeout |
| `DB_POOL_RECYCLE_SECONDS` | `1800` | Pool connection recycle |
| `DB_ECHO` | `false` | Log all SQL statements |

### Migrations

```bash
# Create a new migration
DATABASE_SYNC_URL="..." alembic -c alembic.ini revision --autogenerate -m "description"

# Upgrade to latest
DATABASE_SYNC_URL="..." alembic -c alembic.ini upgrade head

# Downgrade one step
DATABASE_SYNC_URL="..." alembic -c alembic.ini downgrade -1

# Check current revision
DATABASE_SYNC_URL="..." alembic -c alembic.ini current

# View history
DATABASE_SYNC_URL="..." alembic -c alembic.ini history
```

### Current State

- SQLAlchemy metadata is configured with naming conventions
- Alembic is initialised with an empty foundation migration
- No domain models exist yet
- No business tables are created
- Migrations do not run automatically on startup
- `/health` remains a process-health check only (no database requirement)

### Test Database

Database tests require:
1. Docker PostgreSQL running (`make docker-up`)
2. A `tradepilot_test` database created
3. `APP_ENV=test` environment variable set

```bash
# Create test database (one time)
docker compose -f infra/docker/compose.yml exec -T postgres \
  createdb -U tradepilot tradepilot_test

# Run database tests
make db-test
```

## Deferred Capabilities

- User and Trade Session models (TP-0102+)
- Domain migrations
- Repository layer
- Service layer
- API routes for trade sessions
- AI provider integration
- Evidence upload and storage
- Background worker jobs
- Authentication
- Docker containerisation (see `infra/docker/`)
