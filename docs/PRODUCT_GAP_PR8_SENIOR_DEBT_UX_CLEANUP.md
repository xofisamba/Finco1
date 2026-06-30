# Product Gap PR8: Senior Debt UX Cleanup

## Summary

The Senior Debt screen (`app/templates/partials/sheet_senior_debt.html`,
tab `senior-debt`, wired via `_RUNTIME_SHEET_MAP` in `main_web.py` for
both initial render — included from `workspace_shell.html` — and the
post-`/run` out-of-band sheet refresh) already had real editable
inputs and real Run-backed KPIs (confirmed by the prior
`SENIOR_DEBT_C1_MIGRATION_NOTE.md` investigation). The one genuinely
misleading piece of content was an "Output Preview" card containing
fixed copy with no Jinja variable binding to `project_ctx` or
`runtime_summary` at all — described to the user as a "Preview
schedule" with "static reference values", but in fact carrying no
schedule data whatsoever (no rows, no columns, nothing to bind). This
is a UI-honesty pass only: that card is replaced with a single honest
unavailable-state panel reusing the `empty-state-notice` /
`empty-state-notice--warn` CSS pattern established in PR6/PR7. No
debt formulas, sculpting logic, DSCR calculations, Run logic, Save
logic, persistence, export, or Preview Architecture code was touched.

## Investigation findings

`sheet_senior_debt.html` has four distinct regions, matching the
findings already documented in `docs/SENIOR_DEBT_C1_MIGRATION_NOTE.md`
(the prior C1 markup migration for this same sheet):

1. **Live Runtime Summary block** (`#shared-runtime-block`,
   `#runtime-block-kpis`, `#sd-secondary-metrics`) — populated
   client-side from `sessionStorage.getItem("lastRuntimeSummary")` by
   the `_populateSDRuntimeBlock()` script already in this template.
   That sessionStorage value is written by the existing post-`/run`
   flow and traces back to `workspace_state.last_runtime_summary` in
   `main_web.py` (the same mechanism verified in PR6/PR7 for Financial
   Statements/Distribution/Sponsor). **Confirmed genuinely Run-backed.
   Kept unchanged.**

2. **"Debt Facility Summary" editable-grid-table** — 4 rows, each with
   a real `<input class="editable-grid-input" data-grid-source="...">`
   for Gearing (%), Target DSCR, Interest Rate (%), and Tenor (years).
   These update draft workspace state and are unconditionally editable
   (no `is_user_project` gate), as already documented in the C1
   migration note. Each `<td>` also carries a `data-fc-raw` value
   sourced from the real `project_ctx` field
   (`project_ctx.gearing_pct`, `project_ctx.target_dscr`,
   `project_ctx.interest_rate_pct`, `project_ctx.senior_tenor_years`)
   — the project's last-saved/runtime value. **Confirmed genuinely
   editable via a real, already-wired persistence path. Kept
   unchanged — no new persisted fields, no change to
   `input_adapter.py`/`project_factories.py`.**

3. **`assumption-grid` of 4–5 read-only `<div class="assumption-
   item">` metric displays** (Facility Amount, Tenor, All-in Rate,
   Target DSCR, and conditionally Indicative Gearing) — `data-fc-
   editable="false"`, no `<input>`, computed/derived display values
   sourced directly from `project_ctx`. **Confirmed genuinely
   read-only derived data. Kept unchanged, still clearly
   non-editable.**

4. **"Output Preview" card** — a static `.preview-notice` block
   reading: *"Preview schedule — static reference values, not live
   calculated output. Run the model to see actual senior debt output
   above."* There was **no Jinja variable substitution anywhere in
   this block** — no reference to `project_ctx`, `runtime_summary`,
   `last_runtime_summary`, or any debt-schedule/repayment/DSCR-table
   output. Searching the codebase confirms there is no senior-debt
   repayment-schedule, interest/principal bridge, or covenant-table
   runtime payload wired to this template. The card had zero rows or
   columns of actual schedule data — it was pure copy implying a
   schedule exists "above" when no schedule (real or fabricated) was
   ever rendered anywhere on this sheet. **Confirmed not Run-backed,
   confirmed misleading, replaced.**

