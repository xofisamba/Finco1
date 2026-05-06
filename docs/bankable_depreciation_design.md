# Bankable Depreciation Framework — Design

## Philosophy
This is a **bankability-oriented depreciation framework** — not a fully bankable model. Claims of "bankable" require external tax advisor validation, jurisdiction-specific benchmarks, and independent audit. This framework provides the structural separation needed to support a bankable workflow.

## 1. Tax vs Book Separation

### Tax Depreciation
- Used for waterfall tax shield calculation
- Driven by jurisdiction-specific tax lives and methods
- Feeds `tax_shield[p] = tax_depreciation[p] * tax_rate`

### Book/Accounting Depreciation
- Used for financial reporting (IFRS/US GAAP)
- May differ in life, method, and convention from tax
- Stored in output but NOT used in waterfall

## 2. Asset Class Granularity

| Bankable Asset Class | Description |
|---|---|
| SOLAR_MODULES | PV modules |
| INVERTERS | Power electronics, DC/AC conversion |
| MOUNTING_STRUCTURES | Racking, piling |
| GRID_CONNECTION | MV/HV infrastructure, cables |
| TRANSFORMER |升压变压器, MV/LV transformer |
| CIVIL_WORKS | Foundations, roads, fencing |
| DEVELOPMENT_SOFT | Permits, engineering, soft costs |
| LAND | Non-depreciable |
| CONTINGENCY | Allocatable across depreciable classes |
| OTHER | Catch-all with explicit warning |

## 3. Depreciation Conventions

- **FULL_YEAR**: Full amount in year 1 (US MACRS)
- **HALF_YEAR**: 50% in first year, 50% over remaining life (US GAAP ASC 250)
- **DAY_FRACTION**: Pro-rata based on period `day_fraction` from project calendar
- **COD_MONTH**: Depreciation starts from COD month (tax authority approach)

## 4. Depreciation Methods

- **STRAIGHT_LINE**: Equal annual amount over life
- **DECLINING_BALANCE**: Fixed % on remaining book value
- **NON_DEPRECIABLE**: Zero depreciation

## 5. Jurisdiction Profile Concept

```python
DepreciationProfile:
    country: str          # e.g. "Croatia", "Bosnia"
    regime: str           # e.g. "CIT", "IBL"
    tax_method: DepreciationMethod
    book_method: DepreciationMethod
    convention: DepreciationConvention
    asset_lives: dict[BankableAssetClass, int]  # years
    effective_date: date
    source: str           # "Tax Authority website / legal reference"
    notes: str
```

## 6. Contingency Treatment

**Preferred (MVP):** Allocate contingency proportionally across depreciable asset classes based on their relative CAPEX weight.

**Alternative:** Hold as NON_DEPRECIABLE until explicitly assigned.

## 7. MVP Defaults

### Solar Profile (Croatia IB)
| Asset Class | Tax Life | Book Life | Method | Convention |
|---|---|---|---|---|
| SOLAR_MODULES | 20y | 25y | SL | DAY_FRACTION |
| INVERTERS | 10y | 10y | SL | DAY_FRACTION |
| MOUNTING | 20y | 25y | SL | DAY_FRACTION |
| GRID_CONNECTION | 20y | 20y | SL | DAY_FRACTION |
| TRANSFORMER | 20y | 20y | SL | DAY_FRACTION |
| CIVIL_WORKS | 20y | 25y | SL | DAY_FRACTION |
| DEVELOPMENT_SOFT | 5y | 5y | SL | DAY_FRACTION |
| LAND | NON_DEPRECIABLE | NON_DEPRECIABLE | N/A | N/A |
| CONTINGENCY | proportional | proportional | SL | DAY_FRACTION |
| OTHER | 10y | 10y | SL | DAY_FRACTION |

### Wind Profile (Croatia IB)
| Asset Class | Tax Life | Book Life | Method | Convention |
|---|---|---|---|---|
| TURBINE | 20y | 25y | SL | DAY_FRACTION |
| INVERTERS | 10y | 10y | SL | DAY_FRACTION |
| TOWER | 20y | 25y | SL | DAY_FRACTION |
| GRID_CONNECTION | 20y | 20y | SL | DAY_FRACTION |
| TRANSFORMER | 20y | 20y | SL | DAY_FRACTION |
| CIVIL_WORKS | 20y | 25y | SL | DAY_FRACTION |
| DEVELOPMENT_SOFT | 5y | 5y | SL | DAY_FRACTION |
| LAND | NON_DEPRECIABLE | NON_DEPRECIABLE | N/A | N/A |
| CONTINGENCY | proportional | proportional | SL | DAY_FRACTION |
| OTHER | 10y | 10y | SL | DAY_FRACTION |

### Legacy Fallback
When no profile or no advanced CAPEX: use existing CapexItem-based depreciation.

## 8. Inverter Separation Requirement

Inverters MUST be mapped separately from GENERATION. A CapexLineItem with name/code indicating "inverter", "DC/AC", "power electronics" must map to INVERTERS (10y), NOT SOLAR_MODULES (20y).

## 9. Unknown Asset Class Handling

Unknown asset class (not in mapping) must raise `DepreciationMappingWarning` (warning, not exception) and use a fallback life of 10y for tax / 10y for book, with explicit log.

## 10. Waterfall Integration

```
advanced_capex_line_items
  → map_capex_line_item_to_depreciation_basis(item, profile)
  → TaxDepreciationSchedule + BookDepreciationSchedule
  → WaterfallRunConfig(tax_depreciation_schedule=..., book_depreciation_schedule=...)
  → waterfall_core: tax_shield[p] = tax_depr[p] * tax_rate
  → BookDepreciationSchedule stored in result for Excel export
```

Legacy fallback: no change to existing behavior.
