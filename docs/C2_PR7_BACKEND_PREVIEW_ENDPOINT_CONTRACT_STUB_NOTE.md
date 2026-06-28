# C2-PR7: Backend Preview Endpoint Contract Stub — Implementation Note

## Scope

This PR adds the **first server-side seam** for a future
incremental-recalculation preview call. In this PR it remains a
deterministic **no-op contract stub**: it accepts the C2-PR6
client-side preview-payload shape, validates it defensively, and
returns a fixed-shape acknowledgement response. It implements
**infrastructure only**:

1. A new backend route, `POST /model/preview`, in `main_web.py`.
2. A new, explicit, never-auto-called client-side helper,
   `FcRecalcPreview.buildPreviewRequest(payload)`, plus
   `FcRecalcPreview.previewEndpoint` metadata, in
   `static/modelling/recalc-preview.js`.
3. Backend route tests
   (`tests/test_c2_pr7_backend_preview_endpoint.py`) and browser
   safety tests
   (`tests/test_c2_pr7_backend_preview_endpoint_browser.py`).

It does **not** implement, call, or scaffold: real recalculation,
formula evaluation, model engine invocation, any automatic client
fetch, live KPI updates, Save/Run changes, persistence writes, or
export changes.

## Route choice and reasoning

Chosen path: **`POST /model/preview`**.

Rationale, after reading every existing route in `main_web.py`:

- The app already groups model-input-affecting actions under
  top-level verbs with no resource prefix: `/validate`, `/run`,
  `/compare`, `/save-run`. None of these are namespaced under
  `/model/...` today, but `/run` (the real calculation entrypoint)
  is the closest behavioural sibling to a future "preview the effect
  of a recalculation" call — this stub is deliberately *not* that
  endpoint, so reusing the bare `/run`-style top-level verb would
  blur the distinction the whole C2 effort is built around (preview
  vs. execute). `/model/preview` keeps the verb-first convention
  (`preview`, like `run`/`compare`/`validate`) while the `/model`
  prefix signals "this concerns the live in-browser model state, not
  a full project Run" — distinguishing it from `/run`, `/save-run`,
  and `/runs`.
- `/recalc/preview` was considered and rejected only because no
  existing route uses a `/recalc` prefix anywhere in this codebase,
  whereas the client-side modules already establish "model" as the
  shared vocabulary (`FcLiveModel`, `static/modelling/`). `/model/
  preview` reads naturally as "preview the live model's pending
  changes" and matches the existing `static/modelling/` directory
  name.
- The route is added in `main_web.py` directly (not a new
  `app/services/*_service.py` file) because, unlike `/run`/
  `/validate`/`/scenarios/.../update-overrides`, this stub has no
  orchestration logic to extract — it is two small pure functions
  (`_c2_pr7_validate_preview_payload`,
  `_c2_pr7_sorted_unique_strings`) plus a thin route body. Extracting
  a service module for a stub with zero side effects would be
  premature structure for logic that a future PR will likely rewrite
  entirely once real recalculation is implemented.

## Auth

The route requires the existing session-cookie auth, mirroring
`/health`'s JSON-style pattern (not the HTML-redirect pattern used by
form-rendering routes like `/run`/`/validate`): unauthenticated
requests get `401` with
`{"status": "unauthenticated", "detail": "Login required"}`, exactly
like `GET /health`. This was chosen over the `RedirectResponse` to
`/login` pattern (used by `/run`, `/validate`, etc.) because this is a
JSON API consumed by client-side JS, not a form submission expected to
produce an HTML navigation — a redirect response would be the wrong
contract for a `fetch`-style caller. No new auth mechanism was
invented; `get_current_user(request)` is the same dependency every
other protected route in `main_web.py` uses.

## Request schema

JSON body, matching `FcRecalcPreview.buildPreviewPayload()`'s output
shape (`static/modelling/recalc-preview.js`):

```json
{
  "valid": true,
  "dirtyCells": ["capex!C.01.amount"],
  "affectedGroups": ["overview-kpis", "senior-debt"],
  "projectDirty": true,
  "reason": "manual-flush",
  "executionStatus": "stubbed",
  "project": "demo-project"
}
```

All fields are validated defensively (`_c2_pr7_validate_preview_payload`
in `main_web.py`):

- `valid`: must be a boolean.
- `dirtyCells`: must be an array of strings.
- `affectedGroups`: must be an array of strings.
- `projectDirty`: must be a boolean.
- `reason`: must be a string.
- `executionStatus`: must be a string or `null`.
- `project`: must be a string or `null`.

Any deviation (wrong type, missing field, non-object body, malformed
JSON, empty body) is treated as invalid — never raises, never returns
a 500.

## Response schema

**Valid payload** → `200` with:

```json
{
  "ok": true,
  "status": "stubbed",
  "executed": false,
  "accepted": true,
  "affectedGroups": ["overview-kpis", "senior-debt"],
  "dirtyCells": ["capex!C.01.amount"],
  "warnings": [],
  "message": "Preview endpoint contract accepted payload; recalculation is not implemented yet."
}
```

`affectedGroups`/`dirtyCells` are echoed back deduplicated and sorted
— never inventing entries not present in the request.

**Invalid payload** → `200` (deliberately not `400`/`422`/`500` — the
contract is "always answer safely", matching the spec's example
response) with:

```json
{
  "ok": false,
  "status": "invalid-payload",
  "executed": false,
  "accepted": false,
  "warnings": ["'dirtyCells' must be an array of strings", "..."]
}
```

`warnings` lists every validation problem found, for future caller
diagnostics; never throws, never 500s.

## No-side-effect guarantees and verification

The route body (`model_preview` in `main_web.py`) contains exactly:
auth check, `await request.json()` (wrapped in `try`/`except`),
defensive shape validation, sorting/deduplication of two string
arrays, and a `JSONResponse` construction. It does not import or call:

- `app/waterfall_core.py` or any `domain/*` module (no financial
  engine call).
- Any persistence/database write function (`app/persistence/*`,
  `app/scenario_manager.py`, `update_scenario_overrides`,
  `record_workspace_runtime`, etc.).
- `run_project`/`build_projectinputs` or any other Run-path function.
- Any export-generation function (`app/excel_export.py`,
  `app/export/*`, etc.).

Verification performed:

1. **Code inspection**: grepped the new route's code block for
   `waterfall|domain\.|run_project|persist|sqlite|\.db|export|
   save_run|record_workspace` — no matches outside docstring/comment
   text.
2. **Guardrail diff**: `git diff --stat main -- domain
   app/waterfall_core.py app/input_adapter.py
   app/project_factories.py` is empty — confirms zero changes to any
   guarded financial file.
3. **Test-level verification** (`tests/test_c2_pr7_backend_preview_endpoint.py`):
   - `TestNoFinancialEngineCall`: monkeypatches
     `app.waterfall_core.run_project` to raise on call; the route
     still returns `ok: true` (i.e. never touched it), and the
     response body contains no computed-financial-output keys
     (`kpis`/`irr`/`dscr`/`npv`/`cashflow`/`run_id`).
   - `TestNoPersistenceMutation` / `TestNoSideEffectsAcrossRepeatedCalls`:
     compares the sqlite DB file's `mtime`/`size` before and after
     hitting the endpoint (once, and 10x in a row) — unchanged.
   - `TestDeterminism`: same valid input produces structurally
     identical JSON across 5 repeated calls.
   - `TestDistinctFromRunEndpoint`: response is flat JSON with
     `executed: False` and no HTML markup, unlike `/run`'s rendered
     template response.

## Why no recalculation occurs yet

This PR is explicitly scoped as a **contract stub**: its only job is
to give a future PR a stable, already-tested request/response shape
and a real (auth-gated, validated, side-effect-free) network seam to
call, without that future PR having to simultaneously invent the
payload contract, the validation logic, and the test harness. Real
incremental recalculation requires wiring into the dependency graph
(`FcDependencyGraph`, C2-PR4) and an actual execution engine call,
which is deliberately out of scope here — C2-PR5/PR6 established the
client-side stubs for exactly the same reason.

## Client integration (still no automatic fetch)

`static/modelling/recalc-preview.js` gained:

- `FcRecalcPreview.previewEndpoint` — the string `'/model/preview'`,
  metadata only.
- `FcRecalcPreview.buildPreviewRequest(payload)` — returns
  `{url: '/model/preview', method: 'POST', headers: {...}, body: payload}`,
  a plain-data object describing what a future caller *would* send.
  It performs no `fetch`/`XMLHttpRequest`/`htmx.ajax`/`htmx.trigger`
  call — confirmed by grepping every touched JS file for those
  strings (none found outside this note's own prose-comments
  explaining the invariant).

This helper is **not** called by `FcRecalcExecutor.execute()`,
`FcLiveModel.flushScheduledRecalc()`, or anywhere else in the
scheduler/executor/preview chain — it exists purely as inert,
unused-by-default infrastructure. Verified via:

- Code review of every call site of `FcRecalcPreview.*` in
  `static/modelling/recalc-executor.js` — only `buildPreviewPayload`
  is called; `buildPreviewRequest` is not referenced anywhere outside
  its own test files.
- `tests/test_c2_pr7_backend_preview_endpoint_browser.py`'s
  `test_edit_and_flush_never_calls_backend_preview_endpoint`: a real
  edit + flush + preview-build sequence, monitored via
  `page.on("request", ...)`, fires zero requests containing
  `/model/preview` or `preview`.
- `test_build_preview_request_returns_shape_without_sending`: calling
  `buildPreviewRequest()` directly returns the expected shape and
  produces zero network requests.

## What a future PR must do to turn this into real preview execution

(Informational only — none of this is implemented here.)

1. Replace the stub body of `model_preview()` in `main_web.py` with a
   call into a real (read-only) preview/what-if execution path —
   likely reusing `FcDependencyGraph`'s server-side equivalent and a
   non-mutating variant of the calculation engine that computes
   affected KPI deltas without writing to persistence.
2. Decide on, and add, the actual response fields a real preview
   would need (e.g. projected KPI deltas per affected group) — this
   PR's response shape only echoes back what was sent, by design.
3. Wire `FcRecalcExecutor.execute()` (or a new caller) to actually
   invoke `FcRecalcPreview.buildPreviewRequest()` and perform the
   `fetch` — at that point, and only then, should a network call be
   introduced; this PR and all of C2-PR5/PR6 deliberately do not.
4. Add appropriate rate-limiting/debouncing if previews become
   frequent (e.g. on every keystroke) — out of scope until a real
   backend computation exists to protect.
