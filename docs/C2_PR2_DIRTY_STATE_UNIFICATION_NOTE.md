# C2-PR2: Client-Side Dirty-State Unification — Implementation Note

## Scope

This PR makes `FcLiveModel` (`static/modelling/live-model.js`,
introduced inert in C2-PR1) the canonical client-side dirty-state
source for spreadsheet edits made through the C1 interaction layer,
while preserving 100% of the existing visible Save/Run/dirty-banner
behaviour for the legacy `#main-form`-driven workflow.

It implements **client-side dirty-state reconciliation only**:

- No incremental recalculation.
- No dependency graph.
- No formula evaluation.
- No change to financial formulas, `domain/*`, `app/waterfall_core.py`,
  `app/input_adapter.py`, or `app/project_factories.py` (confirmed
  empty via `git diff --stat main -- domain app/waterfall_core.py
  app/input_adapter.py app/project_factories.py`).
- No change to any Save/Run server endpoint, request contract, or
  response shape. The only "server-meta read" this PR relies on is the
  same `applyWorkspaceStateMeta(meta)` JS function the legacy app
  already called with server-provided JSON — nothing new was added on
  the server side.

## The dual dirty-state problem

Before this PR, two entirely separate, non-communicating notions of
"dirty" existed in the client:

1. **The legacy server-computed dirty state.** The dirty banner
   (`#workspace-unsaved-banner`), Run-button gating
   (`btn-run-model-sidebar`/`btn-compare-draft`/`btn-save-run`), and
   export-lineage guidance text were all driven exclusively by
   `meta.dirty`, a value computed **server-side** by diffing the
   current `#main-form` snapshot against the last-saved scenario
   snapshot (`snapshots_equal(...)` in
   `app/services/scenario_state_route_service.py`). The client side of
   this is `queueWorkspaceDraftPersist()` in `static/app.js`: any
   `input`/`change` on a field inside `#main-form` triggers a 350ms-
   debounced `POST /scenarios/state/draft`, whose JSON response is
   applied via `window.applyWorkspaceStateMeta(meta)`.

2. **FcLiveModel's dirty tracking (C2-PR1).** Already wired to observe
   every write made through `FcCellIO.writeValue` (the single write
   path shared by direct typing, `FcUndoManager` undo/redo,
   `FcFillController` fill, and `FcClipboardController` paste — all of
   them dispatch a native `change` event after writing, which
   `FcLiveModel._onChange` already listened for). But nothing ever
   *read* `FcLiveModel`'s dirty state — it was entirely inert from the
   UI's point of view.

**Critically, these two paths did not just duplicate each other — they
were blind to different things.** Investigation showed that the C1
spreadsheet grid cells (CAPEX, OPEX, Senior Debt, Revenue, etc.) live
**outside** `#main-form` entirely; `#main-form` is a separate hidden
mirror form containing only the original top-level scalar Inputs
fields (`capacity_mw`, `gearing_pct`, `tariff_eur_mwh`, ...). The
`data-grid-source` mirroring mechanism that was meant to bridge a C1
grid cell's `<input>` back into its corresponding hidden `#main-form`
field (`bindEditableGridInputs()` in `static/app.js`, matching by
`document.getElementById(sourceId)`) turns out to be a **pre-existing
no-op** for every per-field hidden input in `workspace_shell.html`,
because none of those hidden inputs are given an `id` attribute
matching their `name` (only `name=` is set). This is a latent,
pre-existing gap — **not something this PR fixes or is in scope to
fix** (no persistence/data-flow change was made; `Run`/`Save` still
`hx-include="#main-form"` exactly as before).

The practical consequence: **editing a C1 grid cell was, and remains,
invisible to the legacy server-diff dirty mechanism.** Before this PR,
a CAPEX/OPEX/Senior-Debt/Revenue cell edit produced *no* dirty banner,
*no* Run-button disabling, and *no* unsaved-state indication at all —
a real, user-visible gap, even though `FcLiveModel.isCellDirty()`
already correctly reported the edit internally (this is exactly what
the existing `test_edit_marks_dirty_and_undoable` C1 migration tests
already asserted, against `FcLiveModel`, not against the banner).

