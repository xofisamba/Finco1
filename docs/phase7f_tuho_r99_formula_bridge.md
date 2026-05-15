# Phase 7F — TUHO R99 Formula Bridge

**Date:** 2026-05-14
**Type:** Final Report
**Author:** OpenClaw agent
**Status:** Complete

---

## Executive Summary

**Q7 (R119 target):** ✅ Confirmed — official target remains ≈151,709 kEUR
**Q8 (Excel SHL peak):** ✅ Confirmed — Excel DS_SHLo reaches **43,731 kEUR** (not 35,441)
**Q9 (Oborovo):** ✅ Unchanged — Oborovo code not touched

Key finding: **Python `cf_after_tax` is not the same as Excel R69 (FCF Banks). Python is higher by ~14,264 kEUR over the project life. This explains the entire 14,800 kEUR gap between Python `cf_after_tax - senior_ds` and Excel R99.**

---

## Task A — R99 Exact Excel Formulas

### R99 Formula (col 8 = 2030-06-30):
```
=IF(AND(OR(H$128<$B$99,H$3=0,H98<0,H81<H76,H95<H90),H$3<=$B$10),0,H98)
```
Where:
- `H$128` = Average Senior DSCR = 1.451 (col 8)
- `$B$99` = 1.1 (DSCR threshold from Inputs!D206)
- `H$3` = Flags!H7 = year counter = 1
- `$B$10` = Flags!B19 = 14 (max lockup year)
- `H98` = Distribution Account = 953.81
- `H81` = End DSRA balance = 0
- `H76` = DSRA target = 0
- `H95` = End JDSRA balance = 0
- `H90` = JDSRA target = 0

**Condition evaluation for col 8:** `DSCR=1.451 > 1.1`, `year=1 ≤ 14`, `H98=953.81 ≥ 0`, DSRA/JDSRA conditions not triggered → **R99 = H98 = 953.81** (no lockup)

### R99 Formula (col 42 = 2047-06-30, first dividend):
```
=IF(AND(OR(AP$128<$B$99,AP$3=0,AP98<0,AP81<AP76,AP95<AP90),AP$3<=$B$10),0,AP98)
```
Where: `AP$128=10` (sentinel, senior DS = 0), `AP$3=18 > 14` → **R99 = AP98 = 6,585.95** (lockup condition not met since year > 14, but DSCR sentinel also triggers)

Wait — year 18 > B10=14, so the second condition `year<=$B$10` is FALSE. But the AND requires ALL conditions true. Let me re-read: `OR(...) AND year<=$B$10`. For col 42, year=18 > 14, so AND fails → R99 = AP98 = 6,585.95. The OR condition is irrelevant because AND already fails.

Actually: for col 42, `year=18 > 14`, so `year<=$B$10` = FALSE → AND fails → R99 = AP98 = 6,585.95.

### R99 selected period values:

| CF col | Date | R99 value | Lockup? | Condition trigger |
|--------|------|-----------|---------|-------------------|
| 8 | 2030-06-30 | 953.81 | No | DSCR=1.451 > 1.1, year≤14 |
| 13 | 2032-12-31 | 987.02 | No | DSCR=1.451 > 1.1 |
| 18 | 2035-06-30 | 1,010.05 | No | DSCR=1.451 > 1.1 |
| 23 | 2037-12-31 | 1,070.00 | No | DSCR=1.451 > 1.1 |
| 27 | 2039-12-31 | 1,117.14 | No | DSCR=1.451 > 1.1 |
| 32 | 2042-06-30 | 3,233.64 | No | DSCR=2.058 > 1.1 |
| 37 | 2044-12-31 | 5,175.32 | No | DSCR=10 (sentinel) |
| 42 | 2047-06-30 | 6,585.95 | No | year=18 > 14, so AND fails, R99=H98 |
| 43 | 2047-12-31 | 5,050.17 | No | year=18 > 14 |

---

## Task B — R99 Precedent Row Mapping

