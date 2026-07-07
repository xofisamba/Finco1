# Sprint 12 - Canonical Financial Statements Runtime Integration

## Root Cause

The canonical Financial Statements payload was already assembled by the backend run path as read-only output from the completed waterfall result, but the runtime Financial Statements sheet did not receive that payload through the server-rendered run context. The sheet therefore depended on the older sessionStorage-only fallback and rendered the pre-run unavailable state unless client-side hydration filled it later.

## Fix Summary

- Threaded `financial_statements` through all successful run-service outcomes.
- Passed `financial_statements` into the active Financial Statements sheet OOB render after Run.
- Server-rendered Income Statement, Balance Sheet, and PF Cash Waterfall tables from the canonical runtime payload when available.
- Preserved sessionStorage as a same-run HTMX refresh fallback only.
- Kept the pre-run state explicit: "No model results available. Run the model to generate financial statements."
- Removed developer source copy from rendered HTML while retaining canonical runtime source attribution.

## Changed Files

- `app/services/run_service.py`
- `main_web.py`
- `app/templates/partials/sheet_financials.html`
- `tests/test_sprint12_financial_statements_runtime_integration.py`
- `tests/test_excel_parity_stack_d.py`
- `tests/test_phase20m_runtime_statement_polish.py`
- `reports/sprint12_financial_statements_runtime_integration/report.md`
- `reports/sprint12_financial_statements_runtime_integration/pre_run_financial_statements.html`
- `reports/sprint12_financial_statements_runtime_integration/post_run_financial_statements.html`

## Runtime Binding Map

| Surface | Source |
| --- | --- |
| Income Statement | `result["financial_statements"]["pnl"]["periods"]` |
| Balance Sheet | `result["financial_statements"]["balance_sheet"]["periods"]` |
| PF Cash Waterfall | `result["financial_statements"]["pf_cash_waterfall"]["periods"]` |
| Active sheet OOB refresh | `outcome.context["financial_statements"]` |
| Same-run fallback | `sessionStorage.lastFinancialStatements` |

## Route Matrix Result

| Route / Surface | Result |
| --- | --- |
| POST `/run` user-created path | `financial_statements` in context |
| POST `/run` template-seeded path | `financial_statements` in context |
| POST `/run` generic path | `financial_statements` in context |
| Financial Statements OOB sheet refresh | receives canonical payload |
| Route smoke suite | green |

## Tests

- `tests/test_sprint12_financial_statements_runtime_integration.py`
- `tests/test_excel_parity_stack_d.py`
- `tests/test_ui8g_consistency_guardrails.py`
- `tests/test_phase57pre_route_render_smoke.py`
- `py_compile` for changed Python files

Result: 107 passed, 17 skipped for the focused runtime/parity/route set.

Known unrelated legacy signal: `tests/test_phase20m_runtime_statement_polish.py` now has no Sprint 12 Financial Statements failure, but still contains older nested failures in scenario compare, OPEX/revenue legacy grid expectations, and CSS parser checks.

## Evidence Path

Rendered evidence artefacts:

- `reports/sprint12_financial_statements_runtime_integration/pre_run_financial_statements.html`
- `reports/sprint12_financial_statements_runtime_integration/post_run_financial_statements.html`

PNG screenshots were attempted through the local Python Playwright path and the in-app browser path. Python Playwright is not installed in this environment, and the in-app browser blocks `file://` evidence navigation by policy, so the committed evidence is HTML-only.

## Confirmations

- No model changes.
- No formula changes.
- No persistence changes.
- No schema changes.
- No export changes.
- No waterfall, tax, debt, CAPEX, OPEX, or revenue engine changes.
- No frontend financial calculations.
