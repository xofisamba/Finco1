# Phase 7F PR C0 — Tax/R69 Wiring: Pre-Implementation Report

**Date:** 2026-05-14
**Type:** Pre-Implementation Confirmation
**Author:** OpenClaw agent
**Status:** Complete — Ready for Implementation
**Branch:** `phase7f-tuho-distribution-calibration`

---

## Pre-Implementation Confirmation

This report confirms exact code locations, sign conventions, field names, and formula before any code is written.

---

## 1. Tax Engine Location

**File:** `domain/waterfall/tax_engine.py`
**Function:** `compute_period_tax()`
**Returns:** `TaxPeriodResult` (frozen dataclass)

```python
# domain/waterfall/tax_engine.py, lines 28-111
def compute_period_tax(
    ebitda_keur: float,
    depreciation_keur: float,
    senior_interest_keur: float,
    shl_interest_keur: float,
    loss_carryforward_keur: float,
    tax_rate: float,
    fiscal_reintegration_keur: float = 0.0,
    atad_applies: bool = True,
    atad_ebitda_limit: float = 0.30,
    atad_min_threshold_keur: float = 3000.0,
    loss_carryforward_cap: float = 1.0,
) -> TaxPeriodResult:
```

**TaxPeriodResult fields:**

| Field | Type | Description |
|-------|------|-------------|
| `ebitda_keur` | float | Input EBITDA |
| `depreciation_keur` | float | Depreciation |
| `deductible_interest_keur` | float | ATAD-deductible interest |
| `disallowed_interest_keur` | float | ATAD addback |
| `fiscal_reintegration_keur` | float | Construction cost add-back (HR) |
| `taxable_income_before_losses_keur` | float | Before loss CF |
| `loss_carryforward_applied_keur` | float | Loss CF used this period |
| `loss_carryforward_remaining_keur` | float | Loss CF for next period |
| `taxable_income_keur` | float | **Final taxable income** |
| `tax_keur` | float | **Final tax = taxable_income × tax_rate** |

**Called from:** `domain/waterfall/waterfall_engine.py` lines 613-625

---

## 2. Current Period-Level Field Names

### WaterfallPeriod (domain/waterfall/waterfall_engine.py, lines 41-91)

```
Revenue section:
  generation_mwh    float
  revenue_keur      float  ← positive
  opex_keur         float  ← POSITIVE (cost stored as positive)
  ebitda_keur       float  ← = revenue - opex

Tax section (line 53-58):
  depreciation_keur        float
  interest_senior_keur    float
  interest_shl_keur       float
  taxable_profit_keur     float  ← = tax_result.taxable_income_keur (ATAD-based)
  tax_keur                float  ← = tax_result.tax_keur (POSITIVE, full period tax)

After tax (line 60):
  cf_after_tax_keur       float  ← = ebitda - tax_this_period
                                ← tax_this_period = tax if H2 else 0
```

### Existing Tax-Related Fields on Period

| Field | Sign | H1 | H2 | Notes |
|-------|------|----|----|-------|
| `tax_keur` | Positive (expense) | 0 in early yrs, then non-zero | non-zero | ATAD computed, not H2-masked |
| `taxable_profit_keur` | Positive | non-zero | non-zero | ATAD taxable income |
| `cf_after_tax_keur` | Positive | = ebitda (no tax) | = ebitda - tax | H2-masked only in cf |
| `income_tax_keur` | Not on period | — | — | Does not exist on period |

### Key Finding: `tax_keur` is NOT H2-only

The `tax_keur` field on `WaterfallPeriod` is set to `tax` (the full ATAD result, positive) for ALL periods — not just H2. The H2 mask only applies to `cf_after_tax` computation (line 637: `tax_this_period = tax if is_tax_period else 0.0`), not to `tax_keur` itself (line 834: `tax_keur=tax`).

This means:
- H1 periods after idx ~18: `tax_keur` is **positive** and non-zero
- H2 periods: `tax_keur` is **positive** and non-zero
- Total `tax_keur` = **39,088** kEUR (positive)
- Excel R67 total = **-38,241** kEUR (negative)

