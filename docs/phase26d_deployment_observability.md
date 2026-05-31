# Phase 26D — Deployment / Observability

## Base SHA
`d9f5436aa04f41e0688aa5d2420fd860c5390fb9` (after PR #333 merge)

## Why Phase 26D

Phase 26C completed dependency pinning and CI reproducibility. Phase 26D adds narrow deployment-readiness and observability foundations: health/readiness endpoints, runtime diagnostics helpers, and a deployment runbook. This makes the app easier to run, diagnose, and monitor in a trusted pilot deployment without introducing enterprise infrastructure.

---

## Operational Surfaces Inspected

| File | What was checked |
|---|---|
| `main_web.py` | Existing `/public-health` and `/health` endpoints; FastAPI structure |
| `app/persistence/backup_restore.py` | Backup directory, auto-backup helpers |
| `app/persistence/db.py` | DB path resolution, WAL mode, schema init |
| `.env.example` | All deployment-related env vars already documented |
| `app/auth.py` | `FINCO_APP_MODE` pilot-mode fail-fast behavior |

---

## What Was Added

### 1. `/readyz` endpoint (`main_web.py`)

Lightweight readiness check at `GET /readyz` (no auth required):
- Checks app import OK, config resolved
- Checks DB path accessible (directory exists — not DB content query)
- Checks backup directory accessible
- Returns JSON with `status`, `app_mode`, `db_reachable`, `backup_dir_reachable`, `diagnostics`
- Does **not** trigger model run
- Does **not** access scenario data

Response codes:
- `200 OK` — status is "ok" or "degraded"
- `503 Service Unavailable` — status is "error"

### 2. `app/observability.py`

Minimal runtime diagnostics helpers:

| Function | Purpose |
|---|---|
| `get_app_health_status()` | Lightweight health dict — DB/backup reachability, config resolved, no model run |
| `get_runtime_diagnostics()` | Wraps health + safe config + Python version |
| `redact_config_value(value)` | Redacts sensitive env var values for diagnostics display |
| `get_safe_config_summary()` | Returns non-secret config summary (mode, DB path, backup dir, auto-backup settings) |

**Secret redaction:** `FINCO_SECRET_KEY`, `FINCO_ADMIN_PASSWORD`, `FINCO_ADMIN_PASSWORD_HASH`, `FINCO_CSRF_SECRET` are never exposed in raw form.

### 3. `docs/deployment_runbook.md`

Operational runbook covering:
- Prerequisites and installation (constraints.txt-based)
- Required env vars with `FINCO_APP_MODE` behavior table
- Starting the app (command line and systemd example)
- Health endpoints (`/public-health`, `/readyz`)
- Backup/restore and auto-backup behavior
- SQLite DB path and configuration
- Basic troubleshooting
- Out-of-scope features (multi-user, SSO, cloud DR, SOC2, tenant isolation)
- Governance posture (G20 BLOCKED, R99/R102 NOT APPROVED, partial_pay_sweep not promoted)

---

## What Was NOT Added

- No Dockerfile, docker-compose, Kubernetes, or cloud deployment scripts
- No metrics backend or monitoring SaaS integration
- No logging framework (docs-only recommendation for future)
- No multi-user auth or RBAC
- No enterprise SLA or SOC2 claims

---

## Tests

### `tests/test_phase26d_deployment_observability.py`

11 test cases:
1. `test_phase26d_doc_exists`
2. `test_deployment_runbook_exists`
3. `test_runbook_documents_trusted_pilot_install`
4. `test_health_or_readiness_endpoint_or_helper_exists`
5. `test_health_status_redacts_secrets`
6. `test_health_status_mentions_database_and_backup_posture`
7. `test_no_enterprise_deployment_claims`
8. `test_app_mode_and_pilot_config_documented`
9. `test_no_runtime_model_files_changed_or_claimed`
10. `test_no_js_financial_calculations_added`
11. `test_guardrails_unchanged`

---

## Guardrails Preserved

- No runtime formula changes
- No financial formula changes
- No model files changed
- No JS financial calculations
- No factory flag changes
- No fixture value changes
- No Revenue/OPEX/CAPEX/Tax formula changes
- No SHL/distribution logic changes
- No senior debt sizing logic changes
- G20 BLOCKED
- R99/R102 NOT APPROVED
- partial_pay_sweep not promoted
- flat/min DSCR sculpting not promoted
- Backend remains source of truth
- No lender/bank/audit/SaaS claims
- No multi-tenant/RBAC/SSO

---

## Recommended Next Phase

**Phase 27 — Frozen-Path External Validation Pack**
- Formal validation documentation for TUHO/Oborovo outputs
- External stakeholder presentation pack

**or**

**Phase 26E — Backup/Restore Admin Surface**
- UI surface for managing manual backups, restore, and backup listing
