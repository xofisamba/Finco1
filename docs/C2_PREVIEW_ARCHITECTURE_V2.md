# C2 Preview Architecture v2 — Handoff Document

Captures the architectural shape of `/model/preview` after
C2-PR28/29/30 lands. Read alongside:

* `docs/C2_DEBT_PREVIEW_CHECKPOINT.md` — debt-preview scope &
  guardrails.
* `docs/C2_PR23_PREVIEW_SERVICE_BOUNDARY.md` — earlier extraction
  from `main_web.py` into `app/services/model_preview.py`.
* `docs/C2_PR24_BACKEND_DEBT_PREVIEW_STUB.md` — debt-preview stub
  rationale.
* `docs/C2_OPERATING_PREVIEW_ARCHITECTURE_CHECKPOINT.md` — the
  pre-PR28 architecture-checkpoint doc; this v2 document supersedes
  it for the "next steps" section.

## Target architecture

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
        │   Ordered list of RegisteredPreview entries. │
        │   run_all(context) returns merged delta.    │
        └────┬───────────┬──────────────┬───────────────┘
             │           │              │
             ▼           ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  operating_  │ │    debt_     │ │    tax_      │
    │   preview    │ │   preview    │ │   preview    │
    │ (5 echo      │ │ (backend     │ │ (backend     │
    │  slices)     │ │  multiplier) │ │  STUB)       │
    └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
           │                │                │
           ▼                ▼                ▼
    ┌─────────────────────────────────────────────────┐
    │  Combined JSON:                                 │
    │    ok, status, executed, accepted, ...           │
    │    capex, revenue, opex, ebitda, ocf,           │
    │    debt,                                        │
    │    tax     <-- C2-PR30 addition                 │
    │    overview                                   │
    └─────────────────────────────────────────────────┘
                           │
                           ▼
                  /model/preview (response body)
                           │
                           ▼
            ┌──────────────────────────────────────┐
            │  static/modelling/runtime-renderer.js │
            │   render() patches each region's      │
            │   DOM element; never computes.        │
            └──────────────────────────────────────┘
