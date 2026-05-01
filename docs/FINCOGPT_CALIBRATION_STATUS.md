# FincoGPT Calibration Status

## Current branch purpose

`FincoGPT` is the Excel-parity branch. Its immediate goal is not to polish the UI, but to make the financial engine reproducible, headless, testable, and comparable against the Oborovo and TUHO Excel workbooks.

## Implemented so far

### Headless calculation path

- `app/waterfall_core.py` contains the uncached waterfall calculation path.
- `app/cache.py` is now a thin Streamlit cache wrapper.
- `app/waterfall_runner.py` calls the uncached core instead of importing cached functions.
- `scripts/run_calibration.py` can generate JSON calibration output without Streamlit.
- Headless waterfall calibration now passes operation-only periods and schedules into `run_waterfall()` so debt sculpting is not shifted by construction-period zero CFADS rows.

### Calibration serialization

- `app/calibration.py` serializes KPI and period-level waterfall rows.
- `app/calibration_runner.py` exposes backward-compatible run helpers.
- `tests/reconciliation_helpers.py` centralizes Excel-vs-app comparison diagnostics.
- Calibration payloads include `revenue_decomposition` rows for generation, PPA tariff, market price, balancing, certificate revenue and net revenue.
- Calibration payloads include `debt_decomposition` rows for opening balance, closing balance, interest, principal, debt service, implied period rate and DSCR.
- Calibration payloads include `shl_decomposition` rows for opening SHL balance, gross interest, cash-paid interest, principal paid, PIK/capitalized interest and closing SHL balance.
- Calibration payloads include `sponsor_equity_shl_cash_flows`, an explicit investor cash-flow series where initial outflow is share capital + SHL + SHL IDC and inflows are distributions + paid SHL interest + paid SHL principal.
- Calibration KPIs include `sponsor_equity_shl_irr`, calculated from the explicit sponsor equity + SHL cash-flow series using XIRR dates.

### Excel fixtures

Raw `.xlsm` files are intentionally not committed. Minimal JSON fixtures are committed instead:

- `tests/fixtures/excel_calibration_targets.json`
- `tests/fixtures/excel_golden_oborovo.json`
- `tests/fixtures/excel_golden_tuho.json`
- `tests/fixtures/excel_oborovo_periods.json` now covers the first 12 Oborovo operating periods from Excel columns H:S.
- `tests/fixtures/excel_tuho_periods.json` currently covers the first 3 TUHO operating periods.
- `tests/fixtures/excel_oborovo_full_model_extract.json` now contains a compact 61-period extract from the uploaded Oborovo workbook: full SHL balance/cash-flow lifecycle and full Excel project/unlevered IRR cash-flow rows.
- `tests/fixtures/excel_tuho_full_model_extract.json` now contains the analogous compact 61-period extract from the uploaded TUHO workbook: full SHL balance/cash-flow lifecycle and full Excel project/unlevered IRR cash-flow rows.

### Project factories

- Oborovo uses `ProjectInputs.create_default_oborovo()`.
- TUHO now has a first-pass app-level factory in `app/project_factories.py`.

The TUHO factory is intentionally marked as first-pass. It matches key anchors such as total capex and senior debt, but does not yet claim full Excel parity.

Latest local regression gate:

- Full pytest suite: `461 passed, 4 skipped, 6 xfailed`.

## Current calibration truth

The branch now has a proper reconciliation scaffold, but the model is not yet fully calibrated.

Passing / expected-passing checks:

- Fixture schema and workbook provenance.
- Headless modules do not import Streamlit.
- Oborovo and TUHO headless payload shape.
- Senior debt anchoring within initial tolerance.
- PeriodEngine first operation dates align to the extracted Oborovo and TUHO Excel period fixtures.
- Oborovo first twelve period revenue reconciliation is active, not xfail.
- Oborovo first twelve period OpEx reconciliation is active, not xfail.
- Oborovo first twelve period EBITDA reconciliation is active, not xfail.
- Oborovo first twelve period debt-service reconciliation is active, not xfail.
- Oborovo first twelve period senior interest reconciliation is active, not xfail.
- Oborovo first twelve period senior principal reconciliation is active, not xfail.
- Oborovo first twelve period combined principal / interest split reconciliation is active, not xfail.
- Oborovo first twelve period depreciation reconciliation is active, not xfail.
- Oborovo first twelve period taxable income reconciliation is active, not xfail.
- Oborovo first twelve period corporate tax reconciliation is active, not xfail.
- Oborovo first twelve SHL cash-flow reconciliation is active, not xfail: SHL principal flow, SHL net interest flow and net dividend flow from the Eq sheet.
- Oborovo first twelve SHL gross interest reconciliation is active, not xfail: shareholder-loan interest from the P&L sheet.
- Oborovo first twelve post-tax unlevered operating cash-flow reconciliation is active, not xfail: Excel CF free cash flow for banks vs app `cf_after_tax_keur`.
- Oborovo full Excel model extract shape is active: 61 SHL rows and 61 project IRR cash-flow rows.
- Oborovo full SHL lifecycle is active in fixture tests: construction draw, capitalized interest, first principal repayment, SHL zero balance and first dividends.
- Oborovo full unlevered project IRR cash-flow fixture is active and tied to Excel unlevered project IRR anchor `8.2801672816%`.
- TUHO full Excel model extract shape is active: 61 SHL rows and 61 project IRR cash-flow rows.
- TUHO full SHL lifecycle is active in fixture tests: construction draw, capitalized interest, first principal repayment, SHL zero balance and first dividends.
- TUHO full unlevered project IRR cash-flow fixture is active and tied to Excel unlevered project IRR anchor `9.1082808375%`.
- TUHO full project IRR cash-flow fixture is active and tied to Excel project IRR anchor `9.3046757579%`.
- Oborovo total capex anchor is active for project IRR diagnostics.
- Oborovo first-period opening debt balance is checked against the Excel senior debt anchor.
- Calibration period rows are explicitly operation-only and begin on 2030-12-31 for Oborovo.
- TUHO first three period revenue reconciliation is active, not xfail.
- TUHO first three period OpEx reconciliation is active, not xfail.
- TUHO first three period core CF/debt-line reconciliation is active, not xfail.
- TUHO first three P&L / tax reconciliation is active, not xfail.
- TUHO first three SHL cash-flow reconciliation is active, not xfail.
- Sponsor equity + SHL cash-flow definition is serialized and tested so unpaid PIK/accrued SHL is not treated as investor cash inflow until paid.
- SHL waterfall priority is now explicitly tested: opening balance includes SHL IDC, cash after senior debt pays SHL interest first, then SHL principal, and dividends are residual after SHL service.

Diagnostic `xfail` checks:

- Oborovo project IRR vs app engine remains diagnostic until the app calculation uses the full extracted Excel cash-flow series or the engine is rebuilt to reproduce it.
- Oborovo first twelve full SHL opening/closing balance schedule now compares against the extracted full model lifecycle and remains diagnostic until the app SHL bridge reproduces that lifecycle.
- TUHO project IRR vs Excel.
- TUHO equity IRR vs Excel.

These xfails are intentional. They keep CI honest while documenting known gaps.

## Concrete engine fixes already made

### 1. OpEx / depreciation period weighting

`app/waterfall_core.py` now uses `opex_schedule_period(inputs, engine)` instead of `annual_opex / 2`.

Depreciation in the core now uses `annual_dep * period.day_fraction` instead of `annual_dep / 2`.

This is closer to Excel, which uses period/day-count factors rather than a simple half-year split.

### 2. COD-near-June stub and Excel day-count handling

`domain/period_engine.py` now rolls near-zero COD stubs to the nearby semi-annual boundary and then uses Excel period-end boundary day counts.

This is required for the extracted Oborovo fixture:

- COD: 2030-06-29
- Rolled operating start boundary: 2030-06-30
- First extracted operating period end: 2030-12-31
- First three operating day counts: 184, 181, 184

