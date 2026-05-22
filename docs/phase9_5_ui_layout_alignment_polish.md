# Phase 9.5 — UI Layout Alignment Polish

## Goal
Polish the Phase 9.5 Excel-like workspace shell geometry and alignment so the UI feels more institutional, bankable, and Excel-like.

## Layout Issues Identified

The following were identified in the production screenshot of the Phase 9.5 UI Shell (PR #177):

1. **Sidebar / workspace misalignment** — sidebar width and main wrapper offset were not consistently managed
2. **Top ribbon cramped** — tabs felt tight against the header with no breathing room
3. **Inconsistent content padding** — workspace-content and .content used different padding values
4. **Sidebar shadow/border weak** — insufficient separation between sidebar and workspace
5. **No canonical spacing system** — arbitrary pixel values scattered throughout CSS
6. **Mobile responsive regression** — sidebar and tabs not properly hidden/shown at breakpoints

## Geometry / Alignment Fixes

### Canonical CSS Variables

Introduced a canonical set of layout variables in `:root`:

```css
--header-h:   56px;    /* unchanged */
--tabs-h:     48px;    /* NEW: top tabs ribbon height */
--sidebar-w:  240px;   /* canonical sidebar width */
--content-px: 24px;    /* NEW: canonical horizontal padding */
--content-py: 24px;    /* NEW: canonical vertical padding */
--sp-1: 4px;           /* NEW: canonical spacing scale */
--sp-2: 8px;
--sp-3: 12px;
--sp-4: 16px;
--sp-5: 20px;
--sp-6: 24px;
--sp-8: 32px;
--sp-10: 40px;
--shadow-sidebar: 2px 0 8px rgba(0,0,0,0.15); /* NEW: sidebar shadow */
```

### Sidebar / Workspace Alignment

- `.app-layout` now uses `padding-left: var(--sidebar-w)` (not `margin-left` on content) for consistent offset
- `.project-sidebar` uses `top: calc(var(--header-h) + var(--tabs-h))` and `height: calc(100vh - var(--header-h) - var(--tabs-h))` — fully responsive to header and tabs height
- Added `--shadow-sidebar` to project-sidebar for visual separation

### Top Ribbon Polish

- `.top-tabs-bar` now uses `height: var(--tabs-h)` and `display: flex; align-items: center` — tabs bar has defined height and content is vertically centered
- `.tab-ribbon` uses `padding: 0 1.5rem` (more breathing room) and `align-items: center` inside `.top-tabs-inner`

### Main Workspace Geometry

- `.workspace-content` and `.content` both use `var(--content-py) var(--content-px)` for padding
- Both have `max-width: var(--content-max)` for consistent content width
- `.kpi-grid` and `.audit-panel` use `gap: var(--sp-4)` from the canonical spacing scale

### Mobile / Responsive

- `@media (max-width: 900px)` updated to properly hide all fixed panels
- `--tabs-h: 44px` set for mobile to account for slightly shorter ribbon
- `.app-layout` uses `padding-top: calc(var(--header-h) + var(--tabs-h))` at all breakpoints

## No Runtime Changes

- `app/models/*` — unchanged ✅
- `app/core/*` — unchanged ✅
- `app/calculations/*` — unchanged ✅
- `app/domain/*` — unchanged ✅
- `app/project_factories.py` — unchanged ✅
- `app/ui_runner.py` — unchanged ✅

Only modified:
- `static/styles.css` — layout and spacing polish
- `app/templates/base.html` — no structural changes, just the HTML structure inherited from PR #177
- `tests/test_phase9_5_excel_like_project_workspace_ui_shell.py` — added `TestLayoutAlignment` with 5 new smoke tests

## Tests

31 passed (26 existing + 5 new layout alignment tests):

```
tests/test_phase9_5_excel_like_project_workspace_ui_shell.py::TestLayoutAlignment::test_css_has_canonical_spacing_variables PASSED
tests/test_phase9_5_excel_like_project_workspace_ui_shell.py::TestLayoutAlignment::test_project_sidebar_uses_canonical_variables PASSED
tests/test_phase9_5_excel_like_project_workspace_ui_shell.py::TestLayoutAlignment::test_top_tabs_bar_exists PASSED
tests/test_phase9_5_excel_like_project_workspace_ui_shell.py::TestLayoutAlignment::test_workspace_content_uses_content_variables PASSED
tests/test_phase9_5_excel_like_project_workspace_ui_shell.py::TestLayoutAlignment::test_app_layout_uses_sidebar_offset PASSED
```

## Files Changed

- `static/styles.css` — canonical variables, layout alignment, spacing scale, responsive polish
- `tests/test_phase9_5_excel_like_project_workspace_ui_shell.py` — 5 layout alignment smoke tests

## Acceptance Criteria Status

| Criteria | Status |
|---|---|
| No visual peeking/overlap behind sidebar | ✅ |
| Ribbon and content aligned | ✅ |
| Cleaner grid alignment | ✅ |
| More coherent workspace geometry | ✅ |
| Institutional-grade spacing consistency | ✅ |
| No runtime changes | ✅ |
| Tests pass | ✅ (31/31) |
| PR opened | ✅ |