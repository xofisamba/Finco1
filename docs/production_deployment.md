# FincoGPT Production Deployment Guide

## Directory Structure

```
/opt/finco1/
├── .venv/                    # Python virtual environment
├── main_web.py               # FastAPI application entry point
├── app/                      # Application code
│   ├── templates/
│   └── ...
├── static/                   # CSS, JS, images
├── storage/                  # SQLite DB + run artifacts
│   └── finco.db
├── backups/                  # SQLite backups (auto-generated)
├── .env                      # Secrets (NOT in git)
└── deploy/
    ├── nginx/app.conf        # Nginx config
    ├── systemd/finco-web.service
    ├── env.example           # Template for .env
    └── scripts/
        ├── start_prod.sh
        ├── backup.sh
        ├── smoke_test.sh
        └── healthcheck.sh
```

## Prerequisites

- Ubuntu/Debian Linux (or similar)
- Python 3.11+
- Nginx
- systemd
- certbot (for Let's Encrypt)
- SQLite (built-in)
- User `finco` (create with: `sudo adduser --system finco`)

---

## Step 1 — Create Linux User

```bash
sudo adduser --system finco
sudo mkdir -p /opt/finco1
sudo chown finco:finco /opt/finco1
```

---

## Step 2 — Deploy Application Files

```bash
# As your deploy user, clone/pull the repo
cd /opt/finco1

# Copy project files (from your deployment artifact)
# rsync, git pull, or scp the contents here
sudo chown -R finco:finco /opt/finco1
```

---

## Step 3 — Create Virtual Environment

```bash
cd /opt/finco1
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
# Ensure gunicorn is installed:
.venv/bin/pip install gunicorn
```

---

## Step 4 — Configure Environment Variables

```bash
# Copy the example env file
sudo -u finco cp deploy/env.example .env
sudo -u finco nano .env
```

Required variables in `.env`:

| Variable | Description |
|---|---|
| `FINCO_SECRET_KEY` | Session signing key — generate with `python3 -c "import secrets; print(secrets.token_hex(64))"` |
| `FINCO_ADMIN_USER` | Admin username |
| `FINCO_ADMIN_PASSWORD` | Admin password |
| `FINCO_SESSION_HOURS` | Session lifetime in hours (default: 8) |
| `FINCO_COOKIE_SECURE` | Set `true` in production (requires HTTPS) |
| `FINCO_DB_PATH` | Path to SQLite DB (default: `/opt/finco1/storage/finco.db`) |
| `FINCO_APP_USER` | Linux user that owns the DB (default: `finco`). Used by `restore.sh` to set ownership after restore. |
| `FINCO_APP_GROUP` | Linux group for DB ownership (default: `finco`) |

**Never commit `.env` to version control.**

---

## Step 5 — Nginx Configuration

```bash
# Copy nginx config
sudo cp /opt/finco1/deploy/nginx/app.conf /etc/nginx/sites-available/finco-web.conf

# Edit and replace YOUR_DOMAIN with your actual domain
sudo nano /etc/nginx/sites-available/finco-web.conf

# Enable the site
sudo ln -s /etc/nginx/sites-available/finco-web.conf /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # remove default if present

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

To enable HTTPS with Let's Encrypt:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

---

## Step 6 — Systemd Service

```bash
# Copy service file
sudo cp /opt/finco1/deploy/systemd/finco-web.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable on boot
sudo systemctl enable finco-web

# Start the service
sudo systemctl start finco-web

# Check status
sudo systemctl status finco-web
```

---

## Step 7 — Automated Backups

```bash
# Make backup script executable
sudo chmod +x /opt/finco1/deploy/scripts/backup.sh

# Add to crontab (runs daily at 03:00)
sudo crontab -e
# Add: 0 3 * * * /opt/finco1/deploy/scripts/backup.sh >> /var/log/finco-backup.log 2>&1
```

---

## Step 8 — Verify Deployment

```bash
# Run smoke tests
sudo -u finco /opt/finco1/deploy/scripts/smoke_test.sh
```

Expected output:
```
✓ /public-health returns 200 + OK
✓ /health redirects (auth-protected, expected 302)
✓ / redirects to /login (302)
```

---

## Logs

| Log | Location |
|---|---|
| Application access | `/var/log/finco-web/access.log` |
| Application error | `/var/log/finco-web/error.log` |
| Nginx access | `/var/log/nginx/finco-web.access.log` |
| Nginx error | `/var/log/nginx/finco-web.error.log` |
| Backup | `/var/log/finco-backup.log` |

---

## Common Operations

```bash
# Restart the app
sudo systemctl restart finco-web

# View recent logs
sudo journalctl -u finco-web -f

# Check if it's running
sudo systemctl is-active finco-web

# View backup directory
ls -la /opt/finco1/backups/

# Manually run a backup
sudo -u finco /opt/finco1/deploy/scripts/backup.sh
```

---

## Troubleshooting

### Service fails to start

1. Check logs: `sudo journalctl -u finco-web -xe`
2. Verify `.env` exists and variables are set
3. Verify `.venv` is present and gunicorn is installed: `/opt/finco1/.venv/bin/gunicorn --version`
4. Test manually: `sudo -u finco /opt/finco1/.venv/bin/python -c "from main_web import app; print('OK')"`

### 502 Bad Gateway

- Gunicorn not running: `sudo systemctl status finco-web`
- Wrong bind address: verify systemd service has `--bind 127.0.0.1:8000`
- Port conflict: `sudo lsof -i :8000`

### Database locked errors

- Only one gunicorn worker writes ( `--workers 2` = 1 writer + 1 balancer)
- For high concurrency, increase WAL checkpoint frequency in SQLite
- Check: `sqlite3 /opt/finco1/storage/finco.db "PRAGMA journal_mode;"`

### /public-health returns 404

- Endpoint requires exact path `/public-health` (no trailing slash)
- Verify `main_web.py` is the actual entry point and hasn't been renamed

### Static files not loading

- Check `/static/` is mounted in `main_web.py`
- Verify `static/` directory exists at `/opt/finco1/static/`
- Nginx alias should be: `alias /opt/finco1/static/;` (note trailing slash)

---

## Restore from Backup

If you need to restore from a backup (e.g., after a DB corruption incident):

```bash
sudo /opt/finco1/deploy/scripts/restore.sh /opt/finco1/backups/<backup_file>
```

What `restore.sh` does:
1. Stops the `finco-web` systemd service
2. Backs up the current (potentially corrupted) DB to `*.corrupt_<timestamp>`
3. Decompresses and restores the backup to `FINCO_DB_PATH`
4. **Sets DB ownership to `finco:finco`** (configurable via `FINCO_APP_USER` / `FINCO_APP_GROUP`)
5. Sets parent directory permissions to `750` (owner-only access)
6. Restarts the service
7. Runs a healthcheck (`/public-health`)

Ownership override (in `.env`):
```
FINCO_APP_USER=myuser
FINCO_APP_GROUP=mygroup
```

---

## Security Checklist

- [ ] `.env` file is NOT in git / deployment artifact
- [ ] `FINCO_SECRET_KEY` is a real random key, not the placeholder
- [ ] `FINCO_ADMIN_PASSWORD` is strong
- [ ] `FINCO_COOKIE_SECURE=true` in production
- [ ] HTTPS enforced (nginx redirect or TLS terminator)
- [ ] Nginx config has security headers set
- [ ] Service runs as non-root user (`finco`)
- [ ] `NoNewPrivileges=true` in systemd service
- [ ] Regular backups scheduled