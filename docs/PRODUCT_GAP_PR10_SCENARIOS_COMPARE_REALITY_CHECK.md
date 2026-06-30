# Product Gap PR10: Scenarios / Compare Reality Check

## Summary

Unlike CAPEX/OPEX/Revenue/Financial Statements/Distribution/Sponsor/
Senior Debt/Tax (PR1-PR9), the Scenarios and Compare screens were
investigated in depth and found to be **already honest**. Every
visible value on the Scenarios tab (`scenario_tab.html`), the
Dashboard's Scenario Matrix card (`scenario_matrix.html` /
`_scenario_unified_entry.html`), and the Compare tab
(`scenario_compare.html`, `scenario_compare_multi.html`,
`scenario_multi_compare_picker.html`) traces back to a real saved
`ScenarioRecord` (snapshot, overrides, `base_input_set`,
`last_run_summary`) persisted via `app/persistence/repository.py` /
`app/persistence/exports_repository.py`, or to a real
`run_project()` result. No fabricated/static/mock scenario or
compare output was found. This PR makes **no functional changes** —
it documents the investigation, corrects one stale/inaccurate
developer-facing comment, and confirms (with tests) that the existing
honest behavior holds.

## Investigation findings

### Scenarios screen (`app/templates/partials/scenario_tab.html`,
tab `panel-scenario`, wired directly in `workspace_shell.html`)

- **Scenario matrix table**: Base Case column and every non-base
  scenario column read from `effectiveValue()`, which resolves, in
  priority order, scenario `overrides` → `snapshot` → `base_input_set`
  — all real fields on the `ScenarioRecord` returned by
  `list_scenarios()` (`app/persistence/repository.py`). **Confirmed
  genuinely real, saved scenario input data.**
- **"Active" / "Run ✓" / "Not run" badges**: `workspace_state.
  active_scenario_id` (real workspace state) and
  `scen.last_run_summary` (real, only set after a real run via
  `update_scenario_last_run_summary`). **Confirmed real.**
- **Inline cell editing** (`startScenarioEdit`/`applyScenarioEdit`):
  POSTs to the real `/scenarios/{id}/update-overrides` endpoint, which
  persists through `update_scenario_overrides()`. **Confirmed a real,
  already-wired persistence path** — kept unchanged, not touched.
- **Add Scenario form**: POSTs to the real `/scenarios/add` endpoint
  (`add_scenario()` in the repository). **Confirmed real**, gated on
  `is_user_project` (protected/factory projects correctly cannot add
  scenarios). Kept unchanged.
- No static/hardcoded scenario values, no fake KPI numbers, no
  "preview schedule" style placeholder card was found anywhere in this
  template.

### Dashboard Scenario Matrix card (`app/templates/partials/
scenario_matrix.html`, included in `panel-overview`, plus
`_scenario_unified_entry.html` summary table in `panel-scenario`)

- `build_matrix_context()` (`app/ui/scenario_matrix.py`) builds every
  cell: Base column reads `project_ctx` (or `runtime_kpis` for KPI
  rows, i.e. the real last-run KPIs); Downside/Upside/Custom columns
  read `get_scenario_cell_value()`, which for input rows reads
  `overrides`/`snapshot`/`base_input_set` and for KPI rows reads
  `last_run_summary` — all real saved-scenario data, never fabricated.
- Columns with no scenario assigned correctly show literal "inherits
  Base" / "Future override" placeholder text, not invented numbers —
  this is an honest empty state, not a misleading static value.
  **Confirmed real, no change needed.**
- The Run button (`hx-post="/matrix/scenario/{id}/run"`) and resulting
  `_matrix_run_result.html` fragment render real
  `project_irr`/`avg_dscr` from an actual run, with a real
  `Run ✗`/error-message branch on failure. **Confirmed real.**
- One **stale developer-facing comment** was found in
  `workspace_shell.html` (not user-visible — Jinja `{# #}` comments are
  stripped at render time): it claimed "the other three columns are
  placeholders," which was true at the Phase M1 prototype stage but is
  no longer accurate now that Phase M2/M3/M4 wired live scenario data
  into those columns. **Corrected** (see "What changed" below). This
  had zero effect on rendered output — purely a documentation-accuracy
  fix for future maintainers.

### Compare screen (`app/templates/partials/scenario_compare.html`,
tab `panel-compare`, plus `scenario_compare_multi.html` /
`scenario_multi_compare_picker.html` in the sidebar workspace panel)

- **Base-vs-Active mode** and **legacy pair-compare mode**: both
  render `compare_result`, which is built by `compare_scenarios()`
  (`app/persistence/exports_repository.py`) from `_metric_value()`,
  which reads `record.last_run_summary` (Revenue, EBITDA, Senior Debt,
  SHL, DSCR, Project IRR, Equity IRR, Distributions) and
  `record.snapshot` (OPEX, CAPEX) on two real, ownership-validated
  saved `ScenarioRecord`s. Deltas are computed once, server-side, in
  `compare_scenarios()` (`right_num - left_num`) from these
  authoritative saved values — **not** recomputed client-side and
  **not** new logic added by this PR. **Confirmed genuinely
  Run/saved-state-backed.**
