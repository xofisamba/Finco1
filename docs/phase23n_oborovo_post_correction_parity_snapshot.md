# Phase 23N: Oborovo Post-Correction Parity Snapshot

**Type:** Diagnostic — no runtime changes

**Base SHA:** `da0852795984317394f9f8d0b1db40bd33d05323` (after PR #312 merge)
**Branch:** `phase23n-oborovo-post-correction-parity-snapshot`

---

## ⚠️ Issue Corrected in this Version

The previous version (c3d8682) incorrectly described pre-2050 Oborovo distributions as "normal" or "correct behavior."

**Corrected:** Pre-2050 distributions with SHL principal outstanding are now identified as a **detected blocker** — not confirmed correct. See Section "Distribution Lock-Up Policy Mismatch" below. Diagnostic test passes by proving the mismatch exists; not a CI failure.

This diagnostic PR remains draft until Phase 23O resolves the distribution policy question.

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

| Op# | Date | SHL Balance | SHL Service | Distribution | Status |
|---|---|---|---|---|---|
| 28 | 2044-12-31 | 15,790.0 | 635.1 | 2,615.92 | ⚠️ Requires Excel verification |
| 29 | 2045-06-30 | 15,790.0 | 626.4 | 2,352.21 | ⚠️ Requires Excel verification |
| **30** | **2045-12-31** | **0.00** | **16,416.8** | **0.00** | **Guard ✓ (PR #304)** |
| 31 | 2046-06-30 | 0.00 | 0.00 | 2,335.13 | ⚠️ Requires Excel verification |
| 32 | 2046-12-31 | 0.00 | 0.00 | 2,472.70 | ⚠️ Requires Excel verification |
| 33 | 2047-06-30 | 0.00 | 0.00 | 2,219.07 | ⚠️ Requires Excel verification |
| 38 | 2049-12-31 | 0.00 | 16,426.8 | **0.00** | Guard ✓ — SHL bullet |
| **39** | **2050-06-30** | **0.00** | **0.00** | **2,994.41** | **First distribution after SHL cleared ✓** |
| 40 | 2050-12-31 | 0.00 | 0.00 | 3,332.78 | |
| 41 | 2051-06-30 | 0.00 | 0.00 | 3,043.16 | |
| 42 | 2051-12-31 | 0.00 | 0.00 | 3,387.41 | |

**Note:** Periods 31-37 show shl_balance=0.00 but distributions ARE shown — this means senior debt was repaid at period 28 (2045-12-31). SHL remains at 15,790 kEUR for the 20-year bullet but current-period service (~626-636 kEUR) is far below fcf, so distributions unlock. Per Excel CF tab, dividends in this window should be zero — this is the detected blocker.

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
DSCR ~1.26 during active period — close to target_dscr=1.15 but slightly above.

---

## ⚠️ Detected Blocker: Oborovo Distribution Lock-Up Policy Mismatch

**Severity: BLOCKER for Phase 23O frozen senior DS fixture extraction**

**The Problem:**

Python uses a per-period cash-flow guard: distribute if `fcf_for_shl_keur > shl_service_keur` (current-period interest only). For Oborovo's 20-year bullet SHL (principal 15,790 kEUR), current-period interest is only ~626-636 kEUR — easily covered throughout the loan life. Python distributes 2,000-2,600 kEUR per period throughout 2046-2049 while the SHL principal of 15,790 kEUR remains outstanding.

**Per manual Excel CF tab inspection:** dividends are blank/zero until around 2050; distributions begin only after SHL is cleared at 2049-12-31.

| Policy | Gating rule |
|---|---|
| **Python** | `fcf_for_shl > shl_service` per period (current-period interest only) |
| **Excel (observed)** | No SHL principal outstanding (SHL fully cleared at 2049-12-31) |

This is a **distribution lock-up policy mismatch**. Phase 23H/PR #304 addressed the SHL final period guard. This is a separate, earlier-stage mismatch that exists throughout the entire loan life (15+ years before the bullet).

**Impact:** Oborovo is **NOT ready** for frozen senior DS fixture extraction until the distribution policy is reconciled with Excel.

---

## Remaining Material Gaps

| Gap | Severity | Notes |
|---|---|---|
| **Oborovo distribution lock-up policy vs Excel** | **BLOCKER** | See above — Phase 23O must resolve first |
| **Oborovo frozen senior DS fixture not implemented** | **HIGH** | Deferred until distribution policy resolved |
| Senior debt amount vs Excel | **MEDIUM** | Python = 42,852 kEUR; need Excel anchor |
| Senior DSCR trajectory vs Excel | **MEDIUM** | DSCR ~1.26 during active period |
| Revenue/OpEx calibration vs Excel | **LOW** | Y1 EBITDA ~2,575 kEUR; need Excel anchors |
| Construction funding / IDC | **DEFERRED** | Phase 23L confirmed sufficient |

---

## Recommendation for Next Phase

**Phase 23O: Oborovo distribution lock-up policy parity vs Excel**

1. Confirm exact Excel distribution lock-up rule (no dividends until SHL cleared? or different threshold?)
2. Implement matching rule in Python waterfall
3. Re-run parity snapshot to confirm no distributions while SHL balance > 0
4. Only then proceed to frozen senior DS fixture extraction

**Factory opt-in for Oborovo frozen senior schedule remains BLOCKED — a separate later PR after distribution policy proven correct against Excel.**

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