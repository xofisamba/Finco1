# C2-PR24 — Backend-Computed Debt Preview Stub

## Summary

Adds the **first backend-computed** (not frontend-computed) preview
field to `/model/preview`: a tiny, deliberately minimal "senior debt
preview" seam, proving the pattern *preview payload → backend preview
service → a small Python function → response → runtime renderer
(frontend only renders, never computes)*. This is explicitly **not**
full debt sculpting, amortization, DSCR sizing, an interest schedule,
or debt-service calculation — see "Explicitly NOT implemented" below.

## Exact calculation formula and saved-field names used

`app/services/model_preview.py::compute_debt_preview(body, project_record)`:

```
senior_debt_preview = round(saved_capex_total * (saved_gearing_pct / 100.0), 2)
```

- `saved_capex_total` = `project_record.baseline_snapshot["total_capex_keur"]`
- `saved_gearing_pct` = `project_record.baseline_snapshot["gearing_pct"]`
- `project_record` is the same `ProjectRecord` the route's existing
  `get_project_by_code(user.user_id, project_code)` authorization
  lookup already resolves — no new project-loading mechanism was
  invented.
- `gearing_pct` is confirmed (by reading, read-only,
  `app/persistence/projects_repository.py`'s
  `"gearing_pct": str(... gearing_ratio * 100)` and
  `app/input_adapter.py`'s `gearing_ratio=value / 100.0`) to be stored
  as a **0–100 percentage**, not a 0–1 fraction — dividing by `100.0`
  in the formula above matches that exact convention.
- Both values are parsed defensively via a private `_safe_float()`
  helper (tolerating the string-typed form-field convention used
  throughout `baseline_snapshot`, e.g. `"50000"`) and validated finite
  via `_is_finite_number()`. Either value missing, blank, or
  unparseable yields the unavailable response — never a fabricated
  number.

**Critical architectural rule, enforced and tested:** this function
NEVER reads any field from `body` (the incoming, possibly-unsaved
frontend preview payload, e.g. `capexTotalPreview`) as a debt-
calculation input. `body` is accepted as a parameter purely for
signature symmetry with the rest of the module and is not read inside
`compute_debt_preview()` at all. This is proven by
`tests/test_c2_pr24_backend_debt_preview_stub.py::
TestDebtPreviewIsGenuinelyBackendComputed`, which sends
`capexTotalPreview: 1.0` (a value that, if mistakenly used as a debt
input, would produce `0.7`) alongside a real saved CAPEX/gearing
combination, and confirms the returned `senior_debt_preview` reflects
the real saved CAPEX figure, never `1.0 * gearing`.

## Exact response shape

Additive to `/model/preview`'s JSON body, **unconditionally present**
(unlike the five client-computed fields, which are omitted entirely
when absent from the request — "unavailable" is itself a meaningful,
always-renderable status for this slice):

Unavailable (saved CAPEX total or saved gearing missing/invalid, or no
project context at all):

```json
{"debt": {"status": "preview-unavailable", "senior_debt_preview": null, "currency": "EUR", "basis": "saved-inputs-only"}}
```

Ready:

```json
{"debt": {"status": "preview-ready", "senior_debt_preview": 1234567.89, "currency": "EUR", "basis": "saved-capex-times-saved-gearing"}}
```

## Renderer: label, placeholder, and value text

- **Region/label markup:** `app/templates/partials/workspace_shell.html`,
  inside the existing `#operating-preview-panel` container, as a sixth
  indicator (`#debt-preview`), immediately after the C2-PR16 Operating
  Cash Flow indicator. Reuses the exact same
  `runtime-status-indicator`/`badge badge-preview-only`/`role="status"`/
  `aria-live="polite"`/`aria-busy`/sr-only-span conventions as the
  existing five indicators — no new CSS, no new markup pattern
  invented.
- **Label (exact text):** `Debt preview (saved inputs only):`
- **Placeholder when unavailable:** `—` (the existing `&mdash;`
  convention, unchanged from the other five indicators).
- **Value format when available:** reuses the existing
  `_formatTotalPreview()` helper in
  `static/modelling/runtime-renderer.js` verbatim (no new formatter
  written) — e.g. `1,234,567.89 EUR`.
- **JS additions (`static/modelling/runtime-renderer.js` only):**
  `DEBT_PREVIEW_VALUE_ELEMENT_ID`/`DEBT_REGION_ELEMENT_ID`/
  `DEBT_SR_ELEMENT_ID` constants, `_setDebtState()`,
  `_hasRenderableDebtPreview()` (gated on `debt.status ===
  "preview-ready"` AND a finite `senior_debt_preview`), and one more
  independent render-patch block inside `render()` — each mirrors the
  existing five blocks' structure exactly. No arithmetic of any kind
  is performed in this file; it only formats and patches the DOM with
  the already-backend-computed number.
- **`static/modelling/recalc-preview.js` is untouched** — confirmed by
  `tests/test_c2_pr24_backend_debt_preview_stub.py::
  TestNoDebtSculptingKeywordsInFrontendJs`, which fetches the file via
  its real static route and asserts no new debt-related keyword
  (`sculpt`/`dscr`/`interest schedule`, and zero growth in the count of
  `debt` occurrences beyond the two pre-existing "no debt service"/"no
  debt/tax/depreciation/financing" disclaimer phrases) was introduced.

## Why this proves the "backend-computed complex preview" architecture pattern

Every preview field added in C2-PR10 through C2-PR16 followed the same
pattern: the **client** computes a number (a DOM sum, or arithmetic on
two other client-computed numbers) and the **server only validates
and echoes it back**. That pattern cannot scale to genuinely complex
modelling concepts like debt sizing, tax, or IRR/DSCR — those require
reading saved server-side state (capex, gearing, tenor, interest rate,
target DSCR, etc.) that the browser does not have, and should not be
asked to re-derive client-side. C2-PR24 proves the alternative
architecture end-to-end with the smallest possible real example: the
**backend** reads saved inputs via the existing authorization-time
project lookup, computes a (deliberately crude) number in a small,
isolated, well-tested Python function inside the preview-service
layer, and the **frontend only renders** whatever status/value the
backend decided to send — with zero arithmetic anywhere in any `.js`
file. This is the seam a real debt-sizing PR would build on top of,
without needing to touch the frontend's rendering contract at all
(only the *value* the backend sends would need to get smarter).

## Explicitly NOT implemented (deliberately out of scope)

- Debt sculpting / cash-flow-driven debt sizing.
- DSCR-driven sizing or any DSCR computation at all.
- A repayment schedule of any kind (level, sculpted, mortgage-style,
  bullet, etc.).
- An interest schedule (no accrual, no compounding, no day-count
  convention).
- Amortization of any kind.
- Debt service (interest + principal) computation.
- Tax preview, IRR preview, waterfall preview, or any other financial
  slice beyond this single placeholder number.
- Any reading of CAPEX/Revenue/OPEX/EBITDA/OCF *preview* (unsaved
  frontend) values as a debt-calculation input — only SAVED
  `baseline_snapshot` fields are ever read.
- Any frontend JS computation of this value, in any file, including
  `recalc-preview.js`.

## What a future PR would need to add for real debt sizing

A genuine debt-sizing preview would need, at minimum: (1) a chosen
sizing methodology (gearing-cap vs. DSCR-cap vs. min of both, matching
whatever `app/waterfall_core.py`/`domain/*` already implement for the
real Run path — this PR deliberately does not read or duplicate that
logic); (2) the saved interest rate, tenor, and target DSCR fields
(already present in `baseline_snapshot` as `interest_rate_pct`,
`tenor_years`, `target_dscr` — not read by this stub); (3) a cash-flow
projection to test DSCR against across the debt tenor, which does not
exist anywhere in the preview pipeline today (only a single-year
EBITDA/OCF preview exists); (4) careful judgment about whether the
preview's sizing methodology is allowed to drift from the real engine's
own assumptions without confusing users — flagged as a real risk in
`docs/C2_OPERATING_PREVIEW_ARCHITECTURE_CHECKPOINT.md`'s "Recommended
next options" section, which explicitly recommends a focused review
pass before any of debt/tax/IRR/DSCR previews go further than this
PR's placeholder.
