# Bankable Framework Merge Summary

## What Merges Now

This merge introduces the **bankable depreciation framework** into main:

### Files Added
- `app/depreciation_bankable.py` — tax/book separation framework, `DepreciationProfile`, `AssetClass` enum, `generate_tax_and_book_schedule()`, `build_bankable_waterfall_schedule()`, `to_waterfall_depreciation_schedule()`
- `app/depreciation_engine.py` — integration engine with `CapexLineItem.to_basis_item()`, `map_capex_line_item_to_basis()`
- `tests/test_bankable_depreciation.py` — 26 tests (tax/book separation, inverter mapping, land non-depreciable, convention support, OTHER/UNK policy, integration bridge)
- `tests/test_depreciation_engine.py` — 18 tests (linear schedule, grid totals, zero amount, life end, multiple asset classes, deterministic)
- `tests/test_depreciation_wiring.py` — 4 tests (advanced vs legacy path, tax shield difference, equity IRR effect)

### Docs Added
- `docs/depreciation_integration_status.md` — integration status with runtime status section
- `docs/depreciation_review_package.md` — external review package
- `docs/bankable_depreciation_design.md` — design rationale
- `docs/pre_depreciation_merge_review.md` — merge readiness doc

## What Does NOT Merge Now

### Runtime Path (Deferred)
- `depreciation_engine.generate_schedule()` remains the active runtime path
- `depreciation_bankable.py` is framework-only, NOT runtime-active
- Runtime replacement deferred to `feature/bankable-runtime-wiring` sprint

### NOT Implemented
- Day-fraction double-application fix (needs behavioral regression tests)
- Separate tax/book Excel export tabs
- Inverter-specific 10y runtime behavior (current runtime groups inverter under GENERATION at 25y)
- Mid-year convention
- Declining balance convention

## Why Runtime Wiring Is Deferred

1. **Double-application risk:** `waterfall_core` applies `dep * p.day_fraction`; `generate_tax_and_book_schedule()` also applies day fractions internally. Single authoritative point must be identified first.
2. **Behavioral test coverage incomplete:** Tests for inverter 10y effect on tax shield, contingency allocation basis impact not yet written.
3. **Excel disclosure roadmap needed:** Tax/book export structure must be designed before runtime switch.
4. **External review recommended:** Framework architecture review before runtime activation.

## Backward Compatibility Guarantees

- `run_demo_project()` behavior **unchanged** — same output for same inputs
- Legacy `CapexItem` path **works** — when `advanced_capex_line_items` absent, original depreciation path used
- All 1194 existing tests **continue to pass**
- No changes to waterfall_core logic in this merge

## Future Runtime Wiring Plan

Branch `feature/bankable-runtime-wiring` will:
1. Map current flow: `advanced_capex_line_items` → `generate_schedule()` → `WaterfallRunConfig` → `waterfall_core`
2. Replace with: `advanced_capex_line_items` → `build_bankable_waterfall_schedule()` → `TaxDepreciationSchedule` → `to_waterfall_depreciation_schedule()` → `WaterfallRunConfig`
3. Ensure day_fraction applied exactly once at single authoritative point
4. Add regression tests: COD year correct, annual totals conserved, no double application, deterministic repeated runs

## Test Results (This Branch)

| Suite | Result |
|-------|--------|
| `test_bankable_depreciation.py` | 26 passed ✅ |
| `test_depreciation_engine.py` | 18 passed ✅ |
| `test_depreciation_wiring.py` | 4 passed ✅ |
| Full suite | 1194 passed, 1 xfailed ✅ |
