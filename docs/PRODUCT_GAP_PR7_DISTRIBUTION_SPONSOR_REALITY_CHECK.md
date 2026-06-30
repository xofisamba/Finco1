# Product Gap PR7: Distribution / Sponsor Reality Check

## Summary

The Distribution screen (`app/templates/partials/_sheet_distributions_partial.html`,
tab `distributions`) and the Sponsor screen
(`app/templates/partials/_sheet_sponsor_partial.html`, tab `sponsor`)
both showed fixed, hardcoded copy inside a `.placeholder-panel` block
that looked like product UI but carried zero real model data. This is
a UI-honesty pass only: both panels are replaced with a single honest
unavailable-state panel each, reusing the existing `empty-state-notice`
/ `empty-state-notice--warn` CSS pattern already established for the
Financial Statements sheet in PR6. No financial formulas, Run logic,
Save logic, persistence, export, or Preview Architecture code was
touched.

## Investigation findings

### Distribution screen

`app/templates/partials/_sheet_distributions_partial.html` is the
partial rendered for the `distributions` tab via
`_RUNTIME_SHEET_MAP` in `main_web.py` (used both for the initial
full-page load, included from `workspace_shell.html`, and for the
post-`/run` out-of-band sheet refresh in `main_web.py`).

Pre-PR7, the entire panel body was:

- A static panel header ("Distributions" / static description) — not
  data-bound, purely UI copy. Harmless, kept.
