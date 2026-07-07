# Sprint 13 PR A - Reporting Wording Hardening

## Root Cause

Several lender-facing report and export surfaces still used legacy delivery wording such as "preview", "internal", "placeholder", "hardcoded", "not yet available", and "coming soon". The underlying data sources were already runtime/export-authoritative, but the presentation language was not institutional enough for lender or IC review.

## Fix Summary

- Replaced legacy workbook/export labels with institutional evidence wording.
- Renamed visible OPEX audit column from "Is Hardcoded" to "Fixed Assumption".
- Reworded portfolio sponsor IRR disclosure as unavailable evidence instead of placeholder/experimental language.
- Reworded Export Registry disabled-card copy from "Coming Soon / not yet available" to "Unavailable / outside current package".
- Added Sprint 13 guardrail coverage so removed lender-facing terms do not regress in the targeted reporting files.
- Updated stale terminology tests to read UTF-8 templates consistently on Windows.

## Files Changed

- app/excel_export.py
- app/export/institutional_workbook.py
- app/export/registry.py
- app/templates/partials/export_registry.html
- tests/test_excel_export.py
- tests/test_phase10_institutional_workbook_skeleton.py
- tests/test_u9_remaining_terminology_cleanup.py
- tests/test_sprint13_institutional_reporting_wording.py

## Tests

- Targeted wording/export tests: 24 passed
- Route smoke + institutional workbook + wording/export set: 84 passed, 17 skipped
- Python compile check: passed

## Route Matrix Result

- Route smoke passed across the existing phase57 pre-route matrix.
- Export Registry route rendered without forbidden wording regressions.

## Scope Confirmation

- Presentation/report/export wording only.
- No model changes.
- No formula changes.
- No runtime engine changes.
- No persistence changes.
- No schema changes.
- No financial statement engine changes.

## Evidence Path

- reports/sprint13_institutional_validation/pr_a_reporting_wording_hardening.md
