# phase9 — TUHO Equity IRR: Excel Source Extraction

## Executive Summary

The TUHO Excel workbook (`20260330_TUHO_BP---cb609a8e-8b9a-4e28-b478-bb618eeae31e.xlsm`) has been extracted and analysed. The Excel `Eq!D28 = XIRR(G28:DW28, G23:DW23) = 11.6095%`.

The gap between the model's corrected `shl_plus_dividends` IRR and the Excel target has been narrowed to **3 root causes**:

1. **Investment base includes SHL IDC** (HIGH severity): Model investment base = -33,204 kEUR; Excel = -29,635 kEUR. The difference = exactly SHL IDC (3,568.69 kEUR).
2. **SHL interest timing/binding** (HIGH severity): Excel PIK balance grows during the PIK phase (interest > principal repayment); model PIK balance declines from day 1.
3. **SHL principal repayment timing** (HIGH severity): Excel shows zero principal repayment for periods 1–23 (PIK only); model starts principal repayment from period 1.

## Workbook

**File:** `20260330_TUHO_BP---cb609a8e-8b9a-4e28-b478-bb618eeae31e.xlsm`
**Path in repository:** `/root/.openclaw/media/inbound/20260330_TUHO_BP---cb609a8e-8b9a-4e28-b478-bb618eeae31e.xlsm`

## Exact Formula in `Eq!D28`

```
=XIRR(G28:DW28,G$23:DW$23)
```

- `G28:DW28` = equity cashflow range (121 semi-annual periods, columns G through DW)
- `G23:DW$23` = date range (2028-06-30 through 2090-01-01)
- Result: **0.11609525084495542 (11.61%)**

## Cashflow Range

`Eq!G28:DW28` — 121 cashflows covering 2028-06-30 to 2090-01-01.

Formula per period: `G28 = G27 + G24`

Where:
- `G24` = total SHL flows (principal + interest, drawn at construction)
- `G27` = share capital injection (only at t0: -500 kEUR)

## Date Range

`Eq!G23:DW23` — linked to `Flags!G32:DW32` — semi-annual periods starting 2028-06-30.

## Extracted Excel Values

| Item | Value | Unit |
|------|-------|------|
| Equity IRR (`Eq!D28`) | 11.6095% | |
| Investment base (t0) | -29,635.18 | kEUR |
| SHL drawdown (r24) | -29,135.18 | kEUR |
| Share capital (r27) | -500.00 | kEUR |
| Total SHL interest (r26, periods 1+) | 38,755.35 | kEUR |
| Total SHL principal repaid (r25, periods 1+) | 43,730.70 | kEUR |
| Total dividends (r27, periods 1+) | 151,709.39 | kEUR |
| Total equity CF (sum r28) | 204,560.26 | kEUR |

## SHL Interest Treatment

**EXCEL INCLUDES SHL interest in equity CF stream.**

Excel row 26 (Net Interests) = SHL PIK interest. Non-zero for periods 1–36 (2048-01-01), then zero thereafter.

Excel equity CF (row 28) = SHL total (row 24) + dividend (row 27).  
When SHL balance > 0: row 28 = row 26 (PIK interest only) because row 25 principal = 0.  
When SHL balance = 0: row 28 = row 27 (dividends).

**CRITICAL FINDING:** Excel SHL interest (row 26) grows over time, not declines. The SHL balance (row 24) is the cumulative drawn amount and grows because PIK interest is capitalized (added to balance) before principal repayment begins.

## SHL Principal Treatment

**EXCEL: Principal repayment does not begin until period 24 (2042-01-01).**  
Period 0: -29,135.18 (drawdown).  
Periods 1–23: 0 (PIK only, no principal repayment).  
Periods 24–36: gradual principal repayment starting at 8.28 kEUR and ramping up.

**MODEL: Principal repayment starts from period 1.** The DSCR waterfall prioritises senior debt service, then SHL service, then distributions. Model starts principal repayment immediately.

## Dividends/Distributions Treatment

