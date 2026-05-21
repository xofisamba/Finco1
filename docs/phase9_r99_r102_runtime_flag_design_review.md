# Phase 9: R99/R102 Runtime Flag Design Review

**Branch:** `phase9-r99-r102-runtime-flag-design-review`
**Base:** `9646631` (PR #153 — audit/economic mode contract reconciliation)

---

## Purpose

Design review for an explicit runtime flag that allows R99/R102 gate evaluation to flow to runtime `distribution_keur` under controlled conditions — without being G20 promotion.

**Status: DESIGN REVIEW ONLY — implementation not started.**

---

## Current State

### R99/R102 Gate Governance

| Condition | Result | Routing |
|-----------|--------|---------|
| `audit_economic_mode=False` + `runtime_economic_mode=False` | Gates BLOCKED | Not applicable |
| `audit_economic_mode=True` | Gates evaluated for comparison | Never routed to runtime |
| `runtime_economic_mode=True` | Gates evaluated for staging | Allowed behind `use_distributionaccount_runtime_wiring=True` |

### Existing Fields in `DistributionAccountPeriodInput`

| Field | Default | Purpose |
|-------|---------|---------|
| `enable_r99_r102_runtime` | `False` | Existing field — currently warning-only |
| `audit_economic_mode` | `False` | Audit/comparison only — never routed |
| `runtime_economic_mode` | `False` | Pre-G20 staging for DA wiring |

### Gate Activation

Current logic in `evaluate_r99_gate` / `evaluate_r102_gate`:
```python
gate_active = audit_economic_mode or runtime_economic_mode
if not gate_active:
    # Governed mode: always BLOCKED
    return DistributionGateResult(passed=False, ...)
# Economic mode: evaluate using cash inputs
```

`enable_runtime` parameter exists in gate functions but is **not wired** to gate activation.

---

## Design Questions

### Q1: What is the desired runtime behavior?

Two options for how R99/R102 gates can influence runtime `distribution_keur`:

**Option A: Dedicated flag (`use_r99_r102_runtime`)**
- New top-level flag in `run_waterfall_v3_core()`
- Separate from `use_distributionaccount_runtime_wiring`
- Controls whether R99/R102 gates evaluated in governed+economic dual-run can promote to runtime
- More granular control

**Option B: Extend `enable_r99_r102_runtime`**
- Existing field in `DistributionAccountPeriodInput` already exists
- Currently triggers a warning but doesn't affect gate evaluation
- Could be wired to gate activation
- Less surface area for new flags

**Option C: Combine with existing DA wiring flag**
- `use_distributionaccount_runtime_wiring` already controls DA wiring
- Could add `include_r99_r102_in_wiring` sub-flag
- Tightly coupled with existing DA wiring infrastructure

### Q2: What is the promotion boundary?

R99/R102 promotion to runtime should NOT be unconditional. Required controls:

| Control | Purpose |
|---------|---------|
| Project scope | TUHO-only or TUHO+Oborovo |
| Default-off | Flag defaults to `False` |
| Governance gate | Some governance entity must approve |
| Audit trail | Explicit log of what was promoted |
| Reversibility | Can be rolled back |

### Q3: What does "runtime" mean here?

The phrase "R99/R102 promotion to runtime" is ambiguous:

**Interpretation 1: Full promotion**
- R99/R102 gates become the primary distribution determinant
- Replaces current lockup/DSCR-based distribution logic
- **This is G20** — not what we're designing

**Interpretation 2: Conditional influence**
- R99/R102 gates can increase (not decrease) distributions
- Used alongside existing DA logic
- Falls back to governed behavior if gates fail
- **Pre-G20 staging** — closer to what we're designing

### Q4: How does this interact with existing DA wiring?

`use_distributionaccount_runtime_wiring` already wires `da_paid_distribution_keur` into `distribution_keur` behind a default-off flag. The DA wiring uses `runtime_economic_mode=True` which evaluates R99/R102 gates using cash logic.

Question: Should R99/R102 runtime promotion:
- **Replace** DA wiring? (mutually exclusive)
- **Extend** DA wiring? (DA wiring still applies, R99/R102 adds additional distribution)
- **Be independent** of DA wiring? (separate flag, separate path to distribution_keur)

### Q5: What is the Oborovo policy?

Currently Oborovo is guarded from DA wiring. Should R99/R102 runtime promotion:
- Apply to Oborovo as well?
- Follow same guard as DA wiring?
- Have a separate Oborovo-specific approval?

---

## Recommended Direction (Design Hypothesis)

**Option A + Interpretation 2 + DA wiring extended:**

1. New flag: `use_r99_r102_runtime: bool = False` in `run_waterfall_v3_core()`
2. When `use_r99_r102_runtime=True` AND `runtime_economic_mode=True`:
   - R99/R102 gates can increase distributions above governed floor
   - Falls back to governed behavior if gates fail
   - Still blocked by default (default-off)
3. Oborovo: same guard as DA wiring (TUHO-only by default)
4. R99/R102 gates use cash-based evaluation (same as `runtime_economic_mode`)
5. Dual-run still uses `audit_economic_mode=True` for comparison — never promotion

**Key distinction from G20 promotion:**
- G20 = unconditional promotion of R99/R102 as the primary distribution logic
- This design = conditional increase of distributions, not replacement
- Falls back to governed behavior if gates fail
- Not G20 promotion; pre-G20 staging with explicit governance approval

---

## Acceptance Criteria (Draft)

1. `use_r99_r102_runtime` defaults to `False`
2. R99/R102 gates can increase distributions above governed floor when flag=True
3. If gates fail, falls back to governed (not zero) behavior
4. Oborovo guard applies (same as DA wiring)
5. R99/R102 promotion does not require G20 approval
6. Audit trail: explicit log of gate passes/failures
7. TUHO validation: distribution total vs governed baseline is within expected range
8. Default behavior (flag=False) is bit-identical to current main
9. Dual-run comparison: audit mode unchanged

---

## Open Questions (for cofix review)

1. Should R99/R102 runtime promotion be TUHO-only or TUHO+Oborovo?
2. Should this be a separate flag or extend the existing DA wiring flag?
3. What is the fallback behavior if R99/R102 gates fail — governed floor or zero?
4. Is there a governance entity that must explicitly approve this in your organization?
5. Should there be a cap on how much R99/R102 can increase distributions?

---

## Forbidden (per task brief)

- No G20 promotion
- No unconditional R99/R102 approval
- No default-on behavior
- No Oborovo runtime promotion without explicit guard

---

## Next Branch After Design Review

Once design is approved: `phase9-r99-r102-runtime-flag-implementation`