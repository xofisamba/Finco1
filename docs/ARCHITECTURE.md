# Architecture — FincoGPT Runtime Engine

_Authored during post-RC1 restructuring. Valid as of 2026-05-06._

---

## Overview

FincoGPT is a project-finance runtime model that takes `ProjectInputs` (a dataclass-based
description of a generation asset) and returns a `ModelResult` (waterfall, returns, debt schedule).
It runs in two modes:

| Mode | Entry point | Description |
|---|---|---|
| UI | `streamlit_app.py` | Streamlit multi-tab UI with editable inputs, OPEX matrix, scenario selector |
| Headless | `app/ui_runner.py → run_demo_project()` | Core engine without UI — used in tests and batch jobs |

The core runtime (`domain/`) is project-type agnostic. Application-layer code (`app/`) handles
UI concerns, scenario application, OPEX/CAPEX line-item engines, and Excel export.

---

## Core Data Flow

```
ProjectInputs (dataclass tree)
    │
    ▼
┌─────────────────────────────┐
│   app.ui_runner.run_demo_   │  ← dispatches based on project_type
│   project()                │
└─────────────┬───────────────┘
              ▼
┌─────────────────────────────────────────────┐
│ domain.portfolio_runner / industry_engine  │  ← per-asset model
└─────────────┬───────────────────────────────┘
              ▼
         ModelResult  (result, portfolio_result, validation_issues)
```

---

## Domain Layer (`domain/`)

| Module | Role |
|---|---|
| `inputs.py` | `ProjectInputs`, `ProjectInfo`, `TechnicalParams`, `CapexItem`, `OpexItem`, `RevenueParams`, `FinancingParams`, `TaxParams` — all frozen dataclasses |
| `model_state.py` | `ModelState` — full period-indexed model state (PL, cash, balance sheet) |
| `technology.py` | Technology-specific logic (solar, wind, BESS) |
| `revenue/` | Revenue calculation per technology |
| `opex/` | OPEX per period |
| `capex/` | CAPEX schedule construction |
| `debt/` | Debt sizing and repayment waterfall |
| `waterfall/` | Full financial waterfall (PL → CF → DSCR) |
| `returns/` | IRR / equity return calculations |
| `financing/` | Financing structure helpers |
| `analytics/` | Post-run analytics and ratio calculations |
| `presets.py` | `PROJECT_PRESETS` — hardcoded per-technology defaults |

---

## Application Layer (`app/`)

### `scenarios.py` — Legacy Scenario Engine

Pure-function scenario engine (no Streamlit imports). Applies Base / Downside / Upside
multipliers to the input dataclass tree.

**SCENARIO_RULES multipliers:**
| Scenario | P50 | CapEx | OpEx | Degradation | Tariff |
|---|---|---|---|---|---|
| Base | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 |
| Downside | 0.90 | 1.05 | 1.10 | 1.15 | 0.95 |
| Upside | 1.05 | 0.97 | 0.95 | 0.90 | 1.03 |

**Used by:** `streamlit_app.py` scenario selector, `run_demo_project()`.

### `scenario_manager.py` — Scenario Architecture (NEW, post-RC1)

Clean scenario registry separate from domain. Defines `Scenario` dataclass and
`ScenarioManager` class.

**Scenario dataclass (frozen):**
- `name`, `description`, `is_base`
- `revenue_multiplier`, `opex_multiplier`, `capex_multiplier`
- `debt_sculpting_override: float | None`
- `annual_generation_hours: float | None`

**ScenarioManager:**
- Per-project-type scenario registry (Solar / Wind / BESS fallback)
- `get_scenario(name) → Scenario`
- `apply_overrides(project_inputs, scenario_name) → ProjectInputs` (deep copy)
- Only numeric fields are modified; domain object structure is preserved
- Solar/Wind: Base=1.0x, Downside=0.85x rev/1.10x opex/1.05x capex, Upside=1.15x rev/0.95x opex/0.97x capex

**Backward compatible** with `scenarios.py` — does not replace it.

**Migration status (as of 2026-05-06):** `ScenarioManager` is a **foundation module**. The current runtime still uses `app.scenarios.apply_scenario()` for scenario application in `run_demo_project()`. Full migration to `ScenarioManager` is future work. The `ScenarioManager` API is stable and tested; integration into the run path is a later step.

