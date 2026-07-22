#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# TradePilot AI — Storage (Evidence) Backup Script (TP-1603)
#
# Creates a timestamped tarball of the evidence storage directory.
#
# Prerequisites:
#   - tar
#   - The source directory must exist
#
# Environment variables:
#   STORAGE_DIR       Evidence storage directory (default: ./storage/evidence)
#   BACKUP_DIR        Destination directory (default: ./backups)
# ---------------------------------------------------------------------------

set -euo pipefail

# ---- Defaults ----
STORAGE_DIR="${STORAGE_DIR:-./storage/evidence}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FILENAME="tradepilot_storage_${TIMESTAMP}.tar.gz"
DEST="${BACKUP_DIR}/${FILENAME}"

# ---- Validate source ----
if [[ ! -d "${STORAGE_DIR}" ]]; then
    echo "ERROR: Storage directory does not exist: ${STORAGE_DIR}" >&2
    exit 1
fi

# ---- Ensure destination exists ----
mkdir -p "${BACKUP_DIR}"

# ---- Run backup ----
tar czf "${DEST}" -C "$(dirname "${STORAGE_DIR}")" "$(basename "${STORAGE_DIR}")"

echo "Storage backup written to ${DEST}"
