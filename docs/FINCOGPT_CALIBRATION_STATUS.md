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
- `domain/waterfall/full_model_extract.py` contains pure helpers for full-model extract transformations: project cash-flow rows, SHL lifecycle rows, sponsor equity + SHL cash-flow rows and their XIRR calculations.
- `tests/reconciliation_helpers.py` centralizes Excel-vs-app comparison diagnostics.
- Calibration payloads include `revenue_decomposition` rows for generation, PPA tariff, market price, balancing, certificate revenue and net revenue.
- Calibration payloads include `debt_decomposition` rows for opening balance, closing balance, interest, principal, debt service, implied period rate and DSCR.
- Calibration payloads include `shl_decomposition` rows for opening SHL balance, gross interest, cash-paid interest, principal paid, PIK/capitalized interest and closing SHL balance.
- Calibration payloads include `sponsor_equity_shl_cash_flows`, an explicit investor cash-flow series where initial outflow is share capital + SHL + SHL IDC and inflows are distributions + paid SHL interest + paid SHL principal.
- Calibration KPIs include `sponsor_equity_shl_irr`, calculated from the explicit sponsor equity + SHL cash-flow series using XIRR dates.
- Calibration payloads include `excel_full_model_project_irr`, an Excel-sourced full-horizon project cash-flow block for Oborovo and TUHO, plus `excel_full_model_project_irr` and `excel_full_model_unlevered_project_irr` KPI diagnostics.
- Calibration payloads include `excel_full_model_shl`, an Excel-sourced full-horizon SHL lifecycle block for Oborovo and TUHO.
- Calibration payloads include `excel_full_model_sponsor_equity_shl_cash_flows` plus `excel_full_model_sponsor_equity_shl_irr`, calculated from the full extracted Excel SHL principal, paid net interest and dividend rows.
- Calibration payloads now promote the full-model extract into native-facing KPI fields for project IRR, TUHO equity IRR and sponsor equity + SHL IRR, while preserving the raw engine values under `engine_*_before_full_model_calibration` diagnostics.
- Calibration payloads now expose `engine_return_gap_before_full_model_calibration`, a compact delta summary for return KPIs before the full-model bridge is applied.
- Calibration payloads now expose `raw_engine_shl_decomposition_before_cash_flow_anchors` and `raw_engine_shl_lifecycle_gap_before_cash_flow_anchors`, so formula-level SHL gaps remain visible before full-model SHL cash-flow anchors are applied.
- Calibration payloads now expose raw native debt split and P&L/tax rows before their calibration anchors, plus gap summaries against full-model period diagnostics.
- Calibration payloads now expose `engine_shl_decomposition_before_full_model_calibration` and `engine_shl_lifecycle_gap_before_full_model_calibration`, so SHL lifecycle parity from the full-model extract is visible before the final full-model bridge is applied.
- Calibration payloads now expose `engine_project_cash_flow_gap_before_full_model_calibration`, a compact delta summary for native period `cf_after_tax_keur` versus full-model `fcf_for_banks` before project IRR bridge promotion.
- Calibration payloads now expose `sponsor_equity_shl_cash_flow_gap_before_full_model_calibration`, so the remaining native sponsor cash-flow convention gap is explicit before sponsor return KPI bridge promotion.
- Calibration payloads now expose native formula-candidate series before full-model bridge promotion for project cash flows, SHL lifecycle and sponsor equity + SHL cash flows.
- Calibration payloads now expose `formula_parity_workstreams`, a five-item backlog for project cash flow, SHL lifecycle, sponsor cash flow, debt and P&L/tax formula replacement.
- Calibration payloads now expose `calibration_scaffolding_inventory`, a bridge/anchor inventory showing which formula streams are still blocked and which are ready for removal.
- Calibration payloads now expose `full_horizon_period_parity`, grouped operating-period parity summaries for operating CF, debt and P&L/tax against the full-model period diagnostics.
- Calibration payloads now preserve `full_horizon_period_parity_before_full_model_period_bridge` before promoting the full-model period diagnostics, then expose post-bridge `full_horizon_period_parity` with operating CF, debt and P&L/tax period rows reconciled to the full-model extract.
- Calibration payloads now expose `full_model_period_diagnostics_bridge`, a transparent bridge summary showing how many CF/DS/P&L period diagnostic rows were promoted into serialized period rows.
- Calibration payloads now expose `full_model_period_diagnostics`, a 60-row operating-period extract from CF, DS, P&L and Dep sheets for Oborovo and TUHO.
- Calibration payloads now expose `engine_debt_gap_before_full_model_calibration` and `engine_pl_tax_gap_before_full_model_calibration`, compact deltas against the full-model period diagnostics, including compared metrics, mismatch counts, first mismatch and max-delta location.
- Calibration period rows now use the full-model SHL lifecycle extract for SHL opening balance, gross interest, paid interest, principal, capitalized interest, closing balance and dividend timing.
- Calibration payloads now expose native-facing full-horizon series: `project_cash_flows`, `shl_lifecycle_decomposition`, `sponsor_equity_shl_cash_flows_full_model` and `sponsor_equity_shl_cash_flows_financial_close`.

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

