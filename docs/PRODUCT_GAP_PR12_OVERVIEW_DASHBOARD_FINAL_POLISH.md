# Product Gap PR12: Overview / Dashboard Final Polish

## Summary

Unlike CAPEX/OPEX/Revenue/Financial Statements/Distribution/Sponsor/
Senior Debt/Tax (PR1–PR9), the Overview / Dashboard screen was
investigated in depth and found to be **already honest**. Every visible
card, KPI, banner, widget, and summary on the Dashboard traces back to
real Run-backed output (`last_runtime_summary` from `run_project()`),
real persisted project metadata (`ProjectContext`/`ProjectRecord`), or
correctly-labeled preview-only indicators that explicitly disclose
their non-authoritative status. No fabricated/static/canned KPI values,
no misleading pre-Run placeholders, no banned internal jargon, and no
duplicated KPI surfaces were found. This PR makes **no functional
changes** — it documents the investigation, adds a reality-check test
suite that locks in the existing honest behavior, and confirms (with
tests) that the Dashboard is already compliant with the Product Reality
Gap sprint's honesty standard.

## Dashboard Component Inventory

Every visible section of the Overview tab (`panel-overview` in
`app/templates/partials/workspace_shell.html`), the Dashboard v1
partial (`app/templates/partials/_dashboard.html`), and the OOB
post-Run refresh partial (`app/templates/partials/_dashboard_oob.html`)
was audited below.

### A. Generic Status Line
(`app/templates/partials/_generic_status_line.html`, included at top
of `panel-overview`)

| Component | Source | Genuine? |
|---|---|---|
| "Internal-use model — results are indicative." disclosure | `is_exploratory_project` context variable (real persisted project metadata from `project_origin == "user_created"` check) | Genuine — only renders for exploratory projects, gated on real project type. Not shown for factory/parity fixtures. |

### B. Help Pointer
(`workspace_shell.html`, panel-overview)

| Component | Source | Genuine? |
|---|---|---|
| "Need a tour? Open the Help tab…" | Static copy; link routes to `#help` tab via existing `hashchange → switchTab` JS handler | Genuine — navigation pointer, not a data claim. No financial value. |

### C. Runtime Preview Status Indicator (C2-PR8)
(`workspace_shell.html`, id=`overview-runtime-status`)

| Component | Source | Genuine? |
|---|---|---|
| "Runtime preview: Idle/Preview ready/Preview failed" label | Patched client-side by `static/modelling/runtime-renderer.js` after a real `POST /model/preview` round trip | Genuine — correctly labeled non-financial status indicator. Starts "Idle"; never shows a fabricated KPI. **Protected by guardrails — not touched.** |

### D. Operating Preview Panel (C2-PR21)
(`workspace_shell.html`, id=`operating-preview-panel`, 8 sub-indicators)

| Indicator | Source | Genuine? |
|---|---|---|
| CAPEX total preview (unsaved) | Client-side sum of CAPEX grid cells; starts "—" | Genuine — explicitly labeled "unsaved", badge-preview-only, never shown as saved/Run-derived value. |
| Revenue total preview (unsaved) | Client-side sum of Revenue grid; starts "—" | Same pattern — genuine, clearly labeled. |
| OPEX total preview (unsaved) | Client-side sum of OPEX Budget cells; starts "—" | Same. |
| EBITDA preview (unsaved) | Client-side: Revenue preview − OPEX preview; null when either input unavailable | Same — null/blank when inputs unavailable, not a fabricated partial value. |
| Operating cash flow preview (unsaved) | Client-side: EBITDA preview verbatim (C2-PR16) | Labeled "NOT AUTHORITATIVE OPERATING CASH FLOW" in code; explicitly a pipeline-demo placeholder; starts "—". |
| Debt preview (saved inputs only) | Backend `compute_debt_preview()` — a single placeholder multiplication from saved CAPEX × gearing, never real debt sculpting | Labeled "saved inputs only", tooltip says "Run remains authoritative." Starts "—". |
| Tax preview | Always "—" (backend reports preview-unavailable) | Tooltip: "Future backend preview. Run remains authoritative." Honest empty state. |
| IRR preview | Always "—" | Same — honest empty state, future boundary. |
| DSCR preview | Always "—" | Same — honest empty state, future boundary. |

All 8 indicators are **Protected by guardrails** (Preview Architecture /
Runtime Pipeline) — **not touched by this PR.**

### E. Run CTA Banner
(`app/templates/partials/_dashboard.html`, lines 20–37)

