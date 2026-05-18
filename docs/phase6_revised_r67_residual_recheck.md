# Phase 6 — Revised R67 Residual Recheck

## Branch
`phase6-revised-r67-residual-recheck`

## Status
**Diagnostic/recheck only. No production code changes. No runtime behavior changes.**

---

## 1. Sign Convention

**Residual** is presented as Python cash-tax overpayment vs Excel:
`residual = abs(Python R67) − abs(Excel R67)`

- **Positive residual** = Python pays MORE cash tax than Excel (R67 more negative)
- **Negative residual** = Python pays LESS cash tax than Excel (R67 less negative)

All tables and delta columns follow this convention.

---

## 2. What This Branch Does

Recomputes and documents the revised TUHO R67 residual after the two canonical decisions are formally documented:
1. Loss-window canonical (PR #85): Croatia legal 10-period vintage model
2. Useful-life canonical (PR #86): project-input first, Croatia 20yr/12yr template fallback

**Methodology correction:** Depreciation delta must be converted to CIT/R67 impact via the 18% CIT rate before comparing to R67 residual. Depreciation delta ≠ R67 delta.

Creates:
- `docs/phase6_revised_r67_residual_recheck.md` (this file)
- `reports/phase6_revised_r67_residual_recheck.csv`

---

## 3. What This Branch Does NOT Do

- ❌ No production runtime changes
- ❌ No waterfall runtime changes
- ❌ No factory opt-in
- ❌ No R99/R102 promotion
- ❌ No SHL FCF opt-in
- ❌ No scalar plugs
- ❌ No residual adjustments
- ❌ No silent switch from 30-year to 20-year runtime depreciation
- ❌ Oborovo remains guarded
- ❌ No changes to `app/waterfall_core.py`, `app/waterfall_runner.py`, `app/project_factories.py`

---

## 4. Baseline Residual Table (Pre-Canonical Decisions)

Current runtime state (`use_tax_bridge_engine=True`, TUHO flag-on):

| Segment | Python R67 (kEUR) | Excel Target (kEUR) | Residual (kEUR) |
|---------|------------------:|--------------------:|----------------:|
| Yr1–12 | 0.00 | 0.00 | 0.00 |
| **Yr13–30** | **−43,512.36** | **−38,240.90** | **+5,271.46** |

*Positive residual means Python overpays Excel by 5,271 kEUR over Yr13–30.*

---

## 5. Corrected Counterfactual Methodology

**R67 = cash tax = CIT.** Depreciation affects taxable income, which determines CIT. The approximate CIT/R67 impact of a depreciation change is:

```
CIT impact ≈ depreciation_delta × 18% (CIT rate)
```

Depreciation delta is NOT directly comparable to R67 residual — conversion required.

---

## 6. Useful-Life Canonical Counterfactual (Offline, CIT-Adjusted)

Applying 20yr main + 12yr financing via offline depreciation engine, then converting to CIT impact:

### Depreciation Delta by Segment

| Segment | 30yr Annual Dep (kEUR) | 20+12yr Annual Dep (kEUR) | Dep Delta (kEUR) | CIT Rate | CIT Impact (kEUR) | R67 Direction |
|---------|----------------------:|--------------------------:|----------------:|--------:|-------------------:|---------------|
| Yr13–20 (8 yrs) | 2,344.26 | 3,516.39 | **+9,377** | ×18% | **+1,688** | R67 less negative |
| Yr21–30 (10 yrs) | 2,344.26 | 0.00 | **−23,443** | ×18% | **−4,220** | R67 more negative |
| **Yr13–30 total** | — | — | **−14,065** | ×18% | **−2,532** | **Net: R67 more negative** |

### CIT Impact Calculation

| Step | Value |
|------|------:|
| Yr13–20 dep delta | +9,377 kEUR |
| Yr13–20 CIT impact | +9,377 × 18% = **+1,688 kEUR** (less cash tax) |
| Yr21–30 dep delta | −23,443 kEUR |
| Yr21–30 CIT impact | −23,443 × 18% = **−4,220 kEUR** (more cash tax) |
| **Net CIT impact** | **−2,532 kEUR** (Python pays more overall vs Excel) |

### Estimated New R67

| Component | Value (kEUR) |
|-----------|-------------:|
| Baseline residual | +5,271 |
| + Useful-life CIT impact | −2,532 |
| **Subtotal** | **+2,739** |

*Note: This is a first-order approximation. Loss engine non-linearity means actual R67 after re-running the tax bridge with canonical lives may differ. Do not treat as precise prediction.*

---

## 7. Loss-Window Counterfactual (Directional)

The loss-window canonical (Croatia 10-period) vs Excel 5-period diagnostic override:

| Effect | Value | Direction |
|--------|------:|----------|
| Croatia 10-period vs Excel 5-period CIT delta | ~−661 kEUR | R67 more negative |

*Directional estimate from tax validation pack. Within same depreciation/source basis only — do not compare across different source bases.*

---

## 8. Combined Canonical Estimate (CIT-Adjusted)

| Component | Delta (kEUR) |
|-----------|-------------:|
| Baseline residual | +5,271 |
| Useful-life CIT impact | −2,532 |
| Loss-window effect | −661 |
| **Estimated combined residual** | **+2,078** |

**First-order CIT-adjusted combined residual estimate ≈ +2,078 kEUR** (Python overpays Excel by ~2,078 kEUR over Yr13–30; first-order estimate, pending full recomputation / external sign-off)

This is substantially lower than the baseline +5,271 kEUR. The useful-life canonical decision, when properly converted to CIT impact, reduces the residual. However, the result remains above the cumulative gate threshold (±2,000 kEUR) and still requires full residual-driver recheck or external sign-off.

---

## 9. Residual Gates (Corrected)

After applying the corrected CIT-adjusted methodology:

| Gate | Target | Baseline | After Canonical (est.) | PASS/FAIL |
|------|--------|----------|------------------------|-----------|
| Cumulative Y13–30 residual | ≤ ±2,000 kEUR | +5,271 kEUR | ~+2,078 kEUR | **FAIL** (barely, approx) |
| Max annual residual (Yr13–20) | ≤ ±200 kEUR/yr | N/A | ~+211 kEUR/yr (CIT impact) | **FAIL** |

**Cumulative gate:** ~+2,078 kEUR vs ±2,000 kEUR threshold — FAIL by ~78 kEUR on this first-order estimate, pending full recomputation / external sign-off.

**Annual gate:** +211 kEUR/yr (CIT impact) vs ±200 kEUR/yr — FAIL by ~11 kEUR/yr on this first-order estimate. Both gates fail on this first-order estimate, pending full recomputation / external sign-off.

*Both gates remain FAIL after corrected methodology. The useful-life canonical decision does not bring residual within gates on its own.*

---

## 10. Explaining Residual Movement

### Why Does the Corrected Estimate Show Improvement?

Baseline residual was +5,271 kEUR (Python overpays). After applying CIT-adjusted useful-life effect (−2,532 kEUR):

- Yr13–20: higher depreciation → lower taxable income → less CIT paid (+1,688 kEUR benefit) — Python overpayment reduced
- Yr21–30: zero depreciation → higher taxable income → more CIT paid (−4,220 kEUR cost) — Python overpayment increased

The net CIT impact (−2,532 kEUR) partially offsets the baseline overpayment, reducing residual from +5,271 to ~+2,739 kEUR before loss-window. Adding loss-window (−661 kEUR) gives ~+2,078 kEUR.

### Why Does the Residual Still Fail Gates?

Even after improvement, the first-order residual estimate (+2,078 kEUR) remains above the ±2,000 kEUR cumulative threshold. The annual gate (+211 kEUR/yr) also fails by ~11 kEUR/yr.

The canonical decisions do not fully close the gap — they reduce it. Remaining questions:
- Are there additional unexplained drivers beyond useful-life and loss-window?
- What is the actual full-recomputed R67 after wiring canonical decisions?
- Does external sign-off or residual acceptance apply?

---

## 11. R99/R102 Gate Status

**R99/R102 remain BLOCKED.**

This branch does NOT unblock R99. Gates FAIL both before and after the canonical decisions (though the corrected residual is substantially lower than the uncorrected estimate suggested).

R99 is only unblocked after:
1. ✅ Useful-life canonical decision
2. ✅ Loss-window canonical decision
3. ⬜ Revised R67 residual recheck — **gates still FAIL; external sign-off required**
4. ⬜ External sign-off or explicit internal approval to proceed despite gate FAIL

**Runtime adapter (`phase6-depreciation-engine-runtime-adapter`) remains blocked.**

---

## 12. Recommended Next Branch

**`phase6-r67-residual-driver-recheck`**

Three honest options for consideration:
- **Option A — Accept residual as known consequence of correct policy**; proceed to runtime adapter design with gate FAIL (requires external sign-off)
- **Option B — Full residual-driver recheck**; goal is full driver recheck / full recomputation to determine whether the ~+2,078 kEUR first-order estimate can be reduced below the +-2,000 kEUR gate threshold or must be accepted with external sign-off
- **Option C — Do not proceed to runtime adapter** until gates pass or explicit residual acceptance

This branch shows the corrected first-order residual estimate is approximately +2,078 kEUR - substantially lower than the baseline +5,271 kEUR and substantially lower than the initial uncorrected estimate (the ~-20,000 kEUR figure in an earlier draft was a methodology error; depreciation delta is not directly comparable to R67 without applying the 18% CIT rate). Gates fail on this first-order estimate, pending full recomputation / external sign-off. Option B is the recommended next step before any decision to proceed despite gate FAIL. Option B is the recommended next step before any decision to proceed despite gate FAIL.

---

## 13. Deliverables Created

- `docs/phase6_revised_r67_residual_recheck.md` (this file)
- `reports/phase6_revised_r67_residual_recheck.csv`

---

## 14. Tests

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