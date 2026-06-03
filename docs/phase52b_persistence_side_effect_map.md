# Phase 52B — Persistence Side-Effect Map

**Base SHA:** `5cffb6f21b07bd871bd222ca4cd1354fd4d58a0e` (post-52A main)
**Phase:** 52B — read-only mapping
**Type:** docs/report/test only
**Status:** MAPPING. No runtime code changes. No refactor.

## 1. Scope

This document maps the **write side effects** of the 15 highest-impact persistence functions in `app/persistence/repository.py`. It identifies what fields are written, what metadata is written, what commit/flush behavior is in effect, what ordering dependencies exist between functions, what idempotency risk exists, and whether each side effect is already pinned by a test.

The map is the prerequisite for any Phase 53 refactor of the persistence layer. Every write function listed here should be characterized in a behavior-preservation test before any code move.

## 2. Transactional model

`app/persistence/repository.py` has **no** explicit `cur.commit()` calls. All writes go through `with get_cursor() as cur:`. The transactional model is:

- `get_cursor` (in `app/persistence/db.py`) wraps a `sqlite3.Connection` in a context manager.
- On clean `__exit__`, `commit()` is invoked.
- On exception, `rollback()` is invoked.
- Connection is closed on `__exit__`.

Consequence: every `with get_cursor() as cur:` block is a **single transaction**. There are no nested transactions and no savepoints. A function that opens two `get_cursor()` blocks (no current function does this) would commit each block separately.

## 3. Side-effect matrix

For each write function, the matrix records: function name, file path:line, domain, callers (from Phase 52A), SQL/table target, fields written, metadata written, commit/flush behavior, error/fallback, idempotency risk, ordering dependencies, whether the side effect is already pinned by a test, and risk classification.

### 3.1 `save_project` (L686, projects, write, high-risk)

- **Callers:** `app/services/projects_create_service.py`, `app/services/project_save_as_service.py`, `app/services/scenarios_save_service.py`, `app/services/scenarios_add_service.py`, `main_web.py`, plus tests
- **Table:** `projects`
- **Operation:** SELECT existing → INSERT or UPDATE
- **Fields written (INSERT):** `user_id, project_code, project_name, project_type, source_project_template, project_origin, template_source, baseline_snapshot_json, archived, is_readonly, governance_state_json, last_run_summary_json, replay_metadata_json, created_at, updated_at`
- **Fields written (UPDATE):** `project_name, project_type, project_origin, source_project_template, template_source, baseline_snapshot_json, archived, is_readonly, governance_state_json, last_run_summary_json, replay_metadata_json, updated_at` (preserves `project_id, created_at`)
- **Metadata written:** `replay_metadata` (with `project_id` defaulted), `governance_state` (full dict)
- **Commit/flush:** implicit commit at end of `with get_cursor()` block
- **Error/fallback:** none visible; if SELECT-then-INSERT/UPDATE pattern fails partway, the function does not roll back the SELECT. Since SELECT is read-only, partial failure is impossible at this level.
- **Idempotency risk:** **low** for the same `(user_id, project_code)` — UPDATE re-uses existing row. New `project_id` is **not** generated on the UPDATE path (re-uses existing).
- **Ordering:** call ordering not enforced. Multiple concurrent saves of the same `(user_id, project_code)` are not serialized at this layer.
- **Pinned by tests:** yes — `tests/test_phase17_new_project_foundation.py`, `tests/test_phase20a_saved_baseline_models*.py`, `tests/test_phase51m*.py`, `tests/test_phase51o*.py`
- **Risk classification:** **high** — large body, multi-table implications, replay_metadata + governance_state writes

### 3.2 `save_workspace_state` (L1496, workspace_state, write, high-risk)

