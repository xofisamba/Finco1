# C1-PR5: Keyboard Navigation Foundation — Implementation Note

## Scope

This PR adds **keyboard navigation foundation** on top of C1-PR1
(GridRegistry + InteractionEngine), C1-PR2 (ActiveCellManager),
C1-PR3 (FcSwapLifecycle), and C1-PR4 (FcFocusManager). The active
cell can now be moved with the keyboard, but only while DOM focus is
already on a registered grid cell.

It does **not** add selection, clipboard, undo, fill, formula mode,
or recalculation. Those remain out of scope (see "Deferred" below and
C1-PR6).

## What was implemented

### `static/interaction/keyboard-router.js` (`window.FcKeyboardRouter`)

A new, additive module, loaded after `focus-manager.js` and before
`app.js`. It holds **no parallel state** — every `keydown` reads the
live active cell from `FcActiveCellManager.getActiveCell()` and the
live grid index from `FcGridRegistry.getGrid()`, so behaviour across
htmx swaps is automatic: if `FcSwapLifecycle` restored the active
cell, navigation keeps working from there; if it was cleared, this
module simply has nothing to act on.

**Guard (the only entry condition):** a `keydown` is handled only if
`document.activeElement` matches `[data-fc-cell]` **and** that exact
element is the cell `FcActiveCellManager` currently reports as active.
Any other focus target — a real `<input>`, `<select>`, `<textarea>`,
`<button>`, `<a>`, a modal, or no active cell at all — causes an
immediate, silent no-op. This is what keeps normal text/number editing
and all other page keyboard shortcuts completely unaffected.

**Implemented keys** (only handled when the guard above passes):

| Key | Effect |
|---|---|
| `ArrowRight` / `ArrowLeft` / `ArrowDown` / `ArrowUp` | move one cell in that direction via `FcGridRegistry.neighbors()` |
| `Ctrl+ArrowRight/Left/Down/Up` | move to the edge of the current row/column in that direction (repeated `neighbors()` stepping until none remain) |
| `Enter` | move down one cell |
| `Shift+Enter` | move up one cell |
| `Tab` | move right one cell |
| `Shift+Tab` | move left one cell |
| `Home` | move to the first cell in the current row |
| `End` | move to the last cell in the current row |

For every one of these keys, once the guard passes, `preventDefault()`
is called — this is what stops `Tab`/`Shift+Tab` from escaping the
grid's focus order and stops arrow keys from triggering any native
page-scroll side effect — regardless of whether a target cell is
actually found (e.g. at a grid edge). When no target exists (or the
target is the same cell, e.g. `Home` when already in column 0), the
key is still "claimed" (default prevented) but no move happens —
conservative behaviour per the task's edge-case guidance.

When a target cell is found, the module calls
`FcActiveCellManager.setActiveCell()` (existing PR2 API — no new
active-cell state model) and then `FcFocusManager.syncFocus()` — a
small, additive export added to `focus-manager.js` in this PR
(`syncFocus: _sync`) that simply exposes its already-existing
focus-application logic so this module doesn't have to duplicate it.
No other line of `focus-manager.js`, `active-cell.js`,
`swap-lifecycle.js`, or `grid-registry.js` changed.

### `app/templates/base.html`

One new `<script defer>` tag for `keyboard-router.js`, inserted after
`focus-manager.js` and before `app.js`, matching the existing loading
order convention.

## What was intentionally deferred

- **Selection / ranges / Shift+Arrow extension / multi-cell
  selection** — not implemented; `Shift` is only used here to invert
  `Enter`/`Tab` direction, never to extend a range.
- **Clipboard (copy/paste), undo/redo, fill-down/drag fill** — not
  implemented anywhere in this module.
- **Context menu, formula editing, recalculation** — not touched.
- **Wrapping navigation across row/grid boundaries** (e.g. `Tab` at
  the last column moving to the next row, or moving between
  `fixture-grid` and a second grid) — kept conservative per the task's
  "Keep behaviour conservative if grid edge logic is unclear"
  guidance; at a row/grid edge the key is claimed (default prevented,
  so focus never escapes) but no move occurs.
- **Retrofitting real template markup** — as with PR1-PR4, no
  production grid in `app/templates/*` is given `data-fc-grid`/
  `data-fc-cell` attributes yet, so this PR's behaviour is currently
  only exercised via the dedicated fixture; it is exclusively
  additive/no-op for any page that doesn't yet use the markup
  contract.

## Dependency surface for C1-PR6 (Selection Model)

PR6 can build directly on this PR without re-implementing any
keyboard routing or movement logic:

- The single active cell is already reliably kept in sync with
  `FcActiveCellManager` and DOM focus by the time PR6's selection
  logic would run.
- `FcKeyboardRouter`'s `_resolveTarget()`/`neighbors()`-based movement
  is the natural extension point: PR6 can branch on `Shift+Arrow`
  (currently unhandled — falls through and is ignored) to begin
  extending a selection range from the existing active cell, reusing
  the same `FcGridRegistry.neighbors()` calls already used here for
  plain movement, rather than introducing a second navigation
  primitive.
- Swap/focus/scroll preservation across htmx updates is already
  handled by PR3/PR4 and requires no new wiring from PR6 for the
  active-cell anchor of a selection.
