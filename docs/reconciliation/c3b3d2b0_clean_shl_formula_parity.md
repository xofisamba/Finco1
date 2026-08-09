# C3B3D2B0-R1 — Clean SHL Waterfall Formula Parity

**Status**: `C3B3D2B0_CLEAN_SHL_FORMULA_PARITY_PROVEN`
**Branch**: `stage-c3b3d2b0-clean-shl-formula-parity`
**Base**: `b9a7fec27ea2be061d169162d24bd48af3b78120` (main after C3B3D2A squash-merge)
**DO NOT MERGE**: Proof-of-concept only. Wiring to Tax/CFADS/senior-debt deferred to C3B3D2B1+.

---

## 1. Scope

C3B3D2B0-R1 proves that a single pure Python function — with no mode enum, no
project dispatch, no hardcoded period boundaries — reproduces the Excel-sourced
Oborovo SHL schedule to machine epsilon across all 41 periods using an
**independently computed day-count fraction** that does not read `gross_accrued_interest_keur`.

**Not in scope**: Tax engine, CFADS, senior-debt fixed point, DSRA, distribution account,
R99, R102, Sponsor, production wiring.

---

## 2. Why the Previous DCF Was Circular (Now Resolved)

The initial C3B3D2B0 implementation used `shl_dcf_derived_actual_365` as the test-driver DCF:

```
shl_dcf_derived_actual_365 = gross_accrued_interest_keur / (opening_balance_keur × annual_rate)
```

This is **circular**: it algebraically reconstructs the source gross interest, then feeds
it as the DCF. The formula `gross = opening × rate × DCF` with this DCF must return the
source gross — it is not an independent proof. Therefore the verdict
`C3B3D2B0_CLEAN_SHL_FORMULA_PARITY_PROVEN` based on this driver was invalid.

The field `shl_dcf_derived_actual_365` is retained in the D2A fixture as a diagnostic
(it was used to identify the correct convention), but it may NOT be the final parity driver.

---

## 3. Independent DCF Formula (Source-Proven)

**Convention**: actual/365 with inclusive end date (actual/365-Fixed).

```python
def compute_shl_dcf_actual_365_inclusive(period_start: date, period_end: date) -> float:
    return ((period_end - period_start).days + 1) / 365
```

**Provenance**: `OPERATING_SHL_DAY_COUNT_SOURCE_PROVEN_ACTUAL_365_INCLUSIVE`

**Evidence**: Computed independently from `period_start_date` and `period_end_date`
(from `tests/fixtures/interest_limitation/oborovo_interest_limitation_fixture.json`,
a committed fixture). Max delta vs `shl_dcf_derived_actual_365` across all 40 periods:
**1.11e-16** (machine epsilon). Zero exceptions.

### Inclusive vs Exclusive — Why the Previous Error Occurred

Using `(end - start).days / 365` (exclusive end date) gives 183/365 = 0.50137 for DS[1]
instead of 184/365 = 0.50411. The error per period:

```
opening × rate × (1/365) = 15790.44 × 0.08 / 365 ≈ 3.46 kEUR
```

This compounded recursively through 40 PIK/sweep periods to reach **~387 kEUR closing
error** at DS[40]. Resolution: the Excel SHL convention counts the end date as a calendar
day (inclusive), giving `days + 1` in the numerator.

### Leap-Year Treatment

The denominator is always **365**, even for periods that contain February 29.
Five such periods exist in the Oborovo schedule: DS[4, 12, 20, 28, 36].
All five match `shl_dcf_derived_actual_365` to machine epsilon using fixed denominator 365.

### DS[1] Exact Calculation

```
period_start = 2030-07-01
period_end   = 2030-12-31
days_inclusive = 184
DCF = 184 / 365 = 0.5041095890410959
```

---

## 4. Source Inputs

| Input | Source | Classification |
|---|---|---|
| `shl_draw_keur` | D2A fixture workbook_inputs (Excel Inputs!D325) | SOURCE_RAW_CACHED_VALUE |
| `shl_annual_rate` | D2A fixture workbook_inputs (Excel Inputs!F328) | SOURCE_RAW_CACHED_VALUE |
| Period dates | `oborovo_interest_limitation_fixture.json` (committed) | SOURCE_RAW_CACHED_VALUE |
| `free_cash_flow_for_shl_keur` | `excel_oborovo_financial_truth.json` CF section | SOURCE_RAW_CACHED_VALUE |

