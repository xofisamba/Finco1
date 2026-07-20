# Scenario Input Architecture — Oborovo OPEX

**Status**: Architecture freeze. Design only — no runtime implementation.

## Overview

The Oborovo financial model uses a single-selection scenario architecture for OPEX:

- **Base Project Inputs** — budget values read directly from the authoritative workbook's `Scenarios!E` column, which itself is formula-driven: `=INDEX(H<row>:K<row>,0,MATCH($E$4,$H$4:$K$4,0))`. Column E resolves to whichever of the four named scenarios (H–K) is selected by the index in `Scenarios!E4`.
- **One Selected Named Scenario** — the workbook's `Scenarios!E4` selector picks exactly one column (H=1, I=2, J=3, K=4). All `Scenarios!E` cells resolve to that scenario's values. There is no multi-layer stacking.
- **Resolved Immutable Inputs** — the resolved `Scenarios!E` values, together with shared parameters (`Inputs!D85`, `Inputs!D196`, etc.), form a fully determined input set. These feed the clean computation engine.

This document captures the structural design so it can be implemented correctly in a future sprint. It does not introduce any new runtime code.

---

## Named Scenarios (Workbook)

The workbook defines four named scenarios in the `Scenarios` sheet, rows 3–4, columns H–K:

| Column | Index | Name |
|--------|-------|------|
| H | 1 | HYBRID |
| I | 2 | Fixed NEW OPEX TEMPLATE |
| J | 3 | Tracker system NEW OPEX TEMPLATE |
| K | 4 | DCSA to RTB, no DEV costs |

`Scenarios!E4` holds the active index (currently `4` → column K). Every OPEX budget cell in column E is `=INDEX(H<row>:K<row>,0,MATCH($E$4,$H$4:$K$4,0))`, resolving to the K-column value when E4=4.

The fixture records `scenarios.selected_index`, `scenarios.selected_column`, and per-subitem `budget.scenarios_lineage.per_scenario_values` (H/I/J/K) so all four scenarios are machine-readable without re-running the extractor.

---

## Scenarios Row Mapping

Every OPEX subitem whose budget is formula-driven by the Scenarios sheet has a `scenarios_row` recorded in the fixture. Key rows:

| Category | Name | Scenarios row |
|----------|------|---------------|
| B.01 | Technical Management | 236 |
| B.01.1 | Asset Management Contract | 237 |
| B.01.2 | Bazefield | 239 |
| B.02 | Infrastructure Maintenance | 241 |
| B.02.1 | O&M Y1-2 | 242 |
| B.02.2 | O&M Y3-30 | 243 |
| B.02.4 | Inverter service contract / MRA | 247 |
| B.02.5 | Spare parts reprocurement | 248 |
| B.03 | Maintain Site | 264 |
| B.04 | Clean Material | 269 |
| B.05 | Security | 273 |
| B.06 | Insurance | 277 |
| B.07 | Lease & property Tax | 282 |
| B.08 | Power Expenses | 287 |
| B.08.3 | Balancing costs (input: eur/MWh) | 290–291 |
| B.09 | Fees | 292 |
| B.10 | Audit & Accounting & Legal Fees | 297 |
| B.11 | Bank Fees | 304 |
| B.12 | Environmental & Social management | 309 |
| B.13 | Contingencies (rate = 4%) | 315 |

Full row mapping with per-scenario values is in `tests/fixtures/excel_oborovo_opex_structural_truth.json`.

---

## Special Formula Cases

These deviations from the standard `budget * (1+inf)^(year-1)` formula must be handled explicitly:

### B.02 (Infrastructure Maintenance)
**Two-regime O&M with label/flag mismatch**: B.02.1 is labeled "Y1-2" but actual activation flags show Y1=1, Y2=0 only (active Y1 only). B.02.2 is labeled "Y3-30" but actual flags show Y2=1 through Y30=1 (active Y2-Y30). The workbook labels are misleading; the fixture's `label_flag_mismatch` fields record the true activation.

