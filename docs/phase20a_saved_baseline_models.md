# Phase 20A — Saved Baseline Models

## Overview

Introduces a **Saved Baselines** tier of projects (TUHO — Baseline, Oborovo — Baseline) that are persisted in the database with full snapshots, distinct from runtime factory templates and user-created projects.

---

## Motivation

Factory templates (TUHO, Oborovo) were generated on-the-fly at runtime with no persistent project record. Users making edits had no way to preserve or branch from a known-good starting state.

Saved baselines solve this by:
1. Persisting a read-only snapshot of each model at a reference configuration
2. Allowing "Save As" to branch into a fully-editable user project
3. Providing provenance tracking (`baseline_source` flag in export lineage)

---

## Architecture

### Three-Tier Project Model

| Tier | Origin Value | Persisted | Editable | Example |
|------|-------------|-----------|----------|---------|
| **Factory Templates** | `factory_template` | No (runtime only) | No | TUHO, Oborovo (stateless) |
| **Saved Baselines** | `saved_baseline` | Yes | No (read-only) | TUHO — Baseline, Oborovo — Baseline |
| **User Projects** | `user_created` | Yes | Yes | My Oborovo Variant |

### Database Changes

**`projects` table — new column:**
```sql
ALTER TABLE projects ADD COLUMN is_readonly INTEGER NOT NULL DEFAULT 0;
```

**`project_origin` values:**
- `factory_template` — runtime-only factory templates
- `saved_baseline` — persisted baseline models with read-only flag
- `user_created` — user-editable projects and scenarios

### Key Files Changed

| File | Change |
|------|--------|
| `app/persistence/db.py` | Added `is_readonly` column via `_ensure_column` |
| `app/persistence/repository.py` | `ProjectRecord.is_readonly` field; `seed_baseline_projects_if_needed()`; `list_baseline_records()`; `_compute_baseline_snapshot()` |
| `main_web.py` | Baseline seeding on `/` access; save blocked for non-`user_created` origins; `/projects/{code}/save-as` endpoint; `baseline_source` in export provenance |
| `app/templates/partials/project_selector.html` | Three-section layout (Factory Templates / Saved Baselines / User Projects) with Save-As button on baseline cards |

---

## New Endpoints

### `POST /projects/{project_code}/save-as`

Duplicates a factory template or saved baseline into a new user-editable project.

**Behavior:**
- Factory template → creates `user_created` project with factory snapshot
- Saved baseline → creates `user_created` project with baseline snapshot, sets `baseline_source=True` in replay metadata
- User project → returns `400 Bad Request`

**Response:** `302 Redirect` to `/?project={new_code}`

---

## New Repository Functions

### `seed_baseline_projects_if_needed(user_id) -> list[ProjectRecord]`

Idempotent. Creates TUHO — Baseline and Oborovo — Baseline if they don't exist for the user. Called on every `/` render to ensure baselines are always available.

### `list_baseline_records(user_id) -> list[ProjectRecord]`

Returns all `saved_baseline` projects for a user (excludes factory templates and user projects).

### `_compute_baseline_snapshot(project_type, template_source) -> dict`

Builds a workspace-ready snapshot dict from factory project inputs — same data that drives the runtime for factory templates.

---

## Blocking Behavior

### Save Blocked For

- `factory_template` origins — stateless, no persistent record to update
- `saved_baseline` origins — read-only by design; use Save As instead

**Blocked POSTs return:** The scenario workspace render with an explanatory message (not an error page).

### Save Allowed For

- `user_created` projects — full save semantics as before

---

## UI Changes

### Project Selector Sidebar

Three grouped sections:
1. **Factory Templates** — TUHO, Oborovo, Generic Wind, Generic Solar (stateless)
2. **Saved Baselines** — TUHO — Baseline, Oborovo — Baseline (persisted, read-only)
   - Each card has a `↗` Save As button
3. **User Projects / Scenarios** — user-created projects (fully editable)

### Save As Button

Appears on baseline cards. Submits `POST /projects/{code}/save-as`. Creates a new user project and redirects to it.

---

## Export Provenance

All export types now record `baseline_source` in `replay_metadata`:

```json
{
  "baseline_source": true   // true if project_origin == "saved_baseline"
}
```

Applies to: `excel_model_export`, `runtime_summary_csv`, `institutional_workbook`.

---

## Governance Posture

All baseline and user project records are initialized with:

```python
governance_state = {
    "g20": "BLOCKED",
    "r99_r102": "NOT_APPROVED",
    "lender_ready": False
}
```

---

## Test Coverage

### Repository Tests (`test_phase20a_saved_baseline_models.py`)

- `TestBaselineSnapshotComputation` — snapshot field content for TUHO, Oborovo, generic templates
- `TestBaselinePersistence` — seeding idempotency, readonly flag, origin value, baseline snapshot populated
- `TestIsReadonlyField` — `save_project` and `create_project_record` respect `is_readonly` flag

### Web Tests (`test_phase20a_saved_baseline_models_web.py`)

- `TestBaselineSeeding` — baselines created on first `/` access
- `TestSaveBlockedForBaselines` — save rejected for `factory_template` and `saved_baseline`
- `TestSaveAsBaseline` — save-as creates `user_created` project; rejects duplicate of user project
- `TestExportProvenanceBaselineSource` — `baseline_source` recorded in export metadata

---

## Out of Scope

- Editing baselines in-place (always read-only)
- Versioning or diffing baselines
- Baseline comparison UI
- Exporting baselines as standalone templates