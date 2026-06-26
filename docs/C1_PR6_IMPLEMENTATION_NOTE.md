# C1-PR6: Selection Model Foundation — Implementation Note

## Scope

This PR adds a **selection model foundation** on top of C1-PR1
(GridRegistry + InteractionEngine), C1-PR2 (ActiveCellManager), C1-PR3
(FcSwapLifecycle), C1-PR4 (FcFocusManager), and C1-PR5
(FcKeyboardRouter). Finco One now tracks exactly one selection
globally — a rectangular range anchored to a fixed cell and extending
to the active cell — and renders it with a single CSS class.

It does **not** add clipboard, copy/paste, undo/redo, fill-down/drag
fill, a context menu, formula editing, or recalculation. Those remain
out of scope (see "Deferred" below and C1-PR7).

## What was implemented

### `static/interaction/selection-manager.js` (`window.FcSelectionManager`)

A new, additive module, loaded after `keyboard-router.js` and before
`app.js`. It holds **no parallel grid or active-cell state** — every
operation reads `FcActiveCellManager.getActiveCell()` and
`FcGridRegistry.getGrid()`/`getAddr()` fresh, so it stays correct
across htmx swaps without any state of its own to reconcile.

**Selection state model** (exactly one, globally):

```
{ gridId, anchor: cellRecord, active: cellRecord, cells: [cellRecord, ...] }
```

- `anchor` — the cell selection extension is measured from; fixed
  until a new single-cell selection starts.
- `active` — the current active cell (mirrors
  `FcActiveCellManager.getActiveCell()`); the moving corner of the
  range.
- `cells` — every cell in the rectangle between `anchor` and `active`
  (inclusive), computed fresh from `grid.rows` each time.

**Public API:**

| Function | Behaviour |
|---|---|
| `selectSingle(gridId, cell)` | collapses the selection to one cell (anchor === active) |
| `extendTo(gridId, cell)` | extends the range from the existing anchor to `cell`; falls back to `selectSingle` if there is no existing selection in that grid |
| `collapseToActive()` | reads the current active cell and calls `selectSingle`, or clears if there is none |
| `clearSelection()` | removes the CSS class from all selected cells and drops the selection |
| `getSelection()` | returns `{ gridId, anchorAddr, activeAddr, addresses }` or `null` |

**Rendering:** every cell in the current rectangle gets the
`fc-selected-cell` CSS class (`static/styles.css`, immediately after
the existing `.fc-active-cell` rule); the previous selection's cells
have the class removed first, so exactly one selection is ever visible
at a time, across any number of grids.

**Mouse integration:** a `click` listener checks only whether the
click landed on `[data-fc-cell]` at all, then calls
`collapseToActive()`. It relies on `active-cell.js`'s own click
listener (registered earlier, since `selection-manager.js` loads
later) having already updated the active cell by the time this handler
runs — the same "shared event, load-order-dependent" pattern already
used by `focus-manager.js` in PR4. This module never calls
`preventDefault()`/`stopPropagation()`, so click/dblclick/typing
behaviour is completely unaffected.

**Keyboard integration (`static/interaction/keyboard-router.js`):**
rather than duplicating PR5's guard/movement logic, this PR makes one
small, additive edit to `keyboard-router.js`: after it moves the
active cell, it now also calls `FcSelectionManager.extendTo()` (for
`Shift+ArrowRight/Left/Down/Up`) or `FcSelectionManager.collapseToActive()`
(for every other handled move — `Enter`, `Tab`, `Home`, `End`,
`Ctrl+Arrow`, and plain `Arrow*`). `FcSelectionManager` is optional —
`keyboard-router.js` still works unchanged (active cell + focus only)
if it isn't loaded. No other line of `keyboard-router.js` changed from
PR5.

**Swap reconciliation:** listens to `fc:gridsScanned`/`fc:engineReady`
(registered after `active-cell.js`/`swap-lifecycle.js`/
`focus-manager.js`, so by the time it runs, those modules have already
resolved or cleared the active cell for the swap):

- no active cell survives → `clearSelection()`
- active cell survives but in a different grid than the current
  selection, or the anchor's address no longer resolves → collapse to
  a single-cell selection at the active cell
- both anchor and active cell resolve in the same grid → rebuild the
  rectangle from their freshly re-scanned cell records

This is a deliberate simplification of "restore selection if all
selected cells still exist": rather than tracking/verifying every
individual address in a (potentially large) range, only the two
corners (anchor, active) are checked. This is robust to row/column
reordering within a grid and avoids a second list of addresses to keep
in sync, at the cost of restoring based on position rather than a
strict per-cell existence check.

### `app/templates/base.html`

One new `<script defer>` tag for `selection-manager.js`, inserted
after `keyboard-router.js` and before `app.js`, matching the existing
loading order convention.

### `static/styles.css`

One new rule, `.fc-selected-cell { background-color: rgba(26, 86, 219, 0.08); }`,
added immediately after the existing `.fc-active-cell` rule. Purely
visual; does not affect layout or any other existing class.

## What was intentionally deferred

- **Multi-range / Ctrl-click selection** — not implemented; exactly
  one contiguous range exists globally, per the task's explicit scope.
- **Shift+Click range extension** — only `Shift+Arrow` (keyboard) was
  wired to extend the range; a `Shift+Click` on a second cell still
  collapses to a single-cell selection at that cell, identical to a
  plain click.
- **Home/End/Ctrl+Arrow as selection-extending moves** — only the four
  plain `Arrow*` keys extend the range when held with Shift (see
  `ARROW_KEYS` in `keyboard-router.js`); `Shift+Home`, `Shift+End`, and
  `Shift+Ctrl+Arrow` still collapse the selection, mirroring their
  existing PR5 meaning (Home/End's own row-boundary jump, Ctrl+Arrow's
  own edge jump) rather than gaining a new extending behaviour.
- **Clipboard (copy/paste/cut), undo/redo, fill-down/drag fill** — not
  implemented anywhere in this module.
- **Context menu, formula editing, recalculation** — not touched.
- **Retrofitting real template markup** — as with PR1-PR5, no
  production grid in `app/templates/*` is given `data-fc-grid`/
  `data-fc-cell` attributes yet, so this PR's behaviour is currently
  only exercised via the dedicated fixture; it is exclusively
  additive/no-op for any page that doesn't yet use the markup
  contract.

## Dependency surface for C1-PR7 (Clipboard)

PR7 can build directly on this PR without re-implementing range
computation:

- `FcSelectionManager.getSelection()` already returns the exact set of
  addresses (`addresses`) a copy operation should act on, plus the
  anchor/active addresses if shape-aware behaviour (e.g. pasting back
  the same rectangle) is needed later.
- The rectangle-computation logic (`_rectCells`) and CSS-class
  rendering are already isolated in this module; PR7 should call into
  `FcSelectionManager`'s public API rather than introducing a second
  notion of "what is selected."
- Swap/focus/scroll preservation across htmx updates is already
  handled by PR3/PR4/PR6 and requires no new wiring from PR7 for the
  selection itself.
