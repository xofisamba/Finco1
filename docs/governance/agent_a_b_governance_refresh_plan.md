# Agent A / Agent B Governance Refresh Plan

This file is the **refresh plan** for the B-track governance
documents after Agent A merges route / service work. It defines
when a refresh is required, which documents are likely to go stale,
how to detect stale references, how to refresh without touching
code, and the explicit rule that Agent B never modifies Agent A
files.

> **The refresh plan is internal governance. It is not a code
> change. It does not authorize any external claim.** A refresh
> is a normal B-track operation that updates governance docs to
> reflect the current state of the model after Agent A's work.

---

## 1. Why this plan exists

Agent A owns the route / service extraction work in Phase 51+.
The B-track governance documents (B1, B3, B7, B8, B9, B10, B11, B12,
B13, B14, B15, B16, B17, B18, B19) reference Agent A's work
indirectly through:

* base SHA references (which move when main moves);
* phase commit references (51G-1, 51G-2, 51G-3, 51H-1, 51H-2, 51I,
  51J-1, 51J-2, 51K-1, 51K-2, 51L-1, 51L-2, 51M-1, 51M-2, 51N, ...);
* per-area evidence in the B3 matrix (e.g. AREA-019 covers
  recent Agent A route / state work; AREA-020 covers the Phase 51N
  checkpoint);
* B8 architecture and persistence dimensions (which reference
  Agent A's most recent extractions — 12 service-backed routes,
  13 service modules reached at Phase 51N; 5 remaining inline
  hotspots tracked in B17);
* B13 paid pilot gate (which references Agent A's `/save-run`,
  `/scenarios/state/*`, `/scenarios/save`, `/scenarios/{id}/duplicate`,
  `/scenarios/add`, `/projects/create` work);
* B16 external review closeout tracker (which is independent of
  Claude review);
* B17 remaining hotspots tracker (5 routes — `save-as`, `rename`,
  `archive`, `update-overrides`, `select` — with expected future
  Agent A phase numbering 51O/51P/51Q/51R/51S).

When Agent A merges a new route / state / service, these
references can become stale. A stale reference is not a security
issue, but it is a documentation / matrix consistency issue. This
plan defines how to detect and refresh stale references.

## 2. When a refresh is required

A refresh is required when **any** of the following is true:

* **Agent A merges a new route / state / service work that the
  B-track documents reference.** The trigger is the merge of any
  Phase 51+ phase that touches a route, a state, a service, or a
  related artifact that the B-track documents mention by name
  (e.g. `/save-run`, `/scenarios/state/draft`,
  `/scenarios/state/discard`, `/scenarios/save`,
  `/scenarios/{id}/duplicate`, `/scenarios/add`, `/projects/create`).
* **Agent A merges a new Phase 51F pin or pin-change.** The B3
  matrix's parity-core lock and engine-output golden guardrail
  reference Phase 51F. A new pin or pin-change must be reflected
  in the B3 matrix and in the B12 heatmap.
* **Agent A merges a refactor that renames a file in the
  Agent A ownership list.** The B3 matrix's `evidence_files` and
  `tests_or_reports_to_check` arrays reference specific files. A
  rename may break those references.
* **Agent A merges a Phase 51N-style checkpoint.** The Phase 51N
  checkpoint landed Agent B docs integration and a Claude review
  preparation pack. Future checkpoints (e.g. Phase 51O, 51P, etc.)
  may include similar Agent B integration that requires a B-track
  refresh to keep the matrix / heatmap / data room in sync.
* **The user explicitly requests a refresh.** This is the catch-all
  trigger.

A refresh is **not** required for Agent A work that does not
affect the B-track documents (e.g. a refactor inside an
Agent A file that does not change its name or its semantics).

**Important — Claude review is separate.** Phase 51N includes a
"Claude review preparation pack" (Agent A side), but the Claude
review itself is performed outside the Agent B branch and outside
the B-track governance pack. A Claude review result, when
provided by the user, will be reflected in B16 (External Review
Closeout Tracker) only — and only as a separate workstream, never
as a side-effect of B15. Do not treat any B-track refresh as a
Claude review result.

## 3. Documents likely to go stale

The B-track documents most likely to go stale are:

* `docs/validation/validation_evidence_matrix.md` and
  `reports/validation/validation_evidence_matrix.json` (B3) —
  references to phases, SHAs, files, and tests.
* `docs/validation/model_confidence_heatmap.md` and
  `reports/validation/model_confidence_heatmap.json` (B12) —
  references to phases and the B3 matrix.
* `docs/pilot/controlled_pilot_runbook.md` (B7) — references to
  /save-run and the persistence layer.
* `docs/pilot/pilot_validation_execution_pack.md` (B9) — references
  to the B3 matrix and the B7 runbook.
