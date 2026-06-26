# C1-PR7: Clipboard Foundation (Excel-Compatible) — Implementation Note

## Scope

This PR adds an **Excel-compatible clipboard foundation** on top of
C1-PR1 (GridRegistry + InteractionEngine), C1-PR2 (ActiveCellManager),
C1-PR3 (FcSwapLifecycle), C1-PR4 (FcFocusManager), C1-PR5
(FcKeyboardRouter), and C1-PR6 (FcSelectionManager). Finco One can now
copy the current selection as TSV (tab-separated values) and paste TSV
back from the active cell's origin, clipping safely against grid
bounds.

It does **not** add undo/redo, fill-down/fill-right/drag-fill/autofill,
cut, formula parsing/translation, or recalculation. Those remain out
of scope (see "Deferred" below and C1-PR8).

## What was implemented

### `static/interaction/clipboard-controller.js` (`window.FcClipboardController`)

A new, additive module, loaded after `selection-manager.js` and before
`app.js`. It holds **no parallel grid, active-cell, or selection
state** — every copy/paste reads `FcSelectionManager.getSelection()`
and `FcGridRegistry`'s live grid index fresh. The only state this
module owns is the clipboard payload itself (an in-memory fallback
cache), which is exactly what a clipboard is for, not a selection/grid
model.

**Public API:**

| Function | Behaviour |
|---|---|
| `copySelection()` | builds TSV from the current selection, caches it, best-effort writes it to the system clipboard, returns the TSV (or `null` if there is no selection) |
| `pasteText(text)` | parses `text` as TSV and writes it into the grid from the active cell's origin; returns `true`/`false` |
| `getLastCopiedText()` | returns the in-memory fallback cache (for inspection/testing) |

**Copy (Ctrl+C / Cmd+C):** guarded identically to PR5's keyboard
guard — only acts when `document.activeElement` matches
`[data-fc-cell]` and is exactly the cell `FcActiveCellManager` reports
active; any other focus target (a real `<input>`, etc.) is left
completely untouched, so normal browser copy continues to work there.
When the guard passes, the key is claimed (`preventDefault()`) and
`copySelection()` runs: it resolves the selection's anchor/active
addresses via `FcGridRegistry`, computes the rectangle bounds, and
builds TSV — one row per grid row (newline-joined), one cell value per
column (tab-joined). A cell's "value" is its descendant
`<input>/<select>/<textarea>` value if present, else its trimmed
`textContent`. The TSV is cached in-memory and also handed to
`navigator.clipboard.writeText()` best-effort (any rejection — e.g. no
permission yet, insecure context — is swallowed; the in-memory cache
already covers same-session paste).

**Paste (Ctrl+V / Cmd+V):** guarded the same way. When claimed, the
module prefers `navigator.clipboard.readText()` (the modern async
Clipboard API); if it's unavailable, throws synchronously, or its
promise rejects (e.g. no permission), it falls back to the in-memory
cache from the last `copySelection()` call in this session — this is
what makes copy-then-paste within Finco1 itself fully reliable
regardless of browser clipboard permissions, while still using the
real system clipboard (so pasting from Excel/Sheets/LibreOffice/plain
text works) whenever it's actually available.

`pasteText(text)` parses `text` into rows (handling `\r\n`, `\r`, and
`\n` line endings, and dropping one trailing empty row from a trailing
newline — the common shape when copying a range out of a real
spreadsheet) and columns (split on `\t`):

- **Single value** (one row, one cell) → written to the active cell
  only.
- **Multi-cell TSV** → written starting at the active cell's
  `(row, col)`, advancing through `FcGridRegistry`'s live grid index.
  If the pasted region runs past the last row or the last column of a
  row, that row/column is simply skipped (`break`, never `throw`) —
  pasting clips safely against whatever rectangle of cells actually
  exists, regardless of how large the source TSV is.
- **Non-editable cells** (`data-fc-editable="false"` or absent) within
  the pasted region are skipped (left unmodified) but still occupy
  their position in the grid — pasting over a label/total cell never
  corrupts it.