### Cash Vector Independence

`free_cash_flow_for_shl_keur` is from the CF sheet, upstream of SHL service:

```
free_cash_flow_for_junior = fcf_for_banks + senior_debt_service
free_cash_flow_for_shl    = free_cash_flow_for_junior    (dividends = 0 throughout)
```

Verified: DS[1] = 2575.00 + (−2239.13) = 335.87 ✓; DS[25] = 2992.52 + (−1688.73) = 1303.79 ✓

Production clean code must NOT load this vector; it is a test driver only.

---

## 5. The Natural Waterfall Formula

```
gross          = opening × annual_rate × day_count_fraction
cash_interest  = min(cash_available, gross)
capitalised    = gross - cash_interest
remaining_cash = cash_available - cash_interest
principal      = max(0, min(remaining_cash, opening + capitalised))
closing        = opening + capitalised - principal
```

| Mode | Condition | Outcome |
|---|---|---|
| Full capitalisation | cash_available = 0 | cash_interest = 0, capitalised = gross, principal = 0 |
| Partial (mixed) | 0 < cash_available < gross | cash_interest < gross, capitalised > 0, principal = 0 |
| Full cash + sweep | cash_available >= gross | cash_interest = gross, capitalised = 0, principal > 0 |

No mode enum. No mode dispatch.

### Sweep Provenance

**Status**: `SOURCE_VECTOR_DERIVED_AND_FULL_HORIZON_RECONCILED`

Sweep triggers when `cash_available > gross` (period interest), not annual threshold.
Identity holds for all 40 periods with zero exceptions:
- DS[24]: cash=343.20 < gross=1034.64 → no sweep ✓
- DS[25]: cash=1303.79 > gross=1079.68 → sweep ✓

No direct workbook formula text for the sweep row is committed. Label is honest.

---

## 6. Construction Semantics

Construction is handled by the **C3B3D1 primitive** (`financial_engine.shl.engine.compute_shl_period`):

```python
compute_shl_period(
    opening_balance_keur=0.0,     # opening = 0 (loan not yet drawn)
    drawdown_keur=draw,           # 14620.773894815633 kEUR
    day_count_fraction=1.0,       # DCF = 1.0 (arithmetic-implied)
    annual_rate=0.08,
    payment_mode=ShlInterestPaymentMode.PIK,
    scheduled_principal_keur=0.0,
    period_index=0,
)
```

`gross = (opening + draw) × rate × 1.0 = 14620.773895 × 0.08 = 1169.661912 kEUR`

The operating waterfall function does **NOT** accept a drawdown parameter and does NOT
model construction. Passing `draw` as `opening` is semantically incorrect — the
opening is zero before the draw.

**Construction DCF = 1.0** is arithmetic-implied (`gross / (draw × rate) = 1.0`). The
exact calendar-date proof is unresolved due to a potential 2-day gap at the
construction/operating seam (cf.bop_date[0]=2029-06-29, cf.eop_date[0]=2030-06-30,
IL DS[1].start=2030-07-01). DCF=1.0 implies approximately a full year (365 days at
actual/365) but is not proven from committed construction dates.

---

## 7. Implementation

**File**: `financial_engine/shl/waterfall.py`

**Functions**:
- `compute_shl_dcf_actual_365_inclusive(period_start, period_end) → float`
- `compute_shl_waterfall_period(opening_balance_keur, annual_rate, day_count_fraction, cash_available_for_shl_keur, period_index=0) → ShlWaterfallPeriodResult`

**Result dataclass**: `ShlWaterfallPeriodResult` (frozen, 8 fields)

### Governance

- No mode enum (`ShlInterestPaymentMode` not imported)
- No mode dispatch
- No hardcoded DS25, DS40, or project-specific boundaries
- 13,547.2 not in waterfall.py
- No imports from `app`, `finco_core`, or any production runtime

---

## 8. Parity Results (Independent DCF)

| Metric | Value |
|---|---|
| DCF driver | `((end - start).days + 1) / 365` from committed period dates |
| DCF is circular | No — reads only dates, not gross interest |
| Max gross delta | 2.27e-13 kEUR |
| Max cash-interest delta | 2.27e-13 kEUR |
| Max PIK delta | 1.14e-13 kEUR |
| Max principal delta | 2.27e-13 kEUR |
| Max closing delta | 0.00e+00 kEUR |
| DS[40] final closing | 0.000000 kEUR |
| First sweep period | DS[25] (discovered, not asserted) |

**Verdict**: `C3B3D2B0_CLEAN_SHL_FORMULA_PARITY_PROVEN`

---

## 9. Test Suite

**File**: `tests/test_stage_c3b3d2b0_clean_shl_formula_parity.py`
**Count**: 80 tests, all passing

| Class | Tests | Description |
|---|---|---|
| TestA_DerivedDcfNotUsedAsParity | 4 | Circular DCF proved invalid; independent DCF matches to machine epsilon |
| TestB_SourceDcfFormulaDocumented | 4 | Convention label, formula, denominator, error explanation in fixture |
| TestC_DcfComputedIndependently | 5 | Function signature, no gross reads, DS[1] value |
| TestD_Ds1IndependentDcfValue | 4 | 183 vs 184 days; inclusive=correct, exclusive=wrong |
| TestE_LeapYearPeriods | 10 | Denominator 365 fixed; 5 leap-year periods proven |
| TestF_FirstPeriodTreatment | 2 | DS[1] uniform formula, no special stub |
| TestG_FinalPeriodTreatment | 2 | DS[40] from dates; natural zero closing |
| TestH_RecursiveGrossParityIndependentDcf | 1 | Max gross delta < 1e-6 kEUR |
| TestI_RecursiveCashInterestParity | 1 | Max cash-interest delta < 1e-6 kEUR |
| TestJ_RecursivePikParity | 1 | Max PIK delta < 1e-6 kEUR |
| TestK_RecursivePrincipalParity | 1 | Max principal delta < 1e-6 kEUR |
| TestL_RecursiveClosingParity | 2 | Max closing delta < 1e-6 kEUR; DS[40] = 0 |
| TestM_ConstructionOpening0PlusDraw | 5 | opening=0, drawdown=draw; C3B3D1 engine |
| TestN_CashVectorIndependence | 6 | CF section source; upstream of SHL service |
| TestO_SweepProvenanceClassification | 2 | Honest label; identity holds all 40 periods |
| TestP_No13547InCleanCalculation | 3 | No 13547 in waterfall code or test inputs |
| TestQ_NoHardcodedBoundaries | 3 | No DS25/DS40 in code; boundary discovered |
| TestR_NoSourceVectorProductionReads | 3 | No fixture/finco_core imports |
| TestS_ZeroRuntimeDrift | 3 | No production import; factory unchanged; D1 engine intact |
| TestGovFunctionSignature | 3 | No mode param, no mode enum import, no app import |
| TestGovRollForward | 6 | closing = opening + pik - principal |
| TestGovInputValidation | 7 | Raises on bad inputs, DCF end before start |
| TestGovResultDataclass | 3 | Frozen, shl_service identity, correct type |

---

## 10. Unresolved Items (Deferred to C3B3D2B1+)

| Item | Status |
|---|---|
| CONSTRUCTION_DATE_CONVENTION_UNRESOLVED | DCF=1.0 arithmetic-implied; exact calendar interval unconfirmed |
| SWEEP_FORMULA_PROVENANCE | SOURCE_VECTOR_DERIVED_AND_FULL_HORIZON_RECONCILED (no committed formula text) |
| CASH_VECTOR_NOT_WIRED_TO_RUNTIME | Test driver only; not wired to production FCF waterfall |
| TAX_CFADS_SENIOR_DEBT_NOT_WIRED | Full fixed-point loop deferred to C3B3D2B1+ |

---

## 11. D2B1 Prerequisites

A. Wire `free_cash_flow_for_shl_keur` to production FCF waterfall output (not from fixture).

B. Implement `compute_shl_schedule(periods: list[...]) → tuple[ShlWaterfallPeriodResult, ...]`
   that chains periods recursively from production-derived cash vector.

C. Prove round-trip parity with D2A fixture using production-derived cash vector.

D. Resolve construction period date convention (is DCF=1.0 from exact 365-day interval?
   Investigate 2-day gap at seam).

E. Do NOT wire Tax/CFADS until D2B2+.
