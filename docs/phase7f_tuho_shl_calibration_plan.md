# TUHO SHL Calibration — Implementation Plan

**Date:** 2026-05-13
**Status:** DRAFT — For Review Before Implementation
**Branch:** `phase7f-tuho-distribution-calibration`

---

## Background

Python SHL balance at P28 = 25,768 kEUR vs Excel = 38,302 kEUR.
Python starts distributions at P33 vs Excel at P36.
Total distribution delta: +28,861 kEUR (Python higher).

Two root causes identified:
1. **CF source mismatch:** Excel uses `R99` (FCF for SHL ≈ 2,396 kEUR at P28). Python uses raw `cf_after_reserves` (6,415 kEUR at P28) — a 2.7× overage.
2. **Interest rate:** Python uses flat `shl_rate × 0.5 = 3.965%`. Excel uses actual period day fraction (~5.01% for H2, ~4.93% for H1). This causes Python SHL interest to be ~23% lower → balance shrinks faster.

---

## 1. What is the correct Python equivalent of Excel R99?

**Excel R99 definition:** FCF available for Shareholder Loan service, after senior debt service and all other project-level cash requirements. It equals `CF row 69 (FCF for Banks) + row 70 (Senior DS)` — i.e., the cash left after the senior debt sweep.

**Python `cf_after_reserves`** currently equals `cf_after_tax − senior_ds − dsra_contrib`.

The gap at P28: Excel R99 = 2,396 kEUR vs Python `cf_after_reserves = 6,415 kEUR`.

**Why the gap exists:** Excel's R99 reflects the actual cash leftover after the senior debt sweep test (`DSCR sweep` logic in Excel that Python doesn't replicate identically). Python uses the raw post-tax CF; Excel uses the post-senior-sweep CF.

**Correct fix:** Compute the Excel R99 equivalent in Python before calling SHL logic. This is `cash_for_shl = max(0, cf_after_reserves − sweep_to_senior)`, where `sweep_to_senior` is whatever remains after the DSCR sweep to senior debt.

**Implementation:** Add a new field to the period object or pass as parameter: `fcf_for_shl_keur`. Compute it in `waterfall_engine.py` where the DSCR sweep logic already exists.

---

## 2. Should SHL repayment use R99-equivalent cash, not raw `cf_after_reserves`?

**Yes.** The SHL repayment should be capped at the Excel R99 equivalent. Specifically:

```
cash_for_shl = fcf_for_shl_keur   # or: min(cf_after_reserves, R99_equivalent)
principal_repayment = min(cash_for_shl − interest, balance)
```

Currently Python uses:
```
principal_repayment = min(cf_after_reserves − interest, balance)
```

This overstates available cash and causes excessive SHL principal repayment.

