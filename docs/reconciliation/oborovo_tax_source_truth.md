# Oborovo Tax Source Truth — Stage C3B1 Diagnostic Report

**Extractor version**: 3.0.0 (dual-load: `data_only=False` for formula text, `data_only=True` for cached values)

## 1. Base Commit and Branch

| Item | Value |
|------|-------|
| Base SHA | `b11e5bf7b9ab60bae174081e7d9f8541190bf371` |
| Branch | `stage-c3b1-oborovo-tax-source-truth` |
| Final verdict | `C3B1_TAX_BLOCKED_BY_INTEREST_DEPENDENCY` |

## 2. Changed Files

| File | Change |
|------|--------|
| `finco_recon/extract_oborovo_excel.py` | v3.0.0; dual-load; 24 rows; CIT authority; 61-period machine-readable diagnostic |
| `tests/fixtures/excel_oborovo_financial_truth.json` | Regenerated; `tax.period_diagnostic`, `tax.cit_row43_vs_row44_authority`, 24 rows |
| `tests/test_stage_c3b1_oborovo_tax_source_truth.py` | 91 tests (A–P); financial-freeze tests compare base SHA vs HEAD |
| `docs/reconciliation/oborovo_tax_source_truth.md` | This file |

## 3. Workbook SHA

```
15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920
```

Source file: `d49af8ee-20260414_BP_Oborovo_Sensitivity_FINAL_for_PPT.xlsm`

## 4. Source Map — Corrected P&L Row Inventory

Sheet: **P&L** (not "FID deck outputs" — that is a separate summary tab)

| Row | Label | Exact formula (period 0 = col G) | Notes |
|-----|-------|----------------------------------|-------|
| 8 | Total Revenues | `=CF!G23` | — |
| 10 | Operating Expenses | `=-CF!G49+$B10*(G$3=0)` | — |
| 11 | Local Tax | `=-Macro!G46` | — |
| 12 | WHT on Interests | `=-CF!G113` | — |
| 13 | **Depreciation** | `=Dep!G30` | `Dep!G30 = SUM(G7:G28)` = total book dep **including financing costs**. NOT Dep!G22 (one item) or Dep!G31 (unlevered). |
| 14 | Total Expenses | `=SUM(G10:G13)` | Sum of rows 10–13 |
| 16 | **EBIT** | `=G8-G14` | Total Revenues − Total Expenses. NOT `=G13-G14-G15`. |
| 19 | Interests from Reserve Account | `=(G$3>0)*$B19*(CF!F105+CF!F91)*G$6` | B19=0.01. **Zero for all Oborovo periods** — Oborovo earns no DSRA interest. |
| 20 | Interests from Cash | `=(CF!F144>0)*$B19*CF!F144*G$5*G$6` | Small positive cash-interest in periods 41+ (≈2.77 kEUR/period) after debt repayment. |
| 21 | Financial revenue adj. | `=-SUM(G19:G20)*$B21*G$6` | B21=0; zero. |
| 24 | **Senior Interests** | `=DS!G53-CF!G83` | DS!G53 = net interest; CF!G83 = `=-DS!G35` (VAT facility, always 0). Effective formula = DS!G53. |
| 27 | SHL Interests | `=DS!G125` | Positive convention (expense > 0). |
| 30 | **Financial Earnings** | `=SUM(G19:G21)-SUM(G24:G28)` | Bundles financing revenues minus all financing expenses. Negative during debt tenor. |
| 32 | EBT | `=G16+G30` | — |
| 34 | **Fiscal Reintegration (display)** | `=-G54` | Sign flip of helper. Positive value = addback to taxable income. |
| 35 | **Taxable Income** | `=G34+G32` | FR + EBT. Exact zero residual proved. |
| 36 | Losses N-1 opening | `=SUMIF(IF(G4<=$B$36,$F35:F35,F35:OFFSET(F35,0,-$B$36+1)),"<0")+SUM($F$37:F$37)` | B36=5 periods rolling window + cumulative utilized losses. |
| 37 | Allocated Losses | `=IF(AND(G36<=0,G32>0),MIN(ABS(G36),G32),0)` | **Uses G32 (EBT), NOT G35 (TI)** — losses allocated only when EBT > 0. |
| 38 | Losses N | `=MIN(G37+G36,0)` | Current period net losses. |
| 39 | Carriable Losses | `=MIN(G38,F35*$B37)` | B37=1; F35=prior-period TI. Caps carriable by prior-period TI. |
| 41 | Taxable Profit N | `=-G37+G35` | TI minus allocated losses. |
| **43** | **CIT formula** | `=MAX(SUM(F41:G41),0)*$B43*(G4>0)*(MOD(G4,2)=0)` | B43=0.10. Dynamic formula row. |
| **44** | **CIT → Net Income** | `=Macro!G40` | `=IF(Production_Scenario=base_scenario,Macro!G38,Macro!G39)`. Hardcoded period values matching row 43. |
| 46 | Net Income | `=G32-G44` | Uses **row 44**, NOT row 43. |
| 54 | FR helper | `=MIN(MAX(G57,G58)+G59,G27)` | No leading minus here — row 34 applies `=-G54`. Cached value is negative. |
| 56 | Thin Cap Rule | `=BS!G45` | = False always for Oborovo. |
| 57 | Thin Cap amount | `=IF(G56,MAX(G27-$C$57,0),0)` | C57=3000 kEUR threshold. Zero (thin_cap=False). |
| 58 | ATAD 30% amount | `=IF(G56,MAX(G27-$C$58*(G32-G30+G13),0),0)` | C58=0.30. Zero (thin_cap=False). |
| 59 | Non-deductible SHL | `=-G$27*($C$59)*$D$59` | C59=1.0, D59=True → full SHL non-deductible. |

