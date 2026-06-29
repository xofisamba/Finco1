# C2 Debt Preview — Architecture Checkpoint

Concise handoff for the next reviewer (human or Claude) before any
real debt-sizing, debt-sculpting, interest-schedule, or DSCR-related
work is allowed to land on top of the C2 Operating Preview stack.

Written after C2-PR23 (preview service boundary),
C2-PR24 (backend-computed debt preview stub), and C2-PR25/26/27
(backend-computed debt preview v2 + UI safety + guardrail tests).

## Current debt preview scope

The Debt Preview slice in `/model/preview`'s JSON response body — under
the `"debt"` key — currently returns a single small Python
multiplication (`saved_capex_total * saved_gearing_pct / 100.0`)
along with the two saved inputs it actually read (the new
`saved_total_capex` and `saved_gearing_pct` breakdown fields added in
C2-PR25). The response always has the shape:

```json
{
  "status": "preview-ready" | "preview-unavailable",
  "senior_debt_preview": 1234567.89 | null,
  "saved_total_capex": 2345678.90 | null,
  "saved_gearing_pct": 52.5 | null,
  "currency": "EUR",
  "basis": "saved-inputs-only"
}
```

The UI renders:

* the visible label `Debt preview (saved inputs only):`
* the placeholder number (the value of `senior_debt_preview`), or `—`
  when unavailable
* a breakdown sub-line showing `Saved CAPEX used: X` and
  `Saved gearing used: Y %`, or `—` when unavailable
* a `title` (tooltip) attribute carrying the safety copy
  `"Uses saved CAPEX and saved gearing only. Not sculpted. Run
  remains authoritative."`

## Why it is backend-computed

The five earlier preview slices (CAPEX total, Revenue total, OPEX
total, EBITDA, Operating Cash Flow) are all **client-computed** — a
DOM sum, or a subtraction/passthrough of two DOM sums. The client
sends the numbers to the server, and the server only validates and
echoes them back. That pattern cannot scale to genuinely complex
modelling concepts like debt sizing, tax, or IRR/DSCR — those require
reading saved server-side state (capex, gearing, tenor, interest rate,
target DSCR, etc.) that the browser does not have, and should not be
asked to re-derive client-side.

Debt Preview is the **first** preview slice that follows the opposite
pattern: the **backend** reads saved inputs via the existing
authorization-time project lookup, computes a deliberately small
number in an isolated, well-tested Python function inside the
preview-service layer, and the **frontend only renders** whatever
status/value the backend decided to send — with zero arithmetic
anywhere in any `.js` file.

This is the seam a real debt-sizing PR would build on top of, without
needing to touch the frontend's rendering contract at all (only the
*value* the backend sends would need to get smarter).

## Exactly what it uses

| Field | Source | Purpose |
|---|---|---|
| `project_record.baseline_snapshot["total_capex_keur"]` | server-side saved baseline snapshot | the multiplier's first operand |
| `project_record.baseline_snapshot["gearing_pct"]` | server-side saved baseline snapshot | the multiplier's second operand |
| `project_record` itself | resolved by the route's existing `get_project_by_code(user.user_id, project_code)` authorization lookup | the project context that the route already had to look up anyway |

That is **the entire input set**. Nothing else is read.

## Exactly what it does NOT compute

Deliberately out of scope today, with explicit non-implementation
guarantees pinned by the test suite:

* Debt sculpting / cash-flow-driven debt sizing
* DSCR-driven sizing or any DSCR computation at all
* A repayment schedule of any kind (level, sculpted, mortgage-style,
  bullet, etc.)
* An interest schedule (no accrual, no compounding, no day-count
  convention)
* Amortization of any kind
* Debt service (interest + principal) computation
* Tax preview, IRR preview, waterfall preview, or any other
  financial slice beyond this single placeholder number
* Any reading of CAPEX / Revenue / OPEX / EBITDA / OCF **preview**
  (unsaved frontend) values as a debt-calculation input
* Any frontend JS computation of this value, in any file

## Why it is NOT debt sculpting

Sculpting means "size debt so projected cash flows can cover debt
service at every period, then back-solve the resulting debt
tenor/amortization profile." It requires a multi-period cash-flow
projection (full revenue + OPEX + capex + tax + IDC stack across
the debt tenor), a chosen target DSCR (1.20? 1.30?), a chosen
interest rate convention, a chosen repayment shape, and an
iterative solver.

The current Debt Preview does **none** of that. It is a single
multiplication of two saved scalars (`capex * gearing / 100`) into a
single number, computed in `compute_debt_preview()` in
`app/services/model_preview.py`. There is no iteration, no projection,
no DSCR check, no schedule, no day-count, no repayment method. The
number it returns would never match the real engine's own debt-sizing
output, because the real engine considers none of those factors.

## Why Run remains authoritative

Run (`/run`, implemented in `app/waterfall_core.run_project()` and the
domain layer) is the only code path that:

* reads every saved model input (capex, gearing, tenor, interest
  rate, target DSCR, IDC schedule, tax, depreciation, working capital,
  revenue profile, OPEX profile, DSRA convention, fee structure,
  repayment method, etc.)
