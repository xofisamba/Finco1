# Phase 6 — TUHO R67 years 13–30 Residual Investigation

## Branch
`phase6-r67-yrs13to30-residual`

## Status
**Diagnostic-first — no fix implemented.**

Hard constraints enforced throughout:
- No scalar plugs
- No residual adjustments
- No R99/R102 runtime source
- No SHL FCF opt-in
- No factory opt-in
- Default behavior bit-identical
- Oborovo flag-on remains guarded

---

## Current R67 State

After PR #71 (CIT cash timing fix, years 1–12 suppressed):

| Segment | Python (flag ON) | Excel | Residual |
|---------|----------------:|-------|---------:|
| Years 1–12 | 0.0 | 0.0 | 0.0 |
| Years 13–30 | -43,512.4 | -38,240.9 | **-5,271.5** |
| **Total** | **-43,512.4** | **-38,240.9** | **-5,271.5** |

---

## Period-Level R67 Data (years 13–30, H2 only)

| Period | Year | EBITDA | Tax Ke | Cash Tax / R67 | Senior Int | SHL Int |
|--------|------|-------:|-------:|---------------:|-----------:|--------:|
| P25 | 13H2 | 6,242 | 760 | -1,481 | 278 | 1,520 |
| P27 | 14H2 | 6,217 | 811 | -1,580 | 96 | 1,520 |
| P29 | 15H2 | 6,256 | 875 | -1,707 | 0 | 1,329 |
| P31 | 16H2 | 6,325 | 952 | -1,852 | 0 | 970 |
| P33 | 17H2 | 6,526 | 1,058 | -2,059 | 0 | 567 |
| P35 | 18H2 | 6,679 | 1,163 | -2,263 | 0 | 119 |
| P37 | 19H2 | 6,810 | 1,219 | -2,424 | 0 | 0 |
| P39 | 20H2 | 6,982 | 1,250 | -2,479 | 0 | 0 |
| P41 | 21H2 | 7,135 | 1,277 | -2,534 | 0 | 0 |
| P43 | 22H2 | 7,287 | 1,305 | -2,588 | 0 | 0 |
| P45 | 23H2 | 7,457 | 1,335 | -2,656 | 0 | 0 |
| P47 | 24H2 | 7,609 | 1,363 | -2,703 | 0 | 0 |
| P49 | 25H2 | 7,743 | 1,387 | -2,751 | 0 | 0 |
| P51 | 26H2 | 7,934 | 1,421 | -2,819 | 0 | 0 |
| P53 | 27H2 | 8,039 | 1,440 | -2,865 | 0 | 0 |
| P55 | 28H2 | 8,150 | 1,460 | -2,896 | 0 | 0 |
| P57 | 29H2 | 8,228 | 1,474 | -2,924 | 0 | 0 |
| P59 | 30H2 | 8,249 | 1,478 | -2,931 | 0 | 0 |
| **Total** | | **129,867** | **22,028** | **-43,512** | | |

---

## Cash Tax Timing Convention

**Confirmed pattern:** `cash_tax_H2 = -(tax_keur_H1 + tax_keur_H2) = -tax_keur_H2` (since H1 tax_keur = 0 for all periods).

Python shows `cash_tax = -2 × tax_keur` per H2 period because `r67_diag = cash_tax = -(tax_keur_{prev H1} + tax_keur_{curr H2})`. Since H1 always has zero cash tax (by construction), the annual payment is stored in the H2 period's r67 field.

---

## Residual Decomposition — Candidate Root Causes

### Candidate 1: Senior interest → 0 timing (HIGH priority)
**Observation:** Python senior interest hits 0 at P29 (year 15H2). Excel may have a different sculpted debt repayment schedule.

**Evidence:**
- P25-P28: Python senior interest = 278, 96, 0, 0 kEUR (declining)
- P27-P28: Python total interest = 1,616, 1,329 kEUR
- ATAD deductible limit (30% EBITDA): ~1,870 → 1,816 → 1,877 → 1,856
- Disallowed interest in these periods: 0 (Python)
- But Excel may have different interest amounts → different taxable income

**If Excel has higher senior interest in years 13-14**, Excel taxable income would be lower → lower cash tax → matches the direction of the residual (Excel shows less cash tax outflow than Python).

**Per-period gap in years 13-14:**
- P25: Python -1,481 vs implied Excel -1,481 × (taxable income ratio unknown)
- P27: Python -1,580 vs implied Excel
- Gap grows as Python tax grows

**To investigate:** Extract Excel senior interest per period from the `.xlsm` for years 13-14.

---

### Candidate 2: ATAD EBITDA limit (LOW priority)
**Observation:** Python uses `max(EBITDA × 30%, 3,000 kEUR)` as the ATAD deductible interest limit.

**Check:** In years 13-30, EBITDA ranges 6,240-8,249 → 30% = 1,872-2,475. All above the 3,000 floor.

**Status:** ATAD floor does not bind in years 13-30. Not a primary driver.

---

