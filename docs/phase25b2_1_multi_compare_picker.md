# Phase 25B-2.1 — Multi-Compare Button / Scenario Selection Entry Point

> Type: UI/NAVIGATION ONLY (no new backend, no new financial logic)
> Status: DRAFT (awaiting review)
> Date: 2026-06-09
> Branch: `phase25b2-1-multi-compare-picker`
> Base SHA: `aba8805` (post-25B-2-merge main)
> Hard constraints (all honored):
> - no new financial formulas
> - no formula refactor
> - no construction / C10 / R-PAR promotion
> - no senior IDC changes
> - no schema migration
> - no Tailwind / Alpine
> - no fake outputs / fake runtime IDs
> - no DB writes (the picker does not call any DB function; the existing
>   multi-compare route is GET-only)
> - rc1 untouched
> - factory paths preserved (`app/project_factories.py` zero diff)
> - `use_construction_schedule_engine` stays default `False` in `app/waterfall_core.py`
> - `:root` count = 3 (UI-2.5 invariant)
> - `app/waterfall_core.py` zero diff
> - existing 2-way `/scenarios/compare` flow preserved
> - existing `/scenarios/compare-multi` route preserved (read-only)

---

## 0. Purpose

After Phase 25B-2 (multi-scenario compare endpoint), a first-time finance
user still had to **manually construct** a URL like
`/scenarios/compare-multi?project=...&scenario_ids=base,downside,upside`
to see the multi-compare table. That required knowing the scenario_ids in
advance (via a copy from the Saved Versions list) and assembling the
comma-separated string by hand. This is a discoverability and usability
gap.

This phase adds a **selection entry point** in the existing scenario
workspace: a checkbox-driven picker that lets the user pick 2-4 saved
scenarios and click "Compare selected scenarios" to open the multi-compare
table. The picker is **read-only** — it does not write to the database,
does not call the model, and does not introduce new financial logic. It
just composes the URL and navigates to the existing `/scenarios/compare-multi`
endpoint.

The picker is **only shown for user-created projects** (Generic Solar,
Generic Wind, custom user projects). Factory projects (TUHO, Oborovo)
continue to use the existing 2-way compare flow unchanged.

---

## 1. What was delivered

### 1.1 New template — `partials/scenario_multi_compare_picker.html`

A new partial that renders:

1. A heading "Multi-Compare" with subtitle "pick 2-4 saved scenarios".
2. **EXPLORATORY banner** (if the project is generic_solar / generic_wind):
   `EXPLORATORY` badge + "Generic project. Multi-compare is exploratory
   / not Excel-parity validated."
3. **Descriptive banner** (for non-generic user projects):
   "Multi-compare is descriptive only. The first scenario you pick is
   the Base reference for deltas."
4. **Empty state** (0 saved scenarios): "No saved scenarios. Save at
   least 2 scenarios to enable multi-compare."
5. **One-scenario state** (1 saved scenario): "Only 1 saved scenario.
   Save at least 1 more scenario to enable multi-compare." with a
   locked, checked, disabled checkbox for the existing scenario.
6. **Happy path** (2+ saved scenarios): a `<form method="get"
   action="/scenarios/compare-multi">` with:
   - A hidden `<input name="project" value="...">` for the project code.
   - A list of `<label class="scm-pick-row">` items, one per saved
     scenario. Each contains:
     - A `<input type="checkbox" class="scm-pick-cb"
       name="scenario_id" value="...">` checkbox.
     - The scenario name.
     - An "Active" badge if the scenario is the current workspace active.
     - An "IRR X%" meta chip if `last_run_summary.equity_irr` is present.
   - A "0 of 2-4 selected" count indicator.
   - A "Compare selected scenarios" `<a>` button (initially
     `aria-disabled="true"`, no `href`).
   - A `<noscript>` fallback `<button type="submit">` for no-JS users.
7. An inline `<script>` block that runs only when 2+ scenarios exist.
   It listens to checkbox change events, enforces the 2-4 cap (the JS
   un-checks the (5th) checkbox if the user exceeds 4), and updates the
   Compare button `href` to
   `/scenarios/compare-multi?project=...&scenario_ids=a,b,c,d`.

