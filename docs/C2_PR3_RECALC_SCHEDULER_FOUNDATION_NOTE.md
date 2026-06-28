# C2-PR3: Recalculation Scheduler Foundation — Implementation Note

## Scope

This PR adds a **deterministic recalculation scheduler foundation** on
top of `FcLiveModel` (`static/modelling/live-model.js`), the canonical
client-side dirty-state source established in C2-PR1 and unified with
the legacy dirty banner / Run gating / Save flow in C2-PR2.

It implements **infrastructure only**:

1. Subscribing to (in fact, being driven directly by) FcLiveModel's
   existing dirty-marking call path.
2. Queuing/batching dirty cells per edit.
3. Debouncing the eventual flush so a burst of rapid edits collapses
   into one pending recalc rather than one per edit.
4. An explicit, synchronous manual flush API.
5. Four lifecycle events: `recalc-scheduled`, `recalc-flush-start`,
   `recalc-flush-complete`, `recalc-cancelled`.
6. A deterministic snapshot of "what's pending" with stable ordering.

It does **not** implement, call, or scaffold beyond what already
existed: incremental recalculation, a dependency graph, formula
evaluation, backend model execution, any Run/recalculate network
call, automatic Save, live KPI updates, or any financial formula
change. `flushScheduledRecalc()`/`getPendingRecalcSnapshot()` only
read this module's own existing dirty state
(`getDirtySheets()`/`getDirtyCells()`) and reshape it — no calculation
of any kind occurs.

## API shape chosen: Option A (extend FcLiveModel directly)

The task offered two shapes: extend `FcLiveModel` directly (Option A),
or a separate `static/modelling/recalc-scheduler.js` module/namespace
that subscribes to FcLiveModel's events (Option B).

**Option A was chosen.** `FcLiveModel.scheduler` (the stub
`queueEvent`/`queueLength`/`flush`/`peek` surface from C2-PR1) already
established that a scheduler-shaped API living directly on
`FcLiveModel` is this codebase's existing convention — a separate
module would just re-subscribe to the same `markCellDirty`/`clearDirty`
call sites this file already owns, adding a second file and a second
script-tag load-order dependency for no functional benefit. Extending
in place also makes the "FcLiveModel remains the sole dirty-state
owner" invariant trivially easy to audit: the new scheduler functions
are private closures inside the same IIFE, calling the same private
`getDirtySheets()`/`getDirtyCells()`/`isProjectDirty()` functions the
rest of the module already exposes — there is no second event
subscription, no second copy of dirty data, and no risk of drift
between two files' notions of "dirty."

New public API surface added to `window.FcLiveModel`:

- `scheduleRecalc(reason, meta)` — (re)arms a 250ms debounce timer;
  called automatically by `markCellDirty()` for every dirty edit, and
  safely callable manually too.
- `flushScheduledRecalc()` — explicit synchronous flush; also what the
  debounce timer calls automatically when it fires.
- `cancelScheduledRecalc(reason)` — cancels any pending debounce timer;
  called automatically by `clearDirty()` (and therefore by
  `clearCellDirty`/`clearSheetDirty`/`clearAllDirty`, and by the
  C2-PR2 `applyWorkspaceStateMeta` → `clearAllDirty` clean-server-meta
  sync path).
- `hasPendingRecalc()` — `true` while a debounce timer is armed.
- `getPendingRecalcSnapshot()` — deterministic snapshot, described
  below.

## Ownership: who owns dirty state vs who owns scheduling

**`FcLiveModel`'s existing dirty-state functions
(`markCellDirty`/`isCellDirty`/`isSheetDirty`/`isProjectDirty`/
`getDirtyCells`/`getDirtySheets`/`clearCellDirty`/`clearSheetDirty`/
`clearAllDirty`) remain the single, sole source of dirty-state truth,
completely unchanged by this PR.** The scheduler added in this PR owns
exactly one piece of state of its own: `_recalcTimer` (is a debounce
timer currently armed) and `_recalcReason` (the most recent schedule
reason, for event payloads). It tracks **zero** parallel copy of which
cells/sheets are dirty — every snapshot is derived live, at flush time,
by reading `getDirtySheets()`/`getDirtyCells()`. If a consumer cleared
dirty state via some path that somehow bypassed `clearDirty()`, the
next-computed snapshot would still correctly reflect the live dirty
state, because nothing is cached.