### `opex_engine.py` — OPEX Line-Item Engine

Provides a granular line-item layer on top of `domain.inputs.OpexItem`.

**Key classes:**
- `OpexLineItem` — frozen dataclass with `name`, `category`, `base_year_amount_keur`,
  `inflation_rate`, `calculation_mode`, `annual_values_keur`, `manual_overrides_keur`,
  `is_hardcoded`, `override_note`, `source`
- `OpexScheduleEntry` — single period's computed OPEX value
- `generate_opex_schedule(line_items, horizon_years) → OpexSchedule`

**Calculation modes:**
- `INFLATED_FROM_BASE` — compound inflation on base-year amount
- `MANUAL_SCHEDULE` — explicit per-year values
- `MIXED` — some years formula, others manual override

**Source provenance:** `FORMULA | MANUAL | HARDCODED`

**Integration point:** `streamlit_app.py` OPEX tab (Advanced mode) passes
`advanced_opex_line_items` to `run_demo_project()`.

### `capex_engine.py` — CAPEX Line-Item Engine

Mirrors the OPEX line-item philosophy for CAPEX.

**Key classes:**
- `CapexLineItem` — frozen dataclass with `code`, `name`, `group`, `amount_keur`,
  `asset_class`, `timing_profile`, `timing_fractions`, `is_manual`, `notes`
- `CapexScheduleEntry` — single period's CAPEX draw for one line item
- `CapexSchedule` — full schedule across all items and periods
- `generate_capex_schedule(items, tenor_periods) → CapexSchedule`

**Timing profiles:** `UPFRONT | ELEVATED | ANNUITY | CUSTOM`

### `capex_overrides.py` — CAPEX Scaling Helper

Utility for scaling CapEx items proportionally while preserving structure.

### `project_factories.py` — Project Input Factories

Creates default `ProjectInputs` for named project types:
- `create_default_solar_project()` — generic 50 MWp solar PV
- `create_default_wind_project()` — generic 50 MW wind farm
- `create_default_bess_project()` — generic 50 MW / 100 MWh BESS
- `create_default_oborovo()` — Oborovo (Croatia, calibrated to Excel)
- `create_default_tuho()` — TUHO ( Hungary, calibrated to Excel)

### `ui_runner.py` — Core Dispatcher

`run_demo_project(project_type, scenario, project_inputs_override, advanced_opex_line_items) → DemoResult`

Handles:
1. Scenario application via `app/scenarios.apply_scenario()`
2. Technology-specific model dispatch
3. Result wrapping into `DemoResult`

### `input_forms.py` — Editable Project Input Form

Streamlit form for editing Solar/Wind `ProjectInputs` in the UI.

### `output_tables.py` — Result Tables

Renders model outputs as Streamlit tables and pandas DataFrames.

### `waterfall_core.py` / `waterfall_runner.py` — Waterfall Engine

Core waterfall computation (`waterfall_core`) and Streamlit rendering (`waterfall_runner`).

### `excel_export.py` — Excel Export

Builds a ZIP archive containing formatted Excel output matching the domain model.

---

## UI (`app/ui/`)

- `pages.py` — Page renderers (`render_dashboard`, `render_inputs`, `render_capex`,
  `render_revenue`, `render_debt`, `render_waterfall`, `render_returns`,
  `render_validation_panel`, `render_portfolio`)
- `render_capex_matrix()` — CAPEX matrix editor

---

## Streamlit App (`streamlit_app.py`)

