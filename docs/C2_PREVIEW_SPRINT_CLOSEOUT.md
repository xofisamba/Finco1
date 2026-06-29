# C2 Preview Sprint — Closeout

The C2 Operating Preview + Excel Preview sprint is **complete**.
This document is the formal closeout record. It captures what was
delivered, the high-level timeline of the entire UI / Excel
Preview arc, the final architecture, the preview ownership matrix,
what the preview layer does (and does not do), and what the next
sprint picks up.

Read alongside:

* `docs/C2_PREVIEW_ARCHITECTURE_COMPLETE.md` — final architecture
  detail (built by C2-PR31/32/33).
* `docs/C2_PREVIEW_ARCHITECTURE_V2.md` — earlier architecture
  handoff (built by C2-PR28/29/30).
* `docs/C2_DEBT_PREVIEW_CHECKPOINT.md` — debt-preview scope &
  guardrails.
* `docs/C2_OPERATING_PREVIEW_ARCHITECTURE_CHECKPOINT.md` —
  pre-C2-PR28 architecture checkpoint.

## Complete Timeline (high-level)

| Arc | Phase | Theme | Status |
|---|---|---|---|
| C1 | C1-PR1..C1-PR6+ | Interaction Layer foundation (active-cell, selection, fill down/right, keyboard nav, focus management) | Merged |
| C2 | C2-PR1..C2-PR6 | Live Modelling Foundation (dependency graph, dirty-state unification, recalc scheduler, Live Model foundation) | Merged |
| C2 | C2-PR7 | Backend `/model/preview` Contract Stub | Merged |
| C2 | C2-PR9 | Runtime Request Hardening (abort/sequence guards + project authorization) | Merged |
| C2 | C2-PR10 | CAPEX Total Preview (client-echo slice 1/5) | Merged |
| C2 | C2-PR11 | Preview UX Polish (5-state machine, aria-live, sr-only) | Merged |
| C2 | C2-PR12 | Dirty-Strip Lag Fix | Merged |
| C2 | C2-PR13 | Revenue Total Preview (client-echo slice 2/5) | Merged |
| C2 | C2-PR14 | OPEX Total Preview (client-echo slice 3/5) | Merged |
| C2 | C2-PR15 | EBITDA Preview (client-echo slice 4/5) | Merged |
| C2 | C2-PR16 | Operating Cash Flow Preview (client-echo slice 5/5) | Merged |
| C2 | C2-PR17 | OPEX Line Editability Bridge | Merged |
| C2 | C2-PR18 | Preview-Only OPEX Governance | Merged |
| C2 | C2-PR19 | Preview Reset/Refresh Clarity | Merged |
| C2 | C2-PR20 | Operating Preview Acceptance | Merged |
| C2 | C2-PR21 | Operating Preview Panel (single-row container) | Merged |
| C2 | C2-PR22 | Export / Run Safety Guardrails | Merged |
| C2 | C2-PR23 | Preview Service Boundary (extracted `app/services/model_preview.py`) | Merged |
| C2 | C2-PR24 | Backend-Computed Debt Preview Stub (1st backend-owned slice) | Merged |
| C2 | C2-PR25/26/27 | Debt Preview v2 + UI Safety + Guardrail Tests | Merged |
| C2 | C2-PR28/29/30 | Preview Service Evolution (PreviewContext + Registry + per-slice modules + Tax Preview stub) | Merged |
| C2 | C2-PR31/32/33 | IRR + DSCR Preview Boundaries + Final Preview Architecture QA | Merged |
| **C2** | **C2-PR34/35/36** | **Preview Sprint Closeout (E2E acceptance + Governance lock + this doc)** | **Draft** |

The complete UI / Excel Preview arc spans **C1 + 33 C2 PRs**.

## What was delivered

### C1 — Interaction Layer
* Active cell + selection model + keyboard navigation + fill
  down/right + focus management on every editable cell across
  every production sheet.

