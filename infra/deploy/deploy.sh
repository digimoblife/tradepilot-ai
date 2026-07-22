#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# TradePilot AI — Deployment Script (TP-1703)
#
# Deploys a specific Git revision (default: configured production branch) to
# the TradePilot Compose project on the VPS.  All Compose commands are scoped
# to project name "tradepilot-ai" so that other VPS projects are never
# touched.
#
# Usage:
#   ./infra/deploy/deploy.sh                        # deploy production branch
#   TRADEPILOT_REVISION=<git-ref> ./deploy.sh       # deploy specific ref
#
# Environment variables (all optional with defaults):
#   TRADEPILOT_DEPLOY_DIR    /opt/tradepilot-ai/repository
#   TRADEPILOT_COMPOSE_PROJECT  tradepilot-ai
#   TRADEPILOT_COMPOSE_FILE     docker-compose.production.yml
#   TRADEPILOT_ENV_FILE         /opt/tradepilot-ai/env/production.env
#   TRADEPILOT_STATE_DIR        /opt/tradepilot-ai/deployment-state
#   TRADEPILOT_GATEWAY_PORT     8181
#   TRADEPILOT_REVISION         (default: origin/main)
#   TRADEPILOT_RETRY_SECONDS    5
#   TRADEPILOT_RETRY_ATTEMPTS   12
# ---------------------------------------------------------------------------

set -euo pipefail

# ---- Configuration with defaults ----
DEPLOY_DIR="${TRADEPILOT_DEPLOY_DIR:-/opt/tradepilot-ai/repository}"
COMPOSE_PROJECT="${TRADEPILOT_COMPOSE_PROJECT:-tradepilot-ai}"
COMPOSE_FILE="${TRADEPILOT_COMPOSE_FILE:-docker-compose.production.yml}"
ENV_FILE="${TRADEPILOT_ENV_FILE:-/opt/tradepilot-ai/env/production.env}"
STATE_DIR="${TRADEPILOT_STATE_DIR:-/opt/tradepilot-ai/deployment-state}"
GATEWAY_PORT="${TRADEPILOT_GATEWAY_PORT:-8181}"
REVISION="${TRADEPILOT_REVISION:-origin/main}"
RETRY_SECONDS="${TRADEPILOT_RETRY_SECONDS:-5}"
RETRY_ATTEMPTS="${TRADEPILOT_RETRY_ATTEMPTS:-12}"

COMPOSE_CMD="docker compose -p ${COMPOSE_PROJECT} --env-file ${ENV_FILE} -f ${COMPOSE_FILE}"

# ---- Helpers ----
_fail() { echo "ERROR: $*" >&2; exit 1; }
_info() { echo "==> $*"; }

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_info "Validating deployment environment"

[[ -d "${DEPLOY_DIR}" ]] || _fail "Deployment directory does not exist: ${DEPLOY_DIR}"
cd "${DEPLOY_DIR}"

git rev-parse --git-dir >/dev/null 2>&1 || _fail "Not a Git repository: ${DEPLOY_DIR}"

[[ -f "${ENV_FILE}" ]] || _fail "Environment file not found: ${ENV_FILE}"
[[ -f "${COMPOSE_FILE}" ]] || _fail "Compose file not found: ${DEPLOY_DIR}/${COMPOSE_FILE}"

command -v docker >/dev/null 2>&1 || _fail "docker not found"
command -v docker compose >/dev/null 2>&1 || _fail "docker compose not found"

# Validate Compose file
docker compose -p "${COMPOSE_PROJECT}" --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" config --quiet \
    || _fail "Compose file validation failed"

# Validate required env vars in the env file
for var in POSTGRES_PASSWORD; do
    if grep -q "^${var}=" "${ENV_FILE}" 2>/dev/null; then
        val=$(grep "^${var}=" "${ENV_FILE}" | cut -d= -f2-)
        [[ -n "${val}" ]] || _fail "Environment variable ${var} is empty in ${ENV_FILE}"
    else
        _fail "Required environment variable ${var} not found in ${ENV_FILE}"
    fi
done

# Port-safety check: verify gateway port does not conflict with an unrelated process.
# Allow the port if it is free, or if it is already owned by the current Tradepilot
# Compose project (redeployment).
_info "Checking gateway port ${GATEWAY_PORT}"
PORT_IN_USE=false
if command -v ss >/dev/null 2>&1; then
    if ss -tlnp "sport = :${GATEWAY_PORT}" 2>/dev/null | grep -q LISTEN; then
        PORT_IN_USE=true
    fi
