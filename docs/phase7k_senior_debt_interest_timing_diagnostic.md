# Phase 7K Senior Debt Interest Timing Diagnostic

## Purpose

This diagnostic isolates the remaining senior debt schedule mismatch after the senior opening balance policy was resolved.

Confirmed policy:

- operating senior debt opens on principal only,
- senior IDC is not capitalized into operating senior debt,
- commitment fees are not capitalized into operating senior debt.

No runtime formula changes were made in this branch. SHL, revenue, OPEX, tax, R99, construction capitalization, sponsor waterfall, UI, and cache behavior remain untouched.

## Data Sources

Excel workbooks:

- TUHO: `20260330_TUHO_BP.xlsm`, sheet `DS`.
- Oborovo: `20260414_BP_Oborovo_Sensitivity_FINAL for PPT.xlsm`, sheet `DS`.

Python model:

- Current Phase 7 main lineage with Phase 7I/7J diagnostics and Phase 7K senior opening policy tests.
- Runtime senior opening debt remains principal-only.

## Excel Row References

| Project | Opening | Principal | Interest | Closing | First operating column |
|---|---|---|---|---|---|
| TUHO | `DS!H47` | `DS!H49` | `DS!H50` | `DS!H53` | `H`, ending `2030-06-30` |
| Oborovo | `DS!H50` | `DS!H52` | `DS!H53` | `DS!H56` | `H`, ending `2030-12-31` |

## TUHO Senior Schedule Bridge

First four operating periods:

| op_idx | date | Excel opening | Python opening | Δ opening | Excel interest | Python interest | Δ interest | Excel principal | Python principal | Δ principal | Excel DS | Python DS | Δ DS | Excel closing | Python closing | Δ closing |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 2030-06-30 | 43,358.531 | 43,359.000 | 0.469 | 1,297.082 | 1,246.571 | -50.511 | 819.279 | 742.535 | -76.743 | 2,116.361 | 1,989.107 | -127.255 | 42,539.252 | 42,616.465 | 77.213 |
| 1 | 2030-12-31 | 42,539.252 | 42,616.465 | 77.213 | 1,293.666 | 1,225.223 | -68.443 | 857.773 | 796.852 | -60.921 | 2,151.439 | 2,022.075 | -129.364 | 41,681.478 | 41,819.613 | 138.134 |
| 2 | 2031-06-30 | 41,681.478 | 41,819.613 | 138.134 | 1,246.913 | 1,202.314 | -44.599 | 897.779 | 809.583 | -88.195 | 2,144.692 | 2,011.897 | -132.794 | 40,783.700 | 41,010.029 | 226.330 |
| 3 | 2031-12-31 | 40,783.700 | 41,010.029 | 226.330 | 1,240.278 | 1,179.038 | -61.239 | 939.961 | 866.205 | -73.756 | 2,180.239 | 2,045.244 | -134.995 | 39,843.738 | 40,143.824 | 300.086 |

Final repayment period:

| op_idx | date | Excel opening | Python opening | Δ opening | Excel interest | Python interest | Δ interest | Excel principal | Python principal | Δ principal | Excel DS | Python DS | Δ DS | Excel closing | Python closing | Δ closing |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 27 | 2043-12-31 | 2,760.833 | 3,326.161 | 565.328 | 83.960 | 95.627 | 11.667 | 2,760.833 | 3,326.161 | 565.328 | 2,844.793 | 3,421.788 | 576.995 | 0.000 | 0.000 | 0.000 |

Total senior debt service:

| Project | Excel total senior DS | Python total senior DS | Delta |
|---|---:|---:|---:|
| TUHO | 66,181.347 | 65,826.388 | -354.959 |

## Oborovo Senior Schedule Bridge

First four operating periods:

