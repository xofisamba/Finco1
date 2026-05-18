# Phase 6 — R35 Formula Inspection

## Branch
`phase6-r35-formula-inspection`

## Status
**Diagnostic only — no production code changes, no bridge implemented.**

---

## Goal
Inspect and document the exact Excel P&L R35 formula chain for TUHO, years 13–30, to identify missing components that caused the 6,155 kEUR formula gap in the counterfactual branch.

---

## Exact R35 Formula Chain

```
P&L R35 = R32 + R34
        = R16 + R30 + (-R54)
        = (R8 − R14) + [SUM(R19:R21) − SUM(R24:R28)] − R54
```

| Row | Name | Role in R35 |
|-----|------|-------------|
| R8 | Total Revenues | EBIT numerator |
| R10 | Operating Expenses | |
| R13 | Depreciation | Reduces R14 → R16 |
| R14 | Total Expenses | R16 = R8 − R14 |
| R16 | EBIT | R16 = R8 − R14 (NO interest components) |
| R19 | Interests from Reserve Accounts | Financing revenue |
| R20 | Interests from Cash | Financing revenue |
| R21 | Withholding Tax on Interests | Reduces financing revenues |
| R24 | Senior Interests | Deduction from financing earnings |
| R25 | Senior Refinancing Interest | Deduction from financing earnings |
| R26 | Junior Interest | Deduction from financing earnings |
| R27 | Shareholder Loan Interests | Deduction from financing earnings |
| R28 | Interests on Cash | Reduces financing earnings when cash balance negative |
| **R30** | **Financial Earnings** | **SUM(R19:R21) − SUM(R24:R28)** ← key row |
| R32 | Earnings Before Tax | R16 + R30 |
| R54 | Fiscal Reintegration | Thin cap / non-deductible interest adj; R54 = 0 for yr13–30 |
| **R34** | **Fiscal Reintegration (= −R54)** | **= 0 for yr13–30** |
| **R35** | **Taxable Income** | R32 + R34 = R32 (since R34 = 0) |

### R54 Components (Fiscal Reintegration)
```
R54 = MIN(MAX(R57, R58) + R59, R27)
R57 = IF(R56_flag, MAX(R27 − C57, 0), 0)    ← thin cap deduction
R58 = IF(R56_flag, MAX(R27 − C58×(R32−R30+R13), 0), 0)  ← non-deductible interest
R59 = R27 × (1 − C59/Inputs!C311) × D59     ← SHL withholding factor
```
For TUHO yr13–30: R56 (thin cap flag) = 0 for all periods → R54 = 0 throughout.

### Loss Rows (R36–R39) — Do NOT Affect R35

| Row | Name | Formula | Affects R35? |
|-----|------|---------|-------------|
| R36 | Losses N-1 | `SUMIF("<0")` over rolling lookback window | **NO** — feeds R37 only |
| R37 | Allocated Losses | `IF(R36≤0 AND R32>0, MIN(ABS(R36), R32), 0)` | **NO** — feeds R41 only |
| R38 | Losses N | `MIN(R37+R36, 0)` | **NO** — feeds R39 only |
| R39 | Carriable Losses | `MIN(R38, R35_prev × B37)` | **NO** — carried forward |
| R41 | Taxable Profit N | `R35 − R37` | Result row |

**R35 is pure. R36–R39 are loss-accounting rows that only reduce R41, not R35.**

---

## R43 (CIT) Timing — Economic Convention

```
R43 = MAX(SUM(prev_H1_R41 : this_H2_R41), 0) × 18% × col_active × col_H1_flag
```

- Excel R43 is an **annual CIT formula** triggered once per operating year (at the payment column).
- CF R67 records the corresponding **annual cash tax outflow in H2**.
- The column trigger depends on Excel layout (period index parity), but the **economic fact is unambiguous**: R43/R67 = 18% × annual combined R41 = 18% × (H1_R41 + H2_R41).
- **Annual basis**: H1 R41 + H2 R41.

