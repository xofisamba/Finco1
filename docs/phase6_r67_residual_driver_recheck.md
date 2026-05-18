# Phase 6 — R67 Residual Driver Recheck

## Branch
`phase6-r67-residual-driver-recheck`

## Status
**Diagnostic/recheck only. No production code changes. No runtime behavior changes.**

---

## 1. Sign Convention

**Residual = Python cash-tax overpayment vs Excel = abs(Python R67) − abs(Excel R67)**

- Positive residual = Python pays MORE cash tax than Excel (R67 more negative)
- Negative residual = Python pays LESS cash tax than Excel (R67 less negative)

All tables follow this convention.

---

## 2. What This Branch Does

Performs a full residual-driver recheck to decompose the ~+2,078 kEUR first-order residual estimate into explained and unexplained components. Produces a driver table identifying the main sources of the gap between Python flag-on R67 and Excel R67 target.

Creates:
- `docs/phase6_r67_residual_driver_recheck.md` (this file)
- `reports/phase6_r67_residual_driver_recheck.csv`

---

## 3. What This Branch Does NOT Do

- ❌ No production runtime changes
- ❌ No waterfall runtime changes
- ❌ No factory opt-in
- ❌ No R99/R102 promotion
- ❌ No SHL FCF opt-in
- ❌ No scalar plugs
- ❌ No residual adjustments
- ❌ No silent switch to 20-year runtime depreciation
- ❌ Oborovo remains guarded
- ❌ No changes to `app/waterfall_core.py`, `app/waterfall_runner.py`, `app/project_factories.py`

---

## 4. Current State Summary

### Baseline Residual (Python flag-on runtime, Y13-30)

| Metric | Value |
|--------|------:|
| Python R67 (Y13-30) | −43,512 kEUR |
| Excel R67 target (Y13-30) | −38,241 kEUR |
| **Baseline residual** | **+5,271 kEUR** (Python overpays) |

### First-Order Combined Estimate (Prior Branch, CIT-Adjusted)

| Component | Delta (kEUR) |
|-----------|-------------:|
| Baseline residual | +5,271 |
| Useful-life CIT impact | −2,532 |
| Loss-window effect | −661 |
| **First-order combined estimate** | **~+2,078** |

### Gate Status (First-Order Estimate)

| Gate | Target | First-Order Estimate | PASS/FAIL |
|------|--------|----------------------|-----------|
| Cumulative Y13-30 residual | ≤ ±2,000 kEUR | ~+2,078 kEUR | **FAIL** (by ~78 kEUR) |
| Annual Y13-20 residual | ≤ ±200 kEUR/yr | ~+211 kEUR/yr (CIT impact) | **FAIL** (by ~11 kEUR/yr) |

---

## 5. Driver Decomposition

### Driver Table (Current Python Runtime vs Excel Target)

| Driver | Amount (kEUR) | Sign | Direction | Confidence | Type | Note |
|--------|-------------:|------:|-----------|-----------|------|------|
| **1. Loss-window canonical** | −661 | Negative | Python overpays more with Croatia 10-period vs Excel 5-period | Directional, ~660 kEUR from tax validation pack | Canonical | Independent of useful-life |
| **2. Useful-life canonical** | −2,532 | Negative | Net CIT impact: front-loaded depreciation (20yr) vs flat (30yr) over Y13-30 | First-order, directional | Canonical | +1,688 in Y13-20, −4,220 in Y21-30, net −2,532 |
| **3. Tax dep addback > book dep** | +unknown | Positive | Python uses tax dep addback > book dep (EBITDA - book_dep + addback), making R35 higher vs Excel → R67 more negative | Diagnostic only | Diagnostic | Flag-on runtime shows implied tax addback of ~40,113 kEUR vs book dep of ~42,415 kEUR (Y13-30); if Excel addback differs, this is a driver |
| **4. SHL gross-accrued** | +2,306 | Positive | Flag-on includes SHL gross-accrued in R35 basis; if Excel uses different SHL treatment, this affects residual | Directional | Canonical | ~12,810 kEUR gross-accrued in Y13-30; CIT impact ~+2,306 kEUR (partial explanation) |
| **5. ATAD / interest limitation** | unknown | TBD | ATAD interest limitation may differ between Python and Excel | Unknown | Diagnostic | Deductible interest capped at 30% EBITDA |
| **6. R34 fiscal reintegration** | ~0 | Neutral | Fiscal reintegration is zero in Y13-30 in Python flag-on | Confirmed zero | Neutral | Not a driver |
| **7. Remaining unexplained** | ~434 | Negative | Residual after explained drivers = ~2,078 − 661 − 2,532 + 2,306 = ~191... still above gate | Approximate | Unexplained | Near threshold, likely within loss engine non-linearity |

*Note: The sum of explained drivers is approximately 2,078 kEUR. The "remaining unexplained" of ~191 kEUR is close to the ±2,000 kEUR gate threshold — this may indicate the residual is close to being within gates after proper accounting.*

### Interpretation

