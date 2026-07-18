# TradePilot AI — Docker Development Environment

Local Docker environment for TradePilot AI development.

## Prerequisites

- Docker Engine 24+
- Docker Compose v2+

## Service Overview

| Service   | Image                                | Port  | Health Check               |
|-----------|--------------------------------------|-------|----------------------------|
| postgres  | postgres:17                          | 5432  | pg_isready                 |
| backend   | python:3.12-slim / FastAPI           | 8000  | GET /health                |
| worker    | python:3.12-slim / idle runtime      | —     | none (no HTTP endpoint)    |
| frontend  | node:22-slim / Next.js               | 3000  | HTTP GET /                 |

## Quick Start

```bash
# Copy environment file
cp .env.example .env

# Build images
make docker-build

# Start all services
make docker-up

# Check status
make docker-ps
```

## Service URLs

| Service  | URL                          |
|----------|------------------------------|
| Frontend | http://localhost:3000         |
| Backend  | http://localhost:8000         |
| Health   | http://localhost:8000/health  |
| Postgres | localhost:5432                |

## Commands

```bash
# Build all images
make docker-build

# Start environment (detached)
make docker-up

# Tail all logs
make docker-logs

# List running containers
make docker-ps

# Stop environment (preserves database data)
make docker-down

# Reset environment (removes all volumes + data)
make docker-reset

# Validate Compose file
make docker-config
```

## Data Persistence

- PostgreSQL data is stored in the `pgdata` named volume.
- Evidence uploads are stored in the `evidence_data` named volume.
- Both volumes survive `make docker-down` and are removed only by `make docker-reset`.

## Environment Configuration

Configuration is read from the root `.env` file. Key variables:

| Variable                       | Docker Value                                |
|-------------------------------|---------------------------------------------|
| `POSTGRES_HOST`               | `postgres` (Docker service name)            |
| `DATABASE_URL`                | `postgresql+asyncpg://tradepilot:change_me@postgres:5432/tradepilot` (async) |
| `DATABASE_SYNC_URL`           | `postgresql+psycopg://tradepilot:change_me@postgres:5432/tradepilot` (sync) |
| `NEXT_PUBLIC_API_BASE_URL`    | `http://localhost:8000`                     |
| `EVIDENCE_STORAGE_PATH`       | `/data/evidence` (inside containers)        |

## Test Database

```bash
# Create the test database (one-time setup after docker-up)
docker compose exec -T postgres createdb -U tradepilot tradepilot_test

# Run migrations against test database
DATABASE_SYNC_URL=postgresql+psycopg://tradepilot:change_me@localhost:5432/tradepilot_test \
  alembic -c ../../backend/alembic.ini upgrade head

# Run database integration tests
make db-test
```

## Current Limitations

- SQLAlchemy metadata and Alembic are configured, but no domain models or business tables exist yet.
- PostgreSQL is a running instance with no user-created tables beyond the Alembic version table.
- The worker runs an idle loop — no job queue, AI processing, or business logic.
- The frontend is a static foundation page — no API calls, session features, or trading UI.
- No reverse proxy, TLS, or production deployment configuration.
- AI API keys are optional and unused.

## Architecture Notes

- The backend health check does not require PostgreSQL (foundation scope).
- The worker has no Docker health check — it is a process-only service with no HTTP endpoint.
- The `depends_on` directives use `condition: service_started` (not `service_healthy`) to avoid false startup failures during the foundation phase.
