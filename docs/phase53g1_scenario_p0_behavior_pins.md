# Phase 53G-1 — Scenario P0 behavior pins and coupling pin

## Context

Phase 53G-1 pins the current behavior of the 4 high-risk scenario writes
(`save_scenario`, `add_scenario`, `update_scenario_overrides`,
`get_or_create_base_case_scenario`) and pins the scenario/workspace
coupling before any Group B extraction (53G-2..53G-7).

This is a test/docs/report-only PR. No production code changed.

## Pin files (5 files, 81 tests)

| File | Tests | Target |
|---|---:|---|
| `tests/test_phase53g1_scenario_workspace_coupling_p0_pin.py` | 23 | Coupling: bind/discard/update/add/save between scenarios and workspace |
| `tests/test_phase53g1_save_scenario_p0_behavior_pin.py` | 18 | `save_scenario` |
| `tests/test_phase53g1_add_scenario_p0_behavior_pin.py` | 19 | `add_scenario` |
| `tests/test_phase53g1_update_overrides_p0_behavior_pin.py` | 16 | `update_scenario_overrides` |
| `tests/test_phase53g1_base_case_p0_behavior_pin.py` | 14 | `get_or_create_base_case_scenario` |
| **Total** | **81** | |

## Coupling pin summary

| Coupling point | Pin |
|---|---|
| `bind_workspace_to_scenario` calls `save_workspace_state` with scenario's snapshot as both draft and saved | ✓ |
| `bind_workspace_to_scenario` passes `record.scenario_id` and `record.scenario_name` as active_scenario_id / name | ✓ |
| `bind_workspace_to_scenario` sets `dirty=False` and inherits `governance_state` from record | ✓ |
| `discard_workspace_draft` does NOT touch scenarios table | ✓ |
| `discard_workspace_draft` restores draft from `record.saved_snapshot` | ✓ |
| `update_scenario_overrides` re-resolves snapshot via `resolve_scenario_snapshot` | ✓ |
| `update_scenario_overrides` updates BOTH `overrides_json` AND `snapshot_json` atomically | ✓ |
| `update_scenario_overrides` returns None for base-case | ✓ |
| `update_scenario_overrides` filters keys to `SCENARIO_INPUT_FIELDS` only | ✓ |
| `add_scenario` stores `base_input_set_json`, `overrides_json`, `snapshot_json` at insert | ✓ |
| `add_scenario` records `replay_metadata["action"] = "add_scenario"` and `["parent_scenario_id"]` | ✓ |
| `save_scenario` is INSERT-only (no UPSERT) | ✓ |
| `save_scenario` uses `replay_metadata.setdefault` for `project_id` and `scenario_id` | ✓ |

## Hard gates

- ✓ 81/81 new pin tests pass
- ✓ All previous Phase 53 + 52F + 51F tests pass (no regressions)
- ✓ Phase 51F guardrails pass (21/21)
- ✓ Phase 52F G1-G6 pass (10/10)
- ✓ No production code changed
- ✓ No SQL text changes (none introduced)
- ✓ No replay_metadata/governance_state/last_run_summary shape changes
- ✓ No route/service changes
- ✓ rc1 untouched (SHA `b425a0708719eaa5e1d922b1008e5609758e0ad4` unchanged in history)

## Recommended next step

`Phase 53G-2 — Extract scenario read functions` (auto-merge allowed).

Move the following read-only functions to
`app/persistence/scenarios_repository.py`:
- `get_scenario`
- `list_scenarios`
- `get_scenario_history`
- `resolve_scenario_snapshot`
- `resolve_active_scenario_runtime_snapshot`

DO NOT move in 53G-2:
- `save_scenario`, `add_scenario`, `update_scenario_overrides`,
  `get_or_create_base_case_scenario` (high-risk writes — separate PRs 53G-4..53G-7)
- `promote_scenario_to_base_case`, `duplicate_scenario`, `rename_scenario`,
  `archive_scenario`, `select_scenario` (low-risk actions — 53G-3)
- `record_workspace_runtime` (NOT Group B)
- `seed_scenarios_if_needed` (NOT Group B, stays in repository.py)
- `runtime_guard_for_snapshot` (NOT Group B, stays in repository.py)
- record dataclasses (deferred until after Group B)