- **Multi-scenario compare** (`scenario_compare_multi.html`): same
  pattern, backed by the multi-scenario equivalent of
  `compare_scenarios()` in `exports_repository.py`
  (`MULTI_COMPARE_MIN/MAX_SCENARIOS`-gated). **Confirmed real.**
- **Provenance cards** (Runtime origin / Runtime at / Run ID / Saved
  snapshot timestamp / Runtime snapshot ID): all sourced from
  `replay_metadata` on the real scenario record. **Confirmed real.**
- **Governance rows** (G20 / R99/R102): present in
  `compare_result.governance_rows` and `multi_compare_result
  ['governance_rows']`, but already gated behind `{% if audit_mode %}`
  in both `scenario_compare.html` (line ~150) and
  `scenario_compare_multi.html` (line ~111), and `audit_mode` is
  hardcoded `False` everywhere these templates are rendered for normal
  users (`main_web.py` lines 1927/2556/2758/3909). **Confirmed this
  banned-jargon content never reaches normal-user-facing copy** — same
  audit-only gating pattern already established and accepted in PR7.
  `scenario_version_history.html`'s equivalent G20/R99/R102 badges are
  gated the same way. No change needed; this already matches the PR9
  precedent of removing/gating governance jargon from normal-user
  copy.
- **Empty states**: "No scenarios to compare. Run at least one
  scenario to enable comparison," "No Active Scenario. Select a saved
  scenario to compare against Base Case," "No Multi-Compare Loaded.
  Select 2-4 saved scenarios to start a multi-compare." All honest,
  accurate, no fabricated content shown in the absence of real data.
- A pre-existing test suite, `tests/test_phase14_scenario_compare_
  honesty.py`, independently confirms this same honesty contract was
  already verified in an earlier phase (source-clarity banners,
  timestamps, "pending / unavailable" vs `0`, "not_applicable" vs
  missing, G20/R99/R102 confirmed BLOCKED/NOT APPROVED in
  audit-only context). This PR's findings are consistent with that
  prior work, not a new discovery.

### Orphaned legacy route: `POST /compare` + `comparison.html`

- `app/templates/partials/comparison.html` and the `POST /compare`
  route (`app/services/compare_service.py::execute_compare_route`)
  **are** real, Run-backed (`run_project()` per scenario, soft-error
  per failing scenario, no persistence side effects) — not fake.
  However, searching every template and `static/*.js` file confirms
  **no UI element anywhere links to or posts to `/compare`** — it is
  unreachable from the SPA workspace (the live "Compare" tab uses
  `panel-compare` → `scenario_compare.html`, fed by
  `/scenarios/compare-panel`, an entirely separate, newer code path).
  Like the orphaned `app/tax_assumptions_ui.py` (PR9) and
  `debt_dscr_shl_panel.html` (PR8), this is **not part of the live
  product surface a user can reach** and is therefore out of scope for
  this UI-honesty PR — it is real output, not misleading placeholder
  content, and removing a reachable backend route is outside this
  PR's UI-only scope per the guardrails.

## What changed

`app/templates/partials/workspace_shell.html`:

- **Corrected** a stale, inaccurate developer-facing Jinja comment
  above the `{% include "partials/scenario_matrix.html" %}` line. The
  old comment claimed the Downside/Upside/Custom columns were always
  "placeholders" — no longer true since Phase M2 wired in live
  scenario data. The comment now accurately describes the current
  live/placeholder split (live once a scenario is assigned to a
  column, honest "inherits Base"/"Future override" text otherwise).
  This is a `{# ... #}` Jinja comment, stripped at render time —
  **zero effect on any rendered HTML, zero behavior change.**

No other files were changed. No template markup, no CSS, no Python
route/service code, no persistence code was modified.

## Why no further hide/replace/unavailable-panel work was needed

Per the spec's explicit instruction ("if unsure whether a value is
real, hide/replace rather than exposing it as authoritative"), this
PR's investigation specifically looked for: fake scenario list/matrix
values, fake Live-vs-Scenario labeling, fake post-Run scenario
outputs, fake compare deltas/KPI cards, and unclear "preview"/"example"
copy that could mislead a user into thinking unreal data was real.
**None were found.** Every number on these two screens traces to a
real saved `ScenarioRecord` field or a real `run_project()` result.
Inventing an "unavailable" panel where real data already exists and is
already correctly labeled would have made the product *less* honest,
not more — so none was added. This matches the spirit of PR6/PR7/PR8/
PR9 (which added unavailable-state panels only where static/hardcoded
data was found) applied to a screen where the investigation outcome is
"already compliant" rather than "needs remediation."

## What remains unavailable / future work

- The Dashboard Scenario Matrix's Custom column shows "Future
  override" when no third scenario has been assigned — this is
  already an honest, explicit "not yet" state (not a fake value), and
  is left as-is.
- The orphaned `POST /compare` / `comparison.html` legacy route
  remains unreachable from the UI. Whether to wire it into the SPA, or
  remove it as dead code, is a future routing decision outside this
  UI-honesty-only PR's scope (same treatment as the orphaned files
  found in PR8/PR9).
