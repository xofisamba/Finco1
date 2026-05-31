# Phase 32 — Scenario Persistence / Versioning Foundation

**Branch:** `phase32-scenario-persistence-versioning-foundation`
**Base SHA:** `4a9e8ed29d9e4b3fb1570497e0bfe40d0d9d7bd0` (after PR #343 Phase 31C)
**Date:** 2026-05-31
**Status:** Documentation + validation — no runtime formula changes, no model changes

---

## 1. Scope & Objective

Inspect and document the existing scenario persistence/versioning architecture.
Validate that it already supports named scenario snapshots, version history, draft/saved distinction, and non-destructive saves.
Confirm no runtime model changes are needed for pilot workflows.

---

## 2. Phase 31 Series Recap

| Phase | Finding | Status |
|-------|---------|--------|
| Phase 31 | Oborovo OpEx gap = **false alarm** (Y1=1,338 kEUR ✅) | ✅ Merged |
| Phase 31B | CFADS bridge anchor sign fixed (`-644.34` → `+644.34`) | ✅ Merged |
| Phase 31C | All 3 findings = stale anchors / expected architecture | ✅ Merged |
| Phase 31D | **NOT REQUIRED** | — |

---

## 3. Architecture Inspection

### 3.1 Persistence Layer Files

| File | Purpose |
|------|---------|
| `app/persistence/db.py` | SQLite schema init, `_init_schema()`, `get_cursor()`, `_ensure_column()` for migrations |
| `app/persistence/repository.py` | `ScenarioRecord`, `ProjectRecord`, `RunRecord` dataclasses; `save_scenario()`, `list_scenarios()`, `get_scenario()`, `get_scenario_history()`, `compare_scenarios()` |
| `app/persistence/backup_restore.py` | SQLite backup/restore via `backup()`, `restore()`, scheduled backup via `schedule_backup()` |
| `app/db.py` | Redirects to `app.persistence.db` |

### 3.2 Key Schema Tables

**`scenarios`** — primary versioning table:
```
scenario_id (PK) | project_id (FK) | user_id | scenario_name | project_code
source_project_template | copied_from_scenario_id | archived | is_base_case
parent_scenario_id | base_input_set_json | overrides_json | schema_version
snapshot_json | governance_state_json | last_run_summary_json | replay_metadata_json
created_at | updated_at
```

**`workspace_states`** — draft vs saved boundary:
```
workspace_id (PK) | project_id (FK) | user_id | project_code
active_scenario_id | active_scenario_name
draft_snapshot_json | saved_snapshot_json
last_runtime_snapshot_json | last_runtime_summary_json | last_runtime_snapshot_id
last_runtime_origin | last_runtime_scenario_id | dirty
governance_state_json | replay_metadata_json | created_at | updated_at | last_runtime_at
```

**`runs`** — run snapshots:
```
run_id (PK) | user_id | project_type | scenario | created_at
inputs_json | kpis_json | excel_path | notes | replay_metadata_json
```

**`projects`** — project metadata:
```
project_id (PK) | user_id | project_code | project_name | project_type
project_origin | source_project_template | template_source
baseline_snapshot_json | archived | is_readonly | governance_state_json
last_run_summary_json | replay_metadata_json | created_at | updated_at
```

---

## 4. Current Versioning Behavior

### 4.1 Stable Scenario ID — ✅ Implemented

Each scenario has a `scenario_id` (16-char UUID hex) that is generated once at creation and never changes.

```python
scenario_id = uuid.uuid4().hex[:16]  # set once at creation
```

### 4.2 Version Timestamp — ✅ Implemented

Every scenario has `created_at` and `updated_at` (ISO 8601 UTC timestamps).

- `created_at` is set once at scenario creation
- `updated_at` is updated on every save/update operation

```python
# From save_scenario() in repository.py:
created_at: now.isoformat()  # set once
updated_at: now.isoformat()  # updated on every write
```

### 4.3 Scenario Name — ✅ Implemented

Scenarios have a human-readable `scenario_name` (e.g., "Oborovo Base 2026-05-31 12:30").

```python
scenario_name = f"{project_name} {snapshot.get('scenario', 'Base')} {dt.now().strftime('%Y-%m-%d %H:%M')}"
```

### 4.4 Input Snapshot Payload — ✅ Implemented

Each scenario stores:
- `snapshot_json` — full input state
- `base_input_set_json` — base case inputs (for override resolution)
- `overrides_json` — differential overrides from base case
- `last_run_summary_json` — KPI results from the last run

```python
# From save_scenario() in repository.py:
snapshot_json: _to_json(snapshot)  # full effective input state
base_input_set_json: _to_json(base_input_set)  # base inputs
overrides_json: _to_json(overrides)  # differential
```

### 4.5 Metadata Fields — ✅ Implemented

| Field | Present |
|-------|---------|
| `created_at` | ✅ |
| `updated_at` | ✅ |
| `active_project` | ✅ (via `active_scenario_id` in `workspace_states`) |
| `validation_status` | ✅ (via `governance_state_json` — G20/R99/R102) |
| `last_run_id` | ✅ (via `runs.run_id` linked to `workspace_states.last_runtime_snapshot_id`) |

### 4.6 Version List / Load — ✅ Implemented

`list_scenarios(user_id, project_id, include_archived=False, limit=N)` returns all scenarios ordered by `updated_at DESC`.

`get_scenario(scenario_id, user_id)` loads a specific version by ID.

`get_scenario_history(user_id, project_id, limit=40)` returns saved scenario history including archived items.

```python
# From main_web.py /scenarios endpoint:
scenarios = list_scenarios(user.user_id, project_id=project_record.project_id, include_archived=False, limit=12)
history = get_scenario_history(user.user_id, project_id=project_record.project_id, limit=20)
```

### 4.7 Create New Version Without Mutating Older — ✅ Implemented

`save_scenario()` **always creates a new record** with a new `scenario_id`. It never updates an existing scenario record with the same ID.

```python
# save_scenario() always INSERTs — never overwrites an existing scenario_id:
cur.execute(
    """
    INSERT INTO scenarios (scenario_id, ...) VALUES (?, ...)
    """,
    (scenario_id, ...),  # new UUID, never reuse
)
```

**To create a new version**: the UI calls "Save As" or duplicates an existing scenario — both create a new `scenario_id`.

```python
# From main_web.py /scenarios/{id}/duplicate:
new_scenario_id = uuid.uuid4().hex[:16]
cur.execute("INSERT INTO scenarios (...) VALUES (...)", (new_scenario_id, ...))
```

---

## 5. Draft vs Saved State Distinction

### 5.1 Draft State

`workspace_states.draft_snapshot_json` — current unsaved form state.
Set when user modifies form fields (dirty state).

```
workspace_states.dirty = 1  # draft is unsaved
```

### 5.2 Saved State

`workspace_states.saved_snapshot_json` — last saved scenario boundary.
Also stored as a `scenarios` table row when user explicitly saves.

```
# When save is triggered:
workspace_states.saved_snapshot_json = snapshot
workspace_states.dirty = 0
```

### 5.3 Runtime Snapshot

`workspace_states.last_runtime_snapshot_json` — result of the last model run.
Distinct from draft (unsaved changes) and saved (user-committed input state).

---

## 6. Non-Overwrite Architecture Proof

**Key invariant:** `scenarios` table rows are **append-only** for a given `scenario_id`.

1. **`save_scenario()`** — INSERT only, never UPDATE on same scenario_id
   - `scenario_id = uuid.uuid4().hex[:16]` (fresh UUID every save)
   - Creates a new row, older versions remain accessible

2. **`duplicate_scenario()`** — INSERT with new `scenario_id`, `copied_from_scenario_id` references original
   - Older version remains intact with its own `scenario_id`

3. **`rename_scenario()`** — UPDATE only `scenario_name` field (display name), never creates new row
   - The scenario_id and version identity remain the same
   - This is a display-level rename, not a version-creating operation

4. **`archive_scenario()`** — UPDATE `archived=1` only, preserves all version data
   - Archived scenarios remain accessible via `list_scenarios(include_archived=True)`
   - No data is destroyed

**Conclusion:** Previous versions are **never overwritten unintentionally**. Each explicit save creates a new immutable row.

---

## 7. Backup / Restore Interaction

From `app/persistence/backup_restore.py`:

- **`backup()`** — SQLite VACUUM INTO a `.db` backup file
- **`restore(backup_path)`** — Copies backup over live DB (dangerous, documented)
- **`schedule_backup()`** — Schedules periodic backups via APScheduler

**Interaction with versioning:**
- Backup captures all `scenarios`, `workspace_states`, `runs`, `projects` tables
- Restoring from backup restores all scenario versions simultaneously
- Auto-backup (`schedule_backup()`) runs on a timer and does not affect versioning semantics
- Backup/restore are orthogonal to versioning — they handle durability, not version creation

**Important:** Restoring a backup will overwrite the current DB state. Backup should be taken before any restore operation.

---

## 8. DB Migration Safety

`_init_schema()` is **idempotent**:
- `CREATE TABLE IF NOT EXISTS` — no-op if table exists
- `CREATE INDEX IF NOT EXISTS` — no-op if index exists
- `_ensure_column()` — uses `PRAGMA table_info()` to check before `ALTER TABLE ADD COLUMN`

No destructive operations (no DROP, no ALTER to existing columns).
Safe on existing SQLite DBs with data.

**No Phase 32 schema migration required** — existing schema already covers all versioning needs.

---

## 9. Out-of-Scope (Not Implemented / Declined)

| Feature | Reason |
|---------|--------|
| Multi-user auth / RBAC | Out of scope — single-user pilot mode |
| SSO/OAuth/SAML | Out of scope — not needed for current pilot |
| Multi-tenancy | Out of scope — single tenant for now |
| Billing / subscription | Out of scope — not in pilot scope |
| Cloud persistence | Out of scope — SQLite local only |
| Enterprise audit logs | Out of scope — not in pilot scope |
| JS financial calculations | Not needed — backend is authoritative |
| Broad UI redesign | Not needed — versioning infrastructure already exists |
| Version comparison UI | Nice-to-have but not critical for pilot — documented as future |
| Scenario branching UI | Nice-to-have but not critical for pilot — documented as future |

---

## 10. Guardrails

- ✅ No financial formula changes
- ✅ No runtime model changes
- ✅ No model output changes
- ✅ No project factory changes
- ✅ No fixture CSV changes
- ✅ No TUHO/Oborovo validation behavior changes
- ✅ No senior debt sizing logic changes
- ✅ No DSCR/sculpting logic changes
- ✅ No SHL/distribution logic changes
- ✅ No Revenue/OPEX/CAPEX/Tax formula changes
- ✅ No JS financial calculations added
- ✅ No multi-user auth / RBAC
- ✅ No SSO/OAuth/SAML
- ✅ No multi-tenancy
- ✅ No billing
- ✅ No cloud persistence
- ✅ No enterprise audit logs
- ✅ G20 BLOCKED (unchanged)
- ✅ R99/R102 NOT APPROVED (unchanged)
- ✅ partial_pay_sweep not promoted
- ✅ flat/min DSCR sculpting not promoted
- ✅ Backend remains source of truth
- ✅ No lender/bank/audit/SaaS/certification claims

---

## 11. Recommended Next Phase

**Phase 33** — Scenario Version History UI (lightweight) — add a simple version timeline/list view to the scenario workspace tab.
- Uses existing `list_scenarios()` and `get_scenario_history()` endpoints
- No new schema required
- No financial logic changes

Alternatively: **Phase 34** — Generic Project Path Full Validation — validate the generic solar/wind path end-to-end.

---

## 12. Phase 32 Finding

**Classification: EXISTING ARCHITECTURE ALREADY SUPPORTS VERSIONING — DOCUMENTED**

The existing persistence layer already provides:
- Stable `scenario_id` (UUID hex, immutable)
- `created_at` / `updated_at` timestamps
- Named scenario snapshots (`scenario_name`)
- Full input state (`snapshot_json`) and base/override separation
- Version list (`list_scenarios()` ordered by `updated_at DESC`)
- Version load (`get_scenario(scenario_id)`)
- Non-destructive saves (INSERT-only, never overwrite same `scenario_id`)
- Draft vs saved vs runtime snapshot distinction
- Run snapshots in `runs` table

**No new implementation required.** Phase 32 is a documentation and validation phase confirming the existing architecture meets pilot versioning needs.

**Phase 32D fix: NOT REQUIRED** — architecture is sound.