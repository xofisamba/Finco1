# Phase 9.5 — Run Model Active Project Binding

## Overview

When a user selects TUHO or Oborovo in the project sidebar and clicks "Run Model", the UI now clearly executes the selected project and displays live runtime summary data.

**PR:** Phase 9.5 — Run Model Active Project Binding

## What Was Built

### 1. Active Project Run Binding

**File:** `app/main_web.py`

The `POST /run` route now checks for an `active_project` hidden form field:

```
If active_project = "tuho"  →  run_project("TUHO", "Base")
If active_project = "oborovo"  →  run_project("Oborovo", "Base")
Otherwise → standard form-based run
```

The hidden input is set by JavaScript `setActiveProject()` called from the project selector links.

### 2. TUHO/Oborovo Factory Bindings

**File:** `app/ui_runner.py`

- `FACTORY_MAP` updated to include `"TUHO": create_default_tuho_wind1` and `"Oborovo": create_default_oborovo`
- `PROJECT_CONFIGS` updated with full `"TUHO"` and `"Oborovo"` entries

This allows `run_demo_project("TUHO", "Base")` and `run_demo_project("Oborovo", "Base")` to work correctly.

### 3. Runtime Summary Builder

**File:** `app/ui/runtime_summary.py`

`build_runtime_summary(result, project_id, project_name)` → `RuntimeSummary` frozen dataclass

Fields sourced from actual runtime execution (no fabrications):
- `project_irr`, `equity_irr`, `avg_dscr`, `min_dscr`
- `total_revenue_keur`, `total_ebitda_keur`, `total_opex_keur`, `total_distributions_keur`
- `senior_debt_keur`, `shl_opening_keur` (from factory defaults)
- `ran_at` timestamp, `status`

### 4. KPI Enrichment in run_project

**File:** `app/api/project_runner.py`

Added to kpis dict:
- `total_opex_keur` (previously missing)
- `total_distributions_keur` (previously missing)

### 5. Live Runtime Summary Partial

**File:** `app/templates/partials/runtime_summary.html`

HTMX-swap target for `#model-output-area`. Renders:
- "Last run: {project_name}" banner with timestamp + status badge
- 8 KPI cards with live runtime values
- "Runtime summary" badge + notice distinguishing live from preview
- Warning/error messages

### 6. Project Selector JS (setActiveProject)

**File:** `app/templates/partials/project_selector.html`

`setActiveProject(projectId)` sets hidden input + sessionStorage (for browser back/forward).

### 7. HTMX Output Target in Overview

**File:** `app/templates/partials/workspace_shell.html`

Added `<div id="model-output-area"></div>` inside the Overview tab — this is the HTMX swap target where runtime summary replaces the static "—" KPI placeholders after a run.

## Runtime Values (TUHO vs Oborovo)

| Metric | TUHO | Oborovo |
|---|---|---|
| Project IRR | 9.41% | 7.98% |
| Equity IRR | 11.15% | 9.17% |
| Avg DSCR | 1.554x | 1.229x |
| Total Revenue | 423,844 kEUR | 238,735 kEUR |
| Total OPEX | 85,408 kEUR | 51,221 kEUR |
| Total Distributions | 173,572 kEUR | 104,699 kEUR |

## Files Changed

| File | Change |
|---|---|
| `app/main_web.py` | `POST /run` — active_project branch, runtime_summary template |
| `app/ui_runner.py` | FACTORY_MAP + PROJECT_CONFIGS for TUHO/Oborovo |
| `app/api/project_runner.py` | Added total_opex_keur + total_distributions_keur to kpis |
| `app/ui/runtime_summary.py` | New — RuntimeSummary dataclass + builder |
| `app/templates/partials/runtime_summary.html` | New — HTMX runtime summary partial |
| `app/templates/partials/project_selector.html` | Added setActiveProject JS |
| `app/templates/partials/workspace_shell.html` | Added `#model-output-area` div |
| `app/templates/index.html` | Added `active_project` hidden input |
| `tests/test_phase9_5_run_model_active_project_binding.py` | New — 30 tests |
| `docs/phase9_5_run_model_active_project_binding.md` | This doc |

## What Was NOT Changed (Constraints)

- No waterfall formula changes
- No SHL mechanics changes
- No TaxBridge changes
- No DistributionAccount changes
- No SeniorDebtSizing changes
- No R99/R102 promotion
- No G20 approval
- No persistence backend
- No database changes

## Limitations

1. **Balance-sheet anchors** (senior_debt_keur, shl_opening_keur) — sourced from factory defaults since waterfall table rows use period-column structure without label keys
2. **No scenario support for TUHO/Oborovo** — only "Base" scenario
3. **Session-only run history** — no persistence; refreshing the page clears last run
4. **Output tabs** (P&L, Cash Flow, Balance Sheet) — still show preview content; not yet bound to runtime outputs

## Future Work (Out of Scope for This PR)

- Full output tab binding to runtime results
- Persistence layer for run history
- Scenario management for named projects
- Balance-sheet anchor extraction from waterfall table (requires table structure change)
- Real-time reactive recalculation on input changes