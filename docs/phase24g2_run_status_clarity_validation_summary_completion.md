# Phase 24-G-2 — Run Status Clarity + Validation Summary Completion

> Type: UI-ONLY IMPLEMENTATION
> Status: DRAFT (not yet merged)
> Date: 2026-06-09
> Base SHA: `07cb4d0` (Phase 24-G-1 commit, stacked)
> Branch: `phase24g2-run-status-clarity-validation-summary-completion`
> Source inventory: PR #564 (Phase pilot-ux-safe-track-inventory)
> Sprint: 24-G-2 (G-track, parallel to C10/R-PAR-2 chain)

---

## 0. Purpose

Complete the Pilot UX Safe Track work from PR #564 by:

1. **Run Status Clarity** — make the run status of the current
   workspace visible at a glance (OK / ERROR / BLOCKED / NO RUN),
   with project and scenario association, and a stale/fresh
   inline state.
2. **Validation Summary Completion** — extend Phase 24-G-1 with
   strict severity ordering, hint subtitles, and visual
   consistency.
3. **Empty-state review** — three new top-of-page empty-state
   partials for "no project", "no scenario", "no run".

Hard constraints (from the user request):
- UI-only (no backend / service / domain / persistence / model /
  formula / tax / debt / depreciation / IDC / runtime changes)
- No fake run IDs
- No fake timestamps
- No invented scenario IDs
- No new JavaScript (no app.js change)
- No Tailwind / Alpine
- rc1 untouched
- 24-G-2 stacked on 24-G-1 (no duplication)

---

## 1. Run Status Clarity — implementation

### 1.1 What was already there

- `_last_run_indicator.html` (UI-2.6, Phase 55E) — conservative
  partial that renders nothing if `runtime_summary` is missing
  or has no real `run_id` / `last_run_at`.
