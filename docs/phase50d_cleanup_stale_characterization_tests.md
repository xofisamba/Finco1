# Phase 50D — Clean Up Stale Characterization Tests

## Base SHA
`ec33a5d236e3d6b612fcf1604ae14ffad8717f4d` (PR #376 — Phase 50C closeout)

## Objective
Clean up stale Phase 49D-series characterization tests that asserted intermediate states no longer valid after completed export/audit and scenario state extractions. Restore trust in the test suite by replacing obsolete assertions with current-state assertions.

> **This phase is test-hygiene only.** No production code changed.

---

## Stale Test Files Inspected

| File | Phase | Issue |
|------|-------|-------|
| `tests/test_phase49d1_post_download_characterization.py` | 49D-1 | Asserted old `build_excel_export` (not `build_excel_export_for_post_request`), `runtime_guard_for_snapshot` in route (not `check_runtime_allowed`), `record_export` direct call |
| `tests/test_phase49d2_post_download_extraction.py` | 49D-2 | Asserted `record_export` still in route |
| `tests/test_phase49d3c_get_download_audit_service_wiring.py` | 49D-3C | Asserted exactly 1 direct `record_export` call remains; asserted POST /download uses direct `record_export` (not `record_download_export`) |

---

## Stale Assertions Found

| Test | Stale Assertion | Current Reality |
|------|---------------|------------------|
| `test_record_export_called_in_download_post` | `record_export(` in POST /download section | Zero direct `record_export` calls in main_web.py |
| `test_runtime_guard_for_snapshot_used` | `runtime_guard_for_snapshot(` in POST /download | `check_runtime_allowed(` now used |
| `test_build_excel_export_called_with_result_and_inputs` | `build_excel_export(` in route | `build_excel_export_for_post_request(` now used |
| `test_record_export_still_in_route` | `record_export(` + `replay_metadata=replay_metadata` in route | `record_download_export(` via audit service |
| `test_post_download_still_uses_direct_record_export` | `record_export(` in POST /download | `record_download_export(` via audit service |
| `test_only_one_direct_record_export_remains` | Exactly 1 direct `record_export` call | **0** direct `record_export` calls |

---

## Changes Made

### `tests/test_phase49d1_post_download_characterization.py`
- `test_record_export_called_in_download_post` → asserts `record_download_export(` (audit service) now in POST /download
- `test_runtime_guard_for_snapshot_used` → asserts `check_runtime_allowed(` (service wrapper) now in POST /download
- `test_build_excel_export_called_with_result_and_inputs` → asserts `build_excel_export_for_post_request(` (current service) now in route

### `tests/test_phase49d2_post_download_extraction.py`
- `test_record_export_still_in_route` → asserts `record_download_export(` (audit service) now in POST /download

### `tests/test_phase49d3c_get_download_audit_service_wiring.py`
- `test_post_download_still_uses_direct_record_export` → deleted, replaced with `test_post_download_uses_audit_service_not_direct_record_export`
- `test_only_one_direct_record_export_remains` → replaced with `test_zero_direct_record_export_calls_in_main_web`

### New: `tests/test_phase50d_current_state_after_refactor_cleanup.py`
19 tests verifying final current-state assertions:
- `main_web.py` has 0 direct `record_export` calls
- `main_web.py` does not import `record_export`
- `main_web.py` does not import `runtime_guard_for_snapshot` directly
- `main_web.py` uses `check_runtime_allowed` at all 6 call sites
- All 3 services exist with correct functions
- `POST /download` uses `record_download_export` + `build_excel_export_for_post_request`
- `GET /download` uses `record_download_export` + `build_values_only_export_for_project`
- `_resolve_runtime_snapshot_source` is thin wrapper
- No fixture CSV changes
- No JS financial calculations

---

## Tests Deleted / Converted

| Original Test | Action | Replacement |
|--------------|--------|-------------|
| `test_record_export_called_in_download_post` | Converted | `record_download_export(` assertion |
| `test_runtime_guard_for_snapshot_used` | Converted | `check_runtime_allowed(` assertion |
| `test_build_excel_export_called_with_result_and_inputs` | Converted | `build_excel_export_for_post_request(` assertion |
| `test_record_export_still_in_route` | Converted | `record_download_export(` assertion |
| `test_post_download_still_uses_direct_record_export` | Deleted + replaced | `test_post_download_uses_audit_service_not_direct_record_export` |
| `test_only_one_direct_record_export_remains` | Replaced | `test_zero_direct_record_export_calls_in_main_web` |

---

## Final Current-State Coverage

| Assertion | File | Status |
|-----------|------|--------|
| Zero direct `record_export` calls in main_web | `test_phase50d_current_state_after_refactor_cleanup.py` | ✅ |
| Zero `record_export` imports in main_web | `test_phase50d_current_state_after_refactor_cleanup.py` | ✅ |
| Zero `runtime_guard_for_snapshot` direct imports | `test_phase50d_current_state_after_refactor_cleanup.py` | ✅ |
| 6 `check_runtime_allowed` call sites | `test_phase50d_current_state_after_refactor_cleanup.py` | ✅ |
| POST /download uses `record_download_export` | `test_phase50d_current_state_after_refactor_cleanup.py` | ✅ |
| POST /download uses `build_excel_export_for_post_request` | `test_phase49d1_post_download_characterization.py` | ✅ (updated) |
| GET /download uses `record_download_export` | `test_phase50d_current_state_after_refactor_cleanup.py` | ✅ |
| Scenario state service API complete | `test_phase50d_current_state_after_refactor_cleanup.py` | ✅ |
| Export audit service API complete | `test_phase50d_current_state_after_refactor_cleanup.py` | ✅ |
| Export service API complete | `test_phase50d_current_state_after_refactor_cleanup.py` | ✅ |
| `_resolve_runtime_snapshot_source` thin wrapper | `test_phase50d_current_state_after_refactor_cleanup.py` | ✅ |
| No fixture CSV changes | `test_phase50d_current_state_after_refactor_cleanup.py` | ✅ |

---

## Why This Restores Test-Suite Trust

The Phase 49D tests were written as **transitional characterization tests** — they captured intermediate states during a multi-phase extraction. After Phase 49D-3D and Phase 50C-3, the intermediate states they asserted became **false negatives** (tests that fail not because the code is wrong, but because the tests describe a state that no longer exists).

These false negatives erode trust in the test suite because:
1. Every CI run shows failures that are not real bugs
2. Real regressions could be hidden in the noise
3. Engineers learn to ignore or skip the failing tests

By replacing these with **current-state assertions**, the tests now verify what is actually true today, and will fail if a future change accidentally reintroduces direct `record_export` calls or removes `check_runtime_allowed`.

---

## Guardrails Preserved

- ✅ No production code changed
- ✅ No financial formula changes
- ✅ No runtime calculation changes
- ✅ No model output changes
- ✅ No route behavior changes
- ✅ No export behavior changes
- ✅ No fixture CSV changes
- ✅ No schema/migrations
- ✅ No JS financial calculations
- ✅ G20 BLOCKED · R99/R102 NOT APPROVED
- ✅ partial_pay_sweep not promoted · flat/min DSCR not promoted
- ✅ Backend remains source of truth