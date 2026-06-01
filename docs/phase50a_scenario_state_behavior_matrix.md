# Phase 50A — Scenario State Behavior Matrix

## Base SHA
`c17208638b68240f3ea68c72e441eaee629409ac`

## Rows

### 1. `/run` using saved_state

| Column | Value |
|--------|-------|
| **route/helper** | `POST /run` with `runtime_origin="saved_state"` and `workspace_state.active_scenario_id` set |
| **trigger/input** | Form submission, `active_project` set, runtime_guard returns `saved_state` |
| **scenario source** | `workspace_state.active_scenario_id` → `resolve_active_scenario_runtime_snapshot()` |
| **runtime snapshot source** | `resolved_snapshot` from scenario record (clean scenario snapshot) |
| **project_code/project_type behavior** | From `project_record` (resolved via `_project_workspace_from_snapshot`) |
| **scenario_id behavior** | Passed as `active_scenario_record.scenario_id` to persistence calls |
| **dirty/stale behavior** | Guard blocks if `workspace_state.dirty=True`; must save/discard first |
| **persistence calls** | `save_run()`, `save_project()`, `update_scenario_last_run_summary()` |
| **expected response behavior** | HTML template `partials/run_result.html` with KPIs |
| **extraction risk** | MEDIUM — snapshot resolution is complex but isolated in helper |
| **current test coverage** | Partial — runtime_guard behavior characterized in existing tests |

---

### 2. `/run` using saved_baseline

| Column | Value |
|--------|-------|
| **route/helper** | `POST /run` with `runtime_origin="saved_state"` but `workspace_state.active_scenario_id` is None |
| **trigger/input** | Form submission, no active scenario, project has baseline_snapshot |
| **scenario source** | None (no active scenario) |
| **runtime snapshot source** | `workspace_state.saved_snapshot` or `project_record.baseline_snapshot` |
| **project_code/project_type behavior** | From `project_record` |
| **scenario_id behavior** | `None` |
| **dirty/stale behavior** | Guard blocks if dirty |
| **persistence calls** | `save_run()`, `save_project()`, `update_scenario_last_run_summary()` |
| **expected response behavior** | Same as saved_state — template with KPIs |
| **extraction risk** | MEDIUM — fallback path but well-defined |
| **current test coverage** | Partial |

---

### 3. `/run` using user_created (or current form snapshot)

| Column | Value |
|--------|-------|
| **route/helper** | `POST /run` with `project_record.project_origin == "user_created"` |
| **trigger/input** | Form submission for user-created project |
| **scenario source** | No scenario, uses form snapshot directly |
| **runtime snapshot source** | `workspace_state.saved_snapshot` if exists, else `project_record.baseline_snapshot` or form snapshot |
| **project_code/project_type behavior** | From `project_record.project_code`, `project_record.project_type` |
| **scenario_id behavior** | `None` |
| **dirty/stale behavior** | Guard blocks if dirty; user_created path doesn't use active_scenario_id |
| **persistence calls** | `save_run()`, `save_project()` (no `update_scenario_last_run_summary` for user_created) |
| **expected response behavior** | Template `partials/run_result.html` with KPIs |
| **extraction risk** | HIGH — user_created path has distinct logic in `_resolve_runtime_snapshot_source` |
| **current test coverage** | Partial |

---

### 4. `/run` using factory_base_runtime

| Column | Value |
|--------|-------|
| **route/helper** | `POST /run` with `runtime_origin != "saved_state"` (factory path) |
| **trigger/input** | Form submission, no saved state, project is factory-seeded |
| **scenario source** | None |
| **runtime snapshot source** | `snapshot = _collect_form_snapshot(form)` — form-driven, not from workspace |
| **project_code/project_type behavior** | From form fields (capacity_mw, project_type, etc.) |
| **scenario_id behavior** | `None` |
| **dirty/stale behavior** | Guard still checked; may allow if workspace is clean |
| **persistence calls** | `save_run()`, `save_project()` |
| **expected response behavior** | Template with KPIs — factory path runs demo_project |
| **extraction risk** | LOW — distinct path, no scenario resolution |
| **current test coverage** | Partial |

---

### 5. GET `/download` using factory_base_runtime

