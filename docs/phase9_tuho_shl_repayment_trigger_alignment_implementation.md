# Phase 9 TUHO SHL Repayment Trigger Alignment Implementation

## Executive Summary

This branch implements the controlled alignment path designed in PR #164. The change is narrowly scoped to TUHO SHL principal eligibility and is default-off.

The implementation does not promote R99/R102 as a runtime source, does not change DistributionAccount routing, and does not change SHL interest, PIK, WHT, senior debt, DSCR, TaxBridge, SeniorDebtSizing, Oborovo, or project factory defaults.

Observed result:

| Scenario | First SHL principal | Equity IRR | Project IRR |
|---|---:|---:|---:|
| TUHO baseline | P29 / 2044-06-30 | 11.1495% | 9.4102% |
| TUHO alignment off | P29 / 2044-06-30 | 11.1495% | 9.4102% |
| TUHO alignment on | P25 / 2042-06-30 | 11.3233% | 9.4102% |

The alignment reaches the Excel first-principal timing of P25 / 2042-06-30, but it does not make G20 pass. G20 remains BLOCKED. R99/R102 runtime promotion remains NOT approved.

## Exact Implementation Scope

Changed runtime scope:

- Added TUHO-only repayment alignment configuration fields on financing/run config.
- Passed those fields through the existing waterfall runner/core call chain.
- In `pik_then_sweep`, when the alignment is explicitly enabled and the configured eligibility period has been reached, the SHL principal sweep can begin once available cash covers the semiannual SHL interest amount.

Unchanged runtime scope:

- SHL interest formula.
- SHL PIK formula.
- WHT formula.
- Senior debt schedule and DSCR.
- DistributionAccount routing and R99/R102 source status.
- TaxBridge and SeniorDebtSizing.
- Oborovo default behavior.
- Project factories and default runtime behavior.

## Gating And Config Mechanism

New financing configuration:

- `use_tuho_shl_repayment_alignment: bool = False`
- `tuho_shl_principal_eligibility_start_period: int | None = None`

The guard is explicit:

- Default is off.
- Supported only for `TUHO-WIND-1`.
- Oborovo raises `ValueError` if the alignment path is requested.
- No project factory enables it.

The implementation uses `tuho_shl_principal_eligibility_start_period = 25` in validation to reproduce the Excel first-principal period. This is a controlled eligibility start, not a scalar plug and not an R99/R102 source promotion.

## Before Vs After Repayment Timing

Before alignment:

- First model SHL principal: P29 / 2044-06-30.
- Excel first SHL principal: P25 / 2042-06-30.
- P25-P28 were model-blocked even though Excel repaid SHL principal.

After alignment enabled:

- First model SHL principal: P25 / 2042-06-30.
- P25-P28 now have SHL principal repayments under the existing interest-first cash sweep mechanics.
- Total SHL principal repaid remains 38,028.0 kEUR in the model validation path.

## Before Vs After IRR

With the same investment-base convention:

- Baseline equity IRR: 11.1495%.
- Alignment-on equity IRR: 11.3233%.
- Change: approximately +0.17 percentage points.
- Project IRR remains 9.4102%.

The shift accelerates sponsor SHL principal receipts, so the equity IRR moves upward. This closes the first-principal timing mismatch but does not by itself solve the full G20 parity gap.

## Runtime Drift Analysis

Default behavior:

- TUHO baseline and TUHO alignment-off are identical.
- Oborovo default behavior is unchanged.

Alignment-on expected effects:

- SHL principal schedule changes by design.
- SHL balance changes as a direct consequence of earlier principal.
- Equity IRR changes as a direct consequence of earlier sponsor cash receipts.
- Distributions change as a downstream consequence of the same controlled SHL timing shift.
  In the validation run, total distributions move from 173,516.2 kEUR to
  180,021.7 kEUR because earlier SHL balance reduction changes later sponsor
  cash ordering.

Unaffected in validation:

- Project IRR.
- Senior debt service.
- DSCR.
- R99/R102 audit fields.
- SHL interest formula and early-period PIK formula.

The validation reports are:

- `reports/phase9_tuho_shl_repayment_alignment_runtime_validation.csv`
- `reports/phase9_tuho_shl_repayment_alignment_period_bridge.csv`

## Rollback Strategy

Rollback is immediate: keep `use_tuho_shl_repayment_alignment=False`, or remove the optional start period. The default path remains the existing P29 start. No project factory currently opts into the new path.

## Oborovo Guard Behavior

Oborovo is not calibrated for this alignment path. Attempting to run the alignment for Oborovo raises:

`ValueError: TUHO SHL repayment alignment is currently supported only for TUHO-WIND-1`

Oborovo baseline remains unchanged.

## Remaining Known Gaps Vs Excel

This implementation aligns first SHL principal timing, not the full Excel SHL schedule. Remaining gaps include:

- SHL principal amount differences after P25.
- SHL IDC investment-base treatment.
- Remaining sponsor/equity IRR gap.
- G20 governance and acceptance gates.
- R99/R102 runtime source remains unapproved.

## Governance Status

G20 remains BLOCKED.

R99/R102 runtime promotion remains NOT approved.

This branch is a controlled runtime alignment only for TUHO SHL principal eligibility. It does not approve TUHO factory opt-in.
