# Phase 7 — OPEX Semiannual Projection Audit (Stage 2)

## Purpose

Validate whether Python's annual OPEX engine can correctly project 30 annual values into 60 semiannual periods (H1/H2) matching Excel CF!R38.

## Source Files

- **Excel workbook:** `20260330_TUHO_BP.xlsm`
- **Excel fixture:** `tests/fixtures/excel_tuho_full_model_extract.json`
- **Excel metric:** `CF.operating_expenses_after_bank_tax_keur` (column index 2)
- **Python template:** `domain/opex/templates/tuho.py`
- **Python engine:** `domain/opex/engine.py` — `compute_annual_opex()`
- **Python projection:** `domain/opex/projections.py` — `opex_schedule_period()`

## Annual OPEX Parity Status

| Source | 30-Year Total |
|--------|--------------|
| Excel CF!R38 / OpEx!R105 incl. contingencies | **84,674.78 kEUR** |
| Python offline OPEX engine (`compute_annual_opex`) | **84,674.78 kEUR** |
| Python runtime (flag-off) | 83,942 kEUR |
| **Delta (offline vs Excel)** | **0.00 kEUR — exact match** |

Annual engine is calibrated. Stage 2 tests semiannual projection.

## Excel CF!R38 Extraction

Extracted `CF.operating_expenses_after_bank_tax_keur` from `period_diagnostics` fixture (column index 2). Values are negative in fixture; absolute values used for comparison.

**Period count:** 60 operating periods (P01=Y01-H1 through P60=Y30-H2)

**Period date convention from fixture:**
- H1 end date: June 30 → day count = 181 (non-leap) or 182 (leap)
- H2 end date: December 31 → day count = 184 (non-leap) or 183 (leap)
- Leap years in horizon: 2032, 2036, 2040, 2044, 2048, 2052, 2056

## Projection Methods Tested

### A. Flat Split
- H1 = annual / 2
- H2 = annual / 2
- **Result:** Passes horizon threshold (0.00 kEUR), FAILS per-period threshold (max delta = 15.05 kEUR)

### B. Actual-Day / Day-Count Split
- Non-leap year: H1 = annual × 181/365, H2 = annual × 184/365
- Leap year: H1 = annual × 182/365, H2 = annual × 183/365
- **Result:** PASSES all thresholds (max delta = 4.77 kEUR, horizon delta = 0.00 kEUR)

### C. Current `projections.py` Helper (`opex_schedule_period`)
Uses `period.day_fraction` from runtime period object. The period engine computes actual-day fractions from the calendar:
- Non-leap H1: `181/365 = 0.495890`
- Non-leap H2: `184/365 = 0.504110`
- Leap H1: `182/365 = 0.497268`
- Leap H2: `183/365 = 0.502732`

**Result:** PASSES all thresholds — **identical to Actual-Day** (4.77 kEUR max, 0.00 kEUR horizon)

## Threshold Results

| Method | Max Period Δ | Threshold | Horizon Δ | Threshold |
|--------|-------------|-----------|-----------|-----------|
| Flat split | 15.05 kEUR | ❌ FAIL (≤10) | 0.00 kEUR | ✅ PASS (≤100) |
| Actual-day | 4.77 kEUR | ✅ PASS (≤10) | 0.00 kEUR | ✅ PASS (≤100) |
| Current proj. | 4.77 kEUR | ✅ PASS (≤10) | 0.00 kEUR | ✅ PASS (≤100) |

**Per-period threshold (5 kEUR strict):**
- Flat: ❌ FAIL (15.05 kEUR)
- Actual-day: ✅ PASS (4.77 kEUR)
- Current: ✅ PASS (4.77 kEUR)

## Leap Year Periods Causing Flat Split Failure

Flat split fails specifically for leap years where H1 and H2 day counts differ from 50/50:
- **Y03 (2032):** P05 (Y03-H1) flat=1073.53 vs actual=1070.59 vs excel=1067.66 → flat delta=5.87 kEUR; P06 (Y03-H2) flat=1073.53 vs actual=1076.47 vs excel=1079.39 → flat delta=-5.87 kEUR
- All leap years (Y03, Y07, Y11, Y15, Y19, Y23, Y27) show similar split.

## Selected Projection Convention

**Actual-day / day-count split** is the correct convention.

The `projections.py` helper already uses actual-day fractions via `period.day_fraction`. The period engine computes day fractions from the actual calendar, so the existing runtime projection logic is correct.

**No code changes needed.** The existing `opex_schedule_period()` in `projections.py` already implements the correct convention.

## Stage 3 Runtime Flag

**Stage 3 runtime flag IS allowed.** The semiannual projection convention (actual-day) is validated. Max period delta is 4.77 kEUR (within 5 kEUR strict threshold). Horizon delta is 0.00 kEUR.

If the runtime flag is activated (`use_opex_line_item_engine=True`), the OPEX cash flow will correctly match Excel CF!R38 semiannual presentation using the actual-day convention.

## Known Limitations

1. **Fixture covers 60 operating periods (P01-P60).** The runtime has 61 operating periods (P02-P62) because P01 is construction. Period indices differ but the underlying day fractions are consistent.

2. **`opex_schedule_period` requires runtime period objects.** It cannot be used in a fully offline context without instantiating the period engine. However, this is not a restriction because the period engine is lightweight.

3. **B.02.1 explicit schedule** is already inflation-free and annual. The semiannual split of B.02.1 uses the same day-count convention as all other items.

4. **Oborovo is out of scope** for this branch. Oborovo OPEX projection should be validated separately in a future workstream.

## Recommended Next Branch

`phase7-opex-runtime-flag` — Activate the OPEX runtime flag for TUHO. Wire `use_opex_line_item_engine=True` in the TUHO factory. Validate that runtime waterfall behavior is unchanged except OPEX now uses line-item engine. Oborovo remains guarded.

## R99/R102 BLOCKED

R99 and R102 remain BLOCKED. No SHL FCF runtime source. No R99/R102 promotion.

## Hard Constraints

- No production runtime behavior changes (this branch)
- No OPEX runtime flag activation
- No factory opt-in
- No waterfall changes
- No tax/debt/SHL changes
- Default behavior unchanged