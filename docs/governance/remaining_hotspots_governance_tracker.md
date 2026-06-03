# Remaining Hotspots Governance Tracker

This file is the **governance tracker** for the 5 remaining
inline hotspot routes identified by Agent A's Phase 51N post-M2
route extraction checkpoint. After Phase 51N, 12 service-backed
routes and 13 service modules are in place; 5 inline hotspots
remain:

* `POST /projects/{code}/save-as`
* `POST /scenarios/{id}/rename`
* `POST /scenarios/{id}/archive`
* `POST /scenarios/{id}/update-overrides`
* `POST /scenarios/{id}/select`

> **This tracker is internal governance. It is not a code change.
> It does not authorize Agent B to extract or modify any
> Agent A file. Agent B does not perform the extractions.
> Agent B does not modify Agent A files.** A refresh of this
> tracker is performed by Agent B when Agent A's characterization
> or extraction phase for one of the 5 hotspots lands on main,
> per the B14 governance refresh plan.
>
> **The expected future Agent A phase numbering (51O/51P/51Q/
> 51R/51S) is a planning convention, not a commitment.** Agent A
> may number the actual phases differently; the B-track updates
> the tracker when the actual phase lands.

---

## 1. Post-Phase 51N state

* **Service-backed routes:** 12
* **Service modules:** 13
* **Remaining inline hotspots:** 5
* **Source of state:** Phase 51N commit
  `aced60b58c5552800b95a90e17b22b32981efab8`.

The 5 remaining inline hotspots are tracked in this file and in
`reports/governance/remaining_hotspots_governance_tracker.json`
(B17, machine-readable). They are also reflected in the B3
matrix AREA-019 (`Recent Agent A route / state work`) and in the
B8 enterprise SaaS readiness tracker (architecture dimension: 12
service-backed routes of 17; 5 inline hotspots remaining).

## 2. Per-route tracker

Each route has an entry with the following fields:

* `route` — the inline route path.
* `current_inline_status` — where the route is implemented at
  the current base SHA.
* `risk_level` — `low` / `medium` / `high` based on route
  criticality and complexity.
* `expected_future_agent_a_phase` — the planned Agent A phase
  numbering (e.g. 51O, 51P).
* `expected_characterization_phase` — the planned Agent A
  characterization phase (the "characterize the inline route"
  step).
* `expected_extraction_phase` — the planned Agent A extraction
  phase (the "extract the route into a service module" step).
* `governance_impact` — how the route's extraction affects the
  B-track governance state.
* `pilot_impact` — how the route's extraction affects the
  pilot surface area.
* `external_review_impact` — how the route's extraction affects
  the external review readiness state.
* `no_go_claim_impact` — whether the route's extraction changes
  any no-go claim. (For these 5 hotspots, the answer is `none`
  for the no-go list itself; the extraction is a route /
  service / code change on the Agent A track, not a no-go
  change.)
* `agent_b_refresh_trigger` — what the B-track does when the
  Agent A phase lands.
* `notes` — additional context.

## 3. The 5 routes

### 3.1 `POST /projects/{code}/save-as`

* `current_inline_status`: inline in `main_web.py` (Agent A
  owned). The route handles project save-as; it is the inline
  counterpart to the `projects_create_service.py` extracted in
  Phase 51M-2.
* `risk_level`: `medium` — save-as involves project cloning and
  parameter handling; complex enough to warrant characterization
  before extraction.
