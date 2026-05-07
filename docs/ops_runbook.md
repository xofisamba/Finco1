# FincoGPT Operations Runbook

**Version:** 1.0
**Stack:** FastAPI + Uvicorn/Gunicorn · Nginx · PostgreSQL · Ubuntu 22.04 LTS

---

## 1. Logging Setup

All application logs are written to `/opt/finco1/logs/`.

### Log File Layout

```
/opt/finco1/
  logs/
    app.log              ← main application log (rotating, 10 MB, 5 backups)
    backup.log           ← backup script output (append)
```

### Log Format

Each line follows:

```
YYYY-MM-DD HH:MM:SS | LEVEL    | MODULE        | MESSAGE
2026-05-08 12:00:00 | INFO     | fincogpt       | Logging initialised — file=/opt/finco1/logs/app.log
2026-05-08 12:00:01 | INFO     | fincogpt.middleware.request_logger | method=GET   path=/                                                              client=127.0.0.1           status=200  duration_ms=4.52
2026-05-08 12:00:02 | ERROR    | fincogpt.middleware.exception_handler | Unhandled exception: division by zero
```

### Module Loggers

| Module | Purpose |
|---|---|
| `fincogpt` | General application events |
| `fincogpt.middleware.request_logger` | Per-request access log |
| `fincogpt.middleware.exception_handler` | Uncaught exceptions |

### Querying Logs

```bash
# Follow live log
tail -f /opt/finco1/logs/app.log

# Show only errors
grep 'ERROR' /opt/finco1/logs/app.log

# Show requests for a specific path
grep '/run' /opt/finco1/logs/app.log

# Show requests from a specific IP
grep '192.168.1.5' /opt/finco1/logs/app.log

# Show last 100 lines
tail -n 100 /opt/finco1/logs/app.log
```

---

## 2. Backup & Restore

### 2.1 Backup Script

**Location:** `/opt/finco1/deploy/scripts/backup.sh`

**What it backs up:**
- Live PostgreSQL database (`pg_dump` — custom `.dump` + plain `.sql`)
- WAL segment reference (logged, PITR-optional)

**Output files:**
```
/opt/finco1/backups/
  finco1_backup_YYYYMMDD_HHMMSS.sql
  finco1_backup_YYYYMMDD_HHMMSS.dump
```

**Retention:** Files older than 30 days are automatically deleted.

**Run manually:**
```bash
sudo bash /opt/finco1/deploy/scripts/backup.sh
```

**Setup as a cron job (daily at 02:00 UTC):**
```bash
sudo crontab -e
# Add line:
0 2 * * * sudo bash /opt/finco1/deploy/scripts/backup.sh >> /opt/finco1/logs/backup_cron.log 2>&1
```

**Environment:** Requires `DATABASE_URL` set in `/opt/finco1/.env`:
```
DATABASE_URL=postgres://user:password@localhost:5432/finco1
```

### 2.2 Restore Script

**Location:** `/opt/finco1/deploy/scripts/restore.sh`

**Usage:**
```bash
sudo bash /opt/finco1/deploy/scripts/restore.sh /opt/finco1/backups/finco1_backup_20260508_120000.sql
```

**What it does:**
1. Prompts for confirmation
2. Stops the `finco-web` systemd service
3. Drops and recreates the target database
4. Restores from the SQL/dump file
5. Restarts `finco-web`

**⚠️ Warning:** This destroys the current live database. Use only when you need to roll back.

**Supported formats:**
- Plain SQL (`*.sql`) — via `psql --file=`
- Custom format (`*.dump`) — via `pg_restore`

---

## 3. Uptime Kuma (Docker)

Monitor the `/metrics` endpoint to detect downtime, high error rate, or unusual request volume.

### 3.1 Install Uptime Kuma via Docker

```bash
# Create data directory
sudo mkdir -p /opt/uptime-kuma/data

# Pull and start Uptime Kuma
sudo docker run -d \
  --name uptime-kuma \
  --restart unless-stopped \
  -p 3001:3001 \
  -v /opt/uptime-kuma/data:/app/data \
  uptimekuma/uptime-kuma:latest
```

**UI:** `http://your-server:3001` — set up admin account on first visit.

### 3.2 Configure Monitor

1. **Add Monitor → HTTP(s):**
   - Friendly name: `FincoGPT App`
   - URL: `http://localhost:8000/metrics`
   - Hostname: `app.finco.one`
   - HTTP Method: `GET`
   - Authentication: none (metrics is public)

