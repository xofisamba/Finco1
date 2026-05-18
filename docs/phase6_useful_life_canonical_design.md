# Phase 6 — Useful-Life Canonical Design

## Branch
`phase6-useful-life-canonical-design`

## Status
**Docs/design/governance only. No production code changes. No runtime behavior changes.**

---

## 1. What This Branch Does

Creates a formal canonical useful-life policy decision memo for Phase 6 depreciation. Documents the recommended useful-life defaults for the Croatia renewable template and clarifies the actual-day / leap_frac convention decision.

Creates:
- `docs/phase6_useful_life_canonical_design.md` (this file)

---

## 2. What This Branch Does NOT Do

- ❌ No changes to `app/waterfall_core.py`, `app/waterfall_runner.py`, `app/project_factories.py`
- ❌ No tax runtime behavior changes
- ❌ No depreciation runtime behavior changes
- ❌ No factory opt-in
- ❌ No R99/R102 promotion
- ❌ No SHL FCF opt-in
- ❌ No scalar plugs or residual adjustments
- ❌ Oborovo remains guarded
- ❌ No implementation of actual-day / leap_frac convention in this branch

---

## 3. Documented Evidence

### TUHO Excel Inputs Useful Lives (D358–D379)

| Category Type | Useful Life | Source |
|-------------|----------:|--------|
| Main CAPEX (wind turbines, EPC, project rights, civil, grid, O&M, etc.) | **20 years** | Excel Inputs D358–D379 |
| Financing costs (IDCs, commitment fees, bank fees, structuring fees) | **12 years** | Excel Inputs D374–D376 |
| Land Securing Costs | **Non-depreciable** (residual = capex) | Excel CapEx row 39 |

### Python Historical Behavior

- Python canonical: **30-year straight-line** for all main CAPEX
- `DepreciationEngine` default: `period_count=60` semiannual periods (30 years)
- Offline engine supports per-category `useful_life_years` but was not configured with project inputs historically
- The 30-year assumption is a conservative modelling choice, not an industry-standard for wind

### Industry Context

For wind turbines:
- **Industry standard**: 20–25 years (OEM warranties typically 20–25 years; most wind farms depreciated over 20–25 years)
- **Python 30-year**: Conservative over-assumption; valid for modelling conservatism but not aligned with project inputs
- **Excel 20-year**: Project-specific input from TUHO turbine supply contract

### Offline Engine Capability

The `domain/depreciation_offline` engine supports:
- Per-category `useful_life_years` via `AssetCategoryRule`
- `start_period` offset for mid-project COD
- Multiple `asset_class` categories with independent lives
- Croatia template defaults already partially defined in `domain/tax/loss_carryforward.py` style

### Dep R30 Near-Parity Result (PR #84)

| Metric | Value |
|--------|------:|
| Max \|diff\| per period | **3.13 kEUR** |
| Mean \|diff\| per period | **0.93 kEUR** |
| Within ±5 kEUR | 18/18 H1 periods |
| Within ±1 kEUR | 10/18 H1 periods |

**Root cause**: Excel uses `capex_i / useful_life_i × leap_frac`; offline engine uses `capex_i / (useful_life_i × 2)` flat.

**±5 kEUR is diagnostic-only. Not a Stage 3 gate.**

---

## 4. Policy Options Compared

### Option A — Keep Python 30-Year Canonical Default

| | |
|---|---|
| **Continuity** | No change to existing Python canonical behavior |
| **Conservative** | 30-year straight-line is conservative for wind assets |
| **Con** | Diverges from TUHO project inputs (20-year vs 30-year) |
| **Con** | Not clearly industry-standard for wind turbines |
| **Con** | Increases residual risk vs Excel — Python underpays CIT in yr13–20 |
| **Con** | 10-year gap in depreciation timing widens the R67 residual |

### Option B — Use Project-Input Useful Life Whenever Available

| | |
|---|---|
| **Pro** | Aligns with workbook/source-of-truth per project |
| **Pro** | Generalizes across Oborovo, future projects without TUHO-only hardcoding |
| **Pro** | Uses actual contract/project inputs rather than blanket assumptions |
| **Con** | Requires input validation and template fallback design |
| **Con** | Runtime wiring needed (Stage 3 scope) |

### Option C — Croatia Renewable Template Default

| | |
|---|---|
| **Pro** | Explicit policy: main renewable CAPEX = 20 years |
| **Pro** | Financing costs = 12 years (aligned with TUHO inputs) |
| **Pro** | Land = non-depreciable (residual = capex) |
| **Pro** | Clear fallback: warn if explicit useful life missing, use template default |
| **Con** | Requires project-input wiring in Stage 3 |
| **Con** | Template must be maintained and versioned |

### Option D — Dual-Mode Support

| | |
|---|---|
| **Pro** | Supports legacy, project-input, and Excel parity modes |
| **Con** | Three code paths; adds complexity and test surface |
| **Con** | No strong evidence that Excel parity mode is the correct canonical target |
| **Con** | ~660 kEUR CIT difference from loss-window already documented; further mode complexity not justified |

---

## 5. Recommended Canonical Decision

### **Option C — Croatia Renewable Template Default, with Project-Input When Available**

**Decision:**

1. **Project-input useful life is canonical when explicitly provided** in the project configuration. This aligns the Python model with the actual asset contract and avoids TUHO-only hardcoding.

2. **Croatia renewable template defaults** apply when explicit project input is missing:

