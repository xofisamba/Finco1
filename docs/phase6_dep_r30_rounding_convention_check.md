# Phase 6 — Dep R30 Rounding / Leap-Year Convention Check

## Branch
`phase6-dep-r30-rounding-convention-check`

## Status
**Diagnostic only. No runtime integration. No production behavior change.**

---

## 1. What This Branch Does

Investigates why the offline depreciation engine with extracted TUHO category CAPEX produces near-parity (~3.13 kEUR max diff) but not exact ±1 kEUR per-period parity against Excel Dep R30.

Creates:
- `docs/phase6_dep_r30_rounding_convention_check.md` (this file)
- `reports/phase6_dep_r30_rounding_convention_check.csv`

---

## 2. What This Branch Does NOT Do

- ❌ No changes to `app/waterfall_core.py`, `app/waterfall_runner.py`, `app/project_factories.py`
- ❌ No factory opt-in
- ❌ No R99/R102 promotion
- ❌ No SHL FCF opt-in
- ❌ No scalar fitting to force parity
- ❌ Do not treat ±5 kEUR as final runtime gate

---

## 3. Root Cause Found

### Summary

| Aspect | Excel Dep R30 | Offline Engine |
|--------|--------------|----------------|
| **20yr categories** | `capex_i / life_i * leap_frac` | `capex_i / (life_i * 2)` (flat) |
| **12yr categories** | Same formula, active op_idx 1–23 | Same flat formula |
| **Leap-year frac** | Applied per period (0.49589 / 0.50411 / 0.49727 / 0.50273) | Not applied |
| **Period result** | `sum_i(capex_i/life_i * frac)` | `sum_i(capex_i/(life_i*2))` = `main_total/40` constant |

**Excel uses per-category annual depreciation × leap-year fraction per period.**  
**Engine uses a flat `main_total / 40` constant after 12yr categories exit (op_idx ≥ 24).**

### The Leap-Year Fraction

The Dep sheet (row 5) stores the fraction of each semiannual period that falls within the calendar half-year, accounting for leap years:

| Fraction value | Approximation | Occurs |
|----------------|---------------|--------|
| `0.4958904109589041` | ≈ 0.496 | H1 periods in standard years |
| `0.5041095890410959` | ≈ 0.504 | H2 periods in standard years |
| `0.4972677595628415` | ≈ 0.497 | H1 periods in leap years (years 3, 7, 11…) |
| `0.5027322404371585` | ≈ 0.503 | H2 periods in leap years |

Excel per-period depreciation for each category: `capex_i / life_i * leap_frac`

Engine per-period depreciation: `capex_i / (life_i * 2)` (straight-line, no leap frac)

Since `sum_i(capex_i / life_i) = main_total / 20`, Excel gives:
- H1 (frac≈0.496): `main_total/20 * 0.496 ≈ 0.992 * main_total/40`
- H2 (frac≈0.504): `main_total/20 * 0.504 ≈ 1.008 * main_total/40`

### Period-Level Differential Pattern

Engine constant: `main_total/40 = 70327.87 / 40 = 1758.20 kEUR` (op_idx 24–39)

| CSV op_idx | Excel col | Year | Leap frac | Excel Dep R30 | Engine | Diff |
|-----------|-----------|------|-----------|-------------:|-------:|-----:|
| 24 | AF | 13 H1 | 0.495890 | 1756.45 | 1758.20 | +1.75 |
| 26 | AG | 14 H1 | 0.495890 | 1756.45 | 1758.20 | +1.75 |
| 28 | AI | 15 H1 | 0.504110 | 1761.33 | 1758.20 | **−3.13** |
| 30 | AK | 16 H1 | 0.497268 | 1756.45 | 1758.20 | +1.75 |
| 32 | AM | 17 H1 | 0.495890 | 1756.45 | 1758.20 | +1.75 |
| 34 | AO | 18 H1 | 0.495890 | 1756.45 | 1758.20 | +1.75 |
| 36 | AQ | 19 H1 | 0.504110 | 1761.33 | 1758.20 | **−3.13** |
| 38 | AS | 20 H1 | 0.495890 | 1756.45 | 1758.20 | +1.75 |

Max \|diff\|: **3.13 kEUR** (~0.18% of total annual depreciation)  
Mean \|diff\|: **0.93 kEUR**

The diff sign alternates based on whether `leap_frac < 0.5` (engine overestimates) or `> 0.5` (engine underestimates).

### Why the 12yr/20yr Boundary Creates a Step

