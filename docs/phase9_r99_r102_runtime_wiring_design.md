# Phase 9: R99/R102 Runtime Wiring Design

**Branch:** `phase9-r99-r102-runtime-wiring-design`
**Base:** `main` (PR #126 merge, SHA `0cf425e`)
**Date:** 2026-05-20
**Type:** DESIGN / GATE REVIEW — NO RUNTIME CHANGES
**R99/R102:** BLOCKED — design documents future promotion path only

---

## Executive Summary

- **R99/R102 is currently BLOCKED** — computed as audit-only fields in `DistributionAccountEngine`
- **DistributionAccount** exists as audit-first module (PR #123–#126) with audit export (`to_audit_rows`, `to_csv`, `to_model_summary`)
- **This design** defines the future runtime wiring path for R99/R102 outputs to downstream consumers (SponsorEngine, ShlEngine, DsraEngine)
- **R99/R102 remains BLOCKED** — this document is design-only, no runtime changes are made
- **TUHO only** — Oborovo guard is in place; R99/R102 runtime routing blocked for Oborovo

---

## 1. Current Status: R99/R102 Audit-Only and BLOCKED

### 1.1 Audit-Only Fields

`r99_fcf_for_distribution_keur` and `r102_fcf_for_shl_keur` are computed by `DistributionAccountEngine` in every period and written to `WaterfallPeriod` attributes as **audit values only**. No downstream consumer exists in the runtime waterfall.

```
Current runtime state:
  SeniorDebtEngine → post_senior_cash → WaterfallEngine → r99_fcf_for_distribution_keur (audit only)
                                                            r102_fcf_for_shl_keur (audit only)
                                                            No downstream consumer
```

### 1.2 G8 Rule: R99/R102 BLOCKED Until All Promotion Gates Pass

Per G8 governance rule: R99/R102 must not be promoted to runtime until all prerequisite gates pass. This design is the prerequisite evidence that the promotion path is defined.

### 1.3 Phase 9 DistributionAccount Audit-First Work

PRs delivered in Phase 9:

| PR | Content | Status |
|----|---------|--------|
| #123 | `DistributionAccountEngine` skeleton + gate evaluation | merged |
| #124 | Full `DistributionAccountEngine` implementation | merged |
| #125 | Review fixes: `senior_tenor_years` field, Oborovo guard, safety hardening | merged |
| #126 | Audit export: `to_audit_rows()`, `to_csv()`, `to_model_summary()` | merged |

**Key invariant (audit-only mode):**
```python
equity_distribution_paid_keur = 0.0   # always zero in audit mode
cash_swept_to_shl_keur = 0.0          # always zero in audit mode
```

These fields become non-zero only when `enable_distribution_account_runtime=True` and all gates pass.

---

## 2. What Changed in Phase 9 — DistributionAccount Audit-First

The Phase 9 work established the canonical `DistributionAccountEngine` module:

```
domain/distribution_account/
├── __init__.py      # canonical exports
├── inputs.py        # DistributionAccountInputs, DistributionAccountPeriodInput, R99R102GateInputs
├── result.py        # DistributionAccountResult, DistributionAccountPeriodResult, DistributionGateResult, BLOCKED_REASONS
├── engine.py        # DistributionAccountEngine.compute() + _compute_period()
├── gates.py         # evaluate_r99_gate, evaluate_r102_gate, evaluate_dscr_gate, evaluate_lockup_gate, evaluate_oborovo_guard, evaluate_cash_gate
└── audit.py         # DistributionAuditRow, audit export utilities
```

The engine computes:
- `equity_distribution_candidate_keur` — max possible distribution (before gate evaluation)
- `equity_distribution_paid_keur` — actual paid (0.0 in audit mode; future: non-zero when promoted)
- `cash_swept_to_shl_keur` — actual SHL sweep (0.0 in audit mode; future: non-zero when promoted)
- `cash_retained_keur` — cash retained in distribution account
- `closing_distribution_account_balance_keur` — period-end balance
- `blocked_reasons` — list of active block reasons (empty list when gates pass)

**Audit export available:**
- `to_audit_rows()` — produces `DistributionAuditRow` tuples for all periods
- `to_csv()` — writes audit rows to CSV file
- `to_model_summary()` — produces dict summary of total flows

---

## 3. Proposed Future Runtime Ownership Map

### Before Promotion (Current — Audit Only)

```
SeniorDebtEngine → post_senior_cash → WaterfallEngine
                                            ├── r99_fcf_for_distribution_keur (audit only)
                                            ├── r102_fcf_for_shl_keur (audit only)
                                            └── No downstream consumer
```

### After Promotion (Future)

```
SeniorDebtEngine → post_senior_cash → DistributionAccountEngine.compute()
                                          │
                                          ├── equity_distribution → SponsorEngine (R99)
                                          ├── R102 cash sweep → ShlEngine (R102 as explicit input)
                                          ├── DSRA top-up → DsraEngine
                                          └── closing_balance → DistributionAccountBalance
```

**Key principle:** `r99_fcf_for_distribution_keur` and `r102_fcf_for_shl_keur` are the **source candidates** computed by DistributionAccountEngine. When promoted, these values are **explicitly routed** to the downstream consumers — not read indirectly.

---

## 4. Field-by-Field Ownership Before and After Promotion

| Field | Before (Audit) | After (Runtime) | Owner |
|-------|---------------|-----------------|-------|
| `r99_fcf_for_distribution_keur` | audit only | **runtime output** | DistributionAccountEngine |
| `r102_fcf_for_shl_keur` | audit only | **runtime output** | DistributionAccountEngine |
| `equity_distribution_paid_keur` | always 0.0 | **runtime output** | DistributionAccountEngine → SponsorEngine |
| `cash_swept_to_shl_keur` | always 0.0 | **runtime output** | DistributionAccountEngine → ShlEngine |
| `cash_retained_keur` | retained | retained | DistributionAccountEngine |
| `closing_distribution_account_balance_keur` | computed | computed | DistributionAccountEngine |
| SHL principal repayment | ShlEngine | ShlEngine | unchanged |
| SHL cash interest paid | ShlEngine | ShlEngine | unchanged |
| Senior debt service | SeniorDebtEngine | SeniorDebtEngine | unchanged |
| Actual DSCR | SeniorDebtEngine | SeniorDebtEngine | unchanged |
| Target DSCR | SeniorDebtDSCRPolicy | SeniorDebtDSCRPolicy | unchanged |
| TaxBridge cash tax | TaxBridge | TaxBridge | unchanged |
| Sponsor distribution cashflow | SponsorEngine | SponsorEngine | receives from DistributionAccount |

---

## 5. Proposed Runtime Wiring Location

**Recommended location:** `domain/distribution_account/engine.py` — new method `DistributionAccountEngine.route_runtime_outputs()`

Alternative consideration: `domain/waterfall/waterfall_engine.py` if there is an existing waterfall adapter pattern for routing outputs to multiple consumers.

**NOT recommended:** `app/waterfall_core.py` — too broad; waterfall core orchestrates, it should not own distribution routing logic.

**Design pattern:** Use existing adapter pattern where `DistributionAccountEngine` produces a result containing routing instructions, and the result is consumed by the appropriate downstream engines via explicit input parameters.

---

## 6. DistributionAccount Runtime Responsibility

### Inputs Received (Read-Only)
- `post_senior_cash_keur` — cash after senior debt service
- `post_shl_cash_keur` — cash after SHL sweep (may differ from post_senior if SHL is active)
- Senior debt service amounts (for DSCR gate)
- Actual DSCR (computed before DistributionAccount)
- DSRA state (current balance, required balance)
- Project flags: `is_tuho`, `is_oborovo`, `senior_tenor_years`

### Outputs Produced (Runtime Mode)
- `equity_distribution_paid_keur` — routed to SponsorEngine (when gates pass and flag enabled)
- `cash_swept_to_shl_keur` — routed to ShlEngine as explicit R102 input (when gates pass and flag enabled)
- `cash_retained_keur` — retained in distribution account
- `closing_distribution_account_balance_keur` — period-end balance
- `blocked_reasons` — gate failure reasons (empty when promoted)

### Does NOT Compute
- Senior debt service amounts
- SHL interest or principal
- Tax cash flows (CIT)
- Depreciation schedules
- DSCR — reads DSCR as input, does not recompute

---

## 7. SHL Handoff and R102 Sweep Responsibility

### R102 as Explicit Runtime Input

`DistributionAccountEngine` produces `r102_fcf_for_shl_keur` as a candidate value.

**When promoted:**
1. `DistributionAccountEngine` emits `cash_swept_to_shl_keur` (which equals `r102_fcf_for_shl_keur` when gate passes)
2. This amount is passed to `ShlEngine` as an **explicit input parameter** — NOT read from a shared attribute
3. `ShlEngine` uses the provided R102 sweep amount to reduce SHL principal balance
4. `ShlEngine` does NOT recompute R102 from scratch — uses provided value

### Oborovo Guard for R102
- `is_oborovo=True` blocks R102 sweep routing
- R102 must not apply to Oborovo (TUHO-specific gate)

### SHL Sweep Ordering
1. DistributionAccount computes R102 candidate
2. If R102 gate passes and `enable_distribution_account_runtime=True`: sweep occurs
3. SHL principal balance is reduced by sweep amount
4. Next period's SHL interest is computed on reduced balance

---

## 8. Equity Distribution and Sponsor Handoff Responsibility

### R99 as Explicit Runtime Input

`DistributionAccountEngine` produces `r99_fcf_for_distribution_keur` as a candidate value.

**When promoted:**
1. `DistributionAccountEngine` emits `equity_distribution_paid_keur` (which equals R99 when gate passes)
2. This amount is passed to `SponsorEngine` as an **explicit input parameter**
3. `SponsorEngine` records the equity distribution cashflow
4. `SponsorEngine` does NOT recompute R99 from scratch — uses provided value

### Sponsor Distribution Timing
- Distributions occur at period end, after SHL sweep
- Sponsor receives: `equity_distribution_paid_keur` as explicit input
- Sponsor balance schedule updated accordingly

---

## 9. SeniorDebtSizing / DSCR Dependency Analysis

### Dependency Chain

```
SeniorDebtSizing → computes sizing_cfads → target DSCR → debt capacity
                         ↓
                   TaxBridge → corporate tax cash
                         ↓
                   DistributionAccount → receives post-senior cash
                         ↓
                   DSCR gate uses: actual_dscr = CFADS / senior_debt_service
                         ↓
                   If DSCR gate fails → distribution blocked
```

### DSCR Used by DistributionAccount

DistributionAccount **reads** `actual_dscr` as an input — it does NOT recompute DSCR. DSCR is computed by SeniorDebtEngine from:
- `actual_cfads_keur` — from waterfall runtime
- `senior_debt_service_keur` — from SeniorDebtEngine

### DSCR Stability Analysis

**Risk:** Adding distributions changes the cash available in the waterfall, which changes CFADS, which changes actual_dscr, which affects the DSCR gate — creating a potential loop.

**Containment:** DistributionAccount DSCR gate uses DSCR computed **before** distributions are added to the cashflow. The gate evaluates whether the period is eligible for distribution based on current-period DSCR, not post-distribution DSCR.

**Stability threshold:** ±0.05 — if enabling distributions causes DSCR to drift more than ±0.05 from the baseline, the distribution is blocked.

### Validation Required
- DSCR stability must be validated with a full model run before promotion
- Document in separate DSCR stability validation report

---

## 10. TaxBridge / Depreciation / CIT Boundary

### TaxBridge Independence

- TaxBridge computes corporate income tax (CIT) cash independently of DistributionAccount
- DistributionAccount does NOT recompute TaxBridge outputs
- TaxBridge cash tax flows **remain unchanged** during and after R99/R102 promotion

### Depreciation Orthogonality

- Canonical depreciation is a post-processing audit field (per Phase 8 canonical wiring)
- Depreciation affects CIT computation as input to TaxBridge
- Depreciation does NOT affect DistributionAccount cash routing
- Canonical depreciation and TaxBridge depreciation are independent (Phase 8 confirmed)

---

## 11. Circular Dependency Analysis and Containment Plan

### Known Risks

**Risk 1: R99 → DSCR → debt sizing → FCF → R99 loop**
- R99 gate depends on DSCR
- DSCR depends on senior debt service
- Senior debt service depends on cashflows
- Cashflows may depend on distributions (if sponsor cash is reinvested)
- Reinvested sponsor cash could increase CFADS, improving DSCR, enabling R99
- This is a **potential** loop, not a **confirmed** loop

**Risk 2: SHL sweep ↔ DistributionAccount**
- R102 (SHL sweep) affects cash available for distributions
- But distributions do not affect SHL sweep amount
- This is **not circular** — SHL sweep is upstream of distributions

**Risk 3: DSCR gate self-reference**
- DistributionAccount DSCR gate uses `actual_dscr`
- `actual_dscr` is computed from senior debt service and CFADS
- DistributionAccount outputs do NOT feed back into DSCR computation within the same period
- This is **not circular** — DSCR is computed before distribution decision

### Containment Rules

1. **DistributionAccount must NOT recompute DSCR, senior debt, SHL interest, or tax** — reads only
2. **SeniorDebtSizing must be computed BEFORE DistributionAccount runtime** — ordering enforced
3. **SHL receives sweep cash as EXPLICIT INPUT** — never reads from DistributionAccount directly
4. **SponsorEngine receives distributions as EXPLICIT INPUT** — never reads from DistributionAccount directly
5. **R99/R102 gate evaluation is PURE FUNCTION of inputs** — no side effects
6. **Iterative solving (if required)** — documented as FUTURE_WORK

### Circular Dependency Monitoring

If iterative convergence is required (DSCR gate triggers distribution which changes DSCR), the following applies:
- Document as separate analysis in Phase 9 DSCR stability validation
- May require iterative waterfall passes
- If >3 iterations required, block promotion pending resolution

---

## 12. Oborovo Guard Policy

### Oborovo Exclusion

- Oborovo does NOT have TUHO-specific R99/R102 rows in its source model
- R99/R102 are **TUHO-specific gates**
- `is_oborovo=True` blocks all TUHO-specific gates in DistributionAccount

### Implementation

```python
# In DistributionAccountEngine._compute_period():
if inputs.is_oborovo:
    return DistributionAccountPeriodResult(
        equity_distribution_paid_keur=0.0,
        cash_swept_to_shl_keur=0.0,
        blocked_reasons=[BLOCKED_REASONS.OBOROVO_NOT_SUPPORTED],
        ...
    )
```

### Guard Coverage

- R99 gate: BLOCKED for Oborovo
- R102 gate: BLOCKED for Oborovo
- DSCR gate: available (DSCR is not TUHO-specific)
- Lockup gate: available (lockup is not TUHO-specific)
- Oborovo can still use: DSCR-based distribution, lockup-based distribution

### Runtime Routing Blocked for Oborovo

R99/R102 runtime routing must NOT be enabled for Oborovo unless a separate source-mapping exercise validates R99/R102 behavior for Oborovo's model structure.

---

## 13. Required Default-Off Flag Strategy

### Proposed Flag

```python
enable_distribution_account_runtime: bool = False
```

### Design Specifications

1. **Default:** `False` — audit mode only unless explicitly enabled
2. **TUHO only initially:** check `is_tuho=True` before enabling
3. **Oborovo blocked:** `is_oborovo=True` blocks regardless of flag value
4. **Audit output remains:** `to_audit_rows()` available even when `False`
5. **Location:** `DistributionAccountInputs` dataclass

### Prerequisites for Enabling

The flag cannot be set to `True` without:

1. Cross-module validation matrix pass (Section 15)
2. Explicit approval (G2 governance rule)
3. DSCR stability validation passed (G05, G09)
4. TUHO Excel source-map validated (G04)
5. Circular dependency analysis complete (G10)
6. SHL runtime input implemented (G07)
7. Sponsor cashflow handoff validated (G16)

### Kill-Switch Behavior

- If `enable_distribution_account_runtime=True` causes issues: set back to `False`
- DistributionAccount audit output remains available
- No data loss — audit outputs are always computed
- R99/R102 returns to BLOCKED state
- Sponsor distributions remain at 0.0 until flag re-enabled and validated

---

## 14. Cross-Module Validation Matrix

| Module Pair | Check | Status | Blocker |
|-------------|-------|--------|---------|
| SeniorDebtSizing → DistributionAccount | sizing CFADS not affected by distribution outputs | OK (acyclic) | None |
| DistributionAccount → ShlEngine | R102 sweep amount routed correctly | **BLOCKED** | Not implemented |
| DistributionAccount → SponsorEngine | equity distribution routed correctly | **BLOCKED** | Not implemented |
| TaxBridge → DistributionAccount | tax cash not affected by distributions | OK (independent) | None |
| DSCR Policy → DistributionAccount | DSCR inputs stable when distributions added | **BLOCKED** | Stability unknown |
| SHL → DistributionAccount | post-SHL cash stable when R102 sweep enabled | **BLOCKED** | Not implemented |
| Depreciation → TaxBridge | canonical depreciation CIT boundary preserved | OK | None |
| Waterfall → DistributionAccount | waterfall cash inputs stable | OK | None |

**Key:** `OK` = validated. `BLOCKED` = prerequisite not yet met before R99/R102 promotion.

---

## 15. Promotion Gate Matrix

See `reports/phase9_r99_r102_runtime_wiring_gate_matrix.csv` for full gate matrix.

**Summary of critical gates:**

| Gate ID | Gate Name | Status | Notes |
|---------|-----------|--------|-------|
| G01 | DistributionAccount implementation exists | ✅ READY | PR #124 |
| G02 | DistributionAccount audit export exists | ✅ READY | PR #126 |
| G03 | R99/R102 audit values validated | PENDING | Excel source-map |
| G04 | TUHO Excel source-map validated | PENDING | Phase 7F |
| G05 | Oborovo guard implemented | ✅ READY | PR #125 |
| G07 | SHL R102 runtime input implemented | BLOCKED | Not designed yet |
| G09 | DSCR stability validation passed | BLOCKED | Analysis not done |
| G10 | Circular dependency analysis complete | PENDING | First pass done here |
| G12 | Default-off runtime flag implemented | BLOCKED | Design only in this branch |
| G16 | Sponsor cashflow handoff validated | BLOCKED | Not implemented |
| G20 | R99/R102 promotion allowed | **BLOCKED** | Final gate — remains BLOCKED |

---

## 16. Rollback / Kill-Switch Plan

### Immediate Rollback

If `enable_distribution_account_runtime=True` causes model instability or incorrect results:

1. **Set `enable_distribution_account_runtime = False`**
2. DistributionAccount reverts to audit-only mode
3. `equity_distribution_paid_keur = 0.0`, `cash_swept_to_shl_keur = 0.0`
4. No downstream consumer receives unexpected cashflows
5. Audit outputs remain available for reconciliation

### Data Integrity

- Audit outputs (`to_audit_rows()`) are always computed — never depend on `enable_distribution_account_runtime`
- Promotion flag only affects **runtime routing**, not **audit computation**
- If rollback occurs: no data is lost, reconciliation can proceed using audit outputs

### Kill-Switch Hierarchy

1. `is_oborovo=True` → all TUHO gates blocked (first priority)
2. `enable_distribution_account_runtime=False` → audit-only mode (second priority)
3. Individual gate failures → specific outputs zeroed (third priority)

---

## 17. Non-Goals and Forbidden Scope

This branch does NOT include:

- ❌ R99/R102 runtime promotion implementation
- ❌ `app/waterfall_core.py` changes
- ❌ `DistributionAccountEngine.route_runtime_outputs()` implementation
- ❌ SHL runtime wiring changes (R102 as runtime input)
- ❌ SponsorEngine cashflow handoff implementation
- ❌ SeniorDebtSizing runtime changes
- ❌ TaxBridge changes
- ❌ Oborovo runtime assumptions beyond Oborovo guard
- ❌ Default behavior changes (audit-only remains default)

This branch does include:

- ✅ Design document (this file)
- ✅ Gate matrix CSV
- ✅ Design validation tests
- ✅ Recommended next branch

---

## 18. Recommended Next Branch

### Decision Criteria

| Scenario | Recommended Branch |
|----------|-------------------|
| Gate matrix shows many BLOCKED gates | `phase9-cross-module-validation-pack` |
| Specific missing evidence found | `phase9-r99-r102-source-map-fixes` |
| TUHO Excel source-map incomplete | `phase9-tuho-source-map-validation` |
| All prerequisites met | `phase9-distribution-account-runtime-wiring` |

### Immediate Recommended Branch

Based on current gate matrix:
- **G03, G04**: TUHO Excel source-map not yet validated
- **G07, G16**: SHL/Sponsor runtime wiring not designed
- **G09**: DSCR stability analysis not done

**Recommended next branch:** `phase9-cross-module-validation-pack`
- Conduct DSCR stability analysis (G09)
- Design SHL R102 runtime input contract (G06)
- Design Sponsor cashflow handoff contract (G15)
- Validate cross-module validation matrix (G14)

**Alternative:** If specific source-map issues are found first, address those before cross-module validation.

---

## 19. Appendix: Phase 8 vs Phase 9 Design Distinction

| Aspect | Phase 8 | Phase 9 |
|--------|---------|---------|
| Scope | R99/R102 pre-promotion design | DistributionAccount audit-first |
| Deliverable | Design doc + gate matrix | Implementation (audit-only) |
| R99/R102 | BLOCKED | BLOCKED |
| DistributionAccount | Design only | Implemented (audit-first) |
| Audit export | Not designed | Implemented |
| Runtime wiring | Not designed | Designed (this branch) |
| Next step | Phase 8 cross-module validation | Phase 9 runtime wiring implementation |

---

*End of document. R99/R102 remains BLOCKED.*