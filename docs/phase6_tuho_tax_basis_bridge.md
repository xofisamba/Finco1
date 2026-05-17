# Phase 6 TUHO Tax-Basis Bridge

## Purpose

Phase 7M isolated the TUHO R67 cash-tax timing mismatch. The Excel-style annual H2 diagnostic field reduces the R67 gap from `+18,183.2 kEUR` to `-1,334.8 kEUR`.

This document bridges the remaining residual. It is diagnostic only:

- no runtime tax formulas are changed
- no R99/R102 runtime source is accepted
- SHL FCF waterfall remains disabled by default
- project factories remain unchanged

## Excel References

Source workbook / fixture:

- Workbook: `C:\Users\Ivan\Desktop\modeli za rad\20260330_TUHO_BP.xlsm`
- Fixture: `tests/fixtures/excel_tuho_full_model_extract.json`

Operating periods start at 2030-06-30 and run for 60 semiannual periods.

| Sheet | Row / fixture field | Meaning |
| --- | --- | --- |
| `P&L` | R13 / `P&L.depreciation_keur` | P&L/tax depreciation used in EBT. |
| `P&L` | senior interest / `P&L.senior_interests_keur` | Senior interest deducted in EBT. |
| `P&L` | SHL interest / `P&L.shareholder_loan_interests_keur` | Shareholder-loan interest deducted in EBT. |
| `P&L` | R32 / `P&L.earnings_before_tax_keur` | Earnings before tax. |
| `P&L` | R35 / `P&L.taxable_income_keur` | Taxable income before loss-allocation rows in the fixture. |
| `P&L` | R36 | Losses N-1. |
| `P&L` | R37 | Allocated losses. |
| `P&L` | R38 | Losses N. |
| `P&L` | R41 | Taxable profit N. |
| `P&L` | R43 / `P&L.corporate_income_tax_keur` | Corporate income tax. |
| `P&L` | R44 | Tax payable feeding `CF!R67`. |
| `CF` | R67 / `CF.corporate_income_tax_keur` | Cash tax outflow, negative in cash-flow convention. |
| `Dep` | `Dep.depreciation_keur` | Depreciation schedule source. |

Excel R43/R44 cash-tax timing is annual H2 payment, already handled by the Phase 7M diagnostic field.

## Total Bridge

The bridge uses the Phase 7K explicit senior DS harness, so senior interest is already aligned.

| Component | Excel total | Python total | Delta |
| --- | ---: | ---: | ---: |
| Depreciation | 72,993.7 | 70,691.5 | -2,302.2 |
| Senior interest | 22,822.8 | 22,822.8 | 0.0 |
| SHL interest | 49,782.2 | 39,209.3 | -10,572.9 |
| EBT / Python EBT proxy | 193,569.0 | 205,655.6 | +12,086.6 |
| Excel taxable income fixture row / Python tax-after-loss basis | 184,326.3 | 219,864.9 | +35,538.6 |
| CIT | 38,240.9 | 39,575.7 | +1,334.8 |
| R67, Excel-style cash-tax timing | -38,240.9 | -39,575.7 | -1,334.8 |

The residual is not caused by senior debt service:

```text
Senior interest delta = 0.0 kEUR
```

It is not caused by R67 payment timing anymore:

```text
Current R67 gap before annual H2 diagnostic = +18,183.2 kEUR
Remaining R67 gap after annual H2 diagnostic = -1,334.8 kEUR
```

It is a tax-basis mismatch.

## Period Bridge

Selected periods requested for the bridge:

