# Phase 2B: Policy-Driven Tax, Vintage FIFO LCF, and Canonical CFADS

## Summary

Phase 2B adds annual-aggregation tax computation to the clean financial engine. The engine
computes taxable income annually (not per-period), applies ATAD interest limitation at the
annual level, runs a FIFO vintage loss-carryforward ledger, computes annual CIT liability,
allocates cash tax payments to periods per TAX_YEAR_LAST_PERIOD timing, and produces
canonical CFADS = EBITDA − cash_tax_paid per period.

## Architecture

### Annual Tax Engine (`financial_engine/tax/`)

**`atad.py`** — Annual ATAD interest limitation
- `calculate_annual_atad(basis, policy)` → `AtadAnnualResult`
- `allocate_atad_to_periods(annual_result, period_interests)` → `AtadAnnualResult`
- Capacity = max(atad_ebitda_limit × annual_EBITDA, de_minimis_threshold)
- Chronological period allocation: H1 consumes capacity first

**`loss_ledger.py`** — Annual FIFO vintage ledger
- `run_annual_fifo_ledger(taxable_income_before_lcf, tax_year_indices, opening_inputs, lcf_years)`
- Expiry-before-use: vintages with `last_usable_tax_year < current_tax_year` expire first
- FIFO: oldest `origin_tax_year` consumed before newer vintages

**`engine.py`** — Phase 2B orchestration
- `calculate_tax(periods, tax_input)` → `TaxAndCfadsResult`
- Step 1: Aggregate periods → `TaxYearCalculationBasis` by `year_index`
- Step 2: Annual ATAD per tax year
- Step 3: Taxable income: `EBITDA − tax_dep − deductible_interest + other_reintegration`
  - Disallowed interest is NOT added back separately
- Step 4: Annual FIFO LCF
- Step 5: Annual CIT = `corporate_rate × max(0, taxable_income_after_lcf)`
- Step 6: Cash tax → last period of year + `cash_tax_payment_lag_periods`
- Step 7: `terminal_unpaid_tax_keur` for liabilities falling outside model horizon

### Input Contract

**`TaxCalculationInput`**:
- `policy: TaxPolicy` — properly typed
- `opening_loss_vintages: tuple[OpeningTaxLossVintageInput, ...]`
- `period_interest: tuple[PeriodInterestInput, ...]` — per-period senior/shl/other components
- `period_adjustments: tuple[PeriodTaxAdjustmentInput, ...]`

**`TaxCfadsModelInput`**:
- `operating: OperatingModelInput`
- `tax: TaxCalculationInput`

**`TaxPolicy`**:
- `corporate_rate`, `periods_per_tax_year`, `loss_carryforward_years`
- `atad_enabled`, `atad_ebitda_limit`, `atad_de_minimis_threshold_keur_annual`
- `cash_tax_timing: CashTaxTiming`, `cash_tax_payment_lag_periods`

### Result Contract

**`TaxAndCfadsSchedules`** (in `ProjectModelResult.tax_and_cfads`):
- `taxable_profit_keur`, `taxable_income_before_losses_audit_keur`, `taxable_profit_after_losses_audit_keur`
- `tax_keur`, `corporate_tax_cash_keur`, `cit_accrual_audit_keur`
- `cash_tax_bridge_reconciliation_keur` (= EBITDA − cash_tax, matches legacy TUHO bridge semantics)
- `cash_tax_current_period_audit_keur`
- `tax_loss_opening_audit_keur`, `tax_loss_closing_audit_keur`, `tax_loss_used_audit_keur`
- `fiscal_reintegration_audit_keur`, `tax_depreciation_audit_keur`
- `cf_after_tax_keur` (= EBITDA − cash_tax per period)
- `cfads_keur` (canonical CFADS = EBITDA − cash_tax, the primary deliverable)
- `terminal_unpaid_tax_keur: float` (scalar, not an array)

Waterfall rows (`r69_fcf_banks_keur`, `r84_fcf_junior_keur`, `r99_fcf_for_distribution_keur`,
`r102_fcf_for_shl_keur`, `fcf_for_shl_keur`) are NOT in the clean engine result contract.
They are declared as `unavailable_fields` in the Phase 2B candidate snapshot.

## Taxable Income Formula

```
taxable_income_before_lcf = EBITDA − tax_depreciation − deductible_interest
                           + other_fiscal_reintegration
```

Where `deductible_interest = gross_interest − ATAD_disallowed`. The disallowed portion is
NOT added back separately — it simply is not deducted.

Example: EBITDA=10000, tax_dep=2000, gross_interest=4000, deductible=3000, disallowed=1000
→ taxable = 10000 − 2000 − 3000 + 0 = 5000 ✓ (not 5000 + 1000 = 6000)

## Validation

`validate_tax_calculation_input()` returns error codes TAX001–TAX014:
- TAX001: `corporate_rate` outside [0, 1]
- TAX002: `periods_per_tax_year` ≤ 0
- TAX003: `loss_carryforward_years` < 0
- TAX004: `atad_ebitda_limit` outside [0, 1] (when atad_enabled)
- TAX005: `atad_de_minimis_threshold_keur_annual` < 0
- TAX006: `cash_tax_payment_lag_periods` < 0
- TAX007: opening vintage `amount_keur` invalid
- TAX008: opening vintage `origin_tax_year` not int
- TAX009: period interest component negative or non-finite
- TAX010: duplicate `period_index` in `period_interest`
- TAX011: `period_index` not in known model periods
- TAX012: duplicate `period_index` in `period_adjustments`
- TAX013: `other_fiscal_reintegration_keur` non-finite
- TAX014: `policy` is not a `TaxPolicy` instance