- Full pytest suite: `520 passed, 4 skipped`.

## Current calibration truth

The branch now has a proper reconciliation scaffold, but the model is not yet fully calibrated.

Passing / expected-passing checks:

- Fixture schema and workbook provenance.
- Headless modules do not import Streamlit.
- Oborovo and TUHO headless payload shape.
- Senior debt anchoring within initial tolerance.
- Senior debt now continues from the last Excel debt split anchor instead of reverting to a balloon-style native repayment after the anchor window.
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
- Oborovo full period diagnostics are active: 60 operating rows from CF, DS, P&L and Dep sheets.
- Oborovo full SHL lifecycle is active in fixture tests: construction draw, capitalized interest, first principal repayment, SHL zero balance and first dividends.
- Oborovo full SHL lifecycle is active in the headless calibration payload via `excel_full_model_shl` and promoted into `shl_decomposition`.
- Oborovo full unlevered project IRR cash-flow fixture is active and tied to Excel unlevered project IRR anchor `8.2801672816%`.
- Oborovo full unlevered project IRR parity is active in the headless calibration payload via `excel_full_model_project_irr` and the native-facing `project_irr` KPI.
- TUHO full Excel model extract shape is active: 61 SHL rows and 61 project IRR cash-flow rows.
- TUHO full period diagnostics are active: 60 operating rows from CF, DS, P&L and Dep sheets.
- TUHO full SHL lifecycle is active in fixture tests: construction draw, capitalized interest, first principal repayment, SHL zero balance and first dividends.
- TUHO full SHL lifecycle is active in the headless calibration payload via `excel_full_model_shl` and promoted into `shl_decomposition`.
- TUHO full unlevered project IRR cash-flow fixture is active and tied to Excel unlevered project IRR anchor `9.1082808375%`.
- TUHO full project IRR cash-flow fixture is active and tied to Excel project IRR anchor `9.3046757579%`.
- TUHO full project and unlevered project IRR parity is active in the headless calibration payload via `excel_full_model_project_irr`, with Excel project IRR promoted into the native-facing `project_irr` KPI.
- TUHO full-horizon native-facing project cash-flow and SHL lifecycle payload sections are now explicitly tested as period-parity scaffolding.
- TUHO equity IRR is active against the Excel anchor using full-model SHL/sponsor cash flows timed from financial close.
- Oborovo and TUHO Excel full-model sponsor equity + SHL cash-flow diagnostics are active and recompute `excel_full_model_sponsor_equity_shl_irr` from SHL principal flow, paid net interest and net dividend rows.
- Oborovo and TUHO native-facing full-horizon project cash-flow, SHL lifecycle and sponsor cash-flow series are exposed as stable calibration payload sections.
- Oborovo and TUHO native formula-candidate project cash-flow, SHL lifecycle and sponsor cash-flow sections are serialized before bridge promotion, so formula replacement can now target explicit native rows rather than only KPI deltas.
- Oborovo and TUHO native engine SHL lifecycle snapshots now use all operating SHL cash-flow anchors from the compact full-model extracts before the full lifecycle bridge is applied.
- Oborovo and TUHO SHL lifecycle gap summaries now confirm full extracted lifecycle parity before the full bridge: 59 compared operating rows and no closing-balance mismatch.
- Oborovo and TUHO raw SHL formula gap summaries are preserved before cash-flow anchors. Current first raw mismatches are Oborovo `2030-12-31` and TUHO `2030-06-30`; the tests now lock the raw mismatch values and max absolute deltas.
- Oborovo and TUHO raw debt split and P&L/tax formula gaps are preserved before calibration anchors. Current first raw debt mismatches are Oborovo `2030-12-31` and TUHO `2030-06-30`; current first raw P&L/tax mismatches are Oborovo `2030-12-31` and TUHO `2030-06-30`.
- `formula_parity_workstreams` now points each of the next five formula-replacement streams to its native candidate payload, Excel payload, gap payload and current first mismatch.
- `calibration_scaffolding_inventory` currently shows three active bridge streams and two active anchor streams; no stream is marked ready for scaffolding removal yet.
- `full_horizon_period_parity_before_full_model_period_bridge` currently has remaining native formula mismatches in all three tracked groups for TUHO: operating CF, debt and P&L/tax.
- `full_horizon_period_parity` now confirms full-model period bridge parity for Oborovo and TUHO: operating CF, debt and P&L/tax groups have zero post-bridge mismatches.
- Oborovo and TUHO return KPI gap summaries are serialized before the full-model return bridge is applied.
- Oborovo and TUHO sponsor cash-flow gap summaries now identify the initial IDC convention difference before sponsor return bridge promotion.
- Oborovo and TUHO project cash-flow gap summaries are serialized before the full-model return bridge is applied. Current first full-model `fcf_for_banks` mismatches are Oborovo `2032-06-30` and TUHO `2031-12-31`; the tests now lock the mismatch values and max absolute deltas.
- Oborovo and TUHO debt gap summaries are serialized against full-model DS diagnostics. Current first debt formula mismatches are Oborovo `2032-06-30` and TUHO `2031-12-31`.
- Oborovo and TUHO P&L/tax gap summaries are serialized against full-model P&L/Dep diagnostics. Current first P&L/tax formula mismatches are Oborovo `2032-06-30` and TUHO `2031-12-31`.
- Oborovo and TUHO non-anchor period `cf_after_tax_keur` now reflects tax charges as `ebitda_keur - tax_keur`.
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

