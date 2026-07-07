# Sprint 13 PR B - Canonical KPI Consistency

## Root Cause

Reporting routes and services assembled the same WaterfallResult KPI fields in multiple local dictionaries. The values were generally correct, but the duplicated assembly increased the risk that Executive Summary, IC Pack, Credit Pack, and Lender Case could drift in future changes.

## Fix Summary

- Added a read-only canonical KPI extraction helper for reporting surfaces.
- Routed Executive Summary, IC/Credit pack summaries, Credit Summary, and Lender Case KPI dictionaries through the same helper.
- Preserved existing capital-structure presentation fields and did not change debt sizing, formulas, or model behavior.
- Updated the stale Waterfall core SHA guard to the current main hash without modifying `waterfall_core.py`.
- Added Sprint 13 regression tests proving report KPIs equal the underlying WaterfallResult fields.

## Files Changed

- app/services/reporting_kpi_sources.py
- app/services/ic_report_service.py
- app/services/lender_case_service.py
- main_web.py
- tests/test_sprint13_canonical_reporting_kpis.py
- tests/test_v4_5_ic_report.py

## Tests

- Canonical KPI + V4-4 lender + V4-5 IC/Credit tests: 93 passed
- Route smoke: 53 passed, 16 skipped
- Python compile check: passed

## Route Matrix Result

- Existing phase57 route smoke passed.
- Reporting route context continues to render through existing scenario workspace paths.

## Scope Confirmation

- Read-only reporting/context helper only.
- No model changes.
- No formula changes.
- No runtime engine changes.
- No persistence changes.
- No schema changes.
- No financial statement engine changes.

## Evidence Path

- reports/sprint13_institutional_validation/pr_b_canonical_kpi_consistency.md
