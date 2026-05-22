# Phase 9.5 — Excel-Like Project Workspace UI Design
**Branch:** `phase9_5-excel-like-project-workspace-ui-design`
**Date:** 2026-05-22
**Status:** Design Specification Only — NO implementation

---

## Executive Summary

The current sidebar groups model sections (Inputs, Financing, Outputs, etc.) which makes navigation feel crowded and unlike a professional project finance workflow. This design proposes a **two-tier navigation model** inspired by Excel:

- **Left sidebar** → project workspace (project selector, scenarios, governance status)
- **Top tabs/ribbon** → active project model sheets (Inputs, Production, CAPEX, etc.)
- **Main workspace** → sheet-like content with horizontal period columns

This is a **design-only specification**. No runtime, model formula, or persistence changes.

---

## 1. Current UI Problems

| Problem | Description |
|---------|-------------|
| Crowded sidebar | All model sections (Inputs, Financing, Outputs, Downloads, Governance) packed into one sidebar |
| No project concept | UI has no concept of "project" vs "model sheet" — everything is flat |
| Navigation feels like website | Sidebar nav groups are website-style, not Excel-model-sheet-style |
| No active project indicator | User cannot easily tell which project (TUHO/Oborovo) is active |
| Scenario switching unclear | No visual affordance for duplicate/switch scenario |
| Sheet content mixed with nav | `<details>` accordion panels mix navigation with content |

---

## 2. Proposed Sidebar Architecture (Project Workspace)

The left sidebar (dark navy, 260px) becomes the **project workspace panel**:

```
┌─────────────────────────────────────────────┐
│ [F] Finco One                               │  ← brand
├─────────────────────────────────────────────┤
│ Project: [TUHO ▼]                           │  ← project selector dropdown
├─────────────────────────────────────────────┤
│ Scenario: [Base ▼]                          │  ← scenario selector
│ [Duplicate Scenario]                        │
├─────────────────────────────────────────────┤
│ Runs / History                              │  ← accordion: past runs
│ Portfolio View                              │  ← future: multi-project view
├─────────────────────────────────────────────┤
│ [▶ Run Model]                               │  ← primary action
│ [⚡ Compare]  [📥 Export]                    │
├─────────────────────────────────────────────┤
│ Downloads                                    │
│  · Model Export (.xlsx)                     │
│  · Parity Workbook                          │
│  · Gap Register                             │
├─────────────────────────────────────────────┤
│ 🛡️ Governance                               │  ← collapsible status panel
│  G20: BLOCKED (0.29pp)                      │
│  R99/R102: NOT APPROVED                     │
│  CO2: Enabled, €4.19/MWh                    │
└─────────────────────────────────────────────┘
```

**Sidebar contents:**
- Finco One brand header
- Project selector (TUHO / Oborovo / future projects) — dropdown
- Scenario selector (Base / variants) — dropdown
- Duplicate Scenario button
- Run History accordion
- Portfolio View (future)
- Primary action buttons: Run Model, Compare, Export
- Downloads section
- Governance status panel (G20 BLOCKED, R99/R102 NOT APPROVED)

**Removed from sidebar:**
- All model section links (Overview, Inputs, Financing, Outputs) — these move to top tabs

---

## 3. Proposed Top-Tab/Ribbon Architecture