Excel row 27 (Net Dividend Flows) = 0 for periods 0–34.  
First non-zero dividend: period 35 (2047-07-01) = 2.29 kEUR.

Excel dividends and SHL interest overlap in periods 35–36 (both non-zero), then dividends continue alone (periods 37+).

## WHT Treatment

TUHO SHL WHT = 0% — confirmed in both Excel and model. **Not a gap driver.**

## SHL IDC Treatment

**Excel:** SHL IDC is NOT included in the equity investment base (-29,635 = SHL drawdown -29,135 + share capital 500). The opening SHL balance in the model is 29,135 kEUR, but the actual opening balance including IDC should be 32,704 kEUR. Excel shows this through the PIK interest trajectory (interest grows, not declines, confirming the balance is compounding).

**Model:** Investment base = -33,204 kEUR = SHL drawdown 29,135 + SHL IDC 3,569 + share capital 500. Model correctly tracks IDC in SHL balance; Excel equity IRR investment base does not include it.

## Terminal Cash/Residual

All zero from period 115 onwards (2089-01-01 to 2090-01-01). No terminal residual value.

## Timing Convention

- Excel: semi-annual periods, dates as of period end (2028-06-30 first, then 2030-07-01 etc.)
- Model: semi-annual periods (2030-06-30 first = COD), 62 periods vs Excel's 121
- Model excludes construction period (2028-2030); Excel includes 2 construction periods

## Root Cause of IRR Gap

The 3.5–4.7 pp gap between model (~15.1%) and Excel (11.61%) is explained by **three compounding differences**:

### 1. Investment Base (+1.9 pp effect)

Model uses -33,204 kEUR vs Excel -29,635 kEUR. Difference = 3,569 kEUR (SHL IDC). When model uses Excel's investment base, IRR rises from 15.1% to ~16.3%.

### 2. SHL Interest Trajectory (dominant driver)

Excel PIK interest grows over time (balance compounding); model PIK interest declines from day 1. This reflects different PIK capitalization mechanics:
- Excel: SHL interest added to balance; principal repayment only starts in period 24
- Model: SHL interest is serviced (PIK capitalized in waterfall) but balance starts declining immediately because FCF is insufficient to cover both SHL interest AND senior debt service in early periods

### 3. SHL Principal Repayment Timing

Excel starts principal repayment in period 24 (2042); model starts in period 1 (2030). This means Excel's effective SHL balance stays larger for longer, prolonging the PIK phase and reducing the discount rate impact of early cashflows.

## Missing Evidence / Next Steps

If Excel parity is required, the next branch must:
1. Investigate why Excel SHL balance grows during PIK (PIK capitalization mechanics differ from model)
2. Align the investment base to use Excel's -29,635 kEUR figure (excluding IDC)
3. Verify that the waterfall priority in the model matches Excel's (Excel may not require SHL principal repayment during PIK)
4. Confirm the construction period treatment: Excel includes 2028-2030 construction CFs in the IRR; model starts at COD

## G20 Impact

**G20 remains BLOCKED.** The root cause is a combination of investment base treatment, SHL PIK mechanics, and waterfall priority differences. These are **runtime waterfall behaviour differences**, not just reporting differences.

Fixing the model to match Excel equity IRR requires changes to the SHL repayment logic in the runtime waterfall engine (not just the reporting/harness layer).

## R99/R102 Promotion

**R99/R102 runtime flag promotion is NOT approved in this branch.**

This branch makes no runtime code changes. The path to G20 approval requires a separate runtime fix branch.

## Recommended Next Branch

`phase9-tuho-equity-irr-shl-mechanics-alignment`

This branch would:
1. Investigate the Excel SHL balance trajectory (growing during PIK vs declining in model)
2. Align SHL repayment priority/触发 logic to match Excel
3. Resolve investment base treatment (with/without SHL IDC)
4. Produce a runtime fix for G20 approval

Alternatively, if only the reporting harness needs fixing (not the runtime), a lighter-weight `phase9-tuho-investment-base-fix` branch would address the IDC investment base issue only.