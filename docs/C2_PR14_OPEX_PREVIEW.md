# C2-PR14 — OPEX Total Preview

## Summary

This PR adds the **third** real, non-stub numeric computation in the
C1/C2 incremental-runtime chain (after C2-PR10's CAPEX total preview
and C2-PR13's Revenue total preview): an OPEX total preview. It follows
the exact same architecture as PR10/PR13 — client-side summation of
currently-editable, possibly-unsaved OPEX grid cell values, sent to the
server, validated, and echoed back — with no new request, no new
route, and no financial-engine call of any kind.

## OPEX grid editability: out of scope, intentionally untouched

Unlike CAPEX (`sheet_capex.html`) and Revenue (`sheet_revenue.html`),
the production OPEX grid wired to the C1 interaction layer
(`app/templates/partials/sheet_opex_detail.html`, `data-fc-grid="opex"`)
has **zero** `data-fc-editable="true"` cells — every cell's
`data-fc-editable` is hard-coded `"false"`, with line editing
explicitly deferred (see the template's own pre-existing
`title="Line editing deferred"` comment), a boundary dating back to
Phase 21/24. Making OPEX cells editable is C1 grid-editability work,
not preview-pipeline work, and is **out of scope for this PR** — this
PR adds only the preview computation/transport/render plumbing,
exactly mirroring PR10/PR13, and deliberately makes **no** change to
`sheet_opex_detail.html` or any other cell's editability.

A direct consequence: `_computeOpexTotalFromDom()` (below) will
currently always find zero editable OPEX cells and correctly return
`null`. This is the correct, intended "never fabricate a value"
behaviour given the current state of the grid — not a bug, and not
something this PR works around. Once a future, dedicated C1 PR adds
real OPEX line-item editability, this preview will start producing
non-null values with no further changes required here.

## Calculation approach

`static/modelling/recalc-preview.js`'s new `_computeOpexTotalFromDom()`
mirrors `_computeCapexTotalFromDom()` (PR10) field-for-field:

- Reads the `"opex"` grid via `window.FcGridRegistry.getGrid('opex')`.
- Walks every row's cells, including only cells where
  `cell.editable === true` **and** `cell.kind === 'amount'` — the same
  convention CAPEX uses (OPEX's editable Budget cells, like CAPEX's
  amount cells, are marked `data-fc-kind="amount"`, NOT Revenue's
  `"text"`).
- Reads each matched cell's live value via `window.FcCellIO.readValue(cell)`,
  parses it with `parseFloat`, skips any cell that doesn't parse to a
  number, and sums the rest.
- Rounds the result to 2 decimal places (presentation rounding only).

**Null-handling rationale (matches CAPEX/Revenue exactly):** returns
`null` — never `0`, never a fabricated number — when
`FcGridRegistry`/`FcCellIO` are unavailable, the `"opex"` grid is not
currently registered/rendered, or no editable amount cell parses as a
number.

In `buildPreviewPayload()`, `opexTotalPreview` is only recomputed when
the current flush's dirty-cell set actually contains at least one
`"opex!..."` address — mirroring `capexTotalPreview`'s/
`revenueTotalPreview`'s scoping exactly.

## Payload / response shape

### Request (`POST /model/preview` body), additive field

```json
{
  "valid": true,
  "dirtyCells": ["opex!OM-01.budget"],
  "affectedGroups": ["overview-kpis"],
  "projectDirty": true,
  "reason": "...",
  "executionStatus": "...",
  "project": "<project-code>",
  "capexTotalPreview": null,
  "revenueTotalPreview": null,
  "opexTotalPreview": 8456.0
}
```

### Response, additive field

```json
{
  "ok": true,
  "...": "... existing fields unchanged ...",
  "opex": { "preview": 8456.0, "currency": "EUR" }
}
```

The `opex` field — shaped `{"preview": <number>, "currency": "EUR"}`,
exactly the same shape as `revenue` (not `capex`'s legacy
`capex_total_preview` key, which predates this naming convention) — is
present only when the request's `opexTotalPreview` was a non-null
finite number; omitted entirely otherwise.

`main_web.py`'s `_c2_pr7_validate_preview_payload()` gained one new
validation branch (`opexTotalPreview`, mirroring `capexTotalPreview`/
`revenueTotalPreview` exactly) and `model_preview()` gained one new
response branch (the `opex` field), both following the established
pattern byte-for-byte. No new route was added.

## Rendering: new, distinct, clearly-labeled preview element

`app/templates/partials/workspace_shell.html` gets one new
always-rendered element, placed next to the existing CAPEX/Revenue/
Overview indicators:

```html
<div class="runtime-status-indicator opex-total-preview-indicator"
     id="opex-total-preview" role="status" aria-live="polite"
     aria-label="Unsaved OPEX total preview, not the saved total" aria-busy="false">
  <span class="runtime-status-indicator__label">OPEX total preview (unsaved):</span>
  <span class="runtime-status-indicator__value badge badge-preview-only"
        id="opex-total-preview-value"
        data-c2pr14-opex-preview="idle" data-c2pr11-runtime-state="idle">&mdash;</span>
  <span class="sr-only" id="opex-total-preview-sr">OPEX preview status: Idle</span>
</div>
```

**Exact new user-visible wording:** the label **"OPEX total preview
(unsaved):"**, initial placeholder **"—"**, formatted value e.g.
**"8,456.00 EUR"** (the same `_formatTotalPreview()` helper reused
verbatim). The element reuses the existing `badge`/`badge-preview-only`
classes — no new CSS rule added.

## Integration with the existing PR9/PR11 machinery — fully reused

`static/modelling/live-model.js` was **not modified** by this PR — the
generic flush/fetch/render path already handles any additive payload
field/response field with zero new wiring, exactly as PR13 already
demonstrated for Revenue. `runtime-renderer.js`'s `setUpdating()`/
`setUnavailable()`/`setFailed()` each gained one more call
(`_setOpexState(...)`), in lockstep with Overview/CAPEX/Revenue;
`render()` gained one more independent patch block. PR9's sequencing
and PR11's "never blank a valid value on failure" invariant apply
automatically and identically.

## No real financial engine use

Confirmed: no import of, or call into, `domain/*`,
`app/waterfall_core.py`, `app/input_adapter.py`, or
`app/project_factories.py`; no DB write, persistence call, or export
path touched; `main_web.py`'s route change is limited to validating one
new optional numeric field and adding one new optional response field.

## Tests added

- `tests/test_c2_pr14_opex_preview.py` — backend route-level tests
  mirroring `tests/test_c2_pr13_revenue_preview.py`.
- `tests/test_c2_pr14_opex_preview_browser.py` — Playwright tests
  mirroring `tests/test_c2_pr13_revenue_preview_browser.py`.
