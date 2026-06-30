# Product Gap PR6: Financial Statements Reality Check

## Summary

The Financial Statements screen (`app/templates/partials/sheet_financials.html`,
rendered by the `pl` / `cashflow` / `balance` tabs, all wired to the same
partial in `main_web.py`) showed three statement tables — Income
Statement (P&L), Cash Flow, and Balance Sheet — that looked like real
model output but were not. This PR is a UI-honesty pass only: it
removes the misleading static tables and replaces them with a single
honest unavailable-state panel. No financial formulas, Run logic, Save
logic, persistence, export, or Preview Architecture code was touched.

## Investigation findings

`app/templates/partials/sheet_financials.html` (pre-PR6) contained two
distinct kinds of content:

1. **`fs-runtime-block` / `fs-secondary-metrics`** — a block populated
   entirely client-side from `sessionStorage.getItem("lastRuntimeSummary")`,
   which is written by the existing Run-response flow after a real
   `POST /run` (see `static/modelling/runtime-renderer.js` and the
   `_populateFSRuntimeBlock` script already in this template). The data
   keys read (`project_irr`, `equity_irr`, `avg_dscr`, `total_revenue_keur`,
   `total_ebitda_keur`, `total_opex_keur`, `total_distributions_keur`,
   `shl_opening_keur`) trace back in `main_web.py` to
   `workspace_state.last_runtime_summary`, which is populated from the
   real `run_project()` result (`raw_kpis = getattr(_ws,
   "last_runtime_summary", None)`, `main_web.py` ~line 2685, ~3322-3356).
   **This block is genuinely Run-backed and was kept unchanged.**

