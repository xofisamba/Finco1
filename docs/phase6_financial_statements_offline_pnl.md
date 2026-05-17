# Phase 6 Financial Statements Offline P&L

## Purpose

This branch adds Stage 2 of the financial statements assembly layer: an offline P&L generator and tax bridge audit. It assembles human-readable statement rows from existing `WaterfallResult` and `WaterfallPeriod` fields. It does not become a runtime source of truth and does not change waterfall, tax, revenue, OPEX, debt, SHL, R99/R102, sponsor, UI, cache, or project factory behavior.

## Package Structure

`domain/financial_statements/` contains:

- `assembly.py`: top-level `assemble_financial_statements(...)` entry point.
- `pnl.py`: offline P&L row assembly from waterfall period fields.
- `tax_bridge.py`: audit-only tax bridge from existing tax audit fields.
- `retained_earnings.py`: retained earnings movement helper.
- `result.py`: `PnLPeriodResult`, `PnLStatementResult`, `TaxBridgePeriodResult`, `TaxBridgeResult`, and `FinancialStatementsResult`.
- `inputs.py`: `FinancialStatementsConfig`.
- `excel_mapping.py`: P&L row mapping for Excel rows R8-R50.
- `templates/croatia.py`: Croatia metadata: 18% CIT, semiannual periods, annual H2 cash-tax diagnostic convention, and 5-year loss carry-forward metadata.

The package deliberately has no `app` imports.

## P&L Row Source Owners

| Excel row | Component | Source owner |
|---|---|---|
| R8 | Revenues | `WaterfallPeriod.revenue_keur` |
| R10 | Operating expenses | `WaterfallPeriod.opex_keur`, presented negative |
| R11 | Local tax | Placeholder, currently 0 |
| R12 | WHT on interests | Placeholder, currently 0 |
| R13 | Depreciation | `WaterfallPeriod.tax_depreciation_audit_keur`, presented negative |
| R14 | Total expenses | Assembled subtotal |
| R16 | EBIT | Assembled subtotal |
| R19-R21 | Financing income / WHT | Placeholders, currently 0 |
| R24 | Senior interest | `WaterfallPeriod.senior_interest_keur`, presented negative |
| R25-R26 | Refinancing / junior interest | Placeholders, currently 0 |
| R27 | SHL interest | `WaterfallPeriod.shl_interest_keur`, presented negative |
| R28 | Interest on cash | Placeholder, currently 0 |
| R30 | Financial earnings | Assembled subtotal |
| R32 | EBT | Assembled subtotal |
| R34 | Fiscal reintegration | `WaterfallPeriod.fiscal_reintegration_audit_keur` |
| R35 | Taxable income before losses | `WaterfallPeriod.taxable_income_before_losses_audit_keur` |
| R36 | Losses N-1 | `WaterfallPeriod.tax_loss_opening_audit_keur`, presented negative |
| R37 | Allocated losses | `WaterfallPeriod.tax_loss_used_audit_keur` |
| R38 | Losses N | `WaterfallPeriod.tax_loss_closing_audit_keur`, presented negative |
| R39 | Carriable losses | `WaterfallPeriod.tax_loss_closing_audit_keur`, presented negative |
| R41 | Taxable profit N | `WaterfallPeriod.taxable_profit_after_losses_audit_keur` |
| R43 | CIT accrual | `WaterfallPeriod.cit_accrual_audit_keur`, presented negative |
| R44 | Excel-style H2 cash-tax diagnostic | `WaterfallPeriod.cash_tax_excel_style_h2_diagnostic_keur` |
| R46 | Net income | Assembled subtotal |
| R48 | Legal reserve | Placeholder, currently 0 |
| R49 | Retained earnings | Cumulative `net income - dividends` |
| R50 | Net dividends | `WaterfallPeriod.distribution_keur`, presented negative |

## Assembled vs Calculated

This layer assembles statement presentation rows from existing model outputs. It does calculate presentation subtotals, such as total expenses, EBIT, EBT, net income, and retained earnings movement. Those subtotals are report assembly arithmetic only; they do not feed the model.

It does not recalculate revenue, OPEX, debt service, SHL service, tax payable, construction balances, R99/R102, or distributions.

## Sign Convention

Income rows are positive. Expenses, interest costs, tax charges, loss balances, and dividends are presented as negative where that improves P&L readability. The tax bridge keeps the underlying audit fields in their native positive-value convention, except for the existing Excel-style H2 cash-tax diagnostic, which is already an Excel cash-flow outflow.

## TUHO P&L Bridge

TUHO P&L rows are generated for every waterfall period. The current branch validates that key rows read directly from the existing waterfall outputs:

- revenue from `revenue_keur`
- operating expenses from `opex_keur`
- depreciation from tax audit depreciation
- senior interest from `senior_interest_keur`
- SHL interest from `shl_interest_keur`
- dividends from `distribution_keur`

Known TUHO gaps remain in statement-row equivalence because some Excel P&L rows are not yet exposed as runtime fields, including detailed local tax, financing income, WHT, legal reserve, and Excel-specific fiscal reintegration presentation.

## Oborovo P&L Bridge

Oborovo uses the same offline assembly path and generates a full period set without enabling any TUHO-specific R99 or SHL waterfall behavior. Oborovo rows are produced from the same existing waterfall fields and placeholders.

## Tax Bridge

The tax bridge exposes existing audit fields period by period:

- tax depreciation
- fiscal reintegration
- taxable income before losses
- opening tax loss
- loss used
- closing tax loss
- taxable profit after losses
- CIT accrual
- current period cash tax
- Excel-style annual H2 cash-tax diagnostic

The bridge keeps `r99_runtime_source_accepted=False`. It does not accept any runtime R99/R102 source and does not enable SHL FCF waterfall.

## Known Gaps

- This stage is P&L-only. It intentionally excludes Balance Sheet and PF Cash Waterfall assembly.
- Several Excel P&L rows remain placeholders because the runtime does not yet expose equivalent granular rows.
- Tax basis mapping remains diagnostic-only. No tax formula changes are included.
- The Excel-style H2 cash-tax diagnostic remains audit-only and is not used in runtime cash routing.

## Runtime Safety

The assembly package reads a completed `WaterfallResult` and returns immutable result dataclasses. It does not mutate the waterfall result, add project flags, change factories, or feed any model formula.

## Next Branch

Recommended next branch:

`phase6-financial-statements-balance-sheet-and-cf`

That branch should add Balance Sheet balance checks and PF Cash Waterfall rows R69/R84/R99/R102 using the same offline assembly discipline.
