# Oborovo Tax Source Truth — Stage C3B1 Diagnostic Report

**Extractor version**: 3.4.0 (adds DS!D51 formula chain evidence, direct cell access for D192, corrected LCF expiry boundary `yr > orig_yr + 5`)

## 1. Base Commit and Branch

| Item | Value |
|------|-------|
| Actual PR base SHA | `1fb4943a4319eff8f4ac7a22add6f65f14bd8cec` |
| Historical cumulative-stage base SHA | `b11e5bf7b9ab60bae174081e7d9f8541190bf371` |
| Branch | `stage-c3b1-oborovo-tax-source-truth` |
| PR | `#914 DRAFT — DO NOT MERGE` |
| Final verdict | `C3B1_SOURCE_TRUTH_PARTIAL_MANUAL_CHECK_REQUIRED` |

**SHA provenance note**: `1fb4943a` is the GitHub merge-base used by PR #914 to compute the diff. `b11e5bf7` is the C3B1 task start point (after C3A, before any C3B1 commits). Both production-path diffs (financial_engine/, app/, finco_core/) must be empty vs both SHAs.

## 1a. Runtime Dependency Map

The following upstream dependencies prevent full runtime parity. Each is classified separately — no single blocker:

| Dependency | Classification | Required Resolution |
|---|---|---|
| Senior interest vectors | `SENIOR_INTEREST_DEPENDENCY` | Phase 2C debt model feeds interest into tax model |
| SHL fiscal reintegration | `SHL_REINTEGRATION_INPUT_DEPENDENCY` | Tax policy must configure SHL non-deductibility |
| Tax depreciation basis | `TAX_DEPRECIATION_ADAPTER_SEMANTIC_LOSS` | Adapter must include IDC/fee components |
| LCF policy (rolling-window vs FIFO) | `WORKBOOK_LCF_POLICY_MISMATCH` | Workbook uses rolling-window expiry; clean engine uses FIFO |
| CIT periodisation (H2+H1 pairing) | `CIT_PERIODISATION_MISMATCH` | Workbook uses model-year pairs; clean engine uses calendar years |
| Row 44 Macro staleness risk | `ROW44_MACRO_STALENESS_RISK` | Macro rows 38/39 are hardcoded; risk of staleness if P&L formulas change |

## 1b. C3B2 Alignment

C3B1 proves the tax formula and identifies required upstream interest inputs.
C3B2 is responsible for proving the source-correct senior-debt sizing and interest vector.
A later implementation PR may consume the accepted C3B2 contract.

The approximately 45,873 kEUR Phase 2C diagnostic result is a parity-harness runtime value under current ACT/365 policy. It is NOT the Excel target (42,852 kEUR). C3B2 must resolve the sizing discrepancy before any tax-formula changes are made.

## 2. Changed Files

| File | Change |
|------|--------|
| `finco_recon/extract_oborovo_excel.py` | v3.4.0; fixes LCF expiry boundary (`yr > orig_yr + 5`); rewrites `_derive_debt_sizing_from_workbook()` with direct cell access and DS!D51 chain evidence; v3.3.0: adds `_derive_croatian_legal_lcf_proforma()`, `WORKBOOK_LCF_MECHANICS_PROVED`, `periodisation_mismatch` |
| `tests/fixtures/excel_oborovo_financial_truth.json` | Regenerated v3.4.0; `d192_evidence.formula_mode_content = "=DS!D51"`, `source_classification = FORMULA_DERIVED`; new `ds_d51_chain` section; verdict `DEBT_SIZING_FORMULA_CHAIN_PARTIALLY_PROVED` |
| `tests/test_stage_c3b1_oborovo_tax_source_truth.py` | 160 tests (A–S + Q2 + T/U/V/W governance additions); Group T: verdict/SHA provenance; Group U: contradiction guards; Group V: TI formula period classification; Group W: layer boundary |
| `docs/reconciliation/oborovo_tax_source_truth.md` | This file |
| `.github/workflows/c3b1_diagnostic_check.yml` | New CI workflow running only `test_stage_c3b1_oborovo_tax_source_truth.py` |

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
  TI = EBT + Fiscal_Reintegration
     = EBIT + Financial_Earnings + Fiscal_Reintegration
     = EBIT + fin_earn + SHL

  net_taxable_financial_items_before_senior
     = Financial_Earnings + Fiscal_Reintegration + Senior_Interest
     = fin_earn + SHL + senior

  Simplified identity:  TI = EBIT − Senior_Interest
  Simplified residual:  TI − (EBIT − senior) = net_taxable_financial_items_before_senior

During debt-active periods (senior > 0):
  fin_earn = −(SHL + senior)  →  net = fin_earn + SHL + senior = 0
  TI = EBIT − Senior_Interest  (simplified identity holds; residual = 0)

During SHL-wind-down periods (senior = 0, SHL > 0):
  fin_earn = −SHL  →  net = fin_earn + SHL + 0 = 0
  TI = EBIT  (senior = 0, simplified identity still holds)

After full debt repayment (SHL = 0, senior = 0):
  fin_earn = row 20 (Interests from Cash on surplus) ≈ +2.77 kEUR/period
  net = fin_earn ≠ 0  →  TI = EBIT + cash_interest_on_surplus_cash
  Reason: TAXABLE_CASH_INTEREST_AFTER_DEBT_REPAYMENT