## Dirty-state integration: exact hook points

- **Schedule:** `markCellDirty(gridId, addr, before, after)` — at the
  very end of the function, after dirty flags and the existing
  pub/sub events (`cell-dirty`/`sheet-dirty`/`project-dirty`) have been
  emitted — now also calls `scheduleRecalc('cell-changed', {gridId,
  addr})`. No new DOM listener was added; this reuses the exact
  `change`-event-driven write path (`FcCellIO.writeValue` →
  `change` → `FcLiveModel._onChange` → `markCellDirty`) already shared
  by direct typing, undo/redo, fill, and paste since C2-PR1. A
  non-editable cell write still no-ops at `FcCellIO.writeValue` before
  ever reaching `markCellDirty`, so it never schedules a recalc either.
- **Cancel:** `clearDirty(gridId)` (the function `clearSheetDirty` and
  `clearAllDirty` already delegate to, alongside the per-gridId and
  whole-project branches) now calls `cancelScheduledRecalc('dirty-
  cleared')` at the end of both branches. This means cancellation
  fires consistently from every dirty-clearing path that already
  existed: `clearCellDirty` → (when it empties the last dirty cell in
  a sheet) → `clearDirty(gridId)`; `clearSheetDirty(gridId)`;
  `clearAllDirty()`; and transitively, `app.js`'s `applyWorkspaceStateMeta`
  → `clearAllDirty()` clean-server-meta hook and its `#btn-save`
  `htmx:afterRequest` → `clearAllDirty()` hook from C2-PR2 — neither of
  those call sites needed to change at all.

## Event lifecycle

| Event | When it fires |
|---|---|
| `recalc-scheduled` | Every time `scheduleRecalc()` (re)arms the debounce timer — i.e. on every dirty edit, even if a timer was already pending (the timer is reset, not stacked, but the event still fires so a consumer can observe each edit attempt). Payload: `{reason, meta}`. |
| `recalc-flush-start` | At the start of `flushScheduledRecalc()`, before the snapshot is built. Payload: `{reason}`. |
| `recalc-flush-complete` | At the end of `flushScheduledRecalc()`, after the snapshot is built. Payload: `{reason, snapshot}`. Always fires after the matching `recalc-flush-start` in the same call, synchronously, with no other event interleaved. |
| `recalc-cancelled` | Whenever `cancelScheduledRecalc()` actually cancels an armed timer (no-op silently if nothing was pending). Payload: `{reason}`. |

A debounce-window burst of edits produces many `recalc-scheduled`
events (one per edit) but only **one** eventual
`recalc-flush-start`/`recalc-flush-complete` pair, because each new
edit resets the same timer rather than arming an additional one.

## Deterministic snapshot format

```js
{
  grids: [
    { gridId: "capex", addrs: ["capex!row1!amount", "capex!row2!amount"] },
    { gridId: "seniordebt", addrs: ["seniordebt!gearing_pct"] }
  ],
  projectDirty: true
}
```

Sort rules, applied at snapshot-build time (`getPendingRecalcSnapshot`):

- `grids` is sorted alphabetically by `gridId` (`getDirtySheets().slice().sort()`).
- `addrs` within each grid is sorted alphabetically
  (`getDirtyCells(gridId).slice().sort()`).
- No timestamp, session id, or any other non-reproducible field is
  included anywhere in the snapshot, so two snapshots built from the
  same logical set of dirty cells/sheets — regardless of the order in
  which those edits actually happened, or how much wall-clock time
  elapsed between them — are deep-equal (`assert snap1 == snap2` in
  the new test suite, via Python dict/list equality after
  `page.evaluate`).

## Why no recalculation occurs yet

This PR is purely a scheduling/batching/debouncing shell around dirty
state that already exists. `flushScheduledRecalc()` never evaluates a
formula, never walks a dependency graph (none exists anywhere in the
client or server), and never calls Save, Run, or any backend endpoint
— it only reads `FcLiveModel`'s own dirty-state accessors and reshapes
the result into a stable-ordering snapshot. Building this scheduling
layer first, decoupled from "what to actually recompute," lets a
future PR plug in real incremental-recalculation logic at the single
`flushScheduledRecalc()` seam without having to also invent batching/
debounce/determinism machinery at the same time.

