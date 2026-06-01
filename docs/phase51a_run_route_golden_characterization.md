# Phase 51A — /run route golden characterization

## Pull request

- **PR:** https://github.com/xofisamba/Finco1/pull/379 (draft)
- **Branch:** `phase51a-run-route-golden-characterization`
- **Head SHA:** `3ae8dd2bc8731d917e5e2ca1ecaea11d45e270a2`
- **Base SHA:** `cfae719f6ac062d8c1ebda055bdc89f0bd5423c7` (origin/main, post PR #378 merge)

## Objective

Characterize the current behavior of POST /run in `main_web.py` with golden
output tests BEFORE any /run orchestration extraction in Phase 51B.

This phase is **characterization/testing only**. No production code is changed.
The /run route is **NOT extracted** — it still lives in `main_web.py` and uses
the existing services (`scenario_state_service`, `export_service`,
`export_audit_service`).

## /run route responsibilities

The POST /run route (line 1512 in main_web.py) is the largest remaining
god-module candidate in main_web.py. It is responsible for:

1. **Auth check** — redirects to /login if no session
2. **Form parsing** — 12 form fields plus `active_project` selector
3. **Workspace resolution** — `_project_workspace_from_snapshot` resolves
   the project record and workspace state from the form snapshot
4. **Runtime guard** — `check_runtime_allowed` (from
   `app/services/scenario_state_service.py`) validates the snapshot against
   the last runtime boundary
5. **Runtime snapshot resolution** — `_resolve_runtime_snapshot_source` (thin
   wrapper around `resolve_runtime_snapshot` in scenario_state_service) loads
   saved scenario data when applicable
6. **Three execution paths** based on project origin:
   - **user_created path** (line ~1554) — uses
     `build_projectinputs_from_snapshot`; template `partials/runtime_summary.html`
   - **template-seeded TUHO/Oborovo path** (line ~1640) — uses
     `build_projectinputs(schema)` from form; template
     `partials/runtime_summary.html`
   - **generic template-seeded path** (line ~1787) — uses
     `build_projectinputs(schema)`; template `partials/kpis.html`
7. **Model execution** — `run_project(project_key, scenario_name, override)`
   returns full KPI dict + tables
8. **Persistence** — `record_workspace_runtime` and
   `update_scenario_last_run_summary` write to SQLite via
   `app/persistence/repository.py`
9. **Replay metadata** — `_replay_metadata_for_project` builds governance /
   scenario provenance / warning metadata
10. **Response rendering** — `templates.TemplateResponse` with either
    `partials/runtime_summary.html` (TUHO/Oborovo + user_created) or
    `partials/kpis.html` (generic). sessionStorage write is prepended as a
    `<script>` tag to populate the runtime summary block on next page load.

## Current /run orchestration steps

```
1. Auth check (line 1517)
2. Form parsing (line 1522-1533)
3. Snapshot + project_record + workspace_state (line 1534-1536)
4. Runtime guard (line 1537-1542)
5. Runtime seed normalization (line 1545)
6. Runtime snapshot resolution if saved_state or user_created (line 1548-1553)
7. If user_created → user_created path (line 1556-1640)
8. Elif tuho/oborovo seed → template-seeded factory path (line 1643-1785)
9. Else → generic template-seeded path (line 1787-1895)
```

## Request / form inputs used

| Field | Source | Required |
|---|---|---|
| `active_project` | form (hidden JS input) | optional |
| `project_type` | form | required |
| `scenario` | form | required |
| `capacity_mw` | form | optional |
| `tariff_eur_mwh` | form | optional |
| `p50_hours` | form | optional |
| `total_capex_keur` | form | optional |
| `opex_y1_keur` | form | optional |
| `gearing_pct` | form | optional |
| `target_dscr` | form | optional |
| `interest_rate_pct` | form | optional |
| `tenor_years` | form | optional |

`_collect_form_snapshot(form)` builds a snapshot dict from all 12 fields
plus `active_project` for workspace resolution.

## Project / workspace / scenario state dependencies

- `get_current_user(request)` — session auth
- `get_project_record(user_id, project_code)` — project lookup
- `save_project(...)` — factory template bootstrap (TUHO, Oborovo,
  generic_wind, generic_solar)
- `get_workspace_state(user_id, project_id)` — workspace state
- `save_workspace_state(...)` — workspace bootstrap
- `check_runtime_allowed(workspace_state, snapshot)` — dirty guard
- `_resolve_runtime_snapshot_source(...)` — thin wrapper around
  `resolve_runtime_snapshot` in scenario_state_service

## Model execution path

```
run_project(project_key, scenario_name, project_inputs_override=override)
  → run_demo_project(project_key, scenario_name, override=override)
    → build_projectinputs(...) (UI runner entry point)
      → domain/waterfall_core.py (model engine)
        → result dict with kpis + tables
```

Service wrapper: `app/api/project_runner.py::run_project` builds the full
result dict including:
- `kpis`: `total_revenue_keur`, `total_ebitda_keur`, `total_opex_keur`,
  `total_distributions_keur`, `project_irr`, `equity_irr`, `min_dscr`,
  `avg_dscr`
- `tables`: `waterfall`, `revenue`, `debt`, `returns`
- `messages`, `integration_status`, `dualrun_validation`

## Persistence side effects

- `record_workspace_runtime(user_id, project_id, project_code,
  runtime_snapshot, runtime_summary, runtime_snapshot_id, runtime_origin,
  governance_state, active_scenario_id, active_scenario_name,
  replay_metadata)` — writes to `workspace_runtime` table
- `update_scenario_last_run_summary(user_id, scenario_id, kpis,
  replay_metadata)` — writes to `scenario` table when `saved_state` +
  `bound_scenario_id`

## Rendered response / template behavior

- **user_created path:** `partials/runtime_summary.html` + prepended
  `sessionStorage.setItem("lastRuntimeSummary", ...)` script
- **template-seeded TUHO/Oborovo path:** `partials/runtime_summary.html` +
  prepended script (with `<!DOCTYPE>` body injection)
- **generic path:** `partials/kpis.html` (no sessionStorage prepend)
- **error path:** `partials/errors.html` with `errors: [...]` context

The `lastRuntimeSummary` payload includes:
```json
{
  "project_id": "tuho",
  "project_name": "TUHO Wind 1",
  "ran_at": "2026-06-01 23:46",
  "status": "ok",
  "project_irr": "14.12%",
  "equity_irr": "15.21%",
  "avg_dscr": "2.72x",
  "min_dscr": "2.36x",
  "total_revenue_keur": "265,508 kEUR",
  "total_ebitda_keur": "247,890 kEUR",
  "total_opex_keur": "17,618 kEUR",
  "total_distributions_keur": "98,750 kEUR",
  "senior_debt_keur": "43,359 kEUR",
  "shl_opening_keur": "32,704 kEUR",
  "error_message": ""
}
```

`applyWorkspaceStateMeta(...)` is called alongside to refresh
last_runtime_origin_label and active_scenario_id.

## Golden outputs selected

Phase 51A pins the following:

1. **Service-level KPI structure** — `run_project("Wind", "Base")` and
   `run_project("Solar", "Base")` must return the full KPI dict with all 8
   required keys, all numeric types, and plausible ranges (IRR ∈ [-0.5,
   +0.5], DSCR ∈ (0, 5], revenue > 0).
2. **run_project output structure** — `messages` list, `integration_status`
   ∈ {`full`, `partial`, `degraded`}, `tables` dict with
   `waterfall`/`revenue`/`debt`/`returns` keys (each a list of dicts).
3. **Scenario sensitivity** — `Downside` must differ from `Base` (revenue
   or IRR must differ by > 0.01).
4. **HTTP auth** — unauthenticated POST /run returns 302 with
   `Location: /login`.
5. **HTTP dirty guard** — second POST with non-baseline field returns 200
   with `alert-error` / "Unsaved edits" / "no longer matches" marker.
6. **HTTP response type** — always `text/html` (template response).
7. **Current-state guardrails** — main_web.py still has zero direct
   `record_export(...)` calls; no direct `record_export` import; no direct
   `runtime_guard_for_snapshot` import (uses
   `check_runtime_allowed` from `scenario_state_service` instead).
8. **Service API stability** — `scenario_state_service.check_runtime_allowed`
   and `resolve_runtime_snapshot` still exist and return the expected
   tuple / dict shapes.

## Extraction risks for Phase 51B

When Phase 51B extracts POST /run into `app/services/run_service.py`, the
following must be preserved:

1. **All three execution paths** must remain distinct (user_created vs
   TUHO/Oborovo vs generic). Phase 51B should NOT collapse them into a
   single generic dispatcher.
2. **Persistence side effects** must be preserved in identical order
   (`record_workspace_runtime` first, then conditional
   `update_scenario_last_run_summary`).
3. **Replay metadata construction** (`_replay_metadata_for_project`) must
   receive the same `scenario_provenance`, `runtime_warning`,
   `active_scenario_id`/`active_scenario_name` arguments.
4. **Response rendering** must keep using `templates.TemplateResponse` (no
   JSON shortcut). The sessionStorage prepended script for
   `lastRuntimeSummary` and `applyWorkspaceStateMeta` is part of the
   contract with the frontend.
5. **Auth check** must remain at the top of the route (or be hoisted into
   the service entry point).
6. **Runtime guard** (`check_runtime_allowed`) must fire before any
   `run_project` call.
7. **Dirty state** path must keep returning `partials/errors.html` with
   the existing message text (frontend may match on it).
8. **kpis dict shape** returned by `run_project` must NOT change (Phase
   51A pins structure; Phase 51B must preserve it).

## What must not change in Phase 51B

- Production code behavior (formula outputs, route responses, persistence
  side effects)
- Public service API of `app/api/project_runner.py::run_project`
- Template files (`partials/runtime_summary.html`, `partials/kpis.html`,
  `partials/errors.html`)
- JS frontend contract (`lastRuntimeSummary` payload shape,
  `applyWorkspaceStateMeta` call signature)
- Guardrail state (G20 BLOCKED, R99/R102 NOT APPROVED, etc.)
- Fixture CSVs
- Migrations / schema

## Guardrails (all preserved)

- No changes to financial formulas
- No changes to runtime calculations
- No changes to model outputs
- No changes to route behavior
- No changes to export behavior
- No changes to project factories
- No changes to fixture CSVs
- No changes to schema/migrations
- No JavaScript financial calculations added
- No generic validation
- G20 BLOCKED
- R99/R102 NOT APPROVED
- partial_pay_sweep NOT promoted
- flat/min DSCR NOT promoted
- Backend remains source of truth
- PR #299 remains draft and not merged

## Test results

```
$ .venv/bin/python -m pytest tests/test_phase51a_run_route_golden_characterization.py -q
25 passed in 3.48s

$ .venv/bin/python -m pytest tests/test_phase51a_run_route_golden_characterization.py tests/test_phase50d_current_state_after_refactor_cleanup.py tests/test_phase50c_closeout_scenario_state_service.py -q
75 passed in 3.82s

$ .venv/bin/python -c "import main_web; print('import main_web OK')"
import main_web OK
```

## Files changed

```
docs/phase51a_run_route_golden_characterization.md             | (new)
docs/phase51a_run_route_golden_matrix.md                      | (new)
reports/phase51a_run_route_golden_characterization_summary.json | (new)
tests/test_phase51a_run_route_golden_characterization.py      | (new)
```

## Recommended next phase

**Phase 51B — vertical extraction of POST /run orchestration into
`app/services/run_service.py`, keeping the /run route thin and proving
behavior preservation with Phase 51A golden tests.**

Do not start 51B until this PR is merged.
