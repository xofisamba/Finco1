# Phase 9 TUHO SHL Repayment Trigger Investigation

## Executive Summary

This branch is investigation-only. It does not change runtime formulas, SHL mechanics, R99/R102 logic, DistributionAccount routing, project factories, TaxBridge, SeniorDebtSizing, Oborovo behavior, or runtime flags.

The requested premise that the current model starts TUHO SHL principal repayment immediately in P1 is not reproducible on the current main snapshot used for this investigation. Current TUHO runtime output shows:

| Source | First SHL principal repayment | Date | Principal repaid |
| --- | ---: | --- | ---: |
| Excel fixture | P25 | 2042-06-30 | 1,498.8 kEUR |
| Current model | P29 | 2044-06-30 | 4,688.3 kEUR |

So the current confirmed mismatch is still real, but its direction is different from the P1-repayment premise: Excel starts SHL principal earlier than the current model, not later. The model remains in cash-interest/PIK behavior through P28 and only sweeps SHL principal once senior debt service falls to zero in P29.

Root cause classification:

- Not a sponsor reporting artifact: the timing is visible directly in `WaterfallPeriod.shl_principal_keur`.
- Not a direct DSCR trigger: DSCR affects lockup/senior sweep, but is not passed into `compute_shl_period`.
- Not currently blocked by lockup: lockup is computed after SHL service and does not gate SHL cash service in the present ordering.
- Primary model trigger: `pik_then_sweep` uses post-tax cash after senior debt service, then allows principal only when the sweep condition is active. In current TUHO, that effectively happens once senior debt service is zero and available cash exceeds the full annual SHL interest threshold.
- Excel-specific convention remains likely: Excel begins SHL principal in P25 while senior debt service still exists, consistent with a different R99/R102/distribution-account eligibility convention that is not approved as a runtime source.

Recommendation: a runtime alignment fix may be justified only as a separate guarded TUHO-only branch if the chosen target remains Excel parity. Do not approve G20 and do not promote R99/R102 from audit-only status based on this branch.

## Scope And Non-Goals

Scope:

- Trace current TUHO SHL principal timing.
- Compare model SHL principal against Excel fixture timing.
- Identify model trigger path and upstream conditions.
- Produce human-readable CSV reports for review.
- Add tests that validate the investigation artifacts.

Non-goals:

- No repayment timing fix.
- No SHL cash waterfall change.
- No DistributionAccount or R99/R102 runtime change.
- No DSCR, SeniorDebtSizing, TaxBridge, project factory, Oborovo, or runtime flag change.
- No G20 approval.

## Confirmed Excel Repayment Timing

Excel fixture source: `tests/fixtures/excel_tuho_full_model_extract.json`.

The operating-period SHL fixture shows:

- P1 to P24: SHL principal is zero.
- P25, dated 2042-06-30: SHL principal begins at 1,498.8 kEUR.
- The SHL balance compounds during early periods through capitalized interest.
- SHL is fully repaid by 2047-12-31, after which dividends begin.

This matches the existing Excel fixture tests that identify TUHO first principal repayment at 2042-06-30.

## Confirmed Model Repayment Timing

Current TUHO runtime output shows:

- P1, dated 2030-06-30: SHL principal is 0.0 kEUR.
- P2 to P28: SHL principal remains 0.0 kEUR.
- P29, dated 2044-06-30: first SHL principal repayment is 4,688.3 kEUR.
- The model pays cash SHL interest during the PIK phase and capitalizes residual interest when available cash is insufficient.

This means the "immediate P1 principal repayment" premise was not reproduced on the current main code used here.

## Exact Model Repayment Trigger Path

Relevant runtime path inspected:

1. `run_waterfall` computes `cf_after_tax = ebitda - tax_this_period`.
2. For `shl_repayment_method == "pik_then_sweep"`, `_cf_for_shl = max(0.0, cf_after_tax - senior_ds - dsra_contrib)`.
3. `_pik_trigger = (_cf_for_shl > shl_balance * shl_rate)`.
4. `compute_shl_period(...)` is called before the later lockup/distribution section.
5. `compute_shl_period_v3(..., method="pik_then_sweep")`:
   - if `pik_switch_triggered` is false, cash pays interest first and any shortfall is PIK; principal is zero.
   - if `pik_switch_triggered` is true, cash pays interest and remaining cash sweeps to principal.

In current TUHO:

- P25 to P28 have enough cash to pay SHL interest, but the sweep branch does not create principal while senior debt remains outstanding and the cash threshold pattern has not moved the period into principal sweep.
- P29 has senior debt service of 0.0 kEUR and `cf_for_shl_keur` of 6,187.8 kEUR. This exceeds the full annual SHL interest threshold, so the sweep branch pays 1,499.6 kEUR interest and 4,688.3 kEUR principal.

## Waterfall Ordering Analysis

SHL service is computed before the final lockup/distribution account routing. That means current SHL repayment eligibility is decided from `_cf_for_shl` and the `pik_then_sweep` trigger before any later distribution account lock/carry-forward analysis can block SHL principal.

