# Phase 6 Financial Statements Balance Sheet and PF Cash Waterfall

## Purpose

This branch adds Stage 3 of the financial statements assembly layer: offline Balance Sheet and PF Cash Waterfall assembly. It remains a downstream reconciliation layer. It reads `WaterfallResult`, Stage 2 P&L, and existing audit fields, then returns immutable statement results.

No runtime formula changes are included.

## Added Assemblers

- `domain/financial_statements/balance_sheet.py`
- `domain/financial_statements/pf_cash_waterfall.py`

The top-level `assemble_financial_statements(...)` now returns:

- `pnl`
- `tax_bridge`
- `balance_sheet`
- `pf_cash_waterfall`

## Balance Sheet Assembly

The Balance Sheet bridge creates one `BalanceSheetPeriodResult` for each waterfall period.

| Row family | Source |
|---|---|
| Gross fixed assets | Placeholder equal to accumulated depreciation until capex ledger is exposed |
| Accumulated depreciation | Cumulative Stage 2 P&L depreciation |
| Net fixed assets | Gross fixed assets minus accumulated depreciation |
| DSRA | `WaterfallPeriod.dsra_balance_keur` |
| J-DSRA | Placeholder, currently 0 |
| Distribution account | `WaterfallPeriod.r100_carryforward_keur` |
| Cash | Derived residual balancing line |
| Share capital | Placeholder, currently 0 because not exposed on `WaterfallResult` |
| Legal reserve | Stage 2 P&L legal reserve placeholder |
| Retained earnings | Stage 2 P&L retained earnings |
| SHL balance | `WaterfallPeriod.shl_balance_keur` |
| Junior balance | Placeholder, currently 0 |
| Senior balance | `WaterfallPeriod.senior_balance_keur` |
| Refinancing / short-term loan | Placeholder, currently 0 |
| Balance check | Total assets minus total liabilities and equity |

Cash is explicitly marked as residual with `cash_is_residual=True`. It is not runtime cash and does not feed any model output.

## PF Cash Waterfall Assembly

The PF Cash Waterfall bridge creates one `PFCashWaterfallPeriodResult` for each waterfall period.

| Excel row | Field | Source |
|---|---|---|
| R20 | Operating revenues | `WaterfallPeriod.revenue_keur` |
| R38 | OPEX | `WaterfallPeriod.opex_keur`, presented negative |
| R40 | EBITDA | `WaterfallPeriod.ebitda_keur` |
| R63 | Senior cash interest | `WaterfallPeriod.senior_interest_keur`, presented negative |
| R67 | Cash CIT | `WaterfallPeriod.corporate_tax_cash_keur`, presented negative |
| R69 | FCF Banks | `WaterfallPeriod.r69_fcf_banks_keur` |
| R70 | Senior debt service | `WaterfallPeriod.senior_ds_keur`, presented negative |
| R84 | FCF Junior | `WaterfallPeriod.r84_fcf_junior_keur` |
| R98 | Distribution account pre-lockup | `WaterfallPeriod.r98_distribution_account_keur` |
| R99 | FCF for distribution | `WaterfallPeriod.r99_fcf_for_distribution_keur` |
| R100 | Carryforward | `WaterfallPeriod.r100_carryforward_keur` |
| R102 | FCF for SHL | `WaterfallPeriod.r102_fcf_for_shl_keur` |
| R104 | Net SHL cash outflow | Existing SHL service fields |
| R106 | FCF for dividends | R102 less net SHL cash outflow |
| R119 | Net dividends | `WaterfallPeriod.distribution_keur` |

R99/R102 remains audit-only. The bridge never marks a runtime R99 source as accepted.

## TUHO Bridge Result

TUHO produces:

- one Balance Sheet period for every waterfall period
- one PF Cash Waterfall period for every waterfall period
- accumulated depreciation roll-forward from P&L
- senior and SHL closing balances from existing runtime fields
- R69/R84/R98/R99/R100/R102 from existing C1d audit fields
- R99/R102 identity checked from the audit fields

## Oborovo Bridge Result

Oborovo uses the same assembly path and remains independent of TUHO-specific SHL FCF or R99 runtime paths. No Oborovo factory or flag is changed.

## Balance Check Status

The current Balance Sheet uses cash as an explicit residual line while gross fixed assets and share capital are not yet statement source-of-truth fields on `WaterfallResult`. This makes the assembly balance check visible and stable without changing runtime behavior.

This is an audit bridge, not a full Balance Sheet source-of-truth migration.

## R99/R102 Status

R99 and R102 are exposed from existing C1d audit fields and checked for identity. This branch does not accept them as a runtime source and does not feed SHL FCF waterfall.

## Known Gaps and Placeholders

- Gross fixed assets await a statement-safe capex ledger input.
- Share capital is not exposed on `WaterfallResult`.
- Legal reserve remains a placeholder.
- Junior debt, refinancing, short-term loans, and J-DSRA remain placeholders.
- Cash is a residual balancing line, not runtime cash.
- PF Cash Waterfall rows use available audit fields; missing detailed Excel lines are not inferred.

## Runtime Safety

The assembly functions are pure readers. They do not mutate `WaterfallResult`, add `ProjectInfo` flags, change factories, or alter revenue, OPEX, debt, SHL, construction, tax, R99/R102, sponsor, UI, cache, or persistence logic.

## Next Branch

Recommended next branch:

`phase6-financial-statements-excel-audit-export`
