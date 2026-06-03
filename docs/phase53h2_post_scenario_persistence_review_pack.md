# Phase 53H-2 — Post Scenario Persistence Review Pack

## Context

Phase 53H-2 prepares a **Claude architecture review pack** for the
post-Group-B persistence state. This is a docs-only deliverable that
informs the user (and Claude) about what to review, what evidence is
available, and what questions need answers.

This is a **docs/report/test only** checkpoint. NO production code is
touched. NO app/persistence modules are touched.

## Review scope

The Claude architecture review should cover:

1. **Post-Group-B state of `app/persistence/`**:
   - 7 specialized modules (helpers, runs_repository, exports_repository,
     projects_repository, workspace_repository, scenarios_repository,
     records [future])
   - 1 compatibility façade (repository.py)
   - 2 infrastructure modules (db.py, provenance.py)
   - 1 backup/restore module (backup_restore.py)

2. **The Phase 53 refactor as a whole**:
   - Phase 52 mapping (planning)
   - Phase 53A-53G-8 (extraction + closeout)
   - Phase 53H-1 (records planning)

3. **Hard safety guardrails**:
   - rc1 frozen (b425a0708719eaa5e1d922b1008e5609758e0ad4)
   - No financial formula changes
   - No model output changes
   - No fixture CSV changes
   - G20 BLOCKED, R99/R102 NOT APPROVED, partial_pay_sweep not promoted
   - Backend remains source of truth

## Current main SHA

`8f7c749cb3167820569d66618ed320d370b34ed3` (post-53H-1)

## Evidence files (organized chronologically)

### Phase 52: Mapping (planning only)
- `docs/phase52a_repository_inventory_hotspot_map.md` + `.json`
- `docs/phase52b_persistence_side_effect_map.md` + `.json`
- `docs/phase52c_repository_caller_coupling_graph.md` + `.json`
- `docs/phase52d_persistence_behavior_characterization_plan.md` + `.json`
- `docs/phase52e_persistence_hotspot_phase53_execution_plan.md` + `.json`
- `docs/phase52f_persistence_guardrail_specifications.md` + `.json`
- `docs/phase52g_final_repository_boundary_mapping_closeout.md` + `.json`

### Phase 53A-F: Lower-risk extractions
- `docs/phase53a_persistence_helpers_extraction.md` + `.json` (Group F helpers)
- `docs/phase53b_persistence_runs_extraction.md` + `.json` (Group D runs)
- `docs/phase53c_persistence_exports_audit_extraction.md` + `.json` (Group E exports/audit)
- `docs/phase53d_persistence_project_reads_extraction.md` + `.json` (Group A-reads)
- `docs/phase53e1_save_project_p0_behavior_pin.md` + `.json` (P0 pin)
- `docs/phase53e2_project_write_persistence_extraction.md` + `.json` (Group A-2 writes)
- `docs/phase53f1_save_workspace_state_p0_behavior_pin.md` + `.json` (P0 pin)
- `docs/phase53f2_workspace_state_persistence_extraction.md` + `.json` (Group C workspace)

