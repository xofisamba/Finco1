# Phase 6 — Tax Validation Pack

## Branch
`phase6-tax-validation-pack`

## Status
**Institutional validation / audit / governance package. No production code changes.**

---

## Purpose

This document is the consolidated Phase 6 tax calibration validation package. It is intended for:
- model governance
- future external reviewers
- future enterprise / bankability review
- future Phase 7 / Phase 8 work

It is NOT a production-code implementation branch. It compiles findings from all Phase 6 diagnostic branches and states the current calibration status, known residuals, governance decisions, and future requirements.

---

## Executive Summary

| Item | Status |
|------|--------|
| R35 formula chain | ✅ Calibrated — documented |
| R43/R67 annual H1+H2 timing | ✅ Calibrated |
| Years 1–12 R67 timing fix | ✅ Resolved (PRs #71+) |
| R36/R37/R38/R39 loss mechanics | ✅ Documented — does not affect R35 |
| R34 fiscal reintegration | ✅ Documented — 0 for TUHO yr13–30 |
| Book/tax depreciation split | ✅ Working in tax bridge |
| SHL gross-accrued source ownership | ✅ Confirmed via fixture |
| Depreciation useful-life mismatch | ⚠️ Known structural difference |
| Y13–30 R67 residual | ⚠️ Provisional acceptance — not mathematically closed |
| R99/R102 runtime promotion | 🚫 BLOCKED |
| SHL FCF runtime source | 🚫 Not approved |

---

## Phase 6 Branch Summary

| PR | Branch | Key Finding |
|----|--------|-------------|
| #71 | `phase6-cit-h2-annual-trigger` | R43/R67 timing: annual cash tax paid in H2; H1 CIT = 0 |
| #75 | `phase6-y13-30-residual-attribution-per-driver` | First-pass attribution: 1,295 kEUR explained, 3,977 kEUR unattributed |
| #76 | `phase6-tax-bridge-counterfactual-attribution` | No-ATAD counterfactual formula does not reproduce Excel R35; formula gap 6,155 kEUR explained |
| #77 | `phase6-r35-formula-inspection` | R35 = EBIT + Financial Earnings. NO ATAD. Loss rows R36–R39 do not affect R35. |
| #78 | `phase6-dep-r30-excel-crosscheck` | Excel Dep R30 = 0 for yr21–30; Python 30-year straight-line continues |
| #79 | `phase6-r67-residual-decision` | Provisional acceptance; no bridge; R99 BLOCKED; external review required |
| — | `phase6-r67-yrs13to30-residual` | 54 tests pass; residual confirmed in Python model |
| — | `phase6-excel-interest-dep-extraction` | Excel data extraction for TUHO yr13–30 |
| — | `phase6-tax-bridge-consumes-r35-sources` | Tax bridge consumes R35 as source; loss engine uses Croatia vintage mode |
| — | `phase6-r67-full-calibration-validation` | Full calibration validation confirmed |

---

## Solved vs Remaining Matrix

### A. Solved / Calibrated ✅

| Item | Evidence | Status |
|------|----------|--------|
| R35 formula chain | R35 = R32 + R34 = R16 + R30 + (−R54); R54 = 0 for TUHO yr13–30 | Solved |
| R43/R67 annual H1+H2 timing | R43 = 18% × annual (H1_R41 + H2_R41); cash outflow in H2 | Solved |
| Years 1–12 R67 timing | H2 holds annual CIT for years 1–12 | Solved |
| Loss rows do not affect R35 | R36–R39 are loss-accounting rows; they reduce R41 only | Solved |
| R34 fiscal reintegration | R34 = −R54 = 0 for TUHO yr13–30; R54 formula inspected | Solved |
| Book/tax depreciation split | `taxable_income = ebitda − book_dep − deductible_int + disallowed + tax_dep + fiscal_reint` | Working |
| SHL gross-accrued source ownership | `shl_gross_accrued_interest_keur` confirmed as fixture source for tax bridge | Working |
| CO2 revenue (TUHO) | ✅ Confirmed — Y1 = 611 kEUR is **CF R35 "CO2 Certificates Sales"**; **CF R36** is the CO2 price per MWh (4.191 EUR/MWh) | Solved |
| Tax bridge CIT = 18% for TUHO | 18% confirmed for yr13–30; 31% for yr1–12 | Solved |

### B. Known Structural Differences (Intentional) ⚠️

| Item | Python (canonical) | Excel (TUHO) | Rationale |
|------|--------------------|--------------|-----------|
| **Depreciation useful life** | 30-year straight-line | 20-year (Excel Inputs D358–D379) | Python canonical policy; Excel is project-specific input |
| ATAD / thin-cap visibility | ⚠️ R34 = 0 for Y13–30 **because thin-cap is not binding in profit years**. R34 is **non-zero for Y4–12** (construction period), total around **−9,243 kEUR**, and is calibrated. Excel has a thin-cap / fiscal reintegration mechanism; it is not visible in R35 during profit years but is active in loss/construction years. | Documented |
| **Loss carryforward window** | Croatia vintage mode, 5-year × 2 semiannual periods | Rolling SUMIF over variable lookback window | Python has a canonical Croatia policy; Excel is project-specific |

### C. Known Residuals ⚠️

| Item | Amount | Period |
|------|-------:|--------|
| Observed R67 residual | **+5,271 kEUR** (Python > Excel) | yr13–30 |
| Yr13–20 residual | +5,697 kEUR | yr13–20 |
| Yr21–30 residual | −425 kEUR | yr21–30 |
| Depreciation standalone CIT impact | −2,783 kEUR (opposite sign to total) | yr13–30 net |
| Remaining unallocated after depreciation | ≈+8,055 kEUR | approximate |
| **Per-period average residual** | **+293 kEUR/yr** (5,271 ÷ 18) | annual avg |

The residual is **documented, not mathematically closed**. It is considered acceptable for **provisional calibration governance**, not final bankable parity.

### D. Intentionally Blocked / Runtime-Disabled 🚫

| Item | Status | Reason |
|------|--------|--------|
| R99 runtime-source promotion | BLOCKED | Residual not externally reviewed |
| R102 promotion | BLOCKED | Same as above |
| SHL FCF runtime source | NOT APPROVED | Requires R99 promotion gate |
| TUHO depreciation bridge | NOT IMPLEMENTED | Would flip yr21–30 gap; future architecture preferred |
| Factory opt-in | NOT ACTIVE | Per-test constraint |

### E. Future Architecture Requirements 📋

| Item | Owner | Priority |
|------|-------|----------|
| Domain/depreciation module with per-category `useful_life_years` from project inputs | Future Phase | P1 |
| Loss-window governance clarification (Croatian 5yr × 2 vs Excel rolling window) | Future Phase | P2 |
| R99/R102 design with guardrails and override mechanisms | Future Phase | P3 |
| Tax validation sign-off before any R99 design work | External reviewer | Gate |

---

## Signed Driver Waterfall Summary

**⚠️ These are approximate standalone driver impacts. They are non-additive due to interactions through the loss carryforward engine. Do not infer simple tax-mechanics direction from the standalone driver signs. These signs come from diagnostic counterfactuals and are affected by substitution order and loss-engine interactions.**

| Driver | Approx CIT Impact (kEUR) | Direction / Note | Confidence |
|--------|------------------------------:|-------------------|------------|
| **Depreciation useful-life mismatch** | **−2,783 net** | Standalone estimate; yr13–20 +1,597 / yr21–30 −4,380; sign depends on substitution order | High |
| SHL gross-accrued (Python fixture vs Excel) | −2,209 | Standalone counterfactual estimate; sign depends on substitution order and loss-engine interaction; not isolated proof | Medium |
| Senior interest delta | −2,023 | Standalone counterfactual estimate; sign depends on substitution order and loss-engine interaction; not isolated proof | Medium |
| EBITDA / source delta | −1,754 | Standalone counterfactual estimate; not additive | Medium |
| Loss carryforward (yr13 only) | −2,043 | Yr13 timing effect; interacts with annual R41 and loss engine | High |
| **Remaining unattributed** | **≈+8,055** | Not a closed waterfall; see validation pack CSV | Low |

The **signed direction** of each driver is reliable. The **magnitudes** are approximate standalone estimates and should not be summed to claim mathematical closure. External reviewers should treat the residual as a single documented figure (+5,271 kEUR yr13–30) rather than a sum of driver impacts.

---

## R43 / R67 CIT Rate Confirmation

Excel R43 / CF R67 is confirmed as:
```
CIT = 18% × annual (H1_R41 + H2_R41)
```
Cash tax outflow is recorded in H2 of each operating year. This is consistent across all TUHO operating years 13–30. The tax rate is 18% for yr13–30.

---

## Governance Decisions

The following governance decisions were made in `phase6-r67-residual-decision` (PR #79) and are recorded here for institutional continuity:

| Decision | Decision | Rationale |
|----------|----------|-----------|
| Python 30-year useful life | **Remains canonical** | Model-wide coherent policy; not project-specific |
| Excel 20-year useful life | **Project-specific input** | Acceptable divergence; documented |
| Depreciation bridge | **NOT implemented now** | Would flip yr21–30 gap; future per-category architecture preferred |
| R99/R102 promotion | **BLOCKED** | Requires external review sign-off on residual |
| SHL FCF runtime source | **Not approved** | Requires R99 promotion gate first |
| Residual | **Provisionally accepted** | Documented but not mathematically closed; external review required |

**No TUHO-only depreciation plug was implemented.** Future depreciation architecture should support configurable `useful_life_years` per asset category sourced from project inputs.

---

## Institutional Readiness Assessment

### Sufficient for Internal Validation ✅

| Item | Assessment |
|------|------------|
| R35 formula chain | ✅ Complete — formula inspected and reconciled |
| R43/R67 timing | ✅ Complete — annual H1+H2, cash in H2 |
| Loss mechanics | ✅ Documented — R36–R39 affect R41, not R35 |
| Tax bridge CIT rate | ✅ 18% confirmed for yr13–30 |
| Depreciation driver | ✅ Identified and quantified |
| Test suite | ✅ 54/54 tests passing |

### NOT Sufficient for Final Bankable Parity ⚠️

| Item | Gap |
|------|-----|
| R67 residual within tolerance | **FAIL** — +5,271 kEUR (yr13–30) not within any documented tolerance |
| Per-period delta tolerance | **Unresolved** — no formal tolerance table exists |
| R35 parity | **Partial** — formula known but not fully bridged; minor gaps remain |
| Loss engine parity | **Partial** — yr13 only; full year-by-year reconciliation not performed |
| External reviewer sign-off | **Not obtained** — provisional acceptance only |
| Configurable depreciation | **Not implemented** — domain/depreciation module needed |

### Residual Magnitude Assessment

| Metric | Value | Assessment |
|--------|------:|------------|
| Total residual (yr13–30) | +5,271 kEUR | Material but documented |
| As % of total Excel CIT (38,241 kEUR) | **13.8%** | Above typical calibration tolerance |
| Per-period average | +293 kEUR/yr | Small relative to revenue |
| Yr21–30 gap sign | **Negative** (−425 kEUR) | Python underpays slightly |

**13.8% of total Excel cash tax** is not sufficient for "within tolerance" parity. External review is required before any bankability certification.

### Recommended Tolerances (for future R99 gate)

| Gate | Suggested Tolerance |
|------|-------------------|
| Annual R67 delta | ±200 kEUR/yr (≈3% of Excel annual tax) |
| Yr13–30 cumulative | ±2,000 kEUR |
| Per-period R35 | ±500 kEUR/period |

---

## Canonical Decisions Pending

| Decision | Options | Current State |
|----------|---------|--------------|
| **Useful life policy** | 20y (Excel) vs 30y (Python) vs configurable | Python canonical = 30y; Excel = 20y; **configurable preferred** |
| **Loss carryforward canonical policy** | Croatian 5-year × 2 semiannual vs Excel rolling window | Python uses Croatia policy; **Excel rolling window not replicated** |
| **Future configurable depreciation engine** | Mandatory before pilot release vs TUHO-only bridge | **Mandatory** — per-category useful_life_years from project inputs |
| **Loss window governance** | Preserve Croatia vintage mode vs replicate Excel rolling SUMIF | Croatia mode preserved; **Excel window not replicated** |

---

## R99/R102 Gate Table

| Gate | Status | Notes |
|------|--------|-------|
| R67 residual within tolerance | **FAIL** | +5,271 kEUR (not within documented tolerance) |
| Per-period R67 delta tolerance | **Unresolved** | No formal tolerance table yet |
| R35 formula parity | **Partial** | Formula documented; bridge fidelity not 100% |
| Loss engine parity | **Partial** | yr13 confirmed; full reconciliation not complete |
| R34 fiscal reintegration parity | **PASS** | R34 = 0 for TUHO yr13–30; confirmed |
| Depreciation useful-life aligned | **FAIL** | Excel 20y vs Python 30y; known structural difference |
| CO2 revenue (TUHO) | **PASS** | Y1 = 611 kEUR, co2_price = 4.191 EUR/MWh |
| Tax rate confirmation | **PASS** | 18% for yr13–30 confirmed |
| R99 design complete | **NO** | Not started |
| R99 guardrails defined | **NO** | Not started |
| External reviewer sign-off | **NO** | Not obtained |
| SHL FCF runtime source approved | **NO** | Requires R99 promotion first |

---

## Future Roadmap

| Step | Branch / Action | Dependency |
|------|-----------------|------------|
| 1 | `phase6-tax-validation-pack` | This document — compiles evidence |
| 2 | External / Claude review sign-off | Step 1 complete |
| 3 | `phase6-depreciation-per-category-useful-life` | Domain/depreciation module with configurable useful_life_years | Step 2 sign-off |
| 4 | Loss-window governance clarification | Step 2 sign-off |
| 5 | `phase6-r99-runtime-source-promotion-design` | Guardrails, override mechanisms, tolerance tables | Step 3+4 complete |
| 6 | Sponsor economics / later phases | Independent | Parallel |

---

## Validation
- Tests: 54/54 passed (4 suites)
- Production code: NO changes
- Default behavior: NO CHANGE
- R99/R102: BLOCKED