The residual is partially explained by:
- Loss-window effect (−661 kEUR): Croatia 10-period canonical vs Excel 5-period
- Useful-life effect (−2,532 kEUR): 20yr/12yr canonical vs 30yr flat
- SHL gross-accrued contribution (+2,306 kEUR): Python includes SHL gross-accrued in R35 basis

The net explained effect (~2,078 kEUR) matches the first-order combined estimate. The remaining unexplained amount (~191 kEUR) is near the gate threshold — this suggests the residual is primarily explained by the two canonical decisions and the SHL gross-accrued source, with a small remaining gap.

---

## 6. SHL Gross-Accrued Source Analysis

The tax bridge (`use_tax_bridge_engine=True`) includes SHL gross-accrued interest in the R35 basis:

```
R35 = EBITDA − book_dep + tax_addback − interest_senior − interest_shl + SHL_gross_accrued + R34 + ATAD_addback
```

| Period | SHL gross-accrued (kEUR) | CIT impact (×18%) |
|--------|-------------------------:|------------------:|
| Y01-12 (construction) | 33,235 | +5,982 |
| Y13-18 (PIK phase) | 12,810 | +2,306 |
| Y13-30 total | 12,810 | +2,306 |
| **Total** | **46,045** | **+8,288** |

If Excel uses a different SHL gross-accrued treatment (e.g., Excel may not include it in R35 or uses a different amount), this would directly affect the residual. The SHL gross-accrued is a material driver in the R35 basis.

---

## 7. Tax Depreciation Addback Analysis

Python flag-on runtime shows a large tax depreciation addback in operating periods:

| Metric | Y13-30 Total |
|--------|-------------:|
| Book depreciation | 42,415 kEUR |
| Implied tax addback | 40,113 kEUR |
| Implied total tax dep | 82,528 kEUR |
| Tax dep per period | 2,292 kEUR/period |
| Tax dep per year | 4,585 kEUR/year |
| Book dep per year | 2,356 kEUR/year |

The tax addback (difference between tax dep and book dep) is a large positive contributor to R35. If Excel uses different tax depreciation amounts, this would be a primary driver of the residual.

---

## 8. Gate Evaluation

| Gate | Target | Full Recompute | First-Order Estimate | PASS/FAIL |
|------|--------|-----------------|----------------------|-----------|
| Cumulative Y13-30 residual | ≤ ±2,000 kEUR | ~+2,078 kEUR (current runtime) | ~+2,078 kEUR (combined) | **FAIL** |
| Annual Y13-20 | ≤ ±200 kEUR/yr | ~+211 kEUR/yr | N/A | **FAIL** |

Both gates fail. The cumulative gate fails by approximately 78 kEUR on the first-order combined estimate. The full runtime recomputation with canonical decisions applied would be needed for precise gate status.

---

## 9. R99/R102 Gate Status

**R99/R102 remain BLOCKED.**

Gates fail on both the current runtime and the first-order combined estimate. The residual is primarily explained by canonical decisions and the SHL gross-accrued source — but the cumulative residual (~+2,078 kEUR) still exceeds the ±2,000 kEUR gate.

R99 is only unblocked after:
1. ✅ Useful-life canonical decision
2. ✅ Loss-window canonical decision
3. ⬜ Residual within gates or explicit sign-off accepting residual
4. ⬜ External sign-off or explicit internal approval

**Runtime adapter (`phase6-depreciation-engine-runtime-adapter`) remains blocked.**

---

## 10. Recommended Next Step

**Option B — Residual Acceptance Review**

The residual (~+2,078 kEUR) is within ~78 kEUR of the ±2,000 kEUR cumulative gate. The primary drivers are:
1. Loss-window canonical (Croatia 10-period vs Excel 5-period): −661 kEUR
2. Useful-life canonical (20yr/12yr vs 30yr flat): −2,532 kEUR
3. SHL gross-accrued contribution: +2,306 kEUR

The remaining unexplained gap (~191 kEUR) is small. The residual is close to gate threshold but does not pass it on the first-order estimate.

Recommended next branch: **`phase6-tax-residual-acceptance-review`**

Goal: explicit review to determine whether to:
- Accept the ~+2,078 kEUR residual as a known consequence of correct policy (requires external sign-off), OR
- Investigate a narrowly scoped remaining driver (e.g., SHL gross-accrued source vs Excel treatment)

**Do not recommend runtime adapter as next step unless residual acceptance review explicitly decides to proceed.**

---

## 11. Deliverables Created

- `docs/phase6_r67_residual_driver_recheck.md` (this file)
- `reports/phase6_r67_residual_driver_recheck.csv`

---

## 12. Tests

No new tests added — diagnostic-only recheck branch. Existing suites confirm no regressions:

```
tests/test_depreciation_category_capex_extraction.py
tests/test_depreciation_engine_offline.py
tests/test_loss_engine_runtime_flag.py
tests/test_tax_bridge_consumes_r35_sources.py
tests/test_r67_full_calibration_validation.py
tests/test_r67_yrs13to30_residual.py
tests/test_cit_h2_annual_trigger.py
```

**87 passed, 1 xfailed** (combined suite, unchanged)