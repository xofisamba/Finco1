# Product Gap PR9: Tax Reality Check

## Summary

The Tax screen (`app/templates/partials/sheet_tax.html`, tab `tax`,
wired via `_RUNTIME_SHEET_MAP` in `main_web.py` and included directly
in `workspace_shell.html`) showed two real, project-context-backed
assumptions (CIT Rate, Loss Carryforward) alongside a static "Output
Preview" card with fixed copy claiming a "Preview schedule" that had
zero Jinja variable binding, a static "Convention: AUDIT-ONLY" badge
with no real data behind it, and internal-jargon G20/R99/R102
governance cells. This is a UI-honesty pass only: the misleading
placeholder content and internal jargon are removed/replaced; the two
real assumptions are kept, clearly labeled read-only. No tax formulas,
depreciation formulas, WHT formulas, CIT logic, Run logic, Save logic,
persistence, export, or Preview Architecture code was touched.

## Investigation findings

`sheet_tax.html` (pre-PR9) contained four distinct regions:

1. **Live Runtime Summary block** (`#shared-runtime-block`,
   `#runtime-block-kpis`) — populated client-side from
   `sessionStorage.getItem("lastRuntimeSummary")` by the
   `_populateTaxRuntimeBlock()` script in this template. That
   sessionStorage value is written by the existing post-`/run` flow
   and traces back to `workspace_state.last_runtime_summary` in
   `main_web.py` — the same mechanism verified in PR6/PR7/PR8.
   **Confirmed genuinely Run-backed** for the project-level KPIs
   (Project IRR, Equity IRR, Avg DSCR, Total Revenue, EBITDA, Total
   OPEX). **Kept unchanged.**

   However, the block's secondary metrics row (`#tax-secondary-metrics`)
   contained a `tax-status` cell hardcoded in the template to the text
   `NOT_AVAILABLE`, then *unconditionally overwritten* by the
   population script to the literal string `"AUDIT-ONLY"` regardless
   of what (if anything) `lastRuntimeSummary` actually contained.
   Searching `main_web.py`'s `last_runtime_summary` construction
   confirms **there are no tax-specific keys at all** (no
   `tax_payable`, `cit`, `effective_tax_rate`, `tax_shield`,
   `tax_loss_balance`, `taxable_income`, or `tax_cash_flow` keys
   anywhere in the runtime summary). The `tax-status` cell and its
   `textContent = "AUDIT-ONLY"` assignment were therefore a fabricated
   client-side value with no real binding. **Confirmed not Run-backed,
   removed** along with the related audit-only G20/R99/R102 governance
   cells (`#tax-secondary-metrics-audit`), which only ever rendered
   internal jargon ("G20 Gate: BLOCKED", "R99/R102: NOT APPROVED")
   directly into user-facing markup — banned per this PR's explicit
   no-jargon rule and not real tax data either way.