---

## 3. Where cf_after_tax_keur is Calculated

**File:** `domain/waterfall/waterfall_engine.py`
**Lines:** 632-637

```python
# Line 632-637
is_tax_period = period.period_in_year == 2
tax_this_period = tax if is_tax_period else 0.0

# CF after tax
cf_after_tax = ebitda - tax_this_period
```

**`tax_keur` assignment (line 834):**
```python
tax_keur=tax,  # Full ATAD tax, NOT H2-masked
```

**`cf_after_tax_keur` assignment (line 835):**
```python
cf_after_tax_keur=cf_after_tax,  # H2-masked
```

---

## 4. Tax Payment Timing: Python vs Excel

| Aspect | Python | Excel R67 (CF) | Excel P&L R43 |
|--------|--------|----------------|---------------|
| Payment frequency | Every period (when profitable) | H2 only (MOD(period,2)=0) | H2 only |
| Sign convention | Positive (expense) | Negative (cash outflow) | Positive (expense) |
| First tax period | idx 19 (H2, 2039-12-31) = 3.64 | idx 7 (H2, 2033-12-31) | idx 3 (H2, 2032-12-31) |
| Total | 39,088 | -38,241 | 38,241 |
| Tax basis | ATAD (period EBITDA - dep - interest) | P&L (annual taxable profit) | P&L (annual taxable profit) |

**Critical structural difference:**
- Python: computes ATAD taxable income **per period** (semi-annual)
- Excel: computes P&L taxable profit on an **annual** basis, then applies tax **only in H2** (when annual result is known)

Excel first pays tax in 2033 (idx 7) when first full annual profit is determined. Python first pays tax in 2039 (idx 19) due to loss carryforward from construction period and different tax basis.

---

## 5. Sign Conventions

### Current Python Fields

| Field | Sign | Example (idx 0, 2030-06-30) | Notes |
|-------|------|----------------------------|-------|
| `revenue_keur` | **Positive** | 4,038.55 | Cash in |
| `opex_keur` | **Positive** | 985.32 | Cost stored as positive |
| `ebitda_keur` | **Positive** | 3,053.23 | = rev - opex |
| `depreciation_keur` | **Positive** | 1,162.05 | Straight-line |
| `interest_senior_keur` | **Positive** | 1,246.57 | Interest expense |
| `taxable_profit_keur` | **Positive** | 644.60 | ATAD taxable income |
| `tax_keur` | **Positive** | 0.00 | ATAD tax (full period) |
| `cf_after_tax_keur` | **Positive** | 3,053.23 | = ebitda - H2 tax |

### Excel R69 Components

| Row | Sign | Description |
|-----|------|-------------|
| R20 | Positive | Revenue |
| R38 | **Negative** | OpEx (stored as negative) |
| R63 | Zero | LocalTax (0 in TUHO) |
| R66 | Zero/positive | CashInt (negligible) |
| R67 | **Negative** | CorpTax (negative = cash out) |
| R69 | Positive | = SUM(R20,R38,R63,R66,R67) |

### Sign Convention for R69 Component Sum

```python
# R69 = R20 + R38 + R63 + R66 + R67
# Python equivalent:
r69_fcf_banks_keur = (
    revenue_keur          # R20: positive
  + (-opex_keur)          # R38: Python opex is positive, so negate
  + local_tax_keur        # R63: 0 in TUHO
  + cash_int_keur         # R66: 0 in TUHO
  + corp_tax_keur         # R67: negative in H2, 0 in H1
)
```

**Corp tax sign:** Excel R67 is negative (cash outflow). Python's `tax_keur` is positive (expense). For R69 component sum:
```python
corp_tax_keur = -tax_keur if period.period_in_year == 2 else 0.0
```
This gives: H1 → 0, H2 → negative (matches Excel R67 sign convention).

---

## 6. Period Dataclass Definition

**File:** `domain/waterfall/waterfall_engine.py`
**Lines:** 41-91

