# Phase 4C: SHL End-to-End Portfolio Integration

## Overview

Phase 4C connects the SHL (Subordinated HoldCo Loan) engine to the portfolio
and HoldCo aggregation flow. The integration is **in-place** and **additive**:
SHL flows are enrichment metadata written onto waterfall period objects after
the waterfall and DSRF calculations are complete.

## Architecture

```
SPV operations
  → SPV distributions (waterfall result)
  → SHL facility payments (run_shl_facility)
  → WaterfallPeriod.shl_interest_keur  ← set by enrich_portfolio_result_with_shl
  → WaterfallPeriod.shl_principal_keur ← set by enrich_portfolio_result_with_shl
  → HoldCo aggregation (build_holdco_result)
  → future tax engine
```

## Mapping API

The integration layer uses a clean, decoupled API:

```python
# 1. Group facility results by borrower entity code
shl_by_borrower: dict[str, tuple[SHLFacilityResult, ...]] = \
    group_shl_facilities_by_borrower(shl_portfolio_result)

# 2. Enrich waterfall periods in-place
enrich_portfolio_result_with_shl(portfolio_result, shl_by_borrower)
```

## Grouping by Borrower

`group_shl_facilities_by_borrower(SHLPortfolioResult) → dict[borrower_code, tuple[SHLFacilityResult, ...]]`

- Groups facility results by `facility.borrower_entity_code`
- Preserves all facilities per borrower
- Empty portfolio result returns `{}`
- Key = borrower_entity_code (= SPV project_code in the integration)

## In-Place Enrichment Warning

`enrich_portfolio_result_with_shl` **mutates waterfall period objects in-place**.

This is a Phase 4C pragmatic choice. A future immutable refactor may replace
this with a copy-on-write approach.

The mutation is safe because:
1. It happens **after** the waterfall and DSRF calculations are complete
2. `distribution_keur` is **unchanged**
3. `adjusted_period_distributions_keur` is **unchanged**
4. HoldCo reads via `_safe_get_float` which tolerates absent attributes

## Sequencing

```python
# Step 1: Run portfolio (waterfall + optional DSRF)
portfolio_result = run_independent_portfolio(portfolio_inputs)

# Step 2: Run SHL facilities
shl_portfolio = run_shl_portfolio(shl_portfolio_inputs)

# Step 3: Group SHL by borrower entity code
shl_by_borrower = group_shl_facilities_by_borrower(shl_portfolio)

# Step 4: Enrich waterfall periods with SHL flows (in-place mutation)
enrich_portfolio_result_with_shl(portfolio_result, shl_by_borrower)

# Step 5: Build HoldCo aggregation (now sees SHL interest + principal)
holdco_result = build_holdco_result(holdco_inputs, portfolio_result)
```

## SHL Principal Exclusion Rule

**SHL principal is NEVER included in HoldCo gross income.**

Rationale:
- Principal repayment is a **balance-sheet movement**, not income
- Including principal would overstate HoldCo taxable income
- Principal flows to HoldCo as cash (return of investment, not return **on** investment)
- SHL interest IS taxable income (return on investment)

Implementation:
- `gross_income_keur = dividend_keur + shl_interest_keur` (principal excluded)
- `shl_principal_keur` is tracked separately on the period and total level

## Why SHL Does Not Reduce SPV Distribution

In Phase 4C, SHL principal repayments are **not deducted** from the SPV's
`distribution_keur`. This is deliberate.

Rationale:
- Phase 4C uses the existing SHL engine (straight-line amortization) which
  generates interest + principal from the facility definition
- The SPV distribution is the equity dividend after all waterfall deductions
- SHL flows are **additive upstream metadata** — they flow to HoldCo on top
  of the equity distribution
- Future work (retained earnings / cash-account phase) will determine whether
  SHL principal reduces distributable equity

## DSRF Compatibility

DSRF-adjusted distributions (`adjusted_period_distributions_keur`) and SHL
enrichment are **orthogonal and composable**:

1. DSRF runs first → `adjusted_period_distributions_keur` is set
2. SHL enrichment runs second → `shl_interest_keur` / `shl_principal_keur` set on periods
3. HoldCo reads:
   - `dividend_keur` from `adjusted_period_distributions_keur[i]` (DSRF-adjusted)
   - `shl_interest_keur` from enriched period (SHL interest)
   - `shl_principal_keur` from enriched period (SHL principal)

No double counting: DSRF reduces dividend; SHL adds interest on top.

## Non-Scope (Phase 4C)

The following are explicitly **not implemented** in Phase 4C:

- **Tax template engine** — future phase
- **Withholding tax** — future phase
- **ATAD / thin capitalization** — future phase
- **Transfer pricing** — future phase
- **SHL sculpting** — straight-line only (Phase 4A architectural foundation)
- **SHL capitalization** — future phase
- **Retained earnings logic** — future phase
- **Monthly model** — future phase
- **Sponsor waterfall** — future phase
- **Recursive ownership graphs** — future phase
- **Refinancing** — future phase
- **HoldCo IRR** — future phase
- **Sponsor IRR** — future phase

## Files Changed (Phase 4C)

| File | Change |
|------|--------|
| `domain/portfolio/shl/integration.py` | New — mapping, grouping, enrichment |
| `tests/test_shl_integration.py` | New — unit tests for integration layer |
| `tests/test_shl_holdco_e2e.py` | New — HoldCo E2E tests |
| `tests/test_shl_dsrf_compat.py` | New — DSRF + SHL compatibility tests |
| `docs/phase4c_shl_e2e_integration.md` | New — this document |

## Future Phases

- **Phase 4D**: Retained earnings / cash-account (SHL principal reduces equity distribution)
- **Phase 4E**: Tax template engine (deductibility of SHL interest)
- **Phase 4F**: Sponsor waterfall (equity cascade)
