# HOTFIX-PILOT-BLOCKER-1 — Before / After Evidence

**Date:** 2026-06-16
**Branch:** `hotfix-pilot-blocker-1-routing` (base: `main @ 355da4a`)
**Type:** Hotfix (presentation / routing only)

## Pilot walkthrough failure summary (pre-fix)

The first end-to-end pilot walkthrough on main @ 355da4a surfaced
3 P0 + 2 P1 blockers. One P1 was a false positive, so net: 3 P0 +
1 P1. This document records the user-visible evidence for each
blocker and the post-fix behaviour.

---

## P0-1: Run updates wrong workspace

### Pre-fix (broken)

Scenario: User opens TUHO reference workspace, creates a working
copy via the Save As / Confirm-First-Edit-Copy flow, edits the
working copy, clicks Run.

- The working copy's `draft_snapshot` carried the inherited
  `active_project="tuho"` and `project_origin="factory_template"`.
- The hidden form on the workspace page reads those values from
  the workspace draft, so the form submitted `active_project=tuho`.
- `/run` resolved the active project via `_resolve_project_record`,
  which uses `get_project_record(user_id=1, project_code="tuho")`
  first. That returns the **source** (factory template) record.
- `record_workspace_runtime` then updated the SOURCE workspace's
  `last_runtime_summary`, not the working copy's.

**Visible symptom:** User edits the working copy, clicks Run, and
sees the dashboard update reflect numbers from the TUHO reference
(unchanged from its own previous run), not the working copy's
modified inputs.

### Post-fix (working)

- F1 sanitizes the snapshot at working-copy creation time, so
  `active_project` becomes the new code, `project_origin` becomes
  `user_created`, `project_name` becomes the new name.
- F4 (defense in depth) overrides the form's `active_project`
  with the URL's `?project=` if the URL points to a real
  user-owned project.
- `_resolve_project_record` now matches the working copy.
- `record_workspace_runtime` updates the working copy's
  `last_runtime_summary`.

**Test pinning:** `test_working_copy_does_not_inherit_source_active_project`

---

## P0-2: Dashboard shows "—" for KPIs

### Pre-fix (broken)

- The dashboard initial-load path called
  `build_dashboard_kpis(waterfall_result, project_record, ...)`
  where `waterfall_result = getattr(project_record,
  "last_waterfall_result", None)`.
- `ProjectRecord` has no `last_waterfall_result` field, so
  `waterfall_result` was always `None`.
- `getattr(None, "summary", None)` returned `{}`.
- All KPIs fell through to `"missing"` status, rendered as "—".

**Visible symptom:** After a successful Run, the Dashboard KPI
cards (Project IRR, Equity IRR, Senior Debt, Min DSCR, Avg DSCR,
Y1 Revenue, Y1 EBITDA) all rendered "—" instead of the runtime
values.

**Note:** The post-run OOB update path used a different helper,
`build_dashboard_kpis_from_raw_kpis`, which read from
`workspace.last_runtime_summary` and worked correctly. The OOB
update only triggered on HTMX swap, not on initial page load.

### Post-fix (working)

- `build_dashboard_kpis` now takes `last_runtime_summary` (dict)
  as the first argument.
- It reuses `build_dashboard_kpis_from_raw_kpis` for value
  formatting, guaranteeing initial load and OOB update use the
  same path.
- Call site passes `workspace_state.last_runtime_summary`.
- If the summary is None or empty, KPIs render as "—" with
  `status="missing"` (same as before — no false-positive "0" or
  random values).

**Test pinning:** `test_build_dashboard_kpis_with_runtime_summary`,
`test_build_dashboard_kpis_with_none_summary`,
`test_dashboard_index_renders_runtime_kpis`

---

## P0-3: Working copy has no runtime summary (consequence)

### Pre-fix

A consequence of P0-1: the working copy's `last_runtime_summary`
was never updated because `/run` updated the source workspace
instead.

### Post-fix

Auto-resolved by P0-1 fix. After F1 + F4, `/run` updates the
working copy's `last_runtime_summary`, and F3 reads it for the
dashboard.

---

## P1-1: False "Protected original" banner on working copy

### Pre-fix (broken)

- `_factory_lock_indicator.html` checked
  `elif _ts_l and ('tuho' in _ts_l or 'oborovo' in _ts_l or 'factory' in _ts_l)`.