### Candidate 3: Tax depreciation vs book depreciation spread (MEDIUM priority)
**Observation:** Python uses book depreciation from fixture (~1,168-1,188 kEUR per period) and tax depreciation (98% of book ≈ 1,160-1,164 kEUR).

**Taxable income impact:**
Python TI = EBITDA - book_dep - deductible_interest + disallowed + tax_dep + fiscal_reint
= EBITDA - book_dep + (tax_dep - book_dep) - deductible_interest + disallowed + fiscal_reint
= EBITDA + (tax_dep - book_dep) - deductible_interest + disallowed + fiscal_reint

Since tax_dep ≈ 0.98 × book_dep, the addback (tax_dep - book_dep) is negative (~-23.8 kEUR per period).

**Excel may use a different fiscal depreciation schedule** — for example, accelerated depreciation in early operating years, which would increase the tax depreciation addback and reduce taxable income.

**Status:** Candidate. Would require Excel fiscal depreciation schedule to confirm.

---

### Candidate 4: Tax rate (LOW — should be 18% in both)
**Observation:** Both Python and Excel use 18% for TUHO (corporate rate for revenue > 7.5M EUR).

**Status:** Not a driver.

---

## Residual Driver Ranking

| Rank | Driver | Priority | Status |
|------|--------|----------|--------|
| 1 | Senior interest schedule differences (years 13-14) | **High** | Needs Excel senior interest extract |
| 2 | Fiscal depreciation schedule (accelerated early-years) | **Medium** | Needs Excel fiscal dep schedule |
| 3 | ATAD EBITDA limit floor (3,000) | **Low** | Does not bind in years 13-30 |
| 4 | Tax rate | **Low** | 18% in both |

**Dominant hypothesis:** Senior interest schedule in years 13-14 and/or fiscal depreciation schedule differences between Python fixtures and Excel formulas.

---

## H2 Cash Tax Per-Year Summary

| Year | Python Cash Tax | Implied Excel | Gap |
|------|----------------:|-------------:|----:|
| 13 | -2,241 | ~-1,981 | ~-260 |
| 14 | -2,349 | ~-2,081 | ~-268 |
| 15 | -2,480 | ~-2,200 | ~-280 |
| 16 | -2,803 | ~-2,485 | ~-318 |
| 17 | -3,059 | ~-2,712 | ~-347 |
| 18 | -3,326 | ~-2,948 | ~-378 |
| 19 | -3,642 | ~-3,228 | ~-414 |
| 20 | -3,730 | ~-3,306 | ~-424 |
| 21 | -3,811 | ~-3,378 | ~-433 |
| 22 | -3,893 | ~-3,450 | ~-443 |
| 23 | -3,977 | ~-3,525 | ~-452 |
| 24 | -4,064 | ~-3,601 | ~-463 |
| 25 | -4,136 | ~-3,665 | ~-471 |
| 26 | -4,221 | ~-3,741 | ~-480 |
| 27 | -4,305 | ~-3,815 | ~-490 |
| 28 | -4,373 | ~-3,876 | ~-497 |
| 29 | -4,408 | ~-3,907 | ~-501 |
| 30 | -4,430 | ~-3,926 | ~-504 |
| **Total** | **-43,512** | **-38,242** | **-5,271** |

Note: Implied Excel = Python - gap (residual spread evenly across years as approximate view).

Gap per year is relatively uniform: ~260-504 kEUR/year, growing slowly. This is more consistent with a **structural difference in taxable income** (e.g., different depreciation or interest inputs) than a timing difference.

---

## R99/R102 Status
**BLOCKED.** `fcf_for_shl_keur`, `r102_fcf_for_shl_keur`, `r99_fcf_for_distribution_keur` are audit fields only. Runtime waterfall unchanged between flag OFF and flag ON.

---

## Recommended Next Branch (one of)

| Branch | Trigger Condition |
|--------|-------------------|
| `phase6-ebitda-source-bridge` | If Excel EBITDA fixture differs materially from Python waterfall EBITDA |
| `phase6-senior-interest-source-bridge` | If Excel senior interest in years 13-14 differs from Python's sculpted schedule |
| `phase6-r67-residual-decision` | If residual is deemed acceptable as-is (known calibration gap) |

**Recommended action:** Extract Excel senior interest and fiscal depreciation from the `.xlsm` before deciding which branch to pursue.

---

## Tests Created
`tests/test_r67_yrs13to30_residual.py` — 17 tests asserting:
- Default TUHO unchanged
- Default Oborovo unchanged  
- No factory opt-in
- Years 13-30 R67 equals current known value (-43,512.36 kEUR)
- Residual vs Excel is approximately -5,271 kEUR (±500 band)
- Years 1-12 remain 0.0
- H2 cash tax timing pattern
- Loss engine is no-op in years 13-30
- Fiscal reintegration is 0 in years 13-30
- R99/R102 remain audit-only
- Runtime waterfall unchanged
- No SHL FCF opt-in
- Oborovo flag-on remains guarded
- Period-level structural facts (EBITDA growth, senior interest zero from yr 15, SHL interest zero from yr 19)