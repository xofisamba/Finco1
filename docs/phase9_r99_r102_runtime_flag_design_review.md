# Phase 9: R99/R102 Runtime Flag Design Review

**Branch:** `phase9-r99-r102-runtime-flag-design-review`
**Base:** `9646631` (PR #153 — audit/economic mode contract reconciliation)
**Type:** DOCS / DESIGN REVIEW / GATE REVIEW ONLY
**Date:** 2026-05-21

---

## 1. Executive Summary

Phase 9 Phase C is complete. All prerequisite integrations (SHL R102 input, Sponsor handoff, DA runtime wiring, TaxBridge dual-run, audit/runtime mode contract) are implemented and merged to main. This design review assesses whether those integrations provide sufficient foundation for a future R99/R102 runtime flag, and what evidence is still required before implementation.

**Key finding:** Prerequisites are satisfied. G01–G06 are READY. However, G07 (DSCR stability) and G08 (TUHO Excel parity) are PARTIAL. G20 promotion remains BLOCKED. Evidence gates E03 and E10 are the primary blockers for any implementation branch.

**Recommended next step:** `phase9-r99-r102-runtime-flag-readiness-fixes` — address G07 (DSCR stability measurement) and G08 (Excel parity) before `phase9-r99-r102-runtime-flag-implementation`.

---

## 2. Scope and Non-Goals

### Scope of This Branch
- Gate review of all Phase C integrations
- Three-state runtime model documentation
- Evidence inventory (what's ready, what's not)
- Design hypothesis for future R99/R102 runtime flag
- Rollback/kill-switch plan
- Testing requirements for future implementation

### Non-Goals (Forbidden)
- No runtime code changes — this branch is docs/reports/tests only
- No `app/waterfall_core.py` changes
- No `DistributionAccount` behavior changes
- No SHL changes
- No Sponsor changes
- No TaxBridge changes
- No SeniorDebtSizing changes
- No depreciation changes
- **No R99/R102 promotion**
- No default-on flags
- No Oborovo promotion
- No UI changes
- No Excel export changes
- No scalar plugs

---

## 3. Current Three-State Runtime Model

### State 1: Legacy Default
```
flag: use_distributionaccount_runtime_wiring=False
distribution_source: legacy (lockup/dscr governed)
gate_mode: governed (both audit_economic_mode=False, runtime_economic_mode=False)
runtime_routing: none (legacy path)
r99_status: BLOCKED
r102_status: BLOCKED
oborovo_behavior: guard fires (unchanged)
default_state: YES
TUHO total: 326,165 kEUR
```
**Description:** Default behavior. No DA wiring. R99/R102 gates evaluated but blocked by governed mode. TUHO distribution = legacy governed value.

### State 2: DA Runtime-Wired Staging
```
flag: use_distributionaccount_runtime_wiring=True
distribution_source: DA equity_distribution_paid_keur (pass-through alias)
gate_mode: runtime_economic_mode=True
runtime_routing: explicit wiring behind flag=True
r99_status: BLOCKED_GOVERNED (economic evaluation, not promotion)
r102_status: BLOCKED_GOVERNED (economic evaluation, not promotion)
oborovo_behavior: guard fires (blocked)
default_state: NO
TUHO total: 284,552 kEUR (Δ -41,613 kEUR vs legacy)
```
**Description:** Pre-G20 staging. `distribution_keur` becomes pass-through alias of DA's `equity_distribution_paid_keur`. Uses `runtime_economic_mode=True`. 13 lockup periods zeroed. Not G20 promotion.

### State 3: Future G20 Promoted Candidate
```
flag: use_r99_r102_runtime=True (future, not implemented)
distribution_source: DA + R99/R102 combined (future)
gate_mode: governed + economic + runtime (future)
runtime_routing: full promotion to runtime (future)
r99_status: APPROVED (future)
r102_status: APPROVED (future)
oborovo_behavior: guard status TBD (future)
default_state: NO
```
**Description:** Not implemented. Not approved. G20 promotion requires explicit governance approval. Requires G07 (DSCR stability), G08 (Excel parity), SeniorDebtSizing, TaxBridge, and canonical depreciation evidence.

---

## 4. Why DA Runtime Wiring Is Not G20 Promotion

DA runtime wiring (`use_distributionaccount_runtime_wiring=True`) is **pre-G20 staging**, not G20 promotion, because:

| Property | DA Wiring (State 2) | G20 Promotion (State 3) |
|----------|--------------------|------------------------|
| Distribution source | DA equity_distribution_paid only | DA + R99/R102 combined |
| Gate evaluation | cash-based (runtime_economic_mode) | governance-aware |
| R99/R102 status | BLOCKED (gates evaluated, not promoted) | APPROVED |
| Scope | TUHO-only | TBD |
| Default | OFF | N/A |
| Governance | None required | Explicit approval required |
| Oborovo | Guard fires | TBD |

DA wiring wires DA's `equity_distribution_paid_keur` into runtime. It does not promote R99/R102 gates to unconditional approval. R99/R102 remain BLOCKED in the gate evaluation — they are evaluated but their failure does not zero distributions (because DA evaluation already determines distributions).

**Key distinction:** G20 would make R99/R102 gate **pass/fail** the **direct determinant** of distributions. DA wiring uses DA's cash-based evaluation as the pass-through source. R99/R102 gates are evaluated but their outcome is captured in DA's `equity_distribution_paid` (they gate whether DA passes distributions, not whether R99/R102 directly approve).

---

## 5. audit_economic_mode vs runtime_economic_mode Boundary

| Mode | Field | Purpose | Routing |
|------|-------|---------|---------|
| `audit_economic_mode` | `DistributionAccountPeriodInput` | Audit/dual-run comparison only | **Never** routed to runtime |
| `runtime_economic_mode` | `DistributionAccountPeriodInput` | Explicit runtime staging for DA wiring | Allowed behind `use_distributionaccount_runtime_wiring=True` |

**Contract (from PR #153):**
- `audit_economic_mode=True` → gates evaluated for comparison; output **never flows to runtime**
- `runtime_economic_mode=True` → gates evaluated for staging; output **explicitly allowed** to flow to runtime via DA wiring

**Dual-run:** Uses `audit_economic_mode=True` in `economic_periods` — comparison trace only, never routed.
**DA wiring:** Uses `runtime_economic_mode=True` in `_apply_distributionaccount_runtime_wiring` — staging, explicitly allowed.

---

## 6. Current Gate Status

From `reports/phase9_phasec_gate_refresh.csv` (PR #152):

| Gate | Name | Status |
|------|------|--------|
| G01 | SHL R102 input wiring | ✅ READY |
| G02 | Sponsor distribution handoff | ✅ READY |
| G03 | DA runtime wiring | ✅ READY |
| G04 | TaxBridge dual-run reconciliation | ✅ READY |
| G05 | DA dual-run economic gate eval | ✅ READY |
| G06 | Phase C combo validation | ✅ READY |
| G07 | R99/R102 final promotion approval | 🔴 BLOCKED (DSCR stability not measured) |
| G08 | G20 Oborovo promotion | 🔴 BLOCKED |

From `reports/phase9_r99_r102_runtime_flag_gate_review.csv`:

| Gate | Name | Status | Notes |
|------|------|--------|-------|
| G01 | SHL R102 input | ✅ READY | PR #136 merged |
| G02 | Sponsor handoff | ✅ READY | PR #137 merged |
| G03 | DA runtime wiring | ✅ READY | PR #151 merged |
| G04 | TaxBridge dual-run | ✅ READY | PR #150 merged |
| G05 | Phase C combo validation | ✅ READY | PR #152 merged |
| G06 | Mode contract reconciled | ✅ READY | PR #153 merged |
| G07 | DSCR stability | ⚠️ PARTIAL | Full DSCR time-series comparison needed |
| G08 | TUHO Excel parity | ⚠️ PARTIAL | Equity IRR OK; project IRR + DSCR need work |
| G09 | Oborovo guard | ✅ READY | Guard active |
| G10 | R99/R102 final approval | 🔴 BLOCKED | Awaiting G07+G08 |
| G20 | G20 promotion | 🔴 BLOCKED | Not implemented, not approved |
| G21 | Canonical depreciation CIT | ⚠️ PARTIAL | PARTIAL |

---

## 7. R99 Gate Promotion Requirements

R99 gate (equity distribution gate) promotion requires:

1. **DSCR stability evidence (G07):** DSCR must be ≥ 1.0 for all periods under both flag=False and flag=True configurations. Variation between configurations must be < 0.1.

2. **Excel parity (G08):** TUHO equity IRR must be within ±1.0pp of Excel reference (11.61%). Project IRR within ±0.5pp. Avg DSCR within ±0.05.

3. **SeniorDebtSizing validation:** SeniorDebtSizing engine must be validated in combination with DA wiring.

4. **Explicit governance approval:** R99 promotion must be explicitly approved by governance body.

**Current status:** G07 and G08 are PARTIAL. Implementation branch requires these gates to be READY.

---

## 8. R102 Gate Promotion Requirements

R102 gate (SHL sweep gate) promotion requires:

1. **SHL R102 input wiring (G01):** `distribution_account_r102_sweep_candidate_keur` field must be implemented and validated. ✅ READY (PR #136 merged).

2. **SHL sweep stability:** SHL sweep under DA wiring must not cause DSCR < 1.0 or senior debt service disruption.

3. **SeniorDebtSizing dependency (G10/G20):** SeniorDebtSizing must be wired and validated before R102 can be considered for promotion.

4. **Explicit governance approval:** R102 promotion requires separate governance approval.

**Current status:** G01 READY. G10/G20 BLOCKED.

---

## 9. DSCR Stability Requirements

DSCR stability is the **primary blocker** for R99/R102 runtime flag implementation.

**Requirement:** For all periods under both `flag=False` (legacy) and `flag=True` (DA wiring) configurations:
- DSCR ≥ 1.0 for every period
- DSCR variation between configurations < 0.1
- No DSCR cliff events under either configuration

**Evidence needed (E03):** Full DSCR time-series comparison. Currently **PARTIAL** (gate G07).

**Action required:** Measure DSCR across full tenor (360 months for TUHO). Run TUHO with flag=True vs flag=False. Compare DSCR time-series. Document any periods where DSCR < 1.0 or variation > 0.1.

---

## 10. SeniorDebtSizing Dependency

SeniorDebtSizing engine is **not yet validated** in combination with DA runtime wiring.

**Current status:** PARTIAL

SeniorDebtSizing must be:
1. Wired to `run_waterfall_v3_core` (currently exists as `use_senior_debt_sizing_engine` flag)
2. Validated in combination with `use_distributionaccount_runtime_wiring=True`
3. Confirmed not to conflict with DA gate evaluation
4. Documented for G20 promotion evidence

**Impact on distribution boundary:** SeniorDebtSizing affects the senior debt service schedule, which affects `cf_after_tax - senior_ds`, which affects DA's cash available. Not yet validated as compatible with DA wiring.

---

## 11. SHL R102 Dependency

SHL R102 sweep is **independent** of DA wiring. `distribution_account_r102_sweep_candidate_keur` is wired from ShlEngine output and is not affected by `_apply_distributionaccount_runtime_wiring`.

**Evidence (E05):** SHL R102 input implemented (PR #136 merged). SHL sweep logic unchanged by DA wiring. E05 PASS.

**For R102 promotion:** SHL sweep behavior must be validated under both legacy and DA wiring configurations.

---

## 12. Sponsor Handoff Dependency

Sponsor handoff (`distribution_account_received_by_period`) is **independent** of DA wiring. SponsorEngine does not recompute R99/R102 gates.

**Evidence (E04, E08):** Sponsor cashflow consistency with DA paid amounts needs validation. No hidden dual ownership confirmed. E08 PASS.

**For Sponsor promotion:** Sponsor cashflow must be validated in combination with DA wiring enabled (`use_distributionaccount_runtime_wiring=True`).

---

## 13. TaxBridge / Depreciation Boundary

**TaxBridge (G04):** TaxBridge dual-run cash-source reconciliation is complete. PR #150 merged. TaxBridge is independent of DA wiring.

**Depreciation (G21):** Canonical depreciation CIT source separation is **PARTIAL**. Depreciation CIT bridge exists in `domain/financial_statements/tax_bridge.py` but full canonical implementation and evidence is not yet complete.

**For G20 promotion:** Depreciation CIT source must be canonical (separate from operational CIT) before G20 promotion is considered. G21 PARTIAL.

---

## 14. Oborovo Guard and Exclusion

**Oborovo guard is ACTIVE and must remain.**

In `_apply_distributionaccount_runtime_wiring`:
```python
if not is_tuho:
    result.distribution_source = "oborovo_guard_blocked"
    result.da_paid_distribution_keur = 0.0
    result.legacy_distribution_keur = result.total_distribution_keur
    result.distribution_wiring_delta_keur = 0.0
    # ... per-period guard fields set ...
    return  # early return — distribution unchanged
```

**Oborovo behavior under DA wiring:**
- `distribution_source = "oborovo_guard_blocked"`
- `distribution_keur` unchanged from legacy
- `distribution_wiring_delta_keur = 0.0`
- TUHO-only by design

**For any future R99/R102 flag:** Oborovo guard must be preserved. R99/R102 promotion does not include Oborovo.

---

## 15. Required Evidence Before Implementation

See `reports/phase9_r99_r102_runtime_flag_required_evidence.csv`.

| Evidence | ID | Status | Threshold |
|----------|-----|--------|-----------|
| Default-off zero drift | E01 | ✅ AVAILABLE | Δ < 1 kEUR |
| TUHO DA-runtime delta | E02 | ✅ AVAILABLE | Δ ≈ -41,613 kEUR |
| DSCR stability | E03 | ⚠️ PARTIAL (G07) | DSCR ≥ 1.0, variation < 0.1 |
| Sponsor cashflow consistency | E04 | ⚠️ NOT_STARTED (G20) | Sponsor ≡ DA paid |
| SHL R102 unaffected | E05 | ✅ AVAILABLE | Unchanged |
| TaxBridge combination | E06 | ✅ AVAILABLE | Reconciled |
| Oborovo guard | E07 | ✅ AVAILABLE | Guard fires |
| No hidden dual ownership | E08 | ✅ AVAILABLE | Mutual exclusivity |
| Rollback behavior | E09 | ✅ AVAILABLE | flag=False = legacy |
| Excel parity | E10 | ⚠️ PARTIAL (G08) | Equity IRR ±1.0pp, DSCR ±0.05 |
| R99 gate activation | E11 | ✅ AVAILABLE | Activates correctly |
| R102 gate activation | E12 | ✅ AVAILABLE | Activates correctly |
| audit mode never routed | E13 | ✅ AVAILABLE | Contract respected |
| runtime mode documented | E14 | ✅ AVAILABLE | Staging-only |
| SeniorDebtSizing mapped | E15 | ⚠️ PARTIAL | Validated |

**Primary blockers:** E03 (DSCR stability) and E10 (Excel parity).

---

## 16. Runtime Flag Proposal

### Design Hypothesis

**Flag:** `use_r99_r102_runtime: bool = False`

**Semantics:**
- Default-off (`False`)
- When `True` AND `runtime_economic_mode=True`: R99/R102 gates can increase distributions above governed floor
- Falls back to governed behavior if gates fail (not zero)
- TUHO-only (Oborovo guard applies)
- Still not G20 promotion

**Key distinction from G20:**
- G20 = unconditional replacement of governed distribution with R99/R102 gates as primary determinant
- This design = conditional increase, not replacement; falls back to governed floor

### Interaction with DA Wiring

Two options:
1. **Standalone:** `use_r99_r102_runtime` independent of `use_distributionaccount_runtime_wiring`
2. **Combined:** `use_distributionaccount_runtime_wiring` already provides DA wiring; add `include_r99_r102_in_wiring` sub-flag

**Recommended:** Option 2 (extend existing DA wiring flag) — `use_distributionaccount_runtime_wiring=True` enables DA wiring; R99/R102 influence is added on top within the same flag context.

---

## 17. Rollback / Kill-Switch Plan

**Primary kill-switch:** `use_distributionaccount_runtime_wiring=False` (or any future flag set to `False`)

**Behavior when flag=False:**
- Bit-identical to legacy behavior
- No changes to distribution logic
- R99/R102 gates remain BLOCKED (governed mode)
- TUHO total: 326,165 kEUR

**Rollback procedure:**
1. Set `use_distributionaccount_runtime_wiring=False`
2. Run full test suite (all Phase 9 tests must pass)
3. Verify TUHO total = 326,165 kEUR
4. Verify Oborovo unchanged

**No runtime state persistence:** DA engine is stateless per-run. No accumulated state to roll back.

---

## 18. Testing Requirements for Future Implementation Branch

Any `phase9-r99-r102-runtime-flag-implementation` branch must include:

1. **Zero-drift tests:** `flag=False` ≡ legacy for all projects (TUHO + Oborovo)
2. **DA wiring tests:** `flag=True` TUHO = 284,552 kEUR ± 1 kEUR
3. **DSCR stability test:** DSCR ≥ 1.0 for all periods under both configurations
4. **Oborovo guard test:** `flag=True` Oborovo unchanged (guard fires)
5. **R99/R102 gate activation test:** gates activate with `runtime_economic_mode=True`
6. **Fallback test:** if gates fail, governed behavior is used (not zero)
7. **Audit mode test:** `audit_economic_mode=True` never routes to runtime
8. **Sponsor test:** sponsor cashflow consistent with DA paid
9. **SHL test:** SHL R102 sweep unchanged with DA wiring
10. **TaxBridge test:** TaxBridge + DA wiring combination stable

---

## 19. Explicit Blockers

The following **block** any `phase9-r99-r102-runtime-flag-implementation` branch:

| Blocker | Gate | Evidence | Required Action |
|---------|------|----------|----------------|
| DSCR stability not measured | G07 | E03 PARTIAL | Full DSCR time-series measurement |
| TUHO Excel parity not complete | G08 | E10 PARTIAL | Project IRR + Avg DSCR calibration |
| SeniorDebtSizing not validated | — | E15 PARTIAL | SeniorDebtSizing + DA wiring combination |
| G20 not approved | G20 | — | Explicit governance approval |
| Oborovo promotion | G08/G20 | — | Oborovo remains excluded |

---

## 20. Recommended Next Branch

### If DSCR stability and Excel parity gates are NOT ready (current state):
→ **`phase9-r99-r102-runtime-flag-readiness-fixes`**

Focus:
- G07: Full DSCR time-series measurement under DA wiring vs legacy
- G08: Complete TUHO Excel parity (project IRR, avg DSCR)
- E15: SeniorDebtSizing + DA wiring validation

### If all gates are READY:
→ **`phase9-r99-r102-runtime-flag-implementation`**

Focus:
- Implement `use_r99_r102_runtime: bool = False` in `run_waterfall_v3_core()`
- Wire R99/R102 gate outcome into distribution logic
- Preserve fallback to governed behavior if gates fail
- Preserve Oborovo guard
- Full test suite
- PR for review

---

## Required Conclusions (Stated Explicitly)

- **R99/R102 runtime promotion is NOT approved.** G10 and G20 are BLOCKED.
- **G20 remains BLOCKED.** Not implemented. Not approved. Requires explicit governance.
- **`use_distributionaccount_runtime_wiring=True` is pre-G20 staging, not promotion.** DA wiring wires DA's `equity_distribution_paid` to runtime. R99/R102 gates are evaluated but not promoted.
- **Future runtime flag implementation must not start unless this design review says gates are ready.** G07 and G08 are the primary readiness gates.
- **Oborovo remains excluded.** Guard is active and must remain.
- **Canonical depreciation CIT source remains separate.** G21 is PARTIAL. Must be complete before G20 promotion.

---

## Reports in This Branch

| File | Description |
|------|-------------|
| `reports/phase9_r99_r102_runtime_flag_gate_review.csv` | 13-gate review (G01–G21) |
| `reports/phase9_r99_r102_runtime_flag_state_matrix.csv` | 4-state matrix |
| `reports/phase9_r99_r102_runtime_flag_required_evidence.csv` | 15 evidence items |
| `docs/phase9_r99_r102_runtime_flag_design_review.md` | This document |