# Phase 6 — R67 Residual Driver Recheck

## Branch
`phase6-r67-residual-driver-recheck`

## Status
**First-order diagnostic decomposition. Not a full tax-bridge recomputation.**

---

## 1. Sign Convention

**Residual = Python cash-tax overpayment vs Excel = abs(Python R67) − abs(Excel R67)**

- Positive residual = Python pays MORE cash tax than Excel (R67 more negative)
- Negative residual = Python pays LESS cash tax than Excel (R67 less negative)

All tables follow this convention.

---

## 2. What This Branch Does

Performs a **first-order residual-driver diagnostic decomposition**. This is not a full tax-bridge recomputation.

The goal is to identify candidate drivers of the residual between Python flag-on R67 and Excel R67 target, and to document which drivers are confirmed vs. speculative.

**Full runtime recomputation with canonical useful-life and loss-window settings remains future work.**

Creates:
- `docs/phase6_r67_residual_driver_recheck.md` (this file)
- `reports/phase6_r67_residual_driver_recheck.csv`

---

## 3. What This Branch Does NOT Do

- ❌ Not a full tax-bridge recomputation
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
| **Baseline residual** | **+5,271 kEUR** (Python overpays Excel) |

### First-Order Combined Estimate (Prior Branch, CIT-Adjusted)

| Component | Delta (kEUR) | Sign | Note |
|-----------|-------------:|------:|------|
| Baseline residual | +5,271 | Positive | Python overpays |
| Useful-life CIT impact | −2,532 | Negative | 20yr/12yr vs 30yr flat, net CIT impact ×18% |
| Loss-window effect | −661 | Negative | Croatia 10-period vs Excel 5-period, CIT impact |
| **First-order combined residual estimate** | **~+2,078** | **Positive** | Python overpays Excel by ~2,078 kEUR |

---

## 5. Candidate Driver Decomposition

### Confirmed Canonical Drivers

| Driver | Amount (kEUR) | Sign | Direction | Confidence | Note |
|--------|-------------:|------:|-----------|-----------|------|
| **Loss-window canonical** | −661 | Negative | Python overpays more with Croatia 10-period vs Excel 5-period | Directional; ~660 kEUR from tax validation pack | Confirmed canonical direction |
| **Useful-life canonical** | −2,532 | Negative | Net CIT impact: 20yr/12yr front-loaded vs 30yr flat over Y13-30 | First-order; directional | CIT impact = dep_delta × 18%; +1,688 Y13-20, −4,220 Y21-30 |

### Candidate Drivers (Require Source Verification)

| Driver | Amount (kEUR) | Sign | Direction | Confidence | Note |
|--------|-------------:|------:|-----------|-----------|------|
| **SHL gross-accrued source basis** | up to +2,306 | Positive | Python less negative if Excel treats SHL gross-accrued differently | Candidate only; not proven as Excel/Python delta | ~12,810 kEUR SHL gross-accrued in Y13-30; ×18% = +2,306 kEUR max impact. Not yet verified as actual Excel/Python difference |
| **Tax depreciation / addback** | unknown | TBD | Python may use different tax dep addback vs Excel | Candidate only; not source-mapped | Implied tax addback ~40,113 kEUR vs book dep ~42,415 kEUR (Y13-30). This is a large number but not yet proven as residual driver |

### Non-Drivers (Confirmed)

| Driver | Amount | Confidence | Note |
|--------|--------|-----------|------|
| R34 fiscal reintegration | 0 kEUR | Confirmed zero | Y13-30 fiscal reintegration = 0 in Python flag-on |

### Waterfall Table (First-Order Estimate)

| Component | Amount (kEUR) | Note |
|-----------|-------------:|------|
| Baseline residual | +5,271 | Python flag-on vs Excel target |
| Less: Loss-window canonical effect | −661 | Croatia 10-period vs Excel 5-period |
| Less: Useful-life canonical effect | −2,532 | 20yr/12yr vs 30yr flat, CIT-adjusted |
| **Subtotal after confirmed canonical drivers** | **+2,078** | First-order estimate |
| Plus: SHL gross-accrued candidate | +2,306 | Max; not proven as Excel/Python delta |
| Plus: Tax dep/addback candidate | unknown | Large but unquantified |
| **Final residual estimate** | **not reliably quantifiable** | SHL and tax-dep drivers are candidates, not confirmed |

**Remaining unexplained: not reliably quantified in this branch.** SHL gross-accrued and tax depreciation/addback are candidate drivers requiring source-row verification before they can be used in residual acceptance.

---

## 6. Gate Evaluation (First-Order Estimate Only)

**These gate results are based on the first-order corrected estimate, not a full recomputation.**

| Gate | Target | First-Order Estimate | PASS/FAIL |
|------|--------|----------------------|-----------|
| Cumulative Y13-30 residual | ≤ ±2,000 kEUR | ~+2,078 kEUR | **FAIL** (by ~78 kEUR) |
| Annual Y13-20 residual | ≤ ±200 kEUR/yr | ~+211 kEUR/yr (CIT impact) | **FAIL** (by ~11 kEUR/yr) |

---

## 7. R99/R102 Gate Status

**R99/R102 remain BLOCKED.**

Gates fail on the first-order estimate. The residual is not reliably quantified due to unverified candidate drivers (SHL gross-accrued, tax depreciation/addback).

R99 is only unblocked after:
1. ✅ Useful-life canonical decision
2. ✅ Loss-window canonical decision
3. ⬜ Residual within gates, or explicit acceptance with documented rationale
4. ⬜ External sign-off or explicit internal approval

**Runtime adapter (`phase6-depreciation-engine-runtime-adapter`) remains blocked.**

---

## 8. Recommended Next Step

**`phase6-tax-residual-acceptance-review`** — or **`phase6-shl-taxdep-source-verification`** as a prerequisite.

Two options:
- **Option A:** Accept the ~+2,078 kEUR first-order residual as a known consequence of correct policy (requires external sign-off), OR
- **Option B:** Run a narrow source verification branch to confirm or rule out SHL gross-accrued and/or tax depreciation/addback as material drivers before deciding on acceptance

Do not recommend runtime adapter as next step unless residual acceptance is explicitly decided.

---

## 9. Deliverables Created

- `docs/phase6_r67_residual_driver_recheck.md` (this file)
- `reports/phase6_r67_residual_driver_recheck.csv`

---

## 10. Tests

No new tests added — diagnostic-only branch. Existing suites confirm no regressions:

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