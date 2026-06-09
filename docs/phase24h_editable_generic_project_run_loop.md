# Phase 24-H — Editable Generic Project Run Loop

> Type: UI + minimal-orchestration
> Status: DRAFT
> Date: 2026-06-09
> Base SHA: `f53fd6d` (post-#572, post-24-G-closure)
> Branch: `phase24h-editable-generic-project-run-loop`
> Hard constraints:
> - Generic exploratory path only
> - Do NOT touch TUHO / Oborovo reference parity path
> - No new financial formulas
> - No fake outputs / fake runtime IDs / fake validation status
> - No new model / formula / tax / debt / depreciation / IDC / runtime changes
> - No C10 / R-PAR / construction promotion
> - No schema migration (unless unavoidable and explicitly reported)
> - No Tailwind / Alpine
> - rc1 untouched

---

## 0. Purpose

Phase 1 of Sprint 24-H (per the closure review of the G track,
PR #572). The goal is to make FincoGPT usable as a **basic
modelling tool** for finance users who want to sketch a
Generic Solar or Generic Wind project, edit the safe
assumptions, save them, run the model, and see the financial
outputs respond.

The pre-existing scaffold already supports this loop in
principle: `/projects/new` accepts `template_source =
generic_solar` / `generic_wind` and creates a `user_created`
project record, which is editable in the inputs section
(`is_user_project = True` gates the editable inputs). The
`/run` route already routes `user_created` projects through
`_execute_user_created_path` in `app/services/run_service.py`.

What 24-H Phase 1 adds is the **exploratory labeling** that
makes the loop safe to use. Without the warning, a finance
user could mistake a sketch for a validated, lender-ready
result.

---

## 1. Scope

### 1.1 What this PR implements

1. **Editable Generic Project Workspace.** The pre-existing
   `inputs_section.html` partial already exposes the safe
   editable fields listed in the brief (project name,
   technology, capacity MW, COD, construction months, horizon
   years, total CAPEX, P50 hours, PPA tariff, PPA term, OPEX
   Y1, gearing, interest rate, tenor, target DSCR). These
   are gated by `editable=is_user_project`. The new
   `is_exploratory_project` flag is added next to
   `is_user_project` so the **same** editability is available
   for `user_created` Generic Solar / Generic Wind projects,
   and the **same** read-only behaviour is preserved for
   `factory_template` references (TUHO, Oborovo).

2. **Save → Run → Output loop.** The pre-existing routes
   `/projects/create`, `/scenarios/state/draft`,
   `/scenarios/save`, `/run`, and `/save-run` already work
   for `user_created` projects. The exploratory warning is
   surfaced in the runtime summary when the project is
   exploratory, but the runtime path itself is **unchanged**.

3. **Exploratory labeling.** A new warning appears in:
   - `app/templates/partials/inputs_section.html` — below
     the read-only notice, above the dirty indicator.
   - `app/templates/partials/_last_run_indicator.html` —
     as an additional row in the run indicator.
   - `app/templates/partials/export_registry.html` — at
     the top of the panel.

   All three sites use the same data attributes
   (`data-exploratory-warning="true"`,
   `data-exploration-source="..."`) and the same copy:
   "Exploratory / not Excel-parity validated. Outputs are
   not lender-ready, audit-ready, or bank-approved. Do not
   use for external signoff."

4. **Reference project safety preserved.** TUHO and Oborovo
   remain `factory_template` and remain read-only. The
   `_resolve_project_record` function still produces
   `project_origin="factory_template"` for the factory
   selections. The waterfall construction flag
   (`use_construction_schedule_engine`) remains `False`. The
   C10 / R-PAR / construction promotion items are unchanged.

### 1.2 What this PR does NOT do

- No new financial formulas.
- No new runtime paths.
- No new persistence schema.
- No C10 / R-PAR / construction promotion.
- No schema migration.
- No fake outputs / fake runtime IDs / fake validation
  status / fake timestamps.
- No `app.js` / Tailwind / Alpine changes.
- No TUHO / Oborovo reference parity drift.
- No factory project mutation.
- No `rc1` changes.
- No model / formula / tax / debt / depreciation / IDC
  changes.

---

## 2. Implementation

### 2.1 `main_web.py` — context flag

A new context flag is added in the 3 places that already
pass `is_user_project` to the template:

```python
# Phase 24-H: exploratory warning flag (user_created + generic)
"is_exploratory_project": (
    project_record.project_origin == "user_created"
    and (project_record.template_source or "").strip().lower()
    in {"generic_solar", "generic_wind"}
),
```

The flag is **read-only** in the template. It is computed
from the existing `project_record` and is not stored
anywhere. The factory template path
(`project_origin="factory_template"`) and the non-generic
user-created path
(`template_source` not in `{generic_solar, generic_wind}`)
both evaluate to `False`.

This is the only change to `main_web.py`. The route
handlers, the form parsing, the dependency bundle, the
response rendering, and the persistence layer are
unchanged.

### 2.2 `app/templates/partials/inputs_section.html`

A new `inp-exploratory-notice` block is added below the
read-only notice, gated by `{% if is_exploratory_project %}`:

```html
{% if is_exploratory_project|default(false) %}
<div class="inp-exploratory-notice"
     role="note"
     aria-label="Exploratory / not Excel-parity validated"
     data-exploratory-warning="true"
     data-exploration-source="inputs-section">
  <span class="badge badge-warn">EXPLORATORY</span>
  <span>
    <strong>Exploratory / not Excel-parity validated.</strong>
    This Generic {{ project_ctx.technology or 'project' }} is
    editable for sketching scenarios, but the runtime output
    has not been validated against an Excel reference. Outputs
    are <em>not</em> lender-ready, audit-ready, or
    bank-approved. Use only for exploratory analysis.
  </span>
</div>
{% endif %}
```

The block is **additive**. It does not modify the existing
inputs (which remain gated by `is_user_project`).

### 2.3 `app/templates/partials/_last_run_indicator.html`

A new `last-run-indicator__row--exploratory` row is added
inside the existing `<aside>`, gated by the new
`is_exploratory` local flag (computed from
`is_exploratory_project`):

```html
{% if _is_exploratory %}
<div class="last-run-indicator__row last-run-indicator__row--exploratory"
     role="note" aria-label="Exploratory / not Excel-parity validated"
     data-exploratory-warning="true"
     data-exploration-source="runtime-summary">
  <span class="last-run-indicator__exploratory-badge"
        title="This project is exploratory / not Excel-parity validated">EXPLORATORY</span>
  <span class="last-run-indicator__exploratory-hint">
    Exploratory / not Excel-parity validated. Outputs are
    not lender-ready, audit-ready, or bank-approved. Do not
    use for external signoff.
  </span>
</div>
{% endif %}
```

The block is **additive**. The existing OK / ERROR / BLOCKED
/ NO RUN status badge, project association, scenario
association, stale / fresh indicator, run reference, run
time, and run error rows are unchanged.

### 2.4 `app/templates/partials/export_registry.html`

A new `export-explorer-warning` block is added at the top
of the panel, gated by `{% if is_exploratory_project %}`:

```html
{% if is_exploratory_project|default(false) %}
<div class="export-explorer-warning"
     role="note"
     aria-label="Exploratory project / not Excel-parity validated"
     data-exploratory-warning="true"
     data-exploration-source="export-registry">
  <span class="badge badge-warn">EXPLORATORY</span>
  <span>
    <strong>Exploratory / not Excel-parity validated.</strong>
    This export registry is for an exploratory Generic
    project. Artefacts generated for exploratory projects
    are <em>not</em> lender-ready, audit-ready, or
    bank-approved. They are for internal sketching and
    review only.
  </span>
</div>
{% endif %}
```

The block is **additive**. The empty-state, intro lead,
per-card lineage rows, and 8 export cards are unchanged.

### 2.5 `static/styles.css`

5 new classes appended to the end of `static/styles.css`:

| Class | Purpose |
|---|---|
| `.inp-exploratory-notice` | Inputs-section warning block |
| `.last-run-indicator__row--exploratory` | Run indicator row |
| `.last-run-indicator__exploratory-badge` | "EXPLORATORY" badge |
| `.last-run-indicator__exploratory-hint` | Body copy in the row |
| `.export-explorer-warning` | Export registry warning block |

All 5 are **additive**. The `:root` block count remains 3
(UI-2.5 invariant). The amber color (`#f59e0b`) is the same
as the existing `badge-warn` tone, so the warning sits in
the same visual hierarchy as the G20 / R99 / R102 blocked
notices.

---

## 3. Tests

29 new tests in `tests/test_phase24h_editable_generic_run_loop.py`:

| Test class | Tests | What it verifies |
|---|---|---|
| `TestCSSAdditive` | 2 | `:root` count = 3 (unchanged); all 5 new classes present |
| `TestContextFlag` | 2 | Flag appears 3 times in `main_web.py`; uses both `project_origin` AND `template_source` checks |
| `TestInputsSectionWarning` | 5 | Block present; uses `is_exploratory_project` flag; renders when True; absent when False; absent when factory |
| `TestLastRunIndicatorWarning` | 5 | Block present; uses flag; renders when True and run exists; absent when False; absent when no run |
| `TestExportRegistryWarning` | 4 | Block present; uses flag; renders when True; absent when False |
| `TestFactoryUntouched` | 5 | `_resolve_project_record` keeps `factory_template` origin; `_execute_user_created_path` unchanged; `waterfall_core` gate still defaults to `False`; rc1 not in diff; no flag flips |
| `TestNoFakeData` | 2 | No fake runtime IDs in templates; no fake data in `main_web.py` |
| `TestEndToEnd` | 3 | `projects_create_service` sets `project_origin='user_created'`; exploratory flag computed correctly; warning appears in rendered inputs section |
| `TestNewProjectForm` | 1 | Generic Solar / Wind are exposed as `template_source` options |

All 29 tests pass.

### Regression

- 24-G-closure: 30/30 ✅
- 24-G-1: 47/47 ✅
- 24-G-2: 75/75 ✅
- 24-G-3: 69/69 ✅
- Inventory: 17/17 ✅
- 24-H: 29/29 ✅
- **Total: 267/267 ✅**

---

## 4. Hard constraints — verification

| Constraint | Verification |
|---|---|
| Generic exploratory path only | `is_exploratory_project` is `True` only when `project_origin == 'user_created'` AND `template_source in {generic_solar, generic_wind}` |
| No TUHO / Oborovo reference parity drift | `_resolve_project_record` still produces `project_origin='factory_template'` for `tuho`, `oborovo` |
| No new financial formulas | Diff is only `main_web.py` (3 lines × 3 places) + 3 templates + CSS + tests + docs + report |
| No fake outputs / IDs / timestamps | All output / ID / timestamp data comes from existing `runtime_summary`, `project_record`, `workspace_state` (no new fields, no fabricated values) |
| No construction flag change | `waterfall_core.py` is unchanged; the gate still defaults to `False` |
| No C10 / R-PAR promotion | Not touched |
| No schema migration | `app/persistence/` is unchanged |
| No Tailwind / Alpine | Not touched |
| rc1 untouched | `git diff main...HEAD --name-only \| grep rc1` returns empty |
| `:root` count | 3 (unchanged) |
| Reusable CSS classes | 5 new classes appended; no existing class modified |

---

## 5. How a finance user uses this

### 5.1 Create a new exploratory Generic Solar project

1. Open `/projects/new`.
2. Fill in: project name (e.g. "My Sketch"), project type
   (Solar), template source (`generic_solar`).
3. Click Create Project.
4. The system creates a `user_created` project record with
   `template_source = generic_solar`. The system redirects
   to `/?project=<project_code>`.
5. The user is now in the project workspace. The Inputs
   tab is editable.

### 5.2 Edit assumptions and run

1. Edit any of the 15 safe fields (project name, COD,
   construction months, capacity MW, P50 hours, tariff,
   PPA term, total CAPEX, OPEX Y1, gearing, target DSCR,
   interest rate, tenor years, etc.).
2. The dirty indicator appears.
3. Click **Save Scenario** to persist.
4. Click **Run Model**.
5. The runtime executes through the pre-existing
   `_execute_user_created_path`. The runtime summary
   appears with the existing OK / ERROR / BLOCKED / NO
   RUN status badge. **The new "EXPLORATORY" warning is
   visible in the run indicator row, in the inputs
   section, and in the export registry.**

### 5.3 Export

- The export registry panel shows the new "EXPLORATORY"
  warning at the top.
- The G20 / R99 / R102 status badges remain. Disabled
  cards remain disabled. This is unchanged.
- Any artefact generated for an exploratory project is
  marked as such by the warning at the top of the
  registry. The export itself is not modified.

### 5.4 What the user can NOT do (and that's correct)

- The user **cannot** mistake a sketch for a validated
  result, because the EXPLORATORY warning is visible in
  the inputs section, the run indicator, and the export
  registry.
- The user **cannot** save the sketch to the TUHO or
  Oborovo factory template (the read-only notice still
  appears for factory projects, and the new flag is
  `False` for them).
- The user **cannot** flip the construction flag from
  the UI. `use_construction_schedule_engine` is not
  exposed in any input field.

---

## 6. Out of scope (deferred)

These items were considered and **deferred** to a later
phase:

- **Construction runtime / C10 promotion.** The construction
  engine remains unwired. The exploratory path uses the
  pre-existing `_execute_user_created_path`, which is the
  same path the C-series is preparing to wrap.
- **R-PAR-2 senior IDC resolution.** Not in scope for 24-H
  Phase 1.
- **Generic template Excel validation.** The brief is
  explicit: "Generic exploratory path only" — these are
  not validated against Excel. The warning is the
  safety net.
- **Multi-scenario branching for generic projects.** The
  current loop supports the base case + saved scenarios,
  but the comparison / scenario branch UX is unchanged.
- **Live sculpting / debt re-sizing.** Sprint 24-H
  recommendation from the G-track closure review
  (PR #572). This is the recommended **next** phase, not
  Phase 1.
- **Edit / duplicate the factory templates.** The
  read-only notice still appears for factory projects.
  The user must use `/projects/new` to create an
  editable copy.

---

## 7. Open DRAFT only (per task contract)

Per the task contract:

- ✅ Implementation
- ✅ Tests (29 new, all passing)
- ✅ Docs (this file)
- ✅ Report (`reports/phase24h_editable_generic_project_run_loop.json`)
- ✅ DRAFT only (not marked ready, not merged)
- ✅ Stop after report

cc @cofi19 — please review and approve before I mark ready
+ merge via the established workflow (close DRAFT + create
new non-DRAFT + squash merge, as with #565→#568 and
#569→#570).

---

## 8. References

- `docs/phase24g_closure_and_pilot_testability_review.md`
  (PR #572) — sprint planning input
- `docs/phase_pilot_ux_safe_track_inventory.md` (PR #564)
- `docs/phase24g1_stale_run_warning_validation_summary_clarity.md`
  (PR #567)
- `docs/phase24g2_run_status_clarity_validation_summary_completion.md`
  (PR #568)
- `docs/phase24g3_capex_sheet_readability_export_download_clarity.md`
  (PR #570)
- `app/services/run_service.py` — pre-existing
  `_execute_user_created_path` (Phase 17C snapshot binding,
  Phase 51B refactor)
- `app/services/projects_create_service.py` — pre-existing
  `/projects/create` orchestration
- `app/waterfall_core.py` — pre-existing
  `use_construction_schedule_engine` gate (default `False`)
- `docs/pilot_ux_walkthrough_checklist.md` — walkthrough
  anchor
- `docs/pilot_user_guide.md` — user guide
