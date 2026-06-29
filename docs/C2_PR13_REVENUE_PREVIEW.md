# C2-PR13 — Revenue Total Preview

## Summary

This PR adds the **second** real, non-stub numeric computation in the
C1/C2 incremental-runtime chain (after C2-PR10's CAPEX total preview):
a Revenue total preview. It follows the exact same architecture as
PR10 — client-side summation of currently-editable, possibly-unsaved
Revenue grid cell values, sent to the server, validated, and echoed
back — with no new request, no new route, and no financial-engine
call of any kind.

## Calculation approach

`static/modelling/recalc-preview.js`'s new `_computeRevenueTotalFromDom()`
mirrors `_computeCapexTotalFromDom()` (PR10) field-for-field:

- Reads the `"revenue"` grid via `window.FcGridRegistry.getGrid('revenue')`.
- Walks every row's cells, including only cells where `cell.editable === true`.
- **One necessary difference from CAPEX**: Revenue editable cells are
  marked `data-fc-kind="text"` in
  `app/templates/partials/sheet_revenue.html` (not `"amount"` — that's
  CAPEX's own markup convention), so the selection predicate matches
  `cell.kind === 'text'` instead of `cell.kind === 'amount'`. This is
  the only difference between the two summation functions; the
  selection RULE itself ("editable, plain line-item cells only — never
  derived subtotal/total rows") is identical.
- Reads each matched cell's live value via `window.FcCellIO.readValue(cell)`
  (the same C1 read API CAPEX uses), parses it with `parseFloat`,
  skips any cell that doesn't parse to a number, and sums the rest.
- Rounds the result to 2 decimal places (presentation rounding only).

**Null-handling rationale (matches CAPEX exactly):** the function
returns `null` — never `0`, never a fabricated number — when:

- `window.FcGridRegistry`/`window.FcCellIO` are unavailable (e.g. a
  non-browser test harness or an older page that hasn't loaded C1's
  interaction layer), or
- the `"revenue"` grid is not currently registered/rendered (e.g. a
  different tab is active, or a protected/baseline project renders no
  editable revenue cells at all), or
- every candidate cell fails to parse as a number (`counted === 0`).

"No total available" must never be silently rendered as a real zero
total — this is the same invariant PR10 established and this PR
deliberately preserves, never weakens.

In `buildPreviewPayload()`, `revenueTotalPreview` is only recomputed
when the current flush's dirty-cell set actually contains at least one
`"revenue!..."` address (mirroring `capexTotalPreview`'s `"capex!..."`
scoping exactly) — an unrelated edit (e.g. a CAPEX-only flush) leaves
`revenueTotalPreview: null` rather than needlessly recomputing a sum
nothing changed.

## Payload / response shape

### Request (`POST /model/preview` body), additive field

```json
{
  "valid": true,
  "dirtyCells": ["revenue!ppa_tariff_eur_mwh"],
  "affectedGroups": ["overview-kpis"],
  "projectDirty": true,
  "reason": "...",
  "executionStatus": "...",
  "project": "<project-code>",
  "capexTotalPreview": null,
  "revenueTotalPreview": 12345.67
}
```

`revenueTotalPreview` coexists with the pre-existing `capexTotalPreview`
field — both are independently null or numeric depending on which
grid(s) the current flush's dirty set touched. Sending both in the
same request (e.g. if a user edited both grids before the debounce
settled) is fully supported; the server validates and echoes each
independently.

### Response, additive field

```json
{
  "ok": true,
  "...": "... existing PR6-PR12 fields unchanged ...",
  "overview": { "runtime_status": "Preview executed", "updated": true },
  "capex": { "capex_total_preview": 111.11, "currency": "EUR" },
  "revenue": { "preview": 12345.67, "currency": "EUR" }
}
```

The `revenue` field — shaped `{"preview": <number>, "currency": "EUR"}`
per the task's exact contract — is present only when the request's
`revenueTotalPreview` was a non-null finite number; it is omitted
entirely otherwise (never present-as-null, never fabricated as `0.0`).
`currency` is the same fixed `"EUR"` literal already used for `capex`
— metadata only, never computed.

`main_web.py`'s `_c2_pr7_validate_preview_payload()` gained one new
validation branch, mirroring the existing `capexTotalPreview` branch
exactly: `revenueTotalPreview`, if present, must be `null` or a finite
real number (no NaN, no Infinity, no string, no boolean) — a malformed
value yields the existing `{"ok": false, "status": "invalid-payload"}`
safe response, never a 500. `model_preview()` gained one new response
branch, mirroring the existing `capex` response branch exactly: if
`revenueTotalPreview` is present and not `None`, the route rounds it to
2dp and adds the `revenue` field; otherwise it's omitted entirely. No
new route was added — `/model/preview` is the only route touched.

## Rendering: new, distinct, clearly-labeled preview element

`app/templates/partials/workspace_shell.html` gets one new
always-rendered element, placed next to the existing C2-PR8 runtime
status indicator and C2-PR10 CAPEX preview indicator (same Overview
tab location as both):

```html
<div class="runtime-status-indicator revenue-total-preview-indicator"
     id="revenue-total-preview" role="status" aria-live="polite"
     aria-label="Unsaved Revenue total preview, not the saved total" aria-busy="false">
  <span class="runtime-status-indicator__label">Revenue total preview (unsaved):</span>
  <span class="runtime-status-indicator__value badge badge-preview-only"
        id="revenue-total-preview-value"
        data-c2pr13-revenue-preview="idle" data-c2pr11-runtime-state="idle">&mdash;</span>
  <span class="sr-only" id="revenue-total-preview-sr">Revenue preview status: Idle</span>
</div>
```

**Exact new user-visible wording introduced by this PR:** the label
**"Revenue total preview (unsaved):"** and the initial placeholder
value **"—"** (em dash), later replaced with a formatted number +
currency, e.g. **"12,345.67 EUR"** (the same `_formatTotalPreview()`
helper used for CAPEX — renamed from `_formatCapexTotal` since it is
no longer CAPEX-specific; its formatting behaviour is byte-identical:
fixed 2-decimal, thousands-separated, `toLocaleString('en-US', ...)`
with a `toFixed(2)` fallback). This wording mirrors CAPEX's own
"(unsaved)"/"preview" phrasing deliberately, so it can never be
mistaken for the saved/persisted "Est. Total Y1 Revenue" figure shown
on the Revenue sheet itself (which is always SAVED, runtime-authoritative
data).

The element reuses the existing `badge`/`badge-preview-only` CSS
classes verbatim — no new CSS rule was added anywhere in this PR.

## Integration with the existing PR9/PR11 machinery — fully reused, not duplicated

`static/modelling/live-model.js` was **not modified at all** by this
PR. `flushScheduledRecalc()` already calls `FcRuntimeRenderer.render(json)`
with the entire parsed response body, and already calls
`setUpdating()`/`setUnavailable()`/`setFailed()` generically — none of
that code is CAPEX-specific, so the existing abort/sequence-token
guard (PR9) and the existing 5-state machine triggers (PR11) apply to
the Revenue preview automatically, with zero new wiring:

- **PR9 sequencing**: the same `seq === _previewLatestSeq` check that
  already gates whether *any* response reaches `render()`/`setFailed()`
  gates the Revenue preview's rendering too — there is only one
  request in flight per flush, carrying both previews' data together,
  so "stale response discarded" already means "stale for both
  previews at once." A newer settled edit's response always wins over
  an older one for both CAPEX and Revenue simultaneously.
- **PR11 state machine**: `runtime-renderer.js`'s `setUpdating()`,
  `setUnavailable()`, and `setFailed()` each now call a third
  bookkeeping helper, `_setRevenueState(state)` (added alongside the
  pre-existing `_setOverviewState`/`_setCapexState`), in lockstep with
  the Overview and CAPEX transitions — so all three regions always
  transition together, on the same flush/response. Exactly like
  `_setCapexState`, `_setRevenueState` **never** writes to
  `#revenue-total-preview-value`'s `textContent` — only `render()`'s
  own success-edge value-patching code does that, preserving PR11's
  critical "never blank a valid value on failure" invariant for the
  Revenue preview too.
- `render(body)` gained a third, fully independent patch block (after
  the existing overview and capex blocks): a missing/malformed
  `"revenue"` field never blocks the overview/capex patches, and vice
  versa — exactly the same "rendered/skipped on its own merits"
  independence PR10 established between overview and capex.

## No real financial engine use

This PR's only "calculation" is a plain summation of numbers already
present, unsaved, in the browser DOM (`_computeRevenueTotalFromDom()`),
followed by a server-side round-and-echo — identical in kind to PR10's
CAPEX sum. Confirmed:

- No import of, or call into, `domain/*`, `app/waterfall_core.py`,
  `app/input_adapter.py`, or `app/project_factories.py` was added.
  `git diff --stat origin/main -- domain app/waterfall_core.py
  app/input_adapter.py app/project_factories.py` is empty.
- No DB write, persistence call, or export-path code was touched
  (confirmed by `test_no_persistence_mutation` and
  `test_no_financial_engine_call` in
  `tests/test_c2_pr13_revenue_preview.py`).
- `main_web.py`'s `/model/preview` route change is limited to
  validating one new optional numeric field and adding one new
  optional response field — the same minimal shape as PR10's `capex`
  change. No new route was added.
- `static/app.js` was not touched at all by this PR (it was already
  fixed, narrowly, in C2-PR12, and this PR does not touch it again).

## CAPEX preview / PR9 / PR11 unaffected — confirmed by regression tests

- `tests/test_c2_pr13_revenue_preview_browser.py::test_existing_capex_preview_still_works_unaffected`
  re-runs PR10's own CAPEX-edit-updates-preview assertion end to end,
  confirming the CAPEX preview still works exactly as before with the
  Revenue preview code present.
- `tests/test_c2_pr13_revenue_preview_browser.py::test_save_does_not_erase_revenue_or_capex_preview`
  edits both grids, clicks the real Save button, and asserts neither
  preview's displayed value changes — extending PR12's "Save doesn't
  erase dirty state" guarantee to both preview values.
- `tests/test_c2_pr13_revenue_preview_browser.py::test_sequencing_holds_for_revenue_preview`
  reuses PR9's own delayed-response race-engineering pattern
  (`_install_ordered_delayed_responses`) against the Revenue preview
  element specifically, confirming only the newest response's value is
  ever rendered.
- `tests/test_c2_pr13_revenue_preview.py::TestCapexPreviewRegressionUnaffected`
  confirms both `capex` and `revenue` response fields can be present
  together, or either one alone, without the other being affected.

## Tests added

- `tests/test_c2_pr13_revenue_preview.py` — 16 backend tests against
  the real `/model/preview` route via `fastapi.testclient.TestClient`:
  payload acceptance/validation of `revenueTotalPreview`, response
  shape of the new `revenue` field, omitted/null handling, rejection of
  malformed values, no financial-engine/persistence side effects,
  authorization regression, and CAPEX/Revenue coexistence.
- `tests/test_c2_pr13_revenue_preview_browser.py` — 8 Playwright
  browser tests against a real uvicorn subprocess + real auth + real
  project, covering all of required-behaviour points 1, 2, 3, 4, 5, 7,
  8, 9, and 10 from the task spec.

All 24 new tests pass.
