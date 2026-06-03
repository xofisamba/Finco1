# Phase 53F-1 — P0 behavior pin for save_workspace_state

## Context

Phase 52F-G identified 7 high-risk writes that should NOT be moved without
a behavior pin. `save_workspace_state` is one of them (P0 must-pin item 2).

This PR pins the current behavior of `save_workspace_state` so that 53F-2
(extraction to `app/persistence/workspace_repository.py`) is provably
behavior-preserving.

## What is pinned

| Area | Detail |
|---|---|
| **Importability** | `save_workspace_state` is importable from `app.persistence.repository` |
| **Signature** | All 16 parameters are keyword-only; 5 required, 11 optional with defaults |
| **Return type** | `WorkspaceStateRecord` |
| **Body pattern** | Uses `_now_utc()` for timestamps; calls `get_workspace_state()` for upsert check; default `governance_state` to `{}`; default `replay_metadata` via `dict(replay_metadata or {})` |
| **Single-transaction** | Both UPDATE and INSERT use `with get_cursor() as cur:` (≥ 2 occurrences) |
| **SQL text** | UPDATE on `workspace_states` with 14 SET columns + WHERE `workspace_id=? AND user_id=?`; INSERT with 19 columns |
| **JSON serialization** | Uses `_to_json()` helper for 8+ fields |
| **replay_metadata** | Merged on UPDATE (new keys override existing); `setdefault("workspace_id", workspace_id)` on INSERT |
| **governance_state** | Default to `{}`; inherit from existing on UPDATE if not provided |
| **last_runtime_*** | All 6 fields inherit from existing on UPDATE if not provided |
| **dirty flag** | Default False; stored as `int(dirty)` |
| **Timestamps** | `now` via `_now_utc()`; `last_runtime_at.isoformat() if last_runtime_at else None` |
| **UUID** | `uuid.uuid4().hex[:16]` for new workspace_id |
| **Return record** | Has 19 fields including `workspace_id, project_id, user_id, project_code, active_scenario_id, active_scenario_name, draft_snapshot, saved_snapshot, last_runtime_snapshot, last_runtime_summary, last_runtime_snapshot_id, last_runtime_origin, last_runtime_scenario_id, dirty, governance_state, replay_metadata, created_at, updated_at, last_runtime_at` |
| **Helpers** | `get_workspace_state`, `discard_workspace_draft`, `bind_workspace_to_scenario` importable from `app.persistence.repository` |
| **No callers changed** | `save_workspace_state` defined exactly once |

## Coverage

38 tests, 12 test classes:

1. `TestImportability` — 5 tests
2. `TestSignature` — 4 tests
3. `TestSaveWorkspaceStateBody` — 6 tests
4. `TestSqlTextPinning` — 4 tests
5. `TestReplayMetadataBehavior` — 3 tests
6. `TestGovernanceStateBehavior` — 2 tests
7. `TestLastRuntimeBehavior` — 4 tests
8. `TestDirtyFlagBehavior` — 2 tests
9. `TestReturnRecord` — 1 test
10. `TestNoCallerChanges` — 1 test
11. `TestSqlFragments` — 2 tests
12. `TestGetWorkspaceStateInteraction` — 2 tests
13. `TestGuardrailsPreFlight` — 2 tests

## Hard gates

- ✓ test/docs/report only (no production code changed)
- ✓ All 38 new tests pass
- ✓ Phase 51F guardrails pass (21/21)
- ✓ Phase 52F G1-G6 guardrails pass (10/10)
- ✓ No SQL text changes (none introduced)
- ✓ No replay_metadata/governance_state/last_run_summary shape changes (none introduced)
- ✓ No route/service changes
- ✓ rc1 untouched (SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` unchanged in history)

## Recommended next step

`Phase 53F-2 — Extract workspace_state persistence functions`

Move the following functions to `app/persistence/workspace_repository.py`:
- `save_workspace_state`
- `get_workspace_state`
- `discard_workspace_draft`
- `bind_workspace_to_scenario`

`record_workspace_runtime` and `runtime_guard_for_snapshot` are NOT in Group C
per Phase 52F-G (they're a different concern: runtime guards). 53F-2 will
keep them in `repository.py` unless explicitly added to the scope later.
