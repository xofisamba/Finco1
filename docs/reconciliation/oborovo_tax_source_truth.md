# Oborovo Tax Source Truth — Stage C3B1 Diagnostic Report

## 1. Base Commit and Branch

| Item | Value |
|------|-------|
| Base SHA | `b11e5bf7b9ab60bae174081e7d9f8541190bf371` |
| Branch | `stage-c3b1-oborovo-tax-source-truth` |
| Final verdict | `C3B1_TAX_BLOCKED_BY_INTEREST_DEPENDENCY` |

## 2. Changed Files

| File | Change |
|------|--------|
| `finco_recon/extract_oborovo_excel.py` | Bumped to v2.0.0; dual-load (formula + data); added `_read_pl_tax_formulas` |
| `tests/fixtures/excel_oborovo_financial_truth.json` | Regenerated with `tax` section (19 rows, proved identities) |
| `tests/test_stage_c3b1_oborovo_tax_source_truth.py` | Created — 75 tests across 15 groups (A–O) |
| `docs/reconciliation/oborovo_tax_source_truth.md` | This file |

## 3. Workbook SHA

```
15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920
```

Source file: `d49af8ee-20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm`

## 4. Source Map — Key P&L Tax Rows

Sheet: **FID deck outputs** (P&L tab)

| Row | Label | Formula (period 0) | Proved constant |
|-----|-------|-------------------|----------------|
| 13 | Depreciation | `=Dep!G22` | — references Dep sheet |
| 16 | EBIT | `=G13-G14-G15` | — |
| 24 | Senior interest | `=senior!G43` | — |
| 27 | SHL interest | `-G26*G25/2` | — |
| 30 | Financial earnings | formula bundles -SD - SHL + other | — |
| 32 | EBT | `=G16+G30` | — |
| 34 | Fiscal reintegration | `=-G54` | = full SHL (thin_cap=False) |
| 35 | Taxable income | `=G32+G34` | — |
| 36 | LCF opening | SUMIF rolling | B36 = 5 periods |
| 37 | Allocated losses | `=IF(AND(G36<=0, G32>0), ...)` | EBT > 0 required |
| 38 | New losses this period | `=MIN(G35, 0)` | — |
| 39 | Carriable forward | SUMIF rolling 5 periods | mirrors row 36 |
| 41 | Taxable profit | `=G35-G37` | — |
| 43 | CIT | `=MAX(SUM(F41:G41),0)*B43*(G4>0)*(MOD(G4,2)=0)` | B43 = 0.10 |
| 54 | FR helper | `=-MIN(MAX(G57,G58)+G59, G27)` | = -SHL when thin_cap=False |
| 56 | Thin cap rule | `=BS!G45` | = False (always) |
| 57 | Thin cap amount | 0 when thin_cap=False | — |
| 58 | ATAD 30% amount | 0 when thin_cap=False | — |
| 59 | Non-deductible SHL | `-G27 * C59 * D59` | C59=1.0, D59=True |

## 5. Tax Depreciation Diagnostic

**Classification: `TAX_DEP_BOTH_ARE_INCOMPLETE`**

| Dimension | Value (kEUR) |
|-----------|-------------|
| Excel book depreciation (via EBIT) | 57,973 |
| Python adapter tax_dep (hard CAPEX only) | 55,999 |
| Delta | −1,974 |
| Delta components | IDC 1,086 + commit fees 188 + bank fees 477 + VAT 222 |

- Factory (`app/project_factories.py` lines 355–356) declares `TaxDepreciationMode.BOOK_BASED_PERCENTAGE` with `tax_deductible_book_dep_pct=1.0` — correct intent.
- Clean adapter (`financial_engine/adapters/project_inputs.py`) ignores this flag and uses hard-CAPEX-only basis — wrong implementation.
- Workbook uses book depreciation (via EBIT path, row 16 ← row 13 ← `Dep!G22`), which includes IDC and financing fees capitalized into the asset value.

## 6. Taxable Income Formula (Proved)

```
taxable_income = EBT + fiscal_reintegration

where:
  EBT = EBIT + financial_earnings
  fiscal_reintegration = full SHL interest   (because thin_cap = BS!G45 = False always)

Therefore:
  taxable_income = EBIT + financial_earnings + SHL
                 = EBIT - senior_interest - SHL + small_financial + SHL
                 = EBIT - senior_interest + small_financial

During debt tenor: small_financial ≈ 0  →  TI ≈ EBIT - senior_interest (< 0.01 kEUR)
After repayment:   small_financial = DSRA interest ≈ 2.7 kEUR/period
```

