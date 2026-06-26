# C1-PR4: DOM Focus Management — Implementation Note

## Scope

This PR adds **DOM focus management** on top of C1-PR1 (GridRegistry +
InteractionEngine), C1-PR2 (ActiveCellManager), and C1-PR3
(FcSwapLifecycle). Browser focus now follows whichever cell is
active, and survives compatible htmx swaps.

It does **not** add keyboard navigation, selection, clipboard, or
undo. Those remain out of scope (see "Deferred" below and C1-PR5).

## What was implemented

### `static/interaction/focus-manager.js` (`window.FcFocusManager`)

A new, additive module, loaded after `swap-lifecycle.js` and before
`app.js`. It never modifies `active-cell.js` or `swap-lifecycle.js` —
it only reads `FcActiveCellManager.getActiveCell()` and reacts to the
same `click` / `fc:gridsScanned` / `fc:engineReady` events those
modules already use, registering its listeners after both so it
always observes the post-resolution state:

- On `click` (delegated to `[data-fc-cell]`, mirroring
  `active-cell.js`'s own delegation) — re-syncs focus to whatever cell
  is now active.
- On `fc:gridsScanned` / `fc:engineReady` (dispatched by `engine.js`
  after `FcSwapLifecycle` has already restored or cleared the active
  cell for the swapped subtree) — re-syncs focus to match.
- "Sync" means: if a cell is active, lazily add `tabindex="-1"` to it
  the first time (cells are plain `<td>`/`<th>` elements and aren't
  natively focusable), then call `el.focus({ preventScroll: true })`
  if it isn't already focused. `preventScroll: true` is used
  everywhere so this module never itself causes a scroll jump — scroll
  position remains `FcSwapLifecycle`'s responsibility.
- If no cell is active (cleared by `FcActiveCellManager` or
  `FcSwapLifecycle`), the previously focused cell is blurred — never
  left holding focus, and never trapping it. Blurring simply returns
  focus to the document body (or whatever the browser's default
  behaviour is), so an ordinary focusable control elsewhere on the
  page is unaffected and can still receive focus normally.
- `tabindex="-1"` deliberately keeps cells **out of** the normal Tab
  order — Tab/Shift+Tab navigation between cells is explicitly out of
  scope for this PR (and reserved for C1-PR5).
- `init()` is idempotent (same pattern as every other module in this
  layer) and auto-runs once on script load.

This module never calls `preventDefault()`/`stopPropagation()` and
never attaches any keyboard listener.

### `app/templates/base.html`

One new `<script defer>` tag for `focus-manager.js`, inserted after
`swap-lifecycle.js` and before `app.js`, matching the existing loading
order convention.

No other production file changed.

## What was intentionally deferred

- **Keyboard navigation** (arrow keys, Tab/Shift+Tab, Enter) — no
  `keydown`/`keyup`/`keypress` listeners exist anywhere in this
  module. Deferred to C1-PR5.
- **Selection / ranges / multi-cell selection / drag selection** — not
  implemented.
- **Clipboard (copy/paste), undo/redo, fill-down** — not implemented.
- **Context menu, recalculation, formula/edit-mode changes** — not
  touched.
- **Retrofitting real template markup** — as with PR1-PR3, no
  production grid in `app/templates/*` is given `data-fc-grid`/
  `data-fc-cell` attributes yet, so this PR's behaviour is currently
  only exercised via the dedicated fixture. It is exclusively
  additive/no-op for any page that doesn't yet use the markup
  contract.

## Dependency surface for C1-PR5 (Keyboard Navigation)

PR5 can build directly on this PR without re-implementing any
focus-following logic:

- The active cell already owns DOM focus by the time PR5's keyboard
  handler would run, so `document.activeElement` reliably corresponds
  to `FcActiveCellManager.getActiveCell()`.
- PR5 only needs to call `FcActiveCellManager.setActiveCell()` when
  the user navigates with arrow keys / Tab — `FcFocusManager` will
  automatically move DOM focus to the new active cell via its existing
  `click`/`fc:gridsScanned` sync path (PR5 may need to dispatch an
  equivalent custom event, or this module's sync hook can be extended
  in PR5, but no rewrite of the focus-application logic itself is
  required).
- Focus restoration after htmx swaps is already handled — PR5 does
  not need its own swap-focus logic.
- Since cells use `tabindex="-1"`, native Tab/Shift+Tab still skips
  them; PR5 is responsible for deciding whether/how to change that
  when it implements keyboard navigation.
