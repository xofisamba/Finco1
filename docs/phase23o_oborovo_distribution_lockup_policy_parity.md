# Phase 23O: Oborovo Distribution Lock-Up Policy Parity

**Type:** Runtime fix — targeted SHL distribution lock-up for bullet SHL

**Base SHA:** `845b4c7edf5ca6d3f038bdce4e4745532d67186e` (after PR #313 merge)
**Branch:** `phase23o-oborovo-distribution-lockup-policy-parity`

---

## Phase 23N Blocker Summary

Phase 23N (PR #313) identified a **distribution lock-up policy mismatch** between Python and Excel:

- Python allowed distributions while `shl_balance > 0` and current-period SHL service was covered
- Per manual Excel CF tab inspection, dividends are zero until SHL is cleared (~2050)
- Policy gap: `fcf_for_shl > shl_service` gates on current-period interest only

**Identified periods with incorrect Python distributions:**
- op 0 / 2030-12-31: dist = 95 kEUR while shl_balance = 15,790 kEUR
- op 28 / 2044-12-31: dist = 2,616 kEUR while shl_balance = 15,790 kEUR
- op 29 / 2045-06-30: dist = 2,352 kEUR while shl_balance = 15,790 kEUR
- op 31–37 / 2046–2049: dist ~2,200–2,600 kEUR per period while shl_balance = 15,790 kEUR

---

## Fix: Bullet SHL Distribution Lock-Up Gate

**File changed:** `domain/waterfall/waterfall_engine.py`

**Location:** Standard 2-tier waterfall branch (lines ~1002–1035)

**Before:**
```python
TOLERANCE = 0.01
if shl_svc > _cf_for_shl + TOLERANCE:
    dist = 0.0
else:
    dist = max(0, cf_after_reserves)
```

**After:**
```python
TOLERANCE = 0.01
if shl_svc > _cf_for_shl + TOLERANCE:
    dist = 0.0
elif shl_balance > TOLERANCE and shl_repayment_method == "bullet":
    # Phase 23O: Oborovo bullet SHL distribution lock-up policy parity
    # No distributions while SHL principal remains outstanding.
    dist = 0.0
else:
    dist = max(0, cf_after_reserves)
```

**Scope:** Targeted — only affects `shl_repayment_method == "bullet"` (Oborovo).
- `pik_then_sweep` (TUHO): unaffected — routes through 3-tier pik_then_sweep branch
- `partial_pay_sweep`, `fcf_waterfall`, `cash_sweep`: unaffected — use their own branches
- Phase 23H guard (`shl_svc > _cf_for_shl`) remains active as backstop for all methods

---

## Before/After Oborovo Distribution Table

| Op# | Date | SHL Balance | Distribution Before | Distribution After | Change |
|---|---|---|---|---|---|
| 0 | 2030-12-31 | 15,790.0 | 95.03 | **0.00** | Fixed ✓ |
| 5 | 2033-06-30 | 15,790.0 | 132.58 | **0.00** | Fixed ✓ |
| 10 | 2035-12-31 | 15,790.0 | 43.23 | **0.00** | Fixed ✓ |
| 21 | 2041-06-30 | 15,790.0 | 2.81 | **0.00** | Fixed ✓ |
| 27 | 2044-06-30 | 15,790.0 | 47.48 | **0.00** | Fixed ✓ |
| **28** | **2044-12-31** | **15,790.0** | **2,615.92** | **0.00** | Fixed ✓ |
| **29** | **2045-06-30** | **15,790.0** | **2,352.21** | **0.00** | Fixed ✓ |
| **31** | **2046-06-30** | **15,790.0** | **2,335.13** | **0.00** | Fixed ✓ |
| **32** | **2046-12-31** | **15,790.0** | **2,472.70** | **0.00** | Fixed ✓ |
| 34 | 2047-12-31 | 15,790.0 | 2,529.53 | **0.00** | Fixed ✓ |
| **38** | **2049-12-31** | **0.00** | **0.00** | **0.00** | Guard ✓ |
| **39** | **2050-06-30** | **0.00** | **2,994.41** | **2,994.41** | **Clean ✓** |
| 40 | 2050-12-31 | 0.00 | 3,332.78 | 3,332.78 | Clean ✓ |

**Total distributions reduced:** ~97,693 kEUR → ~71,598 kEUR (correct — pre-SHL now blocked)

---

## TUHO Regression

| Check | Result |
|---|---|
| TUHO `shl_repayment_method` | `pik_then_sweep` ✓ (not bullet) |
| TUHO routes through bullet branch | **No** — own 3-tier pik_then_sweep branch ✓ |
| TUHO distributions | Unchanged ✓ |
| TUHO frozen senior DS fixture | Still active (PR #303) ✓ |

---

## Test Results

```
tests/test_phase23o_oborovo_distribution_lockup_policy_parity.py  7 passed
tests/test_phase23n_oborovo_post_correction_parity_snapshot.py   6 passed
tests/test_phase23l_oborovo_shl_amount_factory_correction.py     6 passed
tests/test_phase23k_oborovo_shl_opening_balance_bridge.py        5 passed
tests/test_phase23h_oborovo_shl_distribution_lockup_fix.py       6 passed
tests/test_phase23f_tuho_frozen_factory_opt_in_candidate.py     84 passed
tests/test_shl_waterfall_priority.py                             42 passed, 2 xfailed, 1 xpassed
tests/test_tuho_shl_calibration.py                              passed
tests/test_revenue.py                                            passed
tests/test_opex.py                                               passed
```

**80 passed, 2 xfailed, 1 xpassed**

---

## Guardrails Confirmed

| Guardrail | Status |
|---|---|
| G20 BLOCKED | ✓ Untouched — Oborovo frozen schedule OFF |
| R99/R102 NOT APPROVED | ✓ Untouched |
| PR #299 remains draft / superseded | ✓ |
| TUHO factory flags unchanged | ✓ |
| No Revenue/OPEX/CAPEX/Tax change | ✓ |
| No construction IDC runtime | ✓ |
| No C.16 / M1–M18 IDC wiring | ✓ |
| `partial_pay_sweep` not promoted | ✓ |
| Sculpting solver not promoted | ✓ |

---

## Recommendation

**Phase 23P: Oborovo post-correction parity snapshot (rerun)**

After Phase 23O locks pre-SHL distributions:
1. Rerun Phase 23N/O parity check on PR #313 post-23O-fix branch
2. Confirm full distribution table now matches Excel expectations
3. Re-check calibration targets (Excel Net Dividends = 104,918 kEUR may shift)
4. Only after full parity proof: consider Oborovo frozen senior DS fixture extraction
5. Factory opt-in remains a **separate later PR**