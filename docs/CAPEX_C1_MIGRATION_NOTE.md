# CAPEX C1 Integration — First Real-Sheet Migration

## Scope

This migrates the production CAPEX sheet (`app/templates/partials/sheet_capex.html`,
the primary `project_ctx.capex_detail_items` rendering path) onto the
C1 Spreadsheet Interaction Layer (C1-PR1 through C1-PR9). This is the
**first real production sheet** to adopt the `data-fc-*` markup
contract — prior C1/C2 work was validated only against standalone test
fixtures.

It does **not** start C2-PR2, implement incremental recalculation or a
dependency graph, migrate any other sheet (OPEX, Inputs, Debt, Tax,
Revenue, etc.), or change persistence, export, calculations, or
project factories. No domain/financial-engine files were touched.

## What was implemented

### 1. C1 markup contract on the production CAPEX grid

`sheet_capex.html`'s primary (user-project) rendering path gained:

- grid root: `data-fc-grid="capex"` and `data-fc-scroll-container="true"`
  on the existing `#capex-single-sheet` wrapper.
- section-band and data rows: `data-fc-row="true"`.
- every cell that already existed (label/code/amount) gained
  `data-fc-cell="true"`, a deterministic `data-fc-addr`, `data-fc-kind`
  (`amount` | `subtotal` | `total`), and `data-fc-editable="true"|"false"`.
- amount cells additionally carry `data-fc-raw` holding the raw
  numeric value (not the formatted display string).

**Address scheme** — deterministic, derived from each line item's
existing stable `code` field, never display text:

| Cell | Address |
|---|---|
| editable line amount | `capex!{child.code}.amount` (e.g. `capex!C.01.01.amount`) |
| category subtotal | `capex!{cat.code}.subtotal` |
| hard-CAPEX subtotal | `capex!hard-capex-total.subtotal` |
| C.17/C.18 financing line | `capex!{child.code}.amount` (always non-editable) |
| grand total | `capex!grand-total.total` |

Subtotal, total, and C.17/C.18 financing cells are always
`data-fc-editable="false"`. Regular line-item amount cells are
`data-fc-editable` per the existing `is_user_project` flag — unchanged
behaviour, just now expressed in the C1 contract.

Only the primary rendering path (used by real user projects) was
touched. The legacy flat-`capex_items` fallback path was left
untouched — it is not exercised by real projects and is out of scope.

The shared `_line_item_grid.html` macro needed **no changes**: it
already renders arbitrary per-row/per-cell `attrs` dicts onto
`<tr>`/`<td>`, so the entire contract was added purely via
`sheet_capex.html`'s Jinja data construction.

### 2. Existing behaviour preserved

No existing `<input>`, `name=` attribute, draft-persistence wiring, or
totals calculation was replaced. The new `data-fc-*` attributes wrap
the existing markup; the existing draft-save/totals logic is
unmodified and continues to read/write the same inputs by `name=`.

### 3. `static/interaction/cell-io.js` (new — `window.FcCellIO`)

Shared cell read/write IO, extracted so Clipboard/Undo/Fill stop
duplicating value-read/value-write logic:

- `readValue(cell)`: prefers `data-fc-raw` (the raw numeric value) when
  present; otherwise reads the first `input`/`select`/`textarea`
  descendant's `.value`; otherwise falls back to the cell's trimmed
  text content.
- `writeValue(cell, value)`: refuses to write to a non-editable cell;
  writes to the first `input`/`select`/`textarea` descendant (firing
  `input`/`change` so existing listeners — draft persistence, dirty
  tracking — still fire), or to `textContent` if there is no real
  form control; also keeps `data-fc-raw` in sync when present.

`static/interaction/clipboard-controller.js`, `undo-manager.js`, and
`fill-controller.js` were repointed to call `FcCellIO.readValue`/
`writeValue` instead of each holding its own read/write logic.
`FcClipboardController.applyCellValue` remains exported as a
backward-compatible alias for `FcCellIO.writeValue`.

`app/templates/base.html` now loads `cell-io.js` before
`clipboard-controller.js`. The four existing C1 browser-test fixtures
(`tests/fixtures/c1_undo_redo_fixture.html`,
`c1_clipboard_controller_fixture.html`, `c2_live_model_fixture.html`,
`c1_fill_controller_fixture.html`) were updated to load it too, since
none of them load `base.html`.

### 4. Raw-value round-tripping

Amount cells' `data-fc-raw` carries the raw numeric value. Copy/paste
and fill read/write through `FcCellIO`, so a copy from one amount cell
and paste into another round-trips the raw value, not the formatted
display string. Covered by
`test_capex_c1_migration_browser.py::test_copy_paste_round_trips_raw_value`.

