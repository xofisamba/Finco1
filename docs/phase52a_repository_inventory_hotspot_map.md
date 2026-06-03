# Phase 52A — Repository Inventory and Hotspot Map

**Base SHA:** `e51a16db61c8981adc21700a671c91bac0d88d2d`
**Phase:** 52A — read-only mapping
**Type:** docs/report/test only
**Status:** MAPPING. No runtime code changes. No refactor.

## 1. Scope

This document inventories the persistence/repository layer in the Finco1 codebase and ranks hotspots by size, coupling, and write intensity. It is a **read-only** mapping produced ahead of any future refactor. No `app/persistence/*` or `repository.py` code is modified. No `main_web.py` or `app/services/*` is modified. The document and accompanying JSON describe the current shape of the layer so that future refactor decisions can be made from a single, verifiable source.

## 2. Files in scope

| File | LOC | Role |
|---|---|---|
| `app/persistence/__init__.py` | 55 | Package init / re-exports |
| `app/persistence/db.py` | 205 | SQLite connection / schema init / `get_cursor` context manager |
| `app/persistence/repository.py` | **2042** | **God-module**: project, scenario, run, export, audit, workspace persistence |
| `app/persistence/backup_restore.py` | 480 | SQLite backup + restore + auto-backup |
| `app/persistence/provenance.py` | 171 | Git SHA, branch, runtime flag, governance, replay metadata |
| **Total** | **2953** | |

`app/persistence/repository.py` is the single largest file and is the Phase 52A hotspot target.

## 3. Function inventory — `app/persistence/repository.py`

The module has **61 top-level public/private functions**. Body LOC is the span from the `def` line to the closing line of the function. Classification: `read` (no DB write), `write` (DB mutation), `mixed` (read + write or compute + persist), `helper` (pure function with no DB access).

### 3.1 Inventory table

