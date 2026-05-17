# Phase 6 Tax Bridge Residual R67 Final Calibration

## Purpose

This branch implements the last safe targeted calibration step before any
R99/R102 runtime-source work: explicit TUHO opening loss bucket support behind
the already default-off `use_tax_bridge_engine` path.

It does not:

- accept R99/R102 as runtime source
- enable SHL FCF
- opt in project factories
- change default behavior
- change revenue, OPEX, senior debt, SHL, or construction formulas
- rewrite tax, loss, or depreciation engines

## Opening Bucket Approach

The TUHO tax bridge flag-on path now creates an explicit opening loss bucket
instead of silently resetting the opening construction-period loss age at COD.

Current fixture assumption:

| Bucket | Amount kEUR | Remaining semiannual periods | Source label |
| --- | ---: | ---: | --- |
| TUHO construction-period opening loss | 25,000.0 | 1 | Near-expiry assumption pending full pre-COD Excel loss extract |

This preserves the known opening amount while making the age assumption explicit
and auditable. The repository still lacks a full pre-COD Excel loss-vintage
extract, so this branch does not claim final R67 parity.

## Before / After R67

| Measure | Total kEUR | Delta vs Excel |
| --- | ---: | ---: |
| Excel R67 target | -38,240.9 | 0.0 |
| Legacy runtime cash tax | -20,140.2 | +18,100.7 |
| TUHO flag-on with R34 + rolling losses + explicit opening bucket | -36,091.6 | +2,149.3 |

The explicit near-expiry opening bucket support does not materially change the
current residual because the remaining mismatch is driven by operating-period
tax basis and generated-loss timing after the initial bucket has already
expired.

## Material Period Count

| Metric | Before final calibration | After final calibration |
| --- | ---: | ---: |
| Cumulative residual | +2,149.3 | +2,149.3 |
| Periods above 100 kEUR absolute delta | 18 | 18 |
| Maximum period delta | 825.6 | 825.6 |

The calibration support is structurally useful, but the current data does not
prove a bucket age that clears the R99 gates.

## Interpretation

The result falsifies the idea that opening loss bucket aging alone is enough to
clear R67 readiness. The remaining residual still points to:

- operating-period tax basis timing
- generated operating-loss timing
- unmapped local tax / WHT / reserve-interest rows
- book/tax depreciation and minor cash-tax row ownership

A scalar residual plug remains rejected because the residual changes sign across
the horizon.

## R99 Readiness Decision

Decision: **NO, not ready for R99 runtime-source acceptance.**

Reasons:

- cumulative residual remains +2,149.3 kEUR
- 18 material periods remain above 100 kEUR absolute delta
- maximum period delta remains 825.6 kEUR
- R99/R102 would inherit the remaining tax timing and basis mismatch directly

## Next Recommendation

Recommended next branch:

`phase6-tax-bridge-tax-basis-row-ownership`

Scope should be diagnostic/targeted:

- extract pre-COD loss vintages if available
- assign owners for local tax, WHT, reserve-interest, and minor tax rows
- bridge generated operating losses period-by-period
- keep R99/R102 audit-only until R67 gates pass

Do not proceed to `phase6-r99-runtime-source-from-tax-bridge` until the R67
materiality gates are either passed or explicitly waived by policy.
