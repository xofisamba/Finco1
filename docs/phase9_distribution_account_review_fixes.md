# Phase 9: DistributionAccount Review Fixes

**Branch:** `phase9-distribution-account-review-fixes`  
**Base:** `6daed7b55153beba2e4400eb02166ed0fd5d3eab` (PR #124)  
**Date:** 2026-05-20

## What Was Fixed

### 1. Lockup Policy Field (senior_tenor_years)
- Added `senior_tenor_years: int = 0` to `DistributionAccountPeriodInput`
- Replaced hardcoded `senior_tenor_years=0` with `inp.senior_tenor_years`
- Default `0` preserves audit-first behavior (no tenor-based lockup)
- Callers can now provide explicit lockup period if known

### 2. enable_r99_r102_runtime=True Safety
- Even when `enable_r99_r102_runtime=True` is passed, the engine remains audit-only
- `equity_distribution_paid_keur` is always `0`
- `cash_swept_to_shl_keur` is always `0`
- A warning is always emitted when `enable_r99_r102_runtime=True`
- R99/R102 gates continue to report BLOCKED status

### 3. Oborovo Guard Strengthening
- Oborovo projects are blocked from TUHO-specific R99/R102 assumptions
- Oborovo guard evaluates to `passed=False`
- All outputs remain audit-only candidate values

### 4. Legacy Helper Compatibility
- `compute_tuho_r99_input_period` unchanged and remains backward compatible
- Uses TUHO-specific Excel row formulas (R69, R84, R98, R99, R100, R102)

## Safety Invariants After PR #124 + These Fixes

| Invariant | Value |
|-----------|-------|
| `equity_distribution_paid_keur` | Always `0` |
| `cash_swept_to_shl_keur` | Always `0` |
| R99 gate | Always `BLOCKED` |
| R102 gate | Always `BLOCKED` |
| Oborovo guard | Blocks TUHO gates |
| `enable_r99_r102_runtime` | Emits warning but does NOT enable routing |

## Recommended Next Branch

`phase9-distribution-account-audit-integration` — attach audit outputs to export pipeline only, still without production cash routing.