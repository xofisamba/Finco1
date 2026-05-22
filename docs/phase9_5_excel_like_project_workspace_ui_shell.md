# Phase 9.5 — Excel-like Project Workspace UI Shell

**Date:** 2026-05-22
**Branch:** `phase9_5-excel-like-project-workspace-ui-shell`
**Status:** Complete

---

## Overview

Phase 9.5 replaces the navigation-sidebar-based UI shell with an Excel-like project workspace UI. The new UI is organized around **two axes**: a **project selector** (sidebar) and a **tab ribbon** (17 tabs across the top of the content area). This matches the mental model of a financial model workbook where each tab is a dedicated sheet.

---

## Architecture

### Layout Hierarchy

```
top-header (fixed, 56px)
  └─ workspace-tabs-bar (sticky, ~48px)
       └─ tab-ribbon (horizontal scroll, 17 tabs)
  └─ app-layout
       ├─ project-sidebar (fixed left, dark navy)
       │    ├─ Branding strip
       │    ├─ Project selector (TUHO / Oborovo cards)
       │    ├─ Actions (New / Duplicate / Run / Save / Load)
       │    ├─ Scenario selector (Base / Audit)
       │    ├─ Governance panel (G20 BLOCKED, R99 NOT APPROVED)
       │    └─ Downloads shortcuts
       ├─ sidebar-input (form, left panel — unchanged)
       └─ content (workspace shell / tab panels)
```

### Sidebar Behaviour (`.project-sidebar`)

- Fixed left panel, dark navy theme (`--sidebar-bg: #0f1b2d`)
- Top edge: immediately below header + tabs bar (`top: calc(var(--header-h) + 48px)`)
- Project cards: click to switch active project (TUHO ↔ Oborovo), JS-driven `switchProject()`
- Active card highlighted with primary-blue left border
- Scenario selector: Base/Audit dot indicators (Base is active by default)
- Governance panel: G20 BLOCKED badge + R99 NOT APPROVED badge
- Scrollable independently of main content

### Tab Ribbon Behaviour

- Sticky below header, above content
- 17 Excel-like tabs: Overview | Inputs | Construction | Production | Revenue | OPEX | CAPEX | Senior Debt | SHL | Tax | P&L | Cash Flow | Balance Sheet | Distributions | Sponsor / Equity | Audit / Parity | Downloads
- Active tab: primary-blue bottom border (2px solid)
- JS-driven `switchTab()` — toggles `.active` class on both tab buttons and panels
- Scrolls active tab into horizontal center view
- All tab panels live in `workspace_shell.html`, toggled via CSS `.tab-panel { display:none } / .tab-panel.active { display:block }`

### TUHO / Oborovo Switching

- `switchProject(projectId)` — deactivates all project cards, activates selected
- Dispatches `projectChanged` CustomEvent for future listeners (e.g. loading project-specific data)
- Active card shows filled `●` dot in primary blue
- Project metadata (name, MW, country) shown on each card

### No Runtime Changes

- **Runtime model logic is untouched**: no changes to `app/models/`, `app/core/`, `app/calculations/`, `app/domain/`
- **Persistence backend not implemented**: no database, no file-based scenario storage
- **No framework added**: pure HTML + CSS + Vanilla JS; no React, Vue, Streamlit, or HTMX patterns beyond existing usage

---

## Files Changed / Created

### New Files

| File | Purpose |
|------|---------|
| `app/templates/partials/project_selector.html` | Project card list (TUHO wind 72MW, Oborovo solar 53.63MW), JS `switchProject()` |
| `app/templates/partials/workspace_tabs.html` | 17-tab ribbon HTML + `switchTab()` JS |
| `app/templates/partials/workspace_shell.html` | All 17 tab panels; Overview = KPIs + governance cards; most tabs = placeholder panels |
| `docs/phase9_5_excel_like_project_workspace_ui_shell.md` | This architecture doc |

### Modified Files

| File | Change |
|------|--------|
| `app/templates/base.html` | Replaced `.sidebar-nav` with `.project-sidebar` (branding, project selector, actions, scenario, governance, downloads); added `{% include "partials/workspace_tabs.html" %}` before `.app-layout`; kept `sidebar-input` and `content` structure |
| `app/templates/index.html` | Replaced dashboard section with governance banner + `{% include "partials/workspace_shell.html" %}`; kept `sidebar_input` block |
| `static/styles.css` | Added CSS for `.top-tabs-bar`, `.tab-ribbon`, `.ws-tab`, `.project-sidebar`, `.ps-*` classes, `.tab-panel`, `.placeholder-panel`, `.sheet-card` |
| `static/app.js` | Added `switchTab()` and `switchProject()` JS functions; New Project / Run Model / Save / Load / Duplicate handlers |

---

## Tab Panel Contents

| Tab | Content |
|-----|---------|
| Overview | KPI grid (8 cards: IRR, DSCR, Revenue, etc.) + Governance Status card + TUHO Parity card |
| Inputs | Placeholder: sidebar form config view note |
| Construction | Placeholder: CAPEX drawdown + COD milestones |
| Production | Placeholder: P50/P90 yield |
| Revenue | Placeholder: tariff + PPA |
| OPEX | Placeholder: OPEX table |
| CAPEX | Placeholder: CAPEX table |
| Senior Debt | Placeholder: debt sculpting + DSCR profile |
| SHL | Placeholder: SHL waterfall |
| Tax | Placeholder: CIT + R35/R69 mapping note (MISSING_EVIDENCE) |
| P&L | Placeholder: income statement |
| Cash Flow | Placeholder: cash flow waterfall |
| Balance Sheet | Placeholder: balance sheet |
| Distributions | Placeholder: distribution schedule |
| Sponsor / Equity | Placeholder: equity waterfall + R99/R102 note (NOT APPROVED) |
| Audit / Parity | TUHO parity status table (PASS/WARN/MISSING), G20 BLOCKED card, R99 NOT APPROVED card, link to parity workbook |
| Downloads | Model Export, Parity Workbook, Gap Register, Source Map download items |

---

## Limitations

- **No project switching persistence**: UI switches active project visually; no data reload / route change
- **No scenario switching**: Base/Audit selector is decorative (visual only, no model re-run)
- **All placeholder tabs are static HTML**: no HTMX endpoints yet for tab content
- **Governance statuses are hardcoded**: G20 BLOCKED, R99 NOT APPROVED reflect current model state, not dynamic reads
- **New Project / Duplicate / Load**: alert placeholders only

---

## Future Integration Points

| Future Phase | Integration |
|-------------|-------------|
| Project persistence | `projectChanged` CustomEvent → load project data from backend |
| Scenario switching | `switchScenario()` → re-run model with scenario params |
| Tab content loading | Tab click → HTMX `hx-get` `/api/tabs/{tab}` → load panel content |
| Real governance reads | G20/R99 badges → `fetch('/api/governance')` → dynamic status |
| Download endpoints | `#download-parity`, `#download-gap`, `#download-source` → `/download?type=parity` etc. |

---

## Allowed File Whitelist (no-runtime test)

Only the following file prefixes may change:

```
app/templates/base.html
app/templates/index.html
app/templates/partials/
static/styles.css
static/app.js
docs/phase9_5_excel_like_project_workspace_ui_shell.md
tests/test_phase9_5_excel_like_project_workspace_ui_shell.py
```