## 5. Formula Discrepancies Resolved (vs. Prior Delivery)

| Claim in prior delivery | Correct value |
|------------------------|---------------|
| Dep!G22 | **Dep!G30** (`=SUM(G7:G28)` total book dep) |
| EBIT = `=G13-G14-G15` | **`=G8-G14`** (Total Revenues − Total Expenses) |
| senior = `=senior!G43` | **`=DS!G53-CF!G83`** |
| SHL = `-G26*G25/2` | **`=DS!G125`** |
| FR helper = `=-MIN(...)` | **`=MIN(...)` (no leading minus)** — row 34 holds the sign flip `=-G54` |

## 6. CIT Row 43 vs Row 44 Authority

**Resolved: both produce identical values; risk is staleness of Macro hardcoded values.**

| Dimension | Value |
|-----------|-------|
| Row 43 formula | `=MAX(SUM(F41:G41),0)*$B43*(G4>0)*(MOD(G4,2)=0)` — formula-driven |
| Row 44 formula | `=Macro!G40 = IF(base,Macro!G38,Macro!G39)` — hardcoded scenario lookup |
| Row 43 vs 44 max delta | **0.000** (machine precision match in current workbook snapshot) |
| Net Income uses | Row 44 |
| CF cash tax (row 77) | `=-'P&L'!G44` (negated row 44) |
| Lifetime CIT (row 43) | **10,443.088 kEUR** |
| Risk | Macro rows 38/39 are hardcoded. If P&L formulas change, rows 38/39 may not auto-update. |

## 7. Tax Depreciation Diagnostic

**Classification: `TAX_DEP_BOTH_ARE_INCOMPLETE`**

| Dimension | Value (kEUR) |
|-----------|-------------|
| Excel P&L dep (Dep!G30 = SUM G7:G28) | 57,973.053 |
| Dep!G31 (unlevered, SUM G7:G22) | 55,999.086 |
| Python adapter (hard CAPEX only) | ≈ 55,999 |
| Gap (levered vs unlevered) | **1,973.967** |
| Gap components | IDC 1,086 + commit fees 188 + bank fees 477 + VAT 222 |

P&L row 13 = `Dep!G30` (levered total, rows 7–28). Python adapter uses hard-CAPEX basis (~Dep!G31). Factory correctly declares `BOOK_BASED_PERCENTAGE=1.0` but adapter ignores it.

## 8. Taxable Income Formula (Proved to Machine Precision)

