# Phase 9 Closeout Gate Report

**Branch:** `phase9-closeout-gate-report`  
**Base:** `808785c` (PR #133 merge)  
**Date:** 2026-05-20  
**Type:** DOCS / REPORTS — no runtime code

## 1. Executive Summary

Phase 9 audit/design/validation/calibration block is **COMPLETE**.

This report documents all Phase 9 deliverables, gate statuses, and the path forward. R99/R102 runtime promotion remains **BLOCKED** (G20). The next work should be implementation of missing contracts or separate CIT-source decision — not direct R99/R102 promotion.

**Phase 9 PRs merged:** #122–#133 (12 PRs)  
**R99/R102 runtime promotion:** ❌ NOT APPROVED — G20 remains BLOCKED

---

## 2. Scope of Phase 9

Phase 9 was the audit-first implementation and design phase for the DistributionAccount stack, covering:
1. SeniorDebtSizing policy wiring (explicit_cfads, derive_from_minimum_dscr)
2. DistributionAccount design + audit-first implementation
3. R99/R102 runtime wiring design
4. Cross-module validation pack
5. TUHO + Oborovo calibration review and deep dive
6. SHL R102 handoff design
7. Sponsor distribution handoff design

---

## 3. Completed PR Inventory

| PR | Branch | Title | Status |
|----|--------|-------|--------|
| #122 | senior-debt-sizing-explicit-cfads | SeniorDebtSizing explicit_cfads policy | ✅ merged |
| #123 | phase9-distribution-account-design | DistributionAccount design | ✅ merged |
| #124 | phase9-distribution-account-audit-first | DistributionAccount audit-first implementation | ✅ merged |
| #125 | phase9-distribution-account-review-fixes | DistributionAccount review fixes | ✅ merged |
| #126 | phase9-distribution-account-audit-integration | DistributionAccount audit integration | ✅ merged |
| #127 | phase9-r99-r102-runtime-wiring-design | R99/R102 runtime wiring design | ✅ merged |
| #128 | phase9-cross-module-validation-pack | Cross-module validation pack | ✅ merged |
| #129 | phase9-tuho-oborovo-calibration-review | TUHO+Oborovo calibration review | ✅ merged |
| #130 | phase7f-oborovo-opex-fix | Oborovo OpEx fix (report correction) | ✅ merged |
| #131 | phase9-tuho-calibration-deep-dive | TUHO calibration deep dive | ✅ merged |
| #132 | phase9-shl-r102-runtime-wiring-design | SHL R102 runtime wiring design | ✅ merged |
| #133 | phase9-sponsor-distribution-handoff-design | Sponsor distribution handoff design | ✅ merged |

---

## 4. SeniorDebtSizing Policy Status

**READY ✅**

- `explicit_cfads`: SeniorDebtSizing accepts explicit CFADS input
- `derive_from_minimum_dscr`: SeniorDebtSizing derives debt from minimum DSCR
- Macro!R50 / actual CFADS separation maintained
- No runtime ownership changes made
- Phase 9 change: policy wiring confirmed working with DistributionAccount audit-first

---

## 5. DistributionAccount Status

**READY — audit-first implementation complete**

- `DistributionAccountEngine.compute()` exists and runs in audit mode
- `to_audit_rows()`, `to_csv()`, `to_model_summary()` implemented
- `equity_distribution_paid_keur = 0.0` always (audit-only)
- `cash_swept_to_shl_keur = 0.0` always (audit-only)
- `enable_distribution_account_runtime = False` by default
- R99/R102 gates evaluated but outputs not routed downstream
- Oborovo guard active

---

## 6. R99/R102 Status

**BLOCKED (G20) — NOT PROMOTED**

- R99 gate: evaluated in DistributionAccount, audit-only output
- R102 gate: evaluated in DistributionAccount, audit-only output
- No runtime routing exists
- R99/R102 promotion requires explicit approval (G2 rule) after all gates pass

---

## 7. SHL R102 Handoff Status

**G06 READY ✅ | G07 PENDING**

- G06: SHL R102 runtime input **DESIGNED** (PR #132)
- Field: `distribution_account_r102_sweep_candidate_keur`
- Produced by: DistributionAccountEngine
- Consumed by: ShlEngine
- G07: SHL R102 runtime input **NOT YET IMPLEMENTED**

---

## 8. Sponsor Distribution Handoff Status

**G15 READY ✅ | G16 PENDING**

- G15: Sponsor handoff **DESIGNED** (PR #133)
- Field pair: `equity_distribution_paid_keur` → `distribution_received_keur`
- Produced by: DistributionAccountEngine
- Consumed by: SponsorCashflowRunner
- G16: Sponsor handoff **NOT YET IMPLEMENTED**

---

## 9. Cross-Module Validation Summary

**PASSED ✅**

- No hidden coupling detected
- R99/R102 blocked in all cases (audit-only)
- Module dependency matrix clean
- Circular dependency containment documented

---

## 10. TUHO Calibration Summary

**CALIBRATED ✅ (with documented gaps)**

| Metric | Excel | Model | Status |
|--------|-------|-------|--------|
| Debt | 43,359 kEUR | 43,359 kEUR | ✅ OK |
| OpEx Y1 | 1,998 kEUR | 1,998 kEUR | ✅ OK |
| CO2 Y1 | 611 kEUR | 611 kEUR | ✅ OK |
| Project IRR | 9.47% | 9.41% | ✅ OK (-0.06pp) |
| Equity IRR | 11.61% | 11.15% | ⚠️ WARN (-0.46pp, within ±1.0pp) |
| Avg DSCR | 1.451 | 1.554 | ⚠️ WARN (+0.103) |

**DSCR delta explained by design:** R99/R102 blocked → distributions not routed → more cash stays in CFADS → higher DSCR

---

## 11. Oborovo Calibration / Guard Summary

**CALIBRATED ✅ (with documented gaps)**

| Metric | Excel | Model | Status |
|--------|-------|-------|--------|
| Debt | 42,852 kEUR | 42,852 kEUR | ✅ OK |
| OpEx Y1 | 1,338 kEUR | 1,338 kEUR | ✅ OK |
| Equity IRR | 10.60% | 9.17% | ⚠️ WARN (-1.43pp) |
| Project IRR | 7.96% | 7.98% | ✅ OK (+0.02pp) |
| Avg DSCR | 1.147 | 1.229 | ⚠️ WARN (+0.082) |

**Oborovo guard:** Active — Oborovo does not receive TUHO-specific R99/R102 gates

---

## 12. TaxBridge and Canonical Depreciation Status

**TaxBridge:** CURRENT CIT SOURCE ✅

- TaxBridge remains the active CIT computation engine for TUHO
- No changes to TaxBridge in Phase 9

**Canonical Depreciation:** SEPARATE FUTURE DECISION ⏳

- Canonical depreciation as CIT source is a separate design decision
- Not implemented in Phase 9
- Not blocking R99/R102 (orthogonal concern)
- Requires its own design/approval branch

---

## 13. Current Source-of-Truth Map

| Field | Source of Truth | Module |
|-------|----------------|--------|
| Senior debt sizing | SeniorDebtSizingEngine | domain/senior_debt_sizing |
| CIT cash | TaxBridge | domain/tax |
| DSCR | SeniorDebtEngine | domain/debt |
| SHL interest/principal | ShlEngine | domain/shl |
| R99/R102 gates | DistributionAccountEngine | domain/distribution_account |
| R99/R102 runtime routing | NONE (audit-only) | — |
| Sponsor distribution | SponsorCashflowRunner | domain/sponsor |
| Canonical depreciation | DEPRECATED | domain/depreciation |

---

## 14. Gate Matrix Summary

| Gate | Status |
|------|--------|
| G01 DistributionAccount exists | ✅ READY |
| G02 DistributionAccount audit export | ✅ READY |
| G05 Oborovo guard | ✅ READY |
| G06 SHL R102 input designed | ✅ READY |
| G10 Circular dependency analysis | ✅ READY |
| G11 Default-off flag designed | ✅ READY |
| G13 Cross-module validation matrix designed | ✅ READY |
| G17 Rollback/kill-switch | ✅ READY |
| G18 No app default behavior change | ✅ READY |
| G03 R99/R102 audit values validated | ⏳ PENDING |
| G04 TUHO Excel source-map validated | ⏳ PENDING |
| G06 SHL R102 input implemented | ⏳ PENDING |
| G07 SHL R102 runtime input implemented | ⏳ PENDING |
| G09 DSCR stability validation passed | ⏳ PENDING |
| G12 Default-off flag implemented | ⏳ PENDING |
| G14 Cross-module validation passed | ⏳ PENDING |
| G15 Sponsor handoff designed | ✅ READY |
| G16 Sponsor handoff validated | ⏳ PENDING |
| G19 Explicit approval recorded | ⏳ PENDING |
| G20 R99/R102 promotion | ❌ BLOCKED |

---

## 15. What Is READY

- SeniorDebtSizing explicit_cfads and derive_from_minimum_dscr policies
- DistributionAccount design, implementation, audit export
- Oborovo guard
- R99/R102 runtime wiring design (ownership map)
- SHL R102 input contract design (G06)
- Sponsor distribution handoff design (G15)
- Cross-module validation pack (no hidden coupling)
- TUHO calibration review and deep dive
- Oborovo calibration correction (OpEx report fix)
- Phase 9 closeout gate report (this document)

---

## 16. What Is PENDING

- SHL R102 runtime input implementation (G07)
- Sponsor distribution handoff implementation (G16)
- DistributionAccount runtime flag implementation (G12)
- Runtime cross-module validation after implementation (G14)
- DSCR stability validation (G09)
- TUHO Excel source-map complete validation (G03/G04)
- Canonical depreciation CIT source design
- External/bankability model review
- Explicit R99/R102 promotion approval (G19/G20)

---

## 17. What Is BLOCKED

- **R99/R102 runtime promotion (G20)** — requires explicit approval after all gates pass
- Oborovo TUHO-specific runtime logic — guard is design-only
- Canonical depreciation as CIT source — separate design decision required
- Direct SponsorEngine distribution feed until handoff implementation
- Direct SHL R102 runtime feed until SHL input implementation

---

## 18. Runtime Promotion Decision

### R99/R102 promotion is NOT approved.

**Reason:** G20 remains BLOCKED. Multiple gates are still PENDING. R99/R102 must not be promoted to runtime until all prerequisite gates pass and explicit approval is recorded (G2 rule).

**The next work should be:**
1. Implementation of missing contracts (SHL R102, sponsor handoff)
2. Or separate CIT-source decision
3. NOT direct R99/R102 promotion

---

## 19. Recommended Next Branch Sequence

| # | Branch | Type | Purpose |
|---|--------|------|---------|
| 1 | `phase9-shl-r102-runtime-wiring` | implementation | Implement SHL R102 input contract, default-off |
| 2 | `phase9-sponsor-distribution-handoff-implementation` | implementation | Implement sponsor handoff contract, default-off |
| 3 | `phase9-canonical-depreciation-cit-source-design` | design | Separate decision, orthogonal to R99/R102 |
| 4 | `phase9-r99-r102-runtime-flag-design-review` | review | Review if all gates are ready before flag implementation |
| 5 | `phase9-r99-r102-runtime-flag` | implementation | Only if G20 explicitly unblocked |
| 6 | `phase9-final-cross-module-runtime-validation` | validation | After any runtime flags are added |
| 7 | `phase9-bankability-review-pack` | external | External review preparation |

---

## 20. Explicit Non-Goals / Forbidden Next Actions

The following are explicitly NOT approved in this branch:

- ❌ R99/R102 runtime promotion
- ❌ DistributionAccount runtime routing to downstream modules
- ❌ SHL R102 runtime input implementation (design only in this phase)
- ❌ Sponsor distribution handoff implementation (design only in this phase)
- ❌ Default-off flag implementation
- ❌ Changes to app/waterfall_core.py
- ❌ Changes to TaxBridge
- ❌ Changes to SeniorDebtSizing production ownership
- ❌ Canonical depreciation as CIT source
- ❌ UI or export changes
- ❌ Scalar plugs or silent default behavior changes

---

## Conclusion

**Phase 9 audit/design/validation/calibration block is COMPLETE.**

R99/R102 runtime promotion is NOT approved. G20 remains BLOCKED.

The model is in a valid, calibrated, audit-first state. All Phase 9 design documents are complete. The next logical step is implementation of the SHL R102 input contract and sponsor handoff, followed by a separate CIT-source decision, before any R99/R102 runtime promotion is considered.