| Category Type | Default Useful Life | Notes |
|-------------|----------:|--------|
| Main renewable CAPEX (wind turbines, EPC, project rights, civil, grid, monitoring, O&M, insurances, due diligence, audit/legal/construction management, contingencies) | **20 years** | Aligned with TUHO project inputs |
| Financing costs (IDCs, commitment fees, bank fees) | **12 years** | Aligned with TUHO inputs and Croatia tax treatment |
| Land Securing Costs | **Non-depreciable** | Residual = capex; no depreciation |
| VAT Costs (construction-period) | **20 years** | Book depreciation target |

3. **30-year straight-line is a fallback only** — when no explicit `useful_life_years` is provided for a category, and no template default exists, the engine should emit a warning and fall back to the conservative 30-year assumption. The fallback must not be silent.

4. **No TUHO-only hardcoded bridge** — the canonical policy applies to all Croatia renewable projects, not just TUHO.

5. **No silent default switch in runtime** — the actual-day / leap_frac convention and per-category project-input wiring must be designed in Stage 3 before any default switch occurs. This branch only documents the policy; it does not change runtime defaults.

---

## 6. Actual-Day / Leap_Frac Convention Decision

**Current convention:** Flat semiannual — `capex_i / (useful_life_i × 2)` per period.

**Decision:**

1. **Current flat semiannual convention is acceptable** for offline diagnostic near-parity. The ±5 kEUR (max 3.13 kEUR) per-period difference is understood and documented.

2. **Exact Excel Dep R30 parity** (~±1 kEUR per period) **would require** an optional actual-day / leap_frac depreciation convention — a per-category `capex_i / useful_life_i × leap_frac` formula applied consistently.

3. **Actual-day / leap_frac should be designed as a generic optional convention**, not as a scalar plug or TUHO-only hardcoded bridge. If implemented, it should:
   - Use the Dep sheet row 5 leap fractions (0.49589 / 0.50411 / 0.49727 / 0.50273)
   - Apply per-category `capex_i / useful_life_i × leap_frac`
   - Be available as a non-default mode for diagnostics

4. **Do not implement actual-day / leap_frac convention in this branch.** This is a Stage 3 design decision.

5. **Stage 3 runtime adapter options:**

| Option | Description | Effect on R67 |
|--------|-------------|--------------|
| **A. Flat semiannual** (current offline) | `capex_i / (useful_life_i × 2)` | ~3 kEUR/period uncertainty |
| **B. Actual-day / leap_frac** (optional) | `capex_i / useful_life_i × leap_frac` | Would improve ±1 kEUR parity |

Stage 3 must choose and document the effect on R67 residual before wiring.

---

## 7. Runtime Adapter Prerequisites

**Stage 3 (`phase6-depreciation-engine-runtime-adapter`) remains BLOCKED until:**

1. ✅ Useful-life canonical decision — **documented in this branch**
2. ✅ Loss-window canonical decision — **documented in PR #85 (`phase6-loss-window-design`)**
3. ⬜ Residual recheck plan — **pending (`phase6-revised-r67-residual-recheck`)**
4. ⬜ External sign-off or explicit internal approval

Until all prerequisites are met, Stage 3 runtime adapter must not be started.

---

## 8. R99/R102 Gate Impact

**R99/R102 remain BLOCKED.**

Useful-life decision does **not** unblock R99. R99 design is only unblocked after:

1. ✅ Useful-life canonical decision
2. ✅ Loss-window canonical decision
3. ⬜ Revised R67 residual recheck
4. ⬜ External sign-off

**No SHL FCF runtime source.** R99/R102 remain audit fields only.

---

## 9. Relationship to Prior Branches

| Branch | Key Finding | Status |
|--------|------------|--------|
| `phase6-depreciation-engine-design` (Stage 1) | Domain architecture, `AssetCategoryRule`, per-category lives | Merged |
| `phase6-depreciation-engine-impl` (Stage 2) | Offline engine with `DepreciationEngine`, `DepreciationConfig` | Merged |
| `phase6-dep-category-capex-extraction` (PR #83) | 17 categories extracted; TUHO useful lives confirmed | Merged |
| `phase6-dep-r30-rounding-convention-check` (PR #84) | Dep R30 near-parity root cause = leap_frac convention | Merged |
| `phase6-loss-window-design` (PR #85) | Croatia legal 10-period canonical | Merged |
| **This branch** | Useful-life canonical decision | **Now** |

---

## 10. Deliverables Created

This branch creates only this document. No runtime code, no CSV report, no test changes.

- `docs/phase6_useful_life_canonical_design.md`

---

## 11. Tests

Docs-only branch. Existing test suites confirm no regressions:

```
tests/test_depreciation_category_capex_extraction.py
tests/test_depreciation_engine_offline.py
tests/test_loss_engine_runtime_flag.py
tests/test_tax_bridge_consumes_r35_sources.py
tests/test_r67_full_calibration_validation.py
tests/test_r67_yrs13to30_residual.py
tests/test_cit_h2_annual_trigger.py
```

**94 passed, 1 xfailed** (combined suite, unchanged)

---

## 12. Recommended Next Branch

**`phase6-revised-r67-residual-recheck`**

Goal: Recompute and document revised R67 residual status after canonical loss-window and useful-life decisions, without runtime promotion. Quantify the combined effect of the two canonical decisions on the R67 residual.

**Do NOT recommend runtime adapter (`phase6-depreciation-engine-runtime-adapter`) as immediate next branch** unless the residual recheck explicitly justifies it and all prerequisites are resolved.