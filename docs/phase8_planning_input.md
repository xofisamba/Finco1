# Phase 8 — Planning Input

> **Status:** PLANNING INPUT ONLY — NOT APPROVED  
> **Phase 8 must not begin without explicit user approval**  
> **Prerequisite: Oborovo DSCR gap must be fixed first**

---

## 1. Phase 7 Outcome

Phase 7 delivered:
- 3 canonical engines (SHL, SeniorDebtSizing, Depreciation) — all audit-only
- 12 runtime flags, all default `False`
- ~163 tests passing
- R99/R102 BLOCKED
- Freeze complete

Phase 7 did NOT wire any canonical engine to runtime. All canonical engines remain audit-only.

---

## 2. Phase 8 Prerequisites

### 2.1 Oborovo DSCR Gap (Blocking)

**Issue:** Model DSCR = 0.848 vs Excel 1.147 (gap = -0.299)

**Root cause:** OpEx duplication in B.01 and B.02 aggregates
- B.01 Technical Management: model 280 vs Excel 198 (+82)
- B.02 Infrastructure Maintenance: model 667 vs Excel 244 (+423)
- B.12 Environmental&Social: model 200 vs Excel 32 (+168)

**Impact:** Oborovo fixture cannot validate Phase 8 canonical promotions until this is fixed.

**This must be resolved before Phase 8 begins.**

### 2.2 TUHO CO2 Calibration