* produces the full multi-period projection
* sizes debt (sculpted or otherwise) against that projection
* computes IRR (project, equity), DSCR (min, avg, by year), debt
  service, cash-flow waterfall, and sponsor returns

Debt Preview knows only `saved_capex_total` and `saved_gearing_pct`.
It cannot, by construction, match the Run's number. The visible label
and the tooltip both say so in plain English, and a dedicated
acceptance test (`test_workspace_shell_does_not_use_internal_jargon_in_label`)
pins the safety copy against the visible label region of the rendered
DOM.

## What remains before real debt preview

A genuine debt-sizing preview would need, at minimum:

1. **Saved input bridge.** Confirm that every input the real Run's
   debt-sizing step needs is currently in `baseline_snapshot` and
   reliably parsed by the existing `_safe_float()` helper. Today, only
   `total_capex_keur` and `gearing_pct` are read.
2. **Debt schedule preview service.** A new function in
   `app/services/model_preview.py` (or a sibling module) that mirrors
   `app/waterfall_core.py`'s debt-sizing step, in isolation, and
   whose output is reviewed against the real engine on the canonical
   TUHO and Oborovo anchors before any user-facing change ships.
3. **DSCR target handling.** Pick the exact DSCR target the preview
   uses (1.20? 1.30? whatever `baseline_snapshot["target_dscr"]`
   holds), and document the convention.
4. **Day-count / rate assumptions.** Document the actual / 360 vs.
   30/360 vs. actual / actual convention, the compounding frequency
   (annual / semiannual / quarterly), and whether the preview uses
   the same convention `app/waterfall_core.py` uses. A discrepancy
   here is the single likeliest source of preview-vs-Run drift.
5. **Repayment method.** Pick a single repayment method for the
   preview (sculpted to target DSCR, level / equal principal, bullet,
   mortgage-style) and document it. Today there is none.
6. **DSRA and fees.** Decide whether the preview sizes debt net of
   the DSRA reserve and up-front fees, matching the real Run's
   treatment, or gross. Almost certainly net, but the assumption
   must be made explicit and tested.
7. **Excel parity validation.** The TUHO / Oborovo / Generic Solar /
   Generic Wind reference workbooks (per
   `docs/generic_validation_reference_excel_spec.md` for the latter
   two) must be re-run end-to-end against the new preview code, and
   the anchor outputs compared to the existing frozen Run anchors.
   Any preview number that drifts from the corresponding Run number
   by more than the tolerances listed in that spec (±0.5% amounts,
   ±1% IDC, ±5bps IRR, ±0.01 DSCR, ±0.5pp gearing) is a stop-the-
   line event, not a doc-only tweak.

Until all seven are done, this stub is intentionally the only debt-
shaped output the Operating Preview stack produces.

## Files in scope for C2-PR25/26/27

* `app/services/model_preview.py` — `compute_debt_preview()` extended
  with the two new saved-input breakdown fields and the new
  `"saved-inputs-only"` basis label.
* `app/templates/partials/workspace_shell.html` — debt-preview
  indicator extended with the `Saved CAPEX used:` / `Saved gearing
  used:` breakdown sub-line and the safety `title` tooltip.
* `static/styles.css` — `.debt-preview-basis` style block (dashed
  border, muted colour, tabular-nums value column).
* `static/modelling/runtime-renderer.js` — new constants for the
  basis sub-element IDs; renderer patch block extended to format and
  patch the saved-inputs values when `debt.status === "preview-ready"`,
  and to revert them to `—` when `preview-unavailable`.
* `tests/test_c2_pr25_27_debt_preview_v2_safety.py` — new 12-point
  guardrail test file (27 tests total).
* `tests/test_c2_pr24_backend_debt_preview_stub.py` — three existing
  assertions updated to match the new response shape (the
  `"saved-capex-times-saved-gearing"` basis label was simplified to
  `"saved-inputs-only"` to match the unavailable branch and the new
  visible UI copy; the breakdown fields are now present in both
  ready and unavailable responses, with `null` in the unavailable
  case).
* `docs/C2_DEBT_PREVIEW_CHECKPOINT.md` — this file.

## What did NOT change

* `domain/*` — untouched.
* `app/waterfall_core.py` — untouched (MD5 unchanged).
* `app/input_adapter.py` — untouched.
* `app/project_factories.py` — untouched.
* Export logic (`app/services/export_service.py`,
  `app/services/export_audit_service.py`) — untouched.
* Persistence write logic — untouched.
* Financial formulas — untouched.
* Save/Run paths — untouched.
* The five existing preview slices (CAPEX, Revenue, OPEX, EBITDA,
  OCF) — behaviour unchanged; their response keys, shapes, validation
  rules, and routing are byte-for-byte identical to C2-PR24.
* `static/modelling/recalc-preview.js` — untouched. The "debt"
  mentions there are still exactly the two pre-existing disclaimer
  phrases ("no debt/tax/depreciation/financing" and "no debt service,
  no tax, no depreciation/amortization, no working"); no new debt-
  related code was added to that file by PR25/26/27.