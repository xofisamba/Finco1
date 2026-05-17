# Phase 6 Loss Carry-Forward Window Design

## Executive Summary

TUHO and Oborovo Excel loss carry-forward formulas use a literal five-column rolling window. In semiannual operating periods, five columns means five periods, or 2.5 years. Croatian tax-law semantics require five years, which means ten semiannual periods.

The production architecture now supports both interpretations:

- Tax-law-correct mode: `duration_years * periods_per_year`.
- Excel compatibility mode: explicit `explicit_override_periods`, used only for workbook parity and regression analysis.

No runtime tax behavior changes in this branch. The change prepares the offline loss engine for a future decision about canonical tax semantics.

## Excel Formula Finding

The reverse-engineered Excel loss row uses a rolling-column pattern:

```text
R36 = SUMIF(IF(H4<=$B$36, ..., prev:OFFSET(prev,0,-$B$36+1)), "<0")
```

`$B$36 = 5`, and the formula rolls over five spreadsheet columns. Because TUHO and Oborovo are semiannual, the workbook behavior is five half-year periods rather than five calendar years.

## Window Semantics

| Frequency | Tax-law duration | Periods per year | Tax-law periods | Excel compatibility override |
| --- | ---: | ---: | ---: | ---: |
| Annual | 5 years | 1 | 5 | 5 |
| Semiannual | 5 years | 2 | 10 | 5 |
| Quarterly | 5 years | 4 | 20 | 5 only if explicitly requested |

The engine derives tax-law windows from years and frequency. It does not hardcode ten semiannual periods.

## Configuration Model

`LossCarryforwardConfig` now exposes:

| Field | Meaning |
| --- | --- |
| `duration_years` | Statutory carry-forward duration in years. |
| `periods_per_year` | Reporting/payment frequency. |
| `explicit_override_periods` | Optional compatibility override for workbook reproduction. |
| `expiry_method` | Currently `fifo_per_vintage`. |
| `country_template` | Metadata label for audit/export. |
| `duration_periods` | Computed active window. |

If `explicit_override_periods` is not set:

```text
duration_periods = duration_years * periods_per_year
```

If it is set:

```text
duration_periods = explicit_override_periods
```

## Croatia Template

The Croatia template builds tax-law-correct loss carry-forward semantics:

```text
duration_years = 5
expiry_method = fifo_per_vintage
duration_periods = 5 * periods_per_year
```

For semiannual periods, the template produces ten periods.

## Excel Compatibility Mode

Excel compatibility mode is explicit:

```python
LossCarryforwardConfig.excel_compatibility(override_periods=5)
```

This mode is for legacy workbook reproduction, parity diagnostics, and regression tests. It is not presented as tax-law-correct behavior.

## TUHO Quantified Impact

| Scenario | Window | CIT total |
| --- | ---: | ---: |
| Excel current workbook compatibility | 5 periods | 38,240.9 kEUR |
| Croatia tax-law-correct semiannual | 10 periods | 37,580.2 kEUR |
| Difference |  | -660.7 kEUR |

The 5-period workbook issue explains about 660.7 kEUR of CIT, or roughly 31% of the current 2,149.3 kEUR R67 residual. About 1,488.6 kEUR remains unresolved.

## Residual Decomposition

| Driver | Estimated amount | Status |
| --- | ---: | --- |
| Excel 5-period window vs 5-year law window | 660.7 kEUR | Explained |
| Remaining R35/tax-basis attribution | ~1,488.6 kEUR | Unresolved |
| Vintage tracking and bucket expiry detail | Unknown | Next branch |
| Minor local tax/WHT/reserve-interest rows | Unknown | Requires row attribution |

## Production Recommendation

Production default should be tax-law-correct. Excel compatibility should remain available as an explicit parity override because it is valuable for:

- reproducing the current TUHO/Oborovo workbook;
- measuring the impact of the apparent workbook porting issue;
- preserving regression tests while the sponsor decides which target is canonical.

The branch deliberately does not change runtime tax bridge outputs, R99/R102 acceptance, SHL FCF behavior, or project factories.

## Roadmap

1. `phase6-loss-engine-vintage-tracking`
   - proper FIFO per vintage;
   - expiry by bucket.

2. `phase6-r35-tax-bridge-row-attribution`
   - remaining ~1.49m kEUR residual;
   - depreciation basis;
   - R32/R35 semantics;
   - local tax/WHT/minor rows.

3. `phase6-cit-annual-h1h2-trigger`
   - annual H2-only CIT timing.

4. `phase6-r67-dual-target-validation`
   - validate against Excel compatibility target and tax-law-correct target.

5. `phase6-r99-runtime-source-promotion`
   - only after sponsor/user decision on canonical semantics.

## Runtime Safety

Runtime behavior changed: no.

The branch only prepares the offline loss carry-forward engine and tests. It does not add runtime flags, change existing expected values, accept R99/R102 as a runtime source, enable SHL FCF, opt in factories, or rewrite waterfall formulas.
