# Phase 9: Sponsor Distribution Handoff Implementation

**Branch:** `phase9-sponsor-distribution-handoff-implementation`
**Based on:** `9ab0faca` (PR #136 merge — SHL R102 runtime wiring)
**Date:** 2026-05-20
**Type:** RUNTIME-SAFE / DEFAULT-OFF / AUDIT-FIRST — sponsor input wiring only

## 1. Executive Summary

Wires explicit `distribution_account_received_by_period` into `SponsorCashflowRunner` as an optional override of `holdco_distribution_by_period`, without promoting R99/R102 and without enabling production DistributionAccount cash routing.

**R99/R102 remains BLOCKED (G20).**

## 2. What This Branch Does

Adds one optional field to `SponsorCashflowRunnerInputs`:

```python
distribution_account_received_by_period: tuple[float, ...] | None = None
```

When `None` (default): `SponsorCashflowRunner` uses `holdco_distribution_by_period` — behavior is bit-identical to main.

When non-`None`: overrides `holdco_distribution_by_period` for each period, allowing an explicit DistributionAccount equity distribution cashflow to reach the sponsor without the sponsor recomputing R99/R102 gates.

## 3. Input Contract

| Property | Value |
|----------|-------|
| Field | `distribution_account_received_by_period` |
| Producing module | `DistributionAccountEngine` (future) |
| Consuming module | `SponsorCashflowRunner` |
| Type | `tuple[float, ...] \| None` |
| Default | `None` |
| Unit | kEUR |
| Override behavior | When provided, replaces `holdco_distribution_by_period[t]` for period t |

## 4. Behavior by Mode

### Default (`None`)

- `holdco_distribution_by_period` drives sponsor cashflow
- All sponsor outputs identical to main
- Zero drift confirmed by tests

### Explicit override provided (non-`None`)

For each period t:
1. `distribution = distribution_account_received_by_period[t]` (overrides holdco path)
2. WHT computed on distribution: `wht = distribution * wht_rate`
3. Capital account updated: `balance += equity_injected - distribution`
4. No gate evaluation — override bypasses holdco path entirely

## 5. Sign Convention

| Field | Sign | Timing |
|-------|------|--------|
| `equity_injected_keur` | positive (inflow to project) | Period 0 + construction |
| `distribution_received_keur` | positive (inflow to sponsor) | Post-COD, after SHL sweep |
| `wht_on_distribution_keur` | positive (outflow from sponsor) | Same period as distribution |
| `net_cashflow_keur` | `dist - injection - wht` | Period-end |

## 6. Design Field Pair

| Direction | Field | Unit | Source |
|-----------|-------|------|--------|
| Out | `equity_distribution_paid_keur` | kEUR | `DistributionAccountEngine` (0 when blocked) |
| In | `distribution_received_keur` | kEUR | `SponsorCashflowRunner` via override |

## 7. R99/R102 Status

- **R99/R102 gates remain BLOCKED** (G8/G20)
- No DistributionAccount production routing enabled
- `SponsorCashflowRunner` does not read or evaluate R99/R102 gates
- `DistributionAccountEngine` remains audit-only
- G20 remains BLOCKED in gate matrix

## 8. Ownership

| Module | Responsibility |
|--------|---------------|
| `DistributionAccountEngine` | Audit-only; produces `equity_distribution_paid_keur = 0` when blocked |
| `SponsorCashflowRunner` | Consumes explicit override; computes capital account + net cashflow |
| `SponsorCashflowRunner` | Does NOT evaluate R99/R102 gates |
| `DistributionAccountEngine` | Does NOT compute sponsor IRR/MOIC |

## 9. Oborovo Guard

- Oborovo project: `equity_distribution_paid_keur = 0` (blocked by guard)
- SponsorCashflowRunner receives `None` override → uses holdco path → `0.0`
- No TUHO-specific distribution values leak into Oborovo

## 10. Forbidden Changes

This branch does **not**:
- Promote R99/R102 to runtime
- Enable DistributionAccount production cash routing
- Change `app/waterfall_core.py`
- Change `domain/shl/*` (SHL R102 wiring unaffected)
- Change `domain/senior_debt_sizing/*`
- Change TaxBridge or depreciation
- Compute sponsor IRR/MOIC inside DistributionAccount
- Add scalar plugs or silent behavior changes

## 11. Test Coverage

25 tests covering all 10 required cases:

| Case | Description |
|------|-------------|
| 1 | Default zero/None behavior unchanged |
| 2 | Explicit distribution input included as sponsor cash inflow |
| 3 | DistributionAccount audit/default output `equity_distribution_paid_keur = 0` |
| 4 | Sponsor module does not recompute R99/R102 gates |
| 5 | No IRR side effects by default |
| 6 | Positive explicit handoff case |
| 7 | Oborovo guard/isolation |
| 8 | No `app/waterfall_core.py` changes |
| 9 | R99/R102 still BLOCKED |
| 10 | Cross-module compatibility (SHL R102 unaffected) |

## 12. Validation

All 99 tests pass (25 new + 74 existing sponsor/distribution/SHL tests).

## 13. Next Branch

Recommended: `phase9-r99-r102-runtime-flag-design-review` (if clean)
Fallback: `phase9-sponsor-distribution-handoff-review-fixes` (if issues found)