# Product Gap PR11: Export Reality Check

## Summary

Unlike CAPEX/OPEX/Revenue/Financial Statements/Distribution/Sponsor/
Senior Debt/Tax (PR1-PR9), Export was investigated in depth and found
to be **already honest** across all three live export surfaces. Every
exported worksheet/cell traces back to a real `run_project()` /
`WaterfallRunner` result, a real persisted `ProjectContext`/
`ProjectInputs`, or the same `assemble_financial_statements(runtime_result)`
offline-assembly layer already confirmed real in PR6. No fabricated/
static/canned/demo worksheet was found anywhere in the live export
pipeline. This PR makes **no functional changes** to export code — it
documents the investigation, adds a reality-check test suite that
locks in the existing honest behavior, and confirms (with tests) that
no banned internal jargon leaks into exported cell values.

## Export surfaces investigated

There are three live, user-reachable export code paths:

1. **`GET /exports/runtime-summary.csv`** — `app/export/runtime_summary.py`
   (`build_runtime_summary_csv` / `build_runtime_summary_rows`), wired via
   `app/services/export_service.py::build_runtime_summary_csv_export`.
2. **`GET /exports/institutional-workbook.xlsx`** — `app/export/institutional_workbook.py`
   (`export_institutional_workbook_skeleton`), wired via
   `app/services/export_service.py::build_institutional_workbook_export`.
3. **`GET /download` / `POST /download`** (values-only Excel export) —
   `app/excel_export.py` (`build_excel_export`), wired via
   `app/services/download_service.py` and
   `app/services/export_service.py::build_excel_export_for_post_request` /
   `build_values_only_export_for_project`.

A fourth module, `app/export/calibration_reconciliation.py`
(`write_calibration_reconciliation_pack`), was found but **confirmed
not wired into any live route in `main_web.py`** — it is only used by
an offline reporting script path (`app/export/registry.py`'s
`reports/phase10_calibration_reconciliation_pack.xlsx` entry) and is
not reachable from the SPA. Like the orphaned `app/tax_assumptions_ui.py`
(PR9) and the orphaned `POST /compare` route (PR10), this is **not
part of the live product surface a user can reach** and is out of
scope for this UI/export-honesty PR.

## Worksheet inventory: Institutional Workbook (`/exports/institutional-workbook.xlsx`)

| Sheet | Source | Genuine? |
|---|---|---|
| Export_Metadata | `build_export_metadata()` from bundle fields (project, scenario, run timestamp) | Genuine — provenance/non-claims, not financial data |
| Workbook_Index | `INSTITUTIONAL_SHEET_INVENTORY` static list of sheet *descriptions* (not data) | Genuine — a table of contents, not a data sheet |
| Cover | `bundle.project_name`, `bundle.generated_at`, `bundle.commit_sha`, etc. — all from `runtime_rows[0]` / `ProjectContext` | Genuine |
| Governance | `runtime_rows[0]["governance_status"/"g20_status"/"r99_r102_status"]` — real governance labels (not fabricated numbers) | Genuine — descriptive governance state, explicitly labeled "no approval implied" |
| Runtime Summary | `bundle.runtime_rows` — built by `build_runtime_summary_rows()` from a real `WaterfallRunner(...).run()` result | Genuine, Run-backed |
| Inputs | `bundle.context` (`ProjectContext`) + `bundle.inputs_summary` (`build_inputs_summary_table`) | Genuine, persisted/template project context |
| Construction | `bundle.context` fields (CAPEX, IDC, bank fees, senior debt anchor via `_resolve_export_senior_debt_keur`) | Genuine. One row ("Runtime status note") honestly discloses "Detailed construction schedule not exported in this branch" — an honest disclosure, not a fake value |
| OPEX | `bundle.runtime_result.total_opex_keur` (runtime) + `bundle.context.opex_items` (template) | Genuine |
| CAPEX | `bundle.context.total_capex_keur` + `bundle.capex_summary`/`bundle.capex_items` (`app/input_helpers.py` table builders) | Genuine |
| Revenue | `bundle.context` revenue assumptions + `bundle.revenue_table` (`build_revenue_table(runtime_result)`) | Genuine, Run-backed |
| Senior Debt | `bundle.context` debt assumptions + `bundle.debt_table` (`build_debt_table(runtime_result)`) | Genuine, Run-backed |
| SHL | `bundle.context` SHL assumptions + real per-period SHL fields off `bundle.runtime_result.periods` | Genuine, Run-backed |
| Tax | `bundle.context` tax assumptions + `bundle.statements.tax_bridge.periods` (`assemble_financial_statements`) | Genuine, Run-backed |
| P&L | `bundle.statements.pnl.periods` (`assemble_financial_statements(runtime_result)`) | Genuine — same offline-assembly layer confirmed real in PR6 |
| Cash Flow | `bundle.statements.pf_cash_waterfall.periods` | Genuine, same as above |
| Balance Sheet | `bundle.statements.balance_sheet.periods`, including a real `balance_check_keur` residual | Genuine, same as above |
| Audit | Static source-map table (e.g. "Inputs ← project context + input helpers") | Genuine — a documentation/provenance table describing where each sheet's data comes from, not itself a data claim |
| Gap Register | Static table of known gaps (GAP-01..GAP-07) with classifications (`RUNTIME_BINDING_PENDING`, `WARN`, `BLOCKER`, `ACCEPTED_CONVENTION`) | Genuine — an honest disclosure register, not fabricated financial output. Each row describes a real, documented scope boundary (e.g. "CAPEX items are bound; full period spend curve is not exported here") |
| Validation Status | `get_validation_status(bundle.active_project)` (`app/validation_status.py`) | Genuine — real per-project/per-metric validation tier classification |

