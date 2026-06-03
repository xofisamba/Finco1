# Phase 52D — Persistence Behavior Characterization Plan

**Base SHA:** `ba992223f3a9c2fd7aeeb966f49a7eebcced39ec`
**Phase:** 52D — read-only planning
**Type:** docs/report/test only
**Status:** PLANNING. No runtime code changes. No refactor.

## 1. Scope

This document converts Phase 52B's 12 must-pin items and Phase 52C's split-group recommendations into a **concrete behavior-characterization plan** for Phase 53. For each must-pin item, it identifies the owning function(s), the existing tests that likely cover it, the gaps, the recommended new characterization test file, the priority, and whether the pin is required before Phase 53 begins.

The plan is the green-light checklist that determines which persistence functions are safe to refactor in which order. It is the last deliverable in Phase 52D before Phase 52E converts it into an execution plan.

## 2. Source evidence

- **52A** (PR #422): function inventory of `app/persistence/repository.py` (61 functions, 22 write, 16 read, 5 mixed, 18 helper) and 4 sibling modules.
- **52B** (PR #423): side-effect matrix for 15 write functions, 7 high-risk writes, 12 must-pin items, 4 metadata columns.
- **52C** (PR #424): caller graph (27 functions, 4 production files with direct imports, 19 files with calls), 6 split groups (A-F), 11 single-owner zones, 3 parallel-safe zones, 4 do-not-parallelize zones.

## 3. The 7 high-risk writes (must characterize before Phase 53)

1. `save_project` (L686, projects, write, 117 LOC)
2. `save_workspace_state` (L1496, workspace_state, write, 131 LOC)
3. `save_scenario` (L1116, scenarios, write, 63 LOC)
4. `add_scenario` (L1299, scenarios, write, 80 LOC)
5. `record_export` (L1713, exports, write, 60 LOC)
6. `update_scenario_overrides` (L1411, scenarios, write, 47 LOC)
7. `get_or_create_base_case_scenario` (L86, scenarios, write, 85 LOC)

## 4. The 12 must-pin items (from Phase 52B)

| # | Function | Aspects to pin |
|---:|---|---|
| 1 | `save_project` | INSERT path, UPDATE path, replay_metadata.project_id defaulting, governance_state preservation |
| 2 | `save_workspace_state` | INSERT path, UPDATE path, replay_metadata merge with existing, last_runtime_* field preservation |
| 3 | `save_scenario` | replay_metadata.project_id and scenario_id defaulting |
| 4 | `add_scenario` | replay_metadata.action=add_scenario, parent_scenario_id storage, is_base_case=0, schema_version=1.0 |
| 5 | `record_export` | replay_metadata.export_id, runtime_snapshot_id, export_timestamp defaulting |
| 6 | `update_scenario_overrides` | is_base_case gate, SCENARIO_INPUT_FIELDS filter, re-resolved snapshot |
| 7 | `select_scenario` | replay_metadata.action=select_scenario, active_scenario_name resolution |
| 8 | `discard_workspace_draft` | draft_snapshot=saved_snapshot, dirty=False, all other fields preserved |
| 9 | `record_workspace_runtime` | last_runtime_scenario_id only set if runtime_origin==saved_state |
| 10 | `bind_workspace_to_scenario` | draft_snapshot=saved_snapshot=record.snapshot, dirty=False |
| 11 | `update_scenario_last_run_summary` | replay_metadata merge with existing |
| 12 | `duplicate_scenario` | copied_from_scenario_id=source.scenario_id, governance_state copied verbatim |

## 5. Behavior characterization matrix

For each of the 12 must-pin items: current behavior, owning function, callers, metadata fields, ordering, existing tests, missing tests, recommended test file, priority, required before Phase 53.

### 5.1 Item 1 — `save_project` (4 aspects)

- **Current behavior:** SELECT existing row by `(user_id, project_code)`. If exists, UPDATE the row with new values while preserving `project_id, created_at`. If not, INSERT a new row with a generated id. Default `replay_metadata.project_id` if missing. Preserve existing `governance_state` if not given.
- **Owning function:** `save_project` (L686-802, 117 LOC, write)
- **Caller services / routes:** `app/services/projects_create_service.py`, `app/services/project_save_as_service.py`, `app/services/scenarios_save_service.py`, `app/services/scenarios_add_service.py`, `main_web.py`
- **Metadata fields involved:** `project_id, created_at, project_type, project_origin, template_source, baseline_snapshot_json, archived, is_readonly, governance_state_json, last_run_summary_json, replay_metadata_json, updated_at`
- **Ordering dependencies:** none enforced at this layer; caller is responsible for ordering
- **Existing tests that likely cover it:** `tests/test_phase17_new_project_foundation.py`, `tests/test_phase20a_saved_baseline_models.py`, `tests/test_phase20a_saved_baseline_models_web.py`, `tests/test_phase51m1_projects_create_route_golden_characterization.py`, `tests/test_phase51o1_project_save_as_route_golden_characterization.py`
- **Missing tests:** explicit INSERT path test (current tests focus on the UPDATE path or end-to-end); explicit `replay_metadata.project_id` defaulting test; explicit `governance_state` preservation test
- **Recommended new test file:** `tests/test_phase52d_persistence_save_project_pin.py`
- **Priority:** **P0** (must be in place before Phase 53)
- **Required before Phase 53:** yes

### 5.2 Item 2 — `save_workspace_state` (4 aspects)

- **Current behavior:** SELECT existing row by `(user_id, project_id)`. If exists, UPDATE while preserving `workspace_id, created_at` and merging `replay_metadata` with existing. If not, INSERT a new row. Preserve `last_runtime_*` fields if not given. Preserve `governance_state` if not given.
- **Owning function:** `save_workspace_state` (L1496-1626, 131 LOC, write)
- **Caller services / routes:** `app/services/scenarios_save_service.py`, `app/services/scenario_state_route_service.py`, `app/services/scenario_select_service.py` (via `select_scenario`), `app/services/scenario_rename_service.py`, `bind_workspace_to_scenario` (wrapper), `select_scenario` (caller), `discard_workspace_draft` (wrapper), `record_workspace_runtime` (caller)
- **Metadata fields involved:** `workspace_id, created_at, project_code, active_scenario_id, active_scenario_name, draft_snapshot_json, saved_snapshot_json, last_runtime_snapshot_json, last_runtime_summary_json, last_runtime_snapshot_id, last_runtime_origin, last_runtime_scenario_id, last_runtime_at, dirty, governance_state_json, replay_metadata_json, updated_at`
- **Ordering dependencies:** central convergence point — wrappers depend on this function
- **Existing tests that likely cover it:** `tests/test_phase20f_active_scenario_runtime_binding.py`, `tests/test_phase51h1_scenario_state_route_family_characterization.py`, `tests/test_phase51h2_scenario_state_route_family_vertical_extraction.py`, `tests/test_phase51j1_scenarios_save_route_golden_characterization.py`
- **Missing tests:** explicit INSERT path test; explicit `replay_metadata` merge test (key+value pairs from existing preserved unless overridden); explicit `last_runtime_*` field preservation test (calling with `last_runtime_summary=None` should keep the existing value)
- **Recommended new test file:** `tests/test_phase52d_persistence_save_workspace_state_pin.py`
- **Priority:** **P0** (must be in place before Phase 53)
- **Required before Phase 53:** yes

### 5.3 Item 3 — `save_scenario` (2 aspects)

- **Current behavior:** INSERT only. Default `replay_metadata.project_id` and `scenario_id` if missing. `archived=0` always.
- **Owning function:** `save_scenario` (L1116-1178, 63 LOC, write)
- **Caller services / routes:** `add_scenario` (within module), `duplicate_scenario` (within module), `app/services/scenarios_save_service.py`, `main_web.py`
- **Metadata fields involved:** `scenario_id, project_id, user_id, scenario_name, project_code, source_project_template, copied_from_scenario_id, archived, snapshot_json, governance_state_json, last_run_summary_json, replay_metadata_json, created_at, updated_at`
- **Ordering dependencies:** must be called after project exists (uses `project_id`)
- **Existing tests that likely cover it:** `tests/test_phase20b_scenario_data_model.py`, `tests/test_phase32_scenario_persistence_versioning_foundation.py`
- **Missing tests:** explicit `replay_metadata.project_id` defaulting test; explicit `replay_metadata.scenario_id` defaulting test; explicit `archived=0` invariant test
- **Recommended new test file:** `tests/test_phase52d_persistence_save_scenario_pin.py`
- **Priority:** **P0** (must be in place before Phase 53)
- **Required before Phase 53:** yes

### 5.4 Item 4 — `add_scenario` (4 aspects)

- **Current behavior:** resolve effective snapshot via `resolve_scenario_snapshot`. INSERT a non-base scenario with `is_base_case=0`, `parent_scenario_id` set, `replay_metadata.action="add_scenario"`, `schema_version='1.0'`. The `parent_scenario_id` is stored verbatim (not validated to exist).
- **Owning function:** `add_scenario` (L1299-1378, 80 LOC, write)
- **Caller services / routes:** `app/services/scenarios_add_service.py`, `main_web.py`
- **Metadata fields involved:** `scenario_id, project_id, user_id, scenario_name, project_code, source_project_template="", copied_from_scenario_id=NULL, archived=0, is_base_case=0, parent_scenario_id, base_input_set_json, overrides_json, snapshot_json, governance_state_json, last_run_summary_json, replay_metadata_json, schema_version='1.0', created_at, updated_at`
- **Ordering dependencies:** must be called after parent scenario exists (but `parent_scenario_id` is stored verbatim)
- **Existing tests that likely cover it:** `tests/test_phase51l1_scenario_add_route_golden_characterization.py`, `tests/test_phase51l2_scenarios_add_route_vertical_extraction.py`
- **Missing tests:** explicit `replay_metadata.action="add_scenario"` tag test; explicit `parent_scenario_id` verbatim storage test (test with non-existent parent_id and confirm it still writes); explicit `is_base_case=0` invariant test; explicit `schema_version='1.0'` test
- **Recommended new test file:** `tests/test_phase52d_persistence_add_scenario_pin.py`
- **Priority:** **P0** (must be in place before Phase 53)
- **Required before Phase 53:** yes

### 5.5 Item 5 — `record_export` (3 aspects)

- **Current behavior:** INSERT only. Default `replay_metadata.project_id, scenario_id, export_id, runtime_snapshot_id, export_timestamp` if missing.
- **Owning function:** `record_export` (L1713-1772, 60 LOC, write)
- **Caller services / routes:** `app/services/export_audit_service.py`, `main_web.py`
- **Metadata fields involved:** `export_id, scenario_id, project_id, user_id, export_type, artifact_name, artifact_path, project_code, governance_state_json, runtime_snapshot_id, replay_metadata_json, created_at`
- **Ordering dependencies:** none enforced
- **Existing tests that likely cover it:** `tests/test_phase49d3a_export_audit_recording_characterization.py`, `tests/test_phase12_audit_replay_metadata_hardening.py`, `tests/test_phase14_*.py`
- **Missing tests:** explicit `replay_metadata.export_id` defaulting test; explicit `replay_metadata.runtime_snapshot_id` defaulting test; explicit `replay_metadata.export_timestamp` defaulting test
- **Recommended new test file:** `tests/test_phase52d_persistence_record_export_pin.py`
- **Priority:** **P0** (must be in place before Phase 53)
- **Required before Phase 53:** yes

### 5.6 Item 6 — `update_scenario_overrides` (3 aspects)

- **Current behavior:** read scenario. If `is_base_case`, return `None` (gate). Else merge existing `overrides` with new ones (new wins), filter to `SCENARIO_INPUT_FIELDS`, re-resolve snapshot via `resolve_scenario_snapshot`. UPDATE `overrides_json, snapshot_json, updated_at`. `replay_metadata` is **not** touched at this layer.
- **Owning function:** `update_scenario_overrides` (L1411-1457, 47 LOC, write)
- **Caller services / routes:** `app/services/scenario_update_overrides_service.py`, `main_web.py`
- **Metadata fields involved:** `overrides_json, snapshot_json, updated_at` (and the in-memory ScenarioRecord: `overrides, snapshot, updated_at`)
- **Ordering dependencies:** must be called after scenario exists
- **Existing tests that likely cover it:** `tests/test_phase51r1_scenario_update_overrides_route_golden_characterization.py`, `tests/test_phase51r2_scenario_update_overrides_route_vertical_extraction.py`
- **Missing tests:** explicit `is_base_case` gate test (return None, no DB write); explicit `SCENARIO_INPUT_FIELDS` filter test (unknown keys silently dropped); explicit re-resolved snapshot test (merged overrides + base_input_set produces the right snapshot)
- **Recommended new test file:** `tests/test_phase52d_persistence_update_scenario_overrides_pin.py`
- **Priority:** **P0** (must be in place before Phase 53)
- **Required before Phase 53:** yes

### 5.7 Item 7 — `select_scenario` (2 aspects)

- **Current behavior:** read scenario + read workspace. If either is None, return False. Call `save_workspace_state` with `active_scenario_id, active_scenario_name, draft_snapshot=existing.draft_snapshot, saved_snapshot=existing.saved_snapshot or existing.draft_snapshot, governance_state=existing.governance_state, replay_metadata={"action":"select_scenario","scenario_id":...}`.
- **Owning function:** `select_scenario` (L1460-1483, 24 LOC, write)
- **Caller services / routes:** `app/services/scenario_select_service.py`, `main_web.py`
- **Metadata fields involved:** `active_scenario_id, active_scenario_name, draft_snapshot_json, saved_snapshot_json, governance_state_json, replay_metadata_json`
- **Ordering dependencies:** must be called after both scenario and workspace exist
- **Existing tests that likely cover it:** `tests/test_phase51s1_scenario_select_route_golden_characterization.py`
- **Missing tests:** explicit `replay_metadata.action="select_scenario"` test; explicit fallback when `saved_snapshot` is None (use draft_snapshot); explicit False return when scenario or workspace not found
- **Recommended new test file:** `tests/test_phase52d_persistence_select_scenario_pin.py`
- **Priority:** **P0** (must be in place before Phase 53)
- **Required before Phase 53:** yes

### 5.8 Item 8 — `discard_workspace_draft` (3 aspects)

- **Current behavior:** read workspace. If None, return None. Call `save_workspace_state` with `draft_snapshot=saved_snapshot, dirty=False` and all other fields preserved (last_runtime_*, governance_state, replay_metadata, last_runtime_at).
- **Owning function:** `discard_workspace_draft` (L1651-1672, 22 LOC, write)
- **Caller services / routes:** `app/services/scenario_state_route_service.py` (state/discard), `main_web.py`
- **Metadata fields involved:** all workspace_state fields preserved; only `draft_snapshot_json` and `dirty` change
- **Ordering dependencies:** must be called after workspace exists
- **Existing tests that likely cover it:** `tests/test_phase51h1_scenario_state_route_family_characterization.py`
- **Missing tests:** explicit `draft=saved` test; explicit `dirty=False` test; explicit preservation of `last_runtime_summary`, `last_runtime_snapshot_id`, `last_runtime_origin`, `last_runtime_scenario_id`
- **Recommended new test file:** `tests/test_phase52d_persistence_discard_workspace_draft_pin.py`
- **Priority:** **P1** (helpful but Phase 53 can start without it; the existing test coverage is moderate)
- **Required before Phase 53:** optional

### 5.9 Item 9 — `record_workspace_runtime` (1 aspect)

- **Current behavior:** read workspace. Compute `saved_snapshot, draft_snapshot, dirty` from existing (or default to runtime_snapshot). Call `save_workspace_state` with all last_runtime_* fields. `last_runtime_scenario_id` is **only** set if `runtime_origin=="saved_state"`, else None.
- **Owning function:** `record_workspace_runtime` (L1675-1710, 36 LOC, write)
- **Caller services / routes:** `app/services/save_run_service.py`, `main_web.py`
- **Metadata fields involved:** `last_runtime_snapshot, last_runtime_summary, last_runtime_snapshot_id, last_runtime_origin, last_runtime_scenario_id (gated), last_runtime_at`
- **Ordering dependencies:** must be called after workspace exists
- **Existing tests that likely cover it:** `tests/test_phase13_editable_grid_*.py`, `tests/test_phase20f_active_scenario_runtime_binding.py`
- **Missing tests:** explicit `last_runtime_scenario_id` gate test (only set when `runtime_origin=="saved_state"`)
- **Recommended new test file:** `tests/test_phase52d_persistence_record_workspace_runtime_pin.py`
- **Priority:** **P1** (helpful but Phase 53 can start without it)
- **Required before Phase 53:** optional

### 5.10 Item 10 — `bind_workspace_to_scenario` (2 aspects)

- **Current behavior:** wrapper around `save_workspace_state`. Sets `active_scenario_id=record.scenario_id, active_scenario_name=record.scenario_name, draft_snapshot=record.snapshot, saved_snapshot=record.snapshot, dirty=False, governance_state=record.governance_state`.
- **Owning function:** `bind_workspace_to_scenario` (L1629-1648, 20 LOC, write)
- **Caller services / routes:** `app/services/scenario_state_route_service.py` (state/draft + state/discard), `main_web.py`
- **Metadata fields involved:** all workspace_state fields; the in-memory ScenarioRecord: `scenario_id, scenario_name, snapshot, governance_state`
- **Ordering dependencies:** must be called after scenario exists
- **Existing tests that likely cover it:** `tests/test_phase20f_active_scenario_runtime_binding.py`
- **Missing tests:** explicit `draft=saved=record.snapshot` test; explicit `dirty=False` test
- **Recommended new test file:** `tests/test_phase52d_persistence_bind_workspace_to_scenario_pin.py`
- **Priority:** **P1** (helpful but Phase 53 can start without it)
- **Required before Phase 53:** optional

### 5.11 Item 11 — `update_scenario_last_run_summary` (1 aspect)

- **Current behavior:** read scenario. If None, return False. Merge `replay_metadata` with existing. UPDATE `last_run_summary_json, replay_metadata_json, updated_at`.
- **Owning function:** `update_scenario_last_run_summary` (L1381-1408, 28 LOC, write)
- **Caller services / routes:** `app/services/save_run_service.py`, `main_web.py`
- **Metadata fields involved:** `last_run_summary_json, replay_metadata_json, updated_at`
- **Ordering dependencies:** must be called after scenario exists
- **Existing tests that likely cover it:** `tests/test_phase51g1_save_run_route_golden_characterization.py`
- **Missing tests:** explicit `replay_metadata` merge test (existing keys preserved unless overridden)
- **Recommended new test file:** `tests/test_phase52d_persistence_update_scenario_last_run_summary_pin.py`
- **Priority:** **P1** (helpful but Phase 53 can start without it)
- **Required before Phase 53:** optional

### 5.12 Item 12 — `duplicate_scenario` (2 aspects)

- **Current behavior:** read source. If None, return None. Call `save_scenario` with `copied_from_scenario_id=source.scenario_id`, copy `governance_state` and `replay_metadata` verbatim.
- **Owning function:** `duplicate_scenario` (L1280-1296, 17 LOC, write)
- **Caller services / routes:** `app/services/scenario_duplicate_service.py`, `main_web.py`
- **Metadata fields involved:** all scenario fields; `copied_from_scenario_id`; `governance_state` and `replay_metadata` copied from source
- **Ordering dependencies:** must be called after source exists
- **Existing tests that likely cover it:** `tests/test_phase51k1_scenario_duplicate_route_golden_characterization.py`
- **Missing tests:** explicit `copied_from_scenario_id=source.scenario_id` test; explicit governance_state verbatim copy test
- **Recommended new test file:** `tests/test_phase52d_persistence_duplicate_scenario_pin.py`
- **Priority:** **P1** (helpful but Phase 53 can start without it)
- **Required before Phase 53:** optional

## 6. Already sufficiently covered

The following 5 must-pin items are **already sufficiently covered** by existing tests. They do not need new characterization tests:

| Must-pin item | Existing coverage |
|---|---|
| `add_scenario` replay_metadata.action | `tests/test_phase51l1_scenario_add_route_golden_characterization.py` |
| `select_scenario` False return | `tests/test_phase51s1_scenario_select_route_golden_characterization.py` |
| `discard_workspace_draft` draft=saved | `tests/test_phase51h1_scenario_state_route_family_characterization.py` |
| `update_scenario_last_run_summary` replay_metadata merge | `tests/test_phase51g1_save_run_route_golden_characterization.py` |
| `duplicate_scenario` copied_from_scenario_id | `tests/test_phase51k1_scenario_duplicate_route_golden_characterization.py` |

These are listed here for completeness but they do not block Phase 53.

## 7. Must add before Phase 53 (P0)

The following 7 must-pin items require new characterization tests before Phase 53 begins:

1. `save_project` — INSERT path + UPDATE path + replay_metadata.project_id defaulting + governance_state preservation
2. `save_workspace_state` — INSERT path + UPDATE path + replay_metadata merge + last_runtime_* field preservation
3. `save_scenario` — replay_metadata.project_id + scenario_id defaulting
4. `add_scenario` — replay_metadata.action="add_scenario" + parent_scenario_id storage + is_base_case=0 + schema_version='1.0'
5. `record_export` — replay_metadata.export_id + runtime_snapshot_id + export_timestamp defaulting
6. `update_scenario_overrides` — is_base_case gate + SCENARIO_INPUT_FIELDS filter + re-resolved snapshot
7. `select_scenario` — replay_metadata.action="select_scenario" + active_scenario_name resolution

These 7 cover the 7 high-risk writes from section 3 (one-to-one). They are the **minimum gate** before any Phase 53 refactor touches a Group B (scenarios), Group C (workspace_state), or Group A (projects) function.

## 8. Defer until specific refactor group (P1)

The following 5 must-pin items can wait until the corresponding Phase 53 group is actually being refactored:

| Must-pin item | Defer until group | Why deferrable |
|---|---|---|
| `discard_workspace_draft` | C (workspace_state) | Existing route-level test covers the surface behavior; pin only matters when the function is moved |
| `record_workspace_runtime` | C (workspace_state) | Same; existing tests cover the surface |
| `bind_workspace_to_scenario` | C (workspace_state) | Same |
| `update_scenario_last_run_summary` | B (scenarios) | Same |
| `duplicate_scenario` | B (scenarios) | Same |

These 5 are all wrappers or single-table writes with well-characterized surface behavior. They do not need dedicated persistence-level pins until Phase 53 actually moves them.

## 9. Phase 53 group test gates

For each Phase 53 group, the minimum test gate that must be in place before the group is touched:

| Group | Functions | Required test gate |
|---|---|---|
| **F (helpers)** | 9 pure functions | No new test needed — refactor is invisible if signatures are preserved |
| **D (runs)** | 5 functions | No new test needed — narrow caller surface (1 service + 1 route); existing tests cover it |
| **E (exports + audit)** | 11 functions | No new test needed — `record_export` is already covered by Phase 49 audit tests; `build_export_lineage` and `list_exports` are covered by Phase 14 lineage tests |
| **A (projects)** | 15 functions | **Must have** the `save_project` P0 pin (must-pin item 1) before any project function moves |
| **C (workspace_state)** | 7 functions | **Must have** the `save_workspace_state` P0 pin (must-pin item 2) before any workspace function moves; P1 pins for the 3 wrappers can be added when each wrapper is actually moved |
| **B (scenarios)** | 17 functions | **Must have** the P0 pins for `save_scenario`, `add_scenario`, `update_scenario_overrides`, `select_scenario`, `get_or_create_base_case_scenario` (must-pin items 3, 4, 6, 7 + the `get_or_create_base_case_scenario` high-risk write); P1 pins for `duplicate_scenario`, `update_scenario_last_run_summary` can be added when each is moved |

## 10. User sign-off required

The following items require explicit user sign-off before Phase 53 begins, because they cross a behavior boundary that Phase 51F guardrails do not cover:

| Item | Reason |
|---|---|
| Refactor of `save_project` (Group A) | The function combines project + baseline_snapshot + governance_state in one transaction; refactor could accidentally split the transaction |
| Refactor of `save_workspace_state` (Group C) | The function is the central convergence point; refactor could break 4 wrappers in cascade |
| Refactor of `add_scenario` (Group B) | The function writes scenario + base_input_set + overrides + governance_state + replay_metadata in one INSERT; refactor could split these |
| Refactor of `update_scenario_overrides` (Group B) | The function has a `is_base_case` gate and a `SCENARIO_INPUT_FIELDS` filter; refactor could break the gate or the filter |
| Refactor of `get_or_create_base_case_scenario` (Group B) | The function has idempotent-or-create semantics; refactor could break the idempotency |
| Refactor of `record_export` (Group E) | The function is the only entry point for the audit pipeline; refactor could break the export_type enum or replay_metadata defaulting |
| Any change to the `replay_metadata` shape | This column is consumed by 13 write functions and many tests; any change is a major migration |

## 11. Red flags requiring user sign-off

The following are red flags. If any of them is observed during Phase 53, the work must stop and the user must be consulted before continuing:

1. Any new test failure in a P0 pin file
2. Any new test failure in `test_phase51f_parallel_work_guardrails.py`
3. Any `git diff` that touches `app/waterfall_core.py`, `app/project_factories.py`, parity-core, schema, JS, or fixture CSVs
4. Any change to the `replay_metadata` shape
5. Any change to the `governance_state` shape
6. Any change to the `SCENARIO_INPUT_FIELDS` set
7. Any change to the `_init_schema` function in `app/persistence/db.py`
8. Any new import of `sqlite3` or `sqlalchemy` outside `app/persistence/*`
9. Any new direct DB connection opened outside `app/persistence/*`
10. Any merge of a Phase 53 PR that wasn't based on a clean 52G closeout
11. Any merge where the diff includes unexpected production code (e.g., a model change bundled with a persistence split)

## 12. Mapping from high-risk writes to required tests

| High-risk write | Required test file (from section 5) | Required before Phase 53? |
|---|---|---|
| `save_project` | `tests/test_phase52d_persistence_save_project_pin.py` | yes |
| `save_workspace_state` | `tests/test_phase52d_persistence_save_workspace_state_pin.py` | yes |
| `save_scenario` | `tests/test_phase52d_persistence_save_scenario_pin.py` | yes |
| `add_scenario` | `tests/test_phase52d_persistence_add_scenario_pin.py` | yes |
| `record_export` | `tests/test_phase52d_persistence_record_export_pin.py` | yes |
| `update_scenario_overrides` | `tests/test_phase52d_persistence_update_scenario_overrides_pin.py` | yes |
| `get_or_create_base_case_scenario` | (no dedicated pin file; covered by `tests/test_phase20b_scenario_data_model.py` + new pin in `tests/test_phase52d_persistence_save_scenario_pin.py`) | yes (covered via Group B) |

## 13. Summary

- 7 P0 must-pin items identified for the 7 high-risk writes
- 5 P1 deferrable items identified
- 5 already-sufficiently-covered items
- 7 P0 characterization test files recommended (`tests/test_phase52d_persistence_*.py`)
- Minimum Phase 53 test gates per group: F (none), D (none), E (none), A (1 pin), C (1 pin), B (5 pins)
- 7 user sign-off items identified
- 11 red flags identified that would halt Phase 53

## 14. Recommended next step

**Phase 52E — Persistence hotspot / Phase 53 execution plan.** Convert the characterization plan into an execution plan: for each of the 6 Phase 53 groups, define the objective, the functions to move, the dependencies, the expected changed files, the compatibility façade, the rollback plan, and the estimated duration.