* `expected_future_agent_a_phase`: `51O`.
* `expected_characterization_phase`: 51O-1 (the "characterize
  the inline /save-as route" step).
* `expected_extraction_phase`: 51O-2 (the "extract /save-as into
  a service module" step).
* `governance_impact`: B3 matrix AREA-019 update; B8
  architecture dimension increment (12 → 13 service-backed
  routes, 13 → 14 service modules); B14 governance refresh
  tracker addition.
* `pilot_impact`: If save-as is in pilot scope (B7 + B9), the
  pilot surface area changes after extraction. Pin refresh or
  forward-compatibility decision is required if save-as is
  pilot-claim-allowed.
* `external_review_impact`: B10 data room index update; B16
  closeout tracker update.
* `no_go_claim_impact`: `none` — the route is a save-as for
  project clone, not a no-go category. The no-go list is
  unchanged.
* `agent_b_refresh_trigger`: When the Agent A phase lands,
  update this tracker, the B3 matrix, the B8 tracker, the B14
  refresh tracker, and the B10 data room index.
* `notes`: Save-as is the most natural follow-up to the
  `projects_create_service.py` extraction in 51M-2. The Agent
  A work on this route will follow the same pattern as 51M-1
  (characterization) + 51M-2 (extraction).

### 3.2 `POST /scenarios/{id}/rename`

* `current_inline_status`: inline in `main_web.py` (Agent A
  owned). The route handles scenario rename; it is a
  persistence-adjacent operation.
* `risk_level`: `low` — rename is a simple string update; lower
  complexity than save-as or update-overrides.
* `expected_future_agent_a_phase`: `51P`.
* `expected_characterization_phase`: 51P-1.
* `expected_extraction_phase`: 51P-2.
* `governance_impact`: B3 matrix AREA-019 update; B8
  architecture dimension increment; B14 governance refresh
  tracker addition.
* `pilot_impact`: If rename is in pilot scope, the pilot
  surface area changes after extraction.
* `external_review_impact`: B10 data room index update; B16
  closeout tracker update.
* `no_go_claim_impact`: `none` — rename is a simple string
  update, not a no-go category.
* `agent_b_refresh_trigger`: Same as 3.1.
* `notes`: Rename is the simplest of the 5 hotspots. The Agent
  A work on this route will follow the same pattern as 51K-1 +
  51K-2 (or 51L-1 + 51L-2).

### 3.3 `POST /scenarios/{id}/archive`

* `current_inline_status`: inline in `main_web.py` (Agent A
  owned). The route handles scenario archive; it is a
  persistence-adjacent operation that changes scenario state.
* `risk_level`: `medium` — archive involves state
  transition (active → archived) and downstream visibility
  changes; more complex than rename.
* `expected_future_agent_a_phase`: `51Q`.
* `expected_characterization_phase`: 51Q-1.
* `expected_extraction_phase`: 51Q-2.
* `governance_impact`: B3 matrix AREA-019 update; B8
  architecture dimension increment; B14 governance refresh
  tracker addition.
* `pilot_impact`: If archive is in pilot scope, the pilot
  surface area changes after extraction.
* `external_review_impact`: B10 data room index update; B16
  closeout tracker update.
* `no_go_claim_impact`: `none` — archive is a state transition,
  not a no-go category.
* `agent_b_refresh_trigger`: Same as 3.1.
* `notes`: Archive is similar in pattern to
  `scenarios/state/*` already extracted in Phase 51H-2. The
  Agent A work on this route may reuse patterns from 51H-2.

### 3.4 `POST /scenarios/{id}/update-overrides`

* `current_inline_status`: inline in `main_web.py` (Agent A
  owned). The route handles scenario update-overrides; it is
  a persistence-adjacent operation that updates scenario
  parameters.
* `risk_level`: `high` — update-overrides is the most
  complex of the 5 hotspots. It involves parameter validation,
  override semantics, and downstream impact on the model run.
* `expected_future_agent_a_phase`: `51R`.
* `expected_characterization_phase`: 51R-1.
* `expected_extraction_phase`: 51R-2.
* `governance_impact`: B3 matrix AREA-019 update; B8
  architecture dimension increment; B14 governance refresh
  tracker addition.
* `pilot_impact`: If update-overrides is in pilot scope, the
  pilot surface area changes after extraction. Pin refresh or
  forward-compatibility decision is required if
  update-overrides is pilot-claim-allowed.
* `external_review_impact`: B10 data room index update; B16
  closeout tracker update.
* `no_go_claim_impact`: `none` — update-overrides is a
  parameter update, not a no-go category.
* `agent_b_refresh_trigger`: Same as 3.1.
* `notes`: Update-overrides is the highest-risk of the 5
  hotspots. The Agent A work on this route will follow the
  same pattern as 51K-1 + 51K-2 (or 51L-1 + 51L-2) with
  additional validation.

### 3.5 `POST /scenarios/{id}/select`

* `current_inline_status`: inline in `main_web.py` (Agent A
  owned). The route handles scenario select; it is a
  persistence-adjacent operation that sets the active scenario
  for the user.
* `risk_level`: `medium` — select involves active-scenario
  tracking; the impact is on which scenario is "active" in
  the UI.
* `expected_future_agent_a_phase`: `51S`.
* `expected_characterization_phase`: 51S-1.
* `expected_extraction_phase`: 51S-2.
* `governance_impact`: B3 matrix AREA-019 update; B8
  architecture dimension increment; B14 governance refresh
  tracker addition.
* `pilot_impact`: If select is in pilot scope, the pilot
  surface area changes after extraction.
* `external_review_impact`: B10 data room index update; B16
  closeout tracker update.
* `no_go_claim_impact`: `none` — select is an active-scenario
  setter, not a no-go category.
* `agent_b_refresh_trigger`: Same as 3.1.
* `notes`: Select is similar in pattern to the
  `scenarios/state/*` extraction in Phase 51H-2. The Agent A
  work on this route may reuse patterns from 51H-2.

## 4. The "Agent B does not perform the extraction" rule

**Agent B does not perform the extraction.** The 5 extractions
are Agent A work. Agent B:

* may read the Agent A files for context (B14 governance
  refresh plan §4);
* may not modify any Agent A file;
* may update this tracker when the Agent A phase lands (B15 +
  B17 governance refresh);
* may update the B3 matrix, B8 tracker, B10 data room index,
  B14 refresh tracker, and B16 closeout tracker when the
  Agent A phase lands.

A violation of the rule (Agent B modifying an Agent A file) is
a serious issue. The remedy is to revert the violation, identify
how it happened, and update the process to prevent recurrence.

## 5. Expected future Agent A phase numbering

The expected future Agent A phase numbering for the 5 hotspots
is a planning convention:

| Route | Expected phase |
|---|---|
| `POST /projects/{code}/save-as` | 51O (51O-1 char, 51O-2 extract) |
| `POST /scenarios/{id}/rename` | 51P (51P-1 char, 51P-2 extract) |
| `POST /scenarios/{id}/archive` | 51Q (51Q-1 char, 51Q-2 extract) |
| `POST /scenarios/{id}/update-overrides` | 51R (51R-1 char, 51R-2 extract) |
| `POST /scenarios/{id}/select` | 51S (51S-1 char, 51S-2 extract) |

The actual phase numbering may differ. The B-track updates the
tracker when the actual phase lands.

## 6. Updating this tracker

When Agent A merges a characterization or extraction phase for
one of the 5 hotspots:

1. Update the `current_inline_status` field (or remove the
   route entry, if extracted).
2. Add a new entry to the B14 governance refresh tracker's
   `agent_a_phase_log`.
3. Update the B3 matrix AREA-019.
4. Update the B8 architecture dimension summary.
5. Update the B10 data room index (if the 51N section needs
   updating).
6. Update the B16 closeout tracker (if the ready_for_external_
   review state changes).
7. Optionally, update the B12 heatmap (if any area's confidence
   label changes).

The update is performed by Agent B as a normal B-track governance
refresh (B14 §5). It is not a code change.

## 7. Cross-references

* `reports/governance/remaining_hotspots_governance_tracker.json`
  (B17, machine-readable)
* `docs/governance/agent_a_b_governance_refresh_plan.md` (B14)
* `reports/governance/governance_refresh_tracker.json` (B14,
  agent_a_phase_log)
* `docs/validation/validation_evidence_matrix.md` (B3 narrative)
* `reports/validation/validation_evidence_matrix.json` (B3
  matrix, AREA-019)
* `docs/validation/model_confidence_heatmap.md` (B12)
* `reports/validation/model_confidence_heatmap.json` (B12
  heatmap, HC-012)
* `docs/roadmap/enterprise_saas_readiness_tracker.md` (B8
  narrative)
* `reports/roadmap/enterprise_saas_readiness_tracker.json` (B8
  tracker, architecture and persistence dimensions)
* `docs/external_review/data_room_index.md` (B10)
* `docs/external_review/external_review_closeout_tracker.md`
  (B16)
* `docs/external_review/no_go_claims.md` (B1, no-go list)
* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)

---

*End of remaining hotspots governance tracker.*
