# Phase 9: CO2 Revenue Bridge — Wiring Confirmation

**Branch:** `phase9-co2-revenue-bridge-wiring`
**Date:** 2026-05-20
**Status:** IMPLEMENTED (confirmed against code)

---

## 1. Overview

The CO2 revenue bridge adds TUHO CO2 certificate revenue (~611 kEUR Y1) into the waterfall `period.revenue_keur`, and therefore into EBITDA. This is the first step in the CO2→CIT bridge chain (Section 13, item 6 of the design doc).

---

## 2. Flag Behavior

**Parameter:** `use_co2_revenue_bridge: bool = False` in `run_waterfall_v3_core()`

| Flag Value | Behavior |
|---|---|
| `False` (default) | Legacy baseline unchanged; CO2 excluded from revenue/EBITDA |
| `True` | CO2 added to `period.revenue_keur` per period; EBITDA increases |

---

## 3. Implementation Location

**Primary file:** `app/waterfall_core.py`

| Element | Location | Description |
|---|---|---|
| Flag declaration | Line 57 | `use_co2_revenue_bridge: bool = False` |
| TUHO-only guard | Lines 115-120 | Raises `ValueError` for non-TUHO-WIND-1 |
| CO2 extraction | Lines 121-127 | From `revenue_decomposition_schedule()` |
| Revenue augmentation | Lines 183-187 | Adds CO2 to `rev` per period |
| Audit metadata | Lines 248-259 | `_co2_revenue_bridge` dict + `co2_revenue_bridge_keur` per period |

---

## 4. What Changes vs. What Remains Unchanged

### Changes when `use_co2_revenue_bridge=True`
- `period.revenue_keur` + CO2 per period
- `ebitda_keur` + CO2 per period (since `ebitda = max(0, rev - opex)`)
- `_co2_revenue_bridge` metadata populated

### NO Changes (R99/R102 remain BLOCKED)
- TaxEngine: No change; CO2 does NOT flow into CIT
- R99 gate: No change
- R102 gate: No change
- DistributionAccount: No change
- Sponsor handoff: No change
- SHL: No change
- SeniorDebt: No change

---

## 5. CO2 Y1 TUHO Amount

- Generation Y1 ≈ 145,750 MWh
- CO2 Y1 = 145,750 × 4.191 / 1,000 ≈ **610.8 kEUR**

---

## 6. Oborovo Protection

TUHO-only guard: Oborovo unchanged when flag=True (raises `ValueError`).

---

## 7. Relationship to Design Doc (PR #140)

Implements Section 15, Items A–C:
- A: CO2 in `revenue_decomposition_schedule()` ✅
- B: CO2 extracted per period ✅
- C: CO2 added to `rev` in waterfall ✅

Items D–G (TaxEngine CO2 field, downstream wiring) remain for future phases.

---

*End of CO2 Revenue Bridge Wiring Confirmation*