The code contains a TUHO SHL cash-cap/R99-equivalent comment block stating that the prior senior-sweep cash cap is disabled and that a valid R99-equivalent source would need a reordered calculation. That means current repayment timing is not using Excel R99/R102 as an accepted source.

## Repayment Eligibility Analysis

Current runtime eligibility is:

- SHL method must be `pik_then_sweep`.
- The period must not be the SHL disbursement/opening period.
- There must be positive post-tax cash after senior debt service and DSRA contribution.
- Principal is paid only in the sweep branch, where cash remaining after SHL interest is swept to principal.

There is no explicit SHL principal grace-period input in the runtime path inspected here.

## Lockup Interaction

Lockup is calculated after SHL service. It blocks distributions and senior sweep logic, but it does not block SHL interest/principal already computed by `compute_shl_period`.

For the key transition periods, lockup is false in the trace. Therefore the current TUHO timing mismatch is not caused by an active lockup flag.

## DSCR Interaction

DSCR is not directly passed into `compute_shl_period`. It is used for lockup and senior cash sweep checks after SHL service has already been calculated.

Therefore DSCR is not the direct trigger for SHL principal. The direct trigger is available post-senior cash under `pik_then_sweep`, plus the sweep/threshold behavior and senior-debt state.

## Senior Debt Interaction

Senior debt is the strongest observed model gate:

- P25 to P28 still have senior debt service, and model SHL principal remains zero.
- P29 has no senior debt service, and model SHL principal begins.

Excel differs because it begins SHL principal in P25 while senior debt service is still present. That points to an Excel-specific repayment eligibility source, likely tied to R99/R102/distribution-account mechanics, rather than the current runtime senior-debt-zero sweep gate.

## Available Cash Analysis

The trace report uses `fcf_for_shl_keur` as the observed model cash available before SHL service where available.

Key periods:

| Period | Date | Model cash pre-SHL | Senior DS | Model SHL interest | Model SHL principal | Notes |
| ---: | --- | ---: | ---: | ---: | ---: | --- |
| 25 | 2042-06-30 | 2,760.6 | 3,379.7 | 1,495.4 | 0.0 | Excel starts principal; model does not. |
| 28 | 2043-12-31 | 1,907.0 | 3,421.8 | 1,520.2 | 0.0 | Final senior service period. |
| 29 | 2044-06-30 | 6,187.8 | 0.0 | 1,499.6 | 4,688.3 | Model first principal. |

## Root-Cause Classification

| Category | Finding |
| --- | --- |
| Intended model behavior | Plausible. The current model applies a coherent senior-first, then SHL-sweep behavior. |
| Unintended mismatch | Yes if Excel parity is the target. Excel begins principal while senior debt service is still present. |
| Reporting artifact | No. The mismatch is visible in runtime `shl_principal_keur`. |
| Excel-specific convention | Likely. Excel appears to use a different R99/R102/distribution-account convention for SHL principal eligibility. |

## Expected IRR Impact

This branch does not recompute a controlled IRR bridge because it is discovery-only and does not change repayment timing. The expected impact is timing-sensitive: earlier Excel principal receipts should generally move sponsor cash receipts earlier, but investment-base treatment and the already-fixed sponsor cashflow double-count issue must be held constant in a separate controlled bridge.

Known governance remains:

- Sponsor cashflow double-count bug from PR #162 is fixed.
- SHL IDC investment-base gap remains separately identified.
- G20 remains BLOCKED.
- R99/R102 runtime promotion remains NOT approved.

## Runtime Fix Recommendation

Runtime fix recommendation: yes, but only if TUHO Excel parity remains the chosen target and only in a separate, guarded branch. The safest branch is:

`phase9-tuho-shl-repayment-trigger-alignment`

That branch should be TUHO-only, default-off or explicitly guarded, and should not accept R99/R102 runtime promotion without separate approval.

If the sponsor/user decides current senior-first model behavior is economically preferable to Excel convention, the safer path is:

`phase9-equity-irr-investment-base-alignment`

## G20 And R99/R102 Status

G20 remains BLOCKED.

R99/R102 runtime promotion remains NOT approved.

This investigation does not approve SHL FCF runtime behavior, R99/R102 as runtime source, project factory opt-in, or any repayment timing change.

## Changed Files Intended By This Branch

No runtime files were changed. Intended files are:

- `docs/phase9_tuho_shl_repayment_trigger_investigation.md`
- `reports/phase9_tuho_shl_repayment_trigger_trace.csv`
- `reports/phase9_tuho_shl_repayment_vs_excel.csv`
- `reports/phase9_tuho_shl_repayment_root_cause_matrix.csv`
- `tests/test_phase9_tuho_shl_repayment_trigger_investigation.py`

## Next Branch

If runtime timing mismatch is confirmed as the desired target:

`phase9-tuho-shl-repayment-trigger-alignment`

If the mismatch is accepted as an Excel-specific convention:

`phase9-equity-irr-investment-base-alignment`
