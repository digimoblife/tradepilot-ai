FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install backend library (required for job imports)
COPY backend/pyproject.toml backend/
RUN pip install --no-cache-dir -e backend

# Install worker
COPY worker/pyproject.toml worker/
RUN pip install --no-cache-dir -e worker

# Copy source code
COPY backend/app backend/app/
COPY worker/app worker/app/
COPY prompts prompts/

# Symlink backend shared modules into the worker's app package so that
# both the worker's own modules and backend shared modules
# are importable under the same 'app' namespace.
RUN for dir in calculations database models repositories \
           services storage validation auth lifecycle trade_workspace; do \
        ln -s "/app/backend/app/$dir" "/app/worker/app/$dir"; \
    done
RUN ln -s /app/backend/app/json_safe.py /app/worker/app/json_safe.py

RUN PYTHONPATH=/app/worker python -c "\
import app.main; \
import app.json_safe; \
import app.lifecycle; \
import app.runtime; \
import app.consumers.rebuild_analysis_requests; \
import app.trade_workspace; \
import app.trade_workspace.workers.analysis_processor; \
import app.trade_workspace.ai.context_builder; \
import app.trade_workspace.ai.gemini_adapter; \
import app.trade_workspace.services.analysis_request_queue; \
"

ENV PYTHONPATH=/app/worker

CMD ["python", "-m", "app.main"]