| Column | Value |
|--------|-------|
| **route/helper** | `GET /download?project_type=...&scenario=...` with no active_scenario_id |
| **trigger/input** | URL params: project_type, scenario; no workspace_context |
| **scenario source** | None |
| **runtime snapshot source** | `runtime_origin="factory_base_runtime"` → `runtime_snapshot=None` |
| **project_code/project_type behavior** | From URL param `project_type`; project resolved from `project_code` param or default |
| **scenario_id behavior** | `None` (GET downloads don't pass scenario_id to audit service) |
| **dirty/stale behavior** | Guard still checked; `runtime_snapshot=None` means form-driven export |
| **persistence calls** | `record_download_export()` via audit service |
| **expected response behavior** | StreamingResponse with Excel bytes (build_values_only_export_for_project) |
| **extraction risk** | MEDIUM — GET download has complex factory_base_runtime branch |
| **current test coverage** | 20 tests from Phase 49D-3C |

---

### 6. POST `/download` using saved_state

| Column | Value |
|--------|-------|
| **route/helper** | `POST /download` with active_scenario_id set |
| **trigger/input** | Form submission with project context |
| **scenario source** | `workspace_state.active_scenario_id` |
| **runtime snapshot source** | `resolved_snapshot` from active scenario record |
| **project_code/project_type behavior** | From `project_record` |
| **scenario_id behavior** | `active_scenario_record.scenario_id` passed to `record_download_export()` |
| **dirty/stale behavior** | Guard blocks if dirty |
| **persistence calls** | `record_download_export()` via audit service |
| **expected response behavior** | StreamingResponse with Excel bytes |
| **extraction risk** | MEDIUM — scenario binding is well-isolated |
| **current test coverage** | 26 tests from Phase 49D-3D |

---

### 7. POST `/download` using saved_baseline

| Column | Value |
|--------|-------|
| **route/helper** | `POST /download` with `saved_baseline` project_origin and no active_scenario_id |
| **trigger/input** | Form submission |
| **scenario source** | None |
| **runtime snapshot source** | `workspace_state.saved_snapshot` or `project_record.baseline_snapshot` |
| **project_code/project_type behavior** | From `project_record` |
| **scenario_id behavior** | `None` |
| **dirty/stale behavior** | Guard blocks if dirty |
| **persistence calls** | `record_download_export()` via audit service |
| **expected response behavior** | StreamingResponse with Excel bytes |
| **extraction risk** | MEDIUM — fallback path |
| **current test coverage** | 26 tests |

---

### 8. POST `/download` using user_created

| Column | Value |
|--------|-------|
| **route/helper** | `POST /download` for `user_created` project |
| **trigger/input** | Form submission |
| **scenario source** | None (user_created projects don't have active scenario) |
| **runtime snapshot source** | `workspace_state.saved_snapshot` or `project_record.baseline_snapshot` |
| **project_code/project_type behavior** | From `project_record` |
| **scenario_id behavior** | `None` |
| **dirty/stale behavior** | Guard blocks if dirty |
| **persistence calls** | `record_download_export()` via audit service |
| **expected response behavior** | StreamingResponse with Excel bytes |
| **extraction risk** | MEDIUM — user_created path distinct |
| **current test coverage** | 26 tests |

---

### 9. runtime_guard allowed

| Column | Value |
|--------|-------|
| **route/helper** | `runtime_guard_for_snapshot(workspace_state, snapshot)` returning `allow_run=True` |
| **trigger/input** | workspace_state.dirty is False OR snapshot matches last_runtime_snapshot_id |
| **scenario source** | Preserved from existing state |
| **runtime snapshot source** | Preserved |
| **project_code/project_type behavior** | Preserved |
| **scenario_id behavior** | Preserved |
| **dirty/stale behavior** | `dirty=False` → guard allows |
| **persistence calls** | Normal route flow continues |
| **expected response behavior** | Normal route response (KPIs / Excel bytes) |
| **extraction risk** | LOW — simple boolean guard |
| **current test coverage** | Partial |

---

### 10. runtime_guard blocked

| Column | Value |
|--------|-------|
| **route/helper** | `runtime_guard_for_snapshot()` returning `allow_run=False` |
| **trigger/input** | workspace_state.dirty is True and snapshot differs from last_runtime_snapshot_id |
| **scenario source** | Preserved |
| **runtime snapshot source** | Preserved |
| **project_code/project_type behavior** | Preserved |
| **scenario_id behavior** | Preserved |
| **dirty/stale behavior** | `dirty=True` → guard blocks with `guard_message` |
| **persistence calls** | None (early return) |
| **expected response behavior** | HTML error template (partials/errors.html or HTMLResponse for download) with guard_message |
| **extraction risk** | LOW — guard is simple boolean check, message is informational |
| **current test coverage** | Partial |

---

### 11. stale runtime warning / dirty state

| Column | Value |
|--------|-------|
| **route/helper** | `_workspace_state_meta()` — returns `dirty` and `runtime_label` |
| **trigger/input** | UI polling for workspace state |
| **scenario source** | From workspace_state |
| **runtime snapshot source** | From workspace_state |
| **project_code/project_type behavior** | Preserved |
| **scenario_id behavior** | Preserved |
| **dirty/stale behavior** | `dirty=True` → runtime_label="Dirty — unsaved changes"; `dirty=False` → "Clean saved state" |
| **persistence calls** | None (read-only metadata) |
| **expected response behavior** | JSON dict with dirty/dirty_label/active_scenario_id/last_runtime_origin/runtime_label |
| **extraction risk** | LOW — pure data transformation |
| **current test coverage** | Partial |

---

### 12. active project switch

| Column | Value |
|--------|-------|
| **route/helper** | `_project_workspace_from_snapshot()` — called when `active_project` form field is set |
| **trigger/input** | Hidden `active_project` form field set by JS on project switch |
| **scenario source** | Reset — new workspace_state for selected project |
| **runtime snapshot source** | From newly resolved project_record + workspace_state |
| **project_code/project_type behavior** | Changed — new project_code/project_type from `active_project` |
| **scenario_id behavior** | Reset — active_scenario_id may be None for new project's workspace |
| **dirty/stale behavior** | New workspace is clean (new project context) |
| **persistence calls** | None (resolution only) |
| **expected response behavior** | Route continues with new project context |
| **extraction risk** | MEDIUM — project resolution is complex, shared across routes |
| **current test coverage** | Partial |

---

### 13. scenario load/list/save/discard endpoints

| Column | Value |
|--------|-------|
| **route/helper** | `/scenarios/{scenario_id}/load`, `/scenarios`, `/scenarios/save`, `/scenarios/state/discard` |
| **trigger/input** | Scenario management UI actions |
| **scenario source** | DB via repository functions |
| **runtime snapshot source** | DB or workspace_state |
| **project_code/project_type behavior** | Preserved |
| **scenario_id behavior** | Used to load/select/save scenario |
| **dirty/stale behavior** | save/discard modify workspace_state.dirty flag |
| **persistence calls** | `resolve_active_scenario_runtime_snapshot`, `save_scenario`, `select_scenario`, `save_workspace_state` |
| **expected response behavior** | Redirect or partial refresh |
| **extraction risk** | LOW — scenario CRUD is simple, repository-backed |
| **current test coverage** | Partial |

---

## Scenario Sources Summary

| Source | Description | Routes Using |
|--------|-------------|--------------|
| `saved_state` | Active scenario with resolved snapshot | /run, /download, /compare |
| `saved_baseline` | Workspace saved_snapshot or project baseline_snapshot | /run, /download, /compare |
| `user_created` | User project, workspace_snapshot or baseline | /run, /download |
| `factory_base_runtime` | No saved state, form-driven | /run, /download |
| `workspace_base` | Fallback when scenario unavailable | All fallback paths |

## Runtime Snapshot Sources Summary

| Source | Used When | Returns |
|--------|----------|---------|
| `resolved_snapshot` (from scenario DB) | active_scenario_id set + scenario valid | Clean scenario snapshot dict |
| `workspace_state.saved_snapshot` | No active scenario, saved_snapshot exists | Saved snapshot dict |
| `project_record.baseline_snapshot` | Fallback | Baseline snapshot dict |
| `form snapshot` | factory_base_runtime path | Form fields as dict |
| `None` | factory path for exports | Form-driven (no pre-binding) |

## Runtime Origin Values

| Value | Meaning |
|-------|---------|
| `saved_state` | Active scenario bound or saved snapshot exists |
| `user_created` | User-created project (distinct handling) |
| `factory_base_runtime` | Factory template, no saved state |
| `workspace_base` | Fallback (scenario unavailable) |