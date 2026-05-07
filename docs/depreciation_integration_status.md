# Depreciation Integration Status

## What Is Now Fully Wired

When `advanced_capex_line_items` are provided to `run_demo_project()`:
1. `ui_runner.py` calls `generate_schedule()` from `app.depreciation_engine`
2. Returns `DepreciationSchedule` with annual depreciation by asset class
3. Injected as `advanced_capex_depreciation_schedule` in `WaterfallRunConfig`
4. Consumed in `waterfall_core.run_waterfall_v3_core()` for tax shield calculation

## What Remains Simplified

### Asset Class → Depreciation Life Mapping
| Asset Class | Life | Notes |
|---|---|---|
| GENERATION (modules, BoS) | 25y | Simplified — inverter grouped here |
| GRID (connection, transformer) | 20y | |
| DEVELOPMENT (permits, soft costs) | 5y | |
| EPC (engineering, construction) | 25y | |
| CONTINGENCY | 5y | Conservative simplified treatment |
| LAND | non-depreciable | |
| OTHER | 10y | Fallback |

**Note:** Inverter is grouped with GENERATION (25y) rather than separately modeled as 10y. This is a simplification.

### Not Yet Implemented
- **No mid-year convention** — all depreciation starts at period 0
- **No separate financial vs tax depreciation** — single straight-line schedule used for both
- **No inflation adjustment** to depreciation basis
- **No per-component inverter separation** from generation equipment

## Why Branch Is Not Merged Yet
1. Simplifications above need external technical review
2. Golden validation outputs may drift with new depreciation schedule
3. Excel export doesn't yet show per-asset-class depreciation breakdown
4. BESS/Portfolio not yet supported in depreciation path

## Behavioral Test
`tests/test_depreciation_wiring.py` verifies:
- Tax shield differs between advanced and legacy paths
- Legacy path unchanged without advanced_capex_line_items
- Taxable income affected by depreciation schedule
- Equity IRR reflects different depreciation timing
---

## Current Runtime Status (2026-05-07)

**IMPORTANT — This branch introduces framework-only, NOT runtime replacement.**

### What This Branch Delivers

* `app/depreciation_bankable.py` — framework with tax/book separation, asset class profiles
* `app/depreciation_engine.py` — integration engine (bridge layer)
* `tests/test_bankable_depreciation.py` — 26 tests for bankable framework
* `tests/test_depreciation_engine.py` — 18 tests for engine
* `tests/test_depreciation_wiring.py` — 4 wiring integration tests
* `docs/depreciation_review_package.md` — external review package
* Profile definitions: solar_croatia_ibl, wind_croatia_ibl

### Runtime Status: NOT YET ACTIVE

The bankable tax/book depreciation framework is **NOT yet runtime-active** in this branch:

* **Framework:** ✅ Present — `depreciation_bankable.py` with `generate_tax_and_book_schedule()`, `DepreciationProfile`, `AssetClass` enum
* **Bridge:** ✅ Present — `build_bankable_waterfall_schedule()` produces waterfall-compatible dict
* **Runtime path:** ❌ Uses `depreciation_engine.generate_schedule()` (not bankable framework)

### Why Runtime Wiring Is Deferred

1. Day-fraction double-application risk must be resolved with behavioral tests
2. Behavioral test coverage for bankable-specific scenarios (inverter 10y, contingency allocation) incomplete
3. Excel disclosure roadmap must be documented before runtime switch
4. External review of framework architecture recommended before runtime activation

### Future Runtime Wiring Plan

Subsequent sprint (`feature/bankable-runtime-wiring`) will:
1. Replace `depreciation_engine.generate_schedule()` calls with `build_bankable_waterfall_schedule()`
2. Ensure day_fraction applied exactly once at single authoritative point
3. Add regression tests for COD year, annual totals conservation, no double application
4. Verify all behavioral tests pass with new path

### Backward Compatibility Guarantee

This branch does NOT change runtime behavior. When merged:
- Existing `run_demo_project()` behavior unchanged
- Legacy CapexItem path still works when `advanced_capex_line_items` absent
- All 1194 existing tests continue to pass