A horizontal **tab bar** sits below the top header, spanning the full width above the main workspace:

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Finco One │ INTERNAL DEMO │ v1.7 Pilot │                    │ Sign out │
├────────────────────────────────────────────────────────────────────────────┤
│ [Overview] [Inputs] [Construction] [Production] [Revenue] [OPEX] [CAPEX]   │
│ [Senior Debt] [SHL] [Tax] [P&L] [Cash Flow] [Balance Sheet] [Dist.] [Eq]  │
│ [Sponsor /│ [Audit] [Downloads]                                       │
├────────────────────────────────────────────────────────────────────────────┤
│                             MAIN WORKSPACE                               │
```

**Design principles:**
- Tabs are **horizontally scrollable** if overflow (like Excel sheet tabs)
- Active tab: highlighted with primary color border-bottom
- Inactive tabs: muted text
- Click tab → loads corresponding sheet in main workspace
- Each tab represents ONE model sheet

**Tab list:**
| Tab | Purpose |
|-----|---------|
| Overview | KPI dashboard, G20 gate, governance summary |
| Inputs | Master inputs form (all input groups in one sheet) |
| Construction | Construction period schedule |
| Production | P50 hours, capacity factor |
| Revenue | Tariff, PPA term |
| OPEX | Y1 OPEX |
| CAPEX | Total CAPEX |
| Senior Debt | Gearing, DSCR, interest rate, tenor |
| SHL | SubordinatedHybridLoan schedule |
| Tax | Tax assumptions |
| P&L | Profit & Loss statement |
| Cash Flow | Cash flow statement |
| Balance Sheet | Balance sheet |
| Distributions | Distribution schedule |
| Sponsor / Equity | Sponsor equity, IRR, MOIC |
| Audit / Parity | Audit parity tables |
| Downloads | Download links |

---

## 4. Proposed Main Workspace Architecture

The main area shows the **active sheet** — a compact, Excel-like data table:

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Sheet: OPEX                                       [periods: 360 months]   │
├────────────────────────────────────────────────────────────────────────────┤
│                    Y1      Y2      Y3      Y4      Y5  ...  Y30           │
│ ─────────────────────────────────────────────────────────────────────────── │
│ Personnel          XXX     XXX     XXX     XXX     XXX  ...   XXX          │
│ O&M                XXX     XXX     XXX     XXX     XXX  ...   XXX          │
│ Insurance          XXX     XXX     XXX     XXX     XXX  ...   XXX          │
│ Land lease         XXX     XXX     XXX     XXX     XXX  ...   XXX          │
│ Other             XXX     XXX     XXX     XXX     XXX  ...   XXX          │
│ ─────────────────────────────────────────────────────────────────────────── │
│ Total OPEX         XXX     XXX     XXX     XXX     XXX  ...   XXX          │
└────────────────────────────────────────────────────────────────────────────┘
```

**Visual principles:**
- Period columns (Y1–Y30) as horizontal columns — familiar from Excel models
- Line items as rows — vertical layout
- Bold totals row at bottom
- Freeze pane effect: sticky left column (line items) + sticky top row (headers)
- Compact numeric formatting: kEUR, EUR/MWh, % — no full decimal precision
- Status badges only in governance cells
- No KPI card clutter inside detailed sheets

---

## 5. TUHO / Oborovo Load Flow

**Design goal:** User selects a project → inputs populate from existing factory defaults → user can run.

```
┌─────────────────────────────────────────────────────────────────┐
│ Project: [TUHO ▼]          ← user selects TUHO or Oborovo    │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Loading TUHO factory inputs...                                  │
│ (server reads from app.models.tuho_factory or oborovo_factory)│
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Project: TUHO | Scenario: Base                                 │
│ [▶ Run Model] enabled                                          │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ Outputs appear in main workspace                                │
│ (IRR, DSCR, Debt, Revenue, etc.)                               │
└─────────────────────────────────────────────────────────────────┘
```

**Current infrastructure:**
- `app.models.tuho_factory` and `app.models.oborovo_factory` already exist
- `run_project(project_type, scenario, **kwargs)` already reads factory defaults
- Project type selector on current form already shows TUHO / Oborovo options

**UI changes needed (future phase):**
- Project selector moved from form field → sidebar dropdown
- Scenario selector added to sidebar
- Active project indicator added to sidebar
- Run history per project/scenario

---

## 6. New Project Flow (Placeholder)

```
┌─────────────────────────────────────────────────────────────────┐
│ [+] New Project                                                  │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│ New Project                                              [✕]   │
│ ────────────────────────────────────────────────────────────────  │
│ Project Name: [________________]                                 │
│                                                                  │
│ Technology:  ○ Solar   ○ Wind   ○ Hybrid / BESS (future)       │
│                                                                  │
│ Template:    ○ Blank project                                     │
│             ○ TUHO-like (wind, 72MW, HR tax)                     │
│             ○ Oborovo-like (solar, 53MW, BIH tax)               │
│                                                                  │
│                                     [Create]  [Cancel]           │
└─────────────────────────────────────────────────────────────────┘
```

**Note:** For Phase 9.5 design spec, this is a placeholder flow. No implementation required.

---

## 7. Save/Load Flow (Future Path)

**Current state:**
- No project persistence — all inputs are form POST parameters
- Session-based: inputs held in server-side session/cookie
- No database

**Minimal future data model (Phase 12):**
```
Project {
  id: UUID
  name: str
  technology: Solar | Wind | Hybrid
  scenario: str
  inputs: JSON
  outputs: JSON (nullable — computed on run)
  created_at: datetime
  updated_at: datetime
}
```

**Save flow (future):**
```
User fills inputs → [Save Project] → Project saved to DB → user sees saved in sidebar
```

**Load flow (future):**
```
User selects saved project from sidebar → inputs populated from DB → user can edit/run
```

**Phase 9.5 stance:** Design only. No persistence implementation.

---

## 8. Excel-Like Visual Principles

| Principle | Application |
|-----------|-------------|
| Horizontal period columns | Y1–Y30 in OPEX, CAPEX, Revenue, P&L, Cash Flow sheets |
| Vertical line items | Personnel, O&M, Insurance in OPEX; Debt service in Cash Flow |
| Freeze pane | Sticky left column (labels) + sticky top row (headers) |
| Compact numbers | kEUR format, 1 decimal, no trailing zeros |
| Section headers | Bold, slightly larger font, border-bottom |
| Totals rows | Bold, top border line |
| Status badges only | Badges only in Governance / Audit cells |
| No dashboard clutter inside sheets | KPIs belong on Overview tab, not on OPEX sheet |
| Monospace numerics | `font-variant-numeric: tabular-nums` for column alignment |

---

## 9. Implementation Phases

| Phase | Scope | Notes |
|-------|-------|-------|
| **9.5 (this design)** | Design spec + docs + tests | NO implementation |
| **9.6 (shell)** | Top-tab HTML/CSS scaffold, sidebar as workspace, tab switching JS | UI shell only |
| **9.7 (overview tab)** | Overview KPI dashboard as first tab | |
| **9.8 (sheet decomposition)** | Decompose current `<details>` accordion into per-tab content sections | |
| **9.9 (TUHO/Oborovo selector)** | Project selector in sidebar wired to factory defaults | |
| **10.x (period tables)** | Horizontal period column formatting for OPEX, CAPEX, P&L | |
| **11.x (freeze panes)** | Sticky headers/columns for period tables | |
| **12.x (persistence)** | DB-backed project save/load | Future |

---

## 10. No Runtime Changes Statement

**This design document describes UI architecture only.**

- No changes to `app.models.*`, `app.core.*`, `app.calculations.*`
- No changes to model formulas, factories, waterfall, SHL, TaxBridge
- No changes to Excel export logic
- No changes to persistence (Phase 12 is the designated persistence phase)
- No changes to runtime flags (R99/R102 remain NOT APPROVED)
- No changes to G20 gate (remains BLOCKED pending stakeholder approval)

---

## 11. Governance Note

| Item | Status | Change |
|------|--------|--------|
| G20 Gate | BLOCKED (0.29pp equity IRR residual) | No change |
| R99/R102 | NOT APPROVED | No change |
| CO2 Revenue | Enabled, €4.19/MWh | No change |
| TUHO Tax | Croatia 10-period | No change |

Governance status badges should remain visible in:
- Sidebar (always visible)
- Overview tab (KPI row)

---

## 12. Next Steps

1. Review and approve this design doc
2. Proceed to `phase9_5-excel-like-project-workspace-ui-shell` for UI shell implementation
3. Wire top-tab scaffold with tab-switching JS
4. Migrate sidebar to workspace panel
5. Decompose accordion content into per-tab sections