### B.07 (Land Leases)
**Pre-COD inflation base**: The workbook applies inflation starting from year 0 (pre-COD), not year 1.  
`annual_Y1 = 204 * 1.02 = 208.08 kEUR` (exponent = year, not year-1).

### B.08 (Power Expenses)
**Zero inflation, step change at Y11**: B.08.3 Balancing costs OFF for Y1–Y10, ON from Y11.  
`annual_Y1-10 = 176.8608 kEUR`, `annual_Y11-30 = 549.7632 kEUR`.

### B.09 (Fees)
**Zero inflation**: Flat 14 kEUR per year.

### B.10 (Audit Fees)
**Auditor step-down**: B.10.1 (16 kEUR) active Y1-Y2 only; B.10.2 (8 kEUR) active Y3-Y30.  
`annual_Y1 = 24 kEUR`, `annual_Y3+ = 16 kEUR` (before inflation).

### B.11 (Bank Fees)
**Debt-tenor-driven activation**: B.11.3 activation formula (read from `OpEx!F68`) is `=IF(F2<=Inputs!$D$196,1,0)` where `Inputs!D196` = 14 (senior debt tenor, sourced from `=Scenarios!E345`). Active Y1-Y14, zero Y15-Y30. This is not a static flag — it tracks the senior debt tenor cell.

### B.12 (Environmental & Social)
**Monitoring expiry**: B.12.3 (Fauna & Flora) and B.12.5 (E&S monitoring) active Y1-Y2 only.  
`annual_Y1 = 32 kEUR`, `annual_Y3+ = 12 kEUR` (B.12.1 + B.12.6 only, before inflation).

### B.13 (Contingencies)
**Rate applied to annual totals, not budget**: `annual_Yn = 0.04 * sum_of_all_other_annual_Yn`.  
Base includes B.01-B.12 + D (Salary) + F (Taxes); Claims (category C) are explicitly excluded.  
Rate cell: `OpEx!D76`. Base rows: `[3,8,26,31,35,39,45,48,53,58,65,70,82,90]`.

---

## Activation Flag Architecture

Each subitem has a Y1-Y30 flag vector (1 = active, 0 = inactive). The annual total for a category is:

```
annual_Yn = SUMPRODUCT(subitem_budgets, subitem_flags_Yn) * (1 + category_inflation) ** (year - 1)
```

Flags are structural truth captured by the extractor. Activation changes require a new structural extraction.

Exception: **B.11.3** — activation is formula-driven by `Inputs!D196` (debt tenor). A scenario that changes senior debt tenor implicitly changes the B.11 activation range; the formula must be re-evaluated against the scenario's debt tenor value.

---

## Inflation Sources

| Category | Inflation source | Rate |
|----------|-----------------|------|
| B.01–B.06, B.10, B.11, B.12 | `Inputs!D85` (EUR CPI) → `=D93` → 0.02 | 2% |
| B.07 | Workbook D column (matches EUR CPI, exponent = year) | 2% |
| B.08 | Hardcoded `D=0` | 0% |
| B.09 | Hardcoded `D=0` | 0% |
| B.13 | `D=0.04` (contingency rate, not CPI) | 4% rate on base |

Inflation chain is fully traced in the fixture: `inputs.inflation_rate.chain` records `OpEx!C102 → Inputs!D85 → Inputs!D93 → 0.02`.

---

## What This Design Does NOT Cover

- No implementation of a Scenario runtime, database, or UI.
- No multi-scenario stacking or last-write-wins composition — the workbook selects exactly one scenario.
- No changes to `finco_core/` OPEX schedules.
- No changes to the financial waterfall.
- Depreciation, tax, merchant pricing, SHL, DSRA are out of scope.

See `tests/fixtures/excel_oborovo_opex_structural_truth.json` for the machine-readable structural truth.  
See `docs/reconciliation/oborovo_opex_structural_truth.md` for the human-readable audit report.
