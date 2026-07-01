# Excel Parity Stack F: Tax Engine → UI Wiring

**Branch:** `excel-parity-stack-f-tax-ui`
**Base:** `main`

## Overview

Stack F wires existing tax engine output from `WaterfallResult` into the Tax sheet UI (`sheet_tax.html`), following the exact same pattern established by Stack D (financial statements) and Stack E (debt schedule).

**No financial logic was changed.** The engine remains the single source of truth. The serializer only reads already-computed fields.

## Architecture

### Pattern (same as Stack D and E)

```
WaterfallResult.periods
  → _serialize_tax_schedule(result)          [project_runner.py]
  → "tax_schedule" key in run_project()      [project_runner.py]
  → tax_schedule=result.get("tax_schedule")  [run_service.py, 3 paths]
  → sessionStorage["lastTaxSchedule"]        [_build_sessionstorage_save_tag]
  → JS in sheet_tax.html reads + renders     [sheet_tax.html]
```

## F1 Audit: Tax Fields on WaterfallPeriod

The following fields exist on `WaterfallPeriod` (in `domain/waterfall/waterfall_engine.py`) and are serialized by `_serialize_tax_schedule()`:

| Field | Description |
|---|---|
| `taxable_profit_keur` | Taxable profit after losses (engine) |
| `tax_keur` | CIT accrual this period |
| `cf_after_tax_keur` | Post-tax cashflow (EBITDA - cash tax) |
| `corporate_tax_cash_keur` | Cash tax paid this period |
| `tax_depreciation_audit_keur` | Fiscal tax depreciation |
| `taxable_income_before_losses_audit_keur` | Taxable income before loss offset |
| `tax_loss_opening_audit_keur` | Loss carryforward opening balance |
| `tax_loss_used_audit_keur` | Losses applied this period |
| `tax_loss_closing_audit_keur` | Loss carryforward closing balance |
| `taxable_profit_after_losses_audit_keur` | Taxable profit after loss offset |
| `cit_accrual_audit_keur` | CIT accrual (audit version) |
| `cash_tax_current_period_audit_keur` | Cash tax current period (audit) |

### Summary Fields on WaterfallResult

| Field | Description |
|---|---|
| `total_tax_keur` | Total CIT accrual over project life |

## Changed Files

| File | Description |
|---|---|
| `app/api/project_runner.py` | Added `_serialize_tax_schedule(result)` + `"tax_schedule"` key in `run_project()` return |
| `app/services/run_service.py` | Added `tax_schedule` parameter to `_build_sessionstorage_save_tag()`, threaded through all 3 execution paths, added `ts_script` block writing `sessionStorage["lastTaxSchedule"]` |
| `app/templates/partials/sheet_tax.html` | Added `tax-schedule-block` div with table, JS reading `lastTaxSchedule`, rendering per-period rows; kept `tax-unavailable-panel` as pre-Run fallback |
| `tests/test_excel_parity_stack_f.py` | Characterization tests (25 tests) |
| `docs/EXCEL_PARITY_STACK_F_TAX_UI.md` | This documentation |

## sessionStorage Key

`lastTaxSchedule` — JSON-serialized dict with structure:

```json
{
  "periods": [
    {
      "period": 1,
      "date": "2025-06-30",
      "year_index": 1,
      "period_in_year": 1,
      "is_operation": true,
      "taxable_profit_keur": 1234.56,
      "tax_keur": 123.46,
      "cf_after_tax_keur": 5678.90,
      "corporate_tax_cash_keur": 0.0,
      "tax_depreciation_audit_keur": 500.0,
      "taxable_income_before_losses_audit_keur": 1234.56,
      "tax_loss_opening_audit_keur": 5000.0,
      "tax_loss_used_audit_keur": 0.0,
      "tax_loss_closing_audit_keur": 5000.0,
      "taxable_profit_after_losses_audit_keur": 1234.56,
      "cit_accrual_audit_keur": 123.46,
      "cash_tax_current_period_audit_keur": 0.0
    }
  ],
  "summary": {
    "total_tax_keur": 12345.67
  },
  "source": "WaterfallResult.periods (per-period engine output)"
}
```

## Guardrail Confirmation

- No financial formulas changed
- No tax calculations changed (engine remains single source of truth)
- No client-side JS calculations (JS only reads and renders engine data)
- `domain/*`, `waterfall_core.py`, `input_adapter.py`, `project_factories.py` untouched
- `tests/test_phase51f_parallel_work_guardrails.py` SHA pin not updated (project_factories.py was not modified)
