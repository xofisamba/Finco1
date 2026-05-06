# CAPEX Depreciation Phase Plan

## Current Gap
CapexLineItem matrix affects `total_capex_override` in the waterfall, but
depreciation still uses the legacy CapexItem path (per-asset-class depreciation
schedule derived from `capex_items`, not from `capex_line_items`).

Result: total CAPEX is correct in waterfall, but depreciation basis is not
updated to match the CapexLineItem structure.

## Target
CapexLineItem entries should generate per-asset-class depreciation/tax base
schedules that feed into the waterfall alongside the existing CapexItem path.

## Proposed Design
1. **Asset class mapping:** CapexLineItem.asset_class → depreciation category
   (e.g. "solar_module" → 25yr linear, "inverter" → 10yr linear)
2. **Depreciation basis schedule:** generate annual depreciation basis from
   line items using asset_class lives
3. **Preserve backward compatibility:** legacy capex_items path still works
   for projects without CapexLineItem overrides
4. **Waterfall integration:** depreciation schedule becomes a third input axis
   alongside revenue and debt

## Risks
- Tax timing changes IRR (any depreciation change affects taxable income timing)
- Validation golden outputs require recalibration
- Excel export must show source of each depreciation line

## Implementation Phases
1. **Design:** map existing CapexLineItem.asset_class values to depreciation lives
2. **Engine test:** generate depreciation schedule from CapexLineItem in isolation
3. **Waterfall integration:** wire depreciation schedule into run_waterfall()
4. **Excel export update:** add CapexLineItem source column in depreciation view
5. **Validation recalibration:** update golden outputs for affected tests

## Deprecation Path
After full implementation, the legacy CapexItem depreciation path can be deprecated
in favor of CapexLineItem as the single source of truth for CAPEX + depreciation.