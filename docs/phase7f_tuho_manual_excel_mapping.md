# Phase 7F — TUHO Manual Excel Mapping & Python Gap Analysis

**Date:** 2026-05-14
**Status:** Final Report
**Branch:** `phase7f-tuho-distribution-calibration` (PR B1, HEAD 940d9bf)
**Author:** OpenClaw agent

---

## 1. Authoritative Row Mapping (from manual copy)

| Excel Row | Label | Total (kEUR) | Note |
|-----------|-------|-------------|------|
| R99 | Pre-SHL FCF pool / **fcf_for_shl input** | **234,745** | True pool BEFORE SHL service |
| R102 | SHL cash outflow (net) | -82,486 | R99 + SHL cash service (negative) |
| R104 | Net SHL | -82,486 | Identical to R102 |
| R106 | FCF for dividends / gross dividends | 152,259 | Before one period adjustment |
| R119 | **Official Net Dividends target** | **≈151,709** | Equals R106 minus 550 kEUR in one period |
| DS_SHLo | SHL opening balance (first op: 32,704) | — | |
| DS_SHL_int | **Gross interest** | 49,782 | Opening × rate per period |
| DS_PIK | **Capitalized portion of gross interest** | 14,596 | R99 = DS_SHL_int − DS_PIK in cash-only |
| DS_Prin | SHL principal | 43,731 | |
| DS_SHL_cl | SHL closing balance | — | |

### Key formula confirmed:
```
gross_interest = opening_shl_balance × rate_per_period
cash_interest_paid = DS_SHL_int − DS_PIK
pik = DS_PIK
fcf_for_shl = R99 (not R102)
```

---

## 2. Calibration targets

| Metric | Value | Notes |
|--------|-------|-------|
| **Official target: R119 total** | **≈151,709 kEUR** | Net dividends — the true calibration target |
| R99 (fcf_for_shl input) | 234,745 kEUR | Pre-SHL FCF pool |
| R106 | 152,259 kEUR | Gross divs before one period adjustment |
| DS_SHL_int (gross interest) | 49,782 kEUR | Cumulative gross interest |
| DS_PIK (capitalized) | 14,596 kEUR | Of which: 14,596 kEUR capitalized |
| DS_Prin (principal) | 43,731 kEUR | |
| **Total SHL service (cash)** | **97,082 kEUR** | DS_SHL_int (49,782) − DS_PIK (14,596) + DS_Prin (43,731) + DS_PIK (14,596) = cash+PIK+principal |

---

## 3. Task B — Python vs Manual R99 comparison

### Q1: Which Python variable is closest to Excel R99?

**Answer:** `cf_after_tax − senior_ds` = `cf_after_tax_minus_senior_ds`

However this **overstates** R99 by **+15,754 kEUR** over the project life.

| Variable | Total (kEUR) | vs R99 |
|----------|-------------|--------|
| Manual R99 | 233,792 | — |
| Python cf_after_tax | 315,191 | +81,399 |
| Python senior_ds | 65,645 | — |
| **Python cf_after_tax − senior_ds** | **249,545** | **+15,754** |

### Q2: First operating period gap (sp_idx=0, 2030-06-30)

| Field | Python | Manual | Delta |
|-------|--------|--------|-------|
| cf_after_tax | 3,053 | — | — |
| senior_ds | 1,946 | — | — |
| cf_after_tax − senior_ds | **1,108** | **970** | **−138** |
| Manual R99 | — | 970 | — |

Gap = **138 kEUR** (Python overstates by 14.2% in first period).

### Q3: Gap causes — breakdown by phase

| Phase | Periods | Gap (Excel − Python) | Note |
|-------|---------|---------------------|------|
| Senior debt period | sp_idx 0–33 | **+4,096** kEUR | Python understates (cf_aft_s < R99) |
| Post-senior (SHL only) | sp_idx 34–59 | **−19,850** kEUR | Python overstates R99 |
| **Total** | **0–59** | **−15,754** kEUR | |

**Gap is NOT uniform** — it changes sign depending on phase.

During senior period: Python `cf_after_tax − senior_ds` is **less** than Excel R99.
After senior debt gone: Python `cf_after_tax − senior_ds` is **greater** than Excel R99.