A fifth file, `app/templates/partials/debt_dscr_shl_panel.html` (a
Phase 24C panel with its own DSCR/SHL/distribution-lock-up tables),
was investigated and found to be **orphaned** — it is not `{% include
%}`-d anywhere in `main_web.py` or any other template, and its own
origin doc (`docs/phase24c_debt_dscr_shl_ui.md`) states routing into
the workspace was deferred to "a subsequent step" that never
happened. Since it is not part of the live Senior Debt screen a user
can reach, it is **out of scope for this PR** and left untouched.

No duplication was found between the initial full-page render and the
post-`/run` OOB refresh path: `workspace_shell.html` already `{%
include %}`s `partials/sheet_senior_debt.html` directly (no inline
copy), and `main_web.py`'s `_RUNTIME_SHEET_MAP` renders the same file
for the OOB refresh. Item 6 of the stacked-PR spec (dedup render
paths) was therefore already satisfied before this PR — no change
needed.

## What changed

`app/templates/partials/sheet_senior_debt.html`:

- **Removed**: the `.preview-notice` "Output Preview" card and its
  fixed copy ("Preview schedule — static reference values, not live
  calculated output...").
- **Added**: a single unavailable-state panel (`sd-unavailable-panel`),
  reusing the pre-existing `empty-state-notice` /
  `empty-state-notice--warn` CSS classes already defined in
  `static/styles.css` (no new CSS invented). Copy: *"Senior debt
  schedule output is not available yet. Run-backed debt sizing,
  interest, principal, and covenant results will be shown here once
  this section is connected to the model engine."*
- **Kept unchanged**: the Live Runtime Summary block (genuinely
  Run-backed), the 4-row editable-grid-table (genuinely editable
  draft inputs), the assumption-grid (genuinely read-only derived
  values), the top sheet banner / "Protected" badge (consistent with
  CAPEX/OPEX/IDC/SHL/Tax/Production sheets' existing badge pattern),
  and the `_populateSDRuntimeBlock()` script.

`main_web.py` was **not** modified — `_RUNTIME_SHEET_MAP` already
pointed at `sheet_senior_debt.html` before and after this change; no
route or context-shaping changes were needed because the removed card
never consumed route-supplied data to begin with.

## Stacked items addressed

1. **Layout cleanup** — the misleading "Output Preview" card is
   replaced with a clearly-labeled "Debt Schedule Output" section
   showing an honest unavailable-state message instead of vague
   "static reference values" copy. No other layout/section grouping
   changes were needed: the existing section structure (Live Runtime
   Summary → Debt Facility Summary → Debt Schedule Output) already
   reads as a sensible Excel-style top-to-bottom flow, and no
   internal/debug-looking columns were found in either the
   editable-grid-table or assumption-grid.
2. **Real editable inputs preserved** — Gearing (%), Target DSCR,
   Interest Rate (%), and Tenor (years) remain fully editable via
   their existing `editable-grid-input` + `data-grid-source` draft
   workspace persistence path. No new assumption was added or made
   editable; no change to `input_adapter.py` or `project_factories.py`.
3. **Placeholder output hidden** — the only placeholder/static/mock
   debt output found (the "Output Preview" card) is replaced with the
   unavailable-state panel described above.
4. **Real Run-backed KPIs kept** — Senior Debt amount, Avg DSCR, Min
   DSCR (and the shared Project IRR/Equity IRR/Avg DSCR/Min DSCR KPI
   grid) remain visible, read-only, sourced from
   `sessionStorage.lastRuntimeSummary` written by the real `/run` flow.
5. **Governance copy** — the existing copy ("These controls update
   draft workspace state only", "Runtime remains blocked while edits
   are unsaved", "Browser does not calculate debt service",
   "Preview-only until saved and re-run") was reviewed and found
   already plain, short, and free of internal jargon — no changes
   needed there. The one piece of confusing copy (the "Output
   Preview" card's "static reference values, not live calculated
   output" line) is the one replaced in item 3 above.
6. **Render-path dedup** — investigated, found already deduplicated
   (see "Investigation findings" above); no change needed.

## Are any displayed values genuinely Run-backed?

Yes: the Live Runtime Summary block (Project IRR, Equity IRR, Avg
DSCR, Min DSCR, and the Senior Debt / Avg DSCR / Min DSCR secondary
metrics), sourced from `sessionStorage.lastRuntimeSummary`, which is
written by the existing post-`/run` flow and ultimately sourced from
`workspace_state.last_runtime_summary` in `main_web.py` — the same
mechanism documented and verified in PR6/PR7. This block was already
present before this PR and is untouched.

## What remains read-only, and why

- The 4–5 `assumption-grid` summary cells (Facility Amount, Tenor,
  All-in Rate, Target DSCR, Indicative Gearing) are computed/derived
  display values sourced directly from `project_ctx`, not independent
  user inputs — they summarize the same underlying fields the 4 draft
  inputs above them edit. Making them separately editable would
  create two conflicting edit surfaces for the same data; they remain
  read-only by design, consistent with the C1 migration's
  `data-fc-editable="false"` contract.

## Why no new calculations were added

Per the Preview Architecture freeze and this PR's explicit
guardrails, no senior-debt repayment-schedule engine, sculpting
solver, interest/principal bridge, or covenant-table engine exists in
the codebase to source real values from. Inventing client-side or
template-side schedule numbers to fill the "Output Preview" card
would have been a worse outcome than an honest "not available yet"
message. This PR adds zero calculation logic anywhere.

## Tests

- `tests/test_product_gap_pr8_senior_debt_ux_cleanup.py` (new): covers
  all minimum-required PR8 behaviors — tab/screen still renders, the
  4 real editable draft inputs remain `data-fc-editable="true"` with a
  real `<input>`, the 4-5 read-only summary cells remain
  `data-fc-editable="false"`, the old `.preview-notice` placeholder
  markup is removed, the unavailable-state panel is present with the
  suggested copy and reuses the existing `empty-state-notice` /
  `empty-state-notice--warn` classes, the Run-backed KPI block and its
  population script are preserved, no banned jargon appears in the
  rendered (non-comment) template text, `main_web.py` was not touched,
  guardrail file paths are untouched (`git diff main`), and the
  PR6/PR7 unavailable panels for Financial Statements/
  Distributions/Sponsor are unaffected.
- Existing tests referencing `sheet_senior_debt.html`
  (`tests/test_senior_debt_c1_markup_contract.py`,
  `tests/test_senior_debt_c1_migration_browser.py`,
  `tests/test_phase9_5_output_tabs_runtime_summary_binding.py`,
  `tests/test_c1_markup_conformance.py`,
  `tests/test_ux1a_navigation_context_fix.py`,
  `tests/test_phase_p2fix3_c2_first_edit.py`,
  `tests/test_phase_p2fix5b_normal_mode_shell_strip.py`,
  `tests/test_phase_s2_gearing_as_output.py`,
  `tests/test_phase_p2min4_navigation_compression.py`,
  `tests/test_phase57a_ui3_line_item_grid_capex_summary.py`,
  `tests/test_phase57f_ui3_2_next_grid_readiness_plan.py`,
  `tests/test_phase57pre_route_render_smoke.py`,
  `tests/test_phase54a_frontend_inventory_ui_baseline.py`,
  `tests/test_phase38_audit_output_trust_surface_polish.py`,
  `tests/test_phase25a_pilot_product_polish_guided_workflow.py`,
  `tests/test_phase24c_debt_dscr_shl_ui.py`,
  `tests/test_phase24c1_frozen_vs_derived_warning.py`,
  `tests/test_phase13_editable_grid_ux.py`,
  `tests/test_phase14a_reviewer_productivity_polish.py`,
  `tests/test_phase15_browser_workflow_verification.py`) were checked
  and continue to pass unchanged: none of them assert on the removed
  `.preview-notice`/"Preview schedule" markup specifically (the two
  tests that OR-check for either "Preview schedule" or "badge-preview"
  — `tests/test_phase9_5_output_tabs_runtime_summary_binding.py`'s
  `TestPreviewLabelsPreserved`/`TestUILabelConsistency` — still pass
  because the sheet's top-banner `badge-preview` "Protected" badge is
  untouched). No test deletions were needed.

## Pre-existing failures (not touched, not regressions)

Confirmed via `git stash` (clean diff against this branch's base
`5fca8a4`) that the following were already failing before this PR and
are unrelated to Senior Debt:

- `tests/test_phase9_5_output_tabs_runtime_summary_binding.py`: 6
  pre-existing failures unrelated to Senior Debt — `TestRuntimeSummaryBinding`
  (3, runtime `/run` sessionStorage extraction issue),
  `TestOutputTabsContainRuntimeSummary::test_sheet_contains_runtime_summary_label[sheet_financials.html]`,
  `TestMissingMetricsNotFabricated::test_runtime_summary_has_not_available_for_missing_fields`,
  and `TestUILabelConsistency::test_runtime_summary_labels_present[sheet_financials.html]`
  (all about `sheet_financials.html` or the `/run` route, not Senior
  Debt).
- `tests/test_phase24c1_frozen_vs_derived_warning.py::test_frozen_schedule_warning_exists_in_panel`:
  pre-existing failure in the orphaned `debt_dscr_shl_panel.html`
  (missing "non-fixture project type"/"generic wind/solar" phrase),
  unrelated to this PR's scope (that file is not part of the live
  Senior Debt screen, see "Investigation findings" above).

Per the sprint-level baseline, the 3 previously-confirmed pre-existing
failures
(`test_c2_pr1_live_model.py::TestStaticWiring::test_no_recalculation_formula_dependency_or_saverun_code_in_live_model`,
`test_c2_pr7_backend_preview_endpoint.py::...::test_no_financial_engine_call`,
`test_c2_pr9_runtime_request_hardening.py::TestNoRegressionForAuthorizedOrNullProject::test_authorized_project_behaviour_matches_pr8_contract`)
remain, with no new failures introduced by this PR. A pre-existing
~13-failure cluster in
`tests/test_phase20m_runtime_statement_polish.py` /
`tests/test_phase9_5_excel_like_sheet_content_foundation.py` (related
to `sheet_opex.html` wiring/CSS issues) is also present and unrelated.

## Confirmation: no financial logic, Run, Save, persistence, export, or Preview Architecture code changed

No formulas, debt-sculpting logic, DSCR calculations, repayment-
schedule logic, preview payload fields, Run output structures, or
persistence changes were added or modified. The change is
template-markup-only. The following guardrailed paths were **not**
touched: `domain/*`, `app/waterfall_core.py`, `app/input_adapter.py`,
`app/project_factories.py`, `static/modelling/runtime-renderer.js`,
`app/services/model_preview.py`, `app/services/preview_context.py`,
`app/services/previews/*`, and `main_web.py`.

## Future work (out of scope for this PR)

- Wiring a real, Run-backed senior debt repayment schedule
  (interest/principal bridge, sculpted debt service, covenant table)
  to the "Debt Schedule Output" section is the natural follow-up, but
  is explicitly out of scope per the Preview Architecture freeze and
  the "no new debt formulas/sculpting" guardrail in this PR's spec.
- Once such an engine exists, the unavailable-state panel added here
  should be replaced with a real per-period table sourced from that
  engine's output, following the same fc-grid presentation pattern
  already used elsewhere in the app (CAPEX/OPEX/Revenue sheets).
- Wiring `debt_dscr_shl_panel.html` into the workspace (it is
  currently orphaned, never `{% include %}`-d) remains a separate,
  future routing decision outside this UI-honesty-only PR's scope.
- Multi-lender senior debt and full Excel-parity debt sculpting remain
  future engine/model tasks, not UI cleanup.
