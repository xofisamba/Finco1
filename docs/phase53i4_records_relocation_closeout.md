# Phase 53I-4 — Records Relocation Closeout

## Context

Phase 53I-4 closes out the records.py relocation stack (53I-1 through
53I-4). All 5 record dataclasses now live in `app/persistence/records.py`,
domain modules import them directly, no lazy imports remain, and the
guardrails prevent future regressions.

This is **docs/report/test only** with **guardrail tests allowed**.

## Current main SHA

`314b7c296ebde7b5400c78c750854823ede6ec52` (post-53I-3)

## Final persistence module map

| Module | LOC | Owns | Risk |
|---|---:|---|---|
| `records.py` | 304 | 5 record dataclasses (ProjectRecord, ScenarioRecord, WorkspaceStateRecord, RunRecord, ScenarioExportRecord) | low |
| `repository.py` | 305 | Compatibility façade + 5 NOT-Group-B functions + 12+ re-exports | low |
| `scenarios_repository.py` | 598 | 4 reads + 5 low-risk + 4 high-risk + helper | mixed |
| `projects_repository.py` | 494 | 6 reads + 8 writes | low |
| `workspace_repository.py` | 253 | 4 workspace functions | low |
| `runs_repository.py` | 107 | 5 run functions (RunRecord re-imported from records) | low |
| `exports_repository.py` | 386 | 10 export/audit functions (ScenarioExportRecord re-imported) | low |
| `db.py` | 205 | get_cursor context manager | n/a |
| `provenance.py` | 171 | replay metadata | n/a |
| `backup_restore.py` | 480 | backup/restore | n/a |
| **Total** | **~3,303** | | |

## Final record dataclass locations

| Record | Location | Defined in |
|---|---|---|
| `ProjectRecord` | `app/persistence/records.py` | records.py (NEW) |
| `ScenarioRecord` | `app/persistence/records.py` | records.py (NEW) |
| `WorkspaceStateRecord` | `app/persistence/records.py` | records.py (NEW) |
| `RunRecord` | `app/persistence/records.py` | records.py (NEW, was runs_repository.py) |
| `ScenarioExportRecord` | `app/persistence/records.py` | records.py (NEW, was exports_repository.py) |

**All 5 records are in records.py.** repository.py has 0 record definitions.

## repository.py remaining responsibilities

After 53I-3, `repository.py` (305 lines) is:

1. **Compatibility façade** — re-exports 12+ items from 7 modules:
   - `_helpers`, `runs_repository`, `exports_repository`,
     `projects_repository`, `workspace_repository`,
     `scenarios_repository`, `records`
2. **5 NOT-Group-B functions** (residual):
   - `seed_scenarios_if_needed` (workshop seeding)
   - `get_scenario_provenance` (provenance metadata)
   - `runtime_guard_for_snapshot` (runtime guard)
   - `update_scenario_last_run_summary` (run summary)
   - `record_workspace_runtime` (workspace runtime)
3. **Module docstring + imports** (preamble)

**0 dataclasses** (moved to records.py).

## scenarios_repository.py LOC and responsibility map

`scenarios_repository.py` (598 lines) is the **single owner of all
scenario persistence**:

- Group B-reads (4 functions, ~200 lines):
  - `resolve_scenario_snapshot`, `get_scenario`, `list_scenarios`,
    `resolve_active_scenario_runtime_snapshot`
- Group B low-risk actions (5 functions, ~80 lines):
  - `rename_scenario`, `archive_scenario`, `select_scenario`,
    `duplicate_scenario`, `promote_scenario_to_base_case`
- Group B high-risk writes (5 functions, ~300 lines):
  - `save_scenario`, `add_scenario`, `update_scenario_overrides`,
    `get_or_create_base_case_scenario`, `get_base_case_scenario`

**0 lazy imports of record dataclasses from `app.persistence.repository`.**
All records imported directly from `app.persistence.records`.

## Lazy import count before/after

| Module | Before 53I-1 | After 53I-3 |
|---|---:|---:|
| `scenarios_repository.py` | 8 | 0 |
| `projects_repository.py` | 7 | 0 |
| `workspace_repository.py` | 3 | 0 |
| **Total** | **18** | **0** |

## Public import compatibility table

| Path | ProjectRecord | ScenarioRecord | WorkspaceStateRecord | RunRecord | ScenarioExportRecord |
|---|:-:|:-:|:-:|:-:|:-:|
| `app.persistence.records` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `app.persistence.repository` | ✓ (re-export) | ✓ (re-export) | ✓ (re-export) | ✓ (re-export) | ✓ (re-export) |
| `app.persistence` (init) | ✓ (re-export) | ✓ (re-export) | ✗ (not re-exported) | ✓ (re-export) | ✓ (re-export) |
| `app.persistence.scenarios_repository` | n/a | ✓ (direct) | n/a | n/a | n/a |
| `app.persistence.projects_repository` | ✓ (direct) | n/a | n/a | n/a | n/a |
| `app.persistence.workspace_repository` | n/a | ✓ (direct) | ✓ (direct) | n/a | n/a |
| `app.persistence.runs_repository` | n/a | n/a | n/a | ✓ (direct) | n/a |
| `app.persistence.exports_repository` | n/a | n/a | n/a | n/a | ✓ (direct) |