* `docs/external_review/data_room_index.md` (B10) — references to
  all B-track artifacts; refreshed to include the 51N section.
* `docs/external_review/reviewer_evidence_checklist.md` (B10) —
  references to all B-track artifacts.
* `docs/external_review/external_review_closeout_tracker.md` and
  `reports/external_review/external_review_closeout_status.json`
  (B16) — explicit closeout state independent of Claude review.
* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11) —
  references to the B1 no-go list (no refresh needed unless the
  B1 no-go list changes).
* `docs/roadmap/enterprise_saas_readiness_tracker.md` and
  `reports/roadmap/enterprise_saas_readiness_tracker.json` (B8) —
  references to Agent A's most recent extractions.
* `docs/governance/agent_a_b_governance_refresh_plan.md` (B14, this
  file) — references to the trigger conditions.
* `docs/governance/remaining_hotspots_governance_tracker.md` and
  `reports/governance/remaining_hotspots_governance_tracker.json`
  (B17) — 5 remaining inline hotspots.
* `docs/pilot/controlled_pilot_launch_checklist.md` and
  `reports/pilot/controlled_pilot_launch_checklist.json` (B18) —
  practical launch checklist; uses B7 + B9 + B13 as input.
* `docs/pilot/post_pilot_evidence_update_template.md`,
  `reports/pilot/post_pilot_evidence_update_template.json`,
  `docs/commercial/demo_script_guardrail.md`,
  `reports/commercial/demo_claims_checklist.json` (B19) — pilot
  follow-up + demo script guardrail; uses B11 as input.

## 4. How to detect stale references

A stale reference is detected by:

* **Periodic rebase of the B-track branch onto latest main.** The
  rebase will produce a clear "what changed" diff between the
  previous base and the new base. The B-track owner reviews the
  diff for any reference that is now stale.
* **Phase commit log on main.** The B-track owner periodically
  inspects `git log origin/main --oneline` for new Phase 51+
  commits. Each new commit is a potential trigger.
* **User-reported staleness.** If the user or a reviewer
  identifies a stale reference, the B-track owner treats it as
  a refresh trigger.
* **CI as a smell test.** If the CI tests on the rebased B-track
  branch surface a failure that is unrelated to the B-track
  artifacts, the failure may indicate a refactor that needs a
  B-track refresh. (B-track artifacts are docs and JSON; they
  should not cause test failures. A test failure after a B-track
  rebase is a sign that a referenced file has changed.)

The B-track owner does not run Agent A's tests. The B-track owner
reads the commit log and the diff to identify what changed.

## 5. How to refresh without touching code

A refresh is a normal B-track operation that updates governance
documents only. The procedure:

1. **Identify the stale references.** Use the methods in §4 to
   find references in the B-track documents that are now stale.
2. **Open a new branch from latest main.** Use the convention
   `parallel-b-governance-refresh-<short-description>` for the
   branch name. (Or use the same umbrella branch if a refresh
   is being made as part of a larger B-track umbrella.)
3. **Update the stale references.** Replace absolute SHAs with
   relative wording where possible. Update per-area references
   in the B3 matrix. Update per-dimension references in the B12
   heatmap. Update per-gate references in the B13 gate.
4. **Verify the package.** Run `git status --short`,
   `git diff --stat`, and `git diff --name-only`. Confirm no code,
   no route, no service, no Agent A file is touched. Confirm the
   refresh is docs/report only.
5. **Open a PR.** Use the standard B-track PR process. Tag the PR
   as a governance refresh, not a feature change. Use the
   `governance_refresh_tracker.json` (B14, machine-readable) to
   record the refresh.
6. **Wait for CI.** CI is a smoke test; a refresh should not
   break tests. If CI fails, investigate before merging.
7. **Merge after review.** The user explicitly approves the
   refresh PR.

The refresh is never a code change. It is never a route, a
service, a fixture CSV, a schema, a migration, or a persistence
change. It is never a change to any Agent A file.

## 6. Checklist for reviewing Agent A Phase 51 route changes from
   governance perspective

When Agent A merges a new Phase 51+ phase, the B-track owner
reviews it from a governance perspective. The checklist is:

* [ ] **Phase commit identified.** What is the phase number, the
      SHA, and the title? Is the phase in the B-track's expected
      set of phases (route extraction, service extraction, route
      characterization, scenario state, scenario duplicate, scenario
      add, projects create, post-M2 checkpoint, etc.)?
* [ ] **Routes / services affected.** What routes or services are
      affected? Are they referenced in any B-track document?
* [ ] **Test files affected.** What new test files are added?
      Are they referenced in the B3 matrix's
      `tests_or_reports_to_check` arrays?