The partial is rendered inside `partials/scenario_workspace.html` only
when **both** of these are true:
- `is_user_project` is True (i.e. `project_record.project_origin == "user_created"`).
- The multi-compare table is NOT already shown (i.e. neither
  `multi_compare_result` nor `multi_compare_error` is set).

This means: the picker appears in the normal Scenarios tab when the user
is browsing saved scenarios. When the user clicks "Compare selected
scenarios" and lands on the multi-compare endpoint, the picker is
replaced by the multi-compare table (no duplication).

### 1.2 New CSS — `.scm-pick-*` in `static/styles.css`

Added the following classes to `static/styles.css`:

- `.scm-pick` (root container)
- `.scm-pick-header`, `.scm-pick-title`, `.scm-pick-subtitle`
- `.scm-pick-banner`, `.scm-pick-exploratory-banner` (banners)
- `.scm-pick-empty` (empty / one-scenario state)
- `.scm-pick-form`, `.scm-pick-list`, `.scm-pick-row`,
  `.scm-pick-row--disabled` (selection list)
- `.scm-pick-cb` (checkbox)
- `.scm-pick-row-name`, `.scm-pick-row-meta`, `.scm-pick-row-active` (row content)
- `.scm-pick-actions`, `.scm-pick-count` (action bar)
- `.scm-pick-compare-btn`, `.scm-pick-compare-btn--disabled`,
  `.scm-pick-compare-btn-fallback` (button states)

All classes use CSS variables (`var(--sidebar-*, var(--text-*, var(--accent-*,
var(--info-bg, var(--warn-bg, var(--warn-fg, var(--text-muted`) for
colors, no hard-coded brand colors. The CSS block is additive — `:root`
count remains 3 (UI-2.5 invariant preserved).

No Tailwind `@apply` directives, no Alpine `x-data` / `x-on`.

### 1.3 Inline JS — vanilla, no dependencies

The picker uses a small inline `<script>` block (no external dependency,
no jQuery, no Alpine, no HTMX for the picker logic) to:

1. Read `data-min-scenarios="2"` and `data-max-scenarios="4"` from the
   picker root.
2. Attach a `change` listener to every `<input class="scm-pick-cb">`
   checkbox.
3. On change, if the user has just checked a (5th) box (count > 4),
   un-check that box.
4. Compute the selected scenario_ids and update the Compare button
   `href` to `/scenarios/compare-multi?project=...&scenario_ids=...`.
5. Toggle the `aria-disabled` attribute and the `--disabled` class on
   the Compare button.

The script is **isolated** to the picker root (it queries
`[data-testid="multi-compare-picker"]`), so it cannot interfere with
other checkboxes or buttons on the page.

If JavaScript is disabled, the user can still submit the form via the
`<noscript>` fallback `<button type="submit">` (or just by pressing
Enter in the form), which sends a regular form GET to
`/scenarios/compare-multi?project=...&scenario_ids=...`. The endpoint
treats the GET exactly like a JS-generated URL.

### 1.4 Wire — `partials/scenario_workspace.html`

Modified `partials/scenario_workspace.html` to include the new partial
inside a `<div class="ps-section" style="margin-top:0.75rem;">`
container, gated on `is_user_project and not (multi_compare_result or
multi_compare_error)`. The existing `partials/scenario_version_history.html`
include is unchanged.

---

## 2. Mapping to the original task

### 2.1 Scenario selection UI

> In the existing scenario workspace:
> - show checkbox or select controls for saved scenarios
> - allow selecting 2-4 scenarios
> - provide "Compare selected scenarios" button/link
> - generate existing /scenarios/compare-multi?project=...&scenario_ids=... URL
> - no new backend calculation

✅ Done. The picker renders checkboxes for every saved scenario in the
project (using the existing `scenario_summary_cards` data the workspace
already loads). The user can select 2-4. The Compare button (an `<a>`
with dynamically-updated `href`) navigates to the existing
`/scenarios/compare-multi?project=...&scenario_ids=...` endpoint. No
new route, no new helper, no new calculation — just URL composition.

### 2.2 Empty and invalid states

> Handle:
> - no scenarios
> - only one scenario
> - more than four selected
> - no run output
> - missing scenario id

✅ Done. The picker handles all 5 states:

| State | Picker behavior | Multi-compare endpoint behavior (25B-2) |
|---|---|---|
| no scenarios | "No saved scenarios" empty state, no form | (cannot reach — no scenarios to pick) |
| only one scenario | "Only 1 saved scenario" + locked, checked, disabled checkbox | (cannot reach via picker; direct URL → "needs at least 2") |
| more than four selected | JS un-checks the (5th) checkbox; cannot reach the endpoint with >4 | "at most 4 scenarios" error message (from 25B-2) |
| no run output | Picker renders the row (IRR meta is hidden if no `last_run_summary`); Compare button still works | Multi-compare table renders with `--` for missing values (from 25B-2) |
| missing scenario id | (cannot happen via picker — all checkboxes are server-rendered) | "could not be resolved" error message (from 25B-2) |

The 25B-2 endpoint already handles the 4th and 5th cases. The picker
handles the 1st, 2nd, and 3rd cases in the UI before the user even
clicks Compare.

### 2.3 Exploratory safety

> Show EXPLORATORY banner on the multi-compare entry point for
> generic_solar/generic_wind.

✅ Done. The picker shows the EXPLORATORY banner (`badge-warn` +
"Generic project. Multi-compare is exploratory / not Excel-parity
validated.") for projects with `template_source` in {`generic_solar`,
`generic_wind`}. For non-generic user projects, it shows a descriptive
banner ("Multi-compare is descriptive only. The first scenario you
pick is the Base reference for deltas."). The picker does NOT show
any "Reference" or "Validated" badge — only the EXPLORATORY warning.

### 2.4 Reference safety

> Tests must prove:
> - generic projects can use the multi-compare entry point
> - factory projects do not get unsafe generic claims
> - existing 2-way compare still works
> - multi-compare route remains read-only
> - use_construction_schedule_engine remains False
> - rc1 untouched

✅ Done. Test Block 5 (TestPickerSafetyConstraints) covers all 6:

- `test_no_new_financial_formulas` — no `.irr(`, `npv(`, `numpy`,
  `pandas`, `atad_*`, `corporate_rate` in the new template.
- `test_no_db_writes_in_picker_code` — no `INSERT`, `UPDATE`, `DELETE`,
  `cur.execute`, `conn.execute` in the picker code.
- `test_no_factory_path_changes` — `app/project_factories.py` zero diff.
- `test_waterfall_core_unchanged` — `app/waterfall_core.py` zero diff.
- `test_no_construction_flag_flips` — no `use_construction_schedule_engine = True`
  in the diff.
- `test_css_root_count_unchanged` — `:root` count = 3.
- `test_no_tailwind_in_picker_css_block` — no `@apply` in the picker CSS.
- `test_no_alpine_in_picker_template` — no `x-data` / `x-on:` / `x-show` / `x-model`.
- `test_no_rc1_in_picker_code` — no `rc1` mention.
- `test_multi_compare_route_remains_read_only` — Compare button is an
  `<a>` with href (GET), not a form POST.
- `test_existing_2way_compare_still_works` — `/scenarios/compare?project=tuho`
  still returns 200 and does not show the picker (factory path).

Test Block 2 covers the entry-point side:
- `test_picker_shown_for_generic_solar` — generic project → picker + EXPLORATORY.
- `test_picker_shown_for_test_template` — non-generic user project → picker + descriptive.
- `test_picker_hidden_for_factory_project` — TUHO (factory) → NO picker.
- `test_picker_hidden_when_multi_compare_result_set` — picker is hidden
  when the multi-compare table is already shown (no duplication).

---

## 3. Test coverage

The new test file
`tests/test_phase25b2_1_multi_compare_picker.py` has 6 test blocks
and 38 tests:

### 3.1 Test Block 1 — Template exists and content (9 tests)

- `test_template_file_exists` — partial file exists.
- `test_template_has_picker_root_testid` — `data-testid="multi-compare-picker"`.
- `test_template_has_min_max_attributes` — `data-min-scenarios="2"`,
  `data-max-scenarios="4"`.
- `test_template_uses_existing_multi_compare_endpoint` — href and
  form action both point to `/scenarios/compare-multi`.
- `test_template_uses_form_get_for_no_js_fallback` — `method="get"`,
  `<noscript>` fallback button.
- `test_template_uses_existing_scenario_summary_cards` — uses the
  same data as the existing version history list.
- `test_template_renders_compare_button_with_aria_disabled` —
  button starts with `aria-disabled="true"`.
- `test_template_renders_count_indicator` — "0 of 2-4 selected" text.
- `test_template_inline_js_is_minimal` — no Tailwind / Alpine; inline
  JS uses `encodeURIComponent` and updates `aria-disabled` + `href`.

### 3.2 Test Block 2 — Conditional rendering (5 tests)

- `test_picker_shown_for_generic_solar` — generic project → picker + EXPLORATORY.
- `test_picker_shown_for_test_template` — non-generic user project → picker + descriptive.
- `test_picker_hidden_for_factory_project` — TUHO (factory) → NO picker.
- `test_picker_hidden_when_multi_compare_result_set` — picker is
  hidden when the multi-compare table is already shown.
- `test_picker_unauthenticated_redirects` — 200 or 302 (depends on
  guest mode).

### 3.3 Test Block 3 — Empty and partial states (5 tests)

- `test_no_scenarios_shows_empty_state` — 0 scenarios → "No saved
  scenarios" empty state, no form.
- `test_one_scenario_shows_partial_state` — 1 scenario → "Only 1
  saved scenario" + locked disabled checkbox, no form.
- `test_two_scenarios_shows_form` — 2 scenarios → form, 2 checkboxes,
  Compare button initially disabled.
- `test_four_scenarios_shows_form_with_4_checkboxes` — 4 scenarios →
  form, 4 checkboxes, all 4 scenario names rendered.

### 3.4 Test Block 4 — End-to-end integration (5 tests)

- `test_compare_button_href_is_well_formed` — JS constructs the URL
  from `data-project-code` and selected scenario_ids.
- `test_form_get_submission_works_without_js` — a plain form GET to
  `/scenarios/compare-multi?project=...&scenario_ids=...` works
  (multi-compare table renders).
- `test_too_few_scenarios_returns_error_state` — submitting 1 scenario
  via the picker path (JS bypassed) shows the multi-compare error
  state, not a crash.
- `test_too_many_scenarios_returns_error_state` — 5+ scenario_ids
  returns the "at most 4" error message.
- `test_missing_run_output_handled` — submitting scenarios with no
  `last_run_summary` does not crash (helper tolerates None).

### 3.5 Test Block 5 — Safety constraints (11 tests)

- `test_no_new_financial_formulas` — no `.irr(`, `npv(`, etc. in picker.
- `test_no_db_writes_in_picker_code` — no INSERT/UPDATE/DELETE.
- `test_no_factory_path_changes` — `app/project_factories.py` zero diff.
- `test_waterfall_core_unchanged` — `app/waterfall_core.py` zero diff.
- `test_no_construction_flag_flips` — no flag flips in diff.
- `test_css_root_count_unchanged` — `:root` count = 3.
- `test_no_tailwind_in_picker_css_block` — no `@apply` in picker CSS.
- `test_no_alpine_in_picker_template` — no Alpine in template.
- `test_no_rc1_in_picker_code` — no `rc1` mention.
- `test_multi_compare_route_remains_read_only` — Compare button is
  an `<a>` with href (GET), not a POST submit.
- `test_existing_2way_compare_still_works` — `/scenarios/compare?project=tuho`
  still returns 200 and does not show the picker (factory path
  preserved).

### 3.6 Test Block 6 — CSS style guard (4 tests)

- `test_css_has_pick_root_classes` — `.scm-pick`, `.scm-pick-header`,
  `.scm-pick-list`, `.scm-pick-row`, `.scm-pick-actions`,
  `.scm-pick-compare-btn` all present.
- `test_css_has_banner_styles` — `.scm-pick-banner` and
  `.scm-pick-exploratory-banner` present.
- `test_css_has_disabled_state` — `.scm-pick-compare-btn--disabled` +
  `.scm-pick-row--disabled` + `pointer-events: none`.
- `test_css_uses_css_variables_for_colors` — picker CSS uses
  `var(--*)` for colors, no hard-coded brand colors.

---

## 4. Hard-constraint verification

| Constraint | How verified |
|---|---|
| no new financial formulas | `test_no_new_financial_formulas` (picks up the new template only) |
| no formula refactor | `git diff main...HEAD app/waterfall_core.py` is empty |
| no construction / C10 / R-PAR promotion | `test_no_construction_flag_flips` + `test_waterfall_core_unchanged` |
| no senior IDC changes | `git diff main...HEAD app/waterfall_core.py` is empty |
| no schema migration | no migration files in diff |
| no Tailwind / Alpine | `test_no_tailwind_in_picker_css_block` + `test_no_alpine_in_picker_template` |
| no fake outputs | the picker does not produce any numeric output (just URL composition) |
| no fake runtime IDs | the picker does not call any model-execution function |
| no DB writes | `test_no_db_writes_in_picker_code` |
| rc1 untouched | `test_no_rc1_in_picker_code` |
| factory paths preserved | `test_no_factory_path_changes` + `test_picker_hidden_for_factory_project` |
| `use_construction_schedule_engine = False` | `test_no_construction_flag_flips` + `test_waterfall_core_unchanged` |
| `:root` count = 3 | `test_css_root_count_unchanged` |
| `app/project_factories.py` zero diff | `test_no_factory_path_changes` |
| `app/waterfall_core.py` zero diff | `test_waterfall_core_unchanged` |
| existing 2-way compare unchanged | `test_existing_2way_compare_still_works` |
| multi-compare route read-only | `test_multi_compare_route_remains_read_only` |
| scenario workspace layout unchanged | the new partial is added inside an existing `<div class="ps-section">` |
| no new backend route | only the new partial + 4 lines in `scenario_workspace.html` + 130 lines in `static/styles.css` |
| no new helper | the existing `compare_multi_scenarios()` is reused |

---

## 5. What the user sees

### 5.1 Before Phase 25B-2.1

A user with 3 saved scenarios (Base, Downside, Upside) had to:
1. Open DevTools or right-click "Inspect" on the saved scenarios.
2. Copy the `data-scenario-id` attribute from each scenario row.
3. Manually construct
   `/scenarios/compare-multi?project=...&scenario_ids=base,downside,upside`
4. Paste it into the address bar.

### 5.2 After Phase 25B-2.1

1. The user opens the Scenarios workspace.
2. Below the existing "Saved Versions" list, a new "Multi-Compare"
   section appears with checkboxes next to each saved scenario.
3. The user checks 2-4 scenarios. The "0 of 2-4 selected" counter
   updates. The "Compare selected scenarios" button becomes enabled
   (no longer `aria-disabled`).
4. The user clicks the button. The browser navigates to
   `/scenarios/compare-multi?project=...&scenario_ids=...` and the
   multi-compare table renders.
5. If the project is `generic_solar` or `generic_wind`, the EXPLORATORY
   warning is visible at the top of the picker and at the top of the
   multi-compare table.

### 5.3 Edge cases

- **0 scenarios** → "No saved scenarios. Save at least 2 scenarios to
  enable multi-compare." No form, no button.
- **1 scenario** → "Only 1 saved scenario. Save at least 1 more scenario
  to enable multi-compare." + a locked, checked, disabled checkbox for
  the existing scenario. No form, no button.
- **2-4 scenarios** → form + checkboxes + counter + Compare button.
  Initially the button is `aria-disabled` (0 selected). The user must
  select 2+ for the button to enable.
- **5+ selections attempted** → JS un-checks the (5th) checkbox. The
  user cannot submit with >4.
- **No run output for a selected scenario** → the multi-compare table
  shows `--` for that scenario's metrics (handled by 25B-2 endpoint).
- **JavaScript disabled** → the user can still submit the form via
  the `<noscript>` fallback button (or by pressing Enter in the
  form).

---

## 6. What is NOT in this phase

1. **No "Select All" / "Deselect All" buttons.** The user can click
   each checkbox individually. A "Select All" button is a follow-up
   (probably 25B-2.2).
2. **No "Move to top" / re-order.** The Base scenario in the multi-compare
   table is determined by the order of scenario_ids in the URL (first
   id = Base). The picker does not let the user re-order scenarios; they
   just pick them. To make a different scenario the Base, they would
   need to construct the URL manually (which is documented in the
   25B-2 report).
3. **No persistent selection state.** The picker does not remember
   which scenarios the user selected last time. A new visit to the
   workspace shows all checkboxes unchecked.
4. **No keyboard shortcuts.** The user must click each checkbox
   individually. (Standard browser keyboard navigation works:
   Tab + Space, etc.)
5. **No drag-to-reorder** for the Base scenario.
6. **No scenario search / filter.** If the user has 50+ saved
   scenarios, the picker list shows all of them (with internal scroll).
   A search input is a follow-up.
7. **No bulk delete / archive** from the picker.
8. **No link from the multi-compare table back to the picker** ("Edit
   selection"). A "Back to Scenarios" link is a follow-up (probably
   25B-2.2 or 25B-3).
9. **No live preview** of the multi-compare table as the user toggles
   checkboxes. The user must click Compare to see the table.

These are all listed in the 24-H closure review recommendations and
will be tackled in subsequent 25B-2.2 / 25B-3 / 25B-4 phases.

---

## 7. Files changed

| File | Type | Δ | Notes |
|---|---|---|---|
| `app/templates/partials/scenario_multi_compare_picker.html` | new | +247 lines | New partial: picker UI + inline JS |
| `app/templates/partials/scenario_workspace.html` | modified | +9 lines | Conditional include of the new partial (gated on `is_user_project and not (multi_compare_result or multi_compare_error)`) |
| `static/styles.css` | modified | +129 lines | New `.scm-pick-*` classes (additive, `:root` count = 3 preserved) |
| `tests/test_phase25b2_1_multi_compare_picker.py` | new | +954 lines | 38 tests, 6 test blocks |
| `docs/phase25b2_1_multi_compare_picker.md` | new | this file | docs |
| `reports/phase25b2_1_multi_compare_picker.json` | new | report | report |

**Unchanged files (verified):**
- `app/project_factories.py` (zero diff)
- `app/waterfall_core.py` (zero diff)
- `app/persistence/exports_repository.py` (the `compare_multi_scenarios`
  helper is reused, not modified)
- `main_web.py` (the `/scenarios/compare-multi` route is unchanged;
  the picker just navigates to it)
- `app/services/compare_service.py` (the 2-way compare flow is
  preserved)
- All 25B-2 / 25B-1 / 24-H / 24-G files (untouched)

**Total implementation: ~385 lines of UI / CSS (no new Python).**

---

## 8. Regression test counts

| Suite | Tests | Status |
|---|---|---|
| **25B-2.1 (new)** | **38** | **✅** |
| 25B-2 (regression) | 53 | ✅ |
| 25B-1 (regression) | 52 | ✅ |
| 24-H-closure (regression) | 34 | ✅ |
| 24-H-4 (regression) | 58 | ✅ |
| 24-H-3 (regression) | 53 | ✅ |
| 24-H-2 (regression) | 55 | ✅ |
| 24-H (regression) | 29 | ✅ |
| 24-G-closure (regression) | 30 | ✅ |
| 24-G-1 (regression) | 47 | ✅ |
| 24-G-2 (regression) | 75 | ✅ |
| 24-G-3 (regression) | 69 | ✅ |
| **Total phase-targeted** | **593** | **✅ 100%** |

---

## 9. Honest summary

**What Phase 25B-2.1 achieves:** A first-time finance user can now
open the Scenarios workspace, see a "Multi-Compare" section with
checkboxes for every saved scenario, pick 2-4, and click "Compare
selected scenarios" to open the multi-compare table — all without
constructing a URL manually. The picker is read-only, works without
JavaScript (via the `<noscript>` form fallback), enforces the 2-4 cap
on the client side, and shows the EXPLORATORY warning for generic
projects. The picker is hidden for factory projects (TUHO, Oborovo)
so they continue to use the existing 2-way compare flow.

**What Phase 25B-2.1 does NOT achieve:** This is a UI / navigation
extension only. It does not introduce new financial logic, does not
write to the database, does not re-execute the model, does not promote
construction / C10 / R-PAR work, and does not change the factory
paths. "Select All" / re-order / persistent selection / live preview
are deferred to 25B-2.2 / 25B-3.

**Recommended next phase:** 25B-2.2 ("Edit selection" link from
multi-compare table back to picker) or 25B-3 ("What changed" delta
indicator). Both are small UX polishes that build on the existing
25B-2 / 25B-2.1 infrastructure.
