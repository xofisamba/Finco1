# Phase 7F — TUHO Tax Basis Diagnostic

**Goal:** Understand why Python tax timing/basis differs from Excel tax timing/basis.
**Status:** Diagnostic only — no implementation

---

## Task A — Excel Tax Calculation Mapping

### Key Formulas (P&L sheet)

| Row | Label | Formula | Notes |
|-----|-------|---------|-------|
| R32 | Earnings before tax | `=H16+H30` | EBIT + Financial Earnings |
| R35 | Taxable Income | `=H34+H32` | EBT + Fiscal Reintegration |
| R36 | Losses N-1 | `=SUMIF(..., "<0") + SUM($F$37:G$37)` | 5-year rolling loss CF |
| R37 | Allocated Losses | `=IF(AND(H36<=0,H32>0), MIN(ABS(H36),H32), 0)` | Offset neg losses with pos profit |
| R38 | Losses N | `=MIN(H37+H36, 0)` | New losses created |
| R41 | Taxable Profit N | `=-H37+H35` | R35 minus allocated losses |
| R43 | Corporate Income Tax | `=MAX(SUM(G41:H41),0)*$B$43*(H4>0)*(MOD(H4,2)=0)` | **Annual** CIT, H2 only |
| R54 | Fiscal Reintegration | `=MIN(MAX(H57,H58)+H59, H27)` | Non-deductible items added back |
| R56 | Thin Cap Rule | `=BS!H45` | Activates based on BS condition |
| R57 | Thin Cap EBTDA | `=IF(H56, MAX(H27-$C$57, 0), 0)` | 0 when thin cap disabled |
| R58 | Thin Cap Taxable | `=IF(H56, MAX(H27-$C$58*(H32-H30+H13), 0), 0)` | ATAD-style restriction |
| R59 | Non-deductible SHL | `=H$27*(1-$C$59/Inputs!$C$311)*$D$59` | SHL non-deductible portion |

### Key Parameters

| Parameter | Excel | Python |
|-----------|-------|--------|
| Tax rate | 18% (B43) | 0.18 |
| Loss CF years | 5 (B36) | 5 |
| ATAD ebitda limit | 30% | 0.30 |
| ATAD min threshold | D399 = 3,000 kEUR | atad_min_interest_keur = 3,000 |
| Thin cap | activates at idx 7 | atad_applies = True |

### Task A — Comparison Table

| idx | date | Excel R35 | Excel R36 | Excel R37 | Excel R38 | Excel R41 | Excel R43 | CF R67 | Python taxable_profit | Python loss_cf | Python tax_keur | delta taxable | delta tax |
|-----|------|-----------|-----------|-----------|-----------|-----------|-----------|---------|----------------------|----------------|---------------|--------------|----------|
| 0 | 2030-06-30 | -1,369.75 | -3,568.69 | 0.00 | -3,568.69 | -1,369.75 | 0.00 | 0.00 | 644.60 | 24,355.40 | 0.00 | +2,014.35 | 0.00 |
| 7 | 2033-12-31 | -1,675.88 | -6,411.15 | 0.00 | -6,411.15 | -1,675.88 | 0.00 | 0.00 | -148.09 | 18,209.55 | 0.00 | +1,527.78 | 0.00 |
| 19 | 2039-12-31 | -1,185.80 | -6,607.52 | 0.00 | -6,607.52 | -1,185.80 | 0.00 | 0.00 | 598.23 | **0.00** | **3.64** | +1,784.04 | +3.64 |
| 20 | 2040-06-30 | -1,099.50 | -6,387.63 | 0.00 | -6,387.63 | -1,099.50 | 0.00 | 0.00 | 682.88 | 0.00 | 368.94 | +1,782.37 | +368.94 |
| 24 | 2042-06-30 | 2,298.72 | -5,291.80 | 2,298.72 | -2,993.09 | 0.00 | 0.00 | 0.00 | 1,030.37 | 0.00 | 436.33 | +1,030.37 | +436.33 |
| 25 | 2042-12-31 | 2,475.00 | -1,807.29 | 1,807.29 | 0.00 | 667.72 | 120.19 | -120.19 | 3,546.27 | 0.00 | 893.35 | +2,878.55 | +773.16 |
| 26 | 2043-06-30 | 2,558.45 | 1,099.50 | 0.00 | 0.00 | 2,558.45 | 0.00 | 0.00 | 3,557.67 | 0.00 | 891.24 | +999.22 | +891.24 |
| 27 | 2043-12-31 | 2,748.42 | 2,197.20 | 0.00 | 0.00 | 2,748.42 | 955.24 | -955.24 | 3,772.51 | 0.00 | 923.27 | +1,024.08 | **-31.96** |
| 29 | 2044-12-31 | 3,122.61 | 4,106.00 | 0.00 | 0.00 | 3,122.61 | 1,084.54 | -1,084.54 | 4,149.71 | 0.00 | 954.08 | +1,027.10 | **-130.46** |
| 35 | 2047-12-31 | 4,730.10 | 4,106.00 | 0.00 | 0.00 | 4,730.10 | 1,644.93 | -1,644.93 | 5,586.07 | 0.00 | 1,005.49 | +855.98 | **-639.44** |
| 41 | 2050-12-31 | 7,153.88 | 4,106.00 | 0.00 | 0.00 | 7,153.88 | 2,554.40 | -2,554.40 | 5,864.70 | 0.00 | 1,055.65 | **-1,289.19** | **-1,498.76** |
| 59 | 2059-06-30 | 8,401.42 | 4,106.00 | 0.00 | 0.00 | 8,401.42 | 2,999.85 | -2,999.85 | 6,727.79 | 0.00 | 1,210.96 | **-1,673.63** | **-1,788.89** |

