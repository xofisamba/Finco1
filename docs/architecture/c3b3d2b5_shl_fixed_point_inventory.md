# C3B3D2B5 SHL Fixed-Point Inventory

## Current State Characterization

Classification: `SHL_OUTSIDE_FIXED_POINT_CURRENT_STATE_CHARACTERIZED`.

Before this slice, the clean engine had:

- `financial_engine.shl.contracts`: typed SHL day-count, schedule, and waterfall policies.
- `financial_engine.shl.day_count`: SHL-specific inclusive ACT/365 Fixed and ACT/360 dispatch.
- `financial_engine.shl.engine`: pure construction-period SHL period primitive.
- `financial_engine.shl.waterfall`: pure operating SHL cash waterfall formula.
- `financial_engine.shl.production`: construction PIK plus operating waterfall chaining through the canonical SHL schedule kernel.
- `financial_engine.adapters.shl_cash_seam`: Base post-senior cash seam from Phase 2C/B4.
- `financial_engine.inputs.PeriodInterestInput.shl_interest_keur`: tax-engine input field already present.
- `financial_engine.adapters.tax_inputs`: ProjectInputs tax-policy adapter. It may build the contract for the B5 complete-interest path, but the plain ATAD adapter still fails closed if complete financing interest is not being injected.

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
`SHL_CONSTRUCTION_DCF_IS_EXPLICIT_INPUT_NOT_BACKSOLVED_FROM_IDC`.

Oborovo tax classification:
`OBOROVO_SHL_INTEREST_AND_FISCAL_REINTEGRATION_CAUSAL_CHAIN_PROVEN`.

Oborovo construction identity:

- opening SHL balance: 0.0 kEUR
- drawdown: 14,620.773894815633 kEUR
- construction PIK: 1,169.6619115852516 kEUR
- closing SHL balance: 15,790.435806400885 kEUR

The drawdown is exposed explicitly in `ShareholderLoanSchedules.shl_drawdown_keur`;
construction principal is no longer hidden as an opening balance.

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
8. Promotes the newly computed SHL schedule that satisfied convergence as the authoritative state.
9. Performs a final self-consistency handshake from final post-senior cash:
   - returned SHL gross interest must match final Base tax SHL interest;
   - returned SHL gross interest must match final Bank tax SHL interest;
   - recomputed SHL from final post-senior cash must match returned closing balances.
10. Fails closed if the final handshake is not within tolerance.

Final recomputation classification:
`SHL_CONVERGENCE_STATE_IS_THE_STATE_THAT_SATISFIED_CONVERGENCE`.

Final handshake classification:
`FINAL_FINANCING_STATE_IS_SELF_CONSISTENT`.

Tax ownership classification:
`CLEAN_ENGINE_NON_DEDUCTIBLE_SHL_TREATMENT`.

SHL tax treatment is owned by `TaxPolicy.shl_interest_deductibility`, not by
`ShareholderLoanModelInput`. It is applied only when
`TaxPolicy.shl_interest_tax_treatment_enabled` confirms that the caller is in a
complete financing-interest path. This preserves standalone tax baselines that
do not yet have complete SHL/Senior/other interest context. Supported B5 modes
are fully deductible, fully non-deductible, and custom deductible percentage.
`SUBJECT_TO_LIMITATIONS` fails closed until the limitation engine has
source-proven clean fixed-point support.

SHL output cash classification:
`POST_SHL_CASH_IS_PRE_RESERVE`.

Accounting boundary classification:
construction Stage B5 calculates SHL amounts only. Useful-life policy for
capitalized financing costs remains owned by the accounting/book-depreciation
layer; Stage B5 does not expose configurable useful-life metadata.

## Unresolved Source Quirks

The B5 slice does not implement DSRA, reserve releases, distributions, sponsor returns, multi-lender structures, multi-SHL facilities, promote, or final distributable cash.

Oborovo Base-performance calendar/leap residuals can still affect clean runtime cash available for SHL. They are classified as:

`UPSTREAM_BASE_CALENDAR_RESIDUAL`.

The source-oracle SHL tests use source cash as validation evidence only. Runtime calculations do not replay source vectors, fit targets, apply calibration deltas, or add residual fillers.

## Production Wiring

`build_senior_debt_model_input_from_project_inputs()` maps configured
`ProjectInputs.financing` SHL fields into `ShareholderLoanModelInput` without
project-name or project-code dispatch. The mapping is generic: if the canonical
project input has no explicit `clean_shl_principal_keur`, the SHL input is
absent and the existing senior-debt-only path is used.

