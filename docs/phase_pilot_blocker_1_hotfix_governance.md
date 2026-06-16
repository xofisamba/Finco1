# HOTFIX-PILOT-BLOCKER-1 — Working copy runtime routing + Dashboard

**Branch:** `hotfix-pilot-blocker-1-routing`
**Type:** Hotfix (presentation / routing only)
**Priority:** P0 (pilot-blocking)
**Date:** 2026-06-16

## Trigger

PILOT ACCEPTANCE WALKTHROUGH (first-time internal pilot simulation,
post-IRR-ANOMALY-1-FIX main) returned **FAIL / Not pilot-ready** with
3 P0 + 2 P1 blockers (1 P1 was a false positive; net: 3 P0 + 1 P1).

## Blockers addressed

| # | Severity | Issue | Root cause | Fix |
|---|----------|-------|------------|-----|
| P0-1 | P0 | Run updates wrong workspace | Hidden form `active_project="tuho"` carried over from source. `_resolve_project_record` matched the SOURCE project, not the working copy. | F1 + F4 |
| P0-2 | P0 | Dashboard shows "—" for all KPIs | `build_dashboard_kpis(waterfall_result, ...)` read `getattr(project_record, "last_waterfall_result", None)` which is always None. | F3 |
| P0-3 | P0 (consequence) | Working copy has no runtime summary | P0-1 consequence. Auto-resolved by F1 + F4. | F1 + F4 |
| P1-1 | P1 | False "Protected original" banner on working copy | `_factory_lock_indicator.html` gate triggered on `template_source` substring match without checking `project_origin`. | F2 |
| P1-2 | P1 | Working copy `baseline_snapshot` has wrong identity | `execute_project_save_as_route` copied `source.baseline_snapshot` verbatim into the new record. | F1 |
| P1-3 | FALSE POSITIVE | Runtime guard mismatch | Test-flow artifact (modified form values). Not a real bug. | n/a |

## Fixes (4, all coupled)

### F1 — Working copy creation sanitizes snapshot

**File:** `app/services/project_save_as_service.py`
**Type:** Service-layer (presentation-routing, no formula / model change)

After `save_project` creates the new record, the new record's
`baseline_snapshot` is built from the source's snapshot but with
`active_project`, `project_origin`, and `project_name` overwritten
to reflect the working copy's own identity. The `save_workspace_state`
call now receives the **sanitized** snapshot as both
`draft_snapshot` and `saved_snapshot`.

Without this, the working copy's draft_snapshot carries
`active_project="tuho"` and `project_origin="factory_template"`,
which is exactly the value the hidden form will pass to `/run`,
causing `_resolve_project_record` to match the SOURCE.

### F2 — Protected banner gate

**File:** `app/templates/partials/_factory_lock_indicator.html`
**Type:** Template-only (no JS, no styling, no service change)

The partial now uses the same `is_protected_reference` service
already used by `_state_banner.html` (P2-FIX-7). The pre-fix
template_source substring matching (`'tuho' in _ts_l` etc.) was
producing false positives for working copies whose
template_source is "tuho" but project_origin is "user_created".

### F3 — Dashboard KPI load

**File:** `app/ui/dashboard.py` + `main_web.py:_build_index_dashboard_context`
**Type:** Presentation-only (no formula, no chart, no SVG change)

`build_dashboard_kpis(waterfall_result, project_record,
realized_gearing_pct)` is now `build_dashboard_kpis(last_runtime_summary,
project_record, realized_gearing_pct)`. The function now reads from
the workspace's `last_runtime_summary` dict (the same authoritative
source already used by `build_dashboard_kpis_from_raw_kpis` for the
OOB update path). The function reuses that same helper for the
value formatting, so initial dashboard load and the post-run OOB
update are guaranteed to render the same values.

The call site in `main_web.py:_build_index_dashboard_context` now
passes `workspace_state.last_runtime_summary` instead of
`getattr(project_record, "last_waterfall_result")` (which was
always None — there is no such field on ProjectRecord).

The chart helpers (`build_revenue_ebitda_series`, etc.) now receive
a small `_StubW` object that exposes `.summary` and `.yearly_series`
attributes, built from the same `last_runtime_summary` dict, so the
chart API is preserved without any change to the chart builders.

### F4 — Defense in depth for /run routing

**File:** `main_web.py` (/run route)
**Type:** Routing-only (no model, no service, no formula change)

After the form is parsed and `_collect_form_snapshot` builds the
form snapshot, the route now reads the URL `?project=` query param
and, if it differs from the form's `active_project` AND it points
to a real user-owned project, overrides the snapshot's
`active_project` (and `project_origin` if the URL rec is
`user_created`).

This is a defense in depth measure that protects against stale
hidden form state. Combined with F1 (the snapshot no longer
carries the source's `active_project`), it ensures the /run route
always updates the correct workspace, regardless of which
stale form value is submitted.

## Constraints (all preserved, all pinned by tests)

- `app/waterfall_core.py` MD5: `6bf49f33efc989736c17cea0cb9b7723` (unchanged)
- `app/project_factories.py` MD5: `3350c93a7689bb3f5e717a064adcd106` (unchanged)
- No `app/persistence/` schema change
- No `app/excel_export.py` change
- No `app/services/run_service.py` change
- No tax / debt / depreciation / IDC / construction / R-PAR / C10 change
- No R99 / R102 / G20 promotion
- No `static/app.js` change
- No `main_api.py` change
- No Tailwind / Alpine / React / Vue / Svelte / Chart.js / Plotly / D3
- No new dependency
- rc1 SHA preserved
- `use_construction_schedule_engine` remains False
- Phase 20B invariant (`SCENARIO_INPUT_FIELDS` 21 keys) preserved
- 21/21 Phase 51F parity guardrails green

## Test evidence

`tests/test_phase_pilot_blocker_1_fix.py` — 16 new tests, 15 PASS + 1 SKIP
(TUHO baseline test skipped when seed data missing).

Cross-arc allowlist patches (5 test files):
- `tests/test_p1_compare_validation.py`
- `tests/test_phase_m4_scenario_matrix_run.py`
- `tests/test_phase_scenario1_base_case_init.py`
- `tests/test_phase_scenario2_fixes.py`
- `tests/test_phase_ux4cde_pilot_polish.py`

All 4 cross-arc file-scope guards pass.

## Pilot readiness

After this hotfix, the pilot walkthrough P0/P1 blockers are
resolved at the source level. Pilot acceptance should be
re-run on the next build to confirm green.

The pilot polish items identified during the walkthrough
(UX-1: duplicated PL indicator, contextual placeholders,
dirty-input markers, post-run auto-switch to Dashboard)
are **non-blocker** items and are not in this hotfix scope.