- None currently active in the full suite.

Known calibration caveat: the native-facing return KPIs and SHL decomposition now match the full-model extracts, but the underlying formula engine still contains calibration bridges. The next work is to replace those bridges with formula-level debt, tax, project cash-flow and SHL logic.

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

The module also contains a narrow, traceable Oborovo first-12 period-level OpEx override extracted from the Excel fixture. This is a calibration anchor, not the final long-term substitute for full line-item and bank-tax mapping.

`tests/test_opex.py` includes synthetic unit coverage for persistent OpEx step changes.

`tests/test_opex_excel_alignment.py` promotes Oborovo first-twelve-period OpEx to an active test.

`tests/test_oborovo_excel_reconciliation.py` promotes Oborovo first-twelve-period EBITDA to an active test.

### 5. Debt service diagnostics and DSCR schedule policy

`tests/test_debt_excel_alignment.py` separates debt service, senior interest, senior principal and the combined principal / interest split.

For the currently extracted Oborovo first-12 period rows, Excel DSCR target is 1.15. This does not support using 1.20 for the first-12 Oborovo PPA rows.

`tests/test_debt_dscr_schedule_policy.py` documents current project policy:

- TUHO uses dual DSCR schedule: 1.20 for the first 24 PPA periods, then 1.40 for merchant periods.
- Oborovo remains single-target 1.15 until later Excel rows are extracted and mapped.

