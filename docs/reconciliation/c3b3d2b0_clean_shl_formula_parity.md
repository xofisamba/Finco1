# C3B3D2B0 — Clean SHL Waterfall Formula Parity

**Status**: `C3B3D2B0_CLEAN_SHL_FORMULA_PARITY_PROVEN`
**Branch**: `stage-c3b3d2b0-clean-shl-formula-parity`
**Base**: `b9a7fec27ea2be061d169162d24bd48af3b78120` (main after C3B3D2A squash-merge)
**DO NOT MERGE**: This stage is a proof-of-concept only. Wiring to Tax/CFADS/senior-debt is deferred to C3B3D2B1+.

---

## 1. Scope

C3B3D2B0 proves that a single pure Python function — with no mode enum, no project
dispatch, and no hardcoded period boundaries — reproduces the Excel-sourced Oborovo
SHL schedule to machine epsilon across all 41 periods (DS[0..40]).

**Not in scope**: Tax engine, CFADS, senior-debt fixed point, DSRA, distribution
account, R99, R102, Sponsor, production wiring.

---

## 2. Source Inputs

| Input | Source | Classification |
|---|---|---|
| `shl_draw_keur` | `excel_oborovo_shl_operating_truth.json` workbook_inputs | SOURCE_RAW_CACHED_VALUE (Excel Inputs!D325) |
| `shl_annual_rate` | `excel_oborovo_shl_operating_truth.json` workbook_inputs | SOURCE_RAW_CACHED_VALUE (Excel Inputs!F328 = 0.08) |
| `shl_dcf_derived_actual_365` | D2A fixture per-period field | SOURCE_RAW_DERIVED (= gross / (opening × rate)) |
| `free_cash_flow_for_shl_keur` | `excel_oborovo_financial_truth.json` cf section | SOURCE_RAW_CACHED_VALUE (Excel CF sheet) |

### DCF Source Note

`shl_dcf_derived_actual_365` is used as the test driver day-count fraction. It is
computed from the source Excel gross interest values and NOT from `(end - start).days / 365`.
Using calendar-date-based DCF from IL fixture dates produces a growing error (~3.5 kEUR
at DS[1], ~387 kEUR by DS[40]) due to an unresolved date-convention gap at the
construction/operating seam. The correct date convention for the source workbook is
deferred to C3B3D2B1.

### Cash Vector Independence

`free_cash_flow_for_shl_keur` is taken from the `cf` section of `excel_oborovo_financial_truth.json`,
which is independent of the SHL DS columns. Waterfall chain:

```
free_cash_flow_for_junior = fcf_for_banks + senior_debt_service
free_cash_flow_for_shl    = free_cash_flow_for_junior      (dividends = 0 throughout)
```

Verified: DS[1] = 2575.00 + (-2239.13) = 335.87 ✓; DS[25] = 2992.52 + (-1688.73) = 1303.79 ✓

---

## 3. The Natural Waterfall Formula

```
gross          = opening × annual_rate × day_count_fraction
cash_interest  = min(cash_available, gross)
capitalised    = gross - cash_interest
remaining_cash = cash_available - cash_interest
principal      = max(0, min(remaining_cash, opening + capitalised))
closing        = opening + capitalised - principal
```

This single formula handles all settlement modes without branching on a mode enum:

| Mode | Condition | Outcome |
|---|---|---|
| Full capitalisation | cash_available = 0 | cash_interest = 0, capitalised = gross, principal = 0 |
| Partial (mixed) | 0 < cash_available < gross | cash_interest < gross, capitalised > 0, principal = 0 |
| Full cash + sweep | cash_available >= gross | cash_interest = gross, capitalised = 0, principal > 0 |

### Sweep Condition (Source-Proven)

Sweep triggers when `cash_available > gross` (surplus above period interest), NOT
when `cash_available > opening × annual_rate` (annual threshold as in legacy engine).

- DS[24]: cash=343.20 < gross=1034.64 → no sweep ✓
- DS[25]: cash=1303.79 > gross=1079.68 → sweep ✓

DS25 is discovered from data, not asserted.

---

## 4. Implementation

**File**: `financial_engine/shl/waterfall.py`

**Function**: `compute_shl_waterfall_period(opening_balance_keur, annual_rate, day_count_fraction, cash_available_for_shl_keur, period_index=0) → ShlWaterfallPeriodResult`

**Result dataclass**: `ShlWaterfallPeriodResult` (frozen, 8 fields including `shl_service_keur`)

### Governance

- No mode enum (`ShlInterestPaymentMode` not imported)
- No mode dispatch (no if/elif on payment mode)
- No hardcoded DS25, DS40, or project-specific period boundaries
- 13,547.2 does not appear anywhere in the file
- No imports from `app`, `finco_core`, or any production runtime
- `financial_engine` does NOT import `finco_core.waterfall`

---

## 5. Parity Results

Test driver: `shl_dcf_derived_actual_365` from D2A fixture (not calendar-date DCF).

| Period | Gross delta | Closing delta |
|---|---|---|
| DS[0] construction | < 1e-12 kEUR | 0.00 kEUR |
| DS[1..40] operating (max) | < 2e-13 kEUR | 0.00 kEUR |
| DS[40] final closing | — | 0.000000 kEUR |

**Verdict**: `C3B3D2B0_CLEAN_SHL_FORMULA_PARITY_PROVEN`

---

## 6. Test Suite

**File**: `tests/test_stage_c3b3d2b0_clean_shl_formula_parity.py`
**Count**: 95 tests, all passing

| Class | Description |
|---|---|
| TestA_GovernanceNoModeDispatch | No mode enum, no mode parameter |
| TestB_GovernanceNoHardcodedProjectConstants | No 13547.2, no DS25/DS40, no finco_core/app imports |
| TestC_GovernanceFinancialEngineIsolation | Module-level import isolation check |
| TestD_RollForwardIdentity | closing = opening + capitalised - principal for all periods |
| TestE_GrossInterestFormula | gross = opening × rate × dcf |
| TestF_CashInterestMinFormula | cash_interest = min(cash_available, gross) |
| TestG_SweepCondition | DS24 no sweep, DS25 sweep, boundary discovered from data |
| TestH_ParityConstruction | DS[0] parity to machine epsilon |
| TestI_ParityOperatingSpot | Spot checks DS[1,12,24,25,30,40] |
| TestJ_ParityFullRecursive | 40-period recursive parity, all deltas < 1e-6 kEUR |
| TestK_CashVectorIndependence | CF section source, not DS section |
| TestL_DcfSourceIsD2aFixture | DCF from D2A fixture, not date calculation |
| TestM_InputValidation | Raises on bad inputs |
| TestN_ResultDataclass | Frozen, correct fields, shl_service identity |
| TestO_ZeroRateEdgeCase | Zero rate, zero opening |
| TestP_ExcessCashCappedAtOutstanding | Principal capped, closing non-negative |
| TestQ_RenameCloneGuard | Not a copy of engine.py; uses ShlWaterfallPeriodResult |
| TestR_FixtureProductionImportGuard | waterfall.py does not import test fixtures |
| TestS_FixtureFieldClassifications | SOURCE_RAW labels present in D2A fixture |

---

## 7. Unresolved Items (Deferred to C3B3D2B1+)

| Item | Description |
|---|---|
| DATE_CONVENTION_UNRESOLVED | Calendar-date DCF from IL fixture differs from source DCF. 2-day gap at construction/operating seam (2029-06-29 → 2030-07-01). Correct convention TBD. |
| PARTIAL_CASH_PIK_MODE_NOT_LABELLED | D2B0 result has `pik_interest_keur` field but no payment_mode label; mode inference deferred. |
| CASH_VECTOR_NOT_WIRED_TO_RUNTIME | `free_cash_flow_for_shl_keur` used only as test driver; not wired to production FCF waterfall. |
| TAX_CFADS_SENIOR_DEBT_NOT_WIRED | Full fixed-point loop deferred to C3B3D2B1+. |

---

## 8. D2B1 Prerequisites

To proceed from D2B0 to D2B1:

A. Resolve the date-convention gap: identify what exact DCF formula the source workbook uses for operating periods. Options: actual/365 with a specific period start reference, or 30/360, or something else. The test driver DCF must match production DCF.

B. Implement a `compute_shl_schedule(periods: list[...]) → tuple[ShlWaterfallPeriodResult, ...]` that chains periods recursively, taking cash vector as input.

C. Wire `free_cash_flow_for_shl_keur` to the FCF waterfall output (not from fixture).

D. Prove round-trip parity with D2A fixture using production-derived cash vector.

E. Do NOT wire Tax/CFADS until D2B2+.
