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
apt update && apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx
pip install fastapi uvicorn jinja2
```

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
ExecStart=/opt/finco1/.venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:8000 \
    --timeout 120 \
    main_web:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
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

## Current Limitations

| Limitation | Severity | Notes |
|------------|----------|-------|
| No auth | 🔴 Critical | Anyone with URL can access and run model |
| No persistence | 🟡 Medium | Excel generated on-demand, no server-side storage |
| No multi-user isolation | 🔴 Critical | All users share same session state |
| No audit log | 🟡 Medium | No record of who ran what scenario |
| No rate limiting | 🟡 Medium | DoS risk in public exposure |

**These limitations must be resolved before any public or B2B deployment.**

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