```
TI (row 35) = EBT (row 32) + FR (row 34)             [exact, max delta = 0.000]

FR (row 34) = -G54
G54 = MIN(MAX(G57, G58) + G59, G27)
  with thin_cap = BS!G45 = False:
    G57 = 0, G58 = 0
    G54 = MIN(G59, G27)
    G59 = -G27 × C59 × D59 = -G27 × 1.0 × True = -G27
    G54 = MIN(-G27, G27) = -G27
    FR = -G54 = G27 = SHL interest

Therefore:
  TI = EBT + SHL = (EBIT + fin_earn - SD - SHL) + SHL = EBIT + fin_earn - SD

During debt tenor (SD > 0):
  fin_earn ≈ 0 (rows 19-21 all zero for Oborovo)  →  TI ≈ EBIT - SD  (< 0.02 kEUR gap)

After debt repayment (SD = 0, SHL = 0, FR = 0):
  fin_earn = row 20 (Interests from Cash) ≈ +2.77 kEUR/period
  TI = EBIT + cash_interest_on_surplus_cash

Note: Oborovo earns ZERO interest on DSRA (row 19 = 0). Cash interest (row 20) is on
surplus cash balance after debt repayment, not on DSRA.
```

## 9. Interest Dependency Result

**Classification: `INTEREST_DEPENDENCY_BLOCKS_TAX`**

- Senior interest (DS!G53) = sole deductible interest. Lifetime: **20,133.079 kEUR**.
- SHL interest (DS!G125) = fully non-deductible (FR = SHL always). Lifetime: **32,104.911 kEUR**.
- Phase 2C frozen fixture matches Excel DS!G53 to 0.0000 kEUR for all 43 operating periods.
- No standalone Phase 2B tax computation can be correct without senior interest.

## 10. Tax Loss Opening Balance and Vintage

- Opening balance at period 0: **0 kEUR** (proved from row 36 cached values).
- `build_opening_loss_vintages("oborovo")` → empty tuple.
- **`TAX_LOSS_YEAR_CONTRACT_BUG`**: `OpeningTaxLossVintageInput.origin_tax_year` docstring says "0-based index"; all callers pass calendar years; ledger compares against calendar years. Docstring is wrong. No runtime impact for Oborovo (zero vintages), but stale docstring is a C3B2 fix.

## 11. Tax-Year Grouping Result

**Model-year pairing (Excel) vs calendar-year splitting (Python):**

| Period | BoP | EoP | Model-year group |
|--------|-----|-----|-----------------|
| 0 | 2029-06-29 | 2030-06-30 | Construction |
| 1 | 2030-07-01 | 2030-12-31 | Model year 1 (H2) |
| 2 | 2031-01-01 | 2031-06-30 | Model year 1 (H1) — CIT in this period |
| 3 | 2031-07-01 | 2031-12-31 | Model year 2 (H2) |
| 4 | 2032-01-01 | 2032-06-30 | Model year 2 (H1) — CIT |
| … | … | … | … |
| 6 | 2033-01-01 | 2033-06-30 | Model year 3 (H1) — CIT |

CIT fires in even periods (MOD(G4,2)=0, G4>0) summing taxable profit[i-1]+taxable profit[i]. Each pair spans H2_year-N + H1_year-(N+1) — straddles calendar year boundary.

Python splits on Jan 1, producing tax_year 2033 = portion of H2-2032 + portion of H1-2033.

LCF: 5-period window (not 5 calendar years) — B36=5.

## 12. Current Tax Result

- Row 43: `MAX(SUM(F41:G41), 0) × 10% × (G4>0) × (MOD(G4,2)=0)`
- Row 44: `=Macro!G40` — same values, hardcoded scenario routing
- Both rows match to machine precision (delta = 0.000 kEUR)
- Lifetime CIT: **10,443.088 kEUR**
- CIT present in periods 6, 8, 10, 12, … (even operating periods)
- LCF delays first CIT to period 6 (periods 2, 4 have accumulated losses not yet expired)

## 13. Cash Tax Timing

- Cash tax = CF row 77 = `=-'P&L'!G44` (negated row 44)
- CF row 77 matches row 43/44 in sign and magnitude
- Cash tax coincides with P&L CIT period (no lag, no deferral)
- Python policy: `cash_tax_timing = TAX_YEAR_LAST_PERIOD`, `cash_tax_payment_lag_periods = 0`