### Phase 53G: Scenario persistence refactor
- `docs/phase53g1_scenario_p0_behavior_pins.md` + `.json` (P0 pins + coupling pin)
- `docs/phase53g2_scenario_read_persistence_extraction.md` + `.json` (Group B-reads)
- `docs/phase53g3_low_risk_scenario_actions_extraction.md` + `.json` (Group B low-risk)
- `docs/phase53g4_save_scenario_persistence_extraction.md` + `.json` (Group B high-risk #1)
- `docs/phase53g5_add_scenario_persistence_extraction.md` + `.json` (Group B high-risk #2)
- `docs/phase53g6_update_scenario_overrides_persistence_extraction.md` + `.json` (Group B high-risk #3)
- `docs/phase53g7_base_case_scenario_persistence_extraction.md` + `.json` (Group B high-risk #4)
- `docs/phase53g8_final_scenario_persistence_closeout.md` + `.json` (final closeout)

### Phase 53H: Records planning
- `docs/phase53h1_records_dataclass_relocation_map.md` + `.json` (records mapping)

## Current app/persistence module inventory

| Module | LOC | Owns | Risk |
|---|---:|---|---|
| `_helpers.py` | 140 | Group F (9 helpers + 1 constant) | low |
| `runs_repository.py` | 140 | Group D (5 run functions + RunRecord) | low |
| `exports_repository.py` | 370 | Group E (10 exports/audit + ScenarioExportRecord) | low |
| `projects_repository.py` | 480 | Group A (6 reads + 8 writes + helpers) | low |
| `workspace_repository.py` | 250 | Group C (4 workspace functions) | low |
| `scenarios_repository.py` | 598 | Group B (4 reads + 5 low-risk + 4 high-risk + helper) | mixed |
| `repository.py` | 455 | Compatibility façade + 5 NOT-Group-B + 3 deferred dataclasses | mixed |
| `db.py` | 205 | get_cursor context manager | n/a |
| `provenance.py` | 171 | replay metadata | n/a |
| `backup_restore.py` | 480 | backup/restore | n/a |
| **Total** | **~3,289** | | |

## Current tests/guardrails inventory

### Phase 51F (parallel work guardrails)
- 21 tests covering parity-core lock, engine-output golden, no-service-imports-main_web

### Phase 52F (persistence guardrails)
- G1: no direct sqlite3/sqlalchemy imports outside `app/persistence` (2 tests)
- G2: no service imports main_web/main_api (2 tests)
- G3: no sqlite3.Connection/connect instantiation (1 test)
- G4: no service imports get_cursor (1 test)
- G5: cross-module total `with get_cursor() as cur:` ≥ 20 (1 test)
- G6: services use public surface only (1 test)
- Plus 19 specifications tests
- **Total Phase 52F: 10 regression + 19 specifications = 29 tests**

### Phase 53G P0 pins
- save_scenario: 16 tests (re-pointed to scenarios_repository)
- add_scenario: 19 tests (re-pointed)
- update_scenario_overrides: 16 tests (re-pointed)
- get_or_create_base_case_scenario: 17 tests (re-pointed)
- scenario/workspace coupling: 23 tests (re-pointed where needed)
- **Total Phase 53G P0 pins: 91 tests**

### Phase 53G structural tests
- 53G-2 (reads): 27 tests
- 53G-3 (low-risk): 30 tests
- 53G-4 (save_scenario): 13 tests
- 53G-5 (add_scenario): 8 tests
- 53G-6 (update_overrides): 7 tests
- 53G-7 (base-case): 10 tests
- 53G-8 (closeout): 16 tests
- **Total Phase 53G structural: 111 tests**

### Phase 53H structural tests
- 53H-1: 16 tests
- **Total Phase 53H: 16 tests**

### Grand total
- 51F: 21
- 52F: 29
- 53G: 202 (91 P0 + 111 structural)
- 53H: 16
- **Total: 268 persistence-related tests**

## Exact Claude review questions

### 1. Did Group B refactor preserve scenario behavior?

**Context**: 4 P0 pins (save_scenario, add_scenario, update_scenario_overrides, get_or_create_base_case_scenario) all pass with full re-pointing to scenarios_repository.py. 23 coupling tests pass.

**Question**: Based on the P0 pin evidence and coupling pin evidence, did the Group B refactor (53G-1 through 53G-8) preserve scenario persistence behavior byte-for-byte?

**Evidence**:
- `tests/test_phase53g1_save_scenario_p0_behavior_pin.py` (16/16)
- `tests/test_phase53g1_add_scenario_p0_behavior_pin.py` (19/19)
- `tests/test_phase53g1_update_overrides_p0_behavior_pin.py` (16/16)
- `tests/test_phase53g1_base_case_p0_behavior_pin.py` (17/17)
- `tests/test_phase53g1_scenario_workspace_coupling_p0_pin.py` (23/23)

### 2. Is repository.py now acceptable as compatibility façade?

**Context**: repository.py is 455 lines = 3 dataclasses (~150) + 5 NOT-Group-B functions (~165) + 12 re-exports (~30) + module docstring/imports (~110).

**Question**: Is the 455-line repository.py acceptable as a long-term compatibility façade, or should records relocation be done to further shrink it?

**Evidence**:
- `docs/phase53g8_final_scenario_persistence_closeout.md` (responsibility map)
- `docs/phase53h1_records_dataclass_relocation_map.md` (records planning)

### 3. Should records.py relocation happen now?

**Context**: 3 dataclasses (ProjectRecord, ScenarioRecord, WorkspaceStateRecord) are still in repository.py. 4 options (A/B/C/D) analyzed in 53H-1.

**Question**: Should records.py relocation be approved now (Option A recommended), deferred, or done as a different option (B, C, D)?

**Evidence**:
- `docs/phase53h1_records_dataclass_relocation_map.md` (full options analysis)
- `reports/phase53h1_records_dataclass_relocation_map.json` (option scores)

### 4. Should records relocation be auto-merge eligible?

**Context**: Records are data-shape definition, not behavior. Moving them is mechanical (3 re-exports added, lazy imports work unchanged).

**Question**: If approved, should records relocation be auto-merge eligible like the lower-risk Phase 53 PRs, or should it be review-required like the high-risk scenario writes?

**Evidence**:
- `docs/phase53h1_records_dataclass_relocation_map.md` (auto-merge discussion)
- `docs/phase53g4_save_scenario_persistence_extraction.md` (high-risk example: was DRAFT, not auto-merged)

### 5. Should we pause persistence work and move to UI/pilot hardening?

**Context**: Phase 53G completed the most sensitive extraction phase. Backend persistence is now well-structured. UI/pilot work has been out of scope for many phases.

**Question**: Is this the right time to pause persistence work and move to UI/pilot hardening? Or should records relocation happen first?

**Evidence**:
- All Phase 53 docs (extraction complete, modules stable)
- `docs/phase53g8_final_scenario_persistence_closeout.md` (state is clean)

### 6. What are the highest-value next phases?

**Question**: Beyond records relocation and UI hardening, what other high-value work should be considered? Examples: app/waterfall_core.py cleanup, app/project_factories.py, schema documentation, financial model test coverage, parity-core audit, etc.

**Evidence**:
- `docs/phase52d_persistence_behavior_characterization_plan.md` (Phase 53 plan)
- `docs/phase52e_persistence_hotspot_phase53_execution_plan.md` (broader plan)
- The 7 no-go claims in closeout reports

### 7. What should be the updated roadmap and duration estimate?

**Question**: Given the current state, what is the realistic 3-6 month roadmap? What is the duration estimate for the next major phase (records, UI, etc.)?

**Evidence**:
- All Phase 52 + Phase 53 docs (current state)
- `docs/phase53h1_records_dataclass_relocation_map.md` (records work breakdown)

## No-go claims (preserved throughout)

These are the safety guardrails that must continue to be respected:

1. **No financial formula changes**
2. **No model output changes**
3. **No fixture CSV changes**
4. **No schema/migration changes**
5. **No JavaScript financial calculations**
6. **No runtime flag promotions**
7. **No parity-core file changes**
8. **Do not touch `app/waterfall_core.py`**
9. **Do not touch `app/project_factories.py`**
10. **Do not touch senior-debt CSVs**
11. **G20 remains BLOCKED**
12. **R99/R102 remain NOT APPROVED**
13. **`partial_pay_sweep` remains not promoted**
14. **`flat/min DSCR sculpting` remains not promoted**
15. **Generic solar/wind remain exploratory and unvalidated**
16. **No lender/bank/audit/certification/SaaS/production/external-validation/customer-reference/investment-advice claims**
17. **Backend remains source of truth**
18. **rc1 remains frozen**

## Recommended prompt for Claude

```
You are a senior software architect reviewing a backend refactor that
extracted a 2,042-line persistence module into 7 specialized modules
plus a compatibility façade. The refactor is documented in 30+ files
(Phase 52 + 53 + 53H-1) and 268+ tests pass.

Current state:
- main SHA: 8f7c749cb3167820569d66618ed320d370b34ed3
- 7 specialized persistence modules: _helpers, runs_repository,
  exports_repository, projects_repository, workspace_repository,
  scenarios_repository, (records.py — future)
- 1 compatibility façade: repository.py (455 lines)
- 2 infrastructure modules: db.py, provenance.py
- 1 backup module: backup_restore.py
- 0 high-risk scenario writes remain in repository.py
- All 4 high-risk scenario writes are in scenarios_repository.py
- 3 deferred dataclasses: ProjectRecord, ScenarioRecord,
  WorkspaceStateRecord (in repository.py, planned for relocation)

Hard safety guardrails (must continue to be respected):
- rc1 frozen (b425a07)
- No financial formula changes
- G20 BLOCKED, R99/R102 NOT APPROVED
- Backend remains source of truth
- Generic solar/wind exploratory only

Review the post-Group-B state and answer the 7 questions in
docs/phase53h2_post_scenario_persistence_review_pack.md. Focus on:
1. Is the Group B refactor behavior-preserving? (P0 pin evidence)
2. Is repository.py acceptable as compatibility façade? (3 dataclasses
   are deferred; Option A in 53H-1 recommends moving them)
3. Should records.py relocation happen now?
4. Auto-merge eligibility for records relocation?
5. Pause persistence and move to UI/pilot hardening?
6. Highest-value next phases beyond records?
7. Updated 3-6 month roadmap and duration estimate?

Be specific. Cite line numbers and file paths. Recommend concrete
next actions. If you see latent issues, raise them with severity
(low/medium/high/critical).
```

## Recommended next human decision point

After Claude review, the user should:

1. **Decide on records relocation**:
   - Approve Option A (records.py) — proceed to 53I-1
   - Approve Option B (per-owner) — proceed to 53I-1 variant
   - Defer (Option C) — focus on other work
   - Modify (Option D variant) — discuss specifics

2. **Decide on UI/pilot work**:
   - Yes, switch to UI hardening (Phase 54+)
   - No, continue persistence work (records, then what?)

3. **Decide on broader roadmap**:
   - Accept Claude's roadmap
   - Modify based on user priorities
   - Defer the broader question and just do next 1-2 phases

## Recommended next step

After Claude review, the user should provide a decision prompt
that references this review pack. The decision should be specific:
"Approve Option A and proceed to 53I-1 as draft PR" or similar.

**Do NOT start records.py implementation in this phase.** Per spec,
this is review prep only. Implementation requires user sign-off after
Claude review.
