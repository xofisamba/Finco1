# Phase C Post-Runtime Validation

**Branch:** `phase9-phasec-post-runtime-validation`
**Based on:** `ef47469` (PR #151 — DA runtime wiring)
**Date:** 2026-05-21
**Type:** VALIDATION / GATE REFRESH / REPORTS / TESTS ONLY

No runtime behavior changes in this branch.

---

## 1. Executive Summary

After PRs #136, #149, #150, #151, and the already-merged sponsor handoff (#137/be088e7), the Phase C runtime integrations are now on `main`. This branch consolidates the post-integration state, refreshes gate statuses, and validates that all combinations behave as designed — with R99/R102 remaining BLOCKED throughout.

**Recommended next branch:** `phase9-r99-r102-runtime-flag-design-review`

---

## 2. What's on Main

### 2.1 DistributionAccount Runtime Wiring (PR #151)

**Flag:** `use_distributionaccount_runtime_wiring: bool = False` in `run_waterfall_v3_core()`

| | flag=False | flag=True |
|---|---|---|
| `distribution_keur` | exact legacy | pass-through alias of DA `equity_distribution_paid_keur` |
| TUHO total | ~326,165 kEUR | ~284,552 kEUR |
| Oborovo | unchanged | blocked by guard |
| Audit metadata | empty | per-period + result-level |
| R99/R102 | BLOCKED | BLOCKED (economic mode, not promoted) |

**Lockup delta explanation:** TUHO senior tenor = 14 semi-annual periods. DA economic mode correctly evaluates the lockup gate, zeroing distributions in periods 1–13. Legacy runtime distributes in lockup. Delta ≈ -41,613 kEUR is expected and correct.

### 2.2 Sponsor Handoff (already merged, commit be088e7)

**Input:** `SponsorCashflowRunnerInputs.distribution_account_received_by_period: tuple[float, ...] | None = None`

| Value | Behavior |
|-------|----------|
| `None` (default) | `holdco_distribution_by_period` used — legacy behavior unchanged |
| non-`None` tuple | Replaces `holdco_distribution_by_period[t]` per period |
| all-zero tuple | Valid explicit source — zero distribution, no HoldCo fallback |

Sponsor IRR/MOIC computed from explicit cashflows only. No R99/R102 gate recomputation.

### 2.3 SHL R102 Input (PR #136)

**Input:** `distribution_account_r102_sweep_candidate_keur` — added to SHL service cash pool.

| Value | Behavior |
|-------|----------|
| `None` / not provided | legacy SHL behavior |
| provided kEUR value | candidate added to SHL service cash pool |

R99/R102 remains BLOCKED. SHL R102 port is an input, not a promotion.

### 2.4 TaxBridge Dual-Run Reconciliation (PR #150)

Tax bridge now uses `cf_after_reserves_keur` (same cash source as runtime distribution) when `r99_fcf` diverges from `cf_after_reserves` in TUHO tax_bridge mode. tax_bridge combos now show 0 UNEXPECTED / 0 BLOCKING.

### 2.5 DA Dual-Run Economic Gate Evaluation (PR #149)

Economic mode (`audit_economic_mode=True`) evaluates gates using cash logic without promoting R99/R102. Governed mode (`audit_economic_mode=False`) always blocks R99/R102 as before.

---

## 3. Gate Status Refresh

| Gate ID | Gate Name | Previous | Current | Evidence | Blocker | Next Action | Owner |
|---------|-----------|----------|---------|----------|---------|-------------|-------|
| G01 | SHL R102 input wiring | IN_PROGRESS | **READY** | PR #136, `distribution_account_r102_sweep_candidate_keur` in use | none | none | domain/shl |
| G02 | Sponsor distribution handoff | IN_PROGRESS | **READY** | be088e7, `distribution_account_received_by_period` in `SponsorCashflowRunnerInputs` | none | none | domain/sponsor |
| G03 | DA runtime wiring | IN_PROGRESS | **READY** | PR #151, `use_distributionaccount_runtime_wiring` flag | none | none | app/waterfall_core |
| G04 | TaxBridge dual-run reconciliation | IN_PROGRESS | **READY** | PR #150, tax_bridge 0 UNEXPECTED/0 BLOCKING | none | none | app/waterfall_core |
| G05 | DA dual-run economic gate eval | IN_PROGRESS | **READY** | PR #149, `audit_economic_mode` in DA inputs | none | none | domain/distribution_account |
| G06 | Phase C combo validation | PENDING | **READY** | This branch: 0 UNEXPECTED, 0 BLOCKING for supported combos | none | proceed to G07 | all |
| G07 | R99/R102 final promotion approval | BLOCKED | **BLOCKED** | G20 governance design; no runtime promotion implemented | G20 governance pending | `phase9-r99-r102-runtime-flag-design-review` | domain/distribution_account |
| G08 | G20 Oborovo promotion | BLOCKED | **BLOCKED** | Oborovo guard design not yet approved | guard design | separate guard review | domain/distribution_account |

---

## 4. Combo Validation Summary

| Case | TUHO flag=False | TUHO flag=True | Oborovo flag=True | R99/R102 |
|------|-----------------|----------------|-------------------|----------|
| baseline | legacy dist | DA wired | guard blocked | BLOCKED |
| +tax_bridge | legacy dist | DA wired | guard blocked | BLOCKED |
| +sponsor_handoff | legacy dist | DA wired | guard blocked | BLOCKED |
| +SHL R102 input | legacy dist | DA wired | guard blocked | BLOCKED |
| all three inputs | legacy dist | DA wired | guard blocked | BLOCKED |

All supported combos: 0 UNEXPECTED, 0 BLOCKING.

---

## 5. R99/R102 Governance

**BLOCKED across all integrations.**

- DA runtime wiring uses `audit_economic_mode=True` (gates evaluated, not promoted)
- Sponsor handoff does not compute R99/R102 gates
- SHL R102 input is a candidate input, not a promotion
- No module promotes R99/R102 to unconditional runtime approval

---

## 6. Non-Goals (Not Changed)

- No R99/R102 promotion
- No SHL behavior changes beyond the candidate input
- No SponsorEngine behavior changes beyond the optional handoff input
- No TaxBridge rewrite
- No SeniorDebtSizing changes
- No depreciation changes
- No UI changes
- No Excel export changes
- No scalar plugs

---

## 7. Next Branch

**Recommended:** `phase9-r99-r102-runtime-flag-design-review`

Purpose: design the explicit runtime flag for R99/R102 promotion, with proper governance, guardrails, and Oborovo-specific considerations.

**Alternate:** `phase9-sponsor-distribution-handoff-review-fixes` — only if issues found in sponsor handoff integration.

---

## 8. Test Coverage

This branch adds:
- `tests/test_phase9_phasec_post_runtime_validation.py` — validates all reports, gate statuses, and non-promotion invariants

Run:
```bash
pytest tests/test_phase9_phasec_post_runtime_validation.py -v
```

---

## 9. Files in This Branch

| File | Type |
|------|------|
| `docs/phase9_phasec_post_runtime_validation.md` | This document |
| `reports/phase9_phasec_gate_refresh.csv` | Gate status matrix |
| `reports/phase9_phasec_runtime_validation_matrix.csv` | Validation case definitions |
| `reports/phase9_phasec_runtime_validation_results.csv` | Actual validation results |
| `tests/test_phase9_phasec_post_runtime_validation.py` | Validation tests |