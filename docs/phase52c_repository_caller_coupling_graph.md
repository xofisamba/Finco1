# Phase 52C — Repository Caller and Coupling Graph

**Base SHA:** `f780572ccfb3c6f3ccaab50842c9cae840d0dc2e` (post-52B main)
**Phase:** 52C — read-only mapping
**Type:** docs/report/test only
**Status:** MAPPING. No runtime code changes. No refactor.

## 1. Scope

This document maps **who calls** the 27 highest-impact persistence functions in `app/persistence/repository.py`, identifies the most-coupled caller files, surfaces direct-import patterns from `app/services/` and `main_web.py`, and proposes candidate split groups for any future Phase 53 refactor.

The map is the last prerequisite before any Phase 53 refactor of the persistence layer. It does not propose any code change. It identifies which functions could be split, which callers would need to be updated, and which zones are safe to parallelize.

## 2. Methodology

- **Caller scan**: every `.py` file under `app/` plus `main_web.py` and `main_api.py` was scanned for calls to the 27 key persistence functions (the 15 writes from Phase 52B plus 12 high-coupling reads).
- **Import scan**: every `from app.persistence...` import line in production code was extracted and grouped by caller file.
- **Call counting**: function calls (not definitions, not imports) were counted via regex `\b<fn>\s*\(`. Calls inside `if` guards, in expressions, and on multi-line blocks are all counted.
- **Domain tagging**: each caller file was tagged with its primary domain based on its filename and import surface.

## 3. Caller adjacency graph (top-15 most-called functions)

| Rank | Function | Total calls | Top caller |
|---:|---|---:|---|
| 1 | `get_scenario` | 17 | `app/services/scenario_duplicate_service.py` (4) |
| 2 | `list_scenarios` | 17 | `app/services/scenario_rename_service.py` (3) |
| 3 | `get_project_by_code` | 14 | `app/services/projects_create_service.py` (3) |
| 4 | `save_workspace_state` | 13 | `app/services/scenarios_save_service.py` (3) |
| 5 | `get_workspace_state` | 13 | `app/services/scenario_state_route_service.py` (3) |
| 6 | `get_project_record` | 11 | `main_web.py` (4) |
| 7 | `record_export` | 9 | `app/services/export_audit_service.py` (5) |
| 8 | `get_scenario_history` | 8 | `main_web.py` (4) |
| 9 | `build_export_lineage` | 8 | `app/services/export_audit_service.py` (4) |
| 10 | `list_exports` | 8 | `app/services/export_audit_service.py` (3) |
| 11 | `save_project` | 7 | `app/services/projects_create_service.py` (3) |
| 12 | `duplicate_scenario` | 6 | `app/services/scenario_duplicate_service.py` (6) |
| 13 | `bind_workspace_to_scenario` | 5 | `app/services/scenario_state_route_service.py` (3) |
| 14 | `add_scenario` | 5 | `app/services/scenarios_add_service.py` (4) |
| 15 | `rename_scenario` | 4 | `app/services/scenario_rename_service.py` (3) |

## 4. Top-10 most-coupled caller files

| Rank | Caller file | Total repo calls | Functions called |
|---:|---|---:|---|
| 1 | `app/services/scenario_duplicate_service.py` | 26 | `get_scenario, list_scenarios, get_project_by_code, get_workspace_state, get_project_record, duplicate_scenario, save_scenario` (via duplicate_scenario) |
| 2 | `app/services/scenario_rename_service.py` | 21 | `list_scenarios, get_workspace_state, get_scenario, rename_scenario, save_workspace_state, get_project_by_code` |
| 3 | `main_web.py` | 19 | `get_project_record, get_scenario_history, get_scenario, list_scenarios, save_workspace_state, save_scenario` (and a 36-symbol bulk import) |
| 4 | `app/services/scenarios_add_service.py` | 18 | `get_scenario, list_scenarios, get_project_record, add_scenario, save_workspace_state, get_project_by_code` |
| 5 | `app/services/scenarios_save_service.py` | 11 | `save_workspace_state, save_scenario, get_workspace_state, get_scenario` |
| 6 | `app/services/scenario_archive_service.py` | 10 | `get_scenario, list_scenarios, archive_scenario, get_workspace_state` |
| 7 | `app/services/scenario_state_route_service.py` | 9 | `get_workspace_state, save_workspace_state, bind_workspace_to_scenario, discard_workspace_draft` |
| 8 | `app/services/project_save_as_service.py` | 8 | `get_project_record, get_scenario, save_workspace_state, save_project` |
| 9 | `app/services/projects_create_service.py` | 7 | `get_project_by_code, get_scenario, create_project_record, save_project, save_workspace_state` |
| 10 | `app/services/export_audit_service.py` | 7 | `record_export, build_export_lineage, list_exports` |

