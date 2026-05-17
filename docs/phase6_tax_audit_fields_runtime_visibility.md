# Phase 6 Tax Audit Fields Runtime Visibility

## Purpose

This branch exposes period-level tax-basis audit fields so the remaining TUHO tax residual can be bridged before any tax formula change.

It is audit-only:

- no tax formula changes
- no runtime cashflow changes
- no R99/R102 source acceptance
- no SHL FCF waterfall opt-in
- no project factory changes

## Added Fields

The fields are added to `domain.waterfall.waterfall_engine.WaterfallPeriod`.

| Field | Source | Populated? | Excel mapping | Notes |
| --- | --- | --- | --- | --- |
| `tax_depreciation_audit_keur` | runtime `dep` passed to `compute_period_tax` | Yes | P&L R13 / Dep depreciation | Current Python tax depreciation basis. |
| `fiscal_reintegration_audit_keur` | `fiscal_reintegration` local variable | Yes | P&L fiscal reintegration row | Currently zero in the active TUHO path because prior construction tax loss is preloaded. |
| `taxable_income_before_losses_audit_keur` | `TaxPeriodResult.taxable_income_before_losses_keur` | Yes | Taxable income before loss allocation | Current engine exposes non-negative pre-loss basis; signed negative pre-loss basis remains unmapped. |
| `tax_loss_opening_audit_keur` | loss carry-forward before tax calculation | Yes | Losses N-1 | Python opening loss pool for the period. |
| `tax_loss_used_audit_keur` | `TaxPeriodResult.loss_carryforward_applied_keur` | Yes | Allocated losses | Python loss used in the period. |
| `tax_loss_closing_audit_keur` | `TaxPeriodResult.loss_carryforward_remaining_keur` | Yes | Losses N | Python closing loss pool. |
| `taxable_profit_after_losses_audit_keur` | `TaxPeriodResult.taxable_income_keur` | Yes | Taxable profit N | Python taxable profit after losses. |
| `cit_accrual_audit_keur` | period `tax` / `TaxPeriodResult.tax_keur` | Yes | P&L R43 CIT | Accrual tax before cash-payment timing. |
| `cash_tax_current_period_audit_keur` | `tax_this_period` | Yes | Current Python cash-tax field | Positive cash tax paid in current Python H2-only timing. |
| `cash_tax_excel_style_h2_diagnostic_keur` | existing R67 diagnostic value | Yes | CF R67 timing diagnostic | Alias for `r67_excel_style_cash_tax_diagnostic_keur`. |

Existing field preserved:

| Field | Status |
| --- | --- |
| `r67_excel_style_cash_tax_diagnostic_keur` | Preserved unchanged. H1 is zero; H2 is `-(previous tax_keur + current tax_keur)`. |

## Diagnostic-Only Guardrails

The new fields do not feed:

- `compute_period_tax`
- `cf_after_tax_keur`
- `corporate_tax_cash_keur`
- R69/R84/R98/R99/R102 audit chain
- accepted R99/R102 runtime source
- SHL FCF waterfall
- distributions
- senior debt
- revenue, OPEX, construction, or sponsor calculations

The active cash tax remains:

```text
tax_this_period = tax if period_in_year == 2 else 0.0
```

The Excel-style R67 diagnostic remains separate:

```text
if period_in_year == 2:
    cash_tax_excel_style_h2_diagnostic_keur = -(previous_period.tax_keur + current_period.tax_keur)
else:
    cash_tax_excel_style_h2_diagnostic_keur = 0.0
```

## What This Enables

The previous bridge found the remaining R67 residual after Excel-style timing:

```text
Python Excel-style R67 diagnostic - Excel R67 = -1,334.8 kEUR
```

The newly exposed fields make it possible to compare period-by-period:

- Python depreciation basis vs Excel P&L R13 / Dep schedule
- Python fiscal reintegration vs Excel fiscal reintegration row
- Python opening loss pool vs Excel losses N-1
- Python loss used vs Excel allocated losses
- Python closing loss pool vs Excel losses N
- Python taxable profit after losses vs Excel taxable profit N
- Python CIT accrual vs Excel P&L R43

## Still Unmapped

The following are still not fully Excel-equivalent:

- signed taxable income before losses when Python pre-loss basis is negative
- Excel fiscal reintegration row details
- Excel-specific loss carry-forward expiry or period ageing, if any
- distinction between book depreciation and tax depreciation if the workbook uses separate bases
- SHL interest deduction basis used by Excel versus current Python SHL interest basis

These are visibility gaps or basis-design questions, not reasons to change formulas in this branch.

## Runtime Decision

No runtime tax change is justified here.

No R99/R102 runtime source is accepted.

SHL FCF waterfall remains blocked from live runtime R99/R102 inputs until tax basis and R99 source parity are proven.

## Next Branch Recommendation

Recommended next branch:

`phase6-tuho-tax-basis-period-comparison`

Scope:

- Use the new audit fields to build a full Excel-vs-Python period comparison.
- Quantify which residual periods are depreciation, fiscal reintegration, loss pool, or SHL interest basis.
- Continue to avoid tax formula changes until both total and period-level root causes are proven.

Possible later implementation branch:

`phase6-tuho-tax-basis-runtime-alignment`

Only start this if the period comparison proves a small, safe formula change.
