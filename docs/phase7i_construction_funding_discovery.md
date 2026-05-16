# Phase 7I Construction Funding Discovery

This is an offline discovery note. It does not change runtime model behavior.

Sources inspected:

- TUHO: `20260330_TUHO_BP.xlsm`
- Oborovo: `20260414_BP_Oborovo_Sensitivity_FINAL for PPT.xlsm`

Primary Excel sheets used:

- `Inputs`: project dates, construction time, source amounts, SHL investment date, funding flags.
- `IDC`: construction phase, monthly utilisation, sources, funding costs, VAT facility.
- `CapEx`: total capex and IDC / commitment fee links.
- `DS`: construction funding links into senior debt and SHL debt schedules.
- `Eq`: SHL and equity construction financing flows.

## Executive Findings

Do not assume a 24-month linear construction draw.

TUHO and Oborovo both use monthly construction-period calculations, but with
different construction durations and non-linear aggregate utilisation profiles.
The funding source logic is also not a simple simultaneous pro-rata funding
percentage. In the inspected Excel models, equity share capital and SHL fund
first, and senior debt funds the residual construction requirement after those
sources are exhausted.

The TUHO known SHL calibration target is explained directly by the Excel SHL
construction IDC formula:

```text
SHL IDC = SHL draw * ((1 + SHL rate) ^ ((COD - investment date) / equity_year) - 1)
```

For TUHO:

- SHL draw: 29,135.176 kEUR (`Inputs!D311`, `IDC!D46`, `DS!B134`)
- SHL rate: 8.0% (`Inputs!G311`)
- investment date: 30-Jun-2028 (`Inputs!D321`, equal to financial close)
- COD / operation start: 30-Dec-2029 (`Inputs!D11`)
- SHL IDC: 3,568.688 kEUR (`IDC!D51`, `DS!B135`)
- opening SHL at COD: 32,703.864 kEUR

This is consistent with compound annual accrual over the elapsed construction
period on the full SHL draw from investment date, rather than monthly
draw-by-draw SHL IDC.

## TUHO Construction Assumptions

| Item | Finding | Excel reference |
|---|---:|---|
| Project code | TUHO | `Inputs!D4` |
| Financial close / construction start proxy | 30-Jun-2028 | `Inputs!D9` |
| Scheduled construction time | 18 months | `Inputs!D10` |
| Operation start / COD proxy | 30-Dec-2029 | `Inputs!D11 = EDATE(D9,D10)` |
| Construction periods | 18 monthly periods | `IDC!G:X`, rows 4-6 |
| Construction phase row | 1 through 18 | `IDC!G4:X4` |
| Construction period flags | all TRUE across G:X | `IDC!G5:X5` |
| Interest period basis | actual monthly day fraction, first partial month 0.002778 | `IDC!G6:X6` |

### TUHO CAPEX Utilisation Profile

Excel uses item-level construction-period weights on `IDC!G9:X30`, sourced from
`Inputs!E:V` rows linked to the CapEx line items.

The core production/EPC-style rows are linear over 18 months:

- `IDC!G9:X9` Production Unit: 1/18 per month.
- `IDC!G10:X10` EPC Contract: 1/18 per month.
- `IDC!G11:X11` Grid connection: 1/18 per month.
- `IDC!G12:X12` Monitoring & Telecom: 1/18 per month.
- `IDC!G13:X13` Operation Investments: 1/18 per month.

Several costs are paid 100% at financial close / first construction month:

- Insurances (`IDC!G14`)
- Land securing (`IDC!G15`)
- Bank due diligence (`IDC!G16`)
- Construction Management (`IDC!G17`, `IDC!G20`)
- Contingencies (`IDC!G21`)
- Project Rights (`IDC!G24`)
- Bank fees / other finance lines as applicable (`IDC!G27:G28`)

Aggregate utilisation is therefore front-loaded, not linear.

| Month | IDC column | Aggregate utilisation weight | Cash requirement kEUR |
|---:|---|---:|---:|
| 1 | G | 33.1902% | 24,226.729 |
| 2 | H | 3.8165% | 2,785.808 |
| 3 | I | 3.8413% | 2,803.874 |
| 4 | J | 3.8424% | 2,804.725 |
| 5 | K | 3.8590% | 2,816.833 |
| 6 | L | 3.8786% | 2,831.107 |
| 7 | M | 3.8636% | 2,820.167 |
| 8 | N | 3.8843% | 2,835.312 |
| 9 | O | 3.9026% | 2,848.618 |
| 10 | P | 3.9077% | 2,852.397 |
| 11 | Q | 3.9392% | 2,875.373 |
| 12 | R | 3.9521% | 2,884.804 |
| 13 | S | 3.9762% | 2,902.406 |
| 14 | T | 3.9881% | 2,911.087 |
| 15 | U | 4.0136% | 2,929.689 |
| 16 | V | 4.0325% | 2,943.438 |
| 17 | W | 4.0428% | 2,950.982 |
| 18 | X | 4.0704% | 2,971.101 |