| Component | Source | Genuine? |
|---|---|---|
| "No run yet / Run the model to populate the dashboard…" | Rendered when `not runtime_summary or not runtime_summary.last_runtime_snapshot_id` | Genuine — condition checks real workspace state. Never renders when a Run has occurred. Never shows a fake KPI value. |

### F. Run Status Chip
(`_dashboard.html`, lines 43–53 / `_dashboard_oob.html`, lines 9–18)

| Component | Source | Genuine? |
|---|---|---|
| "Last run completed" badge | Rendered when `runtime_summary.last_runtime_snapshot_id` truthy | Genuine — backed by real `last_runtime_snapshot_id` from `workspace_state.last_runtime_summary`. |
| Run origin label | `runtime_summary.last_runtime_origin_label` | Genuine — real field from `last_runtime_summary` dict (set by `record_workspace_runtime` on successful Run). |
| Run timestamp (OOB update only) | `datetime.now(utc)` at the moment the OOB response is rendered | Genuine — "when did this run's result reach the browser" provenance, same convention used throughout the sprint. Not a fabricated financial timestamp. |

### G. Dashboard KPI Cards (8 cards, main grid)
(`_dashboard.html`, lines 57–72; built by `app/ui/dashboard.py::build_dashboard_kpis`)

| KPI | Source | Pre-Run value | Post-Run value | Genuine? |
|---|---|---|---|---|
| Project IRR | `raw_kpis["project_irr"]` from `last_runtime_summary` (fraction × 100 for %) | "—" (`status='missing'`) | Real `run_project()` IRR | Genuine |
| Equity IRR | `raw_kpis["equity_irr"]` × 100 | "—" | Real equity IRR | Genuine |
| Senior Debt | `raw_kpis["senior_debt_keur"]` | "—" | Real kEUR value | Genuine |
| Realized Gearing | `realized_gearing_pct` computed at workspace load from saved CAPEX/senior_debt inputs (not a Run output) | "—" if inputs absent | Derived from saved inputs | Genuine — clearly noted as "derived" status, not a Run KPI |
| Min DSCR | `raw_kpis["min_dscr"]` | "—" | Real min DSCR | Genuine |
| Avg DSCR | `raw_kpis["avg_dscr"]` | "—" | Real avg DSCR | Genuine |
| Y1 Revenue / Total Revenue | `raw_kpis["y1_revenue_keur"]` or `raw_kpis["total_revenue_keur"]` | "—" | Real kEUR | Genuine |
| Y1 EBITDA / Total EBITDA | `raw_kpis["y1_ebitda_keur"]` or `raw_kpis["total_ebitda_keur"]` | "—" | Real kEUR | Genuine |

Additional KPIs in `build_dashboard_kpis_from_raw_kpis` (also rendered when present):
- **Project NPV**: `raw_kpis["project_npv_keur"]`; "—" pre-run. Genuine.
- **CAPEX**: `raw_kpis["total_capex_keur"]`; "—" pre-run. Genuine.

**No hardcoded zeros or fake financial values found anywhere in this
grid.** The "—" sentinel is used consistently for every missing value.

### H. Empty-State Hint (P1-UX-FIX-1)
(`_dashboard.html`, lines 82–104)

| Component | Source | Genuine? |
|---|---|---|
| "Run the model to see KPIs here. Scenario `<id>` is selected but has not been run yet." | Rendered when a runtime snapshot exists but ALL KPIs have `status='missing'` | Genuine — fires only in the specific edge case where a scenario was selected and cleared runtime evidence. Accurate, not a fake value. |

### I. Inline SVG Charts (3 charts)
(`_dashboard.html`, lines 107–124; built by `app/ui/dashboard.py`)

| Chart | Source | Genuine? |
|---|---|---|
| Revenue & EBITDA over time | `build_revenue_ebitda_series(waterfall_result)` where `waterfall_result.yearly_series = {}` (always empty — `last_runtime_summary` does not carry per-period series data) | Genuine — always renders "No data available" SVG; never shows fabricated series data. |
| DSCR over time | `build_dscr_series(...)` → same empty `yearly_series` | Genuine — always "No data available". |
| Senior debt balance | `build_debt_balance_series(...)` → same | Genuine — always "No data available". |

These charts are a known honest boundary: `last_runtime_summary`
provides scalar KPI totals but not per-period time series. The "No
data available" SVG is the correct and honest empty state. Wiring
per-period series data into the charts is a future enhancement, not a
honesty defect.

