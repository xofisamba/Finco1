# Phase 57A-9A — CAPEX Add-Line Persistence Design Gate

> **Type:** docs / report / test-only (design gate)
> **Branch:** `phase57a9a-capex-add-line-persistence-design-gate`
> **Base:** post-57A-8 main (`976f5a449e195ecd5fa6ae4fbfe1b734b5ea5446`)
> **rc1:** `b425a0708719eaa5e1d922b1008e5609758e0ad4` — untouched
> **Status:** DESIGN GATE — does NOT implement persistence.
> **Stop-after-report:** This PR is the final word on the persistence
> + backend model contract. No runtime implementation lands in
> 57A-9A. Do not auto-merge without review.

## 1. Purpose

Phase 57A-8 shipped a CAPEX add-line UX that is **in-memory only**.
The user can add temporary sub-lines under any C.01..C.16 category
via a toolbar of `+ Add line` buttons; the new rows live in the
DOM, are visibly labelled "Unsaved / not persisted", and a clearly
worded Run/Save warning block + "Preview only — not used by Run
until persistence is implemented" block make the preview-only
nature of the new rows unambiguous. Persistence is the explicit
follow-up work item.

This document is the **design gate** for that follow-up. It
captures the existing persistence + model architecture, defines
an ownership model for user-added sub-lines, picks a persistence
approach, sketches the data model + business code format +
save/load flow + Run integration + Excel export shape, lays out
the phase plan, and explicitly stops before any implementation.

The objective is to make a future runtime PR (57A-9B or later)
implementable without further design work, and to make any
change to the financial model contract reviewable in isolation.

## 2. Recap: what 57A-8 ships

- 16 `+ Add line` buttons above the LIG grid (one per C.01..C.16,
  **not** C.17 / C.18).
- JS module `bindCapexAddLineUx` (IIFE in `static/app.js`,
  ~269 LOC) is fully DOM-only: no `fetch` / `XHR` /
  `htmx.ajax` / form `.submit` / `localStorage` /
  `sessionStorage`.
- Temporary rows carry `data-capex-tmp="true"`, a generated
  `C.0X.TMP-N` code, an editable label, an editable amount
  input with **no `name` attribute** (never submitted to the
  backend — the form submission would otherwise submit the
  temporary amount to the existing CAPEX update endpoint, which
  is a Phase 20B silent-drop hazard), an "Unsaved" badge, and a
  Remove button.
- The authoritative Hard CAPEX / Financing / Total CAPEX totals
  are NOT modified by temporary rows. A separate preview-only
  totals block is clearly labelled as preview.
- A Run/Save warning block (`#capex-tmp-run-warning`) appears
  whenever temporary rows exist.
- 64 new tests in
  `tests/test_phase57a8_capex_add_line_ux_in_memory.py`.
