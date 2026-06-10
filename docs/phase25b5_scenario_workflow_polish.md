# Phase 25B-5 — Scenario Workflow Polish

## Goal

Make the Base / Downside / Upside workflow obvious for a first-time
finance user. The data model is unchanged — this phase is a pure UI
polish over the existing scenario list.

## What was already there

- Scenario cards in `app/templates/partials/scenario_version_history.html`
  (added in Phase 33) show the scenario name + active badge + IRR.
- A `svh-card--active` class is applied to the active card, but had
  **no CSS rules** (a leftover from the original Phase 33 — the
  active highlight was effectively invisible).
- An "explainer" block at the bottom of the scenario list already
  documents the draft / saved / runtime semantics.

## What 25B-5 adds

### 1. Pure helper module — `app/ui/scenario_workflow.py`

Five public functions:

| Function | Returns | Used for |
|---|---|---|
| `classify_scenario_label(name)` | dict with `kind`, `display_name`, `icon`, `css_class` | Per-scenario label chip (Base / Downside / Upside / Custom) |
| `quick_summary_card(card)` | dict with formatted IRR / Project IRR / DSCR strings and `good` / `ok` / `bad` / `n_a` state | Mini KPI summary on each scenario card |
| `build_compare_shortcut_links(cards, active_id)` | list of compare-link dicts | "Compare with X" shortcut links on the active card |
| `workflow_state(cards)` | dict with `count`, `state`, `message`, `css_class` | Empty / one / two / many notice at the top |
| `build_scenario_workflow_ui(cards, active_id)` | composer — returns `{by_scenario, compare_links, state}` | Single payload for the template |

The module is **pure**:

- No DB imports.
- No I/O.
- No `datetime.now()` calls.
- No mutation of caller's input.
- No autosave / no scheduled tasks.

### 2. Display partial — `app/templates/partials/scenario_workflow_indicators.html`

Four Jinja2 macros, **no JavaScript**:

- `scenario_label(label)` — chip with icon + name
- `quick_summary_card(summary)` — three-row mini KPI block
- `compare_link(link)` — `<a href>` styled as a chip
- `workflow_state_notice(state)` — empty / one / two / many notice

### 3. CSS additions — `static/styles.css`

**Two blocks added, total +140 lines, no `:root` change:**

1. `.svh-*` block — adds the missing styles for the scenario card
   that existed in the template (`.svh-card`, `.svh-card--active`,
   `.svh-card-title`, `.svh-card-meta`, `.svh-card-gov`, `.svh-empty`,
   `.svh-explainer`, `.svh-warning`).
2. `.sw-*` block — workflow polish classes:
   - `.sw-label`, `.sw-label--base`, `.sw-label--downside`,
     `.sw-label--upside`, `.sw-label--custom`
   - `.sw-quick-summary`, `.sw-quick-summary__row`,
     `.sw-quick-summary__label`, `.sw-quick-summary__value`
   - `.sw-state--good`, `.sw-state--ok`, `.sw-state--bad`, `.sw-state--n_a`
   - `.sw-compare-link`, `.sw-compare-link__arrow`, `.sw-compare-link__label`
   - `.sw-empty-notice`, `.sw-empty--empty`, `.sw-empty--one`,
     `.sw-empty--two`, `.sw-empty--many`

No `!important` on `.sw-*` rules. No `:root` modifications (count
stays at 3).

### 4. Wire-up — `main_web.py`

- Added `from app.ui.scenario_workflow import build_scenario_workflow_ui`.
- `_workspace_refresh_payload(user, project_record, workspace_state=None)`
  now returns a 7-tuple that includes the workflow UI payload.
- `_render_scenario_workspace(..., scenario_workflow_ui=None)` accepts
  the workflow UI as an optional keyword argument. When `None`, a
  defensive default is built from the existing card list, so older
  code paths (e.g. legacy routes that call `_current_project_workspace`
  and don't pass workflow UI) still render correctly.
- Template context now includes `scenario_workflow_ui`.

### 5. Template update — `partials/scenario_version_history.html`

- Imported the four macros from `scenario_workflow_indicators.html`
  using Jinja2 `{% from ... import ... %}`.
- Added a workflow-state notice at the top of the list (one of
  empty / one / two / many).
- Replaced the bare scenario name with a workflow label (Base /
  Downside / Upside / Custom).
- Added the quick summary card directly under the title.
- Added the "Compare with X" shortcut links block, but only on the
  active scenario card (otherwise it would be a wall of buttons).

## Behaviour matrix

| Scenario count | Notice | Compare links on active card |
|---|---|---|
| 0 | "No saved scenarios yet. Save a snapshot to start comparing." | none |
| 1 | "One scenario saved. Add at least one more (Downside or Upside) to enable side-by-side compare." | none |
| 2 | "Two scenarios ready. Use compare to view the delta." | 1 link |
| 3+ | "N scenarios saved. Pick a pair or run a multi-compare." | 1+ links |

| Scenario name | Label | CSS class | Quick summary state |
|---|---|---|---|
| Base / Baseline / Case / Main | base | `sw-label--base` (blue) | good / ok / bad / n_a |
| Downside / Down / Low / P10 / Pessimistic / Stress | downside | `sw-label--downside` (red) | same |
| Upside / Up / High / P90 / Optimistic | upside | `sw-label--upside` (green) | same |
| Anything else | custom | `sw-label--custom` (gray) | same |

State thresholds:

- IRR: `good` ≥ 12 %, `ok` ≥ 8 %, `bad` < 8 %, `n_a` when missing.
- DSCR: `good` ≥ 1.50, `ok` ≥ 1.20, `bad` < 1.20, `n_a` when missing.

## Constraints honored

- ✅ **No formula changes** — `app/ui/scenario_workflow.py` only does
  label classification, threshold comparisons, and dict composition.
- ✅ **No model runtime changes** — the model is untouched.
- ✅ **No tax / debt / depreciation / IDC / construction / C10 /
  R-PAR / senior IDC**.
- ✅ **No schema migration** — `scenario_workflow_ui` is a render-time
  payload, not persisted anywhere.
- ✅ **No flag flips** — `use_construction_schedule_engine` is
  unchanged.
- ✅ **rc1 untouched** — the helper does not import
  `compare_service`, `base_vs_active_compare`, or any multi-compare
  path. The "Compare with X" shortcut link uses the existing
  `/scenarios/compare` route with the same query parameters.
- ✅ **TUHO / Oborovo preserved** — the helper is agnostic to project
  origin; the same labels and summary cards work for factory-saved
  scenarios (after Save As).
- ✅ **No Tailwind / Alpine / inline `<script>`** — the partial is
  pure HTML + CSS.

## Tests (88 tests, all passing)

| Test file | Class count | Test count |
|---|---|---|
| `tests/test_phase25b5_workflow_helpers.py` | 5 | 51 |
| `tests/test_phase25b5_factory_safety.py` | 4 | 25 |
| `tests/test_phase25b5_no_regression.py` | 6 | 12 |
| **Total** | **15 classes** | **88 tests** |

## Files in this phase

| File | Status | Lines |
|---|---|---|
| `app/ui/scenario_workflow.py` | new | ~280 |
| `app/templates/partials/scenario_workflow_indicators.html` | new | ~95 |
| `app/templates/partials/scenario_version_history.html` | modified | +20 |
| `main_web.py` | modified | +35 / -3 |
| `static/styles.css` | modified | +140 |
| 3 test files | new | 88 tests |
| `docs/phase25b5_scenario_workflow_polish.md` | new | this file |
| `reports/phase25b5_scenario_workflow_polish.json` | new | (JSON report) |
