# Phase 6 — Revised R67 Residual Recheck

## Branch
`phase6-revised-r67-residual-recheck`

## Status
**Diagnostic/recheck only. No production code changes. No runtime behavior changes.**

---

## 1. What This Branch Does

Recomputes and documents the revised TUHO R67 residual after the two canonical decisions are now formally documented:
1. Loss-window canonical decision (PR #85): Croatia legal 10-period vintage model
2. Useful-life canonical decision (PR #86): project-input first, Croatia 20yr/12yr template fallback

This branch does NOT promote runtime sources, enable R99/R102, or implement the canonical decisions in runtime. Counterfactuals are computed offline using the depreciation engine.

Creates:
- `docs/phase6_revised_r67_residual_recheck.md` (this file)
- `reports/phase6_revised_r67_residual_recheck.csv`

---

## 2. What This Branch Does NOT Do

- ❌ No production runtime changes
- ❌ No waterfall runtime changes
- ❌ No factory opt-in
- ❌ No R99/R102 promotion
- ❌ No SHL FCF opt-in
- ❌ No scalar plugs
- ❌ No residual adjustments
- ❌ No silent switch from 30-year to 20-year runtime depreciation
- ❌ No silent actual-day / leap_frac implementation
- ❌ Oborovo remains guarded
- ❌ No changes to `app/waterfall_core.py`, `app/waterfall_runner.py`, `app/project_factories.py`

---

## 3. Baseline Residual Table (Pre-Canonical Decisions)

Current runtime state (`use_tax_bridge_engine=True`, TUHO flag-on):

| Segment | Python R67 (kEUR) | Excel Target (kEUR) | Residual (kEUR) |
|---------|------------------:|--------------------:|----------------:|
| Yr1–12 | 0.00 | 0.00 | 0.00 |
| Yr13–20 | −15,844.88 | see note | see note |
| Yr21–30 | −27,667.48 | see note | see note |
| **Yr13–30** | **−43,512.36** | **−38,240.90** | **+5,271.46** |

*Note: Excel segment targets (Yr13–20 and Yr21–30 separately) are not explicitly extracted in this recheck. The Yr13–30 total is from `test_r67_yrs13to30_residual.py` fixtures.*

The baseline residual of **+5,271 kEUR** means Python is more negative than Excel by ~5.3M EUR over the operating period. This was documented in prior branches; no canonical decisions had been formally made at that point.

---

## 4. Depreciation Counterfactual

### What Changed in the Offline Engine

The offline `DepreciationEngine` was used to compute per-period depreciation under two configurations:

| Configuration | Main CAPEX (kEUR) | Fin. Costs (kEUR) | Main Life | Fin. Life |
|-------------|------------------:|-----------------:|----------:|----------:|
| Current (30yr flat) | 70,327.87 | 2,302.17 | 30yr | 30yr |
| Useful-life canonical | 70,327.87 | 2,302.17 | **20yr** | **12yr** |

Total CAPEX is identical in both configurations (72,630.04 kEUR). Only the depreciation timing differs.

### Per-Period Annual Depreciation Comparison

| Year | 30yr Annual (kEUR) | 20+12yr Annual (kEUR) | Delta (kEUR) | Direction |
|------|-------------------:|----------------------:|-------------:|----------|
| Yr13–20 | 2,344.26 | 3,516.39 | **+1,172.13** | More dep → lower CIT → R67 less negative |
| Yr21–30 | 2,344.26 | 0.00 | **−2,344.26** | No dep → higher CIT → R67 more negative |
| **Yr13–30 total** | **42,196.72** | **28,131.15** | **−14,065.57** | Net: R67 more negative |

### Key Observation

The 20+12yr canonical policy produces **more** depreciation in years 13–20 (assets still alive) but **zero** depreciation in years 21–30 (both main and financing assets fully written off by end of year 20). The 30yr policy produces equal depreciation throughout all 30 years.

This is the expected behavior of a shorter useful-life policy — front-loaded depreciation — but it **worsens** the R67 residual in aggregate.

---

## 5. Counterfactual Analysis

### A. Current Runtime Baseline
- `use_tax_bridge_engine=True` for TUHO
- Implied 30-year straight-line depreciation (runtime default)
- Croatia 10-period loss window (flag-on default)
- **R67 Y13–30: −43,512 kEUR** (fixture-documented)

### B. Useful-Life Canonical Counterfactual (Offline)

Applying 20yr main + 12yr financing via offline engine (no runtime change):

| Effect | Value | Direction |
|--------|------:|----------|
| Yr13–20 additional depreciation | +9,377 kEUR | R67 less negative |
| Yr21–30 reduced depreciation | −23,443 kEUR | R67 more negative |
| **Net depreciation effect** | **−14,065 kEUR** | **R67 more negative** |
| Estimated new R67 | ~−57,577 kEUR | |
| Delta vs current baseline | ~−14,065 kEUR | Residual worsens |

*Note: This is a first-order approximation. The loss engine has non-linear interactions with taxable income — the actual R67 after re-running the tax bridge with canonical lives may differ from this simple sum.*

### C. Loss-Window Counterfactual (Directional)

The loss-window canonical decision (Croatia 10-period) vs Excel 5-period diagnostic override:

| Effect | Value | Direction |
|--------|------:|----------|
| Croatia 10-period vs Excel 5-period CIT delta | ~−660 kEUR | R67 more negative (Croatia: losses expire later, more available, lower CIT) |

*This directional estimate is from the tax validation pack. The loss-window effect is independent of the depreciation effect and additive (approximately) in the first-order.*

### D. Combined Canonical Counterfactual (Estimated)

| Component | Delta vs Baseline |
|-----------|-------------------:|
| Useful-life (20+12yr) | −14,065 kEUR |
| Loss-window (Croatia 10-period) | −660 kEUR |
| **Combined estimate** | **−14,725 kEUR** |
| Estimated new R67 | **~−58,237 kEUR** |
| Residual vs Excel | **~−20,000 kEUR** |

*Warning: These estimates are directional. Non-linear loss engine interactions mean the actual combined R67 after re-computing the full tax bridge with both canonical decisions applied may differ. Do not treat these as precise predictions.*

---

## 6. Residual Gates

From the Phase 6 tax validation pack, gates are:

| Gate | Target | Estimated State | PASS/FAIL |
|------|--------|-----------------|-----------|
| Cumulative Y13–30 residual | ≤ ±2,000 kEUR | ~+5,271 kEUR (baseline) → ~−20,000 kEUR (estimated combined) | **FAIL** |
| Max annual residual | ≤ ±200 kEUR/yr | yr13–20 per-year R67 diff ~+1,172 kEUR | **FAIL** |

Both gates **FAIL** in both the baseline and the combined canonical counterfactual. The useful-life canonical decision **worsens** the cumulative residual in aggregate (net −14,065 kEUR), though it improves yr13–20 by +9,377 kEUR.

---

## 7. Explaining Residual Movement

### Why Does Useful-Life Canonical Worsen the Residual?

The 30-year flat depreciation policy spreads CAPEX evenly over 30 years. The 20+12yr canonical policy front-loads depreciation into years 13–20 (higher per-year depreciation) but zeroes out in years 21–30.

Since R67 = cumulative cash tax paid = cumulative CIT, the effect on R67 is:
- Years 13–20: Higher depreciation → lower taxable income → lower CIT → R67 less negative (positive movement of ~+9,377 kEUR)
- Years 21–30: Zero depreciation → higher taxable income → higher CIT → R67 more negative (negative movement of ~−23,443 kEUR)
- **Net: −14,065 kEUR** (worse residual)

### Why Not Choose 20+12yr Then?

The canonical decision (PR #86) was made for **legal/policy correctness**, not for minimizing the R67 residual. The 20-year useful life for wind turbines reflects the actual asset contract and industry practice. The 30-year assumption was a conservative modelling choice, not a tax-policy target.

The residual worsens as a consequence of switching to the correct policy. This is expected and documented — not a reason to reverse the canonical decision.

---

## 8. R99/R102 Gate Status

**R99/R102 remain BLOCKED.**

This branch does NOT unblock R99. The residual gates FAIL both before and after the canonical decisions. The useful-life canonical decision moves the residual in the **wrong direction** for gate compliance.

R99 is only unblocked after:
1. ✅ Useful-life canonical decision
2. ✅ Loss-window canonical decision
3. ⬜ Revised R67 residual recheck — **this branch shows gates still FAIL**
4. ⬜ External sign-off or explicit internal approval to accept residual
5. ⬜ Decision on whether to proceed with runtime adapter despite gate FAIL

**Runtime adapter (`phase6-depreciation-engine-runtime-adapter`) remains blocked.**

---

## 9. What This Means for Next Steps

Three honest options:

**Option A — Accept residual as a known consequence of correct policy**
- The 20yr/12yr canonical is legally/policy correct
- The residual (~20,000 kEUR cumulative) is a documented gap, not a bug
- Recommend proceeding with runtime adapter design in a new branch
- Risk: gate FAIL remains

**Option B — Investigate remaining drivers before runtime adapter**
- The residual is large; there may be other unexplained components beyond useful-life and loss-window
- Recommend: `phase6-r67-residual-driver-recheck`
- Goal: decompose remaining gap into explained/unexplained portions

**Option C — Do not proceed to runtime adapter**
- Gates fail; residual is large and worsens under canonical policy
- R99/R102 remain blocked indefinitely until external sign-off or residual closure

---

## 10. Deliverables Created

- `docs/phase6_revised_r67_residual_recheck.md` (this file)
- `reports/phase6_revised_r67_residual_recheck.csv`

---

## 11. Tests

No new tests added — this is a diagnostic-only recheck branch. Existing suites confirm no regressions:

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

---

## 12. Recommended Next Branch

**`phase6-r67-residual-driver-recheck`** — recommended as next diagnostic step.

Rationale:
- The combined canonical counterfactual produces a large estimated residual (~−20,000 kEUR vs Excel)
- Before proceeding to runtime adapter design, the remaining unexplained gap should be decomposed
- Option A (accept residual and proceed) is viable but requires explicit sign-off to proceed despite gate FAIL
- This branch does not change runtime behavior and does not implement the canonical decisions in runtime