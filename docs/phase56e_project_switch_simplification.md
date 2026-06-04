# Phase 56E — Project switch simplification

## Goal

Simplify the active project card and project switching so the
sidebar feels like product navigation, not internal/debug
navigation. From the user feedback captured in Phase 56A:

- The project code / slug is shown too prominently.
- The New Project button is tucked away / not clearly part of
  the workflow.
- Project switching should be easier and clearer.
- The user should quickly understand: current active project;
  current project type/source; how to switch project; how to
  create a new project.

This is a runtime UI change, draft-only. User visual review is
required before merge.

## Scope of changes

### Templates

`app/templates/partials/project_selector.html` — the sidebar
project card is simplified:

| Element | Before | After |
|---|---|---|
| Primary visible label | project_name (font 0.85rem) | project_name (font **0.95rem**, larger) |
| Technology badge | top, separate line | inline in `.ps-ap-meta-row` |
| Project code / slug | always visible, debug-like | hidden by default; revealed via `<details>` "Details" disclosure |
| Project origin | not shown | shown as compact pill (`Reference` / `My project` / `Saved baseline`) |
| Active scenario | small text | labeled (`Scenario: <name>`) |
| Switch button | "Load / Switch" with ⎘ icon | "Switch project" with ⇄ icon, secondary style |
| New project button | below Switch, ghost style | **first**, primary style (`ps-action-btn--primary`) |
| Empty state | "Use Load to open a project" | "Choose an existing project or create a new one." |

`app/templates/partials/project_browser.html` — left as-is. The
browser already has a clean product-style card layout (Factory
Templates / Saved Baselines / My Projects tabs) and does not need
the same visual simplification as the sidebar. The browser
remains htmx-loaded into `#project-browser-container` when the
user clicks "Switch project".

### CSS (additive only)

`static/styles.css` — append a new section "Phase 56E: Project
switch visual hierarchy" defining:

- `.ps-ap-name` override (larger, primary label)
- `.ps-ap-meta-row` (inline row for type + origin)
- `.ps-ap-origin` + 3 origin variants (`.ps-ap-origin--factory`,
  `.ps-ap-origin--user`, `.ps-ap-origin--baseline`)
- `.ps-ap-empty-hint` (empty state hint)
- `.ps-ap-details` + `summary` + `body` + `label` + `code`
  (project code disclosure)
- `.ps-ap-scenario-label` (small "Scenario" label)
- `.ps-action-btn--primary` (primary action style)
- `.ps-action-label` (action button label)

No `:root` variables added or modified (count remains 5).

### No changes to

- `static/app.js`
- `app/main_web.py`
- `app/waterfall_core.py`
- `app/project_factories.py`
- `app/runtime_impact_taxonomy.py`
- `app/persistence/*`
- `app/services/*`
- `app/templates/partials/project_browser.html` (intentionally
  preserved; the browser already has a clean product-style layout)
- `app/templates/partials/workspace_shell.html`
- `app/templates/partials/workspace_tabs.html`
- `app/templates/index.html`
- Any test fixtures, schema, or migration

## Project origin pill wording

The origin pill uses **product-neutral** wording:

| `project_origin` value | Pill label |
|---|---|
| `factory_template` | `Reference` |
| `user_created` | `My project` |
| `saved_baseline` | `Saved baseline` |

This is consistent with the 56B rephrasing of "Validated" →
"Reference" / "parity evidence". No positive "validated" / "lender-
ready" / etc. claims are introduced.

## Behavior preservation

- **All existing endpoints preserved**: `/projects/browse`,
  `/projects/new`, htmx attributes (`hx-get`, `hx-target`,
  `hx-swap`) all unchanged.
- **All existing JS functions preserved**: `openProjectBrowser()`,
  `closeProjectBrowser()`, `switchToProject()` are still in
  `project_selector.html` (the project_selector owns its own JS).
- **Phase 56B / 56C / 56D preserved**: Help tab, v1 New Project
  form, COD readonly, derived COD all intact.
- **No backend changes**: the partial still reads
  `project_record.project_name`, `project_record.project_type`,
  `project_record.project_code`, `project_record.project_origin`,
  `workspace_state.active_scenario_name` — same fields as
  before.

## Hard gates verified

- Only allowed template/CSS files modified (project_selector.html
  + styles.css)
