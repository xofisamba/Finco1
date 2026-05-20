# Phase 9: SHL R102 Runtime Wiring Design

**Branch:** `phase9-shl-r102-runtime-wiring-design`  
**Base:** `805e4b579ebb85822aad194129f53c57d25ab61b` (PR #131)  
**Date:** 2026-05-20  
**Type:** DOCS / DESIGN / GATE REVIEW ONLY — no runtime code

## 1. Executive Summary

This design defines the contract by which `DistributionAccount` passes R102 cash sweep capacity to `ShlEngine` as an explicit runtime input, without recomputing SHL interest/principal and without ShlEngine recomputing R99/R102 gates.

**Key Decision:**  
- Field name: `distribution_account_r102_sweep_candidate_keur`  
- Consumed by: `ShlEngine` as optional explicit input  
- Produced by: `DistributionAccountEngine.compute()`  
- When `enable_distribution_account_runtime=False`: ShlEngine receives 0.0 and computes R102 internally  
- When `enable_distribution_account_runtime=True`: ShlEngine validates provided value and uses it instead of internal R102 computation

**R99/R102 remains BLOCKED (G20).** This design enables future promotion gates G06/G07.

## 2. Current Status and Why R102 Input Contract Is Needed

### Phase 9 Context
- DistributionAccount audit-first module implemented (PR #124)
- R99/R102 gates evaluated but outputs are audit-only (equity_distribution_paid=0, cash_swept_to_shl=0)
- R99/R102 promotion blocked by G8 rule until all gates pass

### Why This Contract Is Needed
- ShlEngine currently computes R102 sweep internally (cash interest → PIK → principal)
- DistributionAccount also computes R102 as audit candidate (r102_fcf_for_shl_keur)
- If both compute independently, they may disagree → inconsistency risk
- The contract defines explicit handoff so ShlEngine can use DistributionAccount's candidate instead of internal computation

### Gate Status
| Gate | Description | Status |
|------|-------------|--------|
| G06 | SHL R102 runtime input designed | READY (this doc) |
| G07 | SHL R102 runtime input implemented | BLOCKED (future branch) |
| G20 | R99/R102 promotion allowed | BLOCKED |

## 3. Existing SHL Source-Map Summary

From `reports/phase7_tuho_shl_cash_sweep_extraction.csv` and `domain/shl/`:

| Metric | Value | Source |
|--------|-------|--------|
| SHL gross accrued interest | ~53,351 kEUR | TUHO Excel SHL sheet |
| Cash interest paid | ~38,755 kEUR | TUHO Excel SHL sheet |
| PIK capitalized | ~14,596 kEUR | TUHO Excel SHL sheet |
| Principal repaid | ~43,731 kEUR | TUHO Excel SHL sheet |
| Total debt service incl. WHT | ~82,486 kEUR | TUHO Excel SHL sheet |

**R102 sweep logic in ShlEngine:**  
Post-SHL cash is applied: first to cash interest, then to PIK, then to principal reduction.

**Oborovo SHL:** SHL sweep does not apply to Oborovo (Oborovo guard active).

## 4. DistributionAccount Ownership

**What DistributionAccount OWNS:**
- R99 gate evaluation (equity_distribution_candidate_keur)
- R102 gate evaluation (r102_fcf_for_shl_keur)
- Cash routing eligibility (equity_distribution_paid_keur, cash_swept_to_shl_keur)
- All gates: R99, R102, DSCR, lockup, Oborovo, cash sufficiency

**What DistributionAccount MUST NOT compute:**
- SHL interest (cash or PIK)
- SHL principal balance
- SHL closing balance
- Any SHL internal state

**Output fields from DistributionAccount:**
```python
@dataclass
class DistributionAccountPeriodResult:
    period_index: int
    r99_gate_result: DistributionGateResult     # BLOCKED or PASSED
    r102_gate_result: DistributionGateResult    # BLOCKED or PASSED
    equity_distribution_candidate_keur: float  # audit candidate
    r102_fcf_for_shl_keur: float               # audit candidate
    equity_distribution_paid_keur: float      # 0 (audit-only)
    cash_swept_to_shl_keur: float              # 0 (audit-only)
    ...
```

**Runtime wiring flag (future):** `enable_distribution_account_runtime: bool = False`  
When True: DistributionAccount passes explicit outputs downstream.

## 5. ShlEngine Ownership

**What ShlEngine OWNS:**
- SHL gross accrued interest calculation
- SHL cash interest vs PIK split
- SHL principal balance and repayment
- SHL closing balance
- WHT on SHL interest
- SHL sweep policy (cash interest → PIK → principal)

**What ShlEngine MUST NOT recompute:**
- R99 gates
- R102 gates
- DistributionAccount eligibility

**Current R102 computation in ShlEngine:**
- Post-senior cash → post-DSRA cash
- R102 sweep = max(0, post_dsra - r102_threshold)
- Routed to cash interest first, then PIK, then principal

**Proposed new input:**
```python
@dataclass
class ShlEngineInputs:
    # ... existing fields ...
    
    # R102 sweep from DistributionAccount
    distribution_account_r102_sweep_candidate_keur: float | None = None
```

## 6. Proposed R102 Input Contract

### Field: `distribution_account_r102_sweep_candidate_keur`

| Property | Value |
|----------|-------|
| Producing module | DistributionAccountEngine |
| Consuming module | ShlEngine |
| Unit | kEUR |
| Type | `float \| None` (None = not provided, use internal) |
| Default | `None` |
| Timing | Computed in same pass as ShlEngine; passed as explicit input |

### Contract Behavior

**When `distribution_account_r102_sweep_candidate_keur = None`:**  
ShlEngine uses internal R102 computation (existing behavior). No change to runtime.

**When `distribution_account_r102_sweep_candidate_keur = X (X >= 0)`:**
1. ShlEngine compares X against internal R102 computation
2. If `abs(X - internal_r102) <= tolerance`: use X
3. If `abs(X - internal_r102) > tolerance`: log warning, use X (provided value takes precedence)
4. Apply X to sweep: cash interest first, then PIK, then principal

**Tolerance:** 0.01 kEUR (essentially exact match for display purposes)

### Cash Routing Order in ShlEngine

```
1. post_senior_cash available
2. DSRA rules applied
3. [NEW] distribution_account_r102_sweep_candidate_keur applied
   → first to cash interest (up to interest due)
   → then to PIK (up to PIK accrued)
   → then to principal reduction
4. ShlEngine closing balance computed
```

## 7. Field Definitions and Units

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `distribution_account_r102_sweep_candidate_keur` | `float \| None` | kEUR | R102 candidate from DistributionAccount; None = use internal |
| `r102_fcf_for_shl_keur` (audit) | `float` | kEUR | R102 candidate computed in DistributionAccount audit |
| `cash_swept_to_shl_keur` (audit) | `float` | kEUR | Always 0 in audit-only mode |
| `shl_gross_accrued_interest_keur` | `float` | kEUR | SHL accumulated interest (cash + PIK) |
| `shl_cash_interest_paid_keur` | `float` | kEUR | Cash interest portion |
| `shl_pik_capitalized_keur` | `float` | kEUR | PIK portion capitalized |
| `shl_principal_repaid_keur` | `float` | kEUR | Principal reduction |

## 8. Cash Routing Order

```
SeniorDebtEngine
    └── post_senior_cash
            └── DistributionAccountEngine (audit)
                    ├── r99_fcf_for_distribution_keur (blocked → 0)
                    └── r102_fcf_for_shl_keur (blocked → 0)
                            │
                            ├── [if enabled] → ShlEngine
                            │         ├── cash interest
                            │         ├── PIK
                            │         └── principal reduction
                            │
                            └── [always] → audit output only
```

## 9. Blocked/Default-Off Behavior

**Default behavior (audit-only, current):**
- `distribution_account_r102_sweep_candidate_keur = None`
- ShlEngine computes R102 internally
- No external cash enters ShlEngine from DistributionAccount

**What happens when R102 is blocked in DistributionAccount:**
- R102 gate returns BLOCKED
- `r102_fcf_for_shl_keur` is computed as audit value but not routed
- ShlEngine receives `None` → uses internal R102 computation
- No runtime cash moves from DistributionAccount to ShlEngine

## 10. Future Runtime Behavior

When `enable_distribution_account_runtime=True` (future flag):

1. DistributionAccountEngine evaluates R102 gate
2. If PASSED: produces `r102_fcf_for_shl_keur` as explicit output
3. This value is passed to ShlEngine as `distribution_account_r102_sweep_candidate_keur`
4. ShlEngine validates against internal computation and applies
5. Sponsor distributions receive residual after SHL handling

**Dependency order:**  
`SeniorDebtSizing → TaxBridge → DistributionAccount → ShlEngine → SponsorEngine`

## 11. Circular Dependency Containment

**No circular dependency exists in this contract.**

| Dependency | Risk | Containment |
|------------|------|-------------|
| R102 → SHL interest | None | DistributionAccount does not compute SHL interest |
| SHL → CFADS → R102 | None | ShlEngine output does not feed back into DistributionAccount input |
| DistributionAccount → DSCR | None | DistributionAccount reads DSCR as INPUT only |

**Rules:**
- DistributionAccount does NOT recompute SHL interest/principal
- ShlEngine does NOT recompute R99/R102 gates
- ShlEngine receives R102 as EXPLICIT INPUT only (not as computed value)
- No iterative solving required — one-pass acyclic dependency

## 12. Oborovo Guard Policy

When `is_oborovo=True` in DistributionAccount:
- Oborovo guard blocks TUHO-specific gates (R99/R102)
- R102 candidate is NOT computed for Oborovo
- ShlEngine receives `None` for Oborovo (uses internal R102 computation or zero)
- Oborovo SHL behavior is unchanged — Oborovo does not inherit TUHO R102 assumptions

**Implementation:**
- `ShlEngineInputs.is_oborovo` flag already exists
- Oborovo projects use internal SHL computation, not DistributionAccount input

## 13. Validation Requirements

| Check | Method | Gate |
|-------|--------|------|
| R102 candidate matches internal within tolerance | Compare `distribution_account_r102_sweep_candidate_keur` vs internal R102 | G07 |
| Oborovo correctly receives None | Check Oborovo guard in DistributionAccount | G05 |
| Kill-switch works | `enable_distribution_account_runtime=False` → None passed | G12 |
| SHL closing balance stable | Compare with/without external R102 input | G14 |
| No circular dependency | Architecture review | G10 |

## 14. Gate Matrix Update

| Gate | Description | Previous | Current |
|------|-------------|----------|---------|
| G06 | SHL R102 runtime input designed | PENDING | **READY** (this design) |
| G07 | SHL R102 runtime input implemented | PENDING | PENDING (future branch) |
| G10 | Circular dependency analysis | READY | READY |
| G11 | Default-off flag designed | READY | READY |
| G12 | Default-off flag implemented | PENDING | PENDING |
| G14 | Cross-module validation passed | PENDING | PENDING |
| G20 | R99/R102 promotion allowed | BLOCKED | BLOCKED |

## 15. Forbidden Scope

- No `domain/shl/engine.py` implementation changes
- No `domain/distribution_account/engine.py` runtime changes
- No `app/waterfall_core.py` changes
- No R99/R102 promotion
- No default-off runtime flag implementation
- No SponsorEngine changes
- No TaxBridge changes
- No SeniorDebtSizing changes
- No canonical depreciation CIT source changes
- No UI or export changes

## 16. Recommended Next Branch

**`phase9-sponsor-distribution-handoff-design`**  
After SHL R102 design is merged, design the sponsor equity distribution handoff (R99 → SponsorEngine contract).

**Recommended implementation sequence:**
1. `phase9-shl-r102-runtime-wiring-design` ✅ (this branch)
2. `phase9-sponsor-distribution-handoff-design`
3. `phase9-shl-r102-runtime-wiring` (implementation)
4. `phase9-sponsor-distribution-handoff` (implementation)
5. `phase9-distribution-account-runtime-wiring` (enable flag + full wiring)
6. Cross-module validation pack
7. Explicit approval (G2) → R99/R102 promotion