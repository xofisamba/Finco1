# Phase P1-CLEANUP-SPRINT-2 — Low-risk Pilot Polish

## Context

After PILOT-HOTFIX-3, the internal pilot loop passes end-to-end (no P0
blockers). P1-CLEANUP-SPRINT-1 audited three low-risk P1 / UX items;
this PR implements them without touching any model, debt, persistence,
or export logic.

## Goals

- No financial formula / IDC / funding / debt / tax / construction changes
- No persistence schema changes
- No routing redesign
- No factory / waterfall changes
- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` untouched
- Engine MD5 `6bf49f33efc989736c17cea0cb9b7723` unchanged
- Factory MD5 `cf73065b8a26aa3f19629829e46260d9` unchanged

## Tasks

### TASK A — POST /scenarios/{id}/update-overrides dual body parsing

**Problem**: The endpoint called `await request.json()` unconditionally.
If a client sent form-data (e.g. a non-HTMX POST, an internal tool, a
debugger replay), the endpoint returned 500 / 422.

**Fix** (`main_web.py` `update_overrides_endpoint`): Branch on
`content-type`:
- `application/json` → existing JSON parse (unchanged). Malformed JSON
  returns 400 with a friendly error instead of bubbling to 500.
- Anything else → `await request.form()` → parse submitted fields into
  the overrides dict. Framework keys (`project_code`, `scenario_id`,
  `csrf_token`, `_dirty_*`) are skipped so the dict represents only
  user override values.

**Invariants preserved**:
- JSON behaviour is bit-identical.
- Scenario persistence semantics unchanged.
- Matrix override logic unchanged.

### TASK B — Editable badge cleanup

**Problem**: P50 Hours was editable for user-created projects but the
template line included `"Template"` in the True branch of the
conditional, which could be misread; PPA Term was editable with no
badge at all (no driver status indicator).

**Fix** (`app/templates/partials/inputs_section.html`):
- P50 Hours: confirmed the conditional `badge=(None if is_user_project
  else "Template")` keeps user projects free of "Template" lock. Added
  a `badge_title` for tooltip context.
- PPA Term: replaced `badge_title` only with `badge=(None if
  is_user_project else "Template")` plus `badge_class="badge-pass" if
  is_user_project else "badge-muted"`. Now user projects see no
  Template badge (badge=None → no badge rendered).

**Invariants preserved**:
- Reference projects (TUHO, Oborovo) keep "Template" / "Protected"
  semantics. The False branch of the conditional still produces
  `"Template"`.
- No runtime / data model changes.
- Pure template label fix.

### TASK C — Landing page Home section cards

**Problem**: `GET /` (no `?project=...`) renders the My Projects table
on a standalone page. The desired product vision is a Home that
provides quick navigation to Projects / Inputs / CAPEX / OPEX /
Results / Scenarios.

**Fix** (`app/templates/partials/project_home.html` +
`static/styles.css`):
- Added a "Quick actions" strip with three cards: **New Project**,
  **Open Reference Projects**, and **Continue Modelling** (the last
  one only renders if the user has at least one project, and links to
  their most-recent project by `home_user_projects[0]`).
- Added a "Sections" strip with five chips: Inputs, CAPEX, OPEX,
  Results, Scenarios. When the user has projects, each chip links to
  `/?project=<recent>&tab=<key>`. When the user has no projects, the
  chips render as disabled spans with a "Create a project to enable"
  tooltip.
- No routes added. No redirects added. No state-mutation.

**Invariants preserved**:
- The My Projects table is unchanged.
- `project_home_page.html` (standalone wrapper) is unchanged.
- All existing GET routes (`/?project=X`, `/projects/new`,
  `/projects/browse`) work as before.
- No auto-redirect from `/` to `/<project>` (per P1-CLEANUP-SPRINT-2
  constraints: "Do NOT auto-redirect to last project").

## Files Changed

| File | Status | Lines |
|---|---|---|
| `main_web.py` | M | +47 / -3 |
| `app/templates/partials/inputs_section.html` | M | +2 / -2 |
| `app/templates/partials/project_home.html` | M | +62 / -0 |
| `static/styles.css` | M | +90 / -0 |
| `tests/test_phase_p1_cleanup_sprint_2_low_risk_pilot_polish.py` | A | +440 / -0 |
| `docs/phase_p1_cleanup_sprint_2_low_risk_pilot_polish.md` | A | this file |
| `reports/phase_p1_cleanup_sprint_2_low_risk_pilot_polish.md` | A | walkthrough report |

## Tests

21 tests across 5 classes:

- `TestTaskAUpdateOverrides` — 4 tests for JSON / form-data parsing
- `TestTaskBEditableBadgeCleanup` — 4 tests for badge conditional logic
- `TestTaskCLandingPageSectionCards` — 5 tests for landing-page cards
- `TestConstraintsPreserved` — 5 tests for rc1 / Engine MD5 / Factory
  MD5 / file-scope / forbidden-files guards
- `TestRouteBehaviourIntegration` — 3 tests for end-to-end route
  behaviour (no crash on form-data)

## Constraints Honoured

- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` — verified
  ancestor of HEAD post-merge.
- Engine MD5 `6bf49f33efc989736c17cea0cb9b7723` — verified unchanged.
- Factory MD5 `cf73065b8a26aa3f19629829e46260d9` — verified unchanged.
- No `waterfall_core.py` / `project_factories.py` / `input_adapter.py`
  / `db.py` / `repository.py` / `run_service.py` / `download_service.py`
  / `scenario_update_overrides_service.py` changes (file-scope guard
  test).
- No persistence schema changes.
- No routing redesign.
- No financial formula changes.
- No tax / debt / construction changes.
- No R99 / R102 / G20 changes.
- TUHO debt 43,359 kEUR + Oborovo debt 42,852.27 kEUR bit-identical.

## Out of Scope

- Reference Excel workbooks for Generic Solar / Wind / BESS (separate
  effort; estimated 80-104h, see P1-CLEANUP-SPRINT-1 Task 4).
- Multi-user cross-project safety test.
- Real auth / CSRF end-to-end test (current tests use TestClient
  without auth; the auth gate at the top of the route is preserved).

## Stop-After-Report Contract

This PR is DRAFT. Do NOT mark ready, do NOT merge before review.