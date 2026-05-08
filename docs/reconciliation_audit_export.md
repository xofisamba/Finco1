# Reconciliation / Audit Export

**Date:** 2026-05-08
**Type:** Additive Feature (RC1 frozen)
**Status:** Implemented, ready for review

## Purpose

Add financial reconciliation/audit visibility so users and reviewers can understand model outputs and differences vs reference Excel. This is **additive only** — no model formula changes, no waterfall rewrites.

## Sheets Added (when `include_reconciliation_sheets=True`)

| Sheet | Description |
|-------|-------------|
| **Debt Schedule** | Period-by-period debt service reconciliation: opening/interest/principal/closing balance, CFADS, DSCR |
| **Project CF Bridge** | Revenue → OpEx → EBITDA → Tax → Project free CF → Cumulative CF |
| **Equity CF Bridge** | Equity investment / SHL service / distributions / DSRA movement / equity CF |
| **Calibration Notes** | Project/Equity IRR status, merchant curve profile, depreciation convention, sensitivity notes |

## How to Use

In Streamlit, check the box:
```
📋 Include Reconciliation Sheets (Debt Schedule, CF Bridges, Calibration Notes)
```

In code:
```python
from app.excel_export import build_excel_export
data = build_excel_export(
    result=result,
    project_inputs=project_inputs,
    include_reconciliation_sheets=True,  # ← opt-in
)
```

## What Each Table Means

### Debt Schedule
- **Opening/Closing balance**: Senior debt balance at start/end of period
- **Interest**: Interest portion of debt service
- **Principal**: Amortization portion of debt service
- **Total DS**: Total senior debt service (interest + principal)
- **CFADS**: EBITDA (cash available for debt service)
- **DSCR**: CFADS / Total DS — should be ≥ target (typically 1.15×)

### Project CF Bridge
- **Revenue**: PPA tariff (Y1-Y12) + merchant prices (Y13-Y30)
- **OpEx**: Operating costs (Oborovo: ~1,338 kEUR/yr after P0 fix)
- **EBITDA**: Revenue − OpEx
- **Unlevered Tax**: `tax_rate × max(0, EBITDA − depreciation)`
- **Project Free CF**: EBITDA − unlevered tax (capex in construction periods)
- **Cumulative Project CF**: Running total — XIRR of this = Project IRR

### Equity CF Bridge
- **Equity Investment**: Negative during construction (cash out)
- **SHL Interest / Principal**: Subordinated Hyun loan service
- **Distributions**: Equity distributions after senior debt + reserves
- **DSRA Movement**: DSRA contribution in period
- **Equity CF**: Distributions − SHL service − DSRA contribution

## Calibration Notes Content

For Oborovo Solar:
- Project IRR: 7.985% vs reference 7.96% (+0.025pp) ✅ Calibrated
- Equity IRR: 9.17% vs reference 10.60% (−1.43pp) ⚠️ Partially calibrated
- Merchant curve: CROATIA_SOLAR_AFRY_CENTRAL_2024 (Y13-Y30)
- Depreciation: 20y (book) / 25y (tax) per Croatia IBL profile

## Limitations

- **Not a substitute for external model audit or lender due diligence**
- Reconciliation sheets are model-internal summaries — Excel formulas not audited
- DSCR shown is sculpted/actual hybrid — check Debt Schedule for actual cashflows
- Equity IRR gap reflects modeling convention differences (depreciation timing, reserve conventions, sculpting method) — not bugs
- Model remains screening-grade, not lender-grade or bank-certified

## Backward Compatibility

Without `include_reconciliation_sheets=True`, Excel export is unchanged. All existing functionality preserved.

## Files Changed

- `app/reconciliation/__init__.py` — NEW registry module
- `app/reconciliation/debt.py` — NEW debt schedule rows builder
- `app/reconciliation/project_cashflow.py` — NEW project CF bridge builder
- `app/reconciliation/equity_cashflow.py` — NEW equity CF bridge builder
- `app/excel_export.py` — added optional reconciliation sheets
- `streamlit_app.py` — added reconciliation checkbox
- `tests/test_reconciliation_export.py` — NEW 19 regression tests
- `docs/known_limitations.md` — doc cleanup (duplicate table removed)
- `docs/reconciliation_audit_export.md` — NEW this file