# Release Checkpoint

## v1.7-private-pilot-ready
**Date:** 2026-05-08
**Branch:** `main` (HEAD: `20f3ac6`)
**Merges:**
- `feature/deployment-hardening` → main (fast-forward, SHA: `ce19dcb`)
- `feature/auth-hardening` → main (ort merge, SHA: `355f558`)
- `feature/pilot-readiness` → main (ort merge, SHA: `03ffab0` (merge commit, parent of 20f3ac6))

### What's New

| Component | Status |
|-----------|--------|
| Deployment hardening | ✅ SQLite backup/restore, systemd service, nginx config |
| Auth hardening (CSRF + rate-limit) | ✅ CSRF token on login, 5-failure lockout, per-IP in-memory |
| Pilot UX | ✅ details/summary replaces onclick, error banner, mobile CSS |
| Saved run export | ✅ /download Excel from stored inputs |
| Session cookie hardening | ✅ httponly, samesite=lax, secure flag configurable |
| SQLite backup scripts | ✅ backup.sh (sqlite3 .backup), restore.sh (ownership fix) |
| Production deployment docs | ✅ docs/production_deployment.md |
| Auth security docs | ✅ docs/auth_security.md |

### CSRF / Rate-Limit Behavior

| Action | Result |
|--------|--------|
| GET /login | HTML page with `name="csrf_token"` hidden field ✅ |
| POST /login without csrf_token | 422 Unprocessable Entity (FastAPI Form validation) |
| POST /login with invalid csrf_token | 403 Forbidden |
| POST /login with valid csrf_token + correct password | 302 redirect to / |
| 5 failed logins from same IP | 429 Too Many Requests, 5-min lockout |
| Successful login | Clears IP failed-attempt counter |
| Logout | Clears session cookie, redirects to /login |

Rate limiting: **in-memory, per-IP, per-process** — not shared across gunicorn workers.

### Deployment Scripts

| Script | Purpose |
|--------|---------|
| `deploy/scripts/backup.sh` | SQLite `.backup` (crash-safe), WAL checkpoint, xz compression |
| `deploy/scripts/restore.sh` | Stop service → restore → fix ownership/perms → restart → healthcheck |
| `deploy/scripts/smoke_test.sh` | /public-health, / redirect, /health redirect, /login page |
| `deploy/scripts/healthcheck.sh` | curl /public-health + service status |
| `deploy/scripts/start_prod.sh` | gunicorn startup wrapper |

### Merge SHAs

```
feature/deployment-hardening → main: ce19dcb (fast-forward merge from 381a2f5)
feature/auth-hardening       → main: 355f558 (ort merge: ce19dcb ← a411c71)
feature/pilot-readiness      → main: 20f3ac6 (docs commit, merge parent: 03ffab0)
```

**Final main HEAD:** `20f3ac6`

### Test Status

| Suite | Result |
|-------|--------|
| `tests/test_auth_lite.py` | 32 passed ✅ |
| `tests/test_project_persistence.py` | 23 passed ✅ |
| `tests/test_htmx_internal_demo.py` | 37 passed ✅ |
| Core suites (auth + persistence + htmx) | **92 passed** ✅ |
| Full suite | **Blocked** — `scipy` not installed in prod env, `test_s1_capex_schedule.py` collection fails |

### Smoke Test Results (all passed)

```
GET / unauthenticated → 302 redirect to /login    ✅
GET /login → 200, "Sign in" in page              ✅
GET /public-health → 200, {"status":"ok"}       ✅
GET /health unauthenticated → 401 (no redirect) ✅
POST /login with valid csrf + password → 200/302 ✅
GET / (auth) → 200, FincoGPT in text            ✅
GET /health (auth) → 200                         ✅
```

### Frozen Files (NOT modified)

- `rc1/**` — untouched ✅
- `domain/**` — untouched ✅
- `app/waterfall_core.py` — untouched ✅
- `app/waterfall_runner.py` — untouched ✅
- `app/scenarios.py` — untouched ✅
- `app/scenario_manager.py` — untouched ✅

### ops-observability Status

**NOT merged** — holds PostgreSQL/psycopg2 contamination. Will rebuild later.

---

## v1.6-project-persistence-mvp
**Date:** 2026-05-07
**Branch:** `main` (HEAD: `2e41c54`)
**Merge:** `feature/project-persistence` → main (fast-forward merge)

### What's New

| Component | Status |
|-----------|--------|
| SQLite persistence | ✅ `app/persistence/` — connection-per-op, WAL, no global shared state |
| Save Run | ✅ `POST /save-run` — re-runs model, stores inputs + KPIs |
| Run History | ✅ `GET /runs` — HTMX panel auto-refreshes after save |
| Reload Run | ✅ `GET /run/{id}` — restores KPIs from DB |
| User isolation | ✅ All queries filtered by `user_id` from session |
| Route-level multi-user tests | ✅ 3 end-to-end tests proving isolation |
| Auth required for app routes | ✅ Session cookie, 24h TTL, httponly, samesite=lax |
| History panel | ✅ `#history-area` listens for `refreshHistory from:body` |
| Save UX feedback | ✅ HTML partial with success/error, "re-run model" note |

