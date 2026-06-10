# Phase M1 — Read-Only Scenario Matrix Prototype — Governance Doc

## Status

- **Type:** UI-only prototype.
- **Branch:** `phase-m1-scenario-matrix-prototype`
- **Base:** main @ `6020b65f` (post-S3 merge, PR #604)
- **Goal:** Validate layout, usability, information density, navigation, and Excel-like feel for the future Scenario Matrix BEFORE implementing actual scenario overrides.

## What M1 is

M1 is a **read-only UX prototype** of the future Scenario Matrix. It demonstrates the intended column structure — **Base | Downside | Upside | Custom** — using existing project inputs and existing runtime outputs.

The Base column is **live** (reads `project_ctx` directly). The other three columns are **placeholders**:

- **Downside** — UI-only "inherits Base" hint. No override values. No storage.
- **Upside** — UI-only "inherits Base" hint. No override values. No storage.
- **Custom** — UI-only "future override" placeholder. No storage. Reserved for M2.

M1 is the **prototype** for the future UX. M2 will introduce actual scenario overrides, persistence, and calculation.

## What M1 is NOT

M1 is **intentionally NOT**:

- an editable matrix
- a scenario persistence layer
- a scenario CRUD layer
- a scenario calculation engine
- a save/load flow
- a comparison flow
- a financial model change
- a factory / frozen-schedule change
- a debt-sizing change
- a tax / depreciation / IDC change
- a construction / C10 / R-PAR change
- a persistence schema change
- an `app.js` change
- a `main_web.py` / `main_api.py` change
- a Tailwind / Alpine / React / Vue / Svelte introduction
- a `manual_gearing` introduction
- an `R99` / `R102` / `G20` promotion

## Why M1 is read-only

Implementing actual scenario overrides in M1 would require:

- a new persistence schema (table + migration)
- a new `ScenarioOverride` Pydantic model
- new service methods (`add_override`, `update_override`, `delete_override`, `list_overrides`)
- new route endpoints for save/load/delete
- new runtime resolution logic (`_apply_scenario_overrides`)
- new UI affordances (forms, save buttons, conflict resolution)
- new tests for persistence, idempotency, multi-tenant isolation, etc.
- a "live vs. draft" reconciliation flow

That is the **M2** work. M1 is deliberately **simpler**: prove the layout, the column ordering, the row ordering, the information density, the visual inheritance hint, the empty-state handling, and the navigation footprint, without committing to any of the above design decisions.

The matrix in M1 is a **visual contract**: it tells the pilot user what the future UX will look like, with **zero** storage or runtime coupling.

## Inheritance concept (UI-only)

M1 demonstrates the future inheritance concept as a **visual hint**, not as actual inheritance:

- Downside and Upside columns render the literal text `inherits Base` in every cell.
- The Custom column renders the em-dash placeholder (`—`) in every cell.
- A legend at the bottom of the card explicitly states: "Inheritance prototype. UI only. No scenario overrides are stored."
- The card header carries a `M1 PROTOTYPE` badge to make the read-only nature obvious.

When M2 introduces real overrides, the same column headers stay in place; the placeholder text gets replaced with live values. The matrix layout itself does not change.

## Why the Overview tab (and not a new tab)

The task allowed three candidate locations:

1. Overview tab (as a new card below the existing governance cards)
2. A separate Scenario Matrix tab
3. A dedicated prototype page

M1 chose **option 1** because:

- The Overview tab is the highest-traffic page in the workspace; placing the prototype there maximises pilot exposure and minimises "did the user see the matrix?" risk.
- A new tab would require a new entry in `workspace_tabs.html`, a new `tab-panel` in `workspace_shell.html`, and a new panel route — more code surface for a UI-only prototype.
- A dedicated page would be off the workspace path; pilots would have to navigate away from the existing project context.

The Overview placement also keeps the M1 changeset minimal: a single `{% include %}` plus the partial + helper + CSS. No new routing, no new tab, no new page.

## Migration path to M2

When M2 begins, the matrix card becomes the host for:

- **Save buttons** in each non-Base column (Downside / Upside / Custom get an "edit" affordance)
- **Override forms** that bind to scenario-specific draft values
- **Persistence** in a new `capex_scenario_overrides` table (or similar) with `add_override` / `update_override` / `delete_override` helpers
- **Runtime resolution** via a new `_apply_scenario_overrides` path in the input resolver
- **Multi-scenario comparison** (Base vs. Downside vs. Upside side-by-side in the same matrix, with live values in all columns)

The M1 partial, helper module, and CSS are designed to be **forward-compatible** with M2:

- The row registry (`INPUT_ROWS`, `KPI_ROWS`) and column registry (`COLUMNS`) are importable constants, so M2 can re-use them to render the same matrix with live values in all columns.
- The cell renderer (`format_cell_value`, `get_base_value`) is decoupled from the placeholder logic, so M2 can replace the placeholder with a real scenario value by swapping one function.
- The data-m1-* attributes on every cell let M2 add a `data-m2-scenario-override-id` attribute without breaking M1's selectors.

## Test coverage (locked by tests)

The M1 test suite (`tests/test_phase_m1_scenario_matrix.py`) proves:

- **Column registry** (4 columns, canonical order, every column has badge + cell class, Base is "Live", Downside/Upside share "Inherits Base", Custom is "Future override")
- **Row registry** (input rows + KPI rows cover all required project_ctx attributes, inputs come before KPIs, no duplicate attrs)
- **Cell rendering** (non-Base placeholder is em-dash, non-Base inherit note is "inherits Base", inheritance note explains no storage, get_base_value reads ctx attr, format_cell_value uses row formatter, em-dash for None)
- **build_matrix_rows** (populates Base from project_ctx, non-Base columns are placeholders, section ordering invariant, no runtime calculation)
- **Jinja partial** (4 columns in header, Inputs section, Outputs (KPIs) section, all row attrs present, reads project_ctx, renders em-dash for missing value, explains inheritance, has legend, NO save/load buttons, NO editable inputs)
- **workspace_shell.html wiring** (matrix is included inside the Overview panel between the panel-open and panel-close markers)
- **CSS** (Phase M1 block present, all required classes: scenario-matrix-card, scenario-matrix-table, matrix-cell-base, matrix-cell-inherit, matrix-cell-future, badge-base, badge-inherit, badge-future)
- **No scenario persistence** (forbidden paths unchanged via git diff, no scenario-save/load references in partial or helper)
- **Phase invariants** (rc1 SHA resolvable, factory paths unchanged, input adapter / schema unchanged, persistence schema unchanged, no static/app.js changes)
- **File scope** (M1 changeset is exactly the 7 expected files: helper, partial, workspace_shell, CSS, test, docs, report)

## Hard no-go (preserved through M1, all pinned by tests)

- **No financial formula / debt / tax / depreciation / IDC changes**
- **No model / factory / frozen-schedule changes**
- **No construction / C10 / R-PAR changes**
- **No `manual_gearing` debt sizing method**
- **No `min(gearing cap, sculpt)` blend**
- **No senior IDC**
- **No persistence schema migration**
- **No R99 / R102 / G20 promotion**
- **No `static/app.js` changes**
- **No `main_web.py` / `main_api.py` changes**
- **No `app/project_factories.py` / `app/waterfall_runner.py` / `app/waterfall_core.py` / `app/services/` / `app/persistence/` changes**
- **No Tailwind / Alpine / React / Vue / Svelte**
- **No JS calc**
- **No scenario persistence (no `capex_scenario_overrides` table, no save/load)**
- **No scenario CRUD (no routes, no service methods, no scenario endpoints)**
- **No scenario calculation (no `_apply_scenario_overrides` engine path)**
- **`use_construction_schedule_engine` remains False**
- **rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` preserved**

## Files in M1 (7)

- `app/ui/scenario_matrix.py` (NEW) — helper module with column + row registries and cell renderer
- `app/templates/partials/scenario_matrix.html` (NEW) — Jinja partial that renders the matrix card
- `app/templates/partials/workspace_shell.html` (MODIFIED) — wires the matrix into the Overview tab
- `static/styles.css` (MODIFIED) — adds the matrix CSS block
- `tests/test_phase_m1_scenario_matrix.py` (NEW) — 9 test classes, 30+ tests
- `docs/phase_m1_scenario_matrix_prototype.md` (this file)
- `reports/phase_m1_scenario_matrix_prototype.md` — test counts, file-scope audit, pre-merge checklist

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do NOT merge. Awaiting user review and explicit go-ahead before M1 lands on main.
