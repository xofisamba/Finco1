# Phase 7M R67 Cash-Tax Diagnostic Field

## Purpose

This branch adds an audit-only Excel-style R67 cash-tax diagnostic field so TUHO R67/R99 diagnostics can show the cash-tax timing bridge directly in each waterfall period.

It does not change runtime tax formulas, tax payable, cash routing, R99/R102 source acceptance, SHL behavior, senior debt, revenue, OPEX, construction diagnostics, sponsor returns, or project factory settings.

## Field

Field name:

`r67_excel_style_cash_tax_diagnostic_keur`

Location:

`domain.waterfall.waterfall_engine.WaterfallPeriod`

Sign convention:

- Negative values are cash-tax outflows, matching Excel `CF!R67`.
- H1 periods are `0.0`.
- H2 periods equal the negative of current period tax plus previous period tax.

Formula:

```text
if period_in_year == 2:
    r67_excel_style_cash_tax_diagnostic_keur = -(previous_period.tax_keur + current_period.tax_keur)
else:
    r67_excel_style_cash_tax_diagnostic_keur = 0.0
```

This mirrors the Excel cash-tax timing identified in the R67 bridge:

`P&L!R43 = MAX(SUM(previous_half_year_taxable_profit, current_half_year_taxable_profit), 0) * tax_rate`

`CF!R67 = -P&L!R44`

## Diagnostic-Only Status

The new field is not used by:

- runtime tax payable
- `corporate_tax_cash_keur`
- `cf_after_tax_keur`
- `r69_fcf_banks_keur`
- `r84_fcf_junior_keur`
- `r98_distribution_account_keur`
- `r99_fcf_for_distribution_keur`
- `r102_fcf_for_shl_keur`
- SHL FCF waterfall
- distributions

The existing C1d audit chain remains unchanged and still uses `corporate_tax_cash_keur`.

## R67 Bridge

Prior Phase 7M bridge result:

| Measure | Total kEUR | Delta vs Excel |
| --- | ---: | ---: |
| Excel R67 | -38,240.9 | 0.0 |
| Current Python C1d cash-tax audit | -20,057.7 | +18,183.2 |
| Excel-style annual H2 diagnostic | -39,575.7 | -1,334.8 |

The diagnostic field reduces the visible R67 bridge gap from `+18,183.2 kEUR` to `-1,334.8 kEUR` by matching Excel's annual H2 cash-payment timing.

## Remaining Gap

The remaining `-1,334.8 kEUR` residual is not a payment-timing issue. It is still a tax-basis mapping issue.

Known contributors from the R67 bridge:

- Python tax depreciation is `2,302.2 kEUR` lower than Excel over the 60 operating periods.
- Excel includes fiscal reintegration, taxable-income, and loss carry-forward mechanics that are not yet fully mapped to the Python tax basis.
- The residual is upstream of the distribution account and independent of R100 carry-forward.

## Runtime Decision

Do not accept a runtime R99/R102 source from this field.

Do not enable SHL FCF waterfall from runtime R99/R102.

Do not replace `corporate_tax_cash_keur` with this field in runtime calculations.

This field exists only to make the R67/R99 diagnostic bridge faithful to Excel cash-tax payment timing.

## Next Recommended Branch

Recommended next branch:

`phase6-tuho-tax-basis-bridge`

Suggested scope:

- Bridge Excel tax depreciation, fiscal reintegration, taxable income, and loss carry-forward rows against Python tax outputs.
- Determine whether the remaining `-1,334.8 kEUR` R67 residual can be eliminated safely.
- Keep R99/R102 source acceptance blocked until tax-basis parity is proven.
