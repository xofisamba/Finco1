# C3B3D2B5 SHL Fixed-Point Inventory

## Current State Characterization

Classification: `SHL_OUTSIDE_FIXED_POINT_CURRENT_STATE_CHARACTERIZED`.

Before this slice, the clean engine had:

- `financial_engine.shl.contracts`: typed SHL day-count, schedule, and waterfall policies.
- `financial_engine.shl.day_count`: SHL-specific inclusive ACT/365 Fixed and ACT/360 dispatch.
- `financial_engine.shl.engine`: pure construction-period SHL period primitive.
- `financial_engine.shl.waterfall`: pure operating SHL cash waterfall formula.
- `financial_engine.shl.production`: construction PIK plus operating waterfall chaining.
- `financial_engine.adapters.shl_cash_seam`: Base post-senior cash seam from Phase 2C/B4.
- `financial_engine.inputs.PeriodInterestInput.shl_interest_keur`: tax-engine input field already present.
- `financial_engine.adapters.tax_inputs`: explicit note that SHL interest was not yet merged by the adapter.

The fixed-point gap was not missing SHL arithmetic. The gap was orchestration:

`SHL balance -> SHL gross interest -> Base/Bank tax -> CFADS -> Senior Debt -> Base post-senior cash -> SHL cash/PIK/principal -> next SHL balance`

was not yet solved as one authoritative loop.

## Source Evidence

Oborovo source anchors:

- SHL principal: 14,620.773894815633 kEUR
- Annual rate: 8.00%
- Construction SHL interest/PIK: 1,169.6619115852516 kEUR
- First operating opening balance: 15,790.435806400885 kEUR
- Operating day count: ACT/365 Fixed inclusive
- Construction day fraction: explicit 1.0
- Operating behavior: early partial cash plus PIK, then full cash interest plus principal sweep
- First source principal period: DS25
- Final source closing balance: zero

Construction DCF classification:
`CONSTRUCTION_SHL_DAY_FRACTION_SOURCE_CONFIGURED_NOT_INFERRED`.

Oborovo tax classification:
`OBOROVO_SHL_INTEREST_AND_FISCAL_REINTEGRATION_CAUSAL_CHAIN_PROVEN`.

## Generic Target

This slice adds an optional immutable `ShareholderLoanModelInput` to `SeniorDebtModelInput`.

When absent, `run_senior_debt_model` keeps the existing Phase 2C path.

When present, the B5 path:

1. Derives Bank operating inputs from explicit `DebtSizingCaseInput`.
2. Iterates Senior Debt with SHL gross interest merged into Bank tax.
3. Recomputes Base tax and Base CFADS with final Senior and current SHL interest.
4. Builds `PostSeniorCashSchedules` from Base CFADS minus actual Senior Debt Service.
5. Builds `ShareholderLoanSchedules` using pre-reserve cash.
6. Compares SHL closing and gross-interest vectors.
7. Fails closed on non-convergence.
8. Performs final deterministic recomputation from converged SHL and Senior schedules.

Final recomputation classification:
`FINAL_FINANCING_STATE_RECOMPUTED_FROM_CONVERGED_SHL_AND_SENIOR_SCHEDULES`.

SHL output cash classification:
`POST_SHL_CASH_IS_PRE_RESERVE`.

## Unresolved Source Quirks

The B5 slice does not implement DSRA, reserve releases, distributions, sponsor returns, multi-lender structures, multi-SHL facilities, promote, or final distributable cash.

Oborovo Base-performance calendar/leap residuals can still affect clean runtime cash available for SHL. They are classified as:

`UPSTREAM_BASE_CALENDAR_RESIDUAL`.

The source-oracle SHL tests use source cash as validation evidence only. Runtime calculations do not replay source vectors, fit targets, apply calibration deltas, or add residual fillers.
