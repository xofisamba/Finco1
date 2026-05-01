# Codex Handoff — FincoGPT Excel-Parity Branch

## Repository / branch

- Repository: `xofisamba/Finco1`
- Branch: `FincoGPT`
- Purpose: Excel-parity calibration branch for Oborovo and TUHO/Tuhobić project finance models.
- Instruction from project owner: work autonomously on `FincoGPT`; do not request approval for file changes in this branch.

## Uploaded Excel models used in this session

Raw `.xlsm` files are not committed to the repository. A manifest is committed at:

- `docs/FINCOGPT_MODEL_FILE_MANIFEST.md`

Current-session files were:

### Oborovo

- Session path: `/mnt/data/20260414_BP_Oborovo_Sensitivity_FINAL for PPT.xlsm`
- SHA-256: `15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920`
- Sheets observed: `FID deck outputs`, `Discount rate NPV`, `Outputs`, `Inputs`, `Scenarios`, `CapEx`, `OpEx`, `IDC`, `CF`, `P&L`, `BS`, `Dep`, `DS`, `Eq`, `Macro`, `Flags`, `Sheet1`

### TUHO / Tuhobić

- Session path: `/mnt/data/20260330_TUHO_BP.xlsm`
- SHA-256: `780779eba4278ccc2b8546a9411ccee24917d388f411ba60c88aa342cb5c727a`
- Sheets observed: `FID deck outputs`, `Discount rate NPV`, `Outputs`, `CapEx`, `Scenarios`, `OpEx`, `Inputs`, `IDC`, `CF`, `P&L`, `BS`, `Dep`, `DS`, `Eq`, `Macro`, `Flags`, `Cash@Risk`

Important: if Codex runs in a fresh environment, these Excel files may need to be re-uploaded or copied into the workspace. The repo contains compact JSON extracts and fixtures, not the raw workbooks.

## High-level calibration state

The branch has been converted from a UI-driven Streamlit model toward a headless, testable Excel-reconciliation model.

Core goal is not UI polish yet. The goal is first to make financial logic reproducible and comparable against the Excel workbooks.

## Main architectural files

- `app/waterfall_core.py`
  - Streamlit-free waterfall core used by calibration/tests.
  - Now passes operation-only periods/schedules into `run_waterfall()` for headless calibration to avoid construction-zero CFADS shifting debt sculpting.

- `app/calibration.py`
  - Main serialization and headless calibration helper.
  - Serializes waterfall KPIs and period rows.
  - Adds reconciliation decomposition payloads:
    - `revenue_decomposition`
    - `debt_decomposition`
    - `shl_decomposition`
    - `sponsor_equity_shl_cash_flows`
  - Adds explicit KPI:
    - `sponsor_equity_shl_irr`
  - Applies temporary narrow Excel anchors for Oborovo first12 debt split, P&L/tax, and SHL cash flows.

- `app/calibration_runner.py`
  - Backward-compatible wrapper around calibration helpers.

- `domain/waterfall/waterfall_engine.py`
  - Main waterfall implementation.
  - Includes SHL period logic via `compute_shl_period()`.
  - Needs future replacement/extension to fully reproduce Excel debt/SHL/tax logic without temporary anchors.

- `domain/period_engine.py`
  - Period schedule generation.
  - Adjusted for Excel-like COD boundary handling and semiannual period dates.

- `domain/revenue/generation.py`
  - Revenue decomposition helpers and PPA/merchant/certificates/balancing components.

- `domain/opex/projections.py`
  - OpEx schedule logic.
  - Includes persistent step-change behavior and temporary Oborovo first12 calibration anchors.

## Key fixture files

Existing / important fixtures:

- `tests/fixtures/excel_calibration_targets.json`
- `tests/fixtures/excel_golden_oborovo.json`
- `tests/fixtures/excel_golden_tuho.json`
- `tests/fixtures/excel_oborovo_periods.json`
  - Oborovo first12 operating period rows.
  - Contains CF, P&L, DS, Eq values used by active reconciliation tests.
- `tests/fixtures/excel_tuho_periods.json`
  - TUHO first3 operating period rows.
- `tests/fixtures/excel_oborovo_full_model_extract.json`
  - Compact full extract from Oborovo workbook.
  - Contains 61 SHL rows and 61 project/unlevered IRR cash-flow rows.
  - Important: 61 rows = 1 construction/COD boundary row + 60 operating semiannual rows.
  - First SHL row `2030-06-30` is not an operating revenue row; it forms opening SHL balance from SHL draw + capitalized construction-period SHL interest/IDC.

## Current Oborovo active reconciliation coverage

Active, non-xfail checks cover:

- first12 revenue
- first12 OpEx
- first12 EBITDA
- first12 senior debt service
- first12 senior interest
- first12 senior principal
- first12 combined senior principal/interest split
- first12 depreciation
- first12 taxable income
- first12 corporate tax
- first12 SHL cash-flow rows from Eq sheet:
  - SHL principal flow
  - SHL net interest flow
  - net dividend flow
- first12 gross SHL interest from P&L sheet
- first12 post-tax unlevered operating CF:
  - Excel CF `free_cash_flow_for_banks_keur`
  - App `cf_after_tax_keur`
- total capex anchor
- operation-only calibration period rows
- first-period opening senior debt balance
- sponsor equity + SHL cash-flow definition
- full Oborovo fixture shape and lifecycle checks

## Temporary anchors currently applied in code

These anchors are intentionally transparent but not enterprise-grade final logic.

### In `app/calibration.py`

- `OBOROVO_DEBT_SPLIT_ANCHORS`
  - First12 senior principal/interest anchors from Excel DS sheet.

- `OBOROVO_PL_TAX_ANCHORS`
  - First12 depreciation, taxable income, corporate tax anchors from Excel P&L sheet.

- `OBOROVO_SHL_CASH_FLOW_ANCHORS`
  - First12 paid SHL net interest, SHL principal flow, net dividends from Eq sheet.
  - Gross SHL interest from P&L sheet.
  - Capitalized/PIK interest is currently derived as `gross_interest - paid_interest`.

These are calibration scaffolding, not final model logic. The long-term objective is to replace them with actual formula logic extracted/reconstructed from the Excel model.

## SHL business rules confirmed by project owner

The project owner clarified:

- Investor IRR should likely be combined equity + SHL invested.
- SHL has IDC during construction that is capitalized into opening SHL balance.
- SHL interest accrues by period.
- After senior debt service, available cash goes to SHL first.
- SHL waterfall priority:
  1. pay SHL interest
  2. repay SHL principal
  3. pay dividends only from residual cash after SHL service
- If there is not enough free cash flow for SHL, part is paid and part is accrued/capitalized/PIK.

Tests added to encode this:

- `tests/test_shl_waterfall_priority.py`

Important detail from full Oborovo extract:

- First SHL row: `2030-06-30`
- This is the construction/COD boundary row.
- It contains opening SHL formation, not operating revenue.
- It includes initial SHL draw/investment and capitalized interest/IDC.
- The first operating row is `2030-12-31`.

## Sponsor equity + SHL IRR convention now serialized

`app/calibration.py` now exposes:

- `payload["investor_cash_flow_definition"]`
- `payload["sponsor_equity_shl_cash_flows"]`
- `payload["kpis"]["sponsor_equity_shl_irr"]`

Current convention:

- Initial outflow = `share_capital_keur + shl_amount_keur + shl_idc_keur`
- Periodic inflow = `distribution_keur + shl_interest_keur + shl_principal_keur`
- Unpaid PIK/accrued interest is not investor cash inflow until paid.

Relevant tests:

- `tests/test_finco_gpt_calibration_runner.py`
- `tests/test_shl_excel_alignment.py`

## Current xfail / known gaps

Known gaps are intentional and documented:

- Oborovo project IRR vs app engine remains xfail until app project CF uses/reproduces the full Excel cash-flow series.
- Oborovo full SHL opening/closing balance schedule vs app engine remains xfail until app SHL bridge reproduces the extracted full SHL lifecycle.
- TUHO project IRR vs Excel remains xfail.
- TUHO equity IRR vs Excel remains xfail.
- TUHO first3 core lines remain xfail/diagnostic.
- TUHO P&L/tax remains xfail/diagnostic.
- TUHO SHL cash-flow rows remain xfail/diagnostic.

## Important tests to run

Suggested quick suite:

```bash
pytest tests/test_finco_gpt_calibration_runner.py \
       tests/test_debt_excel_alignment.py \
       tests/test_pl_tax_excel_alignment.py \
       tests/test_shl_excel_alignment.py \
       tests/test_shl_waterfall_priority.py \
       tests/test_project_irr_excel_alignment.py \
       tests/test_full_model_extracts.py
```

Potential full suite:

```bash
pytest
```

## Immediate next tasks for Codex

### 1. Verify fixture JSON validity and run tests

A prior automated step initially wrote a placeholder to `excel_oborovo_full_model_extract.json` but it was then replaced with compact JSON. Verify this file parses and tests pass.

### 2. Add TUHO full model extract

A local extraction was started conceptually but not committed.

Need to create:

- `tests/fixtures/excel_tuho_full_model_extract.json`

It should mirror the Oborovo structure:

```json
{
  "project_key": "tuho",
  "workbook_sha256": "780779eba4278ccc2b8546a9411ccee24917d388f411ba60c88aa342cb5c727a",
  "shl_columns": ["date", "opening", "closing", "gross_interest", "principal_flow", "paid_net_interest", "capitalized_interest", "net_dividend"],
  "shl": [...],
  "project_cf_columns": ["date", "project_irr_cf", "unlevered_project_irr_cf", "fcf_for_banks"],
  "project_cf": [...],
  "excel_project_irr": ...,
  "excel_unlevered_project_irr": ...
}
```

Recommended workbook sheets to inspect:

- `CF`
- `P&L`
- `BS`
- `Eq`
- `Outputs`
- `Discount rate NPV`
- `IDC`

### 3. Promote full Oborovo project IRR fixture check

Use `tests/fixtures/excel_oborovo_full_model_extract.json` to compute XIRR over `unlevered_project_irr_cf` and compare against `excel_unlevered_project_irr`.

Add to `tests/test_full_model_extracts.py` or `tests/test_project_irr_excel_alignment.py`.

Potential implementation:

- Parse dates from `project_cf[*][0]`
- Cash flows from `project_cf[*][2]`
- Use `domain.returns.xirr.xirr`
- Compare to `0.08280167281627655`

### 4. Replace app project IRR logic or add explicit Excel-sourced parity KPI

Two possible tracks:

A. Short-term calibration track:
- Add a separate `excel_unlevered_project_irr_from_fixture` diagnostic in tests only.
- Do not change production app KPI yet.

B. Engine parity track:
- Rebuild app project CF generation to match Excel full series without fixture anchors.
- Then promote `test_oborovo_project_irr_against_excel` from xfail.

Preferred enterprise-grade path is B, but A is useful for diagnostics.

### 5. Full SHL balance schedule parity

Use `excel_oborovo_full_model_extract.json` `shl` table to compare app `shl_decomposition` over all rows.

Current app `shl_decomposition` is only partially aligned via first12 anchors and does not reproduce the full lifecycle.

Future logic should reproduce:

- construction/COD boundary SHL opening/closing
- capitalized SHL IDC
- gross interest
- cash-paid interest
- capitalized interest
- principal repayment starting later
- dividend timing after SHL zero balance

### 6. Replace temporary anchors with real logic

The code currently has first12 anchors in `app/calibration.py`. Do not remove until proper model logic passes tests.

Replace progressively:

- debt split anchors → debt/interest fee mechanics
- P&L/tax anchors → asset-class depreciation, tax loss, ATAD rules
- SHL anchors → full SHL lifecycle logic
- OpEx first12 anchors → full line-item OpEx schedule

## Files changed / added in this workstream

Important added/updated files include:

- `docs/FINCOGPT_CALIBRATION_STATUS.md`
- `docs/FINCOGPT_MODEL_FILE_MANIFEST.md`
- `docs/CODEX_HANDOFF_FINCOGPT.md`
- `app/calibration.py`
- `app/waterfall_core.py`
- `tests/test_finco_gpt_calibration_runner.py`
- `tests/test_debt_excel_alignment.py`
- `tests/test_oborovo_excel_reconciliation.py`
- `tests/test_pl_tax_excel_alignment.py`
- `tests/test_shl_excel_alignment.py`
- `tests/test_shl_waterfall_priority.py`
- `tests/test_project_irr_excel_alignment.py`
- `tests/test_full_model_extracts.py`
- `tests/fixtures/excel_oborovo_full_model_extract.json`

## Caution / review notes

- The branch is many commits ahead of `main`; review in small logical chunks.
- Some commits were calibration scaffolding and may not be production-quality final design.
- Do not interpret green tests as full enterprise-grade parity yet.
- The current test suite documents known gaps with xfails and explicit fixture anchors.
- The raw Excel models are not in git; keep it that way unless the owner explicitly requests committing them.
- Prefer committing extracted JSON fixtures rather than binary Excel files.

## Recommended Codex starting prompt

```text
You are working in repository xofisamba/Finco1 on branch FincoGPT.
Read docs/CODEX_HANDOFF_FINCOGPT.md, docs/FINCOGPT_CALIBRATION_STATUS.md, and docs/FINCOGPT_MODEL_FILE_MANIFEST.md.
Run the targeted pytest suite listed in the handoff.
Then continue with the next task: validate tests/fixtures/excel_oborovo_full_model_extract.json, compute XIRR from its unlevered_project_irr_cf series, and add/adjust tests so the extracted Excel unlevered IRR is verified against the anchor 0.08280167281627655. After that, add the analogous TUHO full model extract fixture from the uploaded TUHO workbook if available.
```
