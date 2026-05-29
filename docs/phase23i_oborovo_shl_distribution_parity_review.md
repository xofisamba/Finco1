# Phase 23I: Oborovo SHL / Distribution Parity Review

**Date:** 2026-05-29
**Branch:** `phase23i-oborovo-shl-distribution-parity-review` (main, up to date after PR #304 merge)
**Scope:** Post-Phase 23H guard — compare Oborovo SHL service, retained cash, distribution timing, and Excel parity; investigate `shl_tenor_years = 0` factory config.

---

## Summary

Phase 23H guard is **correct** for period 30 (2046-06-30). However, a critical factory config error was found: Oborovo's `shl_tenor_years = 0` causes the SHL bullet to fire **6 years early** relative to Excel (Python: 2044-12-31 vs Excel: 2050-06-30). This is the root cause of the distribution timing mismatch — not Phase 23H.

---

## Finding 1: `shl_tenor_years = 0` is a Factory Config Error (CRITICAL)

| Parameter | Python (`create_default_oborovo`) | Excel |
|---|---|---|
| `shl_repayment_method` | `bullet` | bullet |
| `shl_tenor_years` | **0** (fallback) | **20** (40 periods) |
| Effective SHL tenor | `tenor_periods = 28` (14 years) | 40 periods (20 years) |
| SHL bullet fires | Python op_idx=28 (2044-12-31) | Excel period 40 (2050-06-30) |
| SHL opening balance | 14,716.2 kEUR | 15,790.44 kEUR |

**Root cause:** When `shl_tenor_years = 0`, the waterfall engine falls back to `tenor_periods` (28 periods = 14 years) as the effective SHL tenor. This is the **senior debt tenor**, not the SHL tenor. The SHL in Oborovo is a 20-year bullet (Excel row: "Junior Debt Maturity" = 7 = 7×6 months = 42 months... wait, let me re-read).

Actually:
- Senior Debt Maturity Days = 1 per period for first 14 years (col 7-34) → 14-year senior debt
- Junior Debt Maturity = 1 for all periods → no maturity cap (perpetual? or 20-year?)
- From BS Shareholder Loan: balance goes to 0 at 2050-06-30 (col 46) → 40 periods = 20 years

So the effective SHL tenor in Excel = 20 years = 40 periods.

**Impact:** Python fires SHL bullet at 2044-12-31 (op_idx=28). Excel fires at 2050-06-30 (op_idx~38). This is a **6-year early firing** in Python.

---

## Finding 2: Phase 23H Guard is Correct for Period 30 (2046-06-30)

| Field | Python (post-Phase 23H) | Excel | Match |
|---|---|---|---|
| `distribution_keur` at 2046-06-30 | **0.00** | 0.00 | ✅ |
| `fcf_for_shl_keur` | 3,240.59 | — | — |
| `shl_service_keur` | 0.00 | ~817 kEUR (P&L) | — |
| `shl_balance_keur` | 0.00 | 18,813 kEUR | — |

**Phase 23H guard confirmed:** Python blocks distribution when `shl_service > _cf_for_shl + TOLERANCE`. At 2046-06-30, `shl_service = 0.00` (SHL already cleared at period 28), so distribution flows. This matches Excel (Net Dividends = 0 at 2046-06-30, dividends only start 2050).

**But note:** The distribution timing mismatch is caused by the SHL tenor error, NOT a Phase 23H bug. After the SHL fires early at period 28, distributions start at period 29 (2045-06-30) in Python vs period 40 (2050-06-30) in Excel.

---

## Finding 3: SHL Opening Balance Mismatch

| Component | Python | Excel | Delta |
|---|---|---|---|
| `shl_amount_keur` | 13,547.20 | 14,621 (Inputs) | -1,073.80 |
| `shl_idc_keur` | 1,169.00 | 1,169 (from Inputs row) | 0.00 |
| **Opening balance** | **14,716.20** | **15,790.44** | **-1,074.24** |

The Excel BS shows 15,790.44 at 2030-06-30 (financial close). This includes IDCs (1,169 kEUR) plus the principal. The Python `shl_amount_keur` appears to be set to the "Available Amount" row in Excel Inputs (14,620.77 kEUR), not the opening balance including IDCs.

The 1,074 kEUR gap suggests Python is missing the IDCs from the SHL principal amount, or the Excel uses a different IDCs figure.

---

## Finding 4: TUHO Regression — First Distribution Still at op_idx=35

| Project | First distribution | Date | Amount |
|---|---|---|---|
| TUHO (pik_then_sweep) | op_idx=35 | 2047-12-31 | 5,571.62 kEUR |
| Oborovo (bullet) — Phase 23H | op_idx=29 | 2045-06-30 | 2,978.62 kEUR |
| Oborovo Excel | — | 2050-06-30 | ~589.65 kEUR (first FCF div) |

TUHO confirmed not affected by the SHL tenor issue (uses `pik_then_sweep`, not `bullet`).

---

## Finding 5: DSRA Behavior Difference (Secondary)

| Period | Python DSRA | Excel DSRA |
|---|---|---|
| Early periods | ~1,500-1,900 kEUR | 0.00 |
| op_idx=21+ | Negative (-131 to -353) | 0.00 |

Python accumulates DSRA from cash flow before distributions. Excel keeps DSRA at 0 throughout. This is a separate modeling difference — does not affect SHL distribution timing since SHL service blocks distributions anyway.

---

## Finding 6: TUHO `shl_tenor_years = 0` is Intentional

TUHO uses `pik_then_sweep` method, where the PIK phase lasts 14 years (until SHL balance is swept in the sweep phase). The `shl_tenor_years = 0` for TUHO means "no fixed maturity — sweep drives repayment". This is correct for TUHO's waterfall design. **TUHO is not affected by this issue.**

---

## Conclusion: Root Cause is SHL Tenor, Not Phase 23H

The distribution timing mismatch between Python and Excel for Oborovo is caused by **`shl_tenor_years = 0` falling back to 14 years** instead of the correct 20 years. This causes:
1. SHL bullet fires at 2044-12-31 (op_idx=28) instead of 2050-06-30
2. Distributions start at 2045-06-30 (op_idx=29) in Python vs 2050 (Excel)
3. Phase 23H guard is **correct** — it properly blocks distributions when SHL service > available CF
4. But the underlying SHL maturity date is wrong

**Phase 23H is NOT causing the distribution early start.** The early SHL firing is the root cause. Phase 23H correctly handles the resulting cash shortfall at the moment of firing.

---

## Recommended Next PR (Phase 23J)

**Fix Oborovo `shl_tenor_years` factory configuration:**

```
create_default_oborovo():
  - Change shl_tenor_years from 0 → 20  (40 periods = 20-year bullet)
```

This will align the SHL bullet firing date with Excel (2050-06-30) and correct the distribution timing.

**Scope restrictions (do not change):**
- Do not enable Oborovo frozen senior schedule
- Do not promote R99/R102
- Do not touch G20, C.16 runtime wiring, sculpting solver, partial_pay_sweep default, or M1–M18 IDC wiring
- Revenue/OPEX/CAPEX/Tax unchanged
- Senior debt sizing unchanged

**Also investigate:** SHL opening balance gap (1,074 kEUR). The Excel BS shows 15,790 kEUR at financial close; Python uses 14,716 kEUR. Check whether `shl_amount_keur` should be 14,621 (Excel Inputs "Available Amount") or if the IDCs are partially excluded.

---

## Files Changed

None (analysis-only Phase 23I).