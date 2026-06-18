# Generic Validation Reference Excel Models

This folder contains the two external, independent reference Excel workbooks
built per `docs/generic_validation_reference_excel_spec.md`. They exist
**only** to validate the Finco1 Generic Solar and Generic Wind templates by
cell-by-cell comparison; they are not application artifacts, sales
collateral, or a replacement for the Finco1 runtime model.

## Files

| File | Template | Capacity | Construction | Horizon |
|---|---|---|---|---|
| `GenericSolar_ReferenceModel.xlsx` | Generic Solar PV | 50 MW | 12 months | 25 years |
| `GenericWind_ReferenceModel.xlsx` | Generic Wind Farm | 50 MW | 18 months | 25 years |

## Workbook conventions

- 11 tabs, in order: `Inputs`, `CapEx`, `IDC`, `OpEx`, `Revenue`,
  `Debt Service`, `P&L`, `Cash Flow`, `Equity`, `Summary`, `Methodology`.
- Currency: kEUR. Periods: semiannual (column C = first period onward).
- No VBA macros, no external workbook links, no protected sheets/cells.
- Every cell on the `Summary` tab is a live formula chained back to the
  detail tabs — none of the 15 required output anchors are hardcoded.
- Recalculation: forced full recalculation was performed programmatically
  (Python `formulas` engine, equivalent to a `Ctrl+Alt+F9` full recalc) to
  verify the formula graph resolves to finite values with no errors and no
  circular references. Opening either workbook in Excel or LibreOffice
  Calc with automatic calculation enabled (the default) will reproduce the
  same cached values.

## Metadata

```yaml
template: "Generic Solar" / "Generic Wind"
author: "Claude (AI financial modeler, Anthropic)"
organisation: "Finco1 / xofisamba"
date_created: "2026-06-18"
version: "1.0"
finco_spec_version: "0.1"
finco_commit_at_creation: "4bb27c43ee7122be2f9732b7b67afc22f1760254"
deviations_from_spec: see reports/generic_reference_model_build_report.md
known_limitations: see reports/generic_reference_model_build_report.md
recalculation_method: "Programmatic full recalculation (Python formulas engine); Excel/LibreOffice Ctrl+Alt+F9 equivalent on open"
rounding_convention: "0dp on kEUR, 4dp on ratios, 6dp on IRRs (display only)"
```

See `reports/generic_reference_model_build_report.md` for the full build
report, output anchor values, and documented deviations/simplifications.