Total construction cash requirement is 72,994.450 kEUR (`IDC!D34`).
The aggregate utilisation sum is approximately 100.0010% (`IDC!D31`), with a
small Excel rounding / IDC feedback effect.

### TUHO Funding Source Split and Timing

Excel funding is source waterfall-like, not simultaneous pro-rata.

| Source | Amount kEUR | Share of IDC cash requirement | Excel reference |
|---|---:|---:|---|
| Equity shares | 500.000 | 0.7% | `IDC!D45`, `Inputs!D295` |
| Shareholder loan | 29,135.176 | 39.9% | `IDC!D46`, `Inputs!D308`, `Inputs!D311` |
| Junior / carbon fund | 0.000 | 0.0% | `IDC!D47` |
| Senior debt | 43,359.274 | 59.4% | `IDC!D48`, `Inputs!D175` |
| Total sources | 72,994.450 | 100.0% | `IDC!D44` |

Timing:

- Month 1 funds 500 kEUR equity shares plus 23,726.729 kEUR SHL.
- Month 2 continues SHL funding to 26,512.537 kEUR cumulative.
- Month 3 finishes SHL funding at 29,135.176 kEUR and senior debt begins.
- Months 3-18 senior debt funds the residual construction requirement.

### TUHO COD Opening Balances

| Item | Amount kEUR | Excel reference | Notes |
|---|---:|---|---|
| Senior debt drawn before COD | 43,358.531 / 43,359.274 | `DS!D48`, `IDC!D48` | Difference is rounding / source row mechanics. |
| Senior IDC before COD | 1,519.564 | `IDC!D57`, `CapEx!C110` | Calculated from senior draw balances and construction interest periods. |
| Senior commitment fees | 166.718 | `IDC!D58`, `CapEx!C113` | Construction-period commitment fee on undrawn senior commitment. |
| SHL principal drawn before COD | 29,135.176 | `IDC!D46`, `DS!B134`, `Inputs!D311` | Sponsor SHL only; investor SHL rows are zero. |
| SHL IDC before COD | 3,568.688 | `IDC!D51`, `DS!B135` | Compound annual formula from investment date to COD. |
| Opening SHL at COD | 32,703.864 | `Inputs!D311 + IDC!D51` | Matches known calibration target within rounding. |
| Equity shares before COD | 500.000 | `IDC!D45` | Separate from SHL. |
| Total equity + SHL before COD | 29,635.176 | `IDC!D38`, `IDC!D45:D46` | Funded before senior residual. |

## Oborovo Construction Assumptions

| Item | Finding | Excel reference |
|---|---:|---|
| Project code | Oborovo | `Inputs!D4` |
| Financial close / construction start proxy | 29-Jun-2029 | `Inputs!D9 = Scenarios!E353` |
| Scheduled construction time | 12 months | `Inputs!D10 = Scenarios!E354` |
| Operation start / COD proxy | 29-Jun-2030 | `Inputs!D11 = EDATE(D9,D10)` |
| Construction periods | 12 monthly periods | `IDC!G:R`, rows 4-6 |
| Construction phase row | 1 through 12 | `IDC!G4:R4` |
| Construction period flags | all TRUE across G:R | `IDC!G5:R5` |
| Interest period basis | actual monthly day fraction, first partial month 0.005556 | `IDC!G6:R6` |

### Oborovo CAPEX Utilisation Profile

Oborovo uses a different duration and profile from TUHO.

The core EPC-style rows are linear over 12 months:

- `IDC!G9:R9` Production Units: 1/12 per month.
- `IDC!G10:R10` EPC Contract: 1/12 per month.
- `IDC!G11:R11` EPC other costs: 1/12 per month.
- `IDC!G12:R12` Grid connection: 1/12 per month.
- `IDC!G13:R13` Investments to prepare operation phase: 1/12 per month.

Several costs are paid in the first construction month:

- Insurances (`IDC!G14`)
- Project finance costs due at closing (`IDC!G16`)
- Construction management (`IDC!G20`)
- Contingencies (`IDC!G21`)
- Project rights (`IDC!G24`)
- Bank fees / other finance lines as applicable (`IDC!G27:G28`)

