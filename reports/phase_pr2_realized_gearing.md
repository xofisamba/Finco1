# Phase PR2 — Realized Gearing KPI — Report

## Status

- **Type:** Read-only derived output KPI
  + Scenario Matrix row + relabelled
  input row.
- **Branch:** `post-m1-realized-gearing-kpi`
- **Base:** main @ `33564cce` (post-PR1
  merge, PR #606)
- **PR:** DRAFT only. Do NOT mark ready.
  Do NOT merge. Awaiting user review.

## Summary

Phase PR2 surfaces the **realized
gearing** as a read-only output KPI, so
users can see the actual gearing ratio
the DSCR-sculpt produced, distinct from
the indicative gearing input.

The PR2 fix is:

1. A new `realized_gearing_pct: float |
   None` field on the `ProjectContext`
   dataclass (default `None`).
2. A new helper
   `_compute_realized_gearing_pct(senior_debt_keur, total_capex_keur)`
   that returns the percentage or `None`
   for uninitialised inputs.
3. Population in both
   `_build_context_from_project_inputs`
   and `_build_user_snapshot_context`
   using values the runtime has already
   produced (senior_debt_keur and
   total_capex_keur).
4. A new `KPI_ROWS` entry in
   `app/ui/scenario_matrix.py`:
   `MatrixRow("Realized Gearing",
   ROW_KIND_KPI, "realized_gearing_pct",
   _fmt_pct)`.
5. A new KPI row in the Scenario Matrix
   template with a "derived" badge and
   the formula reminder tooltip.
6. A relabelled input row "Indicative
   Gearing" → "Indicative Gearing
   (input)" with an "input" badge and a
   tooltip explaining that the debt is
   sized by DSCR sculpt and that the
   "Realized Gearing" output below shows
   the actual senior_debt / total_CAPEX
   ratio.

The realized gearing is a **read-only
reformulation** of values the runtime
already produces. PR2 does NOT change
debt sizing, DSCR sculpt semantics,
financial formulas, factory paths,
tax, depreciation, IDC, construction,
C10, R-PAR, R99, R102, G20, persistence
schema, app.js, or any forbidden path.

## Files in PR2 (7)

### Production code (3)

- `app/ui/project_context.py` (MODIFIED)
  - `realized_gearing_pct` field on
    `ProjectContext`
  - `_compute_realized_gearing_pct`
    helper
  - populated in both
    `_build_context_from_project_inputs`
    and
    `_build_user_snapshot_context`

- `app/ui/scenario_matrix.py` (MODIFIED)
  - new `KPI_ROWS` entry for
    `realized_gearing_pct`

- `app/templates/partials/scenario_matrix.html`
  (MODIFIED)
  - new KPI row "Realized Gearing" with
    "derived" badge
  - relabelled input row "Indicative
    Gearing (input)" with "input" badge

### Tests (3 — 1 new + 2 cross-arc patches)

- `tests/test_phase_pr2_realized_gearing.py`
  (NEW) — 9 test classes, 27 tests
- `tests/test_phase_pr1_form_timing_fields.py`
  (MODIFIED) — cross-arc test patch
  (PR1 file-scope forward-fix)
- `tests/test_phase_m1_scenario_matrix.py`
  (MODIFIED) — cross-arc test patch
  (M1 file-scope allowlist extension)

### Docs (2)

- `docs/phase_pr2_realized_gearing.md`
  (NEW)
- `reports/phase_pr2_realized_gearing.md`
  (this file)

## Test results (final, PR2)

- **27 / 27 PR2 tests PASS**
- **448 / 448** S1 + S2 + S3 + M1 + PR1
  + P1-B + P1-A + Phase 51F parity
  guardrails + PR2 + route smoke
  (preserved)
- **51 / 51** route smoke (was 51/51
  pre-PR2, preserved)
- **21 / 21** Phase 51F parity
  guardrails PASS (no model change)

## Pre-merge audit (all pinned by tests)

### What changed in production code

- `app/ui/project_context.py` — read-only
  derived KPI field + helper + population
  in 2 builder functions.
- `app/ui/scenario_matrix.py` — new
  `KPI_ROWS` entry.
- `app/templates/partials/scenario_matrix.html`
  — new KPI row + relabelled input row.

No runtime path changes. No formula
changes. No model changes. No factory
changes. No persistence changes. No
service-code changes. No `app.js`
changes. No forbidden-path changes.

### What did NOT change (forbidden paths, pinned by tests)

- `app/project_factories.py` — UNCHANGED
  (factory paths preserved bit-exact,
  SHA verified)
- `app/waterfall_core.py` — UNCHANGED
  (model SHA verified)
- `app/waterfall_runner.py` —
  UNCHANGED
- `main_web.py` — UNCHANGED
- `main_api.py` — UNCHANGED
- `app/persistence/` — UNCHANGED
- `app/services/` — UNCHANGED
- `app/excel_export.py` — UNCHANGED
- `static/app.js` — UNCHANGED

### Realized gearing helper purity

`_compute_realized_gearing_pct` does
NOT import from any forbidden module
(`app.project_factories`,
`app.waterfall_core`,
`app.waterfall_runner`, `app.services`,
`app.excel_export`, `main_web`,
`main_api`). It is a pure function that
operates on the two scalar inputs.

## Test counts (final, PR2)

- 27 / 27 PR2 tests PASS
- 448 / 448 S1 + S2 + S3 + M1 + PR1 +
  P1-B + P1-A + Phase 51F parity +
  PR2 + route smoke
- 51 / 51 route smoke
- 21 / 21 Phase 51F parity
- 0 failed
- rc1 SHA preserved

## Hard no-go (preserved, all pinned by tests)

- No debt sizing change
- No DSCR sculpt semantics change
- No financial formula change
- No factory path change
- No model / runtime change
- No tax / depreciation / IDC change
- No construction / C10 / R-PAR change
- No `manual_gearing` debt sizing method
- No `min(gearing cap, sculpt)` blend
- No senior IDC
- No persistence schema migration
- No R99 / R102 / G20 promotion
- No `static/app.js` change
- No `main_web.py` change
- No `main_api.py` change
- No `app/services/` change
- No `app/persistence/` change
- No `app/excel_export.py` change
- No Tailwind / Alpine / React / Vue /
  Svelte
- No JS calc
- `use_construction_schedule_engine`
  remains False
- rc1 SHA
  `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  preserved

## Pre-existing infra rot (NOT PR2 regressions)

Same list as S1 / S2 / S3 / M1 / PR1:

- `tests/test_phase24g3_capex_sheet_readability.py`
  — f-string + backslash SyntaxError
- `tests/test_phase9_tuho_full_semester_horizontal_parity_workbook.py::test_no_runtime_files_changed`
  — pre-S1 allowed-file-list
- `tests/test_senior_dscr_sculpting_basis_bridge.py`
  / `tests/test_senior_rate_schedule_project_opt_in.py`
  — numeric drift pre-existing
- `tests/test_phase23d_prep_tuho_fixture_backed_frozen_senior_ds.py::test_oborovo_frozen_fixture_still_unavailable_and_off`
  — Oborovo has
  `use_frozen_excel_senior_debt_schedule=True`
- `tests/test_oborovo_parity.py::TestBaselineInputs::test_shl_amount`
  / `TestBaselineFinancing::test_total_equity_shl` —
  pre-existing numeric drift
- `tests/test_auth_lite.py` /
  `tests/test_ui2_6_run_source_indicator.py` —
  collection error, missing
  `itsdangerous` / `fastapi`

## Roadmap (post-PR2)

1. **PR2** (this PR) — Realized gearing
   KPI (read-only derived output)
2. **PR3** — Taxonomy / brief alignment
   (next, awaiting user go-ahead)

`manual_gearing` is **not** on this
roadmap.

DO NOT START: PR3 until PR2 report is
delivered and reviewed. DO NOT START:
C10, construction runtime promotion,
R-PAR, debt formula changes, tax, IDC,
senior IDC, depreciation, schema
migration, manual_gearing, Tailwind/
Alpine, factory path changes, R99 /
R102 / G20 promotion.

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do
NOT merge. Awaiting user review and
explicit go-ahead before PR2 lands on
main.