- Working copy has `template_source="tuho"` (inherited from
  source) and `project_origin="user_created"` (set by save-as).
- The substring match on template_source triggered the banner
  for the working copy.

**Visible symptom:** Working copy (which the user can edit) shows
"Protected original — TUHO" banner, suggesting it cannot be
edited. This contradicts the whole point of the C2 first-edit-copy
flow (P2-FIX-3).

### Post-fix (working)

- The partial now uses the same `is_protected_reference` service
  used by `_state_banner.html` (P2-FIX-7).
- The service checks both `project_origin == "factory_template"`
  AND `template_source` in the protected set.
- Working copy has `project_origin="user_created"`, so
  `is_protected_reference` returns False, and the banner does not
  render.

**Test pinning:** `test_factory_lock_indicator_uses_is_protected_reference`,
`test_working_copy_does_not_show_protected_banner`,
`test_tuho_reference_still_shows_protected_banner`

---

## P1-2: Working copy baseline_snapshot has wrong identity (root)

### Pre-fix

`execute_project_save_as_route` called `save_project` to create
the new record, then called `save_workspace_state` passing
`source.baseline_snapshot` as both `draft_snapshot` and
`saved_snapshot`. The source's `baseline_snapshot` carried
`active_project="tuho"` and `project_origin="factory_template"`.

This is the **root cause** of P0-1. F1 fixes this.

### Post-fix

- After `save_project` returns the new record, the new record's
  `project_code`, `project_name`, and `project_origin` are
  available.
- The snapshot is mutated: `active_project=new_code`,
  `project_origin="user_created"`, `project_name=new_name`.
- Other fields (capacity, tariff, capex, etc.) are preserved
  unchanged.

**Test pinning:** `test_working_copy_snapshot_has_own_active_project`

---

## Test results

| File | Tests | Pass | Skip |
|------|-------|------|------|
| `tests/test_phase_pilot_blocker_1_fix.py` | 16 | 15 | 1 (TUHO baseline, no seed) |
| Cross-arc file-scope guards (5 files) | 5 | 5 | 0 |
| Total | 21 | 20 | 1 |

## File-scope review

10 files changed (all within allowed scope):

| File | Allowed? | Reason |
|------|----------|--------|
| `app/services/project_save_as_service.py` | NEW (F1) | Sanitize snapshot at copy time |
| `app/templates/partials/_factory_lock_indicator.html` | NEW (F2) | Use `is_protected_reference` gate |
| `app/ui/dashboard.py` | NEW (F3) | Refactor `build_dashboard_kpis` |
| `main_web.py` | NEW (F3 call site, F4 route) | Pass `workspace_state` to dashboard builder; URL `?project=` override |
| `tests/test_phase_pilot_blocker_1_fix.py` | NEW (test) | New test file |
| `tests/test_p1_compare_validation.py` | Allowlist patch | `tests/test_phase_pilot_blocker_1` + `app/services/...` + `app/templates/...` + `app/ui/dashboard.py` |
| `tests/test_phase_m4_scenario_matrix_run.py` | Allowlist patch | Same as above |
| `tests/test_phase_scenario1_base_case_init.py` | Allowlist patch | Same as above |
| `tests/test_phase_scenario2_fixes.py` | Allowlist patch | Same as above |
| `tests/test_phase_ux4cde_pilot_polish.py` | Allowlist patch | Same as above |

## Constraints confirmed

- `app/waterfall_core.py` MD5: `6bf49f33efc989736c17cea0cb9b7723` ✅
- `app/project_factories.py` MD5: `3350c93a7689bb3f5e717a064adcd106` ✅
- rc1 SHA: `b425a0708719eaa5e1d922b1008e5609758e0ad4` ✅
- No `app/persistence/` schema change ✅
- No `app/excel_export.py` change ✅
- No `app/services/run_service.py` change ✅
- No tax / debt / IDC / construction change ✅
- No R99 / R102 / G20 promotion ✅
- No `static/app.js` change ✅
- No new dependency ✅

## Pilot readiness status

After this hotfix, the original 3 P0 + 1 P1 blockers are
resolved. Pilot acceptance should be re-run on the next build to
confirm green. The remaining pilot polish items (UX-1: duplicated
PL indicator, contextual placeholders, dirty-input markers,
post-run auto-switch to Dashboard) are non-blockers and remain on
the post-pilot backlog.