2. **Heartbeat interval:** 60 seconds

3. **Alert on:**
   - HTTP status ≠ 200
   - SSL certificate expiring < 14 days
   - Response time > 5000 ms

4. **Notification channels** (optional): email / Discord webhook / Gotify

### 3.3 Verify Metrics Endpoint

```bash
curl http://localhost:8000/metrics
# Expected output:
# uptime_seconds 3723.45
# total_requests 14921
# total_errors 3
# db_size_kb 8192
```

---

## 4. Disk Monitoring

### Quick Check

```bash
# Overall disk usage
df -h

# Inode usage (if filesystem fills despite free space)
df -i

# Per-directory size (top-level only)
sudo du -sh /opt/finco1/*
```

### Alerting (simple cron check)

```bash
# Add to root crontab — warn if disk usage > 85%
sudo crontab -e
# Add line:
0 */6 * * * df -h | awk '{print $5, $6}' | grep -v 'Use%' | while read pct mount; do [ "${pct%\%}" -gt 85 ] && echo "WARNING: $mount at ${pct}% — $(date)" >> /opt/finco1/logs/disk_alerts.log; done
```

### Common Disk Pressure Points

| Path | Risk | Action |
|---|---|---|
| `/opt/finco1/backups/` | WAL dumps accumulate | `backup.sh` auto-purges >30 days |
| `/opt/finco1/logs/` | Rotating, 10 MB × 5 | Auto-rotated by app |
| `/var/log/finco-web/` | Nginx + gunicorn access logs | Logrotate config |
| `/var/lib/postgresql/data/` | WAL segments | Ensure PITR or WAL trimming configured |

---

## 5. Troubleshooting

### Application won't start

```bash
# Check service status
sudo systemctl status finco-web

# View gunicorn error log
sudo tail -n 50 /var/log/finco-web/error.log

# Test app import directly
cd /opt/finco1 && python3 -c "from main_web import app; print('OK')"

# Check ports are not in use
sudo ss -tlnp | grep 8000
```

### High error count in `/metrics`

```bash
# Find recent errors in app log
grep 'ERROR' /opt/finco1/logs/app.log | tail -n 20

# Check Nginx error log
sudo tail -n 20 /var/log/nginx/error.log
```

### Database connection failures

```bash
# Test PostgreSQL connection
psql "postgres://user:password@localhost:5432/finco1" -c "SELECT 1"

# Check pg running
sudo systemctl status postgresql

# Check connection count
psql "postgres://user:password@localhost:5432/finco1" -c "SELECT count(*) FROM pg_stat_activity"
```

### Nginx returning 502

**Cause:** Uvicorn/gunicorn is down or socket permission issue.

```bash
# Check if gunicorn is running
sudo systemctl status finco-web

# Check nginx error log
sudo tail -n 10 /var/log/nginx/error.log

# Restart in correct order
sudo systemctl restart finco-web
sleep 3
sudo systemctl reload nginx
```

### Backup fails

```bash
# Verify DATABASE_URL is set
grep DATABASE_URL /opt/finco1/.env

# Test pg_dump manually
pg_dump --host=localhost --port=5432 --username=finco1 --dbname=finco1 --format=plain --file=/tmp/test_backup.sql

# Check disk space
df -h /opt/finco1/backups/
```

### Restore fails

```bash
# Verify backup file exists and is readable
ls -lh /opt/finco1/backups/finco1_backup_YYYYMMDD_HHMMSS.sql

# Check PostgreSQL is running
sudo systemctl status postgresql

# Check user permissions
psql "postgres://user:password@localhost:5432/finco1" -c "SELECT 1" || echo "Auth failed"
```

---

## 6. Service Management

| Action | Command |
|---|---|
| Start | `sudo systemctl start finco-web` |
| Stop | `sudo systemctl stop finco-web` |
| Restart | `sudo systemctl restart finco-web` |
| Reload (zero-downtime) | `sudo systemctl reload finco-web` |
| View status | `sudo systemctl status finco-web` |
| View logs | `sudo journalctl -u finco-web -f` |
| View error log | `sudo tail -f /var/log/finco-web/error.log` |
| View access log | `sudo tail -f /var/log/finco-web/access.log` |

---

*Last updated: 2026-05-08*
