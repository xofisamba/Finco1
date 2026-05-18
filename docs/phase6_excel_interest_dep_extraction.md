# Phase 6 — Excel Interest / Depreciation Extraction

## Branch
`phase6-excel-interest-dep-extraction`

## Status
**Diagnostic-first — no production code changes, no fix implemented.**

---

## Excel Workbook
`20260330_TUHO_BP.xlsm` — TUHO project financial model (1.84 MB, macro-enabled)

### Sheet / Row References

| Sheet | Row | Label |
|-------|-----|-------|
| CF | R3 | Year |
| CF | R40 | EBITDA |
| CF | R67 | Corporate Income Tax |
| CF | R71 | Senior Interest |
| P&L | R13 | Depreciation |
| P&L | R16 | EBIT |
| P&L | R24 | Senior Interests |
| P&L | R27 | Shareholder Loan Interests |
| P&L | R35 | Taxable Income |
| P&L | R36 | - Losses N-1 |
| P&L | R37 | - Allocated losses |
| P&L | R38 | - Losses N |
| P&L | R39 | Carriable losses |
| P&L | R41 | Taxable Profit N |
| P&L | R43 | Corporate Income Tax |
| P&L | R48 | Legal reserve |
| Dep | R30 | Depreciation |

### Column Mapping
- col7 = construction period
- col8 = Year 1 H1
- col9 = Year 1 H2
- ...
- col32 = Year 13 H1
- col33 = Year 13 H2
- col34 = Year 14 H1
- col35 = Year 14 H2
- etc.

Python P-index: P_n = (yr - 1) × 2 + (0 if H1 else 1)

---

## Extracted Period-Level Values

### Years 13–15 (P24–P29) — H2 periods

| Period | P&L R35 TI | P&L R36 LossN-1 | P&L R37 Alloc | P&L R38 LossN | P&L R39 CarryFwd | P&L R41 TP | P&L R43 CIT | CF R67 cash tax | R24 SeniorInt | Dep R30 BookDep |
|--------|----------:|-------------:|------------:|------------:|------------:|----------:|----------:|----------:|----------:|----------:|
| P25 yr13H2 | 2,298.72 | -5,291.80 | 2,298.72 | -2,993.09 | -2,993.09 | 0.00 | **120.19** | **-120.19** | 246.46 | 1,785.56 |
| P27 yr14H2 | 2,558.45 | 1,099.50 | 0.00 | 0.00 | 0.00 | 2,558.45 | **955.24** | **-955.24** | 83.96 | 1,785.56 |
| P29 yr15H2 | 2,902.62 | 3,152.60 | 0.00 | 0.00 | 0.00 | 2,902.62 | **1,084.54** | **-1,084.54** | 0.00 | 1,780.69 |

*All values in kEUR.*

### Selected Later Periods

| Period | P&L R35 TI | P&L R36 LossN-1 | P&L R37 Alloc | P&L R38 LossN | P&L R39 CarryFwd | P&L R41 TP | P&L R43 CIT | CF R67 cash tax | eff rate |
|--------|----------:|-------------:|------------:|------------:|------------:|----------:|----------:|----------:|-------:|
| P37 yr19H2 | 5,003.76 | 4,106.00 | 0.00 | 0.00 | **0.00** | 5,003.76 | **1,811.25** | **-1,811.25** | 18.0% |
| P41 yr21H2 | 7,037.24 | 4,106.00 | 0.00 | 0.00 | **0.00** | 7,037.24 | **2,554.40** | **-2,554.40** | 18.0% |
| P49 yr25H2 | 7,701.53 | 4,106.00 | 0.00 | 0.00 | **0.00** | 7,701.53 | **2,795.53** | **-2,795.53** | 18.0% |
| P59 yr30H2 | 8,264.44 | 4,106.00 | 0.00 | 0.00 | **0.00** | 8,264.44 | **2,999.85** | **-2,999.85** | 18.0% |

**Key observation:** P&L R39 is **0.00** from yr14H2 onwards. The +4,106 kEUR plateau is on **R36** (Losses N-1), not R39.

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

### Residual decomposition (per-period direction):
- **Years 13–19**: Python CIT > Excel CIT (positive gap = Python over-pays)
- **Years 21–30**: Python CIT ≈ Excel CIT, gap narrows to near-zero

---

## R36 vs R39 — Critical Correction

The +4,106 kEUR plateau referenced in earlier drafts was **mislabeled as R39 (Carriable losses)**.

**Correct attribution:**
- **R39 is 0.00** from yr14H2 (P27) onwards. R39 is effectively capped at 0 when R38 = 0.
- **R36 (Losses N-1)** shows a +4,106.00 kEUR positive balance from yr16H2 (P31) onwards.

The +4,106.00 kEUR is the cumulative sum of R37 Allocated losses:
- P24 yr13H1: R37 = +2,298.72 (first H1 allocation)
- P25 yr13H2: R37 = +1,807.29 (first H2 allocation)
- Total: 2,298.72 + 1,807.29 = **4,106.01 kEUR**

After P25, R37 = 0, so the R36 balance stays flat at +4,106 while R39 = 0.

**Implication:** R39 never carries a positive balance into years 13–30. The earlier description of "Excel R39 carries construction-period losses into operating years" was incorrect.

---

## Effective Rate Verification — No Anomaly

The apparent ~36% effective rate is a **division artifact**, not a real tax anomaly.

### Example: yr19 H2 (P37)

| Value | Amount |
|-------|-------:|
| R41 H1 (yr19H1) | 5,003.76 |
| R41 H2 (yr19H2) | 5,058.74 |
| **Annual R41 (H1+H2)** | **10,062.50** |
| R43 H2 CIT (yr19H2) | 1,811.25 |
| 18% × Annual R41 | 1,811.25 ✓ |

Excel R43 CIT = 18% of the **full annual** taxable profit (H1 + H2 combined), paid only in H2. Dividing H2-only R41 by H2 CIT gives the misleading ~36% figure.

**Verified for yr20, yr21, yr22:** 18% × annual R41 = H2 CIT, exact match.

**Conclusion:** No legal reserve anomaly. R48 "Legal reserve" = 0 throughout. No investigation required.

---

## Residual Driver Attribution — Open

The remaining Y13–30 R67 residual (~5,271 kEUR) is an **upstream taxable-income basis attribution problem**. Candidate drivers include:

- **SHL gross-accrued interest source consumption / P&L basis** — Excel P&L R27 values differ from Python fixture-extracted R27
- **Book vs tax depreciation basis** — Excel uses Dep R30 directly, Python uses 98% of book dep
- **R34 fiscal reintegration propagation/sign convention** — Python has 0 for years 13-30, may differ
- **Loss engine semantics and R37 trigger/window behavior** — Excel R37 allocation occurs once at P24-P25, Python uses Croatia 5-year rolling
- **Loss usage timing around P24–P25 transition** — Excel R36/R37/R38 chain vs Python loss engine behavior

**No single driver has been confirmed as dominant.** Per-period attribution table is required before any bridge implementation.

---

## Recommended Next Branch

| Branch | Goal |
|--------|------|
| `phase6-y13-30-residual-attribution-per-driver` | Diagnostic-only per-period attribution of the ~5,271 kEUR Y13–30 residual into real drivers before any implementation bridge |

**Removed from immediate next branches:**
- `phase6-loss-carryforward-source-bridge` (reframed as contingent on attribution result)
- `phase6-legal-reserve-source-bridge` (effective rate anomaly is resolved — no anomaly exists)
- `phase6-formula-inspection-r41-r43` (effective rate verification confirms 18% × annual R41, no formula issue)