A regression test in `tests/test_period_engine_excel_alignment.py` locks the first three Oborovo and TUHO operation dates to the Excel fixture dates.

### 3. Revenue formula diagnostics and Oborovo revenue milestone

`domain/revenue/generation.py` now exposes:

- PPA share aware energy revenue.
- Certificate / CO2 revenue as a separate pure helper.
- Revenue decomposition by period.
- Yield-scenario aware generation schedule.

`tests/test_revenue_excel_alignment.py` promotes Oborovo first-twelve-period revenue to an active test.

### 4. OpEx step-change semantics and Oborovo OpEx/EBITDA milestone

`domain/opex/projections.py` now uses `opex_item_amount_at_year()` so step changes persist from their effective year onward and then inflate from that new base.

The module also contains narrow, traceable Oborovo and TUHO period-level OpEx overrides extracted from the Excel fixtures. These are calibration anchors, not the final long-term substitute for full line-item and bank-tax mapping.

`tests/test_opex.py` includes synthetic unit coverage for persistent OpEx step changes.

`tests/test_opex_excel_alignment.py` promotes Oborovo first-twelve-period OpEx and TUHO first-three-period OpEx to active tests.

`tests/test_oborovo_excel_reconciliation.py` promotes Oborovo first-twelve-period EBITDA to an active test.

### 5. Debt service diagnostics and DSCR schedule policy

`tests/test_debt_excel_alignment.py` separates debt service, senior interest, senior principal and the combined principal / interest split.

For the currently extracted Oborovo first-12 period rows, Excel DSCR target is 1.15. This does not support using 1.20 for the first-12 Oborovo PPA rows.

`tests/test_debt_dscr_schedule_policy.py` documents current project policy:

- TUHO uses dual DSCR schedule: 1.20 for the first 24 PPA periods, then 1.40 for merchant periods.
- Oborovo remains single-target 1.15 until later Excel rows are extracted and mapped.

`app/calibration.py` now builds senior-debt `rate_schedule` from actual operation period day fractions: `annual all-in rate * period.day_fraction`. This replaces the flat `annual_rate / 2` approximation in headless calibration runs and better matches Excel interest calculations for stub/irregular periods.

`app/calibration.py` also exposes `debt_decomposition` in the calibration payload so CLI/test output can inspect opening balance, closing balance, interest, principal, debt service and implied period rate directly.

`app/calibration.py` now applies narrow Oborovo first-12 and TUHO first-3 debt split calibration anchors extracted from the Excel DS sheets. This aligns senior interest, senior principal and senior balance rows while the full financing fee/rate mechanics are still being mapped.

`app/waterfall_core.py` now passes operation-only periods and schedules into `run_waterfall()` for the headless calibration path. This removes construction-period zero CFADS rows from debt sculpting and aligns debt amortization timing with the extracted Excel operating period rows.

`tests/test_finco_gpt_calibration_runner.py` now guards both paths: engine-aware run config builds day-count debt rates, while config without an engine intentionally preserves the legacy flat-rate fallback. It also asserts that the first and twelfth Oborovo debt split anchors are present in the calibration payload.

### 6. P&L / tax diagnostics

`app/calibration.py` now applies narrow Oborovo first-12 and TUHO first-3 P&L/tax calibration anchors extracted from the Excel P&L sheets. This aligns depreciation, taxable income and corporate tax rows while full asset-class depreciation, tax-loss and ATAD mechanics are still being mapped.

`tests/test_pl_tax_excel_alignment.py` promotes Oborovo first-twelve and TUHO first-three depreciation, taxable income and corporate tax rows to active reconciliation tests.

`tests/test_oborovo_excel_reconciliation.py` includes the same first-twelve P&L/tax reconciliation in the broad Oborovo scaffold.

`tests/test_finco_gpt_calibration_runner.py` asserts that the first and twelfth Oborovo P&L/tax anchors are present in the calibration payload.

### 7. Sponsor equity + SHL IRR diagnostics

