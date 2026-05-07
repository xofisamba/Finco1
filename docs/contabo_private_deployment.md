# Contabo Private Deployment

**Date:** 2026-05-07
**Status:** Internal private deployment ready (no auth — not for public use)

---

## Deployment Target

| Item | Value |
|------|-------|
| Domain | `app.finco.one` |
| OS | Ubuntu 22.04 LTS |
| Runtime | Python 3.12 |
| Web | FastAPI + Uvicorn |
| Frontend | HTMX 1.9 + Jinja2 |
| Reverse proxy | Nginx |
| SSL | Let's Encrypt (certbot) |
| Process manager | systemd |

---

## Stack Components

```
app.finco.one
    └── Nginx (443, HTTPS)
         └── Uvicorn (127.0.0.1:8000)
              └── main_web.py (FastAPI app)
                   └── Finco1 model engine
```

---

## Required Services

| Service | Purpose |
|---------|---------|
| `main_web.py` | FastAPI app — HTMX internal demo |
| `uvicorn` | ASGI server (gunicorn for production) |
| `nginx` | Reverse proxy + static file serving |
| `certbot` | Let's Encrypt SSL certificates |
| `systemd` | Process auto-restart on crash |

---

## Setup Steps

### 1. Install dependencies

```bash
apt update && apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx apache2-utils
pip install fastapi uvicorn jinja2 gunicorn
```

**Note:** `gunicorn` with `uvicorn.workers.UvicornWorker` is used for production (not plain uvicorn).
Single `uvicorn` CLI is fine for local development only.

### 2. Upload project

```bash
# Clone / rsync project to /opt/finco1/
rsync -avz --exclude='.git' --exclude='__pycache__' \
  ./ user@app.finco.one:/opt/finco1/
```

### 3. Systemd service

```bash
# /etc/systemd/system/finco-web.service
[Unit]
Description=FincoGPT Internal Demo
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/finco1
# gunicorn with uvicorn worker — required for FastAPI async
ExecStart=/opt/finco1/.venv/bin/gunicorn \
    --workers 2 \
    --threads 4 \
    --bind 127.0.0.1:8000 \
    --timeout 120 \
    --keep-alive 65 \
    --log-level info \
    --access-logfile /var/log/finco-web/access.log \
    --error-logfile /var/log/finco-web/error.log \
    -k uvicorn.workers.UvicornWorker \
    main_web:app
Restart=always
RestartSec=5
AmbientCapabilities=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
```

**Production launch command (gunicorn):**
```bash
gunicorn \
    --workers 2 \
    --threads 4 \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --keep-alive 65 \
    -k uvicorn.workers.UvicornWorker \
    main_web:app
```

For local development:
```bash
uvicorn main_web:app --host 0.0.0.0 --port 8765 --reload
```

```bash
systemctl enable finco-web
systemctl start finco-web
```

### 4. Nginx config

```nginx
# /etc/nginx/sites-available/finco-web
server {
    listen 443 ssl;
    server_name app.finco.one;

    ssl_certificate /etc/letsencrypt/live/app.finco.one/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.finco.one/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_read_timeout 120s;
    }

    location /static/ {
        alias /opt/finco1/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}

server {
    listen 80;
    server_name app.finco.one;
    return 301 https://$host$request_uri;
}
```

```bash
ln -s /etc/nginx/sites-available/finco-web /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
certbot --nginx -d app.finco.one
```

---

## Access Protection (Required Before Public Exposure)

**IMPORTANT:** These measures are REQUIRED before exposing `app.finco.one` publicly.
They are NOT a substitute for real auth — they are interim protection only.

### Option A: Nginx Basic Auth

Install `apache2-utils` (provides `htpasswd`):

```bash
# Create password file
htpasswd -c /etc/nginx/.htpasswd admin
# (enter strong password when prompted)

# Verify file created
cat /etc/nginx/.htpasswd
```

Add to Nginx config (`/etc/nginx/sites-available/finco-web`) inside the `server` block:

```nginx
# Inside server { } block, before location /
auth_basic "FincoGPT Internal — Authorized Only";
auth_basic_user_file /etc/nginx/.htpasswd;
```

Test and reload:
```bash
nginx -t && systemctl reload nginx
```

After this, users must enter `admin` + password to access the site.

---

### Option B: IP Whitelist

Restrict access to specific IP addresses only:

```nginx
# Inside server { } block
location / {
    # Allow your IP (replace with your actual IP)
    allow 93.184.216.34;
    # Allow your office/static IP
    allow 185.220.101.0/24;
    # Deny everyone else
    deny all;
    
    proxy_pass http://127.0.0.1:8000;
    # ... rest of proxy settings
}
```

Find your IP:
```bash
curl -s https://api.ipify.org
```

---

### Combining Both (Recommended for Transit)

For the transition period, use BOTH:
1. IP whitelist for your known IPs
2. Basic auth as additional layer

---

## Current Limitations

| Limitation | Severity | Notes |
|------------|----------|-------|
| No auth | 🔴 Critical | Basic Auth is interim only — real auth required before B2B |
| No persistence | 🟡 Medium | Excel generated on-demand, no server-side storage |
| No multi-user isolation | 🔴 Critical | All users share same session state |
| No audit log | 🟡 Medium | No record of who ran what scenario |
| No rate limiting | 🟡 Medium | DoS risk in public exposure |

---

## Auth-lite (v1.6+)

Session-based auth with bcrypt + signed cookies:

```bash
# .env file
export FINCO_SECRET_KEY=<strong-random-key>
export FINCO_ADMIN_USER=admin
export FINCO_ADMIN_PASSWORD=<password>
export FINCO_SESSION_HOURS=24          # session TTL
export FINCO_COOKIE_SECURE=true       # true for HTTPS
export FINCO_COOKIE_SAMESITE=lax
export FINCO_DB_PATH=/opt/finco1/app/data/finco_runs.db
```

Cookie flags: `httponly=True`, `secure=COOKIE_SECURE`, `samesite=lax`, `max_age=86400`.

Auth routes: `/` (redirect to /login), `/run`, `/compare`, `/download`, `/validate`, `/save-run`, `/runs`, `/run/{id}`.
Public routes: `/public-health`, `/login`, `/logout`.

**Persistence:** SQLite at `FINCO_DB_PATH` — backup daily before B2B pilot. Run:
```bash
cp /opt/finco1/app/data/finco_runs.db /opt/finco1/backups/finco_runs_$(date +%Y%m%d).db
```

---

## Post-Merge Deployment (v1.6+)

After merging `feature/project-persistence` to main:

```bash
cd /opt/finco1
git pull origin main
systemctl restart finco-web
systemctl status finco-web
```

Required env variables in `/opt/finco1/.env`:

| Variable | Recommended | Notes |
|---|---|---|
| `FINCO_SECRET_KEY` | Strong random string | **Required** — change from dev default |
| `FINCO_ADMIN_PASSWORD` | Strong password | Login credential |
| `FINCO_SESSION_HOURS` | `24` | Session TTL |
| `FINCO_COOKIE_SECURE` | `true` | HTTPS only |
| `FINCO_DB_PATH` | `/opt/finco1/app/data/finco_runs.db` | SQLite DB location |

---

## Recommended Next Phase (Phase 5)

Before making `app.finco.one` public:

1. **Auth** — session-based (cookie + bcrypt) — required first
2. **Persistence** — PostgreSQL for user accounts + saved scenarios
3. **Project save/load** — allow users to save/retrieve scenarios by name
4. **User sessions** — Redis for session state
5. **Audit log** — track which user ran which scenario + timestamp
6. **Rate limiting** — protect against abuse

---

## Streamlit Fallback

Streamlit remains available for internal admin use on separate ports:

```bash
streamlit run streamlit_app.py --server.port 8501
# Admin UI: http://app.finco.one:8501
```

This is separate from the HTMX app and does not need to be exposed publicly.

---

## Memory / Resource

| Component | Memory |
|-----------|--------|
| FastAPI + gunicorn (2 workers) | ~150MB |
| Nginx | ~20MB |
| Python model (per request) | ~50MB peak |
| **Total estimated** | **~250MB** |

Contabo 4 vCPU / 8GB RAM is sufficient for internal use.

---

## Security Notes

- HTTPS only — Let's Encrypt auto-renewal via certbot
- No auth currently — IP whitelist recommended as interim measure
- `rc1` is never modified — model logic frozen
- No database means no SQL injection risk
- HTMX is stateless — no session fixation risk

---

## Related Docs

- `docs/htmx_internal_demo.md` — how to run locally
- `docs/htmx_foundation_scope.md` — production HTMX scope
- `docs/release_checkpoint.md` — v1.5.0-htmx-internal-demo