| Line | Function | Body LOC | Sync/Async | Class. | Domain | Risk |
|---:|---|---:|---|---|---|---|
| 19 | `_now_utc` | 2 | sync | helper | helpers | low |
| 23 | `_to_json` | 2 | sync | helper | helpers | low |
| 27 | `_from_json` | 4 | sync | helper | helpers | low |
| 33 | `_from_iso` | 4 | sync | helper | helpers | low |
| 69 | `resolve_scenario_snapshot` | 15 | sync | helper | scenarios | low |
| 86 | `get_or_create_base_case_scenario` | 85 | sync | write | scenarios | high |
| 173 | `seed_scenarios_if_needed` | 26 | sync | write | scenarios | medium |
| 201 | `get_scenario_provenance` | 27 | sync | read | scenarios | low |
| 230 | `get_base_case_scenario` | 13 | sync | read | scenarios | low |
| 245 | `resolve_active_scenario_runtime_snapshot` | 49 | sync | mixed | scenarios | high |
| 536 | `_safe_number` | 7 | sync | helper | helpers | low |
| 545 | `_metric_value` | 16 | sync | helper | helpers | low |
| 563 | `snapshots_equal` | 2 | sync | helper | helpers | low |
| 567 | `_strip_empty_fields` | 8 | sync | helper | helpers | low |
| 577 | `runtime_guard_for_snapshot` | 29 | sync | mixed | governance | medium |
| 608 | `save_run` | 48 | sync | write | runs | medium |
| 658 | `get_run` | 5 | sync | read | runs | low |
| 665 | `list_runs` | 7 | sync | read | runs | low |
| 674 | `delete_run` | 4 | sync | write | runs | low |
| 680 | `count_runs` | 4 | sync | read | runs | low |
| 686 | `save_project` | 117 | sync | write | projects | high |
| 805 | `get_project` | 5 | sync | read | projects | low |
| 812 | `get_project_by_code` | 8 | sync | read | projects | low |
| 822 | `list_projects` | 7 | sync | read | projects | low |
| 831 | `list_baseline_records` | 8 | sync | read | projects | low |
| 841 | `seed_baseline_projects_if_needed` | 28 | sync | write | projects | medium |
| 871 | `_compute_baseline_snapshot` | 122 | sync | helper | projects | medium |
| 911 | `_sum_opex` | 6 | sync | helper | helpers | low |
| 995 | `_build_default_snapshot` | 9 | sync | helper | projects | low |
| 1006 | `_fill_missing_defaults` | 18 | sync | helper | projects | low |
| 1026 | `create_project_record` | 28 | sync | write | projects | medium |
| 1056 | `get_project_record` | 11 | sync | read | projects | low |
| 1069 | `list_project_records` | 13 | sync | read | projects | low |
| 1084 | `update_project_record` | 30 | sync | write | projects | medium |
| 1116 | `save_scenario` | 63 | sync | write | scenarios | high |
| 1181 | `get_scenario` | 5 | sync | read | scenarios | low |
| 1188 | `list_scenarios` | 19 | sync | read | scenarios | low |
| 1209 | `rename_scenario` | 7 | sync | write | scenarios | low |
| 1218 | `archive_scenario` | 7 | sync | write | scenarios | low |
| 1227 | `promote_scenario_to_base_case` | 34 | sync | write | scenarios | medium |
| 1263 | `_get_least_created_scenario_for_project` | 15 | sync | helper | helpers | low |
| 1280 | `duplicate_scenario` | 17 | sync | write | scenarios | medium |
| 1299 | `add_scenario` | 80 | sync | write | scenarios | high |
| 1381 | `update_scenario_last_run_summary` | 28 | sync | write | scenarios | medium |
| 1411 | `update_scenario_overrides` | 47 | sync | write | scenarios | high |
| 1460 | `select_scenario` | 24 | sync | write | scenarios | medium |
| 1486 | `get_workspace_state` | 8 | sync | read | workspace_state | low |
| 1496 | `save_workspace_state` | 131 | sync | write | workspace_state | high |
| 1629 | `bind_workspace_to_scenario` | 20 | sync | write | workspace_state | medium |
| 1651 | `discard_workspace_draft` | 22 | sync | write | workspace_state | medium |
| 1675 | `record_workspace_runtime` | 36 | sync | write | workspace_state | medium |
| 1713 | `record_export` | 60 | sync | write | exports | high |
| 1775 | `list_exports` | 20 | sync | read | exports | low |
| 1797 | `get_scenario_history` | 12 | sync | read | audit | low |
| 1811 | `compare_scenarios` | 57 | sync | mixed | scenarios | high |
| 1870 | `build_export_lineage` | 24 | sync | mixed | exports | medium |
| 1899 | `base_vs_active_compare` | 69 | sync | mixed | scenarios | high |
| 1970 | `_scenario_runtime_dict` | 28 | sync | helper | helpers | low |
| 2000 | `_build_compare_metrics` | 16 | sync | helper | helpers | low |
| 2018 | `_delta_sign_class` | 9 | sync | helper | helpers | low |
| 2029 | `_format_db_timestamp` | 13 | sync | helper | helpers | low |

### 3.2 Function counts

| Classification | Count |
|---|---:|
| write | 22 |
| read | 16 |
| mixed | 5 |
| helper | 18 |
| **total** | **61** |

| Domain | Count |
|---|---:|
| projects | 13 |
| scenarios | 19 |
| workspace_state | 5 |
| runs | 5 |
| exports | 3 |
| governance | 1 |
| audit | 1 |
| helpers | 14 |
| **total** | **61** |

## 4. Direct DB / session usage summary

All public functions in `repository.py` use `get_cursor()` from `app/persistence/db.py` as a context manager. There is no `import sqlite3` or `import sqlalchemy` inside `repository.py`. The only direct `import` in the file is:

```python
from app.persistence.db import get_cursor
```

`get_cursor()` is itself a context manager wrapping a `sqlite3` connection with `row_factory = sqlite3.Row`. The connection is opened and closed inside the `with` block; `commit()` is invoked on `__exit__` if no exception was raised, and `rollback()` is invoked on exception. There is no global session and no ORM. Every write function follows the same pattern: `with get_cursor() as cur: cur.execute(...)` — there is no explicit `cur.commit()` and no `session.add(...)` / `session.commit()` style API surface.

**Direct DB access outside `app/persistence/*`:** none. No file under `app/services/`, `main_web.py`, `main_api.py`, or `app/api/*` opens a sqlite3 connection or imports `get_cursor` from `app.persistence.db`. All persistence goes through `repository.py` functions.

## 5. Hotspot ranking

### 5.1 Largest functions (top 10)