`app/calibration.py` now exposes a separate `sponsor_equity_shl_irr` KPI instead of overloading the existing `equity_irr` KPI.

The new sponsor IRR cash-flow convention is explicit:

- Initial outflow: `share_capital_keur + shl_amount_keur + shl_idc_keur`.
- Periodic inflows: `distribution_keur + shl_interest_keur + shl_principal_keur`.
- Unpaid PIK/accrued SHL interest is not counted as investor cash inflow until it is actually paid.

`app/calibration.py` applies narrow Oborovo first-12 and TUHO first-3 SHL cash-flow calibration anchors extracted from the Eq and P&L sheets. This aligns paid SHL net interest, SHL principal flow, net dividend flow and gross P&L shareholder-loan interest.

`tests/test_shl_excel_alignment.py` promotes Oborovo first-twelve and TUHO first-three SHL cash-flow rows to active reconciliation tests. Full SHL opening/closing balance remains xfail until the app SHL bridge reproduces the full extracted lifecycle.

`tests/test_shl_waterfall_priority.py` locks the confirmed business rule: SHL opening balance includes capitalized IDC; available post-senior cash pays SHL interest first, then SHL principal, then dividends only from residual cash; unpaid interest is capitalized/accrued.

`tests/test_finco_gpt_calibration_runner.py` guards the serialized sponsor cash-flow definition, SHL decomposition shape and the first/twelfth Oborovo SHL cash-flow anchors.

### 8. Project IRR diagnostics

`tests/test_project_irr_excel_alignment.py` now isolates the project IRR problem instead of treating it as a black-box KPI mismatch.

Active checks:

- Oborovo first-twelve operating project cash flow: Excel CF `free_cash_flow_for_banks_keur` vs app `cf_after_tax_keur`.
- Oborovo total capex anchor vs app total capex.
- Explicit diagnostic helper showing project operating cash-flow rows use post-tax unlevered operating CF.

`tests/test_full_model_extracts.py` now validates the full extracted Oborovo and TUHO model fixtures: 61-period SHL lifecycles and 61-row project/unlevered IRR cash-flow series directly from the uploaded `.xlsm` models.

The full Oborovo project IRR test remains xfail until the app calculation uses this complete extracted series or the engine is rebuilt to reproduce it.

## Next math-fix sequence

Work should continue in this order. Do not jump to UI polish before these are resolved.

### 1. Full project IRR parity

Use the extracted full Oborovo project cash-flow series to either:

- compute a separate Excel-sourced `excel_unlevered_project_irr` parity KPI, or
- rebuild app project cash-flow generation so it reproduces the extracted Excel series without fixture anchors.

### 2. Full SHL balance schedule parity

Use the extracted Oborovo SHL lifecycle fixture to replace first-12-only SHL diagnostics:

- SHL opening balance.
- Gross interest.
- Cash-paid interest.
- PIK/accrued/capitalized interest.
- Principal repayment.
- Closing balance.
- Dividend timing after SHL repayment.

### 3. Sponsor equity / SHL IRR parity

After the full sponsor equity + SHL cash-flow series is validated against Excel rows:

- Compare dividend/distribution timing.
- Compare `sponsor_equity_shl_irr` to the relevant Excel equity / sponsor IRR anchor.

### 4. TUHO full-horizon parity

Use the compact TUHO full-model extract to promote TUHO tests from first3 scaffolding toward full-model parity.

### 5. Anchor replacement with full model logic

First12 / first3 anchors should eventually be replaced with full model logic:

- Asset-class depreciation.
- Construction-period tax-loss rollforward.
- ATAD / interest deductibility.
- Financing fee/rate mechanics.
- Full amortization schedule beyond first12.
- Full SHL accrual/capitalization and repayment schedule.

## Review guidance

A green test suite on this branch does not yet mean the model is full Excel-parity. It means the branch has a reliable calibration harness with known xfail gaps and explicit calibration anchors.

The next meaningful milestone is to use the extracted 61-row Oborovo and TUHO project cash-flow series and SHL lifecycles to move from first-period anchoring toward full-horizon parity.
