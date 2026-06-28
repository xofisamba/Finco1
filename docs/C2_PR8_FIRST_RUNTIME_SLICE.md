# C2-PR8: First End-to-End Incremental Runtime Slice — Implementation Note

## Scope

This PR closes the loop that C2-PR1 through C2-PR7 deliberately left
open: it wires the FIRST complete, real, end-to-end incremental
runtime path, from an editable C1 cell edit all the way to a real
network call and a DOM patch — proving the whole C2 architecture works
together, while still containing **zero real financial calculation
anywhere**.

Runtime path implemented:

```
Editable C1 cell edit
  -> FcLiveModel.markCellDirty()                    (existing, C2-PR1/2)
  -> FcLiveModel.scheduleRecalc() (250ms debounce)   (existing, C2-PR3)
  -> FcLiveModel.flushScheduledRecalc()              (existing, C2-PR3)
  -> FcDependencyGraph.resolveSnapshot()             (existing, C2-PR4)
     -> snapshot.affectedGroups attached
  -> FcRecalcExecutor.execute()                      (existing, C2-PR5)
     -> snapshot.execution attached
     -> FcRecalcPreview.buildPreviewPayload()        (existing, C2-PR6)
        -> snapshot.execution.previewPayload attached
  -> NEW: FcRecalcPreview.buildPreviewRequest(payload)
  -> NEW: a single real fetch(POST /model/preview)   <-- the new seam
  -> NEW: backend returns stubbed-valid JSON (main_web.py, extended)
  -> NEW: FcRuntimeRenderer.render(json)              (new module)
     -> patches #overview-runtime-status-value text
```

No financial formula evaluates differently anywhere. No persistence
model changes. No export behaviour changes. No call into
`app/waterfall_core.py`, `domain/*`, `app/input_adapter.py`, or
`app/project_factories.py`.

## The intentional, documented exception to "never auto-call fetch"

Every prior C2 PR (PR3 through PR7) explicitly built, tested, and
documented the invariant that no code path ever automatically makes a
network call as a result of an edit:

- C2-PR3: `test_no_backend_run_request_fires`
- C2-PR4: `test_no_backend_run_request_fires`
- C2-PR5: `test_no_backend_run_request_fires`
- C2-PR6: `test_no_backend_request_fires` ("the most safety-critical
  test in this file")
- C2-PR7: `test_edit_and_flush_never_calls_backend_preview_endpoint`,
  `buildPreviewRequest()` documented as "inert, unused-by-default
  infrastructure"

**This PR is the first, and only, intentional exception to that
invariant**, per its explicit task spec: "this is the FIRST PR in this
entire chain where a real network call is wired up — that is
intentional and required by this PR's spec." The justification:

1. C2-PR1 through PR7 deliberately built every layer of the pipeline
   (dirty tracking, scheduling/debouncing, dependency resolution,
   execution stub, payload building, and a backend contract stub) as
   independently testable, side-effect-free seams, explicitly so that
   "a future PR" could wire them together without having to also
   invent the contract at the same time. This PR is that future PR —
   its only job is to prove the seam actually connects end-to-end.
2. The call fires **at most once per flush**, never per keystroke,
   because it sits at the very end of `flushScheduledRecalc()` —
   downstream of the existing 250ms debounce (C2-PR3) that already
   collapses a burst of rapid edits into one flush.
3. The endpoint it calls (`POST /model/preview`) is itself a
   side-effect-free, auth-gated, deterministic contract stub
   (C2-PR7) — verified by that PR's own
   `TestNoFinancialEngineCall`/`TestNoPersistenceMutation` tests, which
   this PR's regression run re-confirms still pass.
4. The response can only ever flow into `FcRuntimeRenderer.render()`,
   which can only ever patch one small, non-financial status text
   element — there is no path from this fetch call to Save, Run,
   persistence, or export.

Existing C2-PR6/PR7 tests that asserted "zero requests fire" were
updated (not deleted) to assert the new, narrower, still-meaningful
invariant: exactly one `/model/preview` request fires, and zero
`/run`-shaped requests ever fire. See "Updated pre-existing tests"
below.

## Backend change — exact request/response shapes

`POST /model/preview` in `main_web.py` is extended (not duplicated)
with one additive field. The valid-payload success response gains an
`"overview"` object:

```json
{
  "ok": true,
  "status": "stubbed",
  "executed": false,
  "accepted": true,
  "affectedGroups": ["overview-kpis", "senior-debt"],
  "dirtyCells": ["capex!C.01.amount"],
  "warnings": [],
  "message": "Preview endpoint contract accepted payload; recalculation is not implemented yet.",
  "overview": {
    "runtime_status": "Preview executed",
    "updated": true
  }
}
```

`runtime_status`/`updated` are fixed, deterministic, non-financial
strings/booleans — they describe "the contract stub was reached," not
"a real recalculation occurred." No IRR, DSCR, revenue, tax, or
waterfall value is computed or referenced anywhere in the route body.

**Decision on the invalid-payload branch:** it remains exactly as
C2-PR7 left it, with **no `overview` key at all** (rather than adding
one with `updated: false`) — an invalid request never produced
anything the client could meaningfully render, so there is nothing to
describe. `FcRuntimeRenderer.render()` already treats a missing
`overview` field as a safe no-op, so this asymmetry is harmless and
intentional.

All of C2-PR7's existing validation, auth-gating, and no-side-effect
guarantees are untouched — this PR adds exactly one dict key to one
`JSONResponse` construction, nothing else, in `model_preview()`.

## Client wiring — exact integration point

`static/modelling/live-model.js`'s `flushScheduledRecalc()` gained one
additive block, after the existing C2-PR4/PR5 annotation steps and
after `recalc-flush-complete` is emitted:

```js
if (
  window.FcRecalcPreview &&
  typeof window.FcRecalcPreview.buildPreviewRequest === 'function' &&
  snapshot.execution &&
  snapshot.execution.previewPrepared &&
  snapshot.execution.previewPayload &&
  typeof fetch === 'function'
) {
  var req = window.FcRecalcPreview.buildPreviewRequest(snapshot.execution.previewPayload);
  fetch(req.url, { method: req.method, headers: req.headers, body: JSON.stringify(req.body) })
    .then(function (res) { return res.json(); })
    .then(function (json) {
      if (window.FcRuntimeRenderer) window.FcRuntimeRenderer.render(json);
    })
    .catch(function () { /* never throws, never touches the DOM */ });
}
```

This was placed in `live-model.js` (rather than inside
`recalc-preview.js` or `recalc-executor.js`) because the task's
runtime path explicitly names `flushScheduledRecalc()` as the real
end-to-end seam — the *flush* is the moment a recalculation is
genuinely due, and `live-model.js` is the only module that already
owns the full snapshot (`affectedGroups` + `execution` +
`previewPayload`) by the time this code runs. `FcRecalcPreview` itself
needed **zero** changes — `buildPreviewRequest()` continues to be the
same inert, request-shape-only helper C2-PR7 built; this PR is simply
the first caller.

- Fires **at most once per flush** (the debounce from C2-PR3 already
  guarantees this; a manual call to `flushScheduledRecalc()` would
  also fire it, by design, since a manual flush is just as real a
  flush as a debounced one).
- Never throws: the outer `if` guard means a missing/older
  `FcRecalcPreview`/no `fetch` global degrades to a silent no-op
  (e.g. an isolated test fixture that doesn't load `recalc-preview.js`
  continues to behave exactly like C2-PR5/PR6/PR7 did); the `fetch()`
  call itself is wrapped in `try`/`catch` and the promise chain has a
  `.catch()` that swallows network/parse errors without ever touching
  the DOM.
- Never calls Save, Run, or any other endpoint — the URL is always
  exactly `req.url` from `buildPreviewRequest()`, which is always
  `'/model/preview'`.

## `static/modelling/runtime-renderer.js` — the new module

`window.FcRuntimeRenderer` is a new, standalone module (same pattern
as `FcDependencyGraph`/`FcRecalcExecutor`/`FcRecalcPreview`), exposing
exactly one function: `render(responseBody)`.

- Never throws for any input, including `null`/`undefined`/a
  malformed `overview` field/an error-shaped object passed through
  from a failed fetch.
- Validates defensively: only renders when
  `body.overview.runtime_status` is a non-empty string.
- Patches exactly one element,
  `#overview-runtime-status-value`, by setting its `textContent`
  synchronously — no animation, no timing race, no randomness. Also
  sets `data-c2pr8-runtime-status="patched"` on it (it starts as
  `data-c2pr8-runtime-status="idle"`) so a test/diagnostic can confirm
  a real patch occurred versus the initial static markup.
- Returns `{ rendered: boolean, reason: string }` for callers/tests
  that want to inspect what happened — purely informational, nothing
  in this module depends on the return value being read.
- Never calls Save, Run, persistence, or export. Never reads
  `FcLiveModel` dirty state. Never makes a network call itself.

## Which Overview DOM element is patched, and why it's safe

`app/templates/partials/workspace_shell.html`'s always-rendered
`#panel-overview` tab gained a small new block, immediately after the
existing (also always-rendered) `#overview-help-pointer` note and
before `#model-output-area`:

```html
<div class="runtime-status-indicator" id="overview-runtime-status" role="status" aria-live="polite" aria-label="Live runtime preview status">
  <span class="runtime-status-indicator__label">Runtime preview:</span>
  <span class="runtime-status-indicator__value" id="overview-runtime-status-value" data-c2pr8-runtime-status="idle">Idle</span>
</div>
```

This is a **new** element, not a repurposed existing KPI/financial
value — chosen deliberately over the Dashboard v1 KPI grid
(`.dashboard-kpi-value`) or the Governance/TUHO panels for three
reasons:

1. Those existing elements are all conditionally rendered (Dashboard
   v1 behind `dashboard_enabled`, Governance/TUHO behind
   `audit_mode`, both behind a runtime snapshot existing at all) and
   hold real financial-style values (`kpi.value`, parsed from a real
   run). Patching one of those — even with a fake/placeholder string —
   would risk being mistaken for "a real KPI updated," exactly what
   the task explicitly warned against.
2. `#panel-overview` itself, and everything inside it up to
   `#model-output-area`, is unconditionally rendered for every
   project/scenario — so this new status element is always present,
   making it a safe, reliable, always-findable target for
   `FcRuntimeRenderer.render()` and for the test suite, with no
   conditional-rendering edge cases to special-case.
3. Its content is a plain runtime/status string ("Idle" ->
   "Preview executed"), never a number, never styled like a KPI
   card, and explicitly named/labelled "Runtime preview:" — it cannot
   be confused with a financial output by a user or a future
   developer reading the markup.

## Files changed

- `static/modelling/runtime-renderer.js` — new module.
- `main_web.py` — one additive `"overview"` key in `/model/preview`'s
  valid-payload success response; the invalid-payload branch and
  every other route/function are unchanged.
- `static/modelling/live-model.js` — one additive block at the end of
  `flushScheduledRecalc()` (the real `fetch` call), plus updated
  header-comment documentation of this PR's explicit exception to the
  prior "never auto-call fetch" discipline. No other function or
  behaviour in this file changed.
- `static/modelling/recalc-preview.js` — **unchanged**. This PR is the
  first caller of `buildPreviewRequest()`, but the function itself
  needed no modification.
- `app/templates/base.html` — one new `<script defer>` tag for
  `runtime-renderer.js`, inserted after `recalc-preview.js`'s tag
  (and before `recalc-executor.js`'s tag, so `window.FcRuntimeRenderer`
  is defined well before any flush's fetch response could resolve).
- `app/templates/partials/workspace_shell.html` — one new, always-
  rendered, non-financial status element in the Overview tab
  (described above).
- `tests/test_c2_pr8_first_runtime_slice_browser.py` — new test file,
  8 tests covering points 1-8 of the task spec (see below).
- `tests/test_c2_pr6_recalc_preview_browser.py` — one existing test
  (`test_no_backend_request_fires`) updated, not deleted, to reflect
  the new intentional behaviour; see "Updated pre-existing tests"
  below.
- `tests/test_c2_pr7_backend_preview_endpoint_browser.py` — one
  existing test
  (`test_edit_and_flush_never_calls_backend_preview_endpoint` ->
  renamed `test_edit_and_flush_calls_backend_preview_endpoint_exactly_once`)
  updated similarly.
- `docs/C2_PR8_FIRST_RUNTIME_SLICE.md` — this note.

## Updated pre-existing tests (intentional, not regressions)

Two tests from prior PRs asserted "zero network requests fire from a
real edit+flush sequence." Both are updated, with an inline comment
explaining why, rather than silently deleted or left broken:

- `tests/test_c2_pr6_recalc_preview_browser.py::test_no_backend_request_fires`
  now asserts zero `/run` requests and exactly one `/model/preview`
  request (previously asserted zero of either).
- `tests/test_c2_pr7_backend_preview_endpoint_browser.py::test_edit_and_flush_never_calls_backend_preview_endpoint`
  is renamed
  `test_edit_and_flush_calls_backend_preview_endpoint_exactly_once`
  and now asserts exactly one request to `/model/preview` (previously
  asserted zero).

Both updated tests still independently verify the part of the old
invariant that remains true and important: the preview path never
escalates into a real Run, and never fires more than the one expected
preview request.

## Guardrail confirmations

```
git diff --stat origin/main -- domain app/waterfall_core.py app/input_adapter.py app/project_factories.py static/app.js
```

→ empty. No change was made to any of `domain/*`,
`app/waterfall_core.py`, `app/input_adapter.py`,
`app/project_factories.py`, or `static/app.js`.

```
grep -in "waterfall|domain\.|run_project|persist|sqlite|\.db|export|save_run|record_workspace" static/modelling/runtime-renderer.js
```

→ no matches.

The `/model/preview` route's existing C2-PR7
`TestNoFinancialEngineCall`/`TestNoPersistenceMutation` tests
(`tests/test_c2_pr7_backend_preview_endpoint.py`) — which monkeypatch
`app.waterfall_core.run_project` to raise, and compare the sqlite DB
file's mtime/size before/after hitting the endpoint — all still pass
unmodified against this PR's extended route, confirming the new
`"overview"` field did not introduce any financial-engine call or
persistence write.

## Test coverage added, mapped to the 9 required points

`tests/test_c2_pr8_first_runtime_slice_browser.py`
(`TestFirstRuntimeSliceBrowser`), 8 new production-route Playwright
tests (real `uvicorn` subprocess, real auth, real project creation,
mirroring `tests/test_c2_pr7_backend_preview_endpoint_browser.py`'s
pattern):

1. **Editable change triggers the runtime pipeline** —
   `test_editable_change_triggers_runtime_pipeline`: edits a CAPEX
   cell, waits out the debounce, asserts at least one `/model/preview`
   request fired.
2. **Endpoint called exactly once per flush** —
   `test_preview_endpoint_called_exactly_once_per_flush`: asserts
   exactly one `POST` request to `/model/preview` per edit+flush.
3. **Stub response received and parsed without error** —
   `test_stub_response_received_and_parsed_without_error`: captures
   the response, asserts it parses as JSON and matches the documented
   shape (`ok`, `status`, `executed`, `overview.runtime_status`,
   `overview.updated`).
4. **Exactly one Overview status element updates** —
   `test_exactly_one_overview_status_element_updates`: asserts
   `#overview-runtime-status-value` starts as `"Idle"`, then becomes
   `"Preview executed"` (with `data-c2pr8-runtime-status="patched"`)
   after the flow completes.
5. **No Save action triggered** — `test_no_save_action_triggered`:
   monitors all requests, asserts zero contain `/scenarios/save`.
6. **No Run action triggered** — `test_no_run_action_triggered`:
   monitors all requests, asserts zero end with `/run`.
7. **No financial values change** — `test_no_financial_values_change`:
   snapshots every `.dashboard-kpi-value`/`[data-p2min3-kpi-status]`
   element's text before and after the flow, asserts byte-for-byte
   equality.
8. **Dirty state remains dirty after the runtime patch** —
   `test_dirty_state_remains_dirty_after_runtime_patch`: after the
   status element is patched, asserts `FcLiveModel.isCellDirty()` /
   `isProjectDirty()` are still `true` and the dirty banner
   (`#workspace-unsaved-banner`) is still visible (not `is-hidden`).

(Point 9, the full existing-suite regression run, is reported in the
PR description / final report, not a new test in this file.)

## Regression summary

All of C1 PR1-PR9 + sheet migrations + C1 final hardening, and C2-PR1
through PR7's own test suites, were re-run. Full results (including
two pre-existing, unrelated failure categories — the C2-PR1
`dependencygraph` string-match assertion already broken since C2-PR4,
and several stale Phase-51-era `git diff`-against-`origin/main`/`HEAD`
characterization tests that fail for *any* uncommitted local diff
touching `static/`/templates, confirmed via `git stash` to fail
identically on the unmodified branch tip) are reported in the PR
description / final report's results table.

## What the next PR should build on top of this

(Informational only — not implemented here.)

1. **Real preview computation.** `model_preview()` in `main_web.py`
   still returns a fixed stub `"overview"` object regardless of input
   — a future PR would replace this with an actual (read-only,
   non-mutating) recomputation of whichever KPI(s) the new endpoint is
   trusted to preview, scoped by `affectedGroups`.
2. **Richer renderer output.** `FcRuntimeRenderer.render()` currently
   only ever touches one status string. A future PR introducing real
   preview values would need to decide which (if any) additional DOM
   elements become safe to patch from a preview response, and would
   likely want a more structured `overview` response shape (e.g. per-
   group deltas) rather than this PR's single fixed string.
3. **In-flight request handling.** This PR does not guard against
   overlapping `/model/preview` requests if a user keeps editing while
   a previous preview's fetch is still pending (each flush fires its
   own independent fetch+render; a slow response landing after a
   newer one could, in principle, render stale data over fresh data).
   Out of scope here, but worth flagging exactly as C2-PR6's note
   already did for this exact concern.
4. **Error/loading states.** `FcRuntimeRenderer` currently has no
   "pending" or "error" rendering state — a failed fetch silently
   leaves the previous status text in place. A future PR might want a
   visible "checking..." or "preview failed" state for real user
   feedback, once there's a real computation worth showing progress
   for.
