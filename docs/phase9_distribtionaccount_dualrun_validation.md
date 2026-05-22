# Phase 9 — DistributionAccount Dual-Run Validation

## Overview

**Branch:** `phase9-distributionaccount-dualrun-validation`  
**Goal:** Audit-only comparison of WaterfallEngine vs DistributionAccount per period  
**Authoritative source:** WaterfallEngine — unchanged in this branch  
**DA role:** Non-authoritative, audit-only

---

## Architecture Summary

### What Was Added

#### 1. `use_dualrun_validation` flag threading

```
API layer (run_project)
  └── run_demo_project(use_dualrun_validation=False)
        └── _run_waterfall(..., use_dualrun_validation=False)
              └── WaterfallRunConfig(use_dualrun_validation=False)
                    └── run_waterfall_v3_core(use_dualrun_validation=False)
                          └── _attach_dualrun_validation() [when True]
                                └── run_dual_validation(waterfall_result, governed_inputs, economic_inputs)
                                      └── DualRunResult dataclass
```

#### 2. Dual-run comparison

`run_dual_validation()` (already existed in `domain/distribution_account/dualrun_validation.py`) runs two DA evaluations side-by-side:

| Mode | R99 | R102 | Purpose |
|---|---|---|---|
| Governed (normal) | BLOCKED | BLOCKED | Current gate-driven behavior |
| Economic (audit) | Evaluated | Evaluated | What distributions would be with R99/R102 gates resolved |

#### 3. Result attachment

`result._dualrun_validation = DualRunResult` — attached to waterfall result when flag=True.

---

## Key Classes

### `DualRunPeriodResult` (frozen dataclass)
Per-period comparison:
- `runtime_distribution_keur` — WaterfallEngine distribution
- `da_governed_paid_distribution_keur` — DA in governed mode
- `da_economic_paid_distribution_keur` — DA in economic mode
- `delta_keur` / `delta_pct` — governed vs runtime delta
- `classification` — IDENTICAL | ROUNDING | EXPECTED_GATE_DIFFERENCE | UNEXPECTED | BLOCKING
- `gates_passed`, `r99_blocked`, `r102_blocked` — gate status

### `DualRunResult` (frozen dataclass)
Full comparison summary:
- `phase_c_ready` — True if no blocking or unexpected diffs
- `runtime_unchanged`, `sponsor_unchanged`, `shl_unchanged` — all True
- `r99_r102_still_blocked` — True
- `identical_periods`, `rounding_periods`, `expected_gate_diff_periods`, `unexpected_diff_periods`, `blocking_periods`

---

## Classification Rules

| Classification | Condition |
|---|---|
| IDENTICAL | `delta == 0` |
| ROUNDING | `gates_passed` and `|delta| <= 1.0 kEUR` |
| EXPECTED_GATE_DIFFERENCE | R99/R102 blocked OR DSCR/lockup/cash failures (expected divergence) |
| UNEXPECTED | `gates_passed` and `|delta_pct| > 1%` — needs investigation |
| BLOCKING | UNEXPECTED with large delta — Phase C must not proceed |

---

## Validation Results (TUHO + Oborovo)

### TUHO Wind 1

| Metric | Value |
|---|---|
| Project IRR | 9.41% |
| Equity IRR | 11.15% |
| Total Distributions (runtime) | 173,572 kEUR |
| phase_c_ready | ✅ True |
| blocking_periods | 0 |
| unexpected_diff_periods | 0 |
| identical_periods (governed) | 35 |
| expected_gate_diff_periods | 26 |
| identical_periods (economic) | 39 |
| runtime_unchanged | ✅ True |
| sponsor_unchanged | ✅ True |
| shl_unchanged | ✅ True |
| r99_r102_still_blocked | ✅ True |

**DA governed total: 0.0 kEUR** (all gated by R99/R102 in audit-only mode)  
**DA economic total: higher** (R99/R102 resolved)

### Oborovo Solar PV

| Metric | Value |
|---|---|
| Project IRR | 7.98% |
| Equity IRR | 9.17% |
| Total Distributions (runtime) | 104,699 kEUR |
| phase_c_ready | ✅ True |
| blocking_periods | 0 |
| unexpected_diff_periods | 0 |
| identical_periods (governed) | 9 |
| expected_gate_diff_periods | 51 |
| identical_periods (economic) | 38 |
| runtime_unchanged | ✅ True |
| sponsor_unchanged | ✅ True |
| shl_unchanged | ✅ True |
| r99_r102_still_blocked | ✅ True |

**DA governed total: 0.0 kEUR** (all gated in audit-only mode)  
**DA economic total: higher** (R99/R102 resolved)

---

## Tolerance Policy

| Tolerance | Value | Applied When |
|---|---|---|
| Rounding threshold | `≤ 1.0 kEUR` | All gates pass |
| Unexpected threshold | `> 1% of runtime` | Gates pass but significant delta |
| Blocking threshold | Any UNEXPECTED with `> 1%` delta | Phase C must not proceed |
| Expected gate diff | Any R99/R102/DSCR/lockup/cash block | Always expected in governed mode |

---

## Files Changed

| File | Change |
|---|---|
| `app/waterfall_runner.py` | Added `use_dualrun_validation: bool = False` to `WaterfallRunConfig`, passes to `run_waterfall_v3_core` |
| `app/ui_runner.py` | Added `use_dualrun_validation` param to `_run_waterfall` and `run_demo_project` |
| `app/api/project_runner.py` | Added `use_dualrun_validation` param, attaches `dualrun_validation` to output dict |
| `app/templates/partials/*.html` | Fixed Jinja2 format strings: `"%,Xf"|format(var)` → `"{:,Xf}".format(var)` |
| `tests/test_phase9_distribaccount_dualrun_integration.py` | New — 28 tests for TUHO/Oborovo dualrun integration |
| `docs/phase9_distribtionaccount_dualrun_validation.md` | This doc |

---

## Constraints Respected

- ✅ No waterfall formula changes
- ✅ No sponsor runtime wiring changes
- ✅ No R99 routing / R102 promotion
- ✅ No tax logic changes
- ✅ No persistence changes
- ✅ No Excel export redesign
- ✅ No UI redesign
- ✅ DA remains non-authoritative

---

## Remaining Risks Before DA Runtime Authority

### 1. Economic mode divergence
In economic mode, Oborovo shows 38 IDENTICAL periods but TUHO shows 39 — meaning ~2-3 periods still have unexplained delta even with gates resolved. These need investigation before Phase C.

### 2. Cash source selection
The `_attach_dualrun_validation` uses `cf_after_reserves_keur` as the primary cash source for DA when `r99_fcf` diverges from it (tax bridge case). This is a policy decision — if the actual cash source hierarchy changes in Excel, the audit results may not match.

### 3. Oborovo high expected-gate-diff count
Oborovo has 51 EXPECTED_GATE_DIFFERENCE periods vs 26 for TUHO — this is a high ratio (51/60 = 85%). Before Phase C, need to confirm this is all R99/R102 blocking and not DSCR/lockup issues.

### 4. No persistence of dualrun results
Results exist only in memory on the server. For audit trails, dualrun results need to be stored (separate from runtime results).

### 5. PHASE_C_READY flag
Both TUHO and Oborovo pass `phase_c_ready=True` — but this is based on classification rules only. It does not mean DA is ready to be made authoritative — that requires stakeholder sign-off on the gate logic.