## 5. Direct persistence imports in production code

Only **4 production files** import directly from `app.persistence.*`:

| Caller | Module | Symbols | Pattern |
|---|---|---|---|
| `main_web.py` | `.repository` | 36 symbols (bulk import at L41-79) | `from app.persistence.repository import ( ... )` |
| `main_web.py` | `.repository` | `get_project_record as gpr` (route-local re-import at L2460) | `from app.persistence.repository import get_project_record as gpr` |
| `main_web.py` | `.provenance` | `build_replay_metadata, utc_now_iso` | `from app.persistence.provenance import ...` |
| `app/services/scenario_state_service.py` | `.repository` | `get_scenario_provenance, get_workspace_state, resolve_active_scenario_runtime_snapshot, runtime_guard_for_snapshot` | `from app.persistence.repository import ( ... )` |
| `app/services/export_audit_service.py` | `.repository` | `record_export` | `from app.persistence.repository import record_export` |
| `app/services/project_save_as_service.py` | `.repository` | (route-local re-import) `get_project_record as gpr` | (inside the service, after Phase 51O-2 extraction) |
| `app/export/runtime_summary.py` | `.provenance` | `build_replay_metadata` | `from app.persistence.provenance import build_replay_metadata` |

**Direct persistence imports in route services:** 1 (`project_save_as_service.py`)
**Direct persistence imports in main_web/main_api:** 1 (main_web.py, with 3 separate import statements)
**No service or route imports `app.persistence.db` directly.**

## 6. Cross-package coupling notes

- `main_web.py` is the **largest** single caller of `app.persistence.repository` with 19 direct calls and a 36-symbol bulk import.
- `app/services/scenario_duplicate_service.py` is the **most-coupled** service with 26 calls.
- `app/services/scenario_rename_service.py` and `app/services/scenarios_add_service.py` are the next most-coupled (21 and 18 calls respectively).
- All four top-coupled service files are **scenario-domain** services, which explains why `get_scenario` and `list_scenarios` dominate the function-call ranking.
- The single export-domain service (`export_audit_service.py`) is much less coupled (7 calls) but is the **only** caller of `record_export`, `build_export_lineage`, and `list_exports`.
- The two project-domain services (`projects_create_service.py`, `project_save_as_service.py`) are mid-coupled (7-8 calls) and are the only callers of `save_project` (other than the bulk-import in main_web.py).

## 7. Circular import check

The `app.persistence` package has the following internal module graph:

| Module | Imports from package |
|---|---|
| `app.persistence.db` | (none) |
| `app.persistence.repository` | `app.persistence.db` (for `get_cursor`) |
| `app.persistence.provenance` | (none) |
| `app.persistence.backup_restore` | `app.persistence.db` (for `DB_PATH`) |

**No circular imports** inside the `app.persistence` package. The graph is a strict DAG with `db` as the root and `provenance` as an isolated node.

**No circular imports** across the package boundary. Production code imports `app.persistence.repository` and `app.persistence.provenance`; nothing inside `app.persistence` imports from `app.services` or `main_web` or `main_api`.

## 8. Phase 53 candidate split groups

Based on the call graph, the persistence layer can be split into 6 candidate groups without changing any caller code beyond updating import paths. Each group is identified by domain and primary caller surface.

