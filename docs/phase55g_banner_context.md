# Phase 55G — Wire banner_context into index context

## Status

DRAFT, awaiting user review. NO auto-merge.

## Summary

Activates the UI-2.1 `_state_banner.html` partial by adding
`banner_context` to the `index.html` render context. The context is
derived from existing state signals (project_record.project_origin,
workspace_state.dirty, workspace_state.last_runtime_snapshot_id,
workspace_state.active_scenario_id, validation_errors) using a
deterministic priority order.

## What changed

### `main_web.py`

- New helper `_banner_context_for_index(project_record, workspace_state, validation_errors)`
  that returns one of the 11 supported banner contexts:
  - `validation_failed` (priority 1, only if explicit errors list non-empty)
  - `stale_result` (priority 2, dirty + last_runtime_snapshot_id)
  - `browser_draft` (priority 3, dirty without last_runtime_snapshot_id)
  - `factory_template` (priority 4, project_origin is not user_created)
  - `active_scenario` (priority 5, user project with active_scenario_id)
  - `user_created_project` (priority 6, user project without active scenario)
  - `None` (no clear state — banner not rendered)
- Added `"banner_context": _banner_context_for_index(...)` to the
  index.html render context dict.
- The helper is read-only.

### Tests

- `tests/test_phase55g_banner_context.py` (40 tests)
- Tests: helper exists, deterministic priority order, all 11 contexts
  supported, partial renders, no no-go copy, no financial changes, no
  CSS/JS changes, no persistence writes.

## Hard gates verified

- ✓ Only `main_web.py` (helper + context key) and tests added
- ✓ No templates changed
- ✓ No static CSS/JS changes
- ✓ No frontend dependency changes
- ✓ No model/parity-core/schema/formula/fixture changes
- ✓ No new persistence writes (helper is read-only)
- ✓ No financial output changes
- ✓ `/run` route behavior unchanged
- ✓ No save/run/scenario behavior changes
- ✓ No no-go UI claims introduced
- ✓ rc1 SHA `b425a07` untouched
- ✓ 905 relevant tests pass

## Context keys added

| Key | Used by | Source |
|---|---|---|
| `banner_context` | `_state_banner.html` | `project_record.project_origin`, `workspace_state.dirty`, `workspace_state.last_runtime_snapshot_id`, `workspace_state.active_scenario_id`, `validation_errors` |

## Deterministic priority order (pinned)

1. `validation_failed` (only if `validation_errors` list non-empty)
2. `stale_result` (`workspace_state.dirty` AND `last_runtime_snapshot_id`)
3. `browser_draft` (`workspace_state.dirty` AND NOT `last_runtime_snapshot_id`)
4. `factory_template` (`project_origin != "user_created"`)
5. `active_scenario` (user project with `active_scenario_id`)
6. `user_created_project` (user project without `active_scenario_id`)
7. None (no clear state)

## Recommendation

Review this PR (#475) for visual confirmation. With the wiring, the
state clarity banner will now show the appropriate context based on
real state signals. No new claims; no external validation.