- A `.placeholder-panel` block containing: a static icon
  ("Cash"), a static title ("Equity Distributions"), a static
  description ("Distribution schedule with lockup, sweep, and
  constraints will appear after a model run."), and a static
  audit-mode note quoting internal jargon directly to the rendered
  page: *"R99/R102 runtime flags NOT APPROVED for production
  promotion. TUHO/Oborovo frozen-template path is validated; generic
  projects remain unvalidated."*

There was **no Jinja variable substitution anywhere** in this block —
no reference to `project_ctx`, `runtime_summary`, `last_runtime_summary`,
or any distribution-account output. Searching the codebase confirms
there is no distribution-account runtime payload wired to this
template at all; the only thing genuinely Run-backed near this tab is
the separately-included `shared_runtime_block.html` (project-level
IRR/DSCR/revenue/OPEX KPIs), which already renders above this panel
and was left untouched. The body of the Distribution panel itself was
100% static, including in `audit_mode`, where it additionally leaked
internal jargon (`R99/R102`) straight into rendered HTML.

**Confirmed: not Run-backed, confirmed misleading as authoritative
output, replaced.**

### Sponsor screen

`app/templates/partials/_sheet_sponsor_partial.html` (tab `sponsor`)
has the exact same shape and the exact same finding: a static panel
header, then a `.placeholder-panel` with a static icon ("User"), a
static title ("Sponsor / Equity Returns"), a static description
("Equity contribution, return metrics, and sponsor waterfall will
appear after a model run."), and a static audit-mode note quoting
*"R99/R102 runtime flags NOT APPROVED for production promotion.
Backend remains source of truth."*

No LP/GP economics, promote/waterfall logic, or IRR/MOIC figures were
ever actually computed or rendered here — the "panel" was pure
copy with no data binding. No sponsor/waterfall runtime engine exists
in the codebase that feeds this template (confirmed by searching for
any reference to this partial outside `main_web.py`'s
`_RUNTIME_SHEET_MAP` and `workspace_shell.html`'s tab include).

**Confirmed: not Run-backed, confirmed misleading as authoritative
output, replaced.**

### A second copy existed in `workspace_shell.html`

`app/templates/partials/workspace_shell.html` (the initial full-page
render path) previously **duplicated** the same static placeholder
markup inline for both `panel-distributions` and `panel-sponsor`,
separately from the `_sheet_distributions_partial.html` /
`_sheet_sponsor_partial.html` files used for the post-Run OOB refresh.
This meant the two render paths (first page load vs. after-Run
refresh) could silently drift out of sync. This PR removes the
duplication: `workspace_shell.html` now `{% include %}`s the same two
partial files used by the OOB refresh, so there is a single source of
truth for each panel's body going forward.

## What changed

`app/templates/partials/_sheet_distributions_partial.html`:

- **Removed**: the `.placeholder-panel` block (icon, title,
  description, and the audit-mode note quoting "R99/R102").
- **Added**: a single unavailable-state panel
  (`dist-unavailable-panel`), reusing the pre-existing
  `empty-state-notice` / `empty-state-notice--warn` CSS classes
  already defined in `static/styles.css` (no new CSS invented). Copy:
  *"Distribution output is not available yet. Run-backed distribution
  account results will be shown here once this section is connected
  to the model engine."*
- **Kept unchanged**: the panel header ("Distributions" title/
  description) and the `shared_runtime_block.html` include that
  precedes this partial in both render paths.

`app/templates/partials/_sheet_sponsor_partial.html`:

- **Removed**: the `.placeholder-panel` block (icon, title,
  description, and the audit-mode note quoting "R99/R102").
- **Added**: a single unavailable-state panel
  (`sponsor-unavailable-panel`), reusing the same
  `empty-state-notice` / `empty-state-notice--warn` CSS classes. Copy:
  *"Sponsor economics are not available yet. Run-backed sponsor cash
  flows and investor returns will be shown here once this section is
  connected to the model engine."*
- **Kept unchanged**: the panel header ("Sponsor / Equity" title/
  description) and the `shared_runtime_block.html` include that
  precedes this partial.

`app/templates/partials/workspace_shell.html`:

- **Replaced** the duplicated inline placeholder markup for
  `panel-distributions` and `panel-sponsor` with `{% include %}`
  statements pointing at the same two partial files used by the
  post-Run OOB refresh path, so both render paths show identical,
  honest content and cannot drift apart again.
- **Kept unchanged**: the `panel-distributions` / `panel-sponsor`
  tab/nav entries — the tabs still render. No existing "hide a whole
  product area" pattern was found in the codebase (same finding as
  PR6), so per the spec's preferred default this PR keeps both tabs
  and clearly labels unavailability rather than removing navigation.

`main_web.py` was **not** modified — `_RUNTIME_SHEET_MAP` already
pointed at the same two partial files before and after this change;
no route or context-shaping changes were needed because the old
panels never consumed route-supplied data to begin with.

## Are any displayed values genuinely Run-backed?

Yes, but only the content that was already there and untouched: the
`shared_runtime_block.html` block included immediately above both the
Distributions and Sponsor panel bodies (project-level IRR, Equity IRR,
DSCR, Senior Debt, Total Revenue, EBITDA, Total OPEX), which reads
real data from `sessionStorage.getItem("lastRuntimeSummary")` —
written by the existing post-`/run` flow and ultimately sourced from
`workspace_state.last_runtime_summary` in `main_web.py` (the same
mechanism documented and verified in PR6 for the Financial Statements
sheet). Neither the Distributions panel body nor the Sponsor panel
body itself contains any Run-backed value; both are now honest
unavailable-state panels rather than fabricated content.

## Why no new calculations were added

Per the Preview Architecture freeze and this PR's explicit guardrails,
no distribution-account engine, sponsor/waterfall engine, LP/GP
economics, or IRR/MOIC calculation exists to source real values from.
Inventing client-side or template-side numbers to fill these panels
would have been a worse outcome than an honest "not available yet"
message. This PR intentionally adds zero calculation logic anywhere.

## Tests

- `tests/test_product_gap_pr7_distribution_sponsor_reality_check.py`
  (new): covers all minimum-required PR7 behaviors — tab/screen still
  renders, old placeholder markup removed, unavailable-state panel
  present with the suggested copy, no banned jargon in the rendered
  (non-comment) template text, guardrail file paths untouched
  (`git diff main`), and the PR6 Financial Statements unavailable
  panel is unaffected.
- Existing tests referencing these two partials
  (`tests/test_phase_pr1_form_timing_fields.py`,
  `tests/test_phase_pr2_realized_gearing.py`,
  `tests/test_phase_pr3_taxonomy.py`,
  `tests/test_phase_stab1_run_refreshes_kpis.py`,
  `tests/test_phase_stab2_realized_gearing_scale.py`,
  `tests/test_phase_stab5_export_route_fix.py`,
  `tests/test_phase_stab6_new_project_first_run.py`,
  `tests/test_phase_stab7_generic_dashboard_parity.py`,
  `tests/test_phase_stab8_e2e_runtime_validation.py`,
  `tests/test_phase_ux1_inputs_badge_cleanup.py`,
  `tests/test_phase_ux2_active_sheet_refresh.py`,
  `tests/test_phase9_5_excel_like_project_workspace_ui_shell.py`) only
  assert that the two partial files exist, contain the word
  "Distributions"/"Sponsor", and are referenced from
  `_RUNTIME_SHEET_MAP` / the file-touch allowlists used by those
  prior-phase regression guards — all of which remain true after this
  change. No test deletions were needed.

## Pre-existing failures (not touched, not regressions)

Confirmed via `git stash` (clean diff against this branch's base
`751d88f`) that the following were already failing before this PR and
are unrelated to Distribution/Sponsor:

- `tests/test_phase9_5_excel_like_project_workspace_ui_shell.py`: 11
  pre-existing failures (sidebar/tab-list/layout assertions unrelated
  to this PR's scope).
- `tests/test_phase_pr2_realized_gearing.py::TestS2IndicativeGearingNotBound::test_s2_tests_still_pass`
  and `::TestS1S2S3M1PR1TestsPreserved::test_s1_s2_s3_m1_pr1_p1a_p1b_51f_all_pass`,
  and `tests/test_phase_pr3_taxonomy.py::TestS1S2S3M1PR1PR2TestsPreserved::test_all_prior_phase_tests_pass`:
  these cascade-invoke `tests/test_phase_s2_gearing_as_output.py` and
  `tests/test_phase_p1b_driver_status_badges.py`, which have
  pre-existing, unrelated failures (gearing/driver-badge UI, not
  Distribution/Sponsor).
- `tests/test_phase24g3_capex_sheet_readability.py`: pre-existing
  Python-version `SyntaxError` at collection time (f-string with
  backslash, invalid on this Python build) — present on a clean
  checkout of the base commit, unrelated to this PR.

Per the sprint-level baseline, the 3 previously-confirmed pre-existing
failures
(`test_c2_pr1_live_model.py::TestStaticWiring::test_no_recalculation_formula_dependency_or_saverun_code_in_live_model`,
`test_c2_pr7_backend_preview_endpoint.py::...::test_no_financial_engine_call`,
`test_c2_pr9_runtime_request_hardening.py::TestNoRegressionForAuthorizedOrNullProject::test_authorized_project_behaviour_matches_pr8_contract`)
remain, with no new failures introduced by this PR.

One transient regression was caught and fixed during development: the
first draft of the investigation comments in both new partial files
included a literal `{{ }}` inside an HTML comment, which Jinja parsed
as an (invalid) expression and raised a `TemplateSyntaxError` at
render time (caught by `tests/test_phase57pre_route_render_smoke.py`
and `TestRouteSmokePreserved::test_route_smoke_passes`). The comment
wording was changed to avoid Jinja delimiter characters; the fix is
included in the final diff.

## Confirmation: no financial logic, Run, Save, persistence, export, or Preview Architecture code changed

No formulas, distribution-account logic, sponsor/waterfall logic,
LP/GP calculations, IRR/MOIC calculations, preview payload fields, Run
output structures, or persistence changes were added or modified. The
change is template-markup-only. The following guardrailed paths were
**not** touched: `domain/*`, `app/waterfall_core.py`,
`app/input_adapter.py`, `app/project_factories.py`,
`static/modelling/runtime-renderer.js`, `app/services/model_preview.py`,
`app/services/preview_context.py`, `app/services/previews/*`, and
`main_web.py`.

## Future work (out of scope for this PR)

- Wiring a real, Run-backed distribution-account engine output
  (lockup, sweep, constraint schedule) to the Distribution panel is
  the natural follow-up, but is explicitly out of scope per the
  Preview Architecture freeze and the "no new distribution formulas"
  guardrail in this PR's spec.
- Wiring a real, Run-backed sponsor/waterfall engine output (LP/GP
  cash flows, IRR, MOIC) to the Sponsor panel is the natural
  follow-up, equally out of scope per the "no promote/waterfall
  logic" guardrail.
- Once such engines exist, the unavailable-state panels added here
  should be replaced with real per-period tables/cards sourced from
  that engine's output, following the same fc-grid presentation
  pattern already used elsewhere in the app (CAPEX/OPEX/Revenue
  sheets) and the precedent set in PR6 for Financial Statements.
