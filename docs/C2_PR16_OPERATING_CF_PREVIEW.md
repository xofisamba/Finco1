# C2-PR16 — Operating Cash Flow Preview

## ⚠️ THIS IS NOT AUTHORITATIVE OPERATING CASH FLOW ⚠️

**Read this section before anything else in this document.** The
"Operating Cash Flow Preview" introduced by this PR is **not** a real
operating cash flow calculation. It applies **no** debt service
adjustment, **no** tax adjustment, **no** depreciation/amortization
add-back, **no** working-capital movement, and **no** financing
adjustment of any kind. It is defined, in full, as:

```
Operating Cash Flow Preview := EBITDA Preview
```

— a direct, verbatim passthrough of C2-PR15's EBITDA Preview value,
with nothing subtracted or added. This is a **deliberate, explicit
simplification**, not an oversight or a placeholder for "PR16 will get
the real formula eventually within this PR." Its entire purpose is to
prove that the preview pipeline built across C2-PR6 through C2-PR15
(dirty → debounced scheduler → dependency graph → executor → preview
payload → `POST /model/preview` → 5-state renderer) can correctly
**chain a preview of a preview of previews**: CAPEX/Revenue/OPEX
previews (each a plain DOM sum) feed EBITDA preview (pure arithmetic on
two of those sums), which in turn feeds this Operating Cash Flow
preview (a passthrough of that arithmetic result). Nothing about the
real, authoritative operating-cash-flow calculation used anywhere else
in this codebase (which does account for debt/tax/depreciation/working
capital) is touched, replaced, or represented by this value.

This non-authoritative framing is enforced in three places, not just
this document:

1. **Code comment** directly above `_computeOcfFromEbitda()` in
   `static/modelling/recalc-preview.js`, in capital letters, reading
   `*** THIS IS NOT AUTHORITATIVE OPERATING CASH FLOW. ***`.
2. **Code comment** directly above the `operating_cash_flow` response
   branch in `main_web.py`'s `model_preview()` route, with the same
   framing.
3. **Code comment** in `static/modelling/runtime-renderer.js`'s module
   header and inline above the OCF render/state-transition blocks.
4. **User-facing label**: the rendered indicator's label is
   "Operating cash flow preview (unsaved):" — deliberately using
   "preview" (never "Operating Cash Flow:" alone, which could be
   mistaken for an authoritative figure) and the region's
   `aria-label` reads "Unsaved, non-authoritative operating cash flow
   preview placeholder" — the word "non-authoritative" and
   "placeholder" both appear explicitly in markup a screen reader will
   announce, not just in this doc.

## Calculation

`static/modelling/recalc-preview.js`'s new `_computeOcfFromEbitda(ebitdaPreview)`:

```js
function _computeOcfFromEbitda(ebitdaPreview) {
  if (typeof ebitdaPreview !== 'number' || !isFinite(ebitdaPreview)) return null;
  return ebitdaPreview;
}
```

Called from `buildPreviewPayload()` immediately after `ebitdaPreview`
is computed (C2-PR15), using `ebitdaPreview` as its only input — never
re-reading the DOM, never reading Overview KPIs, never calling any
engine. If EBITDA preview is `null` (e.g. because either the Revenue or
OPEX preview was unavailable this flush — see
docs/C2_PR15_EBITDA_PREVIEW.md), Operating Cash Flow preview is `null`
too — null propagates straight through, never fabricated.

## Payload / response shape

### Request (`POST /model/preview` body), additive field

```json
{
  "...": "... existing fields unchanged ...",
  "ebitdaPreview": 3889.67,
  "operatingCashFlowPreview": 3889.67
}
```

### Response, additive field

```json
{
  "ok": true,
  "...": "... existing fields unchanged ...",
  "operating_cash_flow": { "preview": 3889.67, "currency": "EUR" }
}
```

Shaped `{"preview": <number>, "currency": "EUR"}`. Present only when
the request's `operatingCashFlowPreview` was a non-null finite number;
omitted entirely otherwise. `main_web.py`'s
`_c2_pr7_validate_preview_payload()` gained one new validation branch;
`model_preview()` gained one new response branch
(`response_body["operating_cash_flow"]`). No new route was added; the
server performs no calculation here either — it only validates
finiteness and echoes the client's number back, rounded to 2dp.

## Rendering

```html
<div class="runtime-status-indicator operating-cf-preview-indicator"
     id="operating-cf-preview" role="status" aria-live="polite"
     aria-label="Unsaved, non-authoritative operating cash flow preview placeholder" aria-busy="false">
  <span class="runtime-status-indicator__label">Operating cash flow preview (unsaved):</span>
  <span class="runtime-status-indicator__value badge badge-preview-only"
        id="operating-cf-preview-value"
        data-c2pr16-ocf-preview="idle" data-c2pr11-runtime-state="idle">&mdash;</span>
  <span class="sr-only" id="operating-cf-preview-sr">Operating cash flow preview status: Idle</span>
</div>
```

**Exact new user-visible wording:** the label **"Operating cash flow
preview (unsaved):"**, initial placeholder **"—"**, formatted value
e.g. **"3,889.67 EUR"** — same `_formatTotalPreview()` helper, same
`badge`/`badge-preview-only` styling, no new CSS.

## Integration with PR9/PR11 — fully reused

`live-model.js` is unmodified. `setUpdating()`/`setUnavailable()`/
`setFailed()` each gained a `_setOcfState(...)` call; `render()` gained
one more independent patch block, gated on `_hasRenderableOcfPreview(body)`
(checks `body.operating_cash_flow.preview` is a finite number) — a
missing/null field is a safe no-op that never blanks a previously-
rendered valid OCF preview value.

## No real financial engine use

Confirmed: this entire feature is two passthrough/arithmetic functions
chained on top of two DOM sums; no import of, or call into, `domain/*`,
`app/waterfall_core.py`, `app/input_adapter.py`, or
`app/project_factories.py` was added anywhere in this PR — and
explicitly, no debt/tax/DSCR/IRR/cash-waterfall engine code of any kind
was touched or referenced.

## Tests added

- `tests/test_c2_pr16_ocf_preview.py` — backend route-level tests:
  Operating Cash Flow preview equals the supplied EBITDA preview
  exactly (chaining correctness), null propagation when EBITDA preview
  is null/absent, validation/rejection of malformed values.
- `tests/test_c2_pr16_ocf_preview_browser.py` — Playwright tests:
  chained calculation correctness end-to-end (editing Revenue + OPEX
  flows all the way through EBITDA to OCF), null/blank state, and
  renderer update.
