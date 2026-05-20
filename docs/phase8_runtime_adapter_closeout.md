# Phase 8: Runtime Adapter Closeout

**Branch:** `phase8-runtime-adapter-closeout-freeze`
**Base:** `main` (PR #120 merge, SHA `4257f84`)
**Date:** 2026-05-20
**Type:** DOCS / FREEZE / GOVERNANCE ONLY
**R99/R102:** BLOCKED

---

## 1. Executive Summary

Phase 8 runtime adapter migration wave (PRs #114–#120) is **formally closed and frozen**.
This document is the authoritative record of what was built, what is deferred,
what is blocked, and what governance rules apply before any future promotion.

**Status:** R99/R102 remains BLOCKED. DistributionAccount remains audit-only.
Canonical runtime adapters are stable and cross-module validation is clean.
No runtime ownership promotion was performed.

**Governance conclusion:** Phase 8 delivered the foundation for future runtime
promotion. The actual promotion work (DistributionAccount, R99/R102 runtime wiring,
Macro!R50 wiring) requires explicit future approval and cross-module validation.

---

## 2. Scope of Phase 8 Runtime Adapter Migration

Phase 8 spanned the design, wiring, hardening, and documentation of the canonical
runtime adapter stack. It covers three canonical modules and one TUHO-specific bridge:

| Module | What it does | Status |
|--------|-------------|--------|
| SHL canonical wiring | Overrides SHL-specific fields as post-processing adapter | ✅ Stable |
| Depreciation canonical wiring | Overrides `depreciation_keur` + `tax_depreciation_audit_keur` as post-processing | ✅ Stable |
| SeniorDebtSizing canonical wiring | Attaches `_canonical_senior_debt_sizing` as audit/diagnostic only | ✅ Stable |
| TaxBridge | TUHO CIT cash tax override; TUHO-only | ✅ Stable |
| R99/R102 | Audit fields only; BLOCKED | 🔴 BLOCKED |
| DistributionAccount | Audit stub only; no runtime routing | 🔴 BLOCKED |

---

## 3. Completed PR Inventory (#114–#120)

| PR | Branch | Title | Type |
|----|--------|-------|------|
| #114 | `phase8-depreciation-canonical-wiring` | Depreciation canonical wiring | Runtime wiring |
| #115 | `phase8-shl-hardening-validation` | SHL hardening validation | Validation |
| #116 | `phase8-cross-module-runtime-validation` | Cross-module runtime validation | Validation |
| #117 | `phase8-cross-module-runtime-validation` (docs) | Cross-module docs/CSV/scripts | Documentation |
| #118 | `phase8-senior-debt-sizing-runtime-wiring` | Senior Debt Sizing canonical wiring | Runtime wiring |
| #119 | `phase8-runtime-adapter-doc-clarification` | Adapter semantics clarification | Documentation |
| #120 | `phase8-r99-r102-prepromotion-design` | R99/R102 pre-promotion design | Design |

**All PRs:** Zero runtime regressions. R99/R102 BLOCKED throughout.

---

## 4. Runtime-Capable Canonical Modules

A canonical module is "runtime-capable" if it can affect actual cash flows when
its flag is enabled. The following are runtime-capable in the **post-processing**
sense — they run after the waterfall completes and override specific fields:

| Module | Flag | What changes when enabled | Ownership |
|--------|------|--------------------------|-----------|
| SHL canonical | `use_shl_canonical_engine` | SHL-specific fields: `total_shl_balance_keur`, `_canonical_shl_wiring` | `domain/shl/canonical_wiring.py` |
| Depreciation canonical | `use_depreciation_canonical_engine` | `depreciation_keur`, `tax_depreciation_audit_keur` (audit fields only — not CIT source) | `domain/depreciation/canonical_wiring.py` |
| TaxBridge | `use_tax_bridge_engine` | CIT cash tax for TUHO; TUHO-only | `domain/tax/tuho_tax_bridge_runtime.py` |
| SeniorDebtSizing | `use_senior_debt_sizing_engine` | Audit/diagnostic only — `_canonical_senior_debt_sizing` attached | `domain/senior_debt_sizing/canonical_wiring.py` |

**Note:** "Runtime-capable" means the flag exists and the module can be wired.
It does not mean the module currently overrides production cash flows. For
SeniorDebtSizing specifically, the current wiring is audit-only.

---

## 5. Audit-Only Canonical Modules

These modules exist in the codebase but are not yet wired as runtime overrides:

| Module | Current state | Future potential |
|--------|--------------|-----------------|
| `use_senior_debt_sizing_engine` | Audit/diagnostic output only | Future: override `fixed_debt_keur` |
| `use_canonical_tax_depreciation_bridge` | Flag exists in `ProjectInfo` but not connected to `waterfall_core` | Future: canonical depreciation as CIT source |
| DistributionAccount | Audit stub (`engine.py` computes R99/R102 as audit fields) | Future: runtime cash routing |

---

## 6. Runtime Ownership Boundaries

Each canonical adapter owns a defined field slice and must not cross into
another module's territory:

| Module | Fields Owned | Must Not Touch |
|--------|-------------|----------------|
| SHL canonical | SHL-specific fields | Senior debt, tax, distributions |
| Depreciation canonical | `depreciation_keur`, `tax_depreciation_audit_keur` | CIT (TaxBridge owns), distributions |
| TaxBridge | CIT cash tax | SHL, depreciation audit, distributions |
| SeniorDebtSizing | `_canonical_senior_debt_sizing` (audit) | Senior debt runtime (not wired) |
| R99/R102 | Audit fields only | Nothing — BLOCKED |
| DistributionAccount | Audit stub only | Nothing — BLOCKED |

**Boundary enforcement:** Each canonical adapter writes only its own field slice.
Cross-boundary writes are forbidden by design.

---

## 7. Current Runtime Source-of-Truth Map

For each waterfall output field, which module is the source of truth?

| Field | Source of truth | Module |
|-------|----------------|--------|
| Senior debt sculpt | `run_waterfall()` → `closed_form_sculpt()` | `domain/waterfall/waterfall_engine.py` |
| SHL balance/PIK | Legacy SHL path (default) / SHL canonical (flag) | `domain/shl/` |
| Depreciation | Legacy CapexItem path (default) / Dep canonical (flag) | `domain/depreciation/` |
| Tax depreciation (CIT) | TaxBridge fixture ledger | `domain/tax/tuho_tax_bridge_runtime.py` |
| Cash tax | TaxBridge fixture ledger | `domain/tax/tuho_tax_bridge_runtime.py` |
| Equity distributions | Not yet implemented | — BLOCKED — |
| SHL sweep | Legacy waterfall | `domain/waterfall/waterfall_engine.py` |
| R99 audit | `domain/distribution_account/engine` | Audit only |
| R102 audit | `domain/distribution_account/engine` | Audit only |
| Sizing CFADS | Proxy: `ebitda × (1 − tax)` | Legacy waterfall |

**Canonical depreciation is NOT the CIT source.** TaxBridge owns the CIT computation
and uses its own independent fixture ledger.

---

## 8. Flag Inventory and Semantics

| Flag | Default | TUHO | Oborovo | Effect |
|------|---------|-----|--------|--------|
| `use_shl_canonical_engine` | False | ✅ | ✅ | SHL-specific fields → post-processing override |
| `use_depreciation_canonical_engine` | False | ✅ | ✅ | `depreciation_keur`, `tax_depreciation_audit_keur` → audit only (NOT CIT source) |
| `use_tax_bridge_engine` | False | ✅ Only | ❌ Blocked | CIT cash tax from TUHO fixture |
| `use_senior_debt_sizing_engine` | False | ✅ | ✅ | Audit only — `_canonical_senior_debt_sizing` attached |
| `use_senior_sculpting_basis_engine` | False | ✅ | ✅ | Senior sculpting config |
| `use_senior_rate_schedule_engine` | False | ✅ | ✅ | Rate schedule from engine |
| `use_canonical_tax_depreciation_bridge` | False | ❌ Not wired | ❌ Not wired | Flag exists, not connected |

---

## 9. Cross-Module Validation Summary

**Result: CLEAN** — PR #116 validation matrix (10 combinations, 6 TUHO + 4 Oborovo):

| Property | Max Drift | Threshold | Status |
|----------|----------|-----------|--------|
| Senior debt | 0.00 kEUR | ±1 kEUR | ✅ PASS |
| Equity IRR | 0.000 pp | ±0.01 pp | ✅ PASS |
| Project IRR | 0.000 pp | ±0.01 pp | ✅ PASS |
| Distributions | 0.00 kEUR | ±1 kEUR | ✅ PASS |
| R99/R102 | BLOCKED | — | ✅ BLOCKED |

**No hidden coupling** detected between:
- SHL canonical ↔ Depreciation canonical
- Depreciation canonical ↔ TaxBridge
- SHL canonical ↔ TaxBridge
- Any flag ↔ Senior debt sizing

---

## 10. R99/R102 BLOCKED Status

R99 and R102 are **audit-only fields** (`WaterfallPeriod.r99_fcf_for_distribution_keur`
and `r102_fcf_for_shl_keur`). They are computed by `domain/distribution_account/engine`
but are not wired into any downstream cash router.

**R99/R102 remains BLOCKED.** See `docs/phase8_r99_r102_prepromotion_design.md` for:
- Exact definition of R99 and R102
- Ownership before and after promotion
- 20-gate prerequisite matrix (G01–G08: BLOCKERS; G09–G10: FUTURE_WORK; G11–G20: READY)
- DistributionAccount as prerequisite for any promotion

**Key blocker:** There is no `DistributionAccount` class that routes post-debt-service
FCF to equity distributions, SHL sweep, and DSRA top-up. R99/R102 promotion
requires this class to exist first.

---

## 11. DistributionAccount Current State

`domain/distribution_account/` contains:
- `engine.py` — `compute_tuho_r99_input_period()`: computes R99/R102 audit values
- `result.py` — `R99InputResult` dataclass
- `__init__.py` — public exports

This is an **audit stub only**. There is no `DistributionAccount` class,
no runtime cash routing, and no equity distribution output.

**What would be needed for promotion:**
1. New `DistributionAccount` class that receives post-DS FCF (R84 + R98)
2. Cash routing: equity distributions → SHL sweep → DSRA top-up → residual
3. Wiring into `app/waterfall_core.py`
4. DSCR stability validation (±0.05 threshold)
5. Circular dependency analysis (distributions → DSCR → debt sizing → FCF)

**DistributionAccount implementation requires explicit approval and a dedicated branch.**

---

## 12. Known Limitations

| Limitation | Impact | Workaround |
|-----------|--------|-----------|
| `use_senior_debt_sizing_engine` is audit-only | Cannot override senior debt sizing yet | Use `fixed_debt_keur` directly if needed |
| Sizing CFADS is proxy (ebitda × (1 − tax)) | Not the true Macro!R50 hardcoded Excel basis | Wire Macro!R50 in future branch before using as calibration reference |
| Canonical depreciation is not CIT source | Cannot use per-asset-class depreciation for CIT | TaxBridge fixture ledger is the CIT source |
| R99/R102 are audit-only | Equity distributions not routed | Requires DistributionAccount class (future) |
| TaxBridge is TUHO-only | Oborovo cannot use CIT cash tax override | Oborovo uses legacy waterfall tax path |
| `use_canonical_tax_depreciation_bridge` not wired | Flag exists but has no runtime effect | Not yet connected to `waterfall_core` |
| `dscr_schedule` display shows `inf` in validation | Display artifact in extraction logic | Actual DSCR drift: 0.00 |

---

## 13. Deferred Work

| Item | Owner module | Blocking items | Priority |
|------|-------------|---------------|----------|
| Macro!R50 explicit sizing CFADS wiring | `domain/senior_debt_sizing/` | FinancingParams extension | High |
| DistributionAccount class | `domain/distribution_account/` | R99/R102 promotion prerequisite | High |
| R99/R102 runtime wiring | `domain/distribution_account/` + `domain/shl/` | DistributionAccount class | High |
| Canonical depreciation as CIT source | `domain/depreciation/` + `domain/tax/` | TaxBridge fixture ledger replacement | Medium |
| SHL sweep receives R102 as runtime input | `domain/shl/` | DistributionAccount class | Medium |
| `use_canonical_tax_depreciation_bridge` wiring | `app/waterfall_core.py` | CIT source decision | Low |
| DSCR dual-target (PPA/Merchant) | `domain/waterfall/` | Already in FinancingParams | Low |
| Circular dependency containment | `domain/waterfall/` | R99/R102 promotion | Low |

---

## 14. Promotion Blockers

### Immediate blockers (must be resolved before any promotion)

| Blocker | Description | Module |
|---------|-------------|--------|
| No DistributionAccount class | Runtime cash routing has no home | `domain/distribution_account/` |
| No SHL sweep runtime input | R102 is not wired to SHL sweep mechanism | `domain/shl/` |
| No DSCR stability validation | Distributions change DSCR denominator — impact unknown | `app/waterfall_core.py` |
| No circular dependency analysis | R99/R102 → DSCR → debt sizing → FCF loop | `domain/waterfall/` |
| No Oborovo guard for R99/R102 | R99/R102 is TUHO-specific; Oborovo must be blocked | `app/waterfall_core.py` |

### Future prerequisites

| Item | Notes |
|------|-------|
| Canonical depreciation as CIT source | Orthogonal to R99/R102 but required before TaxBridge replacement |
| Macro!R50 wiring | Required before SeniorDebtSizing becomes calibration reference |

---

## 15. Governance Rules Before Future Runtime Promotion

> **These rules are binding for all future branches until explicitly changed.**

### G1: No R99/R102 runtime promotion without DistributionAccount implementation
R99/R102 promotion requires a `DistributionAccount` class that routes cash to
equity, SHL, and DSRA. No exceptions.

### G2: No DistributionAccount implementation without explicit approval
The `DistributionAccount` class requires a dedicated design branch and explicit
approval before implementation. No ad-hoc promotion.

### G3: No runtime ownership changes without cross-module validation
Any change to source-of-truth ownership (e.g., canonical depreciation → CIT source)
must run the cross-module validation matrix and pass all gates before merge.

### G4: Macro!R50 wiring is required before SeniorDebtSizing becomes calibration source
The current `use_senior_debt_sizing_engine=True` wiring is **audit-only**. Before
SeniorDebtSizing can be used as a calibration/reference source, Macro!R50 explicit
sizing CFADS must be wired into `FinancingParams.sizing_cfads_keur_by_period`.

### G5: Canonical depreciation as CIT source is orthogonal to R99/R102
Making canonical depreciation the CIT source is a separate design decision from
R99/R102 promotion. Each requires its own prerequisites, validation, and approval.

### G6: Oborovo must be blocked for any TUHO-specific flag
Any TUHO-specific flag (TaxBridge, R99/R102) must have an explicit Oborovo guard
in `waterfall_core.py` similar to the existing `use_tax_bridge_engine` guard.

### G7: All canonical adapters must maintain field-slice ownership
Canonical adapters must not write outside their owned field slice. Any cross-boundary
write requires a design document and explicit review.

### G8: R99/R102 remains BLOCKED
No promotion of R99/R102 to runtime without fulfilling all prerequisites in the
gate matrix (G01–G08: all blockers resolved) and explicit approval.

---

## 16. Recommended Phase 9 Starting Point

**Recommended first Phase 9 branch:** `phase9-macro-r50-sizing-cfads-wiring`

Rationale: Macro!R50 wiring is an independent, high-value enabling step that does
not affect existing runtime behavior (validation-only wiring). It makes
`SeniorDebtSizing` a true calibration reference for debt sizing, which is a
prerequisite for using it as a production reference source.

**Alternative starting point (if DistributionAccount design is preferred):**
`phase9-distribution-account-design`

Rationale: DistributionAccount is the most fundamental blocker for R99/R102
promotion. Starting here unlocks the entire distribution routing path.

**Not recommended as Phase 9 start:** R99/R102 runtime wiring — DistributionAccount
is a hard prerequisite.

---

## Appendix A: Module Inventory (CSV source)

See `reports/phase8_runtime_adapter_inventory.csv`.

## Appendix B: R99/R102 Gate Matrix Reference

See `reports/phase8_r99_r102_prepromotion_gate_matrix.csv`.

## Appendix C: Key Documents

| Document | PR | What it covers |
|----------|----|---------------|
| `phase8_shl_canonical_runtime_wiring.md` | #113 | SHL canonical wiring |
| `phase8_depreciation_canonical_wiring_hardening_validation.md` | #114 | Depreciation canonical + TaxBridge interaction |
| `phase8_cross_module_runtime_validation.md` | #116/#117 | Cross-module validation matrix |
| `phase8_senior_debt_sizing_runtime_wiring.md` | #118 | SeniorDebtSizing wiring + proxy CFADS limitation |
| `phase8_r99_r102_prepromotion_design.md` | #120 | R99/R102 design + gate matrix |

---

## Document History

| Date | Change |
|------|--------|
| 2026-05-20 | Initial closeout — phase8-runtime-adapter-closeout-freeze |