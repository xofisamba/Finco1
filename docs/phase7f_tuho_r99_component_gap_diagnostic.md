# Phase 7F TUHO R99 Component Gap Diagnostic

## Purpose

This diagnostic explains why the C1a TUHO R99/R102 helper produces:

- Python R99 helper total: **249,545.4 kEUR**
- Excel R99/R102 total: **234,745.0 kEUR**
- Gap: **+14,800.4 kEUR**

Inputs used:

- `tests/fixtures/excel_tuho_full_model_extract.json`
- Current PR B1 TUHO Python run
- C1a helper output with runtime opt-in still disabled

No runtime change is recommended from this diagnostic alone. `use_tuho_r99_input_engine` remains disabled, SHL `fcf_waterfall` remains blocked, and no tax/revenue/OPEX logic is changed here.

## Fixture Coverage Note

The fixture exposes Excel R20, R38, R67, R69, R70, and R99/R102 through the period diagnostics. It does not expose period-level R63, R66, R82, R85, R96, R98, or R100 as independent rows. Those fields are therefore shown as `n/a` where the fixture cannot support an authoritative comparison.

In the current fixture, Excel R99 is mechanically equal to available R69 plus signed R70 at total level:

`300,926.8 + (-66,181.3) = 234,745.5 kEUR`

This implies no observable R82/R85/R96/R98/R100 adjustment in the available fixture extract, but it does not prove those Excel rows are zero in the workbook.

## Full-Horizon Bridge

Signs follow Excel cash-flow convention: outflows are negative. Python senior DS is shown as signed outflow for comparability.

| Component | Excel total | Python total | Delta | Comment |
|---|---:|---:|---:|---|
| R20 Revenue | 423,787.5 | 420,529.9 | -3,257.6 | Python revenue is lower overall, but period timing differs materially around the PPA/merchant boundary. |
| R38 OPEX / expenses after bank tax | -84,674.8 | -85,402.8 | -728.0 | Python OPEX is slightly more negative. |
| R67 CorpTax cash used in C1a helper | -38,240.9 | -19,936.6 | +18,304.3 | Dominant full-horizon source: C1a cash-tax proxy under-deducts cash tax. |
| R69 FCF Banks | 300,926.8 | 315,190.5 | +14,263.7 | Nearly the full R99 gap flows through R69. |
| R70 Senior DS signed | -66,181.3 | -65,645.1 | +536.2 | PR B1 senior DS is close in total; residual timing still matters in early periods. |
| R82 DSRA funding/release | n/a | 0.0 | n/a | Fixture does not expose R82; Python C1a helper currently uses zero DSRA movement in TUHO run. |
| R98 Distribution Account proxy | n/a | 249,545.4 | n/a | Fixture does not expose R98 independently. |
| R99/R102 FCF for SHL input | 234,745.0 | 249,545.4 | +14,800.4 | Total helper output is too high, so runtime opt-in remains blocked. |

The C1a helper currently derives `corporate_tax_cash_keur` from `max(0, ebitda - cf_after_tax)`. In this Python run, `cf_after_tax_keur` equals EBITDA for many periods even when `period.tax_keur` is non-zero. That means the helper deducts only **19,936.6 kEUR** of cash tax versus Excel R67 of **38,240.9 kEUR**.

For context only, using `period.tax_keur` instead of the current C1a cash-tax proxy would produce an R99 total of about **230,393.9 kEUR**, or **-4,351.1 kEUR** versus Excel. That would fix the dominant full-horizon overstatement but over-correct selected merchant/post-SHL periods, so it is not sufficient as a blind runtime change.

## Selected Period Bridge

