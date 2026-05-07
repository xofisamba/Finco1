# Project Persistence — Architecture & Design

## Overview

Lightweight persistence layer for saving/loading project model runs. Enables authenticated users to store runs, revisit KPI results, and support controlled B2B pilot workflows.

**Constraint:** Uses raw `sqlite3` (Python stdlib) — SQLAlchemy is NOT available on the production VPS.

### Save Run Semantics

**Important:** `POST /save-run` does NOT snapshot the already-rendered KPI HTML card.
Instead, it **re-runs the model** with the current form field values to get fresh KPIs,
then stores those along with the form inputs. This means:

- The saved run reflects the current form state (inputs as submitted)
- KPIs are computed fresh, not extracted from HTML
- Results should match what you'd get from clicking "Run Model" with the same inputs
- Future improvement: expose a `run_id` from `/run` and store that directly to avoid re-computation

### SQLite Connection Strategy

Connection-per-operation: each `get_connection()` call opens a fresh SQLite connection,
applies WAL mode + foreign keys, runs schema init (idempotent via `CREATE TABLE IF NOT EXISTS`),
and returns it. `get_cursor()` context manager auto-closes the connection after use.

This is safe under gunicorn threaded workers because:
- SQLite's file-level locking serialises writes
- WAL allows concurrent reads across connections
- No global shared mutable connection object

---

## Database Architecture

- **Engine:** SQLite 3 with WAL journal mode
- **Location:** `app/data/finco_runs.db` (env-overrideable via `FINCO_DB_PATH`)
- **Schema migrations:** Manual — run `db.init_db()` or use `INIT_SQL` constant
- **Foreign keys:** Enforced (`PRAGMA foreign_keys=ON`)
- **Concurrency:** WAL mode allows safe shared access within the single-process Uvicorn worker

### Future PostgreSQL Migration Path

The repository layer (`app/persistence/repository.py`) abstracts SQL. To migrate:

1. Replace `app/persistence/db.py` with SQLAlchemy async engine (or `psycopg2`)
2. Replace raw `?` parameter placeholders with SQLAlchemy column expressions
3. Keep `save_run`, `get_run`, `list_runs`, `delete_run` signatures unchanged
4. Run migration: add `user_id` index, rename `runs` table if needed

---

## Schema

```sql
CREATE TABLE runs (
    run_id       TEXT PRIMARY KEY,   -- 16-char hex UUID
    user_id      TEXT NOT NULL,      -- session user identifier
    project_type TEXT NOT NULL,      -- 'Solar' | 'Wind'
    scenario     TEXT NOT NULL,      -- 'Base' | 'Downside' | 'Upside'
    created_at   TEXT NOT NULL,      -- ISO 8601 UTC timestamp
    inputs_json  TEXT NOT NULL,      -- JSON-serialised input dict
    kpis_json    TEXT NOT NULL,      -- JSON-serialised KPI output dict
    excel_path   TEXT,               -- path to exported Excel (optional)
    notes        TEXT                -- free-text notes (optional)
);

CREATE INDEX idx_runs_user ON runs(user_id, created_at DESC);
```

### What Is NOT Persisted

- Giant waterfall intermediate tables (CashflowPeriod rows)
- Full project inputs schema object — only the form-input subset is stored
- Historical DSCR series or debt schedule arrays

---

## Storage Strategy

| Asset | Location | Notes |
|---|---|---|
| SQLite DB | `app/data/finco_runs.db` | WAL mode, not committed to git |
| Excel exports | `storage/exports/` | Created on demand, not stored in DB |
| Run records | `runs` table | JSON blobs for inputs/kpis |

**Backup:** `data/finco_runs.db` should be included in the server backup schedule. No auto-purge yet; consider a retention policy (e.g., 90 days for anonymous/pilot runs).

---

## API Routes

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/save-run` | ✅ | Save current model run, returns `run_id` |
| `GET` | `/runs` | ✅ | List current user's recent runs (≤20) |
| `GET` | `/run/{id}` | ✅ | Reload a specific run's KPIs into the dashboard |
| `GET` | `/public-health` | ❌ | Health check (no auth) |
| `POST` | `/login` | ❌ | Session login |
| `POST` | `/logout` | ❌ | Clear session |

---

## User Isolation

- All queries are filtered by `user_id` extracted from the session cookie
- No cross-user data leakage: `get_run(run_id, user_id)` and `list_runs(user_id)` both enforce `WHERE user_id=?`
- No RBAC yet — single admin role only

### Session-to-User Mapping

```
Session cookie (signed token) → SessionData(user_id, ...) → used as filter in every DB query
```

---

## Dashboard History Panel

Loaded via HTMX on page load:

```
GET /runs  →  renders  app/templates/partials/run_history.html
```

Each run item is clickable and loads KPIs into the results area:

```
hx-get="/run/{run_id}" hx-target="#results-area"
```

---

## Configuration

| Env variable | Default | Description |
|---|---|---|
| `FINCO_DB_PATH` | `app/data/finco_runs.db` | Path to SQLite DB |

> **Important:** `storage/exports/` and `app/data/` are gitignored — DB and exports are never committed.

---
| `FINCO_SECRET_KEY` | `changeme` | Session signing key |
| `FINCO_ADMIN_PASSWORD` | `fincoGPT2026!` | Login password |

---

## Retention Policy Suggestions

- **Pilot phase:** Keep all runs (manual purge via `DELETE FROM runs WHERE created_at < ?`)
- **Production:** Add a background task to purge runs older than 90 days
- **User deletion:** Add `DELETE FROM runs WHERE user_id=?` when user accounts are removed
- **Excel exports:** Currently not tracked in DB — consider adding `excel_path` when saving if audit trail is needed

---

## Test Coverage

| Test class | Coverage |
|---|---|
| `TestSaveAndLoad` | save, get, list, delete, count, user isolation |
| `TestPersistenceRoutes` | auth redirects, save/list/load routes, 404 for missing run |

Run: `python3 -m pytest tests/test_project_persistence.py -q`