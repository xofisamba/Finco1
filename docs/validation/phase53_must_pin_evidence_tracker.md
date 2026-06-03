# Phase 53 Must-Pin / Evidence Tracker

This file is the **Phase 53 must-pin / evidence tracker**.
It tracks the 12 must-pin items that Phase 52D identified
(7 P0 + 5 P1) and the per-item evidence required to pin
each item before or during Phase 53.

> **Agent B does not implement Phase 53. Agent A pins
> the must-pin items.** Agent B tracks the must-pin status
> and the evidence requirements.
>
> **Phase 52 made zero production code changes. Phase 52D
> identified the 12 must-pin items. Phase 53 will pin them.**
> Agent B does not write the pin tests. Agent A writes the
> pin tests.
>
> **No persistence or repository code changes by Agent B.**
> Agent B is docs-only. The must-pin / evidence tracker is
> the B-track governance wrapper for the Agent A pin work.

---

## 1. Source

The must-pin items are sourced from
`reports/phase52d_persistence_behavior_characterization_plan.json`
(field `must_pin_items`, count 12; field
`high_risk_writes`, count 7; field
`behavior_characterization_matrix`, count 12) and
`reports/phase52g_final_repository_boundary_mapping_closeout.json`
(field `final_persistence_inventory.files`, count 5; field
`final_side_effect_map_summary.must_pin_items_count`).

The 12 must-pin items below are extracted directly from the
Phase 52D report. They are the project's internal
self-assessment. They are not externally validated.

## 2. Status values

The must-pin status values are:

* `identified` — must-pin item is identified in Phase 52D but
  not yet pinned.
* `pinned` — must-pin item is pinned by a Phase 53 PR.
* `partially_pinned` — must-pin item is partially pinned; the
  remaining aspects are deferred.
* `deferred` — must-pin item is deferred to a later phase
  (e.g., Phase 54+).
* `blocked` — must-pin item is blocked by a Phase 53
  hard-stop condition.
* `not_applicable` — must-pin item is not applicable (e.g.,
  the function is no longer called).

## 3. P0 must-pin items (7)

### MP-001 / save_project (P0)

* **Function:** `save_project`.
* **Location:** `app/persistence/repository.py` (L686-802).
* **Domain:** projects.
* **Phase 53 group:** A.
* **Aspects to pin:**
  * INSERT path.
  * UPDATE path.
  * `replay_metadata.project_id` defaulting.
  * `governance_state` preservation.
* **Recommended test file:**
  `tests/test_phase52d_persistence_save_project_pin.py`
  (per Phase 52D).
* **Required before Phase 53:** yes.
* **Initial status:** `identified`.
* **Owner:** Agent A (pin) / Agent B (tracker update).
* **Dependency:** none (no upstream must-pin items).
* **Pilot blocker:** yes (P0).
* **Paid pilot blocker:** yes (P0).
* **External review relevance:** high.

### MP-002 / save_workspace_state (P0)

* **Function:** `save_workspace_state`.
* **Location:** `app/persistence/repository.py` (L1496-1626).
* **Domain:** workspace_state.
* **Phase 53 group:** C.
* **Aspects to pin:**
  * INSERT path.
  * UPDATE path.
  * `replay_metadata` merge with existing.
  * `last_runtime_*` field preservation.
* **Recommended test file:**
  `tests/test_phase52d_persistence_save_workspace_state_pin.py`.
* **Required before Phase 53:** yes.
* **Initial status:** `identified`.
* **Owner:** Agent A (pin) / Agent B (tracker update).
* **Dependency:** none.
* **Pilot blocker:** yes (P0).
* **Paid pilot blocker:** yes (P0).
* **External review relevance:** high.

### MP-003 / save_scenario (P0)

* **Function:** `save_scenario`.
* **Location:** `app/persistence/repository.py` (L1116-1178).
* **Domain:** scenarios.
* **Phase 53 group:** B.
* **Aspects to pin:**
  * `replay_metadata.project_id` and `scenario_id` defaulting.
