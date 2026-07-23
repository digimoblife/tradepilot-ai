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
# both the worker's own modules and backend shared modules (e.g. app.jobs)
# are importable under the same 'app' namespace.
RUN for dir in ai context calculations database models repositories \
           schemas services storage validation auth jobs; do \
        ln -s "/app/backend/app/$dir" "/app/worker/app/$dir"; \
    done

ENV PYTHONPATH=/app/worker

CMD ["python", "-m", "app.main"]
