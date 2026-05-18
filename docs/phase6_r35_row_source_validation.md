# Phase 6 R35 Row Source Validation

## Purpose

This diagnostic branch validates whether the prior TUHO R35 row attribution deltas are real model-source differences or artifacts caused by period alignment, sign convention, or workbook mapping.

Runtime behavior changed: no. The branch creates a human-readable validation workbook only and does not change tax, SHL, depreciation, R99/R102, or factory behavior.

Workbook:

```text
reports/phase6_tuho_r35_source_validation.xlsx
```

## Executive Finding

The prior R35 attribution is valid, with an important interpretation: the largest deltas are real row-source ownership gaps, not date, sign, or attribution artifacts.

| Validation area | Result |
| --- | --- |
| op_idx/date alignment | All 60 operating periods align |
| H1/H2 ordering | Matches between Excel fixture and Python |
| Sign normalization | Correct for revenue, expenses, R34, and R35 |
| R34 fiscal reintegration | Calibrated; cumulative delta is approximately zero |
| SHL interest delta | Real gross-accrued source gap, not a sign/date artifact |
| Depreciation delta | Real book-versus-tax row ownership gap |

## Key Totals

| Driver | Validated total delta |
| --- | ---: |
| R35 total delta | +12,216.4 kEUR |
| SHL interest delta | +10,347.3 kEUR |
| Depreciation delta | +2,302.2 kEUR |
| OPEX/local-tax/minor row delta | -733.5 kEUR |
| Senior interest delta | +355.4 kEUR |
| R34 fiscal reintegration delta | 0.0 kEUR |
| Other residual | -55.0 kEUR |

## Workbook Structure

The workbook contains:

- `Summary`
- `Period Alignment`
- `Sign Convention`
- `Revenue Check`
- `OPEX Check`
- `Depreciation Check`
- `Senior Interest Check`
- `SHL Interest Check`
- `R34 Check`
- `R35 Reconstruction`
- `Largest Deltas`

## Period Alignment

The `Period Alignment` sheet compares Excel and Python operating periods across all 60 operating periods.

Result: all periods match.

| Check | Result |
| --- | --- |
| op_idx sequence | 0 through 59 in both sources |
| period start | Matched |
| period end | Matched |
| H1/H2 ordering | Matched |
| COD offset | No mismatch detected in the operating-period bridge |

This rules out period shift as the explanation for the prior R35 attribution.

## Sign Convention

The `Sign Convention` sheet verifies that workbook values and Python values are normalized consistently:

| Row | Result |
| --- | --- |
| R8 Revenue | Positive income, no sign issue |
| R10 OPEX | Normalized to negative expense |
| R13 Depreciation | Normalized correctly, but source is a book/tax gap |
| R24 Senior Interest | Normalized correctly, small source gap remains |
| R27 SHL Interest | Normalized correctly, large gross-accrued source gap remains |
| R30 Financial Earnings | Normalized correctly |
| R32 EBT | Follows upstream row sources |
| R34 Fiscal Reintegration | Sign and source calibrated |
| R35 Taxable Income | Reconstructs from R32 + R34 |

This rules out sign convention as the source of the R35 residual.

## Gross Versus Net SHL Interest

The `SHL Interest Check` sheet compares:

- Excel P&L R27 gross SHL interest;
- the independent interest-limitation fixture R27 gross SHL interest;
- Python `shl_interest_keur`;
- Python cash SHL interest;
- Python PIK;
- Python total SHL service.

Finding: the +10,347.3 kEUR SHL delta is real. Excel P&L R27 uses a gross accrued SHL interest schedule. The Python field used in the current attribution does not reproduce that gross accrued schedule across the horizon.

The first operating period is the clearest example:

| Item | Value |
| --- | ---: |
| Excel P&L R27 gross SHL interest | -1,297.4 kEUR |
| Excel interest-limitation fixture R27 | -1,297.4 kEUR |
| Python `shl_interest_keur` expense | 0.0 kEUR |
| Delta | +1,297.4 kEUR |

Conclusion: this is not a gross/net sign artifact. It is a row ownership gap. The next implementation work should isolate gross accrued SHL interest for P&L/tax bridge use, separate from SHL cash waterfall mechanics.

## Book Versus Tax Depreciation

The `Depreciation Check` sheet compares:

- Excel P&L R13 book depreciation;
- Excel depreciation sheet R30 book depreciation;
- Excel depreciation sheet R31 tax depreciation proxy;
- Python depreciation used in the current tax bridge attribution.

Finding: the +2,302.2 kEUR depreciation delta is real. Python currently has tax depreciation audit visibility, but the P&L bridge needs book depreciation for EBT construction. This is an expected missing book/tax layer, not evidence that the R34 engine is wrong.

The first operating period shows the pattern:

| Item | Value |
| --- | ---: |
| Excel P&L R13 book depreciation | -1,845.4 kEUR |
| Python depreciation used | -1,168.5 kEUR |
| Delta | +676.9 kEUR |

Conclusion: depreciation needs explicit book/tax row ownership. P&L should consume book depreciation; the tax bridge should consume tax depreciation and explicit tax adjustments.

## Revenue, OPEX, And Senior Interest

Revenue is effectively aligned. OPEX has a smaller -733.5 kEUR cumulative grouping/local-tax/minor-row difference. Senior interest has a smaller +355.4 kEUR source/timing residual.

These do not explain the primary R35 gap, but they should remain visible in the row ownership matrix.

## R34 Validation

The `R34 Check` sheet confirms that Excel R34 and Python fiscal reintegration match across the 60-period bridge.

| Metric | Result |
| --- | ---: |
| Cumulative R34 delta | Approximately 0.0 kEUR |
| Max meaningful R34 source issue | None detected |

Conclusion: R34 is calibrated. The remaining R35 gap is upstream of R34 or in the P&L taxable-income source rows.

## R35 Reconstruction

The workbook reconstructs:

```text
Excel R35 = Excel R32 + Excel R34
Python R35 = validated Python-equivalent components
```

The reconstruction confirms:

```text
R35 delta =
  revenue delta
+ OPEX delta
+ depreciation delta
+ senior interest delta
+ SHL interest delta
+ R34 delta
+ other residual
```

The largest single-period deltas are:

| op_idx | R35 delta | Suspected driver |
| ---: | ---: | --- |
| 0 | +2,024.9 kEUR | SHL interest field mapping/accrual |
| 23 | +1,506.3 kEUR | SHL interest field mapping/accrual |
| 21 | +1,426.8 kEUR | SHL interest field mapping/accrual |
| 59 | -1,340.7 kEUR | book vs tax depreciation mapping |
| 58 | -1,318.9 kEUR | book vs tax depreciation mapping |

## Decision

The previous attribution is valid. The branch changes the interpretation from "possible attribution issue" to "confirmed source ownership gap."

Confirmed drivers:

1. Gross accrued SHL interest needs a dedicated P&L/tax bridge source.
2. Book depreciation and tax depreciation need separate row ownership.
3. R34 fiscal reintegration is not the remaining blocker.
4. R99/R102 remains blocked until R35 source ownership and loss/tax timing gates are resolved.

## Recommended Next Branch

`phase6-shl-gross-interest-pnl-bridge`

Recommended scope:

- create an offline/default-off gross accrued SHL interest bridge;
- compare Excel P&L R27 against Python SHL cash, PIK, and gross-accrual candidates;
- keep SHL FCF waterfall and R99/R102 runtime source blocked;
- avoid project factory opt-in and runtime formula changes.