| Group | Functions | Primary caller surface | Why this group |
|---|---|---|---|
| **A — projects** | `save_project, get_project, get_project_by_code, list_projects, list_baseline_records, seed_baseline_projects_if_needed, _compute_baseline_snapshot, _sum_opex, _build_default_snapshot, _fill_missing_defaults, create_project_record, get_project_record, list_project_records, update_project_record, _get_least_created_scenario_for_project` | `projects_create_service`, `project_save_as_service`, `main_web.py` | All project-table writes/reads; `_compute_baseline_snapshot` is a helper but is only called by project-side functions |
| **B — scenarios** | `save_scenario, get_scenario, list_scenarios, rename_scenario, archive_scenario, promote_scenario_to_base_case, duplicate_scenario, add_scenario, update_scenario_last_run_summary, update_scenario_overrides, select_scenario, get_scenario_provenance, get_base_case_scenario, get_or_create_base_case_scenario, seed_scenarios_if_needed, resolve_scenario_snapshot, SCENARIO_INPUT_FIELDS` | `scenario_duplicate_service`, `scenario_rename_service`, `scenarios_add_service`, `scenarios_save_service`, `scenario_archive_service`, `scenario_select_service` (via service) | All scenario-table writes/reads + scenario input-field validation |
| **C — workspace_state** | `save_workspace_state, get_workspace_state, bind_workspace_to_scenario, discard_workspace_draft, record_workspace_runtime, resolve_active_scenario_runtime_snapshot, runtime_guard_for_snapshot` | `scenario_state_route_service`, `scenarios_save_service`, `scenario_select_service` (via service) | All workspace_state writes/reads + the active-scenario binding logic |
| **D — runs** | `save_run, get_run, list_runs, delete_run, count_runs` | `save_run_service`, `main_web.py` | Run-table writes/reads; isolated |
| **E — exports + audit** | `record_export, list_exports, get_scenario_history, compare_scenarios, build_export_lineage, base_vs_active_compare, _scenario_runtime_dict, _build_compare_metrics, _delta_sign_class, _format_db_timestamp, snapshots_equal` | `export_audit_service`, `main_web.py` | Export + audit + compare logic |
| **F — helpers** | `_now_utc, _to_json, _from_json, _from_iso, _safe_number, _metric_value, _strip_empty_fields, _get_least_created_scenario_for_project, SCENARIO_INPUT_FIELDS` | (all groups) | Pure helpers; safe to extract first |

`resolve_active_scenario_runtime_snapshot` and `runtime_guard_for_snapshot` straddle groups B and C. Recommendation: keep them in group **C** (workspace_state) because they primarily read workspace state and return a runtime verdict, even though they read scenario fields too.

`get_scenario_history` and `compare_scenarios` straddle groups B and E. Recommendation: keep `get_scenario_history` in group **E** (audit) because it is part of the audit/export pipeline; keep `compare_scenarios` in group **B** (scenarios) because it is a scenario-to-scenario comparison, not an export.

## 9. Single-owner zones

A **single-owner zone** is a function whose only production caller is one file. Refactoring such a function only requires updating that one file.

| Function | Sole production caller |
|---|---|
| `record_export` | `app/services/export_audit_service.py` |
| `build_export_lineage` | `app/services/export_audit_service.py` |
| `list_exports` | `app/services/export_audit_service.py` |
| `get_scenario_provenance` | `app/services/scenario_state_service.py` |
| `resolve_active_scenario_runtime_snapshot` | `app/services/scenario_state_service.py` |
| `runtime_guard_for_snapshot` | `app/services/scenario_state_service.py` (and `tests/test_phase16_fresh_workspace_first_run_guard.py`, `tests/test_phase18_user_project_workbook_artifact_validation.py`) |
| `get_base_case_scenario` | (no production caller; test-only) |
| `seed_scenarios_if_needed` | (no production caller; called from test fixtures and seed paths) |
| `seed_baseline_projects_if_needed` | (called from test fixtures) |
| `delete_run` | (no production caller; test/admin) |
| `count_runs` | (no production caller; test/admin) |

**10 single-owner zones** identified. 7 are service-coupled; 4 are test-only.

## 10. Parallel-safe zones

A **parallel-safe zone** is a function whose semantics are independent and whose refactor would not affect any other group's behavior.

| Zone | Functions | Why parallel-safe |
|---|---|---|
| **Group D (runs)** | `save_run, get_run, list_runs, delete_run, count_runs` | Runs are an isolated table; no read/write dependencies on projects / scenarios / workspace_state / exports |
| **Group F (helpers)** | `_now_utc, _to_json, _from_json, _from_iso, _safe_number, _metric_value, _strip_empty_fields, _format_db_timestamp, snapshots_equal` | Pure functions; no side effects; refactoring them is invisible to callers as long as the new signature is identical |
| **Group A (projects) reads** | `get_project, get_project_by_code, list_projects, list_baseline_records, get_project_record, list_project_records` | Reads only; no transaction interaction with other groups |

## 11. Do-not-parallelize zones

