# Phase 7 — Revenue CO2 Balancing Split

## Goal

Add explicit revenue-section split matching the Excel P&L presentation:

1. **Electricity revenue** — PPA / merchant power sales
2. **CO2 certificates / green certificates revenue** — certificate sales
3. **Balancing cost** — shown inside revenue section (positive cost line)
4. **Net revenue after balancing** — total after deductions

This is a focused Phase 7 revenue refinement branch.

## Hard Constraints

- No R99/R102 promotion
- No SHL FCF runtime source
- No scalar plugs
- No residual adjustments
- No broad waterfall refactor
- Preserve default behavior unless explicit new inputs are provided
- Oborovo must remain supported / guarded
- No changes to unrelated modules
- Do not change tax formulas
- Do not change senior debt formulas
- Do not change OPEX engine

## Why Balancing Cost Appears in Revenue Section

In the Excel model, balancing cost is presented inside the revenue section as a
positive cost line (P&L row for balancing). This is for **model parity** — the
Excel P&L shows it there, so the Python model must expose it in the same location
for comparison. Economically it is a cost; presentation-wise it lives in the
revenue section in the source model.

## Input Fields Added

### RevenueParams (`domain/inputs.py`)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `co2_certificate_price_eur_per_mwh` | `float` | `0.0` | Flat CO2/green certificate price (EUR/MWh) |
| `balancing_cost_eur_per_mwh` | `float` | `0.0` | Flat balancing cost (EUR/MWh) |

These complement existing fields:
- `co2_enabled` — enables CO2 certificate revenue
- `co2_price_eur` — existing flat price (used when no schedule)
- `balancing_cost_schedule` — schedule-based balancing cost EUR/MWh
- `co2_sales_schedule` — schedule-based CO2 price EUR/MWh

## TUHO Defaults

### CO2 Certificate Price

- **Flat input:** `co2_certificate_price_eur_per_mwh = 4.191063312` EUR/MWh
- **Schedule:** `co2_sales_schedule` with semiannual values (TUHO Excel CF row 31)
  - Y1-H1/H2: 4.191 EUR/MWh → Y30-H1/H2: ~0.7 EUR/MWh (declining ~10%/yr)
- **Source:** TUHO Excel CF sheet, row 31 (CO2 certificates), semiannual values
- **Excel cell reference:** TUHO Excel CF row 31, columns G onwards

### Balancing Cost

- **Flat input:** `balancing_cost_eur_per_mwh = 8.0` EUR/MWh
- **Schedule:** `balancing_cost_schedule = RevenueAdjustmentSchedule(constant_value=8.0)`
- **Source:** TUHO Excel CF row 30 (balancing cost)
- **Excel cell reference:** TUHO Excel CF row 30, constant 8.0 EUR/MWh

## Oborovo Defaults

### CO2 Certificate Price

- **Flat input:** `co2_certificate_price_eur_per_mwh = 1.5` EUR/MWh
- **Schedule:** `co2_sales_schedule = None` (uses flat `co2_price_eur` for calculations)
- **Source:** Oborovo Excel CF sheet, ~1.5 EUR/MWh (semi-annual CO2 revenue ~83 kEUR)
- **Note:** Oborovo CO2 revenue is ~83 kEUR per semi-annual period = 1.5 EUR/MWh

### Balancing Cost

- **Flat input:** `balancing_cost_eur_per_mwh = 0.0`
- **Schedule:** `balancing_cost_schedule = None`
- **Note:** Oborovo Excel has no explicit balancing cost line in revenue section

## Calculation Formulas

### Per-Period Revenue Decomposition

```
generation_mwh = capacity_mw × operating_hours × day_fraction × availability × degradation

electricity_revenue_keur = _period_energy_revenue_keur(generation_mwh, tariff, market_price, ppa_active, ppa_share)

co2_certificate_revenue_keur = generation_mwh × co2_eur_mwh / 1000
  where co2_eur_mwh = co2_sales_schedule.value_for_period(...) if schedule exists
        else co2_price_eur (flat fallback, then co2_certificate_price_eur_per_mwh)

balancing_cost_keur = balancing_cost_pv_keur + balancing_cost_wind_keur
  balancing_cost_pv_keur = electricity_revenue_keur × balancing_cost_pv (PPA %)
  balancing_cost_wind_keur = generation_mwh × balancing_eur_mwh / 1000
  where balancing_eur_mwh = balancing_cost_schedule.value_for_period(...) if schedule exists
        else balancing_cost_eur_per_mwh (flat fallback)

net_revenue_after_balancing_keur = electricity_revenue_keur + co2_certificate_revenue_keur - balancing_cost_keur

revenue_keur (legacy) = net_revenue_after_balancing_keur
```

