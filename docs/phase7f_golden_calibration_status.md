# Phase 7F-3: Golden Calibration Foundation — Status

**Branch:** `phase7f-golden-calibration-foundation`
**Date:** 2026-04-29
**Status:** ✅ Complete

## Goal

Implement the first real Excel-aligned sponsor calibration layer using
Oborovo/TUHO reference scenarios. Calibration and validation only.

---

## Scope (Phase 7F-3)

- ✅ Golden sponsor calibration fixtures (Oborovo, TUHO)
- ✅ LP distributions — validated (ratio, aggregate integrity)
- ✅ GP distributions — validated (ratio, aggregate integrity)
- ✅ GP carry allocation — fixture documented; full enforcement Phase 7F-4
- ⏳ Sponsor IRR — fixture documented; full enforcement Phase 7F-4
- ⏳ Sponsor MOIC — fixture documented; full enforcement Phase 7F-4
- ✅ Preferred return accrual — validated (entries per period, accrual ≥ 0)
- ✅ Tolerance configuration (IRR ±1pp, cashflow ±1kEUR, allocation ±1kEUR)
- ✅ Deterministic comparison reports (fixture reachability tests)
- ✅ Calibration summary doc (this file)

## What was NOT in scope (deferred)

- Full 60-period timeline wiring from project model to sponsor runner
- Full-horizon LP/GP total distribution enforcement (needs 60-period FCF)
- Sponsor IRR/MOIC full-horizon computation (needs complete cashflows)
- UI redesign, persistence redesign, API/productization, deployment

---

## Golden Fixtures

### Oborovo Solar PV (75.26 MWp, Croatia)

| Parameter | Value |
|---|---|
| Financial Close | 2029-06-29 |
| COD | 2030-06-29 |
| LP commitment | 400 kEUR |
| GP commitment | 100 kEUR |
| LP/GP split | 80% / 20% |
| Hurdle rate | 8% p.a. semiannual |
| GP promote | 20% |
| Project debt | 42,852 kEUR |
| SHL opening balance | 14,716.2 kEUR (13,547.2 + 1,169.0 IDC) |
| SHL rate | 8.00%, pik_then_sweep |
| **Full-horizon LP distributions** | **83,934 kEUR** |
| **Full-horizon GP distributions** | **20,984 kEUR** |
| **Full-horizon total** | **104,918 kEUR** |
| LP equity IRR (Excel) | 10.60% |
| GP equity IRR (Excel) | ~18.0% |
| LP MOIC | ~2.10x |
| GP MOIC | ~2.50x |

### TUHO Wind 1 (35 MW, Croatia)

| Parameter | Value |
|---|---|
| Financial Close | 2029-07-01 |
| COD | 2030-01-01 |
| LP commitment | 400 kEUR |
| GP commitment | 100 kEUR |
| LP/GP split | 80% / 20% |
| Hurdle rate | 8% p.a. semiannual |
| GP promote | 20% |
| Project debt | 43,359 kEUR |
| SHL opening balance | 32,704 kEUR (29,135 + 3,569 IDC) |
| SHL rate | 7.93%, pik_then_sweep |
| **Full-horizon LP distributions** | **94,651 kEUR** |
| **Full-horizon GP distributions** | **23,663 kEUR** |
| **Full-horizon total** | **118,314 kEUR** |
| LP equity IRR (Excel) | 11.61% |
| GP equity IRR (Excel) | ~20.0% |
| LP MOIC | ~2.40x |
| GP MOIC | ~2.80x |

---

## Current Test Results (Foundation)

Tests use **first-N-period fixtures + zero-fill remainder**:

```
tests/test_sponsor_golden_calibration.py   19 passed ✅
```

### Oborovo — first 12 periods (3,993.6 kEUR total FCF input)
| Test | Result |
|---|---|
| Config constructs | ✅ |
| Runs to completion | ✅ |
| LP/GP ratio = 4.0 | ✅ (exactly 4.0) |
| LP+GP = input total | ✅ (3993.6 kEUR) |
| Aggregate = sum of parts | ✅ |
| Preferred return entries = 60 | ✅ |
| Waterfall 60 period results | ✅ |

### TUHO — first 3 periods (2,890.4 kEUR total FCF input)
| Test | Result |
|---|---|
| Config constructs | ✅ |
| Runs to completion | ✅ |
| LP/GP ratio = 4.0 | ✅ (exactly 4.0) |
| LP+GP = input total | ✅ (2890.4 kEUR) |
| Aggregate = sum of parts | ✅ |
| Preferred return entries = 60 | ✅ |
| Waterfall 60 period results | ✅ |

---

## Known Limitations (Phase 7F-3)

1. **Partial timeline only**: Tests use first-12 (Oborovo) and first-3 (TUHO)
   periods from fixtures. Remaining 48/57 periods are zero-filled.
   Full-horizon enforcement requires wiring the project model to the sponsor
   runner to produce 60-period `available_cash_by_period` arrays.

2. **LP/GP ratio validation only**: The 4.0 ratio confirms the waterfall
   allocates proportionally. Full waterfall tier mechanics (preferred return,
   catch-up, promote) require full-horizon cashflows to exercise.

3. **Sponsor IRR/MOIC deferred**: These require full 60-period distribution
   timelines and actual date-level cashflows. Documented in fixtures;
   enforcement in Phase 7F-4.

---

## Phase 7F-4 Plan

1. Wire project model (Oborovo/TUHO) → sponsor runner to produce full
   60-period `available_cash_by_period`
2. Validate full-horizon LP/GP totals against golden targets
3. Validate LP equity IRR against ±1pp tolerance
4. Validate GP carry allocations
5. Validate sponsor MOIC

---

## Source Files

- `tests/test_sponsor_golden_calibration.py` — 19 tests (this phase)
- `tests/fixtures/excel_oborovo_periods.json` — first-12 Oborovo periods
- `tests/fixtures/excel_tuho_periods.json` — first-3 TUHO periods
- `tests/fixtures/excel_calibration_targets.json` — reference targets
- `tests/fixtures/excel_golden_oborovo.json` — Oborovo golden cells
- `app/sponsor_runner.py` — sponsor waterfall orchestrator

## Tolerance Reference

| Metric | Tolerance |
|---|---|
| IRR | ±1.0 pp (percentage points) |
| Cashflow | ±1.0 kEUR |
| Allocation | ±1.0 kEUR |