```python
@dataclass
class WaterfallPeriod:
    """Single period in the waterfall."""
    period: int
    date: date
    year_index: int
    period_in_year: int  # 1=H1, 2=H2
    is_operation: bool
    # Revenue section
    generation_mwh: float
    revenue_keur: float
    opex_keur: float
    ebitda_keur: float
    # Tax section
    depreciation_keur: float
    interest_senior_keur: float
    interest_shl_keur: float
    taxable_profit_keur: float
    tax_keur: float
    # After tax
    cf_after_tax_keur: float
    # ... rest of fields
```

**New fields to add (Section A, B, C):**
```python
    # R69-equivalent (new in PR C0)
    corp_tax_keur: float = 0.0        # R67: negative in H2, 0 in H1
    local_tax_keur: float = 0.0       # R63: 0 in TUHO
    cash_int_keur: float = 0.0       # R66: 0 in TUHO
    r69_fcf_banks_keur: float = 0.0   # R69 equivalent
```

---

## 7. Excel/Export/Test Outputs Consuming Period Fields

### Consumers of `tax_keur` / `cf_after_tax_keur`

| File | Usage |
|------|-------|
| `domain/analytics/scenarios.py` | `total_tax_keur` (sum of period tax) |
| `domain/reporting/financial_statements.py` | `tax_keur` for income statement, `income_tax_keur` |
| `domain/portfolio/cash_ledger/adapters.py` | `tax_keur` → HOLDCO_TAX (negative) |
| `domain/portfolio/independent/runner.py` | `cf_after_tax_keur` for IRR |
| `domain/waterfall/waterfall_engine.py` line 948 | `total_tax_keur=sum(wp.tax_keur...)` |

### Key: Adding `r69_fcf_banks_keur` does NOT change any existing outputs

`r69_fcf_banks_keur` is an **audit/validation field only** — it does not feed into any existing calculation unless `use_distribution_account_r99_engine=True` (which is off by default, guarded by feature flag).

---

## 8. Implementation Scope (Confirmed)

### A. Add `corp_tax_keur` field

```python
@dataclass
class WaterfallPeriod:
    # ... existing fields ...
    
    # NEW: R67 equivalent (corp tax, H2 only, negative sign)
    corp_tax_keur: float = 0.0  # negative when tax paid, 0 in H1
```

**Formula (in waterfall_engine.py, line ~834):**
```python
# After tax computation (after line 629):
# tax = tax_result.tax_keur (positive)
# corp_tax_keur = negative in H2, 0 in H1
corp_tax = -tax if period.period_in_year == 2 else 0.0
```

**Note:** `period.period_in_year` comes from `period.period_in_year` (the input Period object from `_build_period_engine`).

### B. Add `local_tax_keur` and `cash_int_keur` fields

Both are **0.0 in TUHO**. They exist for completeness but have no effect on R69 for TUHO.

```python
local_tax_keur: float = 0.0   # R63: 0 in TUHO
cash_int_keur: float = 0.0    # R66: 0 in TUHO
```

### C. Add `r69_fcf_banks_keur` field

```python
r69_fcf_banks_keur: float = 0.0  # R69 equivalent = SUM(R20,R38,R63,R66,R67)
```

**Formula:**
```python
r69_fcf_banks_keur = (
    revenue_keur
  + (-opex_keur)            # Python opex is positive, Excel R38 is negative
  + local_tax_keur          # R63: 0 in TUHO
  + cash_int_keur           # R66: 0 in TUHO
  + corp_tax_keur           # R67: negative in H2, 0 in H1
)
```

### D. Do NOT change `cf_after_tax_keur` behavior

`cf_after_tax_keur` remains: `= ebitda - (tax if H2 else 0)`
No changes to existing model outputs in PR C0.

### E. Feature Flag

No flag needed for PR C0 — adding `r69_fcf_banks_keur` is an audit/validation field that does not change any downstream calculation. Existing `cf_after_tax_keur` behavior is preserved.

If later PR C1 wired `r69_fcf_banks_keur` into the distribution waterfall, it would be guarded by `use_distribution_account_r99_engine=False` (default).

