# C2-PR15 — EBITDA Preview

## Summary

EBITDA Preview = Revenue Preview − OPEX Preview, computed **only** from
the two preview numbers already calculated client-side in the same
flush (C2-PR13's Revenue total preview and C2-PR14's OPEX total
preview). It is never re-read from the DOM, never derived from
Overview KPIs, and never computed by any financial engine — it is pure
arithmetic on two numbers the client already computed.

## Design choice: computed entirely client-side

The task brief offered two options: compute EBITDA entirely
client-side (pure arithmetic on the two already-computed preview
numbers), or send `revenueTotalPreview`/`opexTotalPreview` to the
server and have the server subtract them (also acceptable, since it
would be pure validation-style arithmetic, not financial engine logic).

**Client-side computation was chosen.** Rationale:

- It is the option most consistent with the task's own framing: "EBITDA
  Preview = Revenue Preview − OPEX Preview, computed ONLY from the two
  preview numbers already calculated client-side in the same flush."
  The revenue and opex preview numbers already exist as local
  JavaScript variables inside `buildPreviewPayload()` at the exact
  point EBITDA needs to be computed (`revenueTotalPreview`,
  `opexTotalPreview`) — there is no reason to round-trip them to the
  server and back just to subtract one from the other; doing so would
  add network latency and a server-side branch for a one-line
  subtraction with no validation value the client doesn't already
  provide.
- It keeps `main_web.py`'s role exactly as narrow as it has been for
  every PR in this chain (PR8/PR9/PR10/PR13/PR14): validate a
  client-supplied finite-or-null number, echo it back rounded. Having
  the server perform the subtraction itself would be a small but real
  expansion of the server's responsibility from "pure echo" to
  "performs a calculation," which every prior PR in this chain
  deliberately avoided even for trivial arithmetic — keeping that
  invariant unbroken was judged more valuable than the marginal
  simplicity of sending two numbers instead of one.
- It fits `static/modelling/recalc-preview.js`'s existing architecture
  exactly: `_computeEbitdaFromPreviews(revenuePreview, opexPreview)` is
  a new, small, pure function alongside `_computeCapexTotalFromDom()`/
  `_computeRevenueTotalFromDom()`/`_computeOpexTotalFromDom()`, called
  from `buildPreviewPayload()` in the same place those are, using their
  outputs as its only inputs. No new client/server data shape beyond
  one more additive payload field (`ebitdaPreview`) and one more
  additive response field (`ebitda`) was needed.

The server's role is therefore, again, intentionally minimal: validate
that `ebitdaPreview` (if present) is a finite number or `null`, and
echo it back, rounded to 2 decimals, under a new `ebitda` response
field — it never re-derives EBITDA from `revenueTotalPreview`/
`opexTotalPreview` itself, and never second-guesses the client's
arithmetic.

## Null propagation — the critical invariant

`_computeEbitdaFromPreviews(revenuePreview, opexPreview)` returns `null`
— never a fabricated partial value — whenever **either** input is not
a finite number (including `null`, `undefined`, `NaN`, or a non-number
type). Concretely, in `buildPreviewPayload()`:

```js
var ebitdaPreview = _computeEbitdaFromPreviews(revenueTotalPreview, opexTotalPreview);
```

Since `revenueTotalPreview`/`opexTotalPreview` are themselves each
independently `null` unless the **current flush's** dirty-cell set
touched their own grid (the existing `touchesRevenue`/`touchesOpex`
scoping from PR13/PR14), EBITDA preview is correctly `null` unless
**both** the Revenue and OPEX grids were edited (and settled within the
same debounce window) together. This is intentional: EBITDA must never
be shown using a stale preview value carried over from an earlier,
unrelated flush — only from two values genuinely fresh in this exact
flush.

## Payload / response shape

### Request (`POST /model/preview` body), additive field

```json
{
  "...": "... existing fields unchanged ...",
  "revenueTotalPreview": 12345.67,
  "opexTotalPreview": 8456.0,
  "ebitdaPreview": 3889.67
}
```

`ebitdaPreview` is `null` whenever either `revenueTotalPreview` or
`opexTotalPreview` is `null` in this same payload.

### Response, additive field

```json
{
  "ok": true,
  "...": "... existing fields unchanged ...",
  "ebitda": { "preview": 3889.67, "currency": "EUR" }
}
```

Shaped `{"preview": <number>, "currency": "EUR"}`, following the
`revenue`/`opex` naming pattern exactly. Present only when the
request's `ebitdaPreview` was a non-null finite number; omitted
entirely otherwise (never fabricated as `0.0`).

`main_web.py`'s `_c2_pr7_validate_preview_payload()` gained one new
validation branch (`ebitdaPreview`, mirroring the others exactly) and
`model_preview()` gained one new response branch (the `ebitda` field).
No new route was added; the server performs no subtraction itself.

## Rendering

```html
<div class="runtime-status-indicator ebitda-preview-indicator"
     id="ebitda-preview" role="status" aria-live="polite"
     aria-label="Unsaved EBITDA preview, not the saved total" aria-busy="false">
  <span class="runtime-status-indicator__label">EBITDA preview (unsaved):</span>
  <span class="runtime-status-indicator__value badge badge-preview-only"
        id="ebitda-preview-value"
        data-c2pr15-ebitda-preview="idle" data-c2pr11-runtime-state="idle">&mdash;</span>
  <span class="sr-only" id="ebitda-preview-sr">EBITDA preview status: Idle</span>
</div>
```

**Exact new user-visible wording:** the label **"EBITDA preview
(unsaved):"**, initial placeholder **"—"**, formatted value e.g.
**"3,889.67 EUR"** — same `_formatTotalPreview()` helper, same
`badge`/`badge-preview-only` styling, no new CSS.

## Integration with PR9/PR11 — fully reused

Exactly like OPEX (PR14): `live-model.js` is unmodified; the generic
flush/render path handles the new field automatically. `setUpdating()`/
`setUnavailable()`/`setFailed()` each gained a `_setEbitdaState(...)`
call; `render()` gained one more independent patch block, gated on
`_hasRenderableEbitdaPreview(body)` (checks `body.ebitda.preview` is a
finite number) — a missing/null `ebitda` field is a safe no-op that
never blanks a previously-rendered valid EBITDA value, identical to
every other preview field's behaviour.

## No real financial engine use

EBITDA here is `Revenue Preview − OPEX Preview` — both of which are
themselves plain DOM sums, not financial-engine outputs. No import of,
or call into, `domain/*`, `app/waterfall_core.py`,
`app/input_adapter.py`, or `app/project_factories.py` was added
anywhere in this PR.

## Tests added

- `tests/test_c2_pr15_ebitda_preview.py` — backend route-level tests:
  correct EBITDA computation when both revenue/opex previews are
  supplied, null propagation when either is null/absent, validation/
  rejection of malformed values, omission rules.
- `tests/test_c2_pr15_ebitda_preview_browser.py` — Playwright tests:
  EBITDA updates correctly after both Revenue and OPEX edits settle in
  the same flush, null/blank state when only one grid is edited, and a
  failed preview request preserves the last valid EBITDA value.
