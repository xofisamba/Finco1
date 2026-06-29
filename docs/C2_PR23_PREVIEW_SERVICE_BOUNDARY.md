# C2-PR23 — Preview Service Boundary Extraction

## Summary

Extracts `/model/preview`'s validation/computation/echo logic out of
`main_web.py` and into a new `app/services/model_preview.py` module,
following the convention already established by `app/services/
export_audit_service.py` / `app/services/export_service.py` (a plain
module of typed functions, no class hierarchy, docstrings explaining
exactly which responsibilities the route keeps vs. which move to the
service). This is a pure architectural extraction with **zero
behaviour change** for every existing preview field
(capex/revenue/opex/ebitda/operating_cash_flow).

## Methodology: characterization-first, then refactor

1. **Characterization tests first.** Before touching any production
   code, `tests/test_c2_pr23_preview_service_boundary.py` was written
   and run against the **unmodified** `/model/preview` route (the
   validation/echo logic still living inline as
   `_c2_pr7_validate_preview_payload()`/`model_preview()` in
   `main_web.py`). All 12 tests passed against the pre-extraction
   code, confirmed by running
   `python -m pytest tests/test_c2_pr23_preview_service_boundary.py -q`
   and inspecting the result before any extraction commit was made.
   This file was committed on its own first (see git history:
   "C2-PR23 step 1: characterization tests for /model/preview
   (pre-extraction)").

2. **Extract, do not change behaviour.** `app/services/
   model_preview.py` was created containing:
   - `sorted_unique_strings()` — moved verbatim from
     `_c2_pr7_sorted_unique_strings()`.
   - `validate_preview_payload()` — moved verbatim from
     `_c2_pr7_validate_preview_payload()`.
   - `build_preview_response()` — the response-assembly logic
     previously inlined directly in the route body (the five
     `if "...Preview" in body and body.get(...) is not None:` blocks).
   - `compute_debt_preview()` / `_safe_float()` / `_is_finite_number()`
     — new for C2-PR24 (see `docs/C2_PR24_BACKEND_DEBT_PREVIEW_STUB.md`);
     these did not exist in the pre-extraction code and are called
     additively from `build_preview_response()`.

   `main_web.py`'s `model_preview()` route became a thin adapter:
   (a) `get_current_user(request)` auth check (unchanged, still in
   the route); (b) `get_project_by_code(user.user_id, project_code)`
   project authorization check (unchanged, still in the route); (c) a
   call into `validate_preview_payload()` then `build_preview_response()`;
   (d) returning the `JSONResponse`. The route path
   (`POST /model/preview`) is unchanged.

3. **Re-run characterization tests after extraction.** All 12 tests
   in `tests/test_c2_pr23_preview_service_boundary.py` were re-run
   against the extracted code and passed unchanged — this is the
   direct proof of zero behaviour change for every case the task
   brief required: a full valid payload, missing optional fields,
   explicit-null fields, malformed/non-numeric fields, forbidden
   project, and unauthenticated requests.

## What moved where

| Before (inline in `main_web.py`) | After |
|---|---|
| `_c2_pr7_sorted_unique_strings()` | `app/services/model_preview.py::sorted_unique_strings()` |
| `_c2_pr7_validate_preview_payload()` | `app/services/model_preview.py::validate_preview_payload()` |
| Response-assembly code inlined in `model_preview()` | `app/services/model_preview.py::build_preview_response()` |
| Auth check (`get_current_user`) | Unchanged — still in `main_web.py`'s route |
| Project authorization (`get_project_by_code`) | Unchanged — still in `main_web.py`'s route |

## Confirmation of zero behaviour change

- `tests/test_c2_pr23_preview_service_boundary.py` (12 tests): passes
  identically before and after the extraction.
- The full pre-existing operating-preview test suite (`test_c2_pr7_*`,
  `test_c2_pr9_*`, `test_c2_pr10_*`, `test_c2_pr13_*` through
  `test_c2_pr22_*`) was re-run after the extraction and passes (one
  exact-equality assertion in `test_c2_pr9_runtime_request_hardening.py`
  was updated to tolerate the new, deliberately additive `"debt"`
  response field introduced by the immediately-following C2-PR24 work
  in this same stacked PR — that update is unrelated to the PR23
  extraction itself, which by construction cannot add/remove/rename
  any response field).
- The response shape for every one of the five pre-existing preview
  fields (capex/revenue/opex/ebitda/operating_cash_flow), the
  invalid-payload shape, the forbidden-project shape, and the
  unauthenticated 401 are all byte-for-byte identical to their
  pre-PR23 form.

## What did NOT change

- No route path, request shape, or response field name for any of the
  five pre-existing preview slices.
- No change to `app/waterfall_core.py`, `domain/*`,
  `app/input_adapter.py`, `app/project_factories.py`, any export logic,
  or any persistence write logic.
- No change to `static/modelling/recalc-preview.js`,
  `static/modelling/runtime-renderer.js`, or
  `app/templates/partials/workspace_shell.html` (those are
  C2-PR24-specific changes, documented separately in
  `docs/C2_PR24_BACKEND_DEBT_PREVIEW_STUB.md`).