The identity `TI = EBT + FR` holds to machine precision (max delta = 0.0 across all 61 periods, confirmed from cached workbook values).

## 7. Interest Dependency Result

**Classification: `INTEREST_DEPENDENCY_BLOCKS_TAX`**

- Senior debt interest is the only deductible interest (FR = full SHL).
- Senior debt interest is a Phase 2C output (`senior!G43`).
- No standalone Phase 2B tax calculation can be correct without senior interest.
- Lifetime senior interest: 20,133 kEUR. Lifetime SHL interest: 32,105 kEUR.

## 8. Tax Loss Opening Balance and Vintage

- Opening balance at model start: **0 kEUR** (no pre-existing tax losses).
- `finco_parity/tax_reference_inputs.py` → `build_opening_loss_vintages("oborovo")` → empty tuple.
- `OpeningTaxLossVintageInput.origin_tax_year` docstring says "0-based index" but all callers pass calendar years → **`TAX_LOSS_YEAR_CONTRACT_BUG`** (stale docstring, not a runtime error for Oborovo since there are no opening vintages).

## 9. Tax-Year Grouping Result

**Classification: `TAX_YEAR_GROUPING_MISMATCH`**

| Dimension | Excel | Python |
|-----------|-------|--------|
| Tax year unit | 2-period model-year pair (H1+H2) | Calendar year (Jan–Dec split) |
| CIT timing | Even-indexed operating periods only | `MOD(period_index,2)=0` periods |
| LCF window | 5 periods (not 5 calendar years) | 5 tax years (`lcf_years=5`) |

The 5-period Excel window and the Python 5-year LCF will produce different boundaries when a model year spans a calendar year boundary.

## 10. Current Tax Result

- Formula: `CIT = MAX(sum(TI[N-1] + TI[N]), 0) × 10% × (even period) × (operating period)`
- Rate: B43 = **10%** (confirmed from workbook)
- CIT computed in even-indexed operating periods only (pairs: p3+p4, p5+p6, …)
- Lifetime CIT: **10,443 kEUR** (confirmed from cached values)

## 11. Cash Tax Timing Result

- `cash_tax_timing = TAX_YEAR_LAST_PERIOD` — cash tax coincides with the second period of each 2-period model year.
- `cash_tax_payment_lag_periods = 0` — no deferral.
- No CIT in construction periods (zero TI by formula, period_index condition).

## 12. Period-by-Period Delta Summary

Not applicable to C3B1 (diagnostic only; no production tax numbers produced). Python currently produces incorrect tax because the adapter ignores `BOOK_BASED_PERCENTAGE` and lacks senior interest input.

## 13. Material Unresolved Source Gaps

| Gap | Classification |
|-----|---------------|
| `B_col` for the LCF SUMIF reference years confirmed from workbook | RESOLVED (B36=5) |
| ATAD 30% threshold constant | RESOLVED (disabled; rows 57/58 = 0 for Oborovo) |
| Tax depreciation provenance | RESOLVED (Dep!G22 = book dep including financing costs) |
| Formula evidence for workbook | RESOLVED (dual-load confirmed formula text + cached values) |

No `SOURCE_UNRESOLVED` entries remain.

## 14. Current Python Architecture Findings

### A. TAX-DEPRECIATION MODE (`TAX_DEP_BOTH_ARE_INCOMPLETE`)

Factory declares `BOOK_BASED_PERCENTAGE=1.0` but the clean adapter ignores it:

```python
# app/project_factories.py lines 355-356
tax_depreciation_mode=TaxDepreciationMode.BOOK_BASED_PERCENTAGE,
tax_deductible_book_dep_pct=1.0,
```

The adapter builds tax_dep from hard CAPEX, not `book_dep × pct`.

### B. OPENING TAX-LOSS YEAR SEMANTICS (`TAX_LOSS_YEAR_CONTRACT_BUG`)

`OpeningTaxLossVintageInput.origin_tax_year` docstring:
> "0-based index of the tax year in which the loss was generated"

All callers pass calendar years (e.g., 2022, 2023). The ledger compares against calendar-year integers. The docstring is wrong; passing a relative index would cause immediate expiry.

### C. INTEREST DEPENDENCY

`financial_engine/tax/engine.py` computes:
```
taxable_income = EBITDA - tax_dep - deductible_interest + fiscal_reintegration
```

