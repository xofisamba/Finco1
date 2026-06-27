# C1-PR8: Undo/Redo Foundation — Implementation Note

## Scope

This PR adds an **interaction-layer undo/redo stack** on top of C1-PR1
through C1-PR7 (GridRegistry/InteractionEngine, ActiveCellManager,
FcSwapLifecycle, FcFocusManager, FcKeyboardRouter, FcSelectionManager,
FcClipboardController). Finco One can now undo and redo:

- a multi-cell paste (PR7) as a single transaction, and
- a genuinely observable single-cell edit (a real `<input>`/`<select>`/
  `<textarea>` living inside a `[data-fc-cell]`).

It does **not** add fill-down/fill-right/drag-fill/autofill, formula
parsing/translation, recalculation, or Save/Run integration. Those
remain out of scope (see "Deferred" below and C1-PR9).

## What was implemented

### `static/interaction/undo-manager.js` (`window.FcUndoManager`)

A new, additive module, loaded after `clipboard-controller.js` and
before `app.js`. It holds **no parallel grid, active-cell, or
selection state** — the only state it owns is two stacks of
"transaction" objects (a history of values), each undo/redo
re-resolving the cells it needs to touch fresh via
`FcGridRegistry.getAddr()` at the moment it runs, exactly the same
discipline `FcSelectionManager`/`FcSwapLifecycle` already use.

**Public API:**

| Function | Behaviour |
|---|---|
| `recordTransaction(tx)` | pushes `tx` onto the undo stack and clears the redo stack; no-ops if `tx` has no changes |
| `undo()` | pops the most recent transaction, writes every change's `before` value (skipping cells that no longer resolve), restores active-cell/selection state if it still resolves, pushes the transaction onto the redo stack; returns `true`/`false` |
| `redo()` | symmetric — pops from the redo stack, writes `after` values, restores `activeAfter`/`selectionAfter`, pushes back onto the undo stack |
| `canUndo()` / `canRedo()` | booleans, for callers/tests to check stack state without triggering a no-op |

**Transaction shape** (constructed by the caller, e.g.
`FcClipboardController.pasteText()`, or by this module's own cell-edit
observation):

```js
{
  type: 'cell-edit' | 'paste',
  gridId: string,
  changes: [{ addr, before, after }, ...],
  activeBefore: { gridId, addr } | null,
  activeAfter: { gridId, addr } | null,
  selectionBefore: { gridId, anchorAddr, activeAddr } | null,
  selectionAfter: { gridId, anchorAddr, activeAddr } | null
}
```

**Undo/redo application:** for each `{addr, before/after}` in
`tx.changes`, the cell is resolved fresh via
`FcGridRegistry.getAddr(tx.gridId, addr)`; if it no longer resolves
(e.g. the grid was swapped away), that change is skipped — never
thrown. The value is written via
`FcClipboardController.applyCellValue()` (an additive export added in
this PR, aliasing the same `_setCellValue` helper PR7 already uses for
paste, so undo/redo writes a cell's value through the exact same
input/select/textarea-vs-`textContent` logic as every other write
path, with no duplicated logic). Active-cell/selection restoration is
equally conservative: `activeBefore`/`activeAfter` is only applied if
its address still resolves in the stated grid; `selectionBefore`/
`selectionAfter` is only applied if **both** its anchor and active
addresses still resolve in that grid (reusing
`FcSelectionManager.selectSingle()`/`extendTo()`, never a parallel
selection model). `FcFocusManager.syncFocus()` is called afterwards if
present, mirroring PR4-PR7's optional-dependency pattern.

