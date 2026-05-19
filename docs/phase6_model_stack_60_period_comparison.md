# Phase 6 — 60-Period Model Stack Comparison

## Purpose

Human-readable Excel vs Python comparison workbook for TUHO Wind 1 across all 60 operating periods (Y1-H1 through Y30-H2). Diagnostic / reporting only — no production runtime changes, no formula changes, no parity forcing.

## Source Files

- **Excel workbook:** `20260330_TUHO_BP.xlsm` (TUHO Excel reference model)
- **Python run:** TUHO flag-on runtime (`use_tax_bridge_engine=True`, `cit_cash_tax_start_operating_index=25`)
- **Excel fixture:** `tests/fixtures/excel_tuho_full_model_extract.json`

## Python Run Configuration

```python
tuho = create_default_tuho_wind1()
tuho = replace(tuho,
    info=replace(tuho.info, use_tax_bridge_engine=True),
    tax=replace(tuho.tax, cit_cash_tax_start_operating_index=25),
)
```

## Period Convention

- 60 operating periods: P01 = Y01-H1 ... P60 = Y30-H2
- 6-month (semestrial) periods
- Total column at far right (sum of P01-P60)

## Sheets Generated

1. **Summary** — aggregate totals, max deltas, status per metric
2. **Revenue** — electricity, CO2, balancing cost, net revenue (PR #90 split fields)
3. **OPEX** — total operating expenses
4. **EBITDA** — earnings before interest, tax, depreciation, amortization
5. **Free Cash Flow** — CF for banks, distribution, SHL (BLOCKED)
6. **Depreciation** — book, unlevered, tax (diagnostic)
7. **Senior Debt** — interest, principal, balance, DSCR
8. **SHL** — gross-accrued, balance, PIK, interest (CANDIDATE driver)
9. **CIT Tax** — R35/R41/R43/R67, loss carryforward, fiscal reintegration
10. **Delta Flags** — material differences sorted by absolute delta
11. **Source Mapping** — Excel/Python field mapping with confidence ratings

## Metrics Included

### Revenue (PR #90 split fields)
| Metric | Excel Source | Python Source | Confidence |
|--------|-------------|---------------|------------|
| Electricity Revenue | N/A | decomposition.electricity_revenue_keur | unmapped |
| CO2 Certificate Revenue | N/A | decomposition.co2_certificate_revenue_keur | unmapped |
| Balancing Cost (positive) | N/A | decomposition.balancing_cost_keur | unmapped |
| Net Revenue After Balancing | P&L!total_revenues_keur | result.periods[i].revenue_keur | exact |
| Net Revenue (decomposition) | N/A | decomposition.net_revenue_after_balancing_keur | unmapped |
| EBITDA | CF!ebitda_keur | result.periods[i].ebitda_keur | exact |
| Generation (MWh) | N/A | result.periods[i].generation_mwh | unmapped |

### OPEX
| Metric | Excel Source | Python Source | Confidence |
|--------|-------------|---------------|------------|
| Total OPEX | CF!operating_expenses_after_bank_tax_keur | result.periods[i].opex_keur | exact |

### EBITDA
| Metric | Excel Source | Python Source | Confidence |
|--------|-------------|---------------|------------|
| EBITDA | CF!ebitda_keur | result.periods[i].ebitda_keur | exact |

### Free Cash Flow
| Metric | Excel Source | Python Source | Confidence |
|--------|-------------|---------------|------------|
| FCF for Banks | CF!free_cash_flow_for_banks_keur | result.periods[i].cf_after_tax_keur | approximate |
| FCF for Distribution | CF!free_cash_flow_for_distribution_keur | result.periods[i].r98_distribution_account_keur | approximate |
| FCF for SHL [BLOCKED] | N/A | result.periods[i].r102_fcf_for_shl_keur | unmapped |

### Depreciation
| Metric | Excel Source | Python Source | Confidence |
|--------|-------------|---------------|------------|
| Book Depreciation | Dep!depreciation_keur | result.periods[i].depreciation_keur | exact |
| Unlevered Depreciation | Dep!unlevered_depreciation_keur | N/A | unmapped |
| Tax Depreciation (audit) | N/A | result.periods[i].tax_depreciation_audit_keur | unmapped |

### Senior Debt
| Metric | Excel Source | Python Source | Confidence |
|--------|-------------|---------------|------------|
| Senior Interest | DS!senior_net_interest_keur | result.periods[i].interest_senior_keur | exact |
| Senior Principal | DS!senior_principal_keur | result.periods[i].senior_principal_keur | exact |
| Senior Closing Balance | N/A | result.periods[i].senior_balance_keur | unmapped |
| Total Senior Debt Service | N/A | result.periods[i].senior_ds_keur | unmapped |
| DSCR | N/A | result.periods[i].dscr | unmapped |

### SHL
| Metric | Excel Source | Python Source | Confidence |
|--------|-------------|---------------|------------|
| SHL Gross Accrued Interest [CANDIDATE] | SHL schedule!gross_interest | result.periods[i].shl_gross_accrued_interest_keur | approximate |
| SHL Closing Balance | SHL schedule!closing | result.periods[i].shl_balance_keur | approximate |
| SHL PIK / Capitalised Interest | SHL schedule!capitalized_interest | result.periods[i].shl_pik_keur | approximate |
| SHL Paid Interest | N/A | result.periods[i].shl_interest_keur | unmapped |

### CIT Tax
| Metric | Excel Source | Python Source | Confidence |
|--------|-------------|---------------|------------|
| R35 Taxable Income (flag-on) | P&L!taxable_income_keur | result.periods[i].taxable_income_before_losses_audit_keur | exact |
| R41 Taxable Profit After Losses | P&L!taxable_income_keur (proxy) | result.periods[i].taxable_profit_after_losses_audit_keur | approximate |
| R43 CIT Accrual | P&L!corporate_income_tax_keur | result.periods[i].tax_keur | approximate |
| R67 Cash Tax [DIAGNOSTIC] | N/A | result.periods[i].r67_excel_style_cash_tax_diagnostic_keur | unmapped |
| CIT Accrual Audit | N/A | result.periods[i].cit_accrual_audit_keur | unmapped |
| Tax Loss Opening (audit) | N/A | result.periods[i].tax_loss_opening_audit_keur | unmapped |
| Tax Loss Closing (audit) | N/A | result.periods[i].tax_loss_closing_audit_keur | unmapped |
| Fiscal Reintegration (audit) | N/A | result.periods[i].fiscal_reintegration_audit_keur | unmapped |

## Unmapped Metrics

17 metrics are unmapped (confidence=unmapped). These include:
- PR #90 revenue split fields (electricity_revenue_keur, co2_certificate_revenue_keur, balancing_cost_keur, etc.)
- Senior debt closing balance, DSCR, debt service total
- SHL paid interest
- Tax depreciation audit, loss carryforward, fiscal reintegration
- R67 cash tax diagnostic
- Unlevered depreciation

## Known Limitations

1. **Revenue split fields** (electricity, CO2, balancing) are unmapped in Excel — available only in Python via `revenue_decomposition_schedule()`. The Excel fixture does not contain separate rows for these components.

2. **R99/R102 are BLOCKED** — `r99_fcf_for_distribution_keur` and `r102_fcf_for_shl_keur` are audit-only fields, not runtime drivers. They are presented in the workbook for visibility but must not be used as runtime sources.

3. **SHL gross-accrued interest** is a candidate driver — source verification pending. Treatment may differ between Excel and Python.

4. **Delta flags show 1,181 material differences** — many periods have deltas > 50 kEUR. This reflects the construction vs operations timing differences between Excel and Python.

5. **DSCR unmapped** — Excel does not surface period-level DSCR in the fixture; Python computes it per period.

## Status Thresholds

- **PASS:** abs total delta ≤ 100 kEUR AND max period delta ≤ 25 kEUR
- **MINOR:** abs total delta ≤ 500 kEUR
- **MATERIAL:** abs total delta > 500 kEUR
- **BLOCKED:** R99/R102, SHL FCF runtime source, known blocked items
- **UNMAPPED:** source not available in Excel fixture
- **APPROXIMATE:** source basis differs but comparison is meaningful

## Top material delta categories

> Note: Full delta flag list in Delta Flags sheet of the workbook.

Top contributors to period-level variance:
1. Revenue (PPA period transitions) — Excel P&L total vs Python revenue decomposition
2. Senior debt drawdown — construction period timing differences
3. SHL gross-accrued — PIK capitalization timing
4. Depreciation — straight-line (Python) vs accelerated (Excel) in early periods
5. R67 cash tax — H2-only vs H1+H2 annual CIT timing

## Modules apparently within tolerance under this report basis

- Senior interest
- Senior principal repayment
- EBITDA / total OPEX, subject to source-basis caveats (prior model-stack comparison flagged Book Dep R30 and OPEX as material under a different/source-expanded basis)

**Known caveats:**
- Prior model-stack comparison flagged Book Dep R30 and OPEX as material under a different source basis
- This workbook should be used for visibility, not final parity certification
- SHL gross-accrued is a candidate driver — source verification pending

## Modules Outside Tolerance

- SHL gross-accrued interest (candidate driver, source verification pending)
- SHL closing balance (PIK timing difference)
- R67 cash tax (diagnostic, Excel fixture not available)
- Unlevered depreciation (not computed in Python)

## R99/R102 BLOCKED Statement

**R99** (`r99_fcf_for_distribution_keur`) and **R102** (`r102_fcf_for_shl_keur`) are audit-only fields. They are presented in this workbook for visibility purposes only. They must NOT be used as runtime cash routing sources, SHL service drivers, or distribution triggers. The Phase 6 R99/R102 blocks remain in effect.

## Recommended Next Branch

`phase7-model-stack-blueprint` — canonical model-stack blueprint, derived from this 60-period comparison workbook. Evidence base for Phase 7.

SHL/senior consolidation may be considered later as a Phase 7/8 workstream, but the immediate next step is `phase7-model-stack-blueprint`.

## Generated Outputs

- `reports/phase6_model_stack_60_period_comparison.xlsx` — 11-sheet comparison workbook
- `reports/phase6_model_stack_60_period_comparison_long.csv` — long-format CSV (313 KB)
- `reports/phase6_model_stack_60_period_comparison_wide.csv` — wide-format CSV (57 KB)
- `scripts/export_phase6_model_stack_60_period_comparison.py` — export script

## Validation

All existing tests pass with no production/runtime changes:
```
tests/test_revenue_co2_balancing_split.py   26 passed
tests/test_revenue.py                        16 passed
tests/test_project_factories.py               18 passed
tests/test_depreciation_category_capex_extraction.py  12 passed
tests/test_depreciation_engine_offline.py     3 passed
tests/test_loss_engine_runtime_flag.py        9 passed
tests/test_tax_bridge_consumes_r35_sources.py  6 passed
tests/test_r67_full_calibration_validation.py 27 passed
tests/test_r67_yrs13to30_residual.py         26 passed
tests/test_cit_h2_annual_trigger.py          10 passed
```

**Total: 147 passed, 1 xfailed**

**Generated outputs (not committed to repo):**
- `reports/phase6_model_stack_60_period_comparison.xlsx` — 11-sheet comparison workbook (64 KB)
- `reports/phase6_model_stack_60_period_comparison_long.csv` — long-format CSV (313 KB)
- `reports/phase6_model_stack_60_period_comparison_wide.csv` — wide-format CSV (57 KB)
- `scripts/export_phase6_model_stack_60_period_comparison.py` — export script