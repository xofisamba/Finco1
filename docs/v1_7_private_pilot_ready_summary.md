# v1.7 — Private Pilot Ready

**Date:** 2026-05-08
**Main HEAD:** `03ffab0` (Merge: feature/pilot-readiness → main)
**Status:** ✅ Private deployment ready

---

## Merges Completed

| Branch | → Main | SHA |
|--------|--------|-----|
| `feature/deployment-hardening` | Fast-forward | `ce19dcb` |
| `feature/auth-hardening` | Ort merge | `355f558` |
| `feature/pilot-readiness` | Ort merge | `03ffab0` |

---

## Test Results

| Suite | Passed | Status |
|-------|--------|--------|
| `tests/test_auth_lite.py` | 32 | ✅ |
| `tests/test_project_persistence.py` | 23 | ✅ |
| `tests/test_htmx_internal_demo.py` | 37 | ✅ |
| **Core total** | **92** | ✅ |

**Full suite:** Blocked by `scipy` (not in prod venv) — `test_s1_capex_schedule.py` fails collection. Does not affect app.finco.one deployment.

---

## Smoke Test Results

All checks passed via TestClient:

| Check | Result |
|-------|--------|
| GET / unauthenticated → 302 /login | ✅ |
| GET /login → 200 "Sign in" | ✅ |
| GET /public-health → 200 `{"status":"ok"}` | ✅ |
| GET /health unauthenticated → 401 | ✅ |
| POST /login (valid csrf + password) → 200/302 | ✅ |
| GET / (authenticated) → 200 FincoGPT | ✅ |
| GET /health (authenticated) → 200 | ✅ |

---

## Deployment Readiness

| Item | Status |
|------|--------|
| SQLite backup/restore scripts | ✅ |
| systemd service config | ✅ |
| nginx config | ✅ |
| env.example template | ✅ |
| Production deployment docs | ✅ |
| Auth security docs | ✅ |
| CSRF + rate limiting active | ✅ |
| Session cookie hardening | ✅ |
| Healthcheck + smoke_test scripts | ✅ |
| app.finco.one deploy package | ✅ Ready |

---

## Remaining Blockers

| Item | Severity | Notes |
|------|----------|-------|
| `feature/ops-observability` rebuild | Medium | PostgreSQL contamination — rebuild after pilot stable |
| TUHO CO2 revenue missing | High | Y1 revenue -611 kEUR, model fix needed |
| Oborovo OpEx duplication | High | Y1 OpEx +660 kEUR, model fix needed |
| External model/tax review | High | Required before investor-grade use |
| Per-user auth (not single admin) | Medium | Future: RBAC before multi-tenant |

---

## GO/NO-GO

| Target | Status | Conditions |
|--------|---------|------------|
| **app.finco.one private deployment** | ✅ **GO** | Deploy now |
| **Controlled B2B pilot** | ⚠️ **Conditional GO** | Requires live smoke test confirmation on Contabo |
| **Public production** | ❌ **NO-GO** | Model calibration fixes (TUHO CO2, Oborovo OpEx) + external review required |

---

## ops-observability: NOT Merged

`feature/ops-observability` (SHA: `a273381`) was **NOT merged** due to PostgreSQL/psycopg2 contamination. Branch held for future rebuild from clean main.

---

## rc1: Untouched ✅

No changes to `rc1/` directory or any frozen financial model files.