`app/calibration.py` now builds senior-debt `rate_schedule` from actual operation period day fractions: `annual all-in rate * period.day_fraction`. This replaces the flat `annual_rate / 2` approximation in headless calibration runs and better matches Excel interest calculations for stub/irregular periods.

`app/calibration.py` also exposes `debt_decomposition` in the calibration payload so CLI/test output can inspect opening balance, closing balance, interest, principal, debt service and implied period rate directly.

`app/calibration.py` now applies a narrow Oborovo first-12 debt split calibration anchor extracted from the Excel DS sheet. This aligns first-12 senior interest, senior principal and senior balance rows while the full financing fee/rate mechanics are still being mapped. After the last explicit anchor, the diagnostic debt schedule now continues from the anchored closing balance using actual period day-count rates and the configured target DSCR instead of falling back to a one-period native balloon repayment.

`app/waterfall_core.py` now passes operation-only periods and schedules into `run_waterfall()` for the headless calibration path. This removes construction-period zero CFADS rows from debt sculpting and aligns debt amortization timing with the extracted Excel operating period rows.

`tests/test_finco_gpt_calibration_runner.py` now guards both paths: engine-aware run config builds day-count debt rates, while config without an engine intentionally preserves the legacy flat-rate fallback. It also asserts that the first and twelfth Oborovo debt split anchors are present in the calibration payload.

### 6. P&L / tax diagnostics

`app/calibration.py` now applies a narrow Oborovo first-12 P&L/tax calibration anchor extracted from the Excel P&L sheet. This aligns first-12 depreciation, taxable income and corporate tax rows while full asset-class depreciation, tax-loss and ATAD mechanics are still being mapped. Non-anchor rows now consistently recompute post-tax cash flow from EBITDA less tax when tax is present.

`tests/test_pl_tax_excel_alignment.py` promotes Oborovo first-twelve depreciation, taxable income and corporate tax rows to active reconciliation tests.

`tests/test_oborovo_excel_reconciliation.py` includes the same first-twelve P&L/tax reconciliation in the broad Oborovo scaffold.

`tests/test_finco_gpt_calibration_runner.py` asserts that the first and twelfth Oborovo P&L/tax anchors are present in the calibration payload.

### 7. Sponsor equity + SHL IRR diagnostics

`app/calibration.py` now exposes a separate `sponsor_equity_shl_irr` KPI instead of overloading the existing `equity_irr` KPI.

The new sponsor IRR cash-flow convention is explicit:

- Initial outflow: `share_capital_keur + shl_amount_keur + shl_idc_keur`.
- Periodic inflows: `distribution_keur + shl_interest_keur + shl_principal_keur`.
- Unpaid PIK/accrued SHL interest is not counted as investor cash inflow until it is actually paid.

`app/calibration.py` applies SHL cash-flow calibration anchors from the compact full-model extracts for all operating SHL lifecycle rows. This aligns paid SHL net interest, SHL principal flow, net dividend flow, gross shareholder-loan interest and closing balances across the full extracted lifecycle.

`tests/test_shl_excel_alignment.py` promotes Oborovo first-twelve SHL cash-flow, gross-interest and opening/closing balance rows to active reconciliation tests against the full-model extract. It also validates the full Excel-sourced Oborovo and TUHO SHL lifecycle payloads and the Excel-sourced sponsor equity + SHL cash-flow diagnostics.

The app `shl_decomposition` now uses the full extracted lifecycle for SHL opening/closing balance diagnostics. Formula-level replacement of the SHL bridge is still a future task.

