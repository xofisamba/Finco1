# C2-PR10 — CAPEX Total Preview

## Summary

This PR adds the first **real, non-stub** numeric computation anywhere in
the C1/C2 incremental-runtime chain: a CAPEX total preview. When a user
edits an editable CAPEX grid cell, the existing debounced
dirty-tracking → scheduler → dependency-graph → executor → preview-payload
→ `POST /model/preview` → runtime-renderer pipeline (built across C2-PR1
through C2-PR9) now additionally carries and renders a deterministic sum
of the **current, unsaved, in-browser** CAPEX grid editable amount cells.

This is explicitly **not** a financial-engine run. It is a plain
line-item sum, computed the same way a user could verify by hand, and it
never touches `domain/*`, `app/waterfall_core.py`, `app/input_adapter.py`,
`app/project_factories.py`, or any persistence/export code path.

## Design choice: client-side summation, server-side echo

Two options were considered, per the task brief:

1. **Server-side summation** — send edited cell values to the server and
   have `main_web.py` sum them.
2. **Client-side summation** — sum the values in the browser (where they
   already live, unsaved, in the DOM) and send the already-computed total
   to the server, which simply validates and echoes it back in the
   response.

**Client-side summation (option 2) was chosen.** Rationale:

- It fits the existing `FcRecalcPreview.buildPreviewPayload()` pattern
  exactly: that function already reads dirty-cell state and DOM values
  via `FcGridRegistry`/`FcCellIO` to build the preview payload sent to
  the server (see C2-PR6/PR7). Adding the CAPEX sum as one more
  additive field on that same payload required no new client/server
  data-shape, no new request, and no duplicate "what counts as an
  editable amount cell" logic on the server.
- The editability/kind rules for CAPEX cells (`data-fc-editable`,
  `data-fc-kind="amount"`) are markup-level concepts that the client
  already fully owns via `FcGridRegistry`/`FcCellIO`. Re-deriving them
  server-side (e.g. by re-parsing template/DB state) would duplicate
  logic and risk drifting from the client's notion of "editable," which
  is precisely what this PR must read from (unsaved, in-browser state).
- The server route does not read the DB CAPEX values for this feature at
  all — it has no way to know about unsaved edits unless they are sent
  to it. Summing server-side would have required sending the whole edited
  CAPEX grid as a list of values anyway, which is strictly more payload
  and more server logic than sending one pre-computed number.

The server's role is therefore intentionally minimal: validate that
`capexTotalPreview` (if present) is a finite number or `null`, and echo
it back, rounded to 2 decimals, under a new `capex` response field. This
keeps the server itself free of any new "business logic," consistent
with every prior PR in this chain (PR6/PR7/PR8/PR9 all kept `main_web.py`
a thin, deterministic, validating pass-through).

## New payload / response shape

### Request (`POST /model/preview` body), additive field

```json
{
  "valid": true,
  "dirtyCells": ["capex!C.01.01.amount"],
  "affectedGroups": ["capex", "senior-debt", "overview-kpis"],
  "projectDirty": true,
  "reason": "...",
  "executionStatus": "...",
  "project": "<project-code>",
  "capexTotalPreview": 12345.67
}
```

`capexTotalPreview` is `null` when no dirty CAPEX cell is present in the
current dirty-cell set (i.e. the edit didn't touch the CAPEX grid), or
when the client could not compute a sum (e.g. `FcGridRegistry`/`FcCellIO`
unavailable, no CAPEX grid mounted, or no editable amount cells found).
It is computed in `static/modelling/recalc-preview.js`'s new
`_computeCapexTotalFromDom()`, which walks `FcGridRegistry.getGrid('capex')`
rows, sums every cell where `cell.editable === true` and
`cell.kind === 'amount'`, reading each value via `FcCellIO.readValue(cell)`
(the same C1 API used everywhere else for reading live cell state), and
rounds the result to 2 decimal places.

### Response, additive field

```json
{
  "ok": true,
  "...": "... existing PR6-PR9 fields unchanged ...",
  "overview": { "runtime_status": "Preview executed", "updated": true },
  "capex": { "capex_total_preview": 12345.67, "currency": "EUR" }
}
```

The `capex` field is present only when the request's
`capexTotalPreview` was a non-null finite number; it is omitted entirely
otherwise (not present, not present-as-null) so the renderer's
shape-check (`_hasRenderableCapexPreview`) cleanly distinguishes "no
preview to show" from "show this exact computed value." `currency` is
currently a fixed `"EUR"` literal — this is the project's only supported
display currency at the time of writing and is not re-derived or
formula-computed; it is metadata only, never used in the sum itself.

## Rendering: new, distinct, clearly-labeled preview element

`app/templates/partials/workspace_shell.html` gets one new always-rendered
element, placed next to (never replacing) the existing C2-PR8 runtime
status indicator inside the Overview tab:

```html
<div class="runtime-status-indicator capex-total-preview-indicator"
     id="capex-total-preview" role="status" aria-live="polite"
     aria-label="Unsaved CAPEX total preview, not the saved total">
  <span class="runtime-status-indicator__label">CAPEX total preview (unsaved):</span>
  <span class="runtime-status-indicator__value" id="capex-total-preview-value"
        data-c2pr10-capex-preview="idle">&mdash;</span>
</div>
```

New user-visible text introduced by this PR: the label **"CAPEX total
preview (unsaved):"** and the initial placeholder value **"—"** (em
dash), later replaced with a formatted number + currency (e.g.
`"12,345.67 EUR"`) once a preview response arrives.