2. **Three `<table>` grids** (`#fs-pnl-grid`, `#fs-cf-grid`,
   `#fs-bs-grid`) — every single cell value in these tables (e.g. "PPA
   Revenue: 4,372", "Senior Debt: 43,359", "Total Equity: −8,506") was a
   hardcoded literal in the Jinja template. There was no `{{ }}`
   variable substitution anywhere inside these three tables — they did
   not read from `project_ctx`, `runtime_summary`, `workspace_state`, or
   any other template context object. The template's own footnote
   confirmed this: *"Static TUHO reference values. Not bound to active
   project runtime. Run model to populate live financial statements."*
   A sibling test suite (`tests/test_phase9_5_excel_like_sheet_content_foundation.py`)
   independently corroborates this, requiring the phrases "TUHO factory
   snapshot" and "not live run output" to appear in every sheet partial
   including this one.

   Worse: even where the static Balance Sheet's literals happened to
   satisfy `Total Assets = Total Debt + Total Equity` (e.g. Y1-H1:
   68,854 = 77,360 + (−8,506); Y3-H2: 59,830 = 82,596 + (−22,766)),
   that arithmetic agreement was never derived from any accounting
   identity tied to real project inputs — they are baked-in display
   literals tuned to look balanced for this one canned scenario only.
   They have no relationship to the project the user is actually
   editing/running. Per the PR6 spec's "investigate whether it's wired
   to real run_project() output or hardcoded/static" instruction:
   **confirmed hardcoded, confirmed not Run-backed, confirmed
   misleading as a product financial statement, removed.**

No other Financial-Statement-adjacent KPI cards exist outside this one
template; the Dashboard/Overview KPI cards are out of scope for this
PR (they already source from `runtime_summary`/`last_runtime_summary`
via separate, pre-existing code paths not touched here).

## What changed

`app/templates/partials/sheet_financials.html`:

- **Removed**: the three static statement tables (`#fs-pnl-grid`,
  `#fs-cf-grid`, `#fs-bs-grid`) and their surrounding `fs-statement-card`
  wrappers, including all hardcoded P&L/Cash Flow/Balance Sheet line
  items and the closing "Static TUHO reference values" note.
- **Added**: a single unavailable-state panel (`fs-unavailable-panel`,
  reusing the pre-existing `empty-state-notice` / `empty-state-notice--warn`
  CSS classes already defined in `static/styles.css` and used by
  `app/templates/partials/empty_states_notice.html` and
  `_empty_no_run.html` for the same purpose elsewhere in the app — no
  new CSS or new empty-state pattern was invented). The panel explains,
  in plain language: financial statements are not yet connected to
  Run outputs; modelling can continue via Inputs/Revenue/OPEX/CAPEX/
  Senior Debt/SHL/Tax; Run-backed statements will appear here once the
  statement engine is connected. No internal jargon ("C1", "C2",
  "Preview Architecture", "Runtime Pipeline", "stub") is used.
- **Kept unchanged**: the `fs-runtime-block` / `fs-secondary-metrics`
  block and its `_populateFSRuntimeBlock` script — this is the only
  genuinely Run-backed content on the sheet.
- **Kept unchanged**: the Financial Statements tab/nav entries (`pl`,
  `cashflow`, `balance` panels in `workspace_shell.html` /
  `main_web.py`'s `_RUNTIME_SHEET_MAP`) — the tab still renders, it now
  shows an honest message instead of a fabricated table. No existing
  "hide a whole product area" pattern was found in the codebase, so per
  the spec's preferred default this PR keeps the tab and clearly labels
  unavailability rather than removing navigation.

`main_web.py` was **not** modified — the existing route(s) already pass
the same context (`project_ctx`, `runtime_summary`, `audit_mode`) to
`sheet_financials.html` regardless of which of the three template
literals are rendered; no template-variable shaping was needed because
the static tables never consumed any route-supplied data to begin with
(see investigation above). This kept the change confined entirely to
the template file.

## Tests

- `tests/test_phase20m_runtime_statement_polish.py`
  (`TestFinancialStatementsRendering`): narrowly rewritten. Old
  assertions checking for the static table markup
  (`fs-pnl-grid`/`fs-cf-grid`/`fs-bs-grid`, `fc-grid`, subtotal/grand-
  total rows, "PPA Revenue", etc.) are replaced with assertions that
  (a) those grid ids are now **absent**, (b) the unavailable-state
  panel is present, (c) no banned internal jargon appears in the
  template, and (d) the runtime KPI binding script is still present.
- `tests/test_phase9_5_excel_like_sheet_content_foundation.py`:
  `test_financials_has_preview_label` updated to check for the new
  unavailable-state copy instead of the removed "static illustrative
  TUHO schedule" / "not live calculated output" preview-table phrases.
  `test_financials_has_pl_cf_bs_tables` was left as-is — it only checks
  that the words "Income Statement"/"Cash Flow"/"Balance Sheet" appear
  somewhere on the page (they do, in the unavailable-state copy), so it
  continues to pass unchanged.
- No tests were deleted wholesale.

## Pre-existing failures (not touched, not regressions)

`tests/test_phase9_5_excel_like_sheet_content_foundation.py` and
`tests/test_phase20m_runtime_statement_polish.py` both have additional
pre-existing failures unrelated to the Financial Statements content
(e.g. `sheet_opex.html not included in workspace_shell.html`,
`test_css_has_valid_syntax`, missing "TUHO factory snapshot" phrase on
unrelated sheets). These were independently confirmed present and
identical on a clean `git stash` (i.e. on top of `d42929d`, zero
changes) before this PR's edits, and are out of scope for a Financial-
Statements-only PR.

Per the sprint-level regression suite
(`tests/test_c1_*.py tests/test_c2_*.py tests/test_product_gap_*.py`),
the 3 previously-confirmed pre-existing failures
(`test_c2_pr1_live_model.py::TestStaticWiring::test_no_recalculation_formula_dependency_or_saverun_code_in_live_model`,
`test_c2_pr7_backend_preview_endpoint.py::...::test_no_financial_engine_call`,
`test_c2_pr9_runtime_request_hardening.py::TestNoRegressionForAuthorizedOrNullProject::test_authorized_project_behaviour_matches_pr8_contract`)
remain, with no new failures introduced by this PR.

## Confirmation: no financial logic changed

No formulas, balancing logic, client-side statement calculations,
preview payload fields, Run output structures, or persistence changes
were added or modified. The change is template-markup-only:
removing hardcoded display literals and adding a static informational
panel. `domain/*`, `app/waterfall_core.py`, `app/input_adapter.py`,
`app/project_factories.py`, `app/services/model_preview.py`,
`app/services/preview_context.py`, `app/services/previews/*`,
`static/modelling/runtime-renderer.js`, and `main_web.py` were not
touched.

## Future work (out of scope for this PR)

- Wiring a real, Run-backed Income Statement / Cash Flow / Balance
  Sheet engine (server-side, using existing/extended `run_project()`
  output) is the natural follow-up, but is explicitly out of scope per
  the Preview Architecture freeze and the "no new financial statement
  formulas" guardrail in this PR's spec.
- Once such an engine exists, the unavailable-state panel added here
  should be replaced with real per-period tables sourced from that
  engine's output, following the same fc-grid presentation pattern
  already used elsewhere in the app (CAPEX/OPEX/Revenue sheets).