- **Callers:** `app/services/scenarios_save_service.py`, `app/services/scenario_state_route_service.py`, `app/services/scenario_select_service.py` (via `select_scenario`), `app/services/scenario_rename_service.py` (via workspace updates), `bind_workspace_to_scenario`, `select_scenario`, `discard_workspace_draft`, `record_workspace_runtime`, plus `main_web.py` and tests
- **Table:** `workspace_states`
- **Operation:** SELECT existing → INSERT or UPDATE
- **Fields written (UPDATE):** `project_code, active_scenario_id, active_scenario_name, draft_snapshot_json, saved_snapshot_json, last_runtime_snapshot_json, last_runtime_summary_json, last_runtime_snapshot_id, last_runtime_origin, last_runtime_scenario_id, last_runtime_at, dirty, governance_state_json, replay_metadata_json, updated_at`
- **Fields written (INSERT):** all of the above plus `workspace_id, user_id, project_id, created_at`
- **Metadata written:** `last_runtime_snapshot`, `last_runtime_summary`, `last_runtime_snapshot_id`, `last_runtime_origin`, `last_runtime_scenario_id`, `last_runtime_at`, `governance_state` (preserved from existing if not given), `replay_metadata` (merged with existing if present)
- **Commit/flush:** implicit commit at end of `with get_cursor()` block
- **Error/fallback:** none visible
- **Idempotency risk:** **low** for the same `(user_id, project_id)` — UPDATE re-uses existing row. `dirty` flag is preserved if not given.
- **Ordering dependency:** this function is the **central convergence point** — `bind_workspace_to_scenario`, `select_scenario`, `discard_workspace_draft`, `record_workspace_runtime` all call it.
- **Pinned by tests:** yes — `tests/test_phase20f_active_scenario_runtime_binding.py`, `tests/test_phase51h*.py`, `tests/test_phase51j*.py`, plus Phase 13/16 tests
- **Risk classification:** **high** — largest write function (131 LOC body), central convergence point, multi-field update

### 3.3 `save_scenario` (L1116, scenarios, write, high-risk)

- **Callers:** `add_scenario` (within same module), `duplicate_scenario` (within same module), `app/services/scenarios_save_service.py`, `main_web.py`, tests
- **Table:** `scenarios`
- **Operation:** INSERT only (no SELECT-then-update at this layer; the caller decides insert vs. no-op)
- **Fields written:** `scenario_id, project_id, user_id, scenario_name, project_code, source_project_template, copied_from_scenario_id, archived=0, snapshot_json, governance_state_json, last_run_summary_json, replay_metadata_json, created_at, updated_at`
- **Metadata written:** `replay_metadata` (with `project_id` and `scenario_id` defaulted)
- **Commit/flush:** implicit commit at end of `with get_cursor()` block
- **Error/fallback:** none visible
- **Idempotency risk:** **high** — generates a fresh `scenario_id` every call; calling twice creates two distinct rows. Caller must guarantee no duplicate (no UNIQUE constraint visible at this layer).
- **Ordering:** none enforced. Caller decides when to call.
- **Pinned by tests:** yes — `tests/test_phase20b_scenario_data_model.py`, `tests/test_phase32_scenario_persistence_versioning_foundation.py`, plus Phase 51k/l/m
- **Risk classification:** **high** — replay_metadata + governance_state writes, large body, no idempotency guard

### 3.4 `bind_workspace_to_scenario` (L1629, workspace_state, write, medium-risk)

- **Callers:** `app/services/scenario_state_route_service.py` (state/draft + state/discard), `main_web.py`, tests
- **Table:** `workspace_states` (via `save_workspace_state`)
- **Operation:** wrapper around `save_workspace_state` with a ScenarioRecord already in hand
- **Fields written:** `active_scenario_id=record.scenario_id, active_scenario_name=record.scenario_name, draft_snapshot=record.snapshot, saved_snapshot=record.snapshot, dirty=False, governance_state=record.governance_state`
- **Metadata written:** `replay_metadata` (caller-supplied)
- **Commit/flush:** via `save_workspace_state` (single transaction)
- **Error/fallback:** none
- **Idempotency risk:** **low** — re-binding the same scenario with the same snapshot is a no-op UPDATE
- **Ordering:** must be called **after** the scenario exists (uses `record.scenario_id` directly)
- **Pinned by tests:** yes — `tests/test_phase20f_active_scenario_runtime_binding.py`
- **Risk classification:** **medium** — small body, but the wrapper semantics are critical (binds a scenario to a workspace in one shot)

### 3.5 `save_run` (L608, runs, write, medium-risk)