## What the next step toward dependency graph / incremental recalc would look like

(Informational only — not implemented here.)

1. A dependency graph (which cells/outputs each cell address feeds)
   would need to be built — most plausibly server-side, alongside or
   informed by the existing financial input-adapter code
   (`app/input_adapter.py`), then exposed to the client in a form that
   could be matched against the `gridId`/`addr` pairs this PR's
   snapshot already produces.
2. `getPendingRecalcSnapshot()`'s sorted `{gridId, addrs}` shape is
   already exactly the scoping signal such a consumer would need to
   decide which subset of a dependency graph to walk, instead of
   recomputing the whole project on every flush.
3. The pre-existing `getBatch()`/`flushBatch()` (C2-PR1) still give a
   future consumer the net per-cell before/after values for a batch of
   edits, complementary to this PR's "which cells/sheets are dirty"
   snapshot.
4. `flushScheduledRecalc()` is the single seam a future PR would
   extend to actually trigger a real computation — almost certainly
   via an explicit, debounced server round trip (e.g. a "preview"
   endpoint) rather than a client-side reimplementation of any
   formula, to preserve the existing single-source-of-truth-is-the-
   server invariant Save/Run/export already rely on. This PR
   deliberately stops short of that: `flushScheduledRecalc()` returns
   a snapshot to its caller and to its own `recalc-flush-complete`
   event, but nothing in this PR (or any file it touches) reads that
   return value to do anything beyond what the new tests assert.
5. Cancellation on dirty-clear (this PR) already gives a future
   incremental-recalc consumer the correct invariant for free: a
   recalc can never fire for dirty state that's already been
   superseded by a Save — it's cancelled the moment `clearAllDirty()`
   (or any of its narrower siblings) runs.

## Test coverage added

`tests/test_c2_pr3_recalc_scheduler_browser.py` — 10 new
production-route Playwright tests (real `uvicorn` subprocess, real
auth, real project creation, mirroring
`tests/test_c2_pr2_dirty_state_unification_browser.py`'s pattern),
covering all 11 required-behaviour points from the task spec (point 11
is the full existing-suite regression run, reported separately below):

1. `test_cell_edit_schedules_recalc`
2. `test_rapid_edits_batch_into_one_pending_flush`
3. `test_multiple_sheets_tracked_independently_in_snapshot`
4. `test_pending_snapshot_is_deterministic`
5. `test_manual_flush_emits_start_then_complete`
6. `test_flush_does_not_clear_dirty_state`
7. `test_save_cancels_pending_recalc`
8. `test_non_editable_cell_no_op_does_not_schedule_recalc`
9. `test_no_backend_run_request_fires`
10. `test_no_financial_output_changes_from_schedule_and_flush`

## Integration constraint confirmation

`static/app.js`'s dirty banner / Run gating / Save-clears-dirty flow
(`_syncDirtyFromLiveModel`, `applyWorkspaceStateMeta`, the `#btn-save`
`htmx:afterRequest` listener) is **byte-for-byte unchanged** by this
PR — `git diff main -- static/app.js` is empty. The scheduler only
reads from and is driven by `FcLiveModel`'s existing call sites; no
second dirty model was introduced anywhere.

## Files changed

- `static/modelling/live-model.js` — additive scheduler functions and
  hook calls described above; every C2-PR1/C2-PR2 function/behaviour
  is unchanged.
- `tests/test_c2_pr3_recalc_scheduler_browser.py` — new test file.
- `docs/C2_PR3_RECALC_SCHEDULER_FOUNDATION_NOTE.md` — this note.

No change was made to `static/app.js`, any template, any server route/
service file, or any file under `domain/`, `app/waterfall_core.py`,
`app/input_adapter.py`, or `app/project_factories.py` (confirmed via
`git diff --stat main -- domain app/waterfall_core.py
app/input_adapter.py app/project_factories.py`, which is empty).

## Confirmation: no backend Run/recalc network calls

The new scheduler code makes no network call of any kind — confirmed
by `grep -in "fetch(\|xmlhttprequest" static/modelling/live-model.js`
matching nothing, and by the new
`test_no_backend_run_request_fires` browser test asserting zero
`/run`- or `recalc`-shaped requests fire during an edit + manual-flush
sequence (via Playwright's `page.on("request", ...)`).
