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