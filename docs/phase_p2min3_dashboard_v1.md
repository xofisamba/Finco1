# Phase P2-min-3 — Dashboard v1 (presentation only)

**Type:** Presentation / UX simplification
**Base:** branch `p2-min-2-hide-internal-vocabulary` (PR2 DRAFT, PR #610)
**Status:** DRAFT, awaiting review

---

## Goal

A first version of the Dashboard: 8 KPI cards +
3 inline-SVG charts, server-rendered. NO
Chart.js / Plotly / D3 / any JS library. NO
JS calc. NO formula / debt / DSCR / tax /
IDC / construction / R-PAR / C10 changes.
NO factory / model change. NO persistence
schema migration.

**Hidden != deleted.** The existing
Overview KPI grid + Governance Status
panel + TUHO Parity panel remain in the
Overview tab above the Dashboard v1
section.

---

## What changed

### `app/ui/dashboard.py` (NEW)

Pure-Python presentation-layer helpers:

- `build_dashboard_kpis(...)` — returns
  8 KPI cards (project_irr, equity_irr,
  senior_debt, realized_gearing, min_dscr,
  avg_dscr, y1_revenue, y1_ebitda).
- `build_revenue_ebitda_series(...)` —
  reads Revenue and EBITDA from the
  runtime result.
- `build_dscr_series(...)` — reads DSCR
  and target_dscr from the runtime result.
- `build_debt_balance_series(...)` —
  reads the senior debt balance from the
  **explicit result field** (NOT from a
  `_find_debt_balance` heuristic).
- `render_svg_line_chart(...)` — renders
  a small inline-SVG line chart.
- `render_svg_dscr_chart(...)` — renders
  the DSCR chart with a dashed target
  line.
- `render_svg_debt_chart(...)` — renders
  the debt chart with an area-under-line
  fill.

Realized gearing is computed in the
Python helper (NOT in Jinja / JS / SVG)
and reuses the existing PR2 helper
`_compute_realized_gearing_pct`.

### `app/templates/partials/_dashboard.html` (NEW)

Dashboard v1 partial: 8 KPI cards + 3
inline-SVG charts. Server-rendered.

### `app/templates/partials/workspace_shell.html` (MODIFIED)

Includes the new partial inside the
Overview panel, guarded by
`{% if dashboard_enabled %}`.

### `static/styles.css` (MODIFIED)

A small `.dashboard` CSS block that
reuses the existing CSS variables. No
new dependency.

### `main_web.py` (MODIFIED)

- New helper `_build_index_dashboard_context(...)`
  builds the inline dashboard data.
- The `GET /` (index) context now
  includes the dashboard data for
  user_created projects.

### `tests/test_phase_p2min3_dashboard_v1.py` (NEW)

19 tests across 7 test classes:

- `TestDashboardModule` (5 tests) —
  module imports, 8 KPIs, Realized
  Gearing status='derived', series
  helpers, explicit result field (no
  `_find_debt_balance`).
- `TestSvgRendering` (4 tests) — SVG
  line chart with data / no data, DSCR
  chart with dashed target line, debt
  chart with area fill.
- `TestWorkspaceShellIntegration`
  (3 tests) — partial include,
  partial renders, conditional
  include.
- `TestNoChartLibraries` (2 tests) —
  no Chart.js / Plotly / D3 / React /
  Vue / Svelte / Tailwind / Alpine
  imports; no chart libraries in
  `static/app.js`.
- `TestPhaseInvariants` (3 tests) —
  rc1 SHA, use_construction_schedule_
  engine=False, Phase 51F parity.
- `TestPriorPhaseTestsPreserved`
  (1 test) — full prior-phase test
  stack passes.

### Cross-arc test patches

P2-min-3 adds 5 new file paths. The
file-scope allowlist in PR1, PR2, PR3,
M1 test files is extended to include
the new paths.

---

## What did NOT change (pinned by tests)

- No formula changes
- No debt sizing changes
- No DSCR sculpt semantics changes
- No TUHO / Oborovo factory path changes
- No Excel goldens changes
- No tax / depreciation / IDC changes
- No construction / C10 / R-PAR changes
- No `manual_gearing` / `gearing_cap` /
  `min(gearing_cap, sculpt)` blend
- No R99 / R102 / G20 promotion
- No persistence schema migration
- No `app/services/` downstream service
  code changes
- No `app/persistence/` changes
- No `static/app.js` changes
- No `main_api.py` changes
- No Tailwind / Alpine / React / Vue /
  Svelte
- No Chart.js / Plotly / D3
- No JS calc
- No `_find_debt_balance` heuristic
- No route / CSS class / context-key /
  test / project_origin renames
- `use_construction_schedule_engine`
  remains False
- rc1 SHA preserved

---

## Roadmap (post-PR3)

PR3 is the third PR in the P2-min
stacked UX simplification arc:

1. **PR1** (PR #609) — Project Home +
   Minimal New Project (DRAFT)
2. **PR2** (PR #610) — Hide Internal
   Vocabulary (DRAFT)
3. **PR3** (this PR) — Dashboard v1
   (DRAFT)
4. **PR4** — Navigation Compression
   (depends on PR3)

`manual_gearing` is **not** on this
roadmap.

DO NOT START: PR4 until PR3 is approved
and merged.

---

## Test results

- **19 / 19** P2-min-3 tests PASS
- **361 / 361** cross-arc tests
  (PR1+PR2+PR3+M1+P1-A+P1-B+51F
  parity+P2-min-1+P2-min-2+P2-min-3)
- 21 / 21 Phase 51F parity guardrails
  PASS
- 0 failed
- rc1 SHA preserved
- `use_construction_schedule_engine`
  remains False

---

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do
NOT merge. Awaiting user review and
explicit go-ahead before PR3 lands on
PR2.
