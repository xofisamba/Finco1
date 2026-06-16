# IRR-ANOMALY-1-FIX: Align Matrix Badge with Dashboard

## Problem

During a pilot walkthrough, a user reported that a Downside scenario
(tariff override 60 → 55 EUR/MWh) showed a HIGHER IRR than the Base
case in the Scenario Matrix run badge.

| Source | Base | Downside (tariff 55) | Expected |
|---|---|---|---|
| Matrix badge "IRR" | 7.33% | 7.85% | Downside < Base ❌ |
| Matrix badge "DSCR" | 1.51x | 1.343x | (depends) |

## Root cause

The M4 matrix run route (`POST /matrix/scenario/{id}/run` in
`main_web.py`) passed `equity_irr` and `min_dscr` to the
`_matrix_run_result.html` template. The Dashboard run summary uses
`project_irr` and `avg_dscr`. The two surfaces displayed different
metrics under the same labels.

For a TUHO tariff haircut (60 → 55), the engine produces:

| Metric | Base (60) | Downside (55) |
|---|---|---|
| `project_irr` (real) | **7.33%** | **6.78%** |
| `equity_irr` | 9.04% | 7.85% |
| `actual_avg_dscr` | 1.5089 | 1.5193 |
| `actual_min_dscr` | 1.3430 | 1.3430 |

The matrix badge displayed `equity_irr` (7.85%) under the generic
"IRR" label, creating the impression that lowering tariff increased
IRR. The `equity_irr` lands at 7.85% by coincidence — close to
the Base `project_irr` of 7.33% — which made the comparison
misleading.

The engine output is correct. The display was wrong.

## Fix

1. `main_web.py` M4 route (`m4_run_scenario`):
   - Read `project_irr` and `avg_dscr` from `kpis` (instead of
     `equity_irr` and `min_dscr`).
   - Format as `X.XX%` (project_irr) and `X.XXx` (avg_dscr) with
     2 decimal places to match Dashboard.
   - Pass `project_irr` and `avg_dscr` in the template context
     (both success and error paths).

2. `app/templates/partials/_matrix_run_result.html`:
   - Render `IRR {{ project_irr }}` (was `equity_irr`).
   - Render `DSCR {{ avg_dscr }}` (was `min_dscr`).
   - Update header comment to document the new mapping.

## Why this is the right fix

- The Dashboard run summary already uses `project_irr` and
  `avg_dscr` as the top-level metrics (see
  `app/ui/runtime_summary.py:300-303`).
- The Scenario Matrix KPIs (in `scenario_matrix.html` and
  `dashboard.py`) also use `project_irr` and `avg_dscr`.
- The M4 matrix run badge was the lone holdout using
  `equity_irr` / `min_dscr`. Aligning it with the rest of the UI
  eliminates the inconsistency.

The alternative (labeling as "Equity IRR" and "Min DSCR") was
considered but rejected because:
- "Equity IRR" is not shown anywhere else in the pilot UI
- "Min DSCR" is shown but is the sculpt target, not the
  user-facing KPI

## Constraints (preserved, all pinned by tests)

- No `waterfall_core.py` changes (MD5 unchanged:
  `6bf49f33efc989736c17cea0cb9b7723`).
- No `project_factories.py` changes.
- No persistence schema migration.
- No scenario override / merge / persistence changes.
- No engine calculation changes.
- No tax / debt / depreciation / IDC changes.
- No R99 / R102 / G20 changes.
- No `static/app.js` changes.
- No new dependencies.
- `rc1` SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` preserved.

## Test coverage

13 new tests in `tests/test_phase_irr_anomaly_1_fix.py`:

1. **TestEngineParity** (2): engine MD5 unchanged; project_factories
   still present.
2. **TestTemplateLabels** (3): template uses `project_irr` /
   `avg_dscr`; no `equity_irr` / `min_dscr` interpolation.
3. **TestM4RouteKpiExtraction** (2): route reads `project_irr` /
   `avg_dscr`; uses 2-decimal formatting.
4. **TestMatrixBadgeEndToEnd** (3): HTTP round-trip — badge shows
   `data-m4-kpi="project_irr"` and `data-m4-kpi="avg_dscr"`; values
   are 2-decimal format.
5. **TestEngineOutputInvariants** (2): `project_irr` drops with
   tariff haircut (engine invariant); `avg_dscr >= min_dscr`
   (mathematical invariant).
6. **TestFileScope** (1): no forbidden files changed
   (waterfall_core, project_factories, persistence, etc.).

## Validation

Local pytest:
- 13/13 IRR-ANOMALY-1-FIX tests PASS
- 97/97 cross-arc regression tests PASS (12 skipped, 0 failed)
- 36/36 Phase 51F parity guardrails + Phase 33 version history PASS

Engine parity:
- `waterfall_core.py` MD5: `6bf49f33efc989736c17cea0cb9b7723` (unchanged)
- TUHO baseline: `project_irr=0.073309`, `actual_avg_dscr=1.508914`,
  `actual_min_dscr=1.342992` (matches SCENARIO-2 baseline)

## Files changed (8, +548 / -16)

- `main_web.py` (M4 route KPI extraction)
- `app/templates/partials/_matrix_run_result.html` (label swap)
- `tests/test_phase_irr_anomaly_1_fix.py` (NEW, 13 tests)
- 5 cross-arc test allowlist patches