This wording was chosen deliberately to be honest and unambiguous: it
says "preview" and "(unsaved)" so it can never be mistaken for the
persisted/saved CAPEX total shown elsewhere on the CAPEX sheet, and it
introduces no internal jargon (no "G20", "R99", "R102",
"MISSING_EVIDENCE," or similar codes) anywhere in the rendered UI.

`static/modelling/runtime-renderer.js`'s `render()` function now patches
this element (`#capex-total-preview-value`) **independently** of the
existing `#overview-runtime-status-value` patch — a missing/malformed
`overview` field never blocks rendering a present, valid `capex` field,
and vice versa. Each patch sets its own `data-c2pr8-runtime-status` /
`data-c2pr10-capex-preview` attribute to `"patched"` so tests (and any
future debugging) can confirm exactly which part of a given response
was rendered.

No existing saved/Run-derived KPI element is relabelled, removed, or
silently overwritten by this change — confirmed by the new browser test
`test_overview_kpis_byte_identical_pre_and_post_capex_preview`, which
asserts every `.dashboard-kpi-value`/`[data-p2min3-kpi-status]` element's
text is byte-identical before and after a CAPEX preview round trip.

## No real financial engine use

This PR's only "calculation" is a plain summation of numbers already
present, unsaved, in the browser DOM (`_computeCapexTotalFromDom()`),
followed by a server-side round-and-echo. Confirmed:

- No import of, or call into, `domain/*`, `app/waterfall_core.py`,
  `app/input_adapter.py`, or `app/project_factories.py` was added.
  `git diff --stat origin/main -- domain app/waterfall_core.py
  app/input_adapter.py app/project_factories.py` is empty.
- No DB write, persistence call, or export-path code was touched.
- `main_web.py`'s `/model/preview` route change is limited to validating
  one new optional numeric field and adding one new optional response
  field; it does not query the database for CAPEX rows or call any
  scenario/run/save code path.

## P1 fast-follow issue (dirty-strip badge lag after Save)

The pre-existing, previously logged minor issue — `#workspace-strip-dirty`
remaining at "Unsaved edits" for a few seconds after Save because Save's
HTMX response doesn't trigger the same `applyWorkspaceStateMeta()` path
Run's response does — was **left as a fast-follow and NOT fixed in this
PR**. Confirmed via `git diff --stat origin/main -- static/app.js`,
which is empty: `static/app.js` was read for context but not modified.
This keeps the PR narrow and focused solely on the CAPEX total preview
feature, per the task's explicit instruction not to let this fix expand
the PR's scope.

## Tests added

- `tests/test_c2_pr10_capex_total_preview.py` — 13 backend tests against
  the real `/model/preview` route via `fastapi.testclient.TestClient`:
  payload acceptance/validation of `capexTotalPreview`, response shape
  of the new `capex` field, omitted/null handling, rejection of
  malformed values (`NaN`, `Infinity`, strings, booleans), no
  financial-engine/persistence side effects, and authorization
  regression (owned/null/cross-user/bogus-project) unaffected.
- `tests/test_c2_pr10_capex_total_preview_browser.py` — 7 Playwright
  browser tests against a real uvicorn subprocess + real auth + real
  project, covering required-behaviour points 1, 2, 3, 4, 5, 6, and 9
  from the task spec (editable-cell update, read-only no-op, one-edit/
  one-request, multi-edit/no-Save-no-Run, byte-identical Overview KPIs,
  dirty state persists through preview, and C1 grid behaviour intact on
  the CAPEX grid).

All 20 new tests pass. See the PR description / final report for the
full regression run results.
