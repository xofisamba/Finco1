# UI-2.5 — Stale result warning

## Status

DRAFT, awaiting user visual review.

## Summary

Improves stale result warning visibility on the workspace dashboard by wiring
the existing `stale_run()` macro from `partials/empty_states_notice.html` into
`app/templates/index.html`, gated on existing `runtime_summary` context.

## What changed

### `app/templates/index.html`

- Imports `stale_run` macro from `partials/empty_states_notice.html`
- Renders `{{ stale_run() }}` inside `{% if runtime_summary %}` block
- The macro produces the existing `.empty-state-notice--warn` warning element

### `tests/test_ui2_5_stale_result_warning.py`

- 43 new tests covering: macro reuse, conditional rendering, safe copy,
  forbidden no-go term scan, no backend/persistence/services changes,
  no CSS modifications, no JS financial calculations, integration
  with existing `runtime_summary` context.

## Hard gates verified

- Only `app/templates/index.html` modified
- No new template files created (macro is reused, not redefined)
- No CSS changes (existing `.empty-state-notice--warn` is reused)
- No `static/app.js` changes
- No backend/service/persistence/model changes
- No `app/runtime_impact_taxonomy.py` changes
- No frontend dependency changes
- No `:root` CSS variable changes
- No new forbidden UI claims
- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` untouched
- All 756 relevant tests pass

## Context limitation (per Phase 54F-J)

The context key `inputs_changed_since_run` was documented as MISSING in
Phase 54F. Per UI-2.5 spec, we do NOT add backend context. The
`{% if runtime_summary %}` guard uses the existing context that
indicates "a model run exists at all" — a conservative gate that
prevents showing "stale" on a brand-new project with no run.

## Copy

The existing `stale_run()` macro produces:

- Title: "Stale run"
- Description: "The current outputs are from a previous run. If you changed
  the draft after the last run, run again to reflect your changes. Export
  will use the last clean run."

This copy is conservative and uses no no-go terms.

## Recommendation

Review this PR (#467) for visual confirmation. If approved, merge and
proceed to UI-2.6.
