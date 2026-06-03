# Phase 54A — Frontend Inventory and UI Architecture Baseline

## Context

Phase 54A is the first of 5 UI-1 docs/spec phases. This phase
creates a verified inventory of the current frontend stack and UI
surface. **No runtime code changes. Docs/report/test only.**

## Current Main SHA

`ab33cbb61bc685311e2c18b57f20ef3f01becfce` (post-53I-4)

## Frontend Stack Inventory

### Languages and frameworks

| Item | Status | Location |
|---|---|---|
| Jinja templates | ✓ Active (47 templates) | `app/templates/` |
| HTMX | ✓ Active (vendor copy, 6 templates use `hx-*` attrs) | `static/vendor/htmx.min.js` |
| Custom CSS | ✓ Active (1 file, 4354 lines) | `static/styles.css` |
| Vanilla JS | ✓ Active (1 file, 412 lines) | `static/app.js` |
| Alpine.js | ✗ Not present | n/a |
| Tailwind | ✗ Not present | n/a |
| React | ✗ Not present | n/a |
| Vue | ✗ Not present | n/a |
| Svelte | ✗ Not present | n/a |
| Bundler (Vite/Webpack) | ✗ Not present | n/a |
| Node.js | ✗ Not present | n/a |
| npm/package.json | ✗ Not present | n/a |

**Stack conclusion:** Pure server-rendered Jinja + HTMX + custom
CSS + one small vanilla JS file. No build step. No dependencies.

## Template Inventory

Total: **44 templates** (3 base/index + 41 partials) across **7889 total LOC**.

### Base templates (2)

- `app/templates/base.html` — base layout for authenticated pages
- `app/templates/login.html` — login page

### Index

- `app/templates/index.html` — single-page workspace shell that
  includes many partials (the main analyst surface)

### Partial categories

#### Sheet partials (13)

Used in the Excel-like financial model workspace:

- `sheet_capex.html`, `sheet_capex_detail.html`
- `sheet_opex.html`, `sheet_opex_detail.html`
- `sheet_revenue.html`
- `sheet_production.html`
- `sheet_construction.html`
- `sheet_idc.html`
- `sheet_senior_debt.html`
- `sheet_shl.html`
- `sheet_tax.html`
- `sheet_financials.html`
- `sheet_inputs.html`

#### Workspace / shell partials (6)

- `workspace_shell.html` — main workspace container
- `workspace_tabs.html` — tab navigation
- `scenario_workspace.html` — scenario-specific shell
- `shared_runtime_block.html` — runtime impact + status
- `kpis.html` — KPI summary cards
- `errors.html` — error display partial

#### Scenario partials (6)

- `scenario_tab.html` — main scenario tab
- `scenario_compare.html` — scenario comparison
- `scenario_load_result.html` — load result feedback
- `scenario_version_history.html` — version history list
- `compare_service` partial
- `comparison.html` — comparison view

#### Run / runtime partials (3)

- `runtime_summary.html`
- `run_history.html`
- `save_result.html`

#### Project / form partials (5)

- `project_browser.html`
- `project_selector.html`
- `new_project_form.html`
- `new_project_result.html`
- `inputs_section.html`

#### Audit / export partials (3)

- `audit_reconciliation_tab.html`
- `export_registry.html`
- `export_audit` partial

#### Pilot / notice partials (3)

- `pilot_help_onboarding.html`
- `pilot_limitations_notice.html`
- `pilot_workflow_guide.html`

#### Error / empty state partials (2)

- `error_banner.html`
- `empty_states_notice.html`

## Static Asset Inventory

| File | Lines | Bytes | Role |
|---|---:|---:|---|
| `static/styles.css` | 4,354 | ~ | All styling (custom CSS, no framework) |
| `static/app.js` | 412 | ~ | Tab switching, draft persistence, button states |
| `static/vendor/htmx.min.js` | n/a | 48,101 | HTMX 1.x vendor copy |

### `static/styles.css` theme summary

Top of file declares the **dark navy sidebar / institutional palette** theme:

- Sidebar colors: `--sidebar-bg: #0f1b2d`, `--sidebar-active: #1a56db`
- Content surface: `--bg: #f0f4f8`, `--surface: #ffffff`
- Primary: `--primary: #1a56db`
- Status/badge classes: `badge-pass`, `badge-warn`, `badge-fail` (visible in templates)

### `static/app.js` function summary

- `showNewProjectPanel()` / `closeNewProjectPanel()` — panel switching
- `duplicateCurrentScenario()` — calls HTMX `ajax()`
- `setButtonDisabledState()` — disabled button management
- `switchTab(tab)` — tab switching
- `activeTab` (global) — current tab state
- `draftPersistTimer` — draft auto-save timer

## HTMX Usage Summary

HTMX is included as a vendor file and used in 6 templates:

- `new_project_form.html`
- `project_selector.html`
- `run_history.html`
- `scenario_tab.html`
- `workspace_shell.html`

(Note: `grep -c "hx-"` on `index.html` returned 0, but partials use
`hx-*` attributes via the includes.)

