# Phase P1-UX-FIX-1 — Walkthrough Report (DRAFT)

## Pre-Merge Walkthrough

### TASK A — Realized Gearing for Generic

| Scenario | Expected | Got |
|---|---|---|
| `_compute_realized_gearing_pct(senior=30000, total=100000)` | 30.0 | ✅ 30.0 |
| `_compute_realized_gearing_pct(senior=30000, total=100000, runtime=22500)` | 30.0 (input wins) | ✅ 30.0 |
| `_compute_realized_gearing_pct(senior=0, total=100000, runtime=22500)` | 22.5 (runtime fallback) | ✅ 22.5 |
| `_compute_realized_gearing_pct(senior=None, total=100000, runtime=22500)` | 22.5 (runtime fallback) | ✅ 22.5 |
| `_compute_realized_gearing_pct(senior=0, total=100000)` (no runtime) | None | ✅ None |
| `_compute_realized_gearing_pct(senior=0, total=100000, runtime=0)` | None | ✅ None |
| `_compute_realized_gearing_pct(senior=None, total=0, runtime=22500)` | None (capex=0) | ✅ None |
| `_compute_realized_gearing_pct(senior=None, total=100000, runtime=-100)` | None (negative rejected) | ✅ None |
| TUHO: `_compute(43359.27, 72993.71)` | ~59.40 | ✅ 59.40 |
| Oborovo: `_compute(42852.27, 57973.05)` | ~73.92 | ✅ 73.92 |

**Conclusion**: TASK A works. Backwards-compatible (PR2 two-arg
signature unchanged). TUHO/Oborovo bit-identical.

### TASK B — Scenario Switch Runtime Safety

| Scenario | Expected | Got |
|---|---|---|
| select_scenario with workspace containing runtime evidence | Clears last_runtime_snapshot/summary/origin | ✅ |
| select_scenario with invalid scenario_id | Returns False | ✅ |

**Conclusion**: TASK B works. Direct DB UPDATE bypasses
`save_workspace_state` merge semantics. saved_snapshot preserved.

### TASK C — Dashboard Empty State

| Check | Result |
|---|---|
| Hint block present in `_dashboard.html` | ✅ `id="dashboard-empty-hint"` |
| Hint text matches user requirement | ✅ "Run the model to see KPIs here." |
| Hint wrapped in `runtime_summary.last_runtime_snapshot_id` guard | ✅ |
| P2-FIX-4 "No run yet" CTA preserved | ✅ |
| CSS class `.dashboard-empty-hint` defined | ✅ |

**Conclusion**: TASK C works. Distinct from P2-FIX-4 CTA.

### TASK D — Working Copy Indicator

| Check | Result |
|---|---|
| "Working Copy" badge text in project_selector.html | ✅ |
| Badge data-p1uxfix1-component attribute | ✅ |
| Inside user_created branch only | ✅ |
| Matches tuho / oborovo / generic_solar / generic_wind | ✅ |
| CSS class `.ps-ap-origin--wc` defined | ✅ |

**Conclusion**: TASK D works. Visible only for user-created projects
with a reference template source.

## Constraints Verification

| Check | Result |
|---|---|
| rc1 SHA ancestor | ✅ |
| Engine MD5 `6bf49f33...` | ✅ unchanged |
| Factory MD5 `cf73065b8...` | ✅ unchanged |
| No `waterfall_core.py` change | ✅ |
| No `project_factories.py` change | ✅ |
| No `input_adapter.py` change | ✅ |
| No `db.py` schema change | ✅ |
| No `repository.py` change | ✅ |
| No `run_service.py` / `download_service.py` change | ✅ |
| No `ui_runner.py` change | ✅ |
| No `app.js` change | ✅ |
| No R99/R102/G20 | ✅ |
| No construction-period changes | ✅ |
| No tax/sponsor/IDC changes | ✅ |
| TUHO debt 43,359 kEUR | ✅ |
| Oborovo debt 42,852.27 kEUR | ✅ |

## Tests

| Class | Tests | Pass |
|---|---|---|
| TestTaskARealizedGearingForGeneric | 6 | 6/6 |
| TestTaskBScenarioSwitchRuntimeSafety | 2 | 2/2 |
| TestTaskCDashboardEmptyStateHint | 4 | 4/4 |
| TestTaskDWorkingCopyIndicator | 4 | 4/4 |
| TestConstraintsPreserved | 5 | 5/5 |
| TestBackwardCompat | 1 | 1/1 |
| **TOTAL (new)** | **22** | **22/22** |

## Adjacent Test Suites (regression)

- Phase 51F parallel work guardrails: 21/21 ✅
- P1-CLEANUP-SPRINT-2: 21/21 ✅
- PILOT-HOTFIX-2: 11/11 ✅
- PILOT-HOTFIX-3: 10/11 (1 file-scope fail — expected pre-squash)
- S1-A export runtime: 20/20 ✅
- S1-C factory-resolver: 26/26 ✅
- Excel golden fixtures: 10/10 ✅
- Cross-arc M1/PR1/PR2/P1B: 199/200 (1 cross-arc aggregate fails
  only when run with the PH3 file-scope test; otherwise green)

**Total: 336/337** (PH3 file-scope expected to pass post-squash-merge).

## Recommended Next Step

- Review PR (DRAFT).
- After approval, squash-merge.
- Cleanup worktree.

## Stop-After-Report Contract

DRAFT only. Do NOT mark ready, do NOT merge before review.