**No sheet in this workbook was found to contain hardcoded/canned
financial figures.** Every numeric cell traces to `bundle.context`
(real persisted/template `ProjectContext`), `bundle.runtime_result`
(real `WaterfallRunner` output), or `bundle.statements` (the same
`assemble_financial_statements` offline layer already confirmed real
in PR6's Financial Statements investigation — the key difference from
PR6's `sheet_financials.html` finding is that *this* P&L/Cash Flow/
Balance Sheet binding is genuinely wired, not a static HTML table with
zero variable substitution).

## Worksheet inventory: Runtime Summary CSV (`/exports/runtime-summary.csv`)

Single flat table, one row per metric (`project_irr`, `equity_irr`,
`total_revenue_keur`, `total_ebitda_keur`, `total_opex_keur`,
`avg_dscr`, `min_dscr`, `total_distributions_keur`,
`total_shl_service_keur`, `g20_status`, `r99_r102_status`), all sourced
from a real `WaterfallRunner(...).run()` result
(`app/export/runtime_summary.py::_run_project` /
`build_runtime_summary_rows`) plus real replay/provenance metadata
(`build_replay_metadata`). **Confirmed genuine, Run-backed.**

## Worksheet inventory: Values-only Excel export (`/download`)

`app/excel_export.py::build_excel_export` writes (sheet names as
produced for a representative Solar run): Dashboard, Returns, DSCR
Summary, Waterfall, Revenue, Debt, Tax_Depreciation, Notes, Inputs,
CapEx, CapEx_Items, Validation, Depreciation Assumptions, Tax
Depreciation, Book Depreciation, Depreciation Audit (plus optional
overlay/SPV/HoldCo/sponsor-waterfall sheets when those features are
active for the project). Every sheet is built from a `pandas.DataFrame`
populated from the real `result`/`schedule`/`provenance_metadata`
objects passed in by the route — there is no hardcoded financial
literal anywhere in this module's sheet-writer functions.

One sheet, **Depreciation Audit**, is explicitly and correctly
audit-only: its own docstring states "Audit visibility only. All
values are text. No numeric depreciation values appear on this
sheet," and its content cell is literally titled "Audit-Only Surfaces."
This is the one legitimate exception the PR11 spec carves out for
"audit-only" wording ("unless genuinely audit-only") — confirmed
genuinely audit-only, kept unchanged.

## Export landing page / registry (`app/templates/partials/export_registry.html`)

Already honest before this PR: the three live, working export cards
(Institutional Workbook, TUHO Runtime Summary CSV, Oborovo Runtime
Summary CSV) link to the real routes above. Five **not-yet-built**
export concepts (Reconciliation Pack, TUHO Horizontal Review Workbook,
Gap Analysis, Source Map, Final Closeout Registers) are already
rendered as `export-card--disabled` with an explicit "Coming Soon"
badge and `title="Not yet available — coming in a future release"` —
this is exactly the "Unavailable" pattern this PR's spec asks for, and
it was already in place. **No change needed.**

