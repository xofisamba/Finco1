# Phase 9: Sponsor Distribution Handoff Implementation

**Branch:** `phase9-sponsor-distribution-handoff-implementation`
**Based on:** `9ab0faca` (PR #136 merge — SHL R102 runtime wiring)
**Date:** 2026-05-20
**Type:** RUNTIME-SAFE / DEFAULT-OFF / AUDIT-FIRST — sponsor input wiring only
**PR:** #137

## 1. Executive Summary

Wires explicit `distribution_account_received_by_period` into `SponsorCashflowRunner` as an **intentional source replacement** (not automatic override) of `holdco_distribution_by_period`, without promoting R99/R102 and without enabling production DistributionAccount cash routing.

**R99/R102 remains BLOCKED (G20).**

## 2. What This Branch Does

Adds one optional field to `SponsorCashflowRunnerInputs`:

```python
distribution_account_received_by_period: tuple[float, ...] | None = None
```

This is **NOT** automatic runtime wiring. It is an **intentional, opt-in source replacement**: when the caller (e.g., a future integration adapter) explicitly provides a non-`None` value, it **replaces** `holdco_distribution_by_period` as the distribution source for that period.

### Semantics

| `distribution_account_received_by_period` | Source used |
|-------------------------------------------|-------------|
| `None` (default) | `holdco_distribution_by_period` — legacy HoldCo distribution source, unchanged |
| non-`None` tuple | **Explicit** DistributionAccount handoff source — replaces holdco by **intentional caller opt-in** |

### Key Properties

- **All-zero tuple** is a valid explicit source (produces zero distribution, no fallback to HoldCo)
- **Length must match `period_count`** — mismatch raises `ValueError`
- **Sponsor does not inspect or recompute R99/R102 gates**
- **DistributionAccount remains audit-only** (`equity_distribution_paid_keur = 0` when blocked)
- **R99/R102 remains BLOCKED** — no production routing enabled

## 3. Input Contract

| Property | Value |
|----------|-------|
| Field | `distribution_account_received_by_period` |
| Producing module | `DistributionAccountEngine` (audit-only; future integration) |
| Consuming module | `SponsorCashflowRunner` |
| Type | `tuple[float, ...] \| None` |
| Default | `None` |
| Unit | kEUR |
| Replacement rule | Caller-provided non-`None` tuple **replaces** `holdco_distribution_by_period[t]` per period |
| All-zero tuple | Valid explicit source — results in zero distribution, no HoldCo fallback |

## 4. Design Field Pair

| Direction | Field | Unit | Source |
|-----------|-------|------|--------|
| Out | `equity_distribution_paid_keur` | kEUR | `DistributionAccountEngine` (0 when blocked) |
| In | `distribution_received_keur` | kEUR | `SponsorCashflowRunner` via explicit tuple |

## 5. R99/R102 Status

- **R99/R102 gates remain BLOCKED** (G20).
- No DistributionAccount production routing enabled.
- `SponsorCashflowRunner` does not read or evaluate R99/R102 gates.
- `DistributionAccountEngine` remains audit-only.
- G20 remains BLOCKED in gate matrix.

## 6. Oborovo Guard

- Oborovo project: `equity_distribution_paid_keur = 0` (blocked by guard).
- SponsorCashflowRunner receives `None` override → uses holdco path → `0.0`.
- No TUHO-specific distribution values leak into Oborovo.

## 7. Forbidden Changes

This branch does **not**:
- Promote R99/R102 to runtime
- Enable DistributionAccount production cash routing
- Change `app/waterfall_core.py`
- Change `domain/shl/*` (SHL R102 wiring unaffected)
- Change `domain/senior_debt_sizing/*`
- Change TaxBridge or depreciation
- Compute sponsor IRR/MOIC inside DistributionAccount
- Add scalar plugs or silent behavior changes
- Introduce automatic fallback — explicit tuple always wins

## 8. Test Coverage

**29 tests** covering all required cases:

| Case | Tests |
|------|-------|
| 1. Default zero/None behavior unchanged | 4 tests — bit-identical legacy output when `None` |
| 2. Explicit distribution as sponsor inflow | 4 tests — non-zero tuple used as direct source |
| 2b. Explicit tuple semantics | 4 tests — all-zero no-fallback, per-period zero wins, length mismatch raises, net cashflow sign |
| 3. DistributionAccount audit-only output | 2 tests — `equity_distribution_paid_keur = 0` by default |
| 4. Sponsor does not recompute gates | 2 tests — accepts override without gate check |
| 5. No IRR side effects by default | 2 tests — unchanged when `None` |
| 6. Positive explicit handoff | 2 tests — capital account reflects explicit handoff |
| 7. Oborovo guard/isolation | 3 tests — zero by default, no TUHO leakage, R99/R102 not promoted |
| 8. No `app/waterfall_core.py` changes | 1 test — portable guard |
| 9. R99/R102 still BLOCKED | 2 tests — G20 in gate matrix, no production routing |
| 10. Cross-module compatibility | 3 tests — SHL R102, SHL fields, distribution account fields unaffected |

**103 tests pass** (29 new + 74 existing sponsor/distribution/SHL tests).

## 9. Validation

All tests pass. Default `None` behavior is bit-identical to main. Explicit tuple semantics fully tested.

## 10. Next Branch (Recommended)

`phase9-r99-r102-runtime-flag-design-review` — once all phase9 implementation branches are stable.