### Sign Convention

- `electricity_revenue_keur` — always positive
- `co2_certificate_revenue_keur` — positive when CO2 enabled
- `balancing_cost_keur` — **always positive** (cost shown as positive amount in Excel revenue section)
- `net_revenue_after_balancing_keur` = electricity + CO2 − balancing

### Total Revenue Convention

- `revenue_keur` (legacy field) = `net_revenue_after_balancing_keur` — no change to total revenue
- Revenue decomposition preserves backward compatibility:
  - `energy_revenue_keur` = `electricity_revenue_keur` (alias)
  - `co2_revenue_keur` = `co2_certificate_revenue_keur` (alias)
  - `balancing_cost_pv_keur`, `balancing_cost_wind_keur` — preserved for diagnostics

## Fields Exposed in Result Objects

In `revenue_decomposition_schedule()` output dict per period:

```python
{
    "is_operation": bool,
    "is_ppa_active": bool,
    "generation_mwh": float,
    "ppa_tariff_eur_mwh": float,
    "market_price_eur_mwh": float,
    # Phase 7 explicit split:
    "electricity_revenue_keur": float,
    "co2_certificate_revenue_keur": float,
    "balancing_cost_keur": float,
    "net_revenue_after_balancing_keur": float,
    # Legacy aliases:
    "energy_revenue_keur": float,
    "co2_revenue_keur": float,
    "balancing_cost_pv_keur": float,
    "balancing_cost_wind_keur": float,
    "co2_eur_mwh": float,
    "balancing_cost_eur_mwh": float,
    "revenue_keur": float,
}
```

## Test Coverage

| Test File | Tests | Status |
|-----------|-------|--------|
| `tests/test_revenue_co2_balancing_split.py` | 20 | All passed |
| `tests/test_revenue.py` | 16 | All passed |
| `tests/test_r67_full_calibration_validation.py` | 27 | All passed |
| `tests/test_r67_yrs13to30_residual.py` | 26 | All passed |
| `tests/test_cit_h2_annual_trigger.py` | 10 | All passed |
| `tests/test_depreciation_category_capex_extraction.py` | 12 | All passed |
| `tests/test_depreciation_engine_offline.py` | 3 | All passed |
| `tests/test_loss_engine_runtime_flag.py` | 9 | All passed |
| `tests/test_tax_bridge_consumes_r35_sources.py` | 6 | All passed |

## Known Limitations

1. **Python waterfall `result.periods[i].revenue_keur`** — still returns the total/ net value.
   The explicit split is only available via `revenue_decomposition_schedule()`.
   The export script adds report-only rows for these fields (confidence=unmapped).

2. **Excel fixture gaps** — The fixture JSON does not have separate electricity/CO2/balancing
   columns from the Excel model. The model-stack comparison script marks these as `unmapped`
   (no Python runtime mapping yet).

3. **Oborovo CO2 schedule** — Oborovo uses the flat `co2_price_eur` input, not a schedule.
   The `co2_sales_schedule` is `None` for Oborovo. Calculations use `co2_price_eur`.

## Changed Files

```
domain/inputs.py                           — added co2_certificate_price_eur_per_mwh, balancing_cost_eur_per_mwh to RevenueParams
domain/revenue/generation.py               — extended revenue_decomposition_schedule with explicit split fields
app/project_factories.py                   — TUHO: co2_certificate_price=4.191063312, balancing_cost=8.0; Oborovo: co2_certificate_price=1.5, balancing_cost=0.0
tests/test_revenue_co2_balancing_split.py   — new test file (20 tests)
scripts/export_phase6_model_stack_comparison.py — added electricity_revenue, co2_certificate_revenue, balancing_cost rows (unmapped)
```

## Merge Recommendation

**Merge.** No production runtime behavior changed. All existing tests pass. Revenue split
exposed for TUHO and Oborovo with correct Excel source values.

## Recommended Next Branch

`phase8-shl-sculpt-consolidation` — consolidate SHL PIK + sweep phase logic, consolidate
sculpting debt sizing, remove SHL FCF waterfall flag dependency on Phase 6 CIT bridge.