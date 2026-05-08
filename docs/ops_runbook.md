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

```bash
# Manual backup
sudo -u finco /opt/finco1/deploy/scripts/backup.sh

# Backup path
ls -la /opt/finco1/backups/

# Restore from backup
sudo /opt/finco1/deploy/scripts/restore.sh /opt/finco1/backups/<backup_file>

# Cron schedule (daily at 02:15 server time)
/etc/cron.d/finco-backup:
15 2 * * * finco /opt/finco1/deploy/scripts/backup.sh >> /var/log/finco-backup.log 2>&1
```

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