**Observations:**
- Excel first pays cash tax (CF R67) at idx 25 (2042-12-31), not idx 7 (2033-12-31)
- Python first pays tax at idx 19 (2039-12-31) — **23 years earlier** than Excel
- Loss CF depletion: Python depletes 25,000 kEUR by idx 19; Excel depletes its ~6,411 kEUR by idx 25
- Post-depletion: Python consistently shows **lower** annual tax than Excel (e.g., -1,789 kEUR gap at idx 59)

---

## Task B — Python Tax Engine Mapping

### Tax Engine Location
`domain/waterfall/tax_engine.py` — `compute_period_tax()`

### TaxParams from TUHO Factory

```python
# From create_default_tuho_wind1():
tax=TaxParams(
    corporate_rate=0.18,
    loss_carryforward_years=5,
    loss_carryforward_cap=1.0,
    prior_tax_loss_keur=25000.0,         # ← FACTORY DEFAULT (not from CapEx)
    atad_ebitda_limit=0.30,
    atad_min_interest_keur=3000.0,
)
```

### CapEx Inputs (ignored by factory)

```python
capex=CapEx(
    idc_keur=1519.56,
    bank_fees_keur=782.61,
    commitment_fees_keur=0.0,
)
# Sum of construction-period costs = 2,302.17 kEUR
# NOT used by the factory for prior_tax_loss
# Factory uses hard-coded prior_tax_loss_keur=25000 instead
```

### Taxable Income Formula

```python
# Python: EBITDA - dep - ATAD_deductible_interest + disallowed + fiscal_reintegration
taxable_before = (
    ebitda_keur
    - depreciation_keur
    - deductible_interest
    + disallowed_interest
    + fiscal_reintegration_keur
)
# ATAD: deductible = min(total_interest, max(ebitda*0.30, 3000))
```

**Excel formula (R35):**
```
Taxable Income = EBT - Fiscal Reintegration
              = (EBIT + Financial Earnings) - R54
              = R16 + R30 - R54
```
Where:
- R16 = EBIT (Revenue - OpEx - Depreciation accounting)
- R30 = Financial Earnings (interest expense + other financial items)
- R54 = Fiscal Reintegration (ATAD add-backs)

### Key Differences

| Aspect | Excel | Python |
|--------|-------|--------|
| Starting point | EBT (after interest) | EBITDA (before interest) |
| ATAD formula | R58 thin cap based on EBT | ATAD with 3,000 kEUR floor |
| Loss CF origin | Construction-period accumulated losses | Factory hard-coded 25,000 |
| Loss CF lookback | 5-year rolling SUMIF | Single opening balance |
| Thin cap activation | H2 period if BS condition met | Always ATAD applies=True |
| SHL deductibility | R59 = non-deductible portion | Deducted via ATAD (above floor) |

---

## Answers to Questions

### Q1: Why does Python first pay tax in 2039 while Excel first pays in 2033?

**Excel does NOT pay tax in 2033.** Excel first pays tax at idx 25 (2042-12-31).

Both models pay no tax in early periods because losses exceed profits. The timing difference is caused by the **opening loss carryforward**:

- **Excel:** P&L R36 at idx 0 = **-3,569 kEUR** (construction-period losses from P&L R38)
  - These losses accumulate over construction years via P&L R36 `=SUMIF(..., "<0")`
  - Excel first tax payment at idx 25 when R36 exhausted

- **Python:** `prior_tax_loss_keur = 25,000 kEUR` (factory default)
  - Python first tax payment at idx 19 when 25,000 depleted
  - 25,000 is **~7x larger** than Excel's construction losses

**Root cause: Opening loss carryforward differs** (see Task C).

### Q2: Is Python taxable profit lower because of depreciation, interest, losses, or timing?

**Losses** are the primary driver:
- Python's 25,000 kEUR vs Excel's ~3,569 kEUR at idx 0
- Python absorbs more taxable income early, delaying tax payments

**Secondary:** Different taxable income basis:
- Excel taxable income = EBT - fiscal_reintegration (negative in early periods due to interest)
- Python taxable income = ATAD-EBITDA (positive when EBITDA > dep + ATAD limit)
- This means Python shows positive taxable_profit while Excel shows negative

