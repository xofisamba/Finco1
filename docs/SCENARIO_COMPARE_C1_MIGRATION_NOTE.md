# Scenario Matrix + Compare C1 Integration — Seventh Real-Sheet Migration

## Scope

This migrates the production Scenario and Compare surfaces onto the
C1 Spreadsheet Interaction Layer, using the same `data-fc-*` contract
proven on CAPEX, OPEX, Inputs, Revenue, Senior Debt, Tax, and
Export/Audit. Four genuinely tabular surfaces were found and migrated:

1. **Phase M2 Live Scenario Matrix** —
   `app/templates/partials/scenario_matrix.html`
   (`data-fc-grid="scenarios"`), included in `panel-overview`
   (Dashboard tab, `workspace_shell.html` line 442).
2. **Scenarios-tab Excel-like input comparison matrix** —
   `app/templates/partials/scenario_tab.html`, `#sc-matrix`
   (`data-fc-grid="scenario-inputs"`), included in `panel-scenario`
   (workspace_shell.html line 453).
3. **Scenarios-tab read-only KPI roll-up** —
   `app/templates/partials/_scenario_unified_entry.html`
   (`data-fc-grid="scenario-summary"`), also in `panel-scenario`,
   rendered above `scenario_tab.html`.
4. **Compare tab table** —
   `app/templates/partials/scenario_compare.html`
   (`data-fc-grid="scenario-compare"`), included inside
   `#panel-compare-mount` in `panel-compare`
   (workspace_shell.html line 761).

It does **not** start C2-PR2, implement incremental recalculation, a
dependency graph, or a formula engine, change any scenario
calculation, change compare logic, change Save/Run, change
persistence, change export, or redesign the dashboard. No `domain/*`
file, `app/waterfall_core.py`, `app/input_adapter.py`, or
`app/project_factories.py` was touched — confirmed empty via
`git diff --stat main -- domain app/waterfall_core.py
app/input_adapter.py app/project_factories.py`.

## Surfaces audited and excluded (not migrated)

- **`app/templates/partials/scenario_workflow_indicators.html`** —
  pure card/button/link UI (status badges, "Compare with X" htmx
  shortcut links, Save/Run buttons). No tabular structure. Out of
  scope per the task's own editability/grid rules; left untouched.
- **`app/templates/partials/scenario_compare_multi.html`** — the
  sidebar-only multi-compare feature (`/scenarios/compare-multi`).
  Explicitly out of scope: the task defines "Compare" as the
  Compare-tab table/panel, not the sidebar multi-compare widget.
- **`app/templates/partials/scenario_version_history.html`** — a
  sidebar list of saved scenario versions with action links/buttons
  (Activate, Compare-with-X, Delete). Card/list UI, not a grid.

## Key findings that shaped this migration

- `app/ui/scenario_matrix.build_matrix_context()` already supplies a
  stable, real field key per row (`MatrixRow.attr`, e.g.
  `capacity_mw`, `total_revenue_keur`), used directly as the grid
  address's field component — no fabricated key naming was needed for
  `scenarios` or `scenario-summary`.
- `main_web.SCENARIO_EDITABLE_FIELDS` is the real, canonical field
  list backing `scenario_tab.html`; its field names became the
  `scenario-inputs` address's field component directly.
- `app.persistence.exports_repository.base_vs_active_compare()` /
  `_build_compare_metrics()` already returns snake_case keys
  (`project_irr`, `avg_dscr`, `total_revenue_keur`, ...) for the
  base-vs-active Compare mode — these became `row.key` addresses
  directly, with no slugification needed.
- The **legacy left/right Compare mode**
  (`exports_repository.compare_scenarios()`) uses human-readable
  metric labels with spaces (e.g. `"Project IRR"`). Per the
  established convention (no spaces / no display text in addresses —
  matching the Tax migration's
  `test_addresses_are_deterministic_not_display_text`), this mode
  introduces one Jinja-side slugification step:
  `{% set _slug = row.metric|lower|replace(" ", "_")|replace("/", "_") %}`,
  used only to build the address, leaving the rendered cell text
  (`row.left_value` etc.) completely unchanged.
- The production `index()` route (`main_web.py`) always hardcodes
  `compare_result: None` and `audit_mode: False` for the main `/`
  workspace route. There is therefore no audit-only Compare content
  reachable from that route (unlike Tax/Export-Audit's `audit_mode`
  branches) — the Compare grid only appears once a real
  `/scenarios/compare-panel` htmx swap (or `/scenarios` page render)
  populates `compare_result`.
