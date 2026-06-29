# C2-PR20 — Operating Preview Acceptance Test

## Summary

This PR adds exactly one new test file,
`tests/test_c2_pr20_operating_preview_acceptance.py`, containing two
comprehensive, real-route Playwright acceptance tests that exercise
the **entire** operating preview stack built across C2-PR10 (CAPEX),
C2-PR13 (Revenue), C2-PR14 (OPEX), C2-PR15 (EBITDA), and C2-PR16
(Operating Cash Flow) end to end, against a real running app (real
uvicorn subprocess, real auth, real project, real browser). No
production code is touched by this PR — it is purely a new test file
plus this document.

## Test 1 — full chain, happy path

`TestOperatingPreviewAcceptance::test_full_capex_revenue_opex_ebitda_ocf_chain_end_to_end`:

1. Creates a fresh user project via the same `_create_user_project`
   helper pattern used throughout the PR10–PR19 browser test suites.
2. Edits one editable CAPEX amount cell, settles its own debounce
   flush.
3. Edits one editable OPEX Budget cell, then immediately (without
   waiting for the OPEX flush to settle) switches to the Revenue tab
   and edits one editable Revenue cell — the exact "switch tab, edit,
   switch tab, edit" sequencing already used by
   `tests/test_c2_pr16_ocf_preview_browser.py::test_ocf_chains_through_revenue_opex_ebitda`
   (here: `test_ocf_equals_ebitda_when_both_revenue_and_opex_edited_in_same_flush`)
   to get both edits into the **same** debounce flush, which is
   required for EBITDA preview (and therefore Operating Cash Flow
   preview) to become non-null.
4. Waits for all five preview indicators to reach their `"patched"`
   state via the established `_wait_for_preview_value` helper.
5. Asserts:
   - CAPEX, Revenue, OPEX, and EBITDA preview values are all numeric.
   - EBITDA preview numerically equals Revenue preview minus OPEX
     preview, within a 0.05 float tolerance (parsed from the rendered,
     comma-formatted text).
   - Operating Cash Flow preview equals EBITDA preview **exactly**, by
     a textual (not just numeric) comparison — mirroring
     `test_c2_pr16_ocf_preview_browser.py`'s own
     `assert ocf_text == ebitda_text` assertion style, since OCF
     preview is defined as a verbatim passthrough of EBITDA preview
     (see `docs/C2_PR16_OPERATING_CF_PREVIEW.md`), not merely a
     numerically-close value.
   - No `/scenarios/save`, `/save-run`, or `/run` request was ever
     fired during the entire edit sequence (checked via a
     `page.on("request", ...)` listener spanning the whole test, the
     same pattern used in
     `tests/test_c2_pr14_opex_preview_browser.py::test_no_save_or_run_triggered_by_opex_edit`).
   - The workspace dirty-state indicator (`#workspace-strip-dirty`)
     still reads an "unsaved" state, confirming the preview edits never
     silently cleared dirty-state.
   - The Overview dashboard's KPI elements
     (`.dashboard-kpi-value`, `[data-p2min3-kpi-status]`) are
     byte-identical before and after the entire edit sequence —
     mirroring
     `tests/test_c2_pr14_opex_preview_browser.py::test_overview_kpis_byte_identical_pre_and_post_revenue_preview`'s
     exact assertion style.
   - All five preview indicator labels contain the established
     `"(unsaved)"` convention text.

This single test is the strongest available proof that the full
operating preview stack — CAPEX, Revenue, OPEX, EBITDA, and Operating
Cash Flow previews — works correctly together, end to end, in a real
browser, without ever touching Save, Run, or any authoritative model
output.

## Test 2 — failed preview request, values preserved

`TestOperatingPreviewAcceptance::test_failed_preview_request_preserves_last_valid_values`:

1. Establishes valid, numeric values for all five preview indicators
   (same edit sequence as Test 1).
2. Installs a route handler that aborts every subsequent
   `**/model/preview` request, using the exact
   `_install_failing_preview` helper pattern from
   `tests/test_c2_pr15_ebitda_preview_browser.py`.
3. Triggers one more OPEX edit (which will now fail at the network
   level) and waits for the OPEX preview indicator's
   `data-c2pr11-runtime-state` attribute to reach `"failed"`, using the
   established `_wait_for_runtime_state` helper.
4. Asserts all five preview indicators' rendered text is **unchanged**
   from their pre-failure values — proving the 5-state renderer's
   "never blank a previously-valid value on a transient failure"
   invariant (established in PR11 and re-confirmed by every PR10–PR16
   feature individually) holds for the entire chained stack together,
   not just for each preview in isolation.

## Why one comprehensive test, not several small ones

Each individual link in the chain (CAPEX/Revenue/OPEX sums,
EBITDA = Revenue − OPEX, OCF = EBITDA verbatim, failure-preserves-value)
is already covered by its own dedicated PR's test suite
(`test_c2_pr10_capex_total_preview*.py` through
`test_c2_pr16_ocf_preview*.py`). This PR's purpose, per its own name
("Operating Preview Acceptance Test"), is different: it is the single
acceptance-level proof that the **entire** stack — every link, in the
same browser session, in the same edit sequence — produces a
internally consistent, side-effect-free result, which no individual
PR's test suite was scoped to prove on its own.

## No real financial engine use

Confirmed: this PR adds only one new test file and this document. No
production code (`domain/*`, `app/waterfall_core.py`,
`app/input_adapter.py`, `app/project_factories.py`,
`static/modelling/*.js`, `static/app.js`, `main_web.py`,
`app/templates/**`) was modified.

## Tests added

- `tests/test_c2_pr20_operating_preview_acceptance.py` — 2 Playwright
  acceptance tests against a real uvicorn subprocess + real auth + real
  project, as described above.