The clean production contract deliberately does not promote legacy
`shl_amount_keur` to the B5 fixed-point layer. That field remains a legacy
template/runtime assumption with known baseline sensitivity. The clean SHL
contract uses explicit generic authority fields instead:

- `clean_shl_principal_keur`
- `clean_shl_repayment_method` (falling back to `shl_repayment_method` only
  when the clean override is absent)
- `shl_day_count_convention`
- `shl_construction_day_count_fraction`
- `shl_principal_eligibility_start_period`
- `shl_maturity_period_index`

For Oborovo, this resolves the source conflict by wiring the clean contract to
`Inputs!D325 = 14,620.773894815633 kEUR` while leaving the legacy
`shl_amount_keur = 13,547.2 kEUR` untouched. Classification:
`OBOROVO_CLEAN_SHL_PRINCIPAL_AUTHORITY_IS_SOURCE_CORRECT`.

Oborovo clean SHL production parameters are:

- principal: `14,620.773894815633 kEUR`
- annual rate: `8.00%`
- operating day count: inclusive `ACT_365_FIXED`
- construction DCF: explicit `1.0`
- construction PIK: `1,169.6619115852516 kEUR`
- first operating opening: `15,790.435806400885 kEUR`
- principal eligibility start: `DS25`
- maturity/clearance: `DS40`
- repayment mode: `partial_pay_sweep`

Classification:
`OBOROVO_SHL_CONTRACT_SOURCE_PARAMETERS_PRODUCTION_WIRED`.

Unsupported clean SHL repayment modes fail closed. The B5 production mapping
supports the natural partial-pay/cash-sweep contract only; it does not silently
convert `bullet`, `PIK`, `accrued`, or unknown modes into sweep behavior.
Classification: `UNSUPPORTED_SHL_REPAYMENT_MODE_FAILS_CLOSED`.

TUHO remains blocked at the production adapter boundary because the required
generic clean SHL contract fields are not yet authoritative for that factory.
The manually constructed TUHO fixture remains formula evidence only, not a
production-wiring proof.

## Maturity Boundary

The SHL production schedule has no terminal top-up or forced final draw. If a
positive balance remains at the configured maturity or final clearance boundary,
the runtime raises `SHL_MATURITY_RESIDUAL_FAILS_CLOSED` instead of hiding the
shortfall.

Maturity is never inferred from the model horizon. A 30-year model horizon does
not silently extend a 20-year SHL; clean SHL mapping requires explicit
`shl_maturity_period_index` authority (or a future independently specified
tenor-to-period rule).

Both the ProjectInputs adapter and the clean production schedule require the
configured repayment start and maturity to exist on the authoritative period
grid. The runtime fails closed instead of shifting to the next available period
or allowing maturity beyond the model horizon:

- `SHL_REPAYMENT_START_NOT_ON_PERIOD_GRID_FAILS_CLOSED`
- `SHL_MATURITY_NOT_ON_PERIOD_GRID_FAILS_CLOSED`

The repayment start must be on-grid, maturity must be on-grid, maturity must
not precede first operation, and maturity must be greater than or equal to the
repayment start. This protects manually constructed `ShareholderLoanModelInput`
objects as well as ProjectInputs adapter callers.

## Production Acceptance

Two parity classes are tracked separately:

- `SHL_FORMULA_SOURCE_ORACLE_PARITY`: source cash plus the canonical SHL formula
  reproduces the source SHL schedule at machine precision. Source fixtures are
  used only as test oracles.
- `SHL_PRODUCTION_RUNTIME_PARITY`: actual production runtime cash through
  `create_default_oborovo()` and
  `build_senior_debt_model_input_from_project_inputs()` compared to the source
  SHL fixture.

The production path now proves the clean input authority and construction
identity without `replace(model, shareholder_loan=...)` and without source cash
replay. The remaining production SHL vector difference is classified by first
cause: current backend post-senior cash available for SHL diverges from source
`free_cash_flow_for_shl_keur` at DS1. The SHL layer does not compensate for that
upstream cash difference.

The production diagnostic reports current deltas dynamically, but those wrong
downstream magnitudes are not approved baselines. Classification:
`SHL_PRODUCTION_RUNTIME_BLOCKED_BY_UPSTREAM_POST_SENIOR_CASH`.