**Note:** When `cf_after_reserves < R99_equivalent` (e.g., low-generation periods), the actual cf_after_reserves should be the floor (you can't repay more than you have). The R99-equivalent caps the **maximum** possible repayment, but the actual repayment is capped by both the R99-equivalent AND the actual CF available.

---

## 3. Should SHL interest use actual day count / period day fraction matching Excel?

**Yes.** The interest rate should be:
```
shl_rate_per_period = shl_rate × period.day_fraction
```
Currently Python uses `shl_rate × 0.5` (hardcoded semiannual).

The period engine already provides `period.day_fraction` (e.g., 0.5014 for 183-day H2 periods, 0.4932 for 180-day H1 periods). This should be used instead of `0.5`.

**Impact:** This raises Python interest to match Excel, slowing SHL balance reduction slightly (Excel has higher interest because balance is higher, but also uses actual day fraction).

**Secondary effect:** The PIK trigger comparison `cf > balance × shl_rate` (annual rate) should also be reviewed — but for interest calculation, using `day_fraction` is the primary fix.

---

## 4. Where should the code change live?

### Option A: `waterfall_engine.py` only (compute R99-equivalent before SHL call)

**Pros:** No changes to SHL engine. Isolates Excel-compatible logic to waterfall.
**Cons:** Duplicates DSCR sweep logic that already exists in `waterfall_engine.py`.

### Option B: `waterfall_engine.py` + pass `fcf_for_shl_keur` to `compute_shl_period_v3`

**Pros:** Clean separation. `compute_shl_period_v3` stays pure.
**Cons:** Changes function signature.

### Option C: New helper method in `sponsor_project_adapter.py` that precomputes R99-equivalent

**Pros:** Adapter layer already transforms Excel → Python concepts. No core changes.
**Cons:** Adds another adapter method; SHL parameters should ideally be correct at core level.

### Recommended: **Option B** — minimal core changes with explicit parameter

**Changes:**
1. **`waterfall_engine.py`:** Compute `fcf_for_shl_keur = cash_after_senior_sweep` before SHL call. Pass as `fcf_for_shl_keur` to `compute_shl_period_v3`.
2. **`compute_shl_period_v3`:** Accept `fcf_for_shl_keur` parameter. Use it instead of `cf_available` for principal capping.
3. **`waterfall_engine.py`:** Use `period.day_fraction` for SHL interest rate instead of `0.5`.

**No changes needed to:**
- `sponsor_project_adapter.py` (unless it already passes SHL params)
- `ui_runner.py`
- `project_factories.py`

---

## 5. How to avoid breaking Oborovo and existing SHL tests

### Oborovo context

Oborovo uses `shl_repayment_method = "pik_then_sweep"` with:
- `shl_amount = 14,621 kEUR`, `shl_idc = 1,169 kEUR`, `shl_rate = 8%`, `shl_wht_rate = 0%`
- Total SHL balance = 15,790 kEUR at opening
- Already calibrated: Oborovo distributions start at P36 (matching Excel), so R99-equivalent logic should already be correct for Oborovo OR Oborovo uses a different CF profile

**Key question:** Is Oborovo's `cf_after_reserves` already close to its R99-equivalent? If yes, then the fix needs to target TUHO specifically without changing Oborovo behavior.

**Approach:**
1. Make the R99-equivalent cap **conditional** — compute it but only apply the cap if it's materially different from `cf_after_reserves` (e.g., > 5% difference), OR
2. Add a config flag `use_excel_r99_equivalent = True/False` in `FinancingParams`, defaulting to `False` for backward compatibility, set to `True` for TUHO.
3. Run existing Oborovo tests with the flag both on and off.

### SHL tests to check

```
tests/test_full_horizon_sponsor_calibration.py    # TUHO + Oborovo
tests/test_tuho_calibration_reconciliation.py    # TUHO-specific
domain/portfolio/shl/test*.py                    # SHL engine unit tests
```

### Regression guard

Add a `shl_r99_cap_flag: bool = False` to `WaterfallRunConfig`. Default `False` (current behavior). When `True`, use the R99-equivalent cap. TUHO config sets this to `True`.

---

## 6. Required Regression Tests

### New tests to add

**`tests/test_tuho_shl_calibration.py`** (new file):
- `test_tuho_shl_balance_p28_to_p36_matches_excel()` — compare Python SHL balance vs Excel DS row 126 for P28-P36, tolerance ±1%
- `test_tuho_first_distribution_period_is_p36()` — first distribution in period index 36 (Excel P36, 2047-12-31)
- `test_tuho_total_distributions_match_excel_r119()` — total Python distributions vs Excel R119 sum, tolerance ±5%
- `test_tuho_shl_interest_rate_uses_actual_day_fraction()` — verify `shl_interest / shl_balance` at P28-P35 matches `shl_rate × day_fraction` for that period ±0.01%

**`tests/test_oborovo_shl_unchanged.py`** (new or extend existing):
- `test_oborovo_distributions_unchanged_after_shl_fix()` — verify Oborovo total distributions and first distribution period unchanged after flag is introduced

### Existing tests to verify

- `test_full_horizon_sponsor_calibration.py` — run with both TUHO and Oborovo, expect all existing assertions to pass (TUHO distributions will change — update expected values)
- `test_tuho_calibration_reconciliation.py` — update expected distribution values after fix

### Manual verification checklist

- [ ] TUHO P28 SHL balance: Python ≈ 38,302 kEUR (Excel) vs current 25,768 kEUR
- [ ] TUHO P32 SHL balance: Python ≈ 20,699 kEUR (Excel) vs current 4,465 kEUR
- [ ] TUHO P36 SHL balance: Python = 0 (both)
- [ ] TUHO P36 first distribution: Python starts at P36 (Excel P36 = 2047-12-31)
- [ ] TUHO total distributions: Python ≈ 151,709 kEUR (Excel R119) vs current 180,570 kEUR
- [ ] Oborovo distributions unchanged
- [ ] Oborovo SHL balance P28-P36 unchanged

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Fixing R99-equivalent breaks Oborovo | Medium | High | Use flag `shl_r99_cap_flag`, test with/without |
| Interest day_fraction change causes IRR shift | Low | Medium | Run full TUHO/Oborovo IRR after fix, tolerance ±1pp |
| SHL balance fix doesn't fully close distribution gap | Medium | Medium | May also need to fix SHL rate or PIK trigger |
| PIK trigger still using annual rate after interest fix | Low | Low | Review `_pik_trigger` comparison separately |
| Existing tests have hardcoded TUHO distribution values | High | Medium | Update expected values in test assertions before fix |

---

## Implementation Sequence

1. **Step 1:** Add `use_excel_r99_equivalent: bool = False` to `FinancingParams` and `WaterfallRunConfig`
2. **Step 2:** In `waterfall_engine.py`, compute `fcf_for_shl_keur` before SHL call. If `use_excel_r99_equivalent=True`, cap `cf_after_reserves` at `fcf_for_shl_keur` before passing to `compute_shl_period_v3`
3. **Step 3:** Change SHL interest rate from `shl_rate × 0.5` to `shl_rate × period.day_fraction`
4. **Step 4:** Run TUHO with new flag `True` — verify SHL balance P28-P36 close to Excel
5. **Step 5:** Run Oborovo with flag `False` (default) — verify unchanged
6. **Step 6:** Update regression tests with new expected values
7. **Step 7:** Merge after all tests pass

---

## Open Questions

1. **Oborovo test:** Does Oborovo already pass with current code? If yes, the R99-equivalent cap may not be needed for Oborovo (its CF profile may naturally match R99). Confirm before applying fix broadly.

2. **SHL PIK trigger:** The `_pik_trigger = (_cf_for_shl > shl_balance × shl_rate)` uses annual rate. Should this be changed to `shl_balance × shl_rate × day_fraction` (semiannual rate) for consistency? Currently triggers sweep when CF > annual interest (which is conservative for PIK — less likely to trigger).

3. ** TUHO config:** Which factory creates TUHO with `use_excel_r99_equivalent=True`? Need to confirm in `project_factories.py` or `sponsor_project_adapter.py`.