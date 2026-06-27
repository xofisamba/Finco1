# OPEX C1 Integration — Second Real-Sheet Migration

## Scope

This migrates the production OPEX detail sheet
(`app/templates/partials/sheet_opex_detail.html`, the
`{% include %}` target rendered into `<div class="tab-panel"
id="panel-opex">` in `workspace_shell.html`, driven by
`project_ctx.opex_detail_items`) onto the C1 Spreadsheet Interaction
Layer, using exactly the same `data-fc-*` contract proven on CAPEX
(`docs/CAPEX_C1_MIGRATION_NOTE.md`).

It does **not** start C2, implement recalculation or a dependency
graph, migrate any other sheet (Revenue, Tax, Inputs, Debt, Compare,
dashboard), or change persistence, export, calculations, or project
factories. No `domain/*` file, `app/waterfall_core.py`,
`app/input_adapter.py`, or `app/project_factories.py` was touched —
`app/ui/project_context.py` was only read (to confirm the `cat.code` /
`child.code` fields used for addressing), never modified.

## A key finding that shaped this migration

Unlike CAPEX — where real `<input>` elements already existed in
production before the C1 migration — **the real OPEX detail grid has
zero editable cells today.** Every cell (category totals, child
budget, inflation %, WHT %, every year value) renders as a read-only
`<span class="fc-cell-runtime" title="Line editing deferred">` in
*both* the `is_user_project=True` and `False` Jinja branches. This is
intentional, pre-existing, deferred functionality, not a bug.

The task's guardrails are explicit: "this is not a redesign," "do NOT
replace existing inputs," "everything must continue working exactly as
before." Adding new editable `<input>` elements where none exist today
would be a feature addition, not an interaction-layer wrapper. So this
migration applies the full C1 markup contract to every OPEX cell but
sets `data-fc-editable="false"` on all of them, faithfully matching
current production behaviour — mirroring how CAPEX already marks its
own subtotal/total/financing cells permanently non-editable, just
extended here to the entire grid since none of it is editable yet.

Practical consequence: Active Cell, Keyboard Navigation, Selection,
and read-only Copy all work fully on OPEX. Paste, Undo, and Fill
correctly **no-op** against every OPEX cell — `FcCellIO.writeValue`
already refuses to write to a cell whose `cell.editable` is false, so
no JS changes were needed for this; it is covered explicitly by new
tests (see below) asserting the no-op rather than skipping it. When a
future PR adds real OPEX line editing, those cells' `data-fc-editable`
flips to `"true"` and Undo/Fill/dirty-tracking activate against them
automatically — no interaction-layer changes will be required then,
either.

## What was implemented

### 1. C1 markup contract on the production OPEX detail grid

`sheet_opex_detail.html` gained:

- grid root + scroll container: `data-fc-grid="opex"
  data-fc-scroll-container="true"` on the existing
  `#opex-grid-scroll` (`.fc-grid-scroll-wrapper`) div — the grid
  itself is split across multiple `<tbody>` elements (one per
  category) inside one `<table>`; `FcGridRegistry.scan()` already
  supports `data-fc-grid` on any container and `[data-fc-row]` rows
  resolved via `.closest()`, so this needed no registry changes.
- category total rows and child rows: `data-fc-row="true"` (the
  existing `onclick="opexToggleCategory(...)"` collapse handler on
  category rows is untouched).
- addressable cells gained `data-fc-cell="true"`, a deterministic
  `data-fc-addr`, `data-fc-kind`, `data-fc-editable="false"`, and
  `data-fc-raw` holding the raw numeric value.

**Address scheme** — deterministic, derived from each category's/
child's existing stable `code` field (`cat.code`, `child.code` from
`project_ctx.opex_detail_items`, e.g. `"B.01"`, `"B.01.01"`), never
display text:

| Cell | Address |
|---|---|
| child budget | `opex!{child.code}.budget` (e.g. `opex!B.01.01.budget`) |
| child inflation % | `opex!{child.code}.inflation` |
| child WHT % | `opex!{child.code}.wht` |
| child per-year value | `opex!{child.code}.Y{y}` (e.g. `opex!B.01.01.Y1` … `Y25`) |
| category per-year subtotal | `opex!{cat.code}.Y{y}.subtotal` (e.g. `opex!B.04.Y1.subtotal`) |

Only label/code/notes columns (which carry no numeric value) were left
without the contract, mirroring how CAPEX's migration also left its
label/code columns unaddressed — only value-bearing cells need an
address.

The legacy flat-summary `<details class="opex-legacy-summary">` block
at the bottom of the same file (a separate, always-read-only reference
table built from `project_ctx.opex_items`) was left untouched — it is
not part of the primary grid and out of scope.

### 2. Existing behaviour preserved

