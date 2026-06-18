# Phase P1-UX-FIX-1 — Pilot UX Polish

## Context

POST-P1-CLEANUP-SMOKE-1 surfaced four low-risk UX inconsistencies in the
internal pilot loop. This PR addresses all four without touching any
model, debt, persistence schema, or export logic.

## Tasks

### TASK A — Realized Gearing for Generic

**Problem**: `_compute_realized_gearing_pct(senior_debt, total_capex)`
read from `financing.fixed_debt_keur` which is 0 for Generic Solar /
Wind (post-S1-C factory-direct = resolver = `fixed_debt_keur=0`).
Result: Senior Debt card showed the actual runtime sculpted value
(e.g. 22,500 kEUR for Generic Solar), but Realized Gearing card
showed "—" because the function returned None.

**Fix** (`app/ui/project_context.py`):
- Added optional `runtime_senior_debt_keur` parameter to
  `_compute_realized_gearing_pct`.
- When `senior_debt_keur` is None or 0, the function falls back to
  `runtime_senior_debt_keur` (the runtime's DSCR-sculpt result).
- For TUHO and Oborovo the input value equals the runtime value
  bit-identically, so behaviour is unchanged.
- Negative runtime values are still rejected.

### TASK B — Scenario Switch Runtime Safety

**Problem**: `select_scenario()` updated `active_scenario_id` but
**not** the cached `last_runtime_snapshot`, `last_runtime_summary`,
or `last_runtime_origin`. Result: a user could select Scenario B
without running it, then `POST /download` would export Scenario A's
values (post-PILOT-HOTFIX-3 reads from `last_runtime_snapshot`).

**Fix** (`app/persistence/scenarios_repository.py`):
- `select_scenario()` now performs a direct DB UPDATE that clears:
  - `last_runtime_snapshot_json = '{}'`
  - `last_runtime_summary_json = '{}'`
  - `last_runtime_snapshot_id = NULL`
  - `last_runtime_origin = NULL`
  - `last_runtime_scenario_id = <new scenario id>`
- A subsequent `POST /download` (post-PILOT-HOTFIX-3) returns HTTP
  400 with the existing friendly message "Run the model before
  exporting."
- The existing merge semantics in `save_workspace_state` were not
  usable here because they preserve previous values when a None
  argument is passed; the direct UPDATE bypasses the merge.
- `saved_snapshot` is preserved (form state is project-level, not
  scenario-level).
- `replay_metadata` is updated with `p1_ux_fix_1: cleared_runtime_evidence`.

### TASK C — Dashboard Empty State Hint

**Problem**: When all KPI cards are "—" (e.g. after a scenario select
cleared runtime evidence), there was no inline hint. Only the
P2-FIX-4 "No run yet" CTA existed, and that only fires when there
is no runtime snapshot at all.

**Fix** (`app/templates/partials/_dashboard.html` +
`static/styles.css`):
- Added `dashboard-empty-hint` block that renders between the KPI
  grid and the charts.
- Only renders when `runtime_summary.last_runtime_snapshot_id`
  exists (i.e. there IS a runtime snapshot but the KPI cards cannot
  be populated).
- Shows: "Run the model to see KPIs here." plus optional
  `Scenario <id> is selected but has not been run yet.` if
  `active_scenario_id` is set.
- Distinct from the P2-FIX-4 CTA — both can render briefly during
  a save+run cycle.

### TASK D — Working Copy Indicator

**Problem**: User-created projects that were copied from a reference
template (TUHO / Oborovo / Generic) looked identical to a project
created from scratch. Users had no at-a-glance signal that they
were editing a copy.

**Fix** (`app/templates/partials/project_selector.html` +
`static/styles.css`):
- Added `ps-ap-origin--wc` "Working Copy" badge that renders next
  to the existing "My project" pill.
- Only renders when `project_origin == 'user_created'` AND
  `source_project_template` (or `template_source`) matches one of
  `{tuho, oborovo, generic_solar, generic_wind}`.
- Has a `data-p1uxfix1-component="working-copy-badge"` attribute
  for automated test verification.
- Tooltip shows the source template name (e.g. "Editable copy of
  the TUHO reference template").

## Files Changed

| Status | File | Change |
|---|---|---|
| M | `app/ui/project_context.py` | +22 / -10 (realized gearing runtime fallback) |
| M | `app/persistence/scenarios_repository.py` | +52 / -22 (select_scenario direct UPDATE) |
| M | `app/templates/partials/_dashboard.html` | +26 / -0 (empty hint block) |
| M | `app/templates/partials/project_selector.html` | +18 / -0 (WC badge) |
| M | `static/styles.css` | +31 / -0 (WC badge + empty hint CSS) |
| M | `tests/test_phase_m1_scenario_matrix.py` | +12 / -0 (file-scope cross-arc allowlist) |
| M | `tests/test_phase_pr1_form_timing_fields.py` | +18 / -0 (file-scope cross-arc allowlist) |
| M | `tests/test_phase_p1b_driver_status_badges.py` | +8 / -0 (file-scope cross-arc allowlist) |
| M | `tests/test_phase_pr2_realized_gearing.py` | +13 / -0 (file-scope cross-arc allowlist + file-scope set) |
| A | `tests/test_phase_p1_ux_fix_1_pilot_polish.py` | new test file, 22 tests |
| A | `docs/phase_p1_ux_fix_1_pilot_polish.md` | this file |
| A | `reports/phase_p1_ux_fix_1_pilot_polish.md` | walkthrough report |

## Constraints Honoured

- No `waterfall_core.py` change (MD5 unchanged)
- No `project_factories.py` change (MD5 unchanged)
- No `input_adapter.py` change
- No `db.py` schema change
- No `repository.py` change
- No `run_service.py` / `download_service.py` change
- No `ui_runner.py` change
- No `app.js` change
- No R99/R102/G20
- No construction-period changes
- No tax/sponsor/IDC changes
- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` ancestor preserved
- TUHO debt 43,359 kEUR + Oborovo debt 42,852.27 kEUR bit-identical
- Cross-arc file-scope guards (M1, PR1, PR2, P1B) extended to
  acknowledge P1-UX-FIX-1's intentional `scenarios_repository.py`
  touch.

## Tests

22 new P1-UX-FIX-1 tests pass:

- `TestTaskARealizedGearingForGeneric` (6 tests) — input-only
  backward-compat, zero/None fallback to runtime, None
  rejection, negative rejection, both-None returns None
- `TestTaskBScenarioSwitchRuntimeSafety` (2 tests) — select_scenario
  clears runtime evidence; invalid scenario_id returns False
- `TestTaskCDashboardEmptyStateHint` (4 tests) — hint renders,
  wrapped in runtime snapshot guard, P2-FIX-4 CTA preserved,
  CSS defined
- `TestTaskDWorkingCopyIndicator` (4 tests) — badge present,
  only for user_created + reference template sources, CSS defined
- `TestConstraintsPreserved` (5 tests) — rc1, Engine MD5, Factory
  MD5, file-scope allowlist, no forbidden files
- `TestBackwardCompat` (1 test) — PR2 two-arg call signature still
  works

## Stop-After-Report Contract

DRAFT. Do NOT mark ready, do NOT merge before review.
