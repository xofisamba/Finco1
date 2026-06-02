# Reviewer Evidence Checklist

This file is the **per-artifact reviewer evidence checklist** for
the external reviewer. It is the per-question template for the
reviewer's per-artifact output, cross-referenced from
`docs/external_review/data_room_index.md`.

> **The reviewer is bound by the no-go claim list
> (`docs/external_review/no_go_claims.md`) and is explicitly
> forbidden from producing any external-claim language.** This
> checklist is internal-validation scaffolding, not external
> validation. See `docs/validation/internal_vs_external_validation_boundaries.md`.

---

## 1. How to use this checklist

For each artifact in the data room, the reviewer is expected to
address a short list of questions. The reviewer's output addresses
each question with:

* a short answer (1–3 sentences);
* a citation to the file and line range at the base SHA;
* a per-area go / conditional-go / no-go opinion.

The reviewer's overall go / no-go opinion is the intersection of
per-artifact opinions, plus an explicit acknowledgement of the
no-go claim list.

## 2. Per-artifact checklist

### 2.1 B1 external review package

For each file in the B1 package, the reviewer is expected to
address:

* `docs/external_review/external_review_package_index.md` — is the
  package internally consistent? Does the SHA history chain
  correctly? Is the reading order sensible?
* `docs/external_review/reviewer_instructions.md` — are the
  reviewer instructions clear, complete, and consistent with the
  no-go claim list?
* `docs/external_review/model_scope_and_limitations.md` — is the
  model scope accurately described? Are the limitations honestly
  documented? Are exploratory areas (generic solar / wind) clearly
  marked as such?
* `docs/external_review/tuho_oborovo_validation_summary.md` — are
  the TUHO and Oborovo pins accurate at the base SHA? Is the
  pre-flight evidence honest? Are the goldens within tolerance at
  the base SHA?
* `docs/external_review/no_go_claims.md` — is the no-go list
  complete and unambiguous? Are the categories exhaustive?
* `reports/external_review/external_review_readiness_matrix.json` —
  is the matrix internally consistent? Are the per-area flags
  honest?

### 2.2 B3 validation evidence matrix

For each area in the B3 matrix (currently 19 areas), the reviewer
is expected to address:

* Is `evidence_category` the strongest category that honestly
  applies?
* Is `current_status` accurate at the base SHA?
* Are `evidence_files` and `tests_or_reports_to_check` present
  and correctly named?
* Is `missing_evidence` complete and honest?
* Is `external_claim_allowed` correctly `false` (it should be in
  all rows at this time)?
* Is `pilot_claim_allowed` consistent with the B9 execution pack
  and the B7 runbook?
* Are `blockers`, `dependencies`, and `notes` consistent with the
  code, the tests, and the B1 package?

The reviewer is also expected to enumerate the test files and run
them locally, reporting observed pass / fail / skip per file.

### 2.3 B2 generic reference acquisition

For each file in B2, the reviewer is expected to address:

* `docs/generic_validation/generic_reference_acquisition_plan.md` —
  is the acquisition framework realistic? Are the six-component
  test, the metadata requirements, the parity outputs, and the
  acceptance thresholds appropriate?
* `docs/generic_validation/generic_solar_reference_requirements.md`
  and `generic_wind_reference_requirements.md` — are the
  technology-specific requirements realistic? Are the rejection
  criteria appropriate?
* `docs/generic_validation/generic_validation_no_go_boundaries.md` —
  is the no-go enforcement boundary clear? Is it consistent with
  the B1 no-go list?
* `reports/generic_validation/reference_model_inventory_template.json`
  — is the schema complete? Are the status values exhaustive?
* `reports/generic_validation/generic_validation_readiness_matrix.json`
  — is the gate tracker correct? Are the promotion criteria
  realistic?