| op_idx | date | Excel opening | Python opening | Δ opening | Excel interest | Python interest | Δ interest | Excel principal | Python principal | Δ principal | Excel DS | Python DS | Δ DS | Excel closing | Python closing | Δ closing |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 2030-12-31 | 42,852.279 | 42,852.267 | -0.012 | 1,303.483 | 1,210.577 | -92.907 | 935.650 | 844.906 | -90.744 | 2,239.133 | 2,055.482 | -183.651 | 41,916.629 | 42,007.361 | 90.732 |
| 1 | 2031-06-30 | 41,916.629 | 42,007.361 | 90.732 | 1,254.234 | 1,186.708 | -67.526 | 948.392 | 835.261 | -113.130 | 2,202.626 | 2,021.969 | -180.657 | 40,968.237 | 41,172.100 | 203.863 |
| 2 | 2031-12-31 | 40,968.237 | 41,172.100 | 203.863 | 1,222.505 | 1,163.112 | -59.393 | 1,018.020 | 923.109 | -94.911 | 2,240.525 | 2,086.221 | -154.304 | 39,950.217 | 40,248.990 | 298.774 |
| 3 | 2032-06-30 | 39,950.217 | 40,248.990 | 298.774 | 1,179.169 | 1,137.034 | -42.135 | 1,091.108 | 920.873 | -170.236 | 2,270.277 | 2,057.907 | -212.370 | 38,859.108 | 39,328.117 | 469.009 |

Final repayment period:

| op_idx | date | Excel opening | Python opening | Δ opening | Excel interest | Python interest | Δ interest | Excel principal | Python principal | Δ principal | Excel DS | Python DS | Δ DS | Excel closing | Python closing | Δ closing |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 27 | 2044-06-30 | 1,464.204 | 2,460.654 | 996.450 | 43.235 | 69.513 | 26.278 | 1,464.204 | 2,460.654 | 996.450 | 1,507.439 | 2,530.167 | 1,022.728 | 0.000 | 0.000 | 0.000 |

Total senior debt service:

| Project | Excel total senior DS | Python total senior DS | Delta |
|---|---:|---:|---:|
| Oborovo | 62,985.358 | 63,500.895 | 515.537 |

## Hypotheses Checked

### A. Interest timing

Confirmed likely contributor.

Excel first-period interest is higher than Python for both projects:

- TUHO: Python is `50.511` kEUR lower.
- Oborovo: Python is `92.907` kEUR lower.

Python currently uses a simplified semiannual period rate derived from annual all-in rate divided by two. Excel appears to apply a different first-period interest convention, likely involving actual dates, exact rate basis, hedge/fixed-rate composition, or a workbook-specific interest period fraction.

This branch does not prove the exact Excel day-count method. No interest timing fix was implemented.

### B. Repayment timing

Confirmed likely contributor.

Python first-period principal is lower than Excel for both projects:

- TUHO: Python is `76.743` kEUR lower.
- Oborovo: Python is `90.744` kEUR lower.

The principal gap follows the debt-service gap rather than indicating a shifted repayment start: both Excel and Python repay principal in the first operating period.

### C. DSCR sculpting basis

Likely contributor.

Python first-period DSCR is flat across early periods for each project because the runtime sculpting schedule uses its own CFADS basis:

- TUHO early Python DSCR: approximately `1.5435x`.
- Oborovo early Python DSCR: approximately `1.2529x`.

Excel debt service is higher in early periods, suggesting its CFADS / DSCR sculpting basis is not identical to Python's after-tax EBITDA proxy or repayment schedule.

### D. COD transition

Partially confirmed as a possible interest contributor, but not an opening balance contributor.

The first operating dates align:

- TUHO: `2030-06-30`.
- Oborovo: `2030-12-31`.

Opening balances align within rounding. The remaining mismatch is therefore not caused by adding construction IDC or fees into debt at COD.

## Implemented Timing Fix

None.

The evidence identifies likely timing / sculpting-basis issues but does not yet prove a single safe runtime formula change.

## Remaining Gaps

| Gap | Status | Why not fixed here |
|---|---|---|
| Exact Excel first-period interest rate / day-count basis | unresolved | Requires extracting rate rows, period fractions, and hedge/floating composition from Excel DS / Inputs. |
| Exact Excel DSCR sculpting CFADS basis | unresolved | Requires bridge from Excel CFADS / R69 / senior DS rows against Python sculpting input. |
| Early-period principal repayment gap | unresolved | Depends on the debt-service sculpting basis and interest convention. |
| Final-period larger Python balloon | unresolved | Likely cumulative effect of early lower principal and schedule shape. |

## Recommendation

Do not implement a timing fix yet.

Recommended next branch: `phase7k-senior-rate-daycount-excel-bridge`.

Scope:

- extract Excel senior debt rate rows, period-fraction rows, DSCR rows, and CFADS rows,
- identify whether Excel interest uses ACT/365, ACT/360, fixed semiannual, or workbook-specific period flags,
- compare Excel sculpting input to Python `cfads_for_sculpt`,
- only then implement a small isolated fix if one convention is proven for both TUHO and Oborovo.
