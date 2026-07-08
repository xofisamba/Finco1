# Sprint 13 PR E - Institutional Route Matrix

## Root cause

Sprint 13 requires evidence that lender/report/export surfaces are populated across TUHO, Oborovo, Generic Solar, and Generic Wind. Playwright/Chromium is not installed in this local environment, so browser screenshots cannot be produced honestly here. A backend route matrix was added to protect the same core institutional failure modes: HTTP 500s, blank responses, blank visible HTML, and visible developer wording.

## Scope

Test and evidence only.

No UI templates, runtime behavior, model calculations, persistence, schema, export generation logic, or financial statement engine code changed.

## Files changed

- `tests/test_sprint13_institutional_route_matrix.py`
- `reports/sprint13_institutional_validation/pr_e_institutional_route_matrix.md`

## Route matrix

Projects:

- TUHO
- Oborovo
- Generic Solar
- Generic Wind

Routes:

- `/`
- `/scenarios/exec-summary`
- `/scenarios/ic-pack`
- `/scenarios/credit-pack`
- `/scenarios/credit-summary`
- `/scenarios/lender-case`
- `/scenarios/compare`
- `/exports/runtime-summary.csv`
- `/exports/institutional-workbook.xlsx`

Checks:

- No HTTP 500.
- No blank response.
- No blank visible HTML text for HTML routes.
- No visible `TODO`, `placeholder`, `demo`, `temporary`, `preview-only`, or `Coming Soon`.

## Tests

Command:

`python -m pytest tests/test_sprint13_institutional_route_matrix.py -q --tb=short`

Result:

`36 passed, 1 skipped`

The skipped test documents that Playwright/Chromium is unavailable in the current local environment.

## Screenshot / evidence path

No screenshot files were produced because Playwright is not installed. This is explicitly documented by the skipped dependency-status test.

Evidence report:

`reports/sprint13_institutional_validation/pr_e_institutional_route_matrix.md`

## Institutional readiness score

86 / 100 for backend route coverage.

Remaining work: rerun the same matrix with Playwright/Chromium installed to capture visual screenshots.

## Confirmations

- No model changes.
- No formula changes.
- No runtime calculation changes.
- No persistence changes.
- No schema changes.
- No export generation changes.
- No financial statement engine changes.
- No parity target changes.
