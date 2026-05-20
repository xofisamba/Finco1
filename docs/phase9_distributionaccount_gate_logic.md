# Phase 9 — DistributionAccount Gate Logic Fix

## 1. Executive Summary

`equity_distribution_paid_keur` was structurally hard-coded to `0.0` in `_compute_period()`, bypassing all gate evaluation. This design doc describes the fix: gate-driven computation of `equity_paid` in the audit result.

**Key change:** When all gates pass (R99, R102, DSCR, lockup, oborovo, cash), `equity_distribution_paid_keur = equity_candidate`. When any gate fails, `equity_distribution_paid_keur = 0.0`.

**Important:** This remains **audit-only**. `equity_paid` does NOT flow to `WaterfallEngine.distribution_keur` or Sponsor. Default runtime behavior is unchanged.

## 2. What Changed

### Before

```python
# All distributions blocked in audit-only mode
equity_paid = 0.0
shl_sweep = 0.0
```

### After

```python
# Phase 9: Gate-driven equity paid computation (audit-only).
# When all gates pass: equity_paid = equity_candidate.
# When any gate fails: equity_paid = 0.0.
# R99/R102 remain BLOCKED for runtime routing.
all_gates_passed = (
    r99_gate.passed and
    r102_gate.passed and
    dscr_gate.passed and
    lockup_gate.passed and
    oborovo_gate.passed and
    cash_gate.passed
)
equity_paid = equity_candidate if all_gates_passed else 0.0

# SHL sweep remains 0.0 (not wired to ShlEngine in this branch)
shl_sweep = 0.0
```

## 3. Gate Evaluation

### 3a. Gate priority for `equity_paid`

All six gates must pass for `equity_paid = equity_candidate`:

| Gate | Pass condition |
|---|---|
| `r99_gate` | `enable_r99_r102_runtime=True` (currently always False) |
| `r102_gate` | `enable_r99_r102_runtime=True` (currently always False) |
| `dscr_gate` | `actual_dscr >= target_distribution_dscr` |
| `lockup_gate` | `period_index > senior_tenor_years AND DSRA/JDSRA funded AND cash >= 0` |
| `oborovo_gate` | `is_oborovo=False` (TUHO-only) |
| `cash_gate` | `cash_available >= 0` |

### 3b. R99/R102 always blocked

R99 and R102 gates are evaluated but always return `passed=False` unless `enable_r99_r102_runtime=True` (which is never set in this branch). This means **in this branch, equity_paid will always be 0.0 for the R99/R102 reason alone** — because those gates never pass.

This is **correct behavior for audit-only mode**: the audit result accurately reflects that R99/R102 gates are not yet enabled.

## 4. Runtime Behavior: Unchanged

### 4a. WaterfallEngine unchanged

`WaterfallEngine.run_waterfall()` computes `distribution_keur` using its own internal cash sweep logic. This is **unchanged** by this fix.

### 4b. Sponsor unchanged

Sponsor receives `distribution_keur` from `WaterfallEngine`. This is **unchanged**.

### 4c. SHL unchanged

`ShlEngine` receives `distribution_account_r102_sweep_candidate_keur` as an input port but this port is **not populated** in `waterfall_core.py`. Unchanged.

## 5. Audit Behavior: Now Accurate

### 5a. Before fix

`equity_distribution_paid_keur` was always `0.0` regardless of gate state. The audit result was structurally wrong.

### 5b. After fix

`equity_distribution_paid_keur` reflects actual gate evaluation:
- When all gates pass: `= equity_candidate` (realistic audit output)
- When any gate fails: `= 0.0` with specific `blocked_reason`

The audit is now an accurate representation of what WOULD be paid if R99/R102 were promoted.

## 6. DSCR Gate Interaction

DSCR gate (`dscr_gate`) checks `actual_dscr >= target_distribution_dscr`. This gate IS operational and can pass.

When DSCR passes AND all other non-R99/R102 gates pass, `equity_paid = equity_candidate`.

This means for TUHO post-lockup periods where DSCR > threshold, the audit result will show a non-zero `equity_paid`.

## 7. Equity Candidate vs Paid

```
equity_candidate = cash_for_dist
  (cash available after DSRA top-up and minimum cash reserve)

equity_paid = equity_candidate if all_gates_passed else 0.0
  (what the audit says WOULD be distributable if gates were enabled)
```

## 8. SHL Sweep: Unchanged

`cash_swept_to_shl_keur = 0.0` remains. The SHL sweep port (`distribution_account_r102_sweep_candidate_keur`) is not wired in this branch.

## 9. Validation

| Test | Expected result |
|---|---|
| TUHO, all gates pass | `equity_paid = equity_candidate` (non-zero) |
| TUHO, DSCR fails | `equity_paid = 0.0`, blocked_reason set |
| TUHO, lockup active | `equity_paid = 0.0`, blocked_reason set |
| Oborovo | `equity_paid = 0.0`, blocked_reason = OBOROVO_NOT_SUPPORTED |
| R99/R102 gates | Always BLOCKED (expected in audit-only mode) |

## 10. R99/R102 Promotion Implications

This fix does NOT enable R99/R102 promotion. R99/R102 gates remain blocked (`enable_r99_r102_runtime=False`).

When R99/R102 are eventually promoted, the gate logic change here means `equity_paid` will automatically become operational — the only remaining step is wiring `equity_paid` to `WaterfallEngine.distribution_keur` (blocked by design, to be done in `phase9-distributionaccount-runtime-wiring`).

## Change Table

| File | Change |
|---|---|
| `domain/distribution_account/engine.py` | Replace `equity_paid = 0.0` with gate-driven computation; update module docstring |