No `<input>`, `name=`, draft-persistence wiring, year-range toggle
(`opexSetYearRange`), display-mode toggle (`opexSetDisplayMode`),
category collapse/expand (`opexToggleCategory`/`opexExpandAll`/
`opexCollapseAll`), or sticky-column CSS was changed. The `<script>`
block and toolbar buttons are byte-identical to before this migration;
only `data-fc-*` attributes were added to existing `<tr>`/`<td>`
elements.

### 3. `FcCellIO` reused as-is

No changes to `static/interaction/cell-io.js` were needed.
`readValue()` already reads `data-fc-raw` when present (every OPEX
amount/subtotal cell has one); `writeValue()` already refuses to write
to a cell whose `cell.editable` is false — exactly the no-op OPEX
needs, with zero OPEX-specific code.

### 4. Cross-cutting interaction-layer fixes required

None. The `_isGridCellFocused()` / `_currentActive()` `.closest()`/
`.contains()` fixes and the `undo-manager.js` re-arm fix (both from
the CAPEX migration) already cover OPEX's focusable cells. OPEX cells
have no descendant `<input>` at all (focus lands directly on the
`<td>`, which is given `tabindex` by `FcGridRegistry`/`FcFocusManager`
exactly as every prior C1 fixture's `<td tabindex>` pattern did), so
this migration did not surface any new edge case.

## New tests

- `tests/test_opex_c1_markup_contract.py` — static (non-browser)
  assertions against `sheet_opex_detail.html` rendered standalone with
  a hand-built `project_ctx.opex_detail_items` fixture (covers both
  `is_user_project=True` and `False`): grid root, scroll container,
  every cell has addr/kind/editable, no duplicate addresses, all cells
  are `data-fc-editable="false"`, addresses are deterministic (built
  from `cat.code`/`child.code`, never display text), category subtotal
  and child amount address shapes match the scheme above, deterministic
  ordering across repeated renders. 12/12 passing.
- `tests/test_opex_c1_migration_browser.py` — production-route
  Playwright smoke test, modeled on
  `tests/test_capex_c1_migration_browser.py` (real `uvicorn`
  subprocess, `app.auth.create_session_token()`, a real user project
  seeded from the Oborovo template via `/projects/create` so
  `opex_detail_items` is the full detailed structure, the real
  `/?project=...` route, `window.switchTab('opex')` to reveal the
  hidden tab panel). Covers: grid presence, unique addresses, all
  cells non-editable, all cells have raw values, click sets active
  cell, keyboard nav (`ArrowDown`) moves the active cell, Shift+Arrow
  extends the selection, copy reads the raw value, paste onto a
  non-editable cell is a no-op, a direct `FcCellIO.writeValue` attempt
  does not enable Undo, and the OPEX-specific year-range toggle and
  category collapse/expand continue working unmodified, plus an
  `FcGridRegistry.scan()` re-scan (the same call `FcSwapLifecycle`
  makes after a real htmx swap) leaves the grid correctly registered.
  13/13 passing.

## Test results

- New tests: 13/13 (`test_opex_c1_migration_browser.py`) + 12/12
  (`test_opex_c1_markup_contract.py`) passing.
- Full C1 PR1–PR9 + C2-PR1 + CAPEX C1 + OPEX C1 regression suite:
  293/293 passing (2 skipped — optional browser-dependency guards),
  zero regressions.
- `tests/test_phase57a_ui3_line_item_grid_capex_summary.py`: same 2
  pre-existing failures as documented in
  `docs/CAPEX_C1_MIGRATION_NOTE.md`
  (`test_render_no_lig_input_when_not_user_project`,
  `test_financing_rows_readonly_in_factory_reference`), confirmed via
  `git stash` to fail identically on unmodified `main` — unrelated to
  this change (a CAPEX-template assertion, not touched here).
- `tests/test_phase24g3_capex_sheet_readability.py` fails to even
  collect on unmodified `main` (a pre-existing Python 3.11 f-string
  syntax error unrelated to any C1 work) — confirmed via `git stash`,
  excluded from the regression run, not touched by this change.

## Out of scope / deferred

- Real OPEX line editing (adding `<input>` elements and flipping
  `data-fc-editable` to `"true"`) — a separate, future PR; this
  migration's job was the interaction-layer contract, not new
  editability.
- Any other sheet (Revenue, Tax, Inputs, Debt, Compare, dashboard).
- C2, incremental recalculation, a dependency graph, or formula
  evaluation.
- Any change to `domain/*`, the financial engine,
  `app/waterfall_core.py`, `app/input_adapter.py`,
  `app/project_factories.py`, persistence, or export logic.

## Suggested next sheet

Once real OPEX line editing ships and this grid gains its first real
`<input>`, Debt or Revenue are reasonable next candidates for the C1
contract — both are similarly line-item/period shaped to OPEX's
category × year grid.