- **Callers:** `app/services/save_run_service.py`, `main_web.py`, tests
- **Table:** `runs`
- **Operation:** INSERT only
- **Fields written:** `run_id, user_id, project_type, scenario, created_at, inputs_json, kpis_json, excel_path, notes, replay_metadata_json`
- **Metadata written:** `replay_metadata` (with `run_id` and `runtime_timestamp` defaulted)
- **Commit/flush:** implicit commit
- **Error/fallback:** none
- **Idempotency risk:** **low** — `run_id` is a fresh uuid hex; duplicate calls produce two rows. No upsert.
- **Ordering:** none enforced
- **Pinned by tests:** yes — `tests/test_phase12_audit_replay_metadata_hardening.py`, `tests/test_phase51g*.py`, plus `tests/test_project_persistence.py`
- **Risk classification:** **medium** — touches `replay_metadata` + `inputs` + `kpis`, isolated single-table write

### 3.6 `rename_scenario` (L1209, scenarios, write, low-risk)

- **Callers:** `app/services/scenario_rename_service.py`, `main_web.py`, tests
- **Table:** `scenarios`
- **Operation:** UPDATE only
- **Fields written:** `scenario_name, updated_at`
- **Metadata written:** none
- **Commit/flush:** implicit commit
- **Error/fallback:** returns `False` if no row updated (caller treats as 404 / "scenario not found")
- **Idempotency risk:** **low** — same name produces the same final state, but `updated_at` advances
- **Ordering:** none
- **Pinned by tests:** yes — `tests/test_phase51p1_scenario_rename_route_golden_characterization.py`
- **Risk classification:** **low** — single field, single table

### 3.7 `archive_scenario` (L1218, scenarios, write, low-risk)

- **Callers:** `app/services/scenario_archive_service.py`, `main_web.py`, tests
- **Table:** `scenarios`
- **Operation:** UPDATE only (soft archive — `archived=1`)
- **Fields written:** `archived, updated_at`
- **Metadata written:** none
- **Commit/flush:** implicit commit
- **Error/fallback:** returns `False` if no row updated
- **Idempotency risk:** **low** — archiving an already-archived scenario is a no-op (same final state, `updated_at` advances)
- **Ordering:** none
- **Pinned by tests:** yes — `tests/test_phase51q1_scenario_archive_route_golden_characterization.py`
- **Risk classification:** **low** — single field, soft delete

### 3.8 `select_scenario` (L1460, scenarios + workspace_state, write, medium-risk)

- **Callers:** `app/services/scenario_select_service.py`, `main_web.py`, tests
- **Table:** `workspace_states` (via `save_workspace_state`)
- **Operation:** read scenario + read workspace + write workspace (3 queries)
- **Fields written (workspace):** `active_scenario_id, active_scenario_name, draft_snapshot=existing.draft_snapshot, saved_snapshot=existing.saved_snapshot or existing.draft_snapshot, governance_state=existing.governance_state, replay_metadata={"action":"select_scenario","scenario_id":...}`
- **Metadata written:** `replay_metadata` (with action tag)
- **Commit/flush:** via `save_workspace_state` (single transaction)
- **Error/fallback:** returns `False` if scenario or workspace not found
- **Idempotency risk:** **low** — selecting the already-active scenario is a no-op (same final state)
- **Ordering:** must be called after both scenario and workspace exist
- **Pinned by tests:** yes — `tests/test_phase51s1_scenario_select_route_golden_characterization.py`
- **Risk classification:** **medium** — multi-query; ties scenarios ↔ workspace

### 3.9 `update_scenario_overrides` (L1411, scenarios, write, high-risk)

- **Callers:** `app/services/scenario_update_overrides_service.py`, `main_web.py`, tests
- **Table:** `scenarios`
- **Operation:** read scenario → merge overrides → resolve snapshot → UPDATE
- **Fields written:** `overrides_json, snapshot_json, updated_at`
- **Metadata written:** `replay_metadata` (NOT touched at this layer — only `overrides_json` and `snapshot_json`)
- **Commit/flush:** implicit commit
- **Error/fallback:** returns `None` if scenario not found; returns `None` if `record.is_base_case` (overrides are stored in `base_input_set` for base cases)
- **Idempotency risk:** **low** — patching with the same overrides produces the same final `overrides_json` and `snapshot_json`
- **Ordering:** none enforced
- **Pinned by tests:** yes — `tests/test_phase51r1_scenario_update_overrides_route_golden_characterization.py`
- **Risk classification:** **high** — gate (`is_base_case`), filter (`SCENARIO_INPUT_FIELDS`), re-resolve snapshot, multi-field update

### 3.10 `duplicate_scenario` (L1280, scenarios, write, medium-risk)

