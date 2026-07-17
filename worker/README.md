# TradePilot AI — Background Worker

Python background worker for the TradePilot AI trading analysis workspace.

## Package Structure

```
worker/
├── pyproject.toml
├── README.md
├── app/
│   ├── __init__.py
│   ├── main.py          — Process entry point and signal handling
│   ├── config.py        — Pydantic Settings configuration
│   ├── logging.py       — Logging configuration
│   └── runtime.py       — Async idle runtime loop
└── tests/
    ├── __init__.py
    ├── test_config.py
    ├── test_main.py
    └── test_runtime.py
```

## Local Setup

```bash
cd worker
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
pytest -v

# Start worker
python -m app.main
```

## Graceful Shutdown

The worker handles `SIGINT` (Ctrl+C) and `SIGTERM`. Send either signal to trigger a
clean shutdown:

```bash
python -m app.main &
WORKER_PID=$!
sleep 2
kill -TERM "$WORKER_PID"
wait "$WORKER_PID"
```

## Current Scope

This task (TP-0003) configures only the worker project skeleton:

- Python project configuration with pyproject.toml
- Typed settings via Pydantic Settings
- Async idle runtime with configurable polling interval
- Graceful shutdown via SIGINT/SIGTERM
- Logging foundation
- Development tooling (Ruff, Mypy, Pytest)

## Deferred Capabilities

The worker does **not yet** implement:

- PostgreSQL connection
- Job claiming, leasing, or lifecycle management
- AI analysis execution (Gemini, DeepSeek)
- AI output parsing or schema validation
- Evidence processing
- Canonical trade state updates
- Session lifecycle transitions
- Job retries, timeouts, or dead-letter handling
- Notifications
- HTTP/health server or Docker entry point