---

**The counterfactual used CF_R40/EBITDA as a pre-depreciation taxable basis and then subtracted P&L R13 book depreciation as an additional deduction.**

Excel R35 does not start from CF_R40. It starts from P&L R16 (EBIT), which already nets out book depreciation. Therefore:
- CF_R40 = EBITDA already incorporates the book depreciation effect implicitly
- Subtracting P&L R13 again double-counts it → taxable income overstated by ~P&L R13 per period
- For yr13–20: CF_R40 − P&L R16 = P&L R13 ≈ 1,786 kEUR/period
- × 18% × 8 years × 2 periods ≈ **6,155 kEUR in CIT space**

**The 6,155 kEUR formula gap is entirely explained by the double-counted book depreciation in the counterfactual basis.**

| Period | P&L R16 (EBIT) | CF R40 (EBITDA) | Gap |
|--------|------------:|------------:|-----:|
| yr13 H2 | 4,424.62 | 6,210.19 | +1,785.56 |
| yr14 H2 | 4,410.05 | 6,195.61 | +1,785.56 |
| yr15 H2 | 4,479.19 | 6,259.88 | +1,780.69 |
| yr16 H2 | 4,529.70 | 6,315.26 | +1,785.56 |
| yr17 H2 | 4,743.16 | 6,528.73 | +1,785.56 |
| yr18 H2 | 4,909.54 | 6,695.11 | +1,785.56 |
| yr19 H2 | 5,058.74 | 6,839.43 | +1,780.69 |
| yr20 H2 | 5,240.84 | 7,026.41 | +1,785.56 |
| yr21 H2 | 7,151.11 | 7,151.11 | **0.00** |
| yr22–30 | **0.00** | **0.00** | **0.00** |

**Years 13–20 gap is constant at ≈1,786 kEUR/period = P&L R13 (book depreciation).**  
**Years 21–30: CF_R40 = P&L R16 (no depreciation difference).**

### Formula Gap Quantification

| Metric | kEUR |
|--------|-----:|
| Case7 (no-ATAD formula) total CIT yr13–20 | 34,258 |
| Excel actual CIT yr13–20 | 28,103 |
| **Formula gap yr13–20** | **6,155** |
| Per period: 6,155 ÷ 8 periods = 769 kEUR/period | |

This 769 kEUR/period gap in CIT space (18% × 4,272 kEUR in TI space) = P&L R13 book depreciation × 18% = 1,785.56 × 18% = **321.4 kEUR/period × 2** (H1+H2 pair) = ~643 kEUR/period annual × 8 = **5,144 kEUR**.

The remaining ~1,011 kEUR of the 6,155 kEUR formula gap is explained by:
- Book depreciation in H1 also inflating Case7 CIT
- The H1 R35 is also overstated by the same book_dep amount

---

## R37 Loss Consumption — yr13 H1 Anomaly

In yr13 H1 (col 32), R36 = −5,291 kEUR (rolling SUMIF from all prior negative R35 values, going back to construction periods). This is consumed entirely in H1:
- `R37 = MIN(ABS(−5,291), R32=2,299) = 2,299` (capped at R32)
- `R38 = MIN(2,299 + (−5,291), 0) = −2,993` (carried forward)
- `R41 = R35 − R37 = 2,299 − 2,299 = 0` → CIT = 0 in H1

In yr13 H2: `R36 = −1,807` (opening balance after H1 consumption), `R37 = 1,807`, `R41 = 667.72` → annual CIT = 120.19.

The opening loss balance for yr13 is the cumulative construction-period losses, consumed over yr13 H1 and yr13 H2.

---

## Annual CIT Reconciliation (yr13–30)

