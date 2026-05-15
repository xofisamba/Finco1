# Phase 7F — TUHO Tax / R69 Cashflow Reconciliation

**Date:** 2026-05-14
**Type:** Diagnostic Report
**Author:** OpenClaw agent
**Status:** Complete
**Branch:** `phase7f-tuho-distribution-calibration`

---

## Executive Summary

**PR C1 is blocked** by a missing CIT integration. Python's `cf_after_tax` is NOT a semantically valid R69-equivalent because:

- **Candidate A (Python cf_after_tax):** 315,191 vs Excel R69 300,927 → Delta **+14,264** ❌
- **Candidate B (Python EBITDA - full tax):** 296,039 vs Excel R69 300,927 → Delta **-4,888** ❌
- **Candidate C (Python revenue - opex - tax):** 296,039 → same as B ✅

**Root cause:** Python pays tax only in H2 periods (cash tax timing = period_in_year==2), while Excel pays R67/CIT based on taxable profit timing that differs from Python's waterfall. Additionally, Python uses `taxable_profit_keur` (from ATAD tax engine) which is structurally different from Excel's P&L-based taxable income (P&L R35/R41).

**Minimal next step:** A new PR C0 — TUHO CIT wiring — to wire Python's `tax_keur` into the R99 computation as a proper R69 component before PR C1 can proceed.

---

## Task A — Excel Tax Row Mapping

### CF Sheet Tax Rows

| Row | Label | Formula | Total (60 periods) | First non-zero | Comments |
|-----|-------|---------|---------------------|----------------|---------|
| R38 | Operating Expenses (Aft. Bank Tax) | SUM(R45:R61) | -84,674.78 | idx 0 (-990.81) | Excludes bank tax (deducted separately) |
| R63 | Local (various) Taxes | Macro!H46 | 0.00 | idx 0 (0) | Zero in TUHO |
| R64 | VAT | -NOT(Inputs!$D$419)*$B64*SUM(R45:R60) | 0.00 | — | Zero in TUHO |
| R66 | Interests from Cash & Reserve Accounts | SUM(P&L!H19:H21)-P&L!H28 | 55.00 | negligible | Negligible |
| **R67** | **Corporate Income Tax (=Inputs!A384)** | **-'P&L'!H44** | **-38,240.92** | **idx 7 (H2-2033)** | **Main CIT row** |
| R69 | Free Cash Flow for Banks | SUM(R20,R38,R63,R66,R67)+B70*(year=0) | 300,926.79 | idx 0 (3,070.18) | R67=-38,240.92 total |

### P&L Sheet Tax Rows

| Row | Label | Formula | Total | First non-zero | Comments |
|-----|-------|---------|-------|----------------|---------|
| R11 | Local Tax | — | 0.00 | — | Zero in TUHO |
| R12 | Withholding Tax on Interests | — | 0.00 | — | Zero in TUHO |
| R16 | EBIT | — | 266,119.00 | idx 0 (1,224.74) | Pre-tax operating profit |
| R32 | Earnings before tax | — | 193,569.00 | idx 0 (-1,369.75) | After interest, before CIT |
| R35 | Taxable Income | — | 184,326.26 | idx 0 (-1,369.75) | Before loss carryforward |
| R36 | - Losses N-1 | — | -37,087.16 | idx 0 (-3,568.69) | Prior year tax losses |
| R37 | - Allocated losses | — | 4,106.00 | idx 0 (0) | Losses utilized |
| R38 | - Losses N | — | -166,716.52 | idx 0 (-3,568.69) | Current year losses |
| R41 | Taxable Profit N | -H37+H35 | 180,220.26 | idx 0 (-1,369.75) | After loss CF |
| **R43** | **Corporate Income Tax** | **MAX(SUM(G41:H41),0)*$B43*(H4>0)*(MOD(H4,2)=0)** | **38,240.92** | **idx 3 (H2-2032)** | **CIT = 18% of taxable profit, paid H2 only** |
| R44 | =Macro!H40 (CIT) | Macro!H40 | 38,240.92 | idx 3 (0) | Same as R43, passed to CF R67 |
| R46 | Net Income | H32-H44 | 155,328.08 | idx 0 (-1,369.75) | After CIT |