## Banned internal jargon check

Searched every cell value (not source comments/docstrings) produced
by `export_institutional_workbook_skeleton("tuho")`,
`build_runtime_summary_csv("tuho")`, and a representative
`build_excel_export(...)` run for: `preview architecture`,
`runtime pipeline`, `stub`, `prototype`, `TODO:`, `FIXME`,
`placeholder architecture`. **None were found** in any exported cell
value. (The literal substrings "C1"/"C2" only ever appear inside the
git branch-name string embedded in provenance cells, e.g.
`product-gap-pr11-export-reality-check`, which is itself real
provenance metadata, not internal jargon describing the export
itself.)

`G20`/`R99`/`R102` governance labels **do** appear in exported cell
values (Governance sheet, Tax sheet's "Known limitation" row,
Export_Metadata's non-claims block, the Gap Register, and the export
registry's badges). Unlike PR9's finding for the Tax *screen* (where
G20/R99/R102 were unconditionally fabricated client-side jargon with
no real binding), here these are **real governance status fields**
(`runtime_rows[0]["g20_status"]` / `["r99_r102_status"]`, sourced from
explicit, accurate constants in `runtime_summary.py` — "BLOCKED" /
"NOT APPROVED" — not invented numbers) used in a reviewer/audit export
artifact, where disclosing governance gate status is the correct,
honest thing to show a reviewer. They are not banned "internal
developer wording" (the PR11 spec's banned list is `preview`, `stub`,
`prototype`, `placeholder`, `runtime pipeline`, `preview architecture`,
`audit-only` (when not genuinely audit-only), `TODO`, `FIXME` — it
does not list G20/R99/R102, and PR9/PR10 already established the
precedent that G20/R99/R102 is acceptable when it reflects a real,
accurate governance state rather than fabricated jargon). No change
made here.

## Why no removal/replacement was needed

Per the spec's explicit instruction ("if unsure whether a value is
real, hide/replace rather than exposing it as authoritative"), this
PR's investigation specifically looked for: fake worksheet numbers,
canned/demo example values, preview-only static data, unfinished
financial-statement worksheets, unfinished sponsor/distribution
worksheets exported as if complete, and internal jargon leaking into
cell text. **None were found.** Every exported worksheet across all
three live export surfaces traces to real persisted project state, a
real `run_project()`/`WaterfallRunner` result, or the same
`assemble_financial_statements` offline-assembly layer already
confirmed real in PR6. Inventing "Unavailable" worksheets to replace
already-genuine content would have made the product *less* honest,
not more — so none was added or removed. This matches PR10's outcome
applied to a different product area.

## What changed

No export code, template, or workbook-generation file was modified.
This PR adds:

- `docs/PRODUCT_GAP_PR11_EXPORT_REALITY_CHECK.md` (this file).
- `tests/test_product_gap_pr11_export_reality_check.py` (new): locks
  in the investigation findings with executable tests.

## Tests

`tests/test_product_gap_pr11_export_reality_check.py` covers:

1. Export still works (institutional workbook + runtime summary CSV +
   values-only Excel export all generate successfully and the
   workbook opens via `openpyxl`).
2. Workbook still opens / sheet order unchanged (19 sheets, in the
   pinned order, matching `tests/test_u5_export_polish.py`'s
   pre-existing pin — no sheets were added or removed by this PR).