- **Callers:** `app/services/scenario_duplicate_service.py`, `main_web.py`, tests
- **Table:** `scenarios` (via `save_scenario`)
- **Operation:** read source → call `save_scenario` with copied fields + new name
- **Fields written:** see `save_scenario` (3.3), plus `copied_from_scenario_id=source.scenario_id`
- **Metadata written:** `replay_metadata` (copied from source)
- **Commit/flush:** via `save_scenario`
- **Error/fallback:** returns `None` if source not found
- **Idempotency risk:** **low** for the row (new `scenario_id`); caller controls the new name
- **Ordering:** must be called after source exists
- **Pinned by tests:** yes — `tests/test_phase51k1_scenario_duplicate_route_golden_characterization.py`
- **Risk classification:** **medium** — wraps `save_scenario`; copies governance_state and replay_metadata verbatim

### 3.11 `add_scenario` (L1299, scenarios, write, high-risk)

- **Callers:** `app/services/scenarios_add_service.py`, `main_web.py`, tests
- **Table:** `scenarios`
- **Operation:** resolve snapshot → INSERT (non-base, inherits from parent)
- **Fields written:** `scenario_id, project_id, user_id, scenario_name, project_code, source_project_template="", copied_from_scenario_id=NULL, archived=0, is_base_case=0, parent_scenario_id, base_input_set_json, overrides_json, snapshot_json, governance_state_json, last_run_summary_json, replay_metadata_json, schema_version='1.0', created_at, updated_at`
- **Metadata written:** `replay_metadata` (with `scenario_id` defaulted, `parent_scenario_id`, `action="add_scenario"`)
- **Commit/flush:** implicit commit
- **Error/fallback:** none
- **Idempotency risk:** **high** — fresh `scenario_id` per call; no UNIQUE constraint
- **Ordering:** must be called after parent scenario exists
- **Pinned by tests:** yes — `tests/test_phase51l1_scenario_add_route_golden_characterization.py`
- **Risk classification:** **high** — multi-table implications (parent + new row), replay_metadata + governance_state, large body

### 3.12 `record_export` (L1713, exports, write, high-risk)

- **Callers:** `app/services/export_audit_service.py`, `main_web.py`, tests
- **Table:** `scenario_exports`
- **Operation:** INSERT only
- **Fields written:** `export_id, scenario_id, project_id, user_id, export_type, artifact_name, artifact_path, project_code, governance_state_json, runtime_snapshot_id, replay_metadata_json, created_at`
- **Metadata written:** `replay_metadata` (with `project_id, scenario_id, export_id, runtime_snapshot_id, export_timestamp` defaulted)
- **Commit/flush:** implicit commit
- **Error/fallback:** none
- **Idempotency risk:** **low** for the row (new `export_id` per call)
- **Ordering:** none enforced
- **Pinned by tests:** yes — `tests/test_phase49d3a_export_audit_recording_characterization.py`, `tests/test_phase12_audit_replay_metadata_hardening.py`, `tests/test_phase14_*.py`
- **Risk classification:** **high** — touches `replay_metadata` + `governance_state` + `export_type`, single table but metadata-heavy

### 3.13 `record_workspace_runtime` (L1675, workspace_state, write, medium-risk)

- **Callers:** `app/services/save_run_service.py`, `main_web.py`, tests
- **Table:** `workspace_states` (via `save_workspace_state`)
- **Operation:** read workspace → call `save_workspace_state` with runtime fields
- **Fields written (workspace):** `last_runtime_snapshot, last_runtime_summary, last_runtime_snapshot_id, last_runtime_origin, last_runtime_scenario_id (only if runtime_origin=='saved_state'), last_runtime_at`
- **Metadata written:** `replay_metadata` (caller-supplied); `governance_state` (preserved from existing)
- **Commit/flush:** via `save_workspace_state` (single transaction)
- **Error/fallback:** none
- **Idempotency risk:** **low** — re-recording the same runtime is a no-op (same final state)
- **Ordering:** must be called after workspace exists
- **Pinned by tests:** yes — `tests/test_phase13_*.py`, `tests/test_phase20f_active_scenario_runtime_binding.py`
- **Risk classification:** **medium** — multi-field update, but wrapper semantics are clear

### 3.14 `discard_workspace_draft` (L1651, workspace_state, write, medium-risk)

