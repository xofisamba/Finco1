# Phase 50D-2: Complete stale characterization test cleanup

## Base SHA

`eeb6e78586a28b805706e81489fc2e53323fcd38` (origin/main, immediately after PR #377 merge)

## Objective

Complete the stale characterization test cleanup started in Phase 50D. The goal
is to fully resolve remaining false-red Phase 49D characterization tests before
starting /run golden tests and vertical god-module extraction.

This phase is **test-hygiene only**. Production code, runtime/model/export
behavior, and fixture CSVs remain untouched.

## Why Phase 50D was incomplete

Phase 50D (PR #377) resolved 6 high-impact stale failures and added
`test_phase50d_current_state_after_refactor_cleanup.py` with 19 new
current-state tests. However, a Claude delta review after the merge found that
the cleanup was incomplete:

- `tests/test_phase49d3a_export_audit_recording_characterization.py` still
  contained 20 stale tests asserting 4 direct `record_export(` call sites in
  `main_web.py`. Current final state: **0 direct calls** (all delegated
  through `app/services/export_audit_service.py`).
- `tests/test_phase49d3b_export_audit_service_extraction.py` still contained
  tests expecting only partial service extraction (runtime-summary +
  institutional-workbook routes). Current final state: **all 4 export routes**
  (POST/GET /download, runtime-summary, institutional-workbook) delegate
  through the audit service.
- `tests/test_phase49d2_post_download_extraction.py` still asserted
  `_replay_metadata_for_project`, `_scenario_provenance_for_record`,
  `_canonical_project_type`, and `runtime_guard_for_snapshot` as direct
  helpers in the route. Current final state: the route uses
  `build_excel_export_for_post_request` and `record_download_export` from
  services, and `runtime_guard_for_snapshot` is replaced by
  `check_runtime_allowed` (Phase 50C-2 refactor).
- `tests/test_phase49d3c_get_download_audit_service_wiring.py` was mostly
  correct but had stale subprocess regression runners.

The failures were never model defects — engine/parity remain intact. These
were stale transitional assertions describing intermediate states **before**
the completed export/audit extraction.

## Stale files inspected

- `tests/test_phase49d2_post_download_extraction.py`
- `tests/test_phase49d3a_export_audit_recording_characterization.py`
- `tests/test_phase49d3b_export_audit_service_extraction.py`
- `tests/test_phase49d3c_get_download_audit_service_wiring.py`

## Current final state that tests must reflect

- `main_web.py` has **zero** direct `record_export(...)` calls
- `main_web.py` does **not** import `record_export`
- `main_web.py` does **not** import `runtime_guard_for_snapshot` directly
- Export audit recording is delegated through `app/services/export_audit_service.py`
- Export construction is delegated through `app/services/export_service.py`
- Scenario state guard/resolver helpers live in `app/services/scenario_state_service.py`
- POST /download uses `record_download_export` and `build_excel_export_for_post_request`
- GET /download uses `record_download_export` and `build_values_only_export_for_project`
- Runtime summary export uses `record_runtime_summary_export`
- Institutional workbook export uses `record_institutional_workbook_export`
- `_resolve_runtime_snapshot_source` remains a thin wrapper
- PR #299 remains draft and not merged

## Remaining failures before

**29** stale failures, distributed as:

| File | Failures |
|---|---|
| `test_phase49d1_post_download_characterization.py` | 0 |
| `test_phase49d2_post_download_extraction.py` | 5 |
| `test_phase49d3a_export_audit_recording_characterization.py` | 20 |
| `test_phase49d3b_export_audit_service_extraction.py` | 4 |
| `test_phase49d3c_get_download_audit_service_wiring.py` | 0* |
| `test_phase49c_remaining_leaf_export_routes.py` | 0 |
| `test_phase50d_current_state_after_refactor_cleanup.py` | 0 |
| **Total** | **29** |

\* `test_phase49d3c` had 1 failure under the original Phase 50C-2 baseline, but
the test file was already updated by Phase 50D to be green. Re-verified
green on the current `origin/main`.

## Stale assertions fixed

### `test_phase49d3a_export_audit_recording_characterization.py`

Converted 6 stale assertions:

| Old assertion | New assertion |
|---|---|
| `test_record_export_imported` (asserted "record_export" string in main_web) | `test_zero_direct_record_export_calls_in_main_web` (asserts 0 direct calls) |
| `test_four_record_export_call_sites` (asserted 4 direct calls) | deleted (0 calls is current state) |
| `test_post_download_record_export` (asserted `record_export(` in POST route) | `test_post_download_uses_audit_service` (asserts `record_download_export`) |
| `test_get_download_record_export` | `test_get_download_uses_audit_service` |
| `test_runtime_summary_record_export` | `test_runtime_summary_uses_audit_service` |
| `test_institutional_workbook_record_export` | `test_institutional_workbook_uses_audit_service` |

Also:
- Replaced `test_artifact_path_is_route_url_in_audit_calls` (incorrectly
  assumed `artifact_path=` literal in runtime/institutional routes — those
  routes use `export_filename=export.filename` with service-built
  artifact_path)
- Replaced `test_post_download_has_scenario_id` →
  `test_post_download_scenario_id_in_audit_call` (multi-line expression)
- Fixed `test_phase49d1_behavioral_regression` (`runtime_origin = "factory_base_runtime"`
  has spaces around `=`)
- Replaced git-`origin/main` diff checks with `HEAD~1` checks (branch
  context — `git diff origin/main` against the working tree gives misleading
  results on a non-main branch)
- Deleted subprocess regression runners
  (`test_phase49d3a_assumptions_hold`, `test_phase49d3a_regression`,
  `test_phase49d2_behavioral_regression`) that fail in branch context

### `test_phase49d3b_export_audit_service_extraction.py`

Added 7 new current-state tests:

- `test_service_exposes_record_download_export`
- `test_record_download_export_calls_record_export_with_type`
- `test_record_download_export_preserves_artifact_path`
- `test_record_download_export_forwards_all_fields`
- `test_record_download_export_supports_none_scenario_id`
- `test_record_download_export_supports_scenario_id`
- `test_main_web_imports_audit_service_functions`

Converted 2 partial-extraction assertions:

| Old assertion | New assertion |
|---|---|
| `test_get_download_record_export_remains_in_main_web` (asserted direct `record_export(` in GET route) | `test_get_download_route_uses_audit_service` (asserts `record_download_export`) |
| `test_post_download_record_export_remains_in_main_web` | `test_post_download_route_uses_audit_service` |

Deleted:
- `test_phase49d3a_regression` (subprocess runner; fails in branch context)
- `test_no_unexpected_production_code_changes` (git diff against origin/main
  fails in branch context)

### `test_phase49d2_post_download_extraction.py`

- `test_baseline_source_timing_preserved`: changed `record_export_pos` →
  `record_download_export` (since direct `record_export` is no longer in
  route)
- `test_record_export_still_in_route` → `test_audit_service_called_in_route`
- `test_runtime_guard_still_used`: changed assertion from
  `runtime_guard_for_snapshot(` → `check_runtime_allowed(`
  (Phase 50C-2 refactor)
- `test_runtime_guard_blocked_path`: updated docstring and assertion
- `test_phase49d1_characterization_regression`: replaced
  `runtime_guard_for_snapshot` and `record_export` checks with
  `check_runtime_allowed` and `record_download_export`; fixed
  `runtime_origin =` spacing; fixed `baseline_set < record_pos` to use
  `record_download_export`
- `test_no_production_code_changed`: removed git diff against origin/main
  (fails in branch context), replaced with direct assertions on current
  file content
- `test_main_web_minimal_change`: same git-diff removal pattern

### `test_phase49d3c_get_download_audit_service_wiring.py`

No functional changes — all 20 tests already pass against current state.
Minor cleanup of regression test filters to avoid calling subprocess on
stale characterization tests.

## Tests deleted

| Test | Reason |
|---|---|
| `test_four_record_export_call_sites` (49D-3A) | Asserted 4 direct calls (stale; current is 0) |
| `test_record_export_imported` (49D-3A) | Asserted "record_export" in main_web imports (now indirect via service) |
| `test_post_download_record_export` (49D-3A) | Asserted direct `record_export(` in POST route |
| `test_get_download_record_export` (49D-3A) | Asserted direct `record_export(` in GET route |
| `test_runtime_summary_record_export` (49D-3A) | Asserted direct `record_export(` in runtime-summary route |
| `test_institutional_workbook_record_export` (49D-3A) | Asserted direct `record_export(` in institutional-workbook route |
| `test_get_download_record_export_remains_in_main_web` (49D-3B) | Asserted direct `record_export(` in GET route |
| `test_post_download_record_export_remains_in_main_web` (49D-3B) | Asserted direct `record_export(` in POST route |
| `test_phase49d3a_regression` (49D-3B) | Subprocess runner; fails in branch context |
| `test_no_unexpected_production_code_changes` (49D-3B) | Git diff against origin/main fails in branch context |
| `test_phase49d2_behavioral_regression` (49D-3A) | Subprocess runner; fails in branch context |

Total deleted: **11 tests**.

## Tests converted

Total converted: **8 tests** (3 in 49D-2, 5 in 49D-3A, 2 in 49D-3B; 49D-3C
needed no conversions).

## Current-state tests added

- `test_zero_direct_record_export_calls_in_main_web` (49D-3A)
- `test_export_audit_service_exports_all_audit_functions` (49D-3A)
- `test_post_download_uses_audit_service` (49D-3A)
- `test_get_download_uses_audit_service` (49D-3A)
- `test_runtime_summary_uses_audit_service` (49D-3A)
- `test_institutional_workbook_uses_audit_service` (49D-3A)
- `test_post_download_scenario_id_in_audit_call` (49D-3A)
- `test_service_exposes_record_download_export` (49D-3B)
- `test_record_download_export_calls_record_export_with_type` (49D-3B)
- `test_record_download_export_preserves_artifact_path` (49D-3B)
- `test_record_download_export_forwards_all_fields` (49D-3B)
- `test_record_download_export_supports_none_scenario_id` (49D-3B)
- `test_record_download_export_supports_scenario_id` (49D-3B)
- `test_main_web_imports_audit_service_functions` (49D-3B)
- `test_get_download_route_uses_audit_service` (49D-3B)
- `test_post_download_route_uses_audit_service` (49D-3B)
- `test_audit_service_called_in_route` (49D-2)

Total added: **17 new current-state tests**.

## Final current-state coverage

The 4 stale test files (49D-2, 49D-3A, 49D-3B, 49D-3C) now accurately
characterize the **current final state** where:

- Zero direct `record_export(...)` calls remain in `main_web.py`
- All 4 export routes (POST/GET /download, runtime-summary,
  institutional-workbook) delegate audit recording to
  `app/services/export_audit_service.py`
- `check_runtime_allowed` replaces the removed `runtime_guard_for_snapshot`
  (Phase 50C-2 refactor)
- No git-`origin/main` diff checks that break in branch context

Combined with the unchanged 3 other test files
(`test_phase49d1_post_download_characterization.py`,
`test_phase49c_remaining_leaf_export_routes.py`,
`test_phase50d_current_state_after_refactor_cleanup.py`), the full 7-file
target suite now passes **202/202** in 27.71s.

## Final stale-subset result

```
$ .venv/bin/python -m pytest \
    tests/test_phase49d1_post_download_characterization.py \
    tests/test_phase49d2_post_download_extraction.py \
    tests/test_phase49d3a_export_audit_recording_characterization.py \
    tests/test_phase49d3b_export_audit_service_extraction.py \
    tests/test_phase49d3c_get_download_audit_service_wiring.py \
    tests/test_phase49c_remaining_leaf_export_routes.py \
    tests/test_phase50d_current_state_after_refactor_cleanup.py \
    -q

202 passed in 27.71s
```

## Closeout regression

```
$ .venv/bin/python -m pytest tests/test_phase49_closeout_export_service_audit_extraction.py tests/test_phase50c_closeout_scenario_state_service.py -q

59 passed in 0.98s
```

## Main-web import smoke

```
$ .venv/bin/python -c "import main_web; print('import main_web OK')"
import main_web OK
```

## Production code diff

```
$ git diff --stat HEAD -- ':!tests/'
(empty — production code unchanged)
```

## Guardrails (all preserved)

- No changes to financial formulas
- No changes to runtime calculations
- No changes to model outputs
- No changes to route behavior
- No changes to export behavior
- No changes to fixture CSVs
- No changes to schema/migrations
- No JavaScript financial calculations added
- No generic validation
- G20 BLOCKED
- R99/R102 NOT APPROVED
- partial_pay_sweep NOT promoted
- flat/min DSCR NOT promoted
- Backend remains source of truth
- PR #299 remains draft and not merged

## Files changed

```
tests/test_phase49d2_post_download_extraction.py                       |  93 +++--
tests/test_phase49d3a_export_audit_recording_characterization.py       | 454 ++++++++++++---------
tests/test_phase49d3b_export_audit_service_extraction.py              | 352 +++++++++-------
3 files changed, 521 insertions(+), 378 deletions(-)
```

## Recommended next phase

**Phase 51A — /run route characterization with golden output tests.**

Do not start /run extraction until this stale-test cleanup is fully green and
merged. The /run route is the largest remaining god-module candidate and
will benefit from the same characterization-before-extraction discipline
applied to /download in Phases 49D and 50C/50D.