At op_idx 24 (first H1 after year 12), 12yr categories (IDCs, bank_fees, commitment_fees) end:
- **op_idx 0–23**: Engine constant = 1854.12 = `(main_total + 12yr_total) / 40`
- **op_idx 24–39**: Engine constant = 1758.20 = `main_total / 40`

The engine steps down from 1854.12 → 1758.20 at op_idx 24, while Excel gradually transitions because the 12yr categories end gradually (last active period is op_idx 23).

### Not a Missing Source Data Problem

The category CAPEX extraction (PR #83) correctly identified all 17 categories. The 3.13 kEUR diff is not due to missing categories — it is a **calculation convention difference** between Excel's leap-year-adjusted annual formula and the engine's flat straight-line formula.

---

## 4. Can Exact ±1 kEUR Parity Be Achieved?

**No exact ±1 kEUR parity under the current flat semiannual convention.**

To match Excel exactly, the engine would need per-category leap frac application — equivalent to changing the formula from per-period flat straight-line to per-annual-with-leap-adjustment. This is a structural convention change, not a scalar plug.

Exact ±1 kEUR parity cannot be achieved by the current flat semiannual convention. It would require adding an explicit `leap_frac / actual-day` semiannual convention to the engine. That would be a legitimate optional convention if designed generically, not a scalar plug.

**Acceptable resolution:**
- Document near-parity as final diagnostic result
- Keep ±5 kEUR as the diagnostic tolerance for the offline engine
- Stage 3 (runtime adapter) should proceed with explicit awareness of ±5 kEUR contribution uncertainty from depreciation

---

## 5. Conclusion

**Root cause of 3.13 kEUR max diff:**
- Excel: `sum_i(capex_i / life_i) * leap_frac` per period (annual rate × leap fraction)
- Engine: flat `main_total / 40` constant after 12yr exit (no leap frac applied)
- Difference = `main_total / 40 * (leap_frac - 0.5)`, max when leap_frac = 0.50411

**Not a missing data problem.** All 17 categories correctly extracted.

**Exact ±1 kEUR parity cannot be achieved under the current flat semiannual convention. It would require adding a generic actual-day / leap_frac depreciation convention to the offline engine. That is a legitimate optional convention if designed generically, but it is a structural convention change and should not be slipped in as a silent fix.**

**Recommendation:** Accept near-parity, document ±5 kEUR as diagnostic-only, proceed with Stage 3 design awareness.

---

## 6. Test Results

```
pytest tests/test_depreciation_category_capex_extraction.py -v
pytest tests/test_depreciation_engine_offline.py -v
pytest tests/test_depreciation_engine.py -v
pytest tests/test_r67_yrs13to30_residual.py -v
pytest tests/test_cit_h2_annual_trigger.py -v
pytest tests/test_r67_full_calibration_validation.py -v
pytest tests/test_tax_bridge_consumes_r35_sources.py -v
```

**94 passed, 1 xfailed** (unchanged from PR #83)

---

## 7. Stage 3 Status

**Stage 3 (runtime adapter) remains BLOCKED pending:**
1. ✅ Category-level CAPEX split — **RESOLVED** (PR #83)
2. ✅ Root cause identified — leap-year convention (this branch)
3. ⬜ Useful-life canonical decision — **PENDING**
4. ⬜ Loss-window canonical decision — **PENDING**
5. ⬜ R99 external sign-off — **PENDING**

**±5 kEUR is diagnostic only. Not a Stage 3 gate.**

---

## 8. Files Created / Changed

### New Files
- `reports/phase6_dep_r30_rounding_convention_check.csv` — full 60-period diagnostic table
- `docs/phase6_dep_r30_rounding_convention_check.md` — this file

### No Production / Runtime Files Changed
- `app/waterfall_core.py` — NOT MODIFIED
- `app/waterfall_runner.py` — NOT MODIFIED
- `app/project_factories.py` — NOT MODIFIED

---

## 9. Recommended Next Branch

**`phase6-loss-window-design`** — resolve the 5-year Croatian loss window rolling SUMIF vs pool design first (long-standing blocker).

OR: **`phase6-depreciation-engine-runtime-adapter`** — Stage 3, with explicit awareness that the depreciation contribution to R67 has ~3 kEUR per-period uncertainty due to leap-year convention difference.

**Do NOT recommend:** `phase6-dep-r30-rounding-convention-check` as a separate branch — this investigation is complete and documented. The ±5 kEUR diagnostic tolerance is not a gate that can be fixed without structural convention changes.