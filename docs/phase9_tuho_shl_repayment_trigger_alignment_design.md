# Phase 9 TUHO SHL Repayment Trigger Alignment Design

## Executive Summary

This branch is design, impact analysis, reports, and tests only. It does not change runtime behavior and does not implement a TUHO SHL repayment timing fix.

PR #163 confirmed the current evidence:

- Excel first SHL principal: P25 / 2042-06-30.
- Current model first SHL principal: P29 / 2044-06-30.
- The stale premise that current main repays SHL principal in P1 is not reproducible.
- The mismatch is visible in runtime period data, not only in sponsor reporting.
- G20 remains BLOCKED.
- R99/R102 runtime promotion remains NOT approved.

Design conclusion: proceed to implementation only with a narrowly scoped, TUHO-only, default-off alignment mechanism that changes SHL principal eligibility without promoting R99/R102 as a runtime source. The safest next branch is:

`phase9-tuho-shl-repayment-trigger-alignment-implementation`

## Scope And Non-Goals

Allowed scope in this branch:

- Design the alignment path.
- Quantify expected impact status.
- Produce CSV decision reports.
- Add tests for docs/reports.

Explicitly out of scope:

- No runtime waterfall change.
- No `domain/waterfall/waterfall_engine.py` change.
- No `domain/shl/*` or SHL cash mechanics change.
- No `app/waterfall_core.py` change.
- No project factory change.
- No DistributionAccount, R99/R102, SeniorDebtSizing, TaxBridge, Oborovo, or runtime flag change.
- No repayment timing fix.

## Exact Model Condition Causing P29 Start

Current TUHO uses `shl_repayment_method = "pik_then_sweep"`.

The observed trigger path is:

1. Runtime computes post-tax cash.
2. For `pik_then_sweep`, runtime computes `_cf_for_shl = max(0, cf_after_tax - senior_ds - dsra_contrib)`.
3. Runtime computes a sweep trigger from cash availability versus full annual SHL interest.
4. SHL service is computed before later lockup/distribution routing.
5. Principal is paid only when the SHL engine is in sweep behavior and cash after SHL interest is available.

In the current model:

- P25-P28 still have senior debt service, so model SHL principal stays zero.
- P29 has senior debt service of 0.0 kEUR and enough cash to pay interest plus principal.
- First principal appears in P29 / 2044-06-30.

This is a senior-first SHL sweep behavior. It is economically coherent, but it is not Excel-identical.

## Exact Excel Condition Appearing To Allow P25 Start

The Excel fixture shows:

- P25 / 2042-06-30: SHL principal starts at 1,498.8 kEUR.
- Senior debt service is still present in the same period.
- Excel therefore does not use "senior debt fully repaid" as the sole SHL principal eligibility gate.

The most likely Excel condition is an R99/R102 or distribution-account availability convention that permits SHL principal once FCF for SHL/distribution is positive after senior debt service, even before senior debt is fully repaid. This branch does not approve that source for runtime use.

## Alignment Options

The options report evaluates five paths:

1. `no_change_document_excel_convention`
2. `tuho_only_repayment_start_period_override`
3. `config_driven_shl_principal_eligibility_date`
4. `r99_r102_distribution_account_source`
5. `senior_debt_zero_only_current_behavior`

Recommendation: use `config_driven_shl_principal_eligibility_date` for the implementation branch, scoped to TUHO and default-off. In plain terms, the recommended option is a Config-driven SHL principal eligibility date. It is more auditable than a hard-coded period override and avoids prematurely accepting R99/R102 as a runtime source.

## Minimal Safe Alignment Mechanism

Recommended implementation shape:

- Add a default-off, TUHO-only SHL repayment eligibility configuration.
- Configure the earliest SHL principal eligibility date/period as P25 / 2042-06-30.
- Keep the existing cash availability and interest-first mechanics.
- Do not change SHL interest, PIK, WHT, senior debt, DSCR, DistributionAccount, R99/R102, or sponsor reporting.
- Raise a clear guard for unsupported projects, including Oborovo.
- Preserve default behavior bit-identically when the alignment config is off.

This belongs in SHL repayment eligibility, not sponsor reporting. The mismatch is visible in runtime `shl_principal_keur`; sponsor reporting can only display or consume the resulting schedule. It also should not be implemented as full R99/R102 promotion, because that remains explicitly unapproved.

## Flag Or Config Strategy

Preferred strategy:

- Default-off.
- TUHO-only.
- Config-driven eligibility date/period rather than a global formula change.
- No project factory opt-in.

Whether this is represented as a project input flag, a private TUHO calibration config, or a dedicated guarded runtime option should be decided in the implementation branch. The implementation branch must not silently turn it on in factories.

## Expected IRR Impact

Exact IRR impact is `ESTIMATE_REQUIRED`. This branch does not implement the altered principal schedule and therefore does not calculate a reliable post-alignment XIRR.

Expected direction:

- Moving SHL principal from P29 to P25 accelerates sponsor cash receipts.
- Accelerated SHL receipts usually increase sponsor/equity IRR if investment base is unchanged.
- However, the total equity IRR gap also includes SHL IDC investment-base treatment and prior reporting fixes. The net impact must be computed in the implementation branch with the same investment-base convention held constant.

The impact report therefore marks the alignment scenario as `ESTIMATE_REQUIRED`, not pass/fail.

## Gate Status

Current gates:

- Excel repayment timing evidence: available.
- Model P29 runtime evidence: available.
- Default-off/zero drift requirement: required before implementation.
- Oborovo guard: required.
- R99/R102 not approved: blocking any R99 source promotion.
- G20 blocked: still blocked.
- Sponsor IRR parity: not yet achieved.
- SHL balance/principal schedule parity: not yet achieved.

## Recommended Implementation Branch

Branch name:

`phase9-tuho-shl-repayment-trigger-alignment-implementation`

Strict implementation scope:

- TUHO-only repayment eligibility alignment.
- Default-off or explicitly guarded.
- No project factory opt-in.
- No R99/R102 runtime promotion.
- No DistributionAccount rewrite.
- No SHL interest/PIK/WHT formula change.
- No senior debt, DSCR, TaxBridge, Oborovo, or sponsor reporting formula change.

## Rollback And Default-Off Strategy

Rollback strategy:

- Keep current behavior as default.
- New alignment path must be bypassed unless explicitly enabled.
- Tests must prove default TUHO and Oborovo outputs are unchanged.
- Any implementation branch should be reversible by disabling the new config.

## Required Implementation Tests

The implementation branch should include tests that assert:

- Default behavior bit-identical.
- TUHO flag/config off first principal remains P29.
- TUHO flag/config on first principal becomes P25.
- Excel P25-P28 timing gap closes within tolerance.
- SHL interest, PIK, WHT, senior debt, DSCR, R99/R102 audit status, and distributions do not drift unexpectedly.
- Oborovo remains guarded.
- G20 remains BLOCKED unless separately approved.
- R99/R102 runtime promotion remains NOT approved.

## Final Recommendation

Proceed to implementation only with the controlled TUHO-only alignment branch above. Do not implement R99/R102 source acceptance as part of this work.

G20 remains BLOCKED.

R99/R102 runtime promotion remains NOT approved.
