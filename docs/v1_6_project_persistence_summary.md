# v1.6 — Project Persistence MVP Summary

**Date:** 2026-05-07
**Commit:** `2e41c54` (merged to main)
**Branch:** `feature/project-persistence` → merged to `main`

---

## Files Added

| File | Purpose |
|---|---|
| `app/persistence/__init__.py` | Public API: `save_run`, `get_run`, `list_runs`, `delete_run` |
| `app/persistence/db.py` | SQLite: connection-per-op, WAL, `busy_timeout=30000`, `_init_schema()` |
| `app/persistence/repository.py` | Repository functions with `user_id` filter on all queries |
| `app/templates/partials/run_history.html` | HTMX history panel for `#history-area` |
| `app/templates/partials/save_result.html` | HTMX success/error feedback partial |
| `app/data/.gitkeep` | Preserves `app/data/` directory in git |
| `tests/test_project_persistence.py` | 23 tests: unit + route + multi-user isolation |
| `docs/project_persistence.md` | Full architecture, schema, backup, roadmap |

---

## Routes

| Method | Path | Auth | Notes |
|---|---|---|---|
| `POST` | `/save-run` | ✅ | Re-runs model, stores inputs+KPIs, returns HTML partial + `HX-Trigger: refreshHistory` |
| `GET` | `/runs` | ✅ | Lists ≤20 recent runs for current user as HTML |
| `GET` | `/run/{id}` | ✅ | Returns KPIs for saved run as HTML partial |

Auth routes (redirect to `/login` if unauthenticated): `/`, `/run`, `/compare`, `/download`, `/validate`, `/save-run`, `/runs`, `/run/{id}`

Public routes (no auth): `GET /public-health`, `GET/POST /login`, `POST /logout`

---

## Database

- **Path:** `app/data/finco_runs.db` (env: `FINCO_DB_PATH`)
- **WAL mode:** `PRAGMA journal_mode=WAL` — concurrent reads, serialised writes
- **Write timeout:** `PRAGMA busy_timeout=30000` (30s)
- **Schema:** `CREATE TABLE IF NOT EXISTS runs (...)` — idempotent init on every connection
- **Index:** `idx_runs_user ON runs(user_id, created_at DESC)`
- **Connection strategy:** Each `get_connection()` call opens a fresh connection; `get_cursor()` auto-closes it

---

## Backup

```bash
# Backup DB + WAL files
cp /opt/finco1/app/data/finco_runs.db /opt/finco1/backups/finco_runs_$(date +%Y%m%d).db
cp /opt/finco1/app/data/finco_runs.db-wal /opt/finco1/backups/ 2>/dev/null || true

# Restore
cp /opt/finco1/backups/finco_runs_20260507.db /opt/finco1/app/data/finco_runs.db
sqlite3 /opt/finco1/app/data/finco_runs.db "PRAGMA wal_checkpoint(TRUNCATE);"
```

**Recommendation:** Daily automated backup before B2B pilot. 30-day retention minimum.

---

## Security Limitations

| Limitation | Implication |
|---|---|
| Single shared admin credential | All users share same user_id in session |
| No per-user accounts | No way to distinguish between different people using the app |
| Route isolation via `user_id` from session | Works correctly if session is trusted |
| No RBAC | Anyone with session can access all runs for that user_id |
| `httponly=True`, `secure` flag configurable | Cookie protected against XSS and HTTP leakage |

**Before multi-tenant or public B2B:** Implement per-user auth with individual credentials and user-scoped `user_id`.

---

## Remaining Work Before B2B Pilot

| Item | Priority | Notes |
|---|---|---|
| TUHO CO2 revenue fix | 🔴 High | -611 kEUR Y1 revenue gap |
| Oborovo OpEx duplicate fix | 🔴 High | +660 kEUR Y1 OpEx overstatement |
| Per-user auth | 🟡 Medium | Single admin credential not suitable for B2B clients |
| Delete run UI | 🟢 Low | Append-only MVP, not critical |
| Export saved run from history | 🟢 Low | Future roadmap item |

---

## Cookie & Session Config

| Env | Default | Description |
|---|---|---|
| `FINCO_SESSION_HOURS` | `24` | Session TTL |
| `FINCO_COOKIE_SECURE` | `true` | Send only over HTTPS |
| `FINCO_COOKIE_SAMESITE` | `lax` | CSRF protection |

All cookies: `httponly=True`, `path=/`, `max_age=86400` (24h).

---

## What Was NOT Changed

```
rc1/                    ← untouched
app/waterfall_core.py   ← untouched
app/waterfall_runner.py ← untouched
app/scenarios.py        ← untouched
app/scenario_manager.py ← untouched
domain/                 ← untouched
app/capex_engine.py     ← untouched
app/input_schema.py     ← untouched
financial formulas      ← untouched
depreciation runtime    ← untouched
```

---

**Status:** Merged to `main` ✅ | Deploy to VPS: `git pull && systemctl restart finco-web`