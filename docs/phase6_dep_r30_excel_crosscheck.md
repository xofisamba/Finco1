# Phase 6 — Dep R30 Excel Crosscheck

## Branch
`phase6-dep-r30-excel-crosscheck`

## Status
**Diagnostic only — no production code changes, no bridge implemented.**

---

## Goal
Crosscheck Excel depreciation behavior for TUHO vs Python's ledger and quantify whether the depreciation profile is the remaining structural driver of Y13–30 R67 differences.

---

## Exact Row/Sheet/Column References

| Sheet | Row | Label | Source |
|-------|-----|-------|--------|
| P&L | R13 | Depreciation | `=Dep!{col}30` — confirmed equal to Dep R30 |
| Dep | R30 | Depreciation | Source row for P&L R13 |
| Dep | R31 | Unlevered Depreciation | For reference |

**Column mapping:** Excel column = Python operating index + 8 (e.g. P25 → col33 = yr13H2).

**Confirmed:** P&L R13 and Dep R30 are identical for all columns — no book-vs-tax mismatch in the Excel source rows. R31 (unlevered) is also close to R30 (~52 kEUR/yr lower).

---

## Depreciation Profile Comparison

### Years 13–20 (operating indices P25–P40)

| Source | Annual depreciation (kEUR/period) |
|--------|-----------------------------------:|
| Excel Dep R30 (avg) | ~1,771/period (alternating 1,756/1,785/1,761/1,781) |
| Python ledger book_depreciation_keur | 1,216.56/period (flat) |
| Python tax_depreciation_audit_keur | 1,178.19/period |
| Difference (Excel − Python book) | ~+555/period |

### Years 21–30 (operating indices P41–P60)

| Source | Annual depreciation |
|--------|--------------------:|
| Excel Dep R30 | **0.00** (accelerated write-off complete) |
| Python ledger book_depreciation_keur | 1,216.56/period (flat, straight-line continues) |
| Python tax_depreciation_audit_keur | 1,178.19/period |

**Excel uses accelerated depreciation (construction-period write-off): full book basis depreciated by end of year 20. Python uses 30-year straight-line from COD, continuing through year 30.**

---

## Cumulative Depreciation Delta

| Period | Excel Dep R30 | Python book_dep | Delta (Excel−Python) |
|--------|--------------:|---------------:|----------------------:|
| Yr13–20 (16 periods) | 28,336 | 19,465 | **+8,871 kEUR** |
| Yr21–30 (20 periods) | 0 | 24,331 | **−24,331 kEUR** |
| **Yr13–30 total** | **28,336** | **43,796** | **−15,460 kEUR** |

---

## CIT/R67 Impact Estimate (18% × Depreciation Delta)

| Period | Dep Delta (kEUR) | CIT Impact at 18% (kEUR) | Observed Gap |
|--------|----------------:|-------------------------:|-------------:|
| Yr13–20 | +8,871 | +1,597 | +5,697 |
| Yr21–30 | −24,331 | −4,380 | −425 |
| **Yr13–30 net** | **−15,460** | **−2,783** | **+5,271** |

**Note:** The depreciation CIT impact at 18% partially explains the observed gaps, but the relationship is not 1:1 because:
- In yr13–20: loss carryforward consumption reduces Excel taxable profit, limiting the book-dep shield benefit
- In yr21–30: Excel has 0 depreciation but also 0 SHL interest, while Python continues deducting book+tax depreciation and paying CIT

The yr21–30 small negative gap (−425 kEUR) vs the expected large −4,380 kEUR suggests Python's higher deductions (from continued ledger depreciation) are being offset by other structural differences (e.g. Excel's higher EBIT growth profile, or remaining SHL/senior/EBITDA driver mismatches not yet attributed).

---

## Key Finding: Excel Accelerated Write-off

**Confirmed:** Excel Dep R30 = 0 for years 21–30 (operating indices P41–P60, columns 48–67 in the Dep/P&L sheets).

Excel uses a construction-period accelerated depreciation schedule: the full asset basis is written off by end of year 20 (period 40). Python uses a 30-year semiannual straight-line schedule from COD that continues through year 30.

**This is not a bug or mapping error.** The depreciation profiles diverge — Excel appears to use a construction-period accelerated write-off, Python uses a 30-year straight-line schedule from COD. This appears to be a deliberate Excel depreciation profile/policy difference, not a row mapping error.

---

## Whether Python Should Align

| Alignment target | Case for | Case against |
|----------------|----------|--------------|
| **Book depreciation** | R35 in Python uses book_dep as a deduction | Excel's R35 = EBIT (already nets book dep) − not directly applicable |
| **Tax depreciation** | Python's TI formula subtracts tax_dep after ATAD | Excel R35 does not subtract tax dep separately (fiscal dep only via R34/R54 when R54>0) |

Excel's R35 = EBIT + Financial Earnings − R54. Book depreciation is embedded in EBIT (via R14). Tax depreciation only appears via R34 (fiscal reintegration) when R54>0. For TUHO Y13–30, R54=0, so tax depreciation is effectively invisible in Excel's R35.

**Python's tax bridge formula:** `TI = EBITDA − book_dep − deductible_int + disallowed + tax_dep + fiscal_reint`

The question is whether Python's `tax_dep` should track Excel's Dep R31 (unlevered) or follow a different fiscal schedule. This is a policy decision, not a diagnostic one.

---

## Observed Residual — After Standalone Depreciation Estimate

| Component | Yr13–20 | Yr21–30 | Total |
|-----------|--------:|--------:|------:|
| Observed R67 residual | +5,697 kEUR | −425 kEUR | **+5,271 kEUR** |
| Depreciation standalone CIT impact (18%×Δdep) | +1,597 kEUR | −4,380 kEUR | **−2,783 kEUR** |
| **Remaining residual after depreciation estimate** | **≈+4,100 kEUR** | **≈+3,955 kEUR** | **≈+8,055 kEUR** |

**This branch does not close the R67 residual.** It confirms depreciation profile divergence as a material structural difference, but full residual closure still requires a decision or a full source-bridge/counterfactual branch.

---

## R99/R102 Status

**BLOCKED / audit-only.** No SHL FCF opt-in. No R99/R102 runtime-source change.

---

## Recommended Next Branch

| Priority | Branch | Goal |
|----------|--------|------|
| **P1** | **`phase6-r67-residual-decision`** | **Evaluate and decide on the +5,271 kEUR residual policy. Options:**
|  | *(a) Accept* Excel/Python depreciation policy difference as known structural difference |
|  | *(b) Implement* a default-off Excel depreciation source bridge for TUHO |
|  | *(c) Keep* Python 30-year straight-line as canonical and document Excel variance |
|  | *(d) Defer* R99 runtime promotion while residual policy is unresolved |
| Contingent | **`phase6-tax-dep-excel-source-bridge`** | If decision is to bridge, extract Excel Dep R31 (unlevered depreciation) as the tax depreciation source and replace Python's tax_dep ledger with the Excel values. |
| Contingent | **`phase6-book-dep-excel-source-bridge`** | If book depreciation is the preferred alignment target, extract Excel Dep R30 book depreciation per period and replace Python's book_dep ledger. |

---

## Validation
- Tests: 54/54 passed (4 suites)
- Production code: NO changes
- Default behavior: NO CHANGE
- R99/R102: BLOCKED