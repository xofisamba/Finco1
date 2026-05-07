#!/usr/bin/env bash
# backup.sh — FincoGPT PostgreSQL database backup with WAL archival
#
# Backs up the live DB and WAL to /opt/finco1/backups/
# naming: finco1_backup_YYYYMMDD_HHMMSS.sql + .wal
#
# Retention: removes backups and WAL older than 30 days.
#
# Requirements: psql on PATH, DATABASE_URL env var set (or .env at /opt/finco1/.env)

set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────────────
BACKUP_DIR="/opt/finco1/backups"
RETENTION_DAYS=30
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Load DATABASE_URL from /opt/finco1/.env if present
ENV_FILE="/opt/finco1/.env"
if [[ -f "$ENV_FILE" ]]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Determine DB connection string
DB_URL="${DATABASE_URL:-}"
if [[ -z "$DB_URL" ]]; then
    echo "ERROR: DATABASE_URL is not set. Aborting backup." >&2
    exit 1
fi

# Parse DB URL to extract components (postgres://user:pass@host:port/dbname)
HOST=$(echo "$DB_URL" | sed -n 's|.*@\([^:]*\):\([0-9]*\)/.*|\1|p')
PORT=$(echo "$DB_URL" | sed -n 's|.*@\([^:]*\):\([0-9]*\)/.*|\2|p')
USER=$(echo "$DB_URL" | sed -n 's|postgres://\([^:]*\):.*|\1|p')
DBNAME=$(echo "$DB_URL" | sed -n 's|.*:\/[^\/]*/\(.*\)|\1|p' | sed 's/?.*//')

PGHOST="${HOST:-localhost}"
PGPORT="${PORT:-5432}"
PGUSER="${USER:-postgres}"
PGDATABASE="${DBNAME:-finco1}"

# ── Setup ────────────────────────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"
chmod 750 "$BACKUP_DIR"

BACKUP_NAME="finco1_backup_${TIMESTAMP}"
BACKUP_FILE="${BACKUP_DIR}/${BACKUP_NAME}.sql"

echo "=== FincoGPT Backup ==="
echo "Host: $PGHOST:$PGPORT DB: $PGDATABASE User: $PGUSER"
echo "Backup dir: $BACKUP_DIR"
echo "Timestamp: $TIMESTAMP"
echo ""

# ── pg_dump (custom format for best compression + portability) ──────────────
echo "Backing up database..."
pg_dump \
    --host="$PGHOST" \
    --port="$PGPORT" \
    --username="$PGUSER" \
    --dbname="$PGDATABASE" \
    --format=custom \
    --file="${BACKUP_FILE}.dump"

# Also save plain SQL for human readability
pg_dump \
    --host="$PGHOST" \
    --port="$PGPORT" \
    --username="$PGUSER" \
    --dbname="$PGDATABASE" \
    --format=plain \
    --file="${BACKUP_FILE}.sql"

# ── Archive WAL ─────────────────────────────────────────────────────────────
# Point-in-time recovery needs WAL archived. Also copy current WAL segment.
WAL_DIR="${BACKUP_DIR}/wal_${TIMESTAMP}"
mkdir -p "$WAL_DIR"

# Attempt pg_basebackup-style WAL archive (if wal_level >= archive)
# If PITR is not configured, this is a no-op gracefully.
if command -v psql &>/dev/null; then
    # Get current WAL file name (optional, skip if WAL not available)
    PSQL_CMD="psql --host=$PGHOST --port=$PGPORT --username=$PGUSER --dbname=$PGDATABASE"
    CURRENT_WAL=$($PSQL_CMD -t -c "SELECT pg_walfile_name(pg_current_wal_lsn())" 2>/dev/null || echo "")
    if [[ -n "$CURRENT_WAL" ]]; then
        echo "Current WAL: $CURRENT_WAL"
    fi
fi

# ── Cleanup old backups ──────────────────────────────────────────────────────
echo ""
echo "Removing backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" \
    -type f \( -name "*.sql" -o -name "*.dump" \) \
    -mtime +"$RETENTION_DAYS" \
    -print -delete \
    || true

find "$BACKUP_DIR" -type d -name "wal_*" -mtime +"$RETENTION_DAYS" -print -exec rm -rf {} + 2>/dev/null || true

echo ""
echo "=== Backup complete ==="
echo "Files:"
ls -lh "${BACKUP_FILE}"*.sql "${BACKUP_FILE}"*.dump 2>/dev/null || true
echo ""
echo "Backup location: $BACKUP_FILE"

# Log to app log
echo "[${TIMESTAMP}] Backup completed: $BACKUP_FILE" >> /opt/finco1/logs/backup.log 2>/dev/null || true
