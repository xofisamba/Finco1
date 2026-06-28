# C2-PR6: Incremental Recalculation Preview Boundary — Implementation Note

## Scope

This PR adds a **client-side preview-payload-building boundary**,
sitting immediately after C2-PR5's execution stub in
`FcRecalcExecutor.execute()`. It is deliberately a deterministic
**payload builder only** — it never calls a backend endpoint, never
makes any network request, never evaluates a financial formula, never
mutates the DOM, and never mutates any dirty-state/scheduler/
dependency-graph/execution state. Its entire purpose is to establish,
exercise, and test the request-payload *shape* a future PR's real
backend preview/recalc call will need, without that future PR having
to also invent the payload contract or the test harness at the same
time.

It implements **infrastructure only**:

1. A new standalone module, `window.FcRecalcPreview`
   (`static/modelling/recalc-preview.js`), exposing
   `buildPreviewPayload(snapshot, execution, options)`,
   `validatePreviewPayload(payload)`, `getLastPreviewPayload()`,
   `clearLastPreviewPayload()`.
2. One additive integration point in `FcRecalcExecutor.execute()`:
   after building its existing no-op result object (unchanged from
   C2-PR5), it optionally calls `FcRecalcPreview.buildPreviewPayload()`
   and attaches the result under two new, additive fields:
   `previewPrepared: true` and `previewPayload: {...}`.
3. A new `<script>` tag in `app/templates/base.html` loading
   `recalc-preview.js` before `recalc-executor.js` (and after
   `dependency-graph.js`).

It does **not** implement, call, or scaffold: a backend preview
endpoint, any network request, real recalculation, formula evaluation,
model engine invocation, KPI updates, Save/Run changes, persistence
changes, or export changes.

## Ownership