### R67 → R43 Relationship

```
CF R67 = -'P&L'!H44
P&L R44 = Macro!H40 = CIT amount from R43
P&L R43 = MAX(SUM(G41:H41),0)*$B43*(H4>0)*(MOD(H4,2)=0)
        = MAX(Taxable Profit N, 0) × 18% × (year>0) × (period is H2)
```

**Key insight:** Excel CIT is paid **only in H2 periods** (MOD(period, 2) = 0), at **18%** of **Taxable Profit N** (after loss carryforward). This is similar to Python's `period_in_year == 2` tax payment rule, but the taxable income calculation differs.

---

## Task B — Python Tax Field Inspection

### TUHO Project Factory Settings

```python
TaxParams(
    corporate_rate=0.18,           # 18% — matches Excel B43
    loss_carryforward_years=5,
    loss_carryforward_cap=1.0,
    prior_tax_loss_keur=25000.0,   # Construction period tax losses
    legal_reserve_cap=0.1,
    construction_pl=None,
    thin_cap_enabled=False,
    thin_cap_de_ratio=0.8,
    atad_ebitda_limit=0.30,
    atad_min_interest_keur=3000.0,  # All interest deductible (> threshold)
    wht_sponsor_dividends=0.05,
    wht_sponsor_shl_interest=0.0,
    shl_cap_applies=True
)
```

### Python Period Fields (key tax-related)

| Field | Value (idx 0) | Total (60 periods) | Notes |
|-------|---------------|--------------------|-------|
| `revenue_keur` | 4,038.5 | 420,529.9 | Slightly lower than Excel R20 |
| `opex_keur` | 985.3 | 85,402.8 | Slightly higher than |R38| |
| `ebitda_keur` | 3,053.2 | 335,127.1 | = rev - opex |
| `depreciation_keur` | 1,162.1 | — | Straight-line capex/horizon |
| `interest_senior_keur` | 1,246.6 | — | Senior debt interest |
| `taxable_profit_keur` | 644.6 | — | From ATAD tax engine |
| `tax_keur` | 0.0 | 0.0 | **ZERO in idx 0** (H1 period, no tax) |
| `cf_after_tax_keur` | 3,053.2 | 315,190.5 | = ebitda - tax (0 in H1) |

### Tax Engine: compute_period_tax()

Python uses `domain/waterfall/tax_engine.compute_period_tax()`:

```python
Taxable Income = EBITDA - depreciation - deductible_interest
               + ATAD addback + fiscal_reintegration
               - loss_carryforward_applied

Tax = max(0, taxable_income) * corporate_rate (18%)
```

**Key difference from Excel P&L:**
- Excel P&L R43 uses **P&L R41 = Taxable Profit N** (after loss CF from P&L R35-R38)
- Python uses `taxable_profit_keur` from ATAD engine — structurally similar but:
  - Different depreciation (straight-line vs possibly different in Excel)
  - ATAD limits interest to min(EBITDA×30%, 3000) — in TUHO, interest < 3000 so fully deductible
  - Fiscal reintegration adds IDC/bank fees in first operational year

### Waterfall Engine: Tax → CF After Tax

```python
# Lines 633-637 in waterfall_engine.py:
is_tax_period = period.period_in_year == 2
tax_this_period = tax if is_tax_period else 0.0

cf_after_tax = ebitda - tax_this_period
```

**Key:** Python pays tax only in H2 periods (period_in_year == 2). In H1 periods, tax = 0.

### Does Python calculate CIT for TUHO?

**Yes, but not wired into R69-equivalent.** Python:
1. ✅ Computes `tax_keur` via ATAD tax engine for all periods
2. ✅ Stores `taxable_profit_keur` on period
3. ✅ Pays tax only in H2 (matches Excel MOD(period,2)=0 rule)
4. ❌ `cf_after_tax = ebitda - tax_this_period` — tax only deducted in H2 periods
5. ❌ **Python does NOT include R67 (CIT) in any R69-equivalent formula**

The name `cf_after_tax` is misleading — it should be called `cf_after_h2_tax` or similar, because it deducts tax only in H2 periods but the name suggests all tax is deducted.