- Scenario/Compare engine parity (closing any remaining gaps between
  this app's IRR/DSCR/revenue/OPEX/EBITDA metric definitions and a
  full Excel-parity model) remains a future backend/model task per the
  spec, not a UI cleanup task.

## Confirmation: no scenario/comparison formulas, Run, Save,
persistence, export, Preview Architecture, Runtime Pipeline, tax
engine, senior debt engine, sponsor runtime, or distribution runtime
code was changed

This PR changed exactly one file: a Jinja `{# #}` developer comment in
`app/templates/partials/workspace_shell.html` (no rendered-output
change). `domain/*`, `app/waterfall_core.py`, `app/input_adapter.py`,
`app/project_factories.py`, `static/modelling/runtime-renderer.js`,
`app/services/model_preview.py`, `app/services/preview_context.py`,
`app/services/previews/*`, `app/persistence/repository.py`,
`app/persistence/exports_repository.py`, `app/ui/scenario_matrix.py`,
`app/services/compare_service.py`, and `main_web.py` were **not**
touched. No scenario-add/select/update-overrides/compare/compare-multi
route behavior changed. No new comparison formula, delta formula, or
client-side financial calculation was added anywhere.

## Tests

- `tests/test_product_gap_pr10_scenarios_compare_reality_check.py`
  (new): covers the minimum-required PR10 behaviors — Scenarios tab
  still renders, Compare tab still renders, Live/Active/Base labels
  remain present, real saved scenario assumption cells remain visible
  and correctly source from `effectiveValue()`, no fabricated
  static/mock scenario or compare output exists anywhere in these
  templates, the existing honest empty/unavailable-state copy is
  present, no banned jargon (C1/C2/Preview Architecture/Runtime
  Pipeline/stub/placeholder architecture) appears in user-facing
  Scenarios/Compare copy outside `audit_mode`-gated blocks, G20/R99/
  R102 governance content remains `audit_mode`-gated in all three
  scenario/compare templates that reference it, the corrected
  developer comment is present and the old inaccurate one is gone,
  `main_web.py`/persistence/service files were not touched, restricted
  guardrail paths are untouched (`git diff main`), and PR6-PR9's
  unavailable panels for Financial Statements/Distributions/Sponsor/
  Senior Debt/Tax remain unaffected.
- The full pre-existing Scenarios/Compare test suite (`tests/
  test_phase12_scenario_compare_and_history_workflow.py`,
  `tests/test_phase14_scenario_compare_honesty.py`,
  `tests/test_phase20f_active_scenario_runtime_binding.py`,
  `tests/test_phase20g_scenario_compare_history.py`,
  `tests/test_phase25b2_multi_scenario_compare.py`,
  `tests/test_phase25b2_1_multi_compare_picker.py`,
  `tests/test_phase25b3_factory_safety.py`,
  `tests/test_phase25b3_no_regression.py`,
  `tests/test_phase33_scenario_version_history_ui.py`,
  `tests/test_phase_m1_scenario_matrix.py`,
  `tests/test_phase_m2_scenario_matrix_live.py`,
  `tests/test_phase_m3_scenario_matrix_overrides.py`,
  `tests/test_phase_m4_scenario_matrix_run.py`,
  `tests/test_u4_scenario_matrix_mvp.py`,
  `tests/test_scenario_compare_c1_markup_contract.py`,
  `tests/test_scenario_compare_c1_migration_browser.py`,
  `tests/test_phase51c1_compare_route_golden_characterization.py`,
  `tests/test_phase51c2_compare_route_vertical_extraction.py`, and
  related `test_phase51l1`/`test_phase51r1`/`test_phase51r2`/
  `test_phase51s1`/`test_phase51s2` golden-characterization tests for
  the scenario add/update-overrides/select routes) were run unchanged
  and continue to pass — no narrow updates were needed to any of them,
  since no Scenarios/Compare markup or behavior was altered.

## Pre-existing failures (not touched, not regressions)

Per the sprint-level baseline, the 3 previously-confirmed pre-existing
failures
(`test_c2_pr1_live_model.py::TestStaticWiring::test_no_recalculation_formula_dependency_or_saverun_code_in_live_model`,
`test_c2_pr7_backend_preview_endpoint.py::...::test_no_financial_engine_call`,
`test_c2_pr9_runtime_request_hardening.py::TestNoRegressionForAuthorizedOrNullProject::test_authorized_project_behaviour_matches_pr8_contract`)
remain, with no new failures introduced by this PR. The pre-existing
6-failure cluster in
`tests/test_phase9_5_output_tabs_runtime_summary_binding.py`
(`TestRuntimeSummaryBinding::test_run_tuho_returns_runtime_summary` and
related `/run`-route/`sheet_financials.html` issues) and the
pre-existing clusters in `tests/test_phase20m_runtime_statement_polish.py`
/ `tests/test_phase9_5_excel_like_sheet_content_foundation.py` /
`tests/test_phase24c1_frozen_vs_derived_warning.py` were confirmed
identical on a clean `main` checkout and are unrelated to Scenarios/
Compare or this PR's single-comment change.