| op_idx | date | Excel R69 | Python R69 | dR69 | Excel R70 | Python senior DS | dSeniorDS | Excel R82 | Python DSRA movement | dDSRA | Excel R98 | Python R98 | dR98 | Excel R99 | Python R99 | dR99 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 2030-06-30 | 3070.2 | 3053.2 | -16.9 | -2116.4 | -1945.5 | 170.9 | n/a | 0.0 | n/a | n/a | 1107.8 | n/a | 953.8 | 1107.8 | 153.9 |
| 10 | 2035-06-30 | 3200.0 | 3405.3 | 205.2 | -2189.9 | -2169.8 | 20.1 | n/a | 0.0 | n/a | n/a | 1235.5 | n/a | 1010.1 | 1235.5 | 225.4 |
| 20 | 2040-06-30 | 3556.8 | 3781.2 | 224.4 | -2435.9 | -2409.3 | 26.5 | n/a | 0.0 | n/a | n/a | 1371.9 | n/a | 1121.0 | 1371.9 | 250.9 |
| 21 | 2040-12-31 | 3595.9 | 3439.1 | -156.8 | -2462.6 | -2435.8 | 26.8 | n/a | 0.0 | n/a | n/a | 1003.3 | n/a | 1133.3 | 1003.3 | -130.0 |
| 23 | 2041-12-31 | 3686.4 | 3492.1 | -194.3 | -2525.6 | -2492.3 | 33.3 | n/a | 0.0 | n/a | n/a | 999.7 | n/a | 1160.7 | 999.7 | -161.0 |
| 24 | 2042-06-30 | 6108.9 | 3925.9 | -2183.1 | -2875.3 | -2125.2 | 750.1 | n/a | 0.0 | n/a | n/a | 1800.7 | n/a | 3233.6 | 1800.7 | -1432.9 |
| 28 | 2044-06-30 | 6191.8 | 6414.6 | 222.7 | 0.0 | 0.0 | 0.0 | n/a | 0.0 | n/a | n/a | 6414.6 | n/a | 6191.8 | 6414.6 | 222.7 |
| 34 | 2047-06-30 | 6585.9 | 6663.5 | 77.6 | 0.0 | 0.0 | 0.0 | n/a | 0.0 | n/a | n/a | 6663.5 | n/a | 6585.9 | 6663.5 | 77.6 |
| 36 | 2048-06-30 | 6765.1 | 6772.8 | 7.7 | 0.0 | 0.0 | 0.0 | n/a | 0.0 | n/a | n/a | 6772.8 | n/a | 6765.1 | 6772.8 | 7.7 |

## Period Bridge op_idx 0-36

