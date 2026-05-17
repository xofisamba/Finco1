# Phase 7M R67 Cash-Tax Source Bridge

## Purpose

Phase 7M distribution-account bridging proved that TUHO Excel operating R84, R98, R99, and R102 are equal over the 60 operating periods, with no R100 carry-forward. The remaining Python R99/R102 gap therefore comes from upstream R69.

The largest R69 component delta is R67 cash tax:

| Component | Excel total | Python current audit total | Delta |
| --- | ---: | ---: | ---: |
| R67 cash tax | -38,240.9 | -20,057.7 | +18,183.2 |

This branch is diagnostic only. It does not change tax formulas, does not enable SHL FCF waterfall, does not accept a runtime R99/R102 source, and does not alter project factory behavior.

## Excel Formula References

Source workbook:

`C:\Users\Ivan\Desktop\modeli za rad\20260330_TUHO_BP.xlsm`

Operating periods start in column `H`. Column `G` is the construction/COD-prep period and is excluded from operating totals.

### Cash-Flow Sheet

Sheet: `CF`

| Excel row | Label | Formula pattern | Interpretation |
| ---: | --- | --- | --- |
| R67 | CorpTax | `=-'P&L'!H44` | Cash-flow tax is the negative of P&L row 44 tax payable. |

### P&L Tax Rows

Sheet: `P&L`

| Excel row | Label | Formula pattern | Interpretation |
| ---: | --- | --- | --- |
| R13 | Depreciation | linked from `Dep` | Tax/P&L depreciation basis used before taxable income. |
| R32 | EBT | workbook operating profit after financial items | Pre-tax profit before fiscal reintegration. |
| R34 | Fiscal Reintegration | workbook adjustment row | Tax adjustment included in taxable income. |
| R35 | Taxable Income | `=H34+H32` | EBT plus fiscal reintegration. |
| R36 | Losses N-1 | rolling loss formula | Prior losses available for allocation, subject to carry-forward rules. |
| R37 | Allocated losses | `=IF(AND(H36<=0,H32>0),MIN(ABS(H36),H32),0)` | Losses used against positive taxable profit. |
| R38 | Losses N | `=MIN(H37+H36,0)` | Closing tax-loss carry-forward. |
| R41 | Taxable Profit N | `=-H37+H35` | Taxable profit after allocated losses. |
| R43 | Corporate Income Tax | `=MAX(SUM(G41:H41),0)*$B43*(H4>0)*(MOD(H4,2)=0)` | Annual tax paid only in H2, using current and previous half-year taxable profit. |
| R44 | Tax payable | same total as R43 | Cash tax payable feeding `CF!R67`. |

Key finding: Excel does not pay tax every semiannual period. It pays annual cash tax in H2 periods using `SUM(previous_half_year_taxable_profit, current_half_year_taxable_profit)`.

## Total Bridge

The comparison below uses the Phase 7K explicit senior DS harness so senior debt service is not the driver.

| Measure | Total kEUR | Delta vs Excel R67 |
| --- | ---: | ---: |
| Excel R67 cash tax | -38,240.9 | 0.0 |
| Python current C1d cash-tax audit field | -20,057.7 | +18,183.2 |
| Python paired annual H2 tax reconstruction | -39,575.7 | -1,334.8 |

The paired annual H2 reconstruction applies this diagnostic formula:

```text
if period is H2:
    R67_cash_tax = -(current_period.tax_keur + previous_period.tax_keur)
else:
    R67_cash_tax = 0
```

That diagnostic pairing reduces the absolute R67 gap from 18,183.2 kEUR to 1,334.8 kEUR. Therefore most of the current Python R67 gap is cash-payment timing: the current audit field records current-period H2 tax instead of the Excel annual H1+H2 payment.

## Tax-Basis Bridge

After matching the annual H2 payment pattern, a smaller tax-basis mismatch remains.

| Component | Excel total | Python total | Delta |
| --- | ---: | ---: | ---: |
| Tax depreciation | 72,993.7 | 70,691.5 | -2,302.2 |
| Python tax accrual, signed | -39,575.7 | -39,575.7 | n/a |
| Excel R67 after timing match | -38,240.9 | -39,575.7 | -1,334.8 |

Excel P&L tax row totals over the operating periods:

| Excel row | Total kEUR |
| --- | ---: |
| P&L R13 depreciation | 72,993.7 |
| P&L R32 EBT | 193,569.0 |
| P&L R34 Fiscal Reintegration | -9,242.7 |
| P&L R35 Taxable Income | 184,326.3 |
| P&L R36 Losses N-1 | -37,087.2 |
| P&L R37 Allocated losses | 4,106.0 |
| P&L R38 Losses N | -166,716.5 |
| P&L R41 Taxable Profit N | 180,220.3 |
| P&L R43 Corporate Income Tax | 38,240.9 |
| P&L R44 Tax payable | 38,240.9 |