| op_idx | Date | Excel dep | Python dep | Excel EBT | Python EBT proxy | Excel CIT | Python CIT |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 2030-06-30 | 1,845.4 | 1,168.5 | -1,369.7 | 604.6 | 0.0 | 0.0 |
| 1 | 2030-12-31 | 1,876.0 | 1,187.9 | -1,381.4 | -330.1 | 0.0 | 0.0 |
| 2 | 2031-06-30 | 1,845.4 | 1,168.5 | -1,306.1 | -270.7 | 0.0 | 0.0 |
| 3 | 2031-12-31 | 1,876.0 | 1,187.9 | -1,314.9 | -247.9 | 0.0 | 0.0 |
| 24 | 2042-06-30 | 1,756.5 | 1,168.5 | 2,298.7 | 3,011.3 | 0.0 | 837.5 |
| 25 | 2042-12-31 | 1,785.6 | 1,187.9 | 2,475.0 | 3,139.0 | 120.2 | 865.4 |
| 26 | 2043-06-30 | 1,756.5 | 1,168.5 | 2,558.5 | 3,143.1 | 0.0 | 861.2 |
| 27 | 2043-12-31 | 1,785.6 | 1,187.9 | 2,748.4 | 3,276.3 | 955.2 | 890.1 |
| 28 | 2044-06-30 | 1,761.3 | 1,171.8 | 2,902.6 | 3,370.0 | 0.0 | 902.9 |
| 32 | 2046-06-30 | 1,756.5 | 1,168.5 | 3,844.7 | 4,300.6 | 0.0 | 945.2 |
| 35 | 2047-12-31 | 1,785.6 | 1,187.9 | 4,730.1 | 5,177.3 | 1,644.9 | 988.4 |
| 36 | 2048-06-30 | 1,761.3 | 1,171.8 | 5,003.8 | 5,466.4 | 0.0 | 1,001.5 |
| 37 | 2048-12-31 | 1,780.7 | 1,184.6 | 5,058.7 | 5,625.3 | 1,811.3 | 1,012.6 |
| 57 | 2058-12-31 | 0.0 | 1,187.9 | 8,357.7 | 7,040.0 | 2,984.2 | 1,267.2 |
| 58 | 2059-06-30 | 0.0 | 1,168.5 | 8,264.4 | 6,945.6 | 0.0 | 1,250.2 |
| 59 | 2059-12-31 | 0.0 | 1,187.9 | 8,401.4 | 7,060.7 | 2,999.9 | 1,270.9 |

The period bridge shows two tax-basis effects:

1. Python depreciation is materially lower than Excel in earlier operating periods, which raises Python EBT.
2. Python continues depreciation into late periods where the Excel fixture depreciation row is zero, which lowers Python EBT in the terminal years.

The SHL interest basis also differs materially. Excel deducts `49,782.2 kEUR`; Python deducts `39,209.3 kEUR`, a `-10,572.9 kEUR` delta that raises Python EBT.

## Residual Decomposition

The remaining R67 residual after timing correction is:

```text
Python Excel-style R67 diagnostic - Excel R67
= -39,575.7 - (-38,240.9)
= -1,334.8 kEUR
```

Visible drivers:

| Driver | Delta | Effect |
| --- | ---: | --- |
| Senior interest | 0.0 | Not a driver. |
| Depreciation | -2,302.2 | Python lower depreciation raises taxable basis early. |
| SHL interest | -10,572.9 | Python lower deductible SHL interest raises taxable basis. |
| EBT proxy | +12,086.6 | Combined visible basis effect before loss mechanics. |
| CIT | +1,334.8 | Net residual after loss/tax mechanics. |

The residual cannot be fully decomposed from current runtime fields because Python does not expose period-level equivalents for Excel:

- losses N-1
- allocated losses
- losses N
- taxable profit N before annual H2 pairing
- fiscal reintegration row equivalent

Those are the missing audit fields needed before any runtime tax change can be justified.

## Root Cause

The exact remaining source is the tax-basis layer, not cash-tax payment timing.

The exposed components show:

- senior debt is neutral
- depreciation basis differs
- SHL interest deduction basis differs
- loss carry-forward/allocation cannot yet be bridged period-by-period from runtime outputs

Therefore the residual is a combination of:

1. depreciation schedule mismatch
2. SHL interest basis mismatch
3. unexposed loss carry-forward / allocated-loss timing
4. possible fiscal reintegration mapping differences

## Runtime Decision

No runtime tax change is justified now.

The model needs a tax audit exposure PR before a formula PR:

- expose tax depreciation used by the tax engine
- expose fiscal reintegration
- expose taxable income before losses
- expose loss carry-forward opening/used/closing
- expose taxable income after losses
- expose CIT before cash-payment timing

Only after those fields exist can a safe tax-basis implementation be proposed.

## Recommended Next Branch

Recommended next branch:

`phase6-tax-audit-fields-runtime-visibility`

Scope:

- audit-only tax fields on the waterfall period/result
- no tax formula changes
- no R99 source acceptance
- no SHL opt-in

After that, use the new audit fields to decide whether a formula branch is warranted:

`phase6-tuho-tax-basis-runtime-alignment`