| op_idx | date | Excel R69 | Python R69 | dR69 | Excel R70 | Python senior DS | dSeniorDS | Excel R82 | Python DSRA movement | dDSRA | Excel R98 | Python R98 | dR98 | Excel R99 | Python R99 | dR99 |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 2030-06-30 | 3070.2 | 3053.2 | -16.9 | -2116.4 | -1945.5 | 170.9 | n/a | 0.0 | n/a | n/a | 1107.8 | n/a | 953.8 | 1107.8 | 153.9 |
| 1 | 2030-12-31 | 3121.1 | 3121.1 | 0.0 | -2151.4 | -1988.7 | 162.7 | n/a | 0.0 | n/a | n/a | 1132.4 | n/a | 969.6 | 1132.4 | 162.7 |
| 2 | 2031-06-30 | 3111.6 | 3134.9 | 23.2 | -2144.7 | -1997.5 | 147.2 | n/a | 0.0 | n/a | n/a | 1137.4 | n/a | 967.0 | 1137.4 | 170.4 |
| 3 | 2031-12-31 | 3163.2 | 3186.8 | 23.6 | -2180.2 | -2030.6 | 149.6 | n/a | 0.0 | n/a | n/a | 1156.2 | n/a | 983.0 | 1156.2 | 173.2 |
| 4 | 2032-06-30 | 3121.1 | 3209.6 | 88.4 | -2144.9 | -2045.1 | 99.8 | n/a | 0.0 | n/a | n/a | 1164.5 | n/a | 976.2 | 1164.5 | 188.3 |
| 5 | 2032-12-31 | 3155.4 | 3244.8 | 89.4 | -2168.5 | -2067.6 | 100.9 | n/a | 0.0 | n/a | n/a | 1177.3 | n/a | 987.0 | 1177.3 | 190.3 |
| 6 | 2033-06-30 | 3156.8 | 3267.7 | 110.8 | -2169.3 | -2082.1 | 87.2 | n/a | 0.0 | n/a | n/a | 1185.6 | n/a | 987.5 | 1185.6 | 198.0 |
| 7 | 2033-12-31 | 3209.2 | 3321.8 | 112.7 | -2205.3 | -2116.6 | 88.6 | n/a | 0.0 | n/a | n/a | 1205.2 | n/a | 1003.9 | 1205.2 | 201.3 |
| 8 | 2034-06-30 | 3194.8 | 3335.9 | 141.1 | -2195.0 | -2125.6 | 69.4 | n/a | 0.0 | n/a | n/a | 1210.3 | n/a | 999.8 | 1210.3 | 210.5 |
| 9 | 2034-12-31 | 3247.7 | 3391.2 | 143.4 | -2231.4 | -2160.8 | 70.6 | n/a | 0.0 | n/a | n/a | 1230.4 | n/a | 1016.4 | 1230.4 | 214.0 |
| 10 | 2035-06-30 | 3200.0 | 3405.3 | 205.2 | -2189.9 | -2169.8 | 20.1 | n/a | 0.0 | n/a | n/a | 1235.5 | n/a | 1010.1 | 1235.5 | 225.4 |
| 11 | 2035-12-31 | 3253.1 | 3461.7 | 208.6 | -2226.2 | -2205.7 | 20.5 | n/a | 0.0 | n/a | n/a | 1256.0 | n/a | 1026.8 | 1256.0 | 229.1 |
| 12 | 2036-06-30 | 3276.6 | 3485.5 | 208.9 | -2243.1 | -2220.9 | 22.2 | n/a | 0.0 | n/a | n/a | 1264.6 | n/a | 1033.5 | 1264.6 | 231.1 |
| 13 | 2036-12-31 | 3312.6 | 3523.8 | 211.2 | -2267.8 | -2245.3 | 22.5 | n/a | 0.0 | n/a | n/a | 1278.5 | n/a | 1044.8 | 1278.5 | 233.7 |
| 14 | 2037-06-30 | 3340.2 | 3547.7 | 207.5 | -2287.7 | -2260.5 | 27.1 | n/a | 0.0 | n/a | n/a | 1287.2 | n/a | 1052.6 | 1287.2 | 234.6 |
| 15 | 2037-12-31 | 3395.6 | 3606.5 | 210.9 | -2325.6 | -2298.0 | 27.6 | n/a | 0.0 | n/a | n/a | 1308.5 | n/a | 1070.0 | 1308.5 | 238.5 |
| 16 | 2038-06-30 | 3418.1 | 3620.8 | 202.7 | -2342.1 | -2307.1 | 35.0 | n/a | 0.0 | n/a | n/a | 1313.7 | n/a | 1076.0 | 1313.7 | 237.7 |
| 17 | 2038-12-31 | 3474.8 | 3680.8 | 206.0 | -2380.9 | -2345.4 | 35.6 | n/a | 0.0 | n/a | n/a | 1335.5 | n/a | 1093.8 | 1335.5 | 241.6 |
| 18 | 2039-06-30 | 3494.0 | 3695.1 | 201.1 | -2395.1 | -2354.5 | 40.6 | n/a | 0.0 | n/a | n/a | 1340.7 | n/a | 1098.9 | 1340.7 | 241.7 |
| 19 | 2039-12-31 | 3551.9 | 3752.8 | 200.8 | -2434.8 | -2393.5 | 41.3 | n/a | 0.0 | n/a | n/a | 1359.2 | n/a | 1117.1 | 1359.2 | 242.1 |
| 20 | 2040-06-30 | 3556.8 | 3781.2 | 224.4 | -2435.9 | -2409.3 | 26.5 | n/a | 0.0 | n/a | n/a | 1371.9 | n/a | 1121.0 | 1371.9 | 250.9 |
| 21 | 2040-12-31 | 3595.9 | 3439.1 | -156.8 | -2462.6 | -2435.8 | 26.8 | n/a | 0.0 | n/a | n/a | 1003.3 | n/a | 1133.3 | 1003.3 | -130.0 |
| 22 | 2041-06-30 | 3626.3 | 3847.7 | 221.4 | -2484.5 | -2451.7 | 32.8 | n/a | 0.0 | n/a | n/a | 1396.0 | n/a | 1141.8 | 1396.0 | 254.2 |
| 23 | 2041-12-31 | 3686.4 | 3492.1 | -194.3 | -2525.6 | -2492.3 | 33.3 | n/a | 0.0 | n/a | n/a | 999.7 | n/a | 1160.7 | 999.7 | -161.0 |
| 24 | 2042-06-30 | 6108.9 | 3925.9 | -2183.1 | -2875.3 | -2125.2 | 750.1 | n/a | 0.0 | n/a | n/a | 1800.7 | n/a | 3233.6 | 1800.7 | -1432.9 |
| 25 | 2042-12-31 | 6090.0 | 5539.4 | -550.6 | -2923.0 | -3482.2 | -559.2 | n/a | 0.0 | n/a | n/a | 2057.2 | n/a | 3167.0 | 2057.2 | -1109.9 |
| 26 | 2043-06-30 | 6094.6 | 6309.6 | 215.0 | -2829.3 | -3415.6 | -586.2 | n/a | 0.0 | n/a | n/a | 2894.1 | n/a | 3265.3 | 2894.1 | -371.2 |
| 27 | 2043-12-31 | 5240.4 | 5490.9 | 250.6 | -2844.8 | -3472.2 | -627.4 | n/a | 0.0 | n/a | n/a | 2018.8 | n/a | 2395.6 | 2018.8 | -376.8 |
| 28 | 2044-06-30 | 6191.8 | 6414.6 | 222.7 | 0.0 | 0.0 | 0.0 | n/a | 0.0 | n/a | n/a | 6414.6 | n/a | 6191.8 | 6414.6 | 222.7 |
| 29 | 2044-12-31 | 5175.3 | 5531.0 | 355.6 | 0.0 | 0.0 | 0.0 | n/a | 0.0 | n/a | n/a | 5531.0 | n/a | 5175.3 | 5531.0 | 355.6 |
| 30 | 2045-06-30 | 6212.3 | 6484.5 | 272.2 | 0.0 | 0.0 | 0.0 | n/a | 0.0 | n/a | n/a | 6484.5 | n/a | 6212.3 | 6484.5 | 272.2 |
| 31 | 2045-12-31 | 5090.8 | 5619.2 | 528.5 | 0.0 | 0.0 | 0.0 | n/a | 0.0 | n/a | n/a | 5619.2 | n/a | 5090.8 | 5619.2 | 528.5 |
| 32 | 2046-06-30 | 6422.3 | 6574.1 | 151.8 | 0.0 | 0.0 | 0.0 | n/a | 0.0 | n/a | n/a | 6574.1 | n/a | 6422.3 | 6574.1 | 151.8 |
| 33 | 2046-12-31 | 5092.5 | 5694.0 | 601.4 | 0.0 | 0.0 | 0.0 | n/a | 0.0 | n/a | n/a | 5694.0 | n/a | 5092.5 | 5694.0 | 601.4 |
| 34 | 2047-06-30 | 6585.9 | 6663.5 | 77.6 | 0.0 | 0.0 | 0.0 | n/a | 0.0 | n/a | n/a | 6663.5 | n/a | 6585.9 | 6663.5 | 77.6 |
| 35 | 2047-12-31 | 5050.2 | 5768.5 | 718.3 | 0.0 | 0.0 | 0.0 | n/a | 0.0 | n/a | n/a | 5768.5 | n/a | 5050.2 | 5768.5 | 718.3 |
| 36 | 2048-06-30 | 6765.1 | 6772.8 | 7.7 | 0.0 | 0.0 | 0.0 | n/a | 0.0 | n/a | n/a | 6772.8 | n/a | 6765.1 | 6772.8 | 7.7 |

