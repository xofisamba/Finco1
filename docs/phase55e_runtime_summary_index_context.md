# Phase 55E — Wire runtime_summary into index context

## Status

DRAFT, awaiting user review. NO auto-merge.

## Summary

Activates the UI-2.6 `_last_run_indicator.html` partial by adding
`runtime_summary` to the `index.html` render context. The data is
derived from existing `workspace_state` fields (`last_runtime_snapshot_id`,
`last_runtime_at`) — no new persistence writes, no fake run IDs, no
financial model changes.

## What changed

### `main_web.py`

- New helper `_runtime_summary_for_index(workspace_state)` that returns:
  - `None` if no real runtime data exists
  - `{"run_id": str, "last_run_at": str}` if both exist
  - `{"run_id": str}` if only `last_runtime_snapshot_id` exists
  - `{"last_run_at": str}` if only `last_runtime_at` exists
- Added `"runtime_summary": _runtime_summary_for_index(workspace_state)`
  to the index.html render context dict.
- The helper is read-only — does not write or mutate state.

### Tests

- `tests/test_phase55e_runtime_summary_index_context.py` (30 tests)
- Tests: helper exists, returns None for no data, returns dict for
  real data, partial renders correctly, no fake IDs, no financial
  changes, no CSS/JS changes, no persistence writes.

## Hard gates verified

- ✓ Only `main_web.py` (helper + context key) and tests added
- ✓ No templates changed
- ✓ No static CSS/JS changes
- ✓ No frontend dependency changes
- ✓ No model/parity-core/schema/formula/fixture changes
- ✓ No new persistence writes (helper is read-only)
- ✓ No financial output changes
- ✓ `/run` route behavior unchanged
- ✓ No no-go UI claims introduced
- ✓ rc1 SHA `b425a07` untouched
- ✓ 839 relevant tests pass

## Context keys added

| Key | Used by | Source |
|---|---|---|
| `runtime_summary` | `_last_run_indicator.html` | `workspace_state.last_runtime_snapshot_id` and `workspace_state.last_runtime_at` |

## Recommendation

Review this PR (#473) for visual confirmation. With the wiring, the
last-run indicator now shows the actual run reference and timestamp
when a real runtime exists, and renders nothing when no runtime data
exists. The partial's safe copy is preserved ("Last run" / "Runtime
source" / "Run reference" / "When" / "Review model evidence before
export.").