### Persistence Routes

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/save-run` | ✅ | Save current form state → DB |
| `GET` | `/runs` | ✅ | List recent runs (≤20), HTMX partial |
| `GET` | `/run/{id}` | ✅ | Reload KPIs from saved run |

### Database

- **Path:** `app/data/finco_runs.db` (env: `FINCO_DB_PATH`)
- **Strategy:** Connection-per-operation, WAL mode, `busy_timeout=30000`
- **Schema:** `runs(run_id, user_id, project_type, scenario, created_at, inputs_json, kpis_json, excel_path, notes)`
- **Index:** `idx_runs_user ON runs(user_id, created_at DESC)`
- **Backup:** see `docs/project_persistence.md` — daily recommended

### Security

| Feature | Value |
|---|---|
| Session expiry | 24h (`FINCO_SESSION_HOURS=24`) |
| Cookie flags | `httponly=True`, `secure=COOKIE_SECURE`, `samesite=lax` |
| User isolation | Repository-level filter by `user_id` — no cross-user leakage |
| Delete UI | **Not exposed** — `delete_run()` exists at repo level only (MVP) |

### Configuration (env vars)

```bash
FINCO_SECRET_KEY=<strong-random-key>    # required in production
FINCO_ADMIN_USER=admin
FINCO_ADMIN_PASSWORD=<password>
FINCO_SESSION_HOURS=24
FINCO_COOKIE_SECURE=true                # true for HTTPS, false for localhost HTTP dev
FINCO_DB_PATH=/opt/finco1/app/data/finco_runs.db
```

### Files Added

```
app/persistence/__init__.py
app/persistence/db.py          # SQLite connection-per-op
app/persistence/repository.py  # save_run, get_run, list_runs, delete_run
app/templates/partials/run_history.html   # HTMX history panel
app/templates/partials/save_result.html    # save feedback partial
app/data/.gitkeep
docs/project_persistence.md     # full architecture + backup docs
tests/test_project_persistence.py  # 23 tests
```

### What Was NOT Changed

- `rc1/` — untouched
- `app/waterfall_core.py`, `app/waterfall_runner.py` — untouched
- `app/scenarios.py`, `app/scenario_manager.py` — untouched
- `domain/` — untouched
- Financial formulas — untouched
- Waterfall logic — untouched
- Depreciation runtime — untouched

### Test Status

| Suite | Result |
|-------|--------|
| `tests/test_project_persistence.py` | 23 passed ✅ |
| `tests/test_htmx_internal_demo.py` | 37 passed ✅ |
| Full suite | **1298 passed, 1 xfailed** ✅ |

### GO/NO-GO

| Target | Status |
|---|---|
| Internal deployment | ✅ GO |
| Controlled B2B pilot | ✅ GO (with caveats) |
| Public production | ⬜ Not yet — needs multi-user auth before public exposure |

### Security Limitations (B2B Pilot)

- Single admin credential only — no per-user accounts yet
- No RBAC — all authenticated users share admin credentials
- Route-level isolation enforced by `user_id` in session; a compromised admin cookie exposes all runs
- Future: per-user auth + RBAC before multi-tenant or public pilot

### Smoke Test Results (all passed)

```
GET / unauthenticated → 302 redirect to /login  ✅
/public-health (no auth) → 200 ok              ✅
POST /login → 302 + session cookie            ✅
POST /run (auth) → 200 KPI results             ✅
POST /save-run → 200 saved, run_id returned    ✅
GET /runs → 200, saved run appears            ✅
GET /run/{A_run_id} as User B → 404           ✅
POST /logout → 302                             ✅
```

### Previous Checkpoints

- [v1.5.0-htmx-internal-demo](#v150-htmx-internal-demo)
- [v1.4.1-advisory-ready-screening](./release_checkpoint.md#v141-advisory-ready-screening)

---


**Date:** 2026-05-07
**Branch:** `main` (HEAD: `e079c21` → now updated)
**Hotfix branch:** `hotfix/v1_4_1_advisory_ready` → merged to main

---

### What's New in v1.4.1

| Component | Status |
|-----------|--------|
| Wind profile plumbing fixed | ✅ Wind → wind_croatia_ibl |
| WIND_TURBINES asset class | ✅ Added to BankableAssetClass |
| Excel profile selection threaded | ✅ project_type passed explicitly |
| map_capex_line_item_to_basis updated | ✅ Solar→SOLAR_MODULES, Wind→WIND_TURBINES |
| DSCR tolerance documentation corrected | ✅ Policy tolerance, not cache collision |
| False-green test removed | ✅ test_advanced_capex_changes_taxable_income → meaningful invariant |
| HTMX foundation docs | ✅ docs/htmx_foundation_scope.md |

---

### Advisory Readiness

| Use Case | Status | Notes |
|----------|--------|-------|
| Internal advisory | ✅ GO | With known caveats |
| Controlled B2B pilot | ✅ GO | TUHO CO2 + Oborovo debt-service bug fixed in P0 |
| Investor-grade review | ⬜ Not yet | TUHO CO2 calibrated; Oborovo remaining gap: merchant curve vintage + depreciation |
| HTMX production | ⬜ Not yet | Auth + persistence required first |

---

### Known Calibration Caveats

| Issue | Impact | Fix Owner |
|-------|--------|-----------|
| TUHO CO2 revenue missing | Y1 revenue -611 kEUR (-12.5%) | Model fix |
| Oborovo debt-service bug | DSCR 0.181→1.250, Equity IRR 9.96%→10.16% | Fixed in P0 sprint |

**Do NOT mask these with DSCR tolerance — they are model bugs.**

---

### Bankable Runtime Active

| Component | Status |
|-----------|--------|
| `depreciation_bankable.py` | ✅ Runtime-active |
| `generate_tax_and_book_schedule()` | ✅ Tax/book schedules |
| `build_bankable_waterfall_schedule()` | ✅ Runtime bridge |
| `FULL_YEAR` convention | ✅ Explicitly forced in runtime |
| Day fraction application | ✅ Single point in `waterfall_core` |
| Legacy fallback | ✅ Preserved (no `advanced_capex_line_items`) |
| Excel Depreciation Assumptions | ✅ Solar + Wind profiles |
| Tax Depreciation sheet | ✅ Per-asset-class annual |
| Book Depreciation sheet | ✅ Per-asset-class annual |

---

### Test Status

| Suite | Result |
|-------|--------|
| `test_depreciation_wiring.py` | 10 passed ✅ |
| `test_bankable_depreciation.py` | 26 passed ✅ |
| `test_excel_depreciation_disclosure.py` | 13 passed ✅ |
| `test_golden_values.py` | 36 passed ✅ |
| Full suite | **1216+ passed, 1 xfailed** ✅ |

---

### DSCR Tolerance — Updated

**±0.15 is a defensive policy tolerance** for future model improvements.
**NOT caused by runtime nondeterminism.**

| Concern | Explanation |
|---------|-------------|
| Runtime nondeterminism | None — model is deterministic |
| Cache collisions | Golden tests run via API layer, not Streamlit |
| Deliberate model improvements | May shift DSCR — policy tolerance covers this |
| TUHO CO2 / Oborovo debt-service | Both calibrated — DSCR + tax basis fixed | P0 complete |

---

### Previous Checkpoints

- [v1.4-bankable-runtime-active](./release_checkpoint_v1.4.md)
---

## v1.5.0-htmx-internal-demo
**Date:** 2026-05-07
**Branch:** `main` (HEAD: `c38ac83`)
**Merge:** `feature/htmx-internal-demo` → main

### What's New

| Component | Status |
|-----------|--------|
| HTMX internal demo (`main_web.py`) | ✅ FastAPI + Jinja2 + HTMX |
| Custom inputs wired | ✅ `ProjectInputsSchema` → `build_projectinputs()` |
| Excel download | ✅ POST /download with form state |
| Compare scenarios | ✅ Base/Downside/Upside comparison |
| No silent fallback | ✅ Fail-fast on invalid inputs |
| Regression tests | ✅ 34 tests (test_htmx_internal_demo.py) |
| Depreciation disclosure sheets | ✅ In Excel export |
| Streamlit fallback preserved | ✅ Available on ports 8501-8503 |

### HTMX Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Main input form |
| POST | `/validate` | Form validation (partial) |
| POST | `/run` | Run model → KPI partial |
| POST | `/compare` | Compare Base/Downside/Upside |
| GET/POST | `/download` | Excel export (xlsx) |
| GET | `/health` | `{"status": "ok"}` |

### Deployment

- **Contabo private deployment**: `docs/contabo_private_deployment.md`
- **Internal demo only**: `python main_web.py` → http://localhost:8765
- **No auth / no persistence**: not for public access

### Known Limitations

| Item | Notes |
|------|-------|
| No auth | Single admin deploy only |
| No persistence | Excel on-demand, no server state |
| TUHO CO2 missing | 611 kEUR Y1 not in model |
| Oborovo debt-service bug | DSCR 0.181→1.250 | Fixed P0 |

---

### Previous Checkpoints

- [v1.4.1-advisory-ready-screening](./release_checkpoint.md#v141-advisory-ready-screening)

