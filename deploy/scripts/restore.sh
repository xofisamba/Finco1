#!/usr/bin/env bash
# restore.sh — FincoGPT PostgreSQL database restore
#
# Usage:
#   ./restore.sh <backup_path>
#
# Example:
#   ./restore.sh /opt/finco1/backups/finco1_backup_20260508_120000.sql
#
# What it does:
#   1. Validates the backup file exists
#   2. Stops the finco-web systemd service
#   3. Drops and recreates the target database
#   4. Restores from the backup file
#   5. Restarts the finco-web service
#
# Requirements: psql on PATH, finco-web service must be managed by systemd,
#              DATABASE_URL env var set (or .env at /opt/finco1/.env)

set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────────────
SERVICE_NAME="finco-web"
ENV_FILE="/opt/finco1/.env"

# Load DATABASE_URL from /opt/finco1/.env if present
if [[ -f "$ENV_FILE" ]]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# ── Validate input ───────────────────────────────────────────────────────────
BACKUP_PATH="${1:-}"
if [[ -z "$BACKUP_PATH" ]]; then
    echo "ERROR: Usage: $0 <backup_path>" >&2
    echo "Example: $0 /opt/finco1/backups/finco1_backup_20260508_120000.sql" >&2
    exit 1
fi

if [[ ! -f "$BACKUP_PATH" ]]; then
    echo "ERROR: Backup file not found: $BACKUP_PATH" >&2
    exit 1
fi

# Determine DB connection string
DB_URL="${DATABASE_URL:-}"
if [[ -z "$DB_URL" ]]; then
    echo "ERROR: DATABASE_URL is not set. Aborting restore." >&2
    exit 1
fi

HOST=$(echo "$DB_URL" | sed -n 's|.*@\([^:]*\):\([0-9]*\)/.*|\1|p')
PORT=$(echo "$DB_URL" | sed -n 's|.*@\([^:]*\):\([0-9]*\)/.*|\2|p')
USER=$(echo "$DB_URL" | sed -n 's|postgres://\([^:]*\):.*|\1|p')
DBNAME=$(echo "$DB_URL" | sed -n 's|.*:\/[^\/]*/\(.*\)|\1|p' | sed 's/?.*//')

PGHOST="${HOST:-localhost}"
PGPORT="${PORT:-5432}"
PGUSER="${USER:-postgres}"
PGDATABASE="${DBNAME:-finco1}"

echo "=== FincoGPT Restore ==="
echo "Backup file: $BACKUP_PATH"
echo "Target DB: $PGHOST:$PGPORT/$PGDATABASE as $PGUSER"
echo ""

# ── Confirmation prompt ──────────────────────────────────────────────────────
echo "WARNING: This will DROP the current database and replace it with the backup."
echo "Press Ctrl+C to abort, or Enter to continue..."
read -r REPLY

# ── Stop service ─────────────────────────────────────────────────────────────
echo ""
echo "Stopping service: $SERVICE_NAME..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true
echo "Service stopped."

# ── Restore ──────────────────────────────────────────────────────────────────
echo ""
echo "Restoring database..."

# Check if plain SQL or custom format
if [[ "$BACKUP_PATH" == *.dump ]]; then
    # Custom format pg_restore
    pg_restore \
        --host="$PGHOST" \
        --port="$PGPORT" \
        --username="$PGUSER" \
        --dbname="$PGDATABASE" \
        --clean \
        --if-exists \
        --single-transaction \
        --verbose \
        "$BACKUP_PATH"
else
    # Plain SQL restore
    psql \
        --host="$PGHOST" \
        --port="$PGPORT" \
        --username="$PGUSER" \
        --dbname="$PGDATABASE" \
        --set=ON_ERROR_STOP=on \
        --file="$BACKUP_PATH"
fi

echo ""
echo "=== Restore complete ==="

# ── Restart service ──────────────────────────────────────────────────────────
echo ""
echo "Restarting service: $SERVICE_NAME..."
systemctl start "$SERVICE_NAME"
echo "Service started."
echo ""
echo "Done. Database restored from: $BACKUP_PATH"