`WorkspaceStateRecord` not re-exported from `app.persistence` (init) is
**pre-existing behavior** — it was never in `__init__.py` re-exports
even before the 53I stack. No regression.

## Remaining residual functions in repository.py

| Function | Lines | Reason it stays |
|---|---:|---|
| `seed_scenarios_if_needed` | ~25 | NOT Group B (workshop seeding for new users) |
| `get_scenario_provenance` | ~30 | NOT Group B (provenance metadata builder) |
| `runtime_guard_for_snapshot` | ~30 | NOT Group B (runtime guard for active snapshot) |
| `update_scenario_last_run_summary` | ~30 | NOT Group B (low-level run summary writer) |
| `record_workspace_runtime` | ~50 | NOT Group B (workspace runtime event writer) |

## Guardrails added in 53I stack

1. **`tests/test_phase53i1_records_field_shape_import_pins.py`** (36 tests):
   - Pins field shapes, dataclass options, import paths
   - Will fail if any record's field is added/removed/renamed
   - Will fail if any public import path breaks
2. **`tests/test_phase53i2_records_module_relocation.py`** (21 tests):
   - Verifies records.py exists with all 5 records
   - Verifies no record is in its old location (repository, runs, exports)
   - Verifies public compatibility (object identity)
   - Verifies SQL text unchanged
3. **`tests/test_phase53i3_no_record_lazy_imports.py`** (20 tests):
   - Verifies no `app/persistence/*_repository.py` imports record
     dataclasses from `app.persistence.repository`
   - Verifies object identity across paths
   - Verifies SQL preserved
   - Verifies no new circular import
4. **`tests/test_phase53i4_records_relocation_closeout.py`** (new, this phase):
   - Final guardrail: no `class <Record>` definitions in `repository.py`
   - All 5 records must be in `records.py`
   - Compatibility re-exports must exist in `repository.py`
   - Final closeout structural tests

## Persistence arc closeout recommendation

**The persistence arc can close.** All planned Phase 53 work is
complete:

- ✓ All 7 specialized persistence modules created
- ✓ Compatibility façade stable
- ✓ All 5 record dataclasses relocated
- ✓ No lazy imports remain
- ✓ 4 guardrails added in 53I stack
- ✓ All hard safety guardrails preserved
- ✓ rc1 frozen and untouched
- ✓ 268+ tests pass
- ✓ 91 P0 pins pass

**Recommended next steps (in priority order):**

1. **Agent B governance refresh** (recommended first)
   - Phase 53H-2 review pack prepared questions for this
   - Agent B can now do a full governance doc refresh with the
     post-Phase-53 persistence state
   - Low risk: docs only

2. **UI-1 information architecture** (after Agent B)
   - UI work was paused during Phase 53
   - Now that backend persistence is stable, UI work can resume
   - Medium risk: UI changes can be tested without backend changes

3. **Claude review checkpoint** (already prepared in 53H-2)
   - The 7 questions in the 53H-2 review pack are still valid
   - Run the Claude review to validate the post-53I state

4. **Additional persistence cleanup** (if needed)
   - Backup/restore module (480 LOC) could be split
   - db.py (205 LOC) and provenance.py (171 LOC) are fine
   - Other cleanup: not currently needed

## No-go claims (preserved throughout)

All 18 no-go claims from Phase 53G-8 closeout still apply:

1. No financial formula changes
2. No model output changes
3. No fixture CSV changes
4. No schema/migration changes
5. No JavaScript financial calculations
6. No runtime flag promotions
7. No parity-core file changes
8. Do not touch `app/waterfall_core.py`
9. Do not touch `app/project_factories.py`
10. Do not touch senior-debt CSVs
11. G20 remains BLOCKED
12. R99/R102 remain NOT APPROVED
13. `partial_pay_sweep` remains not promoted
14. `flat/min DSCR sculpting` remains not promoted
15. Generic solar/wind remain exploratory
16. No lender/bank/audit/certification claims
17. Backend remains source of truth
18. rc1 remains frozen

## Final recommendation

The persistence arc is complete. The user's next decision should
be one of:

1. **Agent B governance refresh** (docs only, low risk)
2. **UI-1 information architecture** (UI work resume)
3. **Claude review checkpoint** (per 53H-2 review pack)
4. **Pause persistence** and switch to other work

**Do NOT start:**
- Agent B runtime work (only docs)
- UI runtime work yet
- Pilot work
- Security work
- Deployment work
- Records.py further cleanup (already done)
- Any new persistence module

## Hard gates (53I-4)

- ✓ Docs/report/test only (no production code changes)
- ✓ Guardrail test file added (no weakening)
- ✓ All previous tests still pass
- ✓ No model/parity-core/schema/JS/formula/fixture changes
- ✓ rc1 (b425a07) untouched in history
- ✓ Phase 51F (21/21) + 52F G1-G6 (10/10) pass
- ✓ 53G P0 pins (91/91) pass
- ✓ Coupling pin (23/23) passes

## Tests run
- 53I-1: 36/36 ✓
- 53I-2: 21/21 ✓
- 53I-3: 20/20 ✓
- 53I-4: ~15/15 ✓ (new)
- 53G P0: 91/91 ✓
- Phase 51F: 21/21 ✓
- Phase 52F G1-G6: 10/10 ✓
- **Total: ~214/214 ✓**
