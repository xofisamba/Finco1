# Phase 25B-4 — Dirty State + Unsaved Changes (visual only)

## Goal

Make it always obvious to the user **whether their changes are
saved** and **whether running the model would use the current draft
or an older saved snapshot**.

This is a pure-UI, read-only phase. There is **no autosave**, **no
new state machine**, **no schema migration**, and **no model-formula
change**. The dirty/stale state is already exposed by the existing
`app.services.scenario_state_service.build_workspace_state_metadata()`
helper. Phase 25B-4 surfaces it on the workspace in four clearly
separated UI surfaces.

## What was already there

| Concern | Where it lives (pre-25B-4) |
|---|---|
| `workspace_state.dirty` (bool) | `app.services.scenario_state_service.build_workspace_state_metadata` |
| `workspace_state.last_runtime_snapshot_id` | same helper |
| `workspace_meta["dirty_label"]` (str) | same helper, exposed via `_workspace_refresh_payload` |
| `current_context.dirty_label` (rendered) | `app/templates/partials/workspace_shell.html` line 311 |
| Inline `dirty-indicator` element | `app/templates/partials/inputs_section.html` line 133 (toggled by inline JS) |

Phase 25B-4 does **not** replace or modify any of this. It adds a
**separate, parallel visual layer** that is more discoverable and
self-explanatory for a first-time finance user.

## What 25B-4 adds

### 1. Pure helper module — `app/ui/dirty_state.py`

A new file. Exposes four public helpers plus a composer:

| Helper | Returns | Used for |
|---|---|---|
| `badge_saved_state(dirty, has_runtime_snapshot, is_user_project)` | dict with `label`, `state`, `css_class`, `icon` | Workspace-top "Saved" / "Unsaved" / "Stale" / "Read-only" chip |
| `changes_not_saved_notice(dirty, is_user_project)` | dict or `None` | "Changes not yet saved" banner in the input section |
| `run_disabled_warning(dirty, has_runtime_snapshot, is_user_project)` | dict or `None` | "Run will use older than current draft" warning chip next to the Run button |
| `scenario_dirty_indicator(is_active_scenario, workspace_dirty, is_user_project)` | dict with `is_dirty`, `css_class`, `title` | Per-scenario dirty dot in the scenario list |
| `build_dirty_state_ui(...)` | dict with all of the above + a `scenario_dots` list | Single payload for the template |

The module is **pure**:

- No DB imports.
- No I/O (`open`, `read`, `write`, `json.load`, `json.dump`).
- No `datetime.now()` — the timestamp is provided by the caller (already
  available in the existing workspace state).
- No side effects on the caller's input.
- No autosave, no scheduled tasks, no background jobs.

### 2. Display partial — `app/templates/partials/dirty_state_indicators.html`

A new partial exposing four Jinja2 macros. **No JavaScript**, **no
inline `<script>` tags**, **no Tailwind**, **no Alpine**. The macros
are:

- `saved_state_chip(badge)` — chip with icon + label
- `changes_not_saved_notice(notice)` — yellow notice
- `run_disabled_warning(warning)` — orange warning chip
- `scenario_dirty_dot(dot)` — small pulsing dot
- `dirty_state_row(dirty_state_ui)` — composition of badge + warning

A sixth, `dirty_state_row` macro, is provided so the workspace top
bar can render badge + run warning side by side. The actual
inclusion of these macros is done inline in
`partials/scenario_workspace.html` (workspace top) and
`partials/scenario_version_history.html` (per-scenario card).

### 3. CSS additions — `static/styles.css`

A new section at the bottom of the file, **+173 lines** of additive
CSS. **No `:root` block changes** (Phase 24G-2 invariant preserved:
still 3 `:root` blocks). **No `!important`** on `.ds-*` rules.

New classes:

- `.ds-row` — flex row
- `.ds-badge`, `.ds-badge--saved`, `.ds-badge--unsaved`, `.ds-badge--stale`, `.ds-badge--factory`
- `.ds-badge__icon`, `.ds-badge__label`
- `.ds-notice`, `.ds-notice--unsaved`, `.ds-notice--factory`
- `.ds-notice__icon`, `.ds-notice__body`, `.ds-notice__title`, `.ds-notice__text`
- `.ds-run-warning`, `.ds-run-warning--stale`
- `.ds-run-warning__icon`, `.ds-run-warning__label`
- `.ds-dot`, `.ds-dot--dirty` (with `ds-dirty-pulse` keyframes)
- `.workspace-dirty-state-bar` (layout hook)
- `.workspace-dirty-state-bar__title`