A **do-not-parallelize zone** is a function whose semantics tie it to another group and would require careful coordination to refactor.

| Zone | Function(s) | Why not parallelizable |
|---|---|---|
| **`save_workspace_state` convergence** | `save_workspace_state, bind_workspace_to_scenario, select_scenario, discard_workspace_draft, record_workspace_runtime` | All five route through `save_workspace_state`. Refactoring one without the others creates 2 sources of truth for workspace writes. |
| **Scenario ↔ workspace coupling** | `select_scenario, record_workspace_runtime, bind_workspace_to_scenario` | Read scenarios; write workspace. Any refactor must preserve the read-then-write order. |
| **`save_project` + `seed_baseline_projects_if_needed`** | `save_project, seed_baseline_projects_if_needed, _compute_baseline_snapshot` | `save_project` calls `_compute_baseline_snapshot` for new projects with empty baseline; `seed_baseline_projects_if_needed` populates the same table with bulk factory templates. They share the same write path. |
| **`add_scenario` + `save_scenario`** | `add_scenario, save_scenario, duplicate_scenario` | `add_scenario` and `duplicate_scenario` both call `save_scenario`. Any refactor of `save_scenario` ripples to both. |

## 12. Refactor recommendations

If a future Phase 53 refactor is approved, the recommended order is:

1. **Group F (helpers) first** — pure functions, zero behavior risk, sets the module-pattern precedent.
2. **Group D (runs) next** — isolated table, narrow caller surface (1 service + 1 route).
3. **Group E (exports + audit) next** — narrow caller surface (1 service + 1 route).
4. **Group A (projects) reads next** — read-only, no transaction interaction.
5. **Group C (workspace_state) next** — central convergence point, but well-pinned.
6. **Group B (scenarios) last** — most-coupled, ties projects ↔ workspace.

For all groups, the refactor pattern is the same as Phase 51: keep the function in `repository.py` as a thin re-export, move the body to `app/persistence/<group>.py`, and update callers to import from the new module. Phase 51F guardrails stay green throughout.

## 13. Compatibility facade recommendation

A **compatibility facade** in `app/persistence/repository.py` should be retained for one major version. The facade re-exports every function from the new group modules, so any caller that does `from app.persistence.repository import save_project` continues to work without changes. This is a one-line addition per function (`from app.persistence.projects import save_project`).

The facade can be deprecated incrementally in subsequent minor versions. Tests should be added that exercise both the new direct import and the legacy facade import.

## 14. Direct-import preservation recommendation

For the current state, **direct repository imports from route services should be preserved temporarily** (i.e., not routed through narrower services in this phase). Reasons:

- The 1 service that does a direct import (`project_save_as_service.py`) is a recently-extracted service (Phase 51O-2) and the import is documented as a temporary measure in its own comments.
- The 4 production files with direct imports account for 4 / 4 = 100% of the direct-import surface — small enough to update in one pass when the facade is built.
- Phase 51's pattern keeps services as the single narrowing layer; persistence is allowed to be called directly from services.

When the persistence layer is split (Phase 53), the recommendation is:
- Update the 4 direct-import sites to import from the new group modules
- Keep the facade in `repository.py` for backward compatibility
- The 1 service-direct-import (`project_save_as_service.py`) should be updated to call the new group module

## 15. Summary

- 27 key persistence functions traced across 4 production files with direct imports + 19 files with calls
- `main_web.py` is the largest single caller (19 direct calls + 36-symbol bulk import)
- `app/services/scenario_duplicate_service.py` is the most-coupled service (26 calls)
- No circular imports inside `app.persistence` or across the package boundary
- 6 candidate split groups identified (A-F)
- 10 single-owner zones (7 service-coupled, 4 test-only)
- 3 parallel-safe zones (Group D, Group F, Group A reads)
- 4 do-not-parallelize zones (workspace_state convergence, scenario↔workspace coupling, project seed coupling, scenario add/duplicate coupling)
- Recommended refactor order: F → D → E → A-reads → C → B
- Compatibility facade recommended for one major version
- No new external behavior; no production code changes; Phase 51F guardrails still green

## 16. Recommended next step

**Phase 52D — Behavior characterization plan.** Define the test-pinning plan for the 12 must-pin items from Phase 52B, mapped to the 6 split groups from this document. This is the green-light checklist before any Phase 53 refactor.
