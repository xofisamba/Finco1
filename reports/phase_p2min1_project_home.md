# Phase P2-min-1 — Project Home + Minimal New Project — Report

## Status

- **Type:** Presentation / UX entry point
  (presentation-only).
- **Branch:** `p2-min-1-project-home-minimal-new-project`
- **Base:** main @ `e1ad5db` (post-PR3
  merge, PR #608)
- **PR:** DRAFT only. Do NOT mark ready.
  Do NOT merge.

## Summary

P2-min-1 introduces a product-shaped
Project Home entry point and a minimal
New Project form. The first screen now
feels like a product, not an internal
modelling laboratory. Factory templates
(TUHO, Oborovo), baselines, and internal
vocabulary are hidden from the Project
Home view via a presentation filter (not
deleted — they remain reachable from
`/projects/browse` and the audit fixture
paths).

The minimal New Project form asks only
4 fields: Project name, Technology,
Country, MW. All other driver values
come from template defaults via the
existing `/projects/new/defaults`
endpoint. No backend / no persistence /
no factory change.

A Help link (icon, not a sixth top-level
tab) is added to the site header.

## Files in PR1 (8)

### Production code (6)

- `app/templates/partials/project_home.html`
  (NEW) — Project Home partial
- `app/templates/partials/new_project_minimal.html`
  (NEW) — Minimal New Project partial
- `app/templates/partials/project_selector.html`
  (MODIFIED) — sidebar Home action
  added before "New project"
- `app/templates/base.html` (MODIFIED) —
  Help link (icon) added to site header
- `static/styles.css` (MODIFIED) —
  Project Home CSS block + header
  help-link CSS
- `main_web.py` (MODIFIED) — new routes
  `GET /home` and `GET
  /projects/new/minimal` (presentation
  only)

### Tests (1 + 4 cross-arc patches)

- `tests/test_phase_p2min1_project_home.py`
  (NEW) — 8 test classes, 16 tests:
  - `TestProjectHomeRoute` (4 tests) —
    `/home` route, partial render, CTA,
    base.html help link
  - `TestFactoryTemplatesHiddenFromHome`
    (1 test) — TUHO / Oborovo / factory
    templates / OBR-001 hidden from
    Project Home
  - `TestFactoryPathsStillWork` (2
    tests) — factory template options
    and factory functions unchanged
    (hidden ≠ deleted)
  - `TestBrowseStillRendersFactoryTemplates`
    (1 test) — `/projects/browse` still
    renders the full project browser
    (hidden ≠ deleted)
  - `TestMinimalNewProjectRoute` (4
    tests) — minimal form route, 4
    visible fields, no driver fields,
    posts to existing /projects/create
  - `TestTimingFieldFixPreserved` (1
    test) — PR1 timing-field fix
    preserved
  - `TestPhaseInvariants` (3 tests) —
    rc1 SHA resolvable,
    `use_construction_schedule_engine`
    remains False, Phase 51F parity
    guardrails pass

- Cross-arc test patches (M1, PR1, PR2,
  PR3) — file-scope allowlist extensions
  to include the P2-min-1 follow-up files
  (forward-compatible contract
  extensions)
- PR2 and PR3 `test_no_forbidden_path_changes`
  tests updated to allowlist `main_web.py`
  for the P2-min-1 follow-up (presentation
  only)

### Docs (1)

- `docs/phase_p2min1_project_home.md`
  (NEW) — governance doc

## Test results (final, PR1)

- **16 / 16 PR1 tests PASS**
- **327 / 327** cross-arc tests (PR1 +
  PR2 + PR3 + M1 + P1-A + P1-B + Phase
  51F parity + P2-min-1) PASS
- **21 / 21** Phase 51F parity
  guardrails PASS
- 0 failed
- rc1 SHA
  `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  preserved
- `use_construction_schedule_engine`
  remains False

## Pre-merge audit (all pinned by tests)

### What changed in production code

- `app/templates/partials/project_home.html`
  (NEW) — partial
- `app/templates/partials/new_project_minimal.html`
  (NEW) — partial
- `app/templates/partials/project_selector.html`
  (MODIFIED) — sidebar Home action
- `app/templates/base.html` (MODIFIED) —
  Help link icon
- `static/styles.css` (MODIFIED) —
  Project Home + header help-link CSS
- `main_web.py` (MODIFIED) — new routes
  `GET /home` and
  `GET /projects/new/minimal` (no
  business logic)

### What did NOT change (pinned by tests)

- `app/project_factories.py` —
  UNCHANGED (factory paths preserved
  bit-exact, SHA verified)
- `app/waterfall_core.py` — UNCHANGED
  (model SHA verified)
- `app/waterfall_runner.py` —
  UNCHANGED
- `main_api.py` — UNCHANGED
- `app/persistence/` — UNCHANGED
- `app/services/` — UNCHANGED
- `app/excel_export.py` — UNCHANGED
  (Excel goldens preserved)
- `static/app.js` — UNCHANGED
- `static/styles.css` — only P2-min-1
  CSS additions; no existing rule
  changed

## Files in PR1 — base SHA pinning

| File | Base SHA | Head SHA |
|---|---|---|
| `main_web.py` | `e1ad5db` | (this PR) |
| `app/templates/partials/project_home.html` | `e1ad5db` | NEW |
| `app/templates/partials/new_project_minimal.html` | `e1ad5db` | NEW |
| `app/templates/partials/project_selector.html` | `e1ad5db` | MODIFIED |
| `app/templates/base.html` | `e1ad5db` | MODIFIED |
| `static/styles.css` | `e1ad5db` | MODIFIED |
| `tests/test_phase_p2min1_project_home.py` | `e1ad5db` | NEW |

## Hard no-go (preserved, all pinned by tests)

- No formula changes
- No debt sizing changes
- No DSCR sculpt semantics changes
- No TUHO / Oborovo factory path
  changes (hidden ≠ deleted)
- No Excel goldens changes
- No tax / depreciation / IDC changes
- No construction / C10 / R-PAR changes
- No `manual_gearing` / `gearing_cap` /
  `min(gearing cap, sculpt)` blend
- No R99 / R102 / G20 promotion
- No persistence schema migration
- No `static/app.js` changes
- No Tailwind / Alpine / React / Vue /
  Svelte
- No Chart.js / Plotly / D3
- No new dependency
- No JS calc
- `use_construction_schedule_engine`
  remains False
- rc1 SHA preserved

## Roadmap (post-PR1)

PR1 is the first PR in the P2-min
stacked UX simplification arc:

1. **PR1** (this PR) — Project Home +
   Minimal New Project
2. **PR2** — Hide Internal Vocabulary
   (depends on PR1)
3. **PR3** — Dashboard v1 (depends on
   PR2)
4. **PR4** — Navigation Compression
   (depends on PR3)

`manual_gearing` is **not** on this
roadmap.

DO NOT START: PR2 until PR1 is approved
and merged. DO NOT START: M2, pilot
execution, persistence changes, scenario
override implementation.

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do
NOT merge. Awaiting user review and
explicit go-ahead before PR1 lands on
main.