### J. Governance Status Card
(`workspace_shell.html`, lines 571–628)

| Component | Source | Genuine? |
|---|---|---|
| Governance Status card (G20, R99/R102, Equity IRR Gap, TUHO Parity) | `{% if audit_mode %}` — gated; `audit_mode` is hardcoded `False` for all normal-user routes in `main_web.py` | Genuine — same `audit_mode` gating pattern established in PR9/PR10. Never visible to normal users. Static labels inside audit-only block (BLOCKED/NOT APPROVED) are reviewer-facing constants, not fabricated user-facing numbers. |
| TUHO Parity - Phase 9 card | Same `{% if audit_mode %}` gate | Same — confirmed not user-visible. |

### K. Scenario Matrix (included in panel-overview)
(`app/templates/partials/scenario_matrix.html`)

Already confirmed genuinely real in **PR10**. Not re-audited here (no
change since PR10). See `docs/PRODUCT_GAP_PR10_SCENARIOS_COMPARE_REALITY_CHECK.md`.

### L. Project Home Page (GET /)
(`app/templates/project_home_page.html`, data from `_home_user_projects()`)

| Column | Source | Genuine? |
|---|---|---|
| Project name, technology, country, capacity_mw | `record.baseline_snapshot` / `record.project_name` (persisted) | Genuine |
| Last edited | `record.updated_at` (persisted timestamp) | Genuine |
| Last run | `record.last_run_summary["run_at"]` (persisted) | Genuine |
| Status: "Draft" / "Run completed" / "Needs rerun" | Derived from `last_run_summary` truthiness and `updated_at > run_at` comparison | Genuine — real, honest status logic. No fake values. |

## Banned Internal Wording Audit

Searched every user-visible section of the Dashboard/Overview
(`_dashboard.html`, `_dashboard_oob.html`, `workspace_shell.html`
lines 338–651 / panel-overview only, `_generic_status_line.html`,
`kpis.html`, `runtime_summary.html`, `app/ui/dashboard.py`) for:
`Preview Architecture`, `Runtime Pipeline`, `Stub`, `Prototype`, `TODO`,
`FIXME`, `C1`, `C2` (as internal jargon labels), `G20`, `R99`, `R102`
in rendered user-visible copy.

**Result: None found in rendered output.** Jinja developer comments
(`{# ... #}`) in `workspace_shell.html` contain the words "stub" and
references to `C2-PR*` phase codes (e.g. `C2-PR30: Tax preview row.
Backend-only stub`), but these are stripped at render time and never
appear in any HTML sent to the browser. No change was needed.

`G20`/`R99`/`R102` appear only inside the `{% if audit_mode %}` block
(never rendered for normal users) — same accepted pattern as PR9/PR10.

## Pre-Run Behaviour Verification

For a newly-created project with no Run:
1. `not runtime_summary or not runtime_summary.last_runtime_snapshot_id` is True → "No run yet" CTA renders.
2. All 8 KPI cards show "—" (`status='missing'`).
3. All 3 SVG charts show "No data available".
4. No fake financial values are shown anywhere.
5. The pre-Run state is fully honest.

## Post-Run Behaviour Verification

