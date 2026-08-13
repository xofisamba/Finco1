# C3B3D2B6 Base Performance + Post-Senior Cash Reconciliation

Classification: `BANK_SIZING_REMAINS_SENIOR_DEBT_QUANTUM_AUTHORITY`

First material divergence (>0.1): period 1 `Senior Interest` delta -57.966168788217 kEUR

## DS1 Bridge

- `excel_cf79_fcf_for_banks_keur`: 2575.0034247825092
- `finco_base_cfads_keur`: 2575.0034247825092
- `excel_senior_interest_keur`: 1303.483281763653
- `finco_senior_interest_keur`: 1245.5171129754356
- `excel_senior_principal_keur`: 935.6501310907029
- `finco_senior_principal_keur`: 834.7261870179893
- `excel_cf80_signed_senior_debt_service_keur`: -2239.133412854356
- `excel_senior_debt_service_positive_keur`: 2239.133412854356
- `finco_senior_debt_service_keur`: 2080.243299993425
- `excel_cf112_fcf_shl_keur`: 335.8700119281534
- `finco_cash_available_for_shl_keur`: 494.76012478908433

## Senior Debt Authority
- Bank sizing debt size / authoritative clean opening debt: `40946.629140153134` kEUR
- Binding constraint: `DSCR`
- Initial guess only: `42852.26672602787` kEUR
- `fixed_debt_keur` is not mapped to `opening_debt_balance_keur` in clean DSCR-sculpted production.

## Max Deltas By Line

- `Production`: period 45 delta -2.1827872842550278e-11
- `Price`: period 46 delta -4.263256414560601e-14
- `Revenue`: period 46 delta -2.7284841053187847e-12
- `OPEX`: period 48 delta 9.094947017729282e-13
- `EBITDA`: period 5 delta -9.094947017729282e-13
- `Book Dep`: period 1 delta 2.8193485150040942e-05
- `Senior Interest`: period 1 delta -57.966168788217374
- `SHL Interest`: period 37 delta -307.10020993419545
- `EBT`: period 37 delta 307.10019912773305
- `Fiscal Reintegration`: period 37 delta -307.10020993419545
- `Taxable Income`: period 40 delta 706.7075889497728
- `Loss Utilisation`: period 6 delta 277.53553660067155
- `CIT`: period 60 delta -354.4219621905736
- `Cash Tax`: period 59 delta 706.5567709778473
- `Base CFADS`: period 59 delta -709.3217983002546
- `Senior Principal`: period 28 delta 491.30463189533907
- `Senior Debt Service`: period 28 delta 505.8119165830931
- `Senior Closing`: period 1 delta -1804.7256783371413
- `Post-Senior Cash`: period 59 delta -709.3217983002546
- `Cash Available for SHL`: period 59 delta -709.3217983002546

## Boundary Notes
- Base production, price, revenue, OPEX and EBITDA are source-parity at numerical precision after the generic calendar fixes.
- DS1 Base CFADS matches source CF79.
- DS1 Senior Debt Service and post-Senior cash do not close after restoring bank-sizing authority; the first remaining material boundary is Senior Interest because clean bank-sizing debt quantum differs from the legacy Excel anchor.
- Source fixtures are used only for diagnostics/tests and are not runtime inputs.

## Local Regression Notes
- `tests/test_stage_c3b3d2b6_base_post_senior_cash_parity.py` + `tests/test_stage_c3b3d2b5_shl_fixed_point_integration.py`: 36 passed locally.
- Broader historical B3/B4/C3B3A/C3B1/Phase2B band was run for visibility on the prior head: 634 passed, 45 failed. Expected remaining work includes stale period-axis expectations and pre-existing tax baseline/governance drift.