**Cell-edit observation (the genuinely-observable path):** production
templates do not yet use the `data-fc-*` markup contract with real
form controls in any plain-text `<td>` cell, so per the task's "do not
fake support for edits that are not observable yet" instruction, this
module only observes edits to a real `<input>`/`<select>`/`<textarea>`
that lives inside a `[data-fc-cell]` (the same convention
`FcClipboardController._cellValue`/`_setCellValue` already use to
read/write a cell's "value"). A `focusin` listener captures the
field's value as a "before" snapshot when it receives focus; a
`change` listener compares the committed value against that snapshot
and, if it differs, records a single-cell `cell-edit` transaction
(capturing the surrounding selection as both `selectionBefore` and
`selectionAfter`, since a plain field edit does not move the
selection). If the value is unchanged, or the field/cell can't be
resolved, nothing is recorded.

**Clipboard integration:** `FcClipboardController.pasteText()` (PR7)
was extended additively to accumulate one `changes` entry per
editable cell it actually writes during a paste, plus a
before/after snapshot of the active cell and selection, and call
`FcUndoManager.recordTransaction()` exactly once at the end of the
paste — so a multi-cell paste is always one undo transaction, never
one per cell. This call is guarded by
`if (changes.length && window.FcUndoManager && window.FcUndoManager.recordTransaction)`,
so paste continues to work unchanged (just without undo history) if
`undo-manager.js` isn't loaded — the same optional-dependency pattern
used throughout PR4-PR7.

**Keyboard guard (Ctrl+Z / Ctrl+Y / Ctrl+Shift+Z):** guarded
identically to PR5/PR7's keyboard guards — only acts when
`document.activeElement` matches `[data-fc-cell]` and is exactly the
cell `FcActiveCellManager` reports active; any other focus target (a
real `<input>`, a normal page text selection, etc.) is left completely
untouched, so the browser's own undo inside a real text input
continues to work. When the guard passes:

- **Ctrl+Z / Cmd+Z** → `undo()`.
- **Ctrl+Y / Cmd+Y** or **Ctrl+Shift+Z / Cmd+Shift+Z** → `redo()`.

`evt.preventDefault()` is only called once the guard passes and a
chord is recognized.

### `static/interaction/clipboard-controller.js`

Two additive changes, both purely additive — no copy/parse/clip logic
changed:

- `pasteText()` now builds the `changes`/`activeBefore`/
  `activeAfter`/`selectionBefore`/`selectionAfter` transaction shape
  described above and calls `FcUndoManager.recordTransaction()` if
  that module is loaded.
- The public export object gained one new function,
  `applyCellValue: _setCellValue`, so `FcUndoManager` can write a
  cell's value through the exact same logic `copySelection`/
  `pasteText` already use, rather than duplicating it.

### `app/templates/base.html`

One new `<script defer>` tag for `undo-manager.js`, inserted after
`clipboard-controller.js` and before `app.js`, matching the existing
loading order convention.

## What was intentionally deferred

- **Fill-down / fill-right / drag-fill / autofill** — not implemented
  anywhere in this module (C1-PR9).
- **Formula parsing, relative references, formula translation** — out
  of scope; a cell's value is always treated as plain text.
- **Recalculation, Save/Run integration, persistence, export** — undo/
  redo only mutates the DOM the same way typing/pasting already does;
  it does not trigger any modelling, persistence, or run behaviour.
- **Cut (Ctrl+X), delete-row behaviour** — not implemented (unchanged
  from PR7).
- **Cross-grid / cross-project undo** — every transaction is scoped to
  the single `gridId` it was recorded against; undo/redo never reaches
  into a different grid, even if one happens to be active.
- **Faked cell-edit capture for plain-text `<td>` cells** — as with
  PR1-PR7, no production grid in `app/templates/*` is given
  `data-fc-grid`/`data-fc-cell` attributes yet, and no plain-text cell
  has a real, directly-editable contenteditable/input affordance
  today. Cell-edit transactions are only recorded for a cell that
  contains a genuine `<input>`/`<select>`/`<textarea>` — the one
  authentically observable edit path that exists right now. This PR's
  behaviour is currently only exercised via the dedicated fixture; it
  is exclusively additive/no-op for any page that doesn't yet use the
  markup contract.
- **Undo-history size cap** — not implemented; the undo/redo stacks
  grow for the lifetime of the page and are never persisted across an
  HTMX swap that replaces the whole document or a reload.

## Dependency surface for C1-PR9 (Fill Down / Fill Right)

- `FcUndoManager.recordTransaction()` already accepts an arbitrary
  `changes` array spanning any number of cells in one grid, plus
  active-cell/selection before/after snapshots — PR9 can record a
  fill operation as a single transaction the same way PR8 did for
  paste, with no new transaction shape needed.
- `FcClipboardController.applyCellValue` is now a stable, shared
  single-cell write primitive; PR9's fill logic can reuse it directly
  instead of re-implementing input/select/textarea-vs-`textContent`
  detection.
