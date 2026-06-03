# Phase 53E-1 — P0 Behavior Pin for save_project

**Base SHA:** `57eab0add68a6f692e1f9f0332f3a970679c78b9` (post-Block 1 main)
**Phase:** 53E-1 — P0 behavior pin (test/docs only)
**Type:** test/docs/report only
**Status:** COMPLETE. All hard gates passed. Auto-merged.

## 1. Scope

This document records the P0 behavior pin for `save_project` (Group A-2 / project writes) before any extraction. The pin captures the current behavior of `save_project` so that Phase 53E-2 (extraction) can be verified against these expectations without weakening them.

This is a **test/docs/report-only** PR. No runtime code changed.

## 2. Target function

- **Name:** `save_project`
- **Location:** `app/persistence/repository.py` (line 507)
- **Risk:** **high** (one of the 7 high-risk writes identified in Phase 52)

## 3. Pinned behaviors

### 3.1 Public import path

- `save_project` is importable from `app.persistence.repository`
- `save_project.__module__` is `app.persistence.repository` (not a re-export)
- The function is NOT in `projects_repository.py`, `_helpers.py`, `runs_repository.py`, or `exports_repository.py`

### 3.2 Signature

- Name: `save_project`
- Parameters (in order): `user_id, project_code, project_name, source_project_template, project_type, project_origin, template_source, baseline_snapshot, archived, is_readonly, governance_state, last_run_summary, replay_metadata`
- Defaults:
  - `project_type = None`
  - `project_origin = "factory_template"`
  - `template_source = None`
  - `baseline_snapshot = None`
  - `archived = False`
  - `is_readonly = False`
  - `governance_state = None`
  - `last_run_summary = None`
  - `replay_metadata = None`
- Required (no default): `user_id, project_code, project_name, source_project_template`
- Return annotation: `ProjectRecord`

### 3.3 Single-transaction pattern

- `save_project` has **exactly 1** `with get_cursor() as cur:` block
- No nested transactions
- No explicit `cur.commit()` or `cur.flush()` calls

### 3.4 INSERT path (no existing row)

- Generates new `project_id = uuid.uuid4().hex[:16]`
- `created_at = now = _now_utc()`
- `updated_at = now`
- Sets `replay_metadata.setdefault("project_id", project_id)`
- INSERTs 16 columns: `project_id, user_id, project_code, project_name, project_type, project_origin, source_project_template, template_source, baseline_snapshot_json, archived, is_readonly, governance_state_json, last_run_summary_json, replay_metadata_json, created_at, updated_at`

### 3.5 UPDATE path (existing row found)

- Preserves `project_id = existing["project_id"]`
- Preserves `created_at = _from_iso(existing["created_at"])`
- `project_type = project_type or existing["project_type"]`
- `project_origin = project_origin or existing["project_origin"] or "factory_template"`
- `effective_template_source = effective_template_source or existing["template_source"] or source_project_template`
- `baseline_snapshot = _from_json(existing["baseline_snapshot_json"], {})` if input is empty
- `archived = bool(existing["archived"]) if archived is None else archived`
- `updated_at = now`
- Sets `replay_metadata.setdefault("project_id", project_id)`
- UPDATEs the same 12 columns: `project_name, project_type, project_origin, source_project_template, template_source, baseline_snapshot_json, archived, is_readonly, governance_state_json, last_run_summary_json, replay_metadata_json, updated_at`

### 3.6 replay_metadata behavior

- `replay_metadata = dict(replay_metadata or {})` — None is converted to `{}` before use
- `replay_metadata.setdefault("project_id", project_id)` is called in BOTH INSERT and UPDATE paths
- `_to_json(replay_metadata)` is used for storage

### 3.7 governance_state behavior

- `governance_state = governance_state or {}` — None is converted to `{}`
- `_to_json(governance_state)` is used for storage

### 3.8 last_run_summary behavior

- `last_run_summary = last_run_summary or {}` — None is converted to `{}`
- `_to_json(last_run_summary)` is used for storage

### 3.9 baseline_snapshot behavior

- `baseline_snapshot = baseline_snapshot or {}` — None is converted to `{}`
- In UPDATE path: if input is empty, loaded from existing row via `_from_json(existing["baseline_snapshot_json"], {})`
- `_to_json(baseline_snapshot)` is used for storage

### 3.10 project_origin behavior

- Default value: `"factory_template"`
- In UPDATE path: `project_origin = project_origin or existing["project_origin"] or "factory_template"`

### 3.11 template_source behavior

- Default value: `None`
- `effective_template_source = template_source or source_project_template`
- In UPDATE path: `effective_template_source = effective_template_source or existing["template_source"] or source_project_template`

### 3.12 archived / is_readonly behavior

- Both default to `False`
- Both serialized as `int(bool(...))` in the SQL parameters
- In UPDATE path: `archived = bool(existing["archived"]) if archived is None else archived`

