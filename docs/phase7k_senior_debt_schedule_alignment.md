# Phase 7K Senior Debt Schedule Alignment

## Purpose

This branch documents and tests senior debt schedule behavior after COD. It does not change senior debt formulas, construction funding, SHL behavior, revenue, OPEX, tax, R99, sponsor waterfall, UI, or cache behavior.

The Phase 7J opening-balance policy remains the governing rule: runtime senior debt opens on senior principal only. Senior IDC and commitment fees are not added to the operating senior debt balance unless a future workbook reference proves otherwise.

## Opening Balance Policy Reference

The Excel evidence reviewed in Phase 7J showed:

- TUHO first operating senior opening balance is approximately `43,358.531` kEUR.
- Oborovo first operating senior opening balance is approximately `42,852.279` kEUR.
- Senior IDC and commitment fees are linked to CapEx / IDC rows, not capitalized into the operating DS schedule opening balance.

Policy recommendation remains: **keep runtime fixed senior debt as principal-only**.

## TUHO First Operating Senior Period

Excel source workbook: `20260330_TUHO_BP.xlsm`

Excel references:

- `DS!H47` senior beginning balance.
- `DS!H49` senior principal repayment.
- `DS!H50` senior net interest.
- `DS!H53` senior closing balance.

| Metric | Excel kEUR | Python kEUR | Delta | Likely cause |
|---|---:|---:|---:|---|
| First operating date | 2030-06-30 | 2030-06-30 | aligned | Period mapping is aligned. |
| Opening senior balance | 43,358.531 | 43,359.000 | +0.469 | Rounding of fixed debt input; policy aligned. |
| Senior interest | 1,297.082 | 1,246.571 | -50.511 | Interest timing / rate basis. Excel appears higher than Python for the first period. |
| Senior principal | 819.279 | 742.535 | -76.744 | DSCR sculpting payment amount differs in the first period. |
| Senior debt service | 2,116.361 | 1,989.107 | -127.254 | Combination of interest and principal timing / sculpting basis. |
| Closing senior balance | 42,539.252 | 42,616.465 | +77.213 | Lower Python principal repayment leaves higher closing balance. |

Python total senior DS observed in the current runtime is approximately `65,826.388` kEUR. The final senior balance is `0.0` kEUR.

## Oborovo First Operating Senior Period

Excel source workbook: `20260414_BP_Oborovo_Sensitivity_FINAL for PPT.xlsm`

Excel references:

- `DS!H50` senior beginning balance.
- `DS!H52` senior principal repayment.
- `DS!H53` senior net interest.
- `DS!H56` senior closing balance.

| Metric | Excel kEUR | Python kEUR | Delta | Likely cause |
|---|---:|---:|---:|---|
| First operating date | 2030-12-31 | 2030-12-31 | aligned | Period mapping is aligned. |
| Opening senior balance | 42,852.279 | 42,852.267 | -0.012 | Rounding of fixed debt input; policy aligned. |
| Senior interest | 1,303.483 | 1,210.577 | -92.907 | Interest timing / rate basis. Excel appears higher than Python for the first period. |
| Senior principal | 935.650 | 844.906 | -90.744 | Payment / amortization timing differs in first period. |
| Senior debt service | 2,239.133 | 2,055.482 | -183.651 | Combination of interest and principal timing / repayment basis. |
| Closing senior balance | 41,916.629 | 42,007.361 | +90.732 | Lower Python principal repayment leaves higher closing balance. |

Python total senior DS observed in the current runtime is approximately `63,500.895` kEUR. The final senior balance is `0.0` kEUR.

## Findings

1. The senior opening balance policy is aligned for both projects: Python opens on principal only, matching the inspected Excel DS schedules within rounding.
2. Senior IDC is deliberately excluded from the operating senior opening debt balance.
3. Commitment fees are also excluded from the operating senior opening debt balance.
4. First-period senior debt service remains lower in Python for both TUHO and Oborovo.
5. The residual first-period mismatch is not caused by opening balance capitalization. It is more likely caused by interest timing / rate basis and repayment sculpting or amortization timing.

## Implemented Fixes

No runtime fixes were implemented in this branch.

The only additions are:

- diagnostic regression tests for senior opening policy and first-period schedule values,
- this documentation note.

## Remaining Gaps

| Gap | Status | Suggested next step |
|---|---|---|
| TUHO first-period senior interest is `50.511` kEUR lower in Python | unresolved | Inspect Excel interest period fraction and rate basis for DS row 50. |
| TUHO first-period senior principal is `76.744` kEUR lower in Python | unresolved | Compare Excel debt service sculpting input against Python CFADS / DSCR schedule. |
| Oborovo first-period senior interest is `92.907` kEUR lower in Python | unresolved | Inspect Excel first operating interest timing, especially construction-to-COD boundary. |
| Oborovo first-period senior principal is `90.744` kEUR lower in Python | unresolved | Compare Excel repayment / DSCR basis and first operating period treatment. |
| Total senior DS period-by-period bridge | not yet built | Build a senior DS Excel-vs-Python comparison workbook or fixture-backed test before changing formulas. |

## Recommendation

Do not change senior opening debt policy. The next implementation should focus on senior schedule mechanics, not opening balance:

Recommended next branch: `phase7k-senior-debt-interest-timing-diagnostic`.

Suggested scope:

- extract Excel senior debt period-by-period interest, principal, DS, and closing balance rows for TUHO and Oborovo,
- compare rate, period fraction, DSCR sculpting input, and repayment timing,
- identify whether a small day-count / first-period timing fix is justified,
- avoid SHL waterfall, tax, revenue, OPEX, R99, sponsor, and construction capitalization changes.