### C2 — Live Modelling + Operating Preview + Backend Previews
* Live Model foundation: dependency graph, dirty-state
  unification, debounced recalc scheduler, real-time preview
  flush lifecycle.
* Five operating preview slices (CAPEX / Revenue / OPEX / EBITDA /
  OCF): client-computed, server-echoed, sub-100ms latency.
* Three backend-owned preview slices (Debt / Tax / IRR / DSCR):
  backend-computed from SAVED snapshot, never from frontend
  payload; frontend only renders.
* PreviewContext (frozen dataclass) + Registry (ordered slice
  list) + per-slice modules (`operating_preview.py`,
  `debt_preview.py`, `tax_preview.py`, `irr_preview.py`,
  `dscr_preview.py`).
* Runtime renderer + recalc-preview JS + 5-state machine +
  aria-live + sr-only span conventions + tooltip safety copy on
  every backend-owned indicator.
* Export / Run / Save / persistence / DB writes all proven
  unaffected by the preview pipeline (guardrails in C2-PR22 +
  C2-PR25/26/27 + C2-PR28/29/30 + C2-PR31/32/33 + C2-PR34 + C2-PR35).

### Governance Lock (C2-PR34/35/36)
* E2E acceptance pack (29 tests, fastapi.TestClient-driven,
  real routes, real auth, real projects) — exercises all 9
  preview indicators, all 4 backend slices, and 13 lifecycle
  scenarios.
* Governance lock (30 tests, parametrized module-import tests
  + JS static content + DB mtime/size + export bytes + render
  branch coverage) — permanently prevents silent additions of
  new preview modules, new financial formulas in JS, persistence
  writes from preview, or run side-effects.

## Final Architecture

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
        │   Immutable @dataclass(frozen=True) bundle   │
        └──────────────────┬───────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────────────┐
        │    app/services/previews/_registry.py        │
        │   Ordered list of 5 RegisteredPreview        │
        │   entries. run_all(context) returns delta.   │
        └────┬───────────┬──────────────┬─────────────┘
             ▼           ▼              ▼             ▼             ▼
        ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
        │Operating│ │  Debt   │ │   Tax   │ │   IRR   │ │  DSCR   │
        │ (echo)  │ │(backend)│ │ (stub)  │ │ (stub)  │ │ (stub)  │
        └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
                           │
                           ▼
                Combined JSON response
                (5 echo + 4 backend slices)
                           │
                           ▼
            ┌──────────────────────────────────────┐
            │  static/modelling/runtime-renderer.js │
            │   render() patches each region's      │
            │   DOM element; never computes.        │
            └──────────────────────────────────────┘
