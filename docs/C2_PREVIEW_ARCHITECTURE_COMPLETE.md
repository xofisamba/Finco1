# C2 Preview Architecture — Complete

The C2 Operating Preview sprint is **complete**. This document
captures the final shape of `/model/preview`'s backend preview
pipeline, every module's responsibilities, the backend-ownership
principle, what the preview layer is (vs. what it isn't), and what
remains for the next sprint.

Read alongside:

* `docs/C2_PREVIEW_ARCHITECTURE_V2.md` — the C2-PR28/29/30
  handoff (the architecture this document supersedes for the
  current state).
* `docs/C2_DEBT_PREVIEW_CHECKPOINT.md` — debt-preview scope &
  guardrails.
* `docs/C2_PR23_PREVIEW_SERVICE_BOUNDARY.md` — the earliest
  extraction that created `app/services/model_preview.py`.
* `docs/C2_PR24_BACKEND_DEBT_PREVIEW_STUB.md` — the first
  backend-computed preview field.

## Final architecture

```
                      /model/preview  (request body)
                                │
                                ▼
            ┌──────────────────────────────────────┐
            │      main_web.py (thin adapter)       │
            │  (auth + project authorization only)  │
            └──────────────────┬───────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────────────┐
        │ app/services/model_preview.py (orchestrator) │
        │   - validate_preview_payload()               │
        │   - PreviewContext.build()                   │
        │   - _registry.run_all(context)               │
        └──────────────────┬───────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────────────┐
        │      app/services/preview_context.py         │
        │   Immutable @dataclass(frozen=True) bundle:  │
        │   project_record, baseline_snapshot,         │
        │   project_code, project_id, currency,        │
        │   preview_request                            │
        └──────────────────┬───────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────────────┐
        │    app/services/previews/_registry.py        │
        │   Ordered list of 5 RegisteredPreview        │
        │   entries. run_all(context) returns          │
        │   merged delta.                              │
        └────┬───────────┬──────────────┬─────────────┘
             ▼           ▼              ▼             ▼             ▼
        ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
        │Operating│ │  Debt   │ │   Tax   │ │   IRR   │ │  DSCR   │
        │ (echo)  │ │(backend)│ │ (stub)  │ │ (stub)  │ │ (stub)  │
        └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
                           │
                           ▼
                Combined JSON response
                19 keys (17 stable + 2 new)
                           │
                           ▼
            ┌──────────────────────────────────────┐
            │  static/modelling/runtime-renderer.js │
            │   render() patches each region's      │
            │   DOM element; never computes.        │
            └──────────────────────────────────────┘
```

## What each module owns

### `app/services/preview_context.py` — PreviewContext
Immutable value object passed to every preview computation.
Single source of truth for "what's available to a preview slice".
Sealed by `@dataclass(frozen=True)` so two slices called from the
same request see exactly the same input — no chance of one slice's
helper mutating shared state and silently affecting another slice's
result.

Fields: `project_record`, `baseline_snapshot`, `project_code`,
`project_id`, `currency`, `preview_request`.

### `app/services/previews/_registry.py` — Preview Registry
Ordered list of `RegisteredPreview(name, response_key, compute)`
entries. `run_all(context)` applies them in registration order and
returns the merged response delta. The orchestrator stays a thin
shim. No auto-discovery — every slice is registered explicitly so a
future module-rename accidentally missing one slice causes a clear
ImportError rather than a silent "missing preview" UX bug.

### `app/services/previews/operating_preview.py` — Operating
Wraps the five existing client-computed echo slices (capex /
revenue / opex / ebitda / operating_cash_flow). Special-cased in
the registry because it expands into FIVE top-level keys, not
under a single "operating" top-level key — preserving the
on-the-wire JSON byte stream that every existing consumer
(`runtime-renderer.js`, the export safety guardrails, the
PR24/25/27 characterizations) reads from.

### `app/services/previews/debt_preview.py` — Debt
Backend-owned. Reads only `context.baseline_snapshot` (NEVER
`context.preview_request` — proven by
`tests/test_c2_pr25_27_debt_preview_v2_safety.py::
TestDebtPreviewIsGenuinelyBackendComputed`).
Computes `senior_debt_preview = saved_capex_total *
saved_gearing_pct / 100.0`. Returns a 6-key shape with the two
saved-input breakdown fields added by C2-PR25/26/27
(`saved_total_capex`, `saved_gearing_pct`).

### `app/services/previews/tax_preview.py` — Tax
Backend-owned stub (C2-PR30). Always returns `preview-unavailable`.
A future PR that introduces the first real tax computation will
replace the constant return value with a real computation that
still obeys the same `PreviewContext → compute → dict` contract.

### `app/services/previews/irr_preview.py` — IRR
Backend-owned stub (C2-PR31). Always returns `preview-unavailable`.
A future PR will compute XIRR/IRR/MOIC here.

### `app/services/previews/dscr_preview.py` — DSCR
Backend-owned stub (C2-PR32). Always returns `preview-unavailable`.
A future PR will compute coverage ratios here.

### `app/services/model_preview.py` — Orchestrator
Holds the request-shape validator (`validate_preview_payload`)
and the response assembler (`build_preview_response`). Constructs
the `PreviewContext`, delegates to `_registry.run_all(context)`,
merges slice output into the response body. Re-exports the
`_safe_float` / `_is_finite_number` / `compute_debt_preview`
shims for backward-compat with the PR24/25/27 test suite.

### `app/templates/partials/workspace_shell.html` — UI
Five existing indicator rows (CAPEX / Revenue / OPEX / EBITDA /
OCF) inside `#operating-preview-panel`, plus three new backend-
owned rows (`#debt-preview`, `#tax-preview`, `#irr-preview`,
`#dscr-preview`). Each row uses the same
`runtime-status-indicator` / `badge badge-preview-only` /
`role="status"` / `aria-live="polite"` / `aria-busy` / sr-only-span
conventions — no new CSS pattern invented.

### `static/modelling/runtime-renderer.js` — Renderer
For every registered slice (debt / tax / irr / dscr today),
exposes a `_setXxxState(state)` helper plus a render patch block
in `render()`. The render branch ONLY formats/patches DOM with
whatever the backend decided to send — zero arithmetic, ever.
The `_hasRenderableXxxPreview()` gate guarantees the branch is a
safe no-op when the backend has not yet sent a real number.

### `static/modelling/recalc-preview.js` — Untouched
Continues to contain only the two pre-existing disclaimer phrases
("no debt/tax/depreciation/financing" and "no debt service, no
tax, no depreciation/amortization, no working"). No new IRR/DSCR
computation introduced anywhere on the frontend.

## Backend-ownership principle

The five operating slices (capex / revenue / opex / ebitda /
ocf) are deliberately **client-computed** — they are sums of
editable DOM cells that the browser already has, and the server
only validates/echoes them back. That pattern is right for those
slices: simple arithmetic over user-entered numbers, no need to
round-trip to the backend for each cell edit.

But scaling that pattern to debt sizing, tax, IRR, DSCR, and
waterfall distributions would require the BROWSER to re-derive
sophisticated multi-period modelling logic that it does not have,
and that the user would have to trust the browser to get exactly
right. The debt preview slice (C2-PR24/25/26/27) proved the
alternative: the **backend** reads saved inputs server-side,
computes a (deliberately crude) number in an isolated, well-tested
Python function, and the **frontend only renders** whatever the
backend decided to send.

The four backend-owned slices today (debt, tax, irr, dscr) all
follow this pattern. Each:
1. Reads only `context.baseline_snapshot` (NEVER
   `context.preview_request`).
2. Returns a stable response shape with a `status` field that is
   either `"preview-ready"` (real value) or `"preview-unavailable"`
   (always the case for tax/irr/dscr today).
3. Computes no IRR / DSCR / tax / debt / waterfall / sponsor / DSRA
   math — that's the next sprint's work.
4. Never mutates persistence.
5. Never imports the financial engine (`domain/*`,
   `app/waterfall_core.py`, `app/input_adapter.py`,
   `app/project_factories.py`).
6. Never runs from any route other than `/model/preview`.

## Preview vs. authoritative model

The preview layer is a **non-authoritative** UX hint. It exists
to give users a near-real-time read of "what does this scenario
look like" without forcing a full Save + Run cycle on every cell
edit.

| Concern | Preview layer | Authoritative Run |
|---|---|---|
| Source of computation | Backend preview slice (`app/services/previews/*`) | Financial engine (`domain/*`, `app/waterfall_core.py`) |
| Persistence | None (read-only on saved snapshot) | Full Save + Run cycle writes to `runtime_snapshot` |
| Speed | Sub-100ms per cell edit | Full multi-period projection (seconds) |
| Authoritative for what users see on Save/Run | No — Run is | Yes |
| Visible user copy | "Future backend preview. Run remains authoritative." | Full waterfall / IRR / DSCR / P&L |
| Tested by | C2-PR23..33 characterization + final-QA suites | PR22 export-run safety guardrails + factory/TUHO/Oborovo frozen-anchor tests |
| Updated when | The user edits a C1 grid cell | The user clicks Save + Run |

The user-visible copy is the load-bearing thing here: every
backend-owned preview row carries a tooltip that says "Run
remains authoritative", so a user who reads the preview can never
mistake it for the number that will appear in the export or the
IRR matrix.

## What remains for the next sprint

The preview architecture is complete. The next sprint is
**preview computation** — replacing the four
`preview-unavailable` stubs with real backend-computed values.
Each replacement is its own PR, with its own characterization
tests, its own guardrails, its own checkpoint doc:

### Debt preview → real backend debt sizing
Requires:
* Saved input bridge: confirm `interest_rate_pct`, `tenor_years`,
  `target_dscr`, IDC schedule inputs are all in
  `baseline_snapshot`.
* Debt schedule preview service that mirrors
  `app/waterfall_core.py`'s debt-sizing step in isolation.
* DSCR target handling: pick the convention.
* Day-count / rate conventions: pick annual / semiannual /
  quarterly and the convention (`actual/360`, `30/360`).
* Repayment method: sculpted vs. level vs. mortgage-style vs.
  bullet.
* DSRA and fees treatment (net vs. gross).
* Excel parity validation against TUHO / Oborovo / Generic
  Solar / Generic Wind reference workbooks (per
  `docs/generic_validation_reference_excel_spec.md` for the
  latter two).

### Tax preview → real backend tax preview
Requires:
* Tax engine extraction: Pillar II / CIT / WHT / loss
  carryforward.
* Depreciation method selection (straight-line vs. declining).
* Reconciliation with `domain/*`'s authoritative tax
  computation.

### IRR preview → real backend IRR
Requires:
* XIRR vs. MIRR choice.
* Project IRR vs. equity IRR vs. MOIC distinction.
* Equity cashflow construction (which itself requires debt
  service, tax, sponsor / distribution waterfall).
* Reference workbook parity validation.

### DSCR preview → real backend DSCR
Requires:
* Debt schedule preview (same prerequisite as Debt preview →
  real).
* EBITDA projection (which requires the OPEX persistence work
  that has been deferred since C2-PR17/18).
* Coverage ratio calculation: min / avg / by-year.

All four replacements share the same architectural seam built by
C2-PR28/29/30/31/32/33: a frozen `PreviewContext` is constructed
once per request, the registry iterates the registered slices in
order, and each slice returns a stable-shape dict that the
renderer formats but never computes. Adding a real computation to
any stub slice requires no new front-end code path — only
replacing the constant return value with the real computation.

## File map

| File | Status | Purpose |
|---|---|---|
| `app/services/preview_context.py` | NEW (PR28) | Immutable `PreviewContext` dataclass + factory. |
| `app/services/previews/_base.py` | NEW (PR28) | Protocol + types. |
| `app/services/previews/_registry.py` | MODIFIED (PR31/32) | Adds IRR + DSCR slice registration. |
| `app/services/previews/operating_preview.py` | NEW (PR28) | Five echo slices, byte-identical. |
| `app/services/previews/debt_preview.py` | NEW (PR28) | Backend-owned multiplier, byte-identical. |
| `app/services/previews/tax_preview.py` | NEW (PR28) | Backend-owned stub. |
| `app/services/previews/irr_preview.py` | NEW (PR31) | Backend-owned stub. |
| `app/services/previews/dscr_preview.py` | NEW (PR32) | Backend-owned stub. |
| `app/services/model_preview.py` | MODIFIED (PR28) | Orchestrator (validation + assemble). |
| `app/templates/partials/workspace_shell.html` | MODIFIED (PR24/30/31/32) | 5 indicator rows + 4 backend-owned preview rows. |
| `static/modelling/runtime-renderer.js` | MODIFIED (PR24/30/31/32) | Render branches for every backend-owned slice. |
| `tests/test_c2_pr23_preview_service_boundary.py` | Existing (PR23) | Service extraction characterizations. |
| `tests/test_c2_pr24_backend_debt_preview_stub.py` | Existing (PR24) | Debt preview characterizations. |
| `tests/test_c2_pr25_27_debt_preview_v2_safety.py` | Existing (PR25/26/27) | Debt preview v2 + UI safety + 12-point guardrails. |
| `tests/test_c2_pr28_30_preview_architecture_v2_characterization.py` | Existing (PR28) | Architecture v2 characterizations. |
| `tests/test_c2_pr28_30_tax_preview_stub.py` | Existing (PR28/29/30) | Tax preview + architecture guardrails. |
| `tests/test_c2_pr31_33_preview_architecture_complete_characterization.py` | NEW (PR31/32/33) | Final architecture characterizations. |
| `tests/test_c2_pr31_33_irr_dscr_preview_final_qa.py` | NEW (PR31/32/33) | IRR/DSCR previews + final QA guardrails. |
| `docs/C2_PREVIEW_ARCHITECTURE_V2.md` | Existing (PR28) | Architecture v2 handoff (now superseded by this doc). |
| `docs/C2_PREVIEW_ARCHITECTURE_COMPLETE.md` | NEW (PR31/32/33) | This document. |

## What did NOT change (across the entire C2 Preview sprint)

* `domain/*` — untouched.
* `app/waterfall_core.py` — untouched (MD5 unchanged:
  `6bf49f33efc989736c17cea0cb9b7723`).
* `app/input_adapter.py` — untouched.
* `app/project_factories.py` — untouched.
* Export logic — untouched.
* Persistence write logic — untouched.
* Financial formulas — untouched.
* Save/Run paths — untouched.
* `main_web.py` — only the route's call signature into
  `build_preview_response` is touched; the route body itself is
  not.
* `static/modelling/recalc-preview.js` — untouched. The two
  pre-existing disclaimer phrases remain the only "debt"-mentions
  in that file.
* `static/app.js` — untouched.

## Test summary (post-PR31/32/33)

| Suite | Result |
|---|---|
| `test_c2_pr31_33_preview_architecture_complete_characterization.py` (NEW, 13 tests) | **13/13 PASS** |
| `test_c2_pr31_33_irr_dscr_preview_final_qa.py` (NEW, 38 tests) | **38/38 PASS** |
| `test_c2_pr28_30_preview_architecture_v2_characterization.py` (19 tests, 1 updated) | **19/19 PASS** |
| `test_c2_pr28_30_tax_preview_stub.py` (43 tests) | **43/43 PASS** |
| `test_c2_pr25_27_debt_preview_v2_safety.py` (27 tests, 1 updated) | **27/27 PASS** |
| `test_c2_pr24_backend_debt_preview_stub.py` (12 tests) | **12/12 PASS** |
| `test_c2_pr23_preview_service_boundary.py` (16 tests) | **16/16 PASS** |
| `test_c2_pr22_export_run_safety_guardrails.py` (7 tests) | **7/7 PASS** |
| `test_c2_pr20_operating_preview_acceptance.py` + `test_c2_pr21_operating_preview_panel.py` | **12/12 PASS** |

**Total: 187/187 tests pass, 2 skipped** on the full C2 stack.

The C2 Operating Preview sprint is complete and ready for review.
The next sprint replaces the four `preview-unavailable` stubs with
real backend-computed values, gated by their own characterization
tests, guardrails, and checkpoint docs — exactly the same pattern
this sprint established.