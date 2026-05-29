# Phase 23K: Oborovo SHL Opening Balance Bridge

**Type:** Diagnostic — no runtime changes

**Base SHA:** `dbfa5027634bc7ad149f23445732089fb60d26f3` (after PR #306 merge)
**Branch:** `phase23k-oborovo-shl-opening-balance-bridge`

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
- **Remaining gap: SHL opening balance ~1,074 kEUR**

---

## Manual Excel Check (from PR #304 body)

From cofi19 manual inspection of Oborovo Excel CF tab:
- **2046 dividends: blank/zero**
- **Dividends start ~2050** after SHL is cleared
- Classification: Python waterfall bug (not Excel calibration issue) — fixed in PR #304

---

## SHL Opening Balance Bridge

| Component | Python (current) | Excel (target) | Delta |
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

## Runtime Behavior on Current Main

```
Op[0]  date=2030-12-31  dist=51.73  shl_bal=14716.20  shl_svc=593.49   ← FIRST DISTRIBUTION (Python)
Op[37] date=2049-06-30  dist=2361.93 shl_bal=14716.20  shl_svc=583.81
Op[38] date=2049-12-31  dist=0.00    shl_bal=0.00       shl_svc=15309.69 ← SHL CLEARED (14,716 repaid)
Op[39] date=2050-06-30  dist=2994.41 shl_bal=0.00       shl_svc=0.00     ← LARGE DISTRIBUTION STARTS
```

**Observations:**
1. Python SHL opening balance = 14,716.2 kEUR (13,547.2 + 1,169.0)
2. SHL principal repaid in full at period 38 (2049-12-31) — all in one period
3. Distributions occur alongside SHL interest (small amounts 2030–2049)
4. Distribution spikes at period 39+ (2050+) after SHL cleared
5. Excel target SHL opening = 15,791 kEUR — gap of **1,074.8 kEUR** in the draw amount

---

## Root Cause Hypothesis

Current factory:
- `shl_amount_keur = 13,547.2` in `app/project_factories.py:create_default_oborovo()`
- This appears to be the SHL draw amount used in the waterfall engine
- The construction template uses `shl_keur=14,620.774` as the funding cap

**If the Excel SHL draw is 14,621 kEUR**, the factory understates it by:
```
14,621 - 13,547.2 = 1,073.8 kEUR
```

This single change would raise Python opening SHL from 14,716.2 to 15,785.2 kEUR (≈ 15,790 Excel target).

---

## Conclusion

| Question | Answer |
|---|---|
| Is this a factory config bug? | **Likely yes** — `shl_amount_keur = 13,547.2` appears to be ~1,074 kEUR below Excel's 14,621 kEUR draw |
| Is IDC the problem? | **No** — IDC is 1,169 kEUR in both Python and Excel |
| Is construction IDC engine needed? | **No** — narrow factory correction would fix the gap without runtime IDC engine |
| Is runtime SHL/waterfall logic correct? | **Yes** — SHL interest and repayment mechanics are working; the opening balance is what needs correction |

---

## Recommendation for Phase 23L

**Option A (narrow):** Change Oborovo factory `shl_amount_keur` from `13,547.2` to `14,621.0 kEUR`
- Minimal diff, directly addresses the identified gap
- SHL opening: 14,621 + 1,169 = 15,790 kEUR ≈ Excel 15,791 kEUR
- Requires review and approval before merge

**Option B (broader):** Oborovo construction funding / IDC extraction
- Extract actual SHL draw timing from construction schedule
- Wire into runtime waterfall SHL draw
- Deferred — not enough evidence to proceed

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