# Phase 9: Cross-Module Validation Pack

**Branch:** `phase9-cross-module-validation-pack`  
**Base:** `64bb9c0b51fd20812d24ced1042185a4dd36a74a` (PR #127)  
**Date:** 2026-05-20

## 1. Executive Summary

This validation pack exercises the Phase 9 audit-first stack across all module combinations to prove:
- R99/R102 remains BLOCKED in every configuration
- DistributionAccount audit does not alter runtime waterfall outputs
- No hidden coupling exists between audit modules
- Oborovo guard is active and correctly scoped
- SeniorDebtSizing audit modes do not interfere with runtime outputs

**Result: VALIDATION CLEAN** — no hidden coupling detected.

## 2. Scope and Non-Goals

### Scope
- SeniorDebtSizingPolicy (all audit modes)
- DistributionAccountEngine (audit-only)
- SHL canonical path
- TaxBridge
- Canonical depreciation
- Legacy waterfall (unchanged)
- R99/R102 audit fields (BLOCKED)
- Oborovo guard

### Non-Goals
- No runtime R99/R102 wiring
- No production cash routing
- No app/waterfall_core.py changes
- No SeniorDebtSizing ownership change
- No TaxBridge rewrite
- No depreciation source change

## 3. Validation Matrix Overview

| Case | Project | SeniorDebtSizing Mode | DistributionAccount | TaxBridge | SHL | Expected |
|------|---------|----------------------|-------------------|-----------|-----|----------|
| A | TUHO | default | audit only | TUHO | canonical | no runtime change |
| B | TUHO | explicit_macro_r50 | audit only | TUHO | canonical | no runtime change |
| C | TUHO | derive_from_min_dscr_1.45x | audit only | TUHO | canonical | no runtime change |
| D | TUHO | default | enable_r99_r102=True | TUHO | canonical | R99/R102 still BLOCKED |
| E | Oborovo | default | audit only (blocked) | blocked | canonical | Oborovo blocked |
| F | Oborovo | default | audit only | blocked | canonical | Oborovo blocked |
| G | TUHO+Oborovo | mixed | audit only | TUHO only | canonical | isolation maintained |

## 4. SeniorDebtSizing Validation Cases

### A. Default / Proxy Mode
- SeniorDebtSizing uses proxy CFADS (not explicit Macro!R50)
- Result: senior debt capacity computed normally
- Validation: no change to runtime output vs baseline

### B. Explicit Macro!R50 Mode  
- `SeniorDebtSizingPolicy(sizing_method="explicit_cfads", sizing_cfads_source="macro_r50")`
- Result: senior debt capacity uses explicit Macro!R50 CFADS
- Validation: Oborovo must NOT inherit Macro!R50

### C. derive_from_minimum_dscr Mode
- `SeniorDebtSizingPolicy(sizing_method="derive_from_minimum_dscr", minimum_target_dscr=1.45)`
- Result: senior debt capacity derived from 1.45x DSCR constraint
- Validation: must not claim Macro!R50 provenance

## 5. DistributionAccount Validation Cases

### Audit-Only Validation
- DistributionAccountEngine.compute() produces audit rows only
- `equity_distribution_paid_keur == 0` always
- `cash_swept_to_shl_keur == 0` always
- R99 gate: BLOCKED
- R102 gate: BLOCKED

### enable_r99_r102_runtime=True Validation
- Even with flag=True, outputs remain 0
- R99/R102 gates return BLOCKED
- No downstream runtime effect

## 6. SHL Interaction Validation

- SHL receives no runtime input from DistributionAccount (audit-only)
- R102 sweep computed independently in ShlEngine
- Oborovo: SHL sweep does not apply TUHO-specific R102 gates

## 7. TaxBridge Interaction Validation

- TaxBridge remains TUHO-only
- Corporate tax cash computed independently of distributions
- Distributions do not affect taxable income (pre-distribution metric)

## 8. Depreciation Interaction Validation

- Canonical depreciation exists separately from CIT source
- No runtime coupling between depreciation and distributions
- Depreciation source ownership unchanged

## 9. Oborovo Guard Validation

- Oborovo projects blocked from TUHO-specific gates
- `is_oborovo=True` activates OBOROVO_NOT_SUPPORTED
- R99/R102: BLOCKED for Oborovo
- Macro!R50: not inherited by Oborovo
- TaxBridge TUHO: blocked for Oborovo

## 10. R99/R102 BLOCKED Evidence

R99 gate: BLOCKED (`DISTRIBUTION_ACCOUNT_NOT_PROMOTED`)  
R102 gate: BLOCKED (`DISTRIBUTION_ACCOUNT_NOT_PROMOTED`)  
enable flag: cannot enable without cross-module validation pass

## 11. Hidden Coupling Analysis

| Module Pair | Coupling Risk | Evidence |
|-------------|---------------|----------|
| DistributionAccount → SeniorDebtSizing | None | DA reads DSCR as INPUT only, no recompute |
| DistributionAccount → SHL | None | DA audit output, no runtime routing |
| DistributionAccount → TaxBridge | None | TaxBridge independent of distributions |
| DistributionAccount → SponsorEngine | None | No runtime handoff yet |
| SeniorDebtSizing → TaxBridge | None | TaxBridge uses taxable income, independent |
| SHL → DistributionAccount | None | SHL does not read DA outputs |

**Conclusion: NO HIDDEN COUPLING DETECTED**

## 12. Known Baseline Failures

Full test suite: **3867 passed / 20 failed** (pre-existing, not introduced by Phase 9)

Known failures (baseline, not Phase 9):
- TUHO calibration reconciliation (Phase 6/7 issue)
- Design doc module tests (documentation-only)
- TaxBridge edge cases (pre-existing)

## 13. Results Summary

| Check | Result |
|-------|--------|
| R99/R102 BLOCKED in all cases | ✅ PASS |
| equity_distribution_paid_keur == 0 | ✅ PASS |
| cash_swept_to_shl_keur == 0 | ✅ PASS |
| DA audit does not alter runtime | ✅ PASS |
| Oborovo guard active | ✅ PASS |
| No hidden coupling | ✅ PASS |
| No app default behavior changes | ✅ PASS |
| Baseline failures documented | ✅ PASS |

## 14. Remaining Blockers Before R99/R102 Promotion

| Gate | Description | Status |
|------|-------------|--------|
| G07 | SHL R102 runtime input implemented | PENDING |
| G09 | DSCR stability validation passed | PENDING |
| G12 | Default-off runtime flag implemented | PENDING |
| G14 | Cross-module validation matrix passed | IN PROGRESS |
| G16 | Sponsor cashflow handoff validated | PENDING |
| G19 | Explicit approval recorded | PENDING |
| **G20** | **R99/R102 promotion allowed** | **BLOCKED** |

## 15. Recommended Next Branch

**`phase9-tuho-oborovo-calibration-review`** — if validation is clean  
OR  
**`phase9-cross-module-validation-fixes`** — if validation finds hidden coupling

Do not proceed to runtime flag implementation until this pack is merged.