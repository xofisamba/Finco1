# Phase 9.5 — UI Closeout Review

**Branch:** `phase9_5-ui-closeout-review`
**Date:** 2026-05-22
**Status:** COMPLETE

---

## Section A: What Phase 9.5 Delivered

Phase 9.5 added the Excel-like project workspace UI shell and runtime summary binding:

- **Workspace Shell (`workspace_shell.html`):** Fixed left sidebar with project selector, top tab ribbon (15 tabs: Overview → Downloads), active tab state management, HTMX-driven tab switching
- **Project Selector:** TUHO and Oborovo projects, project switching via HTMX, active state stored in `localStorage`, `active-project-name` display
- **Runtime Binding:** `sessionStorage.setItem("lastRuntimeSummary", {...})` populated on every `POST /run` response; shared JS reads it and populates KPI cards across all output tabs
- **Output Tabs with Runtime Summaries:** P&L, Cash Flow, Balance Sheet, Senior Debt, SHL, Tax — all include `shared_runtime_block.html` and tab-specific secondary metrics (DSCR, SHL Opening, Senior Debt amount, CIT Status)
- **Preview Sections:** All output tabs retain `<div class="preview-notice">Preview schedule — static...values, not live calculated output</div>` so preview vs runtime is clearly distinguished
- **Governance Visibility:** G20 BLOCKED and R99/R102 NOT APPROVED badges prominently visible in Overview, Audit/Parity, Tax, and Sponsor tabs
- **TUHO Parity Panel:** Audit-Only status cards in Overview and Audit/Parity tabs showing Senior Debt PASS, SHL Opening PASS, Distributions ACCEPTED CONV, Equity IRR WARN/0.29pp, Tax/CFADS MISSING_EVIDENCE
- **Downloads Tab:** Four-item download grid (Model Export, Parity Workbook, Gap Register, Source Map)

---

## Section B: Current Architecture

### Stack
- **Frontend:** Vanilla JS + HTMX 1.9.x (no React, no Streamlit rerender)
- **Templates:** Jinja2 HTML partials in `app/templates/partials/`
- **CSS:** Single file `static/styles.css` (~800 lines, institutional navy/light palette)
- **Sessions:** `sessionStorage` for per-tab runtime summary (survives tab navigation, cleared on browser close)

### Project Context
- `app/ui/project_context.py` — `ProjectContext` dataclass with `.id`, `.code`, `.name`, `.data_source`
- FACTORY_MAP keys: `"TUHO"` and `"Oborovo"` (mixed case for Oborovo)
- Active project stored in `sessionStorage.activeProjectKey` → looked up in `FACTORY_MAP`

### Runtime Summary Flow
1. `main_web.py` `POST /run` handler: runs selected project waterfall → calls `ui_runtime_summary.runtime_summary_to_dict()`
2. Response HTML includes `<script>sessionStorage.setItem("lastRuntimeSummary", JSON.stringify({...}))</script>`
3. Each tab's `shared_runtime_block.html` has `window._populateRuntimeBlock()` called on `DOMContentLoaded` and `htmx:afterSwap`
4. KPI grid populated from `lastRuntimeSummary` dict; `NOT_AVAILABLE` sentinel for missing metrics

### Preview / Runtime Separation
- **Preview state:** Static seed data (TUHO factory assumptions), yellow `.preview-notice` banner, `badge badge-preview` label — visible at all times before first run
- **Runtime state:** Runtime summary block appears (display:none → display:""), replaces or supplements preview KPI section — visible after `POST /run`
- Tabs still show preview tables even after run (full runtime tables are future work)

---

## Section C: Known Limitations

- **No persistence:** Runtime summaries survive page refresh only via `sessionStorage`; no server-side state, no database
- **No editable spreadsheets:** Input assumptions are form-based, not cell-editable like Excel
- **Partial runtime schedules:** Output tabs show runtime summary KPIs but full period-by-period schedule tables still show static preview data
- **Preview sections remain:** Even after a successful run, the static P&L/CF/BS preview tables remain visible below the runtime summary — no automatic swap
- **No scenario comparison:** Multi-scenario side-by-side not implemented
- **Audit/Parity workbook download:** Download links (`#download-parity`, etc.) are anchor stubs — no actual XLSX generation yet

---

## Section D: UI Debt Register

Items below are **not changed** in this closeout branch; they are future-phase work.

| # | Area | Issue | Future Phase | Notes |
|---|------|-------|-------------|-------|
| 1 | Persistence | Runtime summaries vanish on browser close; no server-side state | Phase 10 (persistence layer) | Need DB or server-side session store |
| 2 | Full Live Financials | P&L/CF/BS tables show static seed data, not live waterfall output | Phase 10 or 11 | Waterfall engine drives period schedules; needs renderer |
| 3 | Scenario Compare | No side-by-side scenario comparison view | Phase 10 | Multi-scenario tab or modal |
| 4 | Spreadsheet Editing | No cell-by-cell Excel-like editing; form-based inputs only | Phase 11 | Big effort; requires cell-model architecture |
| 5 | Export Integration | `#download-parity` etc. are anchor stubs | Phase 10 | Parity workbook generation via openpyxl |
| 6 | Runtime Table Virtualization | Long period tables (60+ columns) not virtualized | Phase 11 | Use virtual scrolling for large grids |
| 7 | Freeze Panes | No Excel-like freeze panes on financial tables | Phase 11 | CSS `position: sticky` or JS library |
| 8 | Enterprise UX | No keyboard shortcuts, undo/redo, audit trail | Phase 12 | Separate UX sprint |
| 9 | TUHO Parity Workbook | XLSX export with full column-by-column parity | Phase 10 | `openpyxl`-based generation |
| 10 | SHL Repayment Schedule | Full SHL amortization schedule not shown in runtime | Phase 10 | Partial data in runtime summary only |

---

## Section E: Governance Status

**G20 Gate: BLOCKED** — No changes made. Equity IRR residual is within ±1.0pp tolerance per Phase 9 convention; G20 remains BLOCKED pending stakeholder decision on reconciliation IRR or formal acceptance of convention differences.

**R99/R102 Promotion: NOT APPROVED** — No changes made. Sponsor waterfall defaults remain in factory mode; runtime flags not approved for production promotion.

**TUHO Parity: Audit-Only (DA-Wired)** — Senior Debt PASS, SHL Opening PASS, Distributions ACCEPTED CONV, Equity IRR WARN/0.29pp, Tax/CFADS MISSING_EVIDENCE. No changes to parity status in this branch.

No G20 approval or R99/R102 promotion actions were taken or simulated in this branch.

---

## Section F: No Runtime Formula Changes Statement

**Confirmed:** This branch (`phase9_5-ui-closeout-review`) makes zero changes to runtime model files.

Specifically:
- `domain/waterfall/` — unchanged
- `domain/senior_debt/` — unchanged
- `domain/shl/` — unchanged
- `domain/tax/` and `domain/tax_bridge/` — unchanged
- `app/waterfall/` — unchanged
- `app/ui_runner.py` — unchanged
- `app/tax_bridge.py` — unchanged
- `app/project_factories.py` — unchanged

All changes are confined to:
- `app/templates/partials/*.html` — UI templates (no logic changes)
- `static/styles.css` — CSS only (`.badge-runtime` definition added)
- `docs/phase9_5_ui_closeout_review.md` — this document
- `reports/phase9_5_ui_closeout_checklist.csv` — checklist artefact

Test suite confirms: `tests/test_no_runtime_model_files_changed` (part of `TestNoRuntimeModelFilesChanged` class) passes, verifying no waterfall, senior_debt, shl, or tax_bridge files were modified.