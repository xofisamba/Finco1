# Excel UX and Calibration Mapping

## Purpose

The Oborovo and TUHO workbooks are both calculation references and UX references. The application should preserve the Excel mental model while replacing spreadsheet fragility with typed inputs, reproducible runs, tests, auditability and scenario versioning.

Raw `.xlsm` files are not committed to this public repository. This document records the workbook structure and the app mapping derived from the uploaded files.

## Shared workbook spine

Both workbooks use a recognisable project-finance model spine:

| Workbook sheet / area | App equivalent | Notes |
|---|---|---|
| Inputs | Inputs page | Primary editable assumptions. App should keep this as the main assumption-control page. |
| CapEx | CapEx page | Detailed capex, financial costs, reserve funding and total funding requirement. |
| OpEx | OpEx page | OpEx line items, escalation and step changes. |
| CF | Cash Flow / Waterfall page | Core period-by-period cash flow and debt/equity cash flow lines. |
| P&L | P&L / Tax page | Accounting profit, depreciation, tax and loss carryforward. |
| BS | Balance Sheet page | Balance sheet style outputs and closing balances. |
| Dep | Depreciation page/module | Depreciation base and depreciation schedule. |
| DS | Debt Schedule page | Debt drawdown, amortization, interest, DSCR, reserves and flags. |
| Eq | Equity Returns page | Sponsor/SHL/equity cash flow and IRR calculations. |
| Macro | Macros / Scenario tooling | Do not execute macros automatically. Translate required macro behavior into explicit Python/UI flows. |
| Flags | Period Engine / Flags page | Period flags, day-count factors, maturity flags and model-year mappings. |
| Outputs | Overview / Outputs page | KPI dashboard and investment committee outputs. |
| FID deck outputs | Export / IC View | PPT/export-ready values and tables. |

TUHO also contains a hidden `Cash@Risk` workbook area. This should be treated as a future risk-analysis feature and not ignored.

## UX principles to preserve

1. **Excel-like navigation, not generic dashboard-only navigation.** Users should find the same model blocks they know from the workbook.
2. **Input/output separation.** Editable assumptions should be visually distinct from calculated outputs.
3. **Period columns remain inspectable.** The app must support period-by-period review, not only charts and KPI cards.
4. **Calibration is a first-class app page.** Users should see app-vs-Excel deltas by metric and by period.
5. **FID/deck outputs are a workflow, not an afterthought.** The app should expose an investment committee style view aligned with the workbook export area.

## Proposed app page map

| Order | App page | Mirrors workbook | Primary user job |
|---:|---|---|---|
| 1 | Overview / Outputs | Outputs | Read KPIs and investment decision metrics. |
| 2 | Inputs | Inputs | Edit assumptions with validation. |
| 3 | CapEx | CapEx | Inspect total funding requirement and spending profile. |
| 4 | Construction Funding / IDC | IDC / DS / CapEx | Inspect debt drawdowns, IDC and fees. |
| 5 | Revenue | Inputs / CF | Inspect generation, PPA, merchant and CO2 revenue. |
| 6 | OpEx | OpEx / CF | Inspect OpEx categories and escalation. |
| 7 | Cash Flow | CF | Inspect period waterfall. |
| 8 | Debt Schedule | DS | Inspect debt service, DSCR, reserves and maturity. |
| 9 | Tax / P&L | P&L / Dep | Inspect tax, depreciation and carryforwards. |
| 10 | Balance Sheet | BS | Inspect balance sheet outputs. |
| 11 | Equity Returns | Eq | Inspect equity/SHL cash flows and IRR. |
| 12 | Scenarios / Sensitivities | Sensitivity / Outputs | Compare downside/base/upside and sensitivities. |
| 13 | FID Deck Export | FID deck outputs | Prepare IC/export-ready tables. |
| 14 | Calibration | All core sheets | App-vs-Excel reconciliation and known deviations. |

## Calibration fixture strategy

### Stage 1: KPI anchors

The first committed fixture is `tests/fixtures/excel_calibration_targets.json`. It contains workbook-level anchor values only.

### Stage 2: Period-level fixtures

Next fixtures should include row-by-period values for:

- revenue
- OpEx
- EBITDA
- depreciation
- tax
- CFADS
- senior interest
- senior principal
- senior debt service
- DSCR
- DSRA contribution, release and balance
- SHL interest, principal, PIK and balance
- distribution / dividend
- equity cash flow

### Stage 3: App-vs-Excel reconciliation reports

The app should produce a JSON and UI table with:

- Excel value
- app value
- absolute delta
- percentage delta
- tolerance
- pass/fail status
- line-item owner/module

## Known implementation implications

### 1. Streamlit cache must remain a wrapper

`app/cache.py` may use `@st.cache_data`, but the production calculation path must live in a non-Streamlit module. The current `app/waterfall_core.py` is the first step.

### 2. WaterfallRunner still needs cleanup

`app/waterfall_runner.py` currently imports `app.cache`. That means it is not fully headless-safe. The next refactor should make `WaterfallRunner` call `app.waterfall_core.run_waterfall_v3_core`, while Streamlit pages call cache wrappers around that same core.

### 3. Period flags are critical

The workbooks use `Flags` sheets to drive model period logic. The Python period engine must expose equivalent flags rather than hiding them inside helper functions.

### 4. Sensitivity should mirror workbook tables

Sensitivity UI should not be invented from scratch. It should follow the workbook's variables, ranges and outputs wherever possible.

## Immediate next tasks

1. Add tests proving `app.waterfall_core` is importable without Streamlit.
2. Add a headless calibration script or module.
3. Extract period-level fixtures from Oborovo and TUHO.
4. Refactor `WaterfallRunner` so it no longer requires `app.cache` for computation.
5. Add calibration tests that initially report honest failures instead of masking deviations.
