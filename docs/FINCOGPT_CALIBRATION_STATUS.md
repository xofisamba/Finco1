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

### Excel fixtures

Raw `.xlsm` files are intentionally not committed. Minimal JSON fixtures are committed instead:

- `tests/fixtures/excel_calibration_targets.json`
- `tests/fixtures/excel_golden_oborovo.json`
- `tests/fixtures/excel_golden_tuho.json`
- `tests/fixtures/excel_oborovo_periods.json`
- `tests/fixtures/excel_tuho_periods.json`

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

Diagnostic `xfail` checks:

- Oborovo project IRR vs Excel.
- Oborovo first three period core lines vs Excel.
- TUHO project IRR vs Excel.
- TUHO equity IRR vs Excel.
- TUHO first three period core lines vs Excel.

These xfails are intentional. They keep CI honest while documenting known gaps.

## First concrete engine fix already made

`app/waterfall_core.py` now uses `opex_schedule_period(inputs, engine)` instead of `annual_opex / 2`.

Depreciation in the core now uses `annual_dep * period.day_fraction` instead of `annual_dep / 2`.

This is closer to Excel, which uses period/day-count factors rather than a simple half-year split.

## Next math-fix sequence

Work should continue in this order. Do not jump to UI polish before these are resolved.

### 1. Revenue and generation parity

Compare app period revenue to Excel `CF.operating_revenues_keur` for the first 3, then 12, then all periods.

Likely areas:

- COD stub handling.
- PPA period end and PPA term cutoff.
- Production degradation timing.
- Availability treatment.
- Wind vs PV generation basis for TUHO.
- Balancing cost treatment.
- CO2/certificate revenue treatment for Oborovo.

### 2. OpEx parity

The app now uses period-level OpEx, but line-item values still need Excel mapping.

Likely areas:

- Oborovo Y1 OpEx line totals.
- TUHO-specific OpEx line items instead of reused Oborovo OpEx.
- Step changes and inflation timing.
- Bank tax / operating tax treatment.

### 3. Depreciation and tax parity

Compare app depreciation and tax rows to `P&L` fixtures.

Likely areas:

- Depreciation base.
- Depreciation start date.
- Asset class split.
- Construction-period tax loss.
- ATAD / interest deductibility.
- Loss carryforward utilization.

### 4. Debt schedule parity

Compare `senior_principal_keur`, `senior_interest_keur`, and `senior_ds_keur` period by period.

Likely areas:

- Day-count convention for interest.
- Debt sculpting denominator and CFADS definition.
- Fixed-vs-sculpted debt service for TUHO.
- DSCR schedule split between PPA and merchant periods.
- DSRA contribution/release logic.

### 5. Equity / SHL / IRR parity

Only after project-level cash flow and debt schedule are aligned:

- Compare SHL interest and principal flows.
- Compare dividend distribution timing.
- Compare exact equity cash-flow series.
- Then compare equity IRR.

## Review guidance

A green test suite on this branch does not yet mean the model is Excel-parity. It means the branch has a reliable calibration harness with known xfail gaps.

The next meaningful milestone is to turn the Oborovo first-three-period core-line reconciliation from xfail to passing without loosening tolerances.
