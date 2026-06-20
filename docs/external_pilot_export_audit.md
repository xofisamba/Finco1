# External Pilot Export Terminology Audit

Scope: search exported workbook/CSV outputs for factory/baseline/golden/
`create_default_`/calibration wording or sentinel leakage, across both
TUHO and Oborovo.

## Findings

### 1. Runtime-summary CSV leaks raw sentinel values (highest priority, NEW)

`build_runtime_summary_rows()` (`app/export/runtime_summary.py`) writes
the raw internal sentinel strings directly into the `runtime_origin` and
`template_origin` CSV columns with **no display mapping applied**:

- `factory_base_runtime`
- `project_factory:tuho`
- `project_factory:oborovo`

These reach the actual downloadable CSV bytes for both TUHO and Oborovo
(12 rows per project, both sentinel columns populated in every row — up to
24 raw occurrences per project across the two columns). This is a
button-click download with no audit-mode gate, so it is classified
**(A) user-facing** and is the single highest-priority remaining
terminology leak in the export surface.

This is the exact same pattern already fixed for the institutional
workbook (XLSX) export in PR #686 via `_display_runtime_origin()` /
`_display_template_origin()` helpers in
`app/export/institutional_workbook.py`. The fix was never carried over to
the CSV export path.

**Recommended fix (no code yet, documented for the implementation plan):**
apply the same `_display_runtime_origin` / `_display_template_origin`
style mapping at the row-construction boundary in
`build_runtime_summary_rows()`, translating only at the point CSV rows are
written. The underlying sentinel values must remain unchanged everywhere
they are produced (provenance/replay machinery in
`app/persistence/provenance.py` is a system of record and must not be
touched).

### 2. Hardcoded "Factory-bound" prose in the Calibration Reconciliation pack

`app/export/calibration_reconciliation.py` (~line 1404) hardcodes the
literal string `"Factory-bound base runtime"` directly into cell `B6` of
the "Calibration Reconciliation Workbook" export pack. This is hand-authored
display text, not a sentinel passthrough. Lower priority than finding #1
(this export card is currently disabled/"Coming Soon" in the registry per
the terminology audit), but still internal-sounding jargon that would
reach lender/audit-facing text once enabled.

### 3. Institutional workbook (XLSX) — already clean

Confirmed zero "factory" substrings in any generated cell across both
TUHO and Oborovo institutional workbooks (fixed in PR #686, re-verified
via `tests/test_u9_remaining_terminology_cleanup.py`
`TestInstitutionalWorkbookNoFactoryWording`).

### 4. `app/excel_export.py` liveness check

Confirmed this module is live, not dead code: `main_web.py` imports
`build_excel_export` directly, and `app/services/export_service.py`
(lines ~93, 97, 280, 290) calls it for both POST and GET download paths
wired into `main_web.py` (~lines 2843/2894). Any future terminology fix in
this module needs the same scrutiny as the other live export paths — it
has not yet been audited for factory/baseline wording in this pass and
should be added to the implementation plan's checklist.

## Summary table

| Export surface | Status | Priority |
|---|---|---|
| Institutional workbook (XLSX) | Clean (PR #686) | — |
| Runtime-summary CSV | Leaks raw sentinels | **High** |
| Calibration Reconciliation pack (disabled) | Hardcoded "Factory-bound" text | Medium (fix before enabling) |
| `app/excel_export.py` path | Not yet audited | To be scheduled |
