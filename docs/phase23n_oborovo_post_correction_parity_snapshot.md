# Phase 23N: Oborovo Post-Correction Parity Snapshot

**Type:** Diagnostic — no runtime changes

**Base SHA:** `5fd8b63339328fc341db4d4856d055216dfa388a` (after PR #310 merge)
**Branch:** `phase23n-oborovo-post-correction-parity-snapshot`

---

## ⚠️ Issue Corrected in this Version

The previous version (c3d8682) incorrectly described pre-2050 Oborovo distributions as "normal" or "correct behavior."

**Corrected:** Pre-2050 distributions with SHL principal outstanding are now identified as a **diagnostic blocker** — not confirmed correct. The Phase 23L correction closed the SHL draw gap, but the distribution lock-up policy remains visibly different from Excel.

This diagnostic PR remains open until Phase 23O resolves the distribution policy question.

---

## Phase History (23H–23M)

| Phase | PR | Change | Status |
|---|---|---|---|
| 23H | #304 | Oborovo SHL/distribution shortfall guard (2-tier bug fix) | Merged |
| 23J | #306 | Oborovo shl_tenor_years 0→20 (20-year bullet timing) | Merged |
| 23K | #308 | Diagnostic — SHL opening balance gap: 14,716 vs 15,791 kEUR | Merged |
| 23L | #309 | Factory correction — shl_amount_keur 13,547.2 → 14,621.0 | Merged |
| 23M | #310 | Phase 23K tests/docs updated after Phase 23L correction | Merged |

---

## Corrected Oborovo Anchor Table

| Field | Value | Status |
|---|---|---|
| `shl_amount_keur` | **14,621.0** | ✅ Corrected (Phase 23L) |
| `shl_idc_keur` | **1,169.0** | ✅ Unchanged |
| **Opening SHL** | **15,790.0 kEUR** | ✅ ≈ Excel 15,791 kEUR |
| `shl_tenor_years` | **20** | ✅ Corrected (Phase 23J) |
| `shl_rate` | 0.08 | ✅ Unchanged |
| `shl_repayment_method` | bullet | ✅ |
| `fixed_debt_keur` | 42,852.27 kEUR | ⚠️ Needs Excel comparison |
| `senior_tenor_years` | 14 | ⚠️ Needs Excel comparison |
| `use_frozen_excel_senior_debt_schedule` | False | ✅ OFF (TUHO only) |
| `use_senior_debt_sizing_engine` | False | ✅ OFF (TUHO only) |

---

## Period-Level Distribution Timing (2044–2051)

| Op# | Date | SHL Balance | SHL Service | Distribution | Guard Active? |
|---|---|---|---|---|---|
| 28 | 2044-12-31 | 15,790.0 | 635.1 | 2,615.92 | No — fcf>svc |
| 29 | 2045-06-30 | 15,790.0 | 626.4 | 2,352.21 | No — fcf>svc |
| **30** | **2045-12-31** | **0.00** | **16,416.8** | **0.00** | **YES — PR #304 guard blocks** |
| 31 | 2046-06-30 | 0.00 | 0.00 | 2,335.13 | No SHL balance |
| 32 | 2046-12-31 | 0.00 | 0.00 | 2,472.70 | No SHL balance |
| 33 | 2047-06-30 | 0.00 | 0.00 | 2,219.07 | No SHL balance |
| 38 | 2049-12-31 | 0.00 | 16,426.8 | **0.00** | YES — SHL final period (bullet) |
| 39 | 2050-06-30 | 0.00 | 0.00 | **2,994.41** | First distribution after SHL cleared ✓ |
| 40 | 2050-12-31 | 0.00 | 0.00 | 3,332.78 | |
| 41 | 2051-06-30 | 0.00 | 0.00 | 3,043.16 | |
| 42 | 2051-12-31 | 0.00 | 0.00 | 3,387.41 | |

**Note:** SHL is a 20-year bullet (shl_tenor_years=20, Periods 0-39 active). Repaid in full at period 38 (2049-12-31) with principal=15,790 + interest=636.8 = 16,426.8 kEUR. The PR #304 guard correctly blocks distribution at period 38.

---

## Senior Debt Status (Early Periods Sample)

| Op# | Date | Senior DS | Senior Balance | DSCR |
|---|---|---|---|---|
| 0 | 2030-12-31 | 2,033.33 | 42,029.51 | 1.266 |
| 5 | 2033-06-30 | 2,095.31 | 36,393.00 | 1.236 |
| 10 | 2036-06-30 | 2,189.11 | 29,789.00 | ~1.22 |
| 20 | 2041-06-30 | 2,341.22 | 16,827.00 | ~1.24 |
| 27 | 2044-12-31 | 2,450.00 | 2,450.00 | ~1.26 |
| **28** | **2045-12-31** | **0.00** | **0.00** | **inf (senior repaid)** |
| 29+ | 2046+ | 0.00 | 0.00 | inf |

**Senior debt:** 42,852 kEUR, 14-year tenor (periods 0-27), fully repaid at period 28 (2045-12-31).
DSCR ~1.26 during active period — close to target_dscr=1.15 but slightly above, suggesting sculpted DSCR may be active.

---

## Revenue / OpEx / EBITDA (First Operating Year)

| Period | Date | Revenue | OpEx | EBITDA |
|---|---|---|---|---|
| Op[0] | 2030-12-31 | ~4,050 kEUR | ~799 kEUR | ~2,575 kEUR |

**Y1 EBITDA ≈ 2,575 kEUR** — no Excel calibration target confirmed in this snapshot.

---

## Remaining Material Gaps

| Gap | Severity | Notes |
|---|---|---|
| **Oborovo distribution lock-up policy vs Excel** | **BLOCKER** | **NEW — see below** |
| **Oborovo frozen senior DS fixture not implemented** | **HIGH** | Deferred until distribution policy resolved |
| Senior debt amount vs Excel | **MEDIUM** | Python = 42,852 kEUR; need Excel anchor |
| Senior DSCR trajectory vs Excel | **MEDIUM** | DSCR ~1.26 during active period |
| Revenue/OpEx calibration vs Excel | **LOW** | Y1 EBITDA ~2,575 kEUR; need Excel anchors |
| Construction funding / IDC | **DEFERRED** | Phase 23L confirmed sufficient |


---

## ⚠️ Remaining Unresolved Issue: Oborovo Distribution Lock-Up Policy Mismatch

**Severity: BLOCKER for Phase 23O frozen senior DS fixture extraction**


**The Problem:**

Python currently allows Oborovo distributions in any operating period where:
> `fcf_for_shl_keur > shl_service_keur`

This condition is checked **per period**, based only on **current-period SHL interest** (no principal repayment for bullet SHL). As a result, Python distributes in nearly every period while SHL principal balance remains outstanding at 15,790 kEUR.

**Observed Python distributions while SHL balance is outstanding (sample):**

| Op# | Date | Distribution | SHL Balance | SHL Service | SHL Final? |
|---|---|---|---|---|---|
| 0 | 2030-12-31 | 95.03 | 15,790.0 | 636.79 | No |
| 5 | 2033-06-30 | 132.58 | 15,790.0 | 626.41 | No |
| 10 | 2035-12-31 | 43.23 | 15,790.0 | 636.79 | No |
| **28** | **2044-12-31** | **2,615.92** | **15,790.0** | **635.05** | **No** |
| **29** | **2045-06-30** | **2,352.21** | **15,790.0** | **626.41** | **No** |
| **31** | **2046-06-30** | **2,335.13** | **15,790.0** | **626.41** | **No** |
| **32** | **2046-12-31** | **2,472.70** | **15,790.0** | **636.79** | **No** |
| **33** | **2047-06-30** | **2,219.07** | **15,790.0** | **626.41** | **No** |
| 34–37 | 2047–2049 | 2,200–2,600 | 15,790.0 | ~626-636 | No |
| **38** | **2049-12-31** | **0.00** | **0.00** | **16,426.8** | **YES** |
| **39** | **2050-06-30** | **2,994.41** | **0.00** | **0.00** | No |

**Note:** All distributions above occur while SHL balance = 15,790 kEUR (principal not repaid). SHL is a 20-year bullet — principal is due at period 38.

**Excel state is different (per manual inspection of CF tab):**
- Dividends appear to be **blank/zero** until around 2050
- Distributions begin only after SHL is cleared at 2049-12-31 (period 38)
- This matches the behavior where distributions require no outstanding SHL balance (not just current-period service coverage)

**Implication:** The distribution policy gating in Python is **more permissive** than Excel:
- Python gates on: current-period SHL service covered (fcf > shl_service)
- Excel gates on: no SHL principal outstanding (SHL fully cleared)

This is NOT a bug that Phase 23H/PR #304 identified — that fix addresses the SHL final period guard. This is a **separate, earlier-stage distribution lock-up** that exists throughout the entire loan life.

**Therefore:**
- Oborovo is **NOT ready** for frozen senior DS fixture extraction in its current state
- The distribution policy must first be reconciled with Excel
- Factory opt-in for Oborovo frozen schedule remains **BLOCKED**

---

## Recommendation for Next Phase

**Phase 23O: Oborovo distribution lock-up policy parity vs Excel**

Before any fixture or factory work:
1. Confirm exact Excel distribution lock-up rule (no dividends until SHL cleared? or different threshold?)
2. Implement matching rule in Python waterfall
3. Re-run parity snapshot to confirm no distributions while SHL balance > 0
4. Only then proceed to frozen senior DS fixture extraction

**Factory opt-in for Oborovo frozen senior schedule is a later separate PR** — blocked until distribution policy is proven correct against Excel.

---

## Guardrails Confirmed

| Guardrail | Status |
|---|---|
| G20 BLOCKED | ✓ Untouched |
| R99/R102 NOT APPROVED | ✓ Untouched |
| Oborovo frozen schedule NOT enabled | ✓ `use_frozen_excel_senior_debt_schedule=False` |
| TUHO factory flags unchanged | ✓ (PR #303 frozen) |
| No Revenue/OPEX/CAPEX/Tax change | ✓ Diagnostic only |
| `partial_pay_sweep` NOT promoted | ✓ |
| Sculpting solver NOT promoted | ✓ |
| C.16 / M1–M18 IDC NOT wired | ✓ |
| PR #299 remains draft / superseded | ✓ |