- **Callers:** `app/services/scenario_state_route_service.py` (state/discard), `main_web.py`, tests
- **Table:** `workspace_states` (via `save_workspace_state`)
- **Operation:** read workspace → call `save_workspace_state` with draft = saved
- **Fields written (workspace):** `draft_snapshot=saved_snapshot, dirty=False` (all other fields preserved)
- **Metadata written:** `replay_metadata` (preserved from existing)
- **Commit/flush:** via `save_workspace_state` (single transaction)
- **Error/fallback:** returns `None` if workspace not found
- **Idempotency risk:** **low** — discarding an already-clean draft is a no-op
- **Ordering:** must be called after workspace exists
- **Pinned by tests:** yes — `tests/test_phase51h1_scenario_state_route_family_characterization.py`
- **Risk classification:** **medium** — semantic action is "reset draft to saved"

### 3.15 `update_scenario_last_run_summary` (L1381, scenarios, write, medium-risk)

- **Callers:** `app/services/save_run_service.py`, `main_web.py`, tests
- **Table:** `scenarios`
- **Operation:** read scenario → merge replay_metadata → UPDATE
- **Fields written:** `last_run_summary_json, replay_metadata_json, updated_at`
- **Metadata written:** `replay_metadata` (merged with existing)
- **Commit/flush:** implicit commit
- **Error/fallback:** returns `False` if scenario not found
- **Idempotency risk:** **low** — same `last_run_summary` produces same final state
- **Ordering:** must be called after scenario exists
- **Pinned by tests:** yes — `tests/test_phase51g1_save_run_route_golden_characterization.py`
- **Risk classification:** **medium** — touches two JSON columns

## 4. Write-function summary

| Function | Domain | Body LOC | Tables | Txns | Pinned |
|---|---|---:|---|---:|---|
| `save_project` | projects | 117 | `projects` | 1 | yes |
| `save_workspace_state` | workspace_state | 131 | `workspace_states` | 1 | yes |
| `save_scenario` | scenarios | 63 | `scenarios` | 1 | yes |
| `bind_workspace_to_scenario` | workspace_state | 20 | `workspace_states` (via wrapper) | 1 | yes |
| `save_run` | runs | 48 | `runs` | 1 | yes |
| `rename_scenario` | scenarios | 7 | `scenarios` | 1 | yes |
| `archive_scenario` | scenarios | 7 | `scenarios` | 1 | yes |
| `select_scenario` | scenarios+ws | 24 | `workspace_states` (via wrapper) | 1 | yes |
| `update_scenario_overrides` | scenarios | 47 | `scenarios` | 1 | yes |
| `duplicate_scenario` | scenarios | 17 | `scenarios` (via wrapper) | 1 | yes |
| `add_scenario` | scenarios | 80 | `scenarios` | 1 | yes |
| `record_export` | exports | 60 | `scenario_exports` | 1 | yes |
| `record_workspace_runtime` | workspace_state | 36 | `workspace_states` (via wrapper) | 1 | yes |
| `discard_workspace_draft` | workspace_state | 22 | `workspace_states` (via wrapper) | 1 | yes |
| `update_scenario_last_run_summary` | scenarios | 28 | `scenarios` | 1 | yes |

## 5. Metadata behavior summary

The persistence layer persists 8 metadata fields across 4 JSON columns:

| JSON column | Table(s) | Functions writing | Shape (inferred from grep) |
|---|---|---|---|
| `replay_metadata_json` | `projects`, `scenarios`, `runs`, `scenario_exports`, `workspace_states` | 13 (all write functions except `rename_scenario`, `archive_scenario`, `delete_run`, `update_scenario_overrides`, `update_scenario_last_run_summary` (partial)) | `{scenario_id?, project_id?, run_id?, export_id?, runtime_snapshot_id?, export_timestamp?, action?, parent_scenario_id?, runtime_timestamp?, user_id?}` |
| `governance_state_json` | `projects`, `scenarios`, `scenario_exports`, `workspace_states` | 8 (`save_project`, `save_scenario`, `record_export`, `save_workspace_state`, `bind_workspace_to_scenario`, `add_scenario`, `discard_workspace_draft`, `select_scenario`) | opaque dict (caller-supplied) |
| `last_run_summary_json` | `projects`, `scenarios` | 2 (`save_project`, `save_scenario`, `update_scenario_last_run_summary`) | opaque dict |
| `last_runtime_summary_json` | `workspace_states` | 1 (`save_workspace_state` via wrapper) | opaque dict |
| `snapshot_json` | `scenarios` | 3 (`save_scenario`, `update_scenario_overrides`, `duplicate_scenario` (via save_scenario)) | effective input-set dict |
| `overrides_json` | `scenarios` | 2 (`add_scenario`, `update_scenario_overrides`) | per-key dict, filtered by `SCENARIO_INPUT_FIELDS` |
| `base_input_set_json` | `scenarios` | 1 (`add_scenario`) | full input-set dict |
| `baseline_snapshot_json` | `projects` | 1 (`save_project`) | full input-set dict |