- **Empty/`null`/falsy input** → no-op, returns `false`, never throws.

**Clipboard ownership after paste:** the active cell is set to the
pasted region's origin (top-left), and the selection is updated to
cover the full pasted rectangle — done via the existing
`FcSelectionManager.selectSingle()`/`extendTo()` (called as
`selectSingle(gridId, bottomRightCell)` then
`extendTo(gridId, originCell)`, so the rectangle is correct and
`getSelection().activeAddr` matches the real active cell at the
top-left). `FcFocusManager.syncFocus()` is called afterwards (if
present) so DOM focus follows, mirroring the same optional-dependency
pattern PR5/PR6 already use.

**Selection after copy:** untouched — `copySelection()` never calls
into `FcSelectionManager` at all, so the selection that was just
copied remains visibly selected.

### `app/templates/base.html`

One new `<script defer>` tag for `clipboard-controller.js`, inserted
after `selection-manager.js` and before `app.js`, matching the
existing loading order convention.

## Browser compatibility notes

- **Modern path:** `navigator.clipboard.writeText()` /
  `.readText()` are used when present, giving real interoperability
  with Excel/Google Sheets/LibreOffice/plain text editors via the
  actual OS clipboard.
- **Fallback path:** both calls are wrapped in `try`/`catch` (for a
  synchronous throw, e.g. an insecure context where
  `navigator.clipboard` doesn't exist) and the write's promise
  rejection is swallowed / the read's promise rejection falls back to
  the in-memory cache. Same-session copy-then-paste inside Finco1 thus
  works unconditionally, with no dependency on clipboard permissions
  ever being granted.
- **Never blocks permission flows:** this module never awaits a
  clipboard permission prompt before doing anything else, and never
  prevents the browser's own permission UI from appearing — it simply
  proceeds with the fallback if a read/write isn't immediately
  available.
- Outside a registered, currently-active grid cell, this module never
  calls `preventDefault()` on Ctrl+C/Ctrl+V, so normal browser
  copy/paste (selected page text, a real `<input>`, etc.) is
  completely unaffected.

## What was intentionally deferred

- **Undo/redo** — not implemented anywhere in this module; pasting
  overwrites cell content with no history.
- **Cut (Ctrl+X)** — not implemented; only copy and paste.
- **Fill-down / fill-right / drag-fill / autofill** — not implemented.
- **Formula parsing, relative references, formula translation** — a
  pasted value is always copied verbatim as plain text; there is no
  concept of a formula or a reference to translate.
- **Recalculation, Save/Run integration** — pasting only mutates the
  DOM the same way typing into an editable cell would; it does not
  trigger any modelling, persistence, or run behaviour.
- **Delete-row behaviour** — not implemented.
- **Multi-grid / cross-project clipboard** — copy/paste always operate
  on a single grid's selection at a time, per the existing
  one-selection-globally model from PR6; there is no concept of
  copying across two different grids in one operation.
- **Retrofitting real template markup** — as with PR1-PR6, no
  production grid in `app/templates/*` is given `data-fc-grid`/
  `data-fc-cell` attributes yet, so this PR's behaviour is currently
  only exercised via the dedicated fixture; it is exclusively
  additive/no-op for any page that doesn't yet use the markup
  contract.

## Dependency surface for C1-PR8 (Undo/Redo Foundation)

PR8 can build directly on this PR without re-implementing clipboard
mechanics:

- Every DOM mutation this module makes goes through one function,
  `_setCellValue()`, the natural seam for PR8 to hook an undo-history
  entry (old value → new value) without touching copy/parse logic at
  all.
- `pasteText()` already knows the full extent of what it wrote (the
  clipped rectangle from origin to `lastCell`); PR8 can record that
  rectangle as a single undoable paste operation rather than one entry
  per cell.
- Selection/active-cell updates after a paste already go through the
  existing PR2/PR6 APIs, so undoing a paste is a matter of restoring
  prior cell values and letting `FcSelectionManager`/
  `FcActiveCellManager` be re-driven the same way any other
  selection/active-cell change is — no new state model is needed for
  PR8 to integrate.