## Phase Split

| Phase | Excel R99 | Python R99 | Delta R99 | Delta R69 | Delta signed R70 | Comment |
|---|---:|---:|---:|---:|---:|---|
| PIK phase op_idx 0-24 | 28,258.2 | 31,257.7 | +2,999.5 | +690.4 | +2,309.1 | Early excess is mostly senior DS timing: Python DS is less negative than Excel in many PPA periods. |
| Sweep phase op_idx 25-33 | 43,012.9 | 43,287.4 | +274.4 | +2,047.3 | -1,772.9 | R69 overstatement is mostly offset by Python senior DS being more negative in op_idx 25-27. |
| First distribution transition op_idx 34-36 | 18,401.2 | 19,204.7 | +803.5 | +803.5 | 0.0 | Gap is entirely R69 because senior DS is zero. |
| Post-SHL op_idx 37-59 | 145,073.1 | 155,795.6 | +10,722.5 | +10,722.5 | 0.0 | Dominant full-horizon residual comes after senior debt is gone, so it is not caused by senior DS. |

## Answers

1. **Is the 14,800 gap mostly from R69, R70, R82, R98/R100 carry-forward, or lockup/gating?**  
   Mostly R69. Full-horizon R69 is +14,263.7 kEUR versus Excel, while signed senior DS contributes only +536.2 kEUR. R82/R98/R100 cannot be independently proven from the fixture, but the available fixture shows no observable gating effect.

