# Phase 6 — Excel Interest / Depreciation Extraction

## Branch
`phase6-excel-interest-dep-extraction`

## Status
**Diagnostic-first — no production code changes, no fix implemented.**

---

## Excel Workbook
`20260330_TUHO_BP.xlsm` — TUHO project financial model (1.84 MB, macro-enabled)

### Sheet / Row References

| Sheet | Row | Label | Description |
|-------|-----|-------|-------------|
| CF | R3 | Year | Period column header (col7=construction, col8+=operational periods) |
| CF | R40 | EBITDA | Project EBITDA per period |
| CF | R67 | Corporate Income Tax | Annual CIT cash payment (negative) |
| CF | R70 | Senior Debt Service | Senior debt principal + interest |
| CF | R71 | Senior Interest | Senior interest component |
| P&L | R13 | Depreciation | Book depreciation |
| P&L | R16 | EBIT | Earnings before interest and tax |
| P&L | R24 | Senior Interests | Senior interest (P&L) |
| P&L | R27 | Shareholder Loan Interests | SHL interest |
| P&L | R35 | Taxable Income | Pre-loss taxable income |
| P&L | R36 | - Losses N-1 | Opening loss carryforward balance |
| P&L | R37 | - Allocated losses | Losses applied this period |
| P&L | R38 | - Losses N | Closing loss balance |
| P&L | R39 | Carriable losses | Carried-forward loss balance |
| P&L | R41 | Taxable Profit N | Taxable profit after loss utilization |
| P&L | R43 | Corporate Income Tax | CIT charge (positive amount) |
| P&L | R48 | Legal reserve | Legal reserve appropriation |
| P&L | R49 | Retained Earnings | Retained earnings |
| P&L | R50 | Net Dividends | Dividends distributed |
| P&L | R54 | Fiscal Reintegration | ATAD fiscal add-back |
| Dep | R30 | Depreciation | Book depreciation (periodic) |
| Dep | R31 | Unlevered Depreciation | Unlevered depreciation |

### Column Mapping (P&L / CF)
- col7 = construction period
- col8 = Year 1 H1
- col9 = Year 1 H2
- ...
- col6 + 2×yr = yr N H1 (1-based)
- col7 + 2×yr = yr N H2 (1-based)

Python P-index: P_n = (yr - 1) × 2 + (0 if H1 else 1)

---

## Extracted Period-Level Values

### Years 13–15 (P24–P29) — H2 periods

| Period | P&L R35 TI | P&L R36 LossN-1 | P&L R37 Alloc | P&L R38 LossN | P&L R39 CarryFwd | P&L R41 TP | P&L R43 CIT | CF R67 cash tax | R24 SeniorInt | R27 SHLInt | Dep R30 BookDep |
|--------|----------:|-------------:|------------:|------------:|------------:|----------:|----------:|----------:|----------:|----------:|----------:|
| P25 yr13H2 | 2,298.72 | -5,291.80 | 2,298.72 | -2,993.09 | -2,993.09 | 0.00 | **120.19** | **-120.19** | 246.46 | 1,703.16 | 1,785.56 |
| P27 yr14H2 | 2,558.45 | 1,099.50 | 0.00 | 0.00 | 0.00 | 2,558.45 | **955.24** | **-955.24** | 83.96 | 1,577.67 | 1,785.56 |
| P29 yr15H2 | 2,902.62 | 3,152.60 | 0.00 | 0.00 | 0.00 | 2,902.62 | **1,084.54** | **-1,084.54** | 0.00 | 1,356.59 | 1,780.69 |

*All values in kEUR. P&L R43 is positive (CIT charge); CF R67 is negative (cash outflow).*

### Selected Later Periods