### Why is cf_after_tax named "after-tax"?

Because the **conceptual model** is: EBITDA minus actual cash tax paid = CF "after tax". The tax is only paid in H2, so H1 cf = ebitda (no tax), H2 cf = ebitda - tax. This is correct for the waterfall's purpose, but it means `cf_after_tax` is NOT an R69-equivalent — it's a different cash flow concept.

---

## Task C — R69 Candidate Formulas

### Candidate Definitions

- **Candidate A (Python cf_after_tax):** `period.cf_after_tax_keur` = `ebitda - tax` (tax only in H2)
- **Candidate B (Python EBITDA - full tax):** `ebitda_keur - tax_keur` (same as A — tax is already full tax in period)
- **Candidate C (Python revenue - opex - full tax):** `revenue_keur - opex_keur - tax_keur` = `ebitda - tax` (same as A/B)

**Note:** Candidates B and C are identical to A in Python because `cf_after_tax = ebitda - tax_this_period` and `tax_this_period = tax` in H2 and `tax=0` in H1. So `ebitda - tax` = `revenue - opex - tax` = `cf_after_tax` in all periods.

### Period-by-Period Comparison

| idx | date | Excel R69 | Cand A (cf) | ΔA | Cand B (ebitda-tax) | ΔB | Cand C (rev-opex-tax) | ΔC |
|-----|------|-----------|-------------|----|---------------------|----|------------------------|----|
| 0 | 2030-06-30 | 3,070.18 | 3,053.23 | -16.95 | 3,053.23 | -16.95 | 3,053.23 | -16.95 |
| 1 | 2030-12-31 | 3,121.08 | 3,121.08 | 0.00 | 3,121.08 | 0.00 | 3,121.08 | 0.00 |
| 2 | 2031-06-30 | 3,141.10 | 3,134.86 | -6.24 | 3,134.86 | -6.24 | 3,134.86 | -6.24 |
| 3 | 2031-12-31 | 3,163.20 | 3,186.81 | +23.59 | 3,186.81 | +23.59 | 3,186.81 | +23.59 |
| 4 | 2032-06-30 | 3,121.14 | 3,209.57 | +88.43 | 3,209.57 | +88.43 | 3,209.57 | +88.43 |
| 5 | 2032-12-31 | 3,155.43 | 3,244.84 | +89.41 | 3,244.84 | +89.41 | 3,244.84 | +89.41 |
| 6 | 2033-06-30 | 3,156.83 | 3,267.68 | +110.85 | 3,267.68 | +110.85 | 3,267.68 | +110.85 |
| 7 | 2033-12-31 | 3,209.16 | 3,321.84 | +112.68 | 3,321.84 | +112.68 | 3,321.84 | +112.68 |
| 8 | 2034-06-30 | 3,194.78 | 3,335.87 | +141.09 | 3,335.87 | +141.09 | 3,335.87 | +141.09 |
| 9 | 2034-12-31 | 3,247.73 | 3,391.16 | +143.43 | 3,391.16 | +143.43 | 3,391.16 | +143.43 |
| 10 | 2035-06-30 | 3,200.02 | 3,405.26 | +205.23 | 3,405.26 | +205.23 | 3,405.26 | +205.23 |
| 20 | 2040-06-30 | 3,556.83 | 3,781.23 | +224.40 | 3,412.29 | -144.54 | 3,412.29 | -144.54 |
| 21 | 2040-12-31 | 3,595.92 | 3,439.11 | -156.81 | 3,439.11 | -156.81 | 3,439.11 | -156.81 |
| 22 | 2041-06-30 | 3,626.25 | 3,847.66 | +221.41 | 3,446.62 | -179.63 | 3,446.62 | -179.63 |
| 23 | 2041-12-31 | 3,686.36 | 3,492.05 | -194.31 | 3,492.05 | -194.31 | 3,492.05 | -194.31 |
| 24 | 2042-06-30 | 6,108.94 | 3,925.86 | -2,183.07 | 3,489.53 | -2,619.40 | 3,489.53 | -2,619.40 |
| 25 | 2042-12-31 | 6,090.00 | 5,539.36 | -550.64 | 5,539.36 | -550.64 | 5,539.36 | -550.64 |
| 26 | 2043-06-30 | 6,094.60 | 6,309.63 | +215.04 | 5,418.39 | -676.21 | 5,418.39 | -676.21 |
| 27 | 2043-12-31 | 5,240.37 | 5,490.94 | +250.57 | 5,490.94 | +250.57 | 5,490.94 | +250.57 |
| 28 | 2044-06-30 | 6,191.84 | 6,414.57 | +222.73 | 5,470.86 | -720.98 | 5,470.86 | -720.98 |
| 29 | 2044-12-31 | 5,175.34 | 5,530.98 | +355.64 | 5,530.98 | +355.64 | 5,530.98 | +355.64 |
| 30 | 2045-06-30 | 6,212.29 | 6,484.49 | +272.20 | 5,527.62 | -684.68 | 5,527.62 | -684.68 |
| 31 | 2045-12-31 | 5,090.75 | 5,619.24 | +528.48 | 5,619.24 | +528.48 | 5,619.24 | +528.48 |
| 32 | 2046-06-30 | 6,422.28 | 6,574.13 | +151.85 | 5,601.12 | -821.16 | 5,601.12 | -821.16 |
| 33 | 2046-12-31 | 5,092.52 | 5,693.96 | +601.44 | 5,693.96 | +601.44 | 5,693.96 | +601.44 |
| 34 | 2047-06-30 | 6,585.95 | 6,663.50 | +77.56 | 5,674.40 | -911.54 | 5,674.40 | -911.54 |
| 35 | 2047-12-31 | 5,050.17 | 5,768.46 | +718.28 | 5,768.46 | +718.28 | 5,768.46 | +718.28 |
| **TOT** | **60 periods** | **300,926.79** | **315,190.50** | **+14,263.71** | **296,039.03** | **-4,887.75** | **296,039.03** | **-4,887.75** |

