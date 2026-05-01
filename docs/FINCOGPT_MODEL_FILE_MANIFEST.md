# FincoGPT Excel Model File Manifest

This manifest records the Excel workbook files uploaded during FincoGPT calibration work. The raw `.xlsm` files are intentionally not committed to the repository. They remain conversation/session artifacts and should be re-uploaded when a new working session needs to extract additional calibration fixtures.

## Uploaded models in current session

### TUHO / Tuhobić

- Filename: `20260330_TUHO_BP.xlsm`
- Session path: `/mnt/data/20260330_TUHO_BP.xlsm`
- Size observed: `1.8M`
- SHA-256: `780779eba4278ccc2b8546a9411ccee24917d388f411ba60c88aa342cb5c727a`
- File type: `Microsoft Excel 2007+` / macro-enabled workbook

Observed workbook sheets:

- `FID deck outputs`
- `Discount rate NPV`
- `Outputs`
- `CapEx`
- `Scenarios`
- `OpEx`
- `Inputs`
- `IDC`
- `CF`
- `P&L`
- `BS`
- `Dep`
- `DS`
- `Eq`
- `Macro`
- `Flags`
- `Cash@Risk`

### Oborovo

- Filename: `20260414_BP_Oborovo_Sensitivity_FINAL for PPT.xlsm`
- Session path: `/mnt/data/20260414_BP_Oborovo_Sensitivity_FINAL for PPT.xlsm`
- Size observed: `1.5M`
- SHA-256: `15a621c4d6b79024980766e00ebc79d7235fd56f00567be7bf345c769ce57920`
- File type: `Microsoft Excel 2007+` / macro-enabled workbook

Observed workbook sheets:

- `FID deck outputs`
- `Discount rate NPV`
- `Outputs`
- `Inputs`
- `Scenarios`
- `CapEx`
- `OpEx`
- `IDC`
- `CF`
- `P&L`
- `BS`
- `Dep`
- `DS`
- `Eq`
- `Macro`
- `Flags`
- `Sheet1`

## Fixture extraction priorities

Use these files to replace temporary first-12 calibration anchors with full extracted fixtures and model logic.

### 1. Full SHL balance schedule

Extract from `Eq`, `P&L`, and/or `BS` sheets:

- SHL opening balance
- SHL gross interest
- SHL cash-paid interest
- SHL PIK / accrued / capitalized interest
- SHL principal repayment
- SHL closing balance
- dividend / distribution flows

### 2. Project IRR cash-flow series

Extract from `CF`, `CapEx`, `IDC`, `Outputs`, and `Discount rate NPV` sheets:

- construction-period capex timing
- IDC and financing-fee timing where relevant
- full operating project cash-flow series
- terminal / decommissioning / residual assumptions
- exact Excel IRR row and definition

### 3. TUHO fixture extension

Extend TUHO from first 3 period anchors to at least first 12 operating periods, then full operating horizon:

- revenue / generation
- OpEx
- EBITDA
- debt service and debt split
- P&L / tax
- SHL / equity cash flows

## Handling note

Do not commit the raw `.xlsm` workbooks unless explicitly requested. Commit JSON fixtures extracted from these models instead, so the repository remains lightweight and reviewable.