### 5. Two cross-cutting interaction-layer fixes required by this migration

All prior C1 fixtures used a `<td tabindex>` as the focusable cell
itself, with no real `<input>` descendant. CAPEX is the first real
target where the focusable element is a real `<input>` *inside* the
`[data-fc-cell]` `<td>`. That surfaced two pre-existing bugs that were
invisible against every prior fixture:

- **`_isGridCellFocused()`** (in `keyboard-router.js`,
  `clipboard-controller.js`, `undo-manager.js`, `fill-controller.js`)
  checked `document.activeElement.matches('[data-fc-cell]')` — true
  only when the focused element *is* the cell itself. Changed to
  `.closest('[data-fc-cell]')` so it also matches when focus is on a
  real input descendant.
- **`_currentActive()`** (same four files) checked
  `document.activeElement === active.cell.el` — same problem, one
  level up: it also needs to recognize focus landing on a descendant
  input of the active cell, not just the cell element itself. Changed
  to accept `el === active.cell.el || active.cell.el.contains(el)`.
- **`undo-manager.js`'s edit-capture** (`_onFocusIn`/`_onChange`)
  cleared its `_editBefore` baseline to `null` after every committed
  change, relying on a fresh `focusin` event to re-arm it. A real
  `<input>` that stays focused across two consecutive commits (no
  intervening blur) never re-fires `focusin`, so the second commit was
  silently dropped (no transaction recorded) and `Ctrl+Z` undid the
  wrong edit. Fixed by re-arming `_editBefore.value` to the just-committed
  value instead of clearing it.

These are minimal, surgical fixes (one-line condition changes plus a
one-line re-arm), not refactors — kept in scope because the Definition
of Done for this migration explicitly requires keyboard nav, undo, and
dirty-tracking to work on real CAPEX inputs, which they did not before
this fix despite all 195 prior C1/C2 fixture-based tests still passing
(the fixtures never exercised this code path).

## New tests

- `tests/test_capex_c1_markup_contract.py` — static (non-browser)
  assertions against `sheet_capex.html` rendered standalone with a
  hand-built `project_ctx.capex_detail_items` fixture (covers both
  `is_user_project=True` and the factory-reference/`False` case):
  grid root, scroll container, every cell has addr/kind/editable, no
  duplicate addresses, editable amount cells have `data-fc-raw` and a
  real input, subtotal/total/C.17/C.18 cells are non-editable,
  addresses are deterministic (not display text).
- `tests/test_capex_c1_migration_browser.py` — production-route
  Playwright smoke test. Runs the app as a real `uvicorn` subprocess
  (avoiding the documented asyncio/Playwright-sync-API conflict),
  authenticates via `app.auth.create_session_token()`, creates a real
  user project via `/projects/create`, and drives the real
  `/?project=...` route. Covers: grid presence, unique addresses,
  editable amount cells have real inputs + raw, click sets active
  cell, keyboard nav (`ArrowDown`) moves the active cell, an edit marks
  the cell dirty and undoable, `Ctrl+Z` reverts it, and copy/paste
  round-trips the raw value.

## Test results

- New tests: 8/8 (`test_capex_c1_migration_browser.py`) +
  10/10 (`test_capex_c1_markup_contract.py`) passing.
- Full C1 PR1–PR9 + C2-PR1 regression suite: 205/205 passing (zero
  regressions from the `_isGridCellFocused`/`_currentActive`/edit-capture
  fixes).
- `tests/test_phase57a_ui3_line_item_grid_capex_summary.py`: 53 passed,
  2 skipped, **2 pre-existing failures** unrelated to this change
  (`test_render_no_lig_input_when_not_user_project`,
  `test_financing_rows_readonly_in_factory_reference` — both fail on a
  missing "Factory Reference" string; confirmed via `git stash` to
  fail identically on unmodified `main`).

## Out of scope / deferred

- Any other sheet (OPEX, Inputs, Debt, Tax, Revenue, dashboard, etc.).
- C2-PR2, incremental recalculation, a dependency graph, or formula
  evaluation.
- Drag-fill handle, autofill series, formula references.
- Any change to `domain/*`, the financial engine,
  `app/waterfall_core.py`, `app/input_adapter.py`,
  `app/project_factories.py`, persistence, or export logic.

## Suggested next sheet

OPEX is the next-best candidate: it shares the same
`_line_item_grid.html` macro and a similarly small, line-item-shaped
structure, so the same address scheme and markup approach should carry
over directly.