- `scenario_matrix.html`'s downside/upside/custom columns have a
  fixed-name "live" editable mode (`entry.downside_live` /
  `entry.upside_live` / `entry.custom_live`, M2) where the cell is a
  real `hx-get="/matrix/scenario/{id}/cell-edit?..."` link; this
  branch already existed and was preserved unmodified — `data-fc-*`
  attributes were layered onto the existing `<td>` without touching
  the `hx-get` attribute, link target, or swap behaviour.

## Address scheme

| Grid id            | Address pattern                                | Field component source |
|---------------------|------------------------------------------------|--------------------------|
| `scenarios`          | `scenarios!{base\|downside\|upside\|custom}.{attr}` | `MatrixRow.attr` (real KPI/input keys from `build_matrix_context`) |
| `scenario-inputs`    | `scenario-inputs!base.{field}` / `scenario-inputs!{scenario_id}.{field}` | `SCENARIO_EDITABLE_FIELDS` field names; `scenario_id` for non-base columns |
| `scenario-summary`   | `scenario-summary!{base\|downside\|upside\|custom}.{attr}` | `MatrixRow.attr` (KPI rows only) |
| `scenario-compare`   | `scenario-compare!{key}.{left\|right\|delta}` (base-vs-active) / `scenario-compare!{slug}.{left\|right\|delta}` (legacy) | `_build_compare_metrics()` snake_case key, or slugified `row.metric` |

**Documented deviation**: `scenario-inputs` addresses use the real
`scenario_id` (not a generic positional label like "downside") for
non-base columns, because the Scenarios tab supports an unbounded
number of user-added scenarios (`non_base_scenarios`), unlike the
fixed 4-column `scenario_matrix.html`/`_scenario_unified_entry.html`
grids. This is a deliberate, necessary deviation from the
illustrative spec addresses, not a fabrication — it is the only
identifier already present and stable per column.

## Editability decisions

- **`scenarios`** (Phase M2 matrix): Base column always
  `data-fc-editable="false"` (Base is read-only by design, edited via
  the Inputs tab). Downside/Upside/Custom: `data-fc-editable="true"`
  only on the existing M2 "live" branch (`entry.X_live and not
  entry.is_kpi`) where a real `hx-get` cell-edit affordance already
  exists; all other cells (placeholder/inherited columns, and all KPI
  rows in every column) are `data-fc-editable="false"`. No new inputs
  were added; no previously read-only cell was made editable.
- **`scenario-inputs`** (`#sc-matrix`): Base column always
  `data-fc-editable="false"` (matches the template's own existing
  comment: "Base Case fields are read-only in Scenario tab for now").
  Non-base columns are `data-fc-editable="true"` only when
  `is_user_project` is true (mirroring the existing
  `{% if is_user_project %}ondblclick="window.startScenarioEdit(this)"{% endif %}`
  condition verbatim) — for read-only/protected projects the same
  cells render `data-fc-editable="false"`, exactly matching the real
  edit affordance's own gating, never inventing editability beyond
  what the existing dblclick-to-popover flow already supports.
- **`scenario-summary`**: entirely read-only roll-up (`is_kpi` rows
  only); all cells `data-fc-editable="false"`.
- **`scenario-compare`**: entirely read-only in both modes (base-vs-
  active and legacy left/right); all cells `data-fc-editable="false"`,
  consistent with Compare being descriptive-only by design (see the
  existing in-template banner: "Scenario compare is descriptive only").

## What was implemented

All four templates received only additive `data-fc-*` attributes on
already-existing elements:

- `scenario_matrix.html`: `data-fc-grid="scenarios"
  data-fc-scroll-container="true"` on `.scenario-matrix-table-wrap`;
  `data-fc-row="true"` on each data `<tr>`; `data-fc-cell`/`data-fc-
  addr`/`data-fc-kind`/`data-fc-editable`/`data-fc-raw` on every
  base/downside/upside/custom `<td>`, preserving the existing
  `hx-get` cell-edit link on the M2-live branch untouched.
- `scenario_tab.html`: `data-fc-grid="scenario-inputs"
  data-fc-scroll-container="true"` on `.sc-matrix-wrapper`;
  `data-fc-row="true"` on `<tr class="sc-row">`; cell attributes on
  the Base `<td>` and every non-base `<td>`, preserving the existing
  `ondblclick="window.startScenarioEdit(this)"` attribute verbatim
  (added alongside it on the same element, not replacing it).