```

## Why this shape

### Single immutable `PreviewContext`

Every preview slice today (or on the public roadmap) needs SOME of:
the saved project's `baseline_snapshot`, the live (possibly-unsaved)
preview request, the project's `project_code`/`project_id`, the
authoritative currency, and the `ProjectRecord` itself. Passing
each of these as a separate positional argument creates a growing
signature surface area; passing the bundle keeps every future slice
(`irr_preview`, `dscr_preview`, `waterfall_preview`) a one-argument
`compute(context)` function.

Immutability (via `@dataclass(frozen=True)`) guarantees two preview
slices called from the same `build_preview_response()` invocation
see exactly the same input — no chance of one slice's helper
mutating shared state and silently affecting another slice's result.

### Registry pattern (not a god-module)

Pre-PR28/29, `app/services/model_preview.py` was 100% of the
preview pipeline. PR23 moved the validation/echo logic there from
`main_web.py`; PR24 added the debt preview. With the new tax stub
in C2-PR30 and the planned future slices (IRR / DSCR / waterfall),
that file would have crossed the 1000-line threshold while still
having to grow every time a slice was added.

The registry pattern (`app/services/previews/_registry.py`) holds
an ordered list of `RegisteredPreview(name, response_key, compute)`
entries. `run_all(context)` applies them in registration order and
returns the merged response delta. The orchestrator
(`model_preview.py`) stays a thin shim.

Explicit `register_default_slices()` registration (no auto-
discovery) means a future module-rename accidentally missing one
slice causes a clear ImportError rather than a silent "missing
preview" UX bug.

### Operating slice is special-cased

The five existing echo slices (capex / revenue / opex / ebitda /
operating_cash_flow) live at the TOP LEVEL of the response body, not
nested under an `operating` key. Pre-PR28/29/30 they were inline in
`build_preview_response()`; PR29 extracted them into
`app/services/previews/operating_preview.py` but preserved the
on-the-wire JSON byte stream by having the registry's `run_all()`
call `compute_operating_slice(context)` directly and spread the
result, instead of registering the operating slice under a single
top-level key.

This is intentional: every existing consumer
(`static/modelling/runtime-renderer.js`, the export-endpoint safety
guardrails in tests/test_c2_pr22_*, the PR24/25/27 debt-preview
characterizations) reads these slices at their existing top-level
keys. Changing the wire shape would force every consumer to learn
the new shape in the same PR — exactly the kind of opportunistic
refactor this stack is designed to avoid.

### Why every complex preview is backend-owned

The five existing echo slices (capex / revenue / opex / ebitda /
operating_cash_flow) are deliberately client-computed — they are
sums of editable DOM cells that the browser already has, and the
server only validates/echoes them back. That pattern is right for
those slices: simple arithmetic over user-entered numbers, no need
to round-trip to the backend for each cell edit.

But scaling that pattern to debt sizing, tax, IRR, DSCR, and
waterfall distributions would require the BROWSER to re-derive
sophisticated multi-period modelling logic that it does not have,
and that the user would have to trust the browser to get exactly
right. The debt preview stub (C2-PR24/25/26/27) proved the
alternative: the **backend** reads saved inputs server-side,
computes a (deliberately crude) number in an isolated, well-tested
Python function, and the **frontend only renders** whatever the
backend decided to send.

The tax preview stub (C2-PR30) is the second slice to use this
pattern. It always returns `preview-unavailable` today; a future
PR that introduces the first real tax computation will replace the
constant return value with a real computation that still obeys the
same `PreviewContext → compute → dict` contract — no JS, no engine
imports, no DB writes, no exports affected.

### Future slices (placeholder, NOT IMPLEMENTED)

The architecture is forward-compatible with the following future
slices — each would be a new module under `app/services/previews/`,
each would expose a `compute(context)` and a `RESPONSE_KEY`, each
would register itself explicitly in `register_default_slices()`:

```
┌──────────────────────────────────────────────────────────────┐
│                Future (C2-PR-?, NOT in this PR)              │
│                                                              │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│   │     irr_     │  │     dscr_    │  │  waterfall_  │        │
│   │   preview    │  │   preview    │  │   preview    │        │
│   │  (backend)   │  │  (backend)   │  │  (backend)   │        │
│   └──────────────┘  └──────────────┘  └──────────────┘        │
└──────────────────────────────────────────────────────────────┘
```

Each of those will land as its own PR, with its own characterization
tests, its own guardrails, its own checkpoint doc, and its own
explicit "no behaviour change to existing slices" re-proof. None of
them are part of this PR.

## File map

| File | Status | Purpose |
|---|---|---|
| `app/services/model_preview.py` | MODIFIED (refactor) | Orchestration only — `validate_preview_payload`, `build_preview_response`, re-exports of `_safe_float`/`_is_finite_number`/`compute_debt_preview` shim for backward-compat with PR24/25/27 test suites. |
| `app/services/preview_context.py` | NEW | Immutable `PreviewContext` dataclass + `PreviewContext.build()` factory. |
| `app/services/previews/__init__.py` | NEW | Empty package marker. |
| `app/services/previews/_base.py` | NEW | `PreviewComputeFn` type, `PreviewSlice` protocol, `RegisteredPreview` dataclass. |
| `app/services/previews/_registry.py` | NEW | Ordered registry; `register` / `register_default_slices` / `all_slices` / `run_all` / `reset_for_tests`. |
| `app/services/previews/operating_preview.py` | NEW | Five echo slices (capex / revenue / opex / ebitda / ocf), expanded into the response body via `expand_into_response_body`. |
| `app/services/previews/debt_preview.py` | NEW | `compute_debt_slice(context)` — extracted byte-identical from the PR25/26/27 implementation. |
| `app/services/previews/tax_preview.py` | NEW | `compute_tax_slice(context)` — always returns `preview-unavailable`. |
| `app/templates/partials/workspace_shell.html` | MODIFIED (additive) | New `#tax-preview` row inside `#operating-preview-panel`, mirroring the `#debt-preview` row. |
| `static/modelling/runtime-renderer.js` | MODIFIED (additive) | New `TAX_PREVIEW_VALUE_ELEMENT_ID` / `TAX_REGION_ELEMENT_ID` / `TAX_SR_ELEMENT_ID` constants; `_setTaxState(state)` helper; tax patch block in `render()`. |
| `tests/test_c2_pr28_30_preview_architecture_v2_characterization.py` | NEW | 19 characterization tests for byte-identical pre-refactor behaviour. |
| `tests/test_c2_pr28_30_tax_preview_stub.py` | NEW | 43 tests covering PreviewContext / Registry / per-slice modules + 11-point guardrail suite. |
| `docs/C2_PREVIEW_ARCHITECTURE_V2.md` | NEW | This document. |