### Q3: Does Python have an opening tax loss carryforward that Excel does not?

**Yes, structurally.** Python has a fixed opening balance of 25,000 kEUR. Excel has a 5-year rolling loss CF computed from SUMIF of negative taxable incomes.

However, Python's opening balance (25,000) is **not derived from** the CapEx construction costs (idc=1,519 + bank_fees=783 = 2,302 kEUR). The TUHO factory uses a hard-coded value.

### Q4: Does Excel use annual taxable profit while Python uses semiannual?

**Yes, but correctly implemented:**
- Excel R43 = `MAX(SUM(G41:H41),0)*18%*(MOD(H4,2)=0)` — sum of H1+H2, paid in H2 only
- Python `tax_this_period = tax if period.period_in_year == 2 else 0` — matches semiannual timing

Both use semi-annual computation but annual cash payment in H2. This is correctly implemented in Python.

### Q5: Is ATAD causing a delay in Python tax?

**Partially, but not the primary cause.** ATAD is correctly applied:
- Python ATAD deductible interest = `min(si, max(ebitda*0.30, 3000))`
- Excel R58 thin cap = `MAX(R27 - 0.3*(R32-R30+H13), 0)` when thin cap active
- Both use 30% EBITDA limit and 3,000 kEUR floor

Excel's R58 activates at idx 7 (BS!H45 = True from period 8 onward). When active, Excel disallows more interest than ATAD would in some periods.

### Q6: Which tax parameter must be aligned before R69/R99 can be calibrated?

**The opening loss carryforward (`prior_tax_loss_keur`)** is the primary misalignment.

**Secondary:** Taxable income basis differs (EBT vs EBITDA approach). Excel R35 is consistently negative in early periods while Python taxable_profit is positive. This is an architectural difference — Python's ATAD approach is fundamentally different from Excel's EBT-based approach.

---

## Task C — Decision

### Root Cause of Python Tax Starting in 2039 vs Excel 2033

**PRIMARY:** `prior_tax_loss_keur = 25,000 kEUR` in TUHO factory is a factory-level default that **does not reflect the actual construction-period financial costs** (IDC=1,520 + bank_fees=783 = 2,302 kEUR). Excel's P&L R36 starts at -3,569 kEUR from construction; Python starts with 25,000 — **7x larger**.

**SECONDARY:** Taxable income computation differs (EBITDA-ATAD vs EBT-based). Excel R35 is negative (losses) in early periods because EBT includes all interest costs. Python taxable_profit is positive because it starts from EBITDA and limits interest deductibility via ATAD.

### Required Minimal Tax Alignment Before R99 Engine

**Minimal fix:** Set `prior_tax_loss_keur = 0` in TUHO factory, and let `waterfall_engine.py` lines 458-460 compute it from CapEx construction costs:
```python
# Instead of hard-coded 25,000:
prior_tax_loss = idc_keur + bank_fees_keur + commitment_fees_keur  # ≈ 2,302 kEUR
```
This would make Python's loss CF closer to Excel's ~3,569 kEUR initial balance.

**Note:** Even with this fix, taxable income basis still differs (EBT vs EBITDA approach), and Excel thin cap (R58) produces different disallowed interest amounts than Python's ATAD formula. Full alignment would require reconciling the taxable income formula itself (not minimal).

### Whether PR C1 Remains Blocked

**Yes, PR C1 remains blocked** — the tax cashflow (R67) must be correctly wired before R69/R99 distribution engine can be calibrated.

**PR C1 prerequisite:** Opening loss carryforward alignment (minimal fix above) OR acceptance that R69 will have structural tax differences that cannot be closed at the cashflow level.

### Whether This Belongs to Phase 6 Tax Backend or Phase 7F Calibration

**Both:**
- **Phase 6:** Fix `prior_tax_loss_keur` derivation in the TUHO factory (and possibly Oborovo factory) to use actual construction-period costs instead of hard-coded 25,000
- **Phase 7F:** Document the remaining taxable income basis difference (EBITDA-ATAD vs EBT-based) as a known limitation for R69/R99 calibration, or accept the gap

---

## Summary

| Issue | Severity | Location |
|-------|----------|----------|
| Opening loss CF = 25,000 vs Excel ~3,569 | **Critical** | TUHO factory `prior_tax_loss_keur` |
| Taxable income basis: EBITDA-ATAD vs EBT | **Known difference** | `tax_engine.py` |
| Excel thin cap (R58) vs Python ATAD | **Known difference** | `tax_engine.py` vs P&L R58 |
| SHL interest deductibility | **Minor** | Both use 3,000 floor |
| Tax cash timing (H2 only) | **Aligned** | Both correctly implement annual H2 payment |

**Recommended next step:** Fix TUHO factory `prior_tax_loss_keur` to use actual construction costs (2,302 kEUR) instead of hard-coded 25,000. This would align Python's first tax payment timing closer to Excel's.