# Scenario Input Architecture — Oborovo OPEX

**Status**: Architecture freeze. Design only — no runtime implementation.

## Overview

The Oborovo financial model uses a two-layer input architecture for OPEX:

1. **Base Case** — all inputs sourced from the authoritative workbook's `Scenarios!E` column (base-case scenario).
2. **Scenario Overlay** — named scenarios override individual Scenarios cells; unoverridden inputs inherit the base-case value.

This document captures the structural design so it can be implemented correctly in a future sprint. It does not introduce any new runtime code.

---

## Layer 1: Base Case

Every OPEX line item has a budget value sourced from the `Scenarios` sheet, column E (base-case scenario). The mapping is:

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

Full row mapping is in `tests/fixtures/excel_oborovo_opex_structural_truth.json`.

---

## Layer 2: Scenario Overlays

A scenario is a named set of `(scenarios_row, new_value)` overrides. The runtime would:

1. Load the base-case fixture.
2. For each active scenario, apply overrides: `budget[scenarios_row] = override_value`.
3. Recompute annual values: `budget * (1 + inflation_rate) ** (year - 1)` (see special cases below).
4. Recompute B.13 contingencies: `0.04 * sum(annual_totals for B.01..B.12 + D + F, Claims excluded)`.

Scenarios are additive/stackable: multiple named scenarios can be applied in order (last write wins per row).

---

## Special Formula Cases

These deviations from the standard `budget * (1+inf)^(year-1)` formula must be handled explicitly:

### B.02 (Infrastructure Maintenance)
**Two-regime O&M**: B.02.1 is active Y1 only; B.02.2 is active Y3-Y30. Y1 annual total ≠ category budget.  
`annual_Y1 = 179 * 1 + 117 * 0 + ... = 179 kEUR` (approximately; see fixture for exact).

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
**Debt-tenor-driven**: B.11.3 activation = `IF(year <= Inputs!D196, 1, 0)` where D196 = 14 (senior debt tenor).  
Active Y1-Y14, zero Y15-Y30. This is not a flag but a formula — any scenario changing the debt tenor propagates automatically.

### B.12 (Environmental & Social)
**Monitoring expiry**: B.12.3 (Fauna & Flora) and B.12.5 (E&S monitoring) active Y1-Y2 only.  
`annual_Y1 = 32 kEUR`, `annual_Y3+ = 12 kEUR` (B.12.1 + B.12.6 only, before inflation).

### B.13 (Contingencies)
**Rate applied to total, not budget**: `annual_Yn = 0.04 * sum_of_all_other_annual_Yn`.  
Claims (category C) excluded from the sum. Salary (D) and Taxes (F) included but zero for Oborovo.

---

## Activation Flag Architecture

Each subitem has a Y1-Y30 flag vector (1 = active, 0 = inactive). The annual total for a category is:

```
annual_Yn = SUMPRODUCT(subitem_budgets, subitem_flags_Yn) * (1 + category_inflation) ** (year - 1)
```

Flags are structural truth (not scenario-overridable in the current workbook design). Activation changes require a new structural extraction.

Exception: **B.11.3** — activation is formula-driven by `Inputs!D196` (debt tenor), so scenarios that change senior debt tenor implicitly change B.11 activation range.

---

## Inflation Sources

| Category | Inflation source | Rate |
|----------|-----------------|------|
| B.01–B.06, B.10, B.11, B.12 | `Inputs!D85` (EUR CPI) | 2% |
| B.07 | Workbook D column (matches EUR CPI) | 2% |
| B.08 | Hardcoded `D=0` | 0% |
| B.09 | Hardcoded `D=0` | 0% |
| B.13 | `D=0.04` (contingency rate, not CPI) | 4% rate on base |

---

## What This Design Does NOT Cover

- No implementation of a Scenario runtime, database, or UI.
- No changes to `finco_core/` OPEX schedules.
- No changes to the financial waterfall.
- Depreciation, tax, merchant pricing, SHL, DSRA are out of scope.

See `tests/fixtures/excel_oborovo_opex_structural_truth.json` for the machine-readable structural truth.  
See `docs/reconciliation/oborovo_opex_structural_truth.md` for the human-readable audit report.