The `replay_metadata_json` column is **the single most-touched metadata column** — it is written or merged by 13 of the 15 write functions. Any refactor that changes its shape is a major migration.

## 6. Commit/flush summary

- All 15 write functions use `with get_cursor() as cur:` — **single transaction each**.
- 0 explicit `cur.commit()` calls in `repository.py`.
- 0 `cur.flush()` calls.
- 0 nested transactions.
- 0 savepoints.
- All 5 functions that "wrap" `save_workspace_state` (`bind_workspace_to_scenario`, `select_scenario`, `discard_workspace_draft`, `record_workspace_runtime`) participate in **one** transaction per call.
- Multi-query functions (`save_project`, `save_workspace_state`, `add_scenario`, `update_scenario_overrides`, `record_export`, `update_scenario_last_run_summary`, `select_scenario`, `record_workspace_runtime`, `discard_workspace_draft`, `bind_workspace_to_scenario`) all keep their multiple `cur.execute(...)` calls inside the same `with get_cursor()` block — so a partial failure rolls back all the writes.

## 7. Ordering dependencies

| Caller sequence | Required? | Why |
|---|---|---|
| `save_project` → `add_scenario` / `save_scenario` | yes | scenarios need `project_id` |
| `save_scenario` → `select_scenario` | yes | workspace needs the scenario row |
| `bind_workspace_to_scenario` | requires saved scenario | uses `record.scenario_id, scenario_name, snapshot, governance_state` |
| `record_workspace_runtime` | requires workspace | reads `existing = get_workspace_state(...)` |
| `discard_workspace_draft` | requires workspace | reads `record = get_workspace_state(...)` |
| `select_scenario` | requires both scenario and workspace | reads both, writes only workspace |
| `update_scenario_overrides` | requires scenario | reads `record = get_scenario(...)` |
| `update_scenario_last_run_summary` | requires scenario | reads `record = get_scenario(...)` |
| `duplicate_scenario` | requires source scenario | reads `record = get_scenario(...)` |
| `add_scenario` | requires parent scenario | `parent_scenario_id` written into row; existence not validated at this layer |
| `archive_scenario`, `rename_scenario` | requires scenario | returns False otherwise |
| `record_export` | none | scenario_id is optional in the row |

`add_scenario` does **not** validate that `parent_scenario_id` exists — it stores the id verbatim. A future refactor that splits this function should preserve this behavior (or make it explicit) to avoid breaking the test suite.

## 8. High-risk writes

The 7 highest-risk writes (must be characterized before any refactor):

1. **`save_project`** — 117 LOC, multi-field, replay_metadata + governance_state, INSERT-or-UPDATE branching
2. **`save_workspace_state`** — 131 LOC, central convergence point, last_runtime_* fields, governance_state preserved
3. **`save_scenario`** — INSERT only, no idempotency guard
4. **`add_scenario`** — multi-table implications, parent_scenario_id stored verbatim
5. **`record_export`** — single table but metadata-heavy, replay_metadata + governance_state + export_type
6. **`update_scenario_overrides`** — gate (`is_base_case`), filter (`SCENARIO_INPUT_FIELDS`), re-resolve snapshot
7. **`get_or_create_base_case_scenario`** (from Phase 52A) — 85 LOC, idempotent-or-create semantics, called by multiple services (re-listed here for completeness)

## 9. Must-pin-before-refactor list

Before **any** Phase 53 refactor that touches the persistence layer, the following must be pinned by behavior-preservation tests (or have existing tests confirmed to cover the side effect):