HTMX is wired to backend services via:
- Form submission (`hx-post`, `hx-target`)
- Tab/content swaps (`hx-get`, `hx-trigger`)
- HTMX-driven partials (e.g., `run_history`, `project_selector`)

## Runtime Impact Taxonomy Status

The 4-state canonical taxonomy **already exists** in code:

**File:** `app/runtime_impact_taxonomy.py`

| State | Meaning |
|---|---|
| **Drives model** | Input is runtime-effective, directly affects calculation outputs |
| **Display only** | Field is visible/reference/displayed but does not affect runtime |
| **Pending** | Field/section is planned or captured but not yet wired |
| **Needs review** | Field has ambiguous mapping, validation concern, requires review |

### Where Runtime Impact appears in UI today

- `app/templates/partials/sheet_capex_detail.html` — runtime impact marker on line items
- Other sheets show line items with data attributes that reference the taxonomy

### Sub-reasons (for tooltip / helper text)

The taxonomy defines 11 sub-reasons for tooltip/helper use:

- Timing only
- Reference only
- Pending treatment
- Pending runtime source
- Not comparable
- Deferred
- Not applicable
- Fixture-backed
- Frozen schedule
- Source locked
- Validation warning
- Excel parity known gap

**Conclusion:** Runtime Impact taxonomy is **already implemented at
the data layer**. UI display is **inconsistent across sheets** —
some show chips, some show plain text. This is one of the primary
UI-1/UI-2 targets.

## Current UI Duplication Hotspots

| Hotspot | Where | Notes |
|---|---|---|
| **Sheet grids** | 13 `sheet_*.html` partials | Each sheet re-implements row markup, totals, status cells. No shared `line_item_grid` macro. |
| **KPI cards** | `kpis.html` + ad-hoc KPI blocks in sheets | KPI card markup duplicated per page |
| **Banners** | `error_banner.html`, `pilot_*` partials, `audit_reconciliation_tab.html` | Banner styles vary; no shared banner class with tone variants |
| **Badges** | `audit_reconciliation_tab.html` uses `badge-pass`/`badge-warn` | Inconsistent: some pages use class, some inline color |
| **Chips (Runtime Impact)** | `sheet_capex_detail.html` shows them; other sheets inconsistent | Spec exists in `runtime_impact_taxonomy.py` but UI display is fragmented |
| **Forms** | `new_project_form.html`, `inputs_section.html`, project settings | Form markup duplicated; no shared input macro |
| **Tabs** | `workspace_tabs.html` + `scenario_tab.html` + `app.js::switchTab` | Tab logic split between JS and partials |

## Frontend Risk List

| Risk | Severity | Notes |
|---|---|---|
| **No design tokens (CSS vars) for runtime impact** | medium | Tokens exist for primary/sidebar, not for taxonomy colors |
| **No shared LineItemGrid macro** | high | 13 sheets re-implement the same grid; hard to keep consistent |
| **Inconsistent badge/chip styling** | medium | Specs exist in CSS but ad-hoc usage in templates |
| **Single 4354-line styles.css** | low | No build step needed yet, but no module split |
| **No accessibility audit** | medium | Tabs use `aria-disabled`; no full audit |
| **No dark mode** | low | Light mode only (acceptable for v1) |
| **No client-side state machine** | low | OK — server is source of truth (per Phase 51 constraints) |
| **No client-side finance calculations** | none | ✓ Good — backend is source of truth |
| **Hard-coded brand string "Finco One" in CSS comment** | low | Should be "FincoGPT" or be neutralized before public pilot |

## Recommendation for 54B

Proceed to **Phase 54B — Information Architecture and Workflow Map**:

1. Define the 11-section IA: Dashboard / Projects / Inputs / Financing / Scenarios / Compare / Audit / Reports / Data Room / Settings
2. Map the 10 core analyst workflows to existing template/service dependencies
3. Identify which sections can be implemented first (low-risk UI-2 work)
4. Identify the no-go copy risks per workflow

UI-1 architecture stack is well-positioned. Backend is stable
(post-53I). Frontend is small enough to refactor safely.

## Hard Gates (54A)

- ✓ Only docs/report/test files added (no templates, no CSS/JS, no services, no persistence)
- ✓ Branch is `phase54a-frontend-inventory-ui-baseline` based on `ab33cbb61bc685311e2c18b57f20ef3f01becfce`
- ✓ Inventory verifies the post-53I state
- ✓ Runtime Impact taxonomy location and 4 states documented
- ✓ HTMX / Alpine / Tailwind / React / Vue / Svelte / bundler presence verified (HTMX yes, all others no)
- ✓ rc1 (b425a07) untouched
- ✓ No-go claim list preserved

## Files Created in 54A

- `docs/phase54a_frontend_inventory_ui_baseline.md` (this file)
- `reports/phase54a_frontend_inventory_ui_baseline.json`
- `tests/test_phase54a_frontend_inventory_ui_baseline.py` (optional guardrail)