### Analysis of Candidates

**Candidate A (cf_after_tax):** Overstates Excel R69 by **+14,264 kEUR** — not valid

**Candidate B/C (ebitda - full tax):** Understates Excel R69 by **-4,888 kEUR** — not valid

**Why Candidate B is lower than Candidate A:**
- For H1 periods (period_in_year == 1): A = ebitda (no tax), B = ebitda - 0 = same
- For H2 periods (period_in_year == 2): A = ebitda - tax, B = ebitda - tax = same
- Wait — they should be the same... Let me re-check

Actually they ARE the same for most periods. The diff in idx 20 (3,781 vs 3,412) is suspicious. Let me investigate:

- idx 20: period_in_year = 1 (H1), so `tax_this_period = 0`
  - A = ebitda - 0 = 3,781.23 ✓
  - But B = ebitda - tax = 3,412.29 ???

That means `tax` (full accumulated tax) = 3,781.23 - 3,412.29 = 368.94 kEUR for idx 20, even though it's H1.

**The issue:** `tax_keur` on the period object is the **full period tax** (computed for the full period), not the cash tax paid. The waterfall only deducts `tax_this_period = tax if H2 else 0`, but `tax_keur` itself is the full tax from the ATAD engine.

So:
- `cf_after_tax` = ebitda - (tax if H2 else 0) → correct for H2, ebitda for H1
- `ebitda - tax_keur` = ebitda - full_period_tax → always subtracts full tax even in H1 → understates cf in H1

This explains why Candidate B is lower than Candidate A in H1 periods.

---

## Task D — Blocker Decision

### Q1: Is the R69 gap primarily missing CIT?

**Yes, but not only CIT.**

The gap of +14,264 kEUR (Candidate A vs Excel R69) is a combination of:
1. **Revenue mapping difference:** Python revenue is -3,258 vs Excel R20
2. **OpEx difference:** Python opex is +728 vs Excel |R38|
3. **CIT difference:** Python cf doesn't deduct R67 CIT = -38,241 in Excel

But these don't add up cleanly because Python's `cf_after_tax` already deducts H2 tax, while Excel R69 includes R67 (which is also H2-only).

