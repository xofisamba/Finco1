# Phase 7K Senior Rate / Day-Count Excel Bridge

## Purpose

This branch extracts and bridges Excel senior debt rate, day-count, DSCR, and CFADS mechanics before any senior debt formula change. It is forensic only.

No runtime behavior was changed. Senior opening debt remains principal-only, senior IDC remains excluded from operating debt, and commitment fees remain excluded from operating debt.

## Main Finding

The first-period senior interest gap is explained by a rate and day-count basis difference:

- Excel uses workbook all-in senior rates and actual-day-like `Senior Debt Period` fractions from `Flags`.
- Python currently uses `financing.all_in_rate / 2`, a fixed semiannual fraction of `0.5`.

For the first operating period:

- TUHO Excel uses `5.9500% * 181/360`; Python uses `5.7500% * 0.5`.
- Oborovo Excel uses `5.95136% * 184/360`; Python uses `5.6500% * 0.5`.

The DSCR / CFADS basis is not the first-order cause in period 1: Python first-period CFADS is nearly identical to the Excel senior CFADS row for both projects. However, Python debt service is lower, so Python actual DSCR is higher than Excel.

No runtime fix is implemented because the exact convention must still be proven across all senior periods and both projects before changing formulas.

## Excel Formula References

### TUHO

Workbook: `20260330_TUHO_BP.xlsm`

| Mechanic | Excel reference | Value / formula | Meaning |
|---|---|---|---|
| First operating period start | `DS!H1` | `2030-01-01`, `=Flags!H5` | Beginning of first operating senior period. |
| First operating period end | `DS!H2` | `2030-06-30`, `=Flags!H6` | End of first operating senior period. |
| Senior debt period fraction | `DS!H6` | `0.5027777778`, `=Flags!H23` | `181 / 360`; Excel senior debt interest period fraction. |
| Fixed base rate | `DS!H37` | `0.033`, `=IF(H8,$C$37,H36)*H5` | 100% fixed hedge path in TUHO. |
| Margin | `DS!H40` | `0.0265`, `=H5*IF(H$3,VLOOKUP(H$3,Inputs!$F$185:$G$189,2,1),0)%/100` | Senior margin. |
| All-in rate | `DS!H41` | `0.0595`, `=SUM(H38,H40)` | All-in senior rate for first period. |
| Interest formula | `DS!H61` | `=H58*H41*H6*(H88=0)` | Opening balance times all-in rate times period fraction. |
| Senior principal formula | `DS!H60` | `=MIN(H58,H$43*Inputs!$D$182*$B$57-H63)` | Principal from available senior CF / sizing basis less gross interest. |
| Senior CF for repayment | `DS!H20` | `=(H17/H19+SUM(CF!H73:H73))*H9*$B20` | Debt sizing / repayment cash available. |
| DSCR target | `DS!H19` | `1.2`, `=H13*$C$19+(1-H13)*$B$19` | PPA-period DSCR target. |
| Senior opening balance | `DS!H47` | `43,358.531` | Principal-only opening debt. |
| Senior interest | `DS!H50` | `1,297.082` | Total senior net interest. |
| Senior principal | `DS!H49` | `819.279` | Scheduled principal. |
| Senior debt service | `DS!H54` | `2,116.361` | Principal plus interest. |
| Senior closing balance | `DS!H53` | `42,539.252` | Closing debt balance. |
| CFADS / FCF banks | `CF!H69` | `3,070.176` | Senior CFADS / FCF banks reference used in DSCR rows. |

TUHO input references:

- `Inputs!D185 = 0.031`, base rate.
- `Inputs!D187 = 0.033`, all-in base rate before margin add-on.
- `Inputs!D213 = 1.0`, hedge coverage.
- `Inputs!D204 = 1.2`, target DSCR.

### Oborovo

Workbook: `20260414_BP_Oborovo_Sensitivity_FINAL for PPT.xlsm`