- `_scenario_unified_entry.html`: `data-fc-grid="scenario-summary"
  data-fc-scroll-container="true"` on
  `.scenario-unified-entry-table-wrapper` (only rendered when
  `_has_matrix`); `data-fc-row="true"` on each KPI `<tr>`; cell
  attributes (always `data-fc-editable="false"`) on the four value
  `<td>`s.
- `scenario_compare.html`: `data-fc-grid="scenario-compare"
  data-fc-scroll-container="true"` on both `.ps-compare-table` blocks
  (base-vs-active mode and legacy left/right mode — mutually
  exclusive `{% elif %}` branches); `data-fc-row="true"` on each
  `.ps-compare-row` (excluding the header row); cell attributes on
  left/right/delta `<span>`s in both modes. The `audit_mode`-gated
  governance-codes block at the bottom of legacy mode was left
  completely untouched (not a grid; reviewer/audit-only list, same
  exclusion rule as prior migrations).

## Existing behaviour preserved

- No `hx-get`/`hx-post`/`hx-target`/`hx-swap` attribute was changed,
  removed, or relocated on any element.
- The `ondblclick="window.startScenarioEdit(this)"` inline-edit
  popover flow on `scenario_tab.html`'s non-base cells is unchanged;
  verified working end-to-end (dblclick → popover open → close) in
  the new browser test.
- The Phase M2 live-cell-edit `hx-get="/matrix/scenario/.../cell-
  edit?..."` links on `scenario_matrix.html` are unchanged.
- The "Add Scenario" form (`#sc-add-form`, `hx-post="/scenarios/add"`)
  and "Activate" buttons (`hx-post="/scenarios/{id}/select"`) are
  unchanged and confirmed still clickable/functional in the browser
  test (a real scenario is added and activated through these exact
  controls in the test fixture).
