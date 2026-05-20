# Phase 9: DistributionAccount Audit-First Implementation Notes

## Status: ✅ Implemented

## Overview

Phase 9 implements the canonical `DistributionAccount` engine in audit-first mode. All outputs are candidate values — no production cashflow routing occurs. R99/R102 remain BLOCKED per G1/G8 governance rules.

## Module Layout

```
domain/distribution_account/
├── __init__.py      # updated exports (was TUHO-only helper)
├── inputs.py        # NEW — input dataclasses
├── result.py        # UPDATED — added new result types, kept R99InputResult
├── engine.py        # UPDATED — DistributionAccountEngine + preserved compute_tuho_r99_input_period
├── gates.py         # NEW — gate evaluation logic
└── audit.py         # NEW — DistributionAuditRow
```

## Design Principles

### Audit-Only (G1/G8 Governance)
- R99 gate always BLOCKED — requires `enable_r99_r102_runtime=True` (never set in this branch)
- R102 gate always BLOCKED — same rule
- `equity_distribution_paid_keur` always 0.0
- `cash_swept_to_shl_keur` always 0.0
- Engine does NOT import `app.waterfall_core`

### Canonical DistributionAccount
- Operates after senior debt service and SHL sweep
- Computes `equity_distribution_candidate_keur` (not routed)
- Enforces DSCR gate, lockup gate, oborovo guard
- Tracks distribution account balance across periods

### Oborovo Guard
- Oborovo project does NOT have TUHO-specific gates
- R99/R102 gates blocked for Oborovo (OBOROVO_NOT_SUPPORTED)

## Key Dataclasses

### Inputs
- `R99R102GateInputs` — gate evaluation inputs
- `DistributionAccountPeriodInput` — single period input
- `DistributionAccountInputs` — collection of period inputs

### Results
- `DistributionGateResult` — single gate outcome
- `DistributionAccountPeriodResult` — single period outcome
- `DistributionAccountResult` — full-period-set outcome
- `R99InputResult` — preserved from existing TUHO helper

### Gates
- `evaluate_r99_gate` — R99 equity distribution gate
- `evaluate_r102_gate` — R102 SHL sweep gate
- `evaluate_dscr_gate` — DSCR threshold gate
- `evaluate_lockup_gate` — lockup period gate
- `evaluate_oborovo_guard` — Oborovo project guard
- `evaluate_cash_gate` — cash sufficiency gate

## BLOCKED_REASONS

| Key | Value |
|-----|-------|
| R99_BLOCKED | R99 gate not promoted to runtime — audit-only |
| R102_BLOCKED | R102 gate not promoted to runtime — audit-only |
| DSCR_GATE_FAILED | DSCR below target_distribution_dscr threshold |
| OBOROVO_NOT_SUPPORTED | Oborovo project — TUHO-specific gates blocked |
| NEGATIVE_CASH | Insufficient cash for distribution |
| DISTRIBUTION_ACCOUNT_NOT_PROMOTED | DistributionAccount not in runtime — audit-only mode |
| LOCKUP | Period locked — DSRA/JDSRA below target or construction period |
| SENIOR_TENOR | Within senior debt tenor — distributions blocked |

## Tests

10 test classes covering:
- Dataclass construction
- Gate pass/fail logic
- Cash reconciliation
- Blocked reason coverage
- Oborovo guard
- Equity distribution candidate (audit-only)
- Audit row CSV generation
- R99/R102 always blocked
- No runtime ownership changes

## Next Steps

1. Integrate with SPV cashflow model (Phase 9B)
2. Connect to audit export pipeline
3. Enable R99/R102 runtime when governance approves (G1/G8)