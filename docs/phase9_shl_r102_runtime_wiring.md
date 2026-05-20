# Phase 9: SHL R102 Runtime Wiring

**Branch:** `phase9-shl-r102-runtime-wiring`
**Based on:** `d91b8f87` (post-PR #135)
**Date:** 2026-05-20
**Type:** RUNTIME-SAFE / DEFAULT-NONE / AUDIT-FIRST — SHL input wiring only

## 1. Executive Summary

Wires the `distribution_account_r102_sweep_candidate_keur` input contract into `ShlEngine` as an explicit optional input (default `None`), without enabling DistributionAccount production cash routing and without promoting R99/R102.

**R99/R102 remains BLOCKED (G20).**

## 2. What This Branch Does

Adds one optional field to `ShlPeriodInput`:

```python
distribution_account_r102_sweep_candidate_keur: float | None = None
```

When `None` (default): ShlEngine uses internal R102 sweep — behavior is bit-identical to main.

When non-`None` (>= 0): ShlEngine **adds** the R102 candidate to available cash **before** computing interest, following the documented SHL sweep order: cash interest → PIK → principal. The candidate represents explicit external cash from DistributionAccount made available for SHL service.

## 3. Input Contract

| Property | Value |
|----------|-------|
| Field | `distribution_account_r102_sweep_candidate_keur` |
| Producing module | `DistributionAccountEngine` (future) |
| Consuming module | `ShlEngine` |
| Type | `float \| None` |
| Default | `None` |
| Unit | kEUR |
| Tolerance | 0.01 kEUR |

## 4. Behavior by Mode

### Default (`None`)

- Internal R102 sweep used (existing behavior)
- All SHL outputs identical to main
- Zero drift confirmed by tests

### Explicit candidate provided (non-`None`)

1. **Add** candidate to available cash: `available += candidate`
2. Compute gross accrued interest on opening balance
3. Pay cash interest: `min(gross, available)` — **available now includes the candidate**
4. Capitalize PIK: `max(gross - cash_int, 0)`
5. Repay principal: `min(available - cash_int - pik, outstanding)`

The candidate represents **additional SHL service capacity** — it does not subtract from available cash. It expands the pool of cash available for SHL interest and principal service.

## 5. Result Fields

Both `ShlPeriodResult` and `ShlAuditRow` receive two new fields:

| Field | Description |
|-------|-------------|
| `distribution_account_r102_sweep_candidate_keur` | The input value received (may be `None`) |
| `r102_sweep_applied_keur` | The amount applied to available (0 if `None`) |

## 6. Sweep Order

The SHL sweep order is preserved:

1. **Cash interest first** — `min(gross, available)` after candidate is added
2. **PIK / unpaid interest** — `max(gross - cash_int, 0)`
3. **Principal repayment** — remaining after interest

## 7. Oborovo Guard

The Oborovo guard (project-name-based filtering) is applied by the **caller** (e.g. `waterfall_core` adapter), not by `ShlEngine` directly. `ShlEngine` accepts any non-negative candidate value. The caller is responsible for enforcing the guard.

## 8. R99/R102 Status

- **R99/R102 gates remain BLOCKED** (G8/G20)
- No DistributionAccount production routing enabled
- `ShlEngine` does not read or write R99/R102 gate state
- `DistributionAccountEngine` remains audit-only

## 9. Forbidden Changes

This branch does **not**:
- Promote R99/R102 to runtime
- Enable DistributionAccount production cash routing
- Change `app/waterfall_core.py`
- Change `domain/inputs.py` for non-SHL modules
- Implement Sponsor distribution handoff
- Change TaxBridge or SeniorDebtSizing
- Add scalar plugs or silent behavior changes

## 10. Test Coverage

23 tests covering:
1. Default `None` behavior unchanged (TUHO and Oborovo)
2. Zero drift with `candidate=None`
3. Tolerance match/breach handling
4. Oborovo guard (applied by caller)
5. Sweep application order: candidate adds to available
6. R99/R102 still BLOCKED
7. No `app/waterfall_core.py` changes
8. R102 contract field presence

## 11. Validation

All 68 tests pass (23 new + 45 existing SHL/distribution/closeout guard tests).