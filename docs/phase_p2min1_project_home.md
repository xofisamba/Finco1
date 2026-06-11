# Phase P2-min-1 — Project Home + Minimal New Project — Governance Doc

## Status

- **Type:** Presentation / UX entry point
  (presentation-only; no model / formula
  / factory / persistence change).
- **Branch:** `p2-min-1-project-home-minimal-new-project`
- **Base:** main @ `e1ad5db` (post-PR3
  merge, PR #608)
- **PR:** DRAFT only. Do NOT mark ready.
  Do NOT merge. Awaiting user review.

## Goal

First screen should feel like a product,
not an internal modelling laboratory.

Normal users should not land on Factory
Templates, TUHO, Oborovo, baselines, or
internal-vocabulary labels.

The Streamlit prototype review confirmed
that users respond well to: KPI cards
first, charts first, compact inputs,
project-oriented workflow. P2-min-1 is
the first step in the P2-min stacked
simplification arc that ports this
information design.

## What changed

### Project Home partial (new)

- `app/templates/partials/project_home.html`
  (NEW) — product-shaped first screen
  with: My projects (user-created
  projects only) + a single
  "Create New Project" CTA. No factory
  templates, no baselines, no TUHO, no
  Oborovo. The internal vocabulary
  cleanup (factory / baseline / parity /
  calibration / G20 / R99 / R102 /
  runtime-source labels) is deferred to
  PR2.

### Minimal New Project form (new)

- `app/templates/partials/new_project_minimal.html`
  (NEW) — exactly 4 visible input
  fields: Project name, Technology,
  Country or market, Capacity (MW). All
  other driver values come from template
  defaults via the existing
  `/projects/new/defaults` endpoint
  (PR25B-1). The form posts to the
  existing `/projects/create` endpoint
  (no backend / no persistence change).
  The hidden `template_source` field is
  auto-populated server-side to
  `generic_solar` (the canonical default
  template source for the minimal flow).

### Help placement

- `app/templates/base.html` (MODIFIED) —
  a small Help link (icon, not a sixth
  top-level tab) is added to the site
  header. PR1 adds the link, not a
  dedicated tab.

### Sidebar Home action

- `app/templates/partials/project_selector.html`
  (MODIFIED) — a Home action button
  (icon ⌂ + label "Home") is added
  before "New project" in the sidebar
  quick actions. The button loads
  `/home` via htmx into the
  `#panel-overview` target.

### Route handlers (presentation only)

- `main_web.py` (MODIFIED) — new
  presentation-only routes:
  - `GET /home` (project home partial)
  - `GET /projects/new/minimal` (minimal
    new-project partial)
- No business logic, no factory change,
  no model change, no persistence
  change.

### CSS (presentation only)

- `static/styles.css` (MODIFIED) — small
  Project Home CSS block (`.ph-section`,
  `.ph-grid`, `.ph-card`, `.ph-empty`,
  `.ph-actions`, `.ph-cta`,
  `.header-help-link`). Reuses the
  existing `--surface` / `--border` /
  `--primary` / `--text` / `--text-2`
  CSS variables. No new dependency.

## Hidden ≠ deleted rule

The factory templates (TUHO, Oborovo)
remain:

- in `FACTORY_TEMPLATE_OPTIONS` (UI
  options list)
- in `create_default_tuho_wind1()` /
  `create_default_oborovo()` factory
  functions
- reachable from `/projects/browse`
  (the audit / parity fixture reach
  point)
- covered by the parity guardrails
  test (Phase 51F)
- covered by the S1 exact-equality
  test (TUHO / Oborovo factory paths
  preserved bit-exact)

The Presentation filter only hides
TUHO / Oborovo from the Project Home
entry point. They are not deleted.

## PR1 timing-field fix preserved

PR1 (form timing fields) extended
`_build_schema_from_form` with four
new optional kwargs: `cod_date`,
`construction_months`, `horizon_years`,
`ppa_term_years_form`. The minimal
form posts to the same
`/projects/create` endpoint that PR1
preserves. The timing-field fix is
verified by
`TestTimingFieldFixPreserved::test_build_schema_from_form_still_has_timing_kwargs`.

## What did NOT change (pinned by tests)

- No formula changes
- No debt sizing changes
- No DSCR sculpt semantics changes
- No TUHO / Oborovo factory path
  changes (`app/project_factories.py`
  SHA verified)
- No Excel goldens changes
  (`app/excel_export.py` SHA verified)
- No tax / depreciation / IDC changes
- No construction / C10 / R-PAR changes
- No `manual_gearing` / `gearing_cap` /
  `min(gearing cap, sculpt)` blend
- No R99 / R102 / G20 promotion
- No persistence schema migration
- No `app/services/` downstream
  service code changes
- No `app/persistence/` changes
- No `static/app.js` changes
- No `main_api.py` changes
- No Tailwind / Alpine / React / Vue /
  Svelte
- No Chart.js / Plotly / D3
- No new dependency
- No JS calc
- `use_construction_schedule_engine`
  remains False
- rc1 SHA
  `b425a0708719eaa5e1d922b1008e5609758e0ad4`
  preserved

## Files in PR1 (8)

- `app/templates/partials/project_home.html`
  (NEW)
- `app/templates/partials/new_project_minimal.html`
  (NEW)
- `app/templates/partials/project_selector.html`
  (MODIFIED)
- `app/templates/base.html` (MODIFIED)
- `static/styles.css` (MODIFIED)
- `main_web.py` (MODIFIED)
- `tests/test_phase_p2min1_project_home.py`
  (NEW) — 8 test classes, 16 tests
- Cross-arc test patches (M1, PR1, PR2,
  PR3) — file-scope allowlist extensions

## Test results

- **16 / 16 PR1 tests PASS**
- **327 / 327** cross-arc tests (PR1 +
  PR2 + PR3 + M1 + P1-A + P1-B + Phase
  51F parity + P2-min-1)
- **21 / 21** Phase 51F parity
  guardrails PASS (no model change)
- rc1 SHA preserved
- `use_construction_schedule_engine`
  remains False
- 0 failed
- 5/5 GitHub CI jobs GREEN

## Hard no-go (preserved, all pinned by tests)

- No formula / debt sizing / DSCR sculpt
  changes
- No TUHO / Oborovo factory path
  changes (hidden ≠ deleted)
- No Excel goldens changes
- No tax / depreciation / IDC changes
- No construction / C10 / R-PAR changes
- No `manual_gearing` / `gearing_cap` /
  `min(gearing cap, sculpt)` blend
- No R99 / R102 / G20 promotion
- No persistence schema migration
- No `app/services/` (downstream
  service code) changes
- No `app/persistence/` changes
- No `static/app.js` changes
- No `main_api.py` changes
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
stacked UX simplification arc.
The next PRs (PR2, PR3, PR4) build
on PR1. The dependency chain is:

- PR1 (this PR) — Project Home +
  Minimal New Project
- PR2 — Hide Internal Vocabulary
  (depends on PR1)
- PR3 — Dashboard v1 (depends on PR2)
- PR4 — Navigation Compression
  (depends on PR3)

`manual_gearing` is **not** on this
roadmap.

DO NOT START: PR2 until PR1 is
approved and merged. DO NOT START: M2,
pilot execution, persistence changes,
scenario override implementation.

## Stop-after-report contract

DRAFT PR only. Do NOT mark ready. Do
NOT merge. Awaiting user review and
explicit go-ahead before PR1 lands on
main.
