# C1-PR1: Spreadsheet Interaction Layer Skeleton — Implementation Note

Implements PR1 only, per `docs/C1_INTERACTION_LAYER_DESIGN.md`. Foundation
only — no visible or behavioural change.

## Architecture implemented

- **Markup contract** (read by, not enforced by, the registry):
  `data-fc-grid`, `data-fc-row` (optional; falls back to nearest `<tr>`),
  `data-fc-cell`, `data-fc-addr`, `data-fc-editable` (defaults to `false`
  when absent), `data-fc-kind`.
- **`static/interaction/grid-registry.js`** — `window.FcGridRegistry`:
  `scan(root)`, `scanAll()`, `getGrid(gridId)`, `getCell(gridId, row, col)`,
  `getAddr(gridId, addr)`, `neighbors(cell, direction)`. Pure read-only DOM
  introspection; re-scanning a grid replaces its index rather than
  accumulating, so repeated scans are idempotent.
- **`static/interaction/engine.js`** — `window.FcInteractionEngine`:
  `boot()` (idempotent — a no-op after the first call) and `isBooted()`.
  On first boot it runs `scanAll()` on initial load and attaches its own
  `htmx:afterSwap` listener that calls `scan()` scoped to the swapped
  subtree. Dispatches `fc:engineReady` and `fc:gridsScanned` events.
- **`app/templates/base.html`** — the two scripts above are loaded with
  `defer`, before `app.js`, so `FcGridRegistry`/`FcInteractionEngine`
  exist by the time `app.js` runs. `app.js` itself is unmodified.

## Extension points created

- `data-fc-*` attributes are present in the contract but no template
  markup was added to any sheet in this PR (sheets register zero grids
  for now — there's nothing in the DOM yet using `data-fc-grid`).
- `fc:engineReady` / `fc:gridsScanned` events for later PRs to subscribe
  to without modifying `engine.js`.
- `neighbors()` already returns `null` at grid edges and treats
  non-rectangular rows (e.g. subtotal/band rows) as navigable-but-not-
  editable by default, anticipating PR2's keyboard navigation work.

## Intentionally NOT implemented (deferred to later PRs)

Active cell tracking, keyboard navigation (arrows, Enter, Tab), clipboard
(copy/paste), undo/redo, fill-down, selection, drag, Excel-style
shortcuts, recalculation triggers, focus movement, scroll restoration,
any `data-fc-*` markup added to real sheet templates, and any change to
`app.js`'s existing `htmx:afterSwap` listener or the three existing edit
mechanisms (bound inputs, native CAPEX grid inputs, Senior Debt's
`data-grid-source` mirror inputs).

## Tests

- `tests/test_c1_pr1_grid_registry.py` — TestClient static-wiring checks
  (files served, script order in `base.html`, `app.js` untouched,
  existing workspace page still renders).
- `tests/test_c1_pr1_grid_registry_browser.py` — Playwright checks against
  `tests/fixtures/c1_grid_registry_fixture.html`: engine loads, registry
  initializes and registers grids, subtotal rows are navigable-but-not-
  editable, `neighbors()` returns `null` at edges, repeated `scanAll()` is
  safe, two grids stay isolated, `boot()` attaches the `htmx:afterSwap`
  hook exactly once, the hook rescans only the swapped subtree, and
  `fc:engineReady` fires on boot.

## Guardrails respected

No changes to `domain/*`, the modelling engine, waterfall, persistence,
export, or calculations. No sheet template markup changed. No CSS/UX
changes. `app.js` is byte-for-byte unmodified.
