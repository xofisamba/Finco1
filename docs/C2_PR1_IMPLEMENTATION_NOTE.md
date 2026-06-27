# C2-PR1: Live Modelling Foundation — Implementation Note

## Scope

This PR begins the **Live Modelling Layer** (C2), separate from the
C1 Spreadsheet Interaction Layer (PR1-PR9) it sits on top of. It
establishes the infrastructure that will let spreadsheet edits
participate in a live modelling workflow later, without touching the
financial engine, persistence, or export today.

It implements **infrastructure only**:

1. Dirty-state tracking for edited cells/sheets/the project.
2. Change batching (coalescing consecutive edits to the same cell).
3. Live edit session state.
4. A lightweight recalculation scheduler API (stub only — queues and
   flushes plain event objects, never executes anything).
5. An event pipeline (pub/sub) for future incremental recalculation.

No financial formula evaluates differently. No persistence model
changes. No export behaviour changes. No recalculation, dependency
graph, or background model execution happens anywhere in this PR.

## What was implemented

### `static/modelling/live-model.js` (`window.FcLiveModel`)

A new, additive module in a new `static/modelling/` directory (kept
separate from `static/interaction/`, which remains exclusively the
C1 layer), loaded after `fill-controller.js` and before `app.js`. It
holds only its own dirty/batch/session/scheduler state — it never
duplicates `FcGridRegistry`/`FcActiveCellManager`/
`FcSelectionManager`/`FcUndoManager` state, and never calls into any
C1 module to mutate a cell. It only *reads* cell identity (gridId/addr)
from the DOM via the same `[data-fc-grid]`/`[data-fc-cell]`/
`data-fc-addr`/`data-fc-editable` markup contract every C1 module
already uses.

**Dirty-state tracking:**

| Function | Behaviour |
|---|---|
| `markCellDirty(gridId, addr, before, after)` | marks the cell, its sheet, and the project dirty; accumulates the change into the pending batch; queues a `cell-changed` event on the scheduler; emits pub/sub events |
| `isCellDirty(gridId, addr)` | `true` once that cell has been marked dirty |
| `isSheetDirty(gridId)` | `true` once any cell in that grid has been marked dirty |
| `isProjectDirty()` | `true` once any cell anywhere has been marked dirty |
| `getDirtyCells(gridId?)` | dirty cell addresses for one grid, or `{gridId, addr}` pairs for all grids |
| `getDirtySheets()` | array of dirty gridIds |
| `clearDirty(gridId?)` | clears dirty flags (and the pending batch) for one grid, or everything |

Dirty state intentionally **outlives** a flush or a session end — it
is only cleared by an explicit `clearDirty()` call, which is left for
a future PR (e.g. wiring it to an eventual Save) to call; this PR does
not call it anywhere itself.

**Change batching:**

`getBatch(gridId?)` / `flushBatch(gridId?)` return the **coalesced**
set of net changes since the last flush — editing the same cell
twice produces one batch entry whose `before` is the value from the
*first* edit and whose `after` is the value from the *latest* edit,
not two separate entries. `flushBatch()` clears the pending batch (and
emits a `batch-flush` event) but leaves dirty flags and the scheduler
queue untouched — they are independent, separately-cleared concepts.

**Live edit session state:**

A session starts lazily on the first dirty edit
(`startSession()`/auto-started by `markCellDirty()`) and is ended
explicitly with `endSession()`, which returns a summary
(`{id, dirtyCells, dirtySheets, projectDirty, batch}`) and emits
`session-ended`. `isSessionActive()`/`getSession()` expose the current
state. Ending a session does not clear dirty state or the batch by
itself.

**Scheduler (stub only):** `FcLiveModel.scheduler` exposes
`queueEvent(event)`, `queueLength()`, `flush()`, and `peek()`. It
**only stores and returns plain event objects** — it never accepts or
calls a function, and `flush()` never executes anything, it simply
drains and returns the queue. Every `markCellDirty()` call
automatically queues one `{type: 'cell-changed', gridId, addr, before,
after}` event, so the scheduler already accumulates exactly the
event stream a future incremental-recalculation consumer (C2-PR2)
will need, with zero calculation work performed here.

**Event pipeline (pub/sub):** `on(eventName, handler)` /
`off(eventName, handler)` support `'cell-dirty'`, `'sheet-dirty'`
(emitted only on the transition to dirty), `'project-dirty'`,
`'session-started'`, `'session-ended'`, and `'batch-flush'`. This is a
minimal synchronous in-process pub/sub, not a network or persistence
mechanism.

**DOM wiring — the one genuinely observable edit path:** exactly
mirroring C1-PR8's discipline, this module only observes edits to a
real `<input>`/`<select>`/`<textarea>` living inside an *editable*
`[data-fc-cell]` (`data-fc-editable` not `"false"`), via a
`focusin`/`change` pair. A `change` on a non-editable cell's field, or
on any field outside a `[data-fc-grid]`, is never tracked. No
plain-text `<td>` cell is faked as trackable — there is still no
production template using the `data-fc-*` markup contract with real
form controls.

### `app/templates/base.html`

One new `<script defer>` tag for `live-model.js`, inserted after
`fill-controller.js` and before `app.js`, matching the existing
loading order convention.

## What was intentionally deferred

- **Live financial recalculation** — not implemented anywhere; the
  scheduler only ever queues/flushes plain event objects, it never
  calls a function or computes a value.
- **Dependency graph** — not implemented; there is no concept of
  which cells depend on which others.
- **Formula evaluation** — not implemented; only plain values are
  tracked as `before`/`after` strings.
- **Background model execution** — not implemented.
- **Save / Run integration** — not implemented; this module never
  calls any Save or Run endpoint, and nothing in the existing Save/Run
  code paths was touched.
- **Persistence writes, export changes** — not implemented; dirty
  state lives only in memory for the lifetime of the page.
- **Debounce** — not implemented; the scheduler's API shape
  (`queueEvent`/`queueLength`/`flush`/`peek`) is deliberately generic
  enough for a future PR to add debounce logic around it without
  changing this PR's public surface.
- **Faked dirty tracking for plain-text cells** — as with C1-PR8, no
  production grid in `app/templates/*` is given the `data-fc-*`
  markup contract with real form controls yet, so this PR's dirty
  tracking is currently only exercised via the dedicated fixture; it
  is exclusively additive/no-op for any page that doesn't yet use the
  markup contract.

## Dependency surface for C2-PR2 (Incremental Recalculation)

- `FcLiveModel.scheduler.flush()` already returns the exact event
  stream (`{type: 'cell-changed', gridId, addr, before, after}`) a
  future incremental-recalculation consumer needs to decide what to
  recompute — PR2 can drain this queue and walk a dependency graph
  without any change to this PR's event shape.
- `FcLiveModel.getBatch()`/`flushBatch()` already give PR2 the net
  per-cell change for a batch of edits (e.g. after a paste/fill that
  touched many cells at once), so PR2 does not need to recompute
  "what actually changed" itself.
- `isSheetDirty()`/`isProjectDirty()`/`getDirtySheets()` already let
  PR2 scope its recalculation to only the sheets/cells that are
  actually dirty, rather than the whole project.
- The `on()`/`off()` pub/sub already gives PR2 a hook
  (`'cell-dirty'`/`'sheet-dirty'`/`'project-dirty'`) to react to new
  edits incrementally as they happen, instead of polling.
