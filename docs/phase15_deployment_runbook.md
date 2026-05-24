# Phase 15 Deployment Runbook

## Scope

This runbook is for a **single-user guided internal pilot** only.

It does **not** claim:

- lender-ready deployment status
- audit-certified operating status
- multi-user governance readiness
- SaaS or multi-tenant readiness
- replay-engine behavior

The application remains a guided internal pilot tool with backend-owned runtime authority.

## What This Runbook Covers

- local or controlled pilot environment setup
- dependency and environment checks
- start, stop, and restart procedure
- backup and restore procedure
- guided pilot smoke test
- known environment limitations

## Authority Boundaries

- Runtime remains backend-owned and is the only source of financial truth.
- Persistence stores workflow metadata and saved boundaries only.
- Workbook/export remains descriptive and reviewer-facing.
- Scenario compare remains descriptive only.
- Backup and restore is operational recovery only. It is **not** audit replay and does not become replay-engine behavior.
- `audit_economic_mode` remains audit/reconciliation-only.
- `runtime_economic_mode` remains the only explicit runtime staging path.
- `G20` remains `BLOCKED`.
- `R99/R102` remain `NOT APPROVED`.

## Prerequisites

Recommended pilot operator prerequisites:

- Python 3.11 or newer
- writable local filesystem for SQLite and generated artifacts
- ability to set environment variables
- ability to install Python dependencies from `requirements.txt`

Current repo dependency set:

- `fastapi`
- `uvicorn`
- `httpx`
- `pydantic`

Workbook-oriented tests may also need `openpyxl` available in the local Python environment or via the bundled dependency path already used in this workspace.

## Package Source

Use one of these sources:

1. normal repository checkout from a clean branch or main
2. ZIP publish package extracted into a clean repository root when local git publication is blocked

If using ZIP fallback, verify the scoped file list before startup using the existing publish-package validator.

## Environment Setup

Recommended steps:

1. create a virtual environment
2. install `requirements.txt`
3. set required pilot environment variables
4. confirm the database path is writable
5. start the app and verify `/public-health`

## Required and Optional Environment Variables

Minimum pilot set:

- `FINCO_SECRET_KEY`
- `FINCO_ADMIN_USER`
- `FINCO_ADMIN_PASSWORD` or `FINCO_ADMIN_PASSWORD_HASH`

Strongly recommended for local HTTP pilot:

- `FINCO_COOKIE_SECURE=false`

Common optional settings:

- `FINCO_DB_PATH`
- `FINCO_SESSION_HOURS`
- `FINCO_COOKIE_SAMESITE`
- `FINCO_CSRF_SECRET`
- `FINCO_LOG_LEVEL`

## Local Run Command

Strongest known local entry path from the repository:

```bash
python main_web.py
```

The application entry point starts Uvicorn directly and binds to:

- host: `0.0.0.0`
- port: `8765`

Expected local URL:

- [http://127.0.0.1:8765](http://127.0.0.1:8765)

Public health check:

- [http://127.0.0.1:8765/public-health](http://127.0.0.1:8765/public-health)

## Storage, Artifacts, and Diagnostics

Current default SQLite path:

- `app/data/finco_runs.db`
- overridden by `FINCO_DB_PATH` when set

Related SQLite files to preserve when present:

- `*.db`
- `*.db-wal`
- `*.db-shm`

Export artifacts:

- current runtime/export tracking is recorded in persistence metadata
- exported workbooks and related operator-kept files should be preserved in the operator’s chosen artifact folder if they are downloaded or staged locally

Logging/diagnostics:

- application logging is configured to stdout
- request logging middleware logs request summaries except for selected safe paths
- in managed environments, stdout is expected to be captured by the host process manager

Health confirmation:

1. `GET /public-health` returns success
2. `GET /` redirects to `/login` when unauthenticated
3. login page renders
4. after login, project workspace loads

## Stop and Restart

To stop a local pilot session:

- stop the Python process running `main_web.py`

To restart:

1. confirm the database path still exists and is writable
2. restart the app with the same environment variables
3. rerun the pilot smoke checklist below

## Backup Procedure

Back up these items:

1. SQLite database file
2. SQLite WAL and SHM files if present
3. locally retained workbook exports and generated review artifacts
4. local `.env` or equivalent environment file if used outside source control

Recommended backup timing:

- before a pilot session
- after a pilot session
- before destructive local changes
- before extracting a new ZIP publish package into an existing working directory

## Restore Procedure

1. stop the app
2. copy the database and related SQLite files back into place
3. restore pilot artifacts and local environment file if used
4. restart the app
5. rerun the pilot smoke checklist

Integrity checks after restore:

- saved scenario list is visible
- a saved scenario can load
- runtime summary is still visible where expected
- export lineage and provenance remain readable

This restore flow is operational recovery only. It is **not** audit replay and does not promote persistence into runtime authority.

## Guided Internal Pilot Smoke Test

1. start the app
2. confirm `/public-health`
3. open the login page
4. select TUHO
5. select Oborovo
6. edit one supported assumption
7. verify dirty badge and unsaved changes banner
8. verify run / compare / save-run are blocked while dirty
9. save scenario
10. verify dirty state clears
11. run model
12. verify runtime summary appears
13. export workbook
14. verify workbook exists and is readable
15. compare scenarios
16. verify compare remains descriptive and excludes unsaved draft
17. verify export lineage panel is visible
18. verify governance labels:
   - `G20` remains `BLOCKED`
   - `R99/R102` remain `NOT APPROVED`
19. stop app
20. back up database and pilot artifacts

## Optional Dependency Guidance

Current constrained-environment notes:

- `tests/conftest.py` installs a test-only `bcrypt` shim when `bcrypt` is absent
- that shim affects **test collection only** and does not change production auth behavior
- workbook-oriented tests may require `openpyxl` through the bundled spreadsheet package path in constrained environments
- `.pytest_cache` permission warnings may appear in this workspace without affecting test truth
- local `.git` ref-lock permission problems may require ZIP publish fallback rather than direct branch publication

## Recommended Validation Slice

For a pilot operator or reviewer verifying the package in a constrained environment, use the established Phase 15 validation slice documented in the paired test branches.

At minimum:

- deployment runbook test
- browser workflow verification test
- Phase 15 e2e integration suite

## Outcome

This runbook is intended to let a single-user guided pilot operator:

- start the app
- verify health
- execute the core smoke path
- back up pilot data
- restore from local backup if needed

without changing runtime behavior or overstating production readiness.