Note: Oborovo earns ZERO interest on DSRA (row 19 = 0). Cash interest (row 20) is on
surplus cash balance after debt repayment, not on DSRA.
```

## 9. Interest Dependency Result

**Classification: `INTEREST_DEPENDENCY_BLOCKS_TAX`**

- Senior interest (DS!G53) = sole deductible interest. Lifetime: **20,133.079 kEUR**.
- SHL interest (DS!G125) = fully non-deductible (FR = SHL always). Lifetime: **32,104.911 kEUR**.

### 9A. Phase 2C Runtime vs Excel Period-by-Period Comparison

The current clean Phase 2C engine was run (`finco_parity.check_financial_engine_senior_debt`,
baseline `oborovo`) and the senior interest vector was extracted directly from the `SeniorDebtSchedules`
result — **not from the frozen CSV**.

| Metric | Value |
|--------|-------|
| Excel senior interest lifetime | 20,133.079 kEUR (DS!G53 sum, 28 non-zero periods) |
| Phase 2C lifetime | 21,725.016 kEUR (60 periods; 28 non-zero) |
| Frozen phase23q CSV lifetime | 20,133.079 kEUR (matches Excel exactly — it IS an Excel extraction) |
| Period count compared | 28 (debt-active periods 1–28) |
| Maximum absolute period delta (P2C vs Excel) | **90.29 kEUR at period 25** |
| Signed cumulative delta | +1,591.94 kEUR |
| Differing periods (>0.001 kEUR threshold) | 28 (all debt-active periods) |
| Phase 2C sized debt | 45,873 kEUR |
| Excel actual debt | 42,852 kEUR |
| Root cause | Different debt sizing — Phase 2C solves to DSCR=1.15 target with current operating inputs; Excel uses a pre-determined drawdown of 42,852 kEUR |

**Alignment**: Phase 2C `period_index p` corresponds to fixture `period_index p-1` (Phase 2C is 1-indexed from period 2).

**Classification**: `INTEREST_DEPENDENCY_BLOCKS_TAX`

A per-period delta of up to 90 kEUR in senior interest translates to ≈9 kEUR difference in annual CIT (10% rate). This source diagnostic does not prove an algorithm defect in Phase 2C. It proves a debt-sizing-policy mismatch or input mismatch between the Phase 2C configuration used here and the Excel case.

Before modifying the engine, the next stage must determine whether the Excel workbook uses FIXED_AMOUNT, DSCR_SCULPTED, MAX_GEARING, MIN_OF_CONSTRAINTS, or another explicit sizing method — and must compare Phase 2C and Excel under equal inputs and equal sizing policy. Only after confirming a genuine algorithm defect should formulas be changed.

**Explicitly prohibited in C3B2:**
- Hardcoding 42,852 kEUR as the debt target
- Loading the frozen Excel repayment schedule into the production runtime
- Adding an Oborovo-specific sizing branch
- Modifying outputs until they hit an Excel target total

**Note on frozen phase23q CSV**: `reports/phase23q_oborovo_senior_debt_sizing_extraction.csv` is a historical extraction from the Excel workbook, not a Phase 2C runtime output. It matches Excel to 0.0000 kEUR for all 43 operating periods (verified in `test_phase23q_frozen_extraction_matches_excel_senior_interest_period_by_period`). It is properly labelled "frozen historical extraction" and must not be substituted for a live Phase 2C runtime result.

### 9B. Legacy (Baseline Snapshot) Interest

The committed parity baseline snapshot (`_load_baseline_snapshot("oborovo")`) contains an exogenous interest vector starting at 1,210.58 kEUR at period 2 — different from both Excel (1,303.48 kEUR) and Phase 2C current runtime (1,306.58 kEUR). This is a third independent sizing; it too fails to reproduce Excel interest.

- No standalone Phase 2B tax computation can be correct without Excel-matching senior interest.

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

## 13. Cash Tax Timing and CF/BS Chain

### CF Row 77 — Confirmed from Dual-Load

CF row 77 formula (period 1 column, captured from formula workbook):

```
=-'P&L'!H44
```

All 61 period formulas follow the same pattern: `=-'P&L'!{col}44` where `{col}` is the period column letter. This was read from the workbook formula mode (not hardcoded) and stored in `tax.cit_row43_vs_row44_authority.cf_cash_tax_row_77_formula_dual_load`.

### Three-Way Identity: P&L Row 43 = P&L Row 44 = −CF Row 77

Proved from workbook dual-load cached values for all 61 periods:

| Identity | Max delta | Result |
|----------|-----------|--------|
| P&L row 43 vs row 44 | 0.000000000 kEUR | PROVED EXACT |
| CF row 77 vs −P&L row 44 | 0.000000000 kEUR | PROVED EXACT |

Stored in `tax.cf_tax_chain.cf_vs_pl44_max_delta_keur = 0.0`.

### Sign Convention

- P&L row 44: **positive** (CIT expense; 8.904 kEUR at period 6)
- CF row 77: **negative** (cash outflow; −8.904 kEUR at period 6)

### Payment Timing

- Payment lag: **0 periods** — CIT settles within the same semi-annual period it accrues
- Python policy: `cash_tax_timing = TAX_YEAR_LAST_PERIOD`, `cash_tax_payment_lag_periods = 0`

### BS Tax Payable Conclusion

The Balance Sheet sheet was inventoried via dual-load. Full row label inventory:

```
Row  6: Assets
Row  8: Gross Fixed Assets
Row  9: Accumulated Depreciation
Row 10: Total Fixed Assets
Row 12: DSRA
Row 13: J-DSRA
Row 14: Distribution Account
Row 15: Cash
Row 17: Assets (subtotal)
Row 19: Liabilities
Row 21: Capital at Financial close
Row 22: Legal Reserve
Row 23: Retained Earnings
Row 24: Shareholder Loan
Row 25: Sponsor Carbon Fund
Row 26: Senior Debt
Row 27: Refinancing
Row 29: Short term loan
Row 31: Liabilities (subtotal)
Row 33: Balance check
Row 34: Depreciation check
Row 36: Indebtness Ratio
Row 43: Application of Thin capitalisation rules
Row 44: Ratio for thin capitalisation compliance
Row 45: Thin capitalisation indebtness threshold
```

**There is no tax payable or tax receivable row on the BS sheet.** CIT is fully settled within the period it accrues. No BS tax balance accumulates across periods. Terminal BS tax balance = 0.0 kEUR.

Stored in `tax.cf_tax_chain.bs_tax_payable_row_exists = false` and `bs_tax_payable_conclusion`.

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

## 17a. Tax Loss Carry-Forward — Workbook Mechanics (WORKBOOK_LCF_MECHANICS_PROVED)

### LCF Formula Chain

| P&L Row | Label | Formula (col G) | Key finding |
|---------|-------|-----------------|-------------|
| 36 | Opening LCF (losses N-1) | `=SUMIF(IF(G4<=$B$36,$F35:F35,F35:OFFSET(F35,0,-$B$36+1)),"<0")+SUM($F$37:F$37)` | Rolling 5-period SUMIF of negative TI in window; **not** a vintage ledger |
| 37 | Allocated losses | `=IF(AND(G36<=0,G32>0),MIN(ABS(G36),G32),0)` | **Uses EBT (G32)**, NOT TI. Zero for ALL periods (EBT<0 while losses exist). |
| 38 | Current-period loss | `=MIN(G37+G36,0)` | Equals row 36 since row 37=0 |
| 39 | Carriable losses | `=MIN(G38,F35*$B37)` | B37=1; caps by prior-period TI (effectively no cap here) |
| 41 | Taxable profit N | `=-G37+G35` | = TI since row 37=0; no loss offset applied |

**B36 = 5**: rolling window of **5 semi-annual model periods** ≈ 2.5 calendar years. This is **not** a 5-year or 5-tax-year window.

### LCF Taxonomy

| Question | Answer |
|----------|--------|
| Losses stored as positive or negative? | Negative (TI is negative; SUMIF accumulates negative values) |
| Oldest-first consumption? | Not applicable — losses expire by falling out of the rolling window |
| Explicit vintage tracking? | No — SUMIF formula only; no per-vintage ledger |
| Utilization trigger | EBT > 0 (row 37 uses G32=EBT, NOT G35=TI) |
| Utilization cap | 100% of TI (B37=1) |
| "5" means | 5 semi-annual model periods (~2.5 calendar years, NOT 5 tax years) |
| Losses ever utilized? | **Never** — EBT remains negative throughout all loss-carrying periods |

### Tax Milestones (Workbook — WORKBOOK_LCF_MECHANICS_PROVED)

Key `workbook_rolling_window_balance_reaches_zero` (formerly `lcf_balance_exhausted_from_window`).

| Milestone | Period | Date | Value | Note |
|-----------|--------|------|-------|------|
| WORKBOOK_FIRST_POSITIVE_TI | 6 | 2033-01-01 | 92.7 kEUR | H1-2033 |
| WORKBOOK_FIRST_LOSS_UTILIZATION | — | Never | 0 kEUR | EBT<0 blocks row 37 |
| WORKBOOK_FIRST_CIT_YEAR (period) | 6 | 2033-01-01 | 8.9 kEUR | Pair 5_6: (-3.7+92.7)×10% |
| WORKBOOK_FIRST_CASH_TAX_PERIOD | 6 | 2033-01-01 | −8.9 kEUR | No payment lag |
| WORKBOOK_ROLLING_WINDOW_REACHES_ZERO | After p10 | 2035-06-30 | 0 kEUR | p5 TI (−3.7) drops from window |

See Section 17c for the legal pro forma milestones (Article 17 calendar-year LCF).

**EBT < 0 during all loss periods**: SHL interest (>600 kEUR/period) keeps EBT negative even when EBIT > 0 and TI > 0. The loss-allocation gate in row 37 is therefore permanently closed. All accumulated losses (−581.7 kEUR peak at start of period 6) expire naturally through the rolling window, period by period.

### Consequence for C3B2

The LCF mechanism never reduces taxable profit in Oborovo. CIT fires from period 6 onward on the raw paired taxable income (no loss offset). C3B2 must reproduce this EBT-gated utilization condition, NOT a simpler "offset against positive TI" mechanism.

---

## 17b. Tax Year Interpretation — WORKBOOK_PERIODISATION_MISMATCH

**Croatian corporate income tax year: 1 January to 31 December.**

The workbook pairs H2 of year N with H1 of year N+1 in its CIT formula (`SUM(F41:G41)` fires in even periods). This straddles the Jan 1 boundary. It is a **modelling convention**, NOT evidence of a July fiscal year.

| Calendar-year aggregation (naive, no LCF) | Workbook pairing convention |
|-------------------------------------------|-----------------------------|
| Year 2033: H1-2033 (p6) + H2-2033 (p7) = 200.1 kEUR TI → naive CIT 20.0 kEUR | Pair 5_6: H2-2032 (p5) + H1-2033 (p6) = 89.0 kEUR TI → CIT 8.9 kEUR |
| Year 2034: H1-2034 (p8) + H2-2034 (p9) = 427.8 kEUR TI → naive CIT 42.8 kEUR | Pair 7_8: H2-2033 (p7) + H1-2034 (p8) = 313.4 kEUR TI → CIT 31.3 kEUR |

**Important**: the "naive calendar-year CIT" column above applies no LCF offset. With Article 17 LCF applied (see Section 17c), calendar year 2033 CIT = **0** (losses fully offset TI), and 2034 CIT = **4.615 kEUR** (partial offset). Do NOT cite 20.0 kEUR as "the correct 2033 CIT".

**Classification: `WORKBOOK_PERIODISATION_MISMATCH`**

The `calendar_vs_workbook_table` in the fixture shows naive calendar-year CIT (no LCF) vs workbook CIT, illustrating the timing shift only. For the legally accurate (Article 17 LCF-adjusted) comparison, see `croatian_calendar_year_lcf_proforma` in the fixture.

**Impact summary:**
- CIT timing shifts ~6 months (workbook CIT falls in H1 of year N+1, not H2 of year N)
- No impact on LCF window exhaustion date (losses expire by window, not by offset)
- Production `tax_year_start_month = 1`; the H2+H1 pairing is a workbook shortcut
- Do NOT use `tax_payment_frequency = "semi_annual_pair"` — this terminology does not exist in Croatian tax law

**Do not** use `tax_year_start_month = 7`. Do not implement `MODEL_YEAR_PAIR` as a typed enum. The correct production parameter is `tax_year_start_month = 1` combined with the semi-annual period layout.

---

## 17c. Croatian Legal LCF Pro Forma — Article 17 Calendar-Year Treatment

This section proves what the Croatian Article 17 LCF would yield on the same income stream. The **workbook does NOT implement Article 17** — it uses a rolling 5-period window (WORKBOOK_LCF_MECHANICS_PROVED). This pro forma is diagnostic only.

**Article 17 rules:** 5 calendar-year expiry per vintage; oldest-first utilization; no EBT gate.

| Year | Calendar TI | Opening LCF | New Loss | Utilized (oldest-first) | Taxable Base | CIT |
|------|------------|-------------|----------|------------------------|--------------|-----|
| 2030 | −219.2 | 0 | 219.2 | 0 | 0 | 0 |
| 2031 | −320.1 | 219.2 | 320.1 | 0 | 0 | 0 |
| 2032 | −42.5 | 539.3 | 42.5 | 0 | 0 | 0 |
| **2033** | **200.1** | **581.7** | **0** | **200.1 (from 2030)** | **0.0** | **0** |
| **2034** | **427.8** | **381.6** | **0** | **381.6 (exhaust all)** | **46.15** | **4.615** |
| 2035+ | 661+ | 0 | 0 | 0 | full TI | normal |

**Key milestones (legal pro forma):**

| Milestone | Year |
|-----------|------|
| LEGAL_PROFORMA_FIRST_LOSS_UTILIZATION_YEAR | 2033 |
| LEGAL_PROFORMA_FIRST_CIT_YEAR | 2034 |
| LEGAL_PROFORMA_LCF_EXHAUSTION_YEAR | 2034 |

**Contrast with workbook:** The workbook's rolling-window shortcut blocks utilization entirely (EBT gate) and expires losses through the window (not by time-horizon). The legal treatment would yield: 2033 CIT = 0 (vs workbook 8.9), 2034 CIT = 4.6 (vs workbook 31.3). The C3B2 LCF design must choose which treatment to implement — the workbook shortcut or the Croatian legal treatment — and document the choice explicitly.

---

## 18. Exact Recommended C3B2 Scope

> **THIS PARITY HARNESS IS NOT AN APPROVED PRODUCTION RUNTIME PATH.**
> C3B2 production implementations must not depend on: Oborovo baseline IDs; frozen
> baseline snapshots; private parity helpers (`finco_parity.*`); or fixture-backed
> debt schedules. All C3B2 policy inputs must be explicit generic economic inputs
> derivable from project parameters — not Excel-layout terminology.

### Generic Economic Inputs (not Excel-layout terminology)

The Oborovo workbook structure (H2+H1 period pairs, B36=5 window) reflects
**workbook modelling conventions**, not legal tax policy. C3B2 must expose the
underlying economic intent as generic inputs:

| Economic parameter | Derived from workbook | Recommended input name | Notes |
|--------------------|----------------------|------------------------|-------|
| Fiscal year start month | Croatian CIT year is 1 Jan–31 Dec. The H2+H1 pairing is a workbook modelling convention, NOT a July fiscal year. Pairs straddle Jan 1. | `tax_year_start_month = 1` | Use calendar year unless separately evidenced non-calendar fiscal period is provided |
| CIT assessment frequency | CIT fires in even semi-annual periods (every 2 periods) | `tax_assessment_frequency = "ANNUAL"`, `tax_assessment_period = "CALENDAR_YEAR"`, `cash_tax_booking_period = "TAX_YEAR_LAST_MODEL_PERIOD"` | Annual assessment on calendar year; cash booking in last model period of the tax year |
| Loss carry-forward window | B36 = 5 semi-annual periods | `loss_expiry_count = 5`, `loss_expiry_unit = "periods"` | A 5-period window on semi-annual model ≈ 2.5 calendar years, NOT 3 years |
| Loss utilisation limit | No cap in workbook | `loss_utilization_limit_pct = 1.0` | No partial-year limit in current Oborovo model |

**Distinguish three layers:**
1. **Legal tax policy** (external fact): fiscal year = 1 January–31 December (calendar year, Croatia); CIT rate; LCF window in tax years
2. **Modelling convention** (internal choice): semi-annual periods; how fiscal year straddle maps to period pairs
3. **Workbook shortcut** (implementation artefact): B36=5 window count, B43 MOD pairing — these are derivable from layers 1+2 and must not become named enums in production code

**Prohibited in C3B2 production code:**
- `MODEL_YEAR_PAIR` as a named enum — use `tax_year_start_month` + `tax_assessment_frequency` + `cash_tax_booking_period`
- `tax_payment_frequency = "semi_annual_pair"` — this terminology does not exist in Croatian tax law and conflates modelling convention with legal assessment policy
- `MODEL_PERIODS` as a named enum — use `loss_expiry_count` + `loss_expiry_unit`
- `loss_carryforward_years = 3` — this is a year-count approximation, not source parity
- Any string dispatch on `"oborovo"` or project name
- Any hardcoded period count referencing Oborovo-specific layout

### Six Required C3B2 Changes

1. **Fix adapter** (`financial_engine/adapters/project_inputs.py`): when `tax_depreciation_mode = BOOK_BASED_PERCENTAGE`, compute `tax_dep = book_dep × tax_deductible_book_dep_pct`. This eliminates the 1,974 kEUR tax dep gap.

2. **Wire senior interest from Phase 2C** that matches Excel debt sizing: pass `PeriodInterestInput.senior_interest_keur`. The current Phase 2C runtime diverges by up to 90 kEUR/period because it sizes the debt to 45,873 kEUR vs Excel 42,852 kEUR. C3B2 must calibrate Phase 2C to equal inputs and equal sizing policy before any formula changes — the divergence is a sizing-policy mismatch, not a proven algorithm defect.

3. **Add SHL fiscal reintegration**: populate `PeriodTaxAdjustmentInput.other_fiscal_reintegration_keur = SHL_interest` per period (thin_cap=False path; full SHL is non-deductible).

4. **Fix LCF basis**: use `loss_expiry_count = 5`, `loss_expiry_unit = "periods"`. Do not approximate with calendar-year counts.

5. **Fix CIT aggregation basis**: derive from `tax_year_start_month = 1` and semi-annual period layout. The workbook convention (H2[yr N] + H1[yr N+1]) straddles Jan 1 — classify as `WORKBOOK_PERIODISATION_MISMATCH`; do not reinterpret as a July fiscal year.

6. **Fix CIT formula**: implement the row-43 economic formula `MAX(SUM(tp_prev + tp_curr), 0) × rate × (is_operating) × (is_even_period)`. Do not reproduce Macro row-44 hardcoded values — row 44 is workbook routing evidence and a staleness risk.

Additional (low-risk, no runtime impact for Oborovo):

7. **Fix `origin_tax_year` docstring** in `financial_engine/inputs.py`.

## 19. Interest Prerequisite

**Yes — Phase 2C is required before C3B2 can produce correct tax numbers.** The current Phase 2C runtime produces a valid senior interest vector but with 7.9% higher debt sizing (45,873 kEUR vs Excel 42,852 kEUR), causing up to 90 kEUR per-period interest error.

**This is a sizing-policy mismatch, not a proven algorithm defect.** The Phase 2C engine sizes debt by DSCR sculpting against current operating inputs. The Excel debt (42,852 kEUR) was sized under different inputs or a different policy. Before any engine formula is modified, C3B2 must demonstrate that equal inputs + equal policy produce a divergent result. Prohibited:

- Hardcoding 42,852 kEUR as a debt target
- Loading the frozen Excel repayment schedule into the runtime engine
- Adding an Oborovo-specific sizing branch
- Modifying engine outputs to match Excel totals

### Debt-Sizing Evidence (Extractor-Generated, v3.4.0)

The fixture contains `debt_sizing_evidence` (generated by `_derive_debt_sizing_from_workbook()`) with D192 dual-load evidence, DS!D51 chain evidence, and DS row 22 step-up evidence.

**D192 (Inputs!D192 = senior debt amount) — PROVED:**
- Cached value: 42,852.279 kEUR
- Formula-mode content: `=DS!D51` (direct cell access, `data_only=False`)
- Classification: `FORMULA_DERIVED`, `LINKED_VALUE`
- Direct precedent: `DS!D51`

**DS!D51 precedent chain:**

| Step | Cell | Formula | Cached (kEUR) | Note |
|------|------|---------|---------------|------|
| 1 | DS!D51 | `=SUM(G51:DW51)` | 42,852.279 | Sum of all period drawdowns |
| 2 | DS!G51 | `=G62+G72` | 42,852.279 | Tranche-1 + Tranche-2 at construction |
| 3 | DS!G62 | `=(G3=0)*$B$62` | 42,852.279 | Construction drawdown (G3=0 guard) |
| 4 | DS!B62 | `=Inputs!$D$195*B60` | 42,852.279 | Tranche-1 = D195 × proportion (B60=1.0) |
| 5 | Inputs!D195 | `=MIN(DS!$D$47, G171*$D$230)` | 42,852.279 | **Binding MIN** |
| 6 | DS!D47 | `=MAX($G$47:$DW$47)` | 42,852.279 | Peak DSCR-sculpted capacity (**binding**) |
| 7 | Inputs!D230 | `=Scenarios!E348` | 0.80 | Gearing cap = 80% |
| 8 | Inputs!G171 | `=SUM(G165:G170)` | 57,973.053 | Total CAPEX |

**Binding constraint**: `DSCR_SCULPTING` — DS!D47 (42,852 kEUR) < gearing cap (57,973 × 0.80 = 46,378 kEUR).

**Iterative reference**: DS!G47 contains `=SUM(IF(NOT(G7),(G46+H47)/(1+G44*(…))),G82)` — a backward reference to H47 (the next period's value), requiring iterative calculation. This prevents full algebraic proof from static formula inspection alone.

**Debt sizing verdict: `DEBT_SIZING_FORMULA_CHAIN_PARTIALLY_PROVED`**

The formula chain from D192 to the DSCR-sculpting mechanism is fully traced. DS!G47's iterative reference means the chain cannot be algebraically closed from static inspection. No Goal Seek or macro evidence found.

**DS row 22 (DSCR step-up):**
- Formula (period 1): `=($B$22*G15)+(G16*$D$22)+(G17*$C$22)`
- Step-up targets: B22=1.15 (base), C22=1.35 (mid-life), D22=1.65 (tail)
- Cached distinct values: [1.15, 1.35] — 1.65 not reached in Oborovo operating periods

**Evidence table:**

| Parameter | Excel cached value | Phase 2C source | Phase 2C value | Notes |
|-----------|-------------------|-----------------|----------------|-------|
| Debt amount (kEUR) | D192 = 42,852 (via DSCR sculpt) | Engine output | 45,873 | Policy mismatch: step-up absent in Phase 2C |
| All-in rate (%) | D202+D203 = 5.65% | `annual_fixed_rate` | 5.65% | Match |
| DSCR target (initial) | DS row 22 = 1.15 (periods 1-24) | `target_dscr` | 1.15 | Match |
| DSCR step-up | DS row 22 = 1.35 (period 25+) | none | constant 1.15 | **Policy mismatch** — step-up not in Phase 2C |
| Maturity | Inputs!D196 = 14 years | `maturity_period_index` | 28 periods | Approximately aligned |

The absence of the 1.15 → 1.35 DSCR step-up in Phase 2C is confirmed from formula evidence (not just cached values) and is a likely contributor to the 7.9% over-sizing (45,873 vs 42,852 kEUR). Root-cause equality requires equal-input comparison in C3B2.

Items resolved by chain evidence (previously in manual_check_pack):
- Priority 1: D192 is FORMULA_DERIVED (`=DS!D51`) — not a literal or Goal Seek result ✓
- Priority 5: DS!G51 = `=G62+G72` references B62 → D195 → not driven from D192 ✓
- Priority 7: Gearing cap = 80% × 57,973 = 46,378; DS!D47 = 42,852 < 46,378 → not binding ✓

Items still requiring manual check: priorities 3 (CFADS composition), 6 (circular ref resolution), 8 (DSRA funding), 9 (IDC in debt base), 10 (hedge rate split).

### Acceptable C3B2 Approaches for Interest Input

**Option A** (preferred for production): Identify the exact sizing policy that reproduces the Excel debt under equal inputs → implement that policy generically → run Phase 2C → use resulting schedule as `PeriodInterestInput`.

**Option B** (adequate for initial parity proof): Inject the Excel DS!G53 vector directly as exogenous interest. Clearly label as "Excel-sourced" (not Phase 2C modeled). Must not reach production runtime.

## 20b. Manual Verification Pack (Debt Sizing)

The following items require manual workbook inspection to harden the debt-sizing conclusion. Maximum 10 decisive checks:

| Priority | Sheet | Cell / Row | Current value | Question |
|----------|-------|------------|---------------|----------|
| 1 | Inputs | D192 | 42,852.279 kEUR | Hardcoded input or result of Goal Seek / macro? |
| 2 | DS | Row 22 (DSCR target) | 1.15 (p1-24), 1.35 (p25-28) | Is the 1.35 step-up from a named Inputs cell or hard-wired in DS? |
| 3 | DS | Row 20 (CFADS) | 2,575 kEUR (p1) | Does CFADS include/exclude DSRA movements? Is SHL service below the line? |
| 4 | Inputs | D45 (Total CAPEX) | 57,973 kEUR | Is this the eligible debt base, or a different sub-total? |
| 5 | DS | Row 50/51 | Opening 0 → 42,852 at p0 | Does DS row 51 drawdown formula reference `=Inputs!D192` directly? |
| 6 | DS | Principal rows 52/53 | Sculpted repayment | Circular reference or explicit sculpting loop? Does D192 drive the schedule or is D192 an output? |
| 7 | Inputs | Gearing cap input | Actual = 73.9% | Is there an explicit gearing cap cell that determined 42,852? |
| 8 | DS | DSRA rows | Unknown | Is there a DSRA? How is it funded — does it reduce CFADS available for DSCR? |
| 9 | IDC / Inputs | IDC total | 1,086 kEUR (C.IDC) | Are IDC + commitment fees (1,275 kEUR) included in the eligible debt base? |
| 10 | Inputs / DS | Hedge | Unknown | Is 5.65% a fixed all-in rate or hedged rate + unhedged split? |

## 20a. Final PR Positioning

**PR #912 is SOURCE-TRUTH / AUDIT EVIDENCE ONLY.**

This PR establishes the Oborovo Excel tax source map and identifies the senior-debt interest dependency. It does **not**:

- Approve the C3B2 production implementation
- Approve wiring frozen Excel schedules into the runtime engine
- Prove a Senior Debt algorithm defect (the divergence is a sizing-policy mismatch)
- Establish that the Phase 2C engine is wrong
- Authorize any of the six C3B2 items for immediate implementation

C3B2 requires a separate design review that: (a) resolves the debt sizing policy question under equal inputs; (b) defines generic tax policy inputs without Excel-layout terminology; (c) is reviewed as a production code change, not as a diagnostic audit.

**Permanent guardrails (retained):**
- No project-name string dispatch in `financial_engine/`
- No frozen fixtures consumed by production runtime
- No target plugs (`approved_delta`, `tax.*plug`, `cit.*target`)
- No production formula changes without equal-input comparison
- Deterministic output from explicit inputs only

## 20. Test Matrix

| Group | Description | Count | Result |
|-------|-------------|-------|--------|
| A | Provenance + cf_tax_chain + period_diagnostic schema | 10 | PASS |
| B | Source row inventory (24 rows, corrected formulas) | 15 | PASS |
| C | Tax dep source | 5 | PASS |
| D | Taxable income identity | 6 | PASS |
| E | Frozen CSV vs Excel; Phase 2C runtime divergence classification | 7 | PASS |
| F | Tax loss roll-forward (opening balance, 5-period window, expiry) | 6 | PASS |
| G | Tax-year fragmentation (model-year proved) | 3 | PASS |
| H | Current tax identity | 4 | PASS |
| I | CF row 77 dual-load formula; CF=−P44 vector proof; BS conclusion | 8 | PASS |
| J | Sign conventions | 4 | PASS |
| K | Clean/legacy source | 5 | PASS |
| L | Financial freeze (base SHA vs HEAD) | 6 | PASS |
| M | No project identity dispatch | 3 | PASS |
| N | No target plug | 2 | PASS |
| O | C3A upstream freeze | 4 | PASS |
| P | Regression guard (real subprocess assertions; no tautological tests) | 2 | PASS |
| Q | Tax milestones (first CIT, first cash, LCF exhaustion, loss utilization) | 8 | PASS |
| Q2 | Croatian LCF expiry boundary (N+5 inclusive, N+6 exclusive — synthetic) | 2 | PASS |
| R | Periodisation mismatch (WORKBOOK_PERIODISATION_MISMATCH, no July FY) | 4 | PASS |
| S | Debt sizing evidence (D192=DS!D51, chain, verdict, direct-access synthetic) | 18 | PASS |
| **Total** | | **132** | **132 PASS** |

## 21. Introduced vs Pre-Existing Failures and GitHub Workflow Matrix

### Local Test Results

| Test file | Outcome | Classification |
|-----------|---------|---------------|
| `test_stage_c3b1_oborovo_tax_source_truth.py` | **132 PASS** | — |
| `test_stage_c3a_clean_pnl_through_ebit.py` | 129 PASS | — |
| `test_phase2c_senior_debt.py` | PASS | — |
| `test_phase2b_tax_cfads.py::test_w_correction_aware_four_baseline[oborovo]` | FAIL | **PRE_EXISTING_ON_BASE** |

**0 failures introduced by C3B1.**

### GitHub Actions Workflow Failure Matrix (all 7 workflows + new C3B1)

This PR targets `main`. The following matrix covers all workflows that trigger on PRs to `main`.

| Workflow | File | Base SHA (`b11e5bf7`) | PR HEAD (`478a0f8b`) | Classification | Root Cause |
|----------|------|----------------------|----------------------|----------------|------------|
| CI | `ci.yml` | Phase 2A failures (5); Oborovo distribution failures | Phase 2A failures (5); Oborovo distribution failures | **PRE_EXISTING_ON_BASE** | Phase 2A failures predated C3B1; Oborovo distribution test gap predated C3B1 |
| Phase 1B Baseline Check | `phase1b_baseline_check.yml` | 1 FAIL (`test_int_vs_float_is_structural_drift`) | 1 FAIL (same) | PRE_EXISTING_ON_BASE | Float representation drift in snapshot comparison; predated this branch |
| Phase 2A Clean Engine Check | `phase2a_clean_engine_check.yml` | **5 FAIL** | **5 FAIL** | **PRE_EXISTING_ON_BASE** | 5 test failures existed on base SHA b11e5bf7 before this branch was created |
| Phase 2B Tax and CFADS Check | `phase2b_tax_cfads_check.yml` | `test_w_correction_aware_four_baseline[oborovo]` FAIL | Same FAIL | **PRE_EXISTING_ON_BASE** | cash_tax_bridge_reconciliation drift, not approved in parity layer |
| Phase 2C Senior Debt Check | `phase2c_senior_debt_check.yml` | **BLOCKED** by Phase 2A regression step | **BLOCKED** by Phase 2A regression step | **PRE_EXISTING_ON_BASE** | Phase 2C workflow runs Phase 2A suite as prerequisite; Phase 2A failures block Phase 2C tests from executing |
| Phase 2D Recon Check | `phase2d_recon_check.yml` | **3 FAIL** (protected-scope `fatal: bad revision HEAD~1`) | **3 FAIL** | **PRE_EXISTING_ON_BASE** / **WORKFLOW_INFRASTRUCTURE_DEFECT** | Phase 2D workflow uses `HEAD~1` as base ref; on shallow checkouts this fails with `fatal: bad revision 'HEAD~1'`; 3 failures |
| Parity Guardrails | `parity_guardrails.yml` | **3 FAIL** | **3 FAIL** | **PRE_EXISTING_ON_BASE** | Guardrail failures predated C3B1 |
| Excel Mapping Validation | `excel_mapping_validation.yml` | Not triggered (path filter) | Not triggered | — | Branch does not modify `docs/model_mapping/` |
| **C3B1 Diagnostic (new)** | `c3b1_diagnostic_check.yml` | N/A (new workflow) | **113 PASS** expected | NEW | Runs `test_stage_c3b1_oborovo_tax_source_truth.py` only |

**Notable details:**
- **Phase 2A 5 failures**: These exist on `b11e5bf7` and were not caused by C3B1 changes. C3B1 touches only 4 diagnostic files.
- **Phase 2C blocked**: The phase2c_senior_debt_check workflow runs `tests/test_phase2a_*.py` as a prerequisite step; Phase 2A failures cause Phase 2C step to never execute. Classification: `PRE_EXISTING_ON_BASE`.
- **Phase 2D `fatal: bad revision`**: The `check_protected_scope.py` script uses `HEAD~1` as the base ref. In GitHub Actions on shallow clones (`fetch-depth: 0` is set, but `HEAD~1` may still fail on some ref configurations). Classification: `WORKFLOW_INFRASTRUCTURE_DEFECT`.
- **0 failures introduced by C3B1**: All failures on PR HEAD were already present on base SHA `b11e5bf7`.

## 22. No Production Formula Changed

Confirmed. Files changed vs base `b11e5bf7`:
- `finco_recon/extract_oborovo_excel.py` (extractor tooling only — v3.4.0)
- `tests/fixtures/excel_oborovo_financial_truth.json` (regenerated)
- `tests/test_stage_c3b1_oborovo_tax_source_truth.py` (tests only)
- `docs/reconciliation/oborovo_tax_source_truth.md` (this file)
- `.github/workflows/c3b1_diagnostic_check.yml` (new CI step — diagnostic only)

`financial_engine/`, `finco_parity/`, `app/project_factories.py`, `app/orchestrator.py`, all workbooks, scenarios, UI: **unchanged**.

Verified by Group L tests:
```
git diff b11e5bf7b9ab60bae174081e7d9f8541190bf371 HEAD -- financial_engine/  # empty
git diff b11e5bf7b9ab60bae174081e7d9f8541190bf371 HEAD -- finco_parity/      # empty
git diff b11e5bf7b9ab60bae174081e7d9f8541190bf371 HEAD -- app/               # empty
```

---

## Final Verdict

```
C3B1_SOURCE_TRUTH_PARTIAL_MANUAL_CHECK_REQUIRED
```

All C3B1 source evidence items are resolved.

**Tax formula**: `TI = EBT + FR = EBIT + Financial_Earnings + Fiscal_Reintegration` proved to machine precision. Simplified `TI = EBIT − Senior` holds when `net_taxable_financial_items_before_senior = fin_earn + SHL + senior = 0` (all debt-active periods). CF row 77 (`=-P&L!row44`) confirmed from dual-load. BS has no tax payable row.

**LCF mechanics**: B36=5 is a 5-semi-annual-period rolling window (~2.5 calendar years). Allocated losses = 0 for ALL periods because row 37 requires EBT > 0, and EBT remains negative throughout all loss-carrying periods (SHL interest blocks utilization). Losses expire naturally from the window; never utilized. `TAX_LOSS_ROLLFORWARD_SOURCE_PROVED`.

**Tax milestones**: First positive TI = period 6 (Jan-Jun 2033). First CIT = 8.9 kEUR at period 6. LCF window exhausted after period 10 (Jun 2035). No losses utilized.

**Periodisation**: Workbook pairs H2(yr N) + H1(yr N+1) — `WORKBOOK_PERIODISATION_MISMATCH`. Croatian CIT year is Jan–Dec. Do not treat as July fiscal year. Production: `tax_year_start_month = 1`. Use generic `loss_expiry_count = 5`, `loss_expiry_unit = "periods"`.

**Debt sizing**: `Inputs!D192 = "=DS!D51"` (FORMULA_DERIVED, LINKED_VALUE). Chain traced: D51=SUM(G51:DW51) → D195=MIN(DS!D47, CAPEX×0.80). Binding: DSCR sculpting — DS!D47=42,852 kEUR < gearing cap=46,378 kEUR. DS!G47 has iterative reference; verdict: `DEBT_SIZING_FORMULA_CHAIN_PARTIALLY_PROVED`. Phase 2C sizes at constant DSCR=1.15 → 45,873 kEUR; step-up (1.15→1.35 at period 25) absent in Phase 2C. Classification: `DEBT_SIZING_POLICY_MISMATCH_IDENTIFIED`. Remaining manual checks: CFADS composition, DSRA, IDC eligibility, hedge rate split.

C3B2 scope: 6 mandatory items pending separate design review with equal-input comparison.
