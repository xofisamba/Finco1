# Stage B2 generic coverage migration matrix

Date: 2026-07-23  
Scope: PR #906 Stage B2 construction runtime.

This matrix maps the previously reviewed broad Stage B2 contract areas to current tests. The goal is meaningful generic coverage, not restoring obsolete implementation-specific assertions purely for count.

| Old contract | Current test / evidence | Status |
| --- | --- | --- |
| MarginSchedule flat behavior | `test_period_rate_schedule_can_be_derived_from_hedge_and_euribor_primitives` covers flat primitive rate derivation when no curve override is needed. | MIGRATED |
| MarginSchedule stepped behavior | Period-specific Euribor vector path in `_period_rates`; Oborovo parity test covers varying period rates. | MIGRATED |
| Fixed-rate facility pricing | `test_hedge_coverage_zero_and_full_change_derived_rates_generically` exercises 100% hedge fixed-rate behavior. | MIGRATED |
| Floating-rate facility pricing | `test_hedge_coverage_zero_and_full_change_derived_rates_generically` exercises 0% hedge floating behavior. | MIGRATED |
| Hedged-blend pricing | `test_period_rate_schedule_can_be_derived_from_hedge_and_euribor_primitives` and Oborovo config use 80% hedge / 20% unhedged + buffer. | MIGRATED |
| Hedge coverage 0% | `test_hedge_coverage_zero_and_full_change_derived_rates_generically`. | MIGRATED |
| Hedge coverage 80% | `test_oborovo_rate_chain_uses_primitives_not_literal_effective_rates`. | MIGRATED |
| Hedge coverage 100% | `test_hedge_coverage_zero_and_full_change_derived_rates_generically`. | MIGRATED |
| Hedge maturity behavior | No maturity-expiry concept exists in the focused construction-period runtime yet. | OBSOLETE_WITH_REASON |
| External curve buffer | `test_period_rate_schedule_can_be_derived_from_hedge_and_euribor_primitives`. | MIGRATED |
| Swap margin adjustment | `test_swap_forward_and_cva_adjustments_affect_period_rate_generically`. | MIGRATED |
| Forward swap adjustment | `test_swap_forward_and_cva_adjustments_affect_period_rate_generically`. | MIGRATED |
| CVA adjustment | `test_swap_forward_and_cva_adjustments_affect_period_rate_generically`. | MIGRATED |
| Construction vs operational rate distinction | Stage B2 runtime is construction-only; operational debt pricing remains outside this focused runtime. | OBSOLETE_WITH_REASON |
| Period-derived Senior IDC | `test_opening_basis_and_same_period_capitalization_are_runtime_policies`, Oborovo Senior financing total tests. | MIGRATED |
| Funding-period/accrual-period mapping | `test_oborovo_p1_uses_lagged_funding_accrual_mapping_not_profile_replay`; `test_same_period_and_next_funding_period_capitalization_differ_generically`. | MIGRATED |
| Commitment-fee balance basis | `test_oborovo_p1_uses_lagged_funding_accrual_mapping_not_profile_replay`. | MIGRATED |
| FacilityPeriodState roll-forward | `test_vat_reimbursement_lag_rolls_requirement_forward_generically`; VAT runoff tests. | MIGRATED |
| InterestRatePeriodState auditability | Primitive rate inputs and period fractions are exposed on `ConstructionRuntimeConfig`; no separate dataclass exists. | REPLACED |
| CAPEX equal schedule | `test_oborovo_equal_and_m1_payment_schedules_are_explicit`; `test_capex_equal_and_custom_schedules_drive_monthly_uses_generically`. | MIGRATED |
| CAPEX custom schedule | `test_capex_equal_and_custom_schedules_drive_monthly_uses_generically`. | MIGRATED |
| CAPEX schedule sum validation | `test_capex_schedule_sum_validation_rejects_malformed_profile`. | MIGRATED |
| Funding waterfall | `test_funding_waterfall_consumes_equity_then_shl_before_senior`. | MIGRATED |
| VAT facility pricing | Oborovo VAT IDC / commitment tests in `test_oborovo_stageb2_source_parity.py`. | MIGRATED |
| VAT reimbursement lag | `test_vat_reimbursement_lag_rolls_requirement_forward_generically`. | MIGRATED |
| VAT requirement roll-forward | `test_vat_reimbursement_lag_rolls_requirement_forward_generically` and Oborovo 18-period requirement parity. | MIGRATED |
| SHL construction behavior | Funding waterfall consumes SHL before Senior; standalone SHL construction economics remain outside this Stage B2 file. | REPLACED |
| Vector convergence | `test_stage_b2_vector_residual_catches_same_total_different_timing`; convergence audit tests. | MIGRATED |
| Non-convergence fail-fast | `test_non_convergence_fail_fast_for_generic_circular_case`. | MIGRATED |
| Identity invariance | `test_runtime_config_has_no_project_identity_or_approved_delta_fields`. | MIGRATED |
| Generic synthetic project | `_synthetic_config()` tests use amounts/rates/timing materially different from Oborovo. | MIGRATED |
| No target-derived inputs | Oborovo anti-calibration tests assert source vectors and targets are absent from runtime config. | MIGRATED |
| No profile-vector replay | `test_oborovo_senior_financing_formula_totals_are_not_output_profile_replay`. | MIGRATED |
| No project identity dispatch | `test_runtime_config_has_no_project_identity_or_approved_delta_fields`. | MIGRATED |
| No approved_delta / balancing plug | `test_runtime_config_has_no_project_identity_or_approved_delta_fields`; Oborovo hard-CAPEX no-plug test. | MIGRATED |

Meaningful generic coverage loss count for the focused runtime: `0` for implemented Stage B2 runtime concepts. Two old contracts are marked obsolete/replaced because they belonged to broader legacy pricing/operational modules rather than the canonical construction runtime introduced in this PR.
