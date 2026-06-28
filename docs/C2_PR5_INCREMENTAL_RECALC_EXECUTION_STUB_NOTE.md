# C2-PR5: Incremental Recalculation Execution Stub — Implementation Note

## Scope

This PR adds the **first execution-layer boundary** for incremental
recalculation, sitting immediately after C2-PR4's dependency
resolution in `FcLiveModel.flushScheduledRecalc()`. It is deliberately
a deterministic **no-op stub** — it never calculates a financial
output, never calls a backend endpoint, and never mutates any
dirty-state/scheduler/dependency-graph state. Its entire purpose is to
establish, exercise, and test the seam a future PR will replace with a
real incremental-recalculation call, without that future PR having to
also invent the input/output contract, the integration hook, or the
test harness at the same time.

It implements **infrastructure only**:

1. A new standalone module, `window.FcRecalcExecutor`
   (`static/modelling/recalc-executor.js`), exposing
   `execute(snapshot, options)`, `canExecute(snapshot)`,
   `getLastExecution()`, `clearLastExecution()`.
2. One additive integration point in
   `FcLiveModel.flushScheduledRecalc()`: after C2-PR4's
   `snapshot.affectedGroups` is attached, the snapshot is handed to
   `FcRecalcExecutor.execute()` and the result is attached under
   `snapshot.execution`.
3. A new `<script>` tag in `app/templates/base.html` loading
   `recalc-executor.js` before `live-model.js`.

It does **not** implement, call, or scaffold: real recalculation,
formula evaluation, a backend Run/recalc/preview call, any network
request, model engine invocation, DOM/KPI updates, Save/persistence
changes, or export changes.

## Ownership

`FcRecalcExecutor` is a new, standalone module — like
`FcDependencyGraph` (C2-PR4), deliberately not folded into
`FcLiveModel`. Rationale: it is a different kind of thing again — not
a source of dirty-state truth (that's `FcLiveModel`'s job), not a
stateless lookup table (that's `FcDependencyGraph`'s job), but a
*consumer* of both that owns exactly one piece of state of its own:
the most recent `execute()` result (`_lastExecution`). It never reads
`FcLiveModel`'s dirty-state accessors directly, never reads the DOM,
and never recomputes a dependency mapping — it strictly reads the
`affectedGroups` field `FcDependencyGraph` already attached to the
snapshot it is handed, before this module is ever invoked.

Script load order in `app/templates/base.html`: `recalc-executor.js`
loads after `dependency-graph.js` and before `live-model.js`, so
`window.FcRecalcExecutor` is always defined by the time any flush
occurs. If, for any reason, `FcRecalcExecutor` is absent (e.g. an
isolated test fixture that only loads `live-model.js` and
`dependency-graph.js`), `flushScheduledRecalc()` skips the
`execution`-attachment step entirely and returns exactly the snapshot
shape C2-PR4 already returned — guarded by
`if (window.FcRecalcExecutor && typeof window.FcRecalcExecutor.execute === 'function')`.

## Input/output contract

**Input:** a snapshot shaped exactly like the one
`FcLiveModel.flushScheduledRecalc()` produces after C2-PR4's
dependency-resolution step:

```js
{
  grids: [{ gridId: "capex", addrs: ["capex!code.amount", ...] }, ...],
  projectDirty: true,
  affectedGroups: ["capex", "overview-kpis", "senior-debt"]
}
```

`addrs` entries are the raw `data-fc-addr` attribute values, which are
already fully-qualified `gridId!key` strings (confirmed by grepping
`app/templates/partials/sheet_capex.html`, e.g.
`"data-fc-addr": "capex!" ~ child.code ~ ".amount"`) — `gridId` on the
grid object is a separate, redundant field for grouping, not a prefix
that needs to be re-applied.

`canExecute(snapshot)` is a defensive, non-throwing predicate: it
requires `snapshot` to be an object with a `grids` array, where every
present grid entry has a non-empty string `gridId` and an `addrs`
array of strings. `projectDirty` and `affectedGroups` are tolerated as
optional/missing, so the executor remains usable even against a
C2-PR3-only snapshot (no `FcDependencyGraph` loaded).

**Output:** a deterministic, plain-data result object:

```js
{
  status: "stubbed" | "stubbed-unknown" | "stubbed-empty" | "stubbed-invalid",
  executed: false,
  affectedGroups: [...sorted, deduplicated],
  dirtyCells: [...sorted, deduplicated fully-qualified addrs],
  reason: "<string, from options.reason, default 'manual-flush'>"
}
```

- `executed` is **always `false`** in this PR — there is no code path
  in which this stub performs real work.
- `status` distinguishes four cases, all equally safe/no-op:
  - `"stubbed"` — the common case: a well-formed snapshot with some
    dirty cells and/or known affected groups.
  - `"stubbed-unknown"` — `snapshot.affectedGroups` contains
    `"unknown"` (C2-PR4's conservative fallback group). Still a
    no-op; this status exists purely so a future diagnostic/log
    consumer can distinguish "we know exactly what this affects" from
    "we had to fall back to the broad unknown-address guess."
  - `"stubbed-empty"` — the snapshot passed `canExecute` but carries
    no dirty grids/addrs and no affected groups at all (e.g. called
    directly with `{ grids: [] }`).
  - `"stubbed-invalid"` — the snapshot failed `canExecute`'s shape
    check; `execute()` still never throws, it just returns this status
    with empty `affectedGroups`/`dirtyCells`.
- `affectedGroups` is the deduplicated, sorted copy of
  `snapshot.affectedGroups` (empty array if absent/malformed).
- `dirtyCells` is the deduplicated, sorted flat list of every addr
  string across every `grid.addrs` in the snapshot, used verbatim
  (not re-prefixed with `gridId`, since they're already fully
  qualified — see above).
- `reason` defaults to `"manual-flush"` and is otherwise whatever
  string `options.reason` was when `execute()` was called (the
  scheduler integration passes `flushScheduledRecalc()`'s own
  `reason`, e.g. `"cell-changed"`).
- No timestamp, session id, or other non-reproducible field appears
  anywhere in the result — two logically-equal snapshots, however
  differently ordered, always produce deep-equal results.

## Scheduler integration — exact hook point

`FcLiveModel.flushScheduledRecalc()` (`static/modelling/live-model.js`)
gained exactly one additive block, immediately after the existing
C2-PR4 dependency-resolution block and before emitting
`recalc-flush-complete`:

```js
if (window.FcDependencyGraph && typeof window.FcDependencyGraph.resolveSnapshot === 'function') {
  snapshot.affectedGroups = window.FcDependencyGraph.resolveSnapshot(snapshot);
}
if (window.FcRecalcExecutor && typeof window.FcRecalcExecutor.execute === 'function') {
  snapshot.execution = window.FcRecalcExecutor.execute(snapshot, { reason: reason });
}
_emit('recalc-flush-complete', { reason: reason, snapshot: snapshot });
```

This is the only change to `live-model.js`. It:

- Adds a new `execution` field to the snapshot object — every
  pre-existing field (`grids`, `projectDirty`, `affectedGroups`) is
  untouched, so every C2-PR3/C2-PR4 test assertion against the
  snapshot shape continues to pass unmodified (confirmed by re-running
  both prior test suites — all tests still pass, modulo one
  pre-existing C2-PR1 test failure documented below that predates this
  PR).
- Calls into `FcRecalcExecutor.execute()` rather than duplicating any
  stub logic inline in `live-model.js`.
- Performs no calculation, no network call, and no dirty-state
  mutation.
- Degrades gracefully (no `execution` field at all) if
  `FcRecalcExecutor` isn't loaded.

## Why execution is stubbed (and what a future PR would change)

(Informational only — not implemented here.)

This PR exists to decouple "where does the execution call happen and
what shape does it take" from "what does the execution actually
compute" — exactly the same decoupling C2-PR3 applied to scheduling vs.
recalculation, and C2-PR4 applied to dependency mapping vs.
recalculation. A future PR implementing real incremental recalculation
would, almost certainly:

1. Keep the exact same call site
   (`FcRecalcExecutor.execute(snapshot, { reason })` inside
   `flushScheduledRecalc()`) and the exact same `canExecute()` shape
   check — only the body of `execute()` would change.
2. Replace the no-op body with (most plausibly) an explicit, debounced
   server round trip to a new "preview"/"recalc" endpoint, passing
   `snapshot.affectedGroups` and/or `snapshot.grids` so the server can
   selectively recompute only the affected output groups instead of
   the whole project — preserving the existing single-source-of-truth-
   is-the-server invariant Save/Run/export already rely on.
3. Change `status`/`executed` to reflect a real outcome (e.g.
   `"executed"`/`true` on success, some `"error"` status on failure),
   while likely keeping `affectedGroups`/`dirtyCells`/`reason` as
   diagnostic echo fields.
4. Still need to decide separately (out of scope for that future PR's
   inheritance of this one) whether/how a real result feeds back into
   DOM/KPI updates — this PR's `execute()` deliberately never touches
   the DOM, so that remains a clean, not-yet-made decision.
5. `getLastExecution()`/`clearLastExecution()` would likely remain
   useful as-is for a future caller (e.g. a debug panel, or a test)
   wanting to inspect "what did the last recalc attempt do," whether
   real or stubbed.

## What remains explicitly out of scope

- Real recalculation, formula evaluation, or any call into
  `app/waterfall_core.py`, `app/input_adapter.py`,
  `app/project_factories.py`, or any file under `domain/`. Confirmed
  via `git diff --stat main -- domain app/waterfall_core.py
  app/input_adapter.py app/project_factories.py`, which is empty.
- Any backend Run/recalc/preview network call. Confirmed via `grep
  -in "fetch(\|xmlhttprequest\|htmx.trigger\|htmx.ajax"
  static/modelling/recalc-executor.js`, which matches nothing, and by
  the new `test_no_backend_run_request_fires` browser test.
- Any DOM/KPI value change. Confirmed by the new
  `test_no_financial_values_change` browser test.
- Any dirty-state mutation. Confirmed by the new
  `test_dirty_state_unchanged_after_execution` browser test.
- Any change to `static/app.js`. Confirmed via `git diff --stat main
  -- static/app.js`, empty.

## Test coverage added

`tests/test_c2_pr5_recalc_executor_browser.py` — 9 new production-
route Playwright tests (real `uvicorn` subprocess, real auth, real
project creation, mirroring
`tests/test_c2_pr4_dependency_graph_browser.py`'s pattern), covering 9
of the 10 required-behaviour points from the task spec (point 10 is
the full existing-suite regression run, reported separately below):

1. `test_executor_accepts_valid_snapshot`
2. `test_executor_returns_deterministic_no_op_result`
3. `test_unknown_groups_handled_safely`
4. `test_flush_complete_event_includes_execution`
5. `test_dirty_state_unchanged_after_execution`
6. `test_no_backend_run_request_fires`
7. `test_no_financial_values_change`
8. `test_get_last_execution_returns_last_result`
9. `test_clear_last_execution_resets_it`

## Files changed

- `static/modelling/recalc-executor.js` — new module, the executor
  API.
- `static/modelling/live-model.js` — one additive block inside
  `flushScheduledRecalc()`, described above; every other function and
  behaviour is byte-for-byte unchanged.
- `app/templates/base.html` — one new `<script defer>` tag for
  `recalc-executor.js`, inserted before `live-model.js`'s tag (after
  `dependency-graph.js`'s tag).
- `tests/test_c2_pr5_recalc_executor_browser.py` — new test file.
- `docs/C2_PR5_INCREMENTAL_RECALC_EXECUTION_STUB_NOTE.md` — this note.

No change was made to `static/app.js` (confirmed via `git diff --stat
main -- static/app.js`, empty), and no change was made to any file
under `domain/`, `app/waterfall_core.py`, `app/input_adapter.py`, or
`app/project_factories.py` (confirmed via `git diff --stat main --
domain app/waterfall_core.py app/input_adapter.py
app/project_factories.py`, empty).

## Note: a pre-existing, unrelated test failure

`tests/test_c2_pr1_live_model.py::TestStaticWiring::test_no_recalculation_formula_dependency_or_saverun_code_in_live_model`
asserts that the literal substring `"dependencygraph"` never appears
in `static/modelling/live-model.js`. This assertion was already
broken on `main` **before this PR**, as soon as C2-PR4 added the
`window.FcDependencyGraph` reference and explanatory comment text to
`live-model.js` — confirmed by reproducing the same failure with this
PR's changes stashed out, against `main`'s C2-PR4-merged state. This
PR does not introduce, worsen, or fix that pre-existing failure; it is
flagged here for visibility, not addressed, since fixing a prior PR's
test assertion is out of this PR's scope.
