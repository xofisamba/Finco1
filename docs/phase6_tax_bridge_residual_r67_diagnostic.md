# Phase 6 Tax Bridge Residual R67 Diagnostic

## Purpose

This branch diagnoses the remaining TUHO R67 cash-tax residual after the tax
bridge consumes:

- R34 fiscal reintegration from the interest limitation engine
- 5-year rolling FIFO loss carry-forward
- annual H2 cash-tax pairing

It is diagnostics only. It does not accept R99/R102 as a runtime source, does
not enable SHL FCF, does not opt in factories, and does not change formulas.

## Current R67 Position

| Measure | Total kEUR |
| --- | ---: |
| Excel R67 target | -38,240.9 |
| Legacy runtime cash tax | -20,140.2 |
| TUHO flag-on with R34 + rolling losses | -36,091.6 |
| Remaining residual | +2,149.3 |

Positive residual means Python is still paying less cash tax than Excel on a
full-horizon basis.

## Period Bridge Fields

The diagnostic test builds a 60-period bridge with:

- Excel R67
- Python flag-on R67
- delta
- taxable income before losses
- R34
- losses used
- taxable profit
- CIT
- cash-tax timing label

Key observed periods:

| op_idx | Excel R67 | Python R67 | Delta | Interpretation |
| ---: | ---: | ---: | ---: | --- |
| 25 | -120.2 | -945.8 | -825.6 | Python taxes earlier / higher in the first taxable H2 period. |
| 27 | -955.2 | -1,202.0 | -246.7 | Early taxable-period overpayment persists. |
| 35 | -1,644.9 | -1,874.3 | -229.3 | Still overpaying versus Excel in a mid-horizon H2 period. |
| 57 | -2,984.2 | -2,513.7 | +470.5 | Late horizon underpayment versus Excel. |
| 59 | -2,999.9 | -2,521.1 | +478.7 | Late horizon underpayment persists. |

## Residual Attribution

| Component / period band | Delta kEUR | Reading |
| --- | ---: | --- |
| op_idx 24-37 first taxable periods | -2,181.6 | Python overpays tax versus Excel after the rolling loss bucket starts clearing. This points to opening tax-loss age and taxable-basis timing differences. |
| op_idx 38-56 mid horizon | +3,381.7 | Python underpays tax versus Excel. This points to remaining book-vs-tax basis differences, local tax / minor tax rows, and period-boundary effects. |
| op_idx 57-59 final periods | +949.2 | Late-period Python underpayment remains material. |
| Net residual | +2,149.3 | Mixed over/under pattern; not a simple cash-tax timing plug. |

The bridge has 18 material periods with absolute deltas above 100 kEUR. The
sign changes across the horizon, so a scalar R99/R102 adjustment would hide
real period-level mismatches.

## Candidate Causes

### Opening Tax-Loss Bucket Age

The rolling loss engine currently treats the opening 25,000 kEUR tax loss as
available for a full 5-year window from COD. Excel may be aging construction
period losses from their original generation date. This can move the first
taxable periods materially.

### Annual H2 Pairing Convention

The branch already uses annual H2 pairing. Because the residual is mixed by
period and not purely a H1/H2 shift, payment timing is no longer the dominant
gap.

### Book vs Tax Depreciation / Tax Basis

Prior diagnostics showed a tax-basis gap remains. The residual pattern after
R34 and rolling losses still points to basis/timing differences rather than a
runtime cashflow issue.

### Local Tax / WHT / Minor Tax Rows

Excel CF rows may include minor tax or reserve-interest effects that are not
owned by the current tax bridge. These are smaller than the original R67 gap but
can explain part of the remaining 2.1m kEUR.

### Rounding / Period Boundary

Small rounding and period-boundary effects are present, but the residual is too
large and too patterned to classify as rounding only.

## Recommendation

Do not accept R99/R102 as a runtime source yet.

The residual is much smaller than the original tax gap, but the period-level
bridge still shows 18 material period deltas and mixed signs. Proceeding to a
production R99 source would bury unresolved tax-basis and opening-loss-age
behavior inside SHL/distribution results.

Recommended next step:

`phase6-tax-bridge-residual-r67-fix-design`

That branch should decide whether to:

1. age opening construction losses from their original generation dates,
2. add remaining Excel tax-basis rows to the bridge,
3. map local tax / WHT / minor tax rows, or
4. explicitly document the residual as a non-blocking limitation with a tighter
   tolerance gate.