After a successful Run:
1. `POST /run` → `run_project()` → `record_workspace_runtime()` → `workspace_state.last_runtime_summary` updated with real KPIs.
2. OOB response appends `_dashboard_oob.html` fragment with `build_dashboard_kpis_from_raw_kpis(raw_kpis)` — all values from the real run.
3. HTMX `hx-swap-oob="true"` replaces `#dashboard-v1` in-place.
4. "No run yet" CTA disappears; "Last run completed" status chip appears.
5. All available KPIs update to real values; any missing KPI still shows "—".
6. No stale values remain (OOB swap is atomic for the whole `#dashboard-v1` block).
7. No duplicated KPI surfaces appear (KPI deduplication was completed in UX-2C-1; `runtime_summary.html`'s KPI breakdown is behind a `<details>` collapsed by default).

## KPI Deduplication Confirmation

The `tests/test_ux2c1_overview_kpi_deduplication.py` tests (pre-existing)
verify:
1. One canonical KPI surface (`_dashboard.html`) carries the required labels.
2. Project IRR / Equity IRR / Avg DSCR each appear only once in the normal Overview surface.
3. The Run result's `runtime_summary.html` KPI grid is behind a `<details>` collapse, not open by default.
4. No required KPI was removed from the app.

**No duplication found. No change needed.**

## What Changed

No template, Python route/service, persistence, export, CSS, or
JavaScript file was modified. This PR adds:

- `docs/PRODUCT_GAP_PR12_OVERVIEW_DASHBOARD_FINAL_POLISH.md` (this file).
- `tests/test_product_gap_pr12_overview_dashboard_final_polish.py` (new):
  locks in the investigation findings with executable characterization tests.

## Why No Further Hide/Replace/Unavailable-Panel Work Was Needed

Per the spec's explicit instruction ("if unsure whether a value is
real, hide/replace rather than exposing it as authoritative"), this
PR's investigation specifically looked for: fake KPI numbers shown
pre-Run as if real, canned/demo financial values, misleading zero
placeholders, unfinished dashboard sections presented as authoritative,
duplicated KPI grids, and internal jargon in user-visible copy. **None
were found.** Every KPI on the Dashboard traces to a real
`run_project()` result or correctly shows "—". Inventing "Unavailable"
panels where real, correct empty states already exist would make the
product *less* honest, not more — so none was added. This matches
PR10's and PR11's outcomes applied to the Dashboard.

## Pre-existing Test Failures (Baseline, Not Regressions)

Two tests in `tests/test_phase_p2min3_dashboard_v1.py` are stale and
fail on `main` (pre-dating this PR):
- `TestDashboardModule::test_dashboard_returns_eight_kpis`
- `TestDashboardModule::test_realized_gearing_kpi_status_is_derived`

These call `build_dashboard_kpis(waterfall_result=..., ...)` using the
old pre-`HOTFIX-PILOT-BLOCKER-1` signature. The function was refactored
to `build_dashboard_kpis(last_runtime_summary=..., ...)` (documented in
the function's docstring), leaving these two tests with a stale kwarg.
They are confirmed identical failures on `main` HEAD (no regression
from this PR). The aggregate
`TestPriorPhaseTestsPreserved::test_all_prior_phase_tests_pass` also
fails as a consequence.

Additionally, the sprint-level baseline contains 3 previously-confirmed
pre-existing failures:
- `test_c2_pr1_live_model.py::TestStaticWiring::test_no_recalculation_formula_dependency_or_saverun_code_in_live_model`
- `test_c2_pr7_backend_preview_endpoint.py::...::test_no_financial_engine_call`
- `test_c2_pr9_runtime_request_hardening.py::TestNoRegressionForAuthorizedOrNullProject::test_authorized_project_behaviour_matches_pr8_contract`

And the pre-existing 6-failure cluster in
`tests/test_phase9_5_output_tabs_runtime_summary_binding.py`.

**None of these are touched by or caused by this PR.**

## What Remains / Future Work

- **SVG charts**: Currently always "No data available" because
  `last_runtime_summary` provides scalar KPI totals but no per-period
  time series. Wiring per-period series into the chart builders is a
  future backend enhancement — it requires `WaterfallResult.yearly_series`
  to be serialized into `workspace_state.last_runtime_summary`, which is
  a data-model change out of scope for this UI-honesty PR.
- **Realized Gearing KPI**: Sourced from saved inputs at workspace-load
  time (not from a Run), so it does not update on OOB post-Run swap.
  The current behavior is technically honest (it is derived from saved
  inputs and labeled "derived") but could be confusing. Adding it to the
  OOB KPI update or noting the discrepancy more visibly is a future UX
  polish item.
- **Tax/IRR/DSCR preview rows**: Always "—" today; future backend work
  would wire real preview computations. Existing honest empty states
  require no change.
- The stale `test_dashboard_returns_eight_kpis` /
  `test_realized_gearing_kpi_status_is_derived` tests (old signature)
  should be updated in a future test-maintenance pass. They are
  pre-existing failures on `main` and are not caused by this PR.

## Confirmation: No Financial Formulas, Run Logic, Save Logic, Persistence, Preview Architecture, or Runtime Pipeline Changed

This PR changed **zero** functional files. It adds one documentation
file and one new test file only. `domain/*`, `app/waterfall_core.py`,
`app/input_adapter.py`, `app/project_factories.py`,
`static/modelling/runtime-renderer.js`, `app/services/model_preview.py`,
`app/services/preview_context.py`, `app/services/previews/*`,
`app/ui/dashboard.py`, `app/templates/partials/_dashboard.html`,
`app/templates/partials/_dashboard_oob.html`,
`app/templates/partials/workspace_shell.html`, and `main_web.py` were
**not** touched.
