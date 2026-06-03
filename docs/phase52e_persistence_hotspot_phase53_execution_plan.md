# Phase 52E — Persistence Hotspot and Phase 53 Execution Plan

**Base SHA:** `20d90cdf2361d30a99e4f6ab67444ace76700cce` (post-52D main)
**Phase:** 52E — read-only architecture planning
**Type:** docs/report/test only
**Status:** PLANNING. No runtime code changes. No refactor.

## 1. Scope

This document converts Phase 52A-52D evidence into a concrete Phase 53 execution plan. For each of the 6 Phase 53 split groups (F, D, E, A-reads, C, B), it defines the objective, the functions to include/exclude, the dependencies, the required characterization tests, the expected changed files in Phase 53, the compatibility façade requirement, the rollback plan, the auto-merge policy, the single-owner requirement, and the estimated duration. It also specifies parallelization rules, automation policy, and stop conditions.

The plan is the green-light specification that determines whether Phase 53 can begin, and in what order. Phase 53 itself is **out of scope** for this document — Phase 52E produces the plan, not the work.

## 2. Evidence from 52A-52D

- **52A** (PR #422): 5 persistence files mapped, 2953 LOC total. repository.py is 2042 LOC with 61 functions (22 write, 16 read, 5 mixed, 18 helper). 6 high-risk writes.
- **52B** (PR #423): side-effect matrix for 15 write functions. 7 high-risk writes. 12 must-pin items. 4 JSON metadata columns. Single-transaction pattern (`with get_cursor() as cur:`).
- **52C** (PR #424): caller graph identifies 4 production files with direct imports, 19 files with calls, 6 candidate split groups (A-F), 11 single-owner zones, 3 parallel-safe zones, 4 do-not-parallelize zones.
- **52D** (PR #425): behavior characterization plan with 7 P0 must-pin items (required before Phase 53) and 5 P1 deferrable items. Per-group test gates: F (0), D (0), E (0), A (1), C (1), B (5). 7 user sign-off items. 11 red flags.

## 3. Second-order hotspot map

The second-order hotspot map identifies the **highest-pressure zones** that any refactor must address. It is built by composing 52A (function inventory), 52B (side effects), 52C (caller graph), and 52D (test gates).

### 3.1 Function hotspots (52A + 52B)

| Rank | Function | Hotspot type | Body LOC | Pressure |
|---:|---|---|---:|---|
| 1 | `save_workspace_state` | size + writes + convergence | 131 | **extreme** |
| 2 | `save_project` | size + writes + multi-field | 117 | **extreme** |
| 3 | `_compute_baseline_snapshot` | size + helper + project seed coupling | 122 | high |
| 4 | `get_or_create_base_case_scenario` | size + writes + idempotent-or-create | 85 | high |
| 5 | `add_scenario` | size + writes + multi-table | 80 | high |
| 6 | `base_vs_active_compare` | size + mixed | 69 | medium |
| 7 | `save_scenario` | writes + replay_metadata | 63 | high |
| 8 | `record_export` | writes + audit pipeline sole entry | 60 | **extreme** |
| 9 | `compare_scenarios` | mixed | 57 | medium |
| 10 | `resolve_active_scenario_runtime_snapshot` | mixed | 49 | medium |

### 3.2 Caller hotspots (52C)

| Rank | Caller | Calls | Pressure |
|---:|---|---:|---|
| 1 | `main_web.py` | 19 + 36-bulk | **extreme** (route file) |
| 2 | `scenario_duplicate_service.py` | 26 | high |
| 3 | `scenario_rename_service.py` | 21 | high |
| 4 | `scenarios_add_service.py` | 18 | high |
| 5 | `scenarios_save_service.py` | 11 | medium |
| 6 | `scenario_archive_service.py` | 10 | medium |
| 7 | `scenario_state_route_service.py` | 9 | medium |
| 8 | `project_save_as_service.py` | 8 | medium |
| 9 | `projects_create_service.py` | 7 | medium |
| 10 | `export_audit_service.py` | 7 | low (single-owner zone) |

### 3.3 Service coupling hotspots

The top 4 service coupling hotspots are all scenario-domain. This is by design (scenarios are the most-iterated entity), but it means any refactor of Group B (scenarios) must coordinate with 4 services. Group A (projects) coordinates with only 2 services. Group E (exports/audit) coordinates with 1 service. Group D (runs) coordinates with 1 service.

### 3.4 Write-risk hotspots

| Function | Why write-risk | Mitigation |
|---|---|---|
| `save_project` | Multi-table; INSERT-or-UPDATE branching | P0 pin required |
| `save_workspace_state` | Central convergence; last_runtime_* fields | P0 pin required |
| `save_scenario` | INSERT only; no idempotency guard | P0 pin required |
| `add_scenario` | Multi-table (parent + new row) | P0 pin required |
| `record_export` | Sole audit entry point | P0 pin required |
| `update_scenario_overrides` | is_base_case gate + filter | P0 pin required |
| `get_or_create_base_case_scenario` | Idempotent-or-create | P0 pin via Group B |

### 3.5 Metadata-risk hotspots

`replay_metadata_json` is the **single most-touched metadata column** — it is written or merged by 13 of the 15 write functions. Any refactor that changes its shape is a major migration. The other 3 JSON columns (`governance_state_json`, `last_run_summary_json`, `last_runtime_summary_json`) are less-touched but still cross-function dependencies.

## 4. Final recommended Phase 53 refactor order

1. **Group F — helpers** (9 functions, pure, no callers, no DB access)
2. **Group D — runs** (5 functions, isolated table)
3. **Group E — exports + audit** (11 functions, narrow caller surface)
4. **Group A — projects reads** (6 functions, read-only subset of Group A)
5. **Group C — workspace_state** (7 functions, central convergence point)
6. **Group B — scenarios** (17 functions, most-coupled, ties projects ↔ workspace)

This is the order from Phase 52C, confirmed by Phase 52D's test-gate analysis. The 3 first groups (F, D, E) need no new pins; they can begin as soon as the user's 52G sign-off is in. The 3 last groups (A, C, B) need 1, 1, 5 new P0 pins respectively; the user should add the pins before those groups are touched.

## 5. Per-group plan

### 5.1 Group F — helpers

- **Objective:** Extract pure helper functions to `app/persistence/_helpers.py`. Leave one-line re-exports in `repository.py`.
- **Functions included:** `_now_utc, _to_json, _from_json, _from_iso, _safe_number, _metric_value, _strip_empty_fields, _format_db_timestamp, snapshots_equal`
- **Functions excluded:** `_compute_baseline_snapshot, _get_least_created_scenario_for_project, _build_default_snapshot, _fill_missing_defaults, _sum_opex, _scenario_runtime_dict, _build_compare_metrics, _delta_sign_class` (these are domain-specific and stay with their owning group)
- **Risk level:** **low** (pure functions, no side effects)
- **Dependencies:** none
- **Required characterization tests:** **0** (signature-preserving refactor is invisible)
- **Expected changed files in Phase 53:** `app/persistence/_helpers.py` (new), `app/persistence/repository.py` (re-exports)
- **Compatibility façade:** yes, in `repository.py`
- **Rollback plan:** revert the single PR
- **Auto-merge policy:** **allowed** (signature-preserving refactor)
- **Single-owner required:** **no**
- **Estimated duration:** 1 PR (~30 min)

### 5.2 Group D — runs

- **Objective:** Extract run-table reads/writes to `app/persistence/runs.py`. Re-export from `repository.py`.
- **Functions included:** `save_run, get_run, list_runs, delete_run, count_runs`
- **Functions excluded:** `seed_scenarios_if_needed` (cross-domain with scenarios)
- **Risk level:** **low–medium** (isolated table, narrow caller surface, replay_metadata writes)
- **Dependencies:** none (runs table is independent)
- **Required characterization tests:** **0** (existing tests cover the surface; the surface is `save_run` → `RunRecord` which is already well-pinned)
- **Expected changed files in Phase 53:** `app/persistence/runs.py` (new), `app/persistence/repository.py` (re-exports)
- **Compatibility façade:** yes
- **Rollback plan:** revert the single PR
- **Auto-merge policy:** **allowed** (isolated table, narrow surface)
- **Single-owner required:** **no** (1 service + 1 route is small)
- **Estimated duration:** 1 PR (~1 hour)

### 5.3 Group E — exports + audit

- **Objective:** Extract export/audit reads/writes to `app/persistence/exports_audit.py`. Re-export from `repository.py`.
- **Functions included:** `record_export, list_exports, get_scenario_history, compare_scenarios, build_export_lineage, base_vs_active_compare, _scenario_runtime_dict, _build_compare_metrics, _delta_sign_class, _format_db_timestamp, snapshots_equal`
- **Functions excluded:** `save_run` (Group D)
- **Risk level:** **medium** (`record_export` is the sole audit entry point, but it is well-pinned)
- **Dependencies:** `compare_scenarios` reads scenarios; this is read-only, no transaction coupling
- **Required characterization tests:** **0** for the move; the existing 14/49 audit tests already pin the surface
- **Expected changed files in Phase 53:** `app/persistence/exports_audit.py` (new), `app/persistence/repository.py` (re-exports)
- **Compatibility façade:** yes
- **Rollback plan:** revert the single PR
- **Auto-merge policy:** **allowed** (audit pipeline is well-pinned)
- **Single-owner required:** **no** (1 service + 1 route)
- **Estimated duration:** 1 PR (~1 hour)

### 5.4 Group A — projects reads (sub-group of A)

- **Objective:** Extract project-table reads to `app/persistence/projects.py`. This is a sub-group because `save_project` (the writer) is too risky to move first.
- **Functions included:** `get_project, get_project_by_code, list_projects, list_baseline_records, get_project_record, list_project_records`
- **Functions excluded:** `save_project, seed_baseline_projects_if_needed, _compute_baseline_snapshot, _sum_opex, _build_default_snapshot, _fill_missing_defaults, create_project_record, update_project_record` (stay in Group A-2 — moved later after P0 pin)
- **Risk level:** **low** (reads only)
- **Dependencies:** none (reads are independent)
- **Required characterization tests:** **0** (read-only, well-pinned)
- **Expected changed files in Phase 53:** `app/persistence/projects.py` (new), `app/persistence/repository.py` (re-exports)
- **Compatibility façade:** yes
- **Rollback plan:** revert the single PR
- **Auto-merge policy:** **allowed** (reads only)
- **Single-owner required:** **no**
- **Estimated duration:** 1 PR (~30 min)

### 5.5 Group C — workspace_state

- **Objective:** Extract workspace_state reads/writes to `app/persistence/workspace_state.py`. Re-export from `repository.py`. Move the central convergence function last among workspace functions.
- **Functions included:** `save_workspace_state, get_workspace_state, bind_workspace_to_scenario, discard_workspace_draft, record_workspace_runtime, resolve_active_scenario_runtime_snapshot, runtime_guard_for_snapshot`
- **Functions excluded:** `select_scenario` (straddles scenarios ↔ workspace; keep in Group B for now)
- **Risk level:** **high** (central convergence point; 4 wrappers)
- **Dependencies:** `select_scenario` and `record_workspace_runtime` also call `save_workspace_state`; these need to be updated atomically with the move
- **Required characterization tests:** **1 P0** (`save_workspace_state` insert+update+replay_metadata merge+last_runtime_* preservation)
- **Expected changed files in Phase 53:** `app/persistence/workspace_state.py` (new), `app/persistence/repository.py` (re-exports), `app/services/scenario_state_route_service.py` (caller update), possibly `app/services/scenario_select_service.py` (caller update)
- **Compatibility façade:** yes
- **Rollback plan:** revert the single PR; the central convergence makes rollback a single-revert point
- **Auto-merge policy:** **NOT allowed** (high risk; central convergence). **Review required.**
- **Single-owner required:** **yes** (one user/agent should own the move to coordinate wrapper updates)
- **Estimated duration:** 1 PR + 1 P0 pin file (~2 hours)

### 5.6 Group B — scenarios

- **Objective:** Extract scenario reads/writes to `app/persistence/scenarios.py`. This is the largest and most-coupled group; it should be the last in Phase 53.
- **Functions included:** `save_scenario, get_scenario, list_scenarios, rename_scenario, archive_scenario, promote_scenario_to_base_case, duplicate_scenario, add_scenario, update_scenario_last_run_summary, update_scenario_overrides, select_scenario, get_scenario_provenance, get_base_case_scenario, get_or_create_base_case_scenario, seed_scenarios_if_needed, resolve_scenario_snapshot, SCENARIO_INPUT_FIELDS`
- **Functions excluded:** none (all scenario-domain functions move together)
- **Risk level:** **high** (most-coupled, ties projects ↔ workspace)
- **Dependencies:** `save_scenario` is called by `add_scenario` and `duplicate_scenario`; `select_scenario` calls `save_workspace_state` (Group C)
- **Required characterization tests:** **5 P0** (save_scenario, add_scenario, update_scenario_overrides, select_scenario, get_or_create_base_case_scenario) + 2 P1 (duplicate_scenario, update_scenario_last_run_summary) when those specific functions are moved
- **Expected changed files in Phase 53:** `app/persistence/scenarios.py` (new), `app/persistence/repository.py` (re-exports), 4–5 service files (caller updates)
- **Compatibility façade:** yes
- **Rollback plan:** revert the single PR; high coupling makes this complex
- **Auto-merge policy:** **NOT allowed** (high risk; most-coupled). **Review + user sign-off required.**
- **Single-owner required:** **yes** (one user/agent should own the entire move)
- **Estimated duration:** 1 large PR + 5 P0 pin files (~1 day, can be split into 2 sub-PRs if needed)

### 5.7 Group A-2 — projects writes (not in main order, but referenced)

The project write functions (`save_project, seed_baseline_projects_if_needed, _compute_baseline_snapshot, _sum_opex, _build_default_snapshot, _fill_missing_defaults, create_project_record, update_project_record`) are not in the main 6-group refactor order. They should be moved **after** Group A-reads but **before** Group B, because the project write functions are called by scenario-side logic (`get_or_create_base_case_scenario` reads project fields). If Group B is moved first, the project write functions are still in `repository.py` and the re-exports work transparently.

- **Risk level:** **high** (multi-table writes)
- **Required characterization tests:** **1 P0** (`save_project` insert+update+replay_metadata+governance_state preservation)
- **Estimated duration:** 1 PR + 1 P0 pin file (~2 hours)

## 6. Compatibility façade plan

The compatibility façade in `app/persistence/repository.py` re-exports every function from the new group modules. This way, any caller that does `from app.persistence.repository import save_project` continues to work without changes.

**Initial state (post-Group F/D/E/A-reads):** the façade is a one-line per function:
```python
from app.persistence._helpers import _now_utc, _to_json, _from_json, _from_iso, _safe_number, _metric_value, _strip_empty_fields, _format_db_timestamp, snapshots_equal
from app.persistence.runs import save_run, get_run, list_runs, delete_run, count_runs
from app.persistence.exports_audit import record_export, list_exports, get_scenario_history, compare_scenarios, build_export_lineage, base_vs_active_compare, _scenario_runtime_dict, _build_compare_metrics, _delta_sign_class
from app.persistence.projects import get_project, get_project_by_code, list_projects, list_baseline_records, get_project_record, list_project_records
```

**Post-Group C:** add workspace_state re-exports.
**Post-Group B:** add scenarios re-exports.
**Post-Group A-2:** add remaining project writes.

**Deprecation policy:** none for now. The façade is permanent until Phase 54+.

## 7. Do-not-parallelize rules

The following rules forbid parallel work on multiple Phase 53 groups at the same time:

1. **Never work on Group C and Group B in parallel.** Both touch `save_workspace_state` (Group C) and `save_scenario` (Group B); their re-exports overlap.
2. **Never work on Group A-reads and Group A-2 in parallel.** A-reads and A-2 share the same target file (`projects.py`).
3. **Never work on Group E and Group B in parallel.** Both touch `get_scenario_history` (audit vs. scenarios) and `compare_scenarios` (audit vs. scenarios).
4. **Never touch `_init_schema` while any group is being moved.** Schema changes are a separate concern.

## 8. Safe-to-parallelize rules

The following rules allow parallel work:

1. **Group F can run in parallel with anything else.** Pure helpers.
2. **Group D can run in parallel with Group F, Group A-reads, or Group E.** Runs table is isolated.
3. **Group E can run in parallel with Group F, Group D, or Group A-reads.** Exports table is independent.
4. **Group A-reads can run in parallel with Group F, Group D, or Group E.** Reads only.

## 9. Phase 53 automation policy

- **Auto-merge allowed:** Group F, Group D, Group E, Group A-reads (if user signs off on 52G)
- **Review required:** Group C
- **Review + user sign-off required:** Group B, Group A-2
- **Hard-stop conditions:** any test failure in any P0 pin file; any CI failure; any change to `replay_metadata` shape; any change to `_init_schema`; any new import of sqlite3/sqlalchemy outside `app/persistence/*`

## 10. Phase 53 stop conditions

Phase 53 work must stop immediately if any of the following is observed:

1. Any P0 pin test fails
2. Any Phase 51F guardrail fails
3. Any production code change beyond the planned file moves
4. Any change to `app/waterfall_core.py`, `app/project_factories.py`, parity-core, schema, JS, fixture CSVs
5. Any change to `replay_metadata` or `governance_state` shape
6. Any new direct DB connection outside `app/persistence/*`
7. Any merge that includes a model change bundled with a persistence split
8. Any conflict that requires non-trivial judgment to resolve

## 11. Phase 53 PR sequence proposal

| # | PR | Phase | Description | Tests | Auto-merge? |
|---:|---|---|---|---|---|
| 1 | 53A | Group F | Extract helpers | 0 new | yes |
| 2 | 53B | Group D | Extract runs | 0 new | yes |
| 3 | 53C | Group E | Extract exports+audit | 0 new | yes |
| 4 | 53D | Group A-reads | Extract project reads | 0 new | yes |
| 5 | 53E | Group A-P0 | Add save_project P0 pin | 1 new | yes |
| 6 | 53F | Group A-2 | Extract project writes | 0 new | review |
| 7 | 53G | Group C-P0 | Add save_workspace_state P0 pin | 1 new | yes |
| 8 | 53H | Group C | Extract workspace_state | 0 new | review |
| 9 | 53I | Group B-P0 | Add 5 P0 pins (save_scenario, add_scenario, update_scenario_overrides, select_scenario, get_or_create_base_case_scenario) | 5 new | review per file |
| 10 | 53J | Group B | Extract scenarios (large PR) | 0 new | sign-off |

**Total estimated:** 10 PRs across ~5 working sessions. Phase 51's pattern (one PR per session) can be replicated here.

## 12. Compatibility façade re-export pattern

Each group module (`_helpers.py`, `runs.py`, etc.) defines the function with the same signature and behavior. The façade in `repository.py` re-exports them. This pattern was used in Phase 51 for `main_web.py` re-exports of service functions.

Example for Group F:
```python
# app/persistence/_helpers.py
def _now_utc() -> datetime:
    return datetime.now(timezone.utc)
# ... (all 9 functions)
```

```python
# app/persistence/repository.py
from app.persistence._helpers import (
    _now_utc, _to_json, _from_json, _from_iso,
    _safe_number, _metric_value, _strip_empty_fields,
    _format_db_timestamp, snapshots_equal,
)
```

## 13. Auto-merge criteria per group

| Group | All gates pass? | Auto-merge |
|---|---|---|
| F | yes (signature-preserving) | yes |
| D | yes (isolated table) | yes |
| E | yes (audit pipeline pinned) | yes |
| A-reads | yes (reads only) | yes |
| A-2 | requires save_project P0 | review |
| C | requires save_workspace_state P0 | review |
| B | requires 5 P0 pins | sign-off |

## 14. Stop signal received

After 52E, the next prompt should be **Phase 52F — guardrail specifications/tests**, which is the last deliverable before 52G closeout. Phase 53 work itself is **out of scope** for this document.

## 15. Recommended next step

**Phase 52F — Guardrail specifications/tests.** Add or specify structural guardrails to prevent Phase 51-style proliferation and Phase 53 persistence boundary regressions. Implement the safe ones now; defer the brittle ones.
