# C1-PR9: Fill Down / Fill Right Foundation — Implementation Note

## Scope

This PR adds a **fill foundation** on top of C1-PR1 through C1-PR8
(GridRegistry/InteractionEngine, ActiveCellManager, FcSwapLifecycle,
FcFocusManager, FcKeyboardRouter, FcSelectionManager,
FcClipboardController, FcUndoManager). Finco One can now fill the
current selection's top row downward (Ctrl+D/Cmd+D) or its leftmost
column rightward (Ctrl+R/Cmd+R), undoably, in one transaction.

It does **not** add a drag-fill handle, autofill series, formula
parsing/relative references, formatting/validation copy, cut,
delete-row behaviour, recalculation, or Save/Run integration. Those
remain out of scope (see "Deferred" below).

## What was implemented

### `static/interaction/fill-controller.js` (`window.FcFillController`)

A new, additive module, loaded after `undo-manager.js` and before
`app.js`. It holds **no parallel grid, selection, or undo state** —
every fill reads `FcSelectionManager.getSelection()` and
`FcGridRegistry`'s live grid index fresh, and every undo-relevant
write/record goes through the existing `FcClipboardController`/
`FcUndoManager` APIs. This module owns no state of its own.

**Public API:**

| Function | Behaviour |
|---|---|
| `fillDown()` | fills the current selection's top row downward into every editable cell in the rest of the selection; returns `true` if anything changed, `false` otherwise (no-op) |
| `fillRight()` | fills the current selection's leftmost column rightward into every editable cell in the rest of the selection; returns `true`/`false` the same way |

**Source/target resolution:** the current selection's rectangle bounds
are resolved exactly like `FcClipboardController`'s `_selectionBounds`
— via `FcSelectionManager.getSelection()`'s anchor/active addresses
and `FcGridRegistry.getAddr()`, never a duplicated selection model.
Fill Down reads each column's top-row cell as the source and writes
that value into every other row of that column within the bounds;
Fill Right is the symmetric column-wise mirror, reading each row's
leftmost cell.

**Conservative behaviour (never throws, never corrupts):**

- **No selection, or an unresolvable selection** → `fillDown()`/
  `fillRight()` return `false` immediately.
- **Single-cell selection** (`anchorAddr === activeAddr`, i.e. the
  bounds collapse to one row and one column) → no-op, returns `false`
  — there is nothing to fill into.
- **Non-editable target cells** (`data-fc-editable="false"` or
  absent) are skipped entirely — left unmodified — but still occupy
  their position in the grid, exactly like `pasteText()`'s clipping in
  PR7.
- **Out-of-bounds rows/columns** (e.g. a selection whose rectangle
  includes a row/column index past what the grid actually has) are
  skipped (`continue`, never `throw`) the same way `pasteText()` clips
  safely.
- **No editable target with a different value than the source** →
  no-op, returns `false` — a fill that would change nothing records no
  transaction.
- A target cell whose value already equals the source value is left
  untouched and not included in the recorded transaction (no
  redundant no-op writes).

**Values only:** both fill operations copy a cell's plain string
value only (read the same way `FcClipboardController._cellValue`
already reads it — a descendant `<input>/<select>/<textarea>`'s
`.value`, else trimmed `textContent`). There is no concept of a
formula, a relative reference, a format, or a validation rule to
copy or translate.

**Undo integration:** every editable cell actually changed during a
fill is accumulated into one `changes` array of `{addr, before,
after}`, and `FcUndoManager.recordTransaction()` is called **exactly
once** per fill — with `type: 'fill-down'` or `type: 'fill-right'` —
covering the active-cell and selection state (both before and after,
which are identical, since fill never moves the active cell or
changes the selection). This is the same single-transaction
discipline `FcClipboardController.pasteText()` already uses for
multi-cell paste in PR8. Every cell write goes through
`FcClipboardController.applyCellValue()` (PR8's additive export of
the shared `_setCellValue` helper) — no write logic is duplicated.
The call is guarded by
`if (window.FcUndoManager && window.FcUndoManager.recordTransaction)`,
so fill still works (with no undo history) if `undo-manager.js` isn't
loaded, matching every other optional-dependency call in this
codebase.

**Selection/active-cell/focus after fill:** left completely
unchanged — `fillDown()`/`fillRight()` never call
`FcSelectionManager.selectSingle()`/`extendTo()` or
`FcActiveCellManager.setActiveCell()`. `FcFocusManager.syncFocus()` is
called afterwards (if present) purely to keep DOM focus consistent
with whatever was already active, mirroring PR7/PR8's pattern — it
does not change which cell is active.

**Keyboard guard (Ctrl+D/Cmd+D, Ctrl+R/Cmd+R):** guarded identically
to PR5/PR7/PR8's keyboard guards — only acts when
`document.activeElement` matches `[data-fc-cell]` and is exactly the
cell `FcActiveCellManager` reports active; any other focus target (a
real `<input>`, a button, a link, a modal, etc.) is left completely
untouched, so normal browser behaviour and page-level shortcuts
outside the grid continue to work unaffected. `evt.preventDefault()`
is only called once the guard passes and a chord is recognized.

### `app/templates/base.html`

One new `<script defer>` tag for `fill-controller.js`, inserted after
`undo-manager.js` and before `app.js`, matching the existing loading
order convention.

## What was intentionally deferred

- **Drag-fill handle / autofill series** — not implemented; fill is
  triggered only by Ctrl+D/Ctrl+R over an existing selection, never by
  a draggable UI handle or an inferred series (1, 2, 3, ...).
- **Formula parsing, relative references, formula translation** — a
  filled value is always copied verbatim as plain text; there is no
  concept of a formula or a reference to translate.
- **Formatting/validation copy** — fill never touches a cell's
  styling, number format, or validation rule, only its plain value.
- **Recalculation, Save/Run integration, persistence, export** — fill
  only mutates the DOM the same way pasting/editing already does; it
  does not trigger any modelling, persistence, or run behaviour.
- **Cut, delete-row behaviour** — unchanged from PR7/PR8, not
  implemented here either.
- **Cross-grid / cross-project fill** — fill always operates on a
  single grid's selection at a time, per the one-selection-globally
  model from PR6; there is no concept of filling across two different
  grids in one operation.
- **Retrofitting real template markup** — as with PR1-PR8, no
  production grid in `app/templates/*` is given `data-fc-grid`/
  `data-fc-cell` attributes yet, so this PR's behaviour is currently
  only exercised via the dedicated fixture; it is exclusively
  additive/no-op for any page that doesn't yet use the markup
  contract. Real fill behaviour on production sheets is contingent on
  a future sheet-migration PR adopting the `data-fc-*` contract.

## Dependency surface for future sheet migration PRs

- `FcFillController.fillDown()`/`fillRight()` already read/write
  through the same `FcGridRegistry`/`FcSelectionManager`/
  `FcClipboardController.applyCellValue()`/`FcUndoManager` surface
  every other PR1-PR8 module uses, so once a real template adopts the
  `data-fc-*` markup contract, fill works immediately with no further
  changes to this module.
- The single-transaction-per-fill pattern established here (accumulate
  all changes, call `recordTransaction()` once) is the same pattern
  PR8 used for paste — any future bulk-edit feature can follow it
  directly.