| Rank | Function | Body LOC | Domain | Class. |
|---:|---|---:|---|---|
| 1 | `save_workspace_state` (L1496) | 131 | workspace_state | write |
| 2 | `_compute_baseline_snapshot` (L871) | 122 | projects | helper |
| 3 | `save_project` (L686) | 117 | projects | write |
| 4 | `get_or_create_base_case_scenario` (L86) | 85 | scenarios | write |
| 5 | `add_scenario` (L1299) | 80 | scenarios | write |
| 6 | `base_vs_active_compare` (L1899) | 69 | scenarios | mixed |
| 7 | `save_scenario` (L1116) | 63 | scenarios | write |
| 8 | `record_export` (L1713) | 60 | exports | write |
| 9 | `compare_scenarios` (L1811) | 57 | scenarios | mixed |
| 10 | `resolve_active_scenario_runtime_snapshot` (L245) | 49 | scenarios | mixed |

### 5.2 Write-heavy functions (write + mixed, top 10)

| Function | Class. | Domain | Body LOC |
|---|---|---|---:|
| `save_workspace_state` | write | workspace_state | 131 |
| `save_project` | write | projects | 117 |
| `get_or_create_base_case_scenario` | write | scenarios | 85 |
| `add_scenario` | write | scenarios | 80 |
| `base_vs_active_compare` | mixed | scenarios | 69 |
| `save_scenario` | write | scenarios | 63 |
| `record_export` | write | exports | 60 |
| `compare_scenarios` | mixed | scenarios | 57 |
| `save_run` | write | runs | 48 |
| `update_scenario_overrides` | write | scenarios | 47 |

### 5.3 Functions touching governance / replay metadata

| Function | Touches |
|---|---|
| `save_project` | writes `replay_metadata` JSON |
| `save_scenario` | writes `replay_metadata` JSON |
| `save_run` | writes `replay_metadata` JSON + `governance_state` JSON |
| `record_export` | writes `replay_metadata` JSON, `export_type` enum |
| `get_or_create_base_case_scenario` | reads/writes `governance_state` JSON |
| `runtime_guard_for_snapshot` | reads `governance_state`, returns guard verdict |
| `resolve_active_scenario_runtime_snapshot` | reads `replay_metadata` + `governance_state`, returns runtime snapshot |
| `add_scenario` | writes `governance_state` JSON + `replay_metadata` JSON |
| `update_scenario_overrides` | writes `replay_metadata` JSON |
| `select_scenario` | reads `governance_state` |

### 5.4 Functions used by multiple services / routes

Top 10 most-called (call count across entire `app/`, `main_web.py`, `main_api.py`):

| Function | Calls |
|---|---:|
| `list_scenarios` | 18 |
| `get_scenario` | 18 |
| `get_project_by_code` | 14 |
| `save_workspace_state` | 13 |
| `get_workspace_state` | 13 |
| `get_project_record` | 11 |
| `record_export` | 9 |
| `build_export_lineage` | 8 |
| `list_exports` | 8 |
| `get_scenario_history` | 8 |

### 5.5 Coupled caller files (top 10)

| Caller file | Total repo calls |
|---|---:|
| `main_web.py` | 26 |
| `app/services/scenario_duplicate_service.py` | 26 |
| `app/services/scenario_rename_service.py` | 21 |
| `app/services/scenarios_add_service.py` | 21 |
| `app/services/projects_create_service.py` | 12 |
| `app/services/scenario_state_route_service.py` | 12 |
| `app/services/scenarios_save_service.py` | 12 |
| `app/services/scenario_archive_service.py` | 10 |
| `app/services/project_save_as_service.py` | 8 |
| `app/services/export_audit_service.py` | 7 |

## 6. Direct persistence imports summary

### 6.1 Imports of `app.persistence.repository` (production code)

| Caller | Symbols |
|---|---|
| `main_web.py` (L41-79) | 36 symbols (large bulk import) — see 6.3 |
| `main_web.py` (L2460) | `get_project_record as gpr` (route-local re-import) |
| `app/services/scenario_state_service.py` | `get_scenario_provenance, get_workspace_state, resolve_active_scenario_runtime_snapshot, runtime_guard_for_snapshot` |
| `app/services/export_audit_service.py` | `record_export` |
| `app/services/project_save_as_service.py` | (route-local re-import) `get_project_record as gpr` |

### 6.2 Imports of `app.persistence.provenance`

| Caller | Symbols |
|---|---|
| `main_web.py` (L80) | `build_replay_metadata, utc_now_iso` |
| `app/export/runtime_summary.py` | `build_replay_metadata` |

### 6.3 Imports of `app.persistence.db`

