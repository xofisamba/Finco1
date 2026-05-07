# Runtime Wiring Plan — Bankable Depreciation

## Current Flow (Active Path)

```
advanced_capex_line_items
  → ui_runner.py: generate_schedule() [depreciation_engine]
  → DepreciationSchedule (old format, annual amounts per year)
  → WaterfallRunConfig(advanced_capex_depreciation_schedule=...)
  → waterfall_core line 131: dep = annual_dep * p.day_fraction
  → depreciation_schedule (period amount)
```

### Key observation
- `depreciation_engine.generate_schedule()` returns **annual** depreciation amounts
- Day fraction is applied **once** in `waterfall_core`
- `DepreciationSchedule` has `total_by_period(y)` returning annual amounts

## New Bankable Flow (Proposed Path)

```
advanced_capex_line_items
  → ui_runner.py: build_bankable_waterfall_schedule() [depreciation_bankable]
  → dict {total_by_period: [...], profile_name: ..., total_periods: n}
  → WaterfallRunConfig(advanced_capex_depreciation_schedule=...)
  → waterfall_core line 131: dep = annual_dep * p.day_fraction
  → depreciation_schedule (period amount)
```

### Key observation
- `generate_tax_and_book_schedule()` with DAY_FRACTION convention returns **period** amounts
- `total_by_period(p)` = annual_amount * day_fraction[p] / life (already pro-rated)
- Day fraction would be applied **again** in `waterfall_core` = DOUBLE APPLICATION ❌

## Single Authoritative Point Decision

**Option A: Apply day_fraction in waterfall_core only (current behavior)**
- `build_bankable_waterfall_schedule()` must return **annual** amounts
- `generate_tax_and_book_schedule()` should use `full_year` convention internally
- `to_waterfall_depreciation_schedule()` passes through annual amounts
- waterfall_core applies day_fraction → correct

**Option B: Apply day_fraction in bankable schedule only**
- `build_bankable_waterfall_schedule()` returns period amounts
- waterfall_core skips day_fraction application for bankable schedule
- More complex: requires flag to distinguish schedule types

**Recommended: Option A** — simpler, consistent with current behavior.

## Implementation

### Step 1: Ensure `build_bankable_waterfall_schedule()` uses `full_year` convention

In `depreciation_bankable.py`, modify `build_bankable_waterfall_schedule()`:
```python
def build_bankable_waterfall_schedule(
    capex_line_items,
    profile_name: str = "solar_croatia_ibl",
    total_periods: int = 20,
) -> dict:
    profile = get_profile(profile_name)
    basis_items = [map_capex_line_item_to_basis(item, profile) for item in capex_line_items]
    # Use full_year convention so total_by_period returns ANNUAL amounts
    tax_sched, book_sched = generate_tax_and_book_schedule(
        basis_items, profile, total_periods=total_periods,
        convention="full_year"  # ADD THIS
    )
    return to_waterfall_depreciation_schedule(tax_sched)
```

### Step 2: Add regression tests

```python
def test_no_double_day_fraction_application():
    """Annual total from schedule * day_fraction = period total."""
    # Run with semi-annual periods (day_fraction ~0.5)
    # Sum of period depreciation should equal annual depreciation from schedule
    
def test_cod_year_depreciation_correct():
    """COD year partial period uses correct day fraction."""
    
def test_annual_totals_conserved():
    """Sum of all period depreciation = sum of annual depreciation."""
```

### Step 3: Verify behavioral tests pass

- `test_advanced_capex_produces_different_tax_shield_than_legacy`
- `test_legacy_path_unchanged_without_advanced_capex`
- `test_advanced_capex_changes_taxable_income`
- `test_depreciation_schedule_affects_equity_irr`

---

## Implemented Runtime Decision (2026-05-07)

**Status:** Implemented and tested.

### Final Implemented Flow

```
advanced_capex_line_items
  → ui_runner.py: build_bankable_waterfall_schedule(convention=FULL_YEAR)
  → generate_tax_and_book_schedule(..., convention=FULL_YEAR)
    → day_fractions forced to [1.0]*total_periods → returns ANNUAL amounts
  → WaterfallDepreciationSchedule(total_by_period=[annual amounts])
  → WaterfallRunConfig(advanced_capex_depreciation_schedule=...)
  → waterfall_core line 131: dep = annual_dep * p.day_fraction (applied ONCE)
```

### Single Authoritative Application Point

**`waterfall_core` is the ONLY place where day_fraction is applied.**

`build_bankable_waterfall_schedule` explicitly forces `FULL_YEAR` convention:
- `generate_tax_and_book_schedule()` receives `convention=DepreciationConvention.FULL_YEAR`
- Internal logic sets `day_fractions = [1.0] * total_periods` 
- Depreciation entries are full-year amounts (not pro-rated)
- `waterfall_core` applies `dep * p.day_fraction` exactly once

### Double Application Risk: MITIGATED ✅

Risk was: `generate_tax_and_book_schedule()` might use `DAY_FRACTION` internally (pro-rating), and then `waterfall_core` would apply day_fraction again.

Mitigation: `build_bankable_waterfall_schedule` explicitly passes `convention=DepreciationConvention.FULL_YEAR`, which overrides any internal pro-rating. This is explicit in source code, audited by `test_full_year_convention_used_in_runtime_bridge`.

### Backward Compatibility

- Legacy path (no `advanced_capex_line_items`): unchanged
- `CapexItem` path: unchanged  
- Only `advanced_capex_line_items` path uses new bankable engine
