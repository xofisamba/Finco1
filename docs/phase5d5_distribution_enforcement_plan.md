# Phase 5D.5 — Distribution Enforcement Plan

> **Status:** Documentation only. No code. No model output changes.**

---

## 1. Current State

All Phase 5D infrastructure is in place and audit-only:

| Component | Location | Status |
|---|---|---|
| Cash ledger foundation | `domain/portfolio/cash_ledger/` | ✅ |
| Cash ledger → constraint integration | `domain/portfolio/distribution_constraints/integration.py` | ✅ |
| Distribution constraint evaluator | `domain/portfolio/distribution_constraints/runner.py` | ✅ |
| SPV retained cash overlay | `domain/portfolio/distribution_constraints/overlay.py` | ✅ |
| HoldCo retained cash overlay | `domain/portfolio/distribution_constraints/holdco_overlay.py` | ✅ |

**None of these change any model output.** `distribution_keur` in waterfall periods, `SPVOutput.total_distribution_keur`, and all sponsor/equity IRR fields remain exactly as before.

---

## 2. Enforcement Decision Points

Enforcement could be wired at different layers. Each has trade-offs:

### A. SPV Waterfall Level
Inject into `distribution_keur` before cash leaves SPV.

| Pros | Cons |
|---|---|
| Cleanest cash moment | Modifies waterfall economics — breaks regression |
| Natural period-by-period control | Requires SPVOutput mutation |
| Aligns with existing debt/equity priority | Requires coordination with existing waterfall engine |

**Verdict:** ❌ Not recommended first — too invasive.

### B. Post-Waterfall Overlay Level
Wire overlay `allowed_distribution_keur` as a read-only check in HoldCo runner before equity distribution.

| Pros | Cons |
|---|---|
| No waterfall mutation | Must be explicitly wired into HoldCo cash flow |
| Preserves existing waterfall semantics | May miss SPV-level cash timing |
| Overlay already exists (audit → enforcement) | Overlay must be calculated before HoldCo runs |

**Verdict:** ✅ Recommended first enforcement point — lowest risk.

### C. HoldCo Distribution Layer
Apply `HoldCoRetainedCashOverlay.available_distribution_by_period` to sponsor distributions.

| Pros | Cons |
|---|---|
| Aligns with sponsor-level constraint intent | Requires sponsor waterfall (not yet designed) |
| Clean separation from SPV waterfall | Sponsor IRR not yet implemented |

**Verdict:** ✅ Future enforcement point (Phase 5H).

### D. Sponsor Distribution Layer (later)
Final sponsor-level hard cap after all HoldCo/HoldCo waterfall logic.

| Pros | Cons |
|---|---|
| Full constraint coverage | Requires sponsor waterfall + IRR |
| Audit trail from SPV → HoldCo → Sponsor | High complexity |

**Verdict:** ✅ Long-term target (Phase 5H+).

---

## 3. Recommended Sequencing

**Do NOT mutate base waterfall first.**

```
A. audit-only overlays      ← DONE (5D.1–5D.4)
B. Excel / export visibility ← Phase 5E
C. UI warning panel          ← Phase 5F
D. user opt-in enforcement   ← Phase 5G
E. only then modify cash      ← Phase 5H
```

**Rationale:** Changing cash distributions changes the numbers that all stakeholders use for comparison. Starting with visibility (A→B→C) builds confidence before any enforcement (D→E). If users can see what WOULD be constrained and why, they can validate the logic before it becomes binding.

---

## 4. Required Invariants Before Enforcement

Before any enforcement is activated, the following must hold:

| Invariant | Why it matters |
|---|---|
| Total distributions reconcile to cash ledger | No phantom distributions |
| Retained cash is explicit in overlay | No hidden cash lockup |
| SHL principal repayment treated as cash use | SHL is not equity — principal return is cash out, not profit |
| DSRF drawn/repaid logic remains separate | DSRF is a liquidity facility, not equity — must not be conflated |
| HoldCo cash account is explicit | Must trace cash from SPV → HoldCo → Sponsor |
| No silent mutation of `distribution_keur` | Project IRR depends on clean base waterfall |
| Project IRR and Sponsor IRR semantics remain separated | Otherwise IRR comparisons become meaningless |
| Cash ledger closing balances match SPV `closing_cash_keur` | Traceability from waterfall to ledger |

---

## 5. Future Enforcement Modes

| Mode | Behavior | Use case |
|---|---|---|
| `OFF` / audit-only | All overlays computed but not applied. No model output changes. | Default. Always on until explicitly changed. |
| `WARNING_ONLY` | Compute overlays; emit warnings when distribution would be reduced. No cash blocked. | User visibility before enforcement |
| `SOFT_CAP` | Cap distributions at `allowed_distribution_keur` when exceeded. Emit audit trail. Block only excess. | Balanced approach — allow operational headroom |
| `HARD_BLOCK` | Reject any distribution exceeding `allowed_distribution_keur`. Throw or error. | Strict regulatory compliance |