---

## 9. Expected Validation Numbers

### TUHO Corp Tax vs Excel R67

| Metric | Python | Excel | Delta |
|--------|--------|-------|-------|
| Corp tax total (H2 only) | TBD after implementation | -38,241 | TBD |
| First H2 tax | TBD | idx 7 (2033-12-31) | TBD |
| Tax basis | ATAD (period) | P&L (annual) | Different |

**Expected gap:** Python `corp_tax_keur` total will NOT match Excel R67 (-38,241) due to structural timing difference (Python period-basis vs Excel annual-basis). This is a known model difference, not a bug.

### TUHO R69 vs Excel R69 (300,927 kEUR target)

Using formula `r69_fcf_banks_keur = revenue - opex + corp_tax_keur`:

| Component | Total | Notes |
|-----------|-------|-------|
| Python revenue | 420,530 | Excel R20 = 423,787 (gap = -3,258) |
| Python opex (negated) | -85,403 | Excel |R38| = 84,675 (gap = +728) |
| Corp tax (H2, negative) | TBD | Excel R67 = -38,241 |
| **R69 total** | **TBD** | **Excel R69 = 300,927** |

**Note:** Even with corp_tax added, the revenue gap of -3,258 kEUR will persist. The total R69 may not reach ±2% (±6,019) of 300,927 without addressing the revenue mapping separately.

### Improvement vs Old cf_after_tax Gap

| Metric | Value |
|--------|-------|
| Old cf_after_tax total | 315,191 |
| Excel R69 total | 300,927 |
| Old gap | **+14,264** |
| New r69_fcf_banks_keur total | TBD |
| New gap | TBD |
| Expected improvement | Partial — due to corp tax sign correction |

---

## 10. Files to Change

| File | Change |
|------|--------|
| `domain/waterfall/waterfall_engine.py` | Add 4 fields to `WaterfallPeriod` dataclass; compute `corp_tax_keur`, `r69_fcf_banks_keur` in period building loop (after line 834) |
| `domain/waterfall/cash_flow.py` | Optional: add to `CashFlow` dataclass if needed |
| Tests: new file `domain/test/test_waterfall_r69.py` | 5 tests per spec |

**No changes to:** `ui_runner.py`, `app/`, `infrastructure/`, `domain/project_factories.py`, revenue/OPEX factory, SHL mechanics, distribution waterfall.

---

## 11. Summary Confirmation

| Item | Status |
|------|--------|
| Tax engine location | ✅ `domain/waterfall/tax_engine.py` → `compute_period_tax()` |
| `tax_keur` on period | ✅ Positive, full period (not H2-masked) |
| `taxable_profit_keur` on period | ✅ ATAD taxable income |
| `cf_after_tax` computed at | ✅ `waterfall_engine.py` line 637 |
| H2-only mask applies to | ✅ `cf_after_tax` only, NOT `tax_keur` |
| Revenue sign | ✅ Positive |
| OpEx sign | ✅ **Positive** (cost), use `-opex_keur` in R69 sum |
| Tax sign | ✅ Positive on `tax_keur`; **negative** on `corp_tax_keur` (H2) |
| `corp_tax_keur` storage | ✅ Negative in H2, 0 in H1 |
| Period dataclass | ✅ `domain/waterfall/waterfall_engine.py` line 41 |
| New fields addable | ✅ No regression risk — audit fields only |
| Implementation ready | ✅ Yes, code locations confirmed |

---

## Status

**Ready for implementation.** All code locations confirmed, sign conventions verified, fields mapped.

**One known issue to document:**
- Python `tax_keur` is computed every period (ATAD period-basis), Excel R67 is paid H2-only (annual P&L basis)
- This structural timing difference means `corp_tax_keur` total will NOT exactly match Excel R67 (-38,241 kEUR)
- PR C0 exposes the fields; full R69 match requires either (a) further tax timing investigation or (b) accepting residual gap

**Next step:** Await approval to proceed with implementation of PR C0.