2. **Is Excel R100 carry-forward non-zero in any relevant period?**  
   Not observable from the fixture. The C1a helper produces no locked periods and no R100 carry-forward. Since available Excel R99 equals R69 plus R70 in aggregate, there is no evidence of material R100 carry-forward in the extracted rows.

3. **Does Excel R99 ever differ from R98 because of lockup?**  
   The fixture does not expose R98. Within available data, R99 behaves like post-senior cash without observable lockup gating.

4. **Does DSRA/JDSRA gate ever fire?**  
   Not in the C1a helper run: no helper lockups occur and Python DSRA movement is zero in this TUHO run. The fixture does not expose JDSRA or period-level R82.

5. **Is the op_idx 24 large negative delta caused by PPA/merchant senior DS transition?**  
   Yes, but it is mixed. At op_idx 24 / 2042-06-30, Python R69 is **-2,183.1 kEUR** below Excel, consistent with the known PPA/merchant boundary mismatch. Python senior DS is **+750.1 kEUR** less negative than Excel, partly offsetting that R69 shortfall. Net R99 delta is **-1,432.9 kEUR**.

6. **Which single component explains most of the early PIK-phase excess cash?**  
   Senior DS timing explains most of the PIK-phase excess: +2,309.1 kEUR of the +2,999.5 kEUR PIK-phase R99 gap. Across the full horizon, however, the dominant component is the cash-tax source inside R69.

7. **Can C1b be a small component fix, or would it require tax/revenue/OPEX engine changes?**  
   C1b cannot be a runtime opt-in yet. A small diagnostic component fix is possible: replace the C1a helper's cash-tax source with an auditable period cash-tax field candidate such as `period.tax_keur`, then remeasure. But using `period.tax_keur` alone would produce about **230,393.9 kEUR**, or **-4,351.1 kEUR** versus Excel, so it is not enough for runtime enablement without resolving revenue/timing differences.

8. **What is the smallest safe next implementation PR?**  
   The smallest safe next PR is **C1b diagnostic-only source refinement**: keep runtime disabled, add helper-side measurement variants for cash-tax source and R69 component attribution, and assert that no variant is enabled for runtime. Do not reattempt SHL `fcf_waterfall` until R99 input is within tolerance on total and selected periods.

## Recommendation

- **C1b runtime opt-in is blocked.**
- **B2 SHL fcf_waterfall remains blocked.**
- Next step should be a small diagnostic/refinement PR, not a production behavior change.
- The first candidate to test is replacing the current `max(0, ebitda - cf_after_tax)` helper tax proxy with an explicit cash-tax field candidate, but only under diagnostics because it over-corrects the full-horizon total and fails selected merchant/post-SHL periods.