| Mechanic | Excel reference | Value / formula | Meaning |
|---|---|---|---|
| First operating period start | `DS!H1` | `2030-07-01`, `=Flags!H5` | Beginning of first operating senior period. |
| First operating period end | `DS!H2` | `2030-12-31`, `=Flags!H6` | End of first operating senior period. |
| Senior debt period fraction | `DS!H6` | `0.5111111111`, `=Flags!H23` | `184 / 360`; Excel senior debt interest period fraction. |
| Floating base rate | `DS!H39` | `0.037068`, `=IF(H5,HLOOKUP(H$3,Inputs!$A$304:$T$305,2,0),0)*(1+$C$39)` | Floating curve component. |
| Fixed base rate | `DS!H40` | `0.032`, `=IF(H8,$C$40,H39)*H5` | Fixed hedge component. |
| Blended base rate | `DS!H41` | `0.0330136`, `=SUMPRODUCT($B$39:$B$40,H39:H40)` | 20% floating / 80% fixed blend. |
| Margin | `DS!H43` | `0.0265`, `=H5*IF(H$3,VLOOKUP(H$3,Inputs!$F$202:$G$206,2,1),0)%/100` | Senior margin. |
| All-in rate | `DS!H44` | `0.0595136`, `=SUM(H41,H43)` | All-in senior rate for first period. |
| Interest formula | `DS!H64` | `=H61*H44*H6*(H91=0)` | Opening balance times all-in rate times period fraction. |
| Senior principal formula | `DS!H63` | `=MIN(H61,H$46*Inputs!$D$199*$B$60-H66)` | Principal from available senior CF / sizing basis less gross interest. |
| Senior CF for repayment | `DS!H46` | `2,239.133`, `=H23*H5` | Available senior CF / debt service amount. |
| Senior opening balance | `DS!H50` | `42,852.279` | Principal-only opening debt. |
| Senior interest | `DS!H53` | `1,303.483` | Total senior net interest. |
| Senior principal | `DS!H52` | `935.650` | Scheduled principal. |
| Senior debt service | `DS!H57` | `2,239.133` | Principal plus interest. |
| Senior closing balance | `DS!H56` | `41,916.629` | Closing debt balance. |
| Senior DSCR | `CF!H138` | `1.15`, `=IF(H$80=0,10,ROUND(-H$141/H$80,3))` | Excel reported senior DSCR. |
| CFADS / FCFB senior | `CF!H141` | `2,575.003`, `=H$79*H$13` | Senior CFADS / FCFB senior. |

Oborovo input references:

- `Inputs!D202 = 0.03`, base rate.
- `Inputs!D204 = 0.032`, all-in base rate before margin add-on.
- `Inputs!D230 = 0.8`, hedge coverage.
- `Inputs!D221 = 1.15`, target DSCR.

## Period Bridge

### TUHO

| op_idx | date | Excel opening | Python opening | Excel interest | Python interest | Excel principal | Python principal | Excel DS | Python DS | Excel closing | Python closing | Excel rate | Python rate | Excel fraction | Python fraction | Excel CFADS | Python CFADS |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 2030-06-30 | 43,358.531 | 43,359.000 | 1,297.082 | 1,246.571 | 819.279 | 742.535 | 2,116.361 | 1,989.107 | 42,539.252 | 42,616.465 | 5.9500% | 5.7500% | 0.502778 | 0.500000 | 3,070.176 | 3,070.194 |
| 1 | 2030-12-31 | 42,539.252 | 42,616.465 | 1,293.666 | 1,225.223 | 857.773 | 796.852 | 2,151.439 | 2,022.075 | 41,681.478 | 41,819.613 | 5.9500% | 5.7500% | 0.511111 | 0.500000 | 3,121.063 | 3,121.081 |
| 2 | 2031-06-30 | 41,681.478 | 41,819.613 | 1,246.913 | 1,202.314 | 897.779 | 809.583 | 2,144.692 | 2,011.897 | 40,783.700 | 41,010.029 | 5.9500% | 5.7500% | 0.502778 | 0.500000 | 3,111.650 | 3,105.372 |
| 3 | 2031-12-31 | 40,783.700 | 41,010.029 | 1,240.278 | 1,179.038 | 939.961 | 866.205 | 2,180.239 | 2,045.244 | 39,843.738 | 40,143.824 | 5.9500% | 5.7500% | 0.511111 | 0.500000 | 3,163.224 | 3,156.842 |
| 27 | 2043-12-31 | 2,760.833 | 3,326.161 | 83.960 | 95.627 | 2,760.833 | 3,326.161 | 2,844.793 | 3,421.788 | 0.000 | 0.000 | 5.9500% | 5.7500% | 0.511111 | 0.500000 | 5,240.375 | 5,328.821 |

### Oborovo

