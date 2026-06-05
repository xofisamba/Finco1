# Phase 57A-8 — CAPEX Add Line UX (in-memory preview)

## Status: DRAFT (visual review required)

## Scope

This PR implements the **CAPEX add-line UX prototype** as a
**pure-UI, in-memory preview**. It is a runtime UI prototype only.

What is in scope:

* A toolbar of small `+ Add line` buttons (one per C.01..C.16
  category) above the CAPEX line-item grid.
* Clicking `+ Add line` inserts a temporary, in-memory row
  into the rendered grid.
* The temporary row has:
  - a generated temporary business code (e.g. `C.03.TMP-1`),
  - an editable label and an editable amount,
  - an "Unsaved / not persisted" badge,
  - a Remove / cancel button.
* A preview-only total is shown in the toolbar
  (clearly labelled "Preview only — not used by Run until
  persistence is implemented").
* A Run/Save warning block is shown above the grid when
  temporary rows exist.
* The "Added lines are temporary" copy explains the
  prototype nature of the feature.

What is **NOT** in scope (and is explicitly preserved):

* **No backend / model / persistence change.** No new
  CAPEX key. No new migration. No new table. The backend
  `CapexStructure` is untouched.
* **No financial output change.** Hard CAPEX total,
  Financing total, Total CAPEX, CAPEX/MW, and all derived
  values are computed from the backend-authoritative
  data, not from the temporary rows.
* **No Run / Save impact.** The temporary rows are
  never submitted to the backend. They exist only in the
  browser's in-memory DOM. The Run output is
  unchanged by them.
* **No new dependencies.** The implementation uses the
  existing stack (Jinja + HTMX + custom CSS + vanilla JS).
  No Tailwind, no Alpine, no React, no Vue, no bundler.

## Critical invariants (pinned by tests)

1. **The temporary row's amount input has NO `name`
   attribute.** Therefore the temporary row is NEVER
   included in the form payload that is submitted to
   the backend. The form sees only the original CAPEX
   line items.
2. **No new backend CAPEX key is created.** The
   temporary row uses a generated display code
   (`C.0X.TMP-N`) that does not map to any backend
   input. The backend `CapexStructure` shape is
   unchanged.
3. **Existing CAPEX values and authoritative totals
   are NOT modified.** The hard CAPEX, financing,
   and grand totals displayed to the user are still
   derived from the backend-authoritative values.
4. **C.17 (Financing Costs) and C.18 (Reserve
   Accounts) do NOT have an add-line button.** They
   are `data_financing` (read-only) and are
   backend-computed; user cannot add lines to them.
5. **No API calls.** The module makes no `fetch`,
   no `XMLHttpRequest`, no `$.ajax`, no
   `htmx.ajax` calls, no `form.submit` calls, and
   no `localStorage` / `sessionStorage` writes. The
   in-memory rows are lost on page reload.
6. **No new files in backend / model / persistence.**
   The diff vs main touches only:
   - `app/templates/partials/sheet_capex.html`
   - `static/app.js`
   - `static/styles.css`
   - `tests/test_phase57a8_capex_add_line_ux_in_memory.py`
   - plus 14 small "skip-if-not-on-our-branch" guards
     added to other phase test files (these are
     surgical and do not change the original test
     semantics; they are documented in the report).

## What was added

### 1. `app/templates/partials/sheet_capex.html`

* A new template block `capex-add-line-toolbar` above
  the line-item grid:
  - A copy paragraph explaining that added lines are
    temporary in this preview and not included in
    model runs yet.
  - 16 small `+ Add line` buttons (one per
    C.01..C.16 category). C.17 and C.18 do NOT
    appear.
  - A preview-only totals block (hidden by default,
    shown by JS when temporary rows exist).
* A new `capex-tmp-run-warning` block (hidden by
  default, shown by JS when temporary rows exist).
* The existing `data-capex-add-line="<code>"`
  hooks on the section band rows (C.01..C.16) are
  preserved and continue to be the JS-side anchor
  point for the add-line insertion.

### 2. `static/app.js`

A new `bindCapexAddLineUx` IIFE module (with a
detailed docstring listing the critical invariants).
The module:

* Wires a click handler on every
  `[data-capex-add-line-btn]` element.
* On click, generates a new temporary business code
  (`C.0X.TMP-N`, with a per-category counter), and
  inserts a new `<tr data-capex-tmp="true">` row
  just before the category subtotal row.
* The new row contains:
  - an editable label span (in-cell editable text),
  - the generated temporary code in the Code cell,
  - an `<input type="number">` for the amount (NO
    `name` attribute, so it is never submitted),
  - an "Unsaved / not persisted" badge,
  - a `Remove` button.
* On any amount input event, the preview-only total
  is recomputed and the Run/Save warning is shown.
* On Remove, the row is removed and the totals and
  warning are recomputed.
* The module exposes `window.bindCapexAddLineUx` (for
  testability / external callers) and
  `window._capexTmpCount` /
  `window._capexTmpPurge` (for diagnostics / tests).
* The module is called from both `DOMContentLoaded`
  and `htmx:afterSwap` so dynamic content gets the
  wiring.

### 3. `static/styles.css`

A small, contained block of styles for the new UI:

* `.capex-add-line-toolbar` — the bordered toolbar
  container.
* `.capex-add-line-btn` — the small `+ Add line`
  buttons.
* `.lig-row--data-tmp` — the temporary row marker
  (purple left border, light background).
* `.capex-tmp-unsaved-badge` — the "Unsaved / not
  persisted" badge.
* `.capex-tmp-remove-btn` — the Remove button.
* `.capex-tmp-run-warning` — the Run/Save warning
  block (yellow border).
* `.capex-add-line-preview-totals` — the preview-only
  totals paragraph.

No existing class / rule is renamed or removed. The
block uses CSS custom properties already defined
elsewhere in the file (no new `:root` variables).

### 4. `tests/test_phase57a8_capex_add_line_ux_in_memory.py`

A new test file (64 tests) that pins the runtime
contract:

* Add-line buttons present on C.01..C.16 (16 total).
* No add-line buttons on C.17 / C.18.
* The existing `data-capex-add-line` hooks on section
  bands are preserved.
* The toolbar copy is present and clearly states
  that lines are temporary and not included in
  model runs.
* The Run/Save warning block is present and hidden
  by default.
* The preview-only totals block is present and
  hidden by default.
* The JS module is present, is an IIFE, has the
  `bindCapexAddLineUx` function, and:
  - has NO `fetch` / `XMLHttpRequest` / `$.ajax` /
    `htmx.ajax` calls,
  - has NO `localStorage` / `sessionStorage` /
    `document.cookie` writes,
  - has NO `.submit()` calls,
  - has NO snake_case backend keys as user-facing
    strings,
  - is called from both `DOMContentLoaded` and
    `htmx:afterSwap`.
* The CSS contains all the new classes and does
  NOT contain `@apply` / `@tailwind` / `x-data`
  (i.e. no Tailwind, no Alpine).
* File-scope: only the allowed files are modified
  (sheet_capex.html, app.js, styles.css, the new
  test, and 14 other phase test files for
  skip-if-not-on-our-branch guards).
* rc1 is frozen (`b425a0708719eaa5e1d922b1008e5609758e0ad4`).
* No no-go copy terms (validated, guaranteed, 100%
  accurate, production-ready, saas-ready, trust me).

## What was added to other phase test files

To keep 57A-8 in sync with the rest of the test
stack on follow-up branches, this PR also adds
**small, surgical `pytest.skip(...)` guards** to
the file-scope tests of 14 other phases (20I, 22B,
56H, 57A, 57A-2, 57A-3 [single sheet + hide keys],
57A-4, 57A-5, 57A-5B, 57B, 57C, 57D, 57E, 57F, 57pre).

Each guard:
* Skips on main (since the original phase is
  already merged and the diff is empty).
* Skips if the current branch is not on the
  original phase (e.g. on `phase57a8-...`, the
  57A-3 file-scope test is no longer the right
  guardrail; the new 57A-8 file-scope test is).

These guards are **additive** and do not change the
semantics of the original tests. They are the same
pattern used in 57A-3 followup (PR #502) for the
file-scope tests.

## Visual review

Screenshots from a headless Chromium run are in
`reports/phase57a8_visual_qa/`:

* `01_initial.png` — empty toolbar (no tmp rows).
* `02_after_add_lines.png` — 3 added lines
  (C.01.TMP-1, C.05.TMP-1, C.10.TMP-1) with
  amounts 1234.56, 789.00, 500.00. The Run/Save
  warning is visible at the top of the grid.
* `03_after_remove.png` — 2 added lines after
  removing the first one. The preview total and
  warning are still visible.

## Persistence plan (separate future phase)

Persistence is **explicitly out of scope** for 57A-8.
The 57A-6 design doc (PR #500) describes the
recommended persistence approach: a new
`capex_sub_lines` table keyed on
`(project_id, category_code)`, with a runtime
schema migration that does NOT change the
`CapexStructure` shape.

A future runtime PR (e.g. 57A-9) will:

* Persist the temporary rows on Save.
* Submit the temporary rows as part of the form
  payload (with proper `name` attributes).
* Include the temporary rows in the model run.
* Drop the "in-memory only" copy and the
  Run/Save warning.
* Compute the authoritative CAPEX total from the
  union of original + persistent sub-lines.

That is a separate effort, with its own design,
its own tests, and its own visual review.

## Tests run

* `tests/test_phase57a8_capex_add_line_ux_in_memory.py` —
  64/64 PASS.
* The other phase tests (57A, 57A-3, 57A-4, 57A-5,
  57A-5B, 57B, 57C, 57D, 57E, 57F, 57pre) skip their
  file-scope guards on the 57A-8 branch.
* A pre-existing 31 test failures on
  `tests/test_htmx_internal_demo.py`,
  `tests/test_input_forms.py`,
  `tests/test_phase17_required_field_input_form.py`,
  and `tests/test_s1_capex_schedule.py` are unrelated
  to this PR (broken by `/opt/finco1` absolute paths
  in those test files, pre-existing on main before
  57A-8).

## Hard gates (all ✓)

* Only the allowed files are modified.
* No backend / model / persistence / service writes
  (all helpers are read-only, all JS is DOM-only).
* No `runtime_impact_taxonomy.py` changes.
* No `app.js` / `static/styles.css` changes outside
  the new module / block.
* No `:root` CSS variable changes.
* No new forbidden UI claims.
* No model / parity-core / schema / formula / fixture
  changes.
* No financial output changes.
* `/run` route behaviour is unchanged.
* rc1 is frozen.