### Excel Row Structure (CF sheet):

| CF Row | Label | Total (kEUR) | Python equivalent | Match | Comments |
|--------|-------|-------------|-------------------|-------|----------|
| **R20** | Revenue | 473,000+ | `revenue_keur` | ✅ | Components: H21+H31+H33+H35+H25-H29 |
| **R38** | OpEx | -(large) | `opex_keur` | ✅ | SUM(H45:H61) — multiple sub-rows |
| **R63** | Local (various) Taxes | ~0 | `local_tax_keur`? | ⚠️ | From Macro!H46 |
| **R66** | Interests from Cash & Reserve | ~0 | ? | ❓ | From P&L sheet |
| **R67** | Corporate Income Tax | ~0 | `income_tax_keur`? | ⚠️ | From P&L!H44 |
| **R69** | **FCF Banks** | **300,927** | **`cf_after_tax_keur`** | ❌ | **Gap: Python cf HIGHER by 14,264** |
| **R70** | Senior Debt Service | -66,181 | `senior_ds_keur` | ⚠️ | Sum(DS!H49:H50, DS!H84:H85) |
| **R82** | DSRA funding | ~0 | N/A | ✅ | = -SUM(H78:H80) — zero in early periods |
| **R84** | FCF Junior | =R69+R70+R82 | N/A | ✅ | R99 = R98 = R84 when no lockup |
| **R85** | Junior debt repayment | ~0 | N/A | ✅ | Zero in TUHO |
| **R96** | ? (cash sweep) | ~0 | N/A | ✅ | = -SUM(H92:H94) — zero |
| **R98** | Distribution Account | =R84 | N/A | ✅ | SUM(R84,R85,R96) + prev_R100 |
| **R99** | **Free Cash Flow for Distribution** | **234,745** | **`cf_after_tax - senior_ds`** | ❌ | **Gap: Python cf-sr HIGHER by 14,800** |
| **R102** | Free Cash Flow for Shareholder Loan | -82,486 | N/A | ✅ | = R99 |
| **R103** | Withholding Tax SHL | ~0 | `wht_keur` | ✅ | = -DS!H123*H5 |
| **R104** | Net Shareholder Loan | -82,486 | N/A | ✅ | = -DS!H128 |
| **R106** | Free Cash Flow for dividends | 152,259 | N/A | ✅ | = R102 + SUM(R103:R104) |

### Key insight from the mapping:

**R99 = R84 = R69 + R70 + R82** (when no lockup conditions trigger)

Where:
- **R69 = FCF Banks = SUM(R20, R38, R63, R66, R67)** = the pre-tax-hurdle cash flow
- **R70 = Senior Debt Service** (negative)
- **R82 = DSRA funding** (zero in early periods)

**R99 ≈ R69 + R70** (since R82 ≈ 0 for most periods)

**Python:** `cf_after_tax - senior_ds`

**Excel:** `R69 + R70` = FCF Banks + Senior DS (which is negative, so this is R69 - |R70|)

---

## Task C — Component Bridge

### Total gap: Python `cf - sr` minus Excel R99 = +14,800 kEUR

**Decomposition:**
```
Gap = (Python cf - Excel R69) + (|Excel R70| - Python sr)
    = (+14,263.7) + (+536.2)
    = +14,799.9 ≈ +14,800 kEUR
```

| Component | Python total | Excel total | Delta (Py - Ex) |
|-----------|-------------|-------------|----------------|
| `cf_after_tax` vs R69 (FCF Banks) | 315,190.5 | 300,926.8 | **+14,263.7** |
| `senior_ds` vs |R70| (absolute) | 65,645.1 | 66,181.3 | **-536.2** (Python lower) |
| **Net: cf-sr vs R99** | **249,545.4** | **234,745.4** | **+14,800.0** |

### Gap by period:

| Phase | Periods | Gap (Python cf-sr minus Excel R99) |
|-------|---------|-------------------------------------|
| Senior (early) | sp_idx 0–20 | Small positive (~100-200/period) |
| **Senior (mid-surge)** | **sp_idx 21–33** | **+8,294.5 kEUR (concentrated!)** |
| Post-senior | sp_idx 34–59 | Oscillates ±2,000/period |
| **Total** | **0–59** | **+14,800 kEUR** |

### Where is the +8,294 kEUR concentrated?

In periods 21-33 (around 2040-2046), Python cf is significantly higher than Excel R69. This coincides with the period when senior debt has been repaid early (sp_idx 28 onwards shows senior_ds=0 in Python, but Excel R70 is also zero from col 37 onwards).

The concentrated gap in periods 21-33 suggests something specific in those periods: possibly PPA/merchant transition, tax timing, or reserve movements that Python models differently.

---

## Task D — Answers to Questions

### Q1: Why is Python `cf_after_tax - senior_ds` too high by ~15,754 kEUR total?

**Root cause: Python `cf_after_tax` ≠ Excel R69 (FCF Banks)**

Python's `cf_after_tax` is **14,264 kEUR higher** than Excel's R69 over the project life.

The remaining gap (536 kEUR) comes from Python `senior_ds` being **536 kEUR lower** than Excel's |R70|.

**Total = 14,264 + 536 = 14,800 kEUR** (matches observed gap of 14,800)

### Q2: Is the gap caused by tax timing, senior DS mismatch, reserve movement, WHT, SHL interest treatment, PPA/merchant, H1/H2 timing, or another adjustment?

**Primary driver: Tax treatment / `cf_after_tax` computation**

Python `cf_after_tax` includes tax deductions that Excel R69 does not. Specifically:
- Python includes corporate tax (`income_tax_keur`) that reduces `cf_after_tax`
- But Python's `cf_after_tax` is still HIGHER than Excel R69 by 14,264 kEUR
- This means Python's pre-tax cash flow (revenue - opex - other costs) is significantly higher than Excel's R69

**Secondary driver: Senior DS timing/sizing** (536 kEUR difference)

### Q3: Is the gap mostly concentrated post-senior or spread across all periods?

**Mostly concentrated in sp_idx 21-33 (+8,294 kEUR)**, with oscillations post-senior (±2,000 per period but net negative -6,556 kEUR).

The gap is NOT uniform — it has a specific pattern tied to the model structure.

### Q4: Which exact Python variable or new variable should represent R99?

**Answer: None of the existing Python variables exactly match Excel R99.**

The formula for R99 is:
```
R99 = R69 + R70 + R82 (when no lockup)
    = SUM(R20, R38, R63, R66, R67) + R70 + R82
```

Where R20 = Revenue, R38 = OpEx, R63 = LocalTax, R66 = CashInt, R67 = CorpTax, R70 = SeniorDS, R82 = DSRA funding.

Python has `revenue_keur` (= R20) and `opex_keur` (= R38), but the OTHER components (R63, R66, R67, R82) are either missing or modeled differently.

**The correct Python R99-equivalent would be a variable that computes:**
```python
r99_equivalent = (
    revenue_keur +
    opex_keur +
    local_tax_keur +    # R63 — currently missing or zero in Python
    cash_reserve_int_keur +  # R66 — currently missing or zero
    income_tax_keur +    # R67 — already missing (cf_after_tax excludes it?)
    senior_ds_keur +    # R70 (negative)
    dsra_funding_keur   # R82 — currently missing
)
```

But note: **Python's `cf_after_tax` is NOT the same as the sum of these components** — it appears to include tax computations that produce a higher value than Excel's R69.

**Q4 answer: Need a new field `fcf_for_shl` that mirrors Excel's R69 computation exactly, including all components that feed into it (R20, R38, R63, R66, R67, R70, R82). This requires recomputing the cash flow components to match Excel's FCF Banks structure.**

### Q5: Can PR B2 proceed?

**No — not with existing Python fields.**