**Session state keys:**
| Key | Type | Purpose |
|---|---|---|
| `demo_result` | `DemoResult \| None` | Cached model result |
| `last_project_type` | `str \| None` | Prev selected project type for rerun detection |
| `last_scenario` | `str \| None` | Prev selected scenario |
| `editable_inputs` | `ProjectInputs \| None` | Edited project inputs |
| `use_editable_inputs` | `bool` | Whether edits are active |
| `_opex_mode` | `str` | `"Simple"` or `"Advanced"` OPEX mode |
| `_last_opex_sig` | `tuple` | OPEX state signature for rerun detection |
| `_opex_mode_radio` | `str` | OPEX mode radio widget key |
| `last_advanced_opex_signature` | `str` | Advanced OPEX diff signature |
| `advanced_opex_line_items` | `tuple[OpexLineItem]` | Advanced OPEX line items |
| `_advanced_opex_project_type` | `str` | Project type when line items last built |
| `_inputs_edit_toggle` | `bool` | Edit inputs checkbox key |
| `_opex_matrix_editor` | `pd.DataFrame` | OPEX matrix data editor key |
| `demo_result` | `DemoResult \| None` | Cached model result |
| `last_project_type` | `str \| None` | Prev selected project type for rerun detection |
| `last_scenario` | `str \| None` | Prev selected scenario |
| `editable_inputs` | `ProjectInputs \| None` | Edited project inputs |
| `use_editable_inputs` | `bool` | Whether edits are active |
| `_opex_mode` | `str` | `"Simple"` or `"Advanced"` OPEX mode |
| `_last_opex_sig` | `tuple` | OPEX state signature for rerun detection |
| `_opex_mode_radio` | `str` | OPEX mode radio widget key |
| `last_advanced_opex_signature` | `str` | Advanced OPEX diff signature |
| `advanced_opex_line_items` | `tuple[OpexLineItem]` | Advanced OPEX line items |
| `_advanced_opex_project_type` | `str` | Project type when line items last built |
| `_inputs_edit_toggle` | `bool` | Edit inputs checkbox key |
| `_opex_matrix_editor` | `pd.DataFrame` | OPEX matrix data editor key |

**Advanced OPEX flow:**
1. User selects "Advanced" OPEX mode in tab
2. `build_opex_line_items_from_defaults()` creates line items on first render
3. `data_editor` renders matrix with Y1…Yn columns
4. Per-cell diffing detects manual overrides → `manual_overrides_keur` per `OpexLineItem`
5. Shadow styled preview highlights amber override cells
6. `last_advanced_opex_signature` updated on every edit → triggers rerun in run-condition block
7. `run_demo_project()` receives `advanced_opex_line_items` and uses them instead of
   `project_inputs.opex`

---

## Testing (`tests/`)

- `test_scenarios.py` — Legacy scenario engine tests
- `test_scenario_manager.py` — New scenario manager tests (30 tests)
- `test_opex_engine.py` — OPEX line-item engine tests
- `test_capex_engine.py` — CAPEX line-item engine tests
- `test_generic_solar_wind_runtime.py` — Full model integration tests
- `test_generic_full_flow_integration.py` — Portfolio-level integration tests

---

## Known Limitations

1. **BESS / Hybrid**: revenue-only results shown in UI; full waterfall in progress.
2. **Portfolio IRR**: placeholder (marked 🔬 Experimental in UI); do not use for investment decisions.
3. **Sponsor IRR**: not yet implemented; Excel export shows "placeholder" label.
4. **FX conversion**: not implemented; all amounts assumed in single currency.
5. **Debt sculpting override** (via `Scenario.debt_sculpting_override`) is wired in
   `ScenarioManager` but not yet connected to the scenario selector UI.
6. **`scenario_manager.apply_overrides()`** is wired into `run_demo_project()` —
   `ScenarioManager` is the active runtime scenario engine for Solar/Wind (2026-05-06).
   Legacy `app/scenarios.apply_scenario()` is preserved for backward compatibility.
   Multiplier reconciliation complete: both engines use same values.
7. **OPEX matrix** amber-highlight override preview uses a shadow DataFrame;
   the styling function may have edge cases with row index alignment.

---

## Roadmap Status

See `docs/phase3_roadmap.md` for the full RC2 → RC3 roadmap. Key items:

- [x] OPEX line-item engine (`app/opex_engine.py`) — done RC1
- [x] CAPEX line-item engine (`app/capex_engine.py`) — done RC1
- [x] Scenario architecture foundation (`app/scenario_manager.py`) — done post-RC1
- [x] Scenario manager wired into `run_demo_project()` — done 2026-05-06
- [x] Advanced OPEX → `run_demo_project()` bridge — done RC1
- [x] Advanced CAPEX → `run_demo_project()` bridge — done 2026-05-06
- [ ] BESS full waterfall integration — in progress
- [ ] Sponsor IRR — not started