`FcRecalcPreview` is a new, standalone module — like
`FcDependencyGraph` (C2-PR4) and `FcRecalcExecutor` (C2-PR5),
deliberately not folded into `FcLiveModel`. Rationale: it is a
different kind of thing again — not a source of dirty-state truth
(`FcLiveModel`'s job), not a stateless lookup table
(`FcDependencyGraph`'s job), not the execution-result owner
(`FcRecalcExecutor`'s job), but a *consumer* of the snapshot and
execution result that owns exactly one piece of state of its own: the
most recently built payload (`_lastPreviewPayload`). It never reads
`FcLiveModel`'s dirty-state accessors directly, never reads cell/grid
DOM markup, and never recomputes a dependency mapping or an execution
result — it strictly reads the `snapshot`/`execution` objects it is
handed, plus (for the optional `project` field) the current page's URL
query string.

Script load order in `app/templates/base.html`: `recalc-preview.js`
loads after `dependency-graph.js` and **before** `recalc-executor.js`,
so `window.FcRecalcPreview` is always defined by the time
`FcRecalcExecutor.execute()` is ever called. If, for any reason,
`FcRecalcPreview` is absent (e.g. an isolated test fixture that only
loads `live-model.js`/`dependency-graph.js`/`recalc-executor.js`),
`execute()` skips the preview-attachment step entirely and returns
exactly the result shape C2-PR5 already returned — guarded by
`if (window.FcRecalcPreview && typeof window.FcRecalcPreview.buildPreviewPayload === 'function')`.

## Payload contract — exact shape

```js
{
  valid: true | false,
  dirtyCells: [...sorted, deduplicated "gridId!key" strings],
  affectedGroups: [...sorted, deduplicated group strings],
  projectDirty: <boolean>,
  reason: <string>,
  executionStatus: <string | null>,
  project: <string | null>
}
```

- `valid` is `true` only when the `snapshot` argument is an object
  with an array `grids` field; otherwise `false` (and every other
  field degrades to its safest default — see "Safety" below).
- `dirtyCells` is derived identically to `FcRecalcExecutor`'s own
  `dirtyCells` field: the deduplicated, sorted, flat list of every
  `addr` string across every `grid.addrs` in `snapshot.grids`, used
  verbatim (already fully-qualified `gridId!key` strings — not
  re-prefixed).
- `affectedGroups` prefers `execution.affectedGroups` when the
  `execution` argument is a well-formed object with that array field
  (since the execution result is the most "downstream", validated
  copy of this data); otherwise falls back to `snapshot.affectedGroups`.
  Always deduplicated and sorted.
- `projectDirty` is `snapshot.projectDirty` if it is a boolean,
  otherwise `false`.
- `reason` prefers `execution.reason`, then `options.reason`, then the
  literal default `"manual-flush"` — mirroring `FcRecalcExecutor`'s own
  default-reason convention.
- `executionStatus` is `execution.status` if `execution` is an object
  with a non-empty string `status` field, otherwise `null` — never
  fabricated, never defaulted to a placeholder string.
- `project` is described under "Metadata handling" below.
- No timestamp, session id, or other non-reproducible field appears
  anywhere in the payload.

## Deterministic ordering rules

Identical to the ordering discipline already established by
C2-PR3/PR4/PR5:

- `dirtyCells` and `affectedGroups` are deduplicated and
  alphabetically sorted at build time, regardless of the order their
  source arrays (`snapshot.grids[].addrs`, `execution.affectedGroups`/
  `snapshot.affectedGroups`) were populated in.
- Two snapshots representing the same logical dirty set, built via
  different "edit order" (e.g. grids listed in a different order, or
  `addrs` within a grid listed in a different order), produce
  structurally equal payloads — confirmed by
  `test_payload_deterministic_regardless_of_edit_order`.
- No field is randomly generated or wall-clock-dependent.

## Metadata handling decision

**Decision: read the existing `project` URL query-string parameter;
omit/null everything else rather than inventing a new server-rendered
field.**

Investigation before deciding what (if anything) safely/reliably
identifies "which project/scenario is this":

- The **`project` query-string parameter** is already present on
  every real production workspace URL — confirmed both by grepping
  the router (`main_web.py`/route handlers reading `request.query_params.get("project")`)
  and by the existing C2-PR3/PR4/PR5 Playwright fixtures themselves,
  every one of which navigates to `f"{live_server}/?project={project_code}"`.
  This is the most reliable, always-present signal available without
  inventing any new server-rendered markup — it is read defensively
  via `new URLSearchParams(window.location.search).get('project')`
  (the same `URLSearchParams` constructor `static/app.js` already uses
  elsewhere), returning `null` if absent/empty or if `window`/
  `window.location`/`URLSearchParams` is somehow unavailable (e.g. a
  non-browser test harness evaluating this file directly).
- A **scenario identifier** was investigated and explicitly **not**
  included. Several narrow partials carry a `data-*-scenario-id`/
  `data-active-scenario-id` attribute (e.g. `scenario_tab.html`'s
  `data-active-scenario-id` on its own root element), but none of
  these are guaranteed to be present/rendered on every workspace tab —
  unlike the `project` query param, which is on the URL of every page
  view regardless of which tab is active. Rather than reading a
  possibly-absent DOM element and guessing/defaulting, this PR omits
  the scenario field from the payload entirely. A future PR wanting a
  reliable scenario identifier would need either a new, consistently-
  rendered data attribute (e.g. on the workspace shell root, rendered
  on every tab) or a dedicated read API exposed by an existing module
  — neither of which this PR invents.
- **`project` is `null`, never a fabricated value**, whenever the URL
  doesn't carry the parameter — confirmed by
  `test_missing_project_metadata_handled_safely`.

## Executor integration — exact hook point

`FcRecalcExecutor.execute()` (`static/modelling/recalc-executor.js`)
gained exactly one additive block, immediately after building its
existing C2-PR5 result object and before recording/returning it:

```js
var result = {
  status: status,
  executed: false,
  affectedGroups: affectedGroups,
  dirtyCells: dirtyCells,
  reason: reason
};

if (window.FcRecalcPreview && typeof window.FcRecalcPreview.buildPreviewPayload === 'function') {
  result.previewPrepared = true;
  result.previewPayload = window.FcRecalcPreview.buildPreviewPayload(snapshot, result, { reason: reason });
}

_lastExecution = result;
return result;
```

This is the only change to `recalc-executor.js`. It:

- Adds two new, additive fields (`previewPrepared`, `previewPayload`)
  to the result object — every pre-existing field (`status`,
  `executed`, `affectedGroups`, `dirtyCells`, `reason`) is untouched,
  so every C2-PR5 test assertion against the result shape continues to
  pass unmodified (confirmed by re-running
  `tests/test_c2_pr5_recalc_executor_browser.py` — all 9 tests still
  pass).
- Calls into `FcRecalcPreview.buildPreviewPayload()` rather than
  duplicating any payload-building logic inline in
  `recalc-executor.js`.
- Performs no calculation, no network call, and no dirty-state
  mutation.
- Degrades gracefully (no `previewPrepared`/`previewPayload` fields at
  all) if `FcRecalcPreview` isn't loaded.
- Is **not** applied to the `canExecute(snapshot) === false` /
  `status: "stubbed-invalid"` early-return path — a preview payload is
  only meaningfully built once `execute()` has already validated the
  snapshot is well-formed enough to derive `affectedGroups`/
  `dirtyCells` from. This keeps the invalid-input path simple and
  identical to C2-PR5's, while `FcRecalcPreview.buildPreviewPayload()`
  itself remains independently callable (and independently safe) on
  any input, including malformed ones, for direct callers.

`static/modelling/live-model.js` required **zero changes** for this
PR — `flushScheduledRecalc()` already calls
`FcRecalcExecutor.execute(snapshot, { reason: reason })` and attaches
whatever it returns under `snapshot.execution` (C2-PR5's hook point);
since this PR's `previewPayload`/`previewPrepared` fields are additive
fields on that same return value, they automatically appear on
`snapshot.execution.previewPayload` with no further wiring.

## Safety: malformed input handling

`buildPreviewPayload(snapshot, execution, options)` **never throws**.
The chosen approach (documented explicitly, per the task's
"document which approach you took" requirement): **return a valid,
safe payload shape with an explicit `valid: false` flag**, rather than
an exception or a differently-shaped error object. Concretely:

- If `snapshot` is `null`/`undefined`/not an object/has no array
  `grids` field: `valid: false`, `dirtyCells: []`,
  `affectedGroups: []` (unless `execution.affectedGroups` is present
  and well-formed, in which case it's still used — a malformed
  snapshot doesn't have to poison an otherwise-valid execution's
  group list), `projectDirty: false`.
- If `execution` is `null`/`undefined`/not an object/malformed: all
  execution-derived fields (`executionStatus`, the
  `affectedGroups`/`reason` preference) silently fall back to their
  snapshot-derived or default values — never throws, never includes a
  fabricated status string.
- `validatePreviewPayload(payload)` is a separate, non-throwing
  shape-check predicate over an already-built (or hand-constructed)
  payload object — it returns `false` for anything that doesn't match
  the exact field/type contract above, including `null`/`undefined`/
  non-object input.

Confirmed by `test_malformed_snapshot_never_throws`, which calls
`buildPreviewPayload` with `null`, `undefined`, `{}`, and a
non-object string + a number, asserting no exception and a
`valid: false` payload with empty arrays in every case.

## Why no backend request occurs in this PR

Exactly as in C2-PR1 through C2-PR5: this PR answers "what request
WOULD a future backend preview/recalc endpoint need," not "what does
calling that endpoint return." `buildPreviewPayload()` never makes a
network/AJAX/htmx call of any kind — confirmed via `grep -in
"fetch(\|xmlhttprequest\|htmx.trigger\|htmx.ajax"
static/modelling/recalc-preview.js static/modelling/recalc-executor.js`,
which matches nothing in either file, and by the new
`test_no_backend_request_fires` browser test (the most important test
in the new suite, per the task spec), which monitors every network
request fired during an edit + flush + manual preview-build sequence
and asserts none of them target anything `/run`-, `recalc`-, or
`preview`-shaped.

## What a future backend preview endpoint would need (informational only — not implemented here)

1. **Request shape.** This PR's payload (`dirtyCells`,
   `affectedGroups`, `projectDirty`, `reason`, `executionStatus`,
   `project`) is already close to a complete request body for a future
   `POST /scenarios/{project}/preview`-shaped endpoint — it would most
   plausibly be sent close to verbatim, perhaps with `project` promoted
   into the URL path (since it's already available there) rather than
   the JSON body.
2. **Response shape.** A real backend would need to return, per
   affected group, the newly-recomputed output values for that
   group — almost certainly scoped narrowly (e.g.
   `{ "overview-kpis": {...}, "senior-debt": {...} }`) rather than the
   whole project, to keep a preview call fast. This PR does not define
   that response shape; it is purely a request-side concern.
3. **Where the call would be made.** The natural seam is inside
   `FcRecalcExecutor.execute()` itself — once `execute()` stops being a
   no-op stub, it would call the new endpoint with
   `FcRecalcPreview.buildPreviewPayload()`'s output as the request
   body, await the response, and set `executed: true`/`status:
   "executed"` (or an error status) instead of always returning
   `executed: false`. `FcRecalcPreview` itself would likely need no
   change at all — it would keep building the same request payload; only
   `FcRecalcExecutor` would gain the actual network call.
4. **Debouncing/concurrency.** `FcLiveModel.scheduleRecalc()`'s
   existing 250ms debounce (C2-PR3) already gives a future real preview
   call sensible batching for free; a future PR would likely also need
   to guard against overlapping in-flight preview requests (e.g. if the
   user keeps editing while a previous preview call is still pending)
   — out of scope here, but worth flagging since this PR's payload
   builder is synchronous and stateless per call, so it does not by
   itself solve that concurrency question.
5. **Single-source-of-truth invariant.** Exactly as every prior C2 PR's
   note has flagged: a real preview call should be a genuine server
   round trip, not a client-side reimplementation of any formula, to
   preserve the existing invariant that Save/Run/export already rely
   on (the server is the sole source of truth for financial outputs).

## What remains explicitly out of scope

- A backend preview/recalc endpoint, or any network request to one.
  Confirmed via the grep above and the new
  `test_no_backend_request_fires` test.
- Real recalculation, formula evaluation, or any call into
  `app/waterfall_core.py`, `app/input_adapter.py`,
  `app/project_factories.py`, or any file under `domain/`. Confirmed
  via `git diff --stat main -- domain app/waterfall_core.py
  app/input_adapter.py app/project_factories.py`, which is empty.
- Any DOM/KPI value change. Confirmed by the new
  `test_no_financial_values_change` browser test.
- Any dirty-state mutation. Confirmed by the new
  `test_dirty_state_unchanged_by_preview_building` browser test.
- Any change to `static/app.js`. Confirmed via `git diff --stat main
  -- static/app.js`, empty.
- Any change to `static/modelling/live-model.js` — this PR's entire
  integration happens inside `recalc-executor.js`, since
  `live-model.js`'s existing C2-PR5 hook point already forwards
  whatever `execute()` returns verbatim.

## Test coverage added

`tests/test_c2_pr6_recalc_preview_browser.py` — 11 new production-
route Playwright tests (real `uvicorn` subprocess, real auth, real
project creation, mirroring
`tests/test_c2_pr5_recalc_executor_browser.py`'s pattern), covering
all 9 testable required-behaviour points from the task spec (point 10,
the full existing-suite regression run, is reported separately below;
one bonus test for `getLastPreviewPayload`/`clearLastPreviewPayload`
and one bonus defensive-safety test were also added):

1. `test_preview_builds_from_valid_snapshot`
2. `test_payload_deterministic_regardless_of_edit_order`
3. `test_payload_includes_dirty_cells_and_affected_groups`
4. `test_unknown_groups_handled_safely`
5. `test_missing_project_metadata_handled_safely`
6. `test_flush_complete_event_includes_preview_payload`
7. `test_no_backend_request_fires`
8. `test_dirty_state_unchanged_by_preview_building`
9. `test_no_financial_values_change`
10. `test_get_and_clear_last_preview_payload` (bonus)
11. `test_malformed_snapshot_never_throws` (bonus)

## Files changed

- `static/modelling/recalc-preview.js` — new module, the preview
  payload builder API.
- `static/modelling/recalc-executor.js` — one additive block inside
  `execute()`, described above; every other function and behaviour is
  byte-for-byte unchanged.
- `app/templates/base.html` — one new `<script defer>` tag for
  `recalc-preview.js`, inserted before `recalc-executor.js`'s tag
  (after `dependency-graph.js`'s tag).
- `tests/test_c2_pr6_recalc_preview_browser.py` — new test file.
- `docs/C2_PR6_INCREMENTAL_RECALC_PREVIEW_BOUNDARY_NOTE.md` — this
  note.

No change was made to `static/app.js` (confirmed via `git diff --stat
main -- static/app.js`, empty), to `static/modelling/live-model.js`
(confirmed via `git diff --stat main -- static/modelling/live-model.js`,
empty), and no change was made to any file under `domain/`,
`app/waterfall_core.py`, `app/input_adapter.py`, or
`app/project_factories.py` (confirmed via `git diff --stat main --
domain app/waterfall_core.py app/input_adapter.py
app/project_factories.py`, empty).

## Note: a pre-existing, unrelated test failure

`tests/test_c2_pr1_live_model.py::TestStaticWiring::test_no_recalculation_formula_dependency_or_saverun_code_in_live_model`
asserts that the literal substring `"dependencygraph"` never appears
in `static/modelling/live-model.js`. This assertion was already broken
on `main` **before this PR**, as soon as C2-PR4 added the
`window.FcDependencyGraph` reference and explanatory comment text to
`live-model.js` (and re-flagged, unaddressed, by C2-PR5). This PR does
not introduce, worsen, or fix that pre-existing failure — confirmed by
the fact that this PR makes zero changes to `live-model.js` at all, so
the failure's root cause is byte-for-byte identical to its state under
C2-PR5; it is flagged here for visibility, not addressed, since fixing
a prior PR's test assertion is out of this PR's scope.