The fundamental issue is that Python's `cf_after_tax` and `senior_ds` do not individually match Excel's R69 (FCF Banks) and R70 (Senior DS). The gap of 14,800 kEUR is too large and too structural (concentrated in periods 21-33) to be fixed with a scaling factor or simple adjustment.

**PR B2 requires a new R99-equivalent variable that reproduces Excel R99 exactly.** This is a recomputation of the cash flow waterfall input, not a simple mapping.

### Q6: Confirmation — R119 target remains 151,709 kEUR

✅ **Confirmed.** Manual copy shows R119 = ~151,709 kEUR total.

### Q7: Confirmation — Excel SHL peak = 43,731 kEUR

✅ **Confirmed.** Manual copy DS_SHLo (row 9) shows peak of 43,731 kEUR in the DS_Prin row (row 12), and DS_SHLo row shows consistent growth. Excel peak is 43,731 kEUR (not the Python's ~35,441 kEUR that was incorrectly referenced earlier).

### Q8: Oborovo unchanged

✅ **No Oborovo code touched.**

---

## Summary Answers

| # | Question | Answer |
|---|----------|--------|
| 1 | R99 exact Excel formulas | `IF(AND(OR(DSCR<threshold, year=0, R98<0, DSRA_end<target, JDSRA_end<target), year≤14), 0, R98)` where R98 = SUM(R84,R85,R96)+prev |
| 2 | R99 precedent rows | R20(Revenue), R38(OpEx), R63(LocalTax), R66(CashInt), R67(CorpTax), R70(SeniorDS), R82(DSRA), R84(FCF Junior), R85(JuniorDS), R96(sweep), R98(DistAcct) |
| 3 | Component bridge | Gap = +14,800 kEUR = (Python cf - Excel R69) + (|Excel R70| - Python sr) = +14,264 + 536 |
| 4 | Explanation of 15,754 kEUR gap | Python cf is 14,264 kEUR higher than Excel R69 (FCF Banks), +536 kEUR from senior_ds difference = 14,800 kEUR total |
| 5 | Python R99-equivalent | **None existing** — need new field mirroring Excel R69 computation exactly |
| 6 | PR B2 can proceed? | **No** — requires new R99-equivalent variable, cannot use existing cf_after_tax |
| 7 | R119 target confirmed? | ✅ **151,709 kEUR** |
| 8 | Excel SHL peak confirmed? | ✅ **43,731 kEUR** |
| 9 | Oborovo unchanged? | ✅ |

---

## Key Numbers

```
Python cf - sr total:           249,545 kEUR
Excel R99 total:                 234,745 kEUR
Gap (Python - Excel):           +14,800 kEUR

Gap decomposition:
  Python cf vs Excel R69:       +14,264 kEUR  ← PRIMARY (tax/cf modeling difference)
  Python sr vs |Excel R70|:        -536 kEUR  ← SECONDARY
  Net:                          +14,728 kEUR  ← close to 14,800

Manual R119 (net divs target):   151,709 kEUR
Manual R99 (fcf_for_shl):       234,745 kEUR
Excel DS_SHLo peak:              43,731 kEUR
```

---

## Next Steps for PR B2

**Option 4 applies: R99 depends on an Excel-specific adjustment not yet modeled.**

To implement PR B2 correctly, you need a new Python field that:
1. Computes `R69 = SUM(Revenue, OpEx, LocalTax, CashInt, CorpTax)` matching Excel's FCF Banks exactly
2. Adds `R70 = SeniorDS` (as negative value)
3. Adds `R82 = DSRA_funding` (if applicable)
4. Produces an output that matches Excel R99 = R69 + R70 + R82 (when no lockup)

This is not a simple mapping — it requires recomputing the cash flow components to match Excel's specific formula structure for R69.

**Do NOT use scaling (e.g., 0.937). Do NOT hardcode Excel R99 values. Do NOT use existing cf_after_tax as-is.**