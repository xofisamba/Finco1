# Sprint 13 PR D - Export Metadata Wording

## Root cause

Export CSV/workbook metadata still exposed the historical label `runtime_or_preview`, and the institutional workbook binding status CSV exposed `remaining_placeholders`. The underlying values were already evidence classifications, but the column names used pilot-era wording that is not suitable for lender-facing export metadata.

## Scope

Export metadata label cleanup only.

No workbook calculations, runtime values, financial statements, export formulas, persistence, schema, or model behavior changed.

## Files changed

- `app/export/runtime_summary.py`
- `app/export/institutional_workbook.py`
- `app/export/registry.py`
- `tests/test_sprint13_institutional_reporting_wording.py`

## Changes

- Renamed exported metadata key `runtime_or_preview` to `runtime_or_evidence`.
- Renamed exported binding-status key `remaining_placeholders` to `remaining_evidence_gaps`.
- Preserved existing evidence values such as `runtime`, `review`, and `audit`.
- Added guardrail coverage to keep the old export-facing keys out of Sprint 13 reporting source files.

## Tests

Command:

`python -m pytest tests/test_sprint13_institutional_reporting_wording.py tests/test_phase10_institutional_workbook_skeleton.py tests/test_excel_export.py -q --tb=short`

Result:

`89 passed`

## Route matrix result

No route behavior changed. This PR touches export metadata labels and reporting wording tests only.

## Screenshot / evidence path

Evidence report:

`reports/sprint13_institutional_validation/pr_d_export_metadata_wording.md`

## Institutional readiness score

90 / 100 for export metadata wording.

Remaining work: generated artifact screenshot/workbook capture in the full Sprint 13 QA bundle.

## Confirmations

- No model changes.
- No formula changes.
- No runtime calculation changes.
- No persistence changes.
- No schema changes.
- No financial statement engine changes.
- No parity target changes.
