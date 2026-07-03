# Stack V — Excel Audit Completeness

**Branch:** `stack-v-excel-audit-completeness`  
**Goal:** Improve auditability only. No KPI movement. No changes to engine logic.

---

## Sub-tasks

### V1 — All intermediate tax fields in the main CSV export

`utils/export.py` → `export_waterfall_csv`

The following columns are now written after `tax_keur` in the period-level CSV:

| Column | Description |
|---|---|
| `corporate_tax_cash_keur` | Cash CIT paid this period |
| `cit_accrual_audit_keur` | H1 CIT carry-forward to H2 settlement |
| `taxable_profit_keur` | Taxable income display field |
| `taxable_income_before_losses_audit_keur` | Taxable income before loss c/f |
| `taxable_profit_after_losses_audit_keur` | After applying loss carryforward |
| `tax_loss_opening_audit_keur` | Loss c/f opening balance |
| `tax_loss_used_audit_keur` | Losses consumed this period |
| `tax_loss_closing_audit_keur` | Losses remaining after this period |
| `fiscal_reintegration_audit_keur` | Fiscal reintegration amount |
| `tax_depreciation_audit_keur` | Tax depreciation used in CIT calc |
| `cash_tax_current_period_audit_keur` | Cash tax current period audit |
| `cash_tax_excel_style_h2_diagnostic_keur` | H2 diagnostic cross-check |
| `r67_excel_style_cash_tax_diagnostic_keur` | R67 Excel-style diagnostic |

### V2 — Formula source documentation

`utils/export.py` → `_FORMULA_SOURCES` dict + `export_formula_sources_csv`

`_FORMULA_SOURCES` is a module-level `dict[str, str]` mapping every CSV column name to a short string describing the engine module and formula that produces it.

`export_formula_sources_csv(filepath: str) -> None` writes a two-column CSV:

```
column_name,source
period,"waterfall_engine.py — period counter (0-based)"
...
```

### V3 — Tax calculation bridge CSV

`utils/export.py` → `export_tax_audit_csv`

`export_tax_audit_csv(result: WaterfallResult, filepath: str) -> None` writes one row per operating period with columns in logical audit order:

```
period, year_index, ebitda_keur, fiscal_reintegration_audit_keur,
taxable_income_before_losses_audit_keur, tax_loss_opening_audit_keur,
tax_loss_used_audit_keur, tax_loss_closing_audit_keur,
taxable_profit_after_losses_audit_keur, tax_depreciation_audit_keur,
tax_rate_pct, tax_accrued_keur, cit_accrual_audit_keur,
corporate_tax_cash_keur
```

`tax_rate_pct` is derived as `|tax_accrued| / taxable_after_losses × 100` (0 when taxable base is zero or negative).

---

## Tests

`tests/test_stack_v_excel_audit.py`

1. Main CSV contains all new audit columns.
2. `export_tax_audit_csv` produces correct columns.
3. `export_formula_sources_csv` produces a two-column CSV with header `[column_name, source]`.
4. No KPI movement: TUHO `equity_irr` ≈ 0.1132, Oborovo ≈ 0.1054 (±0.0003).
5. Audit CSV row count equals the number of operating periods.
6. `tax_accrued_keur` and `corporate_tax_cash_keur` are non-negative across all rows.

---

## Constraints respected

- Only `utils/export.py`, `tests/test_stack_v_excel_audit.py`, and this doc were modified.
- No changes to `waterfall_engine.py`, `waterfall_core.py`, `project_factories.py`, `app/excel_export.py`, templates, or any financial logic.
