#!/usr/bin/env bash
# restore.sh — FincoGPT SQLite database restore
#
# Usage:
#   ./restore.sh <backup_path>
#
# Example:
#   ./restore.sh /opt/finco1/backups/finco_runs_20260508_120000.db.xz
#
# What it does:
#   1. Validates the backup file exists and is readable
#   2. Stops the finco-web systemd service
#   3. Backs up the current (potentially corrupted) DB
#   4. Decompresses and restores the backup to FINCO_DB_PATH
#   5. Fixes ownership/permissions
#   6. Restarts finco-web
#   7. Runs healthcheck
#
# Requirements: finco-web service managed by systemd, xz for decompression

set -euo pipefail

SERVICE_NAME="finco-web"
BACKUP_FILE="$1"

# Load FINCO_DB_PATH from .env
ENV_FILE="/opt/finco1/.env"
if [[ -f "$ENV_FILE" ]]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

DB_PATH="${FINCO_DB_PATH:-/opt/finco1/app/data/finco_runs.db}"
BACKUP_DIR="${BACKUP_DIR:-/opt/finco1/backups}"

# ── Pre-flight ────────────────────────────────────────────────────────────────
if [[ -z "$BACKUP_FILE" ]]; then
    echo "Usage: $0 <backup_path>" >&2
    echo "Example: $0 /opt/finco1/backups/finco_runs_20260508_120000.db.xz" >&2
    exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE" >&2
    exit 1
fi

# Detect format
if [[ "$BACKUP_FILE" == *.xz ]]; then
    DECOMPRESS="xz -d -k"
    RESTORED="${BACKUP_FILE%.xz}"
elif [[ "$BACKUP_FILE" == *.gz ]]; then
    DECOMPRESS="gunzip -k"
    RESTORED="${BACKUP_FILE%.gz}"
elif [[ "$BACKUP_FILE" == *.db ]]; then
    DECOMPRESS="cp"
    RESTORED="$BACKUP_FILE"
else
    echo "ERROR: Unknown file format. Expected .xz, .gz, or .db" >&2
    exit 1
fi

# ── Stop service ─────────────────────────────────────────────────────────────
echo "Stopping $SERVICE_NAME..."
systemctl stop "$SERVICE_NAME" || {
    echo "WARNING: Could not stop $SERVICE_NAME via systemctl. Trying pkill..." >&2
    pkill -f "gunicorn.*main_web" || true
    sleep 2
}

# ── Backup current DB before overwrite ───────────────────────────────────────
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
CORRUPT_BACKUP="${DB_PATH}.corrupt_${TIMESTAMP}"
if [[ -f "$DB_PATH" ]]; then
    echo "Backing up current DB to $CORRUPT_BACKUP..."
    cp "$DB_PATH" "$CORRUPT_BACKUP"
    # Also backup WAL if exists
    [[ -f "${DB_PATH}-wal" ]] && cp "${DB_PATH}-wal" "${DB_PATH}-wal.corrupt_${TIMESTAMP}" || true
fi

# ── Restore ─────────────────────────────────────────────────────────────────
RESTORED_PATH="/tmp/finco_runs_restored_$$.db"
echo "Decompressing to $RESTORED_PATH..."
$DECOMPRESS "$BACKUP_FILE" -c > "$RESTORED_PATH"

echo "Restoring to $DB_PATH..."
cp "$RESTORED_PATH" "$DB_PATH"
rm -f "$RESTORED_PATH"

# ── Fix permissions ───────────────────────────────────────────────────────────
chown root:root "$DB_PATH"
chmod 600 "$DB_PATH"

# WAL permissions
[[ -f "${DB_PATH}-wal" ]] && chown root:root "${DB_PATH}-wal" && chmod 600 "${DB_PATH}-wal" || true

# ── Restart service ──────────────────────────────────────────────────────────
echo "Restarting $SERVICE_NAME..."
systemctl start "$SERVICE_NAME" || {
    echo "WARNING: systemctl start failed, trying manual restart..." >&2
    cd /opt/finco1
    /opt/finco1/.venv/bin/gunicorn main_web:app --workers 2 --bind 127.0.0.1:8000 &
    sleep 3
}

# ── Healthcheck ───────────────────────────────────────────────────────────────
echo ""
echo "Running healthcheck..."
sleep 2
if curl -sf http://127.0.0.1:8000/public-health > /dev/null; then
    echo "✓ Healthcheck passed — service is up"
    echo ""
    echo "Restore complete: $BACKUP_FILE → $DB_PATH"
    exit 0
else
    echo "✗ Healthcheck failed — review service logs:" >&2
    echo "  journalctl -u $SERVICE_NAME -n 20" >&2
    exit 1
fi