**Default:** `OFF`. No enforcement unless explicitly configured.

---

## 6. Risks

| Risk | Mitigation |
|---|---|
| Breaking historical regression values | Overlay-only path preserves base waterfall exactly |
| Confusing Project IRR vs Sponsor IRR | Keep separate waterfall paths; no cross-contamination |
| Double-counting SHL principal | SHL principal repayment treated as cash use (outflow), not distribution |
| Mixing DSRF liquidity facility with SHL shareholder loan | DSRF: drawn/repaid separate from distributions; SHL: principal return tracked per period |
| Tax treatment not ready | Tax engine is out of scope for 5D — enforcement must not assume tax is finalized |
| Sponsor waterfall dependency | Sponsor distribution enforcement requires sponsor waterfall design (Phase 5H) |
| Excel/UI mismatch if enforcement is hidden | Phase 5E (Excel export) and 5F (UI panel) must show exactly what the model computes |

---

## 7. Proposed Implementation Phases

```
Phase 5D.5  ← this doc (architecture plan only)

Phase 5E    Excel export of SPV + HoldCo retained cash overlays
            → export overlay to xlsx with period-level breakdown

Phase 5F    UI warning panel
            → streamlit page showing constraint results per entity per period

Phase 5G    Opt-in enforcement flag
            → DistributionConstraintConfig.enforcement_mode: OFF|WARNING_ONLY|SOFT_CAP|HARD_BLOCK
            → SPV runner respects flag; base waterfall unchanged in OFF mode

Phase 5H    Sponsor distribution integration
            → wire HoldCo overlay into sponsor distribution runner
            → enforce at sponsor level after HoldCo-level audit trail confirmed

Phase 6A    Tax template schema
            → define tax input schema before hard enforcement depends on it
```

---

## 8. Non-Scope

This document does **NOT** implement:

- ❌ Enforcement or blocking of distributions
- ❌ Tax engine
- ❌ HoldCo IRR or Sponsor IRR
- ❌ Sponsor waterfall
- ❌ Monthly model
- ❌ Any mutation of `distribution_keur` or `SPVOutput`
- ❌ Any change to existing waterfall economics
- ❌ Any regression-breaking change to model outputs

Enforcement is planned but not activated. All existing model outputs remain unchanged until a future phase explicitly opts in.
---

## Phase 5H — Enforcement Simulation Report

Added: `simulation.py` + `test_distribution_constraints_simulation.py`

### Purpose
Simulation shows what distributions WOULD be restricted under future
SOFT_CAP/HARD_BLOCK modes, without applying any restrictions. Pure reporting
layer; no mutation, no enforcement, no waterfall changes.

### What's added
- `simulation.py`:
  - `DistributionConstraintSimulationPeriod` — period-level simulation row
  - `DistributionConstraintSimulationResult` — per-entity aggregation
  - `simulate_distribution_enforcement(constraint_results)` — pure reporter

- Exports added to `__init__.py`

### Behavior
- Input: `tuple[DistributionConstraintResult, ...]` (from `evaluate_distribution_constraints`)
- Output: `tuple[DistributionConstraintSimulationResult, ...]`
- `would_restrict_keur = requested - allowed` (0 if allowed == requested)
- Block reasons preserved as strings
- Warnings preserved
- Totals auto-computed from periods

### Key constraints (Phase 5H)
- No distribution blocking — simulation only
- No waterfall changes
- No `distribution_keur` semantics changes
- No model output changes
- Bridge to future SOFT_CAP/HARD_BLOCK activation

---

### enabled vs enforcement_mode

Two separate controls that compose additively:

**`enabled`** — gate at the call site. Controls whether the evaluator is invoked at all.

- `enabled=False` (default): full pass-through, no evaluation, no reasons, no warnings.
- `enabled=True`: evaluator runs and applies `enforcement_mode`.

**`enforcement_mode`** — behavior once enabled. Only matters when `enabled=True`.

| enforcement_mode | When enabled=True | When enabled=False |
|---|---|---|
| `OFF` (default) | Pass-through; no reasons, no warnings | Pass-through |
| `WARNING_ONLY` | Reasons/warnings computed; `allowed=requested` | — (disabled) |
| `SOFT_CAP` | Same as WARNING_ONLY + "not active" warning | — (disabled) |
| `HARD_BLOCK` | Same as WARNING_ONLY + "not active" warning | — (disabled) |

**Design intent:** Keep `enabled=False` as the safe default. Use `enabled=True` + `enforcement_mode=OFF` when constraints are configured but not yet enforced. This makes the distinction explicit and avoids ambiguity about whether evaluation is active.
