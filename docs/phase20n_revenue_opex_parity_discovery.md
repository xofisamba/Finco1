# Phase 20N — Revenue + OPEX Parity Discovery

**Branch:** `phase20n-revenue-opex-parity-discovery`  
**Base:** `824fc6ac122b9df88bcfccd5b19cee020e785b5c`  
**Date:** 2026-05-27  
**Status:** Discovery only — no runtime formula changes

---

## 1. Revenue Bridge

### 1.1 Formula

```
generation_mwh     = capacity_mw × operating_hours × day_fraction × availability × degradation_factor
electricity_revenue = PPA_generation × ppa_tariff + merchant_generation × market_price
co2_revenue_keur   = generation_mwh × co2_eur_mwh / 1000
balancing_keur     = electricity_revenue × balancing_cost_pv + generation_mwh × balancing_cost_eur_mwh / 1000
net_revenue_keur   = electricity_revenue + co2_revenue_keur − balancing_keur
```

**Period distribution:** semi-annual via `day_fraction`  
**Implementation:** `domain/revenue/generation.py :: revenue_decomposition_schedule()`

### 1.2 TUHO Revenue Mapping

| Excel CF Row | Line | FincoGPT Field | Value | Status |
|---|---|---|---|---|
| R21 | Production (MWh) | `generation_mwh` | 72,271 H1 / 73,469 H2 | ✅ |
| R22 | PPA Revenue | `electricity_revenue_keur` (PPA) | 4,336 / 4,408 kEUR | ✅ |
| R30 | Balancing Cost | `balancing_cost_wind_keur` | 578 / 588 kEUR | ✅ |
| R31 | CO2 Certificates | `co2_certificate_revenue_keur` | 303 / 308 kEUR | ✅ |
| R27 | Total Revenue | `revenue_keur` | 4,061 / 4,128 kEUR | ✅ |

- **PPA:** 60 EUR/MWh Y1, indexed 2%/year, 12-year term  
- **Balancing:** 8.0 EUR/MWh flat (all periods) — from `balancing_cost_schedule = RevenueAdjustmentSchedule(constant_value=8.0)`  
- **CO2 schedule:** starts 4.191 EUR/MWh, declines ~10%/year toward 0.7 by Y30  
- **CO2 source:** `co2_sales_schedule = RevenueAdjustmentSchedule(semiannual_values=...)`  
- **No merchant revenue** in PPA periods (PPA share = 100%)  
- **Merchant periods:** Y13+ (first_merchant_operating_period_index = 24)

### 1.3 Oborovo Revenue Mapping

| Excel CF Row | Line | FincoGPT Field | Value | Status |
|---|---|---|---|---|
| R21 | Production (MWh) | `generation_mwh` | 55,553 H1 / 54,648 H2 | ✅ |
| R22 | PPA Revenue | `electricity_revenue_keur` (PPA) | 3,167 / 3,115 kEUR | ✅ |
| R30 | Balancing Cost | `balancing_cost_pv` | 0 (no PV balancing) | ✅ correct |
| R31 | CO2 Certificates | `co2_certificate_revenue_keur` | 83 / 82 kEUR | ✅ |
| R27 | Total Revenue | `revenue_keur` | 3,250 / 3,197 kEUR | ✅ |

- **PPA:** 57 EUR/MWh Y1, indexed 2%/year, 12-year term  
- **Balancing:** 0 — `balancing_cost_pv = 0`, `balancing_cost_eur_per_mwh = 0`  
- **CO2:** flat 1.5 EUR/MWh (`co2_enabled=True`, `co2_certificate_price_eur_per_mwh=1.5`)  
  - ⚠️ **Gap:** Excel may have escalating CO2 price — not yet verified from Oborovo CF sheet

### 1.4 Revenue Gaps

| Gap | Project | Severity | Notes |
|---|---|---|---|
| CO2 price is flat | Oborovo | Medium | `co2_price_eur=1.5` flat; Excel may have a declining curve |
| PPA production cap / reduced tariff | Oborovo | Medium | `apply_reduced_tariff()` exists but not confirmed as wired |
| Merchant revenue timing | Oborovo | Low | Market_prices_curve is zeros for Y1-Y12 (PPA period) |

---

## 2. OPEX Mapping

### 2.1 TUHO OPEX (12 items, Y1 = 1,998 kEUR)