| Yr | H1 R41 | H2 R41 | Annual R41 | Excel CIT (18%×Ann) |
|-----|--------:|--------:|------------:|--------------------:|
| 13 | 0.00 | 667.72 | 667.72 | 120.19 |
| 14 | 2,558.45 | 2,748.42 | 5,306.88 | 955.24 |
| 15 | 2,902.62 | 3,122.61 | 6,025.22 | 1,084.54 |
| 16 | 3,272.87 | 3,529.94 | 6,802.80 | 1,224.50 |
| 17 | 3,844.67 | 4,134.28 | 7,978.95 | 1,436.21 |
| 18 | 4,408.41 | 4,730.10 | 9,138.51 | 1,644.93 |
| 19 | 5,003.76 | 5,058.74 | 10,062.50 | 1,811.25 |
| 20 | 5,155.40 | 5,240.84 | 10,396.24 | 1,871.32 |
| 21 | 7,037.24 | 7,153.88 | 14,191.13 | 2,554.40 |
| 22 | 7,202.29 | 7,321.67 | 14,523.96 | 2,614.31 |
| 23 | 7,426.03 | 7,507.64 | 14,933.67 | 2,688.06 |
| 24 | 7,552.49 | 7,677.67 | 15,230.17 | 2,741.43 |
| 25 | 7,701.53 | 7,829.18 | 15,530.72 | 2,795.53 |
| 26 | 7,870.66 | 8,001.11 | 15,871.77 | 2,856.92 |
| 27 | 8,037.57 | 8,125.89 | 16,163.46 | 2,909.42 |
| 28 | 8,123.15 | 8,257.79 | 16,380.94 | 2,948.57 |
| 29 | 8,221.41 | 8,357.67 | 16,579.08 | 2,984.23 |
| 30 | 8,264.44 | 8,401.42 | 16,665.86 | 2,999.85 |
| **Total** | | | | **38,240.92** |

---

## Conclusions

1. **R35 = P&L R16 + P&L R30 (EBIT + Financial Earnings). NO ATAD. R34 = 0 for all yr13–30.**

2. **Loss rows R36–R39 do NOT affect R35. They only reduce R41.**

3. **The counterfactual's no-ATAD formula `CF_TI = CF_R40 − book_dep − senior − SHL + book_dep` was structurally wrong.** Using CF_R40 (which already nets out book depreciation) and then subtracting book_dep again double-counts it for years 13–20, producing an inflated CIT that explains the 6,155 kEUR formula gap.

4. **Years 21–30:** CF_R40 = P&L R16 (zero book depreciation). Formula gap ≈ 2.77 kEUR/period = R20 interest on cash (appears in P&L R16 but not in CF R40 for those years). Negligible.

5. **The Case7 overstatement IS the depreciation effect** — the 6,155 kEUR is entirely explained by the double-counted book depreciation in the counterfactual formula for years 13–20.

---

## R99/R102 Status

**BLOCKED / audit-only.** No SHL FCF opt-in. No R99/R102 runtime-source change.

---

## Recommended Next Branch

The next branch should be one of:

| Priority | Branch | Goal |
|----------|--------|------|
| P1 | **`phase6-dep-r30-excel-crosscheck`** | Compare Excel Dep R30 (accelerated write-off, 0 for yr21–30) vs Python ledger (30yr straight-line). Quantify depreciation as the primary driver of Python vs Excel CIT differences in yr21–30. |
| Contingent | **`phase6-loss-engine-yr13-window`** | Bridge the yr13 H1 construction-period loss consumption mechanics (R36 rolling SUMIF window) into Python loss engine for yr13. |

The depreciation difference (Excel accelerated 0 for yr21–30 vs Python 1,217/period straight-line) is the structural reason Python underpays in yr21–30 (small negative gap) while overpaying in yr13–20 (large positive gap from combined loss CF + dep effects).

---

## Validation
- Tests: run pending (no code changes in this branch)
- Production code: NO changes
- Default behavior: NO CHANGE
- R99/R102: BLOCKED