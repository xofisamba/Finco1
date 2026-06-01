# FincoGPT — Deployment Runbook

> **Scope:** Local / trusted-pilot deployment of FincoGPT.  
> **Not in scope:** Multi-user, SSO, OAuth/SAML, cloud DR, enterprise SLA, SOC2, tenant isolation, SaaS-ready production.

---

## What is FincoGPT?

FincoGPT is an internal pilot tool for structured financial modelling of renewable energy projects (wind/solar).  
All calculations run in the Python backend. Browser-side JS is display-only.

**Validated scope:** TUHO Wind (72 MW) and Oborovo Solar (53.63 MW) frozen-template path is parity-validated against Excel.  
**Unvalidated scope:** Generic/new projects — review independently before drawing conclusions.

---

## Prerequisites

- Python 3.10+
- `constraints.txt` for pinned dependencies (reproducible install)
- `FINCO_APP_MODE=pilot` for trusted pilot deployment
- Real secrets required (no placeholder/dev credentials in pilot mode)

---

## Installation

```bash
# 1. Clone / pull
git clone https://github.com/xofisamba/Finco1.git
cd Finco1
git checkout main
git pull origin main

# 2. Install dependencies (use constraints.txt for reproducibility)
pip install -c constraints.txt -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with real values (see Required Environment Variables below)
```

---

## Required Environment Variables

| Variable | Required in pilot mode? | Description |
|---|---|---|
| `FINCO_APP_MODE` | Yes | Set to `pilot` for trusted pilot deployment |
| `FINCO_SECRET_KEY` | Yes | Secret signing key — use a long random string |
| `FINCO_ADMIN_USER` | Yes | Admin username |
| `FINCO_ADMIN_PASSWORD` | Yes | Admin password — must be real, not placeholder |
| `FINCO_DB_PATH` | No | SQLite DB path (default: `app/data/finco_runs.db`) |
| `FINCO_BACKUP_DIR` | No | Backup directory (default: `app/data/backups/sqlite`) |
| `FINCO_AUTO_BACKUP_ENABLED` | No | Enable auto-backup (default: `true`) |
| `FINCO_AUTO_BACKUP_INTERVAL_HOURS` | No | Hours between auto-backups (default: `24`) |
| `FINCO_AUTO_BACKUP_MAX_FILES` | No | Max auto-backups retained (default: `10`) |
| `FINCO_SESSION_HOURS` | No | Session TTL in hours (default: `24`) |

### `FINCO_APP_MODE` Behavior

| Mode | Behavior |
|---|---|
| `development` | Placeholder/dev credentials allowed with warnings |
| `internal` | Same as development; single-user internal use |
| `pilot` | **Fails fast** — refuses to start if secrets are placeholder/insecure |

---

## Starting the App

```bash
# Set env vars and start
export FINCO_APP_MODE=pilot
export FINCO_SECRET_KEY="<your-secret-key>"
export FINCO_ADMIN_USER=admin
export FINCO_ADMIN_PASSWORD="<your-password>"

python -m uvicorn main_web:app --host 127.0.0.1 --port 8000
```

Or with systemd (example override):
```ini
[Service]
Environment=FINCO_APP_MODE=pilot
Environment=FINCO_SECRET_KEY=<your-secret-key>
Environment=FINCO_ADMIN_USER=admin
Environment=FINCO_ADMIN_PASSWORD=<your-password>
```

For local HTTP development (cookie override):
```bash
FINCO_COOKIE_SECURE=false FINCO_SECRET_KEY="dev-secret" \
  python -m uvicorn main_web:app --host 127.0.0.1 --port 8000
```

---

## Health Check Endpoints

| Endpoint | Auth | Description |
|---|---|---|
| `GET /public-health` | None | Basic liveness check — always returns `{"status":"ok"}` |
| `GET /readyz` | None | Readiness check — validates DB path, backup dir, config resolved; no model run triggered |

`/readyz` returns JSON with:
- `status`: "ok" | "degraded" | "error"
- `app_mode`: resolved mode
- `db_reachable`: boolean
- `backup_dir_reachable`: boolean
- `diagnostics`: safe config summary (secrets redacted)

---

## Backup and Restore

### Auto-Backup

- Runs automatically every 24 hours (configurable via `FINCO_AUTO_BACKUP_INTERVAL_HOURS`)
- Retains up to 10 auto-backups; older ones are pruned automatically
- Manual backups and pre-restore safety backups are **never** pruned
- Backup files named: `auto_finco_runs_{timestamp}.db`

### Manual Backup

Create a manual backup via the in-app UI or:
```python
from app.persistence.backup_restore import create_sqlite_backup
backup = create_sqlite_backup()
print(backup.backup_path)
```

### Restore

1. Go to the in-app backup UI (Downloads tab)
2. Find the desired backup file
3. Use the restore function — a pre-restore safety backup is created automatically before restore

**Scope:** Single-user internal recovery. No enterprise DR or cloud/offsite backup.

---

## SQLite Database

- Default path: `app/data/finco_runs.db`
- Path configurable via `FINCO_DB_PATH`
- WAL mode enabled; foreign keys enforced
- Schema auto-initialised on first connect

---

## Troubleshooting

### App won't start in pilot mode
Check that `FINCO_SECRET_KEY` and `FINCO_ADMIN_PASSWORD` are set to real values (not `changeme` or placeholder).

### Database errors
Verify `FINCO_DB_PATH` points to a writable location and the directory exists.

### Backup directory not accessible
Check `FINCO_BACKUP_DIR` exists and is writable.

### Session expired
Check `FINCO_SESSION_HOURS` setting. Default is 24 hours.

---

## What is NOT Included (Out of Scope)

| Feature | Why |
|---|---|
| Multi-user / RBAC | Single-user internal pilot mode only |
| SSO / OAuth / SAML | Not implemented |
| Cloud / offsite backup | Not implemented |
| Enterprise SLA / SOC2 | Internal pilot tool only |
| Multi-tenant | Not implemented |
| Lender / bank / audit / SaaS claims | Explicitly not claimed |

---

## Governance Posture

- **G20:** BLOCKED
- **R99/R102:** NOT APPROVED
- `partial_pay_sweep`: not promoted
- `flat_dscr_sculpted`: not promoted
- `minimum_dscr_sculpted`: not promoted
- Backend remains source of truth

---

*Last updated: Phase 41. For trusted pilot deployment only — not for external distribution.*