* **Recommended test file:**
  `tests/test_phase52d_persistence_save_scenario_pin.py`.
* **Required before Phase 53:** yes.
* **Initial status:** `identified`.
* **Owner:** Agent A (pin) / Agent B (tracker update).
* **Dependency:** none.
* **Pilot blocker:** yes (P0).
* **Paid pilot blocker:** yes (P0).
* **External review relevance:** high.

### MP-004 / add_scenario (P0)

* **Function:** `add_scenario`.
* **Location:** `app/persistence/repository.py` (L1299-1378).
* **Domain:** scenarios.
* **Phase 53 group:** B.
* **Aspects to pin:**
  * `replay_metadata.action=add_scenario`.
  * `parent_scenario_id` storage.
  * `is_base_case=0`.
  * `schema_version=1.0`.
* **Recommended test file:**
  `tests/test_phase52d_persistence_add_scenario_pin.py`.
* **Required before Phase 53:** yes.
* **Initial status:** `identified`.
* **Owner:** Agent A (pin) / Agent B (tracker update).
* **Dependency:** none.
* **Pilot blocker:** yes (P0).
* **Paid pilot blocker:** yes (P0).
* **External review relevance:** high.

### MP-005 / record_export (P0)

* **Function:** `record_export`.
* **Location:** `app/persistence/repository.py` (L1713-1772).
* **Domain:** exports.
* **Phase 53 group:** E.
* **Aspects to pin:**
  * `replay_metadata.export_id`, `runtime_snapshot_id`,
    `export_timestamp` defaulting.
* **Recommended test file:**
  `tests/test_phase52d_persistence_record_export_pin.py`.
* **Required before Phase 53:** yes.
* **Initial status:** `identified`.
* **Owner:** Agent A (pin) / Agent B (tracker update).
* **Dependency:** none.
* **Pilot blocker:** yes (P0).
* **Paid pilot blocker:** yes (P0).
* **External review relevance:** medium.

### MP-006 / update_scenario_overrides (P0)

* **Function:** `update_scenario_overrides`.
* **Location:** `app/persistence/repository.py` (L1411-1457).
* **Domain:** scenarios.
* **Phase 53 group:** B.
* **Aspects to pin:**
  * `is_base_case` gate.
  * `SCENARIO_INPUT_FIELDS` filter.
  * re-resolved snapshot.
* **Recommended test file:**
  `tests/test_phase52d_persistence_update_scenario_overrides_pin.py`.
* **Required before Phase 53:** yes.
* **Initial status:** `identified`.
* **Owner:** Agent A (pin) / Agent B (tracker update).
* **Dependency:** none.
* **Pilot blocker:** yes (P0).
* **Paid pilot blocker:** yes (P0).
* **External review relevance:** high.

### MP-007 / select_scenario (P0)

* **Function:** `select_scenario`.
* **Location:** `app/persistence/repository.py` (L1460-1483).
* **Domain:** scenarios.
* **Phase 53 group:** B.
* **Aspects to pin:**
  * `replay_metadata.action=select_scenario`.
  * `active_scenario_name` resolution.
* **Recommended test file:**
  `tests/test_phase52d_persistence_select_scenario_pin.py`.
* **Required before Phase 53:** yes.
* **Initial status:** `identified`.
* **Owner:** Agent A (pin) / Agent B (tracker update).
* **Dependency:** none.
* **Pilot blocker:** yes (P0).
* **Paid pilot blocker:** yes (P0).
* **External review relevance:** high.

## 4. P1 must-pin items (5)

### MP-008 / discard_workspace_draft (P1)

* **Function:** `discard_workspace_draft`.
* **Location:** `app/persistence/repository.py` (L1651-1672).
* **Domain:** workspace_state.
* **Phase 53 group:** C.
* **Aspects to pin:**
  * `draft_snapshot=saved_snapshot`.
  * `dirty=False`.
  * all other fields preserved.
