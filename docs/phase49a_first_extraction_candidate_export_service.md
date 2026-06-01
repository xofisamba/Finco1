# Phase 49A — First Extraction Candidate: export_service

**Base SHA:** 926317cb4b61015bf8e8e2693161cdcc22d46b0a

## Recommendation

The safest first real refactor (for the next phase, **49B**) is to extract **export/download orchestration** from `main_web.py` into **`app/services/export_service.py`**.

## Why export_service is the safest first extraction

1. **Leaf-like:** export consumes already-computed runtime results and produces bytes; it does not feed back into the model.
2. **Already partly packaged:** writers live in `app/export/*` (`runtime_summary.py`, `institutional_workbook.py`, `workbook_index.py`) and `app/excel_export.py`; the orchestration glue is what sits in `main_web.py`.
3. **Anchored by existing tests:** Phases 47-48 added Export_Metadata (first sheet) and Workbook_Index (second sheet) plus their helpers and tests — these give a parity anchor so the extraction can be proven behavior-preserving.
4. **No runtime-path risk:** unlike run orchestration, moving export call sites cannot change DSCR/SHL/distribution outputs.

## Scope of the proposed 49B extraction (NOT done in 49A)

- Move the orchestration bodies of `POST /download`, `GET /download`, `GET /exports/runtime-summary.csv`, `GET /exports/institutional-workbook.xlsx` into `app/services/export_service.py` functions.
- **Keep route signatures and HTTP responses unchanged** (same status codes, filenames, content-types, body bytes).
- **Keep workbook writers unchanged** except for their call sites.
- **Preserve Export_Metadata / Workbook_Index behavior** from Phases 47-48 exactly (first/second sheet, helper outputs).
- Routes become thin: parse request → call `export_service` → return response.

## Out of scope for 49B

No formula/runtime/model-output changes; no schema/fixture changes; no JS; no changes to `app/export/*` writer internals; no scenario/run/persistence extraction.

## Tests to add (in 49B, before/with the extraction)

- `POST /download` returns 200, correct `Content-Disposition` filename, correct `Content-Type` (xlsx), for an authenticated TUHO/Oborovo request; 302 to `/login` when unauthenticated; 400 on invalid input.
- `GET /exports/runtime-summary.csv` returns 200 + `text/csv` + expected header row.
- `GET /exports/institutional-workbook.xlsx` returns 200 + xlsx content-type.
- The generated workbook still has **Export_Metadata as the first sheet** and **Workbook_Index as the second sheet** (Phase 47/48 parity).
- Byte-or-structure parity: the workbook produced via `export_service` matches the pre-extraction workbook structure (sheet names/order).

## Acceptance criteria for 49B

Routes delegate to `app/services/export_service.py`; all the above tests pass; Phase 47/48 export tests still pass unchanged; no change to runtime model outputs (TUHO DSCR 1.451 / Oborovo 1.15 unaffected — export is downstream).

## Guardrails

G20 BLOCKED; R99/R102 NOT APPROVED; `partial_pay_sweep` not promoted; flat/min DSCR sculpting not promoted; backend source of truth. Phase 49A itself makes no behavior or formula changes; this document is a plan for 49B.