### 3.13 created_at / updated_at behavior

- `now = _now_utc()` called exactly once
- INSERT: `created_at = now`, `updated_at = now`
- UPDATE: `created_at = _from_iso(existing["created_at"])`, `updated_at = now`
- Serialized as ISO 8601 via `.isoformat()`

### 3.14 project_id behavior

- INSERT: `project_id = uuid.uuid4().hex[:16]` (16-char hex)
- UPDATE: `project_id = existing["project_id"]` (preserved)
- `replay_metadata.setdefault("project_id", project_id)` in both paths

## 4. SQL fragments pinned

```
SELECT project_id, created_at, project_type, project_origin, template_source, baseline_snapshot_json, archived
FROM projects
WHERE user_id=? AND project_code=?

UPDATE projects
SET project_name=?, project_type=?, project_origin=?, source_project_template=?, template_source=?,
    baseline_snapshot_json=?, archived=?, is_readonly=?, governance_state_json=?, last_run_summary_json=?,
    replay_metadata_json=?, updated_at=?
WHERE project_id=? AND user_id=?

INSERT INTO projects (
    project_id, user_id, project_code, project_name, project_type, project_origin,
    source_project_template, template_source, baseline_snapshot_json, archived, is_readonly,
    governance_state_json, last_run_summary_json, replay_metadata_json, created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```

## 5. Tests added

`tests/test_phase53e1_save_project_p0_behavior_pin.py` with 41 tests across:

- `TestPublicImportPath` (2 tests) — verifies importable from `app.persistence.repository` and `__module__` is `app.persistence.repository`
- `TestSignature` (3 tests) — pins parameter order, defaults, required vs optional
- `TestSQLFragments` (4 tests) — pins SELECT/UPDATE/INSERT SQL fragments and the single-transaction pattern
- `TestReplayMetadataBehavior` (2 tests) — None-to-{} defaulting and `setdefault("project_id", project_id)`
- `TestGovernanceStateBehavior` (2 tests) — None-to-{} defaulting and JSON serialization
- `TestLastRunSummaryBehavior` (2 tests) — None-to-{} defaulting and JSON serialization
- `TestBaselineSnapshotBehavior` (3 tests) — None-to-{} defaulting, JSON serialization, and UPDATE-path preservation
- `TestProjectOriginBehavior` (2 tests) — default value and UPDATE-path fallback
- `TestTemplateSourceBehavior` (3 tests) — default value, initial effective, and UPDATE-path fallback
- `TestArchivedIsReadonlyBehavior` (4 tests) — defaults, UPDATE-path fallback, and `int(bool(...))` serialization
- `TestReturnType` (2 tests) — return annotation and dataclass
- `TestCreatedAtUpdatedAt` (3 tests) — single `_now_utc()` call, INSERT uses now for both, UPDATE preserves created_at
- `TestProjectIdBehavior` (2 tests) — INSERT generates new, UPDATE preserves existing
- `TestExistingCoverage` (3 tests) — verifies Phase 17/20/51 test files exist that already cover save_project
- `TestOtherGuardrails` (4 tests) — verifies save_project is NOT in other persistence modules

## 6. Hard gates verification

| Gate | Status |
|---|---|
| PR based on current main | ✓ (branched from 57eab0a) |
| PR mergeable | ✓ |
| CI passes | ✓ |
| Parity Guardrails (Phase 51F) pass | ✓ |
| Phase 52F G1-G6 persistence guardrails pass | ✓ |
| All new Phase 53E-1 tests pass | ✓ (41/41) |
| Changed files are test/docs/report only | ✓ (no production code changed) |
| No model/parity-core/schema/JS/formula/fixture changes | ✓ |
| No financial formula changes | ✓ |
| No runtime flag promotions | ✓ |
| No rc1 changes | ✓ (rc1 SHA b425a07 still in history) |
| No direct DB/sqlite imports outside app/persistence | ✓ (no new imports) |
| No service imports main_web/main_api | ✓ |
| No direct get_cursor imports outside allowed persistence internals | ✓ (no new imports) |
| repository.py remains public compatibility façade | ✓ (unchanged) |
| Public import paths remain compatible | ✓ |
| Behavior is unchanged | ✓ (test/docs only) |
| No SQL text changes | ✓ (no code changed) |
| No replay_metadata/governance_state/last_run_summary shape changes | ✓ |
| No route/service behavior changes | ✓ |
| No high-risk write behavior changes | ✓ (no write function touched) |
| No test weakening | ✓ (all assertions are new positive checks) |

## 7. Recommended next step

**Phase 53E-2 — Extract project write persistence functions.** Move `save_project` and other A-2 project write functions from `app/persistence/repository.py` to `app/persistence/projects_repository.py`. Behavior must satisfy the 41 pinned behaviors above. The PR must remain **draft** and not be auto-merged — it is a review-required group.
