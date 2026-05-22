# Phase 10 — Human-Readable Calibration Workbook

## Purpose

The Phase 10 calibration workbook (`reports/phase10_human_readable_calibration_workbook.xlsx`) is a reviewer-friendly Excel workbook that compares TUHO Wind 1 Excel vs Model values across all semiannual operating periods in a horizontal (period-as-columns) layout.

Target audiences:
- Calibration review (lender, auditor, internal finance)
- Identifying remaining deltas by line item
- Documenting runtime vs convention vs missing evidence
- Bridging Excel parity extracts to live runtime

## Workbook Structure

### 15 Sheets

| Sheet | Purpose |
|---|---|
| **Summary** | Headline KPIs (IRR, DSCR, revenue, OPEX, distributions), governance status, top deltas table |
| **Operations** | Installed capacity, production (MWh), availability — Excel/Model/Delta triplets |
| **Revenue** | Electricity revenue, CO2, balancing, total revenue — Excel/Model/Delta triplets |
| **OPEX/EBITDA** | OPEX, EBITDA, margin — Excel/Model/Delta triplets |
| **CAPEX Construction** | Total CAPEX, construction spend, IDC, fees, funding split — all MISSING_EVIDENCE |
| **Senior Debt** | Opening, interest, principal, DS, closing balance, DSCR — Excel/Model/Delta |
| **SHL** | Opening, gross accrued, cash interest, PIK, principal, closing, service — triplets |
| **Tax** | Book/tax depreciation, taxable income/R35, CIT/R67, tax losses — triplets + MISSING |
| **CFADS Waterfall** | EBITDA cash, tax cash, CFADS/R69, senior DS, FCF for SHL/R99, SHL service, R102 |
| **Distributions** | Distribution, legacy distribution, DA staging, equity invested/returned |
| **Returns** | Project IRR, equity IRR, avg/min DSCR, MOIC, reconciliation IRR |
| **Gap Analysis** | All deltas with severity, classification, root cause, recommended action |
| **Source Map** | Section, metric, Excel source, model source, source status |
| **Accepted Conventions** | 10 documented conventions (XIRR, SHL, OPEX, R35, CO2, DSCR, etc.) |
| **Governance** | G20 BLOCKED, R99/R102 NOT APPROVED, stakeholder decisions, runtime vs preview |

## Data Sources

### Excel Evidence
- All Excel values sourced from committed Phase 9 CSV extracts in `reports/`
  - `phase9_tuho_full_line_item_period_bridge.csv` — Operations, Revenue, OPEX, Senior Debt
  - `phase9_tuho_shl_period_bridge.csv` — SHL schedule
  - `phase9_tuho_full_line_item_parity_summary.csv` — parity summary
- **No new Excel values are fabricated** — if a row is not in a committed extract, it is marked `MISSING_EVIDENCE: [exact reason]`

### Model Evidence
- Model values sourced from live TUHO Wind 1 runtime via `run_demo_project('Wind', 'Base', project_inputs_override=create_default_tuho_wind1())`
- Returns `WaterfallResult` with 61 semiannual periods (P1–P61, 2030-06-30 to 2060-12-31)
- Period fields include: `generation_mwh`, `revenue_keur`, `opex_keur`, `ebitda_keur`, `senior_balance_keur`, `shl_balance_keur`, `dscr`, `distribution_keur`, `r69_fcf_banks_keur`, `corporate_tax_cash_keur`, `taxable_profit_keur`, etc.

### MISSING_EVIDENCE Policy
- Any Excel row not in a committed extract → `"MISSING_EVIDENCE: [exact reason]"`
- Any model value not exposed in runtime period data → `"MISSING_EVIDENCE: not exposed in runtime"`
- **Never write 0 for a missing value** — `0` means "truly zero"
- **Never silently fill missing values with zero**

## Excel vs Model Comparison Method

### Triplet Row Structure
For each metric, three consecutive rows:

```
Row N:   "Metric Name — Excel" | source | val_P1 | ... | val_P61 | Total | Status | Notes
Row N+1: "Metric Name — Model" | source | val_P1 | ... | val_P61 | Total | Status | Notes  
Row N+2: "Metric Name — Delta" |        | d_P1   | ... | d_P61   | Total | Status | Notes
```

