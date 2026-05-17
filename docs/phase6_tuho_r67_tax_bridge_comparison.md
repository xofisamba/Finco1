# Phase 6 TUHO R67 Tax Bridge Comparison Workbook

## Purpose

This branch adds a human-readable Excel workbook for reviewing the remaining
TUHO R67 tax bridge difference from COD through the operating horizon.

Workbook:

`reports/phase6_tuho_r67_tax_bridge_comparison.xlsx`

The workbook is diagnostic/reporting only. It does not change runtime formulas,
does not accept R99/R102 as runtime source, does not enable SHL FCF, and does
not opt in factories.

## Workbook Sheets

| Sheet | Purpose |
| --- | --- |
| Summary | Total Excel R67, legacy Python R67, tax bridge R67, residual, material period count, max delta, interpretation. |
| Period Comparison | 60-period R67 bridge with cumulative delta and material flag. |
| Taxable Income Bridge | Python tax bridge components: revenue, OPEX, EBITDA, depreciation, senior/SHL interest, R34, losses, taxable profit, CIT, cash tax. |
| Excel vs Python Upstream Rows | Side-by-side upstream P&L rows where committed fixture data exists. Full Excel loss rows R36-R38 are left blank because they are not yet extracted. |
| Largest Deltas | R67 periods sorted by absolute delta descending. |
| Suspected Causes | Material-period suspected driver, evidence, and proposed owner module. |
| Notes | Limitations and runtime-source warning. |

## Key Totals

| Measure | Total kEUR |
| --- | ---: |
| Excel R67 target | -38,240.9 |
| Python legacy R67 | -20,140.2 |
| Python tax bridge R67 | -36,091.6 |
| Residual | +2,149.3 |

## Top Period Deltas

| op_idx | Period end | Excel R67 | Python R67 | Delta | Initial interpretation |
| ---: | --- | ---: | ---: | ---: | --- |
| 25 | 2042-12-31 | -120.2 | -945.8 | -825.6 | Early taxable-period overpayment after opening loss bucket clears. |
| 59 | 2059-12-31 | -2,999.9 | -2,521.1 | +478.7 | Late-horizon underpayment. |
| 57 | 2058-12-31 | -2,984.2 | -2,513.7 | +470.5 | Late-horizon underpayment. |
| 55 | 2057-12-31 | -2,948.6 | -2,485.9 | +462.7 | Mid-horizon tax-basis underpayment. |
| 53 | 2056-12-31 | -2,909.4 | -2,454.2 | +455.2 | Mid-horizon tax-basis underpayment. |
| 49 | 2054-12-31 | -2,795.5 | -2,340.5 | +455.0 | Mid-horizon tax-basis underpayment. |
| 47 | 2053-12-31 | -2,741.4 | -2,292.9 | +448.6 | Mid-horizon tax-basis underpayment. |
| 51 | 2055-12-31 | -2,856.9 | -2,408.8 | +448.1 | Mid-horizon tax-basis underpayment. |
| 45 | 2052-12-31 | -2,688.1 | -2,245.7 | +442.4 | Mid-horizon tax-basis underpayment. |
| 43 | 2051-12-31 | -2,614.3 | -2,177.8 | +436.5 | Mid-horizon tax-basis underpayment. |

## Interpretation

The workbook reinforces the existing R99 readiness decision: R99 remains
blocked. The residual is smaller than the original R67 gap, but it still has
material period-level deltas and mixed signs. The next diagnostic branch should
assign owner modules for remaining tax-basis rows and unextracted Excel loss
rows before R99 runtime-source promotion.

Recommended next branch:

`phase6-tax-bridge-tax-basis-row-ownership`