| Caller | Symbols |
|---|---|
| `app/persistence/backup_restore.py` | `DB_PATH` |
| `app/persistence/repository.py` | `get_cursor` |
| `app/persistence/backup_restore.py` | (internal) |

No service or route imports `app.persistence.db` directly. No service or route opens a raw sqlite3 connection.

### 6.4 Direct imports of `app.persistence.backup_restore`

| Caller | Symbols |
|---|---|
| `tests/test_phase24f_sqlite_backup_restore.py` | `create_sqlite_backup, get_backup_dir, get_sqlite_db_path, list_sqlite_backups, restore_sqlite_backup, validate_sqlite_backup` |

Backup-restore is **not** imported from production code. It is used only by tests.

## 7. "Do not touch yet" list

The following functions are intentionally **out of scope** for any future refactor until they have a behavior-preserving characterization test, and the relevant Phase 51F guardrail or a Phase 52B+ side-effect pin covers them:

| Function | Why do-not-touch |
|---|---|---|
| `_init_schema` (db.py L30) | Schema migration path; touching it requires a separate migration plan |
| `get_cursor` (db.py L187) | Connection / commit / rollback semantics; this is the single transactional choke point |
| `restore_sqlite_backup` (backup_restore.py L221) | Restore path is high-stakes; any change needs explicit backout |
| `build_replay_metadata` (provenance.py L112) | Replay metadata shape is consumed by tests + downstream systems |
| `get_or_create_base_case_scenario` (repository.py L86) | Idempotent-or-create semantics; called by multiple services |
| `runtime_guard_for_snapshot` (repository.py L577) | Read+decision; gate logic must stay stable |
| `save_run` (repository.py L608) | Touches `replay_metadata` + `governance_state` + run row |
| `save_project` (repository.py L686) | Largest write; touches project + scenario + workspace in one transaction |
| `save_scenario` (repository.py L1116) | Largest scenario write |
| `save_workspace_state` (repository.py L1496) | Largest workspace write |
| `add_scenario` (repository.py L1299) | Creates scenario + base case + governance; multi-table |
| `promote_scenario_to_base_case` (repository.py L1227) | Promotion path |
| `update_scenario_overrides` (repository.py L1411) | Overrides path |

## 8. Recommended Phase 52B input list

Phase 52B should focus on the **write + mixed** functions that touch `replay_metadata`, `governance_state`, runtime timestamps, `last_run_summary`, `active_scenario_id`, draft/saved snapshot state, `project_origin`, and `baseline_source`. Phase 52B's side-effect matrix should cover at minimum:

1. `save_project` — fields, replay_metadata shape, governance_state shape
2. `save_workspace_state` — draft/saved snapshot semantics, bind order
3. `save_scenario` — replay_metadata, governance_state, baseline_source defaulting
4. `bind_workspace_to_scenario` — active_scenario_id, draft clearing
5. `save_run` — replay_metadata, governance_state, last_run_summary
6. `rename_scenario` — name update + created_at immutability
7. `archive_scenario` — soft archive vs hard delete
8. `select_scenario` — active_scenario_id rotation
9. `update_scenario_overrides` — overrides shape, `is_base_case` gate
10. `duplicate_scenario` — copy + new code/name
11. `add_scenario` — full create path with replay_metadata + governance_state
12. `record_export` — export_type, replay_metadata, governance_state
13. `record_workspace_runtime` — runtime timestamps
14. `discard_workspace_draft` — draft clearing
15. `update_scenario_last_run_summary` — last_run_summary field

## 9. Summary

- 1 god-module (`repository.py`, 2042 LOC, 61 functions)
- 22 write + 5 mixed = 27 write-side functions
- 6 high-risk write functions: `save_workspace_state`, `save_project`, `get_or_create_base_case_scenario`, `add_scenario`, `save_scenario`, `record_export`, `update_scenario_overrides`
- 14 helper functions are pure / low-risk and safe to refactor first
- Direct DB access outside `app/persistence/*`: **none** — clean choke point at `get_cursor`
- All Phase 51F guardrails remain green throughout this mapping (no production code touched)

## 10. Recommended next step

**Phase 52B — Persistence side-effect map.** Build a side-effect matrix over the 15 functions listed in section 8, identifying fields written, metadata written, commit/flush behavior, ordering dependencies, idempotency risk, and whether each side effect is already tested. This is the next prerequisite before any Phase 53 refactor.
