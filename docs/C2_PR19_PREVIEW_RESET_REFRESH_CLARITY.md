# C2-PR19 — Preview Reset / Refresh Clarity

## Summary

This PR adds no new button, no new persistence/storage mechanism, and
no new client-side caching of preview values. It confirms — with new
browser tests against the real running app — that preview state
behaves the way the existing architecture already implies it must:

1. Preview values are purely in-memory client-side runtime state
   (`static/modelling/live-model.js` / `recalc-preview.js` /
   `runtime-renderer.js`), never written to `localStorage`,
   `sessionStorage`, a cookie, or any server-side store. A full page
   reload therefore always resets all five preview indicators to their
   initial idle placeholder ("—").
2. Save never relabels a preview value as authoritative — the
   "(unsaved)" (or, for Operating Cash Flow, "non-authoritative")
   labeling convention established by PR10/PR13/PR14/PR15/PR16 is
   present on all five indicators both before and after a real Save.
3. The authoritative Overview KPI dashboard is computed by the real
   Save/Run pipeline and is structurally independent of whatever
   values happen to be sitting in the preview badges at the time.

## Confirmed: no new caching/persistence mechanism was added

A grep of the diff for this PR confirms no new `localStorage`,
`sessionStorage`, cookie, or server-side write was introduced anywhere
in `static/modelling/*.js`, `static/app.js`, or `main_web.py`. If any
such mechanism already existed before this PR, it was left exactly
as-is; this PR's job was only to prove (via tests) that the existing,
purely-client-side, refresh-resets-everything behaviour holds — not to
add, remove, or alter any storage mechanism.

## Behaviour confirmed by test, point by point

### 1. Full reload resets all five preview indicators

`tests/test_c2_pr19_preview_reset_refresh_clarity_browser.py::TestPreviewNotRestoredAfterReload::test_all_five_previews_reset_to_idle_after_full_reload`
edits CAPEX, then OPEX+Revenue (in the same debounce flush, so EBITDA
and Operating Cash Flow previews also become numeric), confirms all
five indicators (`#capex-total-preview-value`,
`#revenue-total-preview-value`, `#opex-total-preview-value`,
`#ebitda-preview-value`, `#operating-cf-preview-value`) are non-blank/
numeric, then calls `page.reload()` (a full browser navigation, not an
htmx partial swap) and asserts every one of the five has returned to a
non-numeric placeholder state — proving none of them were restored
from any cache.

### 2. Preview badges stay labeled "(unsaved)" after Save

`tests/test_c2_pr19_preview_reset_refresh_clarity_browser.py::TestPreviewLabelStaysUnsavedAfterSave::test_preview_badges_remain_labeled_unsaved_after_save`
edits a CAPEX cell, clicks the real `#btn-save` button, waits for the
real `/scenarios/save` (or `/save-run`) response, and asserts every one
of the five preview indicator labels still contains `"(unsaved)"` (the
exact wording already established in
`app/templates/partials/workspace_shell.html`) — Save is never allowed
to silently promote a preview value to "saved"/authoritative status.

### 3. Overview KPIs are structurally unaffected by Save+Run while a preview is showing

`tests/test_c2_pr19_preview_reset_refresh_clarity_browser.py::TestOverviewKpisUnaffectedBySaveAndRun::test_overview_kpis_unaffected_by_preview_state_after_save_and_run`
edits CAPEX, Saves, optionally clicks the real Run button
(`#btn-run-model-sidebar`, gated on `disabled` exactly like the
existing PR2 dirty-state tests), and confirms the Overview KPI element
set is still present, well-formed, and the same count before and after
the round trip — i.e. the authoritative dashboard pipeline runs
independently of, and is not corrupted by, the preview badges' current
non-authoritative contents. (Clicking the real Run button exercises
some pre-existing, unrelated app chrome — e.g. chart re-rendering on a
freshly-Run Overview tab — that triggers a benign, already-existing
Content-Security-Policy console warning unrelated to this PR's preview
isolation guarantee; this test intentionally does not assert against
`page_errors` for that reason, to avoid coupling an unrelated,
pre-existing warning to this PR's scope.)

### 4. The "(unsaved)" labeling convention is present and consistent

`tests/test_c2_pr19_preview_reset_refresh_clarity_browser.py::TestUnsavedLabelingConventionConsistent::test_all_five_preview_labels_use_the_unsaved_convention`
reads each of the five preview indicator labels directly from the live
page and asserts each contains the exact, already-established
`"(unsaved)"` substring — the same convention documented in
`docs/C2_PR10_CAPEX_TOTAL_PREVIEW.md` / `C2_PR13_REVENUE_PREVIEW.md` /
`C2_PR14_OPEX_PREVIEW.md` / `C2_PR15_EBITDA_PREVIEW.md`. (Operating Cash
Flow's label also reads "(unsaved)" verbatim — see
`app/templates/partials/workspace_shell.html`'s
`#operating-cf-preview .runtime-status-indicator__label`, which reads
"Operating cash flow preview (unsaved):" — PR16's stronger
"non-authoritative"/"placeholder" wording lives in the element's
`aria-label`, not its visible label text, so no new wording was
invented here.)

## No labeling/markup change was needed

Reading the exact current label text confirmed all five indicators
already use the "(unsaved)" convention consistently (see above) — so
no markup change to `workspace_shell.html` was required by this PR.
This PR is therefore purely additive (new tests + this document); no
production code was touched.

## Tests added

- `tests/test_c2_pr19_preview_reset_refresh_clarity_browser.py` — 4
  Playwright tests against a real uvicorn subprocess + real auth + real
  project, covering all four required-behaviour points above.

## No real financial engine use

Confirmed: this PR adds only one new test file and this document. No
production code (`domain/*`, `app/waterfall_core.py`,
`app/input_adapter.py`, `app/project_factories.py`,
`static/modelling/*.js`, `static/app.js`, `main_web.py`,
`app/templates/**`) was modified.
