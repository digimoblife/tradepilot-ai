#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# TradePilot AI — Database Restore Script (TP-1603)
#
# Restores a PostgreSQL dump created by backup_database.sh.
# Uses pg_restore with --clean --if-exists for safe restore.
#
# Prerequisites:
#   - pg_restore (PostgreSQL client tools) installed
#   - One of:
#       * PGDATABASE, PGHOST, PGPORT, PGUSER, PGPASSWORD set, OR
#       * DATABASE_URL set (postgresql://user:pass@host:port/dbname)
#   - A backup file created by backup_database.sh
#
# Usage:
#   ./scripts/restore_database.sh /path/to/backup.dump
#
# Environment variables:
#   DATABASE_URL      Full connection string (overrides individual PG* vars)
#   PGDATABASE        Database name (default: tradepilot)
#   PGHOST            Host (default: localhost)
#   PGPORT            Port (default: 5432)
#   PGUSER            User (default: tradepilot)
#   PGPASSWORD        Password (not embedded in the script)
# ---------------------------------------------------------------------------

set -euo pipefail

# ---- Validate argument ----
if [[ $# -lt 1 ]]; then
    echo "ERROR: Missing backup file argument." >&2
    echo "Usage: $0 <backup-file>" >&2
    exit 1
fi

BACKUP_FILE="$1"

if [[ ! -f "${BACKUP_FILE}" ]]; then
    echo "ERROR: Backup file not found: ${BACKUP_FILE}" >&2
    exit 1
fi

if [[ ! -s "${BACKUP_FILE}" ]]; then
    echo "ERROR: Backup file is empty: ${BACKUP_FILE}" >&2
    exit 1
fi

# ---- Build connection args ----
PG_ARGS=()

if [[ -n "${DATABASE_URL:-}" ]]; then
    PG_ARGS+=("${DATABASE_URL}")
else
    DB="${PGDATABASE:-tradepilot}"
    HOST="${PGHOST:-localhost}"
    PORT="${PGPORT:-5432}"
    USER="${PGUSER:-tradepilot}"

    PG_ARGS+=("--dbname=${DB}" "--host=${HOST}" "--port=${PORT}" "--username=${USER}")
fi

# ---- Run restore ----
pg_restore "${PG_ARGS[@]}" \
    --clean \
    --if-exists \
    --verbose \
    "${BACKUP_FILE}"

echo "Database restore completed from ${BACKUP_FILE}"
