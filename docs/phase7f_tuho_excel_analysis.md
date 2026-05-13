# TUHO Calibration Analysis — Excel vs Python Model

**Date:** 2026-05-13
**Branch:** `phase7f-tuho-distribution-calibration`
**Source:** `20260330_TUHO_BP.xlsm` (data_only extraction)

---

## Executive Summary

| Metric | Excel | Python | Delta | Status |
|---|---|---|---|---|
| SPV equity IRR | 11.61% | 11.56% | -0.05 pp | ✅ within ±1pp |
| Total distributions (R119) | 151,709 kEUR | 180,570 kEUR | +28,861 kEUR (+19.0%) | ❌ not calibrated |
| First distribution | P36 (2047-12-31) | P33 (2046-06-30) | -3 periods | ❌ |
| Total CIT (R67) | -38,241 kEUR | TBD | — | ⚠️ |
| SHL fully repaid | P36 (2047-12-31) | TBD | — | ⚠️ |

**Root cause:** Python distributes during P33-P35 when Excel R113 gate = 0 (closed). Excel only starts distributing at P36 when R113 opens partially (421 kEUR) and SHL balance reaches 0.

**Distribution gate:** R113 Max row controls the gate. During P30-P35, R113=0 even though R99 (FCF for Distribution) is positive — indicating Excel holds cash for SHL sweep or other reserves.

---

## 1. Excel Row Mapping

| Row | Description | Total | First non-zero |
|---|---|---|---|
| R67 | Corporate Income Tax | -38,240.9 kEUR | P13 (2041-06-30) |
| R69 | FCF for Banks | 300,926.8 kEUR | P1 |
| R70 | Senior Debt Service | -66,181.3 kEUR | P1 |
| R84 | FCF for Junior Debt | 234,745.4 kEUR | P1 |
| R98 | Distribution Account | 234,745.4 kEUR | P1 |
| R99 | FCF for Distribution | 234,745.4 kEUR | P1 |
| R102 | FCF for SHL | 234,745.4 kEUR | P1 |
| R104 | Net SHL | -82,486.0 kEUR | P1 |
| R106 | FCF for dividends | 152,259.4 kEUR | P36 (2047-12-31) |
| R119 | **Net Dividends** | **151,709.4 kEUR** | **P36 (2047-12-31)** |
| R120 | Gross Dividends | 151,709.4 kEUR | P36 |

**Python `distribution_keur` maps to Excel R119 Net Dividends** (post-senior/post-SHL equity cash), NOT R99 FCF for Distribution.

---

## 2. Per-Period Distribution Comparison

```
Period   Date          Excel R119    Python    Delta    Note
--------------------------------------------------------------
P33     2046-06-30          0.0    5,515.5  +5,515.5  Excel=0 (gate closed)
P34     2046-12-31          0.0    6,663.5  +6,663.5  Excel=0 (gate closed)
P35     2047-06-30          0.0    5,768.5  +5,768.5  Excel=0 (gate closed)
P36     2047-12-31        421.2    6,772.8  +6,351.6  R113=421 (gate partially open)
P37     2048-06-30      6,765.1    5,827.9    -937.1  Python lower than Excel
P38     2048-12-31      5,028.2    6,845.6  +1,817.5  Python higher
P39     2049-06-30      6,911.8    5,920.3    -991.6  Python lower
P40     2049-12-31      4,605.1    6,937.6  +2,332.5  Python higher
P41     2050-06-30      7,037.2    5,996.9  -1,040.3  Python lower
P42     2050-12-31      4,599.5    7,031.3  +2,431.8  Python higher
...
P60     2059-12-31      5,401.6       54.6  -5,347.0  Python mostly repaid
```

**Pattern:** Python > Excel for December periods, Python < Excel for June periods (alternating). This suggests different cash flow timing or SHL interest accrual.

---

## 3. Distribution Gate Analysis (R113 Max Row)

```
Period   Date          R99 FCF Dist    R113 Max    R119 Net Div
--------------------------------------------------------------
P28     2043-12-31        2,395.6           0           0.0
P29     2044-06-30        6,191.8           0           0.0
P30     2044-12-31        5,175.3           0           0.0
P31     2045-06-30        6,212.3           0           0.0
P32     2045-12-31        5,090.8           0           0.0
P33     2046-06-30        6,422.3           0           0.0  ← Python starts distributing here
P34     2046-12-31        5,092.5           0           0.0
P35     2047-06-30        6,585.9           0           0.0
P36     2047-12-31        5,050.2     421.18         421.2  ← Excel first distribution
P37     2048-06-30        6,765.1    6,765.1       6,765.1  ← gate fully open
```

**Finding:** During P33-P35, Excel R99 (FCF for Distribution) is positive (5,000-6,500 kEUR), but R113 Max = 0. This is the SHL sweep/lockup mechanism — cash is withheld for SHL repayment even though senior debt is already repaid (P28).

