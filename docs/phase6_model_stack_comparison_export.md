# Phase 6 — Model Stack Comparison Export

## Branch
`phase6-model-stack-comparison-export`

## Status
**Diagnostic/reporting only. No production code changes. No runtime behavior changes.**

---

## 1. What This Branch Does

Exports a period-by-period comparison workbook (Excel + CSV) comparing TUHO Wind 1 Excel model outputs against Python runtime (flag-on) across the full model stack.

Creates:
- `scripts/export_phase6_model_stack_comparison.py` — report generator
- `reports/phase6_model_stack_comparison.xlsx` — multi-sheet Excel comparison
- `reports/phase6_model_stack_comparison_long.csv` — long-form CSV (one row per period per metric)
- `reports/phase6_model_stack_comparison_wide.csv` — wide-form CSV (periods as columns)
- `docs/phase6_model_stack_comparison_export.md` — this file

---

## 2. What This Branch Does NOT Do

- ❌ No production runtime changes
- ❌ No formula changes
- ❌ No waterfall changes
- ❌ No factory opt-in
- ❌ No R99/R102 promotion
- ❌ No SHL FCF runtime source
- ❌ No scalar plugs
- ❌ No residual adjustments
- ❌ Oborovo remains guarded
- ❌ No changes to `app/waterfall_core.py`, `app/waterfall_runner.py`, `app/project_factories.py`

---

## 3. Source Workbook

- **TUHO Excel model:** `20260330_TUHO_BP.xlsm`
- **Extraction fixture:** `tests/fixtures/excel_tuho_full_model_extract.json`
- **SHA256:** `780779eba4278ccc2b8546a9411ccee24917d388f411ba60c88aa342cb5c727a`
- **Periods:** 60 semiannual periods (Y01 H1 through Y30 H2)
- **Coverage:** operating periods (Y13-Y30) and construction-period data

---

## 4. Python Run Configuration

```
Project: TUHO-WIND-1
Flag: use_tax_bridge_engine=True
cit_cash_tax_start_operating_index=25 (first non-zero R67 at Y13 H2)
Model: flag-on (tax bridge active)
```

Same configuration as `tests.test_r67_yrs13to30_residual._tuho_flag_on_project()`.

---

## 5. Included Metrics

| Category | Metric | Excel Source | Python Source | Confidence |
|----------|--------|--------------|---------------|-------------|
| Revenue | Electricity Revenue | P&L!total_revenues_keur | .revenue_keur | exact |
| OPEX | Total OPEX | CF!operating_expenses_after_bank_tax_keur | .opex_keur | exact |
| EBITDA | EBITDA | CF!ebitda_keur | .ebitda_keur | exact |
| Free Cash Flow | FCF for Banks | CF!free_cash_flow_for_banks_keur | .cf_after_tax_keur | approximate |
| Free Cash Flow | FCF for Distribution | CF!free_cash_flow_for_distribution_keur | .r98_distribution_account_keur | approximate |
| Depreciation | Book Depreciation | Dep!depreciation_keur | .depreciation_keur | exact |
| Depreciation | Unlevered Depreciation | Dep!unlevered_depreciation_keur | N/A | unmapped |
| Senior Debt | Senior Interest | DS!senior_net_interest_keur | .interest_senior_keur | exact |
| Senior Debt | Senior Principal Repayment | DS!senior_principal_keur | .senior_principal_keur | exact |
| Senior Debt | Senior Closing Balance | DS!senior_principal_keur (cumulative) | .senior_balance_keur | approximate |
| SHL | SHL Gross Accrued Interest | SHL schedule!gross_interest | .shl_gross_accrued_interest_keur | approximate |
| SHL | SHL Closing Balance | SHL schedule!closing | .shl_balance_keur | approximate |
| SHL | SHL PIK / Capitalised Interest | SHL schedule!capitalized_interest | .shl_pik_keur | approximate |
| CIT / Tax | Taxable Income / R35 | P&L!taxable_income_keur | .taxable_income_before_losses_audit_keur | exact |
| CIT / Tax | Taxable Profit After Losses / R41 | P&L!taxable_income_keur (proxy) | .taxable_income_after_losses_keur | approximate |
| CIT / Tax | CIT Accrual / R43 | P&L!corporate_income_tax_keur | .corporate_tax_accrual_keur | approximate |
| CIT / Tax | Cash Tax / R67 | N/A | .r67_excel_style_cash_tax_diagnostic_keur | unmapped |
| CIT / Tax | R99 FCF for Distribution | N/A | .r99_fcf_for_distribution_keur | unmapped (audit-only) |
| CIT / Tax | R102 FCF for SHL | N/A | .r102_fcf_for_shl_keur | unmapped (audit-only) |

---

## 6. Unmapped Metrics

- **Unlevered depreciation:** Python does not compute separately
- **R67 cash tax:** Not in Excel fixture; use test_r67_yrs13to30_residual fixture for Python R67 values
- **R99/R102:** Audit-only fields, blocked in runtime; not comparable to Excel

---

## 7. Known Limitations

1. **Excel CIT includes construction-period tax** while Python flag-on correctly defers CIT during construction. Direct comparison of CIT accrual rows will show large deltas in Y01-Y12 that are expected.

2. **SHL gross-accrued** is a candidate driver (see `phase6-r67-residual-driver-recheck`). The Excel and Python treatments may differ — this comparison surface helps identify the gap.

3. **FCF for Banks** uses Python `cf_after_tax_keur` as proxy for Excel `CF.free_cash_flow_for_banks_keur` — exact mapping not confirmed.

4. **Senior closing balance** computed as running cumulative from opening minus principal — Excel fixture does not contain explicit closing balance column.

5. **R41 proxy:** Excel fixture does not have R41 (taxable profit after losses); P&L!taxable_income_keur is used as proxy, which is pre-loss and therefore different from Python R41.

6. **Unlevered depreciation** is not computed in Python — marked as UNMAPPED.

7. **No scalar plugs** applied — comparison is unaudited; deltas reflect actual model differences.

---

## 8. Top Findings

See `Delta Flags` sheet in the Excel workbook. Summary status per category:

| Category | Status | Notes |
|----------|--------|-------|
| Revenue | See workbook | Depends on electricity price assumptions |
| OPEX | See workbook | Depends on Excel cost structure |
| EBITDA | See workbook | Net of revenue and OPEX |
| Depreciation | See workbook | Dep R30 near-parity ±3.13 kEUR/period max; leap_frac convention difference |
| Senior Debt | See workbook | May be partially calibrated / not yet calibrated |
| SHL | See workbook | SHL gross-accrued is candidate driver for residual |
| CIT / Tax | See workbook | R67 residual ~+2,078 kEUR first-order estimate; gates FAIL |

---

## 9. R99/R102 BLOCKED Statement

**R99 and R102 are audit-only fields, BLOCKED in this comparison export.**

- `.r99_fcf_for_distribution_keur` and `.r102_fcf_for_shl_keur` are labeled `[AUDIT ONLY]`
- These fields must NOT be presented as runtime drivers
- R99 design requires: useful-life + loss-window canonical decisions + residual recheck + external sign-off

---

## 10. Recommended Next Branch

**`phase6-tax-residual-acceptance-review`** — to decide whether to accept the ~+2,078 kEUR first-order residual as known consequence of correct policy (requires external sign-off) or run a narrow source verification branch.

---

## 11. Usage

```bash
# Generate comparison reports
python scripts/export_phase6_model_stack_comparison.py

# Output files:
#   reports/phase6_model_stack_comparison.xlsx
#   reports/phase6_model_stack_comparison_long.csv
#   reports/phase6_model_stack_comparison_wide.csv
```

---

## 12. Tests

No new tests in this branch. Existing suites confirm no regressions. See:
- `tests/test_depreciation_category_capex_extraction.py`
- `tests/test_depreciation_engine_offline.py`
- `tests/test_loss_engine_runtime_flag.py`
- `tests/test_tax_bridge_consumes_r35_sources.py`
- `tests/test_r67_full_calibration_validation.py`
- `tests/test_r67_yrs13to30_residual.py`
- `tests/test_cit_h2_annual_trigger.py`

**87 passed, 1 xfailed** (combined suite, unchanged)