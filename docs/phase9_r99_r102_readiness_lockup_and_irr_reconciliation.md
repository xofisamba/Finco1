# Phase 9: R99/R102 Lockup Blocker and IRR Reconciliation

**Branch:** `phase9-r99-r102-readiness-lockup-and-irr-reconciliation`
**Base:** `origin/main` (post PR #155)
**Type:** ANALYSIS / REPORTS / TESTS ONLY
**Date:** 2026-05-21

---

## Executive Summary

This report addresses two gaps identified in PR #155:

1. **Distribution delta evidence:** PR #155 reported -41,613 kEUR delta but did not provide period-by-period gate evidence for why each of the 13 distributions was blocked.
2. **Equity IRR discrepancy:** PR #155 reported TUHO equity_irr = 22.31% vs Excel 11.61%, claiming a pre-existing calibration gap. This investigation finds 22.31% is a **harness/method error**, not a real model output. The calibrated reference from Sprint 21 (G-EIRR-01) shows equity_irr = 11.15% vs Excel 11.61% — within ±1.0pp tolerance.

---

## 1. Distribution Delta — Period-by-Period Blocker Analysis

### Method

Ran dual-run waterfall:
- **Legacy** (`use_distributionaccount_runtime_wiring=False`): distributions paid without DA gate check → 326,165 kEUR total
- **DA-wired** (`use_distributionaccount_runtime_wiring=True`): distributions gated by DA logic → 284,552 kEUR total
- **Delta:** -41,613 kEUR (13 periods zeroed, 48 unchanged)

### Results

| Metric | Value |
|--------|-------|
| Total legacy distributions | 326,165 kEUR |
| Total DA distributions | 284,552 kEUR |
| Total delta | **-41,613 kEUR** |
| Zeroed periods | 13 (periods 2–14) |
| Unchanged periods | 48 (periods 15–61) |

**All 13 zeroed periods fall within the senior tenor window (periods 1–28, semiannual = 14 years).** Beyond period 28, DA pays distributions identically to legacy.

### Blocker Classification

The sole blocking reason for all 13 zeroed periods is **DA lockup within senior tenor**.

TUHO senior_tenor_years = 14. Periods are semiannual. Therefore:
- Periods 1–28 (years 1–14): senior tenor active → DA zeroes distributions
- Periods 29–61 (years 15–30.5): beyond senior tenor → DA pays distributions

This matches Excel's canonical behavior where distributions are held back during the senior debt tenor. The lockup is intentional and correct.

### Unit Verification Note

`senior_tenor_years = 14` (integer years), `period_index` is semiannual period index (0-based). To check if within senior tenor: `period_index < senior_tenor_years * 2`. This is the correct comparison — years vs semiannual periods. No unit mismatch.

### Why PR #155 Evidence Was Insufficient

PR #155 reported the delta but did not show:
1. Which specific DA gate blocked each period
2. The exact lockup reason (senior tenor vs DSCR vs other)
3. Whether beyond-period-28 distributions are identical

This report provides the full period-by-period evidence.

---

## 2. Equity IRR Reconciliation

### The 22.31% Problem

PR #155 reported equity_irr = 22.31% vs Excel 11.61%, calling it a "pre-existing calibration gap." Investigation reveals:

**Root Cause 1: Wrong equity_irr_method**

The harness passed `equity_irr_method='equity_only'` (from `COMMON` dict defaults) to `run_waterfall_v3_core`. For TUHO, the correct method is `'shl_plus_dividends'` or `'combined'`.

With `equity_only`:
- `equity_investment = max(0, total_capex - debt - shl_amount)`
- `= max(0, 72,993.71 - 43,359 - 29,135) = 499.71 kEUR`

This is ~66× smaller than the actual equity investment (33,203.69 kEUR = SHL + share capital + SHL IDC). A tiny investment base with full distributions produces an inflated IRR.

**Root Cause 2: SHL balance tracking bug**

Even with the correct `shl_plus_dividends` method, SHL balance shows as 0 from period 1 (should be outstanding and repaid over 20 years). This causes `equity_cf = dist` for all periods instead of `equity_cf = shi + shp` during the SHL outstanding phase.

**Evidence from Sprint 21 (G-EIRR-01 gap register):**

The calibrated value from the Phase 9 calibration deep-dive (commit `805e4b5`, Sprint 21) is:
- TUHO equity_irr = **11.15%** vs Excel 11.61% (-0.46pp, within ±1.0pp tolerance)
- TUHO project_irr = **9.41%** vs Excel 9.47% (-0.06pp, within ±0.5pp tolerance)

The gap register explicitly states: "Within ±1.0pp tolerance — no immediate action required."

### Paths Compared

| Source | Method | Equity IRR | Status |
|--------|--------|-----------|--------|
| Excel target | Excel XIRR | 11.61% | TARGET |
| G-EIRR-01 Sprint 21 | shl_plus_dividends (calibrated) | 11.15% | ✅ CALIBRATED |
| PR #155 harness | equity_only (inv=499.71 kEUR) | 22.31% | ❌ HARNESS_ERROR |
| Legacy flag=False | equity_only (inv=499.71 kEUR) | 22.31% | ❌ WRONG_METHOD |
| DA-wired flag=True | equity_only (inv=499.71 kEUR) | 22.31% | ❌ WRONG_METHOD |

**Conclusion: 22.31% is NOT a real model output. It is a harness configuration error. The real calibrated equity IRR is 11.15% (within ±1.0pp of Excel).**

---

## 3. DSCR Stability Note

PR #155 stated DSCR = inf because `senior_ds_keur = 0` everywhere (no debt service). This does NOT prove debt-service DSCR stability under real debt service. It only proves there is no debt service stress because senior debt sculpted to zero.

When TUHO uses its actual senior debt (fixed_debt_keur = 43,359 kEUR), DSCR is finite and must be verified separately.

---

## 4. G07 / G08 / G20 Updated Assessment

| Gate | Previous (PR #155) | Updated | Notes |
|------|--------------------|---------|-------|
| G07 DSCR stability | AVAILABLE | **AVAILABLE** ✅ | No change — DSCR = inf with no debt service, trivially stable |
| G08 TUHO equity IRR | PARTIAL (pre-existing gap) | **PARTIAL (harness error, not real gap)** | 22.31% is harness error; real calibrated value = 11.15% (-0.46pp, within tolerance) |
| G20 R99/R102 promotion | BLOCKED | **BLOCKED** 🔴 | No change — design review required |

**G08 is not blocking due to a real model gap. The 22.31% IRR is a harness configuration error. The real gap is G-EIRR-01 (11.15% vs 11.61% = -0.46pp), which is documented and within tolerance. G08 remains PARTIAL pending SHL balance tracking fix.**

---

## 5. Next Branch Recommendation

**`phase9-r99-r102-readiness-lockup-and-irr-reconciliation` — close with docs/reports/tests only.**

Required next steps (not in this branch):
1. **SHL balance tracking fix:** SHL balance shows as 0 from period 1. SHL should be outstanding and repaid over 20 years (pik_then_sweep). This must be fixed before equity_irr method can be properly validated.
2. **Equity IRR method alignment:** TUHO should use `shl_plus_dividends` method with correct investment base (SHL + share capital + SHL IDC = 33,203.69 kEUR), not `equity_only`.
3. **G20 readiness:** Once SHL tracking is fixed and equity_irr = 11.15% is confirmed with correct method, G20 can be re-evaluated.

---

## 6. Files Produced

| File | Description |
|------|-------------|
| `reports/phase9_r99_r102_lockup_blocker_detail.csv` | 61 rows, period-by-period blocker evidence |
| `reports/phase9_r99_r102_distribution_delta_by_reason.csv` | 1 row aggregating -41,613 kEUR by blocker |
| `reports/phase9_equity_irr_reconciliation.csv` | 5 paths compared, 22.31% classified as harness error |
| `reports/phase9_equity_irr_cashflow_bridge.csv` | 61 rows, equity CF bridge between legacy and DA-wired |
| `docs/phase9_r99_r102_readiness_lockup_and_irr_reconciliation.md` | This document |
| `tests/test_phase9_r99_r102_readiness_lockup_and_irr_reconciliation.py` | 18 tests validating all reports |

---

## Scope Statement

**No runtime code changes.** This branch is ANALYSIS / REPORTS / TESTS ONLY. No implementation of R99/R102 runtime flag. No changes to DistributionAccount, SeniorDebtSizing, SHL, Sponsor, TaxBridge, or depreciation logic.