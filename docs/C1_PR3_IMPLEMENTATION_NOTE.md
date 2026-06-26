# C1-PR3: Focus & Scroll Preservation — Implementation Note

## Scope

This PR adds **focus and scroll preservation** on top of the C1-PR1
(GridRegistry + InteractionEngine) and C1-PR2 (ActiveCellManager)
foundations. It makes the active cell, and now also grid scroll
position, survive common htmx swaps more reliably.

It does **not** add keyboard navigation, selection, clipboard, or
undo. Those remain out of scope (see "Deferred" below and
C1-PR4).

## What was implemented

### `static/interaction/swap-lifecycle.js` (`window.FcSwapLifecycle`)

A new, additive module, loaded after `active-cell.js` and before
`app.js`:

- `htmx:beforeSwap` — captures:
  - the currently active grid id + cell address (via
    `FcActiveCellManager.getActiveCell()`), if any.
  - the `scrollTop`/`scrollLeft` of every registered grid's scroll
    container (via the new `FcGridRegistry.getGridIds()` /
    `getGrid(id).container` additions), for any grid that opts in via
    `data-fc-scroll-container`.
- `fc:gridsScanned` (dispatched by `engine.js` after its own
  `FcGridRegistry.scan()` on `htmx:afterSwap`) — restores:
  - the active cell, by re-resolving the captured address against the
    freshly rebuilt grid index. If the address still exists, the cell
    is re-activated via `FcActiveCellManager.setActiveCell()`
    (idempotent if it's already active). If it does not, the active
    cell is cleared via `clearActiveCell()` — never left dangling.
  - the scroll container's position, restored only for grids that
    were actually rescanned and that still report a `container`. If a
    grid or its container disappeared, that grid's snapshot is simply
    dropped — no error, no dangling state.
- `init()` is idempotent (mirrors the pattern in `engine.js` /
  `active-cell.js`) and auto-runs once on script load.

This module never calls `preventDefault()`/`stopPropagation()` and
never touches keyboard, clipboard, or selection state.

### `static/interaction/grid-registry.js` (additive only)

- `_buildIndex()` now also captures `container`: the nearest ancestor
  matching the new, opt-in `data-fc-scroll-container` attribute, or
  `null` if a grid doesn't have one. Grids that don't opt in are
  completely unaffected — no scroll preservation is attempted for
  them, and no existing behaviour changes.
- New exported `getGridIds()` — returns the ids of all currently
  registered grids, used by `FcSwapLifecycle` to enumerate scroll
  containers generically without depending on real markup pages.

No other function in `grid-registry.js` changed. The existing
active-cell carry-forward in `scan()` (added in PR2) is untouched.

### `app/templates/base.html`

One new `<script defer>` tag for `swap-lifecycle.js`, inserted after
`active-cell.js` and before `app.js`, matching the existing loading
order convention.

## What was intentionally deferred

- **Keyboard navigation** (arrow keys, Tab/Shift+Tab, Enter) — none of
  this PR's code listens for `keydown`/`keyup`/`keypress`. Deferred to
  C1-PR4.
- **Selection / ranges / multi-cell selection / drag selection** — not
  implemented anywhere in this module.
- **Clipboard (copy/paste), undo/redo, fill-down** — not implemented.
- **Context menu, recalculation, formula/edit-mode changes** — not
  touched.
- **Retrofitting real template markup with
  `data-fc-scroll-container`** — this PR introduces the attribute and
  the registry/lifecycle support for it, but does not add it to any
  production grid in `app/templates/*`. Until a real grid opts in,
  scroll preservation is a no-op for that grid (active-cell
  preservation, which doesn't depend on the new attribute, still
  applies to all grids as before).

## Dependency surface for C1-PR4 (Keyboard Navigation)

PR4 can build directly on this PR without re-implementing any swap
handling:

- It can read the current active cell via
  `FcActiveCellManager.getActiveCell()` and move it via
  `FcGridRegistry.neighbors(cell, direction)`, exactly as before.
- It does **not** need its own `htmx:beforeSwap`/`htmx:afterSwap`
  handling for focus or scroll — `FcSwapLifecycle` already keeps the
  active cell and (for opted-in grids) scroll position correct across
  swaps. PR4 only needs to call
  `FcActiveCellManager.setActiveCell()` when the user navigates with
  the keyboard; restoration after any subsequent swap is already
  handled.
- If PR4 introduces a scrollable grid container, marking it with
  `data-fc-scroll-container` is sufficient to get scroll preservation
  for free — no new lifecycle code is required.
