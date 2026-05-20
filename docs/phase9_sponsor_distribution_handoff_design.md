# Phase 9: Sponsor Distribution Handoff Design

**Branch:** `phase9-sponsor-distribution-handoff-design`  
**Base:** `f3980bf` (PR #132 merge)  
**Date:** 2026-05-20  
**Type:** DOCS / DESIGN / GATE REVIEW ONLY — no runtime code

## 1. Executive Summary

This design defines the contract by which `DistributionAccount` passes equity distribution cashflow to `SponsorEngine` as an explicit runtime input, without SponsorEngine recomputing R99/R102 gates and without DistributionAccount computing sponsor IRR/MOIC.

**Key Decision:**
- Field: `equity_distribution_paid_keur` (from DistributionAccount)
- Consumed by: `SponsorCashflowRunner` as `distribution_received_keur`
- Default: `0.0` (audit-only, no runtime cash)
- R99/R102 remains BLOCKED throughout

## 2. Current Status

| Gate | Status |
|------|--------|
| G06 SHL R102 input designed | ✅ READY (PR #132) |
| G15 Sponsor handoff designed | ⏳ THIS BRANCH |
| G20 R99/R102 promotion | BLOCKED |

**Existing stack:**
- DistributionAccountEngine: audit-first, computes R99/R102 candidates but routes nothing downstream
- SponsorCashflowRunner: audit-only, uses `holdco_distribution_by_period` (not from DistributionAccount)
- No runtime handoff exists yet

## 3. Existing Sponsor/Equity IRR Path

`SponsorCashflowRunner.run_sponsor_cashflows()` computes sponsor IRR from:
- `equity_injections` — from project inputs
- `holdco_distribution_by_period` — directly from HoldCo outputs (not from DistributionAccount)
- `wht_rate` — project input

**Current flow (audit-only):**
```
HoldCo → holdco_distribution_by_period → SponsorCashflowRunner → sponsor IRR/MOIC
                          ↑
                    NOT from DistributionAccount
```

**DistributionAccount audit output shows:**
- `equity_distribution_candidate_keur` — max possible distribution (before gate evaluation)
- `equity_distribution_paid_keur` — always 0.0 (audit-only)
- `blocked_reasons` — list of active block reasons

## 4. DistributionAccount Ownership

- R99 gate evaluation: checks equity distribution eligibility
- R102 gate evaluation: checks SHL sweep capacity
- DSCR gate, lockup gate, Oborovo guard
- Cash routing decision: pays or blocks
- **Must NOT compute:** sponsor IRR, MOIC, investor waterfall tiers

## 5. SponsorEngine Ownership

- Sponsor-level cashflow schedule (equity injections + distributions)
- Sponsor IRR / MOIC computation
- Capital account balance tracking
- WHT on distributions
- Multi-investor allocation (future)
- **Must NOT recompute:** R99/R102 gates, DSCR gates

## 6. Proposed Sponsor Distribution Input Contract

### Primary Field Pair

| Direction | Field | Unit | Source |
|-----------|-------|------|--------|
| Out | `equity_distribution_paid_keur` | kEUR | DistributionAccountEngine |
| In | `distribution_received_keur` | kEUR | SponsorCashflowRunner |

### Acceptance Behavior

When `distribution_received_keur` is provided (> 0):
1. SponsorCashflowRunner receives it as explicit cash inflow
2. Capital account updated: balance += distribution
3. Sponsor IRR recomputed from explicit cashflows
4. No waterfall inspection, no gate recomputation

## 7. Field Definitions and Units

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `equity_distribution_paid_keur` | float | kEUR | DistributionAccount output; 0.0 when blocked |
| `distribution_received_keur` | float | kEUR | SponsorCashflowRunner input; 0.0 when blocked |
| `net_cashflow_keur` | float | kEUR | distribution - injection - wht |
| `wht_on_distribution_keur` | float | kEUR | Withholding tax on distribution |
| `capital_account_balance_keur` | float | kEUR | Cumulative balance after injection/distribution |

## 8. Timing and Sign Convention

| Field | Sign | Timing |
|-------|------|--------|
| `equity_injected_keur` | negative (outflow) | Period 0 and construction |
| `distribution_received_keur` | positive (inflow) | Post-COD, after SHL sweep |
| `wht_on_distribution_keur` | negative (outflow) | Same period as distribution |
| `net_cashflow_keur` | ± | Period-end |

## 9. Blocked/Default-Off Behavior

**Current (audit-only):**
- `equity_distribution_paid_keur` computed but not routed
- `distribution_received_keur = 0.0` for all periods
- Sponsor IRR computed from `holdco_distribution_by_period` (direct HoldCo path)

**R99 blocked in DistributionAccount:**
- `blocked_reasons` = ["R99_BLOCKED"]
- `equity_distribution_paid_keur = 0.0`
- SponsorEngine receives `0.0` → no sponsor cashflow change

## 10. Future Runtime Behavior

When `enable_distribution_account_runtime=True` (future):

1. DistributionAccount evaluates R99 gate
2. If PASSED: `equity_distribution_paid_keur = equity_distribution_candidate_keur`
3. This value passed to SponsorCashflowRunner as `distribution_received_keur`
4. SponsorEngine treats it as explicit cash inflow
5. Sponsor IRR/MOIC recomputed from explicit inputs only

## 11. Circular Dependency Containment

| Risk | Containment |
|------|-------------|
| Distribution → CFADS → DSCR → Distribution | DSCR gate uses pre-distribution CFADS |
| Sponsor IRR → distribution sizing | No loop: SponsorEngine does not set distribution amount |
| HoldCo → DistributionAccount → Sponsor | No loop: HoldCo output is separate from DistributionAccount output |

## 12. Investor/Waterfall Future Extension

**Phase 7B roadmap (future):**
- LP/GP split in `DistributionAccount` (currently not supported — single equity holder)
- Multi-investor capital account tiers
- Waterfall tier allocation (first priority: senior debt, second: SHL, third: DSRA, etc.)

**This design is compatible with LP/GP split:**
- DistributionAccount produces `lp_distribution_keur` and `gp_distribution_keur` (future)
- SponsorCashflowRunner receives both as separate inputs

## 13. Oborovo Guard Policy

When `is_oborovo=True`:
- Oborovo guard blocks TUHO-specific gates
- `equity_distribution_paid_keur = 0.0` for Oborovo
- SponsorEngine receives `0.0` for Oborovo periods
- Oborovo does not receive TUHO-equity distribution assumptions

## 14. Validation Requirements

| Check | Method | Gate |
|-------|--------|------|
| Sponsor receives zero when R99 blocked | Audit row check | G15 |
| Sponsor IRR stable with/without handoff | Sensitivity run | G16 |
| Oborovo guard verified | Oborovo project run | G05 |
| No circular dependency | Architecture review | G10 |

## 15. Gate Matrix Update

| Gate | Description | Previous | Current |
|------|-------------|----------|---------|
| G05 | Oborovo guard implemented | READY | READY |
| G06 | SHL R102 input designed | READY | READY |
| G07 | SHL R102 input implemented | PENDING | PENDING |
| G15 | Sponsor handoff designed | PENDING | **READY** (this design) |
| G16 | Sponsor handoff validated | BLOCKED | BLOCKED |
| G20 | R99/R102 promotion | BLOCKED | BLOCKED |

## 16. Forbidden Scope

- No `domain/sponsor/*` runtime changes
- No `domain/distribution_account/*` runtime changes
- No `app/waterfall_core.py` changes
- No R99/R102 promotion
- No SHL implementation changes
- No SeniorDebtSizing changes
- No TaxBridge changes

## 17. Recommended Next Branch

**`phase9-closeout-gate-report`**

Documents Phase 9 completion:
- All gates reviewed
- Phase 9 summary: DistributionAccount audit-first complete
- Remaining work: G07 implementation, G16 validation, G20 promotion
- G20 R99/R102 remains BLOCKED