The residual 1,334.8 kEUR gap after H2 pairing is not explained by R99/R100 distribution-account logic or senior DS. It is a tax-basis issue, with depreciation and fiscal/taxable-income construction still not fully matched.

## Selected Period Bridge

| op_idx | Excel R67 | Python current R67 | Current delta | Python paired H2 R67 | Paired delta | Interpretation |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | No cash tax. |
| 1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | No cash tax. |
| 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | No cash tax. |
| 3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | No cash tax. |
| 24 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | H1 period; no Excel annual payment. |
| 25 | -120.2 | -865.4 | -745.2 | -1,702.9 | -1,582.7 | Pairing exposes remaining tax-basis mismatch. |
| 26 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | H1 period. |
| 27 | -955.2 | -890.1 | +65.1 | -1,751.3 | -796.1 | Excel annual payment; Python basis higher after pairing. |
| 28 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | H1 period. |
| 32 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | H1 period. |
| 35 | -1,644.9 | -988.4 | +656.5 | -1,960.8 | -315.8 | Current audit underpays H2; paired timing is closer. |
| 36 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | H1 period. |
| 37 | -1,811.3 | -1,012.6 | +798.7 | -2,014.1 | -202.9 | Current audit underpays H2; paired timing is closer. |
| 57 | -2,984.2 | -1,267.2 | +1,717.0 | -2,513.7 | +470.5 | Current audit underpays H2 materially. |
| 58 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | H1 period. |
| 59 | -2,999.9 | -1,270.9 | +1,728.9 | -2,521.1 | +478.7 | Current audit underpays H2 materially. |

## Root Cause

The R67 delta has two layers:

1. Cash-tax payment timing is the main issue. Excel pays annual tax in H2 using the current and previous semiannual taxable-profit rows. The current Python C1d `corporate_tax_cash_keur` audit field is not equivalent to that Excel cash-tax row; it behaves like a current-period H2 tax proxy. This explains most of the 18,183.2 kEUR R67 gap.
2. After annual H2 pairing, a smaller tax-basis mismatch remains. The likely sources are tax depreciation basis, fiscal reintegration, taxable-income construction, and loss carry-forward timing. Python depreciation is 2,302.2 kEUR lower than Excel over the operating periods, which points directly to tax-basis mapping rather than distribution-account mechanics.

The secondary R69 contributors from the prior bridge remain:

| Component | Delta |
| --- | ---: |
| R38 OPEX | -733.5 |
| R66 reserve interest | -55.0 |
| R67 current cash tax | +18,183.2 |

Senior DS is already neutral in the explicit senior DS harness. R100 carry-forward is zero. Therefore the remaining R99/R102 source gap is not caused by senior DS or distribution-account carry-forward.

## Can The Difference Be Eliminated Now?

Classification: **B. Yes, but full parity requires Phase 6 tax engine work.**

A small future diagnostic/audit improvement could expose an Excel-style annual H2 cash-tax field without changing runtime tax formulas. That would reduce the R67 bridge gap materially and make R99/R102 diagnostics more faithful.

However, accepting a runtime R99/R102 source is not justified yet because the remaining tax-basis gap is still outside the tolerance needed for SHL FCF waterfall production use. Full elimination requires mapping the Excel tax basis, especially depreciation, fiscal reintegration, taxable income, and loss carry-forward behavior.

## Runtime Decision

Do not accept `cf_after_tax - senior_ds` as an R99/R102 source.

Do not accept current C1d `corporate_tax_cash_keur` as Excel R67.

Do not enable SHL FCF waterfall from runtime R99/R102.

The Excel R67 bridge supports a next diagnostic implementation, not a production R99 source.

## Recommended Next Branch

Recommended next branch:

`phase7m-r67-cash-tax-diagnostic-field`

Suggested scope:

- Add an audit-only Excel-style annual H2 cash-tax diagnostic field.
- Keep runtime tax formulas unchanged.
- Keep SHL FCF waterfall disabled by default.
- Continue to reject runtime R99/R102 opt-in until tax-basis parity is proven.

Follow-on tax-basis branch:

`phase6-tuho-tax-basis-bridge`

Suggested scope:

- Map Excel depreciation, fiscal reintegration, taxable income, and loss carry-forward rows against Python tax outputs.
- Decide whether the remaining 1,334.8 kEUR R67 residual can be eliminated safely.