- No backend/service/persistence/model changes
- No `static/app.js` changes (JS in project_selector.html is
  preserved verbatim — 0 changes)
- No `runtime_impact_taxonomy.py` changes
- No `:root` CSS variable changes (count remains 5)
- No new forbidden UI claims (11 forbidden terms checked)
- No financial formula / model output changes
- No schema/migration changes
- No new persistence writes
- rc1 (`b425a0708719eaa5e1d922b1008e5609758e0ad4`) untouched
- Draft-only — does not auto-merge
- 68 new tests added (`tests/test_phase56e_project_switch_simplification.py`)
- 962 relevant tests pass total (68 new 56E + 894 51-56A-D + UI-2)
- 56B / 56C / 56D tests still pass (Help, v1 form, COD derivation,
  COD readonly, derived COD wins over manual)

## Test coverage

`tests/test_phase56e_project_switch_simplification.py` covers:

1. `TestActiveProjectNamePrimary` — `.ps-ap-name` is the first /
   largest visible label, font >= 0.9rem
2. `TestProjectCodeNotPrimary` — project code is inside a
   `<details>` disclosure (not a primary line), `<details>` is NOT
   `open` by default
3. `TestSwitchProjectControl` — Switch project button preserved
   with correct label, htmx attributes, and `openProjectBrowser()`
   call
4. `TestNewProjectControlDiscoverable` — New project button is
   first in the quick-actions block, has
   `ps-action-btn--primary` class, preserves htmx attributes
5. `TestExistingEndpointsPreserved` — `/projects/browse` and
   `/projects/new` endpoints still referenced
6. `TestProjectOriginPill` — 3 origin variants defined
   (factory/user/baseline), wording is product-neutral
7. `TestTechnologyBadgePreserved` — `.ps-ap-badge` + Wind/Solar
   variants
8. `TestEmptyStateImprovement` — empty state has a helpful hint
   pointing to the actions
9. `TestCSSAdditive` — 14 new CSS selectors added; `:root` count
   remains 5
10. `TestScopeGuardrails` — `app.js`, `waterfall_core.py`,
    `project_factories.py`, `runtime_impact_taxonomy.py`,
    `persistence/*`, `services/*`, `main_web.py` all unchanged
11. `TestRc1Untouched` — rc1 SHA constant stable
12. `TestPreviousPhasesPreserved` — 56B Help tab + help-pointer,
    56C v1 form fields, 56D COD readonly
13. `TestNoGoCopyInProjectSelector` — 11 forbidden terms absent
    from `project_selector.html` and `project_browser.html`

## Manual visual review checklist

When reviewing the running app, please verify:

- [ ] The active project card shows the project **name** as the
      first / largest label
- [ ] The project code / slug is **not visible** by default
- [ ] Clicking "Details" reveals the project code
- [ ] The technology badge (Solar / Wind) is shown next to the
      project name
- [ ] The origin pill (`Reference` / `My project` / `Saved
      baseline`) is shown when applicable
- [ ] The active scenario name is shown with a "Scenario" label
- [ ] "New project" button is the **first** action and visually
      primary
- [ ] "Switch project" button is the **second** action
- [ ] Clicking "Switch project" opens the Project Browser
      (Factory Templates / Saved Baselines / My Projects)
- [ ] Clicking "New project" opens the v1 inline form
- [ ] All 56B / 56C / 56D behavior preserved (Help tab, v1 form,
      COD readonly, derived COD)
- [ ] No console errors / no JS errors / no network 404s

## Files changed (summary)

| File | Change | Lines |
|---|---|---|
| `app/templates/partials/project_selector.html` | Active project card simplified; project code moved to `<details>` disclosure; origin pill added; "New project" promoted to primary action; button labels updated to product wording | +60 / -25 |
| `static/styles.css` | Appended Phase 56E section: 14 new selectors, 0 `:root` changes | +115 / -0 |
| `tests/test_phase56e_project_switch_simplification.py` | New tests | +650 (new file) |
| `docs/phase56e_project_switch_simplification.md` | New doc | (this file) |
| `reports/phase56e_project_switch_simplification.json` | New report | (new file) |

## Stack: 56E → 56F → 56G

This PR is the **first** in the 56E → 56F → 56G UX cleanup
sequence. It is based on `main` (post-56B + 56C + 56D). **56E can
be reviewed and merged independently** of 56F and 56G. 56F/56G
will be stacked on top after 56E is approved.
