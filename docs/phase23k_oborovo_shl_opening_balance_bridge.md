# Phase 23K: Oborovo SHL Opening Balance Bridge

**Type:** Diagnostic — no runtime changes

**Base SHA:** `dbfa5027634bc7ad149f23445732089fb60d26f3` (after PR #306 merge)
**Branch:** `phase23k-oborovo-shl-opening-balance-bridge`

---

## ⚠️ Superseded by Phase 23L

> **Phase 23K was a diagnostic PR.** Phase 23L (PR #309) implemented the recommended factory correction.
> The diagnostic gap documented here was **CLOSED by Phase 23L**.
>
> - Phase 23K diagnosed the gap (pre-23L: 14,716.2 vs Excel 15,791 kEUR)
> - Phase 23L corrected `shl_amount_keur` from `13,547.2` → `14,621.0`
> - Post-23L opening SHL = 15,790 kEUR ≈ Excel 15,791 kEUR ✓

| Phase | SHL Draw | Opening SHL | vs Excel |
|---|---|---|---|
| **Pre-23L (this doc)** | 13,547.2 kEUR | 14,716.2 kEUR | −1,074.8 kEUR |
| **Post-23L (corrected)** | 14,621.0 kEUR | 15,790.0 kEUR | −1 kEUR ≈ 0 ✓ |

---

## Context

| PR | Title | Status |
|---|---|---|
| #303 | TUHO factory frozen senior DS opt-in | Merged |
| #304 | Oborovo SHL/distribution lock-up guard (2-tier bug) | Merged |
| #306 | Oborovo shl_tenor_years 0→20 (Excel 20-year bullet alignment) | Merged |

After PR #304 + #306:
- Oborovo distribution now starts ~2050 (period 39+), matching Excel directionally
- SHL clearing: Python at period 38 (2048-12-31), Excel appears to target period 40 (2050-06-30)
- **Remaining gap: SHL opening balance ~1,074 kEUR** ← *Documented in this PR*

---

## Manual Excel Check (from PR #304 body)

From cofi19 manual inspection of Oborovo Excel CF tab:
- **2046 dividends: blank/zero**
- **Dividends start ~2050** after SHL is cleared
- Classification: Python waterfall bug (not Excel calibration issue) — fixed in PR #304

---

## SHL Opening Balance Bridge (Pre-Phase 23L — Historical)

> ⚠️ **HISTORICAL TABLE** — This documents the state *before* Phase 23L correction.
> See the "Superseded by Phase 23L" section above for the current (corrected) state.

| Component | Pre-23L Python | Excel (target) | Delta |
|---|---|---|---|
| SHL draw/principal | **13,547.2 kEUR** | **14,621 kEUR** | **−1,073.8 kEUR** |
| SHL IDC | 1,169.0 kEUR | 1,170 kEUR | −0.97 kEUR ≈ 0 |
| **Opening total** | **14,716.2 kEUR** | **15,791 kEUR** | **−1,074.8 kEUR** |

**Source of Excel target:** Oborovo construction note (from `app/project_factories.py` comment: `shl_idc_keur=1169.0  # IDC from construction — opening SHL balance = 14,621 + 1,169 = 15,790`)

The Excel target of 14,621 kEUR for SHL draw is inferred from the construction funding cap in `domain/construction/templates/oborovo.py`:
```python
shl_keur=14620.774,  # Excel construction funding cap for SHL
```

---

## Runtime Behavior on Pre-23L Main (Historical)

```
Op[0]  date=2030-12-31  dist=51.73  shl_bal=14716.20  shl_svc=593.49   ← FIRST DISTRIBUTION (Python)
Op[37] date=2049-06-30  dist=2361.93 shl_bal=14716.20  shl_svc=583.81
Op[38] date=2049-12-31  dist=0.00    shl_bal=0.00       shl_svc=15309.69 ← SHL CLEARED (14,716 repaid)
Op[39] date=2050-06-30  dist=2994.41 shl_bal=0.00       shl_svc=0.00     ← LARGE DISTRIBUTION STARTS
```

**Observations (pre-23L):**
1. Python SHL opening balance = 14,716.2 kEUR (13,547.2 + 1,169.0)
2. SHL principal repaid in full at period 38 (2049-12-31) — all in one period
3. Distributions occur alongside SHL interest (small amounts 2030–2049)
4. Distribution spikes at period 39+ (2050+) after SHL cleared
5. Excel target SHL opening = 15,791 kEUR — gap of **1,074.8 kEUR** in the draw amount

---

## Root Cause Hypothesis (Pre-23L — Historical)

Pre-23L factory:
- `shl_amount_keur = 13,547.2` in `app/project_factories.py:create_default_oborovo()`
- This appeared to be the SHL draw amount used in the waterfall engine
- The construction template uses `shl_keur=14,620.774` as the funding cap

**If the Excel SHL draw is 14,621 kEUR**, the factory understated it by:
```
14,621 - 13,547.2 = 1,073.8 kEUR
```

This single change would raise Python opening SHL from 14,716.2 to 15,785.2 kEUR (≈ 15,790 Excel target).

---

## Resolution: Phase 23L Factory Correction (PR #309)

Phase 23L implemented Option A from this document:

**Change:** `shl_amount_keur` in `app/project_factories.py:create_default_oborovo()`
```
Before (pre-23L): shl_amount_keur = 13,547.2 kEUR
After  (post-23L): shl_amount_keur = 14,621.0 kEUR
```
`shl_idc_keur` unchanged at `1,169.0 kEUR`.

**Result:** Opening SHL = 14,621.0 + 1,169.0 = **15,790.0 kEUR** ≈ Excel 15,791 kEUR ✓

---

## Conclusion (Historical — Pre-23L Resolution)

| Question | Answer (pre-23L) | Post-23L Status |
|---|---|---|
| Factory config bug? | **Yes** — `shl_amount_keur = 13,547.2` was ~1,074 kEUR below Excel's 14,621 kEUR draw | ✓ FIXED |
| IDC the problem? | **No** — IDC is 1,169 kEUR in both Python and Excel | ✓ Confirmed |
| Construction IDC engine needed? | **No** — narrow factory correction | ✓ Confirmed |
| Runtime SHL/waterfall logic correct? | **Yes** — SHL interest/repayment mechanics work; opening balance was the issue | ✓ Confirmed |

---

## Guardrails Confirmed

| Guardrail | Status |
|---|---|
| G20 BLOCKED | ✓ Untouched |
| R99/R102 NOT APPROVED | ✓ Untouched |
| Oborovo frozen schedule NOT enabled | ✓ `use_frozen_excel_senior_debt_schedule=False` |
| TUHO factory flags unchanged | ✓ |
| No Revenue/OPEX/CAPEX/Tax change | ✓ Diagnostic only |
| No SHL/distribution waterfall change | ✓ |
| `partial_pay_sweep` NOT promoted | ✓ |
| Sculpting solver NOT promoted | ✓ |
| C.16 / M1–M18 IDC NOT wired | ✓ |
| PR #299 remains draft / superseded | ✓ |