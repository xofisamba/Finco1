# Phase 6 Financial Statements Excel Audit Export

## Purpose

This branch adds Stage 4 of the financial statements assembly layer: a human-readable Excel audit export for the offline P&L, Balance Sheet, and PF Cash Waterfall statements.

The export is reporting-only. It reads an existing `FinancialStatementsResult` and writes an `.xlsx` workbook. It does not change runtime model logic, project factories, `ProjectInfo` flags, R99/R102 source acceptance, or SHL FCF waterfall behavior.

## Export Function

`domain.financial_statements.export_excel.export_financial_statements_audit_workbook(...)`

Inputs:

- `statements`: existing `FinancialStatementsResult`
- `output_path`: target `.xlsx` path
- `project_name`: optional display label
- `include_source_mapping`: optional source mapping sheet toggle, default `True`

The function returns the saved workbook path.

## Workbook Sheets

### Summary

The summary sheet contains:

- project name
- generated timestamp
- period count
- total revenue
- total OPEX
- total EBITDA
- total senior debt service
- total cash tax
- total SHL service
- total distributions
- max Balance Sheet balance check
- R99/R102 identity status
- known placeholder count

### P&L

The P&L sheet presents Stage 2 P&L rows by Excel row code, row label, source owner, one column per period, and a total column.

It includes the mapped P&L rows from R8 through R50, including revenue, OPEX, depreciation, EBIT, senior interest, SHL interest, EBT, tax bridge rows, net income, retained earnings, and dividends.

### Balance Sheet

The Balance Sheet sheet presents:

- gross fixed assets
- accumulated depreciation
- net fixed assets
- DSRA
- J-DSRA
- distribution account
- cash residual
- total assets
- share capital
- legal reserve
- retained earnings
- SHL balance
- junior balance
- senior debt
- refinancing
- short-term loan
- total liabilities and equity
- balance check

Balance check cells are highlighted when absolute value exceeds 0.01 kEUR.

### PF Cash Waterfall

The PF Cash Waterfall sheet presents:

- R20 revenue
- R38 OPEX
- R40 EBITDA
- R63 senior cash interest
- R67 cash CIT
- R69 FCF banks
- R70 senior debt service
- R84 FCF junior
- R98 distribution account pre-lockup
- R99 FCF for distribution
- R100 carryforward
- R102 FCF for SHL
- R104 net SHL cash outflow
- R106 FCF for dividends
- R119 net dividends

R99 and R102 remain audit-only rows. They are displayed for comparison but are not accepted as runtime sources.

### Source Mapping

The Source Mapping sheet lists:

- workbook sheet
- Excel row
- label
- source field
- source owner
- status
- notes

Statuses are:

- `runtime output`
- `derived`
- `placeholder`
- `residual`
- `audit-only`

Placeholder and residual rows are highlighted.

### Known Gaps

The Known Gaps sheet documents:

- gross fixed assets placeholder
- share capital placeholder
- legal reserve placeholder
- cash residual status
- R99/R102 audit-only status
- detailed Excel rows without exposed runtime fields

## Runtime Output vs Derived vs Placeholder

Runtime output rows read values already produced by `WaterfallResult`.

Derived rows are assembled from existing statement or waterfall fields, such as P&L retained earnings and Balance Sheet totals.

Placeholder rows are present for Excel statement structure but do not yet have a runtime/audit source field.

Residual rows are explicit balancing rows. The Balance Sheet cash residual is not runtime cash and does not feed any model output.

Audit-only rows expose diagnostic bridges such as R69/R84/R98/R99/R100/R102. They are not promoted to runtime source-of-truth status.

## Cash Residual Interpretation

Cash in the Balance Sheet export is an explicit residual used to make the audit Balance Sheet balance while a statement-safe capex/equity/cash ledger is still unavailable.

It should not be interpreted as model cash, distributable cash, DSRA cash, or operating cash.

## R99/R102 Warning

R99/R102 identity is shown as an audit status only. This branch does not accept R99/R102 as a runtime source and does not enable SHL FCF waterfall.

## Known Limitations

- No committed example workbook is included.
- Export tests create temporary workbooks only.
- Gross fixed assets, share capital, legal reserve, junior debt, refinancing, short-term loan, and J-DSRA remain placeholders.
- Balance Sheet cash is a residual.
- No UI/export button is added.

## Next Branch

Recommended next branch:

`phase6-tax-bridge-runtime-flag-design`
