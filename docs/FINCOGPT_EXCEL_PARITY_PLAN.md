# FincoGPT Excel Parity Plan

## Purpose

The Oborovo and TUHO Excel workbooks are the source of truth for the next development phase. The application must not merely approximate the Excel outputs; it should reproduce the Excel model logic, worksheet structure, and user workflow as closely as possible while replacing fragile spreadsheet behavior with tested Python code.

This document intentionally does not commit the original `.xlsm` files to the public repository. Sensitive commercial data should be transformed into minimal calibration fixtures and documented mapping tables.

## Uploaded source workbooks reviewed

- `20260414_BP_Oborovo_Sensitivity_FINAL for PPT.xlsm`
- `20260330_TUHO_BP.xlsm`

## Workbook structure to mirror in the app

The application should follow the mental model of the Excel files. A pure dashboard is not enough. The app should have spreadsheet-like pages that correspond to the core worksheets:

| Excel area | App page / module | Purpose |
|---|---|---|
| Inputs | Inputs | All project, technical, revenue, capex, financing, tax, SHL and scenario assumptions |
| Outputs | Outputs / Dashboard | KPI summary and investment decision metrics |
| CF | Cash Flow | Period-by-period waterfall and project cash flow |
| DS | Debt Schedule | Senior debt sizing, amortization, DSCR and refinancing logic |
| IDC | IDC / Funding | Construction funding, debt drawdowns, IDC and commitment fees |
| CapEx | CapEx | Detailed capex items, financial costs and total funding requirement |
| P&L | P&L | Revenue, OpEx, depreciation, tax and accounting profit |
| BS | Balance Sheet | Debt, reserves, equity and closing balances |
| Eq | Equity Returns | Sponsor/equity cash flows and equity IRR |
| Flags | Period Engine / Flags | Date flags, period flags, maturity flags and day-count factors |
| Scenarios | Scenario Manager | Case selection, sensitivities and side-by-side outputs |
| FID deck outputs | Reporting | Values exported to the FID/deck format |

## Initial golden KPI anchors observed

These values are extracted from calculated workbook cells and should be treated as first-pass calibration anchors. The next step is to extract period-by-period fixtures and reconcile each line item.

### Oborovo workbook

| Metric / cell area | Observed value |
|---|---:|
| Total CapEx (`CapEx!C141`) | 57,973.052657 kEUR |
| Senior Debt (`IDC!D48` / debt schedule area) | 42,852.2667 kEUR |
| Unlevered Project IRR (`CF!D136`) | 8.280167% |
| Senior debt service first operating periods (`CF!H80:J80`) | -2,239.133 / -2,202.626 / -2,240.525 kEUR |

### TUHO workbook

| Metric / cell area | Observed value |
|---|---:|
| Total CapEx (`Inputs!C45`, `CapEx!C123`) | 72,993.706786 kEUR |
| Senior Debt (`Outputs!H11`, `IDC!D48`) | 43,359.273782 kEUR |
| Project IRR (`CF!D125`) | 9.304676% |
| Unlevered Project IRR (`CF!D126`) | 9.108281% |
| Equity IRR (`Eq!D28`) | 11.609525% |
| Senior debt service first operating periods (`CF!H70:J70`) | -2,116.361 / -2,151.439 / -2,144.692 kEUR |
| Average DSCR PPA / market (`Inputs!G166`, `Inputs!J166`) | 1.20 / 1.40 |

## Key Excel logic that must be reproduced

### 1. Period flags and day-count factors

The `Flags` sheets drive debt maturity, hedge maturity, maturity-day percentages and bank-year day-count factors. These are not cosmetic. They must be represented explicitly in Python and exposed for inspection in the app.

Observed examples:

- Oborovo `DS!G6:J6`: senior debt period factors around `1.01944`, `0.51111`, `0.50278`, `0.51111`.
- TUHO `DS!G6:J6`: senior debt period factors around `1.52778`, `0.50278`, `0.51111`, `0.50278`.

This confirms that simple `annual_value / 2` logic is not sufficient for all schedules.

### 2. Debt sizing and DSCR

Debt is very close in the current app baseline, but DSCR and IRR are not. The most likely reason is that the debt amount may be matching by gearing/constraint while reported CFADS, revenue, opex, tax or DSCR schedule is not matching Excel period-by-period.

The next calibration stage must reconcile:

- CFADS line used for debt sizing
- debt service line
- DSCR numerator and denominator
- maturity flags
- refinancing flags
- DSRA treatment

### 3. Revenue / OpEx / depreciation / tax are not optional details

The Sprint 4 report described the calibration run as simplified. Excel parity requires using the same line logic as the workbook, including:

- PPA and merchant split
- PPA indexation
- day-count weighted generation/revenue
- OpEx escalation and step logic
- depreciation base and tenor
- construction-period tax loss
- ATAD and interest deductibility treatment

### 4. Equity IRR method

The app needs to support the workbook-specific equity cash flow construction, especially SHL plus dividends where applicable. The relevant app page should not show only one equity IRR number; it should show the underlying cash flow series used to compute it.

## UI direction

The UI should be Excel-like in structure, not only in colors. Users should be able to inspect and reconcile the model just like they would in Excel.

Recommended app navigation:

1. Overview / Outputs
2. Inputs
3. CapEx
4. Construction Funding / IDC
5. Revenue
6. OpEx
7. Cash Flow
8. Debt Schedule
9. Tax / P&L
10. Balance Sheet
11. Equity Returns
12. Scenarios / Sensitivities
13. FID Deck Export
14. Calibration / Excel Reconciliation

## Implementation priorities

### P0: Headless runner

Create one uncached calculation path that can be called by Streamlit, CLI and pytest.

### P0: Excel extraction fixtures

Extract minimal golden fixtures from the workbooks into JSON. Do not commit the raw `.xlsm` files unless the repository becomes private and the owner explicitly approves it.

### P0: Period-by-period reconciliation

Do not rely only on final IRR/debt KPIs. Reconcile every period for the main lines:

- Revenue
- OpEx
- EBITDA
- tax
- CFADS
- senior debt interest
- senior debt principal
- senior debt service
- DSCR
- DSRA movement
- SHL interest/principal
- distributions
- equity cash flow

### P1: App pages that mirror workbook tabs

Once the core model is reconciled, build pages that mirror the workbook sheets.

### P1: Scenario and sensitivity parity

The workbook scenario tables and sensitivity areas should become first-class app features, not ad hoc charts.

## Acceptance criteria for Excel parity

Initial tolerance targets:

| Metric type | Initial tolerance | Enterprise target |
|---|---:|---:|
| Senior debt | ±1.0% | ±0.25% |
| Project IRR | ±50 bps | ±15–25 bps |
| Equity IRR | ±50 bps | ±15–25 bps |
| Avg DSCR | ±0.05x | ±0.02x |
| Period revenue | ±0.5% | ±0.1–0.25% |
| Period debt service | ±0.5% | ±0.1–0.25% |
| Period CFADS | ±1.0% | ±0.25–0.5% |

## Current branch changes related to this plan

- Added `app/waterfall_core.py` as an uncached calculation path.
- Updated `app/cache.py` so `cached_run_waterfall_v3` delegates to the uncached core.

This is only the first structural step. The next step is to add a CLI/test harness that loads scenario inputs and produces reconciliation JSON without importing Streamlit.
