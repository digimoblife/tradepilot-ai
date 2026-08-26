# Backup and Restore — TradePilot AI

## Prerequisites

- PostgreSQL client tools (`pg_dump`, `pg_restore`) — version 15+
- `tar` and `gzip`
- Write permission on the backup destination directory

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | *none* | Full connection string; when set, overrides all individual `PG*` vars |
| `PGDATABASE` | `tradepilot` | Database name |
| `PGHOST` | `localhost` | Database host |
| `PGPORT` | `5432` | Database port |
| `PGUSER` | `tradepilot` | Database user |
| `PGPASSWORD` | *none* | Database password (set via environment, never embedded) |
| `BACKUP_DIR` | `./backups` | Destination directory for backup files |
| `STORAGE_DIR` | `./storage/evidence` | Evidence storage directory (storage backup only) |

## Database Backup

```bash
export PGPASSWORD="your_password"
./scripts/backup_database.sh
```

**Filename convention:** `tradepilot_db_YYYYMMDD_HHMMSS.dump`

### With `DATABASE_URL`

```bash
export DATABASE_URL="postgresql://user:password@host:5432/tradepilot"
./scripts/backup_database.sh
```

### Custom destination

```bash
export BACKUP_DIR="/var/backups/tradepilot"
./scripts/backup_database.sh
```

## Storage Backup

```bash
./scripts/backup_storage.sh
```

**Filename convention:** `tradepilot_storage_YYYYMMDD_HHMMSS.tar.gz`

### Custom source and destination

```bash
export STORAGE_DIR="/data/tradepilot/evidence"
export BACKUP_DIR="/var/backups/tradepilot"
./scripts/backup_storage.sh
```

## Database Restore

```bash
export PGPASSWORD="your_password"
./scripts/restore_database.sh ./backups/tradepilot_db_20260722_120000.dump
```

The restore script uses `pg_restore --clean --if-exists`, which drops existing objects before recreating them.

> **Caution:** Restore overwrites the target database. Ensure you are connected to the correct database server before running.

## Verification

After a backup, verify the file exists and has reasonable size:

```bash
ls -lh ./backups/tradepilot_db_*.dump
ls -lh ./backups/tradepilot_storage_*.tar.gz
```

After a restore, verify row counts or run a query against a known table:

```bash
psql -d tradepilot -c "SELECT count(*) FROM trade_sessions;"
```

## Failure Handling

All scripts exit with a non-zero status on failure:

- Missing storage directory → `exit 1`
- Missing or empty backup file (restore) → `exit 1`
- `pg_dump` or `pg_restore` failure → propagated non-zero exit
- `tar` failure → propagated non-zero exit