Aggregate utilisation is front-loaded but less extreme than TUHO because the
main linear component is spread over 12 months.

| Month | IDC column | Aggregate utilisation weight | Cash requirement kEUR |
|---:|---|---:|---:|
| 1 | G | 28.4709% | 16,505.437 |
| 2 | H | 6.3335% | 3,671.747 |
| 3 | I | 6.4322% | 3,728.964 |
| 4 | J | 6.4592% | 3,744.590 |
| 5 | K | 6.4810% | 3,757.251 |
| 6 | L | 6.5130% | 3,775.776 |
| 7 | M | 6.4756% | 3,754.109 |
| 8 | N | 6.5091% | 3,773.506 |
| 9 | O | 6.5358% | 3,788.984 |
| 10 | P | 6.5636% | 3,805.144 |
| 11 | Q | 6.5893% | 3,820.040 |
| 12 | R | 6.6367% | 3,847.494 |

Total construction cash requirement is 57,973.041 kEUR (`IDC!D34`).
The aggregate utilisation sum is approximately 99.99998% (`IDC!D31`).

### Oborovo Funding Source Split and Timing

Oborovo also uses source waterfall-like funding, but because SHL plus equity is
already exhausted in month 1, senior debt starts immediately.

| Source | Amount kEUR | Share of IDC cash requirement | Excel reference |
|---|---:|---:|---|
| Equity shares | 500.000 | 0.9% | `IDC!D45`, `Inputs!D312` |
| Shareholder loan | 14,620.774 | 25.2% | `IDC!D46`, `Inputs!D325`, `Inputs!D328` |
| Sponsor carbon fund / junior | 0.000 | 0.0% | `IDC!D47` |
| Senior debt | 42,852.267 | 73.9% | `IDC!D48`, `Inputs!D192` |
| Total sources | 57,973.041 | 100.0% | `IDC!D44` |

Timing:

- Month 1 draws all 500 kEUR equity shares.
- Month 1 draws the full 14,620.774 kEUR SHL.
- Senior debt begins in month 1 for the residual 1,384.663 kEUR and then funds
  the remaining construction requirement through month 12.

### Oborovo COD Opening Balances

| Item | Amount kEUR | Excel reference | Notes |
|---|---:|---|---|
| Senior debt drawn before COD | 42,852.279 / 42,852.267 | `DS!D51`, `IDC!D48` | Difference is rounding / source row mechanics. |
| Senior IDC before COD | 1,086.032 | `IDC!D57`, `CapEx!C128` | Calculated from senior draw balances and construction interest periods. |
| Senior commitment fees | 188.563 | `IDC!D58`, `CapEx!C131` | Construction-period commitment fee on undrawn senior commitment. |
| SHL principal drawn before COD | 14,620.774 | `IDC!D46`, `DS!B137`, `Inputs!D328` | Sponsor SHL only; investor SHL rows are zero. |
| SHL IDC before COD | 1,169.662 | `IDC!D51`, `DS!B138` | Compound annual formula from investment date to COD. |
| Opening SHL at COD | 15,790.436 | `Inputs!D328 + IDC!D51` | Full SHL invested at financial close. |
| Equity shares before COD | 500.000 | `IDC!D45` | Separate from SHL. |
| Total equity + SHL before COD | 15,120.774 | `IDC!D38`, `IDC!D45:D46` | Fully drawn in month 1. |

## Comparison Table

| Area | TUHO | Oborovo |
|---|---:|---:|
| Financial close / construction start proxy | 30-Jun-2028 | 29-Jun-2029 |
| COD / operation start proxy | 30-Dec-2029 | 29-Jun-2030 |
| Construction duration | 18 months | 12 months |
| Core EPC profile | linear 1/18 monthly | linear 1/12 monthly |
| Aggregate profile | front-loaded + monthly residual | front-loaded + monthly residual |
| Month 1 aggregate utilisation | 33.1902% | 28.4709% |
| Total construction cash requirement | 72,994.450 kEUR | 57,973.041 kEUR |
| Equity shares | 500.000 kEUR | 500.000 kEUR |
| SHL draw | 29,135.176 kEUR | 14,620.774 kEUR |
| Senior debt source | 43,359.274 kEUR | 42,852.267 kEUR |
| Funding order | equity/SHL first, senior residual | equity/SHL first, senior residual |
| Junior/carbon fund | 0.000 kEUR | 0.000 kEUR |
| SHL IDC | 3,568.688 kEUR | 1,169.662 kEUR |
| Opening SHL at COD | 32,703.864 kEUR | 15,790.436 kEUR |
| Senior IDC | 1,519.564 kEUR | 1,086.032 kEUR |