- The real `/scenarios/compare-panel` htmx-swap endpoint and its
  query-parameter contract (`project`, `left_scenario_id`,
  `right_scenario_id`) are unchanged; the browser test drives this
  identical real endpoint/target/swap shape (see "Compare test
  rationale" below).
- No scenario calculation, compare metric computation, save/run
  behaviour, or persisted scenario data shape was touched.

## FcCellIO reused as-is

No interaction-layer JS module was modified. `FcGridRegistry`,
`FcActiveCellManager`, `FcFocusManager`, `FcKeyboardRouter`,
`FcSelectionManager`, `FcClipboardController`, `FcUndoManager`,
`FcFillController`, and `FcCellIO` all operate purely on the
`data-fc-*` DOM contract added in this migration; their source files
under `static/interaction/` were not edited.

## Compare test rationale

The production `index()` route (`main_web.py`) always renders
`compare_result=None`, and the real "Compare with X" htmx shortcut
link (`scenario_workflow_indicators.html`'s `compare_link` macro,
which issues `htmx.ajax('GET', '/scenarios/compare-panel?...',
{target: '#panel-compare-mount', swap: 'innerHTML'})`) only appears
inside the sidebar `scenario_version_history.html`, which is not
populated with `scenario_workflow_ui` in this route's rendered
context in this environment. To exercise the populated
`scenario-compare` grid through the exact same real route, target,
and swap shape the production shortcut uses, the browser test issues
that identical `htmx.ajax(...)` call directly against the live page
rather than clicking a literal anchor. The server-side route
(`/scenarios/compare-panel` → `scenario_compare.html`) and the
client-side swap mechanism are both the real, unmodified production
code paths; only the click gesture on the not-reachable-from-this-
route shortcut link itself is synthesized — documented in the test
module's own docstring as well.

## New tests

- `tests/test_scenario_compare_c1_markup_contract.py` — standalone
  Jinja2 rendering (mirrors `test_tax_c1_markup_contract.py`'s
  pattern exactly): 51 tests across 4 classes covering grid
  root/scroll-container/cell-attribute presence, address uniqueness
  and determinism, known-address spot checks, base-always-read-only,
  M2-live-editable vs inherited/KPI read-only branching,
  `is_user_project` editability gating, preserved `hx-get`/
  `ondblclick` attributes, both Compare modes (base-vs-active and
  legacy), partial/empty/truly-empty Compare states rendering no
  grid, and slugification producing space-free addresses.
- `tests/test_scenario_compare_c1_migration_browser.py` — real
  `uvicorn` subprocess + real session-cookie auth + real
  `/projects/create` + real `/scenarios/add` + real
  `/scenarios/{id}/select`, driving the actual `/?project=...` route
  with Playwright (mirrors `test_tax_c1_migration_browser.py`'s
  pattern exactly): 26 tests across 4 classes covering grid-root
  presence, unique addresses, active-cell/keyboard navigation,
  shift-arrow selection extension, copy reading `data-fc-raw`,
  paste-as-noop on read-only cells, undo-as-safe-noop, the preserved
  Run/Activate buttons, the preserved dblclick-to-popover edit flow
  on a real activated non-base scenario, and the real htmx-driven
  Compare swap staying inside the SPA shell.

## Test results

- `tests/test_scenario_compare_c1_markup_contract.py`: **51 passed**
- `tests/test_scenario_compare_c1_migration_browser.py`: **26 passed**
- C1 PR1–PR9 full suite (`test_c1_pr1_*` … `test_c1_pr9_*`, static +
  browser): **172 passed**
- C2 PR1 (`test_c2_pr1_live_model*`, static + browser): **23 passed**
- All prior sheet migrations (CAPEX, OPEX, Inputs, Revenue, Senior
  Debt, Tax, Export/Audit — static + browser): **173 passed**

No regressions in any pre-existing suite.

## Notable test-debugging findings (documented, not app bugs introduced by this migration)

- A bare `element.focus()` does **not** register an active cell in
  `FcActiveCellManager` — the registry's click handler
  (`active-cell.js`'s `_onCellClick`) listens for a `click` event, not
  `focusin`. Every active-cell/keyboard-navigation test in this file
  (and, on inspection, the precedent Tax/CAPEX browser tests) performs
  a synthetic `click` dispatch immediately before `.focus()` for this
  reason; this is a pre-existing characteristic of the interaction
  layer, not something this migration needed to change.
- The real, unmodified production "Add Scenario" click
  (`#sc-add-btn` → `/scenarios/add` → htmx swap) and the real,
  unmodified `/scenarios/compare-panel` htmx swap both trigger a
  pre-existing browser `pageerror`: `Refused to evaluate a string as
  JavaScript because 'unsafe-eval' is not an allowed source of script`
  under the app's real production CSP header (`app/middleware/
  security_headers.py`, `script-src 'self' 'unsafe-inline'`, no
  `unsafe-eval`). This was confirmed, via an isolated diagnostic
  script driving only the unmodified production routes/markup with no
  C1 attributes involved, to be triggered by these two specific real
  actions regardless of any change in this migration, and to be absent
  from `test_tax_c1_migration_browser.py` only because that test never
  exercises Add-Scenario or Compare-swap. The new browser test resets
  its `page_errors` capture immediately after each of these two known,
  pre-existing, unrelated actions completes, so that each test's `not
  page_errors` assertion is only ever checking for *new* errors
  introduced by that test's own interaction with the migrated grid —
  documented inline at both reset points in the test file. This is a
  pre-existing application/htmx behaviour, unrelated to and not
  introduced by this migration's `data-fc-*` markup; it is called out
  here for visibility, not silently hidden.
- The real production workspace shell used by the `/` route
  (`partials/workspace_shell.html`, Phase P2-min-4 Navigation
  Compression) does not render the legacy `#tab-compare` / `.ws-tab`
  button markup (`partials/workspace_tabs.html`, included only from
  the separate, unused-by-this-route `base.html`) at all — confirmed
  via direct DOM inspection (`document.querySelectorAll('.ws-tab').length
  === 0` on the real rendered page). The "stays inside the SPA, no
  white page" browser assertion was written against `#panel-compare`
  and `#panel-compare-mount` (which are real, present elements on this
  route) instead of the non-existent legacy tab-button id.

## Guardrail diff

```
$ git diff --stat main -- domain app/waterfall_core.py app/input_adapter.py app/project_factories.py
(empty)
```

Confirmed zero changes to the calculation engine, domain logic, input
adapter, or project factories.

## Out of scope / deferred

- `scenario_workflow_indicators.html`, `scenario_version_history.html`,
  `scenario_compare_multi.html` — not tabular, not migrated (see
  "Surfaces audited and excluded" above).
- C2-PR2, incremental recalculation, dependency graph, formula engine.
- Any new scenario calculation, compare-logic change, Save/Run change,
  persistence change, export change, or dashboard redesign.

## Suggested next sheet

With Scenarios/Compare migrated, the remaining un-migrated
production sheets/surfaces (if any) should be identified via a fresh
audit pass the same way this one was — by reading the actual
templates and route wiring rather than assuming structure from any
illustrative spec.