* **Recommended test file:**
  `tests/test_phase52d_persistence_discard_workspace_draft_pin.py`.
* **Required before Phase 53:** no (P1).
* **Initial status:** `identified`.
* **Owner:** Agent A (pin) / Agent B (tracker update).
* **Dependency:** none.
* **Pilot blocker:** no (P1; pilot may proceed).
* **Paid pilot blocker:** medium (P1 may delay).
* **External review relevance:** medium.

### MP-009 / record_workspace_runtime (P1)

* **Function:** `record_workspace_runtime`.
* **Location:** `app/persistence/repository.py` (L1675-1710).
* **Domain:** workspace_state.
* **Phase 53 group:** C.
* **Aspects to pin:**
  * `last_runtime_scenario_id` only set if
    `runtime_origin==saved_state`.
* **Recommended test file:**
  `tests/test_phase52d_persistence_record_workspace_runtime_pin.py`.
* **Required before Phase 53:** no (P1).
* **Initial status:** `identified`.
* **Owner:** Agent A (pin) / Agent B (tracker update).
* **Dependency:** none.
* **Pilot blocker:** no (P1).
* **Paid pilot blocker:** medium.
* **External review relevance:** medium.

### MP-010 / bind_workspace_to_scenario (P1)

* **Function:** `bind_workspace_to_scenario`.
* **Location:** `app/persistence/repository.py` (L1629-1648).
* **Domain:** workspace_state.
* **Phase 53 group:** C.
* **Aspects to pin:**
  * `draft_snapshot=saved_snapshot=record.snapshot`.
  * `dirty=False`.
* **Recommended test file:**
  `tests/test_phase52d_persistence_bind_workspace_to_scenario_pin.py`.
* **Required before Phase 53:** no (P1).
* **Initial status:** `identified`.
* **Owner:** Agent A (pin) / Agent B (tracker update).
* **Dependency:** none.
* **Pilot blocker:** no (P1).
* **Paid pilot blocker:** medium.
* **External review relevance:** medium.

### MP-011 / update_scenario_last_run_summary (P1)

* **Function:** `update_scenario_last_run_summary`.
* **Location:** `app/persistence/repository.py` (L1381-1408).
* **Domain:** scenarios.
* **Phase 53 group:** B.
* **Aspects to pin:**
  * `replay_metadata` merge with existing.
* **Recommended test file:**
  `tests/test_phase52d_persistence_update_scenario_last_run_summary_pin.py`.
* **Required before Phase 53:** no (P1).
* **Initial status:** `identified`.
* **Owner:** Agent A (pin) / Agent B (tracker update).
* **Dependency:** none.
* **Pilot blocker:** no (P1).
* **Paid pilot blocker:** medium.
* **External review relevance:** medium.

### MP-012 / duplicate_scenario (P1)

* **Function:** `duplicate_scenario`.
* **Location:** `app/persistence/repository.py` (L1280-1296).
* **Domain:** scenarios.
* **Phase 53 group:** B.
* **Aspects to pin:**
  * `copied_from_scenario_id=source.scenario_id`.
  * `governance_state` copied verbatim.
* **Recommended test file:**
  `tests/test_phase52d_persistence_duplicate_scenario_pin.py`.
* **Required before Phase 53:** no (P1).
* **Initial status:** `identified`.
* **Owner:** Agent A (pin) / Agent B (tracker update).
* **Dependency:** none.
* **Pilot blocker:** no (P1).
* **Paid pilot blocker:** medium.
* **External review relevance:** medium.

## 5. High-risk writes (7)

The 7 high-risk writes are the functions that Phase 52B
identified as the highest-risk writes in the persistence
layer. They overlap with the must-pin items but are tracked
separately.