**Status:** ✅ CALIBRATED (PR #101/103)
- CO2 enabled: `co2_enabled=True`, `co2_price=4.191 EUR/MWh`
- Y1 CO2 revenue: 611 kEUR
- Equity IRR with CO2: 11.81% vs Excel 11.61% ✅ (within ±1.0pp)

---

## 3. Phase 8 Scope (Proposed)

### 3.1 Mandatory First Step: Oborovo OpEx Fix

**Branch:** `phase8-oborovo-opex-fix`

**Goal:** Fix Oborovo DSCR gap before Phase 8 canonical promotion begins.

**Changes:**
- Remove sub-item double-counting in OpEx aggregates (B.01, B.02, B.12)
- Update Oborovo fixture with corrected values
- Confirm DSCR within ±0.05 of Excel 1.147

**Tests:** Existing Oborovo fixture + DSCR validation

**Risk:** LOW — isolated OpEx fix, no waterfall logic changes

### 3.2 Optional: SHL Canonical Wiring

**Branch:** `phase8-shl-canonical-wiring`

**Goal:** Wire `ShlEngine.compute()` output to `DistributionAccount` when `use_shl_canonical_engine=True`

**Changes:**
- `app/waterfall_core.py`: Connect `ShlEngine.compute()` → `cash_for_distribution_keur`
- Add validation: canonical vs legacy within tolerance (e.g., ±1.0 kEUR)
- Update TUHO + Oborovo fixtures

**Risk:** MEDIUM — first canonical-to-runtime wiring, requires full fixture validation

**Approval required:** YES — explicit user sign-off

### 3.3 Optional: Depreciation Canonical Wiring

**Branch:** `phase8-depreciation-canonical-wiring`

**Goal:** Wire `DepreciationEngine.compute()` output to `TaxEngine` when `use_canonical_tax_depreciation_bridge=True`

**Changes:**
- `app/waterfall_core.py` or tax path: Connect `tax_depreciation_by_period_keur` → `compute_period_tax()`
- Add validation: canonical vs legacy tax depreciation within tolerance
- Update TUHO + Oborovo fixtures

**Risk:** MEDIUM — depreciation-to-tax wiring, requires tax fixture validation

**Approval required:** YES — explicit user sign-off

### 3.4 Optional: SeniorDebtSizing Wiring

**Branch:** `phase8-senior-debt-sizing-wiring`

**Goal:** Wire `SeniorDebtSizingEngine.compute()` output to runtime waterfall sizing when `use_senior_debt_sizing=True`

**Changes:**
- `app/waterfall_core.py`: Connect sizing diagnostics to runtime
- Validate: sized debt vs runtime within tolerance
- Update TUHO + Oborovo fixtures

**Risk:** MEDIUM — sizing-to-waterfall wiring, requires sizing fixture validation

**Approval required:** YES — explicit user sign-off

### 3.5 Optional: R99/R102 Gate (Only After Prerequisites)

**Branch:** `phase8-r99-runtime-gate`

**Goal:** Promote R99 gate to runtime source (after all 6 gates satisfied)

**Prerequisites:**
1. Gate logic decoupled from audit-only path
2. `use_r99_runtime_gate: bool = False` flag added
3. SHL re-wired to receive R102
4. DSCR gate ownership separated from SeniorDebtSizing
5. TUHO fixture with gate-on validated
6. Oborovo fixture with gate equivalent validated

**Changes:**
- `DistributionAccount`: Refactor to expose gate result
- `app/waterfall_core.py`: Wire gate result to runtime
- Add TUHO + Oborovo fixtures

**Risk:** HIGH — first distribution gate promotion, requires full fixture suite

**Approval required:** YES — explicit user sign-off + design PR review

---

## 4. Phase 8 Non-Goals (Forbidden)

The following are explicitly NOT in Phase 8 scope:

- ❌ Deferred tax implementation
- ❌ HoldCo tax implementation
- ❌ DistributionAccount broad rewrite
- ❌ TaxEngine rewrite
- ❌ app/waterfall_core.py broad refactor
- ❌ UI changes
- ❌ Excel export changes
- ❌ R99/R102 promotion without all 6 gates satisfied
- ❌ Any canonical promotion without explicit user approval

---

## 5. Phase 8 Testing Requirements

For each canonical promotion, the following tests are required:

| Test | Scope |
|------|-------|
| TUHO fixture regression | Equity IRR ±1.0pp, Project IRR ±0.5pp, DSCR ±0.05, Debt ±1% |
| Oborovo fixture regression | Same tolerances |
| Sponsor IRR regression | No regression vs flag=False |
| DSCR regression | No regression vs flag=False |
| Distribution regression | Total distributions ±5% |
| All existing tests pass | 0 regressions |

**No canonical promotion may merge without full fixture validation.**

---

## 6. Go / No-Go Gates

Each Phase 8 canonical promotion requires:

| Gate | Oborovo OpEx Fix | SHL Wiring | Depreciation Wiring | Senior Sizing | R99 Gate |
|------|-----------------|------------|--------------------|---------------|----------|
| Oborovo DSCR fixed | ✅ REQUIRED | ✅ | ✅ | ✅ | ✅ |
| TUHO fixture regression | — | ✅ | ✅ | ✅ | ✅ |
| Oborovo fixture regression | ✅ | ✅ | ✅ | ✅ | ✅ |
| Sponsor IRR no regression | — | ✅ | ✅ | ✅ | ✅ |
| DSCR no regression | ✅ | ✅ | ✅ | ✅ | ✅ |
| All existing tests pass | ✅ | ✅ | ✅ | ✅ | ✅ |
| Explicit user approval | ❌ | ✅ | ✅ | ✅ | ✅ |
| Design PR reviewed | ❌ | ✅ | ✅ | ✅ | ✅ |

**Gate status: ALL RED** — Phase 8 has not been approved.

---

## 7. Recommended Sequence

```
Phase 8.0: Oborovo OpEx Fix (MANDATORY before Phase 8.1)
     ↓
Phase 8.1: SHL Canonical Wiring (if approved)
     ↓
Phase 8.2: Depreciation Canonical Wiring (if approved)
     ↓
Phase 8.3: Senior Debt Sizing Wiring (if approved)
     ↓
Phase 8.4: R99/R102 Gate (only after 8.1–8.3 complete)
```

**Each sub-phase requires explicit user approval before the next begins.**

---

## 8. Open Questions for User

1. **Approve Phase 8.0?** Should Oborovo OpEx fix begin now?
2. **Approve Phase 8.1?** Should SHL canonical wiring proceed after 8.0?
3. **Approve Phase 8.2?** Should Depreciation canonical wiring proceed after 8.1?
4. **Approve Phase 8.3?** Should SeniorDebtSizing wiring proceed after 8.2?
5. **Scope of R99/R102?** Is R99 gate promotion a Phase 8 goal or Phase 9?
6. **Pause option?** Should all Phase 8 work be deferred pending review?

**Phase 8 must not begin without explicit answers to questions 1–3 minimum.**

---

## 9. What Happens If Phase 8 Is Not Approved

If Phase 8 is not approved or is deferred:

- Phase 7 canonical engines remain frozen as audit-only
- No runtime promotion work begins
- All 15 PRs (#97–#111) remain the stable Phase 7 foundation
- R99/R102 remains BLOCKED
- TUHO and Oborovo fixtures remain the calibration reference
- No changes to runtime behavior

**This is a valid outcome.** Phase 7 is a complete, stable foundation regardless of whether Phase 8 is pursued.

---

*This document is planning input only. Phase 8 has not been approved.*