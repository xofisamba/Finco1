# Phase 6 — Tax Bridge Counterfactual Attribution

## Branch
`phase6-tax-bridge-counterfactual-attribution`

## Status
**Diagnostic only — no production code changes, no bridge implemented.**

**Attribution: DID NOT reconcile.**

---

## Context

After PRs #71 (CIT timing) and #75 (first-pass attribution):
- Observed Y13–30 residual: **+5,271 kEUR** (Python overpays Excel)
- First-pass sequential attribution: 1,295 kEUR explained, 3,977 kEUR unattributed
- This branch: counterfactual recomputation using Excel source rows as inputs to Python's tax mechanics

---

## Attribution Method

**Annual H1+H2 basis.** Excel R43 CIT = 18% × annual (H1+H2) R41, paid in H2.

**Counterfactual formula (no ATAD):**
```
CF_TI = EBITDA − book_dep − senior − SHL + tax_dep
Annual_CIT = 18% × CF_TI_annual_after_loss
```

This formula is derived from Python's `_tax_bridge_taxable_income_before_losses` with ATAD stripped
(the deductible_interest = total_interest when no ATAD cap applies; confirmed: Python's ATAD cap
= max(30%×EBITDA, 3000) > total_interest for all Y13-30 periods, so no ATAD restriction fires).

**Substitution order:**
1. Case 2 — substitute Excel P&L R13 book depreciation
2. Case 3 — substitute Excel P&L R27 SHL interest
3. Case 4 — substitute Excel P&L R24 senior interest
4. Case 5 — substitute Excel CF R40 EBITDA
5. Case 6 — apply Excel R37 loss consumption in H2
6. Case 7 — substitute all Excel sources simultaneously

---

## Case Results (kEUR)

| Yr | Excel CIT | Python Cash | Gap | C2 Dep | C3 SHL | C4 Sen | C5 EBITDA | C6 Loss | C7 All |
|-----|----------:|----------:|-----:|-------:|-------:|-------:|----------:|-------:|-------:|
| 13 | 120 | 1,481 | +1,360 | 1,896 | 2,019 | 2,109 | 2,084 | 2,096 | 1,822 |
| 14 | 955 | 1,580 | +625 | 1,626 | 1,793 | 1,832 | 1,818 | 1,826 | 1,593 |
| 15 | 1,085 | 1,707 | +622 | 1,731 | 1,920 | 1,930 | 1,932 | 1,930 | 1,722 |
| 16 | 1,225 | 1,852 | +627 | 1,876 | 2,065 | 2,076 | 2,072 | 2,076 | 1,862 |
| 17 | 1,436 | 2,059 | +623 | 2,088 | 2,272 | 2,287 | 2,288 | 2,287 | 2,074 |
| 18 | 1,645 | 2,263 | +618 | 2,298 | 2,476 | 2,498 | 2,504 | 2,498 | 2,282 |
| 19 | 1,811 | 2,424 | +613 | 2,438 | 2,638 | 2,638 | 2,648 | 2,638 | 2,449 |
| 20 | 1,871 | 2,479 | +608 | 2,493 | 2,693 | 2,693 | 2,708 | 2,693 | 2,509 |
| 21 | 2,554 | 2,534 | −21 | 2,548 | 2,110 | 2,110 | 2,115 | 2,110 | 2,553 |
| 22 | 2,614 | 2,588 | −26 | 2,602 | 2,164 | 2,164 | 2,175 | 2,164 | 2,613 |
| 23 | 2,688 | 2,656 | −32 | 2,670 | 2,232 | 2,232 | 2,249 | 2,232 | 2,687 |
| 24 | 2,741 | 2,703 | −38 | 2,717 | 2,279 | 2,279 | 2,302 | 2,279 | 2,740 |
| 25 | 2,796 | 2,751 | −45 | 2,765 | 2,327 | 2,327 | 2,357 | 2,327 | 2,795 |
| 26 | 2,857 | 2,819 | −38 | 2,833 | 2,395 | 2,395 | 2,418 | 2,395 | 2,856 |
| 27 | 2,909 | 2,865 | −45 | 2,878 | 2,440 | 2,440 | 2,470 | 2,440 | 2,908 |
| 28 | 2,949 | 2,896 | −52 | 2,910 | 2,472 | 2,472 | 2,510 | 2,472 | 2,948 |
| 29 | 2,984 | 2,924 | −60 | 2,938 | 2,500 | 2,500 | 2,545 | 2,500 | 2,983 |
| 30 | 3,000 | 2,931 | −68 | 2,945 | 2,507 | 2,507 | 2,561 | 2,507 | 2,999 |
| **Total** | **38,241** | **43,512** | **+5,271** | **44,252** | **41,304** | **41,490** | **41,758** | **41,469** | **44,396** |