## The unified solution

`FcLiveModel` is now the single canonical dirty-state source. The
legacy banner/Run-gating/Save flow becomes a **consumer** of it,
without losing any of its pre-existing behaviour for `#main-form`
fields.

### `static/modelling/live-model.js`

Added (additive only — every C2-PR1 API/behaviour is unchanged):

- `clearCellDirty(gridId, addr)` — clears one cell's dirty flag; if it
  was the last dirty cell in its sheet, the sheet (and, transitively,
  the project) clears too.
- `clearSheetDirty(gridId)` / `clearAllDirty()` — idiomatic, more
  readable aliases of the pre-existing `clearDirty(gridId)` /
  `clearDirty()`. No behaviour change versus C2-PR1's `clearDirty`.
- `'sheet-clean'` / `'project-clean'` pub/sub events, emitted on the
  transition *out* of dirty (mirroring the existing `'sheet-dirty'` /
  `'project-dirty'` transition-in events), so a consumer can react to
  a dirty-state clear without polling.

`markCellDirty`/`isCellDirty`/`isSheetDirty`/`isProjectDirty` and the
DOM wiring (`change` on a real `<input>`/`<select>`/`<textarea>` inside
an editable `[data-fc-cell]`) are unchanged from C2-PR1 — they already
correctly covered every C1 write path (FcCellIO.writeValue is the
single write primitive `FcUndoManager`/`FcFillController`/
`FcClipboardController` all already shared, dispatching `change` after
every write), so no new DOM listener was added to any of those
modules. This satisfies the task's "wire into existing hooks rather
than adding redundant new ones" requirement.

### `static/app.js`

1. `_lastServerMeta` caches the most recent **genuine** server-provided
   meta (from `/scenarios/state/draft`, `/scenarios/{id}/load`,
   `/scenarios/state/discard`, or the post-`/run` sessionStorage save
   tag) — kept strictly separate from whatever gets painted to the DOM,
   so the overlay logic below never mistakes its own prior overlay for
   a real server answer.