elif command -v lsof >/dev/null 2>&1; then
    if lsof -i :"${GATEWAY_PORT}" >/dev/null 2>&1; then
        PORT_IN_USE=true
    fi
fi

if "${PORT_IN_USE}"; then
    # Check if the port is owned by our own Compose project (allowed)
    OUR_PROJECT="tradepilot-ai"
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "${OUR_PROJECT}"; then
        _info "Gateway port ${GATEWAY_PORT} in use by current deployment (allowed)"
    else
        _fail "Gateway port ${GATEWAY_PORT} is in use by another process. Refusing to deploy."
    fi
else
    _info "Gateway port ${GATEWAY_PORT} is free"
fi

# ---------------------------------------------------------------------------
# Record current revision
# ---------------------------------------------------------------------------

mkdir -p "${STATE_DIR}"
PREVIOUS_REVISION=$(git rev-parse HEAD 2>/dev/null || echo "none")
echo "${PREVIOUS_REVISION}" > "${STATE_DIR}/previous_revision"
_info "Recorded previous revision: ${PREVIOUS_REVISION}"

# ---------------------------------------------------------------------------
# Fetch and checkout requested revision
# ---------------------------------------------------------------------------

_info "Fetching latest commits"
git fetch origin 2>&1 || _fail "git fetch failed"

_info "Checking out revision: ${REVISION}"
git checkout "${REVISION}" 2>&1 || _fail "Failed to checkout revision ${REVISION}"
CURRENT_REVISION=$(git rev-parse HEAD)
echo "${CURRENT_REVISION}" > "${STATE_DIR}/current_revision"
_info "Current revision: ${CURRENT_REVISION}"

# ---------------------------------------------------------------------------
# Build images
# ---------------------------------------------------------------------------

_info "Building production images"
${COMPOSE_CMD} build 2>&1 || _fail "Image build failed"

# ---------------------------------------------------------------------------
# Run database migrations
# ---------------------------------------------------------------------------

_info "Running database migrations"
if [[ -d "${DEPLOY_DIR}/backend" ]]; then
    cd "${DEPLOY_DIR}/backend"
    pip install alembic 2>&1 >/dev/null || true
    alembic upgrade head 2>&1 || _fail "Database migration failed"
    cd "${DEPLOY_DIR}"
else
    _info "No backend directory found; skipping database migrations"
fi

# ---------------------------------------------------------------------------
# Start / recreate services
# ---------------------------------------------------------------------------

_info "Starting TradePilot services"
${COMPOSE_CMD} up -d 2>&1 || _fail "docker compose up failed"

# ---------------------------------------------------------------------------
# Verify runtime state
# ---------------------------------------------------------------------------

_info "Verifying container status"
for svc in postgres backend worker frontend gateway; do
    status=$(${COMPOSE_CMD} ps --format json "${svc}" 2>/dev/null | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
    print(d.get('State','unknown'))
except: print('unknown')
" 2>/dev/null || echo "unknown")
    echo "  ${svc}: ${status}"
    if [[ "${svc}" != "worker" && "${status}" != "running" ]]; then
        _fail "Service ${svc} is not running (state: ${status})"
    fi
done

# ---------------------------------------------------------------------------
# Health checks through local gateway
# ---------------------------------------------------------------------------

_info "Running health checks via http://127.0.0.1:${GATEWAY_PORT}"
HEALTH_URL="http://127.0.0.1:${GATEWAY_PORT}"
HEALTHY=false

for attempt in $(seq 1 "${RETRY_ATTEMPTS}"); do
    echo "  Attempt ${attempt}/${RETRY_ATTEMPTS}..."

    LIVES=$(curl -sf "${HEALTH_URL}/health" 2>/dev/null || echo "FAIL")
    READY=$(curl -sf "${HEALTH_URL}/health/ready" 2>/dev/null || echo "FAIL")

    if [[ "${LIVES}" != "FAIL" && "${READY}" != "FAIL" ]]; then
        HEALTHY=true
        echo "  /health:    ${LIVES}"
        echo "  /ready:     ${READY}"
        break
    fi

    if [[ "${attempt}" -lt "${RETRY_ATTEMPTS}" ]]; then
        sleep "${RETRY_SECONDS}"
    fi
done

# ---------------------------------------------------------------------------
# Finalise
# ---------------------------------------------------------------------------

if "${HEALTHY}"; then
    _info "Deployment of revision ${CURRENT_REVISION} successful"
else
    echo ""
    echo "WARNING: Deployment completed but health checks did not pass."
    echo "  Previous revision: ${PREVIOUS_REVISION}"
    echo "  Current revision:  ${CURRENT_REVISION}"
    echo "  Run rollback to restore the previous revision."
    exit 1
fi
