# Phase 23P: Oborovo Post-Lockup Parity Snapshot

**Type:** Diagnostic — no runtime changes

**Base SHA:** `72521a9183d7973615e75fee3be6abe657b1ea83` (after PR #314 merge)
**Branch:** `phase23p-oborovo-post-lockup-parity-snapshot`

---

## Phase History: 23N → 23O

| Phase | PR | Change | Status |
|---|---|---|---|
| 23N | #313 | Diagnostic — Oborovo distribution lock-up mismatch identified | Merged |
| 23O | #314 | Runtime fix — bullet SHL lock-up gate: `shl_balance > 0 → dist = 0` | Merged |

---

## Phase 23N Blocker

**Detected:** Python distributed in periods 0–39 while SHL principal of 15,790 kEUR remained outstanding. Per manual Excel CF tab: dividends zero until around 2050.

**Root cause:** Standard 2-tier waterfall allowed distributions when `shl_service <= _cf_for_shl` (current-period interest only). For bullet SHL, correct gate should be `shl_balance > 0`.

---

## Phase 23O Fix

**File:** `domain/waterfall/waterfall_engine.py` (standard 2-tier branch)

**Added:** For `shl_repayment_method == "bullet"`:
```python
elif shl_balance > TOLERANCE and shl_repayment_method == "bullet":
    # Phase 23O: block distributions while SHL principal remains outstanding
    dist = 0.0
```

**Scope:** Oborovo/bullet only. TUHO (pik_then_sweep) and other methods unaffected — own 3-tier branches.

---

## Corrected Oborovo Anchor Table

| Field | Value | Status |
|---|---|---|
| `shl_amount_keur` | **14,621.0** | ✅ Phase 23L |
| `shl_idc_keur` | **1,169.0** | ✅ Unchanged |
| **Opening SHL** | **15,790.0 kEUR** | ✅ ≈ Excel 15,791 kEUR |
| `shl_tenor_years` | **20** | ✅ Phase 23J |
| `use_frozen_excel_senior_debt_schedule` | **False** | ✅ OFF (TUHO only) |

---

## Post-Fix Period Table

| Op# | Date | SHL Balance | SHL Service | Distribution | Status |
|---|---|---|---|---|---|
| 0 | 2030-12-31 | 15,790.0 | 636.79 | **0.00** | Blocked ✓ |
| 28 | 2044-12-31 | 15,790.0 | 635.05 | **0.00** | Blocked ✓ |
| 29 | 2045-06-30 | 15,790.0 | 626.41 | **0.00** | Blocked ✓ |
| 31 | 2046-06-30 | 15,790.0 | 626.41 | **0.00** | Blocked ✓ |
| **38** | **2049-12-31** | **0.00** | **16,426.79** | **0.00** | **Guard ✓** |
| **39** | **2050-06-30** | **0.00** | **0.00** | **2,994.41** | **First valid ✓** |

**Mismatch count: 0** — all pre-2050 distributions with SHL outstanding now blocked. ✅

---

## Phase 23N Blocker: RESOLVED

`test_phase23n_blocker_remains_resolved` passes:
- Pre-2050 periods with SHL balance > 0 and distribution > 0: **0** ✅
- Phase 23N had 18+ leaking periods; all now blocked ✓

---

## Remaining Material Gaps

| Gap | Severity | Notes |
|---|---|---|
| **Oborovo frozen senior DS fixture not implemented** | **HIGH** | Deferred until after this snapshot passes |
| Senior debt amount vs Excel | **MEDIUM** | Python = 42,852 kEUR; need Excel anchor |
| DSCR trajectory vs Excel | **MEDIUM** | DSCR ~1.26 during active period |
| Distribution amounts after 2050 | **LOW** | Post-SHL distributions active; need Excel comparison |
| Revenue/OpEx calibration | **LOW** | Y1 EBITDA ~2,575 kEUR; need Excel anchors |

---

## Recommendation: Phase 23Q

**Phase 23Q: Oborovo frozen senior DS fixture extraction / parity proof**

After Phase 23P snapshot confirms lock-up parity:
1. Extract senior debt schedule from Oborovo Excel
2. Enable `use_frozen_excel_senior_debt_schedule=True` for Oborovo (fixture-backed)
3. Compare DSCR trajectory and senior debt amounts
4. Only then consider factory-level opt-in (separate PR)

**Factory opt-in remains BLOCKED until Phase 23Q fixture/extract proves correct.**

---

## Guardrails Confirmed

| Guardrail | Status |
|---|---|
| G20 BLOCKED | ✓ Untouched |
| R99/R102 NOT APPROVED | ✓ Untouched |
| Oborovo frozen schedule OFF | ✓ `use_frozen_excel_senior_debt_schedule=False` |
| TUHO flags unchanged | ✓ (PR #303 + #314) |
| PR #299 draft / superseded | ✓ |
| No Runtime logic changes | ✓ Diagnostic only |