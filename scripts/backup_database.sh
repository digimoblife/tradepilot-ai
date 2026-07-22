#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# TradePilot AI — Database Backup Script (TP-1603)
#
# Creates a timestamped PostgreSQL dump using pg_dump.
#
# Prerequisites:
#   - pg_dump (PostgreSQL client tools) installed
#   - One of:
#       * PGDATABASE, PGHOST, PGPORT, PGUSER, PGPASSWORD set, OR
#       * DATABASE_URL set (postgresql://user:pass@host:port/dbname)
#
# Environment variables:
#   DATABASE_URL      Full connection string (overrides individual PG* vars)
#   PGDATABASE        Database name (default: tradepilot)
#   PGHOST            Host (default: localhost)
#   PGPORT            Port (default: 5432)
#   PGUSER            User (default: tradepilot)
#   PGPASSWORD        Password (not embedded in the script)
#   BACKUP_DIR        Destination directory (default: ./backups)
# ---------------------------------------------------------------------------

set -euo pipefail

# ---- Defaults ----
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="tradepilot_db_${TIMESTAMP}.dump"
DEST="${BACKUP_DIR}/${FILENAME}"

# ---- Ensure destination exists ----
mkdir -p "${BACKUP_DIR}"

# ---- Build connection args ----
PG_ARGS=()

if [[ -n "${DATABASE_URL:-}" ]]; then
    # Use DATABASE_URL directly
    PG_ARGS+=("${DATABASE_URL}")
else
    # Build from individual PG* vars
    DB="${PGDATABASE:-tradepilot}"
    HOST="${PGHOST:-localhost}"
    PORT="${PGPORT:-5432}"
    USER="${PGUSER:-tradepilot}"

    PG_ARGS+=("--dbname=${DB}" "--host=${HOST}" "--port=${PORT}" "--username=${USER}")
fi

# ---- Run backup ----
pg_dump "${PG_ARGS[@]}" \
    --format=custom \
    --verbose \
    --file="${DEST}"

echo "Database backup written to ${DEST}"
