# Phase M1 — Read-Only Scenario Matrix Prototype — Report

## Status

- **Type:** UI-only prototype.
- **Branch:** `phase-m1-scenario-matrix-prototype`
- **Base:** main @ `6020b65f` (post-S3 merge, PR #604)
- **PR:** DRAFT only. Do NOT mark ready. Do NOT merge. Awaiting user review.
- **Scope:** ~7 files, +1.3k / -0 (UI + helper + tests + docs).

## Summary

Phase M1 is a **read-only UX prototype** of the future Scenario Matrix. It demonstrates the intended column structure — **Base | Downside | Upside | Custom** — using existing project inputs and existing runtime outputs. The Base column is live; the other three columns are placeholders that visually communicate the future inheritance and override semantics without any storage or runtime coupling.

M1 is the prototype for layout / usability / information density / navigation / Excel-like feel. M2 will introduce actual scenario overrides, persistence, and calculation.

## Files in M1 (7)

### Production code (4)

- `app/ui/scenario_matrix.py` (NEW, +352/-0) — helper module
  - `COLUMNS = ("Base", "Downside", "Upside", "Custom")` — canonical column order
  - `COLUMN_BADGES` / `COLUMN_CELL_CLASSES` — per-column visual metadata
  - `INPUT_ROWS` / `KPI_ROWS` / `ALL_ROWS` — row registries
  - `MatrixRow` dataclass (label, kind, attr, fmt, unit)
  - `get_base_value(ctx, row)` / `format_cell_value(row, value)` — cell renderer
  - `build_matrix_rows(ctx, rows)` — render-ready row list
  - `INHERITANCE_NOTE` — UI-only text explaining the prototype

- `app/templates/partials/scenario_matrix.html` (NEW, +175/-0) — Jinja partial
  - Renders the matrix card with 4 columns, 2 sections (Inputs / Outputs (KPIs))
  - Reads `project_ctx` directly (no route changes needed)
  - Renders em-dash for missing values
  - Has inheritance note + legend at the bottom
  - NO save/load buttons, NO editable inputs (read-only)

- `app/templates/partials/workspace_shell.html` (MODIFIED, +9/-0) — Overview tab wiring
  - Single `{% include "partials/scenario_matrix.html" %}` line inside `#panel-overview`
  - Placed after the existing governance cards, before the closing `</div>` of the Overview panel

- `static/styles.css` (MODIFIED, +125/-0) — Phase M1 CSS block
  - `.scenario-matrix-card`, `.scenario-matrix-table`, `.scenario-matrix-legend`
  - `.matrix-cell-base` (light accent background + 2px accent border on left/right)
  - `.matrix-cell-inherit` (muted + italic)
  - `.matrix-cell-future` (muted)
  - `.badge-base` (soft green), `.badge-inherit` (soft indigo), `.badge-future` (soft gray)

### Tests (1)

- `tests/test_phase_m1_scenario_matrix.py` (NEW, +528/-0)
  - 9 test classes
  - 30+ tests covering column / row registries, cell rendering, `build_matrix_rows`, Jinja partial, workspace_shell wiring, CSS, no-persistence / no-CRUD invariants, phase invariants, file-scope

### Docs (2)

- `docs/phase_m1_scenario_matrix_prototype.md` (NEW, +225/-0) — governance doc
- `reports/phase_m1_scenario_matrix_prototype.md` (this file)

## Pre-merge audit (planned, all pinned by tests)

### What changed in production code

The diff is confined to:

- The new helper module `app/ui/scenario_matrix.py` (column / row registries, cell renderer, no I/O, no persistence)
- The new Jinja partial `app/templates/partials/scenario_matrix.html` (4-column matrix, 2 sections, em-dash placeholders)
- The Overview tab wiring in `app/templates/partials/workspace_shell.html` (single `{% include %}` line)
- The Phase M1 CSS block in `static/styles.css` (no existing rule touched)

No runtime path changes. No formula changes. No model changes. No factory changes. No persistence changes.

### What did NOT change (forbidden paths, pinned by tests)

- `main_web.py` — UNCHANGED
- `main_api.py` — UNCHANGED
- `app/project_factories.py` — UNCHANGED
- `app/waterfall_runner.py` — UNCHANGED
- `app/waterfall_core.py` — UNCHANGED
- `app/services/` — UNCHANGED
- `app/persistence/` — UNCHANGED
- `static/app.js` — UNCHANGED
- `app/input_adapter.py` / `app/input_schema.py` — UNCHANGED
- `app/persistence/` — UNCHANGED

### Honest copy verification

- The card header carries `M1 PROTOTYPE` so the read-only nature is obvious.
- The inheritance note explicitly says "UI prototype only" and "no scenario overrides are stored".
- The legend at the bottom calls out each placeholder type: Base (live), Downside/Upside (inherits Base, no storage), Custom (future override, M2).
- The Custom column renders the em-dash, not a misleading "0" or "—", to make the absence obvious.

### Inheritance / override visibility

- Downside and Upside columns render the literal text `inherits Base` in every cell.
- The Custom column renders the em-dash (`—`) in every cell.
- A pilot user cannot mistake any non-Base cell for a live value.

## Test counts (planned, M1)

- **30+ / 30+ M1 tests PASS**
- All S1, S2, S3, P1-A, P1-B tests continue to PASS (M1 only adds files; does not modify any existing production file beyond `workspace_shell.html` and `static/styles.css`, which the existing tests do not check byte-for-byte for these specific changes)
- **21 / 21** Phase 51F parity guardrails PASS (no model change)
- **132+ / 132+** factory / TUHO / Oborovo tests PASS (no factory change)

## Hard no-go (preserved, all pinned by tests)

- No financial formula / debt / tax / depreciation / IDC changes
- No model / factory / frozen-schedule changes
- No construction / C10 / R-PAR changes
- No `manual_gearing` debt sizing method
- No `min(gearing cap, sculpt)` blend
- No senior IDC
- No persistence schema migration
- No R99 / R102 / G20 promotion
- No `static/app.js` changes
- No `main_web.py` / `main_api.py` changes
- No Tailwind / Alpine / React / Vue / Svelte
- No JS calc
- No scenario persistence (no save/load)
- No scenario CRUD (no routes / no service methods)
- No scenario calculation (no new resolver path)
- `use_construction_schedule_engine` remains False
- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` preserved

## Pre-existing infra rot (NOT M1 regressions)

Same list as S1 / S2 / S3:

- `tests/test_phase24g3_capex_sheet_readability.py` — f-string + backslash SyntaxError
- `tests/test_phase9_tuho_full_semester_horizontal_parity_workbook.py::test_no_runtime_files_changed` — pre-S1 allowed-file-list
- `tests/test_senior_dscr_sculpting_basis_bridge.py` / `tests/test_senior_rate_schedule_project_opt_in.py` — numeric drift pre-existing
- `tests/test_phase23d_prep_tuho_fixture_backed_frozen_senior_ds.py::test_oborovo_frozen_fixture_still_unavailable_and_off` — Oborovo has `use_frozen_excel_senior_debt_schedule=True` (parity evolution)
- `tests/test_oborovo_parity.py::TestBaselineInputs::test_shl_amount` / `TestBaselineFinancing::test_total_equity_shl` — pre-existing numeric drift
- `tests/test_auth_lite.py` / `tests/test_ui2_6_run_source_indicator.py` — collection error, missing `itsdangerous` / `fastapi`

## Roadmap (post-M1)

1. **M1** (this PR) — Read-Only Scenario Matrix Prototype
2. **M2** — Actual scenario overrides (persistence + calculation)
   - New `capex_scenario_overrides` table (or similar)
   - New `ScenarioOverride` Pydantic model
   - New service methods: `add_override`, `update_override`, `delete_override`, `list_overrides`
   - New route endpoints for save/load/delete
   - New runtime resolution path: `_apply_scenario_overrides`
   - Multi-scenario comparison (Base vs. Downside vs. Upside live values)
   - This is the **M2** work and is intentionally deferred from M1.
3. Future: scenario matrix as a primary workspace affordance, not just an Overview card.

`manual_gearing` is **not** on this roadmap. The S3 sculpt + label approach remains ground-truth.

DO NOT START: C10, construction runtime promotion, R-PAR, debt formula changes, tax, IDC, senior IDC, depreciation, schema migration, manual_gearing, Tailwind/Alpine, factory path changes, R99/R102/G20 promotion.

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do NOT merge. Awaiting user review and explicit go-ahead.
