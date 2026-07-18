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
│   ├── models/
│   │   ├── enums.py
│   │   ├── user.py
│   │   ├── trade_session.py
│   │   ├── trade_state.py
│   │   ├── trade_action.py
│   │   ├── evidence.py
│   │   ├── analysis_job.py
│   │   ├── analysis.py
│   │   ├── provider_request.py
│   │   ├── provider_response.py
│   │   └── validation_attempt.py
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
    ├── models/
    ├── database/
    └── fixtures/
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
APP_ENV=test TEST_DATABASE_URL=postgresql+asyncpg://tradepilot:change_me@localhost:5432/tradepilot_test pytest -v

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
- PostgreSQL native enums for controlled domain values
- `ON DELETE RESTRICT` for history-preserving foreign keys

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

# Check for drift
DATABASE_SYNC_URL="..." alembic -c alembic.ini check
```

### Current State

**Domain models implemented:**

| Model | Table | Description |
|-------|-------|-------------|
| `User` | `users` | Application user with email, password hash, account status |
| `TradeSession` | `trade_sessions` | One trade lifecycle per ticker, owned by a user |
| `TradeState` | `trade_states` | Canonical position state (entry, quantity, stop, target, P&L) |
| `TradeAction` | `trade_actions` | Immutable user-confirmed state-changing actions |
| `Evidence` | `evidence` | Uploaded evidence metadata (screenshots, notes) |
| `AnalysisJob` | `analysis_jobs` | Asynchronous AI analysis job with retry and lease support |
| `ProviderRequest` | `provider_requests` | What was sent to an AI provider (prompt, schema, payload) |
| `ProviderResponse` | `provider_responses` | Raw provider output including failures and metadata |
| `ValidationAttempt` | `validation_attempts` | Validation audit (parsed vs validated payload, issues) |
| `Analysis` | `analyses` | Accepted analysis result with immutable history and superseding |

### Analysis Job

`analysis_jobs` represents a requested asynchronous AI analysis. It stores:
- Session ownership and analysis type
- Job status lifecycle: `CREATED → QUEUED → PROCESSING → RETRYING → COMPLETED | FAILED | CANCELLED`
- Retry metadata: attempt count, max attempts, next availability time
- Lease fields for future worker claiming: `lease_owner`, `lease_acquired_at`, `lease_expires_at`
- Stable error metadata: `last_error_code`, `last_error_message`

### Provider Request & Response

`provider_requests` and `provider_responses` form an auditable attempt trail:
- Each request preserves prompt name/version and schema name/version (all mandatory)
- Request payload (JSONB) stores what was sent to the provider
- Response stores raw text output, which is **never automatically an accepted analysis**
- Failed responses remain stored for audit
- Latency, token counts, and error metadata are persisted

### Validation Attempt

`validation_attempts` records each validation stage:
- **Stages:** `PARSE`, `JSON_SCHEMA`, `DOMAIN`, `STATE_CONSISTENCY`, `LIFECYCLE`, `NARRATIVE`
- `parsed_payload` stores the raw parsed JSON (may exist even for failed validation)
- `validated_payload` stores the successfully validated payload (only for successful validation)
- `issues` JSONB preserves normalized validation issues
- `valid` boolean is explicit and not inferred

### Context Summary

`context_summaries` stores compact derived longitudinal memory for a Trade Session:
- Versioned rows (version >= 1, unique per session)
- `source_cutoff` timestamp identifies latest source material
- `payload` JSONB for structured compressed history
- `quality` enum: `HIGH`, `MEDIUM`, `LOW`, `INCOMPLETE`, `DEGRADED`
- `is_stale` boolean flag (future stale-detection service)
- Efficient latest-summary selection via `(session_id, context_version DESC)` index
- Multiple versions retained; historical versions remain immutable
- Context Summary is derived data, NOT canonical Trade State

### Session Event

`session_events` stores immutable timeline history:
- Controlled `event_type` enum with 14 values covering the full session lifecycle
- `occurred_at` timestamp (timezone-aware) for chronological ordering
- Optional FK to `trade_actions.related_action_id`
- Optional FK to `analyses.related_analysis_id`
- Optional `price` (Decimal, `NUMERIC(20,6)`) and `quantity` (Decimal, `NUMERIC(24,6)`)
- Negative quantity rejected by check constraint
- `compact_summary` text for concise audit descriptions
- Chronological retrieval via `(session_id, occurred_at, id)` index with deterministic tie-breaking
- Events do not execute lifecycle changes

### Analysis

`analyses` represents the accepted analysis result:
- **Acceptance Status:** `PENDING`, `ACCEPTED`, `REJECTED`, `SUPERSEDED`
- Schema name and version are mandatory fields
- Prompt version is mandatory
- Payload (JSONB) is the **accepted** content, distinct from raw provider output
- `supersedes_analysis_id` self-referential FK supports immutable corrections
- Self-superseding is prevented by a check constraint
- Prior accepted analyses remain stored when superseded

### Trade Action Analysis FK

`trade_actions.related_analysis_id` has a deferred foreign key to `analyses.id`, added in the TP-0106 migration. This connects user-confirmed actions to the analysis that proposed them.

### Enum Types

- `account_status_enum`, `session_status_enum`, `market_enum`, `currency_enum`
- `position_status_enum`, `thesis_status_enum`
- `trade_action_type_enum`
- `evidence_type_enum`, `evidence_status_enum`, `extraction_status_enum`
- `analysis_type_enum`, `analysis_job_status_enum`, `acceptance_status_enum`
- `provider_enum`, `provider_response_status_enum`
- `validation_stage_enum`
- `context_quality_enum`, `session_event_type_enum`

### Test Database

Database tests require:
1. Docker PostgreSQL running (`make docker-up`)
2. A `tradepilot_test` database created
3. `APP_ENV=test` environment variable set

```bash
# Create test database (one time)
docker compose -f infra/docker/compose.yml exec -T postgres \
  createdb -U tradepilot tradepilot_test

# Run all tests (from project root via Docker)
make db-test
```

## Deferred Capabilities

- **Job claiming** (PostgreSQL queue lease acquisition)
- **Worker polling** and heartbeat
- **AI provider adapters** (Gemini, DeepSeek)
- **Prompt building** from the prompt registry
- **Provider calls** to AI models
- **JSON parsing** of raw provider output
- **Validation execution** (schema, domain, state consistency)
- **Repair and fallback** logic
- **Analysis APIs** (job creation, result retrieval)
- **Repositories** (typed persistence layer)
- **Service transactions** (orchestration layer)
- **Context Summary generation** (material-history selection)
- **Context Summary rebuilding** (stale detection)
- **Session Event publishing**
- **Timeline and context APIs**
- **Authentication and authorisation**
- **Evidence upload and storage**
- **API route handlers** for trade sessions, actions, evidence
- **Docker containerisation** (see `infra/docker/`)
- `/health` remains a process-health check only (no database requirement)
