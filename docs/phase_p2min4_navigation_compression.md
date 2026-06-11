# Phase P2-min-4 — Navigation Compression (presentation only)

**Type:** Presentation / UX simplification
**Base:** branch `p2-min-3-dashboard-v1` (PR3 DRAFT, PR #611)
**Status:** DRAFT, awaiting review

---

## Goal

Compress the 20 top-level tabs into 6
compressed tabs (Dashboard, Inputs,
Scenarios, Outputs, Export & Audit, Help)
for a cleaner, more product-shaped
navigation. The underlying ws-tab buttons
+ panel panels + routes are preserved
(hidden != deleted).

**No route deletion. No panel deletion.
No ws-tab button deletion. No backend
deletion.** The compressed view is a
presentation-only navigation bar that
calls the existing switchTab JS function.

---

## What changed

### `app/templates/partials/_nav_compression.html` (NEW)

A small partial that renders 6 compressed
buttons:

1. Dashboard (default; existing
   `panel-overview`)
2. Inputs (existing `panel-inputs`)
3. Scenarios (existing `panel-scenario`)
4. Outputs (existing `panel-capex`
   default; the user can drill down into
   the 13 underlying Output Sheets)
5. Export & Audit (existing
   `panel-audit`)
6. Help (existing `panel-help`)

Each button calls the existing
`switchTab(targetTab)` JS function. No
new JS library.

### `app/templates/base.html` (MODIFIED)

Includes the new partial above the
existing `workspace_tabs.html`, guarded
by `{% if nav_compression_enabled %}`.

### `static/styles.css` (MODIFIED)

A small `.nav-compression` CSS block
that reuses existing CSS variables. No
new dependency.

### `main_web.py` (MODIFIED)

- The `GET /` (index) context now
  includes `nav_compression_enabled` for
  user_created projects.

### `tests/test_phase_p2min4_navigation_compression.py` (NEW)

16 tests across 6 test classes:

- `TestCompressedNav` (5 tests) —
  partial exists, 5+ tabs, brief-
  approved copy, Dashboard is default
  active, uses existing `switchTab` JS
- `TestNoRouteOrPanelDeletion` (3
  tests) — ws-tab buttons preserved
  (>= 19), all 20 panel-... panels
  preserved, no route renames or
  deletions
- `TestBaseHtmlIntegration` (2 tests)
  — base.html includes the partial +
  guarded by flag
- `TestNoJsLibraries` (2 tests) — no
  React/Vue/Svelte/Tailwind/Alpine/Chart
  in the partial or in `static/app.js`
- `TestPhaseInvariants` (3 tests) —
  rc1 SHA, use_construction_schedule_
  engine=False, Phase 51F parity
- `TestPriorPhaseTestsPreserved`
  (1 test) — full prior-phase test
  stack passes

### Cross-arc test patches

P2-min-4 adds 4 new file paths. The
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
- No new dependency
- No JS calc
- No route deletion
- No panel deletion
- No ws-tab button deletion
- No route / CSS class / context-key /
  test / project_origin renames
- `use_construction_schedule_engine`
  remains False
- rc1 SHA preserved

---

## Roadmap (post-PR4)

PR4 is the **final PR** of the P2-min
stacked UX simplification arc:

1. **PR1** (PR #609) — Project Home +
   Minimal New Project (DRAFT)
2. **PR2** (PR #610) — Hide Internal
   Vocabulary (DRAFT)
3. **PR3** (PR #611) — Dashboard v1
   (DRAFT)
4. **PR4** (this PR) — Navigation
   Compression (DRAFT)

`manual_gearing` is **not** on this
roadmap.

After PR4 lands on PR3, the next arc
will be chosen with explicit user
go-ahead.

---

## Test results

- **16 / 16** P2-min-4 tests PASS
- All prior-phase tests pass (PR1+PR2+
  PR3+M1+P1-A+P1-B+51F parity+P2-min-1+
  P2-min-2+P2-min-3)
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
explicit go-ahead before PR4 lands on
PR3.