2. **"CIT Assumptions" `assumption-grid`** — CIT Rate
   (`project_ctx.cit_rate_pct`) and Loss Carryforward
   (`project_ctx.loss_carryforward_years`), both `data-fc-editable=
   "false"`, sourced directly from `project_ctx`, which in turn is
   populated from the project's tax template
   (`app/ui/project_context.py` line ~2367-2368:
   `cit_rate_pct=tax.corporate_rate`,
   `loss_carryforward_years=tax.loss_carryforward_years`). **Confirmed
   genuinely real project assumptions** — not fabricated, not random
   placeholder numbers. **Investigated for safe editability**: the
   Inputs tab's own "Tax Summary" card
   (`app/templates/partials/inputs_section.html` lines 184-202) renders
   the exact same two fields via the shared `field_row()` macro
   *without* passing `editable=True` (contrast with the adjacent
   "Debt Summary" card on the same file, lines 172-177, which does pass
   `editable=is_user_project` for gearing/DSCR/interest/tenor). This
   confirms there is **no existing, already-wired persistence path**
   anywhere in the app that lets a user edit CIT Rate or Loss
   Carryforward — not on the Inputs tab, and not on the Tax sheet.
   Per the PR9 spec's explicit rule ("only expose editability where a
   real safe persistence path already exists; do not invent new
   editability"), **these two fields remain read-only on the Tax
   sheet**, exactly as they already were everywhere else in the app.
   A `table-note` was added clarifying *why* ("Read-only on this sheet
   — not yet editable via a saved input"), mirroring the honesty goal
   of this PR without inventing a new persisted field.

   Also present in this card pre-PR9: a static "Convention" badge
   hardcoded to the literal text `AUDIT-ONLY` with `data-fc-raw=
   "AUDIT-ONLY"` — not derived from `project_ctx` or any other context
   variable at all (a fixed string, like the Senior Debt "Output
   Preview" card investigated in PR8). **Confirmed not real data,
   removed.**

3. **"Tax Output Preview" card** — a static `.preview-notice` block
   reading: *"Preview schedule — static reference values, not live
   calculated output. Run the model to see actual tax output above."*
   Identical shape to the Senior Debt "Output Preview" card found and
   replaced in PR8: **zero Jinja variable substitution**, no reference
   to `project_ctx`, `runtime_summary`, or any
   CIT/depreciation/loss-carryforward/WHT schedule data. Searching the
   codebase confirms there is no CIT payable schedule, taxable income
   bridge, depreciation schedule, loss carryforward schedule, WHT
   schedule, deductibility table, or HoldCo/SPV tax summary wired to
   this template anywhere. **Confirmed not Run-backed, confirmed
   misleading, replaced** with an honest unavailable-state panel.

4. **Bottom "Protected" badge** (`badge-preview`) — a static UI label
   consistent with every other sheet's top/bottom protected badge
   (CAPEX/OPEX/Revenue/Senior Debt/Financial Statements all carry the
   same badge). Purely a UI consistency marker, not a data claim.
   **Kept unchanged.**

A separate file, `app/tax_assumptions_ui.py`, was found during
investigation but confirmed **not wired into `main_web.py`'s routing
at all** (no reference anywhere in `main_web.py`). Like the orphaned
`debt_dscr_shl_panel.html` found in PR8, it is not part of the live
Tax screen a user can reach and is **out of scope for this PR**.

No duplication was found between the initial full-page render and the
post-`/run` OOB refresh path: `workspace_shell.html` already `{%
include %}`s `partials/sheet_tax.html` directly (no inline copy), and
`main_web.py`'s `_RUNTIME_SHEET_MAP` renders the same file for the OOB
refresh. Item 6 of the stacked-PR spec (dedup render paths) was
therefore already satisfied before this PR — no change needed.

## What changed

`app/templates/partials/sheet_tax.html`:

- **Removed**: the `tax-status` / `tax-secondary-metrics` cell and its
  client-side hardcoded `"AUDIT-ONLY"` assignment (fabricated, no real
  binding).
- **Removed**: the audit-only `tax-secondary-metrics-audit` block
  (G20 Gate / R99/R102 governance cells — internal jargon, not real
  tax output, banned per this PR's no-jargon rule).
- **Removed**: the static "Convention: AUDIT-ONLY" badge (fixed
  literal, no Jinja binding).
- **Removed**: the audit-mode-only "G20 Status" / "R99/R102 Status"
  assumption-grid cells (same governance jargon as above, duplicated
  in the assumptions card).
- **Removed**: the `.preview-notice` "Tax Output Preview" card and its
  fixed copy ("Preview schedule — static reference values, not live
  calculated output...").
- **Added**: a `table-note` on the "Tax Assumptions" card explaining
  the two remaining real fields are read-only because no editable
  persistence path exists.
- **Added**: a single unavailable-state panel (`tax-unavailable-panel`),
  reusing the pre-existing `empty-state-notice` /
  `empty-state-notice--warn` CSS classes already defined in
  `static/styles.css` (no new CSS invented, same pattern as PR6/PR7/
  PR8). Copy: *"Tax output is not available yet. Run-backed taxable
  income, depreciation, loss carryforward, CIT, and withholding tax
  results will be shown here once this section is connected to the
  model engine."*
- **Renamed**: "CIT Assumptions" section header to "Tax Assumptions"
  (the card already covers Loss Carryforward, not just CIT, so the
  more general label is more accurate); "Output Preview" section
  header to "Tax Output" (plainer, less ambiguous than "Preview").
- **Kept unchanged**: the Live Runtime Summary KPI grid
  (`#shared-runtime-block` / `#runtime-block-kpis`) and its
  `_populateTaxRuntimeBlock()` script (minus the fabricated
  `tax-status` assignment removed above) — this remains the only
  genuinely Run-backed content near this sheet.
- **Kept unchanged**: the CIT Rate and Loss Carryforward
  `assumption-item` cells themselves (still `data-fc-editable="false"`,
  still sourced from `project_ctx.cit_rate_pct` /
  `project_ctx.loss_carryforward_years`).
- **Kept unchanged**: the bottom "Protected" badge.

`main_web.py` was **not** modified — `_RUNTIME_SHEET_MAP` already
pointed at `sheet_tax.html` before and after this change; no route or
context-shaping changes were needed because the removed
cards/badges never consumed route-supplied data to begin with.

## Stacked items addressed

1. **Layout cleanup** — "CIT Assumptions" renamed to "Tax Assumptions"
   (more accurate, covers both fields shown); "Output Preview" renamed
   to "Tax Output" (plainer copy). Internal-jargon governance cells
   (G20/R99/R102) and the fake "Convention" badge removed, reducing
   visual clutter and duplicate/misleading wording. No navigation
   changes, no backend data-structure changes.
2. **Real editable inputs identified** — investigation confirmed no
   Tax assumption has a safely-wired, already-persisted editable path
   anywhere in the app (not even on the dedicated Inputs tab). No
   editability was added; CIT Rate and Loss Carryforward remain
   read-only, now with an explicit on-screen explanation of why.
3. **Placeholder output hidden** — the "Tax Output Preview" card (zero
   Jinja binding, fabricated "Preview schedule" copy) and the fake
   "Convention: AUDIT-ONLY" badge are replaced/removed; a single honest
   unavailable-state panel takes their place.
4. **Real Run-backed KPIs kept** — the shared project-level Runtime
   Summary KPI grid (Project IRR, Equity IRR, Avg DSCR, Total Revenue,
   EBITDA, Total OPEX), sourced from
   `sessionStorage.lastRuntimeSummary` / `workspace_state.
   last_runtime_summary`, remains visible, read-only. The one
   fabricated tax-specific metric (`tax-status` hardcoded to
   `"AUDIT-ONLY"`) is removed since it was never real.
5. **Governance copy improved** — internal jargon (G20, R99/R102,
   "AUDIT-ONLY" convention badge) is removed from the Tax sheet
   entirely; the remaining copy ("Read-only on this sheet — not yet
   editable via a saved input", the unavailable-state panel text) is
   plain, short, and free of internal architecture references.
6. **Render-path dedup** — investigated, found already deduplicated
   (see "Investigation findings" above); no change needed.

## Are any displayed values genuinely Run-backed?

Yes, but only the project-level KPIs already present in the shared
Runtime Summary block (Project IRR, Equity IRR, Avg DSCR, Total
Revenue, EBITDA, Total OPEX) — sourced from
`sessionStorage.lastRuntimeSummary`, written by the existing post-
`/run` flow and ultimately sourced from `workspace_state.
last_runtime_summary` in `main_web.py`. There is no Run-backed
tax-specific output (no `tax_payable`, `cit`, `effective_tax_rate`,
`tax_shield`, `tax_loss_balance`, `taxable_income`, or
`tax_cash_flow` key exists anywhere in `last_runtime_summary`).

## What remains read-only, and why

- **CIT Rate** and **Loss Carryforward** remain
  `data-fc-editable="false"`. They are real project-context values
  (sourced from the project's tax template via `app/ui/
  project_context.py`), but no safe, already-wired persistence path
  exists to let a user edit them — the dedicated Inputs tab renders
  the same two fields read-only too. Per the PR9 spec's explicit
  guardrail ("do not invent new persisted fields"), this PR does not
  add one. They remain read-only, now with an explicit on-screen
  explanation.

## Why no new calculations were added

Per the Preview Architecture freeze and this PR's explicit guardrails,
no CIT-payable engine, taxable-income bridge, depreciation schedule
engine, loss-carryforward engine, WHT engine, or HoldCo/SPV tax
summary engine exists in the codebase to source real values from.
Inventing client-side or template-side tax numbers to fill the "Tax
Output" card would have been a worse outcome than an honest "not
available yet" message. This PR adds zero tax calculation logic
anywhere.

## Tests

- `tests/test_product_gap_pr9_tax_reality_check.py` (new): covers all
  minimum-required PR9 behaviors — tab/screen still renders, the two
  real read-only assumption cells remain `data-fc-editable="false"`
  with no `<input>` and a "Read-only" explanation, the old
  `.preview-notice`/"Convention: AUDIT-ONLY" placeholder markup is
  removed, the unavailable-state panel is present with the suggested
  copy and reuses the existing `empty-state-notice`/
  `empty-state-notice--warn` classes, the Run-backed KPI block and its
  population script are preserved (minus the fabricated `tax-status`
  assignment), no banned jargon appears in the rendered (non-comment)
  template text, `main_web.py` was not touched, guardrail file paths
  are untouched (`git diff main`), and the PR6/PR7/PR8 unavailable
  panels for Financial Statements/Distributions/Sponsor/Senior Debt
  are unaffected.
- `tests/test_tax_c1_markup_contract.py` (narrowly updated): the
  `test_known_address_examples_present` test now asserts the removed
  `tax!convention`/`tax!g20_status`/`tax!r99_r102_status` addresses are
  **absent** rather than present; `test_audit_only_fields_present_in_
  audit_mode` / `test_audit_only_fields_absent_in_normal_mode` are
  merged into a single `test_audit_only_fields_absent_in_both_modes`
  asserting the governance cells are gone from both `audit_mode=True`
  and `audit_mode=False` renders. All other markup-contract assertions
  (grid root, scroll container, unique addresses, deterministic
  ordering, no real `<input>` anywhere, raw-value fidelity for
  `tax!cit_rate`/`tax!loss_carryforward`) are unchanged and still pass.
- `tests/test_phase9_5_output_tabs_runtime_summary_binding.py`
  (narrowly updated): `TestGovernanceBadgesUnchanged::
  test_tax_tab_shows_g20_blocked` / `test_tax_tab_shows_r99_not_
  approved` and `TestUILabelConsistency::
  test_governance_labels_present_in_tax_tab` (which previously
  *required* G20/R99/R102 jargon to appear in the Tax tab) are
  replaced with tests asserting the **opposite** — that this jargon is
  now absent from the Tax sheet's user-facing copy — since the PR9
  spec explicitly bans this jargon from Tax UI copy and PR7 already
  established the same precedent for Distribution/Sponsor governance
  notes. The Sponsor tab's equivalent assertion
  (`test_sponsor_tab_shows_r99_not_approved`) is untouched — Sponsor
  is out of scope for this PR.
- Other existing tests referencing `sheet_tax.html`
  (`tests/test_tax_c1_migration_browser.py`,
  `tests/test_c1_markup_conformance.py`,
  `tests/test_phase13_editable_grid_hardening.py`,
  `tests/test_phase14a_reviewer_productivity_polish.py`,
  `tests/test_phase54a_frontend_inventory_ui_baseline.py`,
  `tests/test_phase57a_ui3_line_item_grid_capex_summary.py`,
  `tests/test_phase57f_ui3_2_next_grid_readiness_plan.py`,
  `tests/test_phase57pre_route_render_smoke.py`,
  `tests/test_phase9_5_excel_like_sheet_content_foundation.py`,
  `tests/test_phase9_co2_cit_bridge.py`,
  `tests/test_r67_yrs13to30_residual.py`,
  `tests/test_senior_debt_sizing_policy.py`) were checked and continue
  to pass unchanged (`test_tax_cit_zero` in
  `test_phase9_5_excel_like_sheet_content_foundation.py` only requires
  "0%" or "CIT" to appear somewhere — "CIT" still appears in the "Tax
  Assumptions" section header and "CIT Rate" label). No test deletions
  were needed.

## Pre-existing failures (not touched, not regressions)

Confirmed via `git stash` (clean diff against this branch's base
`79f9ec8`) that the following were already failing before this PR and
are unrelated to Tax:

- `tests/test_phase9_5_output_tabs_runtime_summary_binding.py`: 6
  pre-existing failures (3 `TestRuntimeSummaryBinding` `/run` route
  issues, plus `sheet_financials.html`-specific label/NOT_AVAILABLE
  assertions) — all about the `/run` route or
  `sheet_financials.html`, not Tax.
- `tests/test_phase13_editable_grid_hardening.py::
  test_htmx_rebinding_and_runtime_action_disable_hooks_exist`: missing
  `btn-save-run` id in `index.html`, unrelated to Tax.
- `tests/test_phase14a_reviewer_productivity_polish.py`: 3
  pre-existing failures about `index.html`/`workspace_shell.html`
  "Active Scenario" labeling and `sheet_revenue.html` draft-value
  copy, unrelated to Tax.
- `tests/test_phase57a_ui3_line_item_grid_capex_summary.py`: 2
  pre-existing failures about CAPEX line-item-grid rendering,
  unrelated to Tax.
- `tests/test_phase9_5_excel_like_sheet_content_foundation.py`: a
  12-failure cluster (missing "Template preview"/"TUHO factory
  snapshot"/"not live run output" phrases across multiple sheets,
  `sheet_opex.html` not included in `workspace_shell.html`, a
  forbidden-import string match on an unrelated comment in
  `scenario_multi_compare_picker.html`) — all pre-existing across
  multiple unrelated sheets, not introduced by or specific to this
  PR's Tax changes.

Per the sprint-level baseline, the 3 previously-confirmed pre-existing
failures
(`test_c2_pr1_live_model.py::TestStaticWiring::test_no_recalculation_formula_dependency_or_saverun_code_in_live_model`,
`test_c2_pr7_backend_preview_endpoint.py::...::test_no_financial_engine_call`,
`test_c2_pr9_runtime_request_hardening.py::TestNoRegressionForAuthorizedOrNullProject::test_authorized_project_behaviour_matches_pr8_contract`)
remain, with no new failures introduced by this PR. The full
`tests/test_c1_*.py tests/test_c2_*.py tests/test_product_gap_*.py`
regression suite was run end to end: 913 passed, 3 failed (exactly the
known baseline), 0 new failures.

## Confirmation: no tax formulas, depreciation formulas, WHT formulas, Run, Save, persistence, export, or Preview Architecture code changed

No CIT formulas, taxable-income-bridge logic, depreciation schedule
logic, loss-carryforward engine logic, WHT calculation logic,
HoldCo/SPV tax logic, Run logic, Save logic, persistence logic, export
logic, preview payload fields, or Run output structures were added or
modified. The change is template-markup-only (plus narrow test
updates reflecting the new honest behavior). The following guardrailed
paths were **not** touched: `domain/*`, `app/waterfall_core.py`,
`app/input_adapter.py`, `app/project_factories.py`,
`static/modelling/runtime-renderer.js`, `app/services/model_preview.py`,
`app/services/preview_context.py`, `app/services/previews/*`, and
`main_web.py`.

## Future work (out of scope for this PR)

- Wiring a real, Run-backed CIT payable schedule, taxable income
  bridge, depreciation schedule, loss carryforward schedule, and WHT
  schedule to the "Tax Output" section is the natural follow-up, but
  is explicitly out of scope per the Preview Architecture freeze and
  the "no new tax formulas" guardrail in this PR's spec.
- Once such an engine exists, the unavailable-state panel added here
  should be replaced with real per-period tables sourced from that
  engine's output, following the same fc-grid presentation pattern
  already used elsewhere in the app (CAPEX/OPEX/Revenue sheets).
- If a safe, dedicated tax-assumption persistence/editing path is
  ever added to `input_adapter.py`/`project_factories.py` (a
  backend/persistence task, not a UI task), CIT Rate and Loss
  Carryforward could then be made genuinely editable on this sheet,
  consistent with how Senior Debt's gearing/DSCR/interest/tenor are
  already editable.
- The orphaned `app/tax_assumptions_ui.py` file (not wired into
  `main_web.py` routing) remains a separate, future routing decision
  outside this UI-honesty-only PR's scope.