## Funding and IDC Mechanics Observed

### CAPEX / source funding

The construction model calculates monthly uses first (`IDC!34`) from weighted
CapEx and funding-cost items. Sources then cover cumulative uses.

The source formulas indicate a waterfall:

```text
Equity Shares     = min(cumulative uses, equity share cap)
Shareholder Loan  = min(cumulative uses - prior source rows, SHL cap)
Junior/Carbon     = min(cumulative uses - prior source rows, junior cap)
Senior Debt       = residual senior draw, capped by senior debt availability
```

This means future Python implementation should not use a fixed simultaneous
funding percentage unless explicitly configured for a different workbook.

### SHL IDC

SHL IDC is not calculated from monthly SHL draw balances. The formula uses full
source amount, source rate, and elapsed time from investment date to operation
start:

```text
IDC!D51 = Inputs!D311 * ((1 + IDC!C51) ^ ((Inputs!D11 - Inputs!D321) / equity_year) - 1)
```

TUHO uses `Inputs!D311`; Oborovo uses the analogous `Inputs!D328`.

This is the key reason TUHO produces:

```text
29,135.176 SHL draw + 3,568.688 SHL IDC = 32,703.864 opening SHL
```

### Senior IDC

Senior IDC is calculated monthly from cumulative senior debt draw balances and
actual monthly interest periods:

```text
Senior Debt IDC row = (senior interest rate + base-rate row) * prior senior
draw balance * monthly interest period * construction period flag
```

Observed formulas:

- TUHO: `IDC!H57 = ($C57%/100 + H$59) * G$48 * G$6 * H$5`
- Oborovo: same structure on `IDC!H57`

This differs from SHL IDC and should be configured separately.

## Uncertainties

- The exact Excel definition of `equity_year` was not independently resolved in
  this discovery pass. It appears to be the annual day-count denominator used in
  the SHL compound formula.
- Senior opening balance treatment should be confirmed before runtime
  implementation: Excel shows senior source / DS funding around 43,358.5-43,359.3
  kEUR for TUHO and 42,852.3 kEUR for Oborovo, while senior IDC is separately
  listed in CapEx. The next implementation should decide whether senior IDC is
  a funded use, capitalized into opening senior balance, or represented as a
  separate upfront funding cost in Python.
- VAT facility mechanics are visible and material, but should probably be a
  separate sub-module or optional part of construction funding rather than baked
  into the first construction schedule implementation.
- The models contain WHT during construction rows, but observed totals are zero
  in the inspected cases.
- No monthly milestone names were found; the profile is represented as explicit
  monthly weights by CapEx line item.

## Recommended Configurable Input Schema

Recommended fields for the next implementation branch:

- `construction_months`
- `construction_start_date`
- `cod_date`
- `capex_profile_type`: `linear`, `s_curve`, `front_loaded`, `back_loaded`, `custom`
- `capex_monthly_weights`
- `capex_line_item_monthly_weights`
- `funding_mode`: `source_waterfall`, `pro_rata`
- `senior_debt_funding_pct` or senior commitment amount
- `shl_funding_pct` or SHL commitment amount
- `equity_funding_pct` or equity commitment amount
- `equity_share_amount_keur`
- `shl_draw_keur`
- `senior_debt_commitment_keur`
- `idc_method`: `average_balance`, `opening_balance`, `monthly_cumulative_balance`, `full_source_elapsed_compound`
- `senior_debt_idc_capitalized: bool`
- `shl_idc_capitalized: bool`
- `interest_rate_by_source`
- `investment_date_by_source`
- `allow_manual_opening_balance_override: bool`
- `manual_opening_senior_balance_keur`
- `manual_opening_shl_balance_keur`

## Recommended Next Implementation Branch

Next branch:

```text
phase7i-construction-schedule-engine
```

Suggested scope:

1. Add pure offline construction schedule dataclasses and calculation helpers.
2. Support monthly construction profiles and source-waterfall funding.
3. Support separate SHL IDC and senior IDC methods.
4. Reproduce TUHO and Oborovo Excel construction funding schedules offline.
5. Keep runtime waterfall untouched until offline parity is proven.

Non-goals for the next branch:

- No senior repayment / sculpting changes.
- No SHL operating waterfall changes.
- No revenue / OPEX / tax changes.
- No UI changes.
- No direct runtime construction IDC integration until the offline engine is
  separately validated.