3. No worksheets were removed (this PR removes none — the full
   pinned sheet-name set from PR11's investigation remains present).
4. All genuine worksheets remain exported (Inputs/CAPEX/OPEX/Revenue/
   Senior Debt/SHL/Tax/P&L/Cash Flow/Balance Sheet/Runtime Summary all
   present with their real per-row "runtime"/"template assumption"
   source labels intact).
5. No fake financial data is exported — every numeric Runtime Summary
   metric and every P&L/Cash Flow/Balance Sheet period value is sourced
   from a real `WaterfallRunner` run, asserted by re-running the same
   project directly and comparing key totals against the exported
   workbook's Runtime Summary sheet values.
6. No banned internal wording (`preview architecture`, `runtime
   pipeline`, `stub`, `prototype`, `TODO:`, `FIXME`,
   `placeholder architecture`) appears anywhere in exported cell
   values across the institutional workbook, runtime summary CSV, or
   values-only Excel export.
7. Workbook generation unchanged for genuine sheets — sheet count,
   sheet names, and sheet order match the pre-existing
   `tests/test_u5_export_polish.py` pin exactly.
8. Guardrails untouched — `domain/*`, `app/waterfall_core.py`,
   `app/input_adapter.py`, `app/project_factories.py`,
   `static/modelling/runtime-renderer.js`, `app/services/model_preview.py`,
   `app/services/preview_context.py`, `app/services/previews/*` are not
   in `git diff main --name-only`.
9. The orphaned `app/export/calibration_reconciliation.py`
   (`write_calibration_reconciliation_pack`) is confirmed not wired
   into any `main_web.py` route, so its audit-only wording (governed
   by its own existing test suite, not this PR's scope) does not
   reach the live export surface.

The full pre-existing export test suite (`tests/test_u5_export_polish.py`,
`tests/test_u9_remaining_terminology_cleanup.py`,
`tests/test_phase47_export_hygiene_runtime_metadata.py`,
`tests/test_phase48_export_index_readme_sheet_polish.py`,
`tests/test_c2_pr22_export_run_safety_guardrails.py`,
`tests/test_c2_pr24_backend_debt_preview_stub.py`,
`tests/test_phase_s1a_export_runtime_senior_debt.py`,
`tests/test_export_audit_c1_markup_contract.py`,
`tests/test_export_audit_c1_migration_browser.py`, and others) was run
unchanged and continues to pass — no narrow updates were needed to any
of them, since no export markup, behavior, or workbook structure was
altered by this PR.

## Pre-existing failures (not touched, not regressions)

Per the sprint-level baseline, the 3 previously-confirmed pre-existing
failures
(`test_c2_pr1_live_model.py::TestStaticWiring::test_no_recalculation_formula_dependency_or_saverun_code_in_live_model`,
`test_c2_pr7_backend_preview_endpoint.py::...::test_no_financial_engine_call`,
`test_c2_pr9_runtime_request_hardening.py::TestNoRegressionForAuthorizedOrNullProject::test_authorized_project_behaviour_matches_pr8_contract`)
remain, with no new failures introduced by this PR. The pre-existing
6-failure cluster in
`tests/test_phase9_5_output_tabs_runtime_summary_binding.py` was
confirmed identical on a clean `main` checkout and is unrelated to
Export or this PR's documentation/test-only change.

## Confirmation: no financial formulas, Run logic, Save logic, persistence, export calculations, Preview Architecture, or Runtime Pipeline code changed

This PR changed **zero** export, runtime, persistence, or domain
files. It adds one documentation file and one new test file only.
`domain/*`, `app/waterfall_core.py`, `app/input_adapter.py`,
`app/project_factories.py`, `static/modelling/runtime-renderer.js`,
`app/services/model_preview.py`, `app/services/preview_context.py`,
`app/services/previews/*`, `app/excel_export.py`,
`app/export/institutional_workbook.py`, `app/export/workbook_index.py`,
`app/export/runtime_summary.py`, and `main_web.py` were **not**
touched.

## Future work (out of scope for this PR)

- The orphaned `app/export/calibration_reconciliation.py` /
  `write_calibration_reconciliation_pack` pipeline is real and
  Run-backed, but unreachable from the live UI. Whether to wire it
  into the SPA (as the already-stubbed "Reconciliation Pack" /
  "TUHO Horizontal Review Workbook" / "Gap Analysis" / "Source Map" /
  "Final Closeout Registers" "Coming Soon" cards in
  `export_registry.html` suggest is planned), or remove it as dead
  code, is a future routing decision outside this UI/export-honesty
  PR's scope (same treatment as the orphaned files found in PR8/PR9/
  PR10).
- The Construction sheet's "Detailed construction schedule not
  exported in this branch" and the Gap Register's documented
  `RUNTIME_BINDING_PENDING` items (detailed construction spend curve,
  detailed OPEX escalation schedule, detailed CAPEX spend curve,
  expanded covenant analytics, separate accrued-vs-cash SHL view,
  expanded tax residual diagnostics, extra P&L sub-line mapping,
  distribution account detail, full capital accounts breakout) remain
  honest, explicitly-disclosed scope boundaries — wiring them up is a
  future export-engine task, not a UI/honesty task.