```

## Preview Ownership Matrix

| Preview | Owner | Status |
|---|---|---|
| Operating (CAPEX / Revenue / OPEX / EBITDA / OCF) | Client echo | **Complete** — fully wired, byte-identical round-trip, 5-state machine, aria-live, sr-only span, recalc-preview.js computes the values |
| Debt | Backend | **Stub complete** — saved_capex × saved_gearing / 100; future PR will replace with real debt sizing |
| Tax | Backend | **Stub complete** — always `preview-unavailable`; future PR will replace with real tax computation |
| IRR | Backend | **Stub complete** — always `preview-unavailable`; future PR will replace with real IRR (XIRR / project / equity) |
| DSCR | Backend | **Stub complete** — always `preview-unavailable`; future PR will replace with real DSCR (min / avg / by-year coverage ratio) |

## What Preview DOES

* Shows near-real-time read of "what does this scenario look
  like" without forcing a full Save + Run cycle on every cell
  edit.
* Computes CAPEX / Revenue / OPEX / EBITDA / Operating Cash
  Flow totals in the browser from editable DOM cells; echoes
  them to the server for validation + audit.
* Reads saved project inputs (CAPEX, gearing) server-side,
  computes a backend-owned preview (today: just debt sizing),
  and returns the result for the browser to render.
* Always returns a stable 5-key shape for every backend-owned
  slice (`status` / `basis` / `slice_value_preview` / `message` /
  `currency`), so the renderer can render even an empty result
  without crashing.
* Carries tooltip copy "Future backend preview. Run remains
  authoritative." on every backend-owned indicator so a user
  reading the preview can never mistake it for the number that
  will appear in the export or the IRR matrix.
* Operates at sub-100ms latency per cell edit (client echo) or
  per preview round-trip (backend slice).
* Uses an immutable `PreviewContext` so two slices called from
  the same request see exactly the same input.

## What Preview DOES NOT DO

* **No financial engine.** No call to `domain/*`,
  `app/waterfall_core.py`, `app/waterfall_runner.py`,
  `app/input_adapter.py`, `app/project_factories.py`,
  `app.proj_factories.py` — anywhere in the preview pipeline.
* **No persistence.** No DB writes, no schema migration, no
  Save / Load path interaction. Preview reads saved snapshot,
  never writes it.
* **No exports.** Preview values never leak into
  `/exports/runtime-summary.csv` or
  `/exports/institutional-workbook.xlsx` (proven by sentinel
  tests).
* **No waterfall.** No debt-service / debt-sizing / DSCR /
  cash-flow / sponsor / distribution logic — those live in
  `app/waterfall_core.py` and `domain/*`, which the preview
  pipeline never imports.
* **No sponsor model.** No equity cashflow construction, no
  IRR / XIRR / MOIC / equity IRR / project IRR — backend
  slices today always return `preview-unavailable` for those.
* **No Excel parity.** No anchor-cell validation against
  reference workbooks — that's the next sprint.
* **No debt sculpting.** No amortization schedule, no interest
  schedule, no repayment method, no day-count convention, no
  DSRA — that's the next sprint.
* **No tax engine.** No CIT / loss carryforward / deferred tax
  / tax shield / WHT / Pillar II — that's the next sprint.
* **No IRR calculation.** Backend IRR preview always returns
  `preview-unavailable`; a future PR will replace the constant
  with a real XIRR computation.
* **No DSCR calculation.** Backend DSCR preview always returns
  `preview-unavailable`; a future PR will replace the constant
  with a real coverage-ratio computation.

## Next Sprint

The next sprint is **Excel Parity / Financial Engine** —
replacing the four `preview-unavailable` stubs with real
backend-computed values, and validating them against
reference workbooks. Documentation-only scope this round; no
implementation lands in this sprint.

| Concern | Reference workbook / spec |
|---|---|
| Debt computation | TUHO / Oborovo / Generic Solar / Generic Wind reference workbooks; `docs/generic_validation_reference_excel_spec.md` |
| Tax computation | Same reference workbooks + a new tax-anchor tab per template |
| IRR computation | Same; explicit XIRR vs. MIRR decision per template |
| DSCR computation | Same; min / avg / by-year coverage per template |
| Waterfall | Debt service + principal sculpting + DSRA + fees + tax shield; tied to the waterfall engine (`app/waterfall_core.py`) |
| Excel parity | Round-trip every preview's anchor cell against the corresponding TUHO / Oborovo / Generic Solar / Generic Wind workbook, within the tolerances listed in `docs/generic_validation_reference_excel_spec.md` |

Each replacement is its own PR, with its own characterization
tests, its own guardrails, its own checkpoint doc — exactly the
pattern this sprint established (C2-PR23, PR25/26/27,
PR28/29/30, PR31/32/33, PR34/35/36).

## File map (the entire C2 Preview sprint)

| File | Status | Purpose |
|---|---|---|
| `app/services/preview_context.py` | NEW (PR28) | Immutable PreviewContext dataclass. |
| `app/services/previews/_base.py` | NEW (PR28) | Protocol + types. |
| `app/services/previews/_registry.py` | NEW (PR28) | Ordered registry. |
| `app/services/previews/operating_preview.py` | NEW (PR28) | Five echo slices. |
| `app/services/previews/debt_preview.py` | NEW (PR28) | Backend-owned multiplier. |
| `app/services/previews/tax_preview.py` | NEW (PR28) | Backend-owned stub. |
| `app/services/previews/irr_preview.py` | NEW (PR31) | Backend-owned stub. |
| `app/services/previews/dscr_preview.py` | NEW (PR32) | Backend-owned stub. |
| `app/services/model_preview.py` | MODIFIED (PR28) | Orchestrator. |
| `app/templates/partials/workspace_shell.html` | MODIFIED | 5 indicator rows + 4 backend-owned preview rows. |
| `static/modelling/runtime-renderer.js` | MODIFIED | Render branches for every backend-owned slice. |
| `static/modelling/recalc-preview.js` | UNTOUCHED | Two pre-existing disclaimer phrases preserved. |
| `static/modelling/live-model.js` | EXISTING (PR1) | Dependency graph + recalc scheduler. |
| `static/modelling/dependency-graph.js` | EXISTING (PR4) | Maps dirty cells to output groups. |
| `static/interaction/` | EXISTING (C1) | Interaction layer (active cell, selection, etc.). |
| `static/modelling/` | EXISTING (C2) | Live modelling + preview modules. |
| `docs/C2_PR*.md` | EXISTING | Per-PR docs. |
| `docs/C2_OPERATING_PREVIEW_ARCHITECTURE_CHECKPOINT.md` | EXISTING (PR22) | Pre-C2-PR28 checkpoint. |
| `docs/C2_PREVIEW_ARCHITECTURE_V2.md` | EXISTING (PR28) | PR28 handoff. |
| `docs/C2_PREVIEW_ARCHITECTURE_COMPLETE.md` | EXISTING (PR33) | PR33 handoff. |
| `docs/C2_PREVIEW_SPRINT_CLOSEOUT.md` | NEW (PR36) | This document. |
| `docs/C2_DEBT_PREVIEW_CHECKPOINT.md` | EXISTING (PR25) | Debt-preview scope & guardrails. |

## Test summary (post-PR34/35/36)

| Suite | Result |
|---|---|
| `test_c2_pr34_preview_e2e_acceptance.py` (NEW, 29 tests) | **29/29 PASS** |
| `test_c2_pr35_preview_governance_lock.py` (NEW, 30 tests) | **30/30 PASS** |
| `test_c2_pr31_33_preview_architecture_complete_characterization.py` (13 tests) | **13/13 PASS** |
| `test_c2_pr31_33_irr_dscr_preview_final_qa.py` (38 tests) | **38/38 PASS** |
| `test_c2_pr28_30_preview_architecture_v2_characterization.py` (19 tests) | **19/19 PASS** |
| `test_c2_pr28_30_tax_preview_stub.py` (43 tests) | **43/43 PASS** |
| `test_c2_pr25_27_debt_preview_v2_safety.py` (27 tests) | **27/27 PASS** |
| `test_c2_pr24_backend_debt_preview_stub.py` (12 tests) | **12/12 PASS** |
| `test_c2_pr23_preview_service_boundary.py` (16 tests) | **16/16 PASS** |
| `test_c2_pr22_export_run_safety_guardrails.py` (7 tests) | **7/7 PASS** |
| `test_c2_pr20_operating_preview_acceptance.py` + `test_c2_pr21_operating_preview_panel.py` | **12/12 PASS** |

**Total: 246/246 tests pass, 2 skipped** on the full C2 stack
across the entire UI / Excel Preview arc.

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
* `main_web.py` — only the route's call into
  `build_preview_response` is touched; the route body itself is
  not.
* `static/modelling/recalc-preview.js` — untouched. Two
  pre-existing disclaimer phrases remain the only "debt"-
  mentions in that file.
* `static/app.js` — untouched.

## Stop-after-report contract

* This PR (C2-PR34/35/36) is the **final implementation PR of
  the C2 Preview Architecture sprint**.
* Per brief: **DRAFT, do not merge** until the user has
  reviewed the closeout doc.
* Next sprint: **Excel Parity / Financial Engine** —
  documentation-only scope this round.