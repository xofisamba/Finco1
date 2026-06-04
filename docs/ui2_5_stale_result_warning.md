# UI-2.5 — Stale result warning

## Status

DRAFT — fix applied after review feedback. Awaiting user visual review.

## Summary

Renders the existing `stale_run()` macro from
`partials/empty_states_notice.html` on the workspace dashboard when
**explicit, existing dirty-state signal** is available in the context.

## Critical: explicit stale signal only

Per review feedback, the warning renders **ONLY** when the existing
context signals both of these:

1. `workspace_state.dirty` is True — the draft has unsaved edits
2. `workspace_state.last_runtime_snapshot_id` is truthy — a previous
   runtime snapshot exists

This is the same condition the backend already detects in
`_workspace_state_meta()` (see "older than current draft" label) and
in `_build_export_lineage_ui_context()` (action_note for unsaved drafts).

The first version of this PR used `{% if runtime_summary %}` as the
gate. That was wrong: `runtime_summary` only proves a previous run
exists, NOT that the current draft has changed. That version was
replaced with the explicit `workspace_state.dirty + last_runtime_snapshot_id`
signal in commit `b7e1b5c` (post-feedback fix).

## What changed

### `app/templates/index.html`

- Imports `stale_run` macro from `partials/empty_states_notice.html`
- Renders `{{ stale_run() }}` inside
  `{% if workspace_state and workspace_state.dirty and workspace_state.last_runtime_snapshot_id %}`
- Removed the previous incorrect `{% if runtime_summary %}` guard.

### `tests/test_ui2_5_stale_result_warning.py`

- 48 tests covering: explicit signal source check, runtime_summary
  alone does NOT trigger, explicit signal DOES trigger, missing signal
  renders nothing, no no-go claims, no backend changes, no CSS mods,
  no JS financial calc, no invented context.

## Hard gates verified

- Only `app/templates/index.html` and tests/docs/report modified
- No new template files created (macro is reused, not redefined)
- No CSS changes (existing `.empty-state-notice--warn` is reused)
- No `static/app.js` changes
- No backend/service/persistence/model changes
- No `app/runtime_impact_taxonomy.py` changes
- No frontend dependency changes
- No `:root` CSS variable changes
- No new forbidden UI claims
- rc1 SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` untouched
- 761 relevant tests pass

## Copy

The existing `stale_run()` macro produces:

- Title: "Stale run"
- Description: "The current outputs are from a previous run. If you changed
  the draft after the last run, run again to reflect your changes. Export
  will use the last clean run."

This copy is conservative and uses no no-go terms.

## Recommendation

Review this PR (#467) for visual confirmation. With the explicit signal
fix, the warning is now strictly correct: it appears only when the
backend already knows the draft is newer than the last clean run.
