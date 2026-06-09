# Phase 25B-3 — "What Changed" Delta Indicator

## Scope classification (honest)

This phase is **UI + minimal metadata-persistence rotation**, not UI-only and
not read-only in the strict sense. The UI panel itself is read-only (it never
mutates input), but enabling it required a small behaviour change in
`app/persistence/repository.py` (specifically
`update_scenario_last_run_summary`): the function now rotates the
`last_run_summary` being overwritten into `replay_metadata.previous_run_summary`
(and chains the older previous into `second_last_run_summary`).

This is **not** a schema migration: the columns are unchanged, the JSON shape
inside `replay_metadata` now carries two additional optional keys, and no
existing data is rewritten. Old scenarios that lack
`replay_metadata.previous_run_summary` simply show the no-previous state.

## Goal

After a finance user edits a Generic Solar / Generic Wind scenario and re-runs
it, show a small "What changed since previous run?" panel comparing the most
important KPIs between the current run and the previous run of the same
scenario.

## User Story

> As a user, after I edit and rerun a Generic scenario, I can see a small
> "What changed since previous run?" panel showing the most important KPI
> deltas.

## Scope

- **In scope**:
  - Generic exploratory path (`generic_solar`, `generic_wind`).
  - Compact panel near the scenario version history in the workspace.
  - **Minimal metadata rotation** in `update_scenario_last_run_summary`:
    - `replay_metadata.previous_run_summary` is set to the outgoing
      `last_run_summary` whenever a new run overwrites a non-empty existing
      summary.
    - `replay_metadata.second_last_run_summary` is set to the previous
      `previous_run_summary` (chain of length 2).
    - `replay_metadata.previous_run_at` records the previous run's
      `updated_at` ISO timestamp.
- **Out of scope (do not touch)**:
  - TUHO / Oborovo reference path
  - Construction / C10 / R-PAR
  - Senior IDC
  - Model formulas
  - Tax / debt / depreciation / IDC calculations
  - Persistence **schema** (no migration, no new columns)
  - Tailwind / Alpine / external CSS frameworks

## Design

### Helper module — `app/ui/what_changed.py`

Pure functions, no DB access, no I/O. Used by both the route handler (to
augment the summary card) and the partial (via Jinja2).

- `WHAT_CHANGED_METRICS` — ordered tuple of 10 metrics:
  1. `project_irr` (Project IRR, pct)
  2. `equity_irr` (Equity IRR, pct)
  3. `avg_dscr` (Avg DSCR, x)
  4. `min_dscr` (Min DSCR, x)
  5. `total_revenue_keur` (Revenue, keur)
  6. `total_opex_keur` (OPEX, keur)
  7. `total_ebitda_keur` (EBITDA, keur)
  8. `total_capex_keur` (CAPEX, keur)
  9. `total_distributions_keur` (Distributions, keur)
  10. `senior_debt_keur` (Senior Debt, keur)

- `compute_metric_delta(key, label, fmt, previous, current)` — returns a
  dict with display strings + state. States: `n_a`, `zero`, `positive`,
  `negative`.
- `compute_what_changed(previous, current)` — returns a list of 10 row
  dicts (one per metric).
- `has_any_comparable_delta(rows)` — boolean: any non-`n_a` state.
- `build_scenario_card_deltas(card)` — enriches a summary card dict
  in-place (returns a new dict) with `has_previous_run`, `panel_rows`,
  `is_user_project`, `template_source`.

### Display partial — `app/templates/partials/what_changed_panel.html`

Rendered inside `partials/scenario_version_history.html` per card, gated on
`card.is_user_project` (so factory projects are not affected).

States:
- `data-state="with-previous"` — table rendered with deltas
- `data-state="no-previous"` — "No previous run available" message
- `data-state="no-current"` — defensive (not normally hit)

Banners:
- EXPLORATORY (yellow) for `generic_solar` / `generic_wind`
- Descriptive (blue) for everything else

Row classes:
- `wc-row--positive` (green delta) — current > previous
- `wc-row--negative` (orange delta) — current < previous
- `wc-row--zero` (grey delta) — no change
- `wc-row--n_a` (faded) — missing data

### Wire-up — `main_web.py`

`_workspace_refresh_payload(user, project_record)` now enriches each
summary card with delta data (from `replay_metadata["previous_run_summary"]`)
and `is_user_project` / `template_source` flags.

`partials/scenario_version_history.html` includes `partials/what_changed_panel.html`
per card, using a `{% with %}` block to pass per-card context (Jinja2
`include` does NOT scope `card` from the surrounding `for` loop).

### CSS — `static/styles.css`

+162 lines, all additive. New `.wc-*` classes only. No `:root` selector
modifications. Phase 24G-2 invariant preserved: base `:root` count = 3.

### Persistence — `app/persistence/repository.py` (metadata rotation, read by the panel)

`update_scenario_last_run_summary()` now stamps the previous run summary
into `replay_metadata["previous_run_summary"]` before overwriting
`last_run_summary_json`. This is the only persistence call site affected.