### Status Classification
- **PASS**: |delta| < |value| × 0.001 + 0.1 (approximately machine epsilon level)
- **WARN**: |delta| ≥ threshold but < 5%
- **MISSING_EVIDENCE**: Either Excel or Model value missing
- **ACCEPTED_CONVENTION**: Delta is a documented convention difference
- **GOVERNANCE_BLOCKER**: G20/R99/R102 gate

### Color Coding
- PASS: `C6EFCE` (light green)
- WARN: `FFEB9C` (light yellow)
- MISSING_EVIDENCE: `FFC7CE` (light red)
- ACCEPTED_CONVENTION: `DDEBF7` (light blue)
- BLOCKED: `FF0000` (red)

## Runtime vs Preview Distinction

- **Runtime values**: sourced from live model run — marked as "Model" with source = "runtime"
- **Preview values**: all Excel columns that are MISSING_EVIDENCE (static illustrative values from prior phase)
- The workbook itself is a generated artifact — it does not update the UI or model state
- SessionStorage binding from `POST /run` continues to populate output tabs independently

## Accepted Conventions

1. **XIRR Date Convention**: Model uses mid-period convention; Excel may use actual dates
2. **SHL IDC Investment Base**: PIK compounds on investment base, not gross-up
3. **Distribution vs Dividend**: Model `distribution_keur` = cash wired to sponsor, not tax-classified dividend
4. **SHL Cash/Gross/PIK Presentation**: Model shows as three separate waterfall rows
5. **OPEX Grouping/Contingency Method**: Deterministic contingency method; TUHO Y1 = 1,998 kEUR
6. **R35 Taxable Income Residual**: Taxable income computed from pre-tax waterfall
7. **CO2 Revenue Feed**: Neither Excel nor Model has CO2 in committed extract/runtime period data
8. **DSCR = Infinity Convention**: When senior DS = 0, dscr = None (not infinity)
9. **SHL Principal Timing**: Repayment at period end per waterfall
10. **Waterfall Periodicity**: 61 semiannual periods, index 0 = P1 (2030-06-30)

## Known Limitations

- **Oborovo not included**: Oborovo Excel evidence not available in committed extracts
- **CO2 revenue**: Not in runtime period data; Excel-side also MISSING_EVIDENCE
- **Equity CF**: Sponsor equity invested/returned not in committed extract
- **Book depreciation**: MISSING_EVIDENCE in both Excel and Model
- **CAPEX/Construction**: All MISSING_EVIDENCE — no CAPEX source rows in committed extract
- **R35 taxable income (Excel)**: MISSING_EVIDENCE in committed extract
- **R67 CIT cash (Excel)**: MISSING_EVIDENCE in committed extract
- **No persistence**: Workbook generated on-demand, not stored in database

## No Runtime Formula Changes

This phase is **report-only**. No runtime model files were modified:

- ❌ `domain/waterfall/` — unchanged
- ❌ `domain/senior_debt/` — unchanged
- ❌ `domain/shl/` — unchanged
- ❌ `app/waterfall/` — unchanged
- ❌ `app/ui_runner.py` — unchanged
- ❌ `app/tax_bridge.py` — unchanged
- ❌ `app/project_factories.py` — unchanged
- ❌ `app/distribution_account.py` — unchanged

## Governance Status

| Gate | Status | Notes |
|---|---|---|
| **G20** | 🔴 BLOCKED | Tax rate assumption verification not complete. CO2 revenue acknowledged. |
| **R99** | 🟡 NOT APPROVED | DA/R99 staging mechanism pending board approval. |
| **R102** | 🟡 NOT APPROVED | SHL sweep trigger conditions under review. |

## Output Files

| File | Description |
|---|---|
| `reports/phase10_human_readable_calibration_workbook.xlsx` | 15-sheet horizontal calibration workbook |
| `reports/phase10_human_readable_calibration_summary.csv` | Headline KPIs and governance status |
| `reports/phase10_human_readable_calibration_gap_analysis.csv` | All deltas with classification and root cause |
| `reports/phase10_human_readable_calibration_source_map.csv` | Section/metric/source mapping |

## References

- Phase 9 full semester horizontal parity workbook: `reports/phase9_tuho_full_semester_horizontal_parity_workbook.xlsx`
- Phase 9 horizontal review workbook: `reports/phase9_tuho_full_line_item_horizontal_review_workbook.xlsx`
- Phase 9 accepted conventions: `reports/phase9_final_tuho_accepted_conventions.csv`
- Phase 9 TUHO calibration gap register: `reports/phase9_tuho_calibration_gap_register.csv`