**Python starts distributing at P33** (3 periods before Excel's first distribution at P36).

---

## 4. SHL Balance Analysis (BS Row 24)

```
Period   Date          SHL Balance (BS R24)
--------------------------------------------------------------
P24     2041-12-31        43,730.7 kEUR  (peak)
P25     2042-06-30        42,231.9 kEUR  (repayment starts)
P26     2042-12-31        40,768.0 kEUR
P27     2043-06-30        39,120.1 kEUR
P28     2043-12-31        38,302.2 kEUR  (senior debt = 0 here)
P29     2044-06-30        33,638.2 kEUR
P30     2044-12-31        29,819.5 kEUR
P31     2045-06-30        24,790.2 kEUR
P32     2045-12-31        20,699.2 kEUR
P33     2046-06-30        15,098.0 kEUR
P34     2046-12-31        10,614.4 kEUR
P35     2047-06-30         4,449.5 kEUR
P36     2047-12-31             0.0 kEUR  (SHL fully repaid)
P37     2048-06-30             0.0 kEUR
```

**Note:** SHL is fully repaid at P36 (2047-12-31), which coincides with Excel's first distribution. But Python starts distributing at P33 (6 months earlier).

**Key question:** What does R113 Max formula do? It seems to gate distributions until SHL is nearly paid off. The partial R113 value at P36 (421 kEUR) might be related to the timing of when the last SHL payment clears.

---

## 5. SHL Service vs Net SHL

```
Period   R102 FCF SHL    R104 Net SHL    BS SHL Bal    SHL Interest (P&L R27)
--------------------------------------------------------------
P1       953.8         -953.8        33,047.5          1,297.4
P14      1,044.8       -1,044.8      38,482.7          1,532.3
P24      1,160.7       -1,160.7      43,730.7          1,740.2
P25      3,233.6       -3,233.6      42,231.9          1,734.9  ← higher FCF (debt repaid)
P28      2,395.6       -2,395.6      38,302.2          1,577.7  ← senior debt = 0
P29      6,191.8       -6,191.8      33,638.2          1,527.9
P35      6,585.9       -6,585.9       4,449.5            421.1
P36      5,050.2       -4,629.0           0.0            179.4  ← partial SHL repayment
P37      6,765.1            0.0           0.0              0.0  ← SHL = 0
```

**Observation at P36:** R102 = 5,050.2 but R104 = -4,629.0 (not 0). This means 421 kEUR was retained (excess over remaining SHL balance). This retained amount (421.2) = R113 Max = R119 Net Dividends at P36.

---

## 6. Key Findings Summary

### Finding 1: SPV equity IRR ✅
Python 11.56% vs Excel 11.61% → delta -0.05 pp (within ±1pp tolerance)

### Finding 2: Distribution total mismatch ❌
Python 180,570 kEUR vs Excel 151,709 kEUR → +19.0% (28,861 kEUR more)

### Finding 3: Distribution timing mismatch ❌
Python first non-zero: P33 (2046-06-30)
Excel first non-zero: P36 (2047-12-31)
Gap: 3 periods (18 months)

### Finding 4: Distribution gate R113=0 for P33-P35 ❌
Excel holds all FCF in P33-P35 (R113=0) despite positive R99
Python distributes immediately (no gate)

### Finding 5: Alternating delta pattern
Python > Excel on December period-ends
Python < Excel on June period-ends
Pattern suggests SHL interest timing or cash sweep cadence difference

### Finding 6: SHL repayment timing
Excel: SHL fully repaid at P36 (2047-12-31)
Python: appears to repay SHL earlier → releases cash earlier for distribution

---

## 7. Required Investigation

The R113 Max row formula is the key to understanding the distribution gate. It likely implements one of:

A. **SHL sweep with threshold:** Withhold all distributions while SHL balance > 0, except allow minimal distributions when SHL is near 0

B. **Cash retention for SHL:** Hold cash in R99/R102 until cumulative SHL repayment reaches a threshold

C. **Reserve account policy:** Some reserve account (not DSRA) accumulates during P25-P35

**Recommendation:** Examine the Excel formula in R113 Max row to understand the exact gate condition.

---

## 8. Action Items

| Priority | Action | Status |
|---|---|---|
| P0 | Investigate R113 Max formula in Excel | Pending |
| P0 | Understand why Python allows distributions P33-P35 when Excel R113=0 | Pending |
| P1 | Get Python CIT total vs Excel R67 = -38,241 kEUR | Pending |
| P1 | Get Python SHL total vs Excel Net SHL = -82,486 kEUR | Pending |
| P2 | Align Python distribution gate to match R113 behavior | Pending |
| P2 | Fix distribution timing to match Excel P36 start | Pending |

---

## 9. Not Calibrated — Do Not Mark as Passed

TUHO is **NOT calibrated** despite equity IRR match. The distribution timing and total are structurally wrong. Do not loosen tests or accept model output as golden.

**Target:** Excel R119 = 151,709 kEUR at period P36-P60
**Current:** Python = 180,570 kEUR at period P33-P60
**Gap:** +28,861 kEUR (+19.0%) and 3-period early start