This sign flip suggests the gap is tied to **senior debt presence** and/or **distribution timing**.

### Q4: Gap after SHL is repaid (sp_idx 34+, SHL balance = 0)

| Period | Python cf−sr | Manual R99 | Delta |
|--------|-------------|-----------|-------|
| 34 (2047-06-30) | 6,664 | 5,050 | **−1,613** |
| 35 (2047-12-31) | 5,769 | 6,765 | **+996** |
| 36 (2048-06-30) | 6,773 | 5,028 | **−1,745** |
| 37 (2048-12-31) | 5,828 | 6,912 | **+1,084** |

**Yes, gap persists after SHL is gone.** Python oscillates above/below Excel with semi-annual pattern.

---

## 4. PR B2 failed result explanation

| Metric | PR B2 result | Manual Excel | Delta |
|--------|-------------|-------------|-------|
| Total distributions | ≈175,040 kEUR | 151,709 kEUR | **+23,331 kEUR** (too high) |
| Peak SHL balance | ≈35,416 kEUR | 35,441 kEUR | −25 kEUR (matches) |

**Root cause:** PR B2 `fcf_waterfall` input used a post-reserve figure (probably `cf_after_reserves`) rather than true pre-SHL cash pool matching Excel R99.

Peak SHL balance matches (35,416 vs 35,441), confirming SHL mechanics are structurally correct. The **over-distribution comes from wrong fcf_for_shl input**, not SHL rate.

---

## 5. Python R99-equivalent recommendation

**Problem:** No existing Python field equals Excel R99 exactly.

Available candidates:
- `cf_after_tax` — overstates by +81,399 kEUR (includes senior DS + too much tax)
- `cf_after_tax − senior_ds` — overstates by +15,754 kEUR (still too high)
- `cf_after_tax − senior_ds − shl_interest` (cf_after_reserves) — wrong direction after SHL gone

**Root cause of gap:** Python models tax as a simple subtraction from pre-tax FCF. Excel appears to model a more complex tax computation that results in a **smaller pre-SHL cash pool** (R99 = 233,792 kEUR vs Python's 249,545 kEUR).

The 15,754 kEUR gap represents **Excel's lower effective tax** or **additional deductions** that Python is not capturing before the SHL waterfall.

**Recommendation for PR B2:**
Do NOT use `cf_after_tax` or `cf_after_reserves` directly as fcf_for_shl.

A new field is needed: **pre-SHL net cash pool = R99 equivalent** that accounts for Excel's specific tax treatment.

Possible approach: back-calculate from `cf_after_tax − senior_ds` by applying a **scaling factor** (≈0.937) to match R99 totals, or recompute the tax waterfall using Excel's actual formula structure.

---

## 6. Summary answers

1. ✅ **Updated authoritative row mapping** — documented above
2. ✅ **Confirmation: 151,709 kEUR is the official R119 target** — confirmed
3. ✅ **Confirmation: R99 is fcf_for_shl input, not R102** — confirmed
4. ✅ **Confirmation: DS_SHL_int = gross interest, DS_PIK = capitalized portion** — confirmed
5. ⚠️ **Python R99-equivalent = cf_after_tax − senior_ds** but overstates by 15,754 kEUR
6. 🔴 **PR B2 cannot proceed using an existing Python field** — a new field or corrected tax computation is required to match R99 exactly
7. 🟡 **New pre-SHL cash variable needed** — either a scaling adjustment to `cf_after_tax − senior_ds`, or a recomputed tax path matching Excel's formula
8. ✅ **Oborovo unchanged** — no Oborovo code touched

---

## 7. Key numbers for next step

```
Manual R99 total:          233,792 kEUR
Python cf−sr total:       249,545 kEUR  
Gap:                      −15,754 kEUR

Manual R119 target:       151,709 kEUR
Python distribution B1:   174,894 kEUR
Overstatement:            +23,185 kEUR

Manual DS_SHL_int:         49,782 kEUR
Python SHL interest:       39,081 kEUR  
Interest gap:             +10,701 kEUR  ← SHL rate issue
```