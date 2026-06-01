# Phase 51A — /run route golden matrix

This matrix documents each golden case pinned by `tests/test_phase51a_run_route_golden_characterization.py`.

## Columns

- **case** — descriptive name
- **trigger/input** — the form payload or scenario
- **expected status** — HTTP status code or model result
- **expected project** — `project_id` in the response
- **expected runtime_origin** — `workspace_base` / `saved_state`
- **expected key metrics** — structure (not absolute values)
- **expected warning/guard behavior** — error markers, redirect, etc.
- **expected template/response marker** — template name or HTML marker
- **persistence side effect** — what gets written to DB
- **extraction risk** — what Phase 51B must preserve
- **test coverage** — test function name

## Golden matrix

| # | case | trigger / input | expected status | expected project | expected runtime_origin | expected key metrics | expected warning/guard behavior | expected template/response marker | persistence side effect | extraction risk | test coverage |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `tuho_base_run` | `{active_project: "tuho", project_type: "Wind", scenario: "Base"}` (clean baseline) | 200 | `tuho` | `workspace_base` | full KPI dict (8 keys, all numeric); revenue > 0; DSCR ∈ (0, 5] | none (clean run) | `lastRuntimeSummary` script + `applyWorkspaceStateMeta`; `partials/runtime_summary.html` | `record_workspace_runtime` for tuho; no scenario update (no bound_scenario_id) | All 3 execution-path orderings; replay metadata kwargs; `applyWorkspaceStateMeta` script | route-level: `test_run_route_still_in_main_web`, `test_run_with_dirty_state_returns_error_marker`. Service-level: `test_run_project_wind_base_returns_full_kpi_dict` |
| 2 | `oborovo_base_run` | `{active_project: "oborovo", project_type: "Solar", scenario: "Base"}` (clean baseline) | 200 | `oborovo` | `workspace_base` | full KPI dict (8 keys, all numeric) | none (clean run) | `lastRuntimeSummary` script; `partials/runtime_summary.html` | `record_workspace_runtime` for oborovo | template-seeded path with Solar project type; no `applyWorkspaceStateMeta` `runtime_origin` change | service-level: `test_run_project_solar_base_returns_full_kpi_dict` |
| 3 | `generic_wind_run` | `{project_type: "Wind", scenario: "Base", capacity_mw, tariff_eur_mwh, ...}` (no active_project) | 200 | derived from form (no saved project) | `workspace_base` | full KPI dict | none | `partials/kpis.html` (no lastRuntimeSummary script for generic path) | `record_workspace_runtime` for derived project | generic path uses different template (kpis.html, not runtime_summary.html) — Phase 51B must preserve | (covered by structural /run tests; not pinned as full golden) |
| 4 | `generic_solar_run` | `{project_type: "Solar", scenario: "Base", ...}` | 200 | derived from form | `workspace_base` | full KPI dict | none | `partials/kpis.html` | `record_workspace_runtime` for derived project | same as #3 | (covered by structural /run tests) |
| 5 | `invalid_project_type` | `{active_project: "tuho", project_type: "Nuclear", scenario: "Base"}` | 200 | n/a | n/a | n/a | `must be one of` / `error` marker | `partials/errors.html` | none | error path must return 200 with errors.html (not 4xx) | `test_invalid_project_type_returns_error_marker` (in test_htmx_internal_demo) — verified in characterization test |
| 6 | `no_auth` | any form, no session cookie | 302 | n/a | n/a | n/a | redirect to /login | `Location: /login` | none | auth must happen first (before snapshot resolution) | `test_unauthenticated_run_redirects_to_login` |
| 7 | `dirty_workspace` | form with non-baseline field after a previous run | 200 | n/a | n/a | n/a | `alert-error` / `Unsaved edits` / `no longer matches` | `partials/errors.html` | none (blocked before run_project) | dirty guard must fire BEFORE any model execution; same error text | `test_run_with_dirty_state_returns_error_marker` |
| 8 | `scenario_sensitivity` | `run_project("Wind", "Base")` vs `run_project("Wind", "Downside")` | model returns | n/a | n/a | revenue or IRR must differ by > 0.01 | n/a | n/a | n/a | Phase 51B must NOT collapse Base/Downside into same code path | `test_run_project_downside_differs_from_base` |
| 9 | `messages_and_integration` | `run_project("Wind", "Base")` | model returns | n/a | n/a | `messages: list`, `integration_status ∈ {full, partial, degraded}` | n/a | n/a | n/a | contract: messages list always present; integration_status always one of three values | `test_run_project_returns_messages_and_integration_status` |
| 10 | `tables_structure` | `run_project("Wind", "Base")` | model returns | n/a | n/a | `tables.waterfall`, `tables.revenue`, `tables.debt`, `tables.returns` all present, each a list of dicts | n/a | n/a | n/a | tables shape must be stable (frontend renders them) | `test_run_project_returns_tables` |
| 11 | `check_runtime_allowed_api` | direct service call: `check_runtime_allowed(workspace, snapshot)` | service returns `(bool, str, str\|None)` | n/a | n/a | tuple of 3 with correct types | n/a | n/a | n/a | Phase 51B must NOT change the public signature of `check_runtime_allowed` | `test_check_runtime_allowed_returns_three_tuple` |

## Stale-test cleanup principle (no stale tests in this phase)

This phase adds only NEW tests; it does not modify or convert existing
characterization tests. Future phases that touch /run (51B, 51C, etc.) must
NOT introduce transitional tests like "main_web.py should have N lines" or
"the run_project function should be called at line M". Pin behavior, not
implementation details.

## Production code diff verification

```
$ git diff --stat HEAD -- ':!tests/' ':!docs/' ':!reports/'
(empty — production code unchanged)
```

Verified in `test_no_production_code_changes`.