| Code | Name | Y1 (kEUR) | Inflation | Excel Row |
|---|---|---|---|---|
| B.01 | Technical Management | 279.99 | 2% | OpEx B.01 |
| B.02 | O&M Preventive & Corrective | 426.60 | 2% | OpEx B.02 |
| B.03 | Maintain Site | 68.00 | 2% | OpEx B.03 |
| B.04 | Clean Material | 5.00 | 2% | OpEx B.04 |
| B.05 | Security | 50.00 | 2% | OpEx B.05 |
| B.06 | Insurance | 468.74 | 2% | OpEx B.06 |
| B.07 | Lease & Property Tax | 248.88 | 2% | OpEx B.07 |
| B.08 | Power Expenses | 93.72 | 2% | OpEx B.08 |
| B.10 | Audit & Accounting & Legal | 23.99 | 2% | OpEx B.10 |
| B.11 | Bank Fees | 20.00 | 2% | OpEx B.11 |
| B.12 | Environmental & Social Management | 200.00 | 2% | OpEx B.12 |
| B.13 | Contingencies | 113.09 | **6%** | OpEx B.13 |
| **Total** | | **1,998.01** | | |

### 2.2 Oborovo OPEX (15 items, Y1 = 1,338 kEUR)

| Code | Name | Y1 (kEUR) | Inflation | Notes |
|---|---|---|---|---|
| B.01 | Technical Management | 198.0 | 2% | |
| B.02 | Infrastructure Maintenance | 244.0 | 2% | |
| B.03 | Maintain Site | 45.0 | 2% | |
| B.04 | Clean Material | 40.0 | 2% | |
| B.05 | Security | 30.0 | 2% | |
| B.06 | Insurance | 255.0 | 2% | |
| B.07 | Lease & Property Tax | 208.08 | 2% | |
| B.08 | Power Expenses | 177.0 | **0%** (flat) | |
| B.09 | Fees | 14.0 | **0%** (flat) | |
| B.10 | Audit&Accounting&Legal | 24.0 | 2% | |
| B.11 | Bank Fees | 20.0 | 2% | |
| B.12 | Environmental&Social | 32.0 | 2% | Step Y3→5.2 kEUR |
| B.13 | Contingencies | 51.0 | 2% | |
| B.TAX | Taxes | 0.0 | 0% | |
| B.SAL | Salary&Payroll | 0.0 | 0% | |
| **Total** | | **1,338.08** | | |

### 2.3 Oborovo Double-Count Issue — Resolved

**Historical concern (MEMORY.md):** Model gave Y1 OpEx = 1,998 kEUR vs. Excel target 1,338 kEUR.  
**Root cause identified:** Old factory used Excel **Budget column** values (which sum sub-items) as aggregate amounts.  
**Resolution:** Current `create_default_oborovo()` uses **Y1 column** values which are correctly pre-aggregated per Excel.  
**Verification:** `test_opex_y1_total` passes — Oborovo Y1 = 1,338 kEUR ✅  
**No double-count in current implementation.**

### 2.4 OPEX Calculation Principle

```
Y(N) = Y1 × (1 + inflation)^(N-1)

# Step changes replace base from trigger year onward:
Step at Y(S): Y(S) = step_amount
              Y(S+1) = step_amount × (1 + inflation)
```

- Annual OPEX distributed to semi-annual periods via `day_fraction`
- Construction periods: 0 OPEX
- Full 30-year horizon
- **Exceptions:** Power Expenses (Oborovo) and Fees are flat (0% inflation)

---

## 3. OPEX Stable Code Recommendation

**Current limitation:** `OpexItem` has no stable code field — name-based grouping is fragile.  
**Recommendation:**

```python
@dataclass(frozen=True)
class OpexItem:
    name: str
    code: str = ""              # e.g. "B.01", "B.02.01" — stable identifier
    y1_amount_keur: float
    annual_inflation: float = 0.02
    step_changes: tuple[tuple[int, float], ...] = ()
    is_sub_item: bool = False  # True → excluded from total OPEX sum
```

**Rules:**
- Only `is_sub_item=False` rows count toward total OPEX
- Sub-items exist for audit traceability but are excluded from sum
- `code` enables stable test references and diagnostics
- Default `code=""` preserves backward compatibility with existing factories

---

## 4. CFADS / Free Cash Bridge