This requires `deductible_interest` = senior interest, which is only available after Phase 2C debt calculation.

## 15. Anti-Calibration Findings

- No hardcoded 10,443 value in `financial_engine/`.
- No `approved_delta`, `tax.*plug`, or `cit.*target` patterns in `financial_engine/`.
- No `oborovo` string in `financial_engine/` (project dispatch not permitted there).
- Parity layer (`finco_parity/`) uses `baseline_id` routing — permitted.

## 16. Exact Recommended C3B2 Scope

Minimum changes required (no production freeze violations):

1. **Fix adapter**: `tax_dep = book_dep × tax_deductible_book_dep_pct` when mode is `BOOK_BASED_PERCENTAGE`. This is a 1-line fix in `financial_engine/adapters/project_inputs.py`.

2. **Pass senior interest from Phase 2C**: Wire `PeriodInterestInput.senior_interest_keur` from the Phase 2C debt result into `TaxCalculationInput.period_interest`. Requires Phase 2C to run first.

3. **Add SHL back via fiscal reintegration**: Populate `PeriodTaxAdjustmentInput.other_fiscal_reintegration_keur` with the SHL interest for each period (no-ATAD path, thin_cap=False).

4. **Fix `origin_tax_year` docstring** in `OpeningTaxLossVintageInput` (stale; no runtime impact for Oborovo since no opening vintages).

## 17. Interest Prerequisite

**Yes — Phase 2C is a prerequisite for C3B2.**

Senior interest cannot be derived without the Phase 2C debt amortization schedule. C3B2 must accept Phase 2C results as an input.

## 18. Test Matrix

| Test group | Tests | Result |
|-----------|-------|--------|
| A — Provenance | 5 | PASS |
| B — Source inventory | 5 | PASS |
| C — Tax depreciation source | 5 | PASS |
| D — Taxable income identity | 4 | PASS |
| E — Interest dependency | 5 | PASS |
| F — Tax loss roll-forward | 6 | PASS |
| G — Tax-year fragmentation | 4 | PASS |
| H — Current tax identity | 5 | PASS |
| I — Cash tax timing | 4 | PASS |
| J — Sign conventions | 3 | PASS |
| K — Clean/legacy source | 4 | PASS |
| L — Financial freeze | 5 | PASS |
| M — No project identity dispatch | 4 | PASS |
| N — No target plug | 3 | PASS |
| O — C3A upstream freeze | 5 | PASS |
| **Total** | **75** | **75 PASS** |

## 19. Introduced vs Pre-Existing Failures

Regression run against: `test_stage_c3a_clean_pnl_through_ebit.py`, `test_phase2b_tax_cfads.py`, `test_phase2c_senior_debt.py`

| Test file | Result | Classification |
|-----------|--------|---------------|
| `test_stage_c3a_clean_pnl_through_ebit.py` | 137 passed | — |
| `test_phase2c_senior_debt.py` | 158 passed | — |
| `test_phase2b_tax_cfads.py::test_w_correction_aware_four_baseline[oborovo]` | FAIL | **PRE_EXISTING_ON_BASE** (verified: fails on b11e5bf7 with no C3B1 changes) |
| All other `test_phase2b_tax_cfads.py` | PASS | — |

No failures introduced by C3B1.

## 20. Confirmation: No Production Formula Changed

This stage is a **source diagnostic only**. The following files were not modified:

- `financial_engine/` — no changes
- `finco_parity/` — no changes
- `app/project_factories.py` — no changes
- `app/orchestrator.py` — no changes
- Any workbook or scenario file — no changes

Only `finco_recon/extract_oborovo_excel.py` (extraction tooling), the regenerated fixture, and the new test file were added.

---

## Final Verdict

```
C3B1_TAX_BLOCKED_BY_INTEREST_DEPENDENCY
```

The Oborovo taxable income formula is fully proved from workbook source: `TI = EBT + FR = EBIT - senior_interest + small_financial_income`. Fiscal reintegration = full SHL (thin_cap=False, ATAD disabled). The 5-period rolling SUMIF LCF window is proved. CIT rate = 10%, even-periods-only timing is proved. Cash tax = same period, no lag.

The blocker is that senior interest (the sole deductible interest) is a Phase 2C output and cannot be computed independently in Phase 2B. C3B2 is therefore gated on Phase 2C completion and must wire senior interest from the debt schedule into the tax engine.
