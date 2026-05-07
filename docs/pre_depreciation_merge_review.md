# Pre-Depreciation Merge Review

## Original Review Findings
1. Advanced OPEX + Scenario scaling — confirmed working ✅
2. API messages propagation — fixed ✅
3. CAPEX depreciation gap — `generate_schedule()` now wired ✅

## What Was Fixed
- `ui_runner.py` now calls `generate_schedule()` when `advanced_capex_line_items` provided
- Depreciation schedule injected into `WaterfallRunConfig`
- Consumed in `waterfall_core` for tax shield calculation
- Behavioral test added proving tax shield differs between paths

## Wiring Completed
```
advanced_capex_line_items
    ↓
generate_schedule(list, total_periods=horizon_years)
    ↓
DepreciationSchedule
    ↓
WaterfallRunConfig(advanced_capex_depreciation_schedule=...)
    ↓
waterfall_core → tax_shield = depreciation * tax_rate
```

## Test Coverage
- `tests/test_depreciation_engine.py` — 18 unit tests
- `tests/test_depreciation_wiring.py` — 4 behavioral tests

## Simplifications (need reviewer sign-off)
- Inverter = GENERATION 25y (not separately modeled)
- Contingency = 5y (conservative)
- No mid-year convention
- No separate financial vs tax depreciation

## Remaining Risks
1. Golden outputs may drift — need recalibration
2. Excel export lacks per-asset-class breakdown
3. `horizon_years` sourced from `project.info.horizon_years` — needs verification for Wind

## Questions for Reviewer
1. Is the inverter grouping under GENERATION acceptable for MVP?
2. Should contingency really be 5y or is it contract-dependent?
3. Any concerns about the tax shield integration approach?