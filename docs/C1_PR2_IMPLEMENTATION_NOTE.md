# C1-PR2: Active Cell Foundation — Implementation Note

Implements PR2 only, continuing directly from `docs/C1_INTERACTION_LAYER_DESIGN.md`
and `docs/C1_PR1_IMPLEMENTATION_NOTE.md`. Introduces the concept of a
single active cell — no keyboard navigation, no selection, no
clipboard, no undo.

## Architecture implemented

- **`static/interaction/grid-registry.js`** (extended) — each grid's
  index now carries an `active` field (a cell record or `null`),
  exposed via three new functions: `setActiveCell(gridId, cell)`,
  `clearActiveCell(gridId)`, `getActiveCell(gridId)`. The registry
  remains the single source of truth for which cell is active per
  grid; it still never touches the DOM. `scan()`/`scanAll()` re-attach
  the previously active cell record onto a rebuilt grid index when its
  address still resolves after a rescan, so a grid's active pointer
  survives a re-render of its own markup — it does not infer or guess,
  it only re-looks-up the same address.
- **`static/interaction/active-cell.js`** (new) — `window.FcActiveCellManager`:
  `init()` (idempotent, auto-runs on script load, same pattern as
  `FcInteractionEngine.boot()`), `setActiveCell(gridId, cell)`,
  `clearActiveCell()`, `getActiveCell()`. Tracks at most one
  `{gridId, cell}` pair globally — setting a new active cell first
  clears whichever one (in whichever grid) was previously active, so
  exactly one active cell exists across the whole page, not one per
  grid.
  - Adds/removes a single CSS class, `fc-active-cell`, on the cell's
    element. No other DOM mutation.
  - Listens for plain `click` events (event delegation on
    `document`), resolves the closest `[data-fc-cell]` /
    `[data-fc-grid]` ancestor pair, and calls `setActiveCell`. It never
    calls `preventDefault()` or `stopPropagation()`, so default click
    behaviour (including any existing or future `dblclick` handling)
    is completely unaffected — double-click behaves exactly as today
    because this module never intercepts it.
  - Listens for the `fc:gridsScanned` / `fc:engineReady` events
    dispatched by `engine.js` (PR1) and, after each, re-resolves the
    active cell via `FcGridRegistry.getActiveCell(gridId)`: if the
    registry still has it (address survived the rescan), the CSS class
    is re-applied to the new element; if not, the active cell is
    cleared safely (state reset, no error).
- **`static/styles.css`** — one new rule, `.fc-active-cell { outline:
  2px solid #1a56db; outline-offset: -1px; }`. Visual indicator only;
  no other style touched.
- **`app/templates/base.html`** — `active-cell.js` is loaded with
  `defer`, after `engine.js` and before `app.js`. `app.js` is
  unmodified.

## Lifecycle / lifecycle integration with PR1

- Initial load: nothing is active (no click has happened yet).
- Single click on a `[data-fc-cell]`: becomes active; whatever was
  previously active (in any grid) loses its CSS class.
- After an htmx swap, `engine.js`'s existing rescan (`fc:gridsScanned`)
  fires as it already did in PR1; `active-cell.js` uses that signal to
  restore the active cell's visual state if its address is still
  present in the rebuilt grid, or clear it if the cell disappeared.
  No scrolling, no focus movement — purely a class toggle.

## Intentionally NOT implemented (deferred to later PRs)

Arrow keys, Enter, Tab/Shift+Tab, clipboard (copy/paste), undo/redo,
fill-down, range/multi-selection, drag, context menu, keyboard
shortcuts, auto-edit-on-active, formula mode. Double-click is
untouched and not given any new meaning. No `data-fc-*` markup was
added to any real sheet template in this PR — like PR1, this PR
ships with zero grids actually registered until a later PR opts a
sheet into the markup contract, so there is still no end-user-visible
behaviour change beyond the (currently unreachable) CSS class.

## Future PR dependency

PR3 (keyboard navigation) is expected to read the active cell via
`FcActiveCellManager.getActiveCell()` and `FcGridRegistry.neighbors()`
(from PR1) to move the active cell on arrow/Tab — it should not need
to change `grid-registry.js` or `active-cell.js`'s public API, only
add new keydown handling that calls `setActiveCell` with whatever
`neighbors()` returns.

## Tests

- `tests/test_c1_pr2_active_cell.py` — TestClient static-wiring checks
  (file served, script order in `base.html`, `app.js` untouched,
  existing workspace page still renders).
- `tests/test_c1_pr2_active_cell_browser.py` — Playwright checks
  against `tests/fixtures/c1_active_cell_fixture.html`: manager loads,
  no active cell on initial load, single click sets the active cell,
  clicking another cell clears the previous one's class, only one
  active cell exists across two grids, `clearActiveCell()` removes
  class and state, an htmx swap that preserves the address restores
  the active cell, an htmx swap that removes the cell clears it
  safely, and `init()` is idempotent (no duplicate listeners after
  repeated calls).

## Guardrails respected

No changes to `domain/*`, the modelling engine, persistence, export,
or calculations. No sheet template markup changed. No CSS redesign —
one additive rule. `app.js` is byte-for-byte unmodified. No keyboard,
clipboard, or selection code anywhere in this PR.
