# Phase 23H: Oborovo SHL Distribution Lock-up Shortfall Fix

**Branch:** `phase23h-oborovo-shl-distribution-lockup-fix`
**Base SHA:** `fff25b821059f15f016328336b393a15240abdf4` (PR #303 merged)
**Head SHA:** `9f6b7f60de06d12dc8ec31122c4d64bac338464b` (after push)
**PR:** DRAFT — not merged

---

## Goal

Fix Python waterfall bug where the non-sweep / 2-tier distribution branch pays equity distributions while SHL service obligations exceed available cash. The bug affects Oborovo's `bullet` SHL method where `shl_tenor_years = 0` compresses the full SHL principal + interest into one period (period 30 / 2046-06-30).

---

## Root Cause

**File:** `domain/waterfall/waterfall_engine.py`
**Branch:** the `else` block for non-sweep methods (`"bullet"`, `"cash_sweep"`, `"pik"`, `"accrued"`)

```python
# BEFORE (buggy):
else:
    dist = max(0, cf_after_reserves)  # no guard for SHL cash shortfall
    sweep_amount = 0.0
```

The `"bullet"` method's SHL block is called with `is_final_shl_period = False` in period 30 (op_period_counter=30, shl_tenor_periods=32). This means the SHL engine only pays interest (198.36 kEUR) and no principal — but then the distribution branch gives all `cf_after_reserves` (2,058.03) to equity even though 5,198.36 in SHL obligations remain outstanding.

Manual Excel check confirms this is a Python bug — Excel CF tab in 2046 shows:
- **Free Cash Flow for Shareholder Loan / Net Shareholder Loan:** populated
- **Free Cash Flow for dividends:** blank/zero
- **Dividends:** start only ~2050 after SHL is cleared

---

## Fix

```python
# AFTER (fixed):
else:
    # Guard (Phase 23H): block distribution when SHL service obligations
    # exceed available cash for the SHL step.
    #
    # shl_svc = shi + shp (interest paid + principal paid)
    # _cf_for_shl = cash available for SHL step (cf_after_tax for non-pik_then_sweep)
    #
    # If shl_svc > _cf_for_shl: cash shortfall — retain all cash, no distribution.
    TOLERANCE = 0.01
    if shl_svc > _cf_for_shl + TOLERANCE:
        dist = 0.0
    else:
        dist = max(0, cf_after_reserves)
    sweep_amount = 0.0
```

**Key design decisions:**
- Uses `shl_svc` (total SHL cash outflow = interest + principal), NOT `shl_balance`
- Uses `_cf_for_shl` (cash available for SHL), NOT senior balance
- `shl_gross_accrued_interest_keur` is NOT used as standalone blocker (it accrues every period even when cleared in same SHL service step)
- `pik_then_sweep`, `partial_pay_sweep`, `fcf_waterfall` are NOT affected (already have their own 3-tier branches with SHL guards)

---

## Before / After — Oborovo Period 30 (2046-06-30)

| Field | Before (buggy) | After (fixed) |
|---|---|---|
| `distribution_keur` | **2,058.03** ← LEAK | **0.00** ✓ |
| `shl_service_keur` | 5,198.36 | 5,198.36 |
| `shl_principal_keur` | 5,000.00 | 5,000.00 |
| `shl_interest_keur` | 198.36 | 198.36 |
| `shl_gross_accrued_interest_keur` | 198.36 | 198.36 |
| `shl_balance_keur` (closing) | 0.00 | 0.00 |
| `fcf_for_shl_keur` (`_cf_for_shl`) | 2,256.38 | 2,256.38 |
| `cf_after_reserves_keur` | 2,058.03 | 2,058.03 |
| `senior_ds_keur` | 0.00 | 0.00 |
| `senior_balance_keur` | 0.00 | 0.00 |
| `cash_balance_keur` | 15,828.47 | 17,886.49 (+2,058 retained) |
| `lockup_active` | False | False |

---

## TUHO Regression

**TUHO uses `pik_then_sweep`** — its 3-tier distribution branch is untouched. The fix only affects the `else` block for non-sweep methods (`"bullet"`, `"cash_sweep"`, `"pik"`, `"accrued"`).

| Metric | Value |
|---|---|
| TUHO first distribution | idx=35, 2047-12-31, 5,571.62 kEUR |
| TUHO distribution count | All periods where `shl_service_keur <= fcf_for_shl + TOLERANCE` |
| TUHO `shl_gross_accrued_interest` periods | Correctly NOT used as distribution blocker |
| TUHO frozen factory flags | `use_senior_debt_sizing_engine=True`, `use_frozen_excel_senior_debt_schedule=True` — unchanged |

---

## Test Results

```
tests/test_phase23h_oborovo_shl_distribution_lockup_fix.py
  test_oborovo_period30_distribution_blocked_by_shl_shortfall  PASSED
  test_oborovo_no_distribution_while_shl_shortfall               PASSED
  test_oborovo_dividends_allowed_after_shl_cleared               PASSED
  test_tuho_regression_no_false_distribution_block               PASSED
  test_factory_flags_unchanged                                    PASSED
  test_revenue_opex_unchanged                                     PASSED
```

---

## Oborovo Post-SHL Dividend Schedule (after fix)

| idx | Date | `distribution_keur` | `shl_balance_keur` | `shl_service_keur` |
|---|---|---|---|---|
| 31 | 2046-12-31 | 1,865.69 | 0.00 | 0.00 |
| 35 | 2048-12-31 | 1,888.05 | 0.00 | 0.00 |
| 38 | 2050-06-30 | 2,327.30 | 0.00 | 0.00 |
| 48 | 2055-06-30 | 2,408.51 | 0.00 | 0.00 |
| 49 | 2055-12-31 | 3,271.32 | 0.00 | 0.00 |

First distribution at idx=31 (2046-12-31), 6 months after period-30 shortfall resolution.

---

## Guardrail Table

| Guardrail | Status |
|---|---|
| G20 BLOCKED | ✓ Not touched |
| R99/R102 NOT APPROVED | ✓ Not touched |
| TUHO factory flags unchanged | ✓ `use_senior_debt_sizing_engine=True`, `use_frozen_excel_senior_debt_schedule=True` |
| Oborovo frozen schedule NOT enabled | ✓ `use_frozen_excel_senior_debt_schedule=False` |
| No Revenue/OPEX/CAPEX/Tax change | ✓ Distribution branch only |
| No senior debt sizing change | ✓ |
| `partial_pay_sweep` opt-in only | ✓ Not promoted |
| Sculpting solver NOT promoted | ✓ |
| PR #299 remains draft/not merged | ✓ Confirmed |

---

## Changed Files

| File | Change |
|---|---|
| `domain/waterfall/waterfall_engine.py` | Added cash-shortfall guard in non-sweep `else` distribution branch (8 lines) |
| `tests/test_phase23h_oborovo_shl_distribution_lockup_fix.py` | New — 6 regression tests |
| `docs/phase23h_oborovo_shl_distribution_lockup_fix.md` | New — this document |

---

## Next Steps (post-review)

1. **Phase 23G** — Oborovo frozen fixture extraction (if desired, after this fix is merged)
2. **Phase 23I** — Oborovo full SHL/distribution calibration with corrected waterfall
3. **Decision point:** If Oborovo `shl_tenor_years = 0` is a configuration error (Excel may show a longer tenor), fix the factory default; otherwise the shortfall guard is the correct behavior

---

## Classification

| | |
|---|---|
| **Type** | Python waterfall bug |
| **Affected method** | `"bullet"` (Oborovo default) |
| **Affected periods** | Period 30 (2046-06-30) only |
| **Excel calibration** | NOT an Excel issue — Excel CF tab confirms no dividends in 2046 |
| **Fix scope** | Narrow — 8 lines in `waterfall_engine.py` else-branch |