---

## Driver Impact Summary (vs Python, each case independently)

| Driver | Impact (kEUR) | Note |
|--------|------------:|------|
| Depreciation (C2) | +740 | Excel book dep > Python ledger dep → Python overpays |
| SHL interest (C3) | −2,209 | Excel SHL > Python fixture → Python underpays |
| Senior interest (C4) | −2,023 | Python senior slightly higher → Python overpays |
| EBITDA (C5) | −1,754 | Python EBITDA > Excel CF EBITDA → Python overpays |
| Loss CF (C6) | −2,043 | Excel R37 consumption reduces Excel TI → Python overpays |
| **All Excel (C7)** | **+884** | Combined effect with interactions |

**Counterfactual attribution failed to reconcile because the simplified no-ATAD formula does not reproduce Excel R35/R43.**

Case7 all-Excel-source counterfactual = **44,396 kEUR**
Excel actual = **38,241 kEUR**
Formula gap = **6,155 kEUR**

This implies missing Excel R35 formula-chain components, concentrated in years 13–20 (~638 kEUR/yr × 8 yrs ≈ 5,104 kEUR). Years 21–30 match nearly perfectly.

**Do NOT describe Case7 as a valid attribution bridge.** It is an all-sources substitution that does not reproduce Excel actuals.

---

## Key Finding: Formula Mismatch

**The counterfactual formula does not match Excel's actual R35 structure.**

Case 7 (all Excel inputs) = 44,396 kEUR, but Excel actual = 38,241 kEUR.
The gap of **6,155 kEUR** is the annual CIT computed by the counterfactual formula minus Excel's actual CIT.

This proves that Excel's R35 taxable income is **not** equal to:
`EBITDA − book_dep − senior − SHL + tax_dep`

The Excel model has additional components in its R35 computation that are not captured by the extracted source rows alone. Candidate explanations include:
- Additional tax addbacks or deductions visible only in the full Excel formula chain
- ATAD-like limitation applied differently in the P&L vs the CF model
- R34 fiscal reintegration sign convention differences
- Different treatment of the construction-period loss allocation

**Years 21–30:** Case7 vs Excel gap ≈ 1 kEUR/year (near-perfect match). The unexplained gap is concentrated in **years 13–20** (~638 kEUR/year × 8 years = ~5,104 kEUR), suggesting the discrepancy is specific to how Excel handles the construction-period loss allocation years.

---

## Reconciliation Status

| Metric | Value (kEUR) |
|--------|-------------:|
| Observed residual | +5,271 |
| Case 7 (all Excel) | +884 vs Python |
| Unexplained | +4,387 |
| Target ±200 | NOT MET |

---

## R99/R102 Status

**BLOCKED / audit-only.**

R99/R102 must not be promoted while formula gap > ±200 kEUR. This branch makes no R99/R102 runtime-source decision. No SHL FCF opt-in.

---

## Recommended Next Branch

| Priority | Branch | Goal |
|----------|--------|------|
| P1 | `phase6-r35-formula-inspection` | Inspect Excel P&L R35 formula chain (rows 13–41) to identify missing components causing the 6,155 kEUR formula gap |

---

## Validation
- Tests: 54/54 passed (4 suites)
- Production code: NO changes
- Default behavior: NO CHANGE
- R99/R102: BLOCKED