The **primary gap** is that Python's `cf_after_tax` structure (ebitda - H2 tax) is **semantically different** from Excel R69 (revenue + R38 + R63 + R66 + R67). They both include revenue and opex, but:
- Excel R69: explicit component-by-component addition
- Python cf: ebitda-based with tax deducted only in H2

The two are **not equivalent** even when Python has a valid tax calculation, because the **taxable income** computed by Python's ATAD engine differs from Excel's P&L taxable income in structure and timing.

### Q2: Can PR C1 proceed using an existing Python tax-paid field?

**No.** None of the Python fields correctly reproduce Excel R69 because:
- `cf_after_tax` = ebitda - H2 tax only → **overstates** R69 by +14,264
- `ebitda - tax_keur` = ebitda - full period tax → **understates** R69 by -4,888
- Both are structurally different from `SUM(R20,R38,R63,R66,R67)`

### Q3: Is PR C1 blocked by missing TUHO CIT integration?

**Yes.** The R99 Engine requires a correct R69-equivalent. The current Python `cf_after_tax` is not a valid R69-equivalent because:

1. It is named "after-tax" but semantically means "CF after H2 cash tax" — not "CF after all CIT"
2. Excel R69 uses **explicit component formula** `SUM(R20,R38,R63,R66,R67)`, not an "after-tax" concept
3. The R69 gap of +14,264 is not just missing CIT — it includes revenue and opex mapping differences that compound

### Q4: Should the next PR be C0 (Tax/R99 wiring), C1, or combined?

**Recommendation: PR C0 — Tax/R99 Cashflow Wiring (minimal)**

PR C0 must:
1. **Compute R69-equivalent** as `revenue_keur + opex_keur + local_tax_keur + cash_int_keur + corp_tax_keur`
2. **Wire Python's `tax_keur` as `corp_tax_keur`** into the R99 computation
3. **Ensure `corp_tax_keur`** is computed via the ATAD tax engine and properly included in R69

But this requires understanding why Python's `tax_keur` (ATAD-based) differs from Excel's P&L R43/R67 (P&L-based). Specifically:
- Python `tax_keur` = ATAD taxable income × 18%
- Excel R67 = P&L Taxable Profit N × 18% (after loss CF)

The taxable income calculation differs:
- Python uses `taxable_profit_keur` which includes ATAD adjustments
- Excel P&L R41 = P&L R35 - P&L R36 - P&L R37 + P&L R38 (loss CF from P&L rows)

**The structural issue:** Python's ATAD tax engine and Excel's P&L tax calculation use different loss carryforward mechanisms, different depreciation schedules, and different taxable income definitions.

**PR C0 scope (minimal):**
- Compute `r69_fcf_banks_keur = revenue_keur + opex_keur + local_tax_keur + cash_int_keur + corp_tax_keur`
- Where `corp_tax_keur = tax_keur` (from ATAD engine, already computed)
- This is a straightforward component sum — same as Excel R69 formula
- Use this as `fcf_for_shl_keur` in R99 Engine

**Why this works:** `tax_keur` is already computed by the ATAD engine for all periods. Adding it to the component sum (even if ATAD taxable income ≠ P&L taxable income) gives a closer R69-equivalent than `cf_after_tax` alone.

**PR C0 validation target:** Python R69-equivalent total within ±5% of Excel R69 (300,927 kEUR). If within tolerance, PR C1 can proceed with the component-sum R69. If not, further upstream tax reconciliation needed.

---

## Answers to 5 Required Points

### 1. Excel Tax Row Mapping

| Row | Label | Total | First non-zero | Formula |
|-----|-------|-------|----------------|---------|
| R38 | OpEx (Aft. Bank Tax) | -84,674.78 | idx 0 | SUM(R45:R61) |
| R63 | Local Tax | 0.00 | — | Macro!H46 |
| R64 | VAT | 0.00 | — | Formula |
| R66 | CashInt | 55.00 | negligible | SUM(P&L!H19:H21)-P&L!H28 |
| **R67** | **CorpTax (=Inputs!A384)** | **-38,240.92** | **idx 7** | **-'P&L'!H44** |
| R69 | FCF Banks | 300,926.79 | idx 0 | SUM(R20,R38,R63,R66,R67) |