## 14. Period-by-Period Diagnostic

Machine-readable table stored in `tax.period_diagnostic` (61 entries). Key periods:

| Period | EBIT | SD | SHL | FR | TI | LCF_open | Alloc | TP | CIT | TI=EBT+FR delta |
|--------|------|----|----|----|----|----------|-------|-----|-----|----------------|
| 0 | 0.000 | 0.000 | 1169.662 | 1169.662 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| 1 | 1084.327 | 1303.483 | 636.809 | 636.809 | -219.157 | 0.000 | 0.000 | -219.157 | 0.000 | 0.000 |
| 2 | 1066.647 | 1254.234 | 638.365 | 638.365 | -187.587 | -219.157 | 0.000 | -187.587 | 0.000 | 0.000 |
| 6 | 1191.408 | 1098.692 | 690.075 | 690.075 | 92.716 | -581.719 | 0.000 | 92.716 | 8.904 | 0.000 |
| 7 | 1186.773 | 1079.392 | 688.027 | 688.027 | 107.381 | -362.562 | 0.000 | 107.381 | 0.000 | 0.000 |
| 11 | 1264.498 | 926.227 | 662.542 | 662.542 | 338.271 | 0.000 | 0.000 | 338.271 | 0.000 | 0.000 |
| 41 | 3140.941 | 0.000 | 0.000 | 0.000 | 3143.713 | 0.000 | 0.000 | 3143.713 | 0.000 | 0.000 |
| 60 | 3563.111 | 0.000 | 0.000 | 0.000 | 3565.846 | 0.000 | 0.000 | 3565.846 | 376.898 | 0.000 |

Full table: see `tests/fixtures/excel_oborovo_financial_truth.json` → `tax.period_diagnostic`.

## 15. Material Unresolved Source Gaps

**None.** All 24 rows have formula evidence from dual-load. Resolved items:

| Item | Status |
|------|--------|
| Dep sheet row authority | RESOLVED: Dep!G30 (not G22, not G31) |
| EBIT formula | RESOLVED: `=G8-G14` |
| Senior interest source | RESOLVED: `=DS!G53-CF!G83` |
| FR helper sign | RESOLVED: helper=`=MIN(...)` (positive stored negative); display=`=-G54` |
| CIT row 43 vs 44 | RESOLVED: identical values; Macro hardcoded; row 44 feeds Net Income |
| DSRA vs cash interest | RESOLVED: row 19=0 for Oborovo; row 20 = cash interest post-repayment |
| LCF formula | RESOLVED: SUMIF + SUM($F$37:F$37) accumulated utilization term |

## 16. Current Python Architecture Findings

### A — `TAX_DEP_BOTH_ARE_INCOMPLETE`
Factory: `BOOK_BASED_PERCENTAGE=1.0` (correct). Adapter: hard-CAPEX-only (ignores flag). Delta: 1,974 kEUR.

### B — `TAX_LOSS_YEAR_CONTRACT_BUG`
`origin_tax_year` docstring says "0-based" but callers and ledger use calendar years.

### C — `INTEREST_DEPENDENCY_BLOCKS_TAX`
`financial_engine/tax/engine.py` requires `deductible_interest` = senior interest (Phase 2C output).

### D — `TAX_YEAR_GROUPING_MISMATCH`
Excel: model-year pairs (H2+H1). Python: calendar-year Jan-Dec split. LCF: 5 periods vs 5 years.

### E — `CIT_ROUTING_FRAGILITY`
Row 43 (formula) ≠ production authority. Row 44 (Macro hardcoded) is actual authority. Macro may become stale if upstream formulas change.

## 17. Anti-Calibration Findings

- No `10443` or `10,443` hardcoded in `financial_engine/`
- No `approved_delta`, `tax.*plug`, `cit.*target` patterns in `financial_engine/`
- No `oborovo` string in `financial_engine/`
- Parity layer (`finco_parity/`) uses `baseline_id` routing — permitted

## 18. Exact Recommended C3B2 Scope

Minimum changes required:

1. **Fix adapter** (`financial_engine/adapters/project_inputs.py`): when `tax_depreciation_mode = BOOK_BASED_PERCENTAGE`, compute `tax_dep = book_dep × tax_deductible_book_dep_pct` (1-line fix). This eliminates the 1,974 kEUR tax dep gap.