The reviewer is expected to confirm that the B2 inventory is
empty and that no reference has been acquired yet (per the
readiness matrix's `accepted_count_per_technology: 0`).

### 2.4 B7 controlled pilot runbook

For each file in B7, the reviewer is expected to address:

* `docs/pilot/controlled_pilot_runbook.md` — is the runbook
  realistic? Are the success / failure criteria conservative? Is
  the no-go enforcement clear?
* `docs/pilot/pilot_user_feedback_protocol.md` — is the feedback
  form honest? Is the storage and retention boundary clear?
* `docs/pilot/pilot_issue_triage_process.md` — are the categories,
  severities, and outcomes exhaustive? Is the escalation path
  sensible?
* `docs/ops/support_and_incident_response.md` — are the response
  tiers and on-call expectations realistic? Is the post-incident
  review process documented?
* `reports/pilot/pilot_readiness_checklist.json` — is the gate
  tracker correct?

The reviewer is expected to confirm that no pilot has started
yet (per the B9 execution checklist's `gates_pending: 11`).

### 2.5 B8 enterprise SaaS readiness tracker

For each dimension in the B8 tracker (currently 11 dimensions),
the reviewer is expected to address:

* Is `current_percentage` a self-assessment that is not externally
  validated?
* Is `target_percentage` a project-internal goal that does not
  authorize any external claim?
* Are `blockers`, `dependencies`, and `next_actions` realistic?
* Are `gate_criteria` honest?
* Are `no_go_claims` consistent with the B1 no-go list?

The reviewer is also expected to confirm that the
`enterprise_saas_readiness` dimension has `current_percentage: 10`
and `target_percentage: null`.

### 2.6 B9–B14 pilot review pack (this branch)

For each file in B9–B14, the reviewer is expected to address:

* B9 pilot validation execution pack — does the execution pack
  turn the B7 runbook and the B3 matrix into executable steps?
  Are the per-area criteria conservative? Is the result-summary
  template honest?
* B10 data room index (this file's parent) — does the index
  cover all B-track artifacts? Is the cross-mapping correct?
* B11 commercial messaging guardrail — are the prohibited
  claims exhaustive? Is the red/yellow/green language
  classification clear?
* B12 model confidence heatmap — is the heatmap honest? Are the
  confidence labels conservative?
* B13 paid pilot readiness gate — is the gate between controlled
  internal pilot and controlled paid pilot clearly drawn? Is the
  post-pilot evidence update process documented?
* B14 governance refresh plan — is the trigger for refreshing
  B3/B7/B8/B9/B10/B12/B13 clear? Is the "Agent B never modifies
  Agent A files" rule explicit?

### 2.7 Cross-cutting

The reviewer is expected to confirm:

* the no-go claim list is acknowledged;
* the internal vs external validation boundaries are documented
  and consistent;
* the B1 package is treated as documentation / evidence prep, not
  external validation;
* the B3 matrix is treated as an internal working artifact, not
  external validation;
* the B2 framework is treated as a preparation, not validation;
* the B7 pilot is internal validation, not external validation;
* the B8 tracker is internal planning, not external validation;
* the B9 execution pack, B10 data room, B11 commercial guardrail,
  B12 confidence heatmap, B13 paid pilot gate, and B14 refresh
  plan are all internal validation scaffolding.

## 3. The reviewer's required output

The reviewer's output is per-artifact, with the structure defined
in `docs/external_review/reviewer_qna_template.md`. The reviewer's
overall go / no-go opinion is per-area, with a final
acknowledgement of the no-go claim list.

The reviewer is **not** required to:

* certify the model for any lender, bank, audit, certification,
  regulatory, or SaaS purpose;
* approve any closed, blocked, exploratory, or not-yet-approved
  area for production use;
* produce any external-claim language.

## 4. Cross-references

* `docs/external_review/data_room_index.md` (B10)
* `docs/external_review/reviewer_qna_template.md` (B10)
* `reports/external_review/missing_evidence_tracker.json` (B10)
* `docs/external_review/external_review_package_index.md` (B1)
* `docs/external_review/reviewer_instructions.md` (B1)
* `docs/external_review/no_go_claims.md` (B1)
* `docs/validation/internal_vs_external_validation_boundaries.md` (B3)

---

*End of reviewer evidence checklist.*