| # | Function | Line | LOC | Domain | Group |
|---|---|---|---|---|---|
| HRW-01 | save_project | 686 | 117 | projects | A |
| HRW-02 | save_workspace_state | 1496 | 131 | workspace_state | C |
| HRW-03 | save_scenario | 1116 | 63 | scenarios | B |
| HRW-04 | add_scenario | 1299 | 80 | scenarios | B |
| HRW-05 | record_export | 1713 | 60 | exports | E |
| HRW-06 | update_scenario_overrides | 1411 | 47 | scenarios | B |
| HRW-07 | get_or_create_base_case_scenario | 86 | 85 | scenarios | B |

`get_or_create_base_case_scenario` (HRW-07) is a high-risk
write but is not a must-pin item; it is listed in the
high-risk writes table. It will be tracked separately in
the B27 guardrail adoption tracker.

## 6. 5 persistence files (mapped)

| # | File | LOC | Role |
|---|---|---|---|
| PF-01 | `app/persistence/__init__.py` | 55 | package init / re-exports |
| PF-02 | `app/persistence/db.py` | 205 | sqlite connection / schema init / get_cursor |
| PF-03 | `app/persistence/repository.py` | 2042 | god-module: project, scenario, run, export, audit, workspace |
| PF-04 | `app/persistence/backup_restore.py` | 480 | sqlite backup + restore + auto-backup |
| PF-05 | `app/persistence/provenance.py` | 171 | git sha, branch, runtime flag, governance, replay metadata |
| | **Total** | **2953** | |

The 2953 LOC matches the Phase 52G closeout number. The 5
files match the Phase 52G closeout number. The LOC
distribution will be used in Phase 53 to plan the per-group
extraction.

## 7. Per-PR pin progress tracking

The B-track governance review of each Phase 53 PR will
update the must-pin status of the relevant items. The
expected mapping is:

* **53A (Group F helpers):** no must-pin items pinned.
  Helpers are not must-pin items.
* **53B (Group F consumers):** no must-pin items pinned.
* **53C (Group D):** no must-pin items pinned.
* **53D (Group E):** MP-005 (record_export, P0) pinned.
* **53E (Group A reads):** no must-pin items pinned.
* **53F (Group A writes):** MP-001 (save_project, P0) pinned.
* **53G (Group C):** MP-002 (save_workspace_state, P0)
  pinned; MP-008, MP-009, MP-010 (P1) pinned.
* **53H (Group B part 1):** MP-003, MP-004, MP-006, MP-007
  (P0) pinned.
* **53I (Group B part 2):** MP-011, MP-012 (P1) pinned.
* **53J (Group B part 3):** any deferred must-pin items
  re-evaluated; HRW-07 documented.

The per-PR pin mapping is the B-track governance planning
convention. Agent A may adjust the mapping in execution as
long as the must-pin items are pinned before they are
modified.

## 8. What this tracker is not

* It is not a code change. Agent B does not implement Phase
  53.
* It is not a contract. The must-pin tracker is the
  B-track governance wrapper for the Agent A pin work.
* It is not external validation. The must-pin tracker is
  internal governance.
* It is not a substitute for the Phase 52D report or any
  other B-track artifact.
* It is not Claude review. Claude review is separate.
* It is not the post-51T review. The post-51T review is
  separate.

## 9. Cross-references

* `reports/validation/phase53_must_pin_evidence_tracker.json`
  (B26, machine-readable)
* `docs/governance/post_phase52_governance_refresh.md` (B24)
* `docs/governance/phase53_risk_gate_matrix.md` (B25)
* `docs/governance/phase52_53_guardrail_adoption_tracker.md`
  (B27)
* `docs/pilot/post_phase52_pilot_external_readiness_delta.md`
  (B28)
* `docs/governance/phase53_change_control_checklist.md` (B29)
* `reports/phase52d_persistence_behavior_characterization_plan.json`
  (Phase 52D source)
* `reports/phase52g_final_repository_boundary_mapping_closeout.json`
  (Phase 52G source)
* `docs/external_review/external_review_closeout_tracker.md`
  (B16)

---

*End of Phase 53 must-pin / evidence tracker.*
