#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# TradePilot AI — Rollback Script (TP-1703)
#
# Reads the previous Git revision from deployment state, checks it out,
# rebuilds images, and restarts the TradePilot Compose project.
#
# Never removes PostgreSQL or evidence named volumes.
# Never targets another Compose project.
#
# Usage:
#   ./infra/deploy/rollback.sh
#
# Environment variables (same defaults as deploy.sh):
#   TRADEPILOT_DEPLOY_DIR    /opt/tradepilot-ai/repository
#   TRADEPILOT_COMPOSE_PROJECT  tradepilot-ai
#   TRADEPILOT_COMPOSE_FILE     docker-compose.production.yml
#   TRADEPILOT_ENV_FILE         /opt/tradepilot-ai/env/production.env
#   TRADEPILOT_STATE_DIR        /opt/tradepilot-ai/deployment-state
#   TRADEPILOT_GATEWAY_PORT     8181
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
RETRY_SECONDS="${TRADEPILOT_RETRY_SECONDS:-5}"
RETRY_ATTEMPTS="${TRADEPILOT_RETRY_ATTEMPTS:-12}"

COMPOSE_CMD="docker compose -p ${COMPOSE_PROJECT} --env-file ${ENV_FILE} -f ${COMPOSE_FILE}"

# ---- Helpers ----
_fail() { echo "ERROR: $*" >&2; exit 1; }
_info() { echo "==> $*"; }

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_info "Validating rollback environment"

[[ -d "${DEPLOY_DIR}" ]] || _fail "Deployment directory does not exist: ${DEPLOY_DIR}"
cd "${DEPLOY_DIR}"

git rev-parse --git-dir >/dev/null 2>&1 || _fail "Not a Git repository: ${DEPLOY_DIR}"

[[ -f "${ENV_FILE}" ]] || _fail "Environment file not found: ${ENV_FILE}"
[[ -f "${COMPOSE_FILE}" ]] || _fail "Compose file not found: ${DEPLOY_DIR}/${COMPOSE_FILE}"

command -v docker >/dev/null 2>&1 || _fail "docker not found"
command -v docker compose >/dev/null 2>&1 || _fail "docker compose not found"

# ---------------------------------------------------------------------------
# Read previous revision
# ---------------------------------------------------------------------------

_info "Reading previous revision from state directory"

if [[ ! -f "${STATE_DIR}/previous_revision" ]]; then
    _fail "No previous revision found at ${STATE_DIR}/previous_revision"
fi

PREVIOUS_REVISION=$(cat "${STATE_DIR}/previous_revision")

if [[ -z "${PREVIOUS_REVISION}" || "${PREVIOUS_REVISION}" == "none" ]]; then
    _fail "Previous revision is empty or 'none'. Cannot rollback."
fi

_info "Previous revision to restore: ${PREVIOUS_REVISION}"

# ---------------------------------------------------------------------------
# Checkout previous revision
# ---------------------------------------------------------------------------

_info "Fetching latest commits"
git fetch origin 2>&1 || _fail "git fetch failed"

_info "Checking out revision: ${PREVIOUS_REVISION}"
git checkout "${PREVIOUS_REVISION}" 2>&1 || _fail "Failed to checkout ${PREVIOUS_REVISION}"

# Update state: swap current and previous
CURRENT_REVISION=$(git rev-parse HEAD)
echo "${CURRENT_REVISION}" > "${STATE_DIR}/current_revision"
echo "none" > "${STATE_DIR}/previous_revision"  # clear previous after rollback

# ---------------------------------------------------------------------------
# Build images
# ---------------------------------------------------------------------------

_info "Building production images for rollback revision"
${COMPOSE_CMD} build 2>&1 || _fail "Image build failed during rollback"

# ---------------------------------------------------------------------------
# Run database migrations (forward-only; if schema changed, we run migrations
# on the rolled-back code.  Database downgrade is not supported — the database
# must remain backward-compatible).
# ---------------------------------------------------------------------------

_info "Running database migrations for rollback revision"
if [[ -d "${DEPLOY_DIR}/backend" ]]; then
    cd "${DEPLOY_DIR}/backend"
    pip install alembic 2>&1 >/dev/null || true
    alembic upgrade head 2>&1 || _fail "Database migration failed during rollback"
    cd "${DEPLOY_DIR}"
else
    _info "No backend directory found; skipping database migrations"
fi

# ---------------------------------------------------------------------------
# Restart services
# ---------------------------------------------------------------------------

_info "Restarting TradePilot services"
${COMPOSE_CMD} up -d 2>&1 || _fail "docker compose up failed during rollback"

# ---------------------------------------------------------------------------
# Health checks
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
    _info "Rollback to revision ${PREVIOUS_REVISION} successful"
else
    echo ""
    echo "WARNING: Rollback completed but health checks did not pass."
    echo "  Revision restored: ${CURRENT_REVISION}"
    echo "  Manual intervention required."
    exit 1
fi
