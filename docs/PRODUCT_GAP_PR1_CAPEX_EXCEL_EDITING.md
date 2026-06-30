# Product Gap PR1: CAPEX Real Excel Editing + Live Totals

## Summary

Makes the CAPEX sheet the first truly Excel-like sheet in the app:
typing a number while a CAPEX amount cell is the active cell now
starts editing immediately (no mouse click into the input required),
Enter/Tab (with Shift variants) commit-and-move like Excel, Escape
restores the prior value, and category subtotals / Hard CAPEX Total /
Total CAPEX update live in the DOM as you type.

This is a CAPEX-sheet-only UI behaviour change. No backend, no
financial-engine, no export, no persistence-write code was touched.

## Files changed

- **New:** `static/modelling/capex-sheet-live-totals.js` — the entire
  feature. CAPEX-specific, isolated from the generic C1 interaction
  layer (`static/interaction/*.js`) and from the C2 preview pipeline
  (`static/modelling/recalc-preview.js`, `live-model.js`,
  `runtime-renderer.js`). None of those files were modified.
- **Modified:** `app/templates/base.html` — added one `<script>` tag
  loading the new module, placed after the existing C1 layer scripts
  and before the C2 preview-pipeline scripts (load order does not
  matter functionally — the new module only reads
  `window.FcGridRegistry` / `window.FcCellIO` /
  `window.FcActiveCellManager` / `window.FcFocusManager` at event time,
  not at parse time — but this placement keeps it visually grouped
  with the rest of the spreadsheet interaction stack).
- **New:** `tests/test_product_gap_pr1_capex_excel_editing.py` —
  static/route-level tests (no browser).
- **New:** `tests/test_product_gap_pr1_capex_excel_editing_browser.py`
  — Playwright browser tests.
- **New:** this doc.

`app/templates/partials/sheet_capex.html` was **not** modified — its
existing markup (`data-fc-cell`, `data-fc-addr`, `data-fc-editable`,
`data-fc-kind`, `data-fc-raw`, `data-capex-row="cat-subtotal-<code>"`,
`data-capex-row="hard-capex-total"`, `data-capex-row="grand-total"`,
the `lig-row--data-financing` class on C.17/C.18 rows) already exposed
everything the new module needs.

## Typing / navigation behaviour implemented