## Parity Profile: TAX_CFADS_V1

The `ComparisonProfile.TAX_CFADS_V1` profile compares 14 tax_and_cfads fields between
the legacy baseline and the Phase 2B candidate:

**Compared**: `taxable_profit_keur`, `taxable_income_before_losses_audit_keur`,
`taxable_profit_after_losses_audit_keur`, `cit_accrual_audit_keur`,
`cash_tax_current_period_audit_keur`, `corporate_tax_cash_keur`, `tax_keur`,
`cash_tax_bridge_reconciliation_keur`, `tax_loss_opening_audit_keur`,
`tax_loss_used_audit_keur`, `tax_loss_closing_audit_keur`, `tax_depreciation_audit_keur`,
`fiscal_reintegration_audit_keur`, `cf_after_tax_keur`.

**Declared unavailable** (not computed by Phase 2B):
`r69_fcf_banks_keur`, `r84_fcf_junior_keur`, `r99_fcf_for_distribution_keur`,
`r102_fcf_for_shl_keur`, `fcf_for_shl_keur`.

## Known Differences (Correction Ledger)

Documented in `finco_parity/corrections/tax_cfads_v1.json`. All differences are expected
and arise from:

1. **DEV001** — Annual vs per-period taxable income computation. The clean engine aggregates
   annually and prorates; the legacy computes per-period.
2. **DEV002** — Canonical TaxPolicy vs project-specific legacy parameters. TUHO uses
   fixture-backed depreciation and interest limitation; the clean engine uses adapter-based
   depreciation and exogenous interest from the baseline snapshot.
3. **DEV003** — ATAD fiscal reintegration: clean engine uses annual ATAD from canonical
   params; TUHO uses a hard-coded per-period fixture.
4. **DEV004** — `cash_tax_bridge_reconciliation_keur`: clean engine = EBITDA − cash_tax
   (matching TUHO bridge); non-TUHO legacy has 0 (field never set).
5. **DEV005** — `cf_after_tax_keur`: TUHO legacy retains pre-bridge waterfall value;
   clean engine uses EBITDA − cash_tax uniformly.
6. **DEV006** — `tax_depreciation_audit_keur`: TUHO uses 40-period fixture; clean engine
   uses adapter-based schedule.

## Test Coverage

46 tests in `tests/test_phase2b_tax_cfads.py` covering tests A–J:

- **A**: Zero-interest, no ATAD, no losses — CFADS = EBITDA − cash_tax; annual conservation
- **B**: Annual ATAD threshold logic — `calculate_annual_atad` + `allocate_atad_to_periods`
- **C**: Correct taxable income formula — no double ATAD addback
- **D**: FIFO vintage expiry — expiry-before-use, oldest-first consumption
- **E**: Immutability — `TaxPolicy`, `TaxCalculationInput`, `TaxCfadsModelInput` all frozen
- **F**: SAME_PERIOD cash-tax timing — total conservation holds
- **G**: Terminal unpaid tax — extreme lag pushes payments outside horizon
- **H**: Exogenous interest flows through — reduces taxable income by exact amount
- **I**: Validation codes TAX001–TAX014 — all codes reachable
- **J**: Four-baseline smoke — all four baselines run without error

## Scope Boundaries

Phase 2B does NOT implement:
- Debt sizing, DSCR/LLCR, DSRA, SHL, distributions, financial statements, IRR/MOIC/NPV
- Phase 2C (financing, financial statements, returns)
- Project-identity-aware tax parameters inside `financial_engine`
- Waterfall rows (r69, r84, r99, r102, fcf_for_shl)

## Files Changed

| File | Change |
|------|--------|
| `financial_engine/policies/tax.py` | Added `CashTaxTiming`, `TaxPolicy` (removed `expire_losses_before_use`) |
| `financial_engine/inputs.py` | Added `OpeningTaxLossVintageInput`, `PeriodInterestInput` (3-component), `TaxCalculationInput`, `TaxCfadsModelInput` |
| `financial_engine/tax/models.py` | Full rewrite: `TaxYearCalculationBasis`, `AtadAnnualResult`, `TaxLossVintage`, `TaxAnnualLedgerEntry`, `TaxAnnualResult`, `PeriodCashTaxResult`, `TaxAndCfadsResult` |
| `financial_engine/tax/atad.py` | Full rewrite: annual ATAD + chronological period allocation |
| `financial_engine/tax/loss_ledger.py` | Full rewrite: annual vintage FIFO ledger |
| `financial_engine/tax/engine.py` | Full rewrite: annual tax orchestration |
| `financial_engine/results.py` | `TaxAndCfadsSchedules`: removed waterfall rows, added `cfads_keur`, `terminal_unpaid_tax_keur` |
| `financial_engine/validation.py` | Added `validate_tax_calculation_input()` with TAX001–TAX014 |
| `financial_engine/provenance.py` | Added `compute_tax_cfads_fingerprint()` |
| `financial_engine/orchestrator.py` | Added `run_tax_cfads_model()` |
| `finco_parity/profiles.py` | Added `TAX_CFADS_V1` comparison profile |
| `finco_parity/financial_engine_tax_cfads_candidate.py` | New Phase 2B candidate provider |
| `finco_parity/check_financial_engine_tax_cfads.py` | New Phase 2B parity CLI |
| `finco_parity/corrections/tax_cfads_v1.json` | Correction ledger (6 systematic deviations) |
| `tests/test_phase2b_tax_cfads.py` | 46 tests (A–J) |
| `.github/workflows/phase2b_tax_cfads_check.yml` | 7-gate CI workflow |
