# BESS / Hybrid Design — Architecture Document

> **Status: Design Only. Do not implement dispatch logic in this phase.**

## Overview

Battery Energy Storage System (BESS) and Hybrid projects (Solar+BESS, Wind+BESS) are
defined architecturally here. The current model supports BESS as a partial revenue-only
component — no dispatch optimization, no state-of-charge (SOC) modeling, no integrated
waterfall.

---

## 1. Dispatch Model Concept

### 1.1 Operating Modes

A BESS project operates in one of three modes per period:

| Mode | Description |
|---|---|
| **Charge** | Grid surplus or low-price period → BESS absorbs energy |
| **Discharge** | Grid demand or high-price period → BESS releases energy |
| **Idle** | No viable charge/discharge opportunity |

### 1.2 Dispatch Strategy

Dispatch is optimized against a price curve (merchant price or PPA tariff):

1. **Arbitrage-driven**: Charge when `price < charge_threshold`, discharge when `price > discharge_threshold`
2. **Residual demand**: Meet demand profile when `generation < load`
3. **Ancillary services**: (Future) Frequency regulation, reserve capacity

### 1.3 Simplified Model (Phase 2 — NOT IMPLEMENTED)

- Use annual duration curve to estimate charge/discharge cycles
- Apply round-trip efficiency (RTE): `discharged_energy = charged_energy × RTE`
- Default RTE: 85–90% (Li-ion NMC)
- No intra-day dispatch — semi-annual periods only

### 1.4 Advanced Model (Future)

- Hourly price profile per period
- Linear programming (LP) for optimal dispatch
- SOC dynamics: `SOC[t+1] = SOC[t] × (1 - self_discharge) + charge_amount × RTE - discharge_amount`

---

## 2. Revenue Streams

### 2.1 Arbitrage

Buy low (charge) → Sell high (discharge)
```
revenue_keur = discharged_energy_MWh × price_eur_mwh
cost_keur = charged_energy_MWh × charge_cost_eur_mwh
net_arbitrage = revenue - cost
```

### 2.2 Capacity Payment

BESS provides firm capacity to the grid:
```
revenue_keur = capacity_MW × capacity_price_eur_kw_yr / periods_per_year
```

### 2.3 Ancillary Services

- Frequency regulation (fast response)
- Spinning/non-spinning reserves
- Voltage support

Revenue estimation:
```
revenue_keur = MW × service_price_eur_mw_month × 12 / periods_per_year
```

### 2.4 Current Model

The current model includes **partial BESS revenue** as a fixed or simple time-series
estimate. No dispatch optimization is performed. Status: `partial`.

---

## 3. Constraints

### 3.1 State of Charge (SOC)

```
SOC_min ≤ SOC ≤ SOC_max
SOC_max = max_soc_pct × installed_capacity_MWh
SOC_min = min_soc_pct × installed_capacity_MWh  (typically 10–20%)
```

### 3.2 Degradation

Annual capacity fade:
```
capacity_MWh[t] = capacity_MWh[0] × (1 - degradation_rate)^t
```

Typical degradation: 1.5–3% per year for Li-ion NMC

### 3.3 Efficiency

Round-trip efficiency (RTE):
```
RTE = η_charge × η_discharge
η_charge ≈ 95–98% (AC/DC conversion + battery charge)
η_discharge ≈ 95–98% (battery discharge + DC/AC conversion)
Net RTE ≈ 85–92%
```

### 3.4 Cycle Limits

Calendar vs. cycle aging:
```
Max cycles = f DOD, temperature, C-rate
Calendar life: ~20 years @ 70% SOC
Cycle life: ~5000 cycles @ 80% DOD
```

---

## 4. Integration into Existing Waterfall

### 4.1 CapEx Structure

BESS-capable projects require:

```python
CapexStructure(
    bess_epc=CapexItem(...),   # Battery + inverter
    bess_bop=CapexItem(...),   # Balance of plant
    grid_connection=CapexItem(...),  # Grid connection (shared with solar/wind)
)
```

### 4.2 OpEx Structure

```python
OpexItem(
    name="BESS O&M",
    y1_amount_keur=capacity_MW * om_cost_eur_kw,
    escalation_pct=0.02,
    start_year=1,
)
OpexItem(
    name="BESS Replacement",
    y1_amount_keur=0.0,  # Major replacement reserve (incurred later)
    escalation_pct=0.02,
    start_year=10,
)
```

### 4.3 Revenue Structure

```python
RevenueParams(
    bess_merchant_price=...,    # Arbitrage price curve (EUR/MWh)
    bess_capacity_payment=...,  # EUR/MW/year
    bess_ancillary=...,         # EUR/MW/year
)
```

### 4.4 Waterfall Period

```python
WaterfallPeriod(
    bess_charge_mwh=0.0,
    bess_discharge_mwh=0.0,
    bess_revenue_keur=0.0,
    bess_cost_keur=0.0,
    bess_soc_pct=0.5,
)
```

**Current model:** BESS revenue is included in `total_revenue_keur` and shown in
revenue tables, but the waterfall does not separately model charge/discharge cycles.

---

## 5. Testing Strategy

When BESS is implemented, the following tests are required:

### 5.1 Unit Tests

- `test_bess_soc_bounds`: SOC never exceeds [min, max]
- `test_bess_degradation_applied`: Capacity decreases over time
- `test_bess_round_trip_efficiency`: Net discharge < gross charge
- `test_bess_dispatch_arbitrage_logic`: Charge when price < threshold

### 5.2 Integration Tests

- `test_hybrid_solar_bess_waterfall`: Solar+BESS waterfall completes without error
- `test_hybrid_wind_bess_waterfall`: Wind+BESS waterfall completes without error
- `test_bess_revenue_aggregated`: BESS revenue appears in total_revenue_keur
- `test_bess_cost_aggregated`: BESS OpEx appears in total_opex_keur

### 5.3 Validation Tests

- `test_bess_capacity_degraded_over_20y`: 20-year degradation ≤ 30%
- `test_bess_total_cycles_within_calendar_life`: Cycle count ≤ manufacturer spec
- `test_hybrid_capex_not_double_counted`: Solar cap + BESS cap ≠ double-counted

---

## 6. Hybrid Project Structure

### 6.1 Solar + BESS

```
Generation: Solar PV (variable, depends on weather)
Storage: BESS (fills gaps, arbitrates price)
Load: Grid demand or PPA off-take

Cash flows:
  - Solar revenue: generation × tariff
  - BESS arbitrage: (discharged_MWh × price) - (charged_MWh × cost)
  - BESS capacity: fixed payment (if applicable)
```

### 6.2 Wind + BESS

```
Generation: Wind (variable, depends on wind speed)
Storage: BESS (fills gaps, arbitrates price)
Load: Grid demand or PPA off-take

Same cash flow structure as Solar+BESS
```

### 6.3 CapEx Allocation

Hybrid projects must avoid double-counting shared infrastructure:
- Grid connection: counted once for the whole hybrid
- Land/laydown: counted once
- BESS + Solar/Wind: each counted separately in their own CapEx items

---

## 7. Partial Status Warning

The current model has the following BESS/hybrid limitations:

1. **No dispatch optimization**: Revenue is a simple time series, not optimized
2. **No SOC modeling**: No charge/discharge cycle tracking
3. **No degradation accounting**: BESS capacity assumed constant over time
4. **No ancillary revenue modeling**: Capacity payments only

**BESS status: `partial` — do not use for bankable investment decisions.**

---

*Document created: 2026-05-04 — Phase 2 Step 5 (design only, not implemented)*