2. **Wire senior interest from Phase 2C**: pass `PeriodInterestInput.senior_interest_keur` from Phase 2C frozen debt schedule for each operating period.

3. **Add SHL fiscal reintegration**: populate `PeriodTaxAdjustmentInput.other_fiscal_reintegration_keur = SHL_interest` for each period (thin_cap=False path; full SHL is non-deductible).

4. **Fix LCF semantics**: Python uses 5 tax-year LCF; Excel uses 5-period window. For Oborovo this creates a timing difference in LCF expiry. Recommended fix: set `loss_carryforward_years = 3` (covers 5 operating periods in a ~2.5-year span) OR accept the difference as a known approximation.

5. **Fix `origin_tax_year` docstring** in `financial_engine/inputs.py` (no runtime impact for Oborovo; stale docstring only).

6. **Add CIT model-year pairing option**: Python uses calendar-year CIT; Excel uses H2+H1 model-year pairs. This produces different annual taxable profit sums when TI varies significantly across H1/H2. Recommended scope: document as known approximation with < 1% impact for Oborovo; defer to C3B3 if exact parity required.

## 19. Interest Prerequisite

**Yes — Phase 2C is required before C3B2 can produce correct tax numbers.**

## 20. Test Matrix

| Group | Description | Count | Result |
|-------|-------------|-------|--------|
| A | Provenance + new sections | 9 | PASS |
| B | Source row inventory (corrected) | 15 | PASS |
| C | Tax dep source | 5 | PASS |
| D | Taxable income identity | 6 | PASS |
| E | Interest dependency + Phase 2C vs Excel | 5 | PASS |
| F | Tax loss roll-forward | 6 | PASS |
| G | Tax-year fragmentation (corrected) | 3 | PASS |
| H | Current tax identity | 4 | PASS |
| I | Cash tax timing + P&L vs CF separation | 5 | PASS |
| J | Sign conventions | 4 | PASS |
| K | Clean/legacy source | 5 | PASS |
| L | Financial freeze (base SHA vs HEAD) | 6 | PASS |
| M | No project identity dispatch | 3 | PASS |
| N | No target plug | 2 | PASS |
| O | C3A upstream freeze | 4 | PASS |
| P | Failure classification | 3 | PASS |
| **Total** | | **91** | **91 PASS** |

## 21. Introduced vs Pre-Existing Failures

| Test file | Outcome | Classification |
|-----------|---------|---------------|
| `test_stage_c3a_clean_pnl_through_ebit.py` | 129 PASS | — |
| `test_phase2c_senior_debt.py` | PASS (subset) | — |
| `test_phase2b_tax_cfads.py::test_w_correction_aware_four_baseline[oborovo]` | FAIL | **PRE_EXISTING_ON_BASE** |

**0 failures introduced by C3B1.**

GitHub Actions workflow failures on PR HEAD:
- `test_w_correction_aware_four_baseline[oborovo]`: **PRE_EXISTING_ON_BASE** (verified via `git stash` test on b11e5bf7).

## 22. No Production Formula Changed

Confirmed. Files changed vs base `b11e5bf7`:
- `finco_recon/extract_oborovo_excel.py` (extractor tooling only)
- `tests/fixtures/excel_oborovo_financial_truth.json` (regenerated)
- `tests/test_stage_c3b1_oborovo_tax_source_truth.py` (tests only)
- `docs/reconciliation/oborovo_tax_source_truth.md` (this file)

`financial_engine/`, `finco_parity/`, `app/`, all workbook files: **unchanged**.

---

## Final Verdict

```
C3B1_TAX_BLOCKED_BY_INTEREST_DEPENDENCY
```

All 22 source evidence items are resolved. Taxable income formula is proved to machine precision from dual-load workbook formulas and cached values. The blocker is senior interest (DS!G53): a Phase 2C output required for correct TI = EBIT − SD. C3B2 is gated on Phase 2C. Minimum C3B2 scope: 6 items (expanded from prior 3-item scope to include LCF period semantics, model-year CIT approximation documentation, and CIT routing fragility).
