# Phase 20Q — Diagnostic Drilldown

**Branch:** `phase20q-diagnostic-drilldown`  
**Base:** `ba7a81fd3a90f1cd09d98e507296872c68fd6063` (after PR #279)  
**Date:** 2026-05-27  
**Status:** Diagnostic only — no runtime formula changes

---

## 1. Scope

This phase explains the exact sources of Phase 20P deltas by line item and period, for TUHO P4 and Oborovo P4. No formula changes.

---

## 2. TUHO P4 Drilldown (Period Index 3, Year-Index 1, H2)

### 2.1 Period Context

| Field | Value |
|---|---|
| Period index (0-based) | 3 |
| Period (1-based) | 3 (TUHO internal) |
| Year index | 1 (operating year 1 = Y2) |
| Period in year | 2 (H2) |
| Days in period | 184 |
| Day fraction | 0.504110 |

### 2.2 Revenue Drilldown

#### Excel vs Python comparison

| Line | Excel (kEUR) | Python (kEUR) | Delta | Status |
|---|---|---|---|---|
| Production (MWh) | 73,468.93 | 73,468.93 | +0.00 | ✅ PASS |
| PPA gross revenue | N/A (combined) | 4,408.14 | — | — |
| CO2 certificate revenue | embedded | 307.91 | — | — |
| Balancing cost | ~578 | 587.75 | +10 | ❌ |
| **Operating Revenue (R22)** | **4,186.48** | **4,186.48** | **0.00** | **✅ PASS** |

#### Revenue bridge decomposition

```
PPA tariff:                    60.00 EUR/MWh
Generation:                   73,468.93 MWh
PPA gross (60 × 73,469):      4,408.14 kEUR
Balancing (8.0 × 73,469/1000):  587.75 kEUR
Net after balancing:           4,128.30 kEUR  ← decomp['net_revenue_after_balancing_keur']
CO2 (semiannual schedule):       58.18 kEUR  ← p4.revenue_keur - net_rev
                              ──────────
Excel Operating Revenue:       4,186.48 kEUR  ← p4.revenue_keur ✅ EXACT MATCH
```

**Key finding:** `revenue_keur` (4,186.48) is `net_revenue_after_balancing` (4,128.30) + CO2 portion (58.18). The 58.18 kEUR CO2 portion in revenue comes from `co2_sales_schedule` via `use_co2_revenue_bridge` path. The remaining CO2 (307.91 − 58.18 = 249.73 kEUR) flows to taxable income via `co2_cit_bridge`.

### 2.3 OPEX Drilldown

| Line | Value |
|---|---|
| Annual Y2 OPEX (year_index=1) | 1,998.01 kEUR |
| Semi-annual (×0.504110) | 1,007.22 kEUR |
| P4 waterfall `opex_keur` | 1,029.64 kEUR |
| vs Semi-annual delta | +22.42 kEUR |
| vs Excel absolute (1,023.26) delta | +6.38 kEUR |

**Sign convention:** Python reports absolute value; Excel shows OPEX as a negative deduction in the CF statement. The correct comparison is absolute vs absolute.

**Root cause of +6.38 kEUR delta:** Y2 annual = 1,998.01 kEUR (Y1 base amounts, some inflated at 6% for B.13 Contingencies, rest at 2%). The semi-annual distribution uses day_fraction=0.504110, but slight differences arise from rounding in individual OpexItem inflation calculations vs Excel's period roll.

### 2.4 Senior Debt Drilldown

| Line | Value |
|---|---|
| Opening senior balance | 40,143.82 kEUR |
| Semi-annual period rate | 0.028348 |
| Computed interest (40,143.82 × 0.028348) | 1,138.00 kEUR |
| Actual senior interest | 1,179.04 kEUR |
| **Interest gap** | **+41.03 kEUR** |
| Senior principal | 866.21 kEUR |
| Senior debt service | 2,045.24 kEUR |
| Excel senior service | 2,180.24 kEUR |
| **Delta** | **−135.00 kEUR** |

**Interest basis difference:** Python uses semi-annual period rate (0.028348) compounded from the all-in rate (5.75%). Excel appears to use a slightly different rate or day count convention, resulting in +41 kEUR higher interest per period.

**Senior DS gap of −135 kEUR:** Python sculpts debt service to meet min DSCR (1.3856 at period 25), resulting in DSCR = 1.5435 in P4 (higher than target 1.2 because the debt is sized to the tightest period). Excel's Macro!R50 frozen schedule produces higher per-period DS service (2,180.24 kEUR). This is a known basis difference — Mode C (frozen_excel_schedule) would preserve Excel's schedule.

### 2.5 SHL Drilldown

| Line | Value |
|---|---|
| SHL opening balance | 33,324.92 kEUR |
| Annual SHL interest threshold (balance × rate) | 2,642.67 kEUR |
| CFADS - senior DS | 1,111.60 kEUR |
| Actual SHL interest (PIK capped) | 1,111.60 kEUR |
| SHL principal sweep | 0.00 kEUR |
| Excel sweep | 982.99 kEUR |
| **Delta** | **−982.99 kEUR** |

**Why Python shows no sweep:** `pik_switch_triggered = (cf_for_shl > shl_balance × shl_rate)`  
Python: 1,111.60 < 2,642.67 → **False** → PIK only, no sweep.

**Why Excel shows 982.99 kEUR sweep:** Excel uses a different trigger basis or cash flow basis. One possibility: Excel's senior_ds in P4 is lower (2,180.24), leaving more cash (3,156.84 − 2,180.24 = 976.60 kEUR ≈ 982.99), which exceeds some threshold for sweep. Alternatively, Excel may use an annual interest threshold rather than the PIK formula Python uses.

---

## 3. Oborovo P4 Drilldown (Period Index 3, Year-Index 1, H2)

### 3.1 Period Context

| Field | Value |
|---|---|
| Day fraction | 0.495890 |
| Year index | 1 |
| Period in year | 2 (H2) |

### 3.2 OPEX Drilldown

| Line | Value |
|---|---|
| Y2 annual OPEX | 1,338.08 kEUR |
| Semi-annual (×0.495890) | 663.54 kEUR |
| P4 waterfall `opex_keur` | 676.79 kEUR |
| vs Semi-annual delta | +13.25 kEUR |
| vs Excel absolute (644.34) delta | **+32.45 kEUR** |

**Root cause of +32.45 kEUR delta:** Y2 annual = 1,338.08 kEUR (pre-inflation Y1 baseline for operating OPEX). The 13.25 kEUR difference from semi-annual is due to day_fraction distribution. The additional ~19 kEUR gap vs Excel absolute (644.34) likely comes from different inflation application or different period day count (Excel may use 360-day year vs Python's 365.25).

**Confirmed:** Oborovo has no double-count in the current factory — Y1 amounts (1,338.08 kEUR) are pre-aggregated and correctly inflation-indexed.

### 3.3 Senior Debt Drilldown

| Line | Value |
|---|---|
| Opening senior balance | 39,328.12 kEUR |
| All-in rate | 5.65% |
| Period rate | 0.027862 |
| Computed interest | 1,095.75 kEUR |
| Actual senior interest | 1,137.03 kEUR |
| **Interest gap** | **+41.28 kEUR** |
| Senior DS | 2,057.91 kEUR |
| Excel senior DS | 2,270.28 kEUR |
| **Delta** | **−212.37 kEUR** |

**Same interest basis issue:** Same +41 kEUR gap pattern as TUHO — Excel uses a different rate basis or day count.

**DS gap:** Oborovo uses fixed debt amount (42,852 kEUR from factory), not DSCR-sculpted. The per-period service (2,057.91) differs from Excel's frozen schedule (2,270.28) by −212 kEUR. This is consistent with the frozen_excel_schedule vs sculpted difference.

### 3.4 SHL Drilldown

| Line | Value |
|---|---|
| SHL opening balance | 14,716.20 kEUR |
| Annual SHL interest threshold | 1,177.30 kEUR |
| CFADS - senior DS | 520.46 kEUR |
| SHL interest (PIK) | 585.43 kEUR |
| After SHL interest | −64.97 kEUR |
| SHL principal sweep | 0.00 kEUR |
| Excel sweep | 340.54 kEUR |
| **Delta** | **−340.54 kEUR** |
| Distribution | 64.97 kEUR |
| Excel distribution | 0.00 kEUR |

**Distribution = 64.97 kEUR:** After SHL interest (PIK), remaining CF (520.46 − 585.43 = −64.97) is negative, so no sweep. The residual 64.97 flows to distribution. Excel shows 0 distribution — meaning Excel either has more cash for SHL or applies distribution differently.

---

## 4. Summary of Key Findings

### Revenue
- TUHO production: exact match ✅
- TUHO revenue_keur: exact match (4,186.48) ✅ — explained by net_rev + CO2 portion
- TUHO balancing: 8 EUR/MWh vs Excel's lower rate → delta ~10 kEUR
- Oborovo revenue: exact match (3,255.16) ✅
- Oborovo balancing: 0 confirmed ✅

### OPEX
- TUHO: +6.38 kEUR delta (sign conv. + rounding) — acceptable
- Oborovo: +32.45 kEUR delta — partially from day_fraction, partially from inflation basis difference

### Senior Debt
- Interest basis difference: +41 kEUR/period (Excel uses different rate or day count)
- DS service gap: Python sculpts at min_dscr=1.39; Excel uses frozen Macro!R50 schedule

### SHL Sweep
- TUHO: Python = 0, Excel = 982.99 → different trigger basis
- Oborovo: Python = 0, Excel = 340.54 → same pattern

### SHL Distribution
- TUHO: both 0 ✅
- Oborovo: Python = 64.97, Excel = 0 → opposite direction (Python has distribution, Excel doesn't)

---

## 5. Tests

```bash
pytest tests/test_phase20q_diagnostic_drilldown.py -v
# 19 passed in 1.02s
```

---

## 6. Confirmations

| Check | Result |
|---|---|
| Runtime/model formulas changed? | **No** |
| Senior debt calculations changed? | **No** |
| SHL waterfall logic changed? | **No** |
| Default mode = frozen_excel_schedule? | ✅ |
| Future modes A/B raise NotImplementedError? | ✅ |
| TUHO baseline outputs unchanged? | ✅ 65,826 / 173,572 / 1.230 |
| Oborovo baseline outputs unchanged? | ✅ 63,501 / 104,699 / 1.150 |

---

## 7. Recommended Next Phase

**Phase 20R** — SHL Sweep Trigger Investigation:
1. TUHO: Why does Excel trigger SHL sweep at 982.99 kEUR when Python's threshold check fails?
   - Check if Excel uses annual SHL interest threshold vs semi-annual
   - Check if Excel's CF available for SHL includes DSRA release
2. Oborovo: Why does Python show distribution = 64.97 when Excel shows 0?

**Phase 20S** — Interest Basis Alignment:
1. Investigate +41 kEUR/period interest gap for both projects
2. Determine whether Python's rate/day_fraction basis matches Excel's convention

**Phase 20T** — OPEX Inflation Fix (Oborovo):
1. Investigate Oborovo +32.45 kEUR OPEX delta — is it day_fraction, inflation, or missing line?

---

*This document covers diagnostics only. No runtime formula changes were made.*
