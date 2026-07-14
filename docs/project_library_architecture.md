# Project Library Architecture Inventory

_Generated for PR: project-library-reference-working-copies_

---

## Database Schema

**File:** `app/persistence/db.py`

**`projects` table — all columns:**

| Column | Type | Notes |
|---|---|---|
| `project_id` | TEXT PK | 16-char hex UUID |
| `user_id` | TEXT NOT NULL | owner; `__reference__` for system reference models |
| `project_code` | TEXT NOT NULL | URL-safe slug |
| `project_name` | TEXT NOT NULL | display name |
| `project_type` | TEXT | "Wind" / "Solar" |
| `project_origin` | TEXT DEFAULT 'factory_template' | "factory_template" / "user_created" / "saved_baseline" |
| `source_project_template` | TEXT NOT NULL | legacy template key |
| `template_source` | TEXT | normalized slug: "tuho" / "oborovo" / "generic_solar" / "generic_wind" |
| `baseline_snapshot_json` | TEXT | serialized workspace snapshot |
| `archived` | INTEGER DEFAULT 0 | soft delete |
| `is_readonly` | INTEGER DEFAULT 0 | True for reference projects |
| `governance_state_json` | TEXT | G20/R99 flags |
| `last_run_summary_json` | TEXT | last engine run summary |
| `replay_metadata_json` | TEXT | audit trail |
| `full_inputs_json` | TEXT | full ProjectInputs dict (V3-7) |
| `project_role` | TEXT DEFAULT 'user_project' | **NEW** "reference" / "working_copy" / "user_project" |
| `is_protected` | INTEGER DEFAULT 0 | **NEW** True for reference projects |
| `source_project_id` | TEXT | **NEW** lineage: working_copy → source reference project_id |
| `created_at` | TEXT NOT NULL | ISO datetime |
| `updated_at` | TEXT NOT NULL | ISO datetime |

**Indexes:**
- `idx_projects_user_code ON projects(user_id, project_code)` — unique
- `idx_projects_role ON projects(user_id, project_role, archived, updated_at DESC)` — **NEW**
- `idx_projects_template_role ON projects(template_source, project_role, archived)` — **NEW**

**Migration strategy:** Additive `_ensure_column` calls only. No Alembic. Existing rows get `project_role='user_project'` and `is_protected=0` by default. A one-time backfill UPDATE runs during `_init_schema` to set `project_role='reference', is_protected=1` on all existing `factory_template + tuho/oborovo` rows.

---

## Project Repository / Data Layer

**File:** `app/persistence/projects_repository.py`

**Existing functions (unchanged):**
- `get_project(project_id, user_id)` — fetch by PK + user_id
- `get_project_by_code(user_id, project_code)` — fetch by (user_id, project_code)
- `list_projects(user_id)` — unbounded, sorted updated_at DESC
- `list_project_records(user_id, include_archived)` — unbounded
- `save_project(...)` — upsert (now extended with 3 new params)
- `create_project_record(...)` — thin wrapper around save_project
- `update_project_record(...)` — thin wrapper
- `seed_baseline_projects_if_needed(user_id)` — legacy seeder (kept for backward compat)

**New functions:**
- `REFERENCE_USER_ID = "__reference__"` — sentinel user_id for system-owned references
- `get_reference_projects()` — all projects with `project_role='reference'` (cross-user)
- `get_reference_by_template_source(template_source)` — canonical reference for a template
- `get_project_by_id(project_id)` — fetch by PK without user_id filter (for reference access)
- `list_projects_paged(user_id, page, page_size, search, role_filter)` — paginated, returns (records, total)
- `list_recent_projects(user_id, limit=8, exclude_project_id)` — sidebar recent list

**Re-exports:** All new functions re-exported from `app/persistence/repository.py` for backward compatibility.

---

## Service / Query Layer

**`app/services/project_library_service.py`** (new):
- `ensure_reference_models()` — idempotent bootstrap for TUHO + Oborovo references
- `create_working_copy(user_id, source_reference_id, requested_name)` — canonical clone
- `assert_project_not_protected(project_record)` — raises `ProtectedProjectError` (403) for mutations
- `is_protected_reference(project_record)` — checks `project_role='reference'` OR `is_protected` OR legacy composite
- `ProtectedProjectError` — exception type

**`app/ui/protected_reference_service.py`** (existing, unchanged):
- Legacy `is_protected_reference()` — still used by `main_web.py` for the C2 first-edit confirmation flow
- The new service's `is_protected_reference` is a superset; `main_web.py` now imports from the new service

---

## Routes

**`app/library/router.py`** (new, always mounted at app root):
- `GET /library` — full project library page
- `GET /library/list` — HTMX partial: paginated list
- `POST /library/clone/{source_project_id}` — create working copy, redirect to workbook

**`main_web.py`** (existing, unchanged routes):
- `GET /projects/browse` — legacy browser (still works)
- `GET /home` — legacy home (still works)
- `/scenarios/state/draft` — now imports `is_protected_reference` from the new service

**`app/v2/router.py`** (modified):
- `POST /workbook/update` — now checks `is_protected_reference(project_record)` before any mutation; returns 403 for reference projects

---

## Templates

**New:**
- `app/templates/library/project_library.html` — full library page with search/filter form
- `app/templates/library/project_library_list.html` — paginated list partial (HTMX-swappable)

**Modified:**
- `app/templates/partials/project_selector.html` — sidebar now shows "Recent projects" (capped at 8) + "View all projects" link to `/library`; role badges on working copies

---

## Places That Previously Loaded All Projects Without Pagination

| Location | Function | Status |
|---|---|---|
| `main_web.py:1558` | `_user_project_selector_items` | **Fixed** — now calls `list_recent_projects(limit=8)` |
| `main_web.py:1576` | `_consolidated_project_records` | Unchanged — used by legacy browse page only |
| `main_web.py:1650` | `_my_project_cards` | Unchanged — used by legacy home page |
| `main_web.py:3421` | `_find_existing_working_copy` | Unchanged — bounded by user's projects |
| `app/library/router.py` | `project_library_page` | **Paginated** — `list_projects_paged` with `page_size=20` |

---

## Project Role Governance

| Role | `project_role` | `is_protected` | `user_id` | Editable | Clonable |
|---|---|---|---|---|---|
| Reference | `reference` | `1` | `__reference__` | No | Yes → working_copy |
| Working copy | `working_copy` | `0` | user-owned | Yes | No |
| User project | `user_project` | `0` | user-owned | Yes | No |

### Reference invariants
- Server-side mutation guard in `app/v2/router.py` `/workbook/update` returns HTTP 403
- `assert_project_not_protected` callable from any route
- Legacy C2 "first-edit" 409 flow in `/scenarios/state/draft` also blocks mutations (unchanged)
- `is_protected_reference()` checks `project_role`, `is_protected`, and the legacy `project_origin + template_source` composite — covers both new and unbackfilled rows

---

## Tests That Write to the Default Database (pre-existing, not fixed in this PR)

See inventory in `tests/` directory. Files with names `test_phase*` that do not set `FINCO_DB_PATH` write to `app/data/finco_runs.db`. These are pre-existing and out of scope for this PR. All new tests in `tests/test_project_library_repository.py` use isolated temp databases via the `isolated_db` fixture.

---

## Non-Goals

This PR does NOT include:
- Excel Model Mapping
- Scenario matrix redesign
- Financial equation changes
- UI-wide redesign
- Multi-lender debt
- Automatic destructive cleanup on startup