```
Revenue (net after balancing, incl. CO2)
− OPEX (annual × day_fraction)
= EBITDA

EBITDA
− Cash Tax (ATAD-adjusted, loss-carried, paid H2 each year)
= CFADS / free cash for senior debt sizing

CFADS
− Senior Debt Service
− DSRA funding (+ release)
= Free cash for SHL

Free cash for SHL
− SHL Service (PIK or SWEEP)
= Distribution
```

**Gaps before senior debt sizing can be trusted:**
1. Oborovo CO2 price — flat 1.5 vs. possibly escalating Excel curve
2. Oborovo PPA production cap — `apply_reduced_tariff()` not confirmed as wired
3. TUHO tax = 0 for all periods — large construction carryforward verified ✅

---

## 5. Tests Run

```bash
pytest tests/test_revenue.py tests/test_opex.py -v
```

**Result: 31 passed, 0 failed**

```
tests/test_revenue.py: 17 passed
  - test_annual_generation_p50  ✅
  - test_annual_generation_p90   ✅
  - test_generation_degradation ✅
  - test_full_generation_schedule ✅
  - test_revenue_schedule_basic  ✅
  - test_ppa_tariff_y1           ✅
  - test_ppa_tariff_y2           ✅
  - test_ppa_tariff_y12          ✅
  - test_ppa_tariff_with_cap     ✅
  - test_market_price_from_curve ✅
  - test_market_price_extrapolation ✅
  - test_net_revenue_after_balancing ✅
  - test_co2_certificates        ✅
  - test_tuho_first_operating_period_day_count_matches_excel ✅
  - test_tuho_ppa_merchant_boundary_matches_excel ✅
  - test_tuho_revenue_components_match_excel_rows ✅

tests/test_opex.py: 14 passed
  - test_opex_y1_total           ✅
  - test_opex_items_count        ✅
  - test_opex_schedule_annual    ✅
  - test_opex_escalation         ✅
  - test_opex_per_mw             ✅
  - test_opex_per_mwh            ✅
  - test_opex_breakdown          ✅
  - test_opex_item_step_change_is_persistent_new_base ✅
  - test_opex_growth_rate        ✅
  - test_period_schedule_length  ✅
  - test_construction_periods_zero_opex ✅
  - test_operation_periods_positive_opex ✅
  - test_y1_periods_sum_to_y1_annual_after_excel_stub_roll ✅
  - test_total_opex_undiscounted ✅
  - test_total_opex_discounted   ✅
```

```bash
python3 -c "import main_web"
```

**Result: OK** (Streamlit cache warnings in headless mode are expected)

---

## 6. Runtime / Formula Changes

| Check | Result |
|---|---|
| `git diff --stat` | nothing |
| `git diff --name-only` | nothing |
| `domain/revenue` changes | none |
| `domain/opex` changes | none |
| `domain/waterfall` changes | none |
| workbook/export changes | none |
| JS financial calculations | none |

**This was a discovery-only phase. Zero runtime changes.**

---

## 7. Known Limitations

1. **Oborovo CO2 price:** flat 1.5 EUR/MWh — Excel may have declining curve (not yet verified)
2. **Oborovo PPA production cap:** `apply_reduced_tariff()` exists but not confirmed as wired for Oborovo
3. **No `code` field on OpexItem:** name-based grouping is fragile; schema enhancement recommended (Section 3)
4. **OPEX step changes:** step_amount itself inflates from step year onward — matches Excel behavior but not explicitly verified

---

## 8. Recommended Next Phases

### Phase 20O — OPEX Parity Implementation
1. Add `code` field to `OpexItem` (backward-compatible, default `""`)
2. Add `is_sub_item` field (default `False`)
3. Verify Oborovo CO2 price vs. Oborovo Excel CF sheet R31
4. Verify Oborovo PPA production cap / `apply_reduced_tariff()` wiring
5. Run full TUHO + Oborovo waterfall smoke test after changes

### Phase 20P — Revenue Parity Confirmation
1. CFADS bridge per-period diagnostic vs. Excel
2. TUHO balancing = 8.0 EUR/MWh — verify all periods match
3. TUHO CO2 declining schedule matches Excel R31 values exactly

### Phase 20Q — Senior Debt Sizing
1. Only after CFADS bridge verified
2. Verify DSCR sculpting uses correct CFADS
3. Debt sizing: `min_dscr = debt_service / CFADS`

---

*This document is discovery only. No runtime changes were made.*
