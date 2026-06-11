# Phase P2-FIX-4 — Five-Area Navigation + Dashboard Landing + Reviewer Mode

**Branch:** `p2-fix-4-five-area-nav`
**Base:** `main` @ `510db16` (post P2-FIX-2)
**Type:** presentation / navigation cleanup only
**Status:** DRAFT (PR #618)

> **NOTE on base**: P2-FIX-3 (PR #617) is not yet merged at the
> time of authoring. P2-FIX-4 builds on P2-FIX-2 (`510db16`).
> The P2-FIX-3 C2 first-edit guard is verified in
> `test_phase_p2fix3_c2_first_edit.py` (a separate test file
> gated on P2-FIX-3 merge). The P2-FIX-4 test
> `test_p2fix3_first_edit_guard_still_active` is currently
> SKIPPED; it should be uncommented after P2-FIX-3 merge.

---

## Goal

Create a five-area navigation model so the workspace is no
longer overwhelming. The five top-level visible areas are:

1. **Dashboard** (default view; the existing overview / KPIs
   panel).
2. **Inputs** (existing inputs).
3. **Results** (existing construction + production + revenue
   + opex + capex + senior-debt + shl + tax + pl + cashflow +
   balance + distributions + sponsor).
4. **Scenarios** (existing scenarios).
5. **Export & Audit** (existing audit + downloads).

The 20+ underlying `ws-tab` buttons are preserved (hidden != deleted).
The compressed view is a presentation-only shortcut that calls
the existing `switchTab` JS function.

---

## Before / After

### Before (P2-FIX-2 state)

20 top-level visible tabs in the workspace ribbon:

| # | Tab | Area |
|---|---|---|
| 1 | Overview | (separate; not in 5-area) |
| 2 | Inputs | (separate; not in 5-area) |
| 3 | Scenarios | (separate; not in 5-area) |
| 4 | Construction | (separate; not in 5-area) |
| 5 | Production | (separate; not in 5-area) |
| 6 | Revenue | (separate; not in 5-area) |
| 7 | OPEX | (separate; not in 5-area) |
| 8 | CAPEX | (separate; not in 5-area) |
| 9 | Senior Debt | (separate; not in 5-area) |
| 10 | SHL | (separate; not in 5-area) |
| 11 | Tax | (separate; not in 5-area) |
| 12 | P&L | (separate; not in 5-area) |
| 13 | Cash Flow | (separate; not in 5-area) |
| 14 | Balance Sheet | (separate; not in 5-area) |
| 15 | Distributions | (separate; not in 5-area) |
| 16 | Sponsor / Equity | (separate; not in 5-area) |
| 17 | Audit / Reference | (separate; not in 5-area) |
| 18 | Downloads | (separate; not in 5-area) |
| 19 | Compare | (separate; not in 5-area) |
| 20 | Help | (separate; not in 5-area) |

Plus the P2-min-4 compressed nav (5 tabs) was **only rendered
for user_created projects**. Protected references (TUHO /
Oborovo) did NOT get the compressed view at all.

### After (P2-FIX-4)

5 top-level visible areas + 1 secondary link:

| # | Top-level area | Underlying panels (preserved) |
|---|---|---|
| 1 | **Dashboard** (default, active) | overview + KPI grid + 3 inline-SVG charts |
| 2 | **Inputs** | inputs |
| 3 | **Results** | construction + production + revenue + opex + capex + senior-debt + shl + tax + pl + cashflow + balance + distributions + sponsor (sub-nav lets the user jump to a specific sheet) |
| 4 | **Scenarios** | scenario |
| 5 | **Export & Audit** | audit + downloads (audit tab contains the relocated governance / lineage / runtime-source content from P2-FIX-2) |
| 6 | Help (secondary) | help |

**Top-level visible count: 5 (+ 1 secondary Help link).**

The 20 underlying `ws-tab` buttons are still in the DOM
(hidden != deleted). The compressed view is enabled for
**EVERY** project, including protected references (TUHO /
Oborovo) — the previous P2-min-4 gate
(`project_origin == "user_created"`) was removed.

### Which panels moved under each area

| Area | Panels |
|---|---|
| **Dashboard** | overview, dashboard-v1 (P2-min-3) |
| **Inputs** | inputs |
| **Results** | construction, production, revenue, opex, capex, senior-debt, shl, tax, pl, cashflow, balance, distributions, sponsor |
| **Scenarios** | scenario (existing scenarios tab) |
| **Export & Audit** | audit (with relocated governance / lineage / runtime-source from P2-FIX-2), downloads |
| Help (secondary) | help |

---

## Architecture

### Five-area nav (`_nav_compression.html`)

The `_nav_compression.html` partial is rendered above the
existing `ws-tab` ribbon. It contains 5 main tabs + 1
secondary Help link.

Each tab has `onclick="switchTab('xxx')"` to delegate to the
existing JS function. No new JS is introduced.

The default active tab is `Dashboard` (target: `panel-overview`).
This is unchanged from P2-FIX-1.

### Results sub-navigation (`_results_subnav.html`)

Inside the Results area (which targets `panel-capex` as the
default landing), a secondary `_results_subnav.html` partial
renders 13 sub-nav buttons for the output sheets: Revenue,
OPEX, CAPEX, Senior Debt, SHL, Tax, P&L, Cash Flow, Balance
Sheet, Distributions, Sponsor, Construction, Production.

Each sub-nav button also calls the existing `switchTab` JS
function. No new JS.

### Dashboard content

The Dashboard v1 partial (`_dashboard.html`) is rendered for
EVERY project (user_created, factory_template, saved_baseline).
For a fresh open of a protected reference (TUHO / Oborovo)
where the runtime has not produced a snapshot yet, the
dashboard shows:

- A "No run yet" CTA (`dashboard-run-cta`) with a "Run model"
  button that posts to `/run`.
- A run-status chip when the runtime has a snapshot
  (`dashboard-run-status`).

The 8 KPIs (Project IRR, Equity IRR, Senior debt, Realized
gearing, Min DSCR, Avg DSCR, Y1 Revenue, Y1 EBITDA) are
rendered when the runtime has data. P2-FIX-4 adds **Project
NPV** as a 9th KPI (read defensively from
`summary.get("project_npv_keur")`; status = "missing" if not
available).

---

## Files changed (4 files, +266 / -10)

### New files (2)
- `app/templates/partials/_results_subnav.html` (NEW) — 13-button
  Results sub-navigation.
- `tests/test_phase_p2fix4_five_area_navigation.py` (NEW) — 25
  tests across 6 test classes (1 skip; 24 pass).

### Modified files (2)
- `app/templates/partials/_nav_compression.html` (MODIFIED) —
  renamed "Outputs" to "Results", updated attributes to
  `data-p2fix4-*`, added comment block explaining the
  5-area model.
- `app/templates/partials/_dashboard.html` (MODIFIED) — added
  "No run yet" CTA + run-status chip.
- `app/ui/dashboard.py` (MODIFIED) — added Project NPV KPI.
- `app/templates/partials/workspace_shell.html` (MODIFIED) —
  included `_results_subnav.html` inside `panel-capex`.
- `main_web.py` (MODIFIED) —
  - `nav_compression_enabled` is now `True` for every project
    (removed the `user_created` gate).
  - `_build_index_dashboard_context` is now called for every
    project origin (user_created, factory_template,
    saved_baseline).
- `docs/phase_p2fix4_five_area_navigation.md` (NEW)
- `reports/phase_p2fix4_five_area_navigation.md` (NEW)

---

## Tests (24 PASS, 1 SKIP)

| Test class | Tests | Verifies |
|---|---|---|
| `TestFiveAreaNavigation` | 5 | Five top-level nav tabs render for TUHO, Oborovo, and Generic Solar. Help secondary link preserved. Underlying 17 ws-tab buttons still in the DOM (hidden != deleted). |
| `TestDashboardDefault` | 5 | Dashboard renders for TUHO / Oborovo / Generic. Default active tab is Dashboard. Run CTA + run-status chip present. KPI grid + chart grid referenced. |
| `TestResultsSubNavigation` | 3 | Results sub-nav present, 13 sub-tabs, uses existing switchTab JS (no new JS). |
| `TestNormalModeNegative` | 4 | Workspace overview, Inputs, Scenarios, CAPEX sheet — no forbidden terms (factory / baseline / parity / calibration / golden / G20 / R99 / R102 / Lifecycle Clarity / Export Lineage / Governance Posture / Review boundary). |
| `TestPriorBehaviorPreserved` | 7 | P2-FIX-1 default route renders Project Home. /projects/new minimal form. P2-FIX-3 first-edit guard (currently SKIPPED, gated on P2-FIX-3 merge). P2-FIX-2 audit tab preserved. Export, compare, scenario routes still work. |
| `TestFileScope` | 1 | Only allowed files changed (templates / main_web / dashboard.py / new test / docs / reports). No `app/persistence/`, no `app/services/`, no `main_api.py`, no `static/app.js`. |

**Total: 24 PASS, 1 SKIP, 0 FAIL.**

### Pre-existing tests still pass
- `tests/test_phase_p2fix2_shell_strip.py` — **25 / 25 PASS** (P2-FIX-2)
- `tests/test_phase51f_parallel_work_guardrails.py` — **21 / 21 PASS** (parity guardrails)

**Grand total: 70 / 70 PASS, 1 SKIP (P2-FIX-3 gated).**

---

## Hard constraints preserved (verified)

- ✅ rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` preserved
- ✅ TUHO parity netaknut
- ✅ Oborovo parity netaknut
- ✅ `use_construction_schedule_engine` = False
- ✅ No formula / debt / DSCR / tax / IDC / construction / R-PAR / C10 / R99 / R102 / G20 promotion changes
- ✅ No destructive persistence migration
- ✅ No `static/app.js` changes (0 lines diff; uses existing
  `switchTab` JS)
- ✅ No `main_api.py` changes
- ✅ No route / CSS class / context-key / project_origin renames
- ✅ No new dependencies
- ✅ No Tailwind / Alpine / React / Vue / Svelte
- ✅ No Chart.js / Plotly / D3
- ✅ `factory_template` / `saved_baseline` literals still in `app/persistence/` (hidden != deleted)
- ✅ Frozen senior debt schedule unchanged (fixture-backed)
- ✅ Excel goldens unchanged

---

## Flow-walk evidence (manual, verified by tests)

1. **Project Home** (`GET /`, no project): renders the
   landing (P2-FIX-1 contract preserved).

2. **Dashboard** (`GET /?project=tuho`): the 5-area nav
   renders. The Dashboard tab is active by default. The
   dashboard shows a "No run yet" CTA (TUHO has no runtime
   snapshot for the protected reference).

3. **Inputs** (`GET /inputs?project=tuho`): the Inputs tab is
   reachable. The 5-area nav highlights the Inputs tab.

4. **Results** (`GET /?project=tuho` + click Results): the
   Results sub-nav renders with 13 output-sheet shortcuts.
   Each sub-nav button calls `switchTab(...)` to jump to a
   specific sheet.

5. **Scenarios** (`GET /scenarios?project=tuho`): existing
   scenario functionality preserved.

6. **Export & Audit** (`GET /?project=tuho` + click Export & Audit):
   the audit tab renders with the relocated governance /
   lineage / runtime-source content (P2-FIX-2 contract
   preserved).

---

## Stop-after-report contract

- ✅ PR #618 is **DRAFT** (not marked ready, not merged)
- ✅ No P2-FIX-5 work started
- ✅ No other arc work started

---

## P2-FIX arc status

1. P2-FIX-1 — MERGED @ `c8564fa` (PR #615)
2. P2-FIX-2 — MERGED @ `510db16` (PR #616)
3. P2-FIX-3 — DRAFT #617 (head `23ae0bf`; awaiting merge)
4. P2-FIX-4 — DRAFT (this PR)

`manual_gearing` is NOT on this roadmap.