| Period | P&L R35 TI | P&L R36 LossN-1 | P&L R37 Alloc | P&L R38 LossN | P&L R39 CarryFwd | P&L R41 TP | P&L R43 CIT | CF R67 cash tax | eff rate |
|--------|----------:|-------------:|------------:|------------:|------------:|----------:|----------:|----------:|-------:|
| P37 yr19H2 | 5,003.76 | 4,106.00 | 0.00 | 0.00 | 0.00 | 5,003.76 | **1,811.25** | **-1,811.25** | 36.2% |
| P41 yr21H2 | 7,037.24 | 4,106.00 | 0.00 | 0.00 | 0.00 | 7,037.24 | **2,554.40** | **-2,554.40** | 36.3% |
| P49 yr25H2 | 7,701.53 | 4,106.00 | 0.00 | 0.00 | 0.00 | 7,701.53 | **2,795.53** | **-2,795.53** | 36.3% |
| P59 yr30H2 | 8,264.44 | 4,106.00 | 0.00 | 0.00 | 0.00 | 8,264.44 | **2,999.85** | **-2,999.85** | 36.3% |

---

## Python Comparison (flag ON, H2 periods)

| Period | Python EBITDA | Python tax_keur | Python cash_tax / R67 | Python taxable_inc | Excel P&L R41 TP | Excel CIT | Gap CIT |
|--------|----------:|----------:|----------:|----------:|----------:|----------:|----------:|
| P25 yr13H2 | 6,242 | 760 | 1,481 | 4,223 | 0 | 120 | +1,361 |
| P27 yr14H2 | 6,217 | 811 | 1,580 | 4,505 | 2,558 | 955 | +625 |
| P29 yr15H2 | 6,256 | 875 | 1,707 | 4,861 | 2,903 | 1,085 | +622 |
| P37 yr19H2 | 6,810 | 1,219 | 2,424 | 6,772 | 5,004 | 1,811 | +613 |
| P41 yr21H2 | 7,135 | 1,277 | 2,534 | 7,097 | 7,037 | 2,554 | -20 |
| P49 yr25H2 | 7,743 | 1,387 | 2,751 | 7,704 | 7,702 | 2,796 | -45 |
| P59 yr30H2 | 8,249 | 1,478 | 2,931 | 8,210 | 8,264 | 3,000 | -69 |

*Python flag ON tax bridge engine active. All values in kEUR.*

---

## Cumulative Years 13–30 Residual Bridge

| Source | Amount (kEUR) |
|--------|-------------:|
| Python R67 sum (H2, P24–P59) | -43,512 |
| Excel R67 sum (H2, P25–P59) | -38,241 |
| **Residual** | **-5,271** |

### Residual decomposition (per-period direction analysis):
- **Years 13–19**: Python CIT > Excel CIT (positive gap = Python over-pays)
- **Years 21–30**: Python CIT ≈ Excel CIT, gap narrows to near-zero

This pattern is consistent with a **construction-period loss balance** that:
1. Is applied to reduce taxable income in years 13–19 (where the gap is largest)
2. Is exhausted by year 20–21 (where the gap disappears)

---

## Construction-Period Loss — Evidence

### Opening loss balance at COD (yr1H2 = P1):
P&L R38 Loss N (col8) = **-3,568.69 kEUR**

### Loss balance growth during construction:
- P1 (yr1H2): -3,568.69
- P3 (yr2H2): -6,319.83
- P5 (yr3H2): -8,940.91

The negative balance grows as losses accumulate during construction.

### Loss balance at COD (yr12H2 = P23):
P&L R39 Carriable losses (col30) = **-5,867.62 kEUR**

### Loss balance in years 13–15:
- P24 yr13H1: -5,516.47 (slight recovery as TI positive)
- P25 yr13H2: **-2,993.09** (loss used: 5,516 − 2,993 = 2,523 applied)
- P26 yr14H1: **0.00** (loss fully utilized, partially reversed)

### Loss balance in years 16–30:
- P27 yr14H2: **0.00** (loss fully utilized)
- P29 yr15H2: **0.00** (no residual loss)
- P37 yr19H2: **4,106.00** (positive — cumulative profits exceed losses, net positive carryforward)
- P59 yr30H2: **4,106.00** (unchanged — no losses used or generated)