State model: a CAPEX amount cell can be **active-but-not-editing**
(DOM focus is on the `<td data-fc-cell>` itself, per existing C1
`FcFocusManager`/`FcActiveCellManager` behaviour) or **editing** (DOM
focus has moved onto the cell's descendant `<input class="fc-input-
native">`).

- While **active-but-not-editing** on an editable CAPEX amount cell:
  - Typing a digit, `.`, or `-` immediately opens the cell's `<input>`
    and **replaces** its entire value with the typed character (never
    appends/inserts into the old value — exact Excel "first keystroke
    replaces" semantics), then moves DOM focus into the input.
  - Backspace/Delete opens the cell's `<input>` with its value cleared
    to `""` (does not silently no-op).
  - Any other key (notably the arrow keys, Home/End, Ctrl+Arrow) is
    left completely untouched — those continue to be owned exclusively
    by the pre-existing `static/interaction/keyboard-router.js`
    (`FcKeyboardRouter`), unchanged by this PR.
- While **editing** (focus genuinely on the `<input>`):
  - Every keystroke except Enter/Tab/Escape is handled natively by the
    `<input>` itself — this module does not intercept or double-handle
    them.
  - **Enter** commits and moves the active cell down one row.
  - **Shift+Enter** commits and moves the active cell up one row.
  - **Tab** commits and moves the active cell right one cell.
  - **Shift+Tab** commits and moves the active cell left one cell.
  - **Escape** restores the cell's pre-edit value and exits edit mode
    without committing.
  - A click/tab-away from the input by any other means (e.g. mouse
    click elsewhere) is treated as an implicit commit via the native
    `focusout`/blur path, mirroring ordinary `<input>` semantics.

Note on the CAPEX grid's column shape: `_line_item_grid.html` only
marks the **amount** `<td>` with `data-fc-cell` (the label/code `<td>`
are not separately navigable grid cells). This means each CAPEX row
has exactly one navigable column. Consequently "Tab right" / "Shift+Tab
left" within a row has no same-row target; per the pre-existing
`FcKeyboardRouter` contract (`FcGridRegistry.neighbors(cell, 'right')`
returns `null` when there is no column to the right), the active cell
simply stays where it is in that case. This module reuses that exact
existing neighbor-resolution behaviour rather than inventing new
column semantics — Tab still **commits** the edit in all cases, it
just has nowhere to move to in a single-column-per-row grid.

"Commit" always means: dispatch a final native `change` event on the
`<input>` (mirroring native blur-commits-value semantics) so the
pre-existing `FcLiveModel`'s `focusin`/`change`-based dirty tracking
(in `static/modelling/live-model.js`) observes the edit exactly as it
already does for a mouse-driven edit — this module adds no new dirty-
tracking code path of its own.

## Live CAPEX totals — exact rule

On every `input` event from a CAPEX amount cell's `<input>` (i.e.
live, per-keystroke, not just on commit), `recomputeLiveTotals()` in
`capex-sheet-live-totals.js` recomputes, purely as in-sheet DOM
text/attribute updates:

1. **Category subtotal** (e.g. the "C.01 Subtotal" row, located via
   `tr[data-capex-row="cat-subtotal-C.01"] [data-fc-cell]`): the sum of
   the live (possibly mid-edit, unsaved) values of every editable
   CAPEX amount cell whose `data-fc-addr` belongs to that category
   (parsed as the first two dot-segments of `capex!<code>.amount`,
   e.g. `capex!C.01.03.amount` → category `C.01`).

2. **Hard CAPEX Total (C.01–C.16)** (`tr[data-capex-row="hard-capex-
   total"] [data-fc-cell]`): the sum of the live values of **every**
   editable CAPEX amount cell across the whole `capex` grid (C.17/C.18
   sub-lines are never `data-fc-editable="true"`, so they are
   structurally excluded from this sum without any special-casing).

3. **Total CAPEX (C.01–C.18)** (`tr[data-capex-row="grand-total"]
   [data-fc-cell]`):

   > **Total CAPEX (live) = Hard CAPEX Total (live, as computed above)
   > + the value CURRENTLY DISPLAYED IN THE DOM for C.17 (Financing
   > Costs) + the value CURRENTLY DISPLAYED IN THE DOM for C.18
   > (Reserve Accounts), read verbatim from their existing read-only
   > `data-fc-raw` attributes on each `data_financing` row
   > (`tr.lig-row--data-financing [data-fc-cell][data-fc-raw]`).**
   >
   > C.17 and C.18 are **never** recomputed, estimated, or fabricated
   > client-side. If, defensively, a C.17/C.18 financing row is not
   > present in the DOM at all (this does not happen in the production
   > template, which always renders both — this is purely a defensive
   > fallback for unusual/partial markup), that row's contribution to
   > the live Total CAPEX is treated as exactly `0`, and the live total
   > is then equal to the Hard CAPEX Total alone. In other words: the
   > live Total CAPEX always sums **exactly the values currently
   > available/rendered**, and never substitutes a guessed or
   > previously-cached number for an absent C.17/C.18 row.

This means: as long as the page has fully rendered (the normal case),
the live Total CAPEX always equals (sum of live C.01–C.16 amount
cells) + (the same C.17 figure the backend rendered) + (the same C.18
figure the backend rendered) — i.e. it changes in lockstep with C.01–
C.16 edits while staying numerically consistent with whatever the
backend last computed for C.17/C.18.

## Save/Run separation guarantee

- `capex-sheet-live-totals.js` makes **zero** network requests of any
  kind (no `fetch`, no `XMLHttpRequest`, no `/model/preview` call, no
  `/scenarios/save` call, no `/run` call). It only reads/writes
  `textContent` and `data-fc-raw`/`value` attributes on already-
  rendered DOM nodes.
- It adds **no** new `name=`-attributed `<input>` elements and does
  not modify the existing ones rendered by `_line_item_grid.html`. The
  `Save` button's `hx-include="#main-form"` continues to submit exactly
  the same set of fields it always did — Save's behaviour, route, and
  persisted data are completely unchanged by this PR.
- `Run` (`POST /run`) is untouched — no code in this PR calls it,
  references it, or changes its behaviour.
- Browser tests (`test_save_not_triggered_by_typing`,
  `test_run_not_triggered_by_typing`) assert no request to
  `/scenarios/save` or `/run` happens from typing alone.

## Relationship to the existing CAPEX preview pipeline (C2-PR10)

The existing `#capex-total-preview-value` indicator (built in C2-PR10,
inside `static/modelling/recalc-preview.js` /
`static/modelling/runtime-renderer.js`, driven by `FcLiveModel`'s
debounced `change`-based dirty tracking and an actual
`POST /model/preview` round trip) is **completely untouched** by this
PR:

- `recalc-preview.js`, `runtime-renderer.js`, `live-model.js`,
  `recalc-executor.js`, and `dependency-graph.js` were not modified.
- No new `/model/preview` request/response field was added.
- This PR's live subtotal/total rendering is purely additive,
  synchronous, in-sheet DOM text — it runs on every `input` event
  (i.e. far more often, and entirely independently of the debounced
  preview flush), and is visually distinct from (and does not replace)
  the existing Operating Preview Panel's CAPEX total preview.
- The only interaction between the two: this PR's `_endEdit(true)`
  (commit path) dispatches a final `change` event identical to what a
  native blur on the `<input>` already produced before this PR — so
  `FcLiveModel`'s pre-existing `change`-listener-based dirty tracking,
  and therefore the existing preview flush/`#capex-total-preview-value`
  pipeline, continue to work exactly as before (verified by
  `test_capex_total_preview_panel_still_updates`).

## Tests added

- `tests/test_product_gap_pr1_capex_excel_editing.py` (static/route-
  level, no browser):
  - the new JS module is served and wired into `base.html`;
  - the module only ever references the `'capex'` grid id (never
    `'opex'`/`'revenue'`/`'debt'`/`'senior-debt'`/`'shl'`), so it
    structurally cannot affect other sheets;
  - the module's code (comments excluded) never references
    `/model/preview`, `fetch(`, or `FcRecalcPreview`;
  - none of `app/waterfall_core.py`, `app/input_adapter.py`,
    `app/project_factories.py`, or any file under `domain/` mentions
    the new module/feature;
  - C.17/C.18 rows remain `data-fc-editable="false"` and ordinary
    CAPEX lines remain editable for a user project (existing markup
    contract, unchanged);
  - rendering the CAPEX sheet twice for the same project produces
    byte-identical `<input>` values (no server-side state leak).

- `tests/test_product_gap_pr1_capex_excel_editing_browser.py`
  (Playwright, real-uvicorn-subprocess + real-auth + real-project
  fixture, mirroring `tests/test_c2_pr15_ebitda_preview_browser.py`):
  1. typing a digit on an active (un-clicked-into) CAPEX cell starts
     editing and replaces the value, with no mouse click into the
     input;
  2. Enter commits and moves the active cell down;
  3. Tab commits the edit (proven via the live subtotal changing) —
     see the column-shape note above for why it does not also move
     "right" in this single-column-per-row grid;
  4. Escape restores the pre-edit value;
  5. the category subtotal updates live as the cell is edited;
  6. Hard CAPEX Total updates live;
  7. Total CAPEX updates live;
  8. C.17/C.18 financing rows are never editable;
  9. typing alone never POSTs to `/scenarios/save`;
  10. typing alone never POSTs to `/run`;
  11. the existing `#capex-total-preview-value` indicator still
      updates correctly after a commit;
  12. ArrowDown still moves the active cell when not in edit mode (no
      regression to the pre-existing `FcKeyboardRouter`).

## Judgement calls / ambiguities resolved

- **Backspace/Delete UX**: the spec left the exact behaviour to
  implementer judgement, requiring only "must not silently no-op".
  This PR clears the cell's value and enters edit mode (matching
  Excel's own Delete-key behaviour on a selected, non-editing cell).
- **Tab/Shift+Tab "move right/left"** in a grid where each row has
  exactly one navigable column (the CAPEX grid's existing markup
  shape, unchanged by this PR): per the pre-existing
  `FcKeyboardRouter`/`FcGridRegistry.neighbors()` contract, there is no
  same-row target, so the active cell does not move sideways from
  Tab/Shift+Tab on a single-column grid — this PR reuses that existing
  contract rather than introducing new column-wrapping semantics for
  CAPEX, since changing `FcGridRegistry`'s neighbor logic would be
  exactly the kind of generic-C1-layer change explicitly out of scope
  for this CAPEX-only PR.
- **UI clarity label (spec section 4, optional)**: not added. The
  existing `capex-driving-copy` block above the grid and the existing
  preview-only banner near `#capex-total-preview-value`
  (`Preview only — not used for Run` styling already used elsewhere on
  this sheet, e.g. the add-line preview totals strip) already make it
  clear that on-screen totals are not yet saved/authoritative; adding
  another label directly under the now-fast-moving live subtotal cells
  was judged more likely to add visual noise than clarity, since those
  cells are physically inside the same grid as the Save-bound `name=`
  inputs and are visually distinguished only by row type (subtotal vs.
  data row), which the sheet already explains in the "CAPEX line items
  drive the model-level CAPEX total" driving-copy paragraph.
