# FincoGPT Operations Runbook

**Version:** 1.0 (SQLite-only, no PostgreSQL)
**Last updated:** 2026-05-08
**Branch:** `feature/ops-observability-clean`

---

## Service Management

```bash
# Restart service
sudo systemctl restart finco-web

# Check status
sudo systemctl status finco-web

# View logs
sudo journalctl -u finco-web -f --no-pager

# Check logs via script
sudo -u finco /opt/finco1/deploy/scripts/check_logs.sh
sudo -u finco /opt/finco1/deploy/scripts/check_logs.sh --errors-only
```

---

## Log Locations

| Log | Path |
|-----|------|
| Application logs | `/var/log/finco-web/` |
| Access log | `/var/log/finco-web/access.log` |
| Error log | `/var/log/finco-web/error.log` |
| Backup log | `/var/log/finco-backup.log` |
| Nginx access | `/var/log/nginx/finco-web.access.log` |
| Nginx error | `/var/log/nginx/finco-web.error.log` |

---

## Logrotate

Config: `deploy/logrotate/finco-web`
Installed: `sudo cp deploy/logrotate/finco-web /etc/logrotate.d/finco-web`

- Rotates daily, keeps 14 days
- Compresses old logs
- SIGHUP to finco-web after rotate

---

## Health Checks

```bash
# Public health (no auth)
curl -fsS https://app.finco.one/public-health
# Expected: {"status":"ok","app":"fincogpt","mode":"internal-demo"}

# Smoke test
/opt/finco1/deploy/scripts/smoke_test.sh

# Check logs for errors
/opt/finco1/deploy/scripts/check_logs.sh --errors-only
```

---

## Backup & Restore

### Backup (daily, automatic)
- **Schedule:** 02:15 server time via `/etc/cron.d/finco-backup`
- **Location:** `/opt/finco1/backups/`
- **Format:** `finco_runs_YYYYMMDD_HHMMSS.db.xz` (XZ-compressed SQLite)
- **Retention:** 30 days (older purged automatically)
- **Log:** `/var/log/finco-backup.log`

### Manual backup
```bash
sudo -u finco bash /opt/finco1/deploy/scripts/backup.sh
```

### Validate backup
```bash
# Check backup file size (non-zero)
ls -la /opt/finco1/backups/

# Verify SQLite integrity
xz -d < /opt/finco1/backups/finco_runs_YYYYMMDD_HHMMSS.db.xz -c | sqlite3 /dev/null && echo "Valid SQLite"

# List tables
xz -d < /opt/finco1/backups/finco_runs_YYYYMMDD_HHMMSS.db.xz -c | sqlite3 .tables
```

### Restore from backup
```bash
# 1. Stop service
sudo systemctl stop finco-web

# 2. Backup current DB
cp /opt/finco1/app/data/finco_runs.db /opt/finco1/backups/pre-restore-$(date +%Y%m%d).db

# 3. Restore from backup
xz -d < /opt/finco1/backups/finco_runs_YYYYMMDD_HHMMSS.db.xz -c > /opt/finco1/app/data/finco_runs.db
chown www-data:www-data /opt/finco1/app/data/finco_runs.db
chmod 664 /opt/finco1/app/data/finco_runs.db

# 4. Restart service
sudo systemctl start finco-web
```

**WARNING:** Restore only from a verified backup. Never restore over a live production DB without stopping the service first.

---

## Security Headers

All responses include:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: same-origin`
- `Content-Security-Policy: default-src 'self'`

---

## Metrics (SQLite-only)

For future `/metrics` implementation:
- DB size: `ls -la $FINCO_DB_PATH` or `stat --format=%s $FINCO_DB_PATH`
- WAL size: `stat --format=%s ${FINCO_DB_PATH}-wal` 2>/dev/null || echo "no WAL"
- Backup count: `ls /opt/finco1/backups/ | wc -l`

---

## Incident Response

### High response time
```bash
# Check for slow requests
/opt/finco1/deploy/scripts/check_logs.sh --last 100 | grep SLOW
```

### Service down
```bash
sudo systemctl restart finco-web
sudo journalctl -u finco-web -n 20
```

### Disk space low
```bash
df -h /opt/finco1
# Check backup size
du -sh /opt/finco1/backups/
# Remove old backups manually or via logrotate
```

---

## Forbidden (PostgreSQL era is over)

- **DO NOT** install `psycopg2`
- **DO NOT** set `DATABASE_URL`
- **DO NOT** run `pg_dump` or `pg_restore`
- **DO NOT** add `psql` commands

All data is in SQLite at `FINCO_DB_PATH`.