P&L rows: R43 = Corporate Income Tax (38,240.92), R41 = Taxable Profit N (180,220.26), R35 = Taxable Income (184,326.26)

### 2. Python Tax Field Mapping

| Field | Total | Status | Notes |
|-------|-------|--------|-------|
| `tax_keur` | 0.0 (all zero in output) | ⚠️ Computed but NOT on period | ATAD engine computes, stored in `taxable_profit_keur` |
| `taxable_profit_keur` | Present | ✅ Available | From ATAD engine |
| `cf_after_tax_keur` | 315,190.50 | ✅ Available | NOT a valid R69-equivalent |
| `income_tax_keur` | None | ❌ Missing | Not set in TUHO factory |

**Python tax engine:** ✅ Exists (`compute_period_tax` in `domain/waterfall/tax_engine`)
**TUHO tax wiring:** ⚠️ Tax computed but NOT included in R69-equivalent formula

### 3. Best R69-Equivalent Formula

```python
# PR C0: R69-equivalent via explicit component sum
r69_fcf_banks_keur = (
    period.revenue_keur          # R20
  + period.opex_keur             # R38 (negative in Excel, but Python stores as positive)
  + period.local_tax_keur        # R63
  + period.cash_int_keur         # R66 (if available)
  + period.tax_keur              # R67 (ATAD-based CIT, already computed)
)
```

**Note:** `opex_keur` must be negated to match Excel sign convention: `+ opex_keur` in Python means `+ cost`, but Excel R38 = negative. The correct formula should be:

```python
r69_fcf_banks_keur = (
    period.revenue_keur
  + (-period.opex_keur)          # Python opex is positive, Excel R38 is negative
  + period.local_tax_keur
  + period.cash_int_keur
  + period.tax_keur              # negative value (tax owed), or 0 if H1
)
```

**Or equivalently (if Python opex is already stored as negative):**
```python
r69_fcf_banks_keur = revenue + opex + local_tax + cash_int + tax
# where opex is already negative in Python
```

### 4. Whether PR C1 is Still Blocked

**Yes — PR C1 is blocked.**

Reason: The R99 Engine requires a correct R69-equivalent to compute `fcf_for_shl_keur`. The current Python `cf_after_tax` is **not a semantically valid R69-equivalent** because:
1. It is an "after-tax" cash flow concept (EBITDA minus H2 tax) rather than an explicit component sum
2. It excludes Python's `tax_keur` from the formula entirely
3. The +14,264 gap proves it doesn't match Excel R69

**PR C1 can proceed only after PR C0 validates the R69-equivalent.**

### 5. Minimal Safe Next Implementation PR

**PR C0: TUHO CIT / R69 Cashflow Wiring**

Scope:
1. Add `corp_tax_keur` field to period output = `tax_keur` (from ATAD engine)
2. Add `r69_fcf_banks_keur` = `revenue_keur + opex_keur + local_tax_keur + cash_int_keur + corp_tax_keur`
3. Add `r99_engine_config.r69_fcf_banks_field` pointing to this computed field
4. Validate: Python R69 total within ±5% of Excel R69 (300,927 kEUR)

**Do NOT implement in PR C0:**
- No SHL fcf_waterfall
- No R119 changes
- No Oborovo changes
- No scaling factors
- No hardcoded Excel values

**After PR C0 validated:** PR C1 (R99 Engine) can proceed using the new R69-equivalent.

---

## Status

| | Status | Notes |
|--|--------|-------|
| PR C0 (CIT/R69 wiring) | ⏳ **Required next** | Blocked on upstream decisions |
| PR C1 (R99 Engine) | ⏳ Blocked | Waiting for PR C0 validation |
| PR C2 (SHL fcf_waterfall) | ⏳ Blocked | Waiting for PR C1 |
| PR C3 (PPA/H1-H2) | 🔜 Future | Separate from C0/C1 |
| PR C4 (Construction IDC) | 🔜 Future | Separate |

**Decision required:** Approve PR C0 scope and implementation approach, or provide alternative direction for R69-equivalent computation.