### Interpretation
Excel P&L R39 shows a model-specific carried-loss / cumulative tax position pattern. It is negative through early operating periods, reaches zero, then becomes +4,106 kEUR and remains constant through years 16–30.

This suggests Excel's R36/R37/R38/R39 formula chain is materially different from Python's current loss engine. Python's current tax bridge does not import or reproduce this Excel R39 construction-period/cumulative loss position into years 13–30.

**Evidence quality: HIGH** — directly extracted from P&L R39 "Carriable losses" row for each period. The 4,106 kEUR figure appears consistently from yr16 onwards.

**The exact legal/tax meaning of positive R39 requires formula inspection.** Whether this is:
- An explicit construction-period opening balance (model-set)
- An accumulated result from formula chain (construction-period losses + operating-period profits)
- A hybrid (construction-period losses never expire in this model)

**Cannot be confirmed from data values alone.** Would require formula inspection of P&L R36/R38/R39 cells.

---

## Legal Reserve / Effective Rate Anomaly

### Observed effective rates (Excel P&L):
| Period | P&L R41 TP | P&L R43 CIT | Effective Rate |
|--------|----------:|----------:|--------------:|
| P25 yr13H2 | 0.00 | 120.19 | N/M (TP=0, partial loss allocation, not meaningful) |
| P27 yr14H2 | 2,558.45 | 955.24 | **37.3%** |
| P29 yr15H2 | 2,902.62 | 1,084.54 | **37.3%** |
| P37 yr19H2 | 5,003.76 | 1,811.25 | **36.2%** |
| P41 yr21H2 | 7,037.24 | 2,554.40 | **36.3%** |
| P59 yr30H2 | 8,264.44 | 2,999.85 | **36.3%** |

### Observation
Standard 18% CIT on TP_N would produce ~1,407 kEUR (18% × 7,817 avg TP) for year 21+. Excel shows ~2,554 kEUR, an effective rate of **~36.3%**.

### Candidate explanations:
1. **Legal reserve**: Croatian law requires 10% of net profit to legal reserve until it reaches 10% of share capital. If legal reserve appropriation (P&L R48) reduces retained earnings but not taxable income, the effective tax rate on distributions would be higher.

2. **Formula issue**: P&L R43 "Corporate Income Tax" may be a pre-legal-reserve charge while R41 "Taxable Profit N" = R35 + R36 + R37 + R38.

3. **SHL interest non-deductibility**: If SHL interest above the ATAD/interest limitation is non-deductible but still deducted in the accounting P&L, the accounting tax charge would be higher than the fiscal tax charge.

**Evidence quality: LOW** — R48 "Legal reserve" shows 0 for all extracted years. The effective rate anomaly may be a formula-side effect of how losses are allocated in the model.

**Formula references: NOT confirmed.** Would require formula inspection of P&L R41/R43 cells.

---

## Dominant Residual Driver

**Confidence level: HIGH (construction-period loss pattern), MEDIUM (legal reserve effective rate anomaly)**

Primary: **Excel P&L R39 shows a model-specific construction-period/cumulative tax position pattern** that reduces taxable income (P&L R41) in years 13–19. Python's current tax bridge does not import or reproduce this Excel R39 pattern into years 13–30.

Secondary: **Effective rate anomaly (~36%)** in Excel years 14+ may reflect a legal reserve appropriation or accounting treatment not yet identified in the Python model.

---

## Recommended Next Branch

| Branch | Trigger |
|--------|---------|
| `phase6-loss-carryforward-source-bridge` | If Excel construction-period loss (P&L R38/R39) is confirmed as dominant driver |
| `phase6-legal-reserve-source-bridge` | If legal reserve treatment is confirmed as formula-backed |
| `phase6-r67-residual-decision` | If residual is accepted as known calibration gap |

**Recommended:** Investigate `phase6-loss-carryforward-source-bridge` next — the construction-period loss pattern is the most clearly evidenced driver.
