# Phase 7M R99 Distribution-Account Source Bridge

## Purpose

Phase 7M runtime source validation showed that the best current Python R99/R102 candidate still fails against Excel:

- Python C1d R99/R102 audit family with explicit senior DS: 252,140.1 kEUR
- Excel R99/R102: 234,745.4 kEUR
- Delta: +17,394.7 kEUR
- Material periods within tolerance: 41 / 60

This bridge checks whether the remaining gap is caused by Excel distribution-account carry-forward, cash-tax timing, reserve movement, or another missing component.

This branch is diagnostic only. It does not enable SHL FCF waterfall, does not accept a runtime R99/R102 source, and does not rewrite runtime R99 logic.

## Excel Formula References

Source workbook:

`C:\Users\Ivan\Desktop\modeli za rad\20260330_TUHO_BP.xlsm`

Sheet: `CF`

Operating periods start in column `H`. Column `G` is the construction/COD-prep period and is excluded from operating totals.

| Excel row | Label | Formula pattern | Interpretation |
| ---: | --- | --- | --- |
| R84 | Free Cash Flow for Junior Debt | `=SUM(H69:H70,H82)` | R69 plus senior debt service and DSRA movement. |
| R85 | Junior debt repayment and interests | `=SUM(DS!H106,DS!H109)*-1` | Zero for TUHO operating periods. |
| R96 | J-DSRA | `=-SUM(H92:H94)` | Zero for TUHO operating periods. |
| R98 | Distribution Account | `=SUM(H84,H85,H96)+G100` | R84 plus junior debt, reserve sweep, and previous R100. |
| R99 | Free Cash Flow for Distribution | `=IF(AND(OR(H$128<$B$99,H$3=0,H98<0,H81<H76,H95<H90),H$3<=$B$10),0,H98)` | Lockup/constraint gate; otherwise equals R98. |
| R100 | Distribution Account Balance | `=H98-H99` | Carry-forward balance after R99. |
| R102 | Free Cash Flow for Shareholder Loan | `=H99` | SHL cash input equals R99. |

Workbook values over the 60 operating periods:

| Row | Total | Observation |
| ---: | ---: | --- |
| R84 | 234,745.4 kEUR | Equal to R98/R99/R102. |
| R85 | 0.0 kEUR | No junior debt repayment in TUHO operating periods. |
| R96 | 0.0 kEUR | No J-DSRA/reserve sweep in TUHO operating periods. |
| R98 | 234,745.4 kEUR | Equal to R84 because R85/R96/R100 are zero. |
| R99 | 234,745.4 kEUR | Equal to R98; lockup gate does not create carry-forward over operating horizon. |
| R100 | 0.0 kEUR | No distribution-account carry-forward. |
| R102 | 234,745.4 kEUR | Equal to R99. |

Conclusion: the remaining Python-vs-Excel R99/R102 gap is not caused by R98/R100/R102 distribution-account carry-forward logic in TUHO. In the workbook, operating R99/R102 collapses to R84.

## Component Totals

The comparison below uses the Phase 7K explicit senior DS harness so that senior debt service is already aligned to Excel.

| Component | Excel total | Python total | Delta |
| --- | ---: | ---: | ---: |
| R20 Revenue | 423,787.5 | 423,787.5 | 0.0 |
| R38 OPEX | -84,674.8 | -85,408.3 | -733.5 |
| R63 Local tax | 0.0 | 0.0 | 0.0 |
| R66 Reserve interest | 55.0 | 0.0 | -55.0 |
| R67 CorpTax | -38,240.9 | -20,057.7 | +18,183.2 |
| R69 FCF Banks | 300,926.8 | 318,321.5 | +17,394.7 |
| R70 Senior DS | -66,181.3 | -66,181.3 | 0.0 |
| R82 DSRA | 0.0 | 0.0 | 0.0 |
| R84 FCF Junior | 234,745.4 | 252,140.1 | +17,394.7 |
| R98 Distribution Account | 234,745.4 | 252,140.1 | +17,394.7 |
| R99/R102 | 234,745.4 | 252,140.1 | +17,394.7 |
| R100 Carry-forward | 0.0 | 0.0 | 0.0 |

The full R99/R102 delta is upstream of the distribution account:

```text
R84 delta = R69 delta + R70 delta + R82 delta
          = +17,394.7 + 0.0 + 0.0
          = +17,394.7 kEUR
```

R69 delta is mostly cash-tax timing/source:

```text
R69 delta ~= R38 OPEX delta + R67 CorpTax delta + R66 reserve interest delta
          ~= -733.5 + 18,183.2 - 55.0
          ~= +17,394.7 kEUR
```

## Selected Period Bridge

| op_idx | Date | Excel R99/R102 | Python best candidate | Delta | Main explained component |
| ---: | --- | ---: | ---: | ---: | --- |
| 0 | 2030-06-30 | 953.8 | 953.8 | +0.0 | Senior DS fixture aligns first period. |
| 1 | 2030-12-31 | 969.6 | 969.6 | +0.0 | Senior DS fixture aligns early period. |
| 2 | 2031-06-30 | 967.0 | 960.7 | -6.3 | OPEX only. |
| 3 | 2031-12-31 | 983.0 | 976.6 | -6.4 | OPEX only. |
| 24 | 2042-06-30 | 3,233.6 | 3,264.9 | +31.3 | OPEX only. |
| 25 | 2042-12-31 | 3,167.0 | 2,453.7 | -713.3 | Cash-tax timing/source. |
| 26 | 2043-06-30 | 3,265.3 | 3,286.2 | +20.9 | OPEX only. |
| 27 | 2043-12-31 | 2,395.6 | 2,481.9 | +86.3 | OPEX plus tax. |
| 28 | 2044-06-30 | 6,191.8 | 6,187.8 | -4.0 | OPEX only. |
| 32 | 2046-06-30 | 6,422.3 | 6,419.5 | -2.8 | OPEX only. |
| 35 | 2047-12-31 | 5,050.2 | 5,690.8 | +640.6 | Cash-tax timing/source. |
| 36 | 2048-06-30 | 6,765.1 | 6,735.9 | -29.2 | OPEX only. |
| 37 | 2048-12-31 | 5,028.2 | 5,797.4 | +769.2 | Cash-tax timing/source. |
| 57 | 2058-12-31 | 5,373.4 | 6,960.7 | +1,587.2 | Cash-tax timing/source. |
| 58 | 2059-06-30 | 8,264.4 | 8,114.1 | -150.3 | OPEX only. |
| 59 | 2059-12-31 | 5,401.6 | 6,977.7 | +1,576.1 | Cash-tax timing/source. |

## Root Cause Finding

The exact missing runtime component is not Excel R100 carry-forward. It is a combination of:

1. Cash-tax timing/source difference in R67.
2. Smaller OPEX basis mismatch in R38.
3. Minor missing reserve interest R66.

The senior DS difference is already isolated by the Phase 7K explicit senior DS fixture. DSRA, junior debt, reserve sweep, and distribution-account carry-forward are zero over the TUHO operating horizon in the workbook rows inspected.

The large H2 post-senior deltas are explained by Python cash tax being materially lower than Excel cash tax in those periods. H1 periods are close because Excel R67 is usually zero in H1, so the remaining differences are mostly OPEX.

## Explained vs Unexplained Delta

Total R99/R102 delta with explicit senior DS harness:

| Category | Delta |
| --- | ---: |
| Senior DS | 0.0 kEUR |
| DSRA / reserve movement | 0.0 kEUR |
| Distribution-account carry-forward R100 | 0.0 kEUR |
| OPEX basis | -733.5 kEUR |
| Corporate tax cash timing/source | +18,183.2 kEUR |
| Reserve interest | -55.0 kEUR |
| Residual / rounding | about 0.0 kEUR |
| Total | +17,394.7 kEUR |

## Can The Difference Be Eliminated Now?

Not safely as an R99/R102 runtime source PR.

A distribution-account source implementation alone would not remove the gap because Excel R98/R99/R100/R102 already collapse to R84. The next implementation must address the upstream components that feed R84, especially cash-tax timing/source and the smaller OPEX basis mismatch.

Do not accept the current C1d R99/R102 audit family as the SHL runtime source. It still fails total and period gates.

## Recommendation

Recommended next branch:

`phase7m-r67-cash-tax-source-bridge`

Suggested scope:

- Extract Excel R67/P&L tax formulas and cash-tax timing.
- Compare Python tax engine cash tax to Excel R67 period-by-period.
- Keep SHL FCF waterfall fixture-backed only.
- Keep R99 runtime opt-in blocked until the R67/R38 feed into R84 is validated.

Secondary follow-up:

`phase7h-opex-runtime-tuho-opt-in` or equivalent, if the OPEX basis mismatch remains after the already-built line-item engine is intentionally enabled for TUHO.