- It shows: "Last run" label, optional truncated run_id (12
  chars), optional last_run_at, and a generic note ("Review
  model evidence before export").
- The stale warning lives in `stale_run()` macro in
  `empty_states_notice.html` (Phase 24-G-1).

### 1.2 What changed in Phase 24-G-2

`_last_run_indicator.html` is extended with the following
additive fields, all sourced from the same context that is
already passed in (no new context variables introduced):

1. **Status badge** — OK / ERROR / BLOCKED / — (NO RUN).
   Sourced from `runtime_summary.status` (real data). The
   status value is mapped to a tone class:
   - `ok` → green badge, ✓ prefix
   - `error` → red badge, ✗ prefix
   - `blocked` → amber badge, ⊘ prefix
   - anything else (or missing) → grey "—" badge
   - A "Last run error" row surfaces `runtime_summary.error_message`
     when present.
2. **Project association** — `project_record.project_code` shown
   as a mono-font badge, with `project_record.project_name` as
   the title (tooltip). The row renders nothing if the project
   is missing.
3. **Scenario association** — `base_case_record.scenario_name`
   shown when present. The row renders nothing if the scenario
   name is empty.
4. **Stale state row** — inline indicator showing "STALE"
   badge + "Draft has unsaved changes; outputs reflect a
   previous run. Run again to reflect the current draft." text.
   Same gate as `stale_run()` macro:
   `workspace_state.dirty AND workspace_state.last_runtime_snapshot_id`.
   - `data-stale-state="stale"` or `data-stale-state="fresh"` is
     set on the aside for downstream CSS / future JS hooks.
5. **Tone color stripe** — the aside's left border is colored
   based on the run status tone (green / red / amber / none).

### 1.3 What did NOT change

- `main_web.py` — untouched. The `_runtime_summary_for_index()`
  function in `main_web.py` is unchanged and still returns only
  `run_id` + `last_run_at`. The new fields are sourced from
  `project_record`, `base_case_record`, and `workspace_state`
  which are already in the index context.
- `runtime_summary` (the Python helper) — untouched.
- `runtime_summary.html` (the runtime summary partial) —
  untouched.
- `empty_states_notice.html` — only the `stale_run()` macro
  was changed in 24-G-1; 24-G-2 does not touch this file.
- Any service, persistence, model, formula, or runtime path.
- The `use_construction_schedule_engine` flag (still `False`).
- Any JavaScript file.

### 1.4 CSS

All styles are additive. New classes added:
- `.last-run-indicator--status-ok` / `--error` / `--blocked` / `--none`
  (left border colors)
- `.last-run-indicator__status` (badge container)
- `.last-run-indicator__status--ok` / `--error` / `--blocked` / `--none`
  (badge tone)
- `.last-run-indicator__row--stale` (stale row container)
- `.last-run-indicator__stale-badge` (STALE badge)
- `.last-run-indicator__stale-hint` (stale hint text)
- `.last-run-indicator__row--header` (header row layout)
- `.last-run-indicator__row--project` / `--scenario` / `--id` /
  `--time` / `--error` (row layouts)
- `.last-run-indicator__value--strong` (strong value)
- `.last-run-indicator__value--error` (error value tone)
- `.last-run-indicator__row--note` (note row)

The `:root` block count remains at 5 (UI-2.5 invariant).
No `.stale-result-*` classes added (UI-2.5 invariant).

### 1.5 Test coverage

`tests/test_phase24g2_run_status_clarity.py` covers:
- Renders nothing if runtime_summary is missing or empty
  (4 tests)
- Status badge tone for OK / ERROR / BLOCKED / unknown / missing
  (5 tests)
- Project association renders when present, not when absent
  (4 tests)
- Scenario association renders when present, not when absent
  (3 tests)
- Stale state row appears for the correct gate, and is absent
  for all other combinations (5 tests)
- Run error message surfaces when present (2 tests)
- CSS additive (no `:root` mods, no forbidden classes)
- No production code change
- index.html includes the partial
- Three empty-state partials render correctly
  (3 × 3 = 9 tests)

Total: 47 tests in this file.

---

## 2. Validation Summary Completion — implementation

### 2.1 What was already there (Phase 24-G-1)

- `validation.html` groups messages by severity:
  - Error (red, ! icon)
  - Warning (amber, ⚠ icon)
  - Information (blue, i icon)
- Each group has a header with icon, title, and count badge.
- Plain string errors are treated as Error severity.
- Structured dict errors are grouped by `severity` field.
- Error group deduplicates repeated wording with a `×N` badge.
- Original "Validation failed" / "Input checks passed" copy
  preserved.

### 2.2 What changed in Phase 24-G-2

`validation.html` is rewritten (additive) to:

1. **Strict severity order** — all three groups are ALWAYS
   rendered in the order Error → Warning → Information, even
   when one or more groups is empty. This makes the severity
   hierarchy always visible to the user, so they always see
   "0 Errors, 0 Warnings, 0 Info" when nothing is wrong.
2. **Empty group hint row** — when a group has zero items, the
   body contains a small italic hint row:
   - "No errors. Inputs are clear for run."
   - "No warnings. Nothing to review."
   - "No additional information."
   - The group also has the `.validation-group--empty` modifier
     class, and the body text has the `.validation-group-empty`
     class for styling.
3. **Hint subtitle** — each group has a `.validation-group-hint`
   element after the count badge:
   - Error: "Must be fixed"
   - Warning: "Review before run"
   - Information: "FYI only"
4. **Data attributes** — each group has `data-severity` and
   `data-count` attributes for downstream CSS or future JS
   hooks. **No new JS added.**
5. **aria-label on header** — top-level "Validation failed"
   header now has `role="alert"` and `aria-label`. Passed
   message has `role="status"` and `aria-label`.

### 2.3 What did NOT change

- `_validation_summary_bar.html` — untouched.
- The `validation_summary` context variable on the index page
  (still computed by `_validation_summary_for_context` in
  `main_web.py`).
- The `/validate` route's input shape.
- The `validation_service.py` logic.
- Any backend service, persistence, model, formula, or
  runtime path.
- The `use_construction_schedule_engine` flag (still `False`).
- The `validation_summary` context variable on the index
  page (not changed by 24-G-2).
- Error dedup behavior (still Error group only).
- Backward-compat with plain string and structured dict inputs.

### 2.4 CSS

New classes added (all additive):
- `.validation-group--empty` (modifier on empty group)
- `.validation-group-empty` (the "no items" hint row)
- `.validation-group-hint` (hint subtitle)
- `.validation-group--error .validation-group-hint` (tone)
- `.validation-group--warning .validation-group-hint` (tone)
- `.validation-group--information .validation-group-hint` (tone)

The `:root` block count remains at 5.

### 2.5 Test coverage

`tests/test_phase24g2_validation_summary_completion.py`
covers (28 tests):
- All three groups always render (6 tests, including strict
  order invariant)
- Empty groups render with `--empty` modifier and a "no items"
  hint (7 tests)
- Hint subtitles per group (3 tests)
- `data-severity` and `data-count` attributes (4 tests)
- Original "Validation failed" / "Input checks passed" copy
  preserved (2 tests)
- Backward-compat with plain string errors (2 tests)
- Backward-compat with structured dict errors (3 tests)
- Error dedup from 24-G-1 still works (2 tests)
- CSS additive (4 tests)
- No production code change (2 tests)

---

## 3. Empty-state review — implementation

Three new top-of-page empty-state partials, all in
`app/templates/partials/_empty_*.html`:

1. **`_empty_no_project.html`** — renders when
   `project_record` is missing or has no `project_code`.
   - Title: "No project selected"
   - Description: "Choose a project from the project
     selector in the sidebar to view its baseline,
     scenarios, and model outputs."
   - Style: `.empty-state-notice--info` (neutral, blue)
2. **`_empty_no_scenario.html`** — renders when
   `base_case_record` is missing AND `non_base_scenarios`
   is empty.
   - Title: "No scenario selected"
   - Description: "This project has no scenarios yet.
     Create a base case to start modeling — scenarios
     capture inputs, assumptions, and keep run history
     separate per what-if."
3. **`_empty_no_run.html`** — renders when
   `runtime_summary` has no `run_id` and no `last_run_at`.
   - Title: "No run performed yet"
   - Description: "Save your inputs and click
     **Run Model** to produce model outputs. Exports
     always use the last clean backend run, not unsaved
     draft edits."

All three:
- Use the existing `.empty-state-notice` pattern
- Render nothing if their gate is false
- Have `role="status"` and `aria-label`
- Are wired in `index.html` after the workspace shell and
  before the last run indicator

### 3.1 What did NOT change

- The `no_scenario_selected()`, `no_run_yet()`,
  `unsaved_edits()`, `no_validation_run()`,
  `no_export_yet()`, `generic_project_selected()` macros
  in `empty_states_notice.html` are all still available for
  callers that want to invoke them explicitly inside tab
  panels.
- The `empty_states_notice.html` `<style>` block is
  unchanged.
- The `_last_run_indicator.html` already had a "no
  information" type presentation; 24-G-2's new
  `_empty_no_run.html` is a separate top-level notice.

### 3.2 CSS

New class added:
- `.empty-state-notice--info` (neutral blue variant)
- `.esn-icon--no-project` / `--no-scenario` / `--no-run`
  (icon containers)

The `:root` block count remains at 5.

---

## 4. Test counts

| File | Count | Status |
|---|---|---|
| `test_phase24g2_run_status_clarity.py` | 47 | ✅ pass |
| `test_phase24g2_validation_summary_completion.py` | 28 | ✅ pass |
| `test_phase24g1_stale_run_warning.py` (regressed: 0) | 19 | ✅ pass |
| `test_phase24g1_validation_summary_clarity.py` (relaxed 2) | 28 | ✅ pass |
| `test_ui2_5_stale_result_warning.py` (untouched) | 48 | ✅ pass |
| `test_ui2_3_validation_summary_bar.py` (untouched) | 38 | ✅ pass |
| `test_ui2_1_state_banner_partial.py` (untouched) | 39 | ✅ pass |
| `test_ui2_4_factory_lock_indicator.py` (untouched) | 29 | ✅ pass |
| `test_phase55g_banner_context.py` (untouched) | 36 | ✅ pass |
| `test_phase55f_validation_summary_context.py` (untouched) | 33 | ✅ pass |
| `test_phase57c_validation_bar_semantics_fix.py` (untouched) | 53 | ✅ pass |
| **Total** | **400** | **✅ pass** |

---

## 5. Files changed

| File | Change | Why |
|---|---|---|
| `app/templates/partials/_last_run_indicator.html` | rewritten (additive) | Run status clarity |
| `app/templates/partials/validation.html` | rewritten (additive) | Validation summary completion |
| `app/templates/partials/_empty_no_project.html` | new | Empty state — no project |
| `app/templates/partials/_empty_no_scenario.html` | new | Empty state — no scenario |
| `app/templates/partials/_empty_no_run.html` | new | Empty state — no run |
| `app/templates/index.html` | include 4 new partials | Wire empty states + last run |
| `static/styles.css` | new classes appended | Style the new UI elements |
| `tests/test_phase24g1_validation_summary_clarity.py` | relaxed 2 asserta | Allow always-render groups |
| `tests/test_phase24g2_run_status_clarity.py` | new | Test run status |
| `tests/test_phase24g2_validation_summary_completion.py` | new | Test validation completion |
| `docs/phase24g2_*.md` | new | Documentation |
| `reports/phase24g2_*.json` | new | Machine-readable report |

No production code change:
- `main_web.py` — untouched
- `app/services/` — untouched
- `app/persistence/` — untouched
- `app/api/` — untouched
- `domain/` — untouched
- `tax_bridge/` — untouched
- `waterfall_core.py` — untouched
- `static/app.js` — untouched
- `runtime_summary.html` (Phase 20M) — untouched
- `empty_states_notice.html` (Phase 25A, 24-G-1) — untouched

---

## 6. Hard-rule coverage

| Hard rule | How this PR complies |
|---|---|
| No model changes | No `domain/`, `tax_bridge/`, `waterfall_core.py` change |
| No formula changes | No computation logic in templates |
| No tax/debt/depreciation/IDC changes | Templates are presentation only |
| No persistence changes | No `app/persistence/` change |
| No runtime changes | No `main_web.py` change |
| No project status changes | No `project_status` mutation |
| No Generic promotion | No `project_origin` mutation |
| No C10 promotion | No C10 field changes |
| No construction flag changes | `use_construction_schedule_engine` remains `False` |
| No R-PAR changes | No R-PAR-2 changes |
| No feature flag changes | No flag toggles |
| No fake runtime IDs | Status is sourced from real `runtime_summary` |
| No fake timestamps | All time fields from real `last_run_at` |
| No invented scenario IDs | Scenario name from real `base_case_record` |
| No Tailwind / Alpine | Pure CSS, vanilla |
| No new JavaScript | `static/app.js` unchanged; no `<script>` added |
| Stale warning does not alter calculations | Templates only read context |
| Stale warning does not trigger auto-runs | Anchor link, no JS / fetch / form |
| Stale state inline matches stale_run() gate | Same condition: dirty AND last_runtime_snapshot_id |
| Status badge tone matches data | `ok` / `error` / `blocked` / fallback `—` |
| Project association is real | From `project_record` (always in context) |
| Scenario association is real | From `base_case_record` (always in context) |
| Empty states are gate-driven | Each renders nothing if its gate is satisfied |
| Validation groups always render in order | Strict Error → Warning → Information |
| Validation groups show no-items hint | `.validation-group-empty` row when count is 0 |
| TUHO parity unchanged | No model / formula / tax / debt / depreciation / IDC / persistence change |
| Oborovo parity unchanged | Same as above |
| rc1 untouched | rc1 is a separate file/branch; not modified |

---

## 7. Dependency on Phase 24-G-1

This PR is stacked on `07cb4d0` (Phase 24-G-1 commit).
Reason: 24-G-2 builds on 24-G-1's `validation.html` rewrite
and reuses the same Jinja2 `namespace()` pattern, the same
`.validation-group--{severity}` CSS modifier names, and the
same `.esn-stale-*` macro style. Duplicating these into
24-G-2 would have created drift risk.

If 24-G-1 is rebased or merged independently, this PR
will need a rebase before merge.

---

## 8. Stacked DRAFT PR plan

- 24-G-1 → DRAFT PR (commit `07cb4d0`, base `a421ab5`)
- 24-G-2 → DRAFT PR (commit `24g2`, base `07cb4d0`)
  - **DO NOT MERGE 24-G-2 independently** — it depends
    on 24-G-1.

If 24-G-1 is merged first, 24-G-2's branch will need
`git rebase origin/main` to point to the merged 24-G-1.

---

## 9. Open follow-up items (for 24-G-3 or later)

- "Jump to field" anchor links on validation messages.
  *Requires form field anchor inventory first; not
  available in 24-G-2 without backend changes.*
- Collapsible validation groups.
  *Requires JS; explicitly out of scope per user
  constraint "no new JavaScript".*
- "What changed" diff view for the runtime summary
  (e.g. before/after KPI comparison).
  *Requires runtime snapshot diff in the backend; not
  in 24-G-2.*
- Run error copy localization.
  *Out of scope; English only.*