**Behavioural contract** (proven by tests in
`tests/test_phase25b3_previous_run_persistence.py`):

| Run # | Before-write `last_run_summary` | After-write `replay_metadata.previous_run_summary` | After-write `replay_metadata.second_last_run_summary` |
|---|---|---|---|
| 1 (first run) | empty | absent | absent |
| 2 (second run) | run 1 summary | run 1 summary | absent |
| 3 (third run) | run 2 summary | run 2 summary | run 1 summary |
| 4+ (subsequent) | run N-1 summary | run N-1 summary | run N-2 summary |

Other `replay_metadata` keys are **preserved** across writes (the rotation
only adds three optional keys, never removes or overwrites other keys).
A scenario record with `replay_metadata = None` is tolerated: the rotation
code initialises a fresh dict.

The persistence behaviour for **factory projects (TUHO / Oborovo)** is
unchanged in observable ways: their scenarios also get a
`previous_run_summary` stamped, but the panel is gated on
`is_user_project`, so the panel does not render for them. The factory
runtime output is byte-identical to the pre-Phase-25B-3 path.

## Tests

- `tests/test_phase25b3_panel_helpers.py` — 30 tests, 5 classes
  - `TestWhatChangedMetricOrdering`
  - `TestComputeMetricDelta`
  - `TestComputeWhatChanged`
  - `TestHasAnyComparableDelta`
  - `TestBuildScenarioCardDeltas`
- `tests/test_phase25b3_panel_rendering.py` — 13 tests, 3 classes
  - `TestPanelEmptyState`
  - `TestPanelWithPreviousRun`
  - `TestPanelNegativeAndZeroStates`
- `tests/test_phase25b3_exploratory_banner.py` — 3 tests, 1 class
  - `TestExploratoryBanner`
- `tests/test_phase25b3_factory_safety.py` — 20 tests, 6 classes
  - `TestFactorySafety`
  - `TestVersionHistoryWiring`
  - `TestSafetyConstraints`
  - `TestRC1Untouched`
  - `TestCSSStyleGuard`
  - `TestDisplayHelperDoesNotWrite`
- `tests/test_phase25b3_previous_run_persistence.py` — 11 tests, 5 classes
  - `TestFirstRunNoPrevious` — first run stamps no previous_run_summary
  - `TestSecondRunStampsPrevious` — second run stamps run 1 into previous
  - `TestThirdRunChainsSecondLast` — third run chains run 1 into second_last
  - `TestReplayMetadataKeysPreserved` — non-rotation keys survive
  - `TestCorruptedReplayMetadataTolerated` — None / malformed handled
  - `TestFactoryPersistenceUnchanged` — factory run summary not corrupted

- `tests/test_phase25b3_no_regression.py` — 7 tests, 4 classes
  - `TestScenarioSaveLoadUnchanged`
  - `TestScenarioCompareUnchanged`
  - `TestMultiCompareUnchanged`
  - `TestExportDownloadUnchanged`

**Total: 84 new tests, all passing.**

## Safety constraints verified

- ✅ `use_construction_schedule_engine` — not flipped
- ✅ `wc-panel` / `wc-row--*` classes scoped, no global pollution
- ✅ No Tailwind / Alpine / inline `<script>` in partials
- ✅ No new financial formulas (helper only does subtraction + percentage)
- ✅ Helper is pure: no DB, no I/O, no time
- ✅ Factory projects (TUHO / Oborovo) are SAFE: panel is gated on
  `is_user_project`, factory card has `is_user_project=False`
- ✅ rc1 (run-and-compare 1-export) flow is untouched (compare helper is
  not imported by what_changed module)
- ✅ `replay_metadata` is never mutated by the display path
- ✅ `:root` block count remains 3 (base) + 2 (inside `@media`, pre-existing)
- ✅ Panel is hidden by default in factory sections; for user projects it
  is always present but shows the no-previous state when data is missing

## Deliverables

- `app/ui/what_changed.py` (6458 bytes, pure helpers)
- `app/templates/partials/what_changed_panel.html` (3694 bytes)
- `app/persistence/repository.py` — `update_scenario_last_run_summary` is
  the **only** persistence call site affected. It now rotates
  `last_run_summary` into `replay_metadata["previous_run_summary"]` (and
  chains the previous previous into `second_last_run_summary`) before
  overwriting. No new columns, no schema migration.
- `main_web.py` — `_workspace_refresh_payload` enriched to populate card
  delta data.
- `app/templates/partials/scenario_version_history.html` — added the
  `{% include %}` per card, gated on `is_user_project`, wrapped in a
  `{% with %}` block for per-card context.
- `static/styles.css` — +162 lines, all `.wc-*` classes, additive only.
- 6 new test files (84 tests: 66 UI/helper + 11 persistence rotation + 7 no-regression).
- 1 docs file (this file).
- 1 report file (`reports/phase25b3_what_changed_delta_indicator.json`).

## Stop point

Open DRAFT PR. Do not mark ready. Do not merge. Stop after report.