1. `save_project` — INSERT path + UPDATE path + `replay_metadata.project_id` defaulting + `governance_state` preservation
2. `save_workspace_state` — INSERT path + UPDATE path + `replay_metadata` merging with existing + `last_runtime_*` field preservation
3. `save_scenario` — `replay_metadata.project_id` and `scenario_id` defaulting
4. `add_scenario` — `replay_metadata.action="add_scenario"` + `parent_scenario_id` storage + `is_base_case=0` + `schema_version='1.0'`
5. `record_export` — `replay_metadata.export_id, runtime_snapshot_id, export_timestamp` defaulting
6. `update_scenario_overrides` — `is_base_case` gate + `SCENARIO_INPUT_FIELDS` filter + re-resolved snapshot
7. `select_scenario` — `replay_metadata.action="select_scenario"` + `active_scenario_name` resolution
8. `discard_workspace_draft` — `draft_snapshot=saved_snapshot` + `dirty=False` + all other fields preserved
9. `record_workspace_runtime` — `last_runtime_scenario_id` only set if `runtime_origin=='saved_state'`
10. `bind_workspace_to_scenario` — `draft_snapshot=saved_snapshot=record.snapshot` + `dirty=False`
11. `update_scenario_last_run_summary` — `replay_metadata` merging with existing
12. `duplicate_scenario` — `copied_from_scenario_id=source.scenario_id` + governance_state copied verbatim

## 10. Safe / low-risk functions

The following functions are **safe to refactor first** because their behavior is fully characterized and their bodies are simple:

- `rename_scenario` (7 LOC, single UPDATE)
- `archive_scenario` (7 LOC, single UPDATE)
- `delete_run` (4 LOC, single DELETE)
- `count_runs` (4 LOC, single SELECT COUNT)
- `get_run` (5 LOC, single SELECT)
- `get_scenario` (5 LOC, single SELECT)
- `get_project` (5 LOC, single SELECT)
- `get_workspace_state` (8 LOC, single SELECT)
- `get_project_record` (11 LOC, single SELECT)
- `get_project_by_code` (8 LOC, single SELECT)
- `list_projects` (7 LOC, single SELECT)
- `list_baseline_records` (8 LOC, single SELECT)
- `list_project_records` (13 LOC, single SELECT)
- `list_scenarios` (19 LOC, single SELECT)
- `list_runs` (7 LOC, single SELECT)
- `list_exports` (20 LOC, single SELECT)
- `get_scenario_history` (12 LOC, single SELECT)

## 11. Recommended Phase 52C input list

Phase 52C should map who calls these 15 write functions across `app/services/`, `main_web.py`, `main_api.py`, and `tests/`. Specifically:

- `save_project` callers and which path they hit (INSERT vs UPDATE)
- `save_workspace_state` direct callers and indirect callers (via wrappers)
- `save_scenario` direct callers and the duplicate/adds that wrap it
- `add_scenario` callers (single, but cross-domain)
- `select_scenario` callers and the workspace read pattern they assume
- `record_export` callers and the export_type enum they use
- `update_scenario_overrides` callers and the override shape they send

## 12. Recommended Phase 53 test priorities

If Phase 53 begins a refactor, the **first** test priorities are:

1. Pin `save_project` (INSERT path, UPDATE path, replay_metadata defaulting)
2. Pin `save_workspace_state` (INSERT path, UPDATE path, replay_metadata merge)
3. Pin `add_scenario` (parent_scenario_id + action tag)
4. Pin `record_export` (replay_metadata defaulting)
5. Pin `update_scenario_overrides` (gate + filter + re-resolve)
6. Pin `select_scenario` (action tag + workspace read)
7. Pin `discard_workspace_draft` (draft = saved + dirty=False)
8. Pin `record_workspace_runtime` (last_runtime_scenario_id gate)
9. Pin `bind_workspace_to_scenario` (draft = saved = record.snapshot)

## 13. Summary

- 15 write functions mapped
- All 15 use single-transaction `with get_cursor() as cur:` pattern
- All 15 are pinned by at least one test
- 7 high-risk writes identified for pre-refactor characterization
- 17 low-risk reads/single-field writes safe to refactor first
- `replay_metadata_json` is the single most-touched metadata column (13/15 writes)
- 4 JSON columns: `replay_metadata_json`, `governance_state_json`, `last_run_summary_json`, `last_runtime_summary_json`
- No new external behavior; no production code changes; Phase 51F guardrails still green

## 14. Recommended next step

**Phase 52C — Caller/coupling graph.** Map who calls these 15 write functions, identify direct-import patterns from `app/services/` to `app/persistence.repository`, and surface the most-coupled callers. This is the last prerequisite before any Phase 53 refactor.
