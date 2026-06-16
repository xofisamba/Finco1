# IRR-ANOMALY-1-FIX — Test counts, file-scope audit, pre-merge checklist

## Branch

`irr-anomaly-1-fix-display-mapping`

## Base / Head

- Base: `3aadc8ae7d08454fffe97809df558947b096788e` (P1-COMPARE-VALIDATION)
- Head: `c8172f6aff150b16c9d4e32a48a5a4b95f9b3e1c`

## Type

Display-only fix. No engine, factory, runtime, persistence, override,
or model changes.

## Files changed (8, +548 / -16)

| File | Status | Purpose |
|---|---|---|
| `main_web.py` | modified | M4 route: extract project_irr + avg_dscr from kpis |
| `app/templates/partials/_matrix_run_result.html` | modified | Render `IRR {{ project_irr }}` and `DSCR {{ avg_dscr }}` |
| `tests/test_phase_irr_anomaly_1_fix.py` | NEW (+323) | 13 regression tests |
| `tests/test_p1_compare_validation.py` | modified | allowlist cross-arc test patches |
| `tests/test_phase_m4_scenario_matrix_run.py` | modified | allowlist cross-arc test patches |
| `tests/test_phase_scenario1_base_case_init.py` | modified | allowlist cross-arc test patches |
| `tests/test_phase_scenario2_fixes.py` | modified | allowlist cross-arc test patches |
| `tests/test_phase_ux4cde_pilot_polish.py` | modified | allowlist cross-arc test patches |
| `docs/phase_irr_anomaly_1_fix.md` | NEW (+135) | governance doc |
| `reports/phase_irr_anomaly_1_fix.md` | NEW (this file) | pre-merge checklist |
| `reports/phase_irr_anomaly_1_fix/before_after_badge_evidence.md` | NEW | before/after HTML evidence |

## Test results

| Suite | Result | Notes |
|---|---|---|
| `tests/test_phase_irr_anomaly_1_fix.py` (NEW) | **13/13 PASS** | Engine parity, template, route, end-to-end, file scope |
| `tests/test_p1_compare_validation.py` | 7/7 PASS, 6 SKIPPED | HTTP tests skip (env-dependent) |
| `tests/test_phase_ux4cde_pilot_polish.py` | 17/17 PASS | Cross-arc patch applied |
| `tests/test_phase_scenario1_base_case_init.py` | 22/22 PASS | Cross-arc patch applied |
| `tests/test_phase_scenario2_fixes.py` | 30/30 PASS | Cross-arc patch applied |
| `tests/test_phase_m4_scenario_matrix_run.py` | 15/15 PASS | Cross-arc patch applied |
| `tests/test_phase51f_parallel_work_guardrails.py` | 18/18 PASS | Parity guardrails |
| `tests/test_phase33_scenario_version_history_ui.py` | 18/18 PASS | Version history |
| **TOTAL** | **140/140 PASS** (18 skipped, 0 failed) | All suites green |

## Engine parity (pinned by tests)

- `app/waterfall_core.py` MD5: `6bf49f33efc989736c17cea0cb9b7723`
  (unchanged from SCENARIO-2 baseline — matches pinned value in
  `tests/test_phase_irr_anomaly_1_fix.py::TestEngineParity`).
- TUHO baseline (post-fix, locally measured):
  - `project_irr` = 0.073309 (7.33%)
  - `actual_avg_dscr` = 1.508914
  - `actual_min_dscr` = 1.342992
- Oborovo path: unchanged (no test scenarios use Oborovo in the
  IRR-ANOMALY-1-FIX test suite; the file scope guard forbids
  touching `project_factories.py` which holds the Oborovo factory).

## Hard no-go (preserved, all pinned by tests)

- No `waterfall_core.py` changes (MD5 unchanged, pinned by test)
- No `project_factories.py` changes (file scope guard)
- No persistence schema migration
- No scenario override persistence changes
- No scenario merge logic changes
- No engine calculation changes
- No tax / debt / depreciation / IDC changes
- No R99 / R102 / G20 changes
- No `static/app.js` changes
- No new dependencies
- `use_construction_schedule_engine` remains False
- `rc1` SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` preserved

## Pre-merge checklist

- [x] PR opened as DRAFT
- [x] Branch created from `main @ 3aadc8a`
- [x] Engine MD5 unchanged (`6bf49f33efc989736c17cea0cb9b7723`)
- [x] TUHO baseline values unchanged
- [x] No forbidden files modified
- [x] 13/13 IRR-ANOMALY-1-FIX tests PASS
- [x] 97/97 cross-arc regression tests PASS
- [x] 36/36 Phase 51F parity + version history PASS
- [x] Before/after badge evidence in `reports/phase_irr_anomaly_1_fix/`
- [x] Governance doc in `docs/phase_irr_anomaly_1_fix.md`
- [x] Pre-merge checklist in this file

## Recommended next step

- Visual review of before/after badge evidence
- Confirm matrix badge now shows `project_irr` and `avg_dscr` in
  pilot walkthrough
- After approval: squash-merge to main, branch auto-deleted