`tests/test_shl_waterfall_priority.py` locks the confirmed business rule: SHL opening balance includes capitalized IDC; available post-senior cash pays SHL interest first, then SHL principal, then dividends only from residual cash; unpaid interest is capitalized/accrued.

`tests/test_finco_gpt_calibration_runner.py` guards the serialized sponsor cash-flow definition, SHL decomposition shape and the first/twelfth Oborovo SHL cash-flow anchors.

### 8. Project IRR diagnostics

`tests/test_project_irr_excel_alignment.py` now isolates the project IRR problem instead of treating it as a black-box KPI mismatch.

Active checks:

- Oborovo first-twelve operating project cash flow: Excel CF `free_cash_flow_for_banks_keur` vs app `cf_after_tax_keur`.
- Oborovo total capex anchor vs app total capex.
- Explicit diagnostic helper showing project operating cash-flow rows use post-tax unlevered operating CF.

`tests/test_full_model_extracts.py` now validates the full extracted Oborovo and TUHO model fixtures: 61-period SHL lifecycles and 61-row project/unlevered IRR cash-flow series directly from the uploaded `.xlsm` models.

`tests/test_full_model_extract_helpers.py` validates the reusable full-model extract helper layer directly, so project IRR, unlevered IRR, SHL lifecycle rows and sponsor equity + SHL IRR are no longer tested only through the calibration payload.

`tests/test_project_irr_excel_alignment.py` now validates that `run_project_calibration()` exposes the full extracted Excel cash-flow series, recomputes the Excel-sourced full-horizon project/unlevered IRR diagnostics, and promotes the relevant full-model IRR into the native-facing `project_irr` KPI.

`tests/test_project_irr_excel_alignment.py` also validates `engine_project_cash_flow_gap_before_full_model_calibration`, which isolates the remaining full-horizon period cash-flow formula deltas before the IRR bridge is applied.

`tests/test_tuho_excel_reconciliation.py` now validates TUHO native-facing project IRR and equity IRR against the Excel anchors.

## Next math-fix sequence

Work should continue in this order. Do not jump to UI polish before these are resolved.

### 1. Replace project IRR calibration bridge with formula logic

The extracted full Oborovo and TUHO project cash-flow series are now exposed in the headless calibration payload, recomputed with XIRR and promoted into native-facing KPIs. The remaining task is to rebuild native app project cash-flow generation so it reproduces those extracted Excel series without calibration-bridge promotion:

- exact construction-period capex timing;
- exact project vs unlevered cash-flow definitions;
- full operating and terminal cash-flow series;
- removal of the project IRR calibration bridge once native formula parity is reached.

### 2. Replace SHL lifecycle calibration bridge with formula logic

The extracted Oborovo and TUHO SHL lifecycle fixtures are now exposed and promoted into `shl_decomposition`. The remaining task is to rebuild native app SHL bridge logic so it reproduces the extracted full lifecycle without calibration-bridge promotion:

- SHL opening balance.
- Gross interest.
- Cash-paid interest.
- PIK/accrued/capitalized interest.
- Principal repayment.
- Closing balance.
- Dividend timing after SHL repayment.

### 3. Replace sponsor equity / SHL IRR calibration bridge with formula logic

Excel-sourced sponsor equity + SHL cash-flow diagnostics are now active, and TUHO equity IRR is active against the Excel anchor. The remaining task is to make native app sponsor cash-flow generation reproduce those rows directly:

- exact dividend/distribution timing;
- exact SHL paid-interest and principal timing;
- removal of the sponsor/equity calibration bridge once formula parity is reached.

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

A green test suite on this branch does not yet mean the model is full formula-level Excel parity. It means the branch has a reliable calibration harness with full-model extract parity and explicit calibration bridges.

The next meaningful milestone is replacing the full-horizon SHL calibration bridge with engine logic that reproduces the extracted 61-row Oborovo and TUHO SHL lifecycles directly.
