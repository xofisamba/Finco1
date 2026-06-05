# Phase 57A-9B — CAPEX Sub-Lines Schema + Repository Skeleton

> **Type:** runtime + migration, DRAFT PR
> **Branch:** `phase57a9b-capex-sub-lines-schema`
> **Base:** post-57A-9A main (`c37bc6b8cbd9f144c22a063cccff4925f878d9a3`)
> **rc1:** `b425a0708719eaa5e1d922b1008e5609758e0ad4` — untouched
> **Status:** DRAFT — runtime + migration, design gate is 57A-9A (already MERGED)

## 1. Purpose

Phase 57A-9A (PR #505, MERGED) designed the persistence +
backend model contract for user-added CAPEX sub-lines. This
PR (57A-9B) implements the **schema side** of that design
and the **repository skeleton**: a new `capex_sub_lines`
table, the pure validators + counter + factory project
guard, the locked `CAPEX_CATEGORY_TO_FIELD` mapping, and
the pure `fold_sub_lines_into_capex` aggregation helper.

This PR does **NOT** wire save/load into the project
persistence flow (57A-9C), does **NOT** integrate with the
Run pipeline (57A-9D), does **NOT** change the Excel export
(57A-9E), and does **NOT** touch the
`update_scenario_overrides` allowlist (57A-9C). All four
contracts are deferred to the next runtime PRs in the
phase plan.

## 2. Goals (for 57A-9B)

1. Add the `capex_sub_lines` table with all 16 columns
   from the 57A-9A schema sketch.
2. Add the supporting index `idx_capex_sub_lines_project`.
3. Make the migration idempotent (`CREATE TABLE IF NOT
   EXISTS`, `CREATE INDEX IF NOT EXISTS`).
4. Verify that the existing persistence tables
   (`projects`, `scenarios`, `runs`, `workspace_states`,
   `scenario_exports`) are unchanged.
5. Implement the `CapexSubLine` dataclass (record shape).
6. Lock the `CAPEX_CATEGORY_TO_FIELD` mapping
   (16 categories, 15 unique fields, every field exists on
   `CapexStructure`).
7. Implement pure validators:
   - `validate_parent_category` (C.01..C.16 allowed; C.17,
     C.18, and unknown codes rejected).
   - `validate_business_code` (C.NN.U### format only; the
     C.17/C.18 rejection is enforced at the parent level
     by `validate_parent_category`).
8. Implement `generate_next_business_code(existing_codes,
   parent_category_code)` — pure counter, gap-preserving on
   soft-delete, malformed-codes-tolerated.
9. Implement `assert_project_allows_capex_sub_lines(project_record)`
   — factory guard. `factory_template` and unknown
   `project_origin` raise `PermissionError`.
10. Implement pure aggregation helpers:
    - `resolve_effective_sub_line_amount(default, override)`
      — Claude delta review fix: **override REPLACES default**
      (not a delta).
    - `fold_sub_lines_into_capex(capex, sub_lines, overrides)`
      — factory no-op (empty `user_sub_lines` returns
      `capex` unchanged); C.08 + C.11 fold additively into
      `audit_legal`; soft-deleted excluded; unknown
      categories raise.
11. Implement DB-backed helpers:
    - `list_sub_lines_for_project(cur, project_id, include_inactive=False)`
    - `list_business_codes_for_project(cur, project_id)`
    - `create_sub_line(cur, ...)`
    - `soft_delete_sub_line(cur, ...)`

## 3. Non-goals (for 57A-9B)

- No save/load wiring. The project save / load flow
  (`save_project` in `projects_repository.py`) is unchanged.
  The 57A-9B helpers are the lowest level of the
  persistence stack; they are the building blocks for 57A-9C
  but are NOT called from any existing route / handler in
  57A-9B.
- No Run integration. The `_apply_user_sub_lines_to_capex`
  helper is provided as a pure function in
  `app/persistence/capex_sub_lines.py`, but it is NOT wired
  into the scenario resolution path. 57A-9D.
- No Excel export integration. The `advanced_capex_line_items`
  parameter on `build_excel_export` is unchanged (still
  default `None`). 57A-9E.
- No `update_scenario_overrides` allowlist extension. The
  `SCENARIO_INPUT_FIELDS` set is unchanged at 21 keys. 57A-9C.
- No UI changes. `sheet_capex.html`, `app.js`, `styles.css`
  are untouched. The 57A-8 in-memory preview is still the
  only CAPEX add-line UX in the UI.
- No model changes. `domain/inputs.py` and
  `domain/capex/source_model.py` are untouched.
- No financial output changes. The `fold_sub_lines_into_capex`
  helper is the only place that touches `CapexStructure`,
  and it is not invoked from any existing call site.
- No factory project changes. Factory templates continue to
  be read-only. The `assert_project_allows_capex_sub_lines`
  guard is the only factory enforcement; it is NOT called
  by any existing route / handler.
- No backfill of legacy saved baselines. Migration
  `CREATE TABLE IF NOT EXISTS` is empty; no rows are
  inserted by 57A-9B.
- No G20 / R99 / R102 promotion.
- No Tailwind / Alpine / React / Vue / Svelte.
- No OPEX / Revenue / sub-line work.

## 4. Schema (proposed and committed in this PR)

```sql
CREATE TABLE IF NOT EXISTS capex_sub_lines (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    sub_line_id           TEXT    NOT NULL UNIQUE,
    project_id            TEXT    NOT NULL,
    parent_category_code  TEXT    NOT NULL,
    business_code         TEXT    NOT NULL,
    display_order         INTEGER NOT NULL,
    label                 TEXT    NOT NULL,
    amount_keur           REAL    NOT NULL DEFAULT 0.0,
    comments              TEXT    NOT NULL DEFAULT '',
    schedule_json         TEXT    NOT NULL DEFAULT '{}',
    source                TEXT    NOT NULL DEFAULT 'user',
    is_active             INTEGER NOT NULL DEFAULT 1,
    governance_state_json TEXT    NOT NULL DEFAULT '{}',
    replay_metadata_json  TEXT    NOT NULL DEFAULT '{}',
    created_at            TEXT    NOT NULL,
    updated_at            TEXT    NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(project_id),
    UNIQUE(project_id, business_code)
);

CREATE INDEX IF NOT EXISTS idx_capex_sub_lines_project
    ON capex_sub_lines(project_id, is_active, parent_category_code, display_order);
```

### 4.1 Column rationale

| Column | Type | Rationale |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | Internal monotonic PK; not exposed to UI |
| `sub_line_id` | TEXT UNIQUE | Stable UUID; durable identifier; survives soft-delete + re-add; scenarios override by this |
| `project_id` | TEXT FK → projects | Parent project (the locked TUHO/Oborovo/Generic Solar/Generic Wind/user_project/saved_baseline record) |
| `parent_category_code` | TEXT | e.g. "C.02"; validated against `ALLOWED_PARENT_CATEGORIES` (C.01..C.16); C.17/C.18 rejected |
| `business_code` | TEXT | e.g. "C.02.U001"; format `C.NN.U###`; UNIQUE per project_id |
| `display_order` | INTEGER | 1, 2, 3, ... per (project_id, parent_category_code); used by UI |
| `label` | TEXT | User-supplied display label |
| `amount_keur` | REAL | Project-level default amount; overridable per scenario |
| `comments` | TEXT | Free-form; default empty |
| `schedule_json` | TEXT | Optional M1-M18 schedule override; future (57A-9D+) |
| `source` | TEXT | 'user' / 'imported' / 'cloned'; default 'user' |
| `is_active` | INTEGER | Soft-delete flag; 0 = hidden but row preserved for audit |
| `governance_state_json` | TEXT | Same shape as the rest of the persistence layer |
| `replay_metadata_json` | TEXT | Phase 51F Parity Guardrails pattern |
| `created_at` | TEXT | ISO-8601 UTC |
| `updated_at` | TEXT | ISO-8601 UTC |

### 4.2 Constraint rationale

- `sub_line_id UNIQUE` — durable identifier across
  soft-delete + re-add. Scenarios override by this.
- `UNIQUE(project_id, business_code)` — no two active or
  soft-deleted rows in the same project can share a
  business code. Prevents accidental collisions.
- `FOREIGN KEY(project_id) REFERENCES projects(project_id)` —
  enforces referential integrity at the DB level. Inserting
  a sub-line for a non-existent project raises
  `IntegrityError`. Production code sets
  `PRAGMA foreign_keys = ON` (see `app/persistence/db.py`).

### 4.3 Index rationale

`idx_capex_sub_lines_project` covers the most common
query: "list active sub-lines for this project, ordered by
category + display_order". The column order
`(project_id, is_active, parent_category_code, display_order)`
matches the ORDER BY in `list_sub_lines_for_project`.

## 5. Repository module: `app/persistence/capex_sub_lines.py`

### 5.1 Public surface

```python
ALLOWED_PARENT_CATEGORIES: frozenset[str]   # C.01..C.16
REJECTED_PARENT_CATEGORIES: frozenset[str]  # {"C.17", "C.18"}
CAPEX_CATEGORY_TO_FIELD: Mapping[str, str]  # 16 entries, locked

@dataclass(slots=True)
class CapexSubLine: ...

def validate_parent_category(code) -> str
def validate_business_code(code) -> str
def category_for_field_name(field_name) -> str  # raises KeyError
def generate_next_business_code(existing_codes, parent_category_code) -> str
def assert_project_allows_capex_sub_lines(project_record) -> None
def resolve_effective_sub_line_amount(default, override) -> float
def fold_sub_lines_into_capex(capex, user_sub_lines, scenario_overrides=None) -> CapexStructure

def list_sub_lines_for_project(cur, project_id, include_inactive=False) -> tuple[CapexSubLine, ...]
def list_business_codes_for_project(cur, project_id) -> tuple[str, ...]
def create_sub_line(cur, *, project_id, parent_category_code, label, amount_keur=0.0,
                    business_code=None, comments="", schedule_json="{}",
                    source="user", replay_metadata=None, governance_state=None) -> CapexSubLine
def soft_delete_sub_line(cur, *, project_id, sub_line_id) -> bool
```

### 5.2 The locked mapping (Q4 / Claude delta review)

```python
CAPEX_CATEGORY_TO_FIELD = {
    "C.01": "production_units",
    "C.02": "epc_contract",
    "C.03": "grid_connection",
    "C.04": "ops_prep",
    "C.05": "epc_other",
    "C.06": "insurances",
    "C.07": "lease_tax",
    "C.08": "audit_legal",
    "C.09": "construction_mgmt_a",
    "C.10": "commissioning",
    "C.11": "audit_legal",  # C.08 + C.11 fold additively
    "C.12": "construction_mgmt_b",
    "C.13": "contingencies",
    "C.14": "taxes",
    "C.15": "project_acquisition",
    "C.16": "project_rights",
}
```

C.17 and C.18 are intentionally absent. They are
read-only categories (Financing Costs and Reserve Accounts)
and do not accept user-added sub-lines.

### 5.3 Aggregation rule (Claude delta review fix)

For each sub-line:

1. Look up the parent category in
   `CAPEX_CATEGORY_TO_FIELD`. Unknown categories raise
   `ValueError` — never silent drop.
2. Resolve the effective amount via
   `resolve_effective_sub_line_amount(default, override)`:
   - If `override is None` → return `default`.
   - Else → return `override` (REPLACES the default; it
     is NOT a delta adjustment).
3. The effective amount is added to the existing
   `CapexItem.amount_keur` of the corresponding field.

Soft-deleted sub-lines (`is_active=False`) are excluded.
Multiple sub-lines under the same parent fold additively.
C.08 and C.11 both fold into `audit_legal` — the additive
accumulation is intentional and locked.

Factory projects are a no-op: if `user_sub_lines` is empty,
the helper returns `capex` unchanged. **TUHO / Oborovo /
Generic Solar / Generic Wind parity is preserved by
construction.**

## 6. Files added / changed

| File | Change | LOC | Rationale |
|---|---|---:|---|
| `app/persistence/db.py` | modified | +30 | Add `CREATE TABLE IF NOT EXISTS capex_sub_lines` + index. Idempotent migration. |
| `app/persistence/capex_sub_lines.py` | added | +610 | New module: dataclass, validators, counter, factory guard, aggregation helpers, DB-backed helpers. |
| `tests/test_phase57a9b_capex_sub_lines_schema.py` | added | +1100 | 104 new tests pinning the schema, mapping, validators, counter, factory guard, aggregation contract, and cross-arc consistency. |
| `docs/phase57a9b_capex_sub_lines_schema.md` | added | (this file) | Design + change doc. |
| `reports/phase57a9b_capex_sub_lines_schema.json` | added | +1 | Machine-readable summary. |

Total: 2 production files changed (1 modified, 1 added),
1 test file added, 1 doc added, 1 report added.

## 7. Files NOT changed (all preserved per spec)

- `app/templates/partials/sheet_capex.html`
- `app/templates/partials/_line_item_grid.html`
- `app/templates/partials/workspace_shell.html`
- `static/app.js`
- `static/styles.css`
- `main_web.py`
- `main_api.py`
- `domain/inputs.py`
- `domain/capex/source_model.py`
- `app/waterfall_core.py`
- `app/project_factories.py`
- `app/excel_export.py`
- `app/input_helpers.py`
- `app/ui/project_context.py`
- `app/services/*`
- `app/persistence/_helpers.py`
- `app/persistence/records.py`
- `app/persistence/projects_repository.py`
- `app/persistence/scenarios_repository.py`
- `app/persistence/workspace_repository.py`
- `app/persistence/runs_repository.py`
- `app/persistence/exports_repository.py`
- `app/persistence/repository.py`
- `app/persistence/provenance.py`
- `app/persistence/backup_restore.py`
- `app/persistence/__init__.py`

## 8. Hard no-go (preserved throughout 57A-9B)

- No financial formula changes. `domain/inputs.py`,
  `domain/capex/source_model.py` unchanged.
- No IDC calculation changes. No construction funding
  changes. No debt sizing changes. No tax engine changes.
- No G20 / R99 / R102 promotion.
- No Tailwind / Alpine / React / Vue / Svelte.
- No backend keys visible in UI (Phase 57A-3 invariant
  preserved). The 57A-8 in-memory preview is unchanged.
- No `overrides_json` schema change. `SCENARIO_INPUT_FIELDS`
  still has 21 keys; the allowlist extension lands in
  57A-9C.
- No factory project mutation. Factory templates continue
  to be read-only; `assert_project_allows_capex_sub_lines`
  is the only enforcement and is NOT called by any existing
  route / handler.
- No 57A-8 in-memory preview regression. The 57A-8 toolbar,
  the `data-capex-tmp` marker, the "Unsaved" badge, the
  Run/Save warning, the preview-only totals block all
  continue to work exactly as in 57A-8.
- rc1 (`b425a0708719eaa5e1d922b1008e5609758e0ad4`) frozen
  and verified untouched.

## 9. Phase plan (after 57A-9B)

| Phase | Title | Type | Auto-merge | Pre-req |
|---|---|---|---|---|
| 57A-9A | CAPEX Add-Line Persistence Design Gate | docs/report/test | NO (design gate) | 57A-8 |
| **57A-9B** | **CAPEX Sub-Lines Schema** | **runtime + migration** | **NO (DRAFT)** | **57A-9A** |
| 57A-9C | CAPEX Add-Line Save / Load | runtime | NO | 57A-9B |
| 57A-9D | CAPEX Add-Line Run Integration | runtime | NO | 57A-9C |
| 57A-9E | CAPEX Add-Line Excel Export | runtime | NO | 57A-9D |
| 57A-9F | Agent B post-57A-9 governance refresh | docs/report/test | YES | 57A-9E |
| 57A-10 | Sheet-sheet parity gate (TUHO + Oborovo) | docs/report/test | YES | 57A-9F |

## 10. Stop and document

This PR implements the schema + repository skeleton. It is
**DRAFT** and must NOT be auto-merged. The implementation
is reviewable in isolation because:

- The migration is idempotent and additive to the existing
  schema. No existing table is changed.
- The `capex_sub_lines.py` module is self-contained and
  does NOT import from any UI / static / run / export /
  model / waterfall / factories code.
- The `fold_sub_lines_into_capex` helper is a pure function
  that does NOT modify the input `capex` (returns a new
  `CapexStructure` instance via `dataclasses.replace`). The
  factory no-op branch returns the SAME instance.
- No existing route, handler, template, CSS, or JS is
  changed. The 57A-8 in-memory preview is preserved exactly.
- The 104 new tests pin the design contract end-to-end.

If the reviewer disagrees with the locked mapping, the
aggregation rule, the factory guard, or any other design
choice, the disagreement can be resolved at this PR without
re-touching the schema in 57A-9C / 9D / 9E.

If the reviewer accepts the design, the next runtime PR
(57A-9C) wires `create_sub_line` + `soft_delete_sub_line`
into the project save / load flow, extends the
`update_scenario_overrides` allowlist with the two reserved
keys (`_capex_sub_line_overrides`,
`_capex_sub_line_overrides_metadata`), and pins the
save / load round-trip invariant.
