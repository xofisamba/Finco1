# Phase 6: R67 Full Calibration Validation

## Branch
`phase6-r67-full-calibration-validation`

## HEAD
`47b2ae2` (PR #69 merge commit — baseline for this branch)

## What This Branch Does

Performs structured R67 calibration analysis after the previous branch (`phase6-tax-bridge-consumes-r35-sources`) wired TUHO R35 source ownership:
- Book/tax depreciation ledger (book 72,994 kEUR / tax 70,692 kEUR / 60 semiannual periods)
- SHL gross-accrued Excel R27 fixture
- R34 fiscal reintegration (fixture-backed)
- Croatia 10-period vintage loss engine

**This branch does not change production code.** It creates diagnostic tests and documentation to explain the remaining R67 residual.

## R67 Comparison Table

| | Value (kEUR) | Notes |
|---|---:|---|
| **Excel R67 target** | **-38,240.9** | Sum of `P&L.corporate_income_tax_keur` in Excel, years 13–30 only |
| Python flag OFF R67 | -39,639.7 | Legacy runtime, all 60 periods |
| **Python flag ON R67** | **-45,825.2** | Tax bridge ON, all 60 periods |
| **Residual** | **-7,584.3** | Python flag ON minus Excel target |

### Key Structural Finding: Timing Mismatch

Excel R67 is non-zero **only from year 13 onward** (periods 25–59, semiannual half-years 2, 4, 6, …). Years 1–12 have **zero** tax in Excel.

Python flag ON computes R67 for **all 30 years**, including years 1–12 where Excel shows 0:

| Segment | Python R67 | Excel R67 | Delta |
|---|---:|---:|---:|
| Years 1–12 (P0–23) | -2,312.9 | 0.0 | -2,312.9 |
| Years 13–30 (P24–59) | -43,512.4 | -38,240.9 | -5,271.4 |
| **Total** | **-45,825.2** | **-38,240.9** | **-7,584.3** |

This is the **primary structural driver** of the residual. The years 1–12 over-count (years where no corporate tax is owed in Excel) accounts for ~-2,313 kEUR of the -7,584 kEUR residual. The remaining ~-5,271 kEUR is in years 13–30 and requires deeper investigation.

## R35 / R34 / Loss Bridge Summary

| Item | Flag OFF (kEUR) | Flag ON (kEUR) | Delta (kEUR) |
|---|---:|---:|---:|
| R35 total | 245,276.4 | 254,640.8 | +9,364.4 |
| R34 fixture | — | -9,242.7 | — |
| Total CIT accrual | 39,649.8 | 45,835.3 | +6,185.6 |
| Loss carryforward used | — | 0.0 | — |

**Loss engine note:** R35 is positive in **all 60 operating periods** for TUHO flag ON. The Croatia 10-period vintage loss engine is running but never triggers a loss offset (no negative taxable income in any period). Loss buckets remain all zeros throughout the model life.

## Residual Decomposition

| Driver | Est. Contribution | Notes |
|---|---:|---|
| Years 1–12 tax timing (Excel=0, Python>0) | ~-2,313 kEUR | Primary structural cause |
| Years 13–30 residual | ~-5,271 kEUR | Secondary; requires investigation |
| **Total residual** | **~-7,584 kEUR** | |

### Years 1–12 Residual (-2,313 kEUR)
Excel has zero corporate tax in years 1–12 (likely due to IDC capitalization, construction-period treatment, or a tax holiday/exemption period in the Excel model). Python computes tax for all 30 years including the pre-operational period.

**Hypothesis:** The Excel model applies a construction-period tax exemption or capitalizes all interest/depreciation during construction, only starting CIT accrual in year 13. Python's tax bridge does not replicate this construction-period tax treatment.

### Years 13–30 Residual (-5,271 kEUR)
Within years 13–30, Python R67 (-43,512 kEUR) vs Excel R67 (-38,241 kEUR) — delta -5,271 kEUR. Possible drivers:
1. **EBITDA source:** Python uses waterfall-engine EBITDA; Excel uses a different EBITDA construction (possibly includes adjustments not in the waterfall model)
2. **Senior interest:** Python uses waterfall debt schedule; Excel may have a different senior debt schedule or interest calculation
3. **SHL gross-accrued + ATAD interaction:** The gross-accrued fixture changes the ATAD deductible interest base vs formula
4. **Tax rate or loss interaction differences**

## R99 Readiness Status
**BLOCKED** — R99/R102 remain audit-only. `fcf_for_shl_keur = 0.0` across all periods. No SHL FCF runtime opt-in.

## Root-Cause Hypothesis

The -7,584 kEUR residual is best explained by two compounding effects:

1. **Construction-period tax exemption (years 1–12):** Excel shows zero corporate tax for years 1–12. Python does not model a construction-period tax exemption. This alone accounts for ~-2,313 kEUR of the residual.

2. **EBITDA + interest source differences (years 13–30):** Python uses waterfall-engine EBITDA and debt schedules; Excel uses fixture-extracted values. The ~-5,271 kEUR gap in years 13–30 suggests the waterfall EBITDA or senior interest differs from Excel by enough to shift R35 upward and increase CIT.

## Recommended Next Branch: `phase6-cit-h2-annual-trigger`

**Rationale:** The construction-period CIT exemption (years 1–12 showing 0 in Excel) is a recurring structural pattern that affects R67 directly. The next branch should:

1. Investigate whether the TUHO Excel model has a construction-period tax holiday/exemption
2. Identify if an explicit flag or parameter controls when CIT accrual starts
3. Optionally wire an H2 annual trigger to match the observed Excel timing (start paying CIT in year 13, not year 1)

If evidence suggests the years 13–30 residual is primarily driven by EBITDA or senior interest differences, a narrower branch (`phase6-ebitda-source-bridge` or `phase6-senior-interest-source-bridge`) may be more appropriate before the H2 trigger work.

## Tests

| Test | Status |
|------|--------|
| `tests/test_r67_full_calibration_validation.py` (13 new) | ✅ 13/13 passed |
| `tests/test_tax_bridge_consumes_r35_sources.py` (9) | ✅ 9/9 passed |
| `tests/test_loss_engine_runtime_flag.py` (11) | ✅ 11/11 passed |
| `tests/test_tax_bridge_runtime_flag.py` (8) | ✅ 8/8 passed |
| `tests/test_r35_full_validation.py` (7) | ✅ 7/7 passed |
| `tests/test_shl_gross_interest_pnl_bridge.py` (9) | ✅ 9/9 passed |
| `tests/test_book_depreciation_pnl_bridge.py` (6) | ✅ 6/6 passed |
| `tests/test_financial_statements_excel_export.py` (5) | ✅ 5/5 passed |
| `tests/test_shl_fcf_waterfall_runtime_flag.py` (10) | ✅ 10/10 passed |
| **Total** | **78/78 passed** |

## Merge Recommendation

**READY FOR INFORMATIONAL MERGE.** This branch is diagnostic-only — no production code changes. It documents the R67 residual structure and provides a test suite for the next calibration branch.

Key validations:
1. ✅ Default behavior unchanged (TUHO/Oborovo flag OFF bit-identical)
2. ✅ TUHO flag ON R67 documented (-45,825 kEUR vs Excel -38,241 kEUR, residual -7,584 kEUR)
3. ✅ Excel R67 target explicitly captured (-38,241 kEUR)
4. ✅ Structural timing mismatch identified (years 1–12: Python > 0, Excel = 0)
5. ✅ Loss engine is no-op (R35 always positive)
6. ✅ R99/R102 remain audit-only; no SHL FCF opt-in
7. ✅ Oborovo flag ON remains guarded
8. ✅ All 78 tests pass