2. `_syncDirtyFromLiveModel()` computes `effectiveDirty =
   FcLiveModel.isProjectDirty() || lastServerMeta.dirty` and re-applies
   it via the *existing*, unmodified `applyWorkspaceStateMeta()`
   function — so the banner, Run-button disabling, lineage guidance,
   and the `workspace_dirty_state` hidden field all update through the
   exact same code path they always did, just with an additional input
   signal. This function is subscribed once to `FcLiveModel`'s
   `'project-dirty'`/`'project-clean'` events at module load (not
   polled, and not a redundant new DOM listener — it consumes
   `FcLiveModel`'s existing pub/sub).
3. `applyWorkspaceStateMeta()` itself gained one small addition: when a
   genuine server meta reports `dirty === false` (e.g. right after
   `/scenarios/state/draft` confirms a clean `#main-form` snapshot, or
   after Discard), it calls `FcLiveModel.clearAllDirty()` — otherwise a
   C1 grid edit, once marked dirty, could never clear via that path
   (FcLiveModel dirty state is, by design from C2-PR1, only ever
   cleared by an explicit call).
4. The `#btn-save` click handler gained an `htmx:afterRequest` listener
   that calls `FcLiveModel.clearAllDirty()` on a successful response.
   This was necessary because `/scenarios/save`'s htmx response only
   ever swaps `#saved-scenario-panel` (the saved-scenario summary
   cards) — investigation confirmed it does **not** call
   `applyWorkspaceStateMeta` and never touched the banner element
   directly even before this PR (that swap target doesn't include the
   banner). A successful Save click unambiguously means "the user's
   current edits have just been persisted," so this is the correct,
   minimal point to also clear `FcLiveModel`'s state — without altering
   the `/scenarios/save` request/response contract itself.
5. A guard flag (`_applyingFromLiveModelSync`) prevents
   `_syncDirtyFromLiveModel` → `applyWorkspaceStateMeta` →
   `clearAllDirty` → (`'project-clean'`) → `_syncDirtyFromLiveModel`
   from ever looping.

### Integration points touched (minimal, surgical)

- `FcCellIO.writeValue` — **no change**. It already dispatches `change`
  after every write (and no-ops for a non-editable cell), which is the
  single seam `FcLiveModel` already observed in C2-PR1.
- `FcUndoManager` — **no change**. `undo()`/`redo()` already call
  `FcCellIO.writeValue` per restored cell, which already fires
  `change` and is already observed by `FcLiveModel`.
- `FcFillController` — **no change**, same reasoning.
- `FcClipboardController` — **no change**, same reasoning (and its
  paste path already no-ops at `FcCellIO.writeValue` for a read-only
  destination cell, so a rejected paste was already guaranteed to
  never mark anything dirty).
- `static/app.js` — the dirty-state *consumer* changes described above.
- `static/modelling/live-model.js` — the additive canonical-API
  extensions described above.

No change was made to any sheet template, `app/templates/base.html`'s
script include order, or any server route/service file.

## Undo / baseline-clearing decision

**Decision: conservative approach.** An undo that reverts a cell's
value back to what it was before the edit does **not** automatically
clear that cell's dirty flag.

**Rationale.** The task asked us to investigate whether genuine
load-time baseline data is available before deciding. It is not, in a
form usable for this purpose:

- `data-fc-raw` (the only `data-fc-*` attribute that carries a "raw"
  value) is **not a preserved original/last-saved baseline** — `
  FcCellIO.writeValue` overwrites it on every single write (see
  `static/interaction/cell-io.js`: `cell.el.setAttribute('data-fc-raw',
  value)`). After even one edit, the attribute reflects the *new*
  value, not the page-load value.
- There is no other place in the DOM or in any C1/C2 module that
  separately remembers "the value this cell had when the page was
  loaded / when it was last saved," independent of the value currently
  displayed.
- Building that plumbing (snapshotting every editable cell's value at
  page load or at the last successful Save, and diffing against it on
  every undo) is real, non-trivial new infrastructure — closer to a
  dependency-graph-adjacent bookkeeping concern than a "wire two
  existing things together" unification task, and was judged
  disproportionate to this PR's explicitly scoped objective.

Given that, undo's revert write flows through the exact same
`FcCellIO.writeValue` → `change` → `FcLiveModel.markCellDirty()` path
as any other edit. The cell is marked dirty by the undo's revert write
just as it would be by any new edit, **even if the reverted value
happens to equal the original baseline**. This is intentionally
conservative: the workspace may show "unsaved changes" in a case where,
strictly, the net effect of edit-then-undo was a no-op. It never
errs in the other, unsafe direction (silently showing "clean" while a
real edit is still pending).

This is covered explicitly by
`tests/test_c2_pr2_dirty_state_unification_browser.py::test_undo_keeps_cell_dirty_per_conservative_decision`.

A future PR that wants precise "back-to-baseline clears dirty"
behaviour would need to add an explicit baseline snapshot (e.g.
captured once per cell at page load, and refreshed on every successful
Save) — a small, well-scoped follow-up, but out of scope here.

## Why recalculation is still explicitly out of scope

This PR is a pure client-side state-reconciliation step. Marking a
cell/sheet/the project "dirty" is bookkeeping — it answers "has this
changed since the last clean point," not "what does this change
imply for any other cell or any financial output." No dependency
graph exists to answer the second question, and building one is
explicitly chartered as a separate, later C2 milestone. The scheduler
(`FcLiveModel.scheduler`) introduced in C2-PR1 and left untouched here
continues to only queue/flush plain event objects — it still never
calls a function or computes a value, and this PR adds zero new calls
to it (it does not need to: `markCellDirty()` already auto-queues a
`cell-changed` event for every dirty edit, unchanged from C2-PR1).

## What the next step toward incremental recalculation would look like

(Informational only — not implemented here.)

1. A dependency graph (which cells/outputs each cell address feeds)
   would need to be built — most plausibly server-side, alongside or
   informed by the existing financial input-adapter code, then
   exposed to the client in a form `FcLiveModel`'s event stream could
   be matched against.
2. `FcLiveModel.scheduler.flush()` already returns exactly the
   `{type: 'cell-changed', gridId, addr, before, after}` event stream
   such a consumer would need to decide what to recompute — this PR
   confirms that seam is still intact and unconsumed.
3. `getBatch()`/`flushBatch()` already give a future consumer the net
   per-cell change across a batch of edits (e.g. a paste/fill that
   touched many cells), so it would not need to re-derive "what
   actually changed" itself.
4. `isSheetDirty()`/`isProjectDirty()`/`getDirtySheets()` (and the new
   `clearCellDirty`/`clearSheetDirty` precision-clearing added here)
   already let a future consumer scope recalculation to only the
   sheets/cells that are actually dirty.
5. Any actual recalculation would still need to decide how (and
   whether) to call back into the financial engine
   (`app/waterfall_core.py`/`domain/*`) without violating the
   single-source-of-truth-is-the-server invariant the rest of the app
   relies on for Run/Save/export — almost certainly via a real,
   explicit server round trip (e.g. a debounced "preview" endpoint),
   not a client-side reimplementation of any formula.

None of the above is implemented, called, or scaffolded by this PR
beyond what C2-PR1 already scaffolded (the scheduler/event shape).

## Test coverage added

- `tests/test_c2_pr1_live_model_browser.py` — 7 new fixture-level unit
  tests for the new `clearCellDirty`/`clearSheetDirty`/`clearAllDirty`
  APIs and the new `'sheet-clean'`/`'project-clean'` pub/sub events
  (no server, no `app.js` — pure `FcLiveModel` behaviour, mirroring
  the existing C2-PR1 test style).
- `tests/test_c2_pr2_dirty_state_unification_browser.py` — 9 new
  production-route Playwright tests (real `uvicorn` subprocess, real
  auth, real project creation, mirroring
  `tests/test_capex_c1_migration_browser.py`'s pattern), covering all
  11 required-behaviour points from the task spec (points 10/11 are
  the existing-suite regression runs, reported separately below, not
  new test files):
  1. `test_editable_cell_edit_marks_live_model_dirty`
  2. `test_dirty_banner_updates_from_live_model`
  3. `test_run_gating_disabled_while_dirty`
  4. `test_save_clears_dirty_state`
  5. `test_non_editable_cell_no_op_does_not_mark_dirty`
  6. `test_undo_keeps_cell_dirty_per_conservative_decision`
  7. `test_multiple_sheets_dirty_independently`
  8. `test_clear_all_dirty_clears_project_dirty`
  9. `test_no_recalculation_request_fires_on_dirty_edit`

## Regression summary

See the PR description / final report for the full per-category
pass/fail table. In short: all pre-existing C1 PR1-PR9, sheet
migration, C1 final hardening, and C2-PR1 tests continue to pass
unmodified (except for 7 additive new tests appended to the existing
C2-PR1 browser test file). A pre-existing, unrelated set of 48 test
failures (stale hardcoded `BASE_DIR` path assumptions inside several
older `tests/test_phase16_*`/`test_phase17_*`/`test_phase_stab*` files
predating this branch, e.g. `/root/.openclaw/workspace/finco1/...`)
was confirmed, via `git stash`, to fail identically on the unmodified
branch tip — i.e. they are pre-existing environment-path breakage, not
a regression introduced by this PR.