### 4. Wire-up — `main_web.py`

- Added `from app.ui.dirty_state import build_dirty_state_ui` at the
  top.
- `_workspace_refresh_payload(user, project_record, workspace_state=None)`
  now returns a 6-tuple: `(scenarios, history, exports, export_lineage,
  scenario_summary_cards, dirty_state_ui)`. The new
  `workspace_state` parameter is optional and read-only; when `None`,
  the function falls back to defaults (clean state).
- `_render_scenario_workspace(...)` now accepts an optional
  `dirty_state_ui=None` keyword argument. When omitted, the
  workspace is still renderable (defensive default).
- The template context now includes `dirty_state_ui` which the
  template reads directly.

### 5. Template updates — two partials

- `app/templates/partials/scenario_workspace.html`: added a
  `workspace-dirty-state-bar` block at the top of the workspace,
  with the saved-state chip, run-warning chip (when stale), and the
  "Changes not yet saved" notice (when dirty). The pre-existing
  inline `dirty-indicator` element in `inputs_section.html` is
  **left intact** for now (it is toggled by inline JS); the new
  workspace-top bar is the more discoverable surface.
- `app/templates/partials/scenario_version_history.html`: added a
  per-scenario dirty dot inside the `svh-card-title` div. The dot
  is rendered only when the helper says this scenario is dirty
  (active scenario + workspace dirty + user project).

## Behaviour matrix

| Workspace state | User project? | Top chip | Notice | Run warning | Active scenario dot |
|---|---|---|---|---|---|
| Clean | yes | Saved (green) | (none) | (none) | (none) |
| Unsaved (no snapshot) | yes | Unsaved edits (yellow) | Changes not yet saved | (none) | yellow pulsing |
| Stale (dirty + snapshot) | yes | Stale — older than current draft (orange) | Changes not yet saved | Run will use older than current draft | yellow pulsing |
| Read-only baseline | no (factory) | Read-only baseline (gray) | Factory baseline — Use Duplicate | (none) | (none) |

## Constraints honored

- ✅ **No formula changes** — `app/ui/dirty_state.py` only does label
  selection and small dict composition.
- ✅ **No model runtime changes** — the model is untouched.
- ✅ **No tax / debt / depreciation / IDC changes**.
- ✅ **No construction / C10 / R-PAR / senior IDC**.
- ✅ **No schema migration** — `dirty_state_ui` is a render-time
  payload, not persisted anywhere.
- ✅ **No flag flips** — `use_construction_schedule_engine` is
  unchanged.
- ✅ **rc1 untouched** — the helper does not import
  `compare_service`, `base_vs_active_compare`, or any multi-compare
  path.
- ✅ **TUHO / Oborovo preserved** — factory projects never show
  unsaved / stale / saved badges; the read-only baseline badge is
  used instead.
- ✅ **No Tailwind / Alpine / inline `<script>`** — the partial is
  pure HTML + CSS.

## Tests (77 tests, all passing)

| Test file | Class count | Test count |
|---|---|---|
| `tests/test_phase25b4_dirty_state_helpers.py` | 5 | 28 |
| `tests/test_phase25b4_dirty_state_rendering.py` | 5 | 14 |
| `tests/test_phase25b4_factory_safety.py` | 8 | 26 |
| `tests/test_phase25b4_no_regression.py` | 5 | 9 |
| **Total** | **23 classes** | **77 tests** |

## Files in this phase

| File | Status | Lines |
|---|---|---|
| `app/ui/dirty_state.py` | new | ~225 |
| `app/templates/partials/dirty_state_indicators.html` | new | ~85 |
| `app/templates/partials/scenario_workspace.html` | modified (+~30) | +30 |
| `app/templates/partials/scenario_version_history.html` | modified (+~10) | +10 |
| `main_web.py` | modified | +35 / -3 |
| `static/styles.css` | modified (+173) | +173 |
| 4 test files | new | 77 tests |
| `docs/phase25b4_dirty_state_unsaved_changes.md` | new | this file |
| `reports/phase25b4_dirty_state_unsaved_changes.json` | new | (JSON report) |

## Out of scope (deferred to next phases)

- **Phase 25B-5** — scenario workflow polish (Base / Downside / Upside
  labels, active highlight, summary cards, compare shortcuts).
- **Phase 25B-6** — generic project review pack (assumptions, KPIs,
  limitations, exclusions).
- **Phase 25B-Closure** — pilot readiness review (audit + readiness %).