* [ ] **B3 matrix rows affected.** Are any B3 matrix areas
      affected (current_status, evidence_category, missing_evidence,
      dependencies, notes)? If yes, refresh.
* [ ] **B8 architecture and persistence dimensions affected.**
      Are the architecture and persistence summaries still
      accurate (12 service-backed routes, 13 service modules,
      5 remaining inline hotspots tracked in B17)? If no, refresh.
* [ ] **B13 paid pilot gate affected.** Does the new phase
      affect the pilot surface area? If yes, refresh.
* [ ] **B12 heatmap affected.** Does the new phase change the
      confidence label of any B12 area? If yes, refresh.
* [ ] **B17 remaining hotspots tracker affected.** Is the new
      phase a characterization or extraction of one of the 5
      remaining inline hotspots (`save-as`, `rename`, `archive`,
      `update-overrides`, `select`)? If yes, update the B17
      tracker with the new SHA and the new state.
* [ ] **B16 external review closeout tracker affected.** Does
      the new phase change what is ready for external review,
      what is missing, or what cannot be claimed? If yes, refresh
      B16 (Claude review remains separate and is not represented
      here as completed).
* [ ] **B1 no-go list affected.** Does the new phase change any
      no-go claim? If yes, refresh the B1 list (separate
      governance change) and the B11 commercial messaging
      guardrail.
* [ ] **B11 commercial messaging guardrail affected.** Does the
      new phase introduce a new claim category? If yes, refresh.
* [ ] **Decision: refresh required?** If any of the above are
      affected, a refresh is required. The decision is recorded
      in `reports/governance/governance_refresh_tracker.json`.

The checklist is recorded per refresh in the tracker JSON.

## 7. Tracker JSON for pending refreshes

The tracker is at
`reports/governance/governance_refresh_tracker.json` (B14,
machine-readable). It records:

* `pending_refreshes` — refreshes that have been identified but
  not yet executed;
* `completed_refreshes` — refreshes that have been merged;
* `cancelled_refreshes` — refreshes that were identified but
  determined not to be required (with rationale);
* `agent_a_phase_log` — a log of Agent A phases that have been
  reviewed, with the B-track impact assessed per phase.

The tracker is updated as part of normal B-track work. After
B15, the tracker has 15 phase entries (51G-1 through 51N) and
1 completed refresh (B15 itself).

## 8. The "Agent B never modifies Agent A files" rule

**Agent B never modifies Agent A files.** This is a hard rule.
The rule applies regardless of refresh trigger, regardless of
documentation need, regardless of any other consideration.

The Agent A ownership list (from the project rules) is:

* `main_web.py`
* `main_api.py`
* `app/services/`
* `app/waterfall_core.py`
* `app/project_factories.py`
* `domain/`
* `project_factories.py`
* `repository.py`
* `app/templates/`
* `app/static/`
* fixture CSVs
* `reports/*senior_debt*.csv`
* schema / migrations
* `tests/test_phase51*.py`
* `tests/test_phase52*.py`
* any Agent A route / service extraction files
* `rc1`

Agent B may read these files for context. Agent B may not modify
them. A refresh is a docs-only change; it never modifies any
file in the Agent A ownership list.

A violation of the rule is a serious issue. The remedy is to
revert the violation, identify how it happened, and update the
process to prevent recurrence.

## 9. What this plan is not

* It is not a contract. It is internal governance.
* It is not a code change.
* It is not external validation.
* It is not a substitute for any B-track artifact.
* It is not a justification for Agent B to modify Agent A files.
* It is not Claude review. Claude review is separate.

## 10. Cross-references

* `reports/governance/governance_refresh_tracker.json` (B14,
  machine-readable)
* `reports/governance/remaining_hotspots_governance_tracker.json`
  (B17, machine-readable)
* `docs/validation/validation_evidence_matrix.md` (B3)
* `docs/validation/model_confidence_heatmap.md` (B12)
* `docs/pilot/controlled_pilot_runbook.md` (B7)
* `docs/pilot/pilot_validation_execution_pack.md` (B9)
* `docs/pilot/paid_pilot_readiness_gate.md` (B13)
* `docs/pilot/controlled_pilot_launch_checklist.md` (B18)
* `docs/pilot/post_pilot_evidence_update_template.md` (B19)
* `docs/external_review/data_room_index.md` (B10)
* `docs/external_review/external_review_closeout_tracker.md` (B16)
* `docs/commercial/no_go_claims_commercial_guardrail.md` (B11)
* `docs/commercial/demo_script_guardrail.md` (B19)
* `docs/roadmap/enterprise_saas_readiness_tracker.md` (B8)
* `docs/governance/agent_a_b_governance_refresh_plan.md` (B14, this
  file)
* `docs/external_review/no_go_claims.md` (B1)

---

*End of governance refresh plan.*