- 16 skip-guard test files updated to skip cleanly on main.
  The skip-guards add `pytest.skip(...)` paths only and do not
  change the original test semantics (same pattern as the
  Phase 57A-3 followup PR #502).
- rc1 untouched; 776 passed / 59 skipped / 0 failed on main;
  CI green; Parity Guardrails (Phase 51F) green.

57A-8 is the **last in-memory-only phase**. 57A-9A is the
**first persistence design phase**. The arc is: design gate
(57A-9A) → schema (57A-9B) → save/load (57A-9C) → Run integration
(57A-9D) → Excel export (57A-9E) → governance review (57A-9F).

## 3. Goals (for 57A-9A)

1. Decide the **ownership model**: where does the existence of
   a user-added sub-line live, and where does a per-scenario
   amount-only override live?
2. Decide the **persistence approach**: dedicated table vs.
   scenario-override blob vs. hybrid.
3. Sketch the **schema, business code format, save/load flow,
   Run integration, Excel export shape** in enough detail that
   57A-9B / 57A-9C / 57A-9D / 57A-9E can implement without
   further design.
4. Define the **hard no-go list** (financial output invariants,
   rc1 freeze, no-go copy) that all future 57A-9x phases must
   respect.
5. Spell out the **phase plan** with explicit gates between
   design → schema → save/load → Run → Excel.
6. Pin the **design contract** with tests so the gate cannot
   be silently widened later.

## 4. Non-goals (for 57A-9A)

- No implementation of persistence in 57A-9A. The runtime
  change in 57A-8 (in-memory only) is preserved verbatim.
- No schema migration in 57A-9A.
- No backend model change in 57A-9A.
- No Run payload change in 57A-9A.
- No UI behavior change in 57A-9A.
- No financial output change in 57A-9A.
- No G20 / R99 / R102 promotion.
- No Tailwind / Alpine / React / Vue / Svelte.
- No OPEX sub-line persistence in 57A-9A (OPEX is a future arc).
- No Revenue sub-line persistence in 57A-9A (Revenue is a future
  arc).
- No BESS / Hybrid / Generic Solar / Generic Wind promotion.
- No backfill of legacy saved baselines in 57A-9A.

## 5. Existing architecture (the 5 layers we are integrating into)

### 5.1 Persistence layer

| Module | LOC | Role |
|---|---:|---|
| `app/persistence/db.py` | 205 | SQLite connection + schema (runs, projects, scenarios, scenario_exports, workspace_states) |
| `app/persistence/records.py` | 304 | 5 record dataclasses (Project, Scenario, WorkspaceState, Run, ScenarioExport) |
| `app/persistence/_helpers.py` | 137 | `SCENARIO_INPUT_FIELDS` (22 flat input keys), `_to_json` / `_from_json` / `_from_iso` / `_safe_number` / `snapshots_equal` / `_strip_empty_fields` |
| `app/persistence/projects_repository.py` | 494 | Group A reads/writes; `baseline_snapshot` is canonical project input dict |
| `app/persistence/scenarios_repository.py` | 598 | Group B; `overrides_json` blob; `update_scenario_overrides` silently drops unknown keys |

Key invariants:

- `SCENARIO_INPUT_FIELDS` is a **hard-coded set of 22 strings**
  in `_helpers.py` (lines 57-83). Any key not in this set is
  **silently dropped** by `update_scenario_overrides` (line 462
  comment: "silently drop unknown keys per Phase 20B rules").
  Sub-line overrides need a special-cased extension.
- `ProjectRecord.baseline_snapshot` is the canonical input dict
  stored on the project; it is loaded by `get_project_by_code`
  and used as the base for scenario resolution.
- `ScenarioRecord.overrides` is the per-scenario override dict.
  Merged on top of `base_input_set` by
  `resolve_scenario_snapshot(base_input_set, overrides)`.
- The runtime is **not** consulted when resolving the project
  input set for save / load / export — only the snapshot is.
  The Run pipeline reads the snapshot, materializes a
  `ProjectInputs` (via `domain/inputs.py`), and runs the model.

### 5.2 Domain input layer

`domain/inputs.py` (604 LOC) defines:

- `CapexItem` (frozen dataclass, 1 amount field `amount_keur`).
- `CapexStructure` (frozen dataclass, 15 named `CapexItem` fields
  + 6 financing fields: `idc_keur`, `commitment_fees_keur`,
  `bank_fees_keur`, `other_financial_keur`, `vat_costs_keur`,
  `reserve_accounts_keur`).
- `OpexItem` (frozen dataclass, year-1 amount + annual
  inflation).
- `ProjectInputs` (frozen dataclass, contains `capex` and
  `opex`).
- The model reads **only** the 15 named `CapexItem.amount_keur`
  fields. There is no list-of-sub-lines field on `CapexStructure`
  in the model today.

Key model sums (all derived from the 15 named fields):

- `hard_capex_keur` = sum of 15 `CapexItem.amount_keur`
- `total_capex_before_idc` = `hard_capex_keur + commitment_fees_keur + bank_fees_keur + other_financial_keur + vat_costs_keur + reserve_accounts_keur`
- `total_capex` = `total_capex_before_idc + idc_keur`
- `sculpt_capex_keur` = `hard_capex_keur + idc_keur + bank_fees_keur + other_financial_keur + vat_costs_keur` (excludes reserve accounts)

### 5.3 UI / render layer

`app/ui/project_context.py::_build_capex_detail_items` is a
**UI-only** helper that builds 18 categories (C.01..C.18) with
~73 sub-lines sourced from the `_EXCEL_ROWS` constant (TUHO
reference). Each sub-line carries:

- `code` (e.g. "C.01.01")
- `name` (e.g. "Solar panels")
- `amount_keur` (Excel amount, used as display reference)
- `app_amount_keur` (runtime amount from `CapexStructure`)
- `mapping_status` ("app_only" | "excel_only" | "diff")
- `delta_keur` (Excel - app)
- `runtime_source_field` (e.g. "capex.epc_contract.amount_keur")
- `is_backend_calculated` (True for C.17 / C.18 + some auto-mapped rows)
- `authority_summary` (provenance: "Excel reference" | "App runtime" | "App runtime + Excel reference")

The helper merges `_EXCEL_ROWS` with `CapexStructure` runtime
values via the `runtime_source_field` mapping. The output is a
tuple of category dicts; it is **not persisted**, **not
consumed by the model**, and **not round-tripped through
Excel export today**.

`app/templates/partials/sheet_capex.html` renders the tuple into
the LIG grid (post-57A-5B tuple/dict resolution fix), with
`data-capex-add-line="<code>"` hooks on C.01..C.16 and a
`data-capex-tmp` marker for 57A-8 in-memory rows.

### 5.4 Excel export layer

| Module | LOC | Role |
|---|---:|---|
| `app/excel_export.py` | 1235 | `export_project_to_excel(...)`, `_write_sheet`, tax / book depreciation sheets, notes sheet |
| `app/input_helpers.py` | 147 | `build_capex_summary_table(project_inputs)` (2 rows: Total + Sculpt), `build_capex_items_table(project_inputs)` (15-item view), `build_inputs_summary_table` |

The Excel export reads from `project_inputs.capex`
(`CapexStructure`), **not** from `capex_detail_items`. The
`advanced_capex_line_items` parameter on
`export_project_to_excel` and on `_write_tax_depreciation_sheet_for_project`
/ `_write_book_depreciation_sheet_for_project` is currently an
**unused optional** — it is the planned channel for per-line
export in a future arc.

### 5.5 Project origin model

`ProjectRecord.project_origin` is one of:

- `factory_template` — read-only baseline (TUHO, Oborovo,
  Generic Wind, Generic Solar). `is_readonly = True`. Source
  template is fixed.
- `saved_baseline` — user-cloned copy of a factory template.
  Mutable, but anchored to a source template.
- `user_project` — created by user via `/projects/new`.
  `is_readonly = False`. No source template.

Sub-line add / edit / delete is **only** allowed on
`saved_baseline` and `user_project`. Factory templates stay
read-only at the project level; their underlying TUHO
reference data continues to be the sole source of truth.

## 6. Ownership model (the key design decision)

### 6.1 The two questions

1. **Where does the *existence* of a user-added sub-line
   live?** In the project, or per-scenario?
2. **Where does a *per-scenario amount-only override* live?**
   In the project snapshot, or in the scenario overrides blob?

### 6.2 The four-quadrant matrix

| Where existence lives / Where amount lives | In project snapshot | In scenario overrides blob |
|---|---|---|
| **In project baseline_snapshot** | Q1 (single layer, project) | Q2 (split — existence project, amount scenario) |
| **In dedicated `capex_sub_lines` table** | Q3 (split — existence table, amount project) | **Q4 (split — existence table, amount scenario)** |

### 6.3 Why Q4 (Hybrid: dedicated table + scenario override blob)

- Q1 (project only) means user-added sub-lines always run with
  the same amount across every scenario. That makes scenarios
  useless for what-if analysis on user-added lines — the whole
  point of the scenarios feature is to allow per-scenario
  variation. **Rejected.**
- Q2 (existence in project snapshot, amount in scenario blob)
  is the worst of both worlds: the existence is a JSON blob in
  a JSON blob (project snapshot already holds the baseline),
  and the amount lives in a special-cased extension of the
  overrides blob. Schema-less, hard to query, hard to enforce
  referential integrity. **Rejected.**
- Q3 (existence in dedicated table, amount in project
  snapshot) gives us strong referential integrity, easy
  queries, and easy per-project audit, but it still kills
  per-scenario amount variation. **Rejected.**
- Q4 (existence in dedicated table, amount per scenario in
  override blob) is the hybrid:
  - The table holds identity, parent category, business code,
    label, project-level default amount, ordering, governance
    state, soft-delete state, replay metadata. It is the
    **canonical source of truth for what user-added sub-lines
    exist for this project**.
  - The scenario overrides blob holds a per-scenario amount
    override keyed by `sub_line_id` (UUID) — NOT keyed by
    business code, so soft-delete + re-add with the same code
    is safe.
  - When the Run pipeline materializes a `ProjectInputs`, the
    helper `_apply_user_sub_lines_to_capex(capex, user_sub_lines, scenario_overrides)`
    aggregates user sub-lines by parent category and adds
    them to the existing `CapexItem.amount_keur` fields via a
    **per-category mapping table** (see §8).
  - Factory projects (TUHO, Oborovo, Generic Wind, Generic
    Solar) return the `capex` unchanged. **TUHO/Oborovo
    parity is preserved by construction.**

### 6.4 The per-category mapping table

The 15 named `CapexItem` fields in `CapexStructure` map to C.01..C.16
categories roughly as follows. This mapping is the **single
point of integration** between the user sub-line world and the
model world. It is encoded as a constant `CAPEX_CATEGORY_TO_FIELD`
in `app/persistence/capex_sub_lines.py` (proposed, future
runtime PR):

| Category | Name | `CapexStructure` field |
|---|---|---|
| C.01 | Production Unit | `production_units` |
| C.02 | EPC Contract | `epc_contract` |
| C.03 | Grid Connection | `grid_connection` |
| C.04 | Monitoring & Telecom | `ops_prep` |
| C.05 | Operation Investments | `epc_other` |
| C.06 | Insurances | `insurances` |
| C.07 | Land Securing Costs | `lease_tax` |
| C.08 | Bank Due Diligence | `audit_legal` |
| C.09 | Construction Management | `construction_mgmt_a` |
| C.10 | Commissioning | `commissioning` |
| C.11 | Audit & Accounting & Legal | `audit_legal` (shared) |
| C.12 | Construction Mgmt | `construction_mgmt_b` |
| C.13 | Contingencies | `contingencies` |
| C.14 | Import Taxes | `taxes` |
| C.15 | Project Acquisition / Development | `project_acquisition` |
| C.16 | Project Rights | `project_rights` |
| C.17 | Financing Costs | (no per-line mapping; read-only; sum flows from financing fields) |
| C.18 | Reserve Accounts | (no per-line mapping; read-only; sum flows from `reserve_accounts_keur`) |

The mapping is derived from the existing
`_EXCEL_ROWS` data + the existing `runtime_source_field`
strings. It is **proposed**, not committed in 57A-9A. A future
runtime PR (57A-9B) is responsible for verifying and locking
the mapping; if any mapping turns out to be wrong, the helper
fails loudly with `KeyError` rather than silently dropping the
sub-line amount.

### 6.5 Aggregation rule

For each `CapexStructure` field, the helper computes:

```text
effective_amount_keur = base_amount_keur
                        + sum(user_sub_lines for this category
                              - scenario_overrides[sub_line_id]
                              + user_sub_lines.default_amount_keur)
```

That is: the runtime amount is the base `CapexItem.amount_keur`
**plus the sum of effective user sub-line amounts** for that
category. The effective user sub-line amount is the
`sub_line.default_amount_keur` overridden by
`scenario_overrides.get(sub_line_id, default)` if present. Soft-
deleted sub-lines (`is_active = 0`) are **excluded** from the
sum. Hard-deleted sub-lines no longer exist in the table and so
are also excluded.

The `total_capex_keur` and `sculpt_capex_keur` sums on the
`CapexStructure` re-derive automatically because they are
properties that sum the 15 named `CapexItem.amount_keur` fields.
**No new model code is required** for the financial output to
pick up the user sub-lines. This is the entire point of
folding into the existing fields rather than introducing a new
list-of-sub-lines field on `CapexStructure`.

## 7. Persistence approach (the second key design decision)

### 7.1 Five options considered

- **Option 1: Pure scenario override blob.** Encode
  user-added sub-lines entirely in `overrides_json` with
  reserved keys `_capex_sub_lines` and
  `_capex_sub_lines_metadata`. No new table, no migration.
  **Rejected:** schema-less, hard to query, hard to enforce
  referential integrity across scenarios, hard to enforce
  uniqueness of business codes, hard to audit. Also requires
  changing the silent-drop behavior of
  `update_scenario_overrides` (Phase 20B invariant).

- **Option 2: Pure project-snapshot blob.** Encode
  user-added sub-lines in `ProjectRecord.baseline_snapshot`
  with reserved keys `_capex_sub_lines` and
  `_capex_sub_lines_metadata`. No new table, no migration.
  **Rejected:** kills per-scenario amount variation (see Q1
  rejection in §6.3). Also propagates the schema-less
  problem to the project snapshot, which is read by more
  code paths.

- **Option 3: Dedicated table only.** New
  `capex_sub_lines` table holds everything (existence +
  default amount + per-scenario amount override in a side
  column). No scenario override blob. **Rejected as a
  base** because it requires either (a) a column per
  scenario (impossible — scenarios are dynamic) or (b) a
  side column that holds a JSON blob keyed by scenario_id
  (re-introduces the schema-less blob problem inside the
  table). The side-column approach is workable, but the
  Hybrid (Option 4) is cleaner because the override blob
  already exists for the standard flat input fields.

- **Option 4: Hybrid (dedicated table + scenario override
  blob).** This is the **recommended** approach. Existence
  + default amount in the table; per-scenario amount
  override in the scenario's `overrides_json` with reserved
  keys `_capex_sub_line_overrides` and
  `_capex_sub_line_overrides_metadata`. **Selected.**

- **Option 5: Pure project-template copy.** Clone the
  `CapexStructure` shape on a per-project basis (replace
  the 15 named fields with a list of items at the project
  level). **Rejected:** breaking change to the model; the
  model continues to read only the 15 named fields; this
  option would require re-shaping the model or wrapping
  the model in an adapter, both of which are out of scope
  for the persistence design gate.

### 7.2 Selected: Option 4 (Hybrid)

The Hybrid is the **selected** approach. It is the only option
that satisfies all four hard constraints simultaneously:

1. **No new named field on `CapexStructure`.** The model
   continues to read only the 15 named fields. User sub-lines
   fold into the existing fields at materialization time.
2. **Per-scenario amount variation works.** The scenario
   override blob holds the per-scenario amount.
3. **Schema-strong existence.** The table is the single
   source of truth for "what user-added sub-lines exist for
   this project".
4. **Minimal Phase 20B blast radius.** The override blob
   already exists; the only change to
   `update_scenario_overrides` is to add the two reserved
   keys to `SCENARIO_INPUT_FIELDS` (or, more precisely, to
   a separate allowlist that is consulted *before* the
   silent-drop check, see §9.2).

## 8. Schema sketch (proposed for 57A-9B; not committed in 57A-9A)

```sql
CREATE TABLE IF NOT EXISTS capex_sub_lines (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    sub_line_id           TEXT    NOT NULL UNIQUE,        -- stable UUID; survives soft-delete + re-add
    project_id            TEXT    NOT NULL,
    parent_category_code  TEXT    NOT NULL,               -- e.g. "C.02"
    business_code         TEXT    NOT NULL,               -- e.g. "C.02.U001"; "U" prefix avoids collision with template C.NN.NN codes
    display_order         INTEGER NOT NULL,               -- 1, 2, 3, ... per (project_id, parent_category_code)
    label                 TEXT    NOT NULL,
    amount_keur           REAL    NOT NULL DEFAULT 0.0,   -- project-level default amount
    comments              TEXT    NOT NULL DEFAULT '',
    schedule_json         TEXT    NOT NULL DEFAULT '{}',   -- optional M1-M18 schedule override (future)
    source                TEXT    NOT NULL DEFAULT 'user', -- 'user' | 'imported' | 'cloned'
    is_active             INTEGER NOT NULL DEFAULT 1,    -- soft-delete flag; 0 means hidden but row preserved for audit
    governance_state_json TEXT    NOT NULL DEFAULT '{}',
    replay_metadata_json  TEXT    NOT NULL DEFAULT '{}',
    created_at            TEXT    NOT NULL,
    updated_at            TEXT    NOT NULL,
    FOREIGN KEY(project_id) REFERENCES projects(project_id),
    UNIQUE(project_id, business_code)                     -- prevent accidental code collision
);

CREATE INDEX IF NOT EXISTS idx_capex_sub_lines_project
    ON capex_sub_lines(project_id, is_active, parent_category_code, display_order);
```

### 8.1 Business code format

`C.NN.U###` where:

- `C` is the literal "C" prefix.
- `NN` is the 2-digit zero-padded parent category number
  (`01`..`16`; categories C.17 / C.18 are not user-extensible
  in 57A-9A).
- `U` is the literal "U" prefix marking "user-added" (vs.
  the template `C.NN.NN` codes from `_EXCEL_ROWS`).
- `###` is the 3-digit zero-padded counter, unique **per
  `(project_id, parent_category_code)`**. Counter starts at
  `001` and is assigned by `MAX(counter) + 1` on insert.

**Why `U` prefix:** the template `C.NN.NN` codes are reserved
for the canonical catalogue (C.01.01 = "Solar panels" etc.,
see 57A-5B). Prefixing user codes with `U` makes the namespace
disjoint and prevents collisions with future template changes.

**Gaps are preserved on soft-delete:** if `C.02.U001` is
soft-deleted, the counter does not skip to `U003` — it
continues from `MAX(including deleted) + 1`. This keeps
audit trails readable ("U001 was created, deleted, U001
replaced it"). The `business_code` is **not** the durable
identifier; the UUID `sub_line_id` is. Scenarios override
amount by `sub_line_id`, not by `business_code`.

**Hard-deleted rows** (proposed for 57A-9B) release the
business code so it can be reused. This is a separate flag
(`is_active = 0` + `is_hard_deleted = 1` in a future
migration) and is not committed in 57A-9A.

### 8.2 Why a stable UUID separate from `business_code`

Scenarios that override the amount of a sub-line key the
override by `sub_line_id` (UUID). If the user soft-deletes
`C.02.U001` and creates a new `C.02.U001` with a new UUID,
the old scenario's override still references the old UUID and
silently becomes a no-op. This is the desired behavior: the
scenario does not "follow" the new line. The user can manually
re-bind the override if desired (future UX work, not in
57A-9A).

### 8.3 Replay metadata

`replay_metadata_json` follows the same shape as the rest of
the persistence layer (Phase 53I-2 pattern): a JSON blob
holding `last_replay_id`, `last_replay_at`, `last_replay_sha`,
`replay_count`, etc. It is written on every save and consumed
by the Phase 51F Parity Guardrails scanner.

## 9. Save / load flow (proposed for 57A-9C; not committed in 57A-9A)

### 9.1 Project save flow

The current `save_project` (in
`app/persistence/projects_repository.py`, 130-280) writes
`baseline_snapshot_json` to the `projects` table. The
proposed 57A-9C change adds a sibling function
`save_project_with_sub_lines` (or extends `save_project` with
a `sub_lines` parameter) that:

1. Calls the existing `save_project` to write the project
   row.
2. Opens a single transaction.
3. Marks all existing `capex_sub_lines` rows for the
   `project_id` as `is_active = 0` (soft-delete).
4. Inserts the new sub-lines with `is_active = 1` and fresh
   `sub_line_id` UUIDs.
5. Commits.

This is the standard soft-delete + re-insert pattern; the
audit trail is preserved (soft-deleted rows are not garbage-
collected on save; they are kept for replay / governance).

### 9.2 Scenario override flow

The current `update_scenario_overrides` (in
`app/persistence/scenarios_repository.py`, 442-475) silently
drops any key not in `SCENARIO_INPUT_FIELDS`. The proposed
57A-9C change introduces a **second allowlist**,
`SCENARIO_SUB_LINE_OVERRIDE_KEYS = {"_capex_sub_line_overrides",
"_capex_sub_line_overrides_metadata"}`, that is consulted
*before* the silent-drop check. The behavior is:

- If `key` is in `SCENARIO_INPUT_FIELDS` → store as today.
- Else if `key` is in `SCENARIO_SUB_LINE_OVERRIDE_KEYS` →
  store as today, **but** validate the shape (a dict keyed
  by UUID with float values, or a metadata dict with
  `last_modified_at` and `schema_version`).
- Else → silently drop as today (Phase 20B invariant
  preserved).

The shape validation lives in a new module
`app/persistence/capex_sub_lines.py` (proposed):

```python
def validate_sub_line_override_blob(blob: dict) -> dict:
    """Return a sanitized copy of the override blob. Raises ValueError on schema errors."""
    if not isinstance(blob, dict):
        raise ValueError("sub-line override blob must be a dict")
    out: dict[str, float] = {}
    for sub_line_id, amount in blob.items():
        if not isinstance(sub_line_id, str) or not sub_line_id:
            raise ValueError(f"sub_line_id must be a non-empty string, got {sub_line_id!r}")
        if not isinstance(amount, (int, float)):
            raise ValueError(f"override amount for {sub_line_id!r} must be a number, got {amount!r}")
        out[sub_line_id] = float(amount)
    return out
```

This is the only change to `update_scenario_overrides` and it
is additive (the existing 22-key flat-path is unchanged).

### 9.3 Run integration (proposed for 57A-9D; not committed in 57A-9A)

The Run pipeline materializes a `ProjectInputs` from the
project snapshot. The proposed 57A-9D change adds a single
helper call **after** snapshot resolution and **before** the
model is invoked:

```python
def _apply_user_sub_lines_to_capex(
    capex: CapexStructure,
    user_sub_lines: tuple[CapexSubLine, ...],
    scenario_overrides: dict[str, dict[str, float]],
) -> CapexStructure:
    """Return a new CapexStructure with user sub-line amounts folded in.

    Factory projects (no user sub-lines, empty tuple) return capex unchanged.
    """
    if not user_sub_lines:
        return capex
    # ... build per-category deltas, fold into the appropriate CapexItem ...
    return new_capex
```

The helper is invoked from the existing
`_resolve_inputs_for_scenario` (or its 53G-1 equivalent) in
`app/services/inputs_service.py` (or wherever scenario
resolution lives — that is part of the 57A-9D design
verification). The result is a new `CapexStructure` with
the existing 15 named fields updated; the model then
operates on it exactly as it does today.

**Factory project safety:** `_apply_user_sub_lines_to_capex`
returns `capex` unchanged when the `user_sub_lines` tuple is
empty. Factory projects (TUHO, Oborovo, Generic Wind, Generic
Solar) have no user-added sub-lines, so the helper is a
no-op. **TUHO/Oborovo parity is preserved by construction**;
this is the same pattern as the existing Phase 20H
`_skip_immutability_check_for_factory_projects` guard.

### 9.4 Excel export integration (proposed for 57A-9E; not committed in 57A-9A)

The existing `export_project_to_excel(...,
advanced_capex_line_items=None, ...)` parameter is currently
unused. The proposed 57A-9E change:

1. Materializes the user sub-lines into a tuple of objects
   compatible with `advanced_capex_line_items` (one
   object per `is_active = 1` row, with `amount_keur`
   already overridden by the scenario override blob).
2. Passes the tuple as `advanced_capex_line_items`.
3. The downstream tax / book depreciation sheets consume
   the tuple as today; the existing
   `map_capex_line_item_to_basis` helper applies.
4. The summary CapEx sheet (`build_capex_summary_table`)
   is **not** changed — it reads the post-`CapexStructure`
   sum, which already includes the folded user sub-lines.

**No change to `build_capex_summary_table` or
`build_capex_items_table` is required** — they read from
`project_inputs.capex`, which is already the post-fold
structure. This is the same leverage as in 57A-9D.

### 9.5 Save / load test invariant

The save / load flow must be **round-trippable**: write
project snapshot + sub-lines + scenario overrides, read them
back, run the model, get bit-identical results to the
in-memory-only state. This is the test invariant that
57A-9C and 57A-9D must satisfy; 57A-9A only documents it.

## 10. Governance + audit + replay

- All `capex_sub_lines` writes go through
  `app/persistence/capex_sub_lines.py` (proposed). Direct
  SQL from UI / route handlers is forbidden by convention
  (Phase 53I-2 rule).
- Every write increments `replay_metadata_json.replay_count`
  and stamps `last_replay_at` + `last_replay_sha` (Phase
  51F Parity Guardrails pattern).
- The Phase 51F Parity Guardrails scanner is extended
  (in 57A-9B or 57A-9C, **not** in 57A-9A) to also
  scan `capex_sub_lines` for the no-go copy list. The
  no-go copy list is unchanged.
- The Phase 53I governance refresh (run in 57B) is
  re-run after 57A-9E lands (a 57A-9F governance refresh
  PR is part of the phase plan, see §13).

## 11. Hard no-go (preserved throughout all 57A-9x phases)

These are the **hard no-go** items. Each is enforced by an
existing test, scanner, or convention. They are listed here
as the contract that 57A-9A pins — every future 57A-9x PR
must continue to satisfy them.

- **No financial formula change.** `domain/inputs.py`,
  `domain/financing.py`, `domain/revenue.py`, the model
  layer — all unchanged. The user sub-lines fold into the
  existing 15 named `CapexItem` fields; they do not
  introduce a new sum path.
- **No IDC calculation change.** IDC is derived from the
  15 named fields (via the construction funding engine) and
  is unaffected by where the sub-line amounts come from.
- **No construction funding engine change.** Same reason.
- **No senior debt / SHL drawdown change.** Same reason.
- **No tax engine change.** Same reason.
- **No depreciation engine change.** The book depreciation
  and tax depreciation sheets consume the
  `advanced_capex_line_items` parameter that already exists.
- **No G20 / R99 / R102 promotion.** Generic Solar / Wind
  remain exploratory / unvalidated; their underlying TUHO
  reference data continues to be the sole source of truth
  for those templates.
- **No Tailwind / Alpine / React / Vue / Svelte.** Frontend
  stack stays as server-rendered Jinja + HTMX + custom CSS
  + vanilla JS.
- **No backend keys visible in UI.** The Phase 57A-3 backend
  key hiding continues to apply — `lease_tax`, `epc_contract`,
  `project_rights`, etc. are not shown in the LIG grid even
  when the user adds a sub-line under a category whose
  `CapexStructure` field is one of these backend keys. The
  display name (e.g. "EPC Contract", "Land Securing Costs")
  is what the user sees, not the snake_case field name.
- **No new `app/domain/...` modules.** The new persistence
  helper lives under `app/persistence/capex_sub_lines.py`,
  not under `app/domain/...`.
- **No `overrides_json` schema change.** The two new
  reserved keys (`_capex_sub_line_overrides`,
  `_capex_sub_line_overrides_metadata`) are **additive** to
  the existing 22-key `SCENARIO_INPUT_FIELDS` set. The
  silent-drop behavior for unknown keys is preserved.
- **No silent override of an existing scenario override.**
  If a scenario already has an override for `sub_line_id` X
  and the user adds a new sub-line with that same `sub_line_id`
  (impossible by UUID uniqueness, but defensive), the new
  amount is **rejected** with a clear validation error.
- **No factory project mutation.** Factory templates
  (`factory_template` origin, `is_readonly = True`) cannot
  have user-added sub-lines. The persistence helper raises
  `PermissionError` on attempt. This is the
  `project_origin` invariant from §5.5.
- **rc1 frozen.** `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  is the release-candidate SHA; it is not touched by any
  57A-9x PR.
- **No 57A-8 in-memory preview regression.** The 57A-8
  toolbar of `+ Add line` buttons, the `data-capex-tmp`
  marker, the "Unsaved" badge, the Run/Save warning block,
  and the preview-only totals block all continue to work
  exactly as they do today. Persistence is a strict
  superset: the user can add a temporary row (in-memory)
  and then **save the project** to persist it; both flows
  coexist.

## 12. Out of scope (for the 57A-9 arc)

- OPEX sub-line persistence. OPEX already has per-line
  inflation + step in `OpexItem`, so the model is already
  list-shaped. The 57A-9 design does **not** carry over to
  OPEX; OPEX is a separate future arc.
- Revenue sub-line persistence. Revenue is a future arc.
- Construction schedule (M1-M18) per sub-line override.
  The `schedule_json` column is reserved for a future
  enhancement; 57A-9A only documents the column.
- Tax / depreciation **per-line** override. The
  `advanced_capex_line_items` parameter already supports
  per-line tax / depreciation, but the user-facing UX for
  editing those fields is a future arc.
- Sub-line cloning on scenario creation. The default
  behavior on scenario copy is to inherit the project-level
  default amount. Per-scenario overrides survive the copy
  via the standard `overrides_json` machinery. Cloning
  semantics for new vs. inherited sub-lines are a future
  UX decision (not in 57A-9A).
- Sub-line import / export via Excel. The 57A-9E
  Excel export includes user sub-lines in the
  `advanced_capex_line_items` parameter, but a round-trip
  Excel import that re-creates the `capex_sub_lines` rows
  is a future arc.
- Multi-user sub-line collaboration. The persistence
  helper is per-`user_id` like the rest of the
  persistence layer; multi-user collaboration is out of
  scope.

## 13. Phase plan (proposed, not committed in 57A-9A)

| Phase | Title | Type | Auto-merge | Pre-req | Notes |
|---|---|---|---|---|---|
| **57A-9A** | **CAPEX Add-Line Persistence Design Gate** | docs/report/test | NO (this PR — design gate) | 57A-8 | **THIS PR.** No implementation. |
| 57A-9B | CAPEX Add-Line Schema | runtime + migration | NO (visual review of migration) | 57A-9A | Adds the `capex_sub_lines` table, the `app/persistence/capex_sub_lines.py` module skeleton, and the migration. No UI change. No save / load change. |
| 57A-9C | CAPEX Add-Line Save / Load | runtime | NO (visual review of save flow) | 57A-9B | Wires the project save / load flow to the new table. Adds the 2-key allowlist extension to `update_scenario_overrides`. No Run change. No UI change beyond the existing 57A-8 toolbar (which now optionally persists on save). |
| 57A-9D | CAPEX Add-Line Run Integration | runtime | NO (visual review of post-fold numbers vs. in-memory preview) | 57A-9C | Adds the `_apply_user_sub_lines_to_capex` helper, wires it into the scenario resolution path, and verifies the post-fold numbers match the in-memory preview within rounding tolerance. |
| 57A-9E | CAPEX Add-Line Excel Export | runtime | NO (visual review of Excel output) | 57A-9D | Materializes the user sub-lines into the existing `advanced_capex_line_items` parameter. The summary CapEx sheet and the 15-item CapEx_Items sheet pick up the folded amounts automatically. |
| 57A-9F | Agent B post-57A-9 governance refresh | docs/report/test | YES (auto-merge eligible) | 57A-9E | Re-runs the Phase 53I governance refresh and the Phase 51F Parity Guardrails extension. Updates the no-go copy scanner (57D) to also scan `capex_sub_lines`. |
| 57A-10 | Sheet-sheet parity gate (TUHO + Oborovo) | docs/report/test | YES (auto-merge eligible) | 57A-9F | Verifies that the post-57A-9F TUHO Baseline and Oborovo Baseline sheets produce **bit-identical** numbers to the pre-57A-9B baselines, with the new user sub-line code path disabled (no `capex_sub_lines` rows for those projects). |

Each runtime PR in the plan must:

1. Pass the existing test suite on main + the new
   per-phase tests.
2. Pass the Phase 51F Parity Guardrails.
3. Produce visual QA screenshots for the 57A-8 preview
   + the new persisted state, and post them under
   `reports/phase57a9{letter}_visual_qa/`.
4. Get a `DRAFT` PR opened (no auto-merge) and a squash-
   merge with `delete_branch` flag, just like 57A-5 / 57A-8.

## 14. Stop and document

57A-9A is the **design gate**. It is the last PR in the
57A-9 arc that lands without review. The runtime PRs
(57A-9B through 57A-9E) are explicitly NOT started in
57A-9A. Do not auto-merge 57A-9A. Open it as a DRAFT and
wait for review.

The reason for the explicit stop is that this is the
**first time the CAPEX structure shape changes** in a way
that affects the model layer's input contract. Even though
the change is additive at the model level (we fold into
the existing 15 named fields), the persistence contract
changes, the scenario override contract changes, the
Excel export contract changes, and the governance /
audit / replay contract changes. All four of these
contracts are pinned by 57A-9A's design and verified by
its tests. The runtime PRs implement the design; they
should not redesign it.

If the reviewer disagrees with the design — e.g.
prefers a pure override-blob approach (Option 1), or
a pure-table approach (Option 3), or a model-layer
list-of-sub-lines approach (Option 5) — the disagreement
is resolved at the design gate, not at the runtime PR.
That is what the design gate is for.

## 15. Test scope (for 57A-9A)

The 57A-9A PR is docs/report/test-only. The tests in
`tests/test_phase57a9a_capex_add_line_persistence_design_gate.py`
pin the design contract. The full list is in §15.1.

### 15.1 Test list

1. The design doc exists at
   `docs/phase57a9a_capex_add_line_persistence_design_gate.md`.
2. The report JSON exists at
   `reports/phase57a9a_capex_add_line_persistence_design_gate.json`.
3. The report is valid JSON and has the expected top-level
   keys (`phase`, `title`, `type`, `branch`, `base_sha`,
   `ownership_model`, `persistence_approach`,
   `schema_sketch`, `phase_plan`, `hard_no_go`, `rc1_frozen_sha`).
4. The design states the **ownership model** is Hybrid
   (Q4): existence in dedicated `capex_sub_lines` table,
   amount per scenario in override blob.
5. The design states the **persistence approach** is
   Option 4 (Hybrid) and explicitly rejects Options 1, 2,
   3 (as base), and 5.
6. The design defines a **per-category mapping table**
   that maps each C.01..C.16 category to the corresponding
   `CapexStructure` field name.
7. The design defines the **business code format**
   `C.NN.U###` with a 3-digit counter per
   `(project_id, parent_category_code)`.
8. The design requires a **stable UUID `sub_line_id`**
   separate from the business code, and explains why.
9. The design defines the **scenario override blob shape**:
   `{"_capex_sub_line_overrides": {<sub_line_id>: <float>, ...},
   "_capex_sub_line_overrides_metadata": {...}}`.
10. The design defines the **silent-drop allowlist extension**
    for `update_scenario_overrides` (additive, 2 new keys,
    shape validation, Phase 20B invariant preserved for all
    other keys).
11. The design defines the **Run integration helper**
    `_apply_user_sub_lines_to_capex(capex, user_sub_lines, scenario_overrides)`
    and the aggregation rule (base + sum of effective user
    sub-line amounts, soft-deleted excluded).
12. The design states that **factory projects are no-ops**
    for the helper (no user sub-lines → `capex` unchanged;
    TUHO / Oborovo parity preserved by construction).
13. The design defines the **Excel export integration**
    via the existing `advanced_capex_line_items` parameter
    (no change to `build_capex_summary_table` /
    `build_capex_items_table`).
14. The design defines the **save / load round-trip**
    invariant: write project + sub-lines + overrides, read
    back, run, get bit-identical results to in-memory.
15. The design lists the **hard no-go items** explicitly
    (no formula change, no IDC change, no construction
    funding change, no tax engine change, no G20 / R99 /
    R102 promotion, no Tailwind / Alpine, no backend keys
    visible, no factory project mutation, rc1 frozen, no
    57A-8 regression).
16. The design lists the **out-of-scope items** explicitly
    (OPEX / Revenue / per-line schedule / per-line tax /
    scenario cloning semantics / Excel import / multi-user).
17. The design lays out the **phase plan** as a table with
    7 rows (57A-9A through 57A-10), each with type,
    auto-merge, pre-req, and notes.
18. The design **does not introduce any runtime
    implementation** — no migration, no schema change, no
    model change, no UI change, no financial output change.
19. The design **pins rc1** as
    `b425a0708719eaa5e1d922b1008e5609758e0ad4`.
20. The design **does not start the runtime PRs** — it
    explicitly stops after the report and waits for review.

## 16. Hard no-go (preserved throughout 57A-9A)

- No financial formula changes.
- No IDC calculation changes.
- No construction funding changes.
- No G20 / R99 / R102 promotion.
- No Tailwind / Alpine.
- No Portfolio / BESS / Hybrid.
- No schema migration in 57A-9A.
- No backend keys visible in UI.
- No runtime implementation in 57A-9A.
- rc1 (`b425a0708719eaa5e1d922b1008e5609758e0ad4`)
  frozen.
