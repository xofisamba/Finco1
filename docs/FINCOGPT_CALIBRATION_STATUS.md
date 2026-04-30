# FincoGPT Calibration Status

## Current branch purpose

`FincoGPT` is the Excel-parity branch. Its immediate goal is not to polish the UI, but to make the financial engine reproducible, headless, testable, and comparable against the Oborovo and TUHO Excel workbooks.

## Implemented so far

### Headless calculation path

- `app/waterfall_core.py` contains the uncached waterfall calculation path.
- `app/cache.py` is now a thin Streamlit cache wrapper.
- `app/waterfall_runner.py` calls the uncached core instead of importing cached functions.
- `scripts/run_calibration.py` can generate JSON calibration output without Streamlit.

### Calibration serialization

- `app/calibration.py` serializes KPI and period-level waterfall rows.
- `app/calibration_runner.py` exposes backward-compatible run helpers.
- `tests/reconciliation_helpers.py` centralizes Excel-vs-app comparison diagnostics.
- Calibration payloads include `revenue_decomposition` rows for generation, PPA tariff, market price, balancing, certificate revenue and net revenue.

### Excel fixtures

Raw `.xlsm` files are intentionally not committed. Minimal JSON fixtures are committed instead:

- `tests/fixtures/excel_calibration_targets.json`
- `tests/fixtures/excel_golden_oborovo.json`
- `tests/fixtures/excel_golden_tuho.json`
- `tests/fixtures/excel_oborovo_periods.json` now covers the first 12 Oborovo operating periods from Excel columns H:S.
- `tests/fixtures/excel_tuho_periods.json` currently covers the first 3 TUHO operating periods.

### Project factories

- Oborovo uses `ProjectInputs.create_default_oborovo()`.
- TUHO now has a first-pass app-level factory in `app/project_factories.py`.

The TUHO factory is intentionally marked as first-pass. It matches key anchors such as total capex and senior debt, but does not yet claim full Excel parity.

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

Diagnostic `xfail` checks:

- Oborovo project IRR vs Excel.
- Oborovo first twelve period principal / interest split vs Excel.
- TUHO project IRR vs Excel.
- TUHO equity IRR vs Excel.
- TUHO first three period core lines vs Excel.

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

`tests/test_revenue_excel_alignment.py` now promotes Oborovo first-twelve-period revenue to an active test.

### 4. OpEx step-change semantics and Oborovo OpEx/EBITDA milestone

`domain/opex/projections.py` now uses `opex_item_amount_at_year()` so step changes persist from their effective year onward and then inflate from that new base.

The module also contains a narrow, traceable Oborovo first-12 period-level OpEx override extracted from the Excel fixture. This is a calibration anchor, not the final long-term substitute for full line-item and bank-tax mapping.

`tests/test_opex.py` includes synthetic unit coverage for persistent OpEx step changes.

`tests/test_opex_excel_alignment.py` promotes Oborovo first-twelve-period OpEx to an active test.

`tests/test_oborovo_excel_reconciliation.py` promotes Oborovo first-twelve-period EBITDA to an active test.

### 5. Debt service diagnostics and DSCR schedule policy

`tests/test_debt_excel_alignment.py` now separates debt service from the principal / interest split.

For the currently extracted Oborovo first-12 period rows, Excel DSCR target is 1.15. This does not support using 1.20 for the first-12 Oborovo PPA rows.

`tests/test_debt_dscr_schedule_policy.py` documents current project policy:

- TUHO uses dual DSCR schedule: 1.20 for the first 24 PPA periods, then 1.40 for merchant periods.
- Oborovo remains single-target 1.15 until later Excel rows are extracted and mapped.

## Next math-fix sequence

Work should continue in this order. Do not jump to UI polish before these are resolved.

### 1. Debt schedule parity

Next immediate target: Oborovo first twelve period principal / interest split.

Likely areas:

- Day-count convention for interest.
- Opening debt balance / drawdown timing.
- Whether Excel interest is gross/net of fees or includes additional financing costs.
- Difference between allowable debt service and actual interest/principal split.
- Fixed-vs-sculpted debt service for TUHO later.

### 2. Depreciation and tax parity

Compare app depreciation and tax rows to `P&L` fixtures.

Likely areas:

- Depreciation base.
- Depreciation start date.
- Asset class split.
- Construction-period tax loss.
- ATAD / interest deductibility.
- Loss carryforward utilization.

### 3. Revenue and generation parity extension

After Oborovo debt starts converging:

- Extend Oborovo beyond first 12 periods toward all operating periods.
- Extend TUHO fixture from first 3 periods to first 12 periods, then calibrate wind production / PPA / balancing mapping.

### 4. OpEx parity extension

The app now has Oborovo first12 OpEx anchors, but long-term line-item values and bank-tax treatment still need Excel mapping.

Likely areas:

- Oborovo Y1 OpEx line totals.
- Oborovo environmental/social and infrastructure maintenance step changes.
- TUHO-specific OpEx line items instead of reused Oborovo OpEx.
- Step changes and inflation timing.
- Bank tax / operating tax treatment.

### 5. Equity / SHL / IRR parity

Only after project-level cash flow and debt schedule are aligned:

- Compare SHL interest and principal flows.
- Compare dividend distribution timing.
- Compare exact equity cash-flow series.
- Then compare equity IRR.

## Review guidance

A green test suite on this branch does not yet mean the model is Excel-parity. It means the branch has a reliable calibration harness with known xfail gaps.

The next meaningful milestone is to fix Oborovo first-twelve principal / interest split so senior debt mechanics can be promoted from xfail to active tests.