| op_idx | date | Excel opening | Python opening | Excel interest | Python interest | Excel principal | Python principal | Excel DS | Python DS | Excel closing | Python closing | Excel rate | Python rate | Excel fraction | Python fraction | Excel CFADS | Python CFADS |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 2030-12-31 | 42,852.279 | 42,852.267 | 1,303.483 | 1,210.577 | 935.650 | 844.906 | 2,239.133 | 2,055.482 | 41,916.629 | 42,007.361 | 5.95136% | 5.6500% | 0.511111 | 0.500000 | 2,575.003 | 2,575.331 |
| 1 | 2031-06-30 | 41,916.629 | 42,007.361 | 1,254.234 | 1,186.708 | 948.392 | 835.261 | 2,202.626 | 2,021.969 | 40,968.237 | 41,172.100 | 5.95136% | 5.6500% | 0.502778 | 0.500000 | 2,533.020 | 2,533.342 |
| 2 | 2031-12-31 | 40,968.237 | 41,172.100 | 1,222.505 | 1,163.112 | 1,018.020 | 923.109 | 2,240.525 | 2,086.221 | 39,950.217 | 40,248.990 | 5.83832% | 5.6500% | 0.511111 | 0.500000 | 2,576.604 | 2,613.844 |
| 3 | 2032-06-30 | 39,950.217 | 40,248.990 | 1,179.169 | 1,137.034 | 1,091.108 | 920.873 | 2,270.277 | 2,057.907 | 38,859.108 | 39,328.117 | 5.83832% | 5.6500% | 0.505556 | 0.500000 | 2,610.819 | 2,578.369 |
| 27 | 2044-06-30 | 1,464.204 | 2,460.654 | 43.235 | 69.513 | 1,464.204 | 2,460.654 | 1,507.439 | 2,530.167 | 0.000 | 0.000 | 5.84072% | 5.6500% | 0.505556 | 0.500000 | 2,638.364 | 2,952.834 |

## Root-Cause Candidates

| Candidate | Status | Evidence | Confidence |
|---|---|---|---|
| Rate basis | Confirmed contributor | TUHO Excel first-period all-in rate is `5.95%` vs Python `5.75%`; Oborovo Excel first-period all-in rate is `5.95136%` vs Python `5.65%`. | High |
| Day-count / period fraction | Confirmed contributor | Excel uses `DS!row 6` fractions from `Flags`: TUHO first period `181/360`, Oborovo first period `184/360`; Python uses fixed `0.5`. | High |
| ACT/360 vs ACT/365 | Excel senior debt period strongly indicates ACT/360-style fractions | `181/360 = 0.502778`, `184/360 = 0.511111`; construction IDC rows also use monthly/day fractions. | Medium-high |
| Hedge / base-rate treatment | Confirmed contributor for Oborovo | Oborovo blends 20% floating and 80% fixed via `SUMPRODUCT`; Python uses flat base + margin. TUHO is 100% fixed in Excel, but Python fixed base differs. | High |
| First-period COD transition | Not primary opening-balance issue | Dates and opening balances align. The first-period fraction differs from fixed semiannual timing. | Medium |
| DSCR / CFADS basis | Not first-order first-period issue | First-period CFADS is nearly aligned: TUHO delta about `+0.018`; Oborovo delta about `+0.328`. But Python debt service is lower, producing higher Python DSCR. | Medium |
| Repayment timing | Consequence of interest / debt-service sizing basis | Both models repay in first operating period. Principal gap follows debt-service / interest basis. | Medium |

## Is A Runtime Fix Justified?

Not yet.

The evidence proves Excel uses workbook-specific rates and actual-day-like period fractions, but a safe runtime fix should not be made until:

1. the same period-fraction convention is extracted across all operating periods,
2. rate schedules are mapped to Python inputs without hardcoding Excel rows,
3. Oborovo's floating/fixed blend is represented explicitly,
4. TUHO's fixed base rate difference is explained through inputs rather than a one-off override,
5. sculpting uses the same debt service / discounting convention as Excel.

## Recommendation

Next branch: `phase7k-senior-rate-schedule-runtime-design`.

Scope:

- design runtime-safe rate schedule and day-count inputs,
- decide whether senior debt should use ACT/360 period fractions,
- represent fixed/floating hedge mix without Excel hardcoding,
- define regression tests for TUHO and Oborovo senior schedules,
- still avoid SHL, revenue, OPEX, tax, construction capitalization, R99, sponsor, UI, and cache changes.