## What did NOT change

* `domain/*` — untouched.
* `app/waterfall_core.py` — untouched (MD5 unchanged).
* `app/input_adapter.py` — untouched.
* `app/project_factories.py` — untouched.
* Export logic — untouched.
* Persistence write logic — untouched.
* Financial formulas — untouched.
* Save/Run paths — untouched.
* The five existing operating-preview slices (capex / revenue /
  opex / ebitda / ocf) — JSON byte stream on the wire is
  byte-identical to PR25/26/27.
* The debt preview slice — JSON byte stream is byte-identical to
  PR25/26/27.
* `static/modelling/recalc-preview.js` — untouched. The "debt"
  mentions there remain exactly the two pre-existing disclaimer
  phrases; no new debt-related code was added by PR28/29/30, and
  no tax-related code was added there either.
* `main_web.py` — untouched (the route's call into
  `build_preview_response()` is unchanged; only the function's
  implementation moved).

## Guardrail tests

All pinned in `tests/test_c2_pr28_30_tax_preview_stub.py`:

1. `TestPreviewContextConstruction` (5 tests) — PreviewContext
   constructs correctly with no project, with a fake project, with
   a broken project record, with a non-dict request, and with a
   non-default currency.
2. `TestPreviewContextImmutable` (3 tests) — frozen dataclass
   invariants enforced.
3. `TestRegistryOrderPreserved` (2 tests) — default slices
   registered in documented order; `register_default_slices()` is
   idempotent.
4. `TestRegistryDeterministicAcrossRuns` (1 test) — `run_all()`
   is a pure function.
5. `TestOperatingPreviewSliceByteIdentical` (3 tests) — five echo
   slices byte-identical to PR25/26/27.
6. `TestDebtPreviewSliceByteIdentical` (3 tests) + 4 helper unit
   tests — debt preview unchanged.
7. `TestTaxPreviewUnavailableShape` (5 tests) — tax slice 5-key
   shape, route-level, invalid-payload, forbidden-project.
8. `TestTaxPreviewAlwaysUnavailableRegardlessOfContext` (2 tests) —
   even with tempting saved/frontend inputs, the slice refuses.
9. `TestNoForbiddenImportsInAnyPreviewModule` (7 tests) — every
   module in the new architecture is free of `domain.*` /
   `app.waterfall_core` / `app.waterfall_runner` /
   `app.input_adapter` / `app.project_factories` /
   `app.proj_factories` imports.
10. `TestNoEngineCallFromRegistryOrContext` (1 test) — context
    is a value object with exactly one method (`build()`).
11. `TestPreviewArchitectureNoDbWrites` (1 test) — DB mtime/size
    unchanged after `/model/preview`.
12. `TestPreviewArchitectureNoEngineCall` (1 test) — `waterfall_core
    .run_project` not invoked.
13. `TestNoFrontendTaxComputation` (2 tests) — runtime renderer +
    recalc-preview JS have no tax-arithmetic patterns.
14. `TestPreviewArchitectureNoExportChanges` (1 test) — sentinel
    smoke test.
15. `TestPreviewArchitectureNoSaveRunChanges` (2 tests) — no save
    or run side-effect.