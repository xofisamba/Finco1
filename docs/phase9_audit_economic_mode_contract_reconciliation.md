# Phase 9: Audit/Economic Mode Contract Reconciliation

**PR:** `phase9-audit-economic-mode-contract-reconciliation`
**Type:** GOVERNANCE / SEMANTIC FIX
**Base:** `dc03e50` (PR #152 — Phase C post-runtime validation)

---

## Problem: Architectural Contradiction

`domain/distribution_account/gates.py` documents `audit_economic_mode` as:
- "comparison/audit only"
- "output cannot be routed to runtime"
- "must never flow to runtime"

But `app/waterfall_core.py` `_apply_distributionaccount_runtime_wiring` used:
```python
DistributionAccountPeriodInput(
    ...
    audit_economic_mode=True,  # Economic mode: gates evaluated for distribution
)
# then:
# wp.distribution_keur = da_paid
```

This routes an **audit-only** result into **runtime** `distribution_keur` — contradicting the gate contract.

---

## Solution: Two Distinct Modes

Introduce a second mode, `runtime_economic_mode`, to explicitly distinguish:

### `audit_economic_mode` (existing)
- **Purpose:** Audit / dual-run comparison only
- **Routing:** Must **never** flow to runtime `distribution_keur`
- **Used by:** Dual-run validation (`economic_periods.append(...)`)
- **Default:** `False`
- **Governance:** Comparison-only; never promotion

### `runtime_economic_mode` (new)
- **Purpose:** Explicit runtime staging for DA wiring
- **Routing:** **Allowed** behind `use_distributionaccount_runtime_wiring=True`
- **Used by:** `_apply_distributionaccount_runtime_wiring` only
- **Default:** `False`
- **Governance:** Pre-G20 staging mode; **still NOT G20 promotion**

### Gate activation logic (updated)
```python
gate_active = audit_economic_mode or runtime_economic_mode
if not gate_active:
    # Governed mode: R99/R102 always BLOCKED
    return DistributionGateResult(passed=False, blocked_reason=BLOCKED_REASONS["R99_BLOCKED"])
```

Dual-run uses `audit_economic_mode=True` → comparison only, never routed.
DA wiring uses `runtime_economic_mode=True` → explicit staging, allowed by contract.

---

## Why `runtime_economic_mode` Is NOT G20 Promotion

| Property | G20 Promotion | `runtime_economic_mode` |
|----------|--------------|------------------------|
| Governance | Unconditional approval | Pre-G20 staging |
| R99/R102 | Full promotion to runtime | Economic evaluation only |
| Scope | Whole model | DA wiring only (flag=True) |
| Default | N/A | `False` (default-off) |
| TUHO-only | N/A | ✅ Yes |
| Oborovo guard | N/A | ✅ Still fires |

`runtime_economic_mode` evaluates gates using cash logic — same evaluation as `audit_economic_mode`. The distinction is only in **who is allowed to route the result**:

- `audit_economic_mode` → comparison output, **never routed**
- `runtime_economic_mode` → staging output, **explicitly allowed** by DA wiring contract

---

## Changes Made

### 1. `domain/distribution_account/inputs.py`
Added `runtime_economic_mode: bool = False` to `DistributionAccountPeriodInput`:
```python
audit_economic_mode: bool = False  # audit-only: bypass R99/R102 governance for economic comparison
runtime_economic_mode: bool = False  # Phase 9C-fix: runtime staging (DA wiring), not G20 promotion
```

### 2. `domain/distribution_account/gates.py`
Added `runtime_economic_mode: bool = False` parameter to `evaluate_r99_gate` and `evaluate_r102_gate`. Updated docstrings to clarify both modes and that `runtime_economic_mode` is pre-G20 staging.

### 3. `domain/distribution_account/engine.py`
Passes `runtime_economic_mode=inp.runtime_economic_mode` to gate evaluations (alongside `audit_economic_mode`).

### 4. `app/waterfall_core.py`
- `_apply_distributionaccount_runtime_wiring`: changed `audit_economic_mode=True` → `runtime_economic_mode=True`
- Dual-run `economic_periods`: unchanged — still uses `audit_economic_mode=True`
- `governed_periods`: unchanged — still uses `audit_economic_mode=False`

---

## Oborovo Guard

Unchanged. Oborovo project detection happens before any mode selection:
```python
if not is_tuho:
    result.distribution_source = "oborovo_guard_blocked"
    # distribution_keur unchanged
    return
```

---

## Default-Off Behavior

| Flag combination | Result |
|-----------------|--------|
| `use_distributionaccount_runtime_wiring=False` | Legacy `distribution_keur`, unchanged ✅ |
| `use_distributionaccount_runtime_wiring=True` + TUHO | DA wiring via `runtime_economic_mode=True` |
| `use_distributionaccount_runtime_wiring=True` + Oborovo | Guard fires, unchanged ✅ |

---

## Test Results

**Tests:** `tests/test_phase9_audit_economic_mode_contract_reconciliation.py`
**Result:** 25 passed ✅

| Category | Tests | Status |
|----------|-------|--------|
| Audit mode not routed | 4 | ✅ |
| Runtime mode explicit | 3 | ✅ |
| Dual-run uses audit mode | 1 | ✅ |
| Default behavior unchanged | 3 | ✅ |
| TUHO flag=True unchanged | 3 | ✅ |
| Oborovo guard unchanged | 3 | ✅ |
| R99/R102 BLOCKED | 3 | ✅ |
| SHL/Sponsor unchanged | 2 | ✅ |
| Contract docs | 3 | ✅ |

---

## TUHO DA Wiring Validation

| Metric | Value |
|--------|-------|
| TUHO baseline (`flag=False`) | 326,165 kEUR |
| TUHO DA wiring (`flag=True`) | 284,552 kEUR |
| Delta | -41,613 kEUR |
| R99/R102 status | BLOCKED |

---

## Next Branch

`phase9-r99-r102-runtime-flag-design-review`

R99/R102 governance still needs explicit runtime flag design before any promotion can be considered.

---

## Forbidden Scope (Respected)

- ❌ No R99/R102 promotion
- ❌ No G20 approval
- ❌ No default-on behavior
- ❌ No Oborovo runtime promotion
- ❌ No SHL R102 changes
- ❌ No SponsorEngine changes
- ❌ No SeniorDebtSizing changes
- ❌ No TaxBridge rewrite
- ❌ No depreciation CIT source change
- ❌ No UI changes
- ❌ No Excel export expansion
- ❌ No scalar plugs