# C3B3D2B6 Base Performance + Post-Senior Cash Reconciliation

Classification: `BASE_CASE_RECONCILIATION_DIAGNOSTIC_ONLY`

First material divergence (>0.1): period 1 `Taxable Income` delta 72.099596013762 kEUR

## DS1 Bridge

- `excel_cf79_fcf_for_banks_keur`: 2575.0034247825092
- `finco_base_cfads_keur`: 2575.0034247825092
- `excel_cf80_signed_senior_debt_service_keur`: -2239.133412854356
- `finco_senior_debt_service_keur`: 2239.133412854356
- `excel_cf112_fcf_shl_keur`: 335.8700119281534
- `finco_cash_available_for_shl_keur`: 335.8700119281534

## Max Deltas By Line

- `Production`: period 45 delta -2.1827872842550278e-11
- `Price`: period 46 delta -4.263256414560601e-14
- `Revenue`: period 46 delta -2.7284841053187847e-12
- `OPEX`: period 48 delta 9.094947017729282e-13
- `EBITDA`: period 5 delta -9.094947017729282e-13
- `Book Dep`: period 1 delta 2.8193485150040942e-05
- `Senior Interest`: period 28 delta -43.23513268617058
- `SHL Interest`: period 28 delta 61.15245481680654
- `EBT`: period 28 delta -17.917332790431146
- `Fiscal Reintegration`: period 28 delta 61.15245481680654
- `Taxable Income`: period 40 delta 706.7075889497728
- `Loss Utilisation`: period 8 delta 380.25083642342315
- `CIT`: period 60 delta -354.4219621905736
- `Cash Tax`: period 59 delta 706.5567709778473
- `Base CFADS`: period 59 delta -709.3217983002546
- `Senior Principal`: period 28 delta -1464.203774122742
- `Senior Debt Service`: period 28 delta -1507.4389068089126
- `Senior Closing`: period 27 delta -1464.203774122742
- `Post-Senior Cash`: period 28 delta 1809.0567303556127
- `Cash Available for SHL`: period 28 delta 1809.0567303556127

## Boundary Notes
- Base production, price, revenue, OPEX and EBITDA are source-parity at numerical precision after the generic calendar fixes.
- DS1 Base CFADS, Senior Debt Service, Post-Senior Cash and Cash Available for SHL match source.
- The first remaining material causal boundary is tax/taxable-income compatibility, not SHL formula or post-senior cash assembly.
- Source fixtures are used only for diagnostics/tests and are not runtime inputs.

## Local Regression Notes
- `tests/test_stage_c3b3d2b6_base_post_senior_cash_parity.py` + `tests/test_stage_c3b3d2b5_shl_fixed_point_integration.py`: 36 passed locally.
- Broader historical B3/B4/C3B3A/C3B1/Phase2B band was run for visibility: 634 passed, 45 failed. The failures are stale period-axis expectations (old two-construction-period / clean index 2..29 convention), pre-existing tax baseline/governance drift, and Windows `rg` subprocess availability in legacy tests. They are not hidden in the dedicated B6 workflow because updating those